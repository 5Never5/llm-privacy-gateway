#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway - masking module (masker.py)

Detects and tokenizes sensitive fields locally so that real values never leave
the machine boundary:
  - Built-in regex rules: ID number, mobile, landline, email, bank card, IP, amount
  - Custom dictionary: company names, people, project codenames
    (~/.llm-privacy-gate/custom_words.json)
  - Session-level random tokens: a fresh session suffix per run prevents
    cross-session correlation analysis
  - The mapping table is kept locally only; restore and leak checks run locally

Usage:
  python masker.py mask --text "..." [--out-mapping map.json]
  python masker.py mask --file input.txt [--out-mapping map.json]
  python masker.py restore --text "..." --mapping map.json
  python masker.py check-leak --output "model output" --mapping map.json
"""
import argparse
import json
import os
import random
import re
import string
import sys

HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
CUSTOM_WORDS_FILE = os.path.join(HOME_DIR, "custom_words.json")

# Currency codes accepted AFTER an amount. The word forms are matched
# case-insensitively. The last two alternatives are the yuan (U+5143) and
# renminbi (U+4EBA U+6C11 U+5E01) markers, written as escapes so that this
# source file stays ASCII-only.
_CUR_CODES = (r"(?i:RMB|CNY|USD|EUR|GBP|JPY|HKD|SGD|AUD|CAD|CHF|YUAN|RENMINBI)"
              r"|\u5143|\u4eba\u6c11\u5e01")
# Currency signs accepted BEFORE an amount (U+0024 U+20AC U+00A3 U+00A5 U+FFE5)
_CUR_SIGNS = "$\u20ac\u00a3\u00a5\uffe5"
# A numeric literal: optional thousands separators (comma, space, nbsp),
# optional 1-2 decimals
_NUM = r"(?:\d{1,3}(?:[,\u00a0 ]\d{3})*|\d+)(?:\.\d{1,2})?"

# Built-in rules: (type, regex). The type name is the token prefix.
BUILTIN_RULES = [
    ("ID_CARD", r"(?<!\d)\d{17}[\dXx](?!\d)"),          # 18-digit ID number
    ("PHONE",   r"(?<!\d)1[3-9]\d{9}(?!\d)"),           # 11-digit mobile number
    ("TEL",     r"(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)"),     # landline number
    ("EMAIL",   r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    ("BANKCARD", r"(?<!\d)\d{16,19}(?!\d)"),            # bank card / account run
    ("IP",      r"(?<!\d)(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
                r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}(?!\d)"),
    # AMOUNT matches a currency code after the figure, or a currency sign
    # before it (e.g. "5,000 USD", "12000 RMB", "$5,000", "250 000 EUR").
    ("AMOUNT",  r"(?:(?<![\d.])" + _NUM + r"(?=\s*(?:" + _CUR_CODES + r"))"
                r"|(?<![\d.])[" + _CUR_SIGNS + r"]\s*" + _NUM + r"(?![\d.]))"),
]


def _load_custom_words():
    """Read the custom dictionary: {"words": ["Acme Corporation", "John Smith"]}"""
    try:
        with open(CUSTOM_WORDS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        words = data.get("words", [])
        return [w for w in words if isinstance(w, str) and w.strip()]
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


class Masker:
    def __init__(self, enabled_types=None, session_id=None, custom_words=None):
        # Session suffix: the same field yields different tokens in different
        # sessions, which prevents cross-session correlation.
        self.session_id = session_id or "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4))
        enabled = set(enabled_types) if enabled_types else set()
        self.patterns = [(t, re.compile(p)) for t, p in BUILTIN_RULES
                         if not enabled or t in enabled]
        self.custom_words = list(
            custom_words if custom_words is not None else _load_custom_words())
        if self.custom_words:
            joined = "|".join(
                re.escape(w) for w in sorted(self.custom_words, key=len, reverse=True))
            self.custom_pattern = re.compile(joined)
        else:
            self.custom_pattern = None
        self.mapping = {}      # token -> original value
        self.counter = 0

    def _token(self, typ):
        self.counter += 1
        return "{%s-%s-%d}" % (typ, self.session_id, self.counter)

    def mask(self, text):
        out = text
        for typ, pat in self.patterns:
            def repl(m, _typ=typ):
                value = m.group(0)
                token = self._token(_typ)
                self.mapping[token] = value
                return token
            out = pat.sub(repl, out)
        if self.custom_pattern:
            def crepl(m):
                token = self._token("DICT")
                self.mapping[token] = m.group(0)
                return token
            out = self.custom_pattern.sub(crepl, out)
        return out

    def restore(self, text):
        out = text
        for token in sorted(self.mapping, key=len, reverse=True):
            out = out.replace(token, self.mapping[token])
        return out

    def check_leak(self, raw_output):
        """Call before restoring: does the raw model output expose real values?"""
        leaks = []
        for token, value in self.mapping.items():
            if value and value in raw_output:
                leaks.append({"token": token, "value": value})
        return leaks

    def check_residue(self, restored):
        """Call after restoring: are any un-restored tokens left in the output?"""
        return [t for t in self.mapping if t in restored]

    def masked_stats(self):
        return {"fields": len(self.mapping), "tokens": self.counter}


def _read_input(text, path):
    if text is not None:
        return text
    if path:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    return sys.stdin.read()


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway masking module")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_mask = sub.add_parser("mask", help="mask (tokenize) sensitive fields")
    p_mask.add_argument("--text", default=None)
    p_mask.add_argument("--file", default=None)
    p_mask.add_argument("--out-mapping", default=None)
    p_mask.add_argument("--session", default=None)

    p_res = sub.add_parser("restore", help="restore tokens back to real values")
    p_res.add_argument("--text", default=None)
    p_res.add_argument("--file", default=None)
    p_res.add_argument("--mapping", required=True)

    p_leak = sub.add_parser("check-leak", help="check an output for leaked values")
    p_leak.add_argument("--output", required=True)
    p_leak.add_argument("--mapping", required=True)

    args = ap.parse_args()

    if args.cmd == "mask":
        text = _read_input(args.text, args.file)
        m = Masker(session_id=args.session)
        masked = m.mask(text)
        print(masked)
        payload = {
            "session_id": m.session_id,
            "mapping": m.mapping,
            "stats": m.masked_stats(),
        }
        if args.out_mapping:
            os.makedirs(os.path.dirname(os.path.abspath(args.out_mapping)) or ".",
                        exist_ok=True)
            with open(args.out_mapping, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2),
                  file=sys.stderr)

    elif args.cmd == "restore":
        text = _read_input(args.text, args.file)
        with open(args.mapping, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = Masker(session_id=data.get("session_id", ""))
        m.mapping = data.get("mapping", {})
        restored = m.restore(text)
        residue = m.check_residue(restored)
        print(restored)
        if residue:
            print("Warning: these tokens were not restored -> %s" % residue,
                  file=sys.stderr)

    elif args.cmd == "check-leak":
        with open(args.mapping, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = Masker(session_id=data.get("session_id", ""))
        m.mapping = data.get("mapping", {})
        leaks = m.check_leak(args.output)
        if leaks:
            print("LEAK: real values found in the model output:")
            for item in leaks:
                print("  %s -> %s" % (item["token"], item["value"]))
            sys.exit(2)
        print("Check passed: no masked real values found in the model output.")


if __name__ == "__main__":
    main()
