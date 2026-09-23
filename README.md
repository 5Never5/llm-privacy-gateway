<p align="center"><b>🌐</b> <a href="README.md">English</a> · <a href="docs/i18n/README.zh-CN.md">简体中文</a></p>

<p align="center"><img src="docs/banner.jpg" alt="llm-privacy-gateway" width="100%" /></p>

# 🛡️ LLM Privacy Gateway

<p align="center"><b>Real sensitive data never leaves your machine — even with third-party APIs or untrusted relays.</b></p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Agent%20Skills-Open%20Standard-8A2BE2" alt="Agent Skills open standard" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Cross--Agent-Codex%20%7C%20DSH%20%7C%20OpenClaw%20%7C%20WorkBuddy%20%7C%20Claude%20%7C%20Doubao-0e83cd" alt="Cross-agent tools" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Encryption-AES--256--GCM-critical" alt="AES-256-GCM" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Zero%20Local%20Compute-CPU%20Only-success" alt="Zero local compute" /></a>
</p>

A cross-agent skill: sensitive fields are tokenized locally, files/images are parsed locally (bodies never upload), and only masked text reaches official APIs or relays. Responses are restored and leak-checked locally; every request is audited.

## Features

| Module | Script | What it does |
| --- | --- | --- |
| Masking | `scripts/masker.py` | ID/mobile/landline/email/bank card/IP/amount + custom dictionary → session-random tokens |
| Local extraction | `scripts/local_extract.py` | Text from PDF/Word/Excel/images(OCR) locally — bodies never upload |
| Encrypted storage | `scripts/crypto_store.py` | AES-256-GCM for core secrets; key stays local |
| Privacy gateway | `scripts/gateway.py` | Extract → mask → send → restore + leak check → audit |
| Deps | `scripts/setup_deps.py` | One-click dependency check/install |

## Security

- Every endpoint (incl. relays) is **untrusted** — only masked text goes out; leaked real values are blocked (exit 3); `--strict` refuses enterprise-dictionary hits (exit 4); requests are audited to `~/.llm-privacy-gate/audit.jsonl`.
- Zero local compute: masking/extraction/encryption run on your CPU; inference stays with cloud/relay.
- Session-random tokens `{PHONE-xxxx-N}` prevent cross-session correlation; core secrets encrypted by default.

## Install

Standard Agent skill folder (`SKILL.md` + `scripts/` + `references/`); copy into any compatible tool's skills dir. UI is provided by each platform's agent.

| Tool | Location |
| --- | --- |
| Doubao Work | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` or `.codex/skills/` |
| DeepSeek Harness | `.dsh/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude & other Agent Skills tools | their skills dir convention |

First run per environment: `python scripts/setup_deps.py`

## Quick start

```bash
# Dry-run (no send): preview exactly what would leave your machine
python scripts/gateway.py --text "Invoice for Acme Corp: card 4111111111111111, total 5,000 USD" --dry-run

# Send through a relay (API key from an env var: $env:RELAY_API_KEY=... / export RELAY_API_KEY=...)
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "Summarise this quote: Jane Doe, quoted 12,000 USD" --endpoint relay

# File (text extracted locally, body never leaves)
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# Strict mode: enterprise-dictionary hits refused outbound
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

## Config

Copy `references/config.example.json` → `~/.llm-privacy-gate/config.json`. Priority: `--config` > `LPG_CONFIG` > `~/.llm-privacy-gate/config.json` > built-in example. API keys via env vars only.

## Limitations (see `references/rules.md`)

- Masking protects only rule-matched content; unmatched context still leaves.
- "Model fully understands + provider can't decrypt" is cryptographically impossible. This gateway delivers: real data unobtainable, theft unreconstructable.
- High-risk content (core secrets): use `--local` or encrypted storage — keep off the wire.

## Translations

- Simplified Chinese (zh-CN): [README](docs/i18n/README.zh-CN.md) · [Skill](docs/i18n/SKILL.zh-CN.md) · [Rules](docs/i18n/RULES.zh-CN.md)
