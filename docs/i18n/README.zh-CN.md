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
  <a href="../../LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-007EC6" alt="Apache 许可证 2.0" /></a>
  <a href="../../THIRD-PARTY-NOTICES.md"><img src="https://img.shields.io/badge/third--party_notices-2DD4BF" alt="已列出第三方声明" /></a>
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

> **要在公司里用？** 没有什么需要买的。Apache 2.0 本身就覆盖商业用途，没有付费档位，也没有授权需要申请。许可证唯一要求的是署名：转发任何副本时，请把 [NOTICE](../../NOTICE) 与 [THIRD-PARTY-NOTICES.md](../../THIRD-PARTY-NOTICES.md) 一并保留。

## ⚙️ 配置

复制 `references/config.example.json` 到 `~/.llm-privacy-gate/config.json`。优先级：`--config` → `LPG_CONFIG` → `~/.llm-privacy-gate/config.json` → 内置示例。API Key 仅从环境变量读取。

## ⚠️ 边界

完整规则集与正则写法见 `references/rules.md`。

- 脱敏只保护命中规则的内容 —— 未命中的内容仍会出域。
- "模型完全理解，同时服务商无法解密"在密码学上不可能成立。本网关实际做到的是：真实数据无法被获取，被窃取的内容也无法还原。
- 高危内容（核心机密）请使用 `--local` 或加密存储 —— 完全不让它上网。

[使用场景](use-cases.zh-CN.md)会具体说明这些边界在真实文档上意味着什么、干跑到底会打印出什么，以及哪些情况下这个网关本身就是错的工具。依赖它之前值得花十分钟读一遍。

## ☕ 支持

业余项目，背后没有公司，没有广告，没有遥测，也没有任何功能被锁在价格后面。许可证是 Apache 2.0，在公司里用也不花一分钱，没有任何授权需要购买。

这个项目真正缺的是时间，而这一页上唯一能买到时间的只有打赏。可以算一笔账：那些本该手动脱敏的下午，是它替你省下来的；那些以前不敢交给 API 的客户文件，现在可以直接给。既然真省下过时间，回赠一点，就是让下一个“省下来的下午”继续发生 —— 每一笔打赏都会变成实打实投在这个项目上的时间，而这些时间没有别的来源。

- ⭐ **给项目点个 Star** —— 不花钱，而且真正能让项目被更多人看到
- 🐛 **提一个 Bug** —— 说实话，比打赏更有价值
- 📣 **转给一个需要它的人** —— 零成本，而且能精准触达
- ☕ **打赏** —— 最直接地为这个项目争取更多时间

<p align="center">
  <a href="SUPPORT.zh-CN.md"><b>☕ 打赏方式 · 收款码见此</b></a>
  <br />
  <sub>侧边栏的 <b>Sponsor</b> 按钮指向的也是这一页。</sub>
</p>

## 📄 许可证

[Apache 许可证 2.0 版](../../LICENSE) —— 可以使用、修改、再分发，包括用于商业用途与闭源项目。没有付费档位，没有需要申请的授权，也没有任何被扣下的功能。

它唯一要求的回报是署名。转发任何副本时请保留 [NOTICE](../../NOTICE) 文件。如果你单独分发技能文件夹 —— 而技能通常就是这么安装的 —— 那么 `llm-privacy-gateway/LICENSE` 与 `llm-privacy-gateway/NOTICE` 就在文件夹里面：一个被复制进别人 skills 目录的文件夹，不会把仓库根目录一起带过去。

**第三方组件。** 这里没有从别的项目拷来的代码，但脚本会调用你自己安装的那些库：`cryptography`、`pypdf`、`python-docx`、`openpyxl`、`Pillow`，以及可选的 `pytesseract` 或 `paddleocr`。它们各自遵循自己的许可证与版权。[THIRD-PARTY-NOTICES.md](../../THIRD-PARTY-NOTICES.md) 逐一列出它们、各自的用途，以及它们的许可证对你有什么要求 —— 把它打包进产品之前值得读一遍。

本次变更之前发布的版本曾采用 MIT 许可证，并短暂采用过非商业许可证。那两份授权对当时已取得的每一份副本都继续有效，且无法撤回。本次及之后的版本采用 Apache 2.0。

## 🌐 语言版本

| 语言 | README | 技能说明 | 规则 | 使用场景 | 打赏 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| English | [README](../../README.md) | [Skill](../../llm-privacy-gateway/SKILL.md) | [Rules](../../llm-privacy-gateway/references/rules.md) | [Use cases](../use-cases.md) | [Support](../SUPPORT.md) |
| 简体中文 | 本页 | [技能说明](SKILL.zh-CN.md) | [规则](RULES.zh-CN.md) | [使用场景](use-cases.zh-CN.md) | [打赏](SUPPORT.zh-CN.md) |

`NOTICE` 与 `THIRD-PARTY-NOTICES.md` 只有英文，这是有意的：它们是要随副本一起流传的署名文件，而一份被翻译过的声明，很容易让接收者读到的内容与许可证实际写的条款出现偏差。

---

<p align="center"><sub><a href="#top">回到顶部</a></sub></p>
