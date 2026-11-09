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
        elif lists and all(line.startswith("- ") for line in body):
            for line in body:
                blocks.append({"type": "bullet", "text": line[2:], "notes": notes})
        elif all(line.startswith(">") for line in body):
            blocks.append({"type": "quote", "text": "\n".join(line.lstrip("> ") for line in body), "notes": notes})
        else:
            blocks.append({"type": "para", "text": "\n".join(body), "notes": notes})
    return blocks


# --- HTML ---------------------------------------------------------------------

def to_html(markdown: str, title: str, lang: str, print_on_load: bool = False, lists: bool = True) -> str:
    direction = "rtl" if is_rtl(lang) else "ltr"
    body, footnotes = [], []

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
            value = html.escape(value).replace("\n", "<br>")
            out.append({"bold": f"<strong>{value}</strong>", "italic": f"<em>{value}</em>",
                        "code": f"<code>{value}</code>"}.get(kind, value))
        return "".join(out)

    in_list = False
    for block in parse(markdown, lists):
        if block["type"] != "bullet" and in_list:
            body.append("</ul>")
            in_list = False
        text = render(block["text"], block["notes"])
        if block["type"] == "heading":
            level = min(block["level"], 6)
            body.append(f"<h{level}>{text}</h{level}>")
        elif block["type"] == "bullet":
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{text}</li>")
        elif block["type"] == "quote":
            body.append(f"<blockquote>{text}</blockquote>")
        else:
            body.append(f"<p>{text}</p>")
    if in_list:
        body.append("</ul>")
    if footnotes:
        items = "".join(f'<li id="fn{i}">{render(note, {})} <a href="#ref{i}">↩</a></li>'
                        for i, note in enumerate(footnotes, 1))
        body.append(f'<hr><ol class="footnotes">{items}</ol>')

    script = "<script>window.addEventListener('load', () => setTimeout(() => window.print(), 300));</script>" if print_on_load else ""
    return f"""<!doctype html>
<html lang="{html.escape(lang)}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  body {{ font: 12pt/1.6 Georgia, "Times New Roman", "Noto Naskh Arabic", serif; max-width: 42em; margin: 2em auto; padding: 0 1em; color: #111; }}
  h1, h2, h3 {{ line-height: 1.3; page-break-after: avoid; }}
  p {{ margin: 0 0 .8em; text-align: justify; }}
  blockquote {{ margin: 0 0 .8em; padding-inline-start: 1em; border-inline-start: 3px solid #bbb; color: #333; }}
  sup.fn a {{ text-decoration: none; }}
  .footnotes {{ font-size: 10pt; }}
  code {{ font-family: Menlo, Consolas, monospace; font-size: 10pt; }}
  @page {{ margin: 2cm; }}
  @media print {{ body {{ margin: 0; max-width: none; }} a {{ color: inherit; }} }}
</style>
{script}
</head>
<body>
{chr(10).join(body)}
</body>
</html>
"""


# --- DOCX ---------------------------------------------------------------------

def _x(text: str) -> str:
    return xml_escape(_XML_INVALID.sub("", text))


def _runs(text: str, rtl: bool, base: str = "") -> str:
    rtl_tag = "<w:rtl/>" if rtl else ""
    out = []
    for i, line in enumerate(text.split("\n")):
        if i:
            out.append("<w:r><w:br/></w:r>")
        if line:
            out.append(f'<w:r><w:rPr>{base}{rtl_tag}</w:rPr><w:t xml:space="preserve">{_x(line)}</w:t></w:r>')
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
            style = {"bullet": "ListBullet", "quote": "Quote"}.get(block["type"])
        style_xml = f'<w:pStyle w:val="{style}"/>' if style else ""
        props = f"<w:pPr>{style_xml}{bidi}</w:pPr>"
        text = ("• " if block["type"] == "bullet" else "") + block["text"]
        paragraphs.append(f"<w:p>{props}{content(text, block['notes'])}</w:p>")

    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W}><w:body>'
                + "".join(paragraphs)
                + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                  '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/>'
                  '</w:sectPr></w:body></w:document>')
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
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Arial"/><w:sz w:val="24"/><w:szCs w:val="24"/>
<w:lang w:val="{lang_attr}" w:bidi="{lang_attr if rtl else "ar-SA"}"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:bCs/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="567" w:right="567"/></w:pPr><w:rPr><w:i/><w:iCs/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="60"/><w:ind w:left="360" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>
</w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>
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
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("docProps/core.xml", core)
    return buffer.getvalue()
