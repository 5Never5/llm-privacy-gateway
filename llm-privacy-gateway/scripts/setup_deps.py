#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway · 依赖检查与安装 (setup_deps.py)

跨智能体工具（豆包工作 / Codex / DeepSeek Harness / Claude 系等）首次运行本
Skill 前，用本脚本补齐运行依赖。只检查不安装用 --check。

用法:
  python setup_deps.py --check        # 只检查，列出缺失项
  python setup_deps.py                # 安装缺失的核心依赖（默认）
  python setup_deps.py --install-ocr  # 额外安装 OCR 依赖（图片文字提取用）
"""
import argparse
import importlib.util
import subprocess
import sys

# 核心依赖：模块名 -> 用途
REQUIRED = {
    "cryptography": "AES-256-GCM 加密",
    "pypdf": "PDF 文字提取",
    "docx": "Word(.docx) 提取",
    "openpyxl": "Excel(.xlsx) 提取",
    "PIL": "图片基础（OCR 前置）",
}
# 可选 OCR 依赖
OCR_OPTIONAL = {
    "pytesseract": "Tesseract OCR 接口（需另装 Tesseract 程序与 chi_sim 语言包）",
    "paddleocr": "PaddleOCR（中文效果好，体积较大，另需 paddlepaddle）",
}


def _have(mod):
    return importlib.util.find_spec(mod) is not None


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway 依赖检查/安装")
    ap.add_argument("--check", action="store_true", help="只检查不安装")
    ap.add_argument("--install-ocr", action="store_true", help="额外安装 OCR 依赖")
    args = ap.parse_args()

    print("== 核心依赖 ==")
    missing = []
    for mod, why in REQUIRED.items():
        ok = _have(mod)
        print("  [%s] %-13s %s" % ("OK " if ok else "缺失", mod, why))
        if not ok:
            missing.append(mod)

    if args.check:
        print("缺失项：%s" % ("，".join(missing) if missing else "无，可直接使用"))
        sys.exit(0 if not missing else 1)

    if missing:
        print("正在安装：%s ..." % " ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("安装完成。")

    if args.install_ocr:
        for mod, why in OCR_OPTIONAL.items():
            if not _have(mod):
                print("正在安装 OCR 依赖：%s（%s）" % (mod, why))
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", mod])
                except subprocess.CalledProcessError:
                    print("  安装失败，请按 local_extract.py 的提示手动安装。")
    print("依赖就绪。OCR 未装也不影响文本/PDF/Word/Excel 处理。")


if __name__ == "__main__":
    main()
