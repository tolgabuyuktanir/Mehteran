"""Fake pdftotext, pdftoppm and tesseract for the Mehteran OCR tests: python mehteran_fake_ocr.py <tool> <args>.

A "PDF" here is a text file whose pages are separated by form feeds; a "page image" holds the page's text. An image
whose text contains "SLOW" makes tesseract wait 30 seconds (to test cancel)."""

import sys
import time
from pathlib import Path

tool, args = sys.argv[1], sys.argv[2:]
if tool == "pdftotext":
    pdf, out = Path(args[-2]), Path(args[-1])
    out.write_text(pdf.read_text(encoding="utf-8"), encoding="utf-8")
elif tool == "pdftoppm":
    page = int(args[args.index("-f") + 1])
    pdf, prefix = Path(args[-2]), args[-1]
    pages = pdf.read_text(encoding="utf-8").split("\f")
    Path(f"{prefix}-{page}.png").write_text(f"scan of page {page}: {pages[page - 1].strip()}", encoding="utf-8")
elif tool == "tesseract":
    if args == ["--list-langs"]:
        print("List of available languages in \"/fake/\" (2):\neng\ntur")
    elif args == ["--version"]:
        print("tesseract 5.5.4")
    else:
        image, out = Path(args[0]), Path(args[1])
        text = image.read_text(encoding="utf-8", errors="replace")
        if "SLOW" in text:
            time.sleep(30)
        langs = args[args.index("-l") + 1]
        Path(str(out) + ".txt").write_text(f"OCR({langs}) {text}\n", encoding="utf-8")
