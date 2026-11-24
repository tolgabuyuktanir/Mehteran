"""PDF export with Typst: the Markdown of a workflow becomes Typst markup, and the typst program makes the PDF.

- Finding it: Mehteran's own copy in <code folder>/.runtime/typst first, then PATH.
- Installing it: only when the user asks (the Setup tab, `mehter install-local typst`). The official release archive
  of a pinned version is downloaded from GitHub and checked against the SHA-256 sum written below (the sums were
  computed from the downloaded files and match GitHub's own asset digests). Typst brings its own Latin fonts
  (Libertinus Serif, New Computer Modern, DejaVu Sans Mono: Turkish is covered); for the Arabic script the Amiri font
  (SIL Open Font License) is downloaded the same way into .runtime/typst/fonts. Other scripts (Chinese, Japanese,
  Hebrew...) use the computer's own fonts when it has them.
- Converting: headings, paragraphs, bullet and numbered lists (nested), quotes, code blocks, tables, rules, bold,
  italic, strike-through, inline code, links and footnotes. Every piece of text goes into the Typst file as a string
  (#"..."), so no character of the text can act as Typst markup or code. LaTeX math stays as text.
"""

from __future__ import annotations

import re
import tempfile
import threading
from pathlib import Path

from . import paths, tables
from .i18n import t
from .localtools import ToolError, dir_size, disk_free, exe, find_program, install_archive, platform_key, program_version, run

VERSION = "0.15.1"
RELEASE = f"https://github.com/typst/typst/releases/download/v{VERSION}"
# (system, machine) -> (asset, SHA-256, size) of release v0.15.1.
ASSETS = {
    ("darwin", "arm64"): ("typst-aarch64-apple-darwin.tar.xz", "48f62ed034aa3a7978309579ac6ca00045e2ef0da73114e8af27cfd8e74dc05a", 14438168),
    ("darwin", "x64"): ("typst-x86_64-apple-darwin.tar.xz", "7f9fdd9584866245de9a79e0add8f9236fae6f40a8a45e2c4771ccc14db4e0fa", 15635600),
    ("linux", "x64"): ("typst-x86_64-unknown-linux-musl.tar.xz", "a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c", 17462992),
    ("linux", "arm64"): ("typst-aarch64-unknown-linux-musl.tar.xz", "5aa8d74a3d906e60ea12a66ac2f37f8eef1b14cbad7182a745e393a10c23dcee", 16216812),
    ("windows", "x64"): ("typst-x86_64-pc-windows-msvc.zip", "19ce3551153c2fe7ee9fa2f95208310c8f4d3209fedb699e0333faf8913f6736", 22463684),
    ("windows", "arm64"): ("typst-aarch64-pc-windows-msvc.zip", "4ab28e1b71ec3184d38d580ab797f499b6770d952b6b19167be5cea5c2662e14", 21246627),
}
FONT_URL = "https://github.com/aliftype/amiri/releases/download/1.003/Amiri-1.003.zip"
FONT_SHA256 = "81af0aff7d2086d8af24cea7202f7546130997982534691373485cd96744d05e"
FONT_SIZE = 1033533
TIMEOUT = 300  # seconds for one PDF


def install_dir() -> Path:
    return paths.runtime() / "typst"


def fonts_dir() -> Path:
    return install_dir() / "fonts"


def binary() -> tuple[Path | None, str | None]:
    return find_program("typst", [install_dir() / exe("typst")])


def asset() -> tuple[str, str, int]:
    key = platform_key()
    if key not in ASSETS:
        raise ToolError(t("tool_unsupported", name="Typst", machine="-".join(key)))
    return ASSETS[key]


def status() -> dict:
    program, source = binary()
    try:
        size = asset()[2] + FONT_SIZE
    except ToolError:
        size = None
    return {"id": "typst", "name": "Typst", "installed": program is not None, "source": source,
            "path": str(program) if program else None, "version": program_version(program),
            "pinned_version": VERSION, "size": dir_size(install_dir()), "download_size": size,
            "arabic_font": any(fonts_dir().glob("*.ttf")), "install_dir": str(install_dir()),
            "disk_free": disk_free(install_dir())}


def install() -> Path:
    """Typst VERSION and the Amiri font into .runtime/typst. Output goes to stdout (the job log)."""
    name, sha256, _ = asset()
    print(t("tool_downloading", name="Typst", version=VERSION, file=name), flush=True)
    install_archive(f"{RELEASE}/{name}", sha256, install_dir())
    print(t("tool_downloading", name="Amiri", version="1.003", file=FONT_URL.rsplit("/", 1)[-1]), flush=True)
    install_archive(FONT_URL, FONT_SHA256, fonts_dir())
    program = install_dir() / exe("typst")
    if not program.is_file():
        raise ToolError(t("tool_install_failed", name="Typst"))
    program.chmod(0o755)
    print(t("tool_installed", name="Typst", version=program_version(program) or VERSION, path=program), flush=True)
    return program


# --- Markdown -> Typst ------------------------------------------------------------------

_CONTROL = re.compile("[\x00-\x08\x0b-\x1f\x7f]")
_INLINE = re.compile(
    r"`([^`\n]+)`"                                                    # 1 code
    r"|\[\^([^\]\s]{1,40})\]"                                         # 2 footnote mark
    r"|!?\[([^\]\n]*)\]\(<?([^)\s>]+)>?(?:\s+\"[^\"\n]*\")?\)"       # 3, 4 link (an image: its text and link)
    r"|<((?:https?://|mailto:)[^>\s]+)>"                              # 5 autolink
    r"|\*\*(?!\s)(.+?)(?<!\s)\*\*|__(?!\s)(.+?)(?<!\s)__"             # 6, 7 bold
    r"|(?<![\w*\\])\*(?![\s*])(.+?)(?<![\s\\])\*(?![\w*])"           # 8 italic
    r"|(?<![\w_\\])_(?![\s_])(.+?)(?<!\s)_(?![\w_])"                  # 9 italic
    r"|~~(?!\s)(.+?)(?<!\s)~~")                                       # 10 strike-through
_NOTE_LINE = re.compile(r"^\[\^([^\]\s]{1,40})\]:\s?(.*)$")
_LIST = re.compile(r"^( *)([-*+]|\d{1,9}[.)])\s+(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_RULE = re.compile(r"^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([\w+#.-]*)")
SAFE_LINK = re.compile(r"(https?://|mailto:)[^\s\"\\]+\Z")


def string(text: str) -> str:
    """A Typst string literal: shown as it is, never read as markup."""
    text = _CONTROL.sub("", text.replace("\t", "    "))
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


class _Converter:
    def __init__(self, markdown: str, rtl_doc: bool):
        self.rtl_doc = rtl_doc
        lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.notes = {}
        kept = []
        fence = False
        for line in lines:  # footnote texts, wherever they stand ("[^1]: text"), outside code blocks
            if _FENCE.match(line):
                fence = not fence
            m = None if fence else _NOTE_LINE.match(line.strip())
            if m:
                self.notes[m.group(1)] = m.group(2)
            else:
                kept.append(line)
        self.text, self.tables = tables.extract("\n".join(kept))

    # inline text
    def inline(self, text: str, notes: bool = True) -> str:
        out, pos = [], 0
        for m in _INLINE.finditer(text):
            if m.start() > pos:
                out.append(self.plain(text[pos:m.start()]))
            pos = m.end()
            code, note, label, url, auto, bold1, bold2, ital1, ital2, strike = m.groups()
            if code is not None:
                out.append(f"#raw({string(code)})")
            elif note is not None:
                if notes and note in self.notes:
                    out.append(f"#footnote[{self.inline(self.notes[note], notes=False)}]")
                else:
                    out.append(f"#{string(m.group(0))}")
            elif url is not None or auto is not None:
                target = url if url is not None else auto
                shown = self.inline(label, notes) if label else f"#{string(target)}"
                out.append(f"#link({string(target)})[{shown}]" if SAFE_LINK.match(target) else shown)
            elif bold1 is not None or bold2 is not None:
                out.append(f"#strong[{self.inline(bold1 if bold1 is not None else bold2, notes)}]")
            elif ital1 is not None or ital2 is not None:
                out.append(f"#emph[{self.inline(ital1 if ital1 is not None else ital2, notes)}]")
            else:
                out.append(f"#strike[{self.inline(strike, notes)}]")
        if pos < len(text):
            out.append(self.plain(text[pos:]))
        return "".join(out)

    @staticmethod
    def plain(text: str) -> str:
        text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|~>])", r"\1", text)  # Markdown escapes
        parts = text.split("\n")
        return "#linebreak()".join(f"#{string(p)}" if p else "" for p in parts)

    # blocks
    def blocks(self, text: str) -> list[str]:
        lines = text.split("\n")
        out, i = [], 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            fence = _FENCE.match(line)
            if fence:
                mark, lang = fence.group(1), fence.group(2)
                body, i = [], i + 1
                while i < len(lines) and not lines[i].strip().startswith(mark):
                    body.append(lines[i])
                    i += 1
                i += 1
                lang_arg = f", lang: {string(lang)}" if re.fullmatch(r"[\w+#.-]{1,20}", lang or "") else ""
                out.append(f"#raw({string(chr(10).join(body))}, block: true{lang_arg})")
                continue
            if line.strip() in self.tables:
                out.append(self.table(self.tables[line.strip()]))
                i += 1
                continue
            heading = _HEADING.match(line)
            if heading:
                out.append(f"#heading(level: {len(heading.group(1))})[{self.inline(heading.group(2))}]")
                i += 1
                continue
            if _RULE.match(line):
                out.append("#line(length: 100%, stroke: 0.5pt + gray)")
                i += 1
                continue
            if line.lstrip().startswith(">"):
                body = []
                while i < len(lines) and lines[i].lstrip().startswith(">"):
                    body.append(re.sub(r"^\s*> ?", "", lines[i]))
                    i += 1
                out.append("#quote(block: true)[\n" + "\n\n".join(self.blocks("\n".join(body))) + "\n]")
                continue
            if _LIST.match(line):
                items = []
                while i < len(lines) and lines[i].strip():
                    item = _LIST.match(lines[i])
                    if item:
                        items.append([len(item.group(1)), item.group(2), item.group(3)])
                    elif items and not _HEADING.match(lines[i]) and not _FENCE.match(lines[i]):
                        items[-1][2] += "\n" + lines[i].strip()  # a continued item
                    else:
                        break
                    i += 1
                out.append(self.list(items))
                continue
            body = []
            while i < len(lines) and lines[i].strip() and not (
                    _FENCE.match(lines[i]) or _HEADING.match(lines[i]) or _RULE.match(lines[i])
                    or lines[i].strip() in self.tables or lines[i].lstrip().startswith(">")
                    or (body and _LIST.match(lines[i]))):
                body.append(lines[i].strip())
                i += 1
            if not body:  # a line that looks like a list marker without a list
                body, i = [line.strip()], i + 1
            out.append(self.paragraph("\n".join(body)))
        return out

    def paragraph(self, text: str) -> str:
        from .common.export import mostly_rtl
        content = self.inline(text)
        if not self.rtl_doc and mostly_rtl(text):  # an Arabic passage in a left-to-right text
            return f'#block(width: 100%)[#set text(dir: rtl, lang: "ar")\n{content}]'
        return content

    def list(self, items: list) -> str:
        lines, stack = [], []  # stack: the indent of each open level
        for indent, marker, text in items:
            while stack and indent < stack[-1]:
                stack.pop()
            if not stack or indent > stack[-1]:
                stack.append(indent)
            mark = "-" if marker in "-*+" else f"{marker[:-1]}."
            lines.append("  " * (len(stack) - 1) + f"{mark} {self.inline(text)}")
        return "\n".join(lines)

    def table(self, table: dict) -> str:
        rows = table["rows"]
        width = max(len(r) for r in rows)
        align = [{"center": "center", "right": "end"}.get(table["align"][c] if c < len(table["align"]) else "", "start")
                 for c in range(width)]
        cells = lambda row: ", ".join(f"[{self.inline(row[c] if c < len(row) else '')}]" for c in range(width))  # noqa: E731
        body = "".join(f",\n  {cells(row)}" for row in rows[1:])
        return (f"#table(columns: {width}, align: ({', '.join(align)},),\n"
                f"  table.header({cells(rows[0])}){body})")


def to_typst(markdown: str, title: str, lang: str) -> str:
    """The Typst source of a document."""
    from .common.export import is_rtl
    language, _, region = (lang or "en").partition("-")
    region_arg = f", region: {string(region)}" if re.fullmatch(r"[A-Za-z]{2}", region) else ""
    converter = _Converter(markdown, is_rtl(lang))
    body = "\n\n".join(converter.blocks(converter.text))
    return (f"#set document(title: {string(title)})\n"
            '#set page(paper: "a4", margin: (x: 2.3cm, y: 2.4cm), numbering: "1")\n'
            f'#set text(font: ("Libertinus Serif", "Amiri"), size: 11pt, lang: {string(language)}{region_arg})\n'
            "#set par(justify: true, leading: 0.7em)\n"
            '#show raw: set text(font: "DejaVu Sans Mono", size: 9pt)\n'
            "#show heading: set block(above: 1.3em, below: 0.7em)\n"
            "#set table(stroke: 0.5pt + gray, inset: 5pt)\n"
            "#show table.cell.where(y: 0): strong\n"
            "#show link: underline\n\n" + body + "\n")


def to_pdf(markdown: str, title: str, lang: str, abort: threading.Event | None = None) -> bytes:
    """The PDF of a Markdown text. Raises ToolError when Typst is missing or fails, InterruptedError on a cancel."""
    program, _ = binary()
    if program is None:
        raise ToolError(t("typst_missing"))
    with tempfile.TemporaryDirectory(prefix="mehteran-typst-") as tmp:
        source, out = Path(tmp) / "document.typ", Path(tmp) / "document.pdf"
        source.write_text(to_typst(markdown, title, lang), encoding="utf-8")
        argv = [str(program), "compile", "--root", tmp]
        if fonts_dir().is_dir():
            argv += ["--font-path", str(fonts_dir())]
        code, errors = run(argv + [str(source), str(out)], abort, TIMEOUT)
        if code != 0 or not out.is_file():
            raise ToolError(t("typst_failed", error=errors.strip()[-400:]))
        return out.read_bytes()
