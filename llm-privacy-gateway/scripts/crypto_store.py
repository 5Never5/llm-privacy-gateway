#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway - encrypted storage module (crypto_store.py)

Locally encrypts core business secrets and similar files with AES-256-GCM:
  - The key is generated on first use and kept at ~/.llm-privacy-gate/key.bin
  - An external key can be supplied with --key-hex (64 hex characters)
  - File format: MAGIC("LPG1") + nonce(12B) + tag(16B) + ciphertext
  - Ciphertext can be handed to anyone or any cloud drive; without the key it
    cannot be decrypted

Usage:
  python crypto_store.py encrypt --in secret.docx --out secret.docx.enc
  python crypto_store.py decrypt --in secret.docx.enc --out secret.docx
  python crypto_store.py encrypt --in secret.pdf --out secret.pdf.enc --key-hex <64 hex chars>
"""
import argparse
import os
import sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("Missing dependency: run  python -m pip install cryptography",
          file=sys.stderr)
    sys.exit(1)

MAGIC = b"LPG1"
HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
KEY_FILE = os.path.join(HOME_DIR, "key.bin")


def _load_or_create_key(key_hex=None):
    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError("The key must be 32 bytes (64 hex characters)")
        return key
    os.makedirs(HOME_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        if len(key) != 32:
            raise ValueError("Local key file is corrupt; back it up, delete %s "
                             "and let it be regenerated" % KEY_FILE)
        return key
    key = AESGCM.generate_key(bit_length=256)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    print("Generated a local key: %s  (back it up; without it existing "
          "ciphertext cannot be decrypted)" % KEY_FILE, file=sys.stderr)
    return key


def encrypt_file(in_path, out_path, key_hex=None):
    key = _load_or_create_key(key_hex)
    with open(in_path, "rb") as f:
        data = f.read()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, data, None)
    with open(out_path, "wb") as f:
        f.write(MAGIC + nonce + ct)
    return len(data), len(ct)


def decrypt_file(in_path, out_path, key_hex=None):
    key = _load_or_create_key(key_hex)
    with open(in_path, "rb") as f:
        blob = f.read()
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 12 + 16:
        raise ValueError("Not a ciphertext produced by this module "
                         "(missing the LPG1 header)")
    nonce = blob[len(MAGIC):len(MAGIC) + 12]
    ct = blob[len(MAGIC) + 12:]
    plain = AESGCM(key).decrypt(nonce, ct, None)   # raises InvalidTag on auth failure
    with open(out_path, "wb") as f:
        f.write(plain)
    return len(plain)


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway encrypted storage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("encrypt", "decrypt"):
        p = sub.add_parser(name)
        p.add_argument("--in", dest="in_path", required=True)
        p.add_argument("--out", dest="out_path", required=True)
        p.add_argument("--key-hex", default=None)
    args = ap.parse_args()
    try:
        if args.cmd == "encrypt":
            n, _ = encrypt_file(args.in_path, args.out_path, args.key_hex)
            print("Encrypted %d bytes -> %s" % (n, args.out_path))
        else:
            n = decrypt_file(args.in_path, args.out_path, args.key_hex)
            print("Decrypted %d bytes -> %s" % (n, args.out_path))
    except Exception as exc:
        print("Operation failed: %s" % exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
