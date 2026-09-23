#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway · 核心机密加密模块 (crypto_store.py)

对核心商业机密等文件做本地 AES-256-GCM 加密存储：
  - 密钥自动生成并保存在 ~/.llm-privacy-gate/key.bin（首用生成）
  - 也可用 --key-hex 传入外部密钥（16 进制 64 字符）
  - 文件格式: MAGIC("LPG1") + nonce(12B) + tag(16B) + 密文
  - 密文文件可放心交给任何人/任何云盘，无密钥无法解密

用法:
  python crypto_store.py encrypt --in secret.docx --out secret.docx.enc
  python crypto_store.py decrypt --in secret.docx.enc --out secret.docx
  python crypto_store.py encrypt --in secret.pdf --out secret.pdf.enc --key-hex <64位hex>
"""
import argparse
import os
import sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("缺少依赖：请先执行  python -m pip install cryptography", file=sys.stderr)
    sys.exit(1)

MAGIC = b"LPG1"
HOME_DIR = os.path.join(os.path.expanduser("~"), ".llm-privacy-gate")
KEY_FILE = os.path.join(HOME_DIR, "key.bin")


def _load_or_create_key(key_hex=None):
    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError("密钥长度必须为 32 字节（64 位十六进制）")
        return key
    os.makedirs(HOME_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        if len(key) != 32:
            raise ValueError("本地密钥文件损坏，请备份后删除 %s 重新生成" % KEY_FILE)
        return key
    key = AESGCM.generate_key(bit_length=256)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    print("已生成本地密钥：%s （请妥善备份；删除后历史密文将无法解密）" % KEY_FILE,
          file=sys.stderr)
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
        raise ValueError("不是本模块生成的加密文件（缺少 LPG1 头）")
    nonce = blob[len(MAGIC):len(MAGIC) + 12]
    ct = blob[len(MAGIC) + 12:]
    plain = AESGCM(key).decrypt(nonce, ct, None)   # 校验失败会抛 InvalidTag
    with open(out_path, "wb") as f:
        f.write(plain)
    return len(plain)


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway 核心机密加密")
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
            print("已加密 %d 字节 -> %s" % (n, args.out_path))
        else:
            n = decrypt_file(args.in_path, args.out_path, args.key_hex)
            print("已解密 %d 字节 -> %s" % (n, args.out_path))
    except Exception as exc:
        print("操作失败：%s" % exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
