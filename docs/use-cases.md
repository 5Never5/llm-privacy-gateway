# Use cases

The short version: this pays for itself the first time you want a hosted model's judgement on something you are not allowed to paste into a chat box.

## The shape of a good fit

Three conditions, and all three have to hold:

1. **The input is a file or a block of text.** A contract, a quote sheet, a scan, a support thread, a chain of emails.
2. **The sensitive parts are separable.** Either they match a built-in rule — ID number, mobile, landline, email, bank card, IP, amount — or you can list them in the custom dictionary.
3. **What you want back is judgement or wording, not the exact values.** A summary, a risk list, a translation, a rewrite, a first draft.

When all three hold, the pipeline is: **extract locally → mask → send masked text → restore → leak check → audit**.

## Scenarios

### 1. A second read on a contract

You have `./contracts/quote.pdf` and you want to know which clauses are one-sided. You cannot paste it into a chat box, and you are not going to redact it by hand.

```bash
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay
```

The PDF is parsed on your machine — the file body never uploads. Amounts, bank details, emails, phone numbers and IPs are replaced with session tokens before any text leaves.

Start with the dry run, once for every new document type:

```bash
python scripts/gateway.py --file ./contracts/quote.pdf --dry-run
```

Here is what that actually prints, on a one-line example:

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

Read that output before you trust it. **`Acme Corp` and `Jane Doe` went out in the clear.** No regex can tell a client name from an ordinary noun phrase, so names are not covered by any built-in rule. That is what the dictionary in the next section is for.

### 2. Teaching it your own vocabulary

`~/.llm-privacy-gate/custom_words.json`:

```json
{ "words": ["Acme Corp", "Jane Doe", "Project Falcon"] }
```

Run the same input again and the picture changes:

```
[mask] 6 sensitive fields matched, 6 tokens generated, session 80a0
...
"Invoice for {DICT-80a0-4}: contact {DICT-80a0-5} at {EMAIL-80a0-2} or {PHONE-80a0-1}, total {AMOUNT-80a0-3} USD. {DICT-80a0-6} is on hold."
```

Dictionary hits become `{DICT-...}` tokens. Longer entries are matched first, so adding both `Acme Corp` and `Acme Corp Holding` behaves the way you would expect.

When nothing matches, the gateway says so rather than pretending the content is clean:

```
[mask] 0 sensitive fields matched, 0 tokens generated, session w8ll
[hint] No sensitive field matched. If the content holds company secrets, extend
       the custom dictionary (~/.llm-privacy-gate/custom_words.json).
```

Treat a zero-match run on confidential material as a **failed** run, not a safe one.

### 3. Scanned documents and screenshots

Most OCR happens on the provider's side: you upload the image, the text is read there. Here the image is read on your CPU and **the image itself never leaves**. Only the recognised text, after masking, goes out.

```bash
python scripts/gateway.py --file ./scans/order-form.jpg --endpoint relay
python scripts/gateway.py --file ./scans/signed-agreement.jpg --ocr-lang ch --endpoint relay
```

`--ocr-lang` defaults to `en`; use `ch` for Chinese and `en+ch` for mixed documents.

### 4. Turning a spreadsheet into a first draft

An Excel quote sheet with client names, unit prices and totals, and you want a proposal outline in the same structure. The names and amounts are masked; the structure and the request itself go out intact, which is the part a model is actually good at.

Remember the trade-off: the amounts are opaque tokens now, so the model cannot add them up or take ratios. Do the arithmetic locally and give it the result as plain prose.

### 5. Summarising a long thread

A meeting log, a support thread, a chain of emails where names, numbers and addresses are incidental. Mask them, then ask for the decision list, the open questions and the disagreements. Same command as any other text input, no hand redaction.

### 6. Working through a relay you do not trust

A relay is a plaintext proxy: whoever runs it sees everything you send it. That is exactly the threat model here. The relay is treated as untrusted, and all it ever receives is masked text. If it is compromised or quietly logging, what leaks is a set of session tokens — not reversible without the local mapping table, and not correlatable across runs because the session suffix is regenerated every time.

### 7. Keeping a record

Every request appends one line to `~/.llm-privacy-gate/audit.jsonl`:

```
ts / mode / endpoint / in_chars / out_chars / masked_fields / cost_ms / leaks
```

When someone asks what exactly you sent to that API, and when, you have an answer that is not a memory. A `leak-blocked` line means the model echoed a real value back and the display was blocked. A `strict-blocked` line means strict mode stopped the request on purpose.

## Where it does not fit

A privacy tool that oversells itself is worse than no tool, so:

| You want | Why this is the wrong tool |
| :--- | :--- |
| The model to compute on the real numbers | Masked amounts are opaque tokens. No summing, no ratios, no unit conversion. |
| The model to look at the photo, scan or diagram itself | If the layout, a signature or a diagram carries the meaning, masked text loses it. |
| The model to resolve a real entity or a real person | Entity resolution needs the identifiers, and they are gone. |
| Protection for content that no rule matches | Anything not matched by a rule and not in your dictionary leaves as it is. This is the most common way to get it wrong: a `[mask]` line reading `0 sensitive fields matched` looks like safety. |
| A guarantee about the provider's copy | The provider receives masked text, but read their retention and training policy anyway. Masked text is still your text. |

## Choosing a mode

| Mode | Flag | Behaviour |
| :--- | :--- | :--- |
| Dry run | `--dry-run` | Prints the masked payload and the local mapping, sends nothing. Run it every time the document type changes. |
| Official API | `--endpoint official` | Straight to the provider, masked text only. |
| Relay | `--endpoint relay` | The same, through a middleman you do not control, masked text only. |
| Strict | `--strict` | A custom-dictionary hit refuses the whole request (exit 4), audit only. It needs a populated dictionary to do anything at all. |
| Local only | `--local` | Forces the Ollama model when one is installed. Nothing goes out, so nothing needs masking. |

### Exit codes

| Code | Meaning |
| :--- | :--- |
| `0` | Completed |
| `1` | Network or endpoint error |
| `3` | A real value appeared in the model's output — display blocked, investigate |
| `4` | Strict mode refused the request |

`3` and `4` are the guard working, not a crash. If you script around the gateway, treat `3` as an incident and `4` as expected.

## The two-minute version

```bash
# 1. Check and install the dependencies, once per environment
python scripts/setup_deps.py

# 2. Put your own names and project codenames in ~/.llm-privacy-gate/custom_words.json,
#    then look before you leap
python scripts/gateway.py --file ./contracts/quote.pdf --dry-run

# 3. Send, once the dry run shows you what you expected
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# 4. Something in there is a core secret and should not go out at all: make sure the
#    term is in the dictionary and let strict mode refuse the request
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

---

<p align="center"><sub><a href="../README.md">Back to README</a> &nbsp;·&nbsp; <a href="i18n/use-cases.zh-CN.md">Chinese</a></sub></p>
