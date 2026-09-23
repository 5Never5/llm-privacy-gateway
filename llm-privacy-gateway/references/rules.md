# Masking rules and operating limits

## 1. Built-in regex rules (`masker.py`, `BUILTIN_RULES`)

| Type | Covers | Notes |
| --- | --- | --- |
| ID_CARD | 18-digit ID number | 17 digits plus a check digit |
| PHONE | Mobile number | 11 digits beginning with `1[3-9]` |
| TEL | Landline number | begins with `0`; the area code may use a hyphen |
| EMAIL | Email address | general format |
| BANKCARD | 16–19 digit run | may overlap with ID_CARD; if ID_CARD matches first the value is treated as an ID |
| IP | IPv4 address | all four octets |
| AMOUNT | Monetary amount | matched when followed by a currency code/symbol, or when directly preceded by a currency symbol |

**Locale note** — the `ID_CARD`, `PHONE` and `TEL` defaults cover the formats in most common use in mainland China. `AMOUNT` covers the usual ISO currency codes (`RMB`, `CNY`, `USD`, `EUR`, `GBP`, `JPY`, `HKD`, `SGD`, `AUD`, `CAD`, `CHF`), the yuan and renminbi markers (`U+5143`; `U+4EBA U+6C11 U+5E01`), and the common currency signs — dollar (`U+0024`), euro (`U+20AC`), pound (`U+00A3`), yen (`U+00A5`) and fullwidth yen (`U+FFE5`). To support other locales, extend `BUILTIN_RULES` in `masker.py` or list the literal values in `custom_words.json`.

## 2. Custom dictionary (strongly recommended)

Company secrets — people, company names, project codenames, product codenames, proper nouns — cannot be covered by regex and must be supplied through the dictionary.

File location: `~/.llm-privacy-gate/custom_words.json`

```json
{
  "words": ["Acme Corporation", "John Smith", "Project Falcon", "core-formula-A"]
}
```

Points to note:
- Each dictionary term is replaced whole with a `{DICT-xxxx-N}` token and swapped back on restore;
- Longer terms are matched first;
- Sensitivity: if the input hits a dictionary term, treat it as high sensitivity (route to a local model, or refuse to send it out at all).

## 3. Session-level random tokens

- Each run generates a 4-character random session suffix, producing tokens of the form `{PHONE-a3f9-1}`;
- The same real value maps to the same token within one session, so semantics stay consistent;
- The same real value maps to a different token across sessions, so a relay or provider cannot correlate a user's identity through tokens.

## 4. Security boundary (important — read before use)

1. **Masking only protects rule-matched content.** Unmatched ordinary text (business context, document body) still leaves the boundary — the relay can still see the topic you are discussing.
2. **Model output is visible.** Anything returned passes through the relay/provider and is visible to them; restoration happens locally, but the "analysis conclusion" itself is not a secret.
3. **File and image bodies never leave the boundary.** Run `local_extract.py` first to extract text locally, and send only the extracted text.
4. **Keep high-risk content from leaving at all.** For core business secrets prefer a local model (`--local` / Ollama), or store them with `crypto_store.py` and send them to no model.
5. **On absolutes:** "the model fully understands it and the provider cannot decrypt it" is not achievable simultaneously. What this gateway delivers is "real sensitive data is unobtainable, and theft is unreconstructable".

## 5. Strict mode (core secrets stay off the wire)

- `gateway.py --strict`: as soon as the input hits the custom dictionary (a `DICT` token) the request is **refused**, only an audit entry is written (`mode=strict-blocked`, exit 4), and the user is told to store the file with `crypto_store.py` first;
- Meaning: dictionary terms are the enterprise core-secret list. **By default (without `--strict`) dictionary terms are masked and do leave the boundary**; for core-secret scenarios always add `--strict`;
- No local model is needed to keep core secrets off the wire — they are never sent, so no inference is required.

## 6. Audit

Every request appends one line to `~/.llm-privacy-gate/audit.jsonl`:
`ts / mode / endpoint / in_chars / out_chars / masked_fields / cost_ms / leaks`

- A `leak-blocked` entry means the model output exposed a real value; display was blocked and it should be investigated immediately;
- A `strict-blocked` entry means strict mode stopped content containing a dictionary term — this is expected behaviour.
