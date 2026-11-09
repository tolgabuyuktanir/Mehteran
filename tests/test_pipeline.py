"""Run from the project root: python3 -m unittest discover -s tests -v"""

import io
import os
import shutil
import string
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

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


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_docx_keeps_headings_and_footnotes(self):
        make_docx(self.tmp / "tr.docx")
        self.assertEqual(documents.read_blocks(self.tmp / "tr.docx"), [
            "# Birinci Kısım",
            "Namaz dinin direğidir.[^1]\n[^1]: Hadîs-i şerîf.",
            "İkinci paragraf.",
        ])

    def test_epub_follows_spine_order(self):
        make_epub(self.tmp / "da.epub")
        self.assertEqual(documents.read_blocks(self.tmp / "da.epub"),
                         ["## Kapitel 1", "Første avsnitt.", "Andet afsnit."])

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
        self.assertEqual(blocks[1], "Birinci kalın ve eğik paragraf.[^1]\n[^1]: Dipnot metni.")

    def test_moved_footnote_line_and_dialogue_dash_are_kept(self):
        md = "Birinci paragraf.[^1]\n\nİkinci paragraf.\n[^1]: Kaymış dipnot.\n\n- Diyalog satırı."
        page = export.to_html(md, "K", "tr", lists=False)
        self.assertIn('<li id="fn1">Kaymış dipnot.', page)
        self.assertIn("<p>- Diyalog satırı.</p>", page)
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


class ConfigFileTests(unittest.TestCase):
    def test_stage_board_is_saved_and_comments_are_kept(self):
        import tomllib
        text = (ROOT / "config.toml").read_text(encoding="utf-8")
        assignment = {stage: ["claude"] for stage in stages.LLM_STAGES}
        assignment["translate"] = ["chatgpt/gpt-x.1"]
        assignment["review2"] = ["gemini/gemini-pro", "claude/opus"]
        new = configfile.set_models(configfile.set_stages(text, assignment), "claude", ["opus", "sonnet"])
        cfg = tomllib.loads(new)
        self.assertEqual(cfg["stages"]["translate"], "chatgpt/gpt-x.1")
        self.assertEqual(cfg["stages"]["review2"], ["gemini/gemini-pro", "claude/opus"])
        self.assertEqual(cfg["stages"]["review1"], ["claude"])
        self.assertEqual(cfg["providers"]["claude"]["models"], ["opus", "sonnet"])
        self.assertEqual(cfg["languages"], tomllib.loads(text)["languages"])
        self.assertIn("# interface language", new)
        self.assertIn("# 1  first translation", new)


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
        self.assertEqual(len({str(d) for d in dirs}), 3)  # codex, gemini, node
        self.assertTrue(all(str(d).startswith(str(root / ".runtime")) for d in dirs))

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
        self.assertIn("First review (review1): 3 findings (critical 0, major 3, minor 0); accepted 3, rejected 0", report)
        self.assertIn("Source check from the start (source_check): 3 findings (critical 3", report)
        self.assertIn("Second independent review (review2): 6 findings (critical 0, major 6, minor 0); accepted 3, rejected 3", report)
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
        cfg = cfg.replace('review2 = ["fake", "fake2"]', 'review2 = ["fake/model:b", "fake2"]')
        (self.root / "config.toml").write_text(cfg, encoding="utf-8")
        os.environ["FAKE_LLM_ARGS_LOG"] = str(self.root / "models.log")
        self.addCleanup(os.environ.pop, "FAKE_LLM_ARGS_LOG")

        self.run_cli("run", "sample", "no", "--segments", "1")
        models = Counter((self.root / "models.log").read_text().split())
        self.assertEqual((models["model-a"], models["model:b"]), (1, 1))
        files = sorted(p.name for p in (self.book / "work" / "no" / "review2").iterdir())
        self.assertEqual(files, ["0001.fake2.json", "0001.fake_model_b.json"])
        reviewers = [i["reviewer"] for i in read_json(self.book / "work" / "no" / "reconcile" / "0001.json")]
        self.assertEqual(reviewers, ["fake/model:b", "fake2"])

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
        self.assertIn("ATTENTION: fake2 wrote no findings in these segments, but the other reviewer found critical or major "
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
