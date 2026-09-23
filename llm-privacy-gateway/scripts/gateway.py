#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway - privacy gateway (gateway.py)

Orchestrates the whole pipeline: input (text/file) -> local extraction ->
sensitivity check -> masking (tokenization) -> send (local model / official API
/ relay) -> restore + leak check -> audit log.

Security boundary:
  - Real content (including file and image bodies) never leaves the machine
  - The only thing leaving the boundary is masked text (placeholders plus
    ordinary text that matched no sensitive rule)
  - Every endpoint, relays included, is treated as an untrusted channel that
    receives masked text only
  - The audit log records what left the boundary for every request

Usage:
  python gateway.py --text "Analyse John Smith's contract, total 5,000 USD" --dry-run
  python gateway.py --file contract.pdf --endpoint relay --model gpt-4o-mini
  python gateway.py --text "..." --local                 # use local Ollama
  python gateway.py --text "..." --endpoint official     # use the official API
Environment variables: OPENAI_API_KEY / RELAY_API_KEY / OLLAMA etc.
See references/config.example.json.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from masker import Masker, BUILTIN_RULES, _load_custom_words
import local_extract

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(SKILL_DIR, "references", "config.example.json")
HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
AUDIT_FILE = os.path.join(HOME_DIR, "audit.jsonl")
USER_CONFIG = os.path.join(HOME_DIR, "config.json")

SYSTEM_PROMPT = (
    "Tokens of the form {TYPE-xxxx-N} in the prompt are locally masked "
    "placeholders for sensitive fields. Answer normally from the surrounding "
    "context: do not ask what the placeholders really contain, do not guess or "
    "fabricate their values, and do not copy those tokens anywhere outside the "
    "answer text."
)


def load_config(path=None):
    """Config priority: --config > env var LPG_CONFIG > ~/.llm-privacy-gate/config.json > bundled example"""
    candidates = []
    if path:
        candidates.append(path)
    env = os.environ.get("LPG_CONFIG")
    if env:
        candidates.append(env)
    candidates.append(USER_CONFIG)
    candidates.append(DEFAULT_CONFIG)
    for p in candidates:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise SystemExit("No config file found: %s" % " / ".join(candidates))


def resolve_endpoint(cfg, name, use_local):
    if use_local:
        local = cfg.get("local")
        if not local or not local.get("base_url"):
            raise SystemExit("--local was given but no local endpoint is defined in the config")
        return {"name": "local", "kind": "local", **local}
    eps = cfg.get("endpoints", [])
    if name:
        for e in eps:
            if e.get("name") == name:
                return {"kind": "remote", **e}
        raise SystemExit("No such endpoint in config: %s" % name)
    for e in eps:
        key_env = e.get("api_key_env", "")
        if key_env and os.environ.get(key_env):
            return {"kind": "remote", **e}
    if eps:
        return {"kind": "remote", **eps[0]}
    raise SystemExit("No endpoints configured; edit references/config.example.json")


def chat_completion(endpoint, model, messages, timeout=180):
    base = endpoint["base_url"].rstrip("/")
    url = base + "/chat/completions"
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    key_env = endpoint.get("api_key_env")
    api_key = os.environ.get(key_env) if key_env else None
    if api_key:
        req.add_header("Authorization", "Bearer " + api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit("HTTP %s request failed: %s" % (exc.code, detail))
    except urllib.error.URLError as exc:
        raise SystemExit("Network error: %s" % exc.reason)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise SystemExit("Unexpected response shape: %s" % json.dumps(data, ensure_ascii=False)[:500])


def audit(entry):
    os.makedirs(HOME_DIR, exist_ok=True)
    entry["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(
        description="llm-privacy-gateway: real data never leaves the machine")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", default=None, help="input text")
    src.add_argument("--file", default=None, help="input file (text extracted locally)")
    ap.add_argument("--endpoint", default=None, help="endpoint name: official / relay etc.")
    ap.add_argument("--local", action="store_true",
                    help="optional: force the local Ollama model when installed; not required by default")
    ap.add_argument("--model", default=None, help="override the model name")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the masked payload and mapping stats without sending anything")
    ap.add_argument("--strict", action="store_true",
                    help="strict mode: refuse to send when the input hits the enterprise dictionary (DICT core secrets), audit only")
    ap.add_argument("--config", default=None, help="path to the config file")
    ap.add_argument("--no-mask", action="store_true", help="skip masking (testing only)")
    ap.add_argument("--ocr-lang", default=None,
                    help="OCR language set for image inputs (default: en; use ch for Chinese, en+ch for mixed)")
    ap.add_argument("--prompt", default="Analyse the input and give your conclusion directly.",
                    help="task prompt (optional)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    endpoint = resolve_endpoint(cfg, args.endpoint, args.local)
    model = args.model or endpoint.get("model", "")

    if endpoint.get("kind") == "remote":
        key_env = endpoint.get("api_key_env")
        if key_env and not os.environ.get(key_env):
            print("[warn] Environment variable %s is not set, so the endpoint may "
                  "reject the request." % key_env, file=sys.stderr)

    # 1) Input: files are read locally, the body never leaves the machine
    input_note = ""
    if args.file:
        raw = local_extract.extract_text(args.file, ocr_lang=args.ocr_lang)
        input_note = "file %s: extracted %d characters locally, body not uploaded" % (
            os.path.basename(args.file), len(raw))
    else:
        raw = args.text
    print("[input] %s" % input_note if input_note else "[input] text, %d characters" % len(raw))

    # 2) Masking
    if args.no_mask:
        masked = raw
        masker = None
        print("[mask] skipped (--no-mask, testing only)")
    else:
        masker = Masker()
        masked = masker.mask(raw)
        stats = masker.masked_stats()
        print("[mask] %d sensitive fields matched, %d tokens generated, session %s"
              % (stats["fields"], stats["tokens"], masker.session_id))
        if stats["fields"] == 0 and len(_load_custom_words()) == 0:
            print("[hint] No sensitive field matched. If the content holds company "
                  "secrets, extend the custom dictionary (%s)."
                  % os.path.join(HOME_DIR, "custom_words.json"))

    # 2.5) Strict mode: an enterprise-dictionary hit (core secret) refuses the request
    if args.strict and masker and any(t.startswith("{DICT-") for t in masker.mapping):
        print("[blocked] Strict mode: the content hit the enterprise dictionary "
              "(core secret), refusing to send. Store it with crypto_store.py first.",
              file=sys.stderr)
        audit({"mode": "strict-blocked", "endpoint": endpoint["name"],
               "masked_fields": masker.masked_stats()["fields"]})
        sys.exit(4)

    # 3) Build the payload
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args.prompt + "\n\n" + masked},
    ]
    print("[endpoint] %s (%s) model %s" % (
        endpoint["name"], endpoint.get("kind", ""), model or "(default)"))

    if args.dry_run:
        print("\n===== Masked payload that would be sent (dry-run, nothing sent) =====")
        print(json.dumps({"model": model, "messages": messages},
                         ensure_ascii=False, indent=2))
        if masker:
            print("\n===== Masking map (local only) =====")
            for t, v in masker.mapping.items():
                print("  %s -> %s" % (t, v))
        audit({"mode": "dry-run", "endpoint": endpoint["name"],
               "in_chars": len(raw), "masked_fields": masker.masked_stats()["fields"]
               if masker else 0})
        return

    # 4) Send
    t0 = time.time()
    print("[send] requesting %s ..." % endpoint["name"])
    output = chat_completion(endpoint, model, messages)
    cost_ms = int((time.time() - t0) * 1000)

    # 5) Restore + leak check
    if masker:
        leaks = masker.check_leak(output)
        if leaks:
            print("[critical] the model output leaked %d real value(s); display blocked!"
                  % len(leaks), file=sys.stderr)
            for item in leaks:
                print("  %s -> %s" % (item["token"], item["value"]),
                      file=sys.stderr)
            audit({"mode": "leak-blocked", "endpoint": endpoint["name"],
                   "leaks": len(leaks), "cost_ms": cost_ms})
            sys.exit(3)
        restored = masker.restore(output)
        residue = masker.check_residue(restored)
        if residue:
            print("[warn] un-restored tokens remain in the output: %s" % residue,
                  file=sys.stderr)
        final = restored
        print("[check] no real value leaked; restored %d field(s)" % len(masker.mapping))
    else:
        final = output

    audit({"mode": "ok", "endpoint": endpoint["name"],
           "in_chars": len(raw), "out_chars": len(output),
           "masked_fields": masker.masked_stats()["fields"] if masker else 0,
           "cost_ms": cost_ms})

    print("\n===== Model answer (restored locally) =====")
    print(final)


if __name__ == "__main__":
    main()
