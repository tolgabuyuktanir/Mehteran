"""Fake typst, pandoc, ffmpeg, whisper-cli and qpdf for the Mehteran converter tests: python mehteran_fake_tools.py
<tool> <args>. Each writes a small file that shows what it was asked to do.

- typst: the "PDF" is "%PDF-fake" and the Typst source; a source with FAIL_TYPST fails.
- pandoc: reading (--from odt|rtf) gives "# From pandoc" and the file's text; writing gives "FAKE-<format>", the
  metadata and the Markdown.
- ffmpeg copies the input; whisper-cli writes "[<language>|<model file>] <text>" (SLOW in the text: waits 30 s).
- pdftotext fails on a "PDF" (a text file, pages split by form feeds) that contains BROKEN.
- qpdf writes the input with BROKEN replaced by FIXED and exits with 3 (written, with warnings)."""

import sys
import time
from pathlib import Path

tool, args = sys.argv[1], sys.argv[2:]


def value(flag: str) -> str:
    return args[args.index(flag) + 1]


if args == ["--version"]:
    print({"typst": "typst 0.15.1 (fake)", "pandoc": "pandoc 3.14", "qpdf": "qpdf version 12.4.2"}.get(tool, "1.0.0"))
elif tool == "typst":
    source, out = Path(args[-2]), Path(args[-1])
    text = source.read_text(encoding="utf-8")
    if "FAIL_TYPST" in text:
        print("error: fake failure", file=sys.stderr)
        sys.exit(1)
    fonts = value("--font-path") if "--font-path" in args else ""
    out.write_text(f"%PDF-fake fonts={fonts}\n{text}", encoding="utf-8")
elif tool == "pandoc":
    assert args[0] == "--sandbox", args
    source, out, kind = Path(args[-1]), Path(value("--output")), value("--to")
    if kind.startswith("gfm"):
        out.write_text("# From pandoc\n\n" + source.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        meta = [args[i + 1] for i, a in enumerate(args) if a == "--metadata"]
        out.write_text(f"FAKE-{kind} {value('--from')} {' '.join(meta)}\n" + source.read_text(encoding="utf-8"), encoding="utf-8")
elif tool == "ffmpeg":
    Path(args[-1]).write_bytes(Path(value("-i")).read_bytes())
elif tool == "whisper-cli":
    text = Path(value("-f")).read_text(encoding="utf-8")
    if "SLOW" in text:
        time.sleep(30)
    Path(value("-of") + ".txt").write_text(f"[{value('-l')}|{Path(value('-m')).name}] {text}\n\n", encoding="utf-8")
elif tool == "pdftotext":  # as mehteran_fake_ocr.py, but a "PDF" with BROKEN in it cannot be read
    pdf, out = Path(args[-2]), Path(args[-1])
    if "BROKEN" in pdf.read_text(encoding="utf-8"):
        print("Syntax Error: Couldn't find trailer dictionary", file=sys.stderr)
        sys.exit(1)
    out.write_text(pdf.read_text(encoding="utf-8"), encoding="utf-8")
elif tool == "qpdf":
    source, out = Path(args[-2]), Path(args[-1])
    out.write_text(source.read_text(encoding="utf-8").replace("BROKEN", "FIXED"), encoding="utf-8")
    sys.exit(3)
