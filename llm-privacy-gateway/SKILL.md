---
name: llm-privacy-gateway
description: Privacy-preserving LLM gateway. Before content is sent to any third-party model (official API or untrusted relay) it encrypts core-secret files locally, extracts text from files and images locally, masks (tokenizes) sensitive fields, then restores and leak-checks the response locally, with a full audit trail. Zero local compute — no local model or GPU required; masking, extraction and encryption all run instantly on the local CPU while inference stays with the cloud or the relay. Use when (1) the user wants to use a third-party or relayed model service but is worried about real data leaking; (2) the content involves personal information, company secrets, contract amounts, mobile numbers, ID numbers or other sensitive fields in text or files (PDF/Word/Excel/images); (3) there is a compliance requirement that real sensitive data must not leave the boundary and must be unrecoverable even if intercepted. Trigger words: masking, de-identification, anti-leak, relay, privacy gateway, tokenization, data boundary, PII protection.
---

# LLM Privacy Gateway

Keep real sensitive data local before anything is sent to a third-party model: mask (tokenize) → send masked text → restore locally + verify + audit. **Real content (including file and image bodies) never crosses the machine boundary.**

## Core security boundary

- **Zero local compute**: this skill does not require a local model or GPU. Masking, text extraction, encryption and restoration all run lightly on the local CPU; inference is handled entirely by the cloud or a relay;
- Files/images: text is extracted locally by `local_extract.py` first, and **the body is never uploaded**;
- Text: `masker.py` replaces sensitive fields with session-level random tokens (the mapping table stays local), so only masked text leaves the boundary;
- Every endpoint (official API, relay) is treated as an untrusted channel that receives masked text only;
- Core business secrets: encrypted at rest by `crypto_store.py` by default and **sent to no model at all**; if analysis is genuinely required, mask first and accept the residual risk;
- Audit: every request is appended to `~/.llm-privacy-gate/audit.jsonl`.

## Cross-agent usage (this is a Skill, not standalone software)

This skill is a standard **skill folder** (`SKILL.md` + `scripts/` + `references/`) following the Agent Skills open standard. Copy the whole `llm-privacy-gateway` folder into the skills directory of any tool below and it loads as-is:

| Tool | Location |
| --- | --- |
| Doubao Work | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` or project `.codex/skills/` |
| DeepSeek Harness | project `.dsh/skills/` (natively compatible with the Skills spec) |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude family / other Agent Skills compatible tools | follow that tool's skills directory convention |

Usage is unchanged: **tell the agent what you want in one sentence** (e.g. "run this contract through the privacy gateway"). The agent reads this skill and invokes the scripts in `scripts/`; the UI is provided by each platform — this skill ships no GUI and needs none.
In every new environment, run `python scripts/setup_deps.py` once before first use (see below).

## Quick start

```bash
# 0) First run in a new environment: check / install dependencies (cross-platform)
python scripts/setup_deps.py --check         # check only
python scripts/setup_deps.py                 # install whatever is missing
python scripts/setup_deps.py --install-ocr   # when image OCR is needed

# 1) Mask + dry run (nothing is sent): inspect exactly what would leave
python scripts/gateway.py --text "Invoice for Acme Corp: card 4111111111111111, total 5,000 USD" --dry-run

# 2) Configure endpoints (copy references/config.example.json to ~/.llm-privacy-gate/config.json and edit)
#    A relay example is pre-wired (name=relay) — fill in base_url. API keys go in env vars, never in this file

# 3) Real request through a relay (env var: $env:RELAY_API_KEY=... in PowerShell, export RELAY_API_KEY=... in Bash)
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "Summarise this quote: Jane Doe, quoted 12,000 USD" --endpoint relay

# 4) Process a file (text extracted locally, body never leaves; adjust the path for your machine)
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# 5) (Optional) force local inference for core secrets when Ollama is installed
python scripts/gateway.py --file ./confidential/roadmap.docx --local

# 6) Encrypted storage for core secrets
python scripts/crypto_store.py encrypt --in roadmap.docx --out roadmap.docx.enc
python scripts/crypto_store.py decrypt --in roadmap.docx.enc --out roadmap.docx

# 7) Strict mode: a hit on the enterprise dictionary refuses the request outbound (audit only)
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

> Config auto-load order: `--config` > env var `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > built-in example.
> Copy `references/config.example.json` to `~/.llm-privacy-gate/config.json` and edit it once — no `--config` needed afterwards.

## Batch-processing a folder (the agent loops; the scripts keep a single-file responsibility)

When the user asks to "process this whole folder / directory", **do not add a batch flag to the scripts** — have the agent loop instead:

1. Enumerate the supported files in the directory (txt/md/csv/json/pdf/docx/xlsx/common images; skip `.enc` ciphertext);
2. Call `python scripts/gateway.py --file <path> [--endpoint <name>] [--strict]` once per file;
3. Report each file's result independently and list failures with their reason (extraction failure / leak blocked, exit 3 / strict blocked, exit 4);
4. Finish with a summary: succeeded / failed / outbound requests / audit entries (`~/.llm-privacy-gate/audit.jsonl`, one entry per file);
5. Files blocked by leak-check or strict mode must be surfaced prominently and never skipped silently.

## Modules

### 1. Masking — `scripts/masker.py`
- Built-in rules: ID number / mobile / landline / email / bank card / IP / amount;
- Custom dictionary: `~/.llm-privacy-gate/custom_words.json` (company names, people, project codenames must be listed here);
- Session-level random tokens `{PHONE-xxxx-N}` to prevent cross-session correlation;
- CLI: the `mask` / `restore` / `check-leak` subcommands, for standalone debugging.

### 2. Local extraction — `scripts/local_extract.py`
- Supported: txt/md/csv/json, PDF, Word (.docx), Excel (.xlsx), common images (OCR);
- `--ocr-lang` selects the OCR language set (default `en`; use `ch` for Chinese, or e.g. `en+ch` for mixed pages);
- When no OCR engine is installed it prints clear install guidance;
- Text only — the file body never leaves.

### 3. Encrypted storage — `scripts/crypto_store.py`
- AES-256-GCM; the key is generated at `~/.llm-privacy-gate/key.bin` (created on first use — please back it up);
- Ciphertext files are safe to store or transfer; without the key they cannot be decrypted.

### 4. Gateway — `scripts/gateway.py`
- Pipeline: input → local extraction → masking → send → restore + leak check → audit;
- Leak check: if the model output contains a real value that was masked, display is **blocked** and the event is audited;
- `--strict`: refuses to send when the input hits the enterprise dictionary (core secrets); audit only (exit 4);
- `--dry-run`: preview the masked payload that would be sent, without sending it.

### 5. Dependency management — `scripts/setup_deps.py`
- Run once in a new environment (Codex / DeepSeek Harness etc.); checks and installs cryptography, pypdf, python-docx, openpyxl and Pillow;
- `--check` checks only; `--install-ocr` additionally installs OCR; a missing OCR engine does not affect text/PDF/Word/Excel handling.

## Configuration

See `references/config.example.json` and `references/rules.md` (rule list, security boundary, audit format).
Priority: `--config` > env var `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > built-in example.
API keys are always injected through env vars (e.g. `OPENAI_API_KEY`, `RELAY_API_KEY`) and must never be written into the config file.

## Operating limits (read `references/rules.md` first)

- Masking protects only rule-matched content; unmatched business context still leaves the boundary;
- Anything the model returns is visible to the endpoint;
- "Model fully understands + provider cannot decrypt" is not achievable in the absolute; this gateway delivers "real sensitive data unobtainable, theft unreconstructable";
- For high-risk content (core business secrets), prefer `--local` or encrypted storage so it never leaves at all.

## Licence

PolyForm Noncommercial License 1.0.0 — free for personal, educational, research, charitable and government use. **Commercial use requires a licence**: see `docs/COMMERCIAL.md` in the repository.

This folder is normally installed on its own, so the terms have to travel with it. The licence URL and the notice line below are both part of the deal and must survive any copy you pass on:

```
Required Notice: Copyright 5Never5 (https://github.com/5Never5)
https://polyformproject.org/licenses/noncommercial/1.0.0
```
