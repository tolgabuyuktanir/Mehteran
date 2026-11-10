"""Exports the Markdown output of the pipeline to Word (.docx) and HTML (the HTML is also used for PDF printing).

Only the Markdown that the pipeline writes is supported: headings (#), paragraphs, "- " lists, "> " quotes,
**bold**, *italic*, `code`, and footnotes as a "[^n]" mark plus a "[^n]: text" line in the same block.
No third-party packages are used.
"""

from __future__ import annotations

import html
import io
import re
import zipfile
from xml.sax.saxutils import escape as xml_escape

RTL_LANGUAGES = {"ar", "fa", "ur", "he", "ps", "sd", "ug", "yi", "ckb", "dv"}
_NOTE_LINE = re.compile(r"^\[\^(\d+)\]:\s?(.*)$")
_INLINE = re.compile(r"\*\*(.+?)\*\*|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|`([^`]+)`|\[\^(\d+)\]")
_XML_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


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


def parse(markdown: str, lists: bool = True) -> list[dict]:
    """Returns blocks: {"type": heading|para|bullet|quote, "level", "text", "notes": {n: text}}.

    A footnote text is looked up first in its own block, then in the whole document (a model may have moved
    the "[^n]: text" line to another paragraph). lists=False keeps lines that start with "- " (a dialogue dash in
    a book) as normal paragraphs.
    """
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
        elif lists and all(re.match(r"\s*- ", line) for line in body) and body[0].startswith("- "):
            for line in body:  # "  - " is an item under the item above it
                indent = len(line) - len(line.lstrip(" "))
                blocks.append({"type": "bullet", "level": 1 + indent // 2, "text": line.lstrip(" ")[2:], "notes": notes})
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


BOOK_FONTS = '"Charis SIL", "Noto Serif", "Gentium Plus", "Times New Roman", Georgia, serif'
ARABIC_FONTS = '"Noto Naskh Arabic", "Amiri", "Scheherazade New", "Geeza Pro", "Traditional Arabic", "Times New Roman", serif'


def to_html(markdown: str, title: str, lang: str, print_on_load: bool = False, lists: bool = True) -> str:
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
    in_list = False
    for block in blocks:
        if block["type"] != "bullet" and in_list:
            body.append("</ul>")
            in_list = False
        if block["type"] == "heading" and block["level"] == top and not lists:
            notes_html()  # the notes of a chapter stand at its end
        text = render(block["text"], block["notes"])
        if block["type"] == "heading":
            level = min(block["level"], 6)
            body.append(f"<h{level}>{text}</h{level}>")
        elif block["type"] == "bullet":
            if not in_list:
                body.append("<ul>")
                in_list = True
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
        body.append("</ul>")
    notes_html()

    script = "<script>window.addEventListener('load', () => setTimeout(() => window.print(), 300));</script>" if print_on_load else ""
    page_number = "" if lists else "@bottom-center { content: counter(page); font: 10pt " + BOOK_FONTS.replace('"', "'") + "; }"
    return f"""<!doctype html>
<html lang="{html.escape(lang)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: {BOOK_FONTS}; font-size: 12pt; line-height: 1.55; color: #1b1b1b; background: #fff;
         max-width: 36em; margin: 2.5em auto; padding: 0 1.2em; -webkit-hyphens: auto; hyphens: auto; }}
  h1, h2, h3, h4 {{ line-height: 1.25; font-weight: 600; break-after: avoid; page-break-after: avoid; -webkit-hyphens: manual; hyphens: manual; }}
  h1 {{ font-size: 1.55em; margin: 1.2em 0 1em; }}
  h2 {{ font-size: 1.25em; margin: 1.6em 0 .6em; }}
  h3 {{ font-size: 1.08em; margin: 1.3em 0 .4em; }}
  p {{ margin: 0 0 .7em; orphans: 3; widows: 3; }}
  .book h1 {{ text-align: center; }}
  .book h1:not(:first-child) {{ break-before: page; page-break-before: always; }}
  .book p {{ margin: 0; text-align: justify; text-indent: 1.4em; }}
  .book :is(h1, h2, h3, h4, h5, h6, blockquote, .ar-p, ol, ul) + p, .book p:first-child, .book p.item {{ text-indent: 0; }}
  .book p.item {{ text-align: start; }}
  li {{ margin-bottom: .2em; }}
  li.sub {{ list-style: circle; margin-inline-start: 1.6em; }}
  blockquote {{ margin: .6em 0; padding-inline-start: 1em; border-inline-start: 3px solid #bbb; color: #333; }}
  .ar, [lang="ar"] {{ font-family: {ARABIC_FONTS}; font-size: 1.18em; line-height: 1.7; }}
  .ar-p, .book .ar-p {{ text-align: center; text-indent: 0; margin: .5em 0 .6em; }}
  sup.fn {{ line-height: 0; }}
  sup.fn a {{ text-decoration: none; color: inherit; }}
  .notes {{ font-size: 10pt; line-height: 1.4; margin: 1.6em 0 1.2em; padding: .6em 0 0 1.6em; border-top: .5pt solid #888; text-align: start; }}
  .notes li {{ margin-bottom: .25em; }}
  .notes .back {{ text-decoration: none; color: #888; }}
  code {{ font-family: Menlo, Consolas, monospace; font-size: 10pt; }}
  @page {{ size: A4; margin: 2.2cm 2.3cm 2.6cm; {page_number} }}
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


def to_docx(markdown: str, title: str, lang: str, lists: bool = True) -> bytes:
    rtl = is_rtl(lang)
    footnotes: list[str] = []
    paragraphs: list[str] = []

    def content(text: str, notes: dict) -> str:
        out = []
        for kind, value in inlines(text):
            if kind == "note":
                if value in notes:
                    footnotes.append(notes[value])
                    out.append(f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
                               f'<w:footnoteReference w:id="{len(footnotes)}"/></w:r>')
                else:
                    out.append(_runs(f"[^{value}]", rtl))
                continue
            style = {"bold": "<w:b/><w:bCs/>", "italic": "<w:i/><w:iCs/>",
                     "code": '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'}.get(kind, "")
            out.append(_runs(value, rtl, style))
        return "".join(out)

    bidi = "<w:bidi/>" if rtl else ""
    for block in parse(markdown, lists):
        if block["type"] == "heading":
            style = f"Heading{min(block['level'], 3)}"
        else:
            style = {"bullet": "ListBullet2" if block.get("level", 1) > 1 else "ListBullet", "quote": "Quote"}.get(block["type"])
        style_xml = f'<w:pStyle w:val="{style}"/>' if style else ""
        if not rtl and block["type"] == "para" and mostly_rtl(block["text"]):
            props = f'<w:pPr>{style_xml}<w:bidi/><w:jc w:val="center"/></w:pPr>'  # an Arabic passage (âyet, hadîs)
        else:
            props = f"<w:pPr>{style_xml}{bidi}</w:pPr>"
        text = ({1: "• ", 2: "◦ "}.get(block.get("level", 1), "◦ ") if block["type"] == "bullet" else "") + block["text"]
        paragraphs.append(f"<w:p>{props}{content(text, block['notes'])}</w:p>")

    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W} {R}><w:body>'
                + "".join(paragraphs)
                + '<w:sectPr><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/>'
                  '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/>'
                  '</w:sectPr></w:body></w:document>')
    # The page number in the footer, centred.
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {W}><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
              '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
              '</w:p></w:ftr>')
    # A book is hyphenated automatically in its own language; a report is not.
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {W}>'
                + ("" if lists else "<w:autoHyphenation/>") + '<w:defaultTabStop w:val="708"/></w:settings>')
    body_props = "" if lists else '<w:jc w:val="both"/>'
    chapter_break = "" if lists else "<w:pageBreakBefore/>"
    notes_xml = "".join(
        f'<w:footnote w:id="{i}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/>{bidi}</w:pPr>'
        f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
        f'<w:r><w:t xml:space="preserve"> </w:t></w:r>{content(note, {})}</w:p></w:footnote>'
        for i, note in enumerate(footnotes, 1))
    footnotes_part = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes {W}>'
                      '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                      '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
                      f"{notes_xml}</w:footnotes>")
    lang_attr = _x(lang)
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="26"/>
<w:lang w:val="{lang_attr}" w:bidi="{lang_attr if rtl else "ar-SA"}"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:widowControl/>{body_props}</w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/>{chapter_break}<w:spacing w:before="360" w:after="240"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="34"/><w:szCs w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:right="567"/></w:pPr><w:rPr><w:i/><w:iCs/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/><w:ind w:left="360" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet2"><w:name w:val="List Bullet 2"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/><w:ind w:left="720" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>
</w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
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
