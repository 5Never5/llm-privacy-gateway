#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway · 隐私网关主程序 (gateway.py)

编排完整管线：输入(文本/文件) → 本地提取 → 敏感度判定 → 脱敏(令牌化)
→ 发送(本地模型 / 官方API / 中转站) → 还原 + 泄露校验 → 审计日志。

安全边界：
  - 真实内容（含文件、图片本体）永不离开本机
  - 出域的只有"已脱敏文本"（占位符 + 无敏感规则命中的普通文本）
  - 任何端点（包括中转站）都被视为不可信通道，只接收脱敏文本
  - 审计日志记录每次请求的出域情况

用法:
  python gateway.py --text "帮我分析张三的合同，金额 5000 元" --dry-run
  python gateway.py --file 合同.pdf --endpoint relay --model gpt-4o-mini
  python gateway.py --text "..." --local                 # 走本地 Ollama
  python gateway.py --text "..." --endpoint official     # 走官方 API
环境变量: OPENAI_API_KEY / RELAY_API_KEY / OLLAMA 等，见 references/config.example.json
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masker import Masker, BUILTIN_RULES, _load_custom_words
import local_extract

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(SKILL_DIR, "references", "config.example.json")
HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
AUDIT_FILE = os.path.join(HOME_DIR, "audit.jsonl")
USER_CONFIG = os.path.join(HOME_DIR, "config.json")

SYSTEM_PROMPT = (
    "提示词中 {类型-xxxx-N} 形式的令牌是本地脱敏的敏感字段占位符，"
    "请直接基于上下文正常回答：不要追问占位符的真实内容，不要猜测或编造，"
    "不要把这些令牌复制到回答文本之外的地方。"
)


def load_config(path=None):
    """配置优先级：--config > 环境变量 LPG_CONFIG > ~/.llm-privacy-gate/config.json > 默认示例"""
    candidates = []
    if path:
        candidates.append(path)
    env = os.environ.get("LPG_CONFIG")
    if env:
        candidates.append(env)
    candidates.append(USER_CONFIG)
    candidates.append(DEFAULT_CONFIG)
    for p in candidates:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise SystemExit("找不到任何配置文件：%s" % " / ".join(candidates))


def resolve_endpoint(cfg, name, use_local):
    if use_local:
        local = cfg.get("local")
        if not local or not local.get("base_url"):
            raise SystemExit("--local 已指定，但配置中未定义 local 端点")
        return {"name": "local", "kind": "local", **local}
    eps = cfg.get("endpoints", [])
    if name:
        for e in eps:
            if e.get("name") == name:
                return {"kind": "remote", **e}
        raise SystemExit("配置中不存在端点：%s" % name)
    for e in eps:
        key_env = e.get("api_key_env", "")
        if key_env and os.environ.get(key_env):
            return {"kind": "remote", **e}
    if eps:
        return {"kind": "remote", **eps[0]}
    raise SystemExit("未配置任何端点，请编辑 references/config.example.json")


def chat_completion(endpoint, model, messages, timeout=180):
    base = endpoint["base_url"].rstrip("/")
    url = base + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    key_env = endpoint.get("api_key_env")
    api_key = os.environ.get(key_env) if key_env else None
    if api_key:
        req.add_header("Authorization", "Bearer " + api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit("HTTP %s 调用失败：%s" % (exc.code, detail))
    except urllib.error.URLError as exc:
        raise SystemExit("网络错误：%s" % exc.reason)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise SystemExit("响应格式异常：%s" % json.dumps(data, ensure_ascii=False)[:500])


def audit(entry):
    os.makedirs(HOME_DIR, exist_ok=True)
    entry["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(
        description="llm-privacy-gateway 隐私网关：真实数据不出域")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", default=None, help="输入文本")
    src.add_argument("--file", default=None, help="输入本地文件（本地提取文字）")
    ap.add_argument("--endpoint", default=None, help="端点名：official / relay 等")
    ap.add_argument("--local", action="store_true",
                    help="可选：本机装有 Ollama 时强制走本地模型；本 Skill 默认不需要")
    ap.add_argument("--model", default=None, help="覆盖模型名")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印将发送的脱敏载荷与映射统计，不真正发送")
    ap.add_argument("--strict", action="store_true",
                    help="严格模式：输入命中企业词典(DICT 核心机密)时拒绝发送，仅审计，核心机密不出域")
    ap.add_argument("--config", default=None, help="配置文件路径")
    ap.add_argument("--no-mask", action="store_true", help="跳过脱敏（仅测试用）")
    ap.add_argument("--prompt", default="请根据输入内容完成分析并直接给出结论。",
                    help="任务提示词（可选）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    endpoint = resolve_endpoint(cfg, args.endpoint, args.local)
    model = args.model or endpoint.get("model", "")

    if endpoint.get("kind") == "remote":
        key_env = endpoint.get("api_key_env")
        if key_env and not os.environ.get(key_env):
            print("[警告] 未设置环境变量 %s 的 API Key，请求可能被端点拒绝。"
                  % key_env, file=sys.stderr)

    # 1) 输入：文件在本地提取文字，本体不出域
    input_note = ""
    if args.file:
        raw = local_extract.extract_text(args.file)
        input_note = "文件 %s 已在本地提取 %d 字符，文件本体未上传" % (
            os.path.basename(args.file), len(raw))
    else:
        raw = args.text
    print("[输入] %s" % input_note if input_note else "[输入] 文本 %d 字符" % len(raw))

    # 2) 脱敏
    if args.no_mask:
        masked = raw
        masker = None
        print("[脱敏] 已跳过（--no-mask，仅测试）")
    else:
        masker = Masker()
        masked = masker.mask(raw)
        stats = masker.masked_stats()
        print("[脱敏] 命中 %d 个敏感字段，生成 %d 个令牌，会话 %s"
              % (stats["fields"], stats["tokens"], masker.session_id))
        if stats["fields"] == 0 and len(_load_custom_words()) == 0:
            print("[提示] 未命中任何敏感字段——若内容含企业机密，请补充自定义词典"
                  "（%s）" % os.path.join(HOME_DIR, "custom_words.json"))

    # 2.5) 严格模式：命中企业词典（核心机密）→ 拒绝出域
    if args.strict and masker and any(t.startswith("{DICT-") for t in masker.mapping):
        print("[阻止] 严格模式：内容命中企业词典（核心机密），拒绝发送。"
              "可先用 crypto_store.py 加密存储。", file=sys.stderr)
        audit({"mode": "strict-blocked", "endpoint": endpoint["name"],
               "masked_fields": masker.masked_stats()["fields"]})
        sys.exit(4)

    # 3) 构建载荷
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args.prompt + "\n\n" + masked},
    ]
    print("[端点] %s（%s）模型 %s" % (
        endpoint["name"], endpoint.get("kind", ""), model or "(默认)"))

    if args.dry_run:
        print("\n===== 将发送的脱敏载荷（dry-run，未发送）=====")
        print(json.dumps({"model": model, "messages": messages},
                         ensure_ascii=False, indent=2))
        if masker:
            print("\n===== 脱敏映射（仅本地）=====")
            for t, v in masker.mapping.items():
                print("  %s -> %s" % (t, v))
        audit({"mode": "dry-run", "endpoint": endpoint["name"],
               "in_chars": len(raw), "masked_fields": masker.masked_stats()["fields"]
               if masker else 0})
        return

    # 4) 发送
    t0 = time.time()
    print("[发送] 正在请求 %s ..." % endpoint["name"])
    output = chat_completion(endpoint, model, messages)
    cost_ms = int((time.time() - t0) * 1000)

    # 5) 还原 + 泄露校验
    if masker:
        leaks = masker.check_leak(output)
        if leaks:
            print("[严重] 模型输出泄露了 %d 个真实值，已阻止展示！" % len(leaks),
                  file=sys.stderr)
            for item in leaks:
                print("  %s -> %s" % (item["token"], item["value"]),
                      file=sys.stderr)
            audit({"mode": "leak-blocked", "endpoint": endpoint["name"],
                   "leaks": len(leaks), "cost_ms": cost_ms})
            sys.exit(3)
        restored = masker.restore(output)
        residue = masker.check_residue(restored)
        if residue:
            print("[警告] 输出残留未还原令牌：%s" % residue, file=sys.stderr)
        final = restored
        print("[校验] 未发现真实值泄露，已还原 %d 个字段" % len(masker.mapping))
    else:
        final = output

    audit({"mode": "ok", "endpoint": endpoint["name"],
           "in_chars": len(raw), "out_chars": len(output),
           "masked_fields": masker.masked_stats()["fields"] if masker else 0,
           "cost_ms": cost_ms})

    print("\n===== 模型回答（已本地还原）=====")
    print(final)


if __name__ == "__main__":
    main()
