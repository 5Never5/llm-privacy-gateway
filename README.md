<p align="center">
  <img src="docs/banner.jpg" alt="llm-privacy-gateway — 古典油画风格网络安全横幅" width="100%" />
</p>

<h1 align="center">🛡️ LLM Privacy Gateway</h1>

<p align="center">
  <b>真实敏感数据不出域 —— 即使用第三方官方 API 或不可信中转站，也不泄密。</b>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Agent%20Skills-Open%20Standard-8A2BE2" alt="Agent Skills 开放标准" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Cross--Agent-Codex%20%7C%20DSH%20%7C%20Claude%20%7C%20Doubao-0e83cd" alt="跨智能体工具" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Encryption-AES--256--GCM-critical" alt="AES-256-GCM" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Zero%20Local%20Compute-CPU%20Only-success" alt="零本地算力" /></a>
</p>

---

## 🎨 一幅画，也是一面盾

这张横幅本身就是本项目的宣言，画面里的每个元素都对应一条安全设计：

| 画面元素 | 对应机制 |
| --- | --- |
| 中央古铜盾牌 + 发光锁孔 | **密钥只存本地**（`~/.llm-privacy-gate/key.bin`），没有它，任何密文都不可解 |
| 盾面青蓝电路纹路 | 脱敏（令牌化）替换规则，敏感字段在出域前被改写 |
| 缠绕的锁链 | 文件 / 图片**本体永不上传**，只有本地提取的文字出域 |
| 左侧破碎的旧挂锁 | 旧防线（明文直连、字典加密）已被击穿，本项目是更坚固的新防线 |
| 神经网络节点网络 | 出域内容只够模型完成推理，不足以还原任何真实数据 |
| 流动的 0 / 1 数据流 | 中转站 / 官方 API 拿到的只是脱敏文本与占位符 |

---

## ✨ 核心能力

| 模块 | 脚本 | 作用 |
| --- | --- | --- |
| 脱敏（令牌化） | `scripts/masker.py` | 身份证 / 手机号 / 座机 / 邮箱 / 银行卡 / IP / 金额 + 自定义企业词典，替换为会话级随机令牌 |
| 本地文字提取 | `scripts/local_extract.py` | PDF / Word(.docx) / Excel(.xlsx) / 图片(OCR) 在本地提取文字，**文件本体永不上传** |
| 加密存储 | `scripts/crypto_store.py` | 核心商业机密 AES-256-GCM 加密，密钥仅存本地 |
| 隐私网关 | `scripts/gateway.py` | 提取 → 脱敏 → 发送（官方/中转站） → 本地还原 + 泄露校验 → 审计 |
| 依赖管理 | `scripts/setup_deps.py` | 新环境一键检查/安装依赖 |

## 🔒 安全边界

> **任何端点（含中转站）都被视为不可信通道**，只接收脱敏文本。
> 模型输出若泄露真实值，网关**阻止展示**（exit 3）；`--strict` 命中企业词典时**拒绝出域**（exit 4）；
> 每次请求写入 `~/.llm-privacy-gate/audit.jsonl`，全程可审计。

- 零本地算力：脱敏 / 提取 / 加密全部在本机 CPU 上瞬时完成，推理由云端或中转站承担；
- 会话级随机令牌 `{PHONE-xxxx-N}`，防跨会话关联；
- 核心商业机密默认加密存储，确需分析时先脱敏发送（接受残余风险，见边界）。

## 📦 安装到各智能体工具

它不是一个独立软件，而是一个标准 **Agent 技能文件夹**（`SKILL.md` + `scripts/` + `references/`），
复制到对应工具的 skills 目录即可，用户界面由各平台的 Agent 提供：

| 工具 | 放置位置 |
| --- | --- |
| 豆包工作 | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` 或项目 `.codex/skills/` |
| DeepSeek Harness | 项目 `.dsh/skills/`（原生兼容 Skills 规范） |
| Claude 系 / 其他兼容 Agent Skills 标准工具 | 按各自 skills 目录约定 |

每个新环境首次使用前：

```bash
python scripts/setup_deps.py --check      # 只检查
python scripts/setup_deps.py              # 安装缺失依赖
python scripts/setup_deps.py --install-ocr  # 需要图片 OCR 时
```

## 🚀 快速开始

```bash
# 1) 脱敏 + 干跑（不发送）：查看将出域的内容
python scripts/gateway.py --text "张三的手机 13800138000，金额 5000 元" --dry-run

# 2) 配置端点（复制 references/config.example.json 到 ~/.llm-privacy-gate/config.json 修改）
#    中转站示例已预置（name=relay），填入 base_url；API Key 走环境变量，勿写入配置文件

# 3) 真实发送（走中转站；环境变量 PowerShell 用 $env:RELAY_API_KEY=..., Bash 用 export RELAY_API_KEY=...）
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "分析这份报价单：李四，报价 12000 元" --endpoint relay

# 4) 处理文件（本地提取文字，本体不出域）
python scripts/gateway.py --file ./合同/报价单.pdf --endpoint relay

# 5) （可选）本机装有 Ollama 时，核心机密可强制本地推理
python scripts/gateway.py --file ./机密/规划.docx --local

# 6) 文件加密存储（核心商业机密）
python scripts/crypto_store.py encrypt --in 机密.docx --out 机密.docx.enc
python scripts/crypto_store.py decrypt --in 机密.docx.enc --out 机密.docx

# 7) 严格模式：命中企业词典的核心机密 → 拒绝发送（仅审计）
python scripts/gateway.py --file ./机密/规划.docx --endpoint relay --strict
```

> 批量处理整个文件夹？交给 Agent 循环即可（见 `SKILL.md` 中"批量处理文件夹"工作流），脚本保持单文件职责。

## ⚙️ 配置

复制 `references/config.example.json` 到 `~/.llm-privacy-gate/config.json` 后修改（已预置 official / relay / local 示例）。
配置优先级：`--config` 指定 > 环境变量 `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > 内置示例。
API Key 一律走环境变量，禁止写入配置文件。

## ⚠️ 边界与局限（务必阅读 `references/rules.md`）

- 脱敏只保护命中规则的内容，未命中的业务上下文仍会出域；
- "模型完全理解 + 服务商无法解密"在密码学上不可兼得；本网关实现的是**真实敏感数据不可获取、窃取亦不可还原**；
- 高危内容（核心商业机密）优先 `--local`（可选）或加密存储，不出域。

---

<p align="center">
  <i>数据如颜料，每一次出域都只留下一笔看不见真实色彩的笔触。</i>
</p>
