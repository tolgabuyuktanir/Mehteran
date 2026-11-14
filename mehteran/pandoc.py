"""Pandoc: optional document conversion. With it, document.export writes EPUB and can write Word files whose LaTeX
math ($...$, $$...$$) becomes real Word equations, and document.extract reads OpenDocument (.odt) and RTF files.
Without it, Mehteran's own Word exporter stays the default.

- Finding it: Mehteran's own copy in <code folder>/.runtime/pandoc first, then PATH.
- Installing it: only when the user asks (the Setup tab, `mehter install-local pandoc`). The official release archive
  of a pinned version is downloaded from GitHub and checked against the SHA-256 sum written below (the sums were
  computed from the downloaded files and match GitHub's own asset digests). Windows on ARM uses the x64 build.
- Pandoc always runs with --sandbox: a document cannot make it read other files or fetch anything from the network.
"""

from __future__ import annotations

import re
import tempfile
import threading
from pathlib import Path

from . import paths
from .i18n import t
from .localtools import ToolError, dir_size, disk_free, exe, find_program, install_archive, platform_key, program_version, run

VERSION = "3.14"
RELEASE = f"https://github.com/jgm/pandoc/releases/download/{VERSION}"
# (system, machine) -> (asset, SHA-256, size) of release 3.14.
ASSETS = {
    ("darwin", "arm64"): ("pandoc-3.14-arm64-macOS.zip", "58d6593884fec9d4424b641b92503c316d9c36decb2891ff8d73ae74dd3b6304", 43712865),
    ("darwin", "x64"): ("pandoc-3.14-x86_64-macOS.zip", "891708579061e7b1c1a6ce0df30ebb3cb2b6d0ca045ed3c8554ab830c1e0c270", 27490795),
    ("linux", "x64"): ("pandoc-3.14-linux-amd64.tar.gz", "c5f4720cdefb3f7bdc5d07202ef579feef0d1370773c873804dd8fdaa8c4f1b8", 36635549),
    ("linux", "arm64"): ("pandoc-3.14-linux-arm64.tar.gz", "c692f3d78a415741bbbac4cdbbbe26fa7edca1f43d2301b982fbf4009cc8cf7f", 39208196),
    ("windows", "x64"): ("pandoc-3.14-windows-x86_64.zip", "0144b96e8c7b023fd382ec5ef5bdc475e873f1019d6fa72502492df2c9a94a3b", 43614099),
}
ASSETS[("windows", "arm64")] = ASSETS[("windows", "x64")]
READS = ("odt", "rtf")   # input formats that only Pandoc reads here
MATH = re.compile(r"\$\$.+?\$\$|(?<![\\$\w])\$(?![\s$])[^$\n]+?(?<![\s\\])\$(?![\w$])", re.S)
TIMEOUT = 300


def install_dir() -> Path:
    return paths.runtime() / "pandoc"


def binary() -> tuple[Path | None, str | None]:
    own = install_dir()
    return find_program("pandoc", [own / "bin" / exe("pandoc"), own / exe("pandoc")])


def asset() -> tuple[str, str, int]:
    key = platform_key()
    if key not in ASSETS:
        raise ToolError(t("tool_unsupported", name="Pandoc", machine="-".join(key)))
    return ASSETS[key]


def status() -> dict:
    program, source = binary()
    try:
        size = asset()[2]
    except ToolError:
        size = None
    return {"id": "pandoc", "name": "Pandoc", "installed": program is not None, "source": source,
            "path": str(program) if program else None, "version": program_version(program),
            "pinned_version": VERSION, "size": dir_size(install_dir()), "download_size": size,
            "install_dir": str(install_dir()), "disk_free": disk_free(install_dir())}


def install() -> Path:
    name, sha256, _ = asset()
    print(t("tool_downloading", name="Pandoc", version=VERSION, file=name), flush=True)
    install_archive(f"{RELEASE}/{name}", sha256, install_dir())
    program, source = binary()
    if program is None or source != "mehteran":
        raise ToolError(t("tool_install_failed", name="Pandoc"))
    program.chmod(0o755)
    print(t("tool_installed", name="Pandoc", version=program_version(program) or VERSION, path=program), flush=True)
    return program


def has_math(markdown: str) -> bool:
    return bool(MATH.search(markdown))


def _run(args: list[str], abort: threading.Event | None, name: str) -> None:
    program, _ = binary()
    if program is None:
        raise ToolError(t("pandoc_missing"))
    code, errors = run([str(program), "--sandbox", *args], abort, TIMEOUT)
    if code != 0:
        raise ToolError(t("pandoc_failed", name=name, error=errors.strip()[-400:]))


def export(markdown: str, fmt: str, title: str, lang: str, abort: threading.Event | None = None) -> bytes:
    """A docx or epub file of a Markdown text."""
    from pipeline.export import is_rtl
    with tempfile.TemporaryDirectory(prefix="mehteran-pandoc-") as tmp:
        source, out = Path(tmp) / "document.md", Path(tmp) / f"document.{fmt}"
        source.write_text(markdown, encoding="utf-8")
        meta = ["--metadata", f"lang={lang}"] + (["--metadata", "dir=rtl"] if is_rtl(lang) else [])
        if fmt == "epub":
            meta += ["--metadata", f"title={title}"]  # an EPUB needs a title
        # Markdown as Mehteran's own exporters read it: a line break inside a paragraph stays a line break.
        _run(["--from", "markdown+hard_line_breaks", "--to", fmt, *meta, "--output", str(out), str(source)], abort, out.name)
        return out.read_bytes()


def read(path: Path, abort: threading.Event | None = None) -> str:
    """The text of a document as Markdown (tables become Markdown tables)."""
    fmt = path.suffix.lower().lstrip(".")
    with tempfile.TemporaryDirectory(prefix="mehteran-pandoc-") as tmp:
        out = Path(tmp) / "document.md"
        _run(["--from", fmt, "--to", "gfm-raw_html", "--wrap=none", "--output", str(out), str(path)], abort, path.name)
        return out.read_text(encoding="utf-8", errors="replace")
