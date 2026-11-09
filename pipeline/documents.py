"""Turns book files into a list of paragraphs and groups them into segments.

A "block" is one paragraph. Headings are kept in Markdown form ("# Heading").
Footnotes are kept as a "[^1]" mark and a "[^1]: text" line directly below the paragraph.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from .core import PipelineError
from .i18n import t

SUPPORTED = (".md", ".txt", ".docx", ".epub", ".pdf")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_blocks(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return _text_blocks(path.read_text(encoding="utf-8"))
    if ext == ".docx":
        return _docx_blocks(path)
    if ext == ".epub":
        return _epub_blocks(path)
    if ext == ".pdf":
        return _pdf_blocks(path)
    raise PipelineError(t("unsupported_file", name=path.name, supported=", ".join(SUPPORTED)))


def _text_blocks(text: str) -> list[str]:
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def _pdf_blocks(path: Path) -> list[str]:
    exe = shutil.which("pdftotext")
    if not exe:
        raise PipelineError(t("pdftotext_missing", name=path.name))
    out = subprocess.run([exe, "-enc", "UTF-8", str(path), "-"], capture_output=True, check=True)
    return _text_blocks(out.stdout.decode("utf-8", "replace").replace("\f", "\n\n"))


def _parse_xml(data: bytes) -> ET.Element:
    """XXE and "billion laughs" attacks rely on entity declarations; such XML is not read."""
    if any("<!ENTITY".encode(enc) in data for enc in ("utf-8", "utf-16-le", "utf-16-be")):
        raise PipelineError(t("xml_entity"))
    return ET.fromstring(data)


ZIP_MEMBER_LIMIT = 100 * 1024 * 1024  # at most 100 MB per file after decompression


def _zip_read(z: zipfile.ZipFile, name: str) -> bytes:
    """A member that becomes huge when decompressed (zip bomb) is not read."""
    if z.getinfo(name).file_size > ZIP_MEMBER_LIMIT:
        raise PipelineError(t("zip_member_too_large", name=name))
    return z.read(name)


# --- DOCX -------------------------------------------------------------------

MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _para_text(p: ET.Element, footnote_marker=None) -> str:
    """Text of one paragraph. Nested paragraphs (text boxes) and compatibility fallbacks are skipped here:
    text boxes are read as paragraphs of their own, and a fallback repeats content that is already present."""
    parts = []

    def walk(el: ET.Element) -> None:
        for child in el:
            tag = child.tag
            if tag in (W + "txbxContent", MC_FALLBACK):
                continue
            if tag == W + "t":
                parts.append(child.text or "")
            elif tag == W + "tab":
                parts.append("\t")
            elif tag in (W + "br", W + "cr"):
                parts.append("\n")
            elif tag == W + "noBreakHyphen":
                parts.append("\u2011")
            elif tag in (W + "footnoteReference", W + "endnoteReference") and footnote_marker:
                parts.append(footnote_marker(("e" if tag == W + "endnoteReference" else "f") + child.get(W + "id")))
            else:
                walk(child)

    walk(p)
    return "".join(parts)


def _paragraphs(root: ET.Element) -> list[ET.Element]:
    """All paragraphs in document order, without those inside a compatibility fallback (they repeat content)."""
    out = []

    def walk(el: ET.Element) -> None:
        for child in el:
            if child.tag == MC_FALLBACK:
                continue
            if child.tag == W + "p":
                out.append(child)
            walk(child)

    walk(root)
    return out


def _docx_blocks(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        doc = _parse_xml(_zip_read(z, "word/document.xml"))
        styles = _parse_xml(_zip_read(z, "word/styles.xml")) if "word/styles.xml" in names else None
        notes = _parse_xml(_zip_read(z, "word/footnotes.xml")) if "word/footnotes.xml" in names else None
        endnotes = _parse_xml(_zip_read(z, "word/endnotes.xml")) if "word/endnotes.xml" in names else None

    # w:name in styles.xml is English ("heading 1") whatever the language of Word is.
    heading_level = {}
    if styles is not None:
        for style in styles.iter(W + "style"):
            name = style.find(W + "name")
            value = (name.get(W + "val") if name is not None else "").lower()
            m = re.fullmatch(r"heading (\d)", value)
            if m or value == "title":
                heading_level[style.get(W + "styleId")] = int(m.group(1)) if m else 1

    footnotes = {}  # key: "f<id>" for footnotes, "e<id>" for endnotes; both become "[^n]" notes
    for prefix, root, tag in (("f", notes, "footnote"), ("e", endnotes, "endnote")):
        if root is None:
            continue
        for note in root.iter(W + tag):
            if note.get(W + "type"):  # separator lines
                continue
            paras = (_para_text(p).strip() for p in note.iter(W + "p"))
            footnotes[prefix + note.get(W + "id")] = " ".join(text for text in paras if text)

    blocks = []
    count = 0
    for p in _paragraphs(doc):
        ids = []

        def marker(note_id, ids=ids, base=count):
            ids.append(note_id)
            return f"[^{base + len(ids)}]"

        text = _para_text(p, marker).strip()
        if not text:
            continue
        style = p.find(f"{W}pPr/{W}pStyle")
        level = heading_level.get(style.get(W + "val")) if style is not None else None
        if level:
            text = "#" * level + " " + " ".join(text.split())
        for i, note_id in enumerate(ids, 1):
            text += f"\n[^{count + i}]: {footnotes.get(note_id, '')}"
        count += len(ids)
        blocks.append(text)
    return blocks


# --- EPUB -------------------------------------------------------------------

class _HTMLBlocks(HTMLParser):
    BLOCK = {"p", "div", "li", "blockquote", "br", "tr", "td", "th", "section", "article", "hr", "dt", "dd",
             "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self.blocks = []
        self.buf = []
        self.skip = 0
        self.level = 0

    def flush(self):
        text = " ".join("".join(self.buf).split())
        self.buf = []
        if text:
            self.blocks.append("#" * self.level + " " + text if self.level else text)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.flush()
            self.level = int(tag[1]) if tag[0] == "h" and tag != "hr" else 0

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.flush()
            self.level = 0

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def _epub_blocks(path: Path) -> list[str]:
    blocks = []
    with zipfile.ZipFile(path) as z:
        container = _parse_xml(_zip_read(z, "META-INF/container.xml"))
        opf_path = next(e.get("full-path") for e in container.iter() if e.tag.endswith("}rootfile"))
        opf = _parse_xml(_zip_read(z, opf_path))
        hrefs = {e.get("id"): e.get("href") for e in opf.iter() if e.tag.endswith("}item")}
        for itemref in (e for e in opf.iter() if e.tag.endswith("}itemref")):
            href = hrefs.get(itemref.get("idref"))
            if not href:
                continue
            name = posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), urllib.parse.unquote(href)))
            if name not in z.namelist():
                raise PipelineError(t("epub_missing_part", name=name))
            parser = _HTMLBlocks()
            parser.feed(_zip_read(z, name).decode("utf-8", "replace"))
            parser.close()
            parser.flush()
            blocks += parser.blocks
    return blocks


# --- Segmentation -----------------------------------------------------------

def split_long(blocks: list[str], limit: int) -> list[str]:
    """Splits a paragraph that exceeds the limit, first at line breaks, then at sentence ends."""
    out = []
    for block in blocks:
        if len(block) <= limit:
            out.append(block)
            continue
        pieces = []  # (separator, text)
        for line in block.split("\n"):
            sentences = [line] if len(line) <= limit else re.split(r"(?<=[.!?…:;])\s+", line)
            pieces += [("\n" if i == 0 else " ", s) for i, s in enumerate(sentences)]
        current = ""
        for sep, piece in pieces:
            if current and len(current) + len(piece) + 1 > limit:
                out.append(current)
                current = piece
            else:
                current = current + sep + piece if current else piece
        if current:
            out.append(current)
    return out


def segment(blocks: list[str], limit: int) -> list[str]:
    """Groups paragraphs into segments of about `limit` characters; a boundary never falls inside a paragraph."""
    segments = []
    current: list[str] = []
    size = 0

    def flush():
        nonlocal current, size
        carry = []
        # Keep a heading together with the text below it.
        while len(current) > 1 and current[-1].startswith("#"):
            carry.insert(0, current.pop())
        segments.append("\n\n".join(current))
        current = carry
        size = sum(len(b) for b in carry)

    for block in blocks:
        new_chapter = block.startswith("#") and size >= limit / 4
        if current and (size + len(block) > limit or new_chapter):
            flush()
        current.append(block)
        size += len(block)
    if current:
        segments.append("\n\n".join(current))
    return segments
