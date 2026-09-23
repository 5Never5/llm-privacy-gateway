#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway · 脱敏模块 (masker.py)

在本地完成敏感字段识别与令牌化替换，保证真实数据不出域：
  - 内置正则规则库：身份证、手机号、座机、邮箱、银行卡、IP、金额
  - 自定义词典：公司名、人名、项目代号等（~/.llm-privacy-gate/custom_words.json）
  - 会话级随机令牌：每次运行生成随机会话后缀，防止跨会话关联分析
  - 映射表只保存在本地，还原与泄露校验均在本地完成

用法:
  python masker.py mask --text "..." [--out-mapping map.json]
  python masker.py mask --file input.txt [--out-mapping map.json]
  python masker.py restore --text "..." --mapping map.json
  python masker.py check-leak --output "模型返回原文" --mapping map.json
"""
import argparse
import json
import os
import random
import re
import string
import sys

HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
CUSTOM_WORDS_FILE = os.path.join(HOME_DIR, "custom_words.json")

# 内置规则：(类型, 正则)。类型名即令牌前缀。
BUILTIN_RULES = [
    ("ID_CARD", r"(?<!\d)\d{17}[\dXx](?!\d)"),          # 18 位身份证
    ("PHONE",   r"(?<!\d)1[3-9]\d{9}(?!\d)"),           # 大陆手机号
    ("TEL",     r"(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)"),     # 座机
    ("EMAIL",   r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    ("BANKCARD", r"(?<!\d)\d{16,19}(?!\d)"),            # 银行卡/卡号段
    ("IP",      r"(?<!\d)(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
                r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}(?!\d)"),
    ("AMOUNT",  r"(?<![\d.])(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{1,2})?"
                r"(?=\s*(?:元|人民币|RMB|￥|¥))"),
]


def _load_custom_words():
    """读取自定义词典：{"words": ["公司甲", "张三", "项目代号X"]}"""
    try:
        with open(CUSTOM_WORDS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        words = data.get("words", [])
        return [w for w in words if isinstance(w, str) and w.strip()]
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


class Masker:
    def __init__(self, enabled_types=None, session_id=None, custom_words=None):
        # 会话后缀：同一字段在不同会话产生不同令牌，防止跨会话关联
        self.session_id = session_id or "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4))
        enabled = set(enabled_types) if enabled_types else set()
        self.patterns = [(t, re.compile(p)) for t, p in BUILTIN_RULES
                         if not enabled or t in enabled]
        self.custom_words = list(
            custom_words if custom_words is not None else _load_custom_words())
        if self.custom_words:
            joined = "|".join(
                re.escape(w) for w in sorted(self.custom_words, key=len, reverse=True))
            self.custom_pattern = re.compile(joined)
        else:
            self.custom_pattern = None
        self.mapping = {}      # token -> 原始值
        self.counter = 0

    def _token(self, typ):
        self.counter += 1
        return "{%s-%s-%d}" % (typ, self.session_id, self.counter)

    def mask(self, text):
        out = text
        for typ, pat in self.patterns:
            def repl(m, _typ=typ):
                value = m.group(0)
                token = self._token(_typ)
                self.mapping[token] = value
                return token
            out = pat.sub(repl, out)
        if self.custom_pattern:
            def crepl(m):
                token = self._token("DICT")
                self.mapping[token] = m.group(0)
                return token
            out = self.custom_pattern.sub(crepl, out)
        return out

    def restore(self, text):
        out = text
        for token in sorted(self.mapping, key=len, reverse=True):
            out = out.replace(token, self.mapping[token])
        return out

    def check_leak(self, raw_output):
        """在还原前调用：检查模型原始输出是否泄露了真实值"""
        leaks = []
        for token, value in self.mapping.items():
            if value and value in raw_output:
                leaks.append({"token": token, "value": value})
        return leaks

    def check_residue(self, restored):
        """在还原后调用：检查输出是否残留未还原的令牌"""
        return [t for t in self.mapping if t in restored]

    def masked_stats(self):
        return {"fields": len(self.mapping), "tokens": self.counter}


def _read_input(text, path):
    if text is not None:
        return text
    if path:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    return sys.stdin.read()


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway 脱敏模块")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_mask = sub.add_parser("mask", help="脱敏（令牌化）")
    p_mask.add_argument("--text", default=None)
    p_mask.add_argument("--file", default=None)
    p_mask.add_argument("--out-mapping", default=None)
    p_mask.add_argument("--session", default=None)

    p_res = sub.add_parser("restore", help="还原")
    p_res.add_argument("--text", default=None)
    p_res.add_argument("--file", default=None)
    p_res.add_argument("--mapping", required=True)

    p_leak = sub.add_parser("check-leak", help="泄露校验")
    p_leak.add_argument("--output", required=True)
    p_leak.add_argument("--mapping", required=True)

    args = ap.parse_args()

    if args.cmd == "mask":
        text = _read_input(args.text, args.file)
        m = Masker(session_id=args.session)
        masked = m.mask(text)
        print(masked)
        payload = {
            "session_id": m.session_id,
            "mapping": m.mapping,
            "stats": m.masked_stats(),
        }
        if args.out_mapping:
            os.makedirs(os.path.dirname(os.path.abspath(args.out_mapping)) or ".",
                        exist_ok=True)
            with open(args.out_mapping, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2),
                  file=sys.stderr)

    elif args.cmd == "restore":
        text = _read_input(args.text, args.file)
        with open(args.mapping, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = Masker(session_id=data.get("session_id", ""))
        m.mapping = data.get("mapping", {})
        restored = m.restore(text)
        residue = m.check_residue(restored)
        print(restored)
        if residue:
            print("警告：以下令牌未还原 → %s" % residue, file=sys.stderr)

    elif args.cmd == "check-leak":
        with open(args.mapping, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = Masker(session_id=data.get("session_id", ""))
        m.mapping = data.get("mapping", {})
        leaks = m.check_leak(args.output)
        if leaks:
            print("泄露！模型输出中出现真实值：")
            for item in leaks:
                print("  %s -> %s" % (item["token"], item["value"]))
            sys.exit(2)
        print("校验通过：模型输出中未发现已脱敏的真实值。")


if __name__ == "__main__":
    main()
