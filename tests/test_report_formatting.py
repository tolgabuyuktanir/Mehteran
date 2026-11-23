import io
import unittest
import zipfile
from xml.etree import ElementTree as ET

from mehteran import tables


class ReportFormattingTests(unittest.TestCase):
    def test_compact_report_exports(self):
        report = "## Karar\nÖzet\n* **Onay**\n3. Kontrol et\n> Kaynak\n~~~txt\n# örnek\n| A |\n|---|\n~~~"
        page = tables.to_html(report, "Rapor", "tr")
        for element in ("<h2>Karar</h2>", "<li><strong>Onay</strong></li>", '<li value="3">Kontrol et</li>',
                        "<blockquote>Kaynak</blockquote>", "<pre><code># örnek\n| A |\n|---|</code></pre>"):
            self.assertIn(element, page)
        with zipfile.ZipFile(io.BytesIO(tables.to_docx(report, "Rapor", "tr"))) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = ["".join(p.itertext()) for p in root.findall(".//w:body/w:p", ns)]
        for text in ("Karar", "Özet", "• Onay", "3. Kontrol et", "# örnek", "| A |"):
            self.assertIn(text, texts)
        self.assertIsNotNone(root.find(".//w:rFonts[@w:ascii='Consolas']", ns))
