"""Exports Markdown to Word (.docx) and HTML (the HTML is also used for PDF printing).

Only this Markdown is supported: headings (#), paragraphs, "- " lists, "> " quotes,
**bold**, *italic*, `code`, and footnotes as a "[^n]" mark plus a "[^n]: text" line in the same block.
No third-party packages are used.
"""

from __future__ import annotations

import html
import io
import re
import zipfile
from xml.sax.saxutils import escape as xml_escape

from . import figure

RTL_LANGUAGES = {"ar", "fa", "ur", "he", "ps", "sd", "ug", "yi", "ckb", "dv"}
_NOTE_LINE = re.compile(r"^\[\^(\d+)\]:\s?(.*)$")
_INLINE = re.compile(r"\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|`([^`]+)`|\[\^(\d+)\]")
_XML_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


# The layout of an exported book (the report always has the standard layout). Fonts "" mean the built-in lists.
PAGE_SIZES = {"A4": (210, 297), "A5": (148, 210), "B5": (176, 250), "13.5x21": (135, 210), "16x24": (160, 240),
              "Letter": (215.9, 279.4)}
DEFAULT_LAYOUT = {"page_size": "A4", "margin_top": 2.5, "margin_bottom": 2.5, "margin_side": 2.5, "font": "",
                  "arabic_font": "", "font_size": 12.0, "line_spacing": 1.15, "justify": True, "chapter_new_page": True}
# The allowed range of each number, and the characters a font name cannot contain (it goes into CSS and XML).
LIMITS = {"margin_top": (0.5, 5.0), "margin_bottom": (0.5, 5.0), "margin_side": (0.5, 5.0), "font_size": (8.0, 16.0),
          "line_spacing": (1.0, 3.0)}
FONT_RE = re.compile(r"^[^\"'<>;{}\\&]{0,60}$")


def layout_problem(values: dict) -> str | None:
    """The first invalid key of a layout, or None."""
    for key, default in DEFAULT_LAYOUT.items():
        value = values.get(key, default)
        if key == "page_size":
            ok = value in PAGE_SIZES
        elif isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, float):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool) and LIMITS[key][0] <= value <= LIMITS[key][1]
        else:
            ok = isinstance(value, str) and bool(FONT_RE.match(value))
        if not ok:
            return key
    return None


def layout(values: dict | None) -> dict:
    """The layout of config.toml [export]; a missing or invalid value takes its default."""
    out = dict(DEFAULT_LAYOUT)
    for key, value in (values or {}).items():
        if key not in out:
            continue
        if isinstance(out[key], float) and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if layout_problem({key: value}) is None:
            out[key] = value
    return out


def is_rtl(lang: str) -> bool:
    return lang.split("-")[0] in RTL_LANGUAGES


# --- parsing ------------------------------------------------------------------

def inlines(text: str) -> list[tuple[str, str]]:
    """Splits text into (kind, text) parts: text, bold, italic, code, note."""
    parts, pos = [], 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            parts.append(("text", text[pos:m.start()]))
        if m.group(1) is not None:
            parts.append(("bold", m.group(1)))
        elif m.group(2) is not None:
            parts.append(("italic", m.group(2)))
        elif m.group(3) is not None:
            parts.append(("code", m.group(3)))
        else:
            parts.append(("note", m.group(4)))
        pos = m.end()
    if pos < len(text):
        parts.append(("text", text[pos:]))
    return parts


def _report_blocks(markdown: str) -> list[dict]:
    """Read report structure line by line, including compact Markdown from model outputs."""
    blocks, notes = [], {}
    fence = ""
    for line in markdown.splitlines():
        stripped = line.strip()
        if fence:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", stripped):
                fence = ""
            else:
                blocks[-1]["lines"].append(line)
            continue
        opener = re.match(r"^(`{3,}|~{3,})\s*([^\s`]*)", stripped)
        if opener:
            fence = opener[1]
            blocks.append({"type": "code", "lang": opener[2], "lines": []})
            continue
        note = _NOTE_LINE.match(stripped)
        if note:
            notes[note[1]] = note[2]
            continue
        if not stripped:
            blocks.append({"type": "break"})
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        bullet = re.match(r"^( *)([-*+])\s+(.+)$", line)
        number = re.match(r"^ *(\d{1,9})[.)]\s+(.+)$", line)
        if heading:
            blocks.append({"type": "heading", "level": len(heading[1]), "lines": [heading[2]]})
        elif bullet:
            blocks.append({"type": "bullet", "level": 1 + len(bullet[1]) // 2, "lines": [bullet[3]]})
        elif number:
            blocks.append({"type": "ordered", "number": int(number[1]), "lines": [number[2]]})
        else:
            kind = "quote" if line.startswith(">") else "para"
            value = line.lstrip("> ") if kind == "quote" else line
            if blocks and blocks[-1]["type"] == kind:
                blocks[-1]["lines"].append(value)
            else:
                blocks.append({"type": kind, "lines": [value]})
    result = []
    for block in blocks:
        if block["type"] != "break":
            block["text"] = "\n".join(block.pop("lines"))
            block["notes"] = notes
            result.append(block)
    return result


def parse(markdown: str, lists: bool = True) -> list[dict]:
    """Returns blocks with a type, text, footnotes, and optional heading or list metadata.

    A footnote text is looked up first in its own block, then in the whole document (a model may have moved
    the "[^n]: text" line to another paragraph). lists=False keeps lines that start with "- " (a dialogue dash in
    a book) as normal paragraphs.
    """
    if lists:
        return _report_blocks(markdown)
    all_notes = {m.group(1): m.group(2) for m in (_NOTE_LINE.match(line.strip()) for line in markdown.splitlines()) if m}
    blocks = []
    for chunk in re.split(r"\n\s*\n", markdown.replace("\r\n", "\n").strip()):
        lines = chunk.split("\n")
        notes = {}
        body = []
        for line in lines:
            m = _NOTE_LINE.match(line.strip())
            if m:
                notes[m.group(1)] = m.group(2)
            else:
                body.append(line)
        if not body:
            continue
        first = body[0]
        heading = re.match(r"^(#{1,6})\s+(.*)$", first)
        notes = {**all_notes, **notes}
        if heading and len(body) == 1:
            blocks.append({"type": "heading", "level": len(heading.group(1)), "text": heading.group(2), "notes": notes})
        elif all(line.startswith(">") for line in body):
            blocks.append({"type": "quote", "text": "\n".join(line.lstrip("> ") for line in body), "notes": notes})
        else:
            blocks.append({"type": "para", "text": "\n".join(body), "notes": notes})
    return blocks


# --- HTML ---------------------------------------------------------------------

_RTL = "֐-ࣿיִ-﷿ﹰ-ﻼ"
_RTL_RUN = re.compile(f"[{_RTL}][{_RTL}\\sً-ٰٟ.,:;!?()«»\"'،؛؟-]*[{_RTL}ً-ٰٟ]|[{_RTL}]")


def mostly_rtl(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if re.match(f"[{_RTL}]", c)) > len(letters) / 2


# The report's look: sans-serif headings in the Mehteran blue, answer choices as a grid of boxes, framed figures.
_SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif'
REPORT_CSS = f"""  .report {{ max-width: 40em; }}
  .report :is(h1, h2, h3, h4) {{ font-family: {_SANS}; color: #11213e; letter-spacing: -.01em; }}
  .report h1 {{ font-size: 1.9em; margin: .3em 0 1.1em; padding-bottom: .45em; border-bottom: 3px solid #2151af; }}
  .report h2 {{ font-size: 1.22em; margin: 2em 0 .8em; padding-top: 1em; border-top: 1px solid #e3e7ef; }}
  .report h1 + h2 {{ border-top: 0; padding-top: 0; margin-top: 0; }}
  .report h3 {{ font-size: 1.04em; color: #2151af; margin: 1.6em 0 .5em; }}
  .report blockquote {{ background: #f5f7fb; border-inline-start-color: #2151af; padding: .5em 1em; border-radius: 0 8px 8px 0; }}
  .choices {{ list-style: none; padding: 0; margin: .5em 0 1.2em; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
             gap: .45em .9em; break-inside: avoid; page-break-inside: avoid; }}
  .choices.wide {{ grid-template-columns: 1fr; }}
  .choices li {{ display: flex; gap: .65em; align-items: baseline; margin: 0; padding: .45em .75em; border: 1px solid #dfe4ee;
                border-radius: 8px; background: #fafbfd; }}
  .choices .letter {{ flex: none; display: inline-grid; place-items: center; width: 1.7em; height: 1.7em; border-radius: 50%;
                     background: #e6edfb; color: #2151af; font: 600 .78em/1 {_SANS}; }}
  .fig-box {{ margin: .8em 0 1.2em; padding: .9em; border: 1px solid #e3e7ef; border-radius: 10px; background: #fbfcfe;
             text-align: center; break-inside: avoid; page-break-inside: avoid; }}
  .fig-box svg {{ max-width: 100%; height: auto; font: 12px {_SANS}; }}
  .fig-box figcaption {{ font: .85em {_SANS}; color: #5a6475; margin-top: .4em; }}
  .fig .fig-grid {{ stroke: #e3e7ef; stroke-width: 1; fill: none; }}
  .fig .fig-axis {{ stroke: #161f30; stroke-width: 1.3; fill: none; }}
  .fig .fig-arrow {{ fill: #161f30; }}
  .fig .fig-tick {{ fill: #5a6475; font-size: 11px; }}
  .fig .fig-label {{ fill: #161f30; font-style: italic; font-size: 13px; }}
  .fig .fig-line {{ fill: none; stroke-width: 2.2; stroke-linejoin: round; stroke-linecap: round; }}
  .fig .fig-dash {{ stroke-dasharray: 6 5; }}
  .fig .fig-text {{ fill: #161f30; font-size: 13px; font-weight: 600; paint-order: stroke; stroke: #fbfcfe; stroke-width: 3px; }}
  .fig .fig-bar {{ fill: #2151af; opacity: .85; }}
  .fig .fig-value {{ fill: #161f30; font-size: 11px; font-weight: 600; }}
  .fig .fig-fill {{ fill-opacity: .12; }}
""" + "".join(f"  .fig .fig-c{n} {{ stroke: {c}; }} .fig :is(.fig-t{n}, .fig-d{n}, .fig-f{n}) {{ fill: {c}; }}\n"
              for n, c in enumerate(("#2151af", "#b6322b", "#1c6d51", "#5b4a9e")))

_CHOICE = re.compile(r"^\(?([A-F])[).]\s+(.+)$")


def _choices(text: str) -> list[tuple[str, str]] | None:
    """The answer choices of a paragraph whose lines are "A) ...", "B) ..." in order (2 to 6 lines), or None."""
    lines = text.split("\n")
    found = [_CHOICE.match(line.strip()) for line in lines]
    if not 2 <= len(lines) <= 6 or not all(found):
        return None
    if [m[1] for m in found] != list("ABCDEF"[:len(lines)]):
        return None
    return [(m[1], m[2]) for m in found]


BOOK_FONTS = '"Charis SIL", "Noto Serif", "Gentium Plus", "Times New Roman", Georgia, serif'
ARABIC_FONTS = '"Noto Naskh Arabic", "Amiri", "Scheherazade New", "Geeza Pro", "Traditional Arabic", "Times New Roman", serif'


def to_html(markdown: str, title: str, lang: str, print_on_load: bool = False, lists: bool = True,
            book_layout: dict | None = None) -> str:
    """A page for reading and printing. A book (lists=False) gets book typesetting: justified and hyphenated text,
    indented paragraphs, each top-level chapter on a new page, its notes at its end, page numbers when printed.
    Arabic-script passages in a left-to-right text are set right to left in an Arabic typeface."""
    rtl_doc = is_rtl(lang)
    direction = "rtl" if rtl_doc else "ltr"
    body: list[str] = []
    footnotes: list[str] = []
    shown = 0  # footnotes already written

    def text_html(value: str) -> str:
        value = html.escape(value)
        if not rtl_doc:  # Arabic inside a left-to-right paragraph
            value = _RTL_RUN.sub(lambda m: f'<span class="ar" dir="rtl" lang="ar">{m.group(0)}</span>', value)
        return value.replace("\n", "<br>")

    def render(text: str, notes: dict) -> str:
        out = []
        for kind, value in inlines(text):
            if kind == "note":
                if value in notes:
                    footnotes.append(notes[value])
                    n = len(footnotes)
                    out.append(f'<sup class="fn"><a href="#fn{n}" id="ref{n}">{n}</a></sup>')
                else:
                    out.append(html.escape(f"[^{value}]"))
                continue
            value = text_html(value)
            out.append({"bold": f"<strong>{value}</strong>", "italic": f"<em>{value}</em>",
                        "code": f"<code>{value}</code>"}.get(kind, value))
        return "".join(out)

    def notes_html() -> None:
        nonlocal shown
        if len(footnotes) > shown:
            items = "".join(f'<li id="fn{i}">{render(note, {})} <a class="back" href="#ref{i}" aria-label="↩">↩</a></li>'
                            for i, note in enumerate(footnotes[shown:], shown + 1))
            body.append(f'<ol class="notes" start="{shown + 1}">{items}</ol>')
            shown = len(footnotes)

    blocks = parse(markdown, lists)
    top = min((b["level"] for b in blocks if b["type"] == "heading"), default=None)
    in_list = ""
    for block in blocks:
        list_tag = {"ordered": "ol", "bullet": "ul"}.get(block["type"], "")
        if in_list and list_tag != in_list:
            body.append(f"</{in_list}>")
            in_list = ""
        if block["type"] == "heading" and block["level"] == top and not lists:
            notes_html()  # the notes of a chapter stand at its end
        if block["type"] == "code":
            spec = figure.load(block["text"]) if block.get("lang") == "figure" else None
            if spec is not None:
                caption = figure.caption(spec)
                body.append('<figure class="fig-box">' + figure.serialize(figure.tree(spec))
                            + (f"<figcaption>{html.escape(caption)}</figcaption>" if caption else "") + "</figure>")
            else:
                body.append("<pre><code>" + html.escape(block["text"]) + "</code></pre>")
            continue
        choices = _choices(block["text"]) if lists and block["type"] == "para" else None
        if choices:
            wide = max(len(c) for _, c in choices) > 28
            items = "".join(f'<li><span class="letter">{html.escape(letter)}</span><span>{render(c, block["notes"])}</span></li>'
                            for letter, c in choices)
            body.append(f'<ol class="choices{" wide" if wide else ""}">{items}</ol>')
            continue
        text = render(block["text"], block["notes"])
        if block["type"] == "heading":
            level = min(block["level"], 6)
            body.append(f"<h{level}>{text}</h{level}>")
        elif list_tag:
            if not in_list:
                body.append(f"<{list_tag}>")
                in_list = list_tag
            if list_tag == "ol":
                body.append(f'<li value="{block["number"]}">{text}</li>')
                continue
            body.append(f'<li class="sub">{text}</li>' if block.get("level", 1) > 1 else f"<li>{text}</li>")
        elif block["type"] == "quote":
            body.append(f"<blockquote>{text}</blockquote>")
        elif not rtl_doc and mostly_rtl(block["text"]):
            body.append(f'<p class="ar-p" dir="rtl" lang="ar">{text}</p>')
        elif re.match(r"(\d{1,3}|[a-zA-Z]|[ivxlcdm]{1,6})[.)]\s|[•–—-]\s", block["text"]):
            body.append(f'<p class="item">{text}</p>')  # a numbered item or a dialogue line: not indented
        else:
            body.append(f"<p>{text}</p>")
    if in_list:
        body.append(f"</{in_list}>")
    notes_html()

    script = "<script>window.addEventListener('load', () => setTimeout(() => window.print(), 300));</script>" if print_on_load else ""
    if lists:  # the report: the standard layout
        fonts, arabic, size, line, page, chapter, align = BOOK_FONTS, ARABIC_FONTS, 12, 1.55, "A4; margin: 2.2cm 2.3cm 2.6cm", "", "justify"
    else:
        lay = layout(book_layout)
        fonts = f'"{lay["font"]}", {BOOK_FONTS}' if lay["font"] else BOOK_FONTS
        arabic = f'"{lay["arabic_font"]}", {ARABIC_FONTS}' if lay["arabic_font"] else ARABIC_FONTS
        size, line = lay["font_size"], round(lay["line_spacing"] * 1.35, 2)  # a Word line is taller than a CSS line
        width, height = PAGE_SIZES[lay["page_size"]]
        page = f'{width}mm {height}mm; margin: {lay["margin_top"]}cm {lay["margin_side"]}cm {lay["margin_bottom"]}cm'
        chapter = ".book h1:not(:first-child) { break-before: page; page-break-before: always; }" if lay["chapter_new_page"] else ""
        align = "justify" if lay["justify"] else "start"
    page_number = "" if lists else "@bottom-center { content: counter(page); font: 10pt " + fonts.replace('"', "'") + "; }"
    return f"""<!doctype html>
<html lang="{html.escape(lang)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: {fonts}; font-size: {size}pt; line-height: {line}; color: #1b1b1b; background: #fff;
         max-width: 36em; margin: 2.5em auto; padding: 0 1.2em; -webkit-hyphens: auto; hyphens: auto; }}
  h1, h2, h3, h4 {{ line-height: 1.25; font-weight: 600; break-after: avoid; page-break-after: avoid; -webkit-hyphens: manual; hyphens: manual; }}
  h1 {{ font-size: 1.55em; margin: 1.2em 0 1em; }}
  h2 {{ font-size: 1.25em; margin: 1.6em 0 .6em; }}
  h3 {{ font-size: 1.08em; margin: 1.3em 0 .4em; }}
  p {{ margin: 0 0 .7em; orphans: 3; widows: 3; }}
  .book h1 {{ text-align: center; }}
  {chapter}
  .book p {{ margin: 0; text-align: {align}; text-indent: 1.4em; }}
  .book :is(h1, h2, h3, h4, h5, h6, blockquote, .ar-p, ol, ul) + p, .book p:first-child, .book p.item {{ text-indent: 0; }}
  .book p.item {{ text-align: start; }}
  li {{ margin-bottom: .2em; }}
  li.sub {{ list-style: circle; margin-inline-start: 1.6em; }}
  blockquote {{ margin: .6em 0; padding-inline-start: 1em; border-inline-start: 3px solid #bbb; color: #333; }}
  .ar, [lang="ar"] {{ font-family: {arabic}; font-size: 1.18em; line-height: 1.7; }}
  .ar-p, .book .ar-p {{ text-align: center; text-indent: 0; margin: .5em 0 .6em; }}
  sup.fn {{ line-height: 0; }}
  sup.fn a {{ text-decoration: none; color: inherit; }}
  .notes {{ font-size: 10pt; line-height: 1.4; margin: 1.6em 0 1.2em; padding: .6em 0 0 1.6em; border-top: .5pt solid #888; text-align: start; }}
  .notes li {{ margin-bottom: .25em; }}
  .notes .back {{ text-decoration: none; color: #888; }}
  pre {{ overflow-x: auto; }}
  code {{ font-family: Menlo, Consolas, monospace; font-size: 10pt; }}
{REPORT_CSS if lists else ""}
  @page {{ size: {page}; {page_number} }}
  @media print {{ body {{ max-width: none; margin: 0; padding: 0; }} a {{ color: inherit; }} .notes .back {{ display: none; }} }}
</style>
{script}
</head>
<body class="{"report" if lists else "book"}">
{chr(10).join(body)}
</body>
</html>
"""


# --- DOCX ---------------------------------------------------------------------

def _x(text: str) -> str:
    return xml_escape(_XML_INVALID.sub("", text))


def _runs(text: str, rtl: bool, base: str = "") -> str:
    """Word runs of a text. In a left-to-right document an Arabic-script passage is a right-to-left run of its own."""
    out = []
    for i, line in enumerate(text.split("\n")):
        if i:
            out.append("<w:r><w:br/></w:r>")
        pieces, pos = [], 0
        for m in ([] if rtl else _RTL_RUN.finditer(line)):
            pieces += [(line[pos:m.start()], False), (m.group(0), True)]
            pos = m.end()
        pieces.append((line[pos:], rtl))
        for piece, piece_rtl in pieces:
            if piece:
                tag = "<w:rtl/>" if piece_rtl else ""
                out.append(f'<w:r><w:rPr>{base}{tag}</w:rPr><w:t xml:space="preserve">{_x(piece)}</w:t></w:r>')
    return "".join(out)




W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DOC_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
NOTES_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
# The styles that the document uses, by their built-in Word name (a template names its style ids in its own language).
STYLE_NAMES = {"Heading1": "heading 1", "Heading2": "heading 2", "Heading3": "heading 3", "Quote": "Quote",
               "ListBullet": "List Bullet", "ListBullet2": "List Bullet 2", "FootnoteText": "footnote text",
               "FootnoteReference": "footnote reference"}
TEMPLATE_LIMIT = 20 * 1024 * 1024        # the uploaded file
TEMPLATE_UNPACKED_LIMIT = 80 * 1024 * 1024  # all its parts unpacked


def _twips(cm: float) -> int:
    return round(cm * 567)


def _docx_body(markdown: str, lang: str, lists: bool, ids: dict, first_note: int) -> tuple[str, list[str]]:
    """The paragraphs of the document and the <w:footnote> elements of its notes (numbered from first_note)."""
    rtl = is_rtl(lang)
    footnotes: list[str] = []

    def content(text: str, notes: dict) -> str:
        out = []
        for kind, value in inlines(text):
            if kind == "note":
                if value in notes:
                    footnotes.append(notes[value])
                    out.append(f'<w:r><w:rPr><w:rStyle w:val="{ids["FootnoteReference"]}"/></w:rPr>'
                               f'<w:footnoteReference w:id="{first_note + len(footnotes) - 1}"/></w:r>')
                else:
                    out.append(_runs(f"[^{value}]", rtl))
                continue
            style = {"bold": "<w:b/><w:bCs/>", "italic": "<w:i/><w:iCs/>",
                     "code": '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'}.get(kind, "")
            out.append(_runs(value, rtl, style))
        return "".join(out)

    bidi = "<w:bidi/>" if rtl else ""
    paragraphs = []
    for block in parse(markdown, lists):
        if block["type"] == "heading":
            style = f"Heading{min(block['level'], 3)}"
        else:
            style = {"bullet": "ListBullet2" if block.get("level", 1) > 1 else "ListBullet", "quote": "Quote"}.get(block["type"])
        style_xml = f'<w:pStyle w:val="{ids[style]}"/>' if style else ""
        if not rtl and block["type"] == "para" and mostly_rtl(block["text"]):
            props = f'<w:pPr>{style_xml}<w:bidi/><w:jc w:val="center"/></w:pPr>'  # an Arabic passage (âyet, hadîs)
        else:
            props = f"<w:pPr>{style_xml}{bidi}</w:pPr>"
        text = ({1: "• ", 2: "◦ "}.get(block.get("level", 1), "◦ ") if block["type"] == "bullet" else "") + block["text"]
        if block["type"] == "ordered":
            text = f"{block['number']}. {text}"
        if block["type"] == "code":
            monospace = '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'
            for line in text.split("\n"):
                paragraphs.append(f"<w:p>{props}{_runs(line, rtl, monospace)}</w:p>")
        else:
            paragraphs.append(f"<w:p>{props}{content(text, block['notes'])}</w:p>")

    # The notes are rendered after the body, so their own marks do not change the numbering above.
    notes = []
    for i, note in enumerate(list(footnotes)):
        notes.append(f'<w:footnote w:id="{first_note + i}"><w:p><w:pPr><w:pStyle w:val="{ids["FootnoteText"]}"/>{bidi}</w:pPr>'
                     f'<w:r><w:rPr><w:rStyle w:val="{ids["FootnoteReference"]}"/></w:rPr><w:footnoteRef/></w:r>'
                     f'<w:r><w:t xml:space="preserve"> </w:t></w:r>{content(note, {})}</w:p></w:footnote>')
    return "".join(paragraphs), notes


def _style_defs(lists: bool, lay: dict) -> dict:
    """Our definition of each style that the document uses, by style id."""
    size = 12.0 if lists else lay["font_size"]
    pt = lambda factor: round(size * factor * 2)  # noqa: E731  (Word sizes are half points)
    chapter_break = "<w:pageBreakBefore/>" if not lists and lay["chapter_new_page"] else ""
    heading = ('<w:style w:type="paragraph" w:styleId="{id}"><w:name w:val="{name}"/><w:basedOn w:val="Normal"/>'
               '<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/>{extra}<w:spacing w:before="{before}" w:after="{after}"/>'
               '<w:jc w:val="{jc}"/><w:outlineLvl w:val="{level}"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="{sz}"/>'
               '<w:szCs w:val="{sz}"/></w:rPr></w:style>')
    return {
        "Heading1": heading.format(id="Heading1", name="heading 1", extra=chapter_break, before=360, after=240, jc="center", level=0, sz=pt(1.42)),
        "Heading2": heading.format(id="Heading2", name="heading 2", extra="", before=280, after=120, jc="left", level=1, sz=pt(1.25)),
        "Heading3": heading.format(id="Heading3", name="heading 3", extra="", before=240, after=120, jc="left", level=2, sz=pt(1.08)),
        "Quote": '<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:right="567"/></w:pPr><w:rPr><w:i/><w:iCs/></w:rPr></w:style>',
        "ListBullet": '<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/><w:ind w:left="360" w:hanging="360"/></w:pPr></w:style>',
        "ListBullet2": '<w:style w:type="paragraph" w:styleId="ListBullet2"><w:name w:val="List Bullet 2"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/><w:ind w:left="720" w:hanging="360"/></w:pPr></w:style>',
        "FootnoteText": f'<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:sz w:val="{pt(10 / 12)}"/><w:szCs w:val="{pt(10 / 12)}"/></w:rPr></w:style>',
        "FootnoteReference": '<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>',
    }


def to_docx(markdown: str, title: str, lang: str, lists: bool = True, book_layout: dict | None = None,
            template: bytes | None = None) -> bytes:
    """A Word document. A book takes the layout of config.toml [export], or the styles, page size, margins, headers
    and footers of the publisher's Word template when one is given; the report always has the standard layout."""
    if template and not lists:
        return _into_template(template, markdown, lang)
    lay = layout(book_layout)
    rtl = is_rtl(lang)
    ids = {key: key for key in STYLE_NAMES}
    body, notes = _docx_body(markdown, lang, lists, ids, 1)
    if lists:
        width, height, top, bottom, side = 210, 297, 2.5, 2.5, 2.5
        font, arabic, size, line, justify = "Times New Roman", "Times New Roman", 12.0, 1.15, False
    else:
        (width, height), top, bottom, side = PAGE_SIZES[lay["page_size"]], lay["margin_top"], lay["margin_bottom"], lay["margin_side"]
        font = lay["font"] or "Times New Roman"
        arabic = lay["arabic_font"] or lay["font"] or "Times New Roman"
        size, line, justify = lay["font_size"], lay["line_spacing"], lay["justify"]
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W_NS} {R_NS}><w:body>{body}'
                f'<w:sectPr><w:footerReference w:type="default" r:id="rId3"/>'
                f'<w:pgSz w:w="{round(width * 56.7)}" w:h="{round(height * 56.7)}"/>'
                f'<w:pgMar w:top="{_twips(top)}" w:right="{_twips(side)}" w:bottom="{_twips(bottom)}" w:left="{_twips(side)}" '
                'w:header="709" w:footer="709" w:gutter="0"/></w:sectPr></w:body></w:document>')
    # The page number in the footer, centred.
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {W_NS}><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
              '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
              '</w:p></w:ftr>')
    # A book is hyphenated automatically in its own language; a report is not.
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {W_NS}>'
                + ("" if lists else "<w:autoHyphenation/>") + '<w:defaultTabStop w:val="708"/></w:settings>')
    footnotes_part = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes {W_NS}>'
                      '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                      '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
                      f'{"".join(notes)}</w:footnotes>')
    lang_attr = _x(lang)
    font, arabic = _x(font), _x(arabic)
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W_NS}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{arabic}"/><w:sz w:val="{round(size * 2)}"/><w:szCs w:val="{round(size * 2) + 2}"/>
<w:lang w:val="{lang_attr}" w:bidi="{lang_attr if rtl else "ar-SA"}"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="{round(line * 240)}" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:widowControl/>{'<w:jc w:val="both"/>' if justify else ""}</w:pPr></w:style>
{chr(10).join(_style_defs(lists, lay).values())}
</w:styles>'''
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="{DOC_TYPE}"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footnotes.xml" ContentType="{NOTES_TYPE}"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="{REL}/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    doc_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="{REL}/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="{REL}/footnotes" Target="footnotes.xml"/>
<Relationship Id="rId3" Type="{REL}/footer" Target="footer1.xml"/>
<Relationship Id="rId4" Type="{REL}/settings" Target="settings.xml"/>
</Relationships>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{_x(title)}</dc:title><dc:language>{lang_attr}</dc:language></cp:coreProperties>'''

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footnotes.xml", footnotes_part)
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/settings.xml", settings)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
    return buffer.getvalue()


# --- Word template --------------------------------------------------------------

def template_problem(data: bytes) -> str | None:
    """Why a file cannot be used as a Word template ("type", "size", "macros" or "broken"), or None."""
    if len(data) > TEMPLATE_LIMIT:
        return "size"
    if not data.startswith(b"PK\x03\x04"):
        return "type"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            if not {"[Content_Types].xml", "word/document.xml", "word/_rels/document.xml.rels"} <= names:
                return "type"
            if sum(i.file_size for i in z.infolist()) > TEMPLATE_UNPACKED_LIMIT:
                return "size"
            if "macroEnabled" in z.read("[Content_Types].xml").decode("utf-8", "replace") or "word/vbaProject.bin" in names:
                return "macros"
        _into_template(data, "# Test\n\nText.[^1]\n\n[^1]: Note.", "en")
    except Exception:  # noqa: BLE001  (any unreadable part makes the file unusable)
        return "broken"
    return None


def _style_ids(styles: str) -> dict:
    """{lower-case style name: style id} of a styles part."""
    out = {}
    for m in re.finditer(r"<w:style\b([^>]*)>(.*?)</w:style>", styles, re.S):
        sid = re.search(r'w:styleId="([^"]*)"', m.group(1))
        name = re.search(r'<w:name w:val="([^"]*)"', m.group(2))
        if sid and name:
            out.setdefault(name.group(1).lower(), sid.group(1))
    return out


def _into_template(template: bytes, markdown: str, lang: str) -> bytes:
    """The book in the publisher's template: its styles, page setup, headers and footers are kept, its body text is
    replaced. A style that the template lacks is added with our definition."""
    with zipfile.ZipFile(io.BytesIO(template)) as z:
        parts = {info.filename: z.read(info) for info in z.infolist() if not info.is_dir()}
    text = lambda name: parts[name].decode("utf-8")  # noqa: E731

    def add_part(name: str, content: str, rel_type: str, content_type: str) -> None:
        """A part that the template lacks, with its relationship and its content type."""
        parts[f"word/{name}"] = content.encode("utf-8")
        rels = text("word/_rels/document.xml.rels")
        end = rels.rindex("</Relationships>")
        rel_id = f"rIdTP{len(parts)}"
        parts["word/_rels/document.xml.rels"] = (
            rels[:end] + f'<Relationship Id="{rel_id}" Type="{REL}/{rel_type}" Target="{name}"/>' + rels[end:]).encode("utf-8")
        types = text("[Content_Types].xml")
        if f'PartName="/word/{name}"' not in types:
            end = types.rindex("</Types>")
            parts["[Content_Types].xml"] = (
                types[:end] + f'<Override PartName="/word/{name}" ContentType="{content_type}"/>' + types[end:]).encode("utf-8")

    if "word/styles.xml" not in parts:  # a valid but bare Word file: our styles are added below
        add_part("styles.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles {W_NS}>'
                 '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>',
                 "styles", "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml")
    styles = text("word/styles.xml")
    known = _style_ids(styles)
    taken = set(known.values())
    ids, missing = {}, []
    ours = _style_defs(False, dict(DEFAULT_LAYOUT, chapter_new_page=False))  # the template decides the chapter breaks
    for key, name in STYLE_NAMES.items():
        if name.lower() in known:
            ids[key] = known[name.lower()]
        else:
            ids[key] = key if key not in taken else f"TP{key}"
            missing.append(ours[key].replace(f'w:styleId="{key}"', f'w:styleId="{ids[key]}"'))
    if missing:
        end = styles.rindex("</w:styles>")
        parts["word/styles.xml"] = (styles[:end] + "".join(missing) + styles[end:]).encode("utf-8")

    # The notes: the template's separators stay, its other notes go; ours are numbered after the separators.
    notes_xml = text("word/footnotes.xml") if "word/footnotes.xml" in parts else None
    kept = re.findall(r"<w:footnote\b[^>]*w:type=\"[^\"]*\"[^>]*>.*?</w:footnote>", notes_xml, re.S) if notes_xml else []
    used = [int(n) for n in re.findall(r'w:id="(-?\d+)"', "".join(kept))]
    body, notes = _docx_body(markdown, lang, False, ids, max(used, default=0) + 1)
    if notes_xml:
        head = re.match(r"(.*?<w:footnotes\b[^>]*>)", notes_xml, re.S).group(1)
        parts["word/footnotes.xml"] = (head + "".join(kept) + "".join(notes) + "</w:footnotes>").encode("utf-8")
    else:
        add_part("footnotes.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes {W_NS}>'
                 '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                 '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
                 f'{"".join(notes)}</w:footnotes>', "footnotes", NOTES_TYPE)
    parts["[Content_Types].xml"] = text("[Content_Types].xml").replace(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml", DOC_TYPE).encode("utf-8")

    # The body: our paragraphs, then the template's page setup (the last section properties of its body).
    document = text("word/document.xml")
    start = re.search(r"<w:body>", document).end()
    end = document.rindex("</w:body>")
    old = document[start:end]
    at = old.rfind("<w:sectPr")
    section = old[at:].strip() if at >= 0 and old[at:].rstrip().endswith(("</w:sectPr>", "/>")) else ""
    parts["word/document.xml"] = (document[:start] + body + section + document[end:]).encode("utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return buffer.getvalue()
