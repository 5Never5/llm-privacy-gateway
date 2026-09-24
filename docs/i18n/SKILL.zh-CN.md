---
name: llm-privacy-gateway
description: 隐私保护大模型网关：在把内容发给第三方模型（官方 API 或不可信中转站）之前，本地完成核心机密文件加密存储、文件/图片文字本地提取、敏感字段脱敏（令牌化），结果返回后本地还原并做泄露校验，全程审计。零本地算力要求——无需部署本地模型，脱敏/提取/加密全部在本机 CPU 上瞬时完成，推理由云端或中转站承担。适用于以下场景：(1) 用户要用第三方/中转模型服务但担心真实数据泄露；(2) 需要处理含个人信息、企业机密、合同金额、手机号身份证等敏感字段的文本或文件（PDF/Word/Excel/图片）；(3) 需要"真实敏感数据不出域、窃取亦不可还原"的合规诉求。触发词：脱敏、防泄露、中转站、隐私网关、令牌化、数据不出域、敏感信息保护。
---

> **Note / 说明**：本文件是 `SKILL.md` 的简体中文翻译版本，仅供阅读参考。
> **技能实际加载的是仓库根目录下的 `llm-privacy-gateway/SKILL.md`（英文版）**，请勿把本文件当作生效的技能定义。

# LLM 隐私网关

在发送给第三方模型前，把真实敏感数据留在本地：脱敏（令牌化）→ 发送脱敏文本 → 本地还原 + 校验 + 审计。**真实内容（含文件、图片本体）永不跨越本机边界。**

## 核心安全边界

- **零本地算力**：本 Skill 不要求部署本地模型/GPU。脱敏、文字提取、加密、还原全部在本机 CPU 上轻量完成，推理完全由云端或中转站承担；
- 文件/图片：先用 `local_extract.py` 在本地提取文字，**本体永不上传**；
- 文本：`masker.py` 把敏感字段替换为会话级随机令牌（映射表只留本地），只有脱敏文本出域；
- 端点（官方 API、中转站）一律视为不可信通道，只接收脱敏文本；
- 核心商业机密：默认用 `crypto_store.py` 加密存储、**不送任何模型**；确需分析时先脱敏发送（接受残余风险）；
- 审计：每次请求写入 `~/.llm-privacy-gate/audit.jsonl`。

## 跨智能体工具使用（不是独立软件，是一个 Skill）

本技能是标准**技能文件夹**（`SKILL.md` + `scripts/` + `references/`），采用 Agent Skills 开放标准，
可原样加载到以下工具（把整个 `llm-privacy-gateway` 文件夹复制到对应工具的 skills 目录即可）：

| 工具 | 放置位置 |
| --- | --- |
| 豆包工作 | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` 或项目 `.codex/skills/` |
| DeepSeek Harness | 项目 `.dsh/skills/`（原生兼容 Skills 规范） |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude 系 / 其他兼容 Agent Skills 标准工具 | 按各自 skills 目录约定 |

使用方式不变：**对 Agent 说一句话**（如"用隐私网关处理这个合同"），Agent 读取本技能并调用 `scripts/` 执行；
用户界面由各平台提供，本技能不需要也不提供 GUI。
每个新环境首次使用前：`python scripts/setup_deps.py` 补齐依赖（见下）。

## 快速开始

```bash
# 0) 新环境首次使用：检查/安装依赖（跨平台）
python scripts/setup_deps.py --check      # 只检查
python scripts/setup_deps.py              # 安装缺失依赖
python scripts/setup_deps.py --install-ocr  # 需要图片 OCR 时

# 1) 脱敏 + 干跑（不发送）：查看将出域的内容
python scripts/gateway.py --text "Acme 公司的账单：卡号 4111111111111111，总额 5,000 元" --dry-run

# 2) 配置端点（复制 references/config.example.json 到 ~/.llm-privacy-gate/config.json 修改）
#    中转站示例已预置（name=relay），填入 base_url；API Key 走环境变量，勿写入配置文件

# 3) 真实发送（走中转站；环境变量 PowerShell 用 $env:RELAY_API_KEY=..., Bash 用 export RELAY_API_KEY=...）
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "分析这份报价单：Jane Doe，报价 12000 元" --endpoint relay

# 4) 处理文件（本地提取文字，本体不出域；路径按本机实际调整）
python scripts/gateway.py --file ./合同/报价单.pdf --endpoint relay

# 5) （可选）本机装有 Ollama 时，核心机密可强制本地推理
python scripts/gateway.py --file ./机密/规划.docx --local

# 6) 文件加密存储（核心商业机密）
python scripts/crypto_store.py encrypt --in 机密.docx --out 机密.docx.enc
python scripts/crypto_store.py decrypt --in 机密.docx.enc --out 机密.docx

# 7) 严格模式：命中企业词典的核心机密 → 拒绝发送（仅审计）
python scripts/gateway.py --file ./机密/规划.docx --endpoint relay --strict
```

> 配置自动加载顺序：`--config` 指定 > 环境变量 `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > 内置示例。
> 复制 `references/config.example.json` 到 `~/.llm-privacy-gate/config.json` 修改即可，无需每次带 `--config`。

## 批量处理文件夹（由 Agent 循环，脚本保持单文件职责）

当用户要求"处理整个文件夹/目录"时，**不要给脚本加批量参数**——由 Agent 按以下工作流执行循环：

1. 枚举目录内支持的文件（txt/md/csv/json/pdf/docx/xlsx/常见图片；跳过 `.enc` 加密文件）；
2. 逐个调用 `python scripts/gateway.py --file <路径> [--endpoint <名>] [--strict]`；
3. 每个文件的结果独立输出；失败文件单独列出原因（提取失败 / 泄露拦截 exit 3 / 严格拦截 exit 4）；
4. 结束后汇总：成功数 / 失败数 / 出域请求数 / 审计条目数（`~/.llm-privacy-gate/audit.jsonl` 每文件一条）；
5. 泄露拦截或严格拦截的文件必须醒目提示，不得静默跳过。

## 模块说明

### 1. 脱敏 `scripts/masker.py`
- 内置规则：身份证 / 手机号 / 座机 / 邮箱 / 银行卡 / IP / 金额；
- 自定义词典：`~/.llm-privacy-gate/custom_words.json`（公司名、人名、项目代号必须在此配置）；
- 会话级随机令牌 `{PHONE-xxxx-N}`，防跨会话关联；
- CLI：`mask` / `restore` / `check-leak` 三个子命令，供单独调试。

### 2. 本地提取 `scripts/local_extract.py`
- 支持：txt/md/csv/json、PDF、Word(.docx)、Excel(.xlsx)、常见图片(OCR)；
- `--ocr-lang` 指定 OCR 语言（默认 `en`，中文用 `ch`，中英混排可用 `en+ch`）；
- OCR 未安装时给出明确安装指引；
- 只输出文本，文件本体不出域。

### 3. 加密存储 `scripts/crypto_store.py`
- AES-256-GCM，密钥自动生成于 `~/.llm-privacy-gate/key.bin`（首用生成，请备份）；
- 密文文件可放心存放/传输，无密钥不可解密。

### 4. 网关 `scripts/gateway.py`
- 管线：输入 → 本地提取 → 脱敏 → 发送 → 还原 + 泄露校验 → 审计；
- 泄露校验：模型输出若出现已脱敏的真实值，**阻止展示并记录审计**；
- `--strict`：输入命中企业词典（核心机密）时**拒绝出域**，仅记录审计（exit 4）；
- `--dry-run` 预览将发送的脱敏载荷，不发真实请求。

### 5. 依赖管理 `scripts/setup_deps.py`
- 新环境（Codex/DeepSeek Harness 等）首次运行前执行，自动检查/安装：cryptography、pypdf、python-docx、openpyxl、Pillow；
- `--check` 只检查；`--install-ocr` 额外装 OCR；OCR 缺失不影响文本/PDF/Word/Excel 处理。

## 配置

见 `references/config.example.json` 与 `references/rules.md`（规则清单、安全边界、审计格式）。
配置优先级：`--config` 指定 > 环境变量 `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > 内置示例。
API Key 一律通过环境变量注入（如 `OPENAI_API_KEY`、`RELAY_API_KEY`），禁止写入配置文件。

## 使用边界（务必先读 references/rules.md）

- 脱敏只保护命中规则的内容；未命中的业务上下文仍会出域；
- 模型返回的"分析结论"对端点可见；
- 绝对意义上"模型完全理解 + 服务商无法解密"不可兼得；本网关实现"真实敏感数据不可获取、窃取不可还原"；
- 高危内容（核心商业机密）优先 `--local` 或加密存储，不出域。

## 许可证

Apache 许可证 2.0 版 —— 可以使用、修改、再分发，包括用于商业用途。完整正文见本文件夹内的 `LICENSE`。

这个文件夹通常是单独安装的，所以条款必须跟着它走。请把 `LICENSE` 与 `NOTICE` 与本文件放在一起，并在转发任何副本时保留下面三行（英文原文，照抄即可）：

```
LLM Privacy Gateway — Copyright 2026 5Never5 (https://github.com/5Never5)
Licensed under the Apache License, Version 2.0
https://www.apache.org/licenses/LICENSE-2.0
```

这里不包含任何第三方源码：脚本为原创，只引用 Python 标准库。安装后调用的那些库 —— cryptography、pypdf、python-docx、openpyxl、Pillow，以及可选的 pytesseract 或 paddleocr —— 各自遵循自己的许可证，仓库中的 `THIRD-PARTY-NOTICES.md` 逐一记录。

---

<p align="center"><b>🌐</b> <a href="../../README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="RULES.zh-CN.md">中文规则说明</a> · <a href="../../llm-privacy-gateway/SKILL.md">英文 SKILL</a></p>
