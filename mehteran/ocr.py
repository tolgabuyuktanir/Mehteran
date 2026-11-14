"""Text recognition (OCR) for scanned PDFs and images: Tesseract, with the PDF pages turned into images by Poppler's
pdftoppm.

- Finding them: Mehteran's own copies in <code folder>/.runtime first (tesseract/, poppler/), then PATH.
- Installing: only when the user asks (the Setup tab, `mehter install-local ocr`). Poppler and micromamba come from
  the translation app's installer (pipeline.runtime.install_poppler: micromamba checked against its published
  SHA-256 sum); Tesseract is the pinned conda-forge package (micromamba checks every package against the channel's
  SHA-256 sums) in .runtime/tesseract. The language data is the "fast" model set of tesseract-ocr/tessdata_fast,
  tag 4.1.0, each file checked against the SHA-256 sum written below (the downloads were checked against the git
  blob hashes of that tag when the sums were written). It goes to .runtime/tessdata.
- Ottoman Turkish has no Tesseract model ("ota" does not exist in tessdata); for Ottoman texts use "ara" or "fas"
  (Persian), which read the Arabic script.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from . import paths
from .i18n import t
from .localtools import ToolError, dir_size, download_verified, run

TESSERACT_SPEC = "tesseract=5.5.4"
TESSDATA_URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/{lang}.traineddata"
LANGUAGES = {  # tessdata_fast 4.1.0: SHA-256 and size of each file
    "eng": ("7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2", 4113088),
    "tur": ("7393381111e1152420fc4092cb44eef4237580d21b92bf30d7d221aad192c6b7", 4550554),
    "ara": ("e3206d3dc87fd50c24a0fb9f01838615911d25168f4e64415244b67d2bb3e729", 1432056),
    "fas": ("db1c0a91208aff00d3cf1ed2c1d23f76419afd5f024688b4f71adc3f2ce4a505", 431500),
    # More languages, offered in the Setup tab (checked against the git blob hashes of tag 4.1.0 as well).
    "deu": ("19d219bbb6672c869d20a9636c6816a81eb9a71796cb93ebe0cb1530e2cdb22d", 1525436),
    "fra": ("ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca", 1130365),
    "spa": ("6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464", 2294433),
    "ita": ("b8f89e1e785118dac4d51ae042c029a64edb5c3ee42ef73027a6d412748d8827", 2701314),
    "por": ("c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb", 1982756),
    "nld": ("ced0e5e046a84c908a6aa7accbef9a232c4a5d9a8276691b81c6ee64d02963f6", 6050296),
    "rus": ("e16e5e036cce1d9ec2b00063cf8b54472625b9e14d893a169e2b0dedeb4df225", 3861738),
    "ell": ("4fba8a0b461038d51f1c20d043d4f2ac38c4e778f1b90830847f7bd8fa3ba726", 1419514),
    "aze": ("a365310848aecb739f19369cb3831d4660fcd9345d798e91a3042455f9ccc9f0", 3524799),
    "kmr": ("a3ef2daa828399ca8d6ae69edfa21ed21aa5abb3f868e2024d3235406312e7b6", 3568615),
    "urd": ("62e8250ce2a994106e313a82e26a516a39e2cf159d0ce3c5b5008387fd0d555f", 1398718),
    "heb": ("11f9e43ab227f786352a50f75c94c2e9906f1baba86d93276da19da7ce0904db", 961404),
    "hin": ("4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825", 1122751),
    "chi_sim": ("a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730", 2469156),
    "jpn": ("1f5de9236d2e85f5fdf4b3c500f2d4926f8d9449f28f5394472d9e8d83b91b4d", 2471260),
    "kor": ("6b85e11d9bbf07863b97b3523b1b112844c43e713df8b66418a081fd1060b3b2", 1677415),
}
DEFAULT_LANGUAGES = ["eng", "tur", "ara", "fas"]  # installed with Tesseract when its own data lacks them
IMAGE_FORMATS = ("png", "jpg", "jpeg", "tif", "tiff")
LANG_RE = re.compile(r"[a-z]{3}(_[a-z]+)?(\+[a-z]{3}(_[a-z]+)?){0,7}\Z")
MAX_PAGES = 500          # pages recognised in one file
PAGE_TIMEOUT = 180       # seconds per page (pdftoppm, then tesseract)
DPI = 300
SPARSE = 25              # a PDF page with fewer letters than this has no real text layer


def _exe(name: str) -> str:
    return name + ".exe" if sys.platform == "win32" else name


def _bin(prefix: Path) -> Path:
    return prefix / "Library" / "bin" if sys.platform == "win32" else prefix / "bin"


def _find(name: str, prefix: Path) -> Path | None:
    own = _bin(prefix) / _exe(name)
    if own.is_file():
        return own
    found = shutil.which(name)
    return Path(found) if found else None


def tesseract() -> Path | None:
    return _find("tesseract", paths.runtime() / "tesseract")


def pdftoppm() -> Path | None:
    return _find("pdftoppm", paths.runtime() / "poppler")


def pdftotext() -> Path | None:
    return _find("pdftotext", paths.runtime() / "poppler")


def tessdata() -> Path:
    return paths.runtime() / "tessdata"


def languages() -> list[str]:
    """The languages Tesseract can read here: Mehteran's language files and those of the installed Tesseract."""
    found = {p.stem for p in tessdata().glob("*.traineddata")}
    program = tesseract()
    if program:
        try:
            out = subprocess.run([str(program), "--list-langs"], capture_output=True, text=True, timeout=20)
            found |= {line.strip() for line in out.stdout.splitlines()[1:] if re.fullmatch(r"[a-z_]{3,20}", line.strip())}
        except (OSError, subprocess.SubprocessError):
            pass
    return sorted(found - {"osd", "equ"})


def _version(program: Path | None) -> str | None:
    if not program:
        return None
    try:
        out = subprocess.run([str(program), "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+\.\d+(\.\d+)?)", out.stdout + out.stderr)
    return m.group(1) if m else None


def status() -> dict:
    program, ppm = tesseract(), pdftoppm()
    own = paths.runtime() / "tesseract"
    have = languages() if program else []
    return {"id": "ocr", "name": "Tesseract OCR", "installed": bool(program and ppm), "path": str(program) if program else None,
            "source": None if not program else "mehteran" if str(program).startswith(str(paths.runtime())) else "system",
            "version": _version(program), "pinned_version": TESSERACT_SPEC.partition("=")[2],
            "pdftoppm": str(ppm) if ppm else None, "size": (dir_size(own) or 0) + (dir_size(tessdata()) or 0) or None,
            "languages": have,
            "available_languages": [{"code": code, "size": size, "installed": code in have}
                                    for code, (_, size) in LANGUAGES.items()]}


# --- recognising ---------------------------------------------------------------------

def check_languages(langs: str) -> str:
    """The languages to use. Without a choice: Turkish and English, as far as they are installed."""
    have = languages()
    if not (langs or "").strip():
        chosen = [code for code in ("tur", "eng") if code in have]
        langs = "+".join(chosen) or "tur+eng"
    langs = langs.strip()
    if not LANG_RE.match(langs):
        raise ToolError(t("ocr_bad_languages", value=langs))
    missing = [code for code in langs.split("+") if code not in have]
    if missing:
        raise ToolError(t("ocr_language_missing", languages=", ".join(missing)))
    return langs


def _tesseract_args(langs: str) -> list[str]:
    own = tessdata()
    if all((own / f"{code}.traineddata").is_file() for code in langs.split("+")):
        return ["--tessdata-dir", str(own), "-l", langs]
    return ["-l", langs]


def image_text(image: Path, langs: str, abort: threading.Event | None, workdir: Path) -> str:
    program = tesseract()
    if program is None:
        raise ToolError(t("ocr_missing"))
    out = workdir / f"{image.stem}-ocr"
    code, errors = run([str(program), str(image), str(out), *_tesseract_args(langs)], abort, PAGE_TIMEOUT)
    result = out.with_suffix(".txt")
    if code != 0 or not result.exists():
        raise ToolError(t("ocr_failed", name=image.name, error=errors.strip()[-300:]))
    return result.read_text(encoding="utf-8", errors="replace").strip()


def pdf_pages(pdf: Path, abort: threading.Event | None) -> list[str]:
    """The text layer of each page (pdftotext; pages end with a form feed)."""
    program = pdftotext()
    if program is None:
        raise ToolError(t("ocr_need_poppler"))
    with tempfile.TemporaryDirectory(prefix="mehteran-pdf-") as tmp:
        out = Path(tmp) / "text.txt"
        code, errors = run([str(program), "-enc", "UTF-8", str(pdf), str(out)], abort, 600)
        if code != 0 or not out.exists():
            raise ToolError(t("ocr_failed", name=pdf.name, error=errors.strip()[-300:]))
        pages = out.read_text(encoding="utf-8", errors="replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def sparse(text: str) -> bool:
    return sum(ch.isalnum() for ch in text) < SPARSE


def pdf_ocr(pdf: Path, pages: list[int], langs: str, abort: threading.Event | None) -> dict[int, str]:
    """{page number (from 1): recognised text} for the given pages."""
    ppm = pdftoppm()
    if ppm is None:
        raise ToolError(t("ocr_need_poppler"))
    if len(pages) > MAX_PAGES:
        raise ToolError(t("ocr_too_many_pages", count=len(pages), limit=MAX_PAGES))
    out = {}
    with tempfile.TemporaryDirectory(prefix="mehteran-ocr-") as tmp:
        work = Path(tmp)
        for page in pages:
            prefix = work / f"page-{page}"
            code, errors = run([str(ppm), "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", "-gray",
                                str(pdf), str(prefix)], abort, PAGE_TIMEOUT)
            images = sorted(work.glob(f"page-{page}*.png"))
            if code != 0 or not images:
                raise ToolError(t("ocr_failed", name=f"{pdf.name} ({page})", error=errors.strip()[-300:]))
            out[page] = image_text(images[0], langs, abort, work)
            for image in images:
                image.unlink()
    return out


# --- installing -------------------------------------------------------------------------

def install(langs: list[str] | None = None) -> None:
    """Poppler (with micromamba) if missing, Tesseract into .runtime/tesseract, and the language files. Output goes
    to stdout (the job log)."""
    from pipeline import runtime
    base = paths.runtime()
    micromamba = base / "micromamba" / _exe("micromamba")
    if not micromamba.exists() or pdftoppm() is None:
        print(t("ocr_installing_poppler"), flush=True)
        runtime.install_poppler(base.parent)  # <root>/.runtime/poppler and <root>/.runtime/micromamba
    prefix = base / "tesseract"
    env = {**os.environ, "MAMBA_ROOT_PREFIX": str(base / "mamba"), "CONDA_PKGS_DIRS": str(base / "mamba" / "pkgs")}
    root_prefix = ["--root-prefix", str(base / "mamba")]
    print(t("ocr_installing", spec=TESSERACT_SPEC), flush=True)
    for argv in ([str(micromamba), "create", *root_prefix, "--yes", "--prefix", str(prefix), "--channel", "conda-forge",
                  "--override-channels", TESSERACT_SPEC],
                 [str(micromamba), "clean", "--all", "--yes"]):
        print("> " + subprocess.list2cmdline(argv), flush=True)
        if subprocess.run(argv, env=env, stdin=subprocess.DEVNULL).returncode != 0:
            raise ToolError(t("ocr_install_failed"))
    if not (_bin(prefix) / _exe("tesseract")).is_file():
        raise ToolError(t("ocr_install_failed"))
    have = languages()  # the conda-forge package brings the language data of tessdata itself (125 languages)
    install_languages([code for code in (langs or DEFAULT_LANGUAGES) if code not in have])


def install_languages(langs: list[str]) -> None:
    for code in langs:  # checked first: an unknown code downloads nothing
        if code not in LANGUAGES:
            raise ToolError(t("ocr_unknown_language", code=code, known=", ".join(LANGUAGES)))
        target = tessdata() / f"{code}.traineddata"
        if target.is_file() and target.stat().st_size == LANGUAGES[code][1]:
            continue
        print(t("ocr_language_downloading", code=code), flush=True)
        download_verified(TESSDATA_URL.format(lang=code), target, LANGUAGES[code][0])
    print(t("ocr_installed", languages=", ".join(languages())), flush=True)
