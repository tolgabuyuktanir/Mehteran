"""Tables: spreadsheets (CSV, TSV, Excel .xlsx) read into Markdown tables, and Markdown tables in Word and HTML reports.

Standard library only. An .xlsx file is a zip of XML parts; it is read with the translation app's guarded readers
(pipeline.documents: no entity declarations, no member that unpacks to more than 100 MB). Large sheets are cut to
the limits below, and the text says so where it was cut.

Reports: the translation app's exporter (pipeline.export, used read-only) knows no tables. Each Markdown table is
replaced by a marker paragraph before the export, and the marker is then replaced by a real table in the HTML page
or in the Word document.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import io
import re
import secrets
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from .i18n import t

SPREADSHEETS = ("csv", "tsv", "xlsx")
MAX_ROWS = 1000      # data rows per table (sheet)
MAX_COLS = 40
MAX_CELL = 300       # characters per cell
MAX_SHEETS = 20
MAX_CHARS = 500_000  # the Markdown of one file

S_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DATE_FORMATS = set(range(14, 23)) | {45, 46, 47}  # Excel's built-in date and time formats


class TableError(ValueError):
    """The file cannot be read as a table; the message is shown to the user."""


# --- reading ------------------------------------------------------------------------

def read(path: Path) -> str:
    """A CSV, TSV or .xlsx file as Markdown: one table per sheet (an .xlsx sheet under a "## <name>" heading)."""
    ext = path.suffix.lower().lstrip(".")
    if ext == "xlsx":
        sheets, more = _xlsx_sheets(path)
        parts = [f"## {name}\n\n{markdown_table(rows)}" for name, rows in sheets]
        if not parts:
            raise TableError(t("table_empty", name=path.name))
        if more:
            parts.append(t("table_more_sheets", shown=MAX_SHEETS))
    else:
        rows = _delimited_rows(path, "\t" if ext == "tsv" else None)
        if not any(any(cell.strip() for cell in row) for row in rows):
            raise TableError(t("table_empty", name=path.name))
        parts = [markdown_table(rows)]
    text = "\n\n".join(parts)
    if len(text) > MAX_CHARS:
        text = text[:text.rfind("\n", 0, MAX_CHARS)] + "\n\n" + t("table_cut_chars", limit=f"{MAX_CHARS:,}")
    return text


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1254", "latin-1"):  # cp1254: Turkish Windows; latin-1 always decodes
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _delimited_rows(path: Path, delimiter: str | None) -> list[list[str]]:
    text = _decode(path.read_bytes())
    if delimiter is None:  # a CSV written by a European spreadsheet often uses ";"
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    try:
        return [row for row in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)]
    except csv.Error as e:
        raise TableError(t("table_unreadable", name=path.name, error=e)) from None


def _column(ref: str) -> int:
    """"C7" -> 2 (from 0)."""
    n = 0
    for ch in re.match(r"[A-Z]*", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def _xlsx_sheets(path: Path) -> tuple[list[tuple[str, list[list[str]]]], bool]:
    """The visible, non-empty sheets (at most MAX_SHEETS) and whether more were left out."""
    from pipeline.core import PipelineError
    from pipeline.documents import _parse_xml, _zip_read
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            xml = lambda name: _parse_xml(_zip_read(z, name))  # noqa: E731
            book = xml("xl/workbook.xml")
            rels = {r.get("Id"): r.get("Target", "") for r in xml("xl/_rels/workbook.xml.rels").iter(PKG_REL + "Relationship")}
            strings = [_rich_text(si) for si in xml("xl/sharedStrings.xml").iter(S_NS + "si")] \
                if "xl/sharedStrings.xml" in names else []
            dates = _date_styles(xml("xl/styles.xml")) if "xl/styles.xml" in names else set()
            pr = book.find(f"{S_NS}workbookPr")
            epoch = dt.datetime(1904, 1, 1) if pr is not None and pr.get("date1904") in ("1", "true") \
                else dt.datetime(1899, 12, 30)
            out = []
            for sheet in book.iter(S_NS + "sheet"):
                if sheet.get("state") in ("hidden", "veryHidden"):
                    continue
                target = rels.get(sheet.get(R_ID), "")
                target = target.lstrip("/") if target.startswith("/") else "xl/" + target
                if target not in names:
                    continue
                rows = _sheet_rows(xml(target), strings, dates, epoch)
                if not any(any(cell.strip() for cell in row) for row in rows):
                    continue
                if len(out) == MAX_SHEETS:
                    return out, True
                out.append((sheet.get("name") or target, rows))
            return out, False
    except (zipfile.BadZipFile, KeyError, ValueError, PipelineError) as e:
        raise TableError(t("table_unreadable", name=path.name, error=e)) from None


def _rich_text(si) -> str:
    """The text of a shared string or an inline string: its own <t>, or the <t> of each run (no phonetic hints)."""
    parts = []
    for child in si:
        if child.tag == S_NS + "t":
            parts.append(child.text or "")
        elif child.tag == S_NS + "r":
            parts += [node.text or "" for node in child.iter(S_NS + "t")]
    return "".join(parts)


def _date_styles(styles) -> set[int]:
    """The indexes of the cell styles that show a number as a date."""
    custom = {}
    for fmt in styles.iter(S_NS + "numFmt"):
        code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", fmt.get("formatCode", "")).lower()
        custom[int(fmt.get("numFmtId", "0"))] = bool(re.search(r"[dy]", code)) or bool(re.search(r"h.*m|m.*s", code))
    xfs = styles.find(f"{S_NS}cellXfs")
    out = set()
    for i, xf in enumerate(xfs if xfs is not None else []):
        fmt = int(xf.get("numFmtId", "0"))
        if fmt in DATE_FORMATS or custom.get(fmt):
            out.add(i)
    return out


def _number(value: str, is_date: bool, epoch: dt.datetime) -> str:
    try:
        number = float(value)
    except ValueError:
        return value
    if is_date and 0 <= number < 2_958_466:  # up to the year 9999
        moment = epoch + dt.timedelta(days=number)
        return moment.strftime("%Y-%m-%d %H:%M" if number % 1 else "%Y-%m-%d")
    return str(int(number)) if number.is_integer() and abs(number) < 1e15 else format(number, ".15g")


def _sheet_rows(sheet, strings: list[str], dates: set[int], epoch: dt.datetime) -> list[list[str]]:
    rows = []
    for row in sheet.iter(S_NS + "row"):
        cells: dict[int, str] = {}
        for n, c in enumerate(row.iter(S_NS + "c")):
            col = _column(c.get("r", "")) if c.get("r") else n
            kind, v = c.get("t", "n"), c.find(S_NS + "v")
            value = v.text or "" if v is not None else ""
            if kind == "s":
                value = strings[int(value)] if value.isdigit() and int(value) < len(strings) else ""
            elif kind == "inlineStr":
                node = c.find(S_NS + "is")
                value = _rich_text(node) if node is not None else ""
            elif kind == "b":
                value = "TRUE" if value == "1" else "FALSE"
            elif kind == "n" and value:
                value = _number(value, int(c.get("s", "0") or 0) in dates, epoch)
            if 0 <= col < 16384:
                cells[col] = value
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def _cell(value: str) -> str:
    value = " ".join(str(value).split())
    if len(value) > MAX_CELL:
        value = value[:MAX_CELL] + "…"
    return value.replace("\\", "\\\\").replace("|", "\\|")


def markdown_table(rows: list[list[str]]) -> str:
    """Rows (the first is the header) as a Markdown table, cut to MAX_ROWS rows and MAX_COLS columns with a note."""
    rows = [row for row in rows if any(str(cell).strip() for cell in row)]
    if not rows:
        return t("table_no_rows")
    width = max(len(row) for row in rows)
    cols = min(width, MAX_COLS)
    header, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(_cell(c) or " " for c in (header + [""] * cols)[:cols]) + " |",
             "|" + "---|" * cols]
    for row in body[:MAX_ROWS]:
        lines.append("| " + " | ".join(_cell(c) for c in (row + [""] * cols)[:cols]) + " |")
    notes = []
    if len(body) > MAX_ROWS:
        notes.append(t("table_cut_rows", shown=MAX_ROWS, total=len(body)))
    if width > MAX_COLS:
        notes.append(t("table_cut_cols", shown=MAX_COLS, total=width))
    return "\n".join(lines) + ("\n\n" + " ".join(notes) if notes else "")


# --- Markdown tables in reports -------------------------------------------------------

_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)]


def extract(markdown: str) -> tuple[str, dict[str, dict]]:
    """The Markdown with each table replaced by a marker paragraph, and {marker: {"rows", "align"}}.
    A table is a header line with "|", a separator line ("|---|:--:|") and the rows below it; code blocks are
    left alone."""
    lines = markdown.replace("\r\n", "\n").split("\n")
    nonce = secrets.token_hex(4)
    out, tables, fence, i = [], {}, False, 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and "|" in line and i + 1 < len(lines) and "|" in lines[i + 1] and _SEPARATOR.match(lines[i + 1]):
            header = _split_row(line)
            align = ["center" if c.strip().startswith(":") and c.strip().endswith(":") else
                     "right" if c.strip().endswith(":") else "" for c in _split_row(lines[i + 1])]
            rows, i = [header], i + 2
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                rows.append(_split_row(lines[i]))
                i += 1
            marker = f"MTBL{nonce}N{len(tables)}X"
            tables[marker] = {"rows": rows, "align": align}
            out += ["", marker, ""]
            continue
        out.append(line)
        i += 1
    return "\n".join(out), tables


def _inline_html(text: str) -> str:
    from pipeline.export import inlines
    out = []
    for kind, value in inlines(text):
        value = html.escape(value if kind != "note" else f"[^{value}]")
        out.append({"bold": f"<strong>{value}</strong>", "italic": f"<em>{value}</em>",
                    "code": f"<code>{value}</code>"}.get(kind, value))
    return "".join(out)


TABLE_CSS = ("table.md { border-collapse: collapse; margin: .8em 0 1em; font-size: .9em; line-height: 1.35; } "
             "table.md th, table.md td { border: 1px solid #b8b8b8; padding: .3em .55em; vertical-align: top; "
             "text-align: start; hyphens: manual; } table.md th { background: #f1f1f1; font-weight: 600; }")


def to_html(markdown: str, title: str, lang: str) -> str:
    """pipeline.export.to_html with real tables."""
    from pipeline import export
    text, tables = extract(markdown)
    page = export.to_html(text, title, lang)
    for marker, table in tables.items():
        width = max(len(r) for r in table["rows"])
        rows = []
        for n, row in enumerate(table["rows"]):
            tag = "th" if n == 0 else "td"
            cells = []
            for c in range(width):
                align = table["align"][c] if c < len(table["align"]) else ""
                style = f' style="text-align: {align}"' if align else ""
                cells.append(f"<{tag}{style}>{_inline_html(row[c] if c < len(row) else '')}</{tag}>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        block = f'<table class="md"><thead>{rows[0]}</thead><tbody>{"".join(rows[1:])}</tbody></table>'
        page = re.sub(rf"<p[^>]*>{marker}</p>", lambda _m: block, page)
    return page.replace("</style>", f"  {TABLE_CSS}\n</style>", 1) if tables else page


_XML_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _runs(text: str, bold: bool) -> str:
    from pipeline.export import inlines
    out = []
    for kind, value in inlines(text):
        props = ("<w:b/><w:bCs/>" if bold or kind == "bold" else "") + ("<w:i/><w:iCs/>" if kind == "italic" else "") + \
            ('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>' if kind == "code" else "")
        value = value if kind != "note" else f"[^{value}]"
        out.append(f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{xml_escape(_XML_INVALID.sub("", value))}</w:t></w:r>')
    return "".join(out)


def _docx_table(table: dict, rtl: bool) -> str:
    width = max(len(r) for r in table["rows"])
    col = 9000 // max(width, 1)
    border = "".join(f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="A0A0A0"/>'
                     for side in ("top", "left", "bottom", "right", "insideH", "insideV"))
    rows = []
    for n, row in enumerate(table["rows"]):
        cells = []
        for c in range(width):
            align = table["align"][c] if c < len(table["align"]) else ""
            jc = f'<w:jc w:val="{"center" if align == "center" else "right"}"/>' if align else ""
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="F1F1F1"/>' if n == 0 else ""
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{col}" w:type="dxa"/>{shade}</w:tcPr><w:p><w:pPr><w:spacing w:after="0"/>'
                         f'{"<w:bidi/>" if rtl else ""}{jc}</w:pPr>{_runs(row[c] if c < len(row) else "", n == 0)}</w:p></w:tc>')
        header = "<w:trPr><w:tblHeader/></w:trPr>" if n == 0 else ""
        rows.append(f"<w:tr>{header}{''.join(cells)}</w:tr>")
    grid = "".join(f'<w:gridCol w:w="{col}"/>' for _ in range(width))
    return (f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{"<w:bidiVisual/>" if rtl else ""}'
            f'<w:tblBorders>{border}</w:tblBorders><w:tblLayout w:type="autofit"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
            f'{"".join(rows)}</w:tbl><w:p/>')


def to_docx(markdown: str, title: str, lang: str) -> bytes:
    """pipeline.export.to_docx with real tables."""
    from pipeline import export
    text, tables = extract(markdown)
    data = export.to_docx(text, title, lang)
    if not tables:
        return data
    source = zipfile.ZipFile(io.BytesIO(data))
    document = source.read("word/document.xml").decode("utf-8")
    for marker, table in tables.items():
        document = re.sub(rf"<w:p>(?:(?!<w:p>).)*?{marker}</w:t></w:r></w:p>",
                          lambda _m: _docx_table(table, export.is_rtl(lang)), document, flags=re.S)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for item in source.infolist():
            z.writestr(item, document if item.filename == "word/document.xml" else source.read(item.filename))
    return buffer.getvalue()
