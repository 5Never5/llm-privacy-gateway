<p align="center"><a id="top"></a><b>🌐</b> English · <a href="docs/i18n/README.zh-CN.md">Chinese</a></p>

<p align="center"><img src="docs/banner.jpg" alt="LLM Privacy Gateway" width="100%" /></p>

<h1 align="center">🛡️ LLM Privacy Gateway</h1>

<p align="center"><b>Real sensitive data never leaves your machine — even with third-party APIs or untrusted relays.</b></p>

<p align="center">
  <a href="#-how-it-works"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+" /></a>
  <a href="#-install"><img src="https://img.shields.io/badge/Agent%20Skills-Open%20Standard-8A2BE2" alt="Agent Skills open standard" /></a>
  <a href="#-install"><img src="https://img.shields.io/badge/Cross--Agent-Codex%20%7C%20DSH%20%7C%20OpenClaw%20%7C%20WorkBuddy%20%7C%20Claude%20%7C%20Doubao-0e83cd" alt="Cross-agent tools" /></a>
  <a href="#-security-model"><img src="https://img.shields.io/badge/Encryption-AES--256--GCM-critical" alt="AES-256-GCM" /></a>
  <a href="#-how-it-works"><img src="https://img.shields.io/badge/Zero%20Local%20Compute-CPU%20Only-success" alt="Zero local compute" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-F5A623" alt="PolyForm Noncommercial License 1.0.0" /></a>
  <a href="docs/COMMERCIAL.md"><img src="https://img.shields.io/badge/Commercial%20use-licence%20required-4B5563" alt="A commercial licence is required for commercial use" /></a>
</p>

<p align="center">
  <a href="#-how-it-works">How it works</a> &nbsp;·&nbsp;
  <a href="#-features">Features</a> &nbsp;·&nbsp;
  <a href="docs/use-cases.md">Use cases</a> &nbsp;·&nbsp;
  <a href="#-install">Install</a> &nbsp;·&nbsp;
  <a href="#-quick-start">Quick start</a> &nbsp;·&nbsp;
  <a href="#-security-model">Security</a> &nbsp;·&nbsp;
  <a href="#-support">Support</a> &nbsp;·&nbsp;
  <a href="#-license">License</a>
</p>

---

## 🔍 How it works

A cross-agent skill: sensitive fields are tokenized locally, files and images are parsed locally (bodies never upload), and only masked text reaches official APIs or relays. Responses are restored and leak-checked locally, and every request is audited.

No framework, no backend, no daemon — plain Python scripts running on your own CPU.

<p align="center"><img src="docs/assets/flow.svg" alt="Data flow: files are parsed and sensitive values replaced on your machine, only masked text reaches the provider, and responses are restored and audited locally." width="100%" /></p>

## ✨ Features

| Module | Script | What it does |
| :--- | :--- | :--- |
| 🔍 **Masking** | `scripts/masker.py` | ID / mobile / landline / email / bank card / IP / amount + custom dictionary → session-random tokens |
| 📄 **Local extraction** | `scripts/local_extract.py` | Text from PDF / Word / Excel / images (OCR) locally — bodies never upload |
| 🔐 **Encrypted storage** | `scripts/crypto_store.py` | AES-256-GCM for core secrets; the key stays local |
| 🚦 **Privacy gateway** | `scripts/gateway.py` | Extract → mask → send → restore + leak check → audit |
| 📦 **Dependencies** | `scripts/setup_deps.py` | One-click dependency check and install |

## 🚀 Quick start

```bash
# Dry-run (no send): preview exactly what would leave your machine
python scripts/gateway.py --text "Invoice for Acme Corp: card 4111111111111111, total 5,000 USD" --dry-run

# Send through a relay (API key from an env var: $env:RELAY_API_KEY=... / export RELAY_API_KEY=...)
set RELAY_API_KEY=sk-xxx
python scripts/gateway.py --text "Summarise this quote: Jane Doe, quoted 12,000 USD" --endpoint relay

# File (text extracted locally, the body never leaves)
python scripts/gateway.py --file ./contracts/quote.pdf --endpoint relay

# Strict mode: enterprise-dictionary hits are refused outbound
python scripts/gateway.py --file ./confidential/roadmap.docx --endpoint relay --strict
```

## 🔐 Security model

- Every endpoint — relays included — is treated as **untrusted**. Only masked text goes out; leaked real values are blocked (exit 3); `--strict` refuses enterprise-dictionary hits (exit 4); every request is appended to `~/.llm-privacy-gate/audit.jsonl`.
- **Zero local compute**: masking, extraction and encryption run on your CPU, so no GPU is needed. Inference stays with the cloud provider or relay you already use.
- **Session-random tokens** such as `{PHONE-xxxx-N}` prevent cross-session correlation; core secrets are encrypted by default.

## 📦 Install

This is a standard Agent skill folder (`SKILL.md` + `scripts/` + `references/`). Copy it into the skills directory of any compatible tool — the UI is provided by that platform's agent.

| Tool | Location |
| :--- | :--- |
| Doubao Work | `workspace/.user_skills/` |
| OpenAI Codex | `~/.codex/skills/` or `.codex/skills/` |
| DeepSeek Harness | `.dsh/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| WorkBuddy | `.codebuddy/skills/` |
| Claude and other Agent Skills tools | their own skills directory convention |

Then run once per environment:

```bash
python scripts/setup_deps.py
```

> **Using this at work?** Personal, educational, research, charitable and government use is free and needs no licence. A company using it for its own business — even only to redact its own contracts — needs a commercial licence. See [Commercial use](docs/COMMERCIAL.md); it is a flat fee and the software itself never changes.

## ⚙️ Config

Copy `references/config.example.json` to `~/.llm-privacy-gate/config.json`. Resolution order: `--config` → `LPG_CONFIG` → `~/.llm-privacy-gate/config.json` → the built-in example. API keys are read from environment variables only.

## ⚠️ Limitations

Read `references/rules.md` for the full rule set and their exact patterns.

- Masking protects only content that matches a rule — everything else still leaves.
- "The model fully understands it, yet the provider cannot decrypt it" is cryptographically impossible. What this gateway actually delivers: the real data cannot be obtained, and anything stolen cannot be reconstructed.
- For high-risk content (core secrets), use `--local` or the encrypted store — keep it off the wire entirely.

[Use cases](docs/use-cases.md) walks through what those limits mean on real documents, what a dry run actually prints, and the cases where this gateway is simply the wrong tool. Worth ten minutes before you rely on it.

## ☕ Support

Spare-time project, no company behind it, no ads, no telemetry, and nothing gated behind a price. Personal and non-commercial use is free under the licence and stays that way; the only thing that is paid is permission to use it commercially, which is deliberate.

So this is not a paywall, it is a tip jar. But count up what it has already given you: the afternoon you did not spend redacting a contract by hand, the client file you could hand to an API without hesitating first. If it saved you even one of those, sending a little back is the most direct way to keep the next one saved too. A tip turns into hours spent on this project, and those hours have no other source.

**If you are using this at work, skip the tip and buy a licence** — same page, and it is what actually funds the next version.

- ⭐ **Star the repository** — free, and it is what actually gets the project in front of people
- 🐛 **Report a bug** — honestly worth more than a tip
- 📣 **Send it to one person who needs it** — costs nothing, reaches exactly the right person
- ☕ **Send a tip** — the most direct way to buy the project more time
- 🧾 **Buy a commercial licence** — if a company is the one benefiting from it

<p align="center">
  <a href="docs/SUPPORT.md"><b>☕ Support options · payment codes inside</b></a>
  <br />
  <sub>The <b>Sponsor</b> button in the sidebar opens the same page.</sub>
</p>

## 📄 License

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for personal, educational, research, charitable and government use. **Commercial use requires a licence**, which [Commercial use](docs/COMMERCIAL.md) explains and how to request one.

The practical line: if you are running this inside a company to do that company's work, or shipping it in something you sell, that is commercial use. Everything else is free and stays free.

Nothing is gated by this — no feature, no rule, no content. The licence decides *who may use the software commercially*, not what the software does. A commercial licence buys permission, not capability.

Versions published before this change were released under the MIT License, and **that grant cannot be withdrawn**: anyone who obtained a copy while MIT applied keeps those rights for that copy, permanently. Only versions from this change onward are covered by PolyForm Noncommercial.

## 🌐 Translations

| Language | README | Skill | Rules | Use cases | Support | Commercial |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| English | this file | `SKILL.md` | `references/rules.md` | `docs/use-cases.md` | `docs/SUPPORT.md` | `docs/COMMERCIAL.md` |
| Simplified Chinese | [README](docs/i18n/README.zh-CN.md) | [Skill](docs/i18n/SKILL.zh-CN.md) | [Rules](docs/i18n/RULES.zh-CN.md) | [Use cases](docs/i18n/use-cases.zh-CN.md) | [Support](docs/i18n/SUPPORT.zh-CN.md) | [Commercial](docs/i18n/COMMERCIAL.zh-CN.md) |

---

<p align="center"><sub><a href="#top">Back to top</a></sub></p>
