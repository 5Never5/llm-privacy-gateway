> **Note / 说明**：本文件是 `references/rules.md` 的简体中文翻译版本，仅供阅读参考。
> **生效的规则说明是 `llm-privacy-gateway/references/rules.md`（英文版）**。

# 脱敏规则与使用边界

## 一、内置正则规则（masker.py BUILTIN_RULES）

| 类型 | 覆盖内容 | 备注 |
| --- | --- | --- |
| ID_CARD | 18 位身份证号 | 17 位数字 + 校验位 |
| PHONE | 手机号 | 1[3-9] 开头 11 位 |
| TEL | 座机 | 0 开头，区号可带连字符 |
| EMAIL | 邮箱地址 | 通用格式 |
| BANKCARD | 16–19 位数字串 | 与身份证存在重叠可能，先被 ID_CARD 命中即按身份证处理 |
| IP | IPv4 地址 | 完整四段 |
| AMOUNT | 金额 | 仅当后跟币种代码/符号，或紧跟前置币种符号时命中 |

**地域说明**：`ID_CARD`、`PHONE`、`TEL` 三条默认规则覆盖中国大陆常用格式；`AMOUNT` 覆盖常见币种代码与符号（`RMB`、`CNY`、`USD`、`EUR`、`GBP`、`JPY`、`HKD`、`SGD`、`AUD`、`CAD`、`CHF`、`元`、`人民币`、`￥`、`¥`、`$`、`€`、`£`）。需要支持其他地域时，请扩展 `masker.py` 中的 `BUILTIN_RULES`，或把字面值写进 `custom_words.json`。

## 二、自定义词典（推荐必须配置）

企业机密（人名、公司名、项目代号、产品代号、专有名词）正则无法覆盖，必须通过词典补足。

文件位置：`~/.llm-privacy-gate/custom_words.json`

```json
{
  "words": ["Acme 公司", "Jane Doe", "项目代号 Falcon", "核心配方 A"]
}
```

要点：
- 词典词会整词替换为 `{DICT-xxxx-N}` 令牌，还原时换回原文；
- 词条越长优先匹配；
- 敏感度判定：若输入命中词典词，建议按"高敏"处理（走本地模型或直接拒绝出域）。

## 三、会话级随机令牌

- 每次运行生成 4 位随机会话后缀，令牌形如 `{PHONE-a3f9-1}`；
- 同一真实值在同一会话内映射到同一令牌（保证语义一致）；
- 跨会话同一真实值令牌不同，防止中转站/服务商通过令牌关联用户身份。

## 四、安全边界（重要，使用前必读）

1. **脱敏只保护"命中规则的内容"**。未命中的普通文本（业务上下文、文档正文）仍会出域——中转站仍能看到你讨论的话题。
2. **模型输出可见**。返回结果经中转站/服务商，其内容对它们可见；还原发生在本地，但"分析结论"本身不是秘密。
3. **文件/图片本体永远不出域**。必须先经 local_extract.py 在本地提取文字，只发送提取文本。
4. **高危内容建议不出域**。核心商业机密建议走本地模型（--local / Ollama），或仅用 crypto_store.py 加密存储，不送任何模型。
5. **绝对语义**："模型完全理解 + 服务商完全无法解密"不可兼得。本网关实现的是"真实敏感数据不可获取、窃取亦不可还原"。

## 五、严格模式（核心机密默认不出域）

- `gateway.py --strict`：只要输入命中自定义词典（DICT 令牌），**拒绝发送**，仅写审计（mode=strict-blocked，exit 4），并提示先用 `crypto_store.py` 加密存储；
- 含义：词典词 = 企业核心机密名单。**默认（不加 --strict）词典词会脱敏后出域**；核心机密场景请始终加 `--strict`；
- 没有本地模型也能做到"核心机密不出域"——因为它根本不发送，不需要任何推理。

## 六、审计

每次请求追加一行到 `~/.llm-privacy-gate/audit.jsonl`：
`ts / mode / endpoint / in_chars / out_chars / masked_fields / cost_ms / leaks`

- 出现 `leak-blocked` 条目 = 模型输出泄露真实值，已阻止展示，应立即排查；
- 出现 `strict-blocked` 条目 = 严格模式拦截了含词典词的内容，属预期行为。

---

<p align="center"><b>🌐</b> <a href="../../README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="SKILL.zh-CN.md">中文技能说明</a> · <a href="../../llm-privacy-gateway/references/rules.md">英文规则说明</a></p>
