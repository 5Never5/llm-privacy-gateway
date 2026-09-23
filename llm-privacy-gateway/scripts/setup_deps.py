#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway - dependency check and install (setup_deps.py)

Run this once before the first use of this skill in a new environment
(Doubao Work / Codex / DeepSeek Harness / Claude family etc.) to install the
runtime dependencies. Use --check to inspect without installing.

Usage:
  python setup_deps.py --check        # check only, list what is missing
  python setup_deps.py                # install the missing core dependencies (default)
  python setup_deps.py --install-ocr  # additionally install the OCR dependencies
"""
import argparse
import importlib.util
import subprocess
import sys

# Core dependencies: module name -> what it is for
REQUIRED = {
    "cryptography": "AES-256-GCM encryption",
    "pypdf": "PDF text extraction",
    "docx": "Word (.docx) extraction",
    "openpyxl": "Excel (.xlsx) extraction",
    "PIL": "image basics (prerequisite for OCR)",
}
# Optional OCR dependencies
OCR_OPTIONAL = {
    "pytesseract": "Tesseract OCR binding (also needs the Tesseract program and the traineddata for your language)",
    "paddleocr": "PaddleOCR (larger download, also needs paddlepaddle)",
}


def _have(mod):
    return importlib.util.find_spec(mod) is not None


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway dependency check/install")
    ap.add_argument("--check", action="store_true", help="check only, do not install")
    ap.add_argument("--install-ocr", action="store_true", help="also install the OCR dependencies")
    args = ap.parse_args()

    print("== Core dependencies ==")
    missing = []
    for mod, why in REQUIRED.items():
        ok = _have(mod)
        print("  [%-7s] %-13s %s" % ("ok" if ok else "missing", mod, why))
        if not ok:
            missing.append(mod)

    if args.check:
        print("Missing: %s" % (", ".join(missing) if missing else "none - ready to use"))
        sys.exit(0 if not missing else 1)

    if missing:
        print("Installing: %s ..." % " ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("Install complete.")

    if args.install_ocr:
        for mod, why in OCR_OPTIONAL.items():
            if not _have(mod):
                print("Installing OCR dependency: %s (%s)" % (mod, why))
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", mod])
                except subprocess.CalledProcessError:
                    print("  Install failed; follow the hint printed by "
                          "local_extract.py to install it manually.")
    print("Dependencies ready. A missing OCR engine does not affect "
          "text/PDF/Word/Excel handling.")


if __name__ == "__main__":
    main()
