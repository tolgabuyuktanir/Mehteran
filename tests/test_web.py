"""Tests of the web interface server. They make no real LLM calls; they use the fake tool."""

import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from unittest import mock
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from pipeline import system  # noqa: E402
from pipeline.core import Project  # noqa: E402
from pipeline.web import App, make_handler  # noqa: E402
from test_pipeline import REFERENCE, SOURCE, make_project, make_template  # noqa: E402


class WebTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        make_project(self.root)
        (self.root / "books").mkdir()

        self.app = App(Project.load(self.root))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=None, raw=None, token=True, host=None, lang="en"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if token:
            req.add_header("X-Token", self.app.token)
        if host:
            req.add_header("Host", host)
        if lang:
            req.add_header("X-Lang", lang)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def json(self, *args, **kwargs):
        status, body = self.call(*args, **kwargs)
        return status, json.loads(body)

    def test_page_carries_token_and_api_requires_it(self):
        status, body = self.call("GET", "/", token=False)
        self.assertEqual(status, 200)
        self.assertIn(self.app.token.encode(), body)
        self.assertEqual(self.call("GET", "/api/books", token=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/books", host="evil.example:80")[0], 403)
        self.assertEqual(self.call("GET", "/../config.toml", token=False)[0], 404)

    def test_messages_follow_the_request_language(self):
        self.assertEqual(self.json("GET", "/api/books", token=False, lang="en")[1]["error"],
                         "Invalid session key. Reload the page.")
        self.assertEqual(self.json("GET", "/api/books", token=False, lang="tr")[1]["error"],
                         "Oturum anahtarı geçersiz. Sayfayı yenileyin.")
        prompts = self.json("GET", "/api/prompts", lang="tr")[1]
        self.assertEqual(prompts[0]["description"], "Yayın ilkeleri: bütün adımlarda geçerli kurallar")
        self.assertEqual(prompts[1]["description"], "1. adım: ilk tercüme")

    def test_book_upload_and_validation(self):
        status, data = self.json("POST", "/api/books", {"name": "Büyük İlmihal"})
        self.assertEqual((status, data["name"]), (200, "buyuk-ilmihal"))
        self.assertEqual(self.call("POST", "/api/books", {"name": "Büyük İlmihal"})[0], 409)

        base = "/api/books/buyuk-ilmihal"
        # The extension is .docx but the content is not: rejected.
        self.assertEqual(self.call("PUT", f"{base}/source?file=book.docx", raw=b"not a zip")[0], 400)
        self.assertEqual(self.call("PUT", f"{base}/source?file=book.exe", raw=b"x")[0], 400)
        self.assertEqual(self.call("PUT", f"{base}/references/xx?file=da.md", raw=b"x")[0], 400)  # unknown language
        self.assertEqual(self.call("PUT", "/api/books/..%2Fx/source?file=a.md", raw=b"x")[0], 404)

        docx = self.root / "k.docx"
        with zipfile.ZipFile(docx, "w") as z:
            z.writestr("word/document.xml", "<x/>")
        self.assertEqual(self.call("PUT", f"{base}/source?file=k.docx", raw=docx.read_bytes())[0], 200)
        # A new source replaces the old one; the path in the file name is ignored.
        self.assertEqual(self.call("PUT", f"{base}/source?file=../../tr.md", raw=SOURCE.encode())[0], 200)
        self.assertEqual(sorted(p.name for p in (self.root / "books" / "buyuk-ilmihal" / "source").iterdir()), ["tr.md"])
        self.assertEqual(self.call("PUT", f"{base}/references/da?file=dansk.md", raw=REFERENCE.encode())[0], 200)

        status, books = self.json("GET", "/api/books")
        self.assertEqual(books[0]["source"], ["tr.md"])
        self.assertEqual(books[0]["references"], [{"lang": "da", "file": "da.md"}])

        self.assertEqual(self.json("DELETE", f"{base}/references/da")[0], 200)
        self.assertFalse((self.root / "books" / "buyuk-ilmihal" / "references" / "da.md").exists())

    def test_prompt_edit_requires_placeholders(self):
        status, prompts = self.json("GET", "/api/prompts")
        translate = next(p for p in prompts if p["name"] == "translate")
        self.assertIn("source", translate["required"])
        self.assertFalse(translate["changed"])

        status, data = self.json("PUT", "/api/prompts/translate", {"text": "Translate.\n{{source}}"})
        self.assertEqual(status, 400)
        self.assertIn("missing placeholders", data["error"])
        status, data = self.json("PUT", "/api/prompts/translate", {"text": translate["text"] + "\n{{unknown}}"})
        self.assertIn("unknown placeholders", data["error"])

        edited = translate["text"] + "\nAlways keep the word 'Allah' unchanged.\n"
        self.assertEqual(self.json("PUT", "/api/prompts/translate", {"text": edited})[0], 200)
        self.assertEqual((self.root / "prompts" / "translate.md").read_text(encoding="utf-8"), edited)
        self.assertTrue(next(p for p in self.json("GET", "/api/prompts")[1] if p["name"] == "translate")["changed"])
        self.assertEqual(self.json("POST", "/api/prompts/translate/restore")[0], 200)
        self.assertNotIn("Allah", (self.root / "prompts" / "translate.md").read_text(encoding="utf-8"))

    def test_estimate_before_preparation(self):
        self.json("POST", "/api/books", {"name": "sample"})
        self.call("PUT", "/api/books/sample/source?file=tr.md", raw=SOURCE.encode())
        status, plan = self.json("POST", "/api/books/sample/estimate", {"lang": "no", "references": []})
        self.assertEqual(status, 200, plan)
        self.assertFalse(plan["prepared"])
        self.assertGreater(plan["total_calls"], 0)
        self.assertNotIn("fake", [p for p, n in plan["calls"].items() if n == 0])

    def test_source_preview_prepares_the_book_without_model_calls(self):
        self.json("POST", "/api/books", {"name": "kitap"})
        self.call("PUT", "/api/books/kitap/source?file=tr.md", raw=SOURCE.encode("utf-8"))
        status, data = self.json("POST", "/api/books/kitap/preview", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["segments"], 3)
        self.assertIn("Segment 1", data["text"])
        self.assertIn("Namaz dinin direğidir", data["text"])
        self.assertFalse((self.root / "calls.log").exists())
        _, books = self.json("GET", "/api/books")
        self.assertTrue(books[0]["prepared"])

    def test_workflow_board_save_and_validation(self):
        settings = self.json("GET", "/api/settings")[1]
        board = settings["stages"]
        self.assertEqual(board["review2"], ["fake", "fake2"])
        self.assertIn("fake", settings["providers"])

        board["translate"] = ["fake2/some-model"]
        board["review2"] = ["fake", "fake2/other:model"]
        status, data = self.json("PUT", "/api/stages", {"stages": board, "flow": settings["flow"],
                                                       "models": {"fake2": ["some-model", "bad model!"]}})
        self.assertEqual(status, 200, data)
        settings = self.json("GET", "/api/settings")[1]
        self.assertEqual(settings["stages"]["translate"], ["fake2/some-model"])
        self.assertEqual(settings["stages"]["review2"], ["fake", "fake2/other:model"])
        self.assertEqual(settings["providers"]["fake2"]["models"], ["some-model"])

        bad = dict(board, translate=["fake", "fake2"])                     # one model only
        self.assertEqual(self.call("PUT", "/api/stages", {"stages": bad, "flow": settings["flow"]})[0], 400)
        bad = dict(board, translate=["unknown/x"])                          # unknown tool
        self.assertEqual(self.call("PUT", "/api/stages", {"stages": bad, "flow": settings["flow"]})[0], 400)
        bad = dict(board, review1=[])                                       # empty step
        self.assertEqual(self.call("PUT", "/api/stages", {"stages": bad, "flow": settings["flow"]})[0], 400)
        self.assertEqual(self.json("POST", "/api/models/test", {"name": "fake2/some-model"})[0], 200)

    def test_export_formats(self):
        self.json("POST", "/api/books", {"name": "sample"})
        out = self.root / "books" / "sample" / "output"
        out.mkdir()
        (out / "no.md").write_text("# Del\n\nTekst.[^1]\n[^1]: Note.\n", encoding="utf-8")
        (out / "no.report.md").write_text("# Report\n\n- one\n", encoding="utf-8")
        base = "/api/books/sample/export/no"
        status, data = self.call("GET", f"{base}/translation/docx")
        self.assertEqual(status, 200)
        self.assertIn("word/footnotes.xml", zipfile.ZipFile(io.BytesIO(data)).namelist())
        # Without a browser the page opens with the print dialog; with one, the answer is a PDF file.
        with mock.patch.object(system, "find_browser", return_value=None):
            status, data = self.call("GET", f"{base}/translation/pdf")
        self.assertIn(b"window.print", data)
        if system.find_browser():
            status, data = self.call("GET", f"{base}/translation/pdf")
            self.assertTrue(data.startswith(b"%PDF"), data[:100])
        status, data = self.call("GET", f"{base}/report/html")
        self.assertIn(b"<li>one</li>", data)
        self.assertEqual(self.call("GET", f"{base}/translation/exe")[0], 404)
        self.assertEqual(self.call("GET", "/api/books/sample/export/da/translation/md")[0], 404)

    def test_export_layout_and_word_template(self):
        import tomllib
        self.json("POST", "/api/books", {"name": "sample"})
        out = self.root / "books" / "sample" / "output"
        out.mkdir()
        (out / "no.md").write_text("# Del\n\nTekst.[^1]\n[^1]: Note.\n", encoding="utf-8")
        (out / "no.report.md").write_text("# Report\n\n- one\n", encoding="utf-8")
        base = "/api/books/sample/export/no"
        status, settings = self.json("GET", "/api/settings")
        self.assertEqual(settings["export"]["page_size"], "A4")  # the test config has no [export]: the defaults
        self.assertEqual(settings["word_template"], "")

        layout = {**settings["export"], "page_size": "16x24", "font": "Minion Pro", "font_size": 11}
        self.assertEqual(self.json("PUT", "/api/export", layout)[0], 200)
        self.assertEqual(tomllib.loads((self.root / "config.toml").read_text(encoding="utf-8"))["export"]["font_size"], 11.0)
        self.assertIn(b"size: 160mm 240mm", self.call("GET", f"{base}/translation/html")[1])
        self.assertIn(b"size: A4", self.call("GET", f"{base}/report/html")[1])
        status, error = self.json("PUT", "/api/export", {**layout, "font": "x</style>"})
        self.assertEqual(status, 400)
        self.assertIn("font", error["error"])
        self.assertEqual(self.json("PUT", "/api/export", {**layout, "margin_top": 0})[0], 400)

        # The template: refused when it is not a usable Word file, used for the translation, removed again.
        self.assertEqual(self.call("PUT", "/api/export/template?file=t.pdf", raw=b"%PDF")[0], 400)
        self.assertEqual(self.call("PUT", "/api/export/template?file=t.docx", raw=b"not a zip")[0], 400)
        status, data = self.json("PUT", "/api/export/template?file=Yay%C4%B1nevi.dotx", raw=make_template(dotx=True))
        self.assertEqual(status, 200, data)
        self.assertEqual(self.json("GET", "/api/settings")[1]["word_template"], "Yayınevi.dotx")
        with zipfile.ZipFile(io.BytesIO(self.call("GET", f"{base}/translation/docx")[1])) as z:
            self.assertIn("Balk1", z.read("word/document.xml").decode())
        with zipfile.ZipFile(io.BytesIO(self.call("GET", f"{base}/report/docx")[1])) as z:
            self.assertNotIn("word/header1.xml", z.namelist())
        self.assertIn(b"size: 160mm 240mm", self.call("GET", f"{base}/translation/html")[1])  # PDF/HTML keep the settings
        self.assertEqual(self.json("PUT", "/api/export", layout)[0], 200)  # saving the settings keeps the template
        self.assertEqual(self.json("GET", "/api/settings")[1]["word_template"], "Yayınevi.dotx")
        self.assertEqual(self.json("DELETE", "/api/export/template")[0], 200)
        self.assertEqual(self.json("GET", "/api/settings")[1]["word_template"], "")
        self.assertFalse((self.root / "export" / "word-template.docx").exists())
        with zipfile.ZipFile(io.BytesIO(self.call("GET", f"{base}/translation/docx")[1])) as z:
            self.assertIn("Minion Pro", z.read("word/styles.xml").decode())

    def test_run_that_fails_at_once_reports_the_reason(self):
        self.json("POST", "/api/books", {"name": "sample"})
        self.call("PUT", "/api/books/sample/source?file=tr.md", raw=SOURCE.encode())
        cfg = (self.root / "config.toml").read_text(encoding="utf-8")
        (self.root / "config.toml").write_text(cfg.replace('translate = "fake"', 'translate = "missing"')
                                               .replace("[providers.fake2]", '[providers.missing]\ncommand = ["no-such-tool-xyz"]\n[providers.fake2]'),
                                               encoding="utf-8")
        status, data = self.json("POST", "/api/books/sample/run", {"lang": "no"})
        self.assertEqual(status, 400, data)
        self.assertIn("could not start", data["error"])
        self.assertIn("missing", data["error"])

    def test_rejected_upload_still_gets_an_answer(self):
        self.json("POST", "/api/books", {"name": "sample"})
        status, data = self.json("PUT", "/api/books/sample/source?file=big.exe", raw=b"x" * (8 * 1024 * 1024))
        self.assertEqual(status, 400)
        self.assertIn("Unsupported file type", data["error"])

    def test_model_name_cannot_look_like_an_option(self):
        board = self.json("GET", "/api/settings")[1]["stages"]
        board["translate"] = ["fake/--dangerous-flag"]
        self.assertEqual(self.call("PUT", "/api/stages", {"stages": board})[0], 400)
        self.assertEqual(self.call("POST", "/api/models/test", {"name": "fake/-x"})[0], 400)

    def test_add_language(self):
        self.assertEqual(self.json("POST", "/api/languages", {"code": "tg", "name": "Tajik"})[0], 200)
        self.assertEqual(self.json("GET", "/api/settings")[1]["languages"]["tg"], "Tajik")
        self.assertEqual(self.json("POST", "/api/languages", {"code": "tg", "name": "Tajik"})[0], 409)
        self.assertEqual(self.json("POST", "/api/languages", {"code": 'x"]', "name": "Bad"})[0], 400)
        self.assertEqual(self.json("POST", "/api/languages", {"code": "xy", "name": 'Bad"\n[stages]'})[0], 400)

    def wait_idle(self, book, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.json("GET", f"/api/books/{book}/log")[1]["running"]:
                return
            time.sleep(0.2)
        self.fail("the run did not finish")

    def test_run_from_web_until_output(self):
        self.json("POST", "/api/books", {"name": "sample"})
        self.call("PUT", "/api/books/sample/source?file=tr.md", raw=SOURCE.encode())
        self.call("PUT", "/api/books/sample/references/da?file=da.md", raw=REFERENCE.encode())

        status, data = self.json("POST", "/api/books/sample/run", {"lang": "no", "references": ["da"], "segments": "1-2"}, lang="tr")
        self.assertEqual(status, 200, data)
        self.wait_idle("sample")
        # The first run processed only segments 1-2.
        status, books = self.json("GET", "/api/books")
        self.assertEqual(books[0]["status"]["languages"]["no"]["stages"]["reconcile"], [2, 3])
        # The run used the language of the request that started it.
        log = self.json("GET", "/api/books/sample/log")[1]["log"]
        self.assertIn("1-2", log)
        self.assertIn("2/3 bölüm", log)
        self.assertIn("[tamamlandı]", log)

        self.assertEqual(self.json("POST", "/api/books/sample/run", {"lang": "no", "references": ["da"]})[0], 200)
        self.wait_idle("sample")
        status, books = self.json("GET", "/api/books")
        self.assertEqual(books[0]["outputs"], ["no"])
        self.assertEqual(books[0]["run"]["state"], "finished")
        self.assertEqual(self.json("POST", "/api/books/sample/estimate", {"lang": "no", "references": ["da"]})[1]["total_calls"], 0)
        self.assertEqual(books[0]["status"]["languages"]["no"]["stages"]["reconcile"], [3, 3])
        self.assertIn("[completed]", self.json("GET", "/api/books/sample/log")[1]["log"])

        status, text = self.call("GET", f"/api/books/sample/output/no/translation?token={self.app.token}", token=False)
        self.assertEqual(status, 200)
        self.assertIn("Birinci Kısım", text.decode())
        status, text = self.call("GET", "/api/books/sample/output/no/report")
        self.assertIn("Translation report", text.decode())

        # The source of a prepared book cannot change without a reset.
        self.assertEqual(self.call("PUT", "/api/books/sample/source?file=tr.md", raw=b"new")[0], 409)
        self.assertEqual(self.json("POST", "/api/books/sample/reset")[0], 200)
        self.assertEqual(self.call("PUT", "/api/books/sample/source?file=tr.md", raw=b"new")[0], 200)

    def test_running_book_blocks_changes_and_can_be_stopped(self):
        self.json("POST", "/api/books", {"name": "sample"})
        self.call("PUT", "/api/books/sample/source?file=tr.md", raw=SOURCE.encode())
        os.environ["FAKE_LLM_DELAY"] = "30"  # the fake tool waits on each call
        self.addCleanup(os.environ.pop, "FAKE_LLM_DELAY")
        self.assertEqual(self.json("POST", "/api/books/sample/run", {"lang": "no"})[0], 200)
        self.assertTrue(self.json("GET", "/api/books/sample/log")[1]["running"])
        self.assertEqual(self.json("POST", "/api/books/sample/run", {"lang": "no"})[0], 409)
        self.assertEqual(self.json("POST", "/api/books/sample/reset")[0], 409)

        status, books = self.json("GET", "/api/books")
        self.assertEqual(books[0]["run"]["state"], "running")
        self.assertGreater(books[0]["run"]["remaining"]["total_calls"], 0)

        self.assertEqual(self.json("POST", "/api/books/sample/stop")[0], 200)
        self.wait_idle("sample", timeout=10)
        self.assertEqual(self.json("GET", "/api/books")[1][0]["run"]["state"], "stopped")


if __name__ == "__main__":
    unittest.main()
