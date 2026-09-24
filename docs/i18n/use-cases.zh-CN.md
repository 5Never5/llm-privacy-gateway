# 使用场景

一句话：当你第一次需要让云端模型帮你判断一份**不能粘进聊天框**的材料时，这个网关就回本了。

## 什么情况下合适

三个条件，缺一不可：

1. **输入是一份文件或一大段文本。** 合同、报价单、扫描件、客服工单、一长串邮件。
2. **敏感部分是"分得出来"的。** 要么命中内置规则（身份证、手机号、座机、邮箱、银行卡、IP、金额），要么你能把它们列进自定义词典。
3. **你要的是判断和表达，不是那些具体的值。** 摘要、风险清单、翻译、改写、初稿。

三个都成立时，流程是：**本地抽取 → 脱敏 → 只发脱敏文本 → 本地还原 → 泄露校验 → 审计留痕**。

## 具体场景

### 1. 找人替你把合同再看一遍

手上有 `./contracts/quote.pdf`，想知道哪些条款是单方面有利的。整份粘进聊天框不合适，手工涂黑又太费时间。

```bash
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay
```

PDF 在你本机解析，**文件正文不上传**。金额、银行信息、邮箱、电话、IP 在出境前已被替换成本次会话的令牌。

每种新的文档类型，先跑一次干跑：

```bash
python scripts/gateway.py --file ./contracts/quote.pdf --dry-run
```

下面是一段单行样例的**真实**输出：

```
[mask] 5 sensitive fields matched, 5 tokens generated, session p0nk
[endpoint] official (official-direct) model gpt-4o-mini

===== Masked payload that would be sent (dry-run, nothing sent) =====
"content": "Analyse the input and give your conclusion directly.\n\nInvoice for Acme Corp: card {BANKCARD-p0nk-3}, contact Jane Doe at {EMAIL-p0nk-2} or {PHONE-p0nk-1}, server {IP-p0nk-4}, total {AMOUNT-p0nk-5} USD"

===== Masking map (local only) =====
  {PHONE-p0nk-1}     -> 13800138000
  {EMAIL-p0nk-2}     -> jane.doe@acme.com
  {BANKCARD-p0nk-3}  -> 4111111111111111
  {IP-p0nk-4}        -> 10.0.0.7
  {AMOUNT-p0nk-5}    -> 5,000
```

**这段输出一定要自己看一遍再往下走。** 注意 `Acme Corp` 和 `Jane Doe` 是**原样出去的**——正则区分不了"客户名"和"普通名词短语"，所以人名、公司名不在任何内置规则里。这就是下一节自定义词典要解决的事。

### 2. 教会它你的专属词表

`~/.llm-privacy-gate/custom_words.json`：

```json
{ "words": ["Acme Corp", "Jane Doe", "Project Falcon"] }
```

同样的输入再跑一次，结果就变了：

```
[mask] 6 sensitive fields matched, 6 tokens generated, session 80a0
...
"Invoice for {DICT-80a0-4}: contact {DICT-80a0-5} at {EMAIL-80a0-2} or {PHONE-80a0-1}, total {AMOUNT-80a0-3} USD. {DICT-80a0-6} is on hold."
```

词典命中会变成 `{DICT-...}` 令牌。词表按**长词优先**匹配，所以同时写 `Acme Corp` 和 `Acme Corp Holding` 时行为符合直觉，短词不会把长词咬掉一半。

如果一个都没命中，网关会明说，而不是假装内容已经干净：

```
[mask] 0 sensitive fields matched, 0 tokens generated, session w8ll
[hint] No sensitive field matched. If the content holds company secrets, extend
       the custom dictionary (~/.llm-privacy-gate/custom_words.json).
```

**在涉密材料上出现"零命中"，要当成一次失败的运行，而不是一次安全的运行。**

### 3. 扫描件与截图

多数工具的 OCR 在服务商那一侧完成：你把图片传上去，文字在那里被读出来。这里图片在你自己 CPU 上识别，**图片本体不出境**，出去的只是识别出的文字，而且已经脱敏。

```bash
python scripts/gateway.py --file ./scans/order-form.jpg --endpoint relay
python scripts/gateway.py --file ./scans/signed-agreement.jpg --ocr-lang ch --endpoint relay
```

`--ocr-lang` 默认是 `en`；中文文档用 `ch`，中英混排用 `en+ch`。

### 4. 把表格变成初稿

一份带客户名、单价、总价的 Excel 报价单，你想让模型按同样结构给出一版方案提纲。名字和金额被脱敏，**结构和需求本身完整出去**——而这恰恰是模型擅长的那部分。

代价要说清楚：金额已经变成不透明令牌，模型没法求和、没法算比例。**算术在本地做完**，把结果用文字告诉它。

### 5. 长对话、长工单的摘要

会议记录、客服工单、一串邮件，里面的人名、号码、地址都只是顺带出现的。脱敏之后让它给决策清单、待办问题和分歧点。命令与处理普通文本完全相同，不需要手工涂黑。

### 6. 走你不信任的中转站

中转站是明文代理：谁运营它，谁就能看见你发过去的一切。这正是本项目的威胁模型。中转站被当作不可信通道，它收到的永远只是脱敏文本。就算它被入侵或偷偷记日志，泄露的也只是一组会话令牌——没有本地映射表无法还原，而且每次运行的会话后缀都会重新生成，跨次关联不起来。

### 7. 留下可查的记录

每个请求都会往 `~/.llm-privacy-gate/audit.jsonl` 追加一行：

```
ts / mode / endpoint / in_chars / out_chars / masked_fields / cost_ms / leaks
```

当有人问"你究竟往那个接口发了什么、什么时候发的"，你拿得出一份记录，而不是靠回忆。`leak-blocked` 表示模型回包里带出了真实值、显示被拦截；`strict-blocked` 表示严格模式按预期拦下了请求。

## 什么情况下不合适

一个自我吹嘘的隐私工具比没有工具更糟，所以这里说清楚：

| 你想要的 | 为什么这个工具帮不上 |
| :--- | :--- |
| 让模型对**真实数字**做计算 | 金额已是不透明令牌。不能求和、不能算比例、不能换算单位。 |
| 让模型**看图本身**、看版式、看印章 | 如果含义承载在版式、签名或图示里，脱敏后的文字会丢掉它。 |
| 让模型**识别真实的法人或自然人** | 实体识别必须要那些标识符，而它们已经不存在了。 |
| 保护**任何规则都匹配不到**的内容 | 既没命中规则、又不在词典里的内容会原样出去。这是最容易踩的坑：一行 `[mask] 0 sensitive fields matched` 看上去很像"安全"。 |
| 对**服务商那一份副本**的保证 | 服务商收到的是脱敏文本，但仍要读它的留存与训练政策。脱敏文本依然是你的文本。 |

## 模式怎么选

| 模式 | 参数 | 行为 |
| :--- | :--- | :--- |
| 干跑 | `--dry-run` | 打印将要发送的脱敏载荷与本地方案映射表，什么都不发。文档类型一变就重跑一次。 |
| 官方接口 | `--endpoint official` | 直连服务商，只发脱敏文本。 |
| 中转站 | `--endpoint relay` | 同上，但经过你不掌控的中间人，只发脱敏文本。 |
| 严格模式 | `--strict` | 命中自定义词典即**整个请求拒绝**（退出码 4），只写审计。**词典为空时它什么也拦不住。** |
| 仅本地 | `--local` | 装有 Ollama 时强制走本地模型。什么都不出去，因此也就不需要脱敏。 |

### 退出码

| 退出码 | 含义 |
| :--- | :--- |
| `0` | 正常完成 |
| `1` | 网络或接口错误 |
| `3` | 模型输出里出现了真实值——显示已拦截，需要排查 |
| `4` | 严格模式拒绝了请求 |

`3` 和 `4` 是护栏在工作，不是崩溃。如果你要写脚本包一层，把 `3` 当事故处理，`4` 当预期行为处理。

## 两分钟上手

```bash
# 1) 每个环境装一次依赖
python scripts/setup_deps.py

# 2) 把人名、项目代号写进 ~/.llm-privacy-gate/custom_words.json，然后先看再发
python scripts/gateway.py --file ./contracts/quote.pdf --dry-run

# 3) 干跑结果符合预期了，再真正发送
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# 4) 如果里面有核心机密、压根不该出去：确认该词在词典里，让严格模式直接拒绝
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

---

<p align="center"><sub><a href="README.zh-CN.md">返回 README</a> &nbsp;·&nbsp; <a href="../use-cases.md">English</a></sub></p>
