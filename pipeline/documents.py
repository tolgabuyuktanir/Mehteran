"""Turns book files into a list of paragraphs and groups them into segments.

A "block" is one paragraph. Headings are kept in Markdown form ("# Heading").
Footnotes are kept as a "[^1]" mark and a "[^1]: text" line directly below the paragraph.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from . import pdfglyphs
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
    # The layout output gives the position and size of every word: page headers, footnotes, superscript note
    # numbers, headings and paragraph starts are recognised from it. The plain text output is the fallback.
    out = subprocess.run([exe, "-bbox-layout", "-enc", "UTF-8", str(path), "-"], capture_output=True)
    pages = None
    if out.returncode == 0:
        try:
            pages = _pdf_pages(out.stdout)
        except (ET.ParseError, ValueError, TypeError):
            pages = None
    if pages is not None:
        _use_pdf_glyphs(path, pages)
        if sum(len(line.text) for page in pages for line in page) < 5 * max(1, len(pages)):
            raise PipelineError(t("pdf_no_text", name=path.name))
        return _pdf_layout_blocks(pages)
    out = subprocess.run([exe, "-enc", "UTF-8", str(path), "-"], capture_output=True, check=True)
    return _pdf_text_blocks(out.stdout.decode("utf-8", "replace"))


_LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
                            "ﬅ": "st", "ﬆ": "st", "­": None})


def _join_lines(block: str) -> str:
    """One paragraph on one line; a word hyphenated at a line end is joined again.

    The hyphen stays when the part on the next line has one or two letters: in Turkish that is a joined suffix
    ("Kur'ân-ı", "ehl-i", "Redd-ül-muhtâr"); a typesetter does not break a word so close to its end."""
    def join(m: re.Match) -> str:
        rest = re.match(r"\w+", block[m.start(2):]).group(0)
        return m[1] + m[2] if m[2].islower() and len(rest) > 2 else f"{m[1]}-{m[2]}"

    block = re.sub(r"(\w)[-‐­]\n(\w)", join, block)
    return " ".join(block.split())


# --- PDF layout ----------------------------------------------------------------

@dataclass
class _Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    logical: bool = False  # right-to-left text already in reading order (built from the PDF's glyphs)


class _Line:
    def __init__(self, words: list[_Word]):
        self.words = words
        self.x0, self.x1 = min(w.x0 for w in words), max(w.x1 for w in words)
        self.y0, self.y1 = min(w.y0 for w in words), max(w.y1 for w in words)
        heights = sorted(w.y1 - w.y0 for w in words)
        self.size = heights[len(heights) // 2]  # the type size (a superscript number does not change it)
        self.text = " ".join(w.text for w in words)


def _pdf_pages(xhtml: bytes) -> list[list[_Line]]:
    """The lines of each page, in pdftotext's reading order."""
    ns = "{http://www.w3.org/1999/xhtml}"
    pages = []
    for page in _parse_xml(xhtml).iter(ns + "page"):
        lines = []
        for line in page.iter(ns + "line"):
            words = [_Word((w.text or "").translate(_LIGATURES), *(float(w.get(k)) for k in ("xMin", "yMin", "xMax", "yMax")))
                     for w in line.iter(ns + "word")]
            # A word of letters with no width was cut away by the page's clipping (a browser draws a line that
            # crosses the page break on both pages); only vowel signs are drawn without width.
            words = [w for w in words if w.text.strip()
                     and (w.x1 - w.x0 > 0.05 or not any(unicodedata.category(c).startswith("L") for c in w.text))]
            if words:
                lines.append(_Line(words))
        pages.append(lines)
    return pages


_RTL_CHAR = re.compile(r"[֐-ࣿיִ-﷿ﹰ-ﻼ]")


def _logical(visual: str) -> str:
    """A right-to-left word as pdftotext gives it (letters in visual order, each mark after its letter) in reading order."""
    clusters: list[str] = []
    for ch in visual:
        if clusters and unicodedata.category(ch) == "Mn":
            clusters[-1] += ch
        else:
            clusters.append(ch)
    return "".join(reversed(clusters))


def _reading_order(words: list[_Word], size: float) -> list[str]:
    """The words of a line in reading order. pdftotext gives right-to-left words (Arabic, Hebrew) in visual order:
    such runs are reversed, and the pieces of a word that the layout split are joined again."""
    if not any(_RTL_CHAR.search(w.text) for w in words):
        return [w.text for w in words]
    runs: list[tuple[bool, list[_Word]]] = []
    for w in sorted(words, key=lambda w: w.x0):
        rtl = bool(_RTL_CHAR.search(w.text))
        if runs and runs[-1][0] == rtl:
            runs[-1][1].append(w)
        else:
            runs.append((rtl, [w]))
    out = []
    for rtl, run in runs:
        if not rtl:
            out.append([w.text for w in run])
            continue
        pieces: list[list[_Word]] = []
        for w in run:  # left to right; pieces closer than a space belong to one word
            if pieces and not w.logical and not pieces[-1][-1].logical and w.x0 - pieces[-1][-1].x1 < 0.17 * size:
                pieces[-1].append(w)
            else:
                pieces.append([w])
        out.append([piece[0].text if piece[0].logical else _logical("".join(p.text for p in piece))
                    for piece in reversed(pieces)])
    if _mostly_rtl([w.text for w in words]):
        out.reverse()  # a right-to-left line: its runs are read from the right
    return [text for run in out for text in run]


_MIRROR = str.maketrans("()[]{}<>«»‹›", ")(][}{><»«›‹")
_NUMBER_SIGNS = set(".,/:-٫٬")
# Joined shapes that look the same as an Arabic letter's but belong to a Persian or Urdu letter. A PDF maker
# may write them for Arabic text; only the shape is known, so they are read as the Arabic letter.
# In Persian text (see _PERSIAN) the Persian yeh is kept.
_SAME_SHAPE = {"ﯾ": "ي", "ﯿ": "ي"}
# Urdu's heh (ھ) is not used in Arabic, Persian or Ottoman text; fonts give it for the heh of those.
_URDU_HEH = {"ھ": "ه", "ﮪ": "ه", "ﮫ": "ه", "ﮬ": "ه", "ﮭ": "ه"}
_RIGHT_JOINING = set("اأإآٱدذرزژوؤة")  # letters that never join the letter after them
# Letters only Persian (and Ottoman) writing has: peh, tcheh, jeh, keheh, gaf, and yeh in its final shapes.
_PERSIAN = re.compile("[پچژکگیﭖ-ﭙﭺ-ﭽﮊﮋﮎ-ﮕﯼﯽ]")
# For comparing with pdftotext's text: the Arabic and Persian forms of a letter count as the same letter.
_FOLD = str.maketrans("یکھ", "يكه")
_ALLAH_LAM_MARKS = "ّٰ"  # shadda and the small alif stand on the second lam of "Allah"


def _is_mark(text: str) -> bool:
    """Vowel signs only (also a presentation form of them, such as ﱠ for shadda with fatha)."""
    text = _plain(text)
    return bool(text) and all(unicodedata.category(c) in ("Mn", "Me") for c in text)


def _plain(text: str, persian: bool = False) -> str:
    """Presentation forms (the joined shapes of Arabic letters, ligatures such as ﷲ) as the letters they stand for."""
    out = []
    for c in text:
        if c in _URDU_HEH:
            c = _URDU_HEH[c]
        elif c in _SAME_SHAPE and not persian:
            c = _SAME_SHAPE[c]
        elif "ﭐ" <= c <= "﷿" or "ﹰ" <= c <= "﻿":
            c = unicodedata.normalize("NFKC", c).replace(" ", "")
        if c != "ـ":  # tatweel only stretches a word
            out.append(c)
    return "".join(out)


def _with_marks(base: pdfglyphs.Glyph, marks: list[pdfglyphs.Glyph], persian: bool = False) -> str:
    """A glyph's letters with the vowel signs drawn on it.

    A glyph of several letters (a ligature such as لم or ﷲ) is shared out among its letters, which stand from
    right to left. A sign has no width and the point where the PDF puts it is at the left of the sign, often a
    little left of its letter, so the order of the signs from left to right counts more than their position."""
    text = _plain(base.text, persian)
    own: list[str] = []  # the letters, each with the signs that follow it
    for c in text:
        if _is_mark(c) and own:
            own[-1] += c
        else:
            own.append(c)
    # One glyph can show two signs (kasra with shadda): each sign is placed on its own.
    marks = [pdfglyphs.Glyph(c, m.x0, m.x1, m.y, m.size, m.order) for m in marks for c in _plain(m.text)]
    if len(own) < 2 or not marks:
        return text + "".join(m.text for m in marks)
    marks.sort(key=lambda m: ((m.x0 + m.x1) / 2, m.order))  # left to right
    last = len(own) - 1  # the leftmost letter
    letters = "".join(c[0] for c in own)
    shadda = any(m.text == "ّ" for m in marks)
    if letters.endswith("لله"):  # "Allah" (ﷲ, or a ligature of lam, lam and heh)
        lam, heh = len(own) - 2, len(own) - 1
        others = [m for m in marks if m.text not in _ALLAH_LAM_MARKS]
        own[lam] += "".join(m.text for m in marks if m.text in _ALLAH_LAM_MARKS)
        if len(others) <= 2:
            for m, k in zip(others, (heh, 0)):
                own[k] += m.text
            return "".join(own)
        marks = others
    elif letters[0] == "ل" and letters[1:] in ("ا", "أ", "إ", "آ"):  # lam-alif
        if len(marks) == 2 and not shadda:
            # A sukun is the lam's (الْأَرْض); a kasra under hamza is the alif's (الْإِيمَان); else by position.
            on_lam = [m.text == "ْ" for m in marks]
            on_alif = [letters[1] == "إ" and m.text in "ٍِ" for m in marks]
            if any(on_lam) or any(on_alif):
                lam_sign = marks[0] if on_lam[0] or on_alif[1] else marks[1]
                alif_sign = marks[1] if lam_sign is marks[0] else marks[0]
                return own[0] + lam_sign.text + own[1] + alif_sign.text
            return own[0] + marks[1].text + own[1] + marks[0].text  # the alif is the left letter
        return own[0] + "".join(m.text for m in marks) + own[1]  # one sign, or shadda: the lam's
    elif len(marks) == len(own) and not shadda:  # one sign on each letter
        for i, m in enumerate(marks):
            own[last - i] += m.text
        return "".join(own)
    width = (base.x1 - base.x0) / len(own) or 1.0
    for m in marks:
        k = int((base.x1 - ((m.x0 + m.x1) / 2 + 0.3 * width)) // width)
        own[min(max(k, 0), last)] += m.text
    return "".join(own)


def _letters(text: str) -> Counter:
    text = unicodedata.normalize("NFD", _plain(text, persian=True).translate(_FOLD))
    return Counter(c for c in text if not c.isspace() and c not in "()[]{}<>«»‹›"
                   and unicodedata.category(c) != "Cf")  # a zero-width non-joiner is not drawn


def _same_text(rebuilt: str, extracted: str) -> bool:
    """The rebuilt words have the letters of pdftotext's words. pdftotext drops a sign drawn at the same point as
    an equal sign (it takes it for fake bold), so the rebuilt words may have more vowel signs, never fewer."""
    a, b = _letters(rebuilt), _letters(extracted)
    if any(a[c] != b[c] for c in a.keys() | b.keys() if not _is_mark(c)):
        return False
    return all(a[c] >= b[c] for c in b if _is_mark(c))


def _glyph_words(glyphs: list[pdfglyphs.Glyph], rtl_line: bool) -> list[_Word] | None:
    """Right-to-left words in reading order, from the glyphs of a right-to-left line or of one run of a line.

    A mark (a vowel sign) belongs to its letter. A word ends at a space glyph or a gap. The letters are read
    from the right; digits and Latin letters keep their left-to-right order, and brackets are mirrored. In a
    left-to-right line, brackets and quotes at the edges of the run belong to the surrounding text.
    The words are returned left to right, as a line keeps them."""
    if not glyphs:
        return None
    size = max(g.size for g in glyphs) or 10.0
    if any(not g.text and g.x1 - g.x0 > 0.05 * size for g in glyphs):
        return None  # a visible glyph whose letters the PDF does not give
    persian = any(_PERSIAN.search(g.text) for g in glyphs)
    bases = [g for g in glyphs if g.text and not _is_mark(g.text)]
    units = {id(g): [g, []] for g in bases}
    marks = [g for g in glyphs if g.text and _is_mark(g.text)]
    # A vowel sign has no width, and where it is drawn depends on the font. The PDF writes it right before or
    # right after its letter: the side that agrees with the positions in this run is taken.
    stream = sorted((g for g in glyphs if g.text and not g.text.isspace()), key=lambda g: g.order)
    place = {id(g): k for k, g in enumerate(stream)}

    def letter_beside(m, step: int):
        k = place[id(m)] + step
        while 0 <= k < len(stream) and _is_mark(stream[k].text):
            k += step
        return stream[k] if 0 <= k < len(stream) else None

    def over(m, b, slack: float = 0.5) -> bool:
        return b is not None and b.x0 - slack <= (m.x0 + m.x1) / 2 < b.x1 + slack

    # Counted without slack: a sign put exactly on the edge between two letters counts for the one starting there.
    step = max((1, -1), key=lambda s: sum(over(m, letter_beside(m, s), 0.0) for m in marks))
    for m in marks:
        under = letter_beside(m, step)
        if not over(m, under, 0.3 * size):
            candidates = [g for g in bases if not g.text.isspace()]
            if not candidates:
                return None
            cx = (m.x0 + m.x1) / 2
            under = min(candidates, key=lambda b: (not over(m, b), abs((b.x0 + b.x1) / 2 - cx)))
        units[id(under)][1].append(m)
    letters = [g for g in bases if not g.text.isspace()]
    # A space drawn over a letter (the space at the end of a justified line) does not end a word.
    units = [u for u in units.values() if not u[0].text.isspace()
             or not any(b.x0 < (u[0].x0 + u[0].x1) / 2 < b.x1 for b in letters)]
    units.sort(key=lambda u: (u[0].x0 + u[0].x1) / 2)  # left to right
    words: list[list] = []
    for u in units:
        g = u[0]
        if g.text.isspace():
            words.append([])
            continue
        if not words or (words[-1] and g.x0 - words[-1][-1][0].x1 > 0.25 * size):
            words.append([])
        words[-1].append(u)
    words = [w for w in words if w]
    if not words:
        return None

    def strong_rtl(u) -> bool:
        return bool(_RTL_CHAR.search(u[0].text)) and not any(c.isdigit() for c in u[0].text)

    prefix = suffix = ""
    if not rtl_line:
        while words[0] and not strong_rtl(words[0][0]):
            prefix += words[0].pop(0)[0].text
        while words[-1] and not strong_rtl(words[-1][-1]):
            suffix = words[-1].pop()[0].text + suffix
        words = [w for w in words if w]
        if not words:
            return None

    out = []
    for w in reversed(words):
        text, forward = [], []  # forward: digits or Latin letters, which keep their left-to-right order
        cut = False  # the letter before was drawn in its end shape inside the word
        for u in reversed(w):
            piece = _with_marks(u[0], u[1], persian)
            left_to_right = piece.isdigit() or (piece.isalnum() and not _RTL_CHAR.search(piece))
            if left_to_right or (forward and piece in _NUMBER_SIGNS):
                forward.insert(0, piece)
                continue
            if forward:
                text += forward
                forward = []
            if cut and piece[:1].isalpha():
                text.append("‌")  # a zero-width non-joiner (Persian "می‌کند") is not drawn but keeps that shape
            text.append(piece.translate(_MIRROR))
            last_shape = u[0].text[-1:]
            cut = (("FINAL FORM" in unicodedata.name(last_shape, "") or "ISOLATED FORM" in unicodedata.name(last_shape, ""))
                   and _plain(last_shape)[-1:] not in _RIGHT_JOINING)
        text += forward
        out.append(_Word(unicodedata.normalize("NFC", "".join(text)), w[0][0].x0, 0, w[-1][0].x1, 0, logical=True))
    out[0].text = prefix + out[0].text
    out[-1].text += suffix
    # Some PDF makers give a mirrored bracket as the letter it shows, others as the letter it stands for: a
    # pair that closes before it opens, »…«, was read the wrong way round. (A bracket alone can belong to a
    # quotation that starts or ends on another line.)
    text = " ".join(w.text for w in out)
    if _reversed_pair(text) and not _reversed_pair(text.translate(_MIRROR)):
        for w in out:
            w.text = w.text.translate(_MIRROR)
    out.reverse()  # left to right, as the line's words are kept
    return out


def _reversed_pair(text: str) -> bool:
    for opening, closing in ("()", "[]", "{}", "«»", "‹›"):
        first_close, last_open = text.find(closing), text.rfind(opening)
        if first_close >= 0 and last_open > first_close and text.find(opening) > first_close:
            return True
    return False


def _use_pdf_glyphs(path: Path, pages: list[list[_Line]]) -> None:
    """Puts the right-to-left words of each line in reading order from the PDF's own glyphs (see pdfglyphs).

    A run whose letters differ from pdftotext's keeps pdftotext's words, so this never loses text."""
    wanted = [i for i, page in enumerate(pages) if any(_RTL_CHAR.search(line.text) for line in page)]
    for i in wanted:
        pages[i] = _merge_split_lines(pages[i])
    if not wanted:
        return
    try:
        glyphs = pdfglyphs.read(path.read_bytes(), wanted)
    except Exception:  # any file this reader cannot handle keeps pdftotext's text
        return
    for i, page in glyphs.items():
        lines = pages[i]
        # A letter belongs to the line of pdftotext's word around it, else to the line around it whose middle
        # is nearest (line boxes of Arabic type overlap). A vowel sign stands above or below its letter, so it
        # goes with the letter written next to it.
        page = sorted(page, key=lambda g: g.order)
        boxes = [(w, j) for j, ln in enumerate(lines) for w in ln.words]
        line_of: dict[int, int] = {}
        for k, g in enumerate(page):
            if g.text and _is_mark(g.text):
                continue
            cx = (g.x0 + g.x1) / 2
            near = [(abs((w.y0 + w.y1) / 2 - g.y), j) for w, j in boxes
                    if w.y0 <= g.y <= w.y1 and w.x0 - 0.5 <= cx <= w.x1 + 0.5]
            near = near or [(abs((ln.y0 + ln.y1) / 2 - g.y), j) for j, ln in enumerate(lines)
                            if ln.y0 <= g.y <= ln.y1 and ln.x0 - 2 <= cx <= ln.x1 + 2]
            if near:
                line_of[k] = min(near)[1]
        for k, g in enumerate(page):
            if not (g.text and _is_mark(g.text)):
                continue
            cx = (g.x0 + g.x1) / 2
            for step in (1, -1):
                n = k + step
                while 0 <= n < len(page) and page[n].text and _is_mark(page[n].text):
                    n += step
                if n in line_of and page[n].x0 - 1 <= cx <= page[n].x1 + 1 and abs(page[n].y - g.y) < 2 * g.size:
                    line_of[k] = line_of[n]
                    break
            else:
                near = [(abs((ln.y0 + ln.y1) / 2 - g.y), j) for j, ln in enumerate(lines)
                        if ln.y0 <= g.y <= ln.y1 and ln.x0 - 2 <= cx <= ln.x1 + 2]
                if near:
                    line_of[k] = min(near)[1]
        owned: dict[int, list[pdfglyphs.Glyph]] = {}
        for k, j in line_of.items():
            owned.setdefault(j, []).append(page[k])
        for j, line in enumerate(lines):
            if _RTL_CHAR.search(line.text) and j in owned:
                lines[j] = _rebuild_line(line, owned[j])


def _merge_split_lines(lines: list[_Line]) -> list[_Line]:
    """pdftotext can cut one line of Arabic type into several lines (vowel signs that stand higher than the
    letters may even form a line of their own). Right-to-left lines at the same height that touch are one line
    again; it takes the place of the first piece."""
    def same(a: _Line, b: _Line) -> bool:
        overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
        gap = max(a.x0, b.x0) - min(a.x1, b.x1)  # negative when they overlap
        return (bool(_RTL_CHAR.search(a.text) and _RTL_CHAR.search(b.text))
                and overlap >= 0.5 * min(a.y1 - a.y0, b.y1 - b.y0) and gap < 2 * max(a.size, b.size))

    def small(a: _Line) -> bool:
        return len(a.text.replace(" ", "")) <= 4 and bool(_RTL_CHAR.search(a.text))

    def fit(piece: _Line, line: _Line) -> tuple:
        """How well a small piece belongs to a line it touches, best first: inside the line's height, standing
        on the line (a letter set high above the others, as the tall lam of "Allah" in some fonts rises over
        its own line), hanging below it."""
        overlap = min(line.y1, piece.y1) - max(line.y0, piece.y0)
        inside = piece.y0 >= line.y0 - 1 and piece.y1 <= line.y1 + 1
        on_top = piece.y0 < line.y0 and piece.y1 < line.y1
        return (0 if inside else 1 if on_top else 2, -overlap)

    out = list(lines)
    # A small piece that touches two lines joins the one it fits best.
    for piece in [line for line in out if small(line)]:
        if piece not in out:  # it has taken in another piece already
            continue
        hosts = [line for line in out if line is not piece and _RTL_CHAR.search(line.text)
                 and min(line.y1, piece.y1) > max(line.y0, piece.y0)
                 and max(line.x0, piece.x0) - min(line.x1, piece.x1) < 2 * max(line.size, piece.size)]
        if len(hosts) >= 2:
            host = min(hosts, key=lambda line: fit(piece, line))
            joined = _Line(host.words + piece.words)
            joined.y0, joined.y1 = host.y0, host.y1  # a raised letter does not make the line taller
            out[out.index(host)] = joined
            out.remove(piece)
    merged = True
    while merged:  # a piece can join only after the piece between has joined
        merged = False
        for a in range(len(out)):
            b = next((b for b in range(a + 1, len(out)) if same(out[a], out[b])), None)
            if b is not None:
                out[a] = _Line(out[a].words + out.pop(b).words)
                merged = True
                break
    return out


def _rebuild_line(line: _Line, glyphs: list[pdfglyphs.Glyph]) -> _Line:
    words = sorted(line.words, key=lambda w: w.x0)
    if _rtl_line(line):
        # A right-to-left line is rebuilt whole: the pieces pdftotext made of it can overlap.
        rebuilt = _glyph_words(glyphs, True)
        if rebuilt and _same_text(" ".join(w.text for w in rebuilt), line.text):
            return _Line(_placed(rebuilt, words))
        return line
    out: list[_Word] = []
    i = 0
    while i < len(words):
        if not _RTL_CHAR.search(words[i].text):
            out.append(words[i])
            i += 1
            continue
        j = i
        while j < len(words) and _RTL_CHAR.search(words[j].text):
            j += 1
        size = max(g.size for g in glyphs)

        def mark_only(w: _Word) -> bool:  # quotes or brackets right beside the run belong to it
            return not any(c.isalnum() for c in w.text)

        if out and mark_only(out[-1]) and words[i].x0 - out[-1].x1 < 0.5 * size:
            i -= 1
            out.pop()
        if j < len(words) and mark_only(words[j]) and words[j].x0 - words[j - 1].x1 < 0.5 * size:
            j += 1
        run = words[i:j]
        x0, x1 = run[0].x0, max(w.x1 for w in run)

        def in_run(g) -> bool:
            cx = (g.x0 + g.x1) / 2
            if g.text and _is_mark(g.text):  # a sign can stand a little outside its letter's box
                return x0 - 0.6 * size <= cx <= x1 + 0.6 * size
            return x0 - 1 <= cx <= x1 + 1 and not any(o.x0 <= cx <= o.x1 for o in words[:i] + words[j:])

        rebuilt = _glyph_words([g for g in glyphs if in_run(g)], False)
        if rebuilt and _same_text(" ".join(w.text for w in rebuilt), " ".join(w.text for w in run)):
            out += _placed(rebuilt, run)
        else:
            out += run
        i = j
    return _Line(out)


def _placed(rebuilt: list[_Word], model: list[_Word]) -> list[_Word]:
    """Gives the rebuilt words the height and middle that most of pdftotext's words had (the type size is read
    from it; a word of vowel signs alone is not counted)."""
    letters = [w for w in model if not _is_mark(w.text)] or model
    heights = sorted(w.y1 - w.y0 for w in letters)
    middles = sorted((w.y0 + w.y1) / 2 for w in letters)
    height, middle = heights[len(heights) // 2], middles[len(middles) // 2]
    for w in rebuilt:
        w.y0, w.y1 = middle - height / 2, middle + height / 2
    return rebuilt


def _note_number(text: str) -> str | None:
    text = text.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
    return text if re.fullmatch(r"\d{1,3}", text) else None


_SENTENCE_END = re.compile(r"[.!?…:؟۔][\"”’»«)\]]*(\[\^\d+\])*$")


def _rtl_line(line: _Line) -> bool:
    return _mostly_rtl([w.text for w in line.words])


def _mostly_rtl(words: list[str]) -> bool:
    """Most letters are right-to-left ones. Vowel signs are not counted: a fully voweled Arabic quotation in a
    Turkish line has more signs than letters."""
    letters = [c for w in words for c in w if unicodedata.category(c).startswith("L")]
    return sum(1 for c in letters if _RTL_CHAR.match(c)) > len(letters) / 2


def _pdf_layout_blocks(pages: list[list[_Line]]) -> list[str]:
    """Paragraphs of a typeset book, from the position and size of each word.

    - Running headers, footers and page numbers are dropped: a first or last line of a page that is a number,
      that repeats at the edge of other pages, or (at the top) that is short and in a smaller type.
    - Footnotes are the lines in a smaller type below the last line of the main text. A raised number in the text
      becomes a "[^n]" mark and its note a "[^n]: text" line below the paragraph. A note continues on the next page
      when the first footnote line there has no number.
    - A paragraph starts with an indented line, after a short line, after a larger space or when the type size
      changes. A clearly larger type is a heading ("#", "##", … from the largest size down).
    - A paragraph that runs on to the next page is joined, also when footnotes stand between.
    """
    # Sizes are measured on left-to-right lines: Arabic type has taller boxes at the same size.
    lines_all = [line for page in pages for line in page if not _RTL_CHAR.search(line.text)]
    if not lines_all:
        lines_all = [line for page in pages for line in page]
    if not lines_all:
        return []
    weights: Counter = Counter()
    for line in lines_all:
        weights[round(line.size * 2) / 2] += len(line.text)
    body = weights.most_common(1)[0][0]
    small, big = 0.92 * body, 1.06 * body
    heading_sizes = sorted({round(line.size * 2) / 2 for line in lines_all if line.size >= big}, reverse=True)

    def key(line: _Line) -> str:
        return re.sub(r"\d+", "#", " ".join(line.text.split())).lower()

    def numeric(line: _Line) -> bool:
        return bool(re.fullmatch(r"[-–—\s]*(\d{1,4}|[ivxlcdm]{1,7})[-–—\s]*", line.text, re.I))

    def rows_of(lines: list[_Line]) -> list[list[_Line]]:
        """Lines grouped by height on the page (a header often has two parts: a title and a page number)."""
        rows: list[list[_Line]] = []
        for line in sorted(lines, key=lambda line: (line.y0, line.x0)):
            middle = (line.y0 + line.y1) / 2
            if rows and abs(middle - (rows[-1][0].y0 + rows[-1][0].y1) / 2) < 0.6 * max(line.size, rows[-1][0].size):
                rows[-1].append(line)
            else:
                rows.append([line])
        return rows

    page_rows = [rows_of(page) for page in pages]
    edges = Counter(key(line) for rows in page_rows for i in {0, 1, len(rows) - 2, len(rows) - 1} & set(range(len(rows)))
                    for line in rows[i])
    repeated = {k for k, n in edges.items() if n >= 2}

    # The text column of odd and even pages (their margins often differ): a page with few lines uses these.
    column: dict[int, tuple[float, float]] = {}
    for parity in (0, 1):
        normal = [line for page in pages[parity::2] for line in page if abs(line.size - body) < 0.1 * body]
        if normal:
            column[parity] = (Counter(round(line.x0) for line in normal).most_common(1)[0][0], max(line.x1 for line in normal))

    blocks: list[dict] = []
    notes: dict[int, str] = {}
    last_note: int | None = None
    for page_no, (page, rows) in enumerate(zip(pages, page_rows)):
        rows = list(rows)
        if not rows:
            continue
        width = max(line.x1 for line in page) - min(line.x0 for line in page)

        def margin(row: list[_Line], inner: list[_Line] | None, top: bool) -> bool:
            """A header or footer row: a page number, a text that repeats on other pages, or a short line in a
            smaller type at the top. It is set apart from the text: in a smaller type or by a larger space."""
            apart = inner is None or (inner[0].y0 - row[0].y1 if top else row[0].y0 - inner[0].y1) > 0.9 * body
            # An Arabic line that repeats is a quotation (the Besmele that opens each chapter), not a header;
            # a header is shorter than a full line of text.
            return all(line.size <= 1.05 * body and (line.size < small or apart) and (
                numeric(line) or (key(line) in repeated and not _rtl_line(line) and line.x1 - line.x0 < 0.8 * width)
                or (top and line.size < small and line.x1 - line.x0 < 0.6 * width))
                for line in row)

        for _ in range(2):  # at most two rows at each edge: a header or footer and a page number
            if rows and margin(rows[0], rows[1] if len(rows) > 1 else None, True):
                rows.pop(0)
            if rows and margin(rows[-1], rows[-2] if len(rows) > 1 else None, False):
                rows.pop()
        ordered = [line for row in rows for line in row]
        kept = set(map(id, ordered))

        # Footnotes: smaller lines below the last line of the main text, read row by row (a note number can be a
        # line of its own beside the note text).
        main_end = max((line.y1 for line in ordered if line.size >= small), default=None)
        foot = [line for line in ordered if main_end is not None and line.y0 >= main_end - 1 and line.size < small]
        rows: list[list[_Line]] = []
        for line in foot:
            middle = (line.y0 + line.y1) / 2
            if rows and abs(middle - (rows[-1][0].y0 + rows[-1][0].y1) / 2) < 0.6 * max(line.size, rows[-1][0].size):
                rows[-1].append(line)
            else:
                rows.append([line])
        page_notes: dict[str, int] = {}
        current = last_note
        consumed: set[int] = set()
        for row in rows:
            words = [w for line in sorted(row, key=lambda line: line.x0) for w in line.words]
            number = _note_number(words[0].text.rstrip(".)"))
            size = max(line.size for line in row)
            text = " ".join(_reading_order(words[1:] if number else words, size))
            if number:
                current = len(notes) + 1
                notes[current] = text
                page_notes[number] = current
            elif current is not None:
                notes[current] = _join_lines(notes[current] + "\n" + text)
            else:
                continue  # small type without a note number before it: part of the text
            consumed.update(map(id, row))
        if page_notes:
            last_note = current
        main = [line for line in page if id(line) in kept and id(line) not in consumed]
        if not main:
            continue

        normal = [line for line in main if abs(line.size - body) < 0.1 * body]
        if len(normal) >= 5 or page_no % 2 not in column:
            left = Counter(round(line.x0) for line in normal).most_common(1)[0][0] if normal else min(line.x0 for line in main)
            right = max((line.x1 for line in normal), default=max(line.x1 for line in main))
        else:
            left, right = column[page_no % 2]
        # A line starts at the left edge and ends at the right one; a right-to-left line the other way round.
        def reaches_end(line: _Line, slack: float) -> bool:
            return line.x0 <= left + slack if _rtl_line(line) else line.x1 >= right - slack

        def indented(line: _Line) -> bool:
            return line.x1 < right - 0.6 * line.size if _rtl_line(line) else line.x0 > left + 0.6 * line.size

        # Justified text: most lines reach the end edge, so a short line ends a paragraph. In ragged text only a
        # clearly short line that ends a sentence does.
        justified = sum(1 for line in normal if reaches_end(line, 0.3 * line.size)) >= 0.4 * len(normal)

        def short(line: _Line) -> bool:
            # Arabic text is set justified and often has no full stop, so its lines are measured that way.
            if justified or _rtl_line(line):
                return not reaches_end(line, 1.5 * line.size)
            return not reaches_end(line, 0.25 * (right - left)) and bool(_SENTENCE_END.search(line.text))
        used: set[int] = set()

        def text_of(line: _Line) -> str:
            words = []
            for w in line.words:
                number = _note_number(w.text)
                raised = number and w.y1 - w.y0 < 0.8 * line.size and w.y1 < line.y1 - 0.1 * line.size
                if raised and number in page_notes:
                    used.add(page_notes[number])
                    w = _Word(f"[^{page_notes[number]}]", w.x0, w.y0, w.x1, w.y1)
                words.append(w)
            return re.sub(r"\s+(\[\^\d+\])", r"\1", " ".join(_reading_order(words, line.size)))

        page_blocks: list[dict] = []
        previous: _Line | None = None
        for line in main:
            heading = line.size >= big and not _RTL_CHAR.search(line.text)
            new = (
                previous is None
                or abs(line.size - previous.size) > 0.12 * body
                or line.y0 - previous.y1 > 0.7 * line.size
                or _rtl_line(line) != _rtl_line(previous)
                or (not heading and indented(line))
                or (not heading and short(previous))
            )
            if new:
                page_blocks.append({"lines": [], "size": line.size, "first": line})
            page_blocks[-1]["lines"].append(text_of(line))
            page_blocks[-1]["last"] = line
            previous = line
        for b in page_blocks:
            b["text"] = _join_lines("\n".join(b["lines"]))
            # A heading: a larger type, a few lines at most, not a sentence (an Arabic passage is never a heading).
            b["heading"] = (b["size"] >= big and len(b["lines"]) <= 3 and not _RTL_CHAR.search(b["text"])
                            and (b["size"] >= 1.12 * body or not _SENTENCE_END.search(b["text"])))
            if b["heading"]:
                size = round(b["size"] * 2) / 2
                b["text"] = "#" * min(heading_sizes.index(size) + 1 if size in heading_sizes else 1, 6) + " " + b["text"]
            b["full"] = justified and reaches_end(b["last"], 1.5 * b["last"].size)
        # A note whose number was not found in the text stays at the end of the page's text.
        lost = [i for i in page_notes.values() if i not in used]
        if lost and page_blocks:
            page_blocks[-1]["text"] += "".join(f"[^{i}]" for i in lost)

        if blocks and page_blocks:
            before, first = blocks[-1], page_blocks[0]
            runs_on = not before["heading"] and (before["full"] or not _SENTENCE_END.search(before["text"]))
            continues = (not first["heading"] and abs(first["size"] - before["size"]) < 0.1 * body
                         and not indented(first["first"]) and _rtl_line(first["first"]) == _rtl_line(before["last"]))
            if runs_on and continues:
                before["text"] = _join_lines(before["text"] + "\n" + first["text"])
                before["full"], before["last"] = first["full"], first["last"]
                page_blocks.pop(0)
        blocks += page_blocks

    out = []
    for b in blocks:
        ids = [int(n) for n in re.findall(r"\[\^(\d+)\]", b["text"])]
        out.append(b["text"] + "".join(f"\n[^{i}]: {notes.get(i, '')}" for i in ids))
    return out


def _pdf_text_blocks(text: str) -> list[str]:
    """Cleans the text of pdftotext (pages are separated by form feeds).

    Drops page numbers and running headers and footers (a first or last line that repeats on many pages), joins
    the lines of a paragraph, and joins a paragraph that continues on the next page. pdftotext often puts no
    empty line between paragraphs; then a paragraph ends at a clearly short line that ends a sentence, and a
    short line without sentence punctuation after a paragraph end is a heading.
    """
    pages = [page.split("\n") for page in text.replace("\r", "").split("\f")]
    pages = [page for page in pages if any(line.strip() for line in page)]

    def key(line: str) -> str:
        return re.sub(r"\d+", "#", " ".join(line.split()))

    def edges(page: list[str]) -> set[int]:  # the first two and the last two lines that have text
        filled = [i for i, line in enumerate(page) if line.strip()]
        return set(filled[:2] + filled[-2:])

    counts = Counter(key(page[i]) for page in pages for i in edges(page))
    repeated = {k for k, n in counts.items() if n >= max(3, 0.3 * len(pages))}
    for page in pages:
        for i in edges(page):
            if key(page[i]) in repeated or re.fullmatch(r"[-–—\s]*\d{1,4}[-–—\s]*", page[i]):
                page[i] = ""
    lengths = sorted(len(line.strip()) for page in pages for line in page if line.strip())
    width = lengths[int(0.9 * (len(lengths) - 1))] if lengths else 0  # length of a full line
    ends_sentence = re.compile(r"[.!?…:][\"”’»)\]]*$")

    def page_paragraphs(page: list[str]) -> tuple[list[str], bool]:
        """The paragraphs of a page, and whether the last one runs to the page end with a full last line."""
        out, current, runs_on = [], [], False
        lines = [line.strip() for line in page] + [""]
        for line, following in zip(lines, lines[1:]):
            if not line:
                if current:
                    out.append("\n".join(current))
                    current = []
                continue
            current.append(line)
            heading = len(current) == 1 and len(line) < 0.6 * width and not ends_sentence.search(line) and following[:1].isupper()
            ended = heading or bool(ends_sentence.search(line) and len(line) < 0.75 * width)
            runs_on = not ended and len(line) >= 0.75 * width
            if ended:
                out.append("\n".join(current))
                current = []
        return [_join_lines(b) for b in out], runs_on

    blocks: list[str] = []
    open_end = False  # the previous page ended in the middle of a paragraph
    for page in pages:
        page_blocks, runs_on = page_paragraphs(page)
        continues = open_end or (blocks and blocks[-1][-1] not in ".!?…:;\"”’»)]" and page_blocks[:1] and page_blocks[0][0].islower())
        open_end = runs_on
        if blocks and page_blocks and continues:
            blocks[-1] = _join_lines(blocks[-1] + "\n" + page_blocks.pop(0))
        blocks += page_blocks
    return blocks


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


def _on(props: ET.Element | None, tag: str) -> bool:
    """A run property such as <w:i/> is on unless its value says off."""
    el = props.find(W + tag) if props is not None else None
    return el is not None and el.get(W + "val", "true").lower() not in ("0", "false", "none")


def _emphasis(parts: list[tuple[str, str]]) -> str:
    """Joins (marker, text) parts; italic and bold text gets Markdown marks ("*", "**", "***").

    Neighbouring parts with the same marks are joined first, and spaces stay outside the marks."""
    merged: list[list[str]] = []
    for mark, text in parts:
        if merged and merged[-1][0] == mark:
            merged[-1][1] += text
        else:
            merged.append([mark, text])
    out = []
    for mark, text in merged:
        core = text.strip()
        if not mark or not core or "\n" in core:
            out.append(text)
            continue
        lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
        out.append(f"{lead}{mark}{core}{mark}{trail}")
    return "".join(out)


def _para_text(p: ET.Element, footnote_marker=None, marks: bool = True) -> str:
    """Text of one paragraph, with italic and bold as Markdown marks. Nested paragraphs (text boxes) and
    compatibility fallbacks are skipped here: text boxes are read as paragraphs of their own, and a fallback
    repeats content that is already present."""
    parts: list[tuple[str, str]] = []

    def walk(el: ET.Element, mark: str) -> None:
        for child in el:
            tag = child.tag
            if tag in (W + "txbxContent", MC_FALLBACK):
                continue
            if tag == W + "r":
                props = child.find(W + "rPr")
                run_mark = ("**" if _on(props, "b") else "") + ("*" if _on(props, "i") else "") if marks else ""
                walk(child, run_mark)
            elif tag == W + "t":
                parts.append((mark, child.text or ""))
            elif tag == W + "tab":
                parts.append(("", "\t"))
            elif tag in (W + "br", W + "cr"):
                parts.append(("", "\n"))
            elif tag == W + "noBreakHyphen":
                parts.append((mark, "‑"))
            elif tag in (W + "footnoteReference", W + "endnoteReference") and footnote_marker:
                parts.append(("", footnote_marker(("e" if tag == W + "endnoteReference" else "f") + child.get(W + "id"))))
            else:
                walk(child, mark)

    walk(p, "")
    return _emphasis(parts)


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


def _roman(n: int) -> str:
    out = ""
    for value, letters in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"),
                           (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= value:
            out, n = out + letters, n - value
    return out


def _number(n: int, fmt: str) -> str:
    if fmt in ("lowerLetter", "upperLetter"):
        text = ""
        while n:
            n, rest = divmod(n - 1, 26)
            text = chr(97 + rest) + text
        return text.upper() if fmt == "upperLetter" else text
    if fmt in ("lowerRoman", "upperRoman"):
        return _roman(n).upper() if fmt == "upperRoman" else _roman(n)
    return str(n)


class _Numbering:
    """The numbers of numbered paragraphs ("1.", "a)", "•"), counted as Word counts them."""

    def __init__(self, root: ET.Element | None):
        self.levels: dict[str, dict[int, tuple[str, str, int]]] = {}  # numId → level → (format, text, start)
        self.counters: dict[str, list[int]] = {}
        if root is None:
            return
        abstract = {}
        for a in root.iter(W + "abstractNum"):
            levels = {}
            for lvl in a.iter(W + "lvl"):
                get = lambda tag, default: (lvl.find(W + tag).get(W + "val") if lvl.find(W + tag) is not None else default)  # noqa: E731
                levels[int(lvl.get(W + "ilvl", "0"))] = (get("numFmt", "decimal"), get("lvlText", "%1."), int(get("start", "1")))
            abstract[a.get(W + "abstractNumId")] = levels
        for num in root.iter(W + "num"):
            ref = num.find(W + "abstractNumId")
            if ref is not None:
                self.levels[num.get(W + "numId")] = abstract.get(ref.get(W + "val"), {})

    def prefix(self, num_id: str, level: int) -> str:
        levels = self.levels.get(num_id)
        if not levels or level not in levels or num_id == "0":
            return ""
        fmt, text, _ = levels[level]
        if fmt == "bullet":
            return "•"
        if fmt == "none":
            return ""
        counters = self.counters.setdefault(num_id, [levels[i][2] - 1 if i in levels else 0 for i in range(9)])
        counters[level] += 1
        for deeper in range(level + 1, 9):  # a new item restarts the levels below it
            counters[deeper] = levels[deeper][2] - 1 if deeper in levels else 0
        return re.sub(r"%(\d)", lambda m: _number(counters[int(m.group(1)) - 1], levels.get(int(m.group(1)) - 1, (fmt,))[0]), text)


def _docx_blocks(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        part = lambda name: _parse_xml(_zip_read(z, name)) if name in names else None  # noqa: E731
        doc = _parse_xml(_zip_read(z, "word/document.xml"))
        styles, notes, endnotes, numbering = (part(f"word/{n}.xml") for n in ("styles", "footnotes", "endnotes", "numbering"))

    # Paragraph styles: heading level and numbering, also when a style inherits them (basedOn) or sets an outline
    # level. w:name in styles.xml is English ("heading 1") whatever the language of Word is.
    style_info: dict[str, dict] = {}
    if styles is not None:
        for style in styles.iter(W + "style"):
            name = style.find(W + "name")
            value = (name.get(W + "val") if name is not None else "").lower()
            m = re.fullmatch(r"heading (\d)", value)
            outline = style.find(f"{W}pPr/{W}outlineLvl")
            num = style.find(f"{W}pPr/{W}numPr")
            based = style.find(W + "basedOn")
            level = int(m.group(1)) if m else 1 if value == "title" else (
                int(outline.get(W + "val")) + 1 if outline is not None and outline.get(W + "val", "9").isdigit() and int(outline.get(W + "val")) < 6 else None)
            style_info[style.get(W + "styleId")] = {
                "level": level, "based": based.get(W + "val") if based is not None else None,
                "num": (num.find(W + "numId").get(W + "val"), int(num.find(W + "ilvl").get(W + "val")) if num.find(W + "ilvl") is not None else 0)
                if num is not None and num.find(W + "numId") is not None else None,
            }

    def inherited(style_id: str | None, key: str):
        for _ in range(10):  # follow basedOn, but never in a circle
            info = style_info.get(style_id or "")
            if not info:
                return None
            if info[key] is not None:
                return info[key]
            style_id = info["based"]
        return None

    footnotes = {}  # key: "f<id>" for footnotes, "e<id>" for endnotes; both become "[^n]" notes
    for prefix, root, tag in (("f", notes, "footnote"), ("e", endnotes, "endnote")):
        if root is None:
            continue
        for note in root.iter(W + tag):
            if note.get(W + "type"):  # separator lines
                continue
            paras = (_para_text(p).strip() for p in note.iter(W + "p"))
            footnotes[prefix + note.get(W + "id")] = " ".join(text for text in paras if text)

    numbers = _Numbering(numbering)
    blocks = []
    count = 0
    for p in _paragraphs(doc):
        ids = []

        def marker(note_id, ids=ids, base=count):
            ids.append(note_id)
            return f"[^{base + len(ids)}]"

        style = p.find(f"{W}pPr/{W}pStyle")
        style_id = style.get(W + "val") if style is not None else None
        outline = p.find(f"{W}pPr/{W}outlineLvl")
        level = inherited(style_id, "level")
        if outline is not None and outline.get(W + "val", "9").isdigit() and int(outline.get(W + "val")) < 6:
            level = int(outline.get(W + "val")) + 1
        text = _para_text(p, marker, marks=not level).strip()
        if not text:
            continue
        num = p.find(f"{W}pPr/{W}numPr")
        num_ref = ((num.find(W + "numId").get(W + "val") if num.find(W + "numId") is not None else None,
                    int(num.find(W + "ilvl").get(W + "val")) if num.find(W + "ilvl") is not None else 0)
                   if num is not None else inherited(style_id, "num"))
        if level:
            text = "#" * level + " " + " ".join(text.split())
        elif num_ref and num_ref[0]:
            prefix = numbers.prefix(num_ref[0], num_ref[1])
            if prefix:
                text = f"{prefix} {text}"
        for i, note_id in enumerate(ids, 1):
            text += f"\n[^{count + i}]: {footnotes.get(note_id, '')}"
        count += len(ids)
        blocks.append(text)
    return blocks


# --- EPUB -------------------------------------------------------------------

_NOTE_TYPES = {"footnote", "endnote", "rearnote", "note", "doc-footnote", "doc-endnote"}
_NOTE_LISTS = {"footnotes", "endnotes", "rearnotes", "doc-endnotes", "doc-footnotes"}
_VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "col", "area", "base", "source"}


def _kinds(attrs: dict) -> set[str]:
    return set((attrs.get("epub:type") or "").split()) | set((attrs.get("role") or "").split())


class _NoteCollector(HTMLParser):
    """First pass over an EPUB part: the texts of its footnotes and endnotes, by element id."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.notes: dict[str, str] = {}
        self.stack: list[str] = []
        self.in_list = 0           # depth of an enclosing notes list (0: none)
        self.capture: tuple[str, int] | None = None  # (id, depth) of the note being read
        self.buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        kinds = _kinds(attrs)
        if tag not in _VOID:
            self.stack.append(tag)
        if kinds & _NOTE_LISTS and not self.in_list:
            self.in_list = len(self.stack)
        note = kinds & _NOTE_TYPES or (self.in_list and tag in ("li", "aside", "div", "p", "section"))
        if self.capture is None and note and attrs.get("id"):
            self.capture, self.buf = (attrs["id"], len(self.stack)), []
        if tag == "br" and self.capture:
            self.buf.append(("", " "))

    def handle_endtag(self, tag):
        if tag in _VOID or tag not in self.stack:
            return
        while self.stack and self.stack.pop() != tag:
            pass
        if self.capture and len(self.stack) < self.capture[1]:
            text = " ".join(_emphasis(self.buf).split())
            text = re.sub(r"^(\[?\d{1,4}\]?[.)]?|[↩↑^*])\s+", "", text)
            self.notes[self.capture[0]] = re.sub(r"\s*[↩↑⤴]+\s*$", "", text)
            self.capture = None
        if self.in_list and len(self.stack) < self.in_list:
            self.in_list = 0

    def handle_data(self, data):
        if self.capture:
            marks = {_HTMLBlocks.MARKS.get(tag) for tag in self.stack}
            self.buf.append((("**" if "**" in marks else "") + ("*" if "*" in marks else ""), data))


class _HTMLBlocks(HTMLParser):
    """Paragraphs of an (X)HTML part. Italic and bold become Markdown marks. A note reference becomes a "[^n]" mark
    and the note text a "[^n]: text" line below the paragraph; the notes themselves are not read as text."""

    BLOCK = {"p", "div", "li", "blockquote", "br", "tr", "td", "th", "section", "article", "hr", "dt", "dd",
             "h1", "h2", "h3", "h4", "h5", "h6", "aside"}
    SKIP = {"script", "style", "head"}
    MARKS = {"i": "*", "em": "*", "cite": "*", "b": "**", "strong": "**"}

    def __init__(self, notes: dict[str, str] | None = None, resolve=None, counter: list[int] | None = None):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.buf: list[tuple[str, str]] = []
        self.skip = 0
        self.level = 0
        self.sup = None  # position in buf where an open <sup> started
        self.notes = notes or {}
        self.resolve = resolve or (lambda href: href.partition("#")[2])  # href → key in notes
        self.counter = counter if counter is not None else [0]
        self.pending: list[tuple[int, str]] = []  # notes of the paragraph being read
        self.stack: list[tuple[str, str]] = []    # (tag, role) of open elements: "skip", "ref", "mark" or ""

    def mark(self) -> str:
        if self.level:
            return ""
        marks = [r for t, r in self.stack if r in ("*", "**")]
        return ("**" if "**" in marks else "") + ("*" if "*" in marks else "")

    def flush(self):
        text = " ".join(_emphasis(self.buf).split())
        self.buf = []
        self.sup = None
        if text:
            text = "#" * self.level + " " + text if self.level else text
            text = re.sub(r"\s+(\[\^\d+\])", r"\1", text)
            self.blocks.append(text + "".join(f"\n[^{n}]: {note}" for n, note in self.pending))
            self.pending = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        kinds = _kinds(attrs)
        if tag in self.SKIP or kinds & (_NOTE_TYPES | _NOTE_LISTS) or (attrs.get("id") and attrs["id"] in self.notes
                                                                      and tag in ("li", "aside", "div", "p", "section")):
            role = "skip"
            self.skip += 1
        elif tag == "a" and not self.skip and (kinds & {"noteref", "doc-noteref"} or self.resolve(attrs.get("href", "")) in self.notes):
            key = self.resolve(attrs.get("href", ""))
            if key in self.notes:
                self.counter[0] += 1
                self.pending.append((self.counter[0], self.notes[key]))
                self.buf.append(("", f"[^{self.counter[0]}]"))
                role = "ref"
                self.skip += 1
            else:
                role = ""
        else:
            role = self.MARKS.get(tag, "")
        if tag == "sup" and not self.skip:
            self.sup = len(self.buf)
        elif tag in self.BLOCK and not self.skip:
            self.flush()
            self.level = int(tag[1]) if tag[0] == "h" and tag != "hr" else 0
        if tag not in _VOID:
            self.stack.append((tag, role))

    def handle_endtag(self, tag):
        if tag in _VOID or tag not in (t for t, _ in self.stack):
            return
        while self.stack:
            open_tag, role = self.stack.pop()
            if role in ("skip", "ref"):
                self.skip = max(0, self.skip - 1)
            if open_tag == tag:
                break
        if self.skip:
            return
        if tag == "sup" and self.sup is not None:
            # A footnote number written as superscript: "word<sup>3</sup>" must not become "word3".
            number = "".join(text for _, text in self.buf[self.sup:]).strip()
            if re.fullmatch(r"\d{1,4}", number):
                self.buf[self.sup:] = [("", f"[{number}]")]
            self.sup = None
        elif tag in self.BLOCK:
            self.flush()
            self.level = 0

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if not self.skip:
            self.buf.append((self.mark(), data))


def _epub_blocks(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        container = _parse_xml(_zip_read(z, "META-INF/container.xml"))
        opf_path = next(e.get("full-path") for e in container.iter() if e.tag.endswith("}rootfile"))
        opf = _parse_xml(_zip_read(z, opf_path))
        hrefs = {e.get("id"): e.get("href") for e in opf.iter() if e.tag.endswith("}item")}
        parts = []
        for itemref in (e for e in opf.iter() if e.tag.endswith("}itemref")):
            href = hrefs.get(itemref.get("idref"))
            if not href:
                continue
            name = posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), urllib.parse.unquote(href)))
            if name not in z.namelist():
                raise PipelineError(t("epub_missing_part", name=name))
            parts.append((name, _zip_read(z, name).decode("utf-8", "replace")))

    # Notes can be in the same part as their reference or in a notes chapter: they are collected first.
    notes: dict[str, str] = {}
    for name, text in parts:
        collector = _NoteCollector()
        collector.feed(text)
        collector.close()
        notes.update({f"{name}#{key}": value for key, value in collector.notes.items()})
    blocks, counter = [], [0]
    for name, text in parts:
        def resolve(href: str, base=name) -> str:
            target, _, fragment = href.partition("#")
            target = posixpath.normpath(posixpath.join(posixpath.dirname(base), urllib.parse.unquote(target))) if target else base
            return f"{target}#{fragment}"

        local = {key.partition("#")[2]: value for key, value in notes.items() if key.startswith(name + "#")}
        parser = _HTMLBlocks({**notes, **local}, resolve, counter)
        parser.feed(text)
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
