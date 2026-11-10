"""The glyphs of PDF pages with their position and text, read from the content streams (standard library only).

pdftotext gives right-to-left text (Arabic, Hebrew) in visual order and does not say where one glyph ends:
when one glyph stands for several letters (a ligature, or an /ActualText span as browsers write them for every
Arabic cluster) its letters cannot be put back in reading order. This reader gives each glyph, or each
/ActualText span, with its box. Sorted by position, the text is exact.

Only what that needs is read. A file this reader does not support (encryption, an unknown filter) raises
PdfError; the caller then keeps pdftotext's text."""

from __future__ import annotations

import base64
import re
import zlib
from dataclasses import dataclass


class PdfError(Exception):
    pass


@dataclass
class Glyph:
    text: str     # "" when the font gives no text for the glyph
    x0: float     # page coordinates as pdftotext gives them: points from the top left of the crop box
    x1: float
    y: float      # middle of the letter body, between baseline and x-height
    size: float   # type size in points
    order: int    # position in the content stream


class _Name(str):
    pass


class _Op(str):
    pass


@dataclass(frozen=True)
class _Ref:
    num: int
    gen: int


@dataclass
class _Stream:
    dict: dict
    raw: bytes


_TOKEN = re.compile(rb"""
    (?P<ws>[\s\x00]+|%[^\r\n]*)
  | (?P<num>[+-]?(?:\d+\.?\d*|\.\d+)(?![^\s\x00()<>\[\]{}/%]))
  | (?P<name>/[^\s\x00()<>\[\]{}/%]*)
  | (?P<dopen><<) | (?P<dclose>>>)
  | (?P<hex><[0-9A-Fa-f\s]*>)
  | (?P<aopen>\[) | (?P<aclose>\])
  | (?P<lit>\()
  | (?P<brace>[{}])
  | (?P<kw>[^\s\x00()<>\[\]{}/%]+)
""", re.X)

_ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f"}


class _Parser:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.pos = data, pos
        self.ahead: list = []

    def _literal(self) -> bytes:
        data, i, depth, out = self.data, self.pos, 1, bytearray()
        while i < len(data):
            c = data[i]
            if c == 0x5C:  # backslash
                i += 1
                if i >= len(data):
                    break
                c = data[i]
                if c in _ESCAPES:
                    out += _ESCAPES[c]
                elif 0x30 <= c <= 0x37:
                    m = re.match(rb"[0-7]{1,3}", data[i:i + 3])
                    out.append(int(m[0], 8) & 0xFF)
                    i += len(m[0]) - 1
                elif c == 0x0D:
                    if data[i + 1:i + 2] == b"\n":
                        i += 1
                elif c != 0x0A:
                    out.append(c)
            elif c == 0x28:
                depth += 1
                out.append(c)
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    self.pos = i + 1
                    return bytes(out)
                out.append(c)
            else:
                out.append(c)
            i += 1
        raise PdfError("unterminated string")

    def _raw_token(self):
        while True:
            m = _TOKEN.match(self.data, self.pos)
            if not m:
                if self.pos >= len(self.data):
                    return None
                raise PdfError(f"bad token at {self.pos}")
            self.pos = m.end()
            kind = m.lastgroup
            text = m[kind]
            if kind == "ws" or kind == "brace":
                continue
            if kind == "num":
                return float(text) if b"." in text else int(text)
            if kind == "name":
                return _Name(re.sub(rb"#([0-9A-Fa-f]{2})", lambda h: bytes([int(h[1], 16)]), text[1:]).decode("latin-1"))
            if kind == "hex":
                digits = re.sub(rb"\s", b"", text[1:-1])
                return bytes.fromhex((digits + b"0" * (len(digits) % 2)).decode())
            if kind == "lit":
                return self._literal()
            return _Op(text.decode("latin-1")) if kind == "kw" else _Op(text.decode())

    def token(self):
        return self.ahead.pop(0)[0] if self.ahead else self._raw_token()

    def peek(self, n: int):
        while len(self.ahead) < n:
            start = self.pos
            self.ahead.append((self._raw_token(), start))
        return self.ahead[n - 1][0]

    def rewind(self) -> None:
        """Forget the tokens read ahead: pos is then right after the last value."""
        if self.ahead:
            self.pos = self.ahead[0][1]
            self.ahead = []

    def value(self, refs: bool = True):
        tok = self.token()
        return self._complete(tok, refs)

    def _complete(self, tok, refs: bool):
        if tok == "[" and isinstance(tok, _Op):
            items = []
            while True:
                t = self.token()
                if t is None:
                    raise PdfError("unterminated array")
                if isinstance(t, _Op) and t == "]":
                    return items
                items.append(self._complete(t, refs))
        if tok == "<<" and isinstance(tok, _Op):
            d = {}
            while True:
                k = self.token()
                if k is None:
                    raise PdfError("unterminated dictionary")
                if isinstance(k, _Op) and k == ">>":
                    return d
                d[str(k)] = self._complete(self.token(), refs)
        if refs and isinstance(tok, int) and not isinstance(tok, bool):
            gen, r = self.peek(1), self.peek(2)
            if isinstance(gen, int) and isinstance(r, _Op) and r == "R":
                self.ahead = self.ahead[2:]
                return _Ref(tok, gen)
        if isinstance(tok, _Op) and tok in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[tok]
        return tok


_OBJ = re.compile(rb"(?<![0-9])(\d+)\s+(\d+)\s+obj\b")
_STREAM = re.compile(rb"[ \t\r\n]*stream\r?\n")


class Document:
    def __init__(self, data: bytes):
        if b"/Encrypt" in data:
            raise PdfError("encrypted")
        self.data = data
        self.objects: dict[int, object] = {}
        self.roots: list[_Ref] = []
        self._scan()
        self._fonts: dict[int, _Font | None] = {}
        self._pages: list[tuple[dict, dict]] | None = None

    def _scan(self) -> None:
        """Every object in file order (a later definition wins, as an incremental update does), then the objects
        inside object streams. The cross-reference table is not needed for this."""
        data, pos = self.data, 0
        while m := _OBJ.search(data, pos):
            parser = _Parser(data, m.end())
            try:
                value = parser.value()
            except (PdfError, ValueError, IndexError):
                pos = m.end()
                continue
            parser.rewind()
            s = _STREAM.match(data, parser.pos) if isinstance(value, dict) else None
            if s:
                start = s.end()
                length = value.get("Length")
                if isinstance(length, int) and data[start + length:start + length + 12].lstrip().startswith(b"endstream"):
                    stop = start + length
                else:
                    stop = data.find(b"endstream", start)
                    if stop < 0:
                        break
                value = _Stream(value, data[start:stop])
                pos = stop + 9
            else:
                pos = parser.pos
            self.objects[int(m[1])] = value
            d = value.dict if isinstance(value, _Stream) else value
            if isinstance(d, dict) and d.get("Type") == "XRef" and isinstance(d.get("Root"), _Ref):
                self.roots.append(d["Root"])
        for m in re.finditer(rb"trailer\s*<<", data):
            try:
                trailer = _Parser(data, m.end() - 2).value()
            except PdfError:
                continue
            if isinstance(trailer, dict) and isinstance(trailer.get("Root"), _Ref):
                self.roots.append(trailer["Root"])
        for obj in list(self.objects.values()):
            if isinstance(obj, _Stream) and obj.dict.get("Type") == "ObjStm":
                try:
                    self._object_stream(obj)
                except (PdfError, ValueError, zlib.error):
                    continue

    def _object_stream(self, stream: _Stream) -> None:
        data = self.decode(stream)
        first, n = self.get(stream.dict.get("First")), self.get(stream.dict.get("N"))
        header = _Parser(data[:first])
        pairs = [(header.value(refs=False), header.value(refs=False)) for _ in range(n)]
        for num, offset in pairs:
            if num not in self.objects:
                self.objects[num] = _Parser(data, first + offset).value()

    def get(self, value, depth: int = 0):
        while isinstance(value, _Ref) and depth < 32:
            value = self.objects.get(value.num)
            depth += 1
        return value

    def decode(self, stream: _Stream) -> bytes:
        filters = self.get(stream.dict.get("Filter"))
        filters = [] if filters is None else filters if isinstance(filters, list) else [filters]
        parms = self.get(stream.dict.get("DecodeParms"))
        parms = parms if isinstance(parms, list) else [parms] * len(filters)
        data = stream.raw
        for f, p in zip(filters, parms):
            f, p = self.get(f), self.get(p) or {}
            if f in ("FlateDecode", "Fl"):
                data = zlib.decompressobj().decompress(data)
                if self.get(p.get("Predictor", 1)) > 1:
                    data = _png_unpredict(data, self.get(p.get("Columns", 1)) * self.get(p.get("Colors", 1)))
            elif f in ("ASCIIHexDecode", "AHx"):
                digits = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
                data = bytes.fromhex((digits + b"0" * (len(digits) % 2)).decode())
            elif f in ("ASCII85Decode", "A85"):
                data = base64.a85decode(re.sub(rb"\s", b"", data).removeprefix(b"<~").split(b"~>")[0])
            else:
                raise PdfError(f"filter {f}")
        return data

    def pages(self) -> list[tuple[dict, dict]]:
        """Each page with its inherited attributes (Resources, MediaBox, CropBox, Rotate), in page order."""
        catalog = None
        for ref in reversed(self.roots):
            catalog = self.get(ref)
            if isinstance(catalog, dict):
                break
        if not isinstance(catalog, dict):
            catalog = next((o for o in self.objects.values() if isinstance(o, dict) and o.get("Type") == "Catalog"), None)
        if catalog is None:
            raise PdfError("no catalog")
        out: list[tuple[dict, dict]] = []
        seen: set[int] = set()

        def walk(ref, inherited: dict, depth: int) -> None:
            if isinstance(ref, _Ref):
                if ref.num in seen or depth > 64:
                    return
                seen.add(ref.num)
            node = self.get(ref)
            if not isinstance(node, dict):
                return
            attrs = dict(inherited)
            for key in ("Resources", "MediaBox", "CropBox", "Rotate"):
                if key in node:
                    attrs[key] = self.get(node[key])
            if "Kids" in node:
                for kid in self.get(node["Kids"]) or []:
                    walk(kid, attrs, depth + 1)
            else:
                out.append((node, attrs))

        walk(catalog.get("Pages"), {}, 0)
        return out

    def glyphs(self, page_index: int) -> list[Glyph]:
        if self._pages is None:
            self._pages = self.pages()
        page, attrs = self._pages[page_index]
        if (self.get(attrs.get("Rotate")) or 0) % 360:
            raise PdfError("rotated page")
        box = [float(self.get(v)) for v in (attrs.get("CropBox") or attrs.get("MediaBox") or [0, 0, 612, 792])]
        left, top = min(box[0], box[2]), max(box[1], box[3])
        content = self.get(page.get("Contents"))
        parts = content if isinstance(content, list) else [content]
        data = b"\n".join(self.decode(self.get(p)) for p in parts if isinstance(self.get(p), _Stream))
        out: list[Glyph] = []
        _Interpreter(self, out).run(data, attrs.get("Resources") or {}, (1, 0, 0, 1, 0, 0), 0)
        for g in out:
            g.x0, g.x1, g.y = g.x0 - left, g.x1 - left, top - g.y
        return out

    def font(self, ref) -> _Font | None:
        key = ref.num if isinstance(ref, _Ref) else id(ref)
        if key not in self._fonts:
            d = self.get(ref)
            self._fonts[key] = _Font(self, d) if isinstance(d, dict) else None
        return self._fonts[key]


def _png_unpredict(data: bytes, columns: int) -> bytes:
    rows, prev, out = len(data) // (columns + 1), bytearray(columns), bytearray()
    for r in range(rows):
        kind, row = data[r * (columns + 1)], bytearray(data[r * (columns + 1) + 1:(r + 1) * (columns + 1)])
        for i in range(columns):
            left = row[i - 1] if i else 0
            up, ul = prev[i], prev[i - 1] if i else 0
            if kind == 1:
                row[i] = (row[i] + left) & 0xFF
            elif kind == 2:
                row[i] = (row[i] + up) & 0xFF
            elif kind == 3:
                row[i] = (row[i] + (left + up) // 2) & 0xFF
            elif kind == 4:
                p = left + up - ul
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
                row[i] = (row[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else ul)) & 0xFF
        out += row
        prev = row
    return bytes(out)


def _utf16(hexbytes: bytes) -> str:
    raw = bytes.fromhex(re.sub(rb"\s", b"", hexbytes).decode())
    return raw.decode("utf-16-be", "replace") if len(raw) % 2 == 0 else raw.decode("latin-1")


def _to_unicode(data: bytes) -> dict[int, str]:
    """Code -> text from a ToUnicode CMap. Hex strings may contain spaces ("<0644 0627>")."""
    table: dict[int, str] = {}
    hexa = rb"<([0-9A-Fa-f\s]*)>"
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(hexa + rb"\s*" + hexa, block[1]):
            table[int(re.sub(rb"\s", b"", src) or b"0", 16)] = _utf16(dst)
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, dst in re.findall(hexa + rb"\s*" + hexa + rb"\s*(<[0-9A-Fa-f\s]*>|\[[^\]]*\])", block[1]):
            lo, hi = int(re.sub(rb"\s", b"", lo) or b"0", 16), int(re.sub(rb"\s", b"", hi) or b"0", 16)
            if dst.startswith(b"["):
                for i, item in enumerate(re.findall(hexa, dst)):
                    table[lo + i] = _utf16(item)
            elif hi - lo < 0x10000:
                digits = re.sub(rb"\s", b"", dst[1:-1])
                base = int(digits, 16)
                for i in range(hi - lo + 1):
                    table[lo + i] = _utf16(f"{base + i:0{len(digits)}X}".encode())
    return table


class _Font:
    def __init__(self, doc: Document, d: dict):
        get = doc.get
        self.two_byte = get(d.get("Subtype")) == "Type0"
        self.scale = 0.001
        self.widths: dict[int, float] = {}
        if self.two_byte:
            desc = get((get(d.get("DescendantFonts")) or [{}])[0]) or {}
            self.default = float(get(desc.get("DW", 1000)))
            w, i = [get(x) for x in get(desc.get("W")) or []], 0
            while i < len(w):
                if i + 1 < len(w) and isinstance(w[i + 1], list):
                    for j, width in enumerate(w[i + 1]):
                        self.widths[w[i] + j] = float(get(width))
                    i += 2
                elif i + 2 < len(w):
                    for code in range(int(w[i]), int(w[i + 1]) + 1):
                        self.widths[code] = float(w[i + 2])
                    i += 3
                else:
                    break
        else:
            self.default = float(get(get(d.get("FontDescriptor") or {}) or {}).get("MissingWidth", 500))
            first = get(d.get("FirstChar", 0))
            for j, width in enumerate(get(d.get("Widths")) or []):
                self.widths[first + j] = float(get(width))
            if get(d.get("Subtype")) == "Type3":
                self.scale = float((get(d.get("FontMatrix")) or [0.001])[0])
        cmap = get(d.get("ToUnicode"))
        self.unicode = _to_unicode(doc.decode(cmap)) if isinstance(cmap, _Stream) else {}
        encoding = get(d.get("Encoding"))
        encoding = get(encoding.get("BaseEncoding")) if isinstance(encoding, dict) else encoding
        self.codec = {"MacRomanEncoding": "mac_roman", "WinAnsiEncoding": "cp1252"}.get(encoding, "latin-1")

    def codes(self, s: bytes):
        """(code, text, width) of each glyph; text is "" when the font does not say which letters it shows."""
        if self.two_byte:
            for i in range(0, len(s) - 1, 2):
                code = s[i] << 8 | s[i + 1]
                yield code, self.unicode.get(code, ""), self.widths.get(code, self.default) * self.scale
        else:
            for code in s:
                text = self.unicode.get(code)
                if text is None:  # as pdftotext does: the font's encoding tells the letter
                    text = "" if code < 32 else bytes([code]).decode(self.codec, "replace")
                yield code, text, self.widths.get(code, self.default) * self.scale


def _mul(m, n):
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + b * r, a * q + b * s, c * p + d * r, c * q + d * s, e * p + f * r + t, e * q + f * s + u)


def _apply(m, x, y):
    return x * m[0] + y * m[2] + m[4], x * m[1] + y * m[3] + m[5]


class _Interpreter:
    def __init__(self, doc: Document, out: list[Glyph]):
        self.doc, self.out = doc, out

    def run(self, data: bytes, resources, ctm, depth: int) -> None:
        doc, get = self.doc, self.doc.get
        resources = get(resources) or {}
        fonts = get(resources.get("Font")) or {}
        state = {"ctm": ctm, "tc": 0.0, "tw": 0.0, "th": 1.0, "tl": 0.0, "rise": 0.0, "font": None, "fs": 0.0}
        stack: list[dict] = []
        tm = tlm = (1, 0, 0, 1, 0, 0)
        spans: list[list | None] = []  # open marked-content sequences: [text, glyphs] for /ActualText, else None
        parser, operands = _Parser(data), []

        def show(s: bytes) -> None:
            nonlocal tm
            font, fs, th = state["font"], state["fs"], state["th"]
            if font is None:
                return
            for code, text, w in font.codes(s):
                trm = _mul((fs * th, 0, 0, fs, 0, state["rise"]), _mul(tm, state["ctm"]))
                x0, _ = _apply(trm, 0, 0)
                x1, _ = _apply(trm, w, 0)
                _, y = _apply(trm, w / 2, 0.3)
                size = abs(trm[3]) or abs(trm[1])
                glyph = Glyph(text, min(x0, x1), max(x0, x1), y, size, len(self.out))
                span = next((sp for sp in reversed(spans) if sp is not None), None)
                if span is not None:
                    span[1].append(glyph)
                else:
                    self.out.append(glyph)
                spacing = state["tw"] if code == 32 and not font.two_byte else 0.0
                tm = _mul((1, 0, 0, 1, (w * fs + state["tc"] + spacing) * th, 0), tm)

        while True:
            tok = parser.token()
            if tok is None:
                break
            if not isinstance(tok, _Op) or tok in ("[", "<<"):
                operands.append(parser._complete(tok, refs=False))
                continue
            op, args = str(tok), operands
            operands = []
            try:
                if op == "q":
                    stack.append(dict(state))
                elif op == "Q":
                    if stack:
                        state = stack.pop()
                elif op == "cm":
                    state["ctm"] = _mul(tuple(float(a) for a in args[:6]), state["ctm"])
                elif op == "BT":
                    tm = tlm = (1, 0, 0, 1, 0, 0)
                elif op == "Tf":
                    state["font"] = doc.font(fonts.get(str(args[0])))
                    state["fs"] = float(args[1])
                elif op == "Tc":
                    state["tc"] = float(args[0])
                elif op == "Tw":
                    state["tw"] = float(args[0])
                elif op == "Tz":
                    state["th"] = float(args[0]) / 100
                elif op == "TL":
                    state["tl"] = float(args[0])
                elif op == "Ts":
                    state["rise"] = float(args[0])
                elif op in ("Td", "TD"):
                    if op == "TD":
                        state["tl"] = -float(args[1])
                    tlm = _mul((1, 0, 0, 1, float(args[0]), float(args[1])), tlm)
                    tm = tlm
                elif op == "Tm":
                    tm = tlm = tuple(float(a) for a in args[:6])
                elif op == "T*":
                    tlm = _mul((1, 0, 0, 1, 0, -state["tl"]), tlm)
                    tm = tlm
                elif op == "Tj":
                    show(args[0])
                elif op in ("'", '"'):
                    if op == '"':
                        state["tw"], state["tc"] = float(args[0]), float(args[1])
                    tlm = _mul((1, 0, 0, 1, 0, -state["tl"]), tlm)
                    tm = tlm
                    show(args[-1])
                elif op == "TJ":
                    for item in args[0]:
                        if isinstance(item, bytes):
                            show(item)
                        else:
                            tm = _mul((1, 0, 0, 1, -float(item) / 1000 * state["fs"] * state["th"], 0), tm)
                elif op == "BDC":
                    props = args[1] if len(args) > 1 else {}
                    if isinstance(props, _Name):
                        props = get((get(resources.get("Properties")) or {}).get(str(props)))
                    text = props.get("ActualText") if isinstance(props, dict) else None
                    spans.append([_text_string(get(text)), []] if isinstance(get(text), bytes) else None)
                elif op == "BMC":
                    spans.append(None)
                elif op == "EMC":
                    span = spans.pop() if spans else None
                    if span is not None and span[1]:
                        g = span[1]
                        letter = max(g, key=lambda x: x.x1 - x.x0)  # the widest glyph: a letter, not a sign
                        glyph = Glyph(span[0], min(x.x0 for x in g), max(x.x1 for x in g), letter.y,
                                      max(x.size for x in g), g[0].order)
                        outer = next((sp for sp in reversed(spans) if sp is not None), None)
                        (outer[1] if outer is not None else self.out).append(glyph)
                elif op == "Do" and depth < 8:
                    xobj = get((get(resources.get("XObject")) or {}).get(str(args[0])))
                    if isinstance(xobj, _Stream) and xobj.dict.get("Subtype") == "Form":
                        matrix = tuple(float(get(a)) for a in (get(xobj.dict.get("Matrix")) or (1, 0, 0, 1, 0, 0)))
                        self.run(doc.decode(xobj), xobj.dict.get("Resources") or resources,
                                 _mul(matrix, state["ctm"]), depth + 1)
                elif op == "ID":  # inline image data: skip to EI
                    m = re.compile(rb"\sEI(?=[\s\x00]|$)").search(data, parser.pos)
                    parser.pos = m.end() if m else len(data)
                    parser.ahead = []
            except (IndexError, TypeError, ValueError, AttributeError):
                continue


def _text_string(raw: bytes) -> str:
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", "replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    return raw.decode("latin-1")


def read(data: bytes, pages: list[int]) -> dict[int, list[Glyph]]:
    """Glyphs of the given pages (0-based). A page that cannot be read is left out."""
    doc = Document(data)
    out = {}
    for i in pages:
        try:
            out[i] = doc.glyphs(i)
        except (PdfError, ValueError, TypeError, IndexError, KeyError, zlib.error):
            continue
    return out
