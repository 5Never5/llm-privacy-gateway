# Third-party notices

**This repository contains no third-party source code.** Everything in
`llm-privacy-gateway/scripts/` is original work, and it imports nothing but the
Python standard library. The packages listed below are **runtime dependencies**:
they are not vendored, not copied in, and not distributed from here. Each user
installs them with `python scripts/setup_deps.py`, and they arrive under their
own licences from their own distributors.

Two reasons this file exists. First, those licences require the attribution to
survive redistribution, and redistributing this skill is the normal way it is
used — the folder is copied into someone else's skills directory. Second, if you
are bundling this skill into a product of your own, this is the list of what you
are then carrying.

Verified against the upstream repositories on 24 September 2026. Version numbers
are deliberately left out: pin your own in your own requirements file, and read
the installed package's `LICENSE` when it matters.

## Core dependencies — installed by `setup_deps.py`

| Component | Used for | Licence | Upstream |
| :--- | :--- | :--- | :--- |
| **cryptography** | AES-256-GCM encryption of core secrets; key generation | Apache-2.0 **or** BSD-3-Clause (dual) | [pyca/cryptography](https://github.com/pyca/cryptography) |
| **pypdf** | Local text extraction from PDF files | BSD-3-Clause | [py-pdf/pypdf](https://github.com/py-pdf/pypdf) |
| **python-docx** | Local text extraction from Word `.docx` files | MIT | [python-openxml/python-docx](https://github.com/python-openxml/python-docx) |
| **openpyxl** | Local text extraction from Excel `.xlsx` files | MIT | [openpyxl](https://openpyxl.readthedocs.io/) |
| **Pillow** | Image handling, and a prerequisite for the OCR engines | MIT-CMU | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) |

`cryptography` is genuinely dual-licensed: its `LICENSE` says contributions are
made under *both* the Apache and the BSD terms and that you may use the software
under *either*. Take whichever suits you; both are recorded here because the
upstream asks for both to travel.

## Optional OCR dependencies — installed by `setup_deps.py --install-ocr`

Only needed for `.png/.jpg/.bmp/.webp/.tiff` input. Text, PDF, Word and Excel
handling work without any of this.

| Component | Used for | Licence | Upstream |
| :--- | :--- | :--- | :--- |
| **pytesseract** | Python binding for the Tesseract engine | Apache-2.0 | [madmaze/pytesseract](https://github.com/madmaze/pytesseract) |
| **Tesseract OCR** | The engine that actually reads the image; a system program, not a pip package, and it also needs the `traineddata` for the language you are reading | Apache-2.0 | [tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) |
| **paddleocr** | Alternative OCR engine, tried first when present | Apache-2.0 | [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) |
| **paddlepaddle** | Inference framework required by `paddleocr` | Apache-2.0 | [PaddlePaddle/Paddle](https://github.com/PaddlePaddle/Paddle) |

The OCR engines pull in trained models of their own. Those model files carry
their own licences, separate from the code — check them before shipping the
models inside anything, because this repository does not fetch or bundle them
for you.

## What those licences require of you

They are all permissive: none of them restricts commercial use, and none of them
requires you to publish your own changes. What they do require, when you
redistribute the dependency itself — which includes shipping it inside a bundle:

- **Keep the notice.** Every licence above requires that the copyright notice
  and the licence text of the component be reproduced. Do not strip the
  `LICENSE` files or the `*.dist-info` metadata directories out of an
  installation.
- **Do not imply endorsement.** BSD-3-Clause, which covers `pypdf`, forbids
  using the names of its authors or contributors to endorse or promote your
  derived product without written permission. The same goes for the trademarks
  listed in the repository `NOTICE`.
- **Apache-2.0 components carry a patent grant and a patent-retaliation clause.**
  `cryptography`, `pytesseract`, Tesseract, PaddleOCR and Paddlepaddle are all
  Apache-2.0. If you initiate patent litigation alleging that one of them
  infringes, your licence to it ends. Nothing here asks you to do anything
  beyond that.
- **Pass this file along.** If you redistribute this skill, keep
  `THIRD-PARTY-NOTICES.md` and `NOTICE` with it. Under Apache-2.0 the notice file
  is part of what has to be reproduced, and this repository's own
  `NOTICE` states that in the same terms.

## What this repository does not include

- No Python package is vendored, mirrored or archived here.
- No font, icon, logo or illustration from another project is used. The
  diagrams under `docs/assets/` and the banner are made for this repository.
  The payment QR cards are renderings of the maintainer's own payment links.
- The names of the agent tools in the README (Doubao Work, OpenAI Codex,
  DeepSeek Harness, OpenClaw, WorkBuddy, Claude) belong to their respective
  owners and appear only to say where this skill runs.

---

<p align="center"><sub><a href="README.md">Back to README</a> &nbsp;·&nbsp; <a href="NOTICE">NOTICE</a> &nbsp;·&nbsp; <a href="LICENSE">LICENSE</a></sub></p>
