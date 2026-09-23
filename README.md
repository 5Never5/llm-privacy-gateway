# llm-privacy-gateway

**隐私网关 Agent Skill：真实敏感数据不出域——即使用第三方官方 API 或不可信中转站，也不泄密。**

一个标准的 **Agent 技能文件夹**（`SKILL.md` + `scripts/` + `references/`），采用 Agent Skills 开放标准，
复制到任意兼容工具的 skills 目录即可使用，**不是独立软件，不需要 GUI，不要求本地算力**。

## 核心能力

| 模块 | 脚本 | 作用 |
| --- | --- | --- |
| 脱敏（令牌化） | `scripts/masker.py` | 身份证 / 手机号 / 座机 / 邮箱 / 银行卡 / IP / 金额 + 自定义企业词典，替换为会话级随机令牌 |
| 本地文字提取 | `scripts/local_extract.py` | PDF / Word(.docx) / Excel(.xlsx) / 图片(OCR) 在本地提取文字，**文件本体永不上传** |
| 加密存储 | `scripts/crypto_store.py` | 核心商业机密 AES-256-GCM 加密，密钥仅存本地 |
| 隐私网关 | `scripts/gateway.py` | 提取 → 脱敏 → 发送(官方/中转站) → 本地还原 + 泄露校验 → 审计 |
| 依赖管理 | `scripts/setup_deps.py` | 新环境一键检查/安装依赖 |

**安全边界**：只有"已脱敏文本"出域；任何端点（含中转站）都被视为不可信通道；
模型输出若泄露真实值即拦截（exit 3）；`--strict` 命中企业词典时拒绝出域（exit 4）；
每次请求写入 `~/.llm-privacy-gate/audit.jsonl`。

## 安装到各智能体工具

把整个 `llm-privacy-gateway` 文件夹复制到对应工具的 skills 目录：

| 工具 | 放置位置 |
| --- | --- |
| 豆包工作 | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` 或项目 `.codex/skills/` |
| DeepSeek Harness | 项目 `.dsh/skills/` |
| Claude 系 / 其他兼容 Agent Skills 标准工具 | 按各自 skills 目录约定 |

每个新环境首次使用前：`python scripts/setup_deps.py` 补齐依赖。

## 快速开始

```bash
# 1) 检查/安装依赖
python scripts/setup_deps.py --check

# 2) 脱敏 + 干跑（不发送）
python scripts/gateway.py --text "张三的手机 13800138000，金额 5000 元" --dry-run

# 3) 走中转站发送（环境变量注入 API Key，勿写入配置文件）
set RELAY_API_KEY=sk-xxx          # PowerShell；Bash 用 export RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "分析这份报价单：李四，报价 12000 元" --endpoint relay

# 4) 处理文件（本地提取，本体不出域）
python scripts/gateway.py --file ./合同/报价单.pdf --endpoint relay

# 5) 严格模式：命中企业词典 → 拒绝发送，仅审计
python scripts/gateway.py --file ./机密/规划.docx --endpoint relay --strict
```

## 配置

复制 `references/config.example.json` 到 `~/.llm-privacy-gate/config.json` 后修改（已预置 official / relay / local 示例）。
配置优先级：`--config` 指定 > 环境变量 `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > 内置示例。
API Key 一律走环境变量，禁止写入配置文件。

## 边界与局限（务必阅读 `references/rules.md`）

- 脱敏只保护命中规则的内容，未命中的业务上下文仍会出域；
- "模型完全理解 + 服务商无法解密"在密码学上不可兼得；本网关实现的是**真实敏感数据不可获取、窃取亦不可还原**；
- 高危内容（核心商业机密）优先 `--local`（可选）或加密存储，不出域。

> 演示与决策过程相关讨论见本项目聊天记录中的多张决策图（GUI 取舍、中转站泄密分析等）。
