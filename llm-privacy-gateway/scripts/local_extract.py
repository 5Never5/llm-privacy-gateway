#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm-privacy-gateway - local text extraction module (local_extract.py)

File and image bodies are parsed and reduced to text locally, so the body
never leaves the machine:
  - .txt/.md/.csv/.json/.log  read as text directly
  - .pdf                      extracted with pypdf
  - .docx                     extracted with python-docx (paragraphs + tables)
  - .xlsx                     extracted with openpyxl (all cells)
  - images (.png/.jpg/.jpeg/.bmp/.webp/.tiff)
                              OCR (paddleocr first, then pytesseract; when no
                              engine is installed a clear install hint is given)

Usage:
  python local_extract.py --file path [--max-chars 20000] [--ocr-lang en]
"""
import argparse
import os
import sys

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".log", ".xml", ".html"}
SUPPORTED_EXTS = (TEXT_EXTS | IMAGE_EXTS | {".pdf", ".docx", ".xlsx"})

DEFAULT_OCR_LANG = "en"
# Aliases mapping the short codes used on the command line to Tesseract's
# traineddata names. PaddleOCR understands the short codes directly.
_TESSERACT_ALIASES = {"en": "eng", "ch": "chi_sim"}

_DEP_HINT = "run  python scripts/setup_deps.py  to install the missing dependencies first"


def _paddle_lang(ocr_lang):
    """PaddleOCR takes a single language code, so use the first one given."""
    first = (ocr_lang or DEFAULT_OCR_LANG).split("+")[0].strip()
    return first or DEFAULT_OCR_LANG


def _tesseract_lang(ocr_lang):
    """Tesseract takes a '+'-joined list of traineddata names."""
    parts = [p.strip() for p in (ocr_lang or DEFAULT_OCR_LANG).split("+") if p.strip()]
    mapped = [_TESSERACT_ALIASES.get(p, p) for p in parts]
    return "+".join(mapped) or _TESSERACT_ALIASES[DEFAULT_OCR_LANG]


def extract_text(path, max_chars=None, ocr_lang=None):
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError(
            "Unsupported file type: %s (supported: text such as txt/md/csv/json, "
            "PDF, Word (.docx), Excel (.xlsx), common images; re-save legacy "
            ".doc/.xls files in the newer format first)" % ext)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if ext in TEXT_EXTS:
        text = _read_text_file(path)
    elif ext == ".pdf":
        text = _extract_pdf(path)
    elif ext == ".docx":
        text = _extract_docx(path)
    elif ext == ".xlsx":
        text = _extract_xlsx(path)
    elif ext in IMAGE_EXTS:
        text = _extract_image(path, ocr_lang)
    else:
        raise ValueError("Unsupported file type: %s" % ext)
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return text


def _read_text_file(path):
    for enc in ("utf-8", "gb18030", "utf-16"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Fallback: decode with errors ignored
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("Missing the PDF parsing dependency (%s)." % _DEP_HINT)
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception as exc:  # one bad page must not abort the whole extraction
            parts.append("[page %d extraction failed: %s]" % (len(parts) + 1, exc))
    return "\n".join(p for p in parts if p)


def _extract_docx(path):
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("Missing the Word parsing dependency (%s)." % _DEP_HINT)
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            parts.append(" | ".join(cells))
    return "\n".join(parts)


def _extract_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise RuntimeError("Missing the Excel parsing dependency (%s)." % _DEP_HINT)
    wb = load_workbook(path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append("== Sheet: %s ==" % ws.title)
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else str(v) for v in row]
            if any(vals):
                parts.append(" | ".join(vals))
    wb.close()
    return "\n".join(parts)


def _extract_image(path, ocr_lang=None):
    """OCR: paddleocr first, then pytesseract; if neither is present, explain how to install."""
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang=_paddle_lang(ocr_lang), show_log=False)
        result = ocr.ocr(path, cls=True)
        lines = []
        for page in result or []:
            for item in page or []:
                lines.append(item[1][0])
        return "\n".join(lines)
    except ImportError:
        pass
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(
            Image.open(path), lang=_tesseract_lang(ocr_lang))
    except ImportError:
        pass
    except Exception as exc:
        raise RuntimeError("OCR engine call failed: %s" % exc)
    raise RuntimeError(
        "No OCR engine installed, so text cannot be extracted from images. "
        "Install either one:\n"
        "  1) python -m pip install paddleocr paddlepaddle   (recommended)\n"
        "  2) python -m pip install pytesseract, then install the Tesseract OCR "
        "program and the traineddata for your language (e.g. eng, chi_sim)")


def main():
    ap = argparse.ArgumentParser(description="llm-privacy-gateway local text extraction")
    ap.add_argument("--file", required=True, help="path to the local file")
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--ocr-lang", default=None,
                    help="OCR language set for images (default: en; use ch for "
                         "Chinese, en+ch for mixed, or any Tesseract code)")
    args = ap.parse_args()
    try:
        text = extract_text(args.file, max_chars=args.max_chars,
                            ocr_lang=args.ocr_lang)
    except Exception as exc:
        print("Extraction failed: %s" % exc, file=sys.stderr)
        sys.exit(1)
    print("Extracted %d characters locally (file body not uploaded)." % len(text),
          file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
