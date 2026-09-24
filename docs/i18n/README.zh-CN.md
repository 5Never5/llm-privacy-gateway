<p align="center"><a id="top"></a><b>🌐</b> <a href="../../README.md">English</a> · 简体中文</p>

<p align="center"><img src="../../docs/banner.jpg" alt="LLM Privacy Gateway" width="100%" /></p>

<h1 align="center">🛡️ LLM Privacy Gateway</h1>

<p align="center"><b>真实敏感数据不出域 —— 即便使用第三方 API 或不可信中转站。</b></p>

<p align="center">
  <a href="#-工作原理"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+" /></a>
  <a href="#-安装"><img src="https://img.shields.io/badge/Agent%20Skills-Open%20Standard-8A2BE2" alt="Agent Skills 开放标准" /></a>
  <a href="#-安装"><img src="https://img.shields.io/badge/Cross--Agent-Codex%20%7C%20DSH%20%7C%20OpenClaw%20%7C%20WorkBuddy%20%7C%20Claude%20%7C%20Doubao-0e83cd" alt="跨智能体工具" /></a>
  <a href="#-安全模型"><img src="https://img.shields.io/badge/Encryption-AES--256--GCM-critical" alt="AES-256-GCM" /></a>
  <a href="#-工作原理"><img src="https://img.shields.io/badge/Zero%20Local%20Compute-CPU%20Only-success" alt="零本地算力" /></a>
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-F5A623" alt="PolyForm 非商业许可证 1.0.0" /></a>
  <a href="COMMERCIAL.zh-CN.md"><img src="https://img.shields.io/badge/Commercial%20use-licence%20required-4B5563" alt="商业用途需取得授权" /></a>
</p>

<p align="center">
  <a href="#-工作原理">工作原理</a> &nbsp;·&nbsp;
  <a href="#-功能">功能</a> &nbsp;·&nbsp;
  <a href="use-cases.zh-CN.md">使用场景</a> &nbsp;·&nbsp;
  <a href="#-安装">安装</a> &nbsp;·&nbsp;
  <a href="#-快速开始">快速开始</a> &nbsp;·&nbsp;
  <a href="#-安全模型">安全</a> &nbsp;·&nbsp;
  <a href="#-支持">支持</a> &nbsp;·&nbsp;
  <a href="#-许可证">许可证</a>
</p>

---

## 🔍 工作原理

跨智能体技能：敏感字段本地令牌化，文件与图片本地解析（**本体永不上传**），只有脱敏文本发往官方 API 或中转站；结果本地还原并做泄露校验，每次请求全程审计。

无框架、无后端、无常驻进程 —— 纯 Python 脚本，跑在本机 CPU 上。

<p align="center"><img src="../../docs/assets/flow.svg" alt="数据流：文件与敏感值在本机解析和替换，只有脱敏文本抵达服务商，结果本地还原并审计。" width="100%" /></p>

## ✨ 功能

| 模块 | 脚本 | 作用 |
| :--- | :--- | :--- |
| 🔍 **脱敏** | `scripts/masker.py` | 身份证 / 手机 / 座机 / 邮箱 / 银行卡 / IP / 金额 + 自定义词典 → 会话级随机令牌 |
| 📄 **本地提取** | `scripts/local_extract.py` | PDF / Word / Excel / 图片（OCR）本地提取 —— 本体永不上传 |
| 🔐 **加密存储** | `scripts/crypto_store.py` | 核心机密采用 AES-256-GCM 加密；密钥仅存本地 |
| 🚦 **隐私网关** | `scripts/gateway.py` | 提取 → 脱敏 → 发送 → 还原 + 泄露校验 → 审计 |
| 📦 **依赖管理** | `scripts/setup_deps.py` | 一键检查与安装依赖 |

## 🚀 快速开始

```bash
# 干跑（不发送）：预览将出域的内容
python scripts/gateway.py --text "Invoice for Acme Corp: card 4111111111111111, total 5,000 USD" --dry-run

# 经中转站发送（API Key 走环境变量：$env:RELAY_API_KEY=... / export RELAY_API_KEY=...）
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "Summarise this quote: Jane Doe, quoted 12,000 USD" --endpoint relay

# 处理文件（文本本地提取，本体不出域）
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# 严格模式：命中企业词典即拒绝出域
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

## 🔐 安全模型

- 任何端点 —— 包括中转站 —— **均视为不可信**。只发脱敏文本；泄露真实值即拦截（exit 3）；`--strict` 命中企业词典拒绝出域（exit 4）；每次请求追加写入 `~/.llm-privacy-gate/audit.jsonl`。
- **零本地算力**：脱敏、提取与加密在本机 CPU 完成，无需显卡；推理仍由云端服务商或中转站承担。
- **会话级随机令牌**（如 `{PHONE-xxxx-N}`）防止跨会话关联；核心机密默认加密。

## 📦 安装

标准 Agent 技能文件夹（`SKILL.md` + `scripts/` + `references/`），复制到任意兼容工具的 skills 目录即可 —— 界面由该平台的 Agent 提供。

| 工具 | 位置 |
| :--- | :--- |
| 豆包工作 | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` 或 `.codex/skills/` |
| DeepSeek Harness | `.dsh/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude 及其他 Agent Skills 工具 | 按各工具自身的目录约定 |

安装后每个环境运行一次：

```bash
python scripts/setup_deps.py
```

> **要在公司里用？** 个人、教育、科研、慈善与政府用途免费，无需授权。但公司把它用于自身业务 —— 哪怕只是用来脱敏自家合同 —— 属于商业用途，需要取得商业授权。详见 [商业用途](COMMERCIAL.zh-CN.md)：一次性费用，软件本身不会有任何差别。

## ⚙️ 配置

复制 `references/config.example.json` 到 `~/.llm-privacy-gate/config.json`。优先级：`--config` → `LPG_CONFIG` → `~/.llm-privacy-gate/config.json` → 内置示例。API Key 仅从环境变量读取。

## ⚠️ 边界

完整规则集与正则写法见 `references/rules.md`。

- 脱敏只保护命中规则的内容 —— 未命中的内容仍会出域。
- "模型完全理解，同时服务商无法解密"在密码学上不可能成立。本网关实际做到的是：真实数据无法被获取，被窃取的内容也无法还原。
- 高危内容（核心机密）请使用 `--local` 或加密存储 —— 完全不让它上网。

[使用场景](use-cases.zh-CN.md)会具体说明这些边界在真实文档上意味着什么、干跑到底会打印出什么，以及哪些情况下这个网关本身就是错的工具。依赖它之前值得花十分钟读一遍。

## ☕ 支持

业余项目，背后没有公司，没有广告，没有遥测，也没有任何功能被锁在价格后面。个人与非商业用途依据许可证免费，并且一直免费；唯一收费的是商业使用许可，这是有意为之。

所以这里不是付费墙，只是一个随喜的钱箱。不过可以算一笔账：那些本该手动脱敏的下午，是它替你省下来的；那些以前不敢交给 API 的客户文件，现在可以直接给。既然真省下过时间，回赠一点，就是让下一个“省下来的下午”继续发生 —— 每一笔打赏都会变成实打实投在这个项目上的时间，而这些时间没有别的来源。

**如果是在公司里用，请别打赏，直接买授权** —— 在同一页，而且那才是真正支撑下一个版本的东西。

- ⭐ **给项目点个 Star** —— 不花钱，而且真正能让项目被更多人看到
- 🐛 **提一个 Bug** —— 说实话，比打赏更有价值
- 📣 **转给一个需要它的人** —— 零成本，而且能精准触达
- ☕ **打赏** —— 最直接地为这个项目争取更多时间
- 🧾 **购买商业授权** —— 如果受益的是公司

<p align="center">
  <a href="SUPPORT.zh-CN.md"><b>☕ 打赏方式 · 收款码见此</b></a>
  <br />
  <sub>侧边栏的 <b>Sponsor</b> 按钮指向的也是这一页。</sub>
</p>

## 📄 许可证

本项目采用 [PolyForm 非商业许可证 1.0.0](../../LICENSE) 发布 —— 个人、教育、科研、慈善与政府用途免费。**商业用途需要取得授权**，[商业用途](../../docs/COMMERCIAL.md)说明了授权范围与申请方式（中文版见[这里](COMMERCIAL.zh-CN.md)）。

实操上的分界：在公司里用它做公司的事，或者把它打包进你要卖的东西里，都算商业用途；其余情况一律免费，并且一直免费。

这份许可证不锁任何东西 —— 不锁功能、不锁规则、不锁内容。它管的是**谁可以把它用于商业目的**，不是软件能做什么。买商业授权买的是许可，不是能力。

本次换证之前发布的版本采用 MIT 许可证，**那份授权无法撤回**：任何在 MIT 期间取得副本的人，就那份副本永久保有当时授予的权利。只有本次变更之后的版本才适用 PolyForm 非商业许可证。

## 🌐 语言版本

| 语言 | README | 技能说明 | 规则 | 使用场景 | 打赏 | 商业授权 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| English | [README](../../README.md) | [Skill](../../llm-privacy-gateway/SKILL.md) | [Rules](../../llm-privacy-gateway/references/rules.md) | [Use cases](../use-cases.md) | [Support](../SUPPORT.md) | [Commercial](../COMMERCIAL.md) |
| 简体中文 | 本页 | [技能说明](SKILL.zh-CN.md) | [规则](RULES.zh-CN.md) | [使用场景](use-cases.zh-CN.md) | [打赏](SUPPORT.zh-CN.md) | [商业授权](COMMERCIAL.zh-CN.md) |

---

<p align="center"><sub><a href="#top">回到顶部</a></sub></p>
