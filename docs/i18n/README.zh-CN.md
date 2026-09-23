<p align="center"><b>🌐</b> <a href="../../README.md">English</a> · <a href="README.zh-CN.md">简体中文</a></p>

<p align="center"><img src="../../docs/banner.jpg" alt="llm-privacy-gateway" width="100%" /></p>

# 🛡️ LLM Privacy Gateway

<p align="center"><b>真实敏感数据不出域 —— 用第三方 API 或不可信中转站也不泄密。</b></p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Agent%20Skills-Open%20Standard-8A2BE2" alt="Agent Skills 开放标准" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Cross--Agent-Codex%20%7C%20DSH%20%7C%20OpenClaw%20%7C%20WorkBuddy%20%7C%20Claude%20%7C%20Doubao-0e83cd" alt="跨智能体工具" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Encryption-AES--256--GCM-critical" alt="AES-256-GCM" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Zero%20Local%20Compute-CPU%20Only-success" alt="零本地算力" /></a>
</p>

跨智能体技能：敏感字段本地令牌化，文件/图片本地解析（**本体永不上传**），只有脱敏文本发往官方 API 或中转站；结果本地还原并做泄露校验，每次请求全程审计。

## 功能

| 模块 | 脚本 | 作用 |
| --- | --- | --- |
| 脱敏 | `scripts/masker.py` | 身份证/手机/邮箱/银行卡/IP/金额 + 自定义词典 → 会话级随机令牌 |
| 本地提取 | `scripts/local_extract.py` | PDF/Word/Excel/图片(OCR) 本地提取 — 本体永不上传 |
| 加密存储 | `scripts/crypto_store.py` | 核心机密 AES-256-GCM 加密；密钥仅存本地 |
| 隐私网关 | `scripts/gateway.py` | 提取 → 脱敏 → 发送 → 还原 + 泄露校验 → 审计 |
| 依赖管理 | `scripts/setup_deps.py` | 一键检查/安装依赖 |

## 安全

- 任何端点（含中转站）**均视为不可信**——只发脱敏文本；泄露真实值即拦截（exit 3）；`--strict` 命中企业词典拒绝出域（exit 4）；请求审计至 `~/.llm-privacy-gate/audit.jsonl`。
- 零本地算力：脱敏/提取/加密在本机 CPU 完成；推理仍由云端或中转站承担。
- 会话级随机令牌 `{PHONE-xxxx-N}` 防跨会话关联；核心机密默认加密。

## 安装

标准 Agent 技能文件夹（`SKILL.md` + `scripts/` + `references/`），复制到兼容工具的 skills 目录即可；界面由各平台 Agent 提供。

| 工具 | 位置 |
| --- | --- |
| 豆包工作 | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` 或 `.codex/skills/` |
| DeepSeek Harness | `.dsh/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude 及其他 Agent Skills 工具 | 按各工具约定 |

每个新环境首次运行：`python scripts/setup_deps.py`

## 快速开始

```bash
# 干跑（不发送）：预览将出域内容
python scripts/gateway.py --text "张三的手机 13800138000，金额 5000 元" --dry-run

# 走中转站发送（API Key 走环境变量：$env:RELAY_API_KEY=... / export RELAY_API_KEY=...）
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "分析这份报价单：李四，报价 12000 元" --endpoint relay

# 处理文件（本地提取，本体不出域）
python scripts/gateway.py --file ./合同/报价单.pdf --endpoint relay

# 严格模式：命中企业词典拒绝出域
python scripts/gateway.py --file ./机密/规划.docx --endpoint relay --strict
```

## 配置

复制 `references/config.example.json` → `~/.llm-privacy-gate/config.json`。优先级：`--config` > `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > 内置示例。API Key 仅走环境变量。

## 边界（见 `references/rules.md`）

- 脱敏只保护命中规则的内容，未命中内容仍会出域。
- "模型完全理解 + 服务商无法解密"不可兼得；本网关实现：真实数据不可获取、窃取不可还原。
- 高危内容（核心机密）：用 `--local` 或加密存储，不出域。
