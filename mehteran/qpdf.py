"""qpdf: repairs a damaged PDF and removes the encryption of a PDF that opens without a password, so that it can be
read. document.extract uses it by itself: when a PDF cannot be read, it reads the copy that qpdf writes.

- Finding it: Mehteran's own copy in <code folder>/.runtime/qpdf first, then PATH.
- Installing it: only when the user asks (the Setup tab, `mehter install-local qpdf`): the pinned conda-forge package
  (micromamba checks every package against the channel's SHA-256 sums) into .runtime/qpdf.
"""

from __future__ import annotations

import threading
from pathlib import Path

from . import paths
from .i18n import t
from .localtools import (ToolError, conda_bin, conda_install, dir_size, disk_free, exe, find_program, micromamba_missing,
                         program_version, run)

SPEC = "qpdf=12.4.2"
DOWNLOAD_SIZE = 5_500_000  # with its libraries, about (measured on macOS arm64)
TIMEOUT = 300


def prefix() -> Path:
    return paths.runtime() / "qpdf"


def binary() -> tuple[Path | None, str | None]:
    return find_program("qpdf", [conda_bin(prefix()) / exe("qpdf")])


def status() -> dict:
    program, source = binary()
    return {"id": "qpdf", "name": "qpdf", "installed": program is not None, "source": source,
            "path": str(program) if program else None, "version": program_version(program),
            "pinned_version": SPEC.partition("=")[2], "size": dir_size(prefix()), "download_size": DOWNLOAD_SIZE,
            "install_dir": str(prefix()), "disk_free": disk_free(prefix()), "poppler_first": micromamba_missing()}


def install() -> None:
    conda_install(prefix(), [SPEC])
    program = conda_bin(prefix()) / exe("qpdf")
    if not program.is_file():
        raise ToolError(t("tool_install_failed", name="qpdf"))
    print(t("tool_installed", name="qpdf", version=program_version(program) or SPEC, path=program), flush=True)


def repair(pdf: Path, out: Path, abort: threading.Event | None = None) -> bool:
    """Writes a repaired, decrypted copy of pdf to out. False when qpdf is missing or cannot repair it."""
    program, _ = binary()
    if program is None:
        return False
    # Exit code 3: written, with warnings (that is what a repaired file gives).
    code, _ = run([str(program), "--decrypt", "--object-streams=disable", str(pdf), str(out)], abort, TIMEOUT)
    return code in (0, 3) and out.is_file() and out.stat().st_size > 0
