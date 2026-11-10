"""Run from the project root: python3 -m unittest discover -s tests -v"""

import hashlib
import io
import json
import os
import re
import shutil
import string
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import checks, configfile, documents, export, i18n, providers, runtime, stages, system  # noqa: E402
from pipeline.cli import main  # noqa: E402
from pipeline.core import PipelineError, Project, read_json  # noqa: E402

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(path: Path) -> None:
    document = f"""<w:document {W_NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="Balk1"/></w:pPr><w:r><w:t>Birinci Kısım</w:t></w:r></w:p>
<w:p><w:r><w:t>Namaz dinin </w:t></w:r><w:r><w:t>direğidir.</w:t></w:r><w:r><w:footnoteReference w:id="2"/></w:r></w:p>
<w:p><w:r><w:t></w:t></w:r></w:p>
<w:p><w:r><w:t>İkinci paragraf.</w:t></w:r></w:p>
</w:body></w:document>"""
    styles = f"""<w:styles {W_NS}><w:style w:type="paragraph" w:styleId="Balk1"><w:name w:val="heading 1"/></w:style></w:styles>"""
    footnotes = f"""<w:footnotes {W_NS}>
<w:footnote w:type="separator" w:id="0"><w:p><w:r><w:t>---</w:t></w:r></w:p></w:footnote>
<w:footnote w:id="2"><w:p><w:r><w:footnoteRef/></w:r><w:r><w:t>Hadîs-i şerîf.</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/footnotes.xml", footnotes)


def make_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/container.xml",
                   '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                   '<rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf",
                   '<package xmlns="http://www.idpf.org/2007/opf"><manifest>'
                   '<item id="b" href="text/b.xhtml"/><item id="a" href="text/a.xhtml"/></manifest>'
                   '<spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
        z.writestr("OEBPS/text/a.xhtml",
                   "<html><head><title>none</title><style>p{}</style></head><body><h2>Kapitel 1</h2>"
                   "<p>Første <i>avsnitt</i>.</p></body></html>")
        z.writestr("OEBPS/text/b.xhtml", "<html><body><p>Andet afsnit.</p></body></html>")


def make_arabic_pdf(path: Path) -> None:
    """Two lines of Arabic written the way PDF makers write them (glyphs in visual order, left to right).

    Line 1, as a browser writes it: every letter cluster in an /ActualText span; "لْمُ" is one ligature glyph.
    Line 2, as macOS writes it: each vowel sign right before its letter, the ligature لم mapped to two letters
    in a ToUnicode entry with spaces ("<0644 0645>"), no ActualText."""
    letters = {1: "0644", 2: "0645", 3: "0627", 4: "0648", 5: "0646", 6: "0643", 7: "0631",
               8: "064E", 9: "0652", 10: "064F", 11: "0650", 12: "0020", 13: "0644 0645"}
    cmap = "".join(f"<{code:04X}> <{text}>\n" for code, text in letters.items())
    tounicode = (b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n1 begincodespacerange\n<0000> <FFFF>\n"
                 b"endcodespacerange\n13 beginbfchar\n" + cmap.encode() + b"endbfchar\nendcmap end end\n")

    def span(text: str, *codes: int) -> str:  # one cluster: a letter (width 10 at size 20) and its signs (no width)
        utf16 = "FEFF" + "".join(f"{ord(c):04X}" for c in text)
        return f"/Span <</ActualText <{utf16}> >> BDC " + " ".join(f"<{c:04X}> Tj" for c in codes) + " EMC "

    line1 = ("BT /F1 20 Tf 1 0 0 1 100 250 Tm " + span("رِ", 7, 11) + span("كَ", 6, 8) + span("نْ", 5, 9)
             + span("لْمُ", 13, 9, 10) + span("ا", 3) + span("وَ", 4, 8) + "ET\n")
    line2 = ("BT /F1 20 Tf 1 0 0 1 100 180 Tm <0009> Tj 1 0 0 1 106 180 Tm <0008> Tj 1 0 0 1 100 180 Tm <000D> Tj "
             "1 0 0 1 112 180 Tm <0008> Tj 1 0 0 1 110 180 Tm <0004> Tj ET\n")
    content = (line1 + line2).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /ArialMT /Encoding /Identity-H /DescendantFonts [6 0 R] /ToUnicode 7 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ArialMT /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) "
        b"/Supplement 0 >> /DW 500 /W [8 [0 0 0 0]] /FontDescriptor 8 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(tounicode) + tounicode + b"endstream",
        b"<< /Type /FontDescriptor /FontName /ArialMT /Flags 32 /FontBBox [0 -200 1000 900] /ItalicAngle 0 "
        b"/Ascent 900 /Descent -200 /CapHeight 700 /StemV 80 >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_pdf_glyphs_give_text_and_position_of_each_glyph(self):
        from pipeline import pdfglyphs
        make_arabic_pdf(self.tmp / "ar.pdf")
        glyphs = pdfglyphs.read((self.tmp / "ar.pdf").read_bytes(), [0])[0]
        line1 = [g for g in glyphs if g.y < 100]  # from the top of the page
        self.assertEqual([g.text for g in line1], ["رِ", "كَ", "نْ", "لْمُ", "ا", "وَ"])  # one glyph per span
        self.assertEqual([round(g.x0) for g in line1], [100, 110, 120, 130, 140, 150])
        line2 = sorted((g for g in glyphs if g.y > 100), key=lambda g: g.order)
        self.assertEqual([g.text for g in line2], ["ْ", "َ", "لم", "َ", "و"])

    def test_right_to_left_glyphs_keep_numbers_and_mirror_brackets(self):
        from pipeline.pdfglyphs import Glyph
        # "آية (٢٥)" as drawn, left to right: the number keeps its order, the brackets are drawn mirrored.
        drawn = ["(", "٢", "٥", ")", " ", "ة", "ي", "آ"]
        glyphs = [Glyph(text, 10 * i, 10 * i + 8, 50, 20, i) for i, text in enumerate(drawn)]
        words = documents._glyph_words(glyphs, True)
        self.assertEqual(" ".join(w.text for w in reversed(words)), "آية (٢٥)")

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext is not installed")
    def test_pdf_arabic_is_read_in_reading_order(self):
        make_arabic_pdf(self.tmp / "ar.pdf")
        blocks = [__import__("unicodedata").normalize("NFC", b) for b in documents.read_blocks(self.tmp / "ar.pdf")]
        self.assertEqual(blocks, ["وَالْمُنْكَرِ", "وَلَمْ"])
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_docx_keeps_headings_and_footnotes(self):
        make_docx(self.tmp / "tr.docx")
        self.assertEqual(documents.read_blocks(self.tmp / "tr.docx"), [
            "# Birinci Kısım",
            "Namaz dinin direğidir.[^1]\n[^1]: Hadîs-i şerîf.",
            "İkinci paragraf.",
        ])

    def test_pdf_text_loses_headers_and_page_numbers_and_keeps_paragraphs(self):
        bodies = ["Birinci paragraf burada baş-\nlar ve sonraki say-\nfada devam eder",
                  "ve burada biter. Yeni cümle.\n\nİkinci Bölüm\n\nBaşka bir paragraf.",
                  "Üçüncü sayfanın metni.", "Dördüncü sayfanın metni."]
        pages = [f"İslam İlmihali\n\n{body}\n\n{n}\n" for n, body in enumerate(bodies, 1)]
        blocks = documents._pdf_text_blocks("\f".join(pages))
        self.assertEqual(blocks[0], "Birinci paragraf burada başlar ve sonraki sayfada devam eder ve burada biter. Yeni cümle.")
        self.assertEqual(blocks[1:3], ["İkinci Bölüm", "Başka bir paragraf."])
        self.assertFalse([b for b in blocks if "İslam İlmihali" in b or b.isdigit()])
        # No empty lines between paragraphs: a short line that ends a sentence ends the paragraph; a short line
        # without sentence punctuation after it is a heading.
        full = "Bu satır sayfanın bütün genişliğini dolduran uzun bir satırdır"
        text = "\n".join(["Namaz Bahsi", full, full + ".", full, "ve kısa biter.", "Oruç Bahsi", full, "son satır."])
        self.assertEqual([b[:14] for b in documents._pdf_text_blocks(text)],
                         ["Namaz Bahsi", "Bu satır sayfa", "Oruç Bahsi", "Bu satır sayfa"])

    def test_epub_footnote_number_is_not_glued_to_the_word(self):
        parser = documents._HTMLBlocks()
        parser.feed("<p>Namaz dinin direğidir<sup>3</sup>. 10<sup>2</sup> ve x<sup>n</sup></p>")
        parser.close()
        parser.flush()
        self.assertEqual(parser.blocks, ["Namaz dinin direğidir[3]. 10[2] ve xn"])

    def test_epub_follows_spine_order(self):
        make_epub(self.tmp / "da.epub")
        self.assertEqual(documents.read_blocks(self.tmp / "da.epub"),
                         ["## Kapitel 1", "Første *avsnitt*.", "Andet afsnit."])

    def test_epub_note_references_become_footnotes(self):
        with zipfile.ZipFile(self.tmp / "n.epub", "w") as z:
            z.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                       '<rootfiles><rootfile full-path="c.opf"/></rootfiles></container>')
            z.writestr("c.opf", '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml"/>'
                       '<item id="n" href="notes.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="n"/></spine></package>')
            z.writestr("a.xhtml", '<html xmlns:epub="http://www.idpf.org/2007/ops"><body>'
                       '<p>Namaz dinin direğidir.<a epub:type="noteref" href="#f1"><sup>1</sup></a> Oruç da farzdır.'
                       '<a href="notes.xhtml#e1">2</a></p>'
                       '<aside epub:type="footnote" id="f1"><p><a href="#r1">1</a> Tirmizî, <i>Îmân</i>, 8.</p></aside></body></html>')
            z.writestr("notes.xhtml", '<html><body><section role="doc-endnotes"><ol>'
                       '<li id="e1"><p>Bakara sûresi, 183. <a href="a.xhtml#r2">↩</a></p></li></ol></section></body></html>')
        self.assertEqual(documents.read_blocks(self.tmp / "n.epub"), [
            "Namaz dinin direğidir.[^1] Oruç da farzdır.[^2]\n[^1]: Tirmizî, *Îmân*, 8.\n[^2]: Bakara sûresi, 183."])

    def test_docx_numbering_inherited_headings_and_emphasis(self):
        doc = f"""<w:document {W_NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="Bolum"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Namaz</w:t></w:r></w:p>
<w:p><w:pPr><w:outlineLvl w:val="2"/></w:pPr><w:r><w:t>Alt başlık</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="5"/></w:numPr></w:pPr><w:r><w:t>Abdest.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="5"/></w:numPr></w:pPr><w:r><w:t>Niyet.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="5"/></w:numPr></w:pPr><w:r><w:t>Kıble.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="6"/></w:numPr></w:pPr><w:r><w:t>Madde.</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Kitabın adı </w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">Mektûbât </w:t></w:r><w:r><w:rPr><w:i w:val="0"/></w:rPr><w:t>dır.</w:t></w:r></w:p>
</w:body></w:document>"""
        styles = f"""<w:styles {W_NS}><w:style w:styleId="Baslik2"><w:name w:val="heading 2"/></w:style>
<w:style w:styleId="Bolum"><w:name w:val="Bölüm Başlığı"/><w:basedOn w:val="Baslik2"/></w:style></w:styles>"""
        numbering = f"""<w:numbering {W_NS}>
<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2)"/></w:lvl></w:abstractNum>
<w:abstractNum w:abstractNumId="2"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/></w:lvl></w:abstractNum>
<w:num w:numId="5"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="6"><w:abstractNumId w:val="2"/></w:num></w:numbering>"""
        with zipfile.ZipFile(self.tmp / "n.docx", "w") as z:
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/numbering.xml", numbering)
        self.assertEqual(documents.read_blocks(self.tmp / "n.docx"), [
            "## Namaz", "### Alt başlık", "1. Abdest.", "a) Niyet.", "2. Kıble.", "• Madde.", "Kitabın adı *Mektûbât* dır."])

    def test_pdf_layout_footnotes_headers_headings_and_page_breaks(self):
        def line(x, y, text, h=12.0, sup=()):
            words, out = text.split(), []
            for i, w in enumerate(words):
                x1 = x + 6 * len(w)
                if i in sup:  # a raised note number in a smaller type
                    out.append(f'<word xMin="{x}" yMin="{y - 1}" xMax="{x + 4}" yMax="{y + 0.6 * h - 1}">{w}</word>')
                else:
                    out.append(f'<word xMin="{x}" yMin="{y}" xMax="{x1}" yMax="{y + h}">{w}</word>')
                x = x1 + 3
            return f"<line>{''.join(out)}</line>"

        def page(lines):
            return f'<page width="420" height="600"><flow><block>{"".join(lines)}</block></flow></page>'

        full = "a" * 50  # a line that reaches the right edge
        pages = [
            page([line(180, 20, "İLMİHAL", 9), line(150, 50, "BİRİNCİ BÖLÜM", 16), line(40, 80, "Namazın Önemi", 13),
                  line(57, 100, f"Namaz dinin direğidir. 1 {full}", sup=(3,)), line(40, 115, "kılınır."),
                  line(57, 130, f"İkinci paragraf {full}"), line(40, 145, f"devam {full}"),
                  line(40, 530, "1", 6), line(46, 531, "Tirmizî, Îmân, 8;", 9), line(46, 541, "ilk satır", 9),
                  line(205, 570, "7", 10)]),
            page([line(185, 20, "Namaz", 9), line(40, 50, "eden kimse kurtulur."),
                  line(46, 531, "devam eden dipnot.", 9), line(205, 570, "8", 10)]),
            page([line(180, 20, "İLMİHAL", 9), line(57, 50, "Son paragraf."), line(205, 570, "9", 10)]),
        ]
        xhtml = ('<html xmlns="http://www.w3.org/1999/xhtml"><body><doc>' + "".join(pages) + "</doc></body></html>").encode()
        blocks = documents._pdf_layout_blocks(documents._pdf_pages(xhtml))
        self.assertEqual(blocks[:3], ["# BİRİNCİ BÖLÜM", "## Namazın Önemi",
                                      f"Namaz dinin direğidir.[^1] {full} kılınır.\n[^1]: Tirmizî, Îmân, 8; ilk satır devam eden dipnot."])
        self.assertEqual(blocks[3], f"İkinci paragraf {full} devam {full} eden kimse kurtulur.")
        self.assertEqual(blocks[4:], ["Son paragraf."])

    def test_pdf_hyphenation_keeps_turkish_suffixes(self):
        self.assertEqual(documents._join_lines("namaz kı-\nlınır, Kur’ân-\nı kerîm, ehl-\ni sünnet"),
                         "namaz kılınır, Kur’ân-ı kerîm, ehl-i sünnet")

    def test_docx_text_box_is_read_once_and_endnotes_are_kept(self):
        mc = 'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
        document = f"""<w:document {W_NS} {mc}><w:body>
<w:p><w:r><w:t>Ana metin.</w:t></w:r><w:r><mc:AlternateContent><mc:Choice><w:drawing><w:txbxContent>
<w:p><w:r><w:t>Kutu metni.</w:t></w:r></w:p></w:txbxContent></w:drawing></mc:Choice>
<mc:Fallback><w:pict><w:txbxContent><w:p><w:r><w:t>Kutu metni.</w:t></w:r></w:p></w:txbxContent></w:pict></mc:Fallback>
</mc:AlternateContent></w:r><w:r><w:endnoteReference w:id="1"/></w:r></w:p>
</w:body></w:document>"""
        endnotes = f"""<w:endnotes {W_NS}><w:endnote w:id="1"><w:p><w:r><w:t>Son not.</w:t></w:r></w:p></w:endnote></w:endnotes>"""
        with zipfile.ZipFile(self.tmp / "b.docx", "w") as z:
            z.writestr("word/document.xml", document)
            z.writestr("word/endnotes.xml", endnotes)
        self.assertEqual(documents.read_blocks(self.tmp / "b.docx"),
                         ["Ana metin.[^1]\n[^1]: Son not.", "Kutu metni."])

    def test_xml_with_entity_declaration_is_rejected(self):
        with zipfile.ZipFile(self.tmp / "x.docx", "w") as z:
            z.writestr("word/document.xml", '<!DOCTYPE d [<!ENTITY a "b">]><d>&a;</d>')
        with self.assertRaises(PipelineError):
            documents.read_blocks(self.tmp / "x.docx")

    def test_segment_keeps_heading_with_its_text(self):
        # The heading fits at the end of the first segment but its paragraph does not: the heading moves along.
        blocks = ["a" * 20, "# Başlık", "b" * 90, "c" * 30]
        self.assertEqual(documents.segment(blocks, 100), ["a" * 20, "# Başlık\n\n" + "b" * 90, "c" * 30])
        # A heading after a sufficiently full segment starts a new segment.
        blocks = ["a" * 60, "# Başlık", "b" * 20]
        self.assertEqual(documents.segment(blocks, 100), ["a" * 60, "# Başlık\n\n" + "b" * 20])

    def test_split_long_breaks_at_sentence_ends_without_losing_text(self):
        block = "Bir cümle. " * 30
        parts = documents.split_long([block.strip()], 100)
        self.assertTrue(all(len(p) <= 100 for p in parts))
        self.assertEqual(" ".join(parts), block.strip())


class CheckTests(unittest.TestCase):
    def setUp(self):
        i18n.set_default("en")
        self.addCleanup(i18n.set_default, "tr")

    def test_clean_translation_has_no_warnings(self):
        source = "# Başlık\n\nBeş vakit namaz 5 vakittir.[^1] بسم الله\n[^1]: Not."
        translation = "# Overskrift\n\nDe 5 daglige bønnene.[^1] بسم الله\n[^1]: Note."
        self.assertEqual(checks.check_segment(source, translation), [])

    def test_reports_each_kind_of_loss(self):
        source = "# Başlık\n\n40 gün.[^1] بسم الله\n\nİkinci."
        translation = "Førti dager og 7."
        joined = " ".join(checks.check_segment(source, translation))
        for expected in ("Arabic-script", "missing in the translation: 40", "not in the source: 7", "footnote",
                         "number of paragraphs", "number of headings"):
            self.assertIn(expected, joined)

    def test_length_outlier_flags_short_translation(self):
        lengths = {f"{i:04d}": (1000, 1100) for i in range(1, 7)}
        lengths["0007"] = (1000, 500)
        self.assertEqual(list(checks.length_outliers(lengths)), ["0007"])


class GateTests(unittest.TestCase):
    def setUp(self):
        i18n.set_default("en")
        self.addCleanup(i18n.set_default, "tr")

    def test_completeness_gate(self):
        source = "# Başlık\n\n" + "Birinci cümle burada. " * 12 + "\n\n" + "İkinci paragraf cümlesi. " * 12 + "[^1]\n[^1]: Not."
        good = "# Heading\n\n" + "First sentence here. " * 12 + "\n\n" + "Second paragraph sentence. " * 12 + "[^1]\n[^1]: Note."
        self.assertEqual(checks.completeness_problems(source, good), [])
        dropped = "# Heading\n\n" + "First sentence here. " * 12
        self.assertIn("paragraphs", " ".join(checks.completeness_problems(source, dropped)))
        no_note = good.replace("[^1]\n[^1]: Note.", "")
        self.assertIn("footnote", " ".join(checks.completeness_problems(source, no_note)))
        # One paragraph much shorter than the others: a sentence is probably missing.
        short = "# Heading\n\n" + "First sentence here. " * 12 + "\n\n" + "Second. " * 3 + "[^1]\n[^1]: Note."
        self.assertIn("much shorter", " ".join(checks.completeness_problems(source, short)))
        # A correction must not shrink the text it was given.
        self.assertIn("shorter than before", " ".join(checks.completeness_problems(source, short, previous=good)))
        self.assertEqual(checks.completeness_problems(source, good, previous=good), [])

    def test_reviewer_reading_proof(self):
        text = "# Heading\n\nThe first paragraph ends here.\n\nThe second one, too."
        self.assertEqual(checks.coverage_problems(text, ["Heading", "ends here.", "one, too"]), [])
        self.assertIn("read 0 paragraphs", " ".join(checks.coverage_problems(text, None)))
        self.assertIn("read 2 paragraphs", " ".join(checks.coverage_problems(text, ["Heading", "ends here"])))
        # One copying mistake is tolerated; two in three paragraphs are not.
        self.assertEqual(checks.coverage_problems(text, ["Heading", "ends there", "one, too"]), [])
        self.assertIn("2, 3", " ".join(checks.coverage_problems(text, ["Heading", "x y", "z w"])))

    def test_sentence_and_note_pair_warnings(self):
        source = "Bir. İki. Üç. Dört.[^1]\n[^1]: Not."
        warnings = " ".join(checks.check_segment(source, "One. Two.[^1]\n[^2]: Note."))
        self.assertIn("fewer sentences", warnings)
        self.assertIn("do not match: 1, 2", warnings)

    def test_quota_scan_ignores_the_echoed_prompt(self):
        self.assertTrue(providers.is_quota_message("Error 429 Too Many Requests"))
        echoed = "user\nHadis 429 şöyledir...\nERROR: stream disconnected"
        self.assertTrue(providers.is_quota_message(echoed))  # the reason for removing the prompt before scanning
        self.assertFalse(providers.is_quota_message(echoed.replace("user\nHadis 429 şöyledir...", "")))

    def test_glossary_term_must_start_a_word(self):
        entries = [{"tr": "ilm", "target": "ilm", "note": ""}, {"tr": "el", "target": "hand", "note": ""}]
        block = stages.glossary_block(entries, "İlmin önemi büyüktür. Bu güzel bir şeydir.")
        self.assertIn("ilm → ilm", block)       # "İlmin" starts with the term (suffix added)
        self.assertNotIn("el → hand", block)    # "güzel" only contains it

    def test_glossary_file_without_header_keeps_its_first_row(self):
        path = Path(tempfile.mkdtemp()) / "no.tsv"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text("namaz\tnamaz\t\n", encoding="utf-8")
        self.assertEqual([e["tr"] for e in stages.load_glossary(path)], ["namaz"])
        path.write_text("tr\tno\tnote\nnamaz\tnamaz\t\n", encoding="utf-8")
        self.assertEqual([e["tr"] for e in stages.load_glossary(path)], ["namaz"])


class ExportTests(unittest.TestCase):
    MD = "# Başlık\n\nBirinci **kalın** ve *eğik* paragraf.[^1]\n[^1]: Dipnot metni.\n\n- madde bir\n- madde iki\n\nبسم الله"

    def test_docx_is_a_valid_word_file_with_real_footnotes(self):
        data = export.to_docx(self.MD, "Kitap", "no")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            self.assertTrue({"[Content_Types].xml", "word/document.xml", "word/footnotes.xml", "word/styles.xml"} <= names)
            import xml.etree.ElementTree as ET
            doc = z.read("word/document.xml").decode()
            notes = z.read("word/footnotes.xml").decode()
            for part in names:
                if part.endswith(".xml") or part.endswith(".rels"):
                    ET.fromstring(z.read(part))  # every part is well-formed XML
        self.assertIn('<w:pStyle w:val="Heading1"/>', doc)
        self.assertIn('<w:footnoteReference w:id="1"/>', doc)
        self.assertIn("Dipnot metni.", notes)
        self.assertIn("<w:b/>", doc)
        self.assertIn("بسم الله", doc)
        self.assertNotIn("[^1]", doc)
        # Documents read by this pipeline come back unchanged.
        path = Path(tempfile.mkdtemp()) / "x.docx"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_bytes(data)
        blocks = documents.read_blocks(path)
        self.assertEqual(blocks[0], "# Başlık")
        self.assertEqual(blocks[1], "Birinci **kalın** ve *eğik* paragraf.[^1]\n[^1]: Dipnot metni.")

    def test_moved_footnote_line_and_dialogue_dash_are_kept(self):
        md = "Birinci paragraf.[^1]\n\nİkinci paragraf.\n[^1]: Kaymış dipnot.\n\n- Diyalog satırı."
        page = export.to_html(md, "K", "tr", lists=False)
        self.assertIn('<li id="fn1">Kaymış dipnot.', page)
        self.assertIn("<p class=\"item\">- Diyalog satırı.</p>", page)
        self.assertNotIn("[^1]", page)

    def test_html_and_right_to_left(self):
        page = export.to_html(self.MD, "Kitap <x>", "ar")
        self.assertIn('dir="rtl"', page)
        self.assertIn("<h1>Başlık</h1>", page)
        self.assertIn("<strong>kalın</strong>", page)
        self.assertIn('<li id="fn1">Dipnot metni.', page)
        self.assertIn("Kitap &lt;x&gt;", page)
        self.assertNotIn("window.print", page)
        self.assertIn("window.print", export.to_html(self.MD, "K", "no", print_on_load=True))
        self.assertIn("<w:bidi/>", zipfile.ZipFile(io.BytesIO(export.to_docx(self.MD, "K", "ar"))).read("word/document.xml").decode())


def make_template(dotx: bool = False, macros: bool = False) -> bytes:
    """A Word template as Word writes it in Turkish: localized style ids, a header, a sample text, LibreOffice-style
    footnote separators (ids 0 and 1)."""
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    main = "template.main+xml" if dotx else ("document.macroEnabled.main+xml" if macros else "document.main+xml")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   f'<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{main}"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                   '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
                   '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>'
                   '<Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>')
        z.writestr("word/header1.xml", f'<?xml version="1.0"?><w:hdr {W}><w:p><w:r><w:t>YAYINEVİ</w:t></w:r></w:p></w:hdr>')
        z.writestr("word/styles.xml", f'<?xml version="1.0"?><w:styles {W}>'
                   '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Minion Pro"/></w:rPr></w:style>'
                   '<w:style w:type="paragraph" w:styleId="Balk1"><w:name w:val="heading 1"/></w:style>'
                   '<w:style w:type="paragraph" w:styleId="DipnotMetni"><w:name w:val="footnote text"/></w:style>'
                   '<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Intense Quote"/></w:style></w:styles>')
        z.writestr("word/footnotes.xml", f'<?xml version="1.0"?><w:footnotes {W}>'
                   '<w:footnote w:id="0" w:type="separator"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
                   '<w:footnote w:id="1" w:type="continuationSeparator"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
                   '<w:footnote w:id="2"><w:p><w:r><w:t>Örnek dipnot</w:t></w:r></w:p></w:footnote></w:footnotes>')
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {W}><w:body>'
                   '<w:p><w:r><w:t>Örnek metin</w:t></w:r></w:p>'
                   '<w:sectPr><w:headerReference w:type="default" r:id="rId7"/><w:pgSz w:w="7655" w:h="11907"/>'
                   '<w:pgMar w:top="1134" w:right="851" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>'
                   '</w:body></w:document>')
        if macros:
            z.writestr("word/vbaProject.bin", b"x")
    return buffer.getvalue()


class ExportLayoutTests(unittest.TestCase):
    MD = ExportTests.MD + "\n\n# İkinci bölüm\n\n> Alıntı.[^2]\n[^2]: İkinci dipnot."

    def test_book_layout_reaches_pdf_and_word_and_the_report_keeps_the_standard(self):
        lay = {"page_size": "A5", "margin_top": 2.0, "margin_bottom": 1.5, "margin_side": 1.8, "font": "Minion Pro",
               "arabic_font": "Amiri", "font_size": 10.5, "line_spacing": 1.5, "justify": False, "chapter_new_page": False}
        page = export.to_html(self.MD, "K", "no", lists=False, book_layout=lay)
        self.assertIn("size: 148mm 210mm; margin: 2.0cm 1.8cm 1.5cm", page)
        self.assertIn('font-family: "Minion Pro", "Charis SIL"', page)
        self.assertIn('font-family: "Amiri", "Noto Naskh Arabic"', page)
        self.assertIn("font-size: 10.5pt; line-height: 2.03", page)
        self.assertIn("text-align: start; text-indent", page)
        self.assertNotIn("break-before: page", page)
        report = export.to_html(self.MD, "K", "no", lists=True, book_layout=lay)
        self.assertIn("size: A4; margin: 2.2cm 2.3cm 2.6cm", report)
        self.assertNotIn("Minion", report)

        with zipfile.ZipFile(io.BytesIO(export.to_docx(self.MD, "K", "no", False, lay))) as z:
            doc, styles = z.read("word/document.xml").decode(), z.read("word/styles.xml").decode()
        self.assertIn('<w:pgSz w:w="8392" w:h="11907"/>', doc)
        self.assertIn('w:top="1134" w:right="1021" w:bottom="850" w:left="1021"', doc)
        self.assertIn('w:ascii="Minion Pro" w:hAnsi="Minion Pro" w:cs="Amiri"', styles)
        self.assertIn('<w:sz w:val="21"/>', styles)
        self.assertIn('w:line="360"', styles)
        self.assertNotIn('<w:jc w:val="both"/>', styles)
        self.assertNotIn("pageBreakBefore", styles)
        # Invalid values in config.toml fall back to the defaults; the checks name the first invalid key.
        self.assertEqual(export.layout({"font_size": 40, "font": 'x"; }', "page_size": "A3", "justify": 1}), export.DEFAULT_LAYOUT)
        self.assertEqual(export.layout_problem({**export.DEFAULT_LAYOUT, "margin_side": 9.0}), "margin_side")
        self.assertIsNone(export.layout_problem(export.DEFAULT_LAYOUT))

    def test_word_template_gives_its_styles_page_and_header(self):
        import xml.etree.ElementTree as ET
        data = export.to_docx(self.MD, "K", "no", False, {"font": "Arial"}, template=make_template(dotx=True))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for part in z.namelist():
                if part.endswith((".xml", ".rels")):
                    ET.fromstring(z.read(part))  # every part is well-formed XML
            doc, styles = z.read("word/document.xml").decode(), z.read("word/styles.xml").decode()
            notes, types = z.read("word/footnotes.xml").decode(), z.read("[Content_Types].xml").decode()
            self.assertIn("word/header1.xml", z.namelist())
        self.assertIn('<w:pStyle w:val="Balk1"/>', doc)  # the template's own heading style
        self.assertIn('<w:pgSz w:w="7655" w:h="11907"/>', doc)  # the template's page
        self.assertIn('<w:headerReference w:type="default" r:id="rId7"/>', doc)
        self.assertNotIn("Örnek metin", doc)
        self.assertNotIn("Arial", styles)  # the settings do not change a template
        self.assertIn('<w:pStyle w:val="DipnotMetni"/>', notes)
        self.assertNotIn("Örnek dipnot", notes)
        # The separators keep ids 0 and 1; the notes follow them.
        self.assertIn('<w:footnoteReference w:id="2"/>', doc)
        self.assertIn('<w:footnoteReference w:id="3"/>', doc)
        self.assertIn("İkinci dipnot.", notes)
        # Styles that the template lacks are added; an id that the template uses for another style is not reused.
        self.assertIn('w:styleId="TPQuote"><w:name w:val="Quote"/>', styles)
        self.assertIn('<w:pStyle w:val="TPQuote"/>', doc)
        self.assertIn('<w:name w:val="List Bullet"/>', styles)
        self.assertIn("wordprocessingml.document.main+xml", types)
        self.assertNotIn("template.main+xml", types)
        # The report never takes the template.
        report = export.to_docx(self.MD, "K", "no", True, template=make_template())
        self.assertNotIn(b"header1.xml", report)

    def test_unusable_templates_are_refused(self):
        self.assertIsNone(export.template_problem(make_template()))
        self.assertEqual(export.template_problem(b"not a zip"), "type")
        self.assertEqual(export.template_problem(make_template(macros=True)), "macros")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("word/document.xml", "<x/>")
        self.assertEqual(export.template_problem(buffer.getvalue()), "type")
        broken = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(make_template())) as src, zipfile.ZipFile(broken, "w") as z:
            for name in src.namelist():
                z.writestr(name, src.read(name) if name != "word/document.xml" else b"<w:document>no body</w:document>")
        self.assertEqual(export.template_problem(broken.getvalue()), "broken")
        # A bare Word file without styles or notes (as some programs write it) gets ours.
        bare = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(make_template())) as src, zipfile.ZipFile(bare, "w") as z:
            for name in src.namelist():
                if name not in ("word/styles.xml", "word/footnotes.xml"):
                    z.writestr(name, src.read(name))
        self.assertIsNone(export.template_problem(bare.getvalue()))
        with zipfile.ZipFile(io.BytesIO(export.to_docx(self.MD, "K", "no", False, template=bare.getvalue()))) as z:
            self.assertIn('w:styleId="Heading1"', z.read("word/styles.xml").decode())
            self.assertIn("İkinci dipnot.", z.read("word/footnotes.xml").decode())
            self.assertIn('Target="footnotes.xml"', z.read("word/_rels/document.xml.rels").decode())


class ConfigFileTests(unittest.TestCase):
    def test_export_section_is_added_once_and_keeps_the_comments_around_it(self):
        import tomllib
        text = (ROOT / "config.toml").read_text(encoding="utf-8")
        without = re.sub(r"\[export\]\n.*?\n\n", "", text, flags=re.S)
        self.assertNotIn("[export]", without)
        values = {**export.DEFAULT_LAYOUT, "font": 'Minion "Pro"', "font_size": 11.0, "word_template": "Yayınevi.docx"}
        added = configfile.set_export(without, values)
        again = configfile.set_export(added, values)
        self.assertEqual(added, again)
        self.assertEqual(tomllib.loads(added)["export"], values)
        self.assertEqual(added.count("[export]"), 1)
        self.assertIn("# Each command reads the prompt", added)
        self.assertLess(added.index("[export]"), added.index("# Each command reads the prompt"))


    def test_stage_board_is_saved_and_comments_are_kept(self):
        import tomllib
        text = (ROOT / "config.toml").read_text(encoding="utf-8")
        flow = ["review1", "revise1", "source_check", "custom1", "review2", "reconcile", "gate1"]
        nodes = {"custom1": {"title": 'Üslup "sade"', "mode": "rewrite"}, "gate1": {"back_to": "review2", "max": 2}}
        assignment = {stage: ["claude"] for stage in stages.PREP_STAGES + ["translate"] + flow}
        assignment["translate"] = ["chatgpt/gpt-x.1"]
        assignment["review2"] = ["gemini/gemini-pro", "claude/opus"]
        new = configfile.set_models(configfile.set_stages(text, assignment, flow, nodes), "claude", ["opus", "sonnet"])
        cfg = tomllib.loads(new)
        self.assertEqual(cfg["stages"]["flow"], flow)
        self.assertEqual(cfg["nodes"], nodes)
        self.assertIsNone(stages.flow_problem(flow, cfg))
        # Saved again with fewer nodes: the options of the removed nodes go, and [nodes] stays a single section.
        again = tomllib.loads(configfile.set_stages(new, assignment, flow[:3], nodes))
        self.assertEqual(again["nodes"], {})
        self.assertEqual(cfg["stages"]["translate"], "chatgpt/gpt-x.1")
        self.assertEqual(cfg["stages"]["review2"], ["gemini/gemini-pro", "claude/opus"])
        self.assertEqual(cfg["stages"]["review1"], ["claude"])
        self.assertEqual(cfg["providers"]["claude"]["models"], ["opus", "sonnet"])
        self.assertEqual(cfg["languages"], tomllib.loads(text)["languages"])
        self.assertIn("# interface language", new)
        self.assertIn("# first translation", new)


class PlatformTests(unittest.TestCase):
    def test_windows_cmd_tools_are_quoted_for_cmd_exe(self):
        from unittest import mock
        path = r"C:\Users\Ahmet Çelik\AppData\Roaming\npm\codex.cmd"
        with mock.patch.object(system, "IS_WINDOWS", True), mock.patch.object(system.shutil, "which", return_value=path):
            argv = system.resolve(["codex", "exec", "-o", r"C:\Temp\tp 1\output.txt", "--model", "gpt-x"])
        self.assertEqual(argv[:4], ["cmd.exe", "/d", "/s", "/c"])
        # One outer pair of quotes around a normal command line: cmd.exe /s removes only the outer pair.
        self.assertEqual(argv[4], '""C:\\Users\\Ahmet Çelik\\AppData\\Roaming\\npm\\codex.cmd" exec -o "C:\\Temp\\tp 1\\output.txt" --model gpt-x"'.replace("\\\\", "\\"))
        with mock.patch.object(system, "IS_WINDOWS", False), mock.patch.object(system.shutil, "which", return_value="/usr/bin/codex"):
            self.assertEqual(system.resolve(["codex", "exec"]), ["/usr/bin/codex", "exec"])

    def test_downloaded_archive_cannot_escape_its_folder(self):
        import tarfile
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        evil = tmp / "evil.tar.gz"
        with tarfile.open(evil, "w:gz") as tar:
            data = io.BytesIO(b"x")
            info = tarfile.TarInfo("../outside.txt")
            info.size = 1
            tar.addfile(info, data)
        with self.assertRaises(Exception):
            runtime._safe_extract(evil, "tar", tmp / "out")
        self.assertFalse((tmp / "outside.txt").exists())
        with zipfile.ZipFile(tmp / "evil.zip", "w") as z:
            z.writestr("../outside.txt", "x")
        with self.assertRaises(PipelineError):
            runtime._safe_extract(tmp / "evil.zip", "zip", tmp / "out2")
        self.assertFalse((tmp / "outside.txt").exists())

    def test_each_npm_tool_has_its_own_folder_on_path(self):
        root = Path("/app")
        dirs = runtime.bin_dirs(root)
        self.assertEqual(len({str(d) for d in dirs}), 4)  # codex, gemini, node, the PDF reader
        self.assertTrue(all(str(d).startswith(str(root / ".runtime")) for d in dirs))

    def test_pdf_reader_install_checks_the_download_and_installs_poppler(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        payload = b"micromamba binary"
        sums = {"sha": hashlib.sha256(payload).hexdigest()}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=60):
            return Response((sums["sha"] + "  micromamba\n").encode())

        def fake_download(url, dest):
            self.assertIn("micromamba-", url)
            dest.write_bytes(payload)

        calls = []

        def fake_run(argv, env=None):
            calls.append(argv)
            if argv[1] == "create":  # what micromamba does: the environment with pdftotext
                bin_dir = runtime.poppler_bin_dir(root)
                bin_dir.mkdir(parents=True)
                (bin_dir / ("pdftotext.exe" if system.IS_WINDOWS else "pdftotext")).write_text("x")
                self.assertEqual(env["MAMBA_ROOT_PREFIX"], str(root / ".runtime" / "mamba"))

        with mock.patch.object(runtime.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(runtime, "_download", fake_download), mock.patch.object(runtime, "_run_streaming", fake_run):
            sums["sha"] = "0" * 64  # a download that does not match its published sum is not used
            with self.assertRaises(PipelineError):
                runtime.install_tool("pdf", root)
            self.assertFalse(any((root / ".runtime" / "micromamba").glob("micromamba*")))
            self.assertEqual(calls, [])
            sums["sha"] = hashlib.sha256(payload).hexdigest()
            runtime.install_tool("pdf", root)
        self.assertEqual(calls[0][1:], ["create", "--root-prefix", str(root / ".runtime" / "mamba"), "--yes", "--prefix",
                                        str(root / ".runtime" / "poppler"), "--channel", "conda-forge", "--override-channels", "poppler"])
        self.assertEqual(calls[1][1], "clean")
        self.assertIn(runtime.poppler_bin_dir(root), runtime.bin_dirs(root))

    def test_codex_models_are_read_from_its_own_list(self):
        from pipeline import tools
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home)
        (home / "models_cache.json").write_text('{"models": [{"slug": "gpt-a", "visibility": "list"}, '
                                               '{"slug": "hidden", "visibility": "hide"}, {"slug": "-x", "visibility": "list"}]}')
        os.environ["CODEX_HOME"] = str(home)
        self.addCleanup(os.environ.pop, "CODEX_HOME")
        self.assertEqual(tools.list_models("codex"), ["gpt-a"])
        (home / "models_cache.json").write_text("not json")
        self.assertEqual(tools.list_models("codex"), [])
        self.assertIn("opus", tools.list_models("claude"))

    def test_multiline_models_array_is_replaced_whole(self):
        import tomllib
        text = '[providers.claude]\nmodels = [\n  "opus",\n  "sonnet",\n]\nmodel = ""\n\n[languages]\ntr = "Turkish"\n'
        new = configfile.set_models(text, "claude", ["haiku"])
        self.assertEqual(tomllib.loads(new)["providers"]["claude"]["models"], ["haiku"])
        self.assertEqual(tomllib.loads(new)["providers"]["claude"]["model"], "")

    def test_second_interface_on_a_busy_port_gives_a_message(self):
        import socket
        from pipeline import web
        from pipeline.core import Project
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        self.addCleanup(sock.close)
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        make_project(root)
        out = io.StringIO()
        i18n.set_default("en")
        self.addCleanup(i18n.set_default, "tr")
        with redirect_stdout(out):
            web.serve(Project.load(root), sock.getsockname()[1], open_browser=False)  # returns instead of raising
        self.assertIn("is in use; the interface is probably already open", out.getvalue())


FAKE_AGY = r"""
import json, os, sys
message = json.loads(sys.stdin.readline())["message"]["content"]
conversation = "0f0e0d0c-1111-2222-3333-444455556666"
home = os.environ["FAKE_AGY_DIR"]
os.makedirs(os.path.join(home, "conversations"), exist_ok=True)
os.makedirs(os.path.join(home, "brain", conversation), exist_ok=True)
for suffix in (".db", ".db-wal"):
    open(os.path.join(home, "conversations", conversation + suffix), "w").close()
open(os.path.join(home, "conversations", "keep.db"), "w").close()  # a conversation of the user
print(json.dumps({"event": "init", "init": {"cwd": os.getcwd(), "tools": []}}))
if "use a tool" in message:
    result = {"conversation_id": conversation, "status": "SUCCESS", "response": "",
              "denied_actions": [{"action": "command", "display_name": "RunCommand"}]}
else:
    print(json.dumps({"event": "step_update", "step_update": {"step_type": "agent_response", "text_delta": "Hal"}}))
    result = {"conversation_id": conversation, "status": "SUCCESS", "response": "Hallo «" + message[-8:] + "»\n"}
print(json.dumps({"event": "result", "result": result}))
"""


class StreamJsonProviderTests(unittest.TestCase):
    def test_prompt_goes_as_one_message_and_the_stored_conversation_is_removed(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "agy.py").write_text(FAKE_AGY, encoding="utf-8")
        make_project(tmp)
        cfg = (tmp / "config.toml").read_text(encoding="utf-8")
        (tmp / "config.toml").write_text(cfg + f"""
[providers.agy]
command = [{json.dumps(sys.executable)}, {json.dumps(str(tmp / "agy.py"))}]
input = "stream-json"
model = ""
""", encoding="utf-8")
        proj = Project.load(tmp)
        store = tmp / "agy-home"
        with mock.patch.dict(os.environ, {"FAKE_AGY_DIR": str(store)}), mock.patch.object(providers, "AGY_DIR", store):
            # A prompt with quotes, new lines and Arabic arrives whole.
            answer = providers.run(proj, "agy", 'Say "hi"\nبسم الله', wait_for_quota=False, attempts=1)
            self.assertEqual(answer, "Hallo «بسم الله»")
            self.assertEqual(sorted(p.name for p in (store / "conversations").iterdir()), ["keep.db"])
            self.assertFalse((store / "brain" / "0f0e0d0c-1111-2222-3333-444455556666").exists())
            # A model that tries a tool instead of answering: a failed call that says why.
            with self.assertRaises(providers.LLMError) as caught:
                providers.run(proj, "agy", "use a tool", wait_for_quota=False, attempts=1)
            self.assertIn(i18n.t("tool_use_denied"), str(caught.exception))


class ReferenceCheckTests(unittest.TestCase):
    # A Turkish source with the signals that survive translation: Arabic phrases and numbers.
    SOURCE = ("# Namaz\n\nNamaz dînin direğidir. Bu hadîs Beyhakî'de 2807 numara ile bildirilmiştir. Bekara sûresinin 43. "
              "âyetinde: وَأَقِيمُوا الصَّلَاةَ وَآتُوا الزَّكَاةَ\n\n# Abdest\n\nAbdestin farzı dörttür ve bunlar Mâide sûresinin 6. "
              "âyetinde bildirilir: يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا قُمْتُمْ إِلَى الصَّلَاةِ. Tirmizî 3, Ebû Dâvûd 61.\n\n"
              "# Vakitler\n\nNisâ 103: إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَوْقُوتًا. Bu bölüm 1250 yılında yazıldı.\n")
    DANISH = ("# Bøn\n\nBønnen er religionens søjle. Denne hadith er overleveret hos Bayhaqi under nummer 2807. I Surah "
              "al-Baqarah vers 43: وَأَقِيمُوا الصَّلَاةَ وَآتُوا الزَّكَاةَ\n\n# Afvaskning\n\nAfvaskningens pligter er fire, og "
              "de nævnes i Surah al-Ma'idah vers 6: يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا قُمْتُمْ إِلَى الصَّلَاةِ. Tirmidhi 3, Abu Dawud 61."
              "\n\n# Tider\n\nAn-Nisa 103: إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَوْقُوتًا. Dette kapitel blev skrevet i år 1250.\n")

    def test_a_translation_of_the_book_and_a_part_of_it_pass(self):
        from pipeline import refcheck
        self.assertEqual(refcheck.problems(self.SOURCE, self.DANISH, "da"), [])
        half = self.DANISH[:len(self.DANISH) // 2]
        self.assertEqual(refcheck.problems(self.SOURCE, half, "da"), [])
        self.assertEqual(refcheck.problems("", self.DANISH, "da"), [])  # no source yet: only the language checks

    def test_wrong_files_are_named(self):
        from pipeline import refcheck
        self.assertEqual(refcheck.problems(self.SOURCE, self.SOURCE, "da"), [("ref_looks_turkish", {})])
        self.assertEqual(refcheck.problems(self.SOURCE, self.DANISH, "ru"),
                         [("ref_wrong_script", {"found": "latin", "expected": "cyrillic"})])
        self.assertEqual(refcheck.problems(self.SOURCE, self.DANISH, "ur")[0][0], "ref_wrong_script")
        other = ("Ramadan er fastens måned, og den troende afholder sig fra mad og drikke fra daggry til solnedgang i hele "
                 "måneden. Surah al-Baqarah 183 og 185: شَهْرُ رَمَضَانَ الَّذِي أُنْزِلَ فِيهِ الْقُرْآنُ هُدًى لِلنَّاسِ. "
                 "Profeten sagde om fasten mange vigtige ting, som er overleveret hos Bukhari 1891 og Muslim 1151, og "
                 "de lærde har skrevet om dem siden år 1987 i mange bøger og artikler. ") * 3
        self.assertEqual(refcheck.problems(self.SOURCE, other, "da")[0][0], "ref_not_same_book")
        self.assertEqual(refcheck.problems(self.SOURCE, self.DANISH[:120], "da")[0][0], "ref_too_short")
        # A translation that leaves the Arabic out is judged by its numbers only.
        no_arabic = refcheck._ARABIC_WORD.sub("", refcheck._ARABIC_MARKS.sub("", self.DANISH))
        self.assertEqual(refcheck.problems(self.SOURCE, no_arabic, "da"), [])


class QuotaMessageTests(unittest.TestCase):
    def test_reset_time_is_read_from_the_message(self):
        wait = providers.quota_wait_seconds
        self.assertAlmostEqual(wait("You've hit your usage limit. Try again in 2 hours 13 minutes.", 999), 2 * 3600 + 13 * 60 + 15)
        self.assertEqual(wait("429 Too Many Requests. Please retry in 34.5s", 999), 49.5)
        self.assertEqual(wait("Quota exceeded for this project.", 999), 999)
        self.assertGreater(wait("Claude AI usage limit reached|9999999999", 999), 3600)

    def test_short_successful_answer_with_a_number_is_not_a_quota_message(self):
        self.assertFalse(providers.is_quota_message("Hadis 429: Ameller niyetlere göredir.", failed=False))
        self.assertTrue(providers.is_quota_message("Claude AI usage limit reached", failed=False))
        self.assertTrue(providers.is_quota_message("HTTP 429", failed=True))


class MessageTests(unittest.TestCase):
    def test_every_message_has_both_languages_with_the_same_placeholders(self):
        fields = lambda text: {f[1] for f in string.Formatter().parse(text) if f[1]}  # noqa: E731
        for key, texts in i18n.MESSAGES.items():
            self.assertEqual(set(texts), set(i18n.LANGUAGES), key)
            self.assertEqual(fields(texts["tr"]), fields(texts["en"]), key)

    def test_web_interface_texts_have_both_languages(self):
        import re
        src = (ROOT / "pipeline" / "ui" / "app.js").read_text(encoding="utf-8")
        tr_block = src[src.index("  tr: {"):src.index("  en: {")]
        en_block = src[src.index("  en: {"):src.index("};\n\nconst LANGS")]
        entry = re.compile(r"""(?:^|[\s,{])([a-z0-9_]+): ("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')""")
        tr, en = dict(entry.findall(tr_block)), dict(entry.findall(en_block))
        self.assertGreater(len(tr), 100)
        self.assertEqual(set(tr), set(en))
        for key in tr:
            self.assertEqual(sorted(re.findall(r"\{\w+\}", tr[key])), sorted(re.findall(r"\{\w+\}", en[key])), key)

    def test_request_language_overrides_default_only_in_its_thread(self):
        i18n.set_request("en")
        self.addCleanup(i18n.set_request, None)
        self.assertEqual(i18n.t("not_found"), "Not found.")
        self.assertEqual(i18n.note_language(), "English")


CONFIG = """
[stages]
align = "fake"
glossary = "fake"
translate = "fake"
review1 = "fake"
revise1 = "fake"
source_check = "fake"
review2 = ["fake", "fake2"]
reconcile = "fake"
[general]
language = "tr"
segment_size = 120
parallel = 2
timeout = 30
retries = 1
keep_awake = false
[providers.fake]
command = [{python}, {script}]
[providers.fake2]
command = [{python}, {script}]
[languages]
tr = "Turkish"
da = "Danish"
no = "Norwegian"
"""

SOURCE = "\n\n".join([
    "# Birinci Kısım",
    "Namaz dinin direğidir. Her müslüman günde 5 vakit namaz kılar ve bunu terk etmez.",
    "# İkinci Kısım",
    "Oruç Ramazan ayında tutulur. Bu ay 29 veya 30 gün sürer, her günü kıymetlidir.",
    "# Üçüncü Kısım",
    "Zekât malın kırkta biridir. Zengin olan müslüman bunu yılda 1 defa fakirlere verir.",
])
REFERENCE = "\n\n".join(f"Afsnit {i}: dansk tekst om emnet." for i in range(1, 9))


def make_project(root: Path) -> None:
    shutil.copytree(ROOT / "prompts", root / "prompts")
    script = repr(str(ROOT / "tests" / "fake_llm.py")).replace("'", '"')
    python = repr(sys.executable).replace("'", '"')
    (root / "config.toml").write_text(CONFIG.format(python=python, script=script), encoding="utf-8")
    os.environ["FAKE_LLM_LOG"] = str(root / "calls.log")


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.addCleanup(i18n.set_default, "tr")
        make_project(self.root)
        book = self.root / "books" / "sample"
        (book / "source").mkdir(parents=True)
        (book / "references").mkdir()
        (book / "source" / "tr.md").write_text(SOURCE, encoding="utf-8")
        (book / "references" / "da.md").write_text(REFERENCE, encoding="utf-8")
        self.book = book
        self.log = self.root / "calls.log"

    def run_cli(self, *argv, code=0) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            result = main(list(argv), root=self.root)
        self.assertEqual(result, code, out.getvalue())
        return out.getvalue()

    def calls(self) -> Counter:
        return Counter(self.log.read_text(encoding="utf-8").split()) if self.log.exists() else Counter()

    def test_full_run_resume_and_redo(self):
        self.run_cli("--lang", "en", "run", "sample", "no")

        # 3 segments. Per segment: 1 alignment, 1 glossary, 1 translation, 1 + 2 review reports (review1 + review2),
        # 2 revisions (revise1 + reconcile), 1 source check.
        self.assertEqual(self.calls(), Counter({
            "align": 3, "glossary": 3, "translate": 3, "review": 9, "revise": 6, "source_check": 3,
        }))

        # The final text passed through these steps in order: translate → revise1 → source_check → reconcile
        final = (self.book / "output" / "no.md").read_text(encoding="utf-8")
        self.assertEqual(final.count(" (no)+u+k+u"), 6)
        self.assertTrue(final.startswith("# Birinci Kısım (no)+u+k+u\n\nNamaz dinin"))

        # The models were asked to write their notes in the interface language.
        self.assertEqual((self.root / "glossary" / "no.tsv").read_text(encoding="utf-8").splitlines(),
                         ["tr\tno\tnote", "namaz\tnamaz\tnote in English"])

        def decisions(folder):
            issues = read_json(self.book / "work" / "no" / folder / "0001.json")
            return [(i["stage"], i["reviewer"], i["decision"]) for i in issues]

        self.assertEqual(decisions("revise1"), [("review1", "fake", "accepted")])
        self.assertEqual(decisions("source_check"), [("source_check", "fake", "accepted")])
        self.assertEqual(decisions("reconcile"), [("review2", "fake", "accepted"), ("review2", "fake2", "rejected")])

        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("# Translation report: sample → Norwegian (no)", report)
        self.assertIn("Finished segments: 3/3", report)
        self.assertIn("Review (review1): 3 findings (critical 0, major 3, minor 0); accepted 3, rejected 0", report)
        self.assertIn("Source check from the start (source_check): 3 findings (critical 3", report)
        self.assertIn("Review (review2): 6 findings (critical 0, major 6, minor 0); accepted 3, rejected 3", report)
        self.assertIn("major · terminology · review2/fake2 · REJECTED", report)               # rejected major finding is listed
        self.assertIn("critical · omission · source_check/fake · accepted] Missing sentence.", report)  # critical always listed
        self.assertNotIn("review1/fake · accepted", report)                                  # accepted major finding is not

        # A second run makes no LLM calls.
        before = self.calls()
        self.run_cli("run", "sample", "no")
        self.assertEqual(self.calls(), before)

        # A glossary row edited by hand is kept; --redo renews only that stage and later ones, for the chosen segment.
        (self.root / "glossary" / "no.tsv").write_text("tr\tno\tnote\nnamaz\tsalah\tedited by hand\n", encoding="utf-8")
        self.run_cli("run", "sample", "no", "--segments", "2", "--redo", "translate")
        self.assertEqual(self.calls() - before, Counter({"translate": 1, "review": 3, "revise": 2, "source_check": 1}))
        self.assertIn("salah", (self.root / "glossary" / "no.tsv").read_text(encoding="utf-8"))

        before = self.calls()
        self.run_cli("run", "sample", "no", "--segments", "1", "--redo", "review2")
        self.assertEqual(self.calls() - before, Counter({"review": 2, "revise": 1}))

        status = self.run_cli("--lang", "en", "status")
        self.assertIn("reference da: 3/3 segments aligned", status)
        self.assertIn("translate 3/3 · review1 3/3 · revise1 3/3 · source_check 3/3 · review2 6/6 · reconcile 3/3", status)

    def test_turkish_report_and_messages(self):
        out = self.run_cli("--lang", "tr", "run", "sample", "no", "--segments", "1")
        self.assertIn("sample → Norwegian: 1/3 bölüm, referans: da", out)
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("# Çeviri raporu: sample → Norwegian (no)", report)
        self.assertIn("EKSİK ÇIKTI: 3 bölümün 1 tanesi tamamlandı.", report)
        self.assertIn("kritik · eksik · source_check/fake · kabul edildi] Cümle atlanmış.", report)
        self.assertIn("note in Turkish", (self.root / "glossary" / "no.tsv").read_text(encoding="utf-8"))

    def test_quota_limit_waits_and_continues(self):
        os.environ["FAKE_LLM_QUOTA_ONCE"] = str(self.root / "quota.flag")
        self.addCleanup(os.environ.pop, "FAKE_LLM_QUOTA_ONCE")
        min_wait = providers._MIN_WAIT
        providers._MIN_WAIT = 0  # the fake tool says "try again in 1s"
        self.addCleanup(setattr, providers, "_MIN_WAIT", min_wait)

        out = self.run_cli("--lang", "en", "run", "sample", "no", "--segments", "1")
        self.assertIn("[quota] fake reached its usage limit; waiting until", out)
        self.assertEqual(self.calls()["quota"], 1)
        self.assertTrue((self.book / "output" / "no.md").exists())  # the run continued by itself

        status = read_json(self.book / "work" / "run.json")
        self.assertEqual(status["state"], "finished")
        self.assertEqual([e["provider"] for e in status["quota_events"]], ["fake"])
        self.assertEqual(status["quota"], {})
        self.assertIn("fake", read_json(self.root / ".jobs" / "quota.json"))

    def test_estimate_counts_only_remaining_calls(self):
        before = stages.estimate(self._project(), "sample", "no", ["da"])
        self.assertFalse(before["prepared"])
        self.assertGreater(before["segments"], 0)
        self.run_cli("run", "sample", "no", "--segments", "1")
        plan = stages.estimate(self._project(), "sample", "no", ["da"])
        # Segment 1 is finished: 2 segments remain. Per segment: 1 align + 1 glossary + 1 translate + 1 review1
        # + 1 revise1 + 1 source_check + 2 review2 + 1 reconcile = 9 calls; "fake2" does one of the review2 calls.
        self.assertEqual((plan["segments"], plan["selected"]), (3, 3))
        self.assertEqual(plan["calls"], {"fake": 16, "fake2": 2})
        self.assertEqual(stages.estimate(self._project(), "sample", "no", ["da"], "1")["total_calls"], 0)
        status = read_json(self.book / "work" / "run.json")
        self.assertEqual(status["stages"]["translate"], {"done": 1, "failed": 0, "total": 1})
        self.assertEqual(status["stages"]["align"], {"done": 1, "failed": 0, "total": 1})  # counted in segments
        self.assertIn("translate", status["durations"])

    def _project(self):
        from pipeline.core import Project
        return Project.load(self.root)

    def test_models_are_passed_to_the_tools_and_names_are_file_safe(self):
        cfg = (self.root / "config.toml").read_text(encoding="utf-8")
        cfg = cfg.replace('translate = "fake"', 'translate = "fake/model-a"')
        cfg = cfg.replace('review2 = ["fake", "fake2"]', 'review2 = ["fake/model:b@high", "fake2"]')
        # The thinking level goes to the tool with its own option; a tool without that option gets nothing.
        cfg = cfg.replace('[providers.fake2]', 'effort = ["--effort", "{effort}"]\n[providers.fake2]')
        cfg = cfg.replace('revise1 = "fake"', 'revise1 = "fake2@low"')
        (self.root / "config.toml").write_text(cfg, encoding="utf-8")
        os.environ["FAKE_LLM_ARGS_LOG"] = str(self.root / "models.log")
        self.addCleanup(os.environ.pop, "FAKE_LLM_ARGS_LOG")

        self.run_cli("run", "sample", "no", "--segments", "1")
        models = Counter((self.root / "models.log").read_text().split())
        self.assertEqual((models["model-a"], models["model:b@high"]), (1, 1))
        self.assertEqual(models["-@low"], 0)  # fake2 has no effort option: the level is not passed
        files = sorted(p.name for p in (self.book / "work" / "no" / "review2").glob("*.json"))
        self.assertEqual(files, ["0001.fake2.json", "0001.fake_model_b_high.json"])
        reviewers = [i["reviewer"] for i in read_json(self.book / "work" / "no" / "reconcile" / "0001.json")]
        self.assertEqual(reviewers, ["fake/model:b@high", "fake2"])

    def test_incomplete_translation_is_rejected_and_retried(self):
        os.environ["FAKE_LLM_TRUNCATE"] = f"{self.root / 'trunc.count'}:1"
        self.addCleanup(os.environ.pop, "FAKE_LLM_TRUNCATE")
        self.run_cli("run", "sample", "no", "--segments", "1", "--until", "translate")
        self.assertEqual(self.calls()["translate-truncated"], 1)
        self.assertEqual(self.calls()["translate"], 1)  # the second answer was complete and accepted
        text = (self.book / "work" / "no" / "translate" / "0001.md").read_text(encoding="utf-8")
        self.assertEqual(len(text.strip().split("\n\n")), 2)

    def test_persistently_incomplete_translation_fails_the_segment(self):
        os.environ["FAKE_LLM_TRUNCATE"] = f"{self.root / 'trunc.count'}:99"
        self.addCleanup(os.environ.pop, "FAKE_LLM_TRUNCATE")
        out = self.run_cli("--lang", "en", "run", "sample", "no", "--segments", "1", "--until", "translate", code=1)
        self.assertIn("answer rejected: the answer has 1 paragraphs, the source 2", out)
        self.assertEqual(self.calls()["translate-truncated"], 3)
        self.assertFalse((self.book / "work" / "no" / "translate" / "0001.md").exists())
        status = read_json(self.book / "work" / "run.json")
        self.assertEqual(status["state"], "failed")
        self.assertIn("answer rejected", status["failures"][0]["error"])

    def test_review_without_reading_proof_is_asked_again(self):
        os.environ["FAKE_LLM_NO_PROOF_ONCE"] = str(self.root / "noproof.flag")
        self.addCleanup(os.environ.pop, "FAKE_LLM_NO_PROOF_ONCE")
        self.run_cli("run", "sample", "no", "--segments", "1", "--until", "review1")
        self.assertEqual(self.calls()["review-noproof"], 1)
        self.assertEqual(self.calls()["review"], 1)
        saved = read_json(self.book / "work" / "no" / "review1" / "0001.fake.json")
        self.assertEqual(saved["paragraphs"], 2)
        self.assertEqual(len(saved["issues"]), 1)

    def test_finding_without_decision_is_asked_again(self):
        os.environ["FAKE_LLM_UNDECIDED_ONCE"] = str(self.root / "undecided.flag")
        self.addCleanup(os.environ.pop, "FAKE_LLM_UNDECIDED_ONCE")
        self.run_cli("run", "sample", "no", "--segments", "1", "--until", "revise1")
        self.assertEqual(self.calls()["revise-undecided"], 1)
        self.assertEqual(self.calls()["revise"], 1)
        decisions = [i["decision"] for i in read_json(self.book / "work" / "no" / "revise1" / "0001.json")]
        self.assertEqual(decisions, ["accepted"])

    def test_silent_reviewer_is_reported(self):
        config = self.root / "config.toml"
        text = config.read_text(encoding="utf-8")
        fake2 = text.index("[providers.fake2]")
        end = text.index("\n", text.index("command", fake2))
        config.write_text(text[:end - 1] + ', "--silent"]' + text[end:], encoding="utf-8")
        self.run_cli("--lang", "en", "run", "sample", "no")
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("review2 · fake2: 3 segments, no findings in 3, 0 findings in total", report)
        self.assertIn("review2 · fake: 3 segments, no findings in 0, 3 findings in total", report)
        self.assertIn("ATTENTION: fake2 wrote no findings in these segments, but another reviewer of the same round found critical or major "
                      "errors in them: 0001, 0002, 0003", report)
        rows = stages.book_status(Project.load(self.root), "sample")["languages"]["no"]["reviews"]
        self.assertEqual([(r["stage"], r["reviewer"], r["empty"], len(r["missed"])) for r in rows],
                         [("review1", "fake", 0, 0), ("review2", "fake", 0, 0), ("review2", "fake2", 3, 3)])

    def test_refused_account_fails_at_once_with_a_clear_message(self):
        os.environ["FAKE_LLM_REFUSED"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_LLM_REFUSED")
        i18n.set_default("en")
        with self.assertRaises(providers.LLMError) as caught:
            providers.run(Project.load(self.root), "fake", "prompt")
        self.assertIn("does not accept this account (IneligibleTierError: This client is no longer supported", str(caught.exception))
        self.assertEqual(self.calls(), Counter({"refused": 1}))  # no retries

    def test_package_holds_the_application_and_no_user_data(self):
        (self.root / ".runtime").mkdir()
        (self.root / ".runtime" / "big").write_text("x", encoding="utf-8")
        (self.root / "translate").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / "translate").chmod(0o755)
        out = self.root / "share.zip"
        self.run_cli("package", "--out", str(out))
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            mode = z.getinfo("TranslationPipeline/translate").external_attr >> 16
        self.assertIn("TranslationPipeline/config.toml", names)
        self.assertIn("TranslationPipeline/prompts/review.md", names)
        self.assertFalse([n for n in names if "books/" in n or ".runtime" in n or "calls.log" in n])
        if not system.IS_WINDOWS:
            self.assertTrue(mode & 0o100)  # the launcher stays executable

    def test_changed_glossary_or_instructions_are_reported_for_finished_segments(self):
        self.run_cli("--lang", "en", "run", "sample", "no")
        proj = Project.load(self.root)
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"]), {})
        # A glossary row changes: only the segment that contains the term is old ("namaz" is in segment 1).
        (self.root / "glossary" / "no.tsv").write_text("tr\tno\tnote\nnamaz\tsalah\tedited by hand\n", encoding="utf-8")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"]), {"translate": ["0001"]})
        out = self.run_cli("--lang", "en", "run", "sample", "no")
        self.assertIn("produce these segments again from the 'translate' step: 0001", out)
        self.assertIn("from the 'translate' step: 0001", (self.book / "output" / "no.report.md").read_text(encoding="utf-8"))
        # Producing the segment again clears the report.
        self.run_cli("run", "sample", "no", "--segments", "1", "--redo", "translate")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"]), {})
        # Changed review instructions: every segment is old from the first review on. Another set of references: from the translation on.
        review = self.root / "prompts" / "review.md"
        review.write_text(review.read_text(encoding="utf-8") + "\nBe strict.\n", encoding="utf-8")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"]), {"review1": ["0001", "0002", "0003"]})
        self.assertEqual(stages.stale_for(proj, "sample", "no", []), {"translate": ["0001", "0002", "0003"]})

    def set_flow(self, flow: str, extra: str = "") -> Project:
        path = self.root / "config.toml"
        path.write_text(path.read_text(encoding="utf-8").replace("[stages]\n", f"[stages]\nflow = {flow}\n{extra}", 1),
                        encoding="utf-8")
        return Project.load(self.root)

    def test_edited_flow_runs_its_own_steps_in_order(self):
        proj = self.set_flow('["source_check", "review3"]', 'review3 = ["fake2"]\nrevise3 = "fake"\n')
        self.assertEqual(stages.all_stages(proj), ["prepare", "align", "glossary", "translate", "source_check",
                                                   "review3", "revise3", "assemble"])
        self.run_cli("--lang", "en", "run", "sample", "no")
        work = self.book / "work" / "no"
        self.assertFalse((work / "review1").exists())
        self.assertIn("from translate", (work / "source_check" / "0001.in").read_text(encoding="utf-8"))
        self.assertIn("from source_check", (work / "review3" / "0001.fake2.in").read_text(encoding="utf-8"))
        final = (work / "revise3" / "0001.md").read_text(encoding="utf-8").strip()
        self.assertTrue((self.book / "output" / "no.md").read_text(encoding="utf-8").startswith(final))
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("- Review (review3):", report)
        self.assertNotIn("(review1)", report)
        self.run_cli("run", "sample", "no", "--until", "review1", code=1)  # not a stage of this flow

    def test_changed_flow_marks_segments_that_worked_on_another_text(self):
        self.run_cli("--lang", "en", "run", "sample", "no")
        work = self.book / "work" / "no"
        # Fingerprints written before the flow was editable have no "from" line: the diagram order is assumed.
        for f in work.glob("*/*.in"):
            f.write_text(f.read_text(encoding="utf-8").split("\n")[0] + "\n", encoding="utf-8")
        self.assertEqual(stages.stale_for(Project.load(self.root), "sample", "no", ["da"]), {})
        # Without the source check, the second review works on the text of revise1, not of source_check.
        proj = self.set_flow('["review1", "review2"]')
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"]), {"review2": ["0001", "0002", "0003"]})

    def set_nodes(self, flow: str, stages_extra: str, nodes: str) -> Project:
        path = self.root / "config.toml"
        text = path.read_text(encoding="utf-8").replace("[general]\n", f"[nodes]\n{nodes}\n[general]\n", 1)
        path.write_text(text, encoding="utf-8")
        return self.set_flow(flow, stages_extra)

    def test_flow_rules(self):
        cfg = {"nodes": {"gate1": {"back_to": "review1", "max": 2}, "gate2": {"back_to": "review1", "max": 1},
                         "custom1": {"title": "Üslup", "mode": "report"}}}
        self.assertIsNone(stages.flow_problem(["review1", "revise1", "gate1"], cfg))
        self.assertIsNone(stages.flow_problem(["custom1", "review1", "apply1"], cfg))  # two reports, one apply
        self.assertEqual(stages.flow_problem(["review1", "source_check", "revise1"], cfg), "flow_unapplied:review1")
        self.assertEqual(stages.flow_problem(["revise1", "custom1"], cfg), "flow_unapplied:custom1")
        self.assertEqual(stages.flow_problem(["gate1", "review1", "revise1"], cfg), "flow_gate_invalid:gate1")  # forward
        # Loops do not overlap: gate2 cannot send back past gate1.
        self.assertEqual(stages.flow_problem(["review1", "revise1", "gate1", "source_check", "gate2"], cfg),
                         "flow_gate_invalid:gate2")
        self.assertEqual(stages.flow_problem(["custom2"], cfg), "flow_custom_invalid")
        self.assertEqual(stages.flow_problem(["review1", "revise1"] * 2, cfg), "flow_invalid")  # a node twice

    def test_checkpoint_sends_a_segment_back_and_its_findings_are_applied(self):
        self.set_nodes('["review1", "revise1", "gate1"]', 'gate1 = "fake2"\n', 'gate1 = { back_to = "review1", max = 2 }')
        os.environ["FAKE_LLM_GATE_FAILS"] = f"{self.root / 'gate.count'}:1"  # only the first check finds a problem
        self.addCleanup(os.environ.pop, "FAKE_LLM_GATE_FAILS")
        self.run_cli("--lang", "en", "run", "sample", "no")
        self.assertEqual(self.calls()["gate"], 3)          # 3 segments pass in the end
        self.assertEqual(self.calls()["gate-fail"], 1)     # one was sent back once
        work = self.book / "work" / "no"
        again = [p.name for p in (work / "gate1.2").glob("*.json")]
        self.assertEqual(len(again), 1)                    # only that segment was checked again
        sid = again[0][:4]
        self.assertEqual(sorted(p.name for p in (work / "review1.2").glob("*.json")), [f"{sid}.fake.json"])
        applied = read_json(work / "revise1.2" / f"{sid}.json")
        self.assertIn("gate1", {i["stage"] for i in applied})           # the checkpoint's findings were applied
        self.assertIn("from revise1", (work / "review1.2" / f"{sid}.fake.in").read_text(encoding="utf-8"))
        out = (self.book / "output" / "no.md").read_text(encoding="utf-8")
        self.assertIn((work / "revise1.2" / f"{sid}.md").read_text(encoding="utf-8").strip(), out)
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("- Checkpoint (gate1): sent back 1 times; segments with serious problems left: 0", report)
        before = self.calls()
        self.run_cli("run", "sample", "no")                # everything is done: no call is made again
        self.assertEqual(self.calls(), before)
        self.assertEqual(stages.stale_for(Project.load(self.root), "sample", "no", ["da"]), {})

    def test_checkpoint_stops_sending_back_at_its_limit(self):
        self.set_nodes('["review1", "revise1", "gate1"]', 'gate1 = "fake"\n', 'gate1 = { back_to = "revise1", max = 1 }')
        os.environ["FAKE_LLM_GATE_FAILS"] = f"{self.root / 'gate.count'}:99"  # every check finds a problem
        self.addCleanup(os.environ.pop, "FAKE_LLM_GATE_FAILS")
        self.run_cli("--lang", "en", "run", "sample", "no")
        self.assertEqual(self.calls()["gate-fail"], 6)     # each segment: checked, sent back once, checked again
        self.assertEqual(self.calls()["revise"], 6)
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("segments with serious problems left: 3", report)
        self.assertIn("major · mistranslation · gate1.2/fake · no decision] Still wrong.", report)

    def test_custom_steps_follow_their_instructions(self):
        self.set_nodes('["custom1", "review1", "apply1", "custom2"]', 'custom1 = ["fake2"]\napply1 = "fake"\ncustom2 = "fake"\n',
                       'custom1 = { title = "Terimler", mode = "report" }\ncustom2 = { title = "Üslup", mode = "rewrite" }')
        custom = self.root / "prompts" / "custom"
        custom.mkdir()
        (custom / "custom1.md").write_text("Terimleri sözlükle karşılaştır.\n", encoding="utf-8")
        (custom / "custom2.md").write_text("Üslubu sadeleştir.\n", encoding="utf-8")
        self.run_cli("--lang", "en", "run", "sample", "no", "--segments", "1")
        self.assertEqual(self.calls()["custom-report"], 1)
        self.assertEqual(self.calls()["custom-rewrite"], 1)
        work = self.book / "work" / "no"
        self.assertEqual({i["stage"] for i in read_json(work / "apply1" / "0001.json")}, {"custom1", "review1"})
        out = (self.book / "output" / "no.md").read_text(encoding="utf-8")
        self.assertIn((work / "custom2" / "0001.md").read_text(encoding="utf-8").strip(), out)
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("- Custom step: Üslup (custom2):", report)
        proj = Project.load(self.root)
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"], "1"), {})
        (custom / "custom2.md").write_text("Başka bir talimat.\n", encoding="utf-8")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"], "1"), {"custom2": ["0001"]})

    def test_publishing_rules_reach_every_text_step_and_mark_old_segments(self):
        proj = Project.load(self.root)
        (self.root / "prompts" / "rules.md").write_text("Kural: Allah ismi çevrilmez.\n", encoding="utf-8")
        for name in ("translate", "review", "revise", "source_check", "glossary"):
            text = proj.prompt(name, **{k: "x" for k in ("target_lang", "ref_langs", "context", "glossary", "references",
                                                        "source", "translation", "issues", "note_lang")})
            self.assertIn("<publishing_rules>\nKural: Allah ismi çevrilmez.\n</publishing_rules>", text, name)
        self.run_cli("run", "sample", "no", "--segments", "1")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"], "1"), {})
        (self.root / "prompts" / "rules.md").write_text("Kural: değişti.\n", encoding="utf-8")
        self.assertEqual(stages.stale_for(proj, "sample", "no", ["da"], "1"), {"translate": ["0001"]})

    def test_missing_segments_are_marked_in_the_output(self):
        self.run_cli("--lang", "en", "run", "sample", "no", "--segments", "2")
        out = (self.book / "output" / "no.md").read_text(encoding="utf-8")
        self.assertTrue(out.startswith("[[MISSING SEGMENT 0001"))
        self.assertIn("[[MISSING SEGMENT 0003", out)
        self.assertIn("# İkinci Kısım", out)
        report = (self.book / "output" / "no.report.md").read_text(encoding="utf-8")
        self.assertIn("Segments missing from the output (marked): 0001, 0003", report)

    def test_partial_run_stops_at_requested_stage(self):
        self.run_cli("run", "sample", "no", "--segments", "1", "--until", "translate")
        self.assertEqual(self.calls(), Counter(align=1, glossary=1, translate=1))
        self.assertFalse((self.book / "output").exists())

    def test_changed_source_is_refused(self):
        self.run_cli("run", "sample", "no", "--until", "prepare")
        (self.book / "source" / "tr.md").write_text(SOURCE + "\n\nYeni paragraf.", encoding="utf-8")
        self.assertIn("has changed", self.run_cli("--lang", "en", "run", "sample", "no", code=1))


if __name__ == "__main__":
    unittest.main()
