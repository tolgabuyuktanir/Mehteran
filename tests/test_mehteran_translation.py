"""The translation app inside Mehteran (mehteran/translation.py): its API under /api/tr/ of Mehteran's own server
(the translation app's own request handling, behind Mehteran's Host and session-key checks), its interface files
served from pipeline/ui, no frame, and a server that notices changes of the translation app's code."""

import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402
from test_pipeline import SOURCE, make_project  # noqa: E402

from mehteran import paths, translation, web  # noqa: E402
from mehteran.translation import Translation  # noqa: E402


class MehteranServerCase(HomeCase):
    """Mehteran's server on a free port, with the translation app of a temporary project (unless with_translation is
    False)."""

    with_translation = True

    def setUp(self):
        super().setUp()
        self.app = web.App(self.engine())
        if self.with_translation:
            self.root = Path(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, self.root, True)
            make_project(self.root)
            self.app.translation = Translation()
            self.assertTrue(self.app.translation.start(self.root, token=self.app.token), self.app.translation.detail)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = web.make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=None, raw=None, token=True, host=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if token:
            req.add_header("X-Token", self.app.token if token is True else token)
        if host:
            req.add_header("Host", host)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read(), res.headers
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read(), e.headers

    def json(self, *args, **kwargs):
        status, body, _ = self.call(*args, **kwargs)
        return status, json.loads(body)


class TranslationApiTests(MehteranServerCase):
    def test_books_are_the_translation_apps(self):
        self.assertEqual(self.json("GET", "/api/tr/books"), (200, []))
        self.assertTrue((self.root / "books").is_dir())
        status, data = self.json("POST", "/api/tr/books", {"name": "Büyük İlmihal"})
        self.assertEqual((status, data["name"]), (200, "buyuk-ilmihal"))
        self.assertTrue((self.root / "books" / "buyuk-ilmihal" / "source").is_dir())
        # The translation app's own errors keep their code (pipeline.web.HTTPError is not a PipelineError).
        status, data = self.json("POST", "/api/tr/books", {"name": "Büyük İlmihal"})
        self.assertEqual(status, 409)
        self.assertIn("buyuk-ilmihal", data["error"])
        self.assertEqual(self.json("GET", "/api/tr/books/nothing/log")[0], 404)
        self.assertEqual(self.json("GET", "/api/tr/nothing")[0], 404)
        self.assertEqual(self.json("GET", "/api/tr/settings")[1]["languages"]["da"], "Danish")

    def test_upload_goes_into_the_book(self):
        self.json("POST", "/api/tr/books", {"name": "kitap"})
        base = "/api/tr/books/kitap"
        status, data = self.json("PUT", f"{base}/source?file=../tr.md", raw=SOURCE.encode())
        self.assertEqual(status, 200, data)
        self.assertEqual((self.root / "books" / "kitap" / "source" / "tr.md").read_text(encoding="utf-8"), SOURCE)
        self.assertEqual(self.json("PUT", f"{base}/source?file=book.exe", raw=b"x")[0], 400)
        self.assertEqual(self.json("PUT", f"{base}/references/xx?file=a.md", raw=b"x")[0], 400)  # unknown language
        self.assertEqual(self.json("GET", "/api/tr/books")[1][0]["source"], ["tr.md"])
        # Larger than Mehteran's own JSON limit: the translation app reads the body itself, in parts.
        big = ("Bir paragraf.\n\n" * 200_000).encode()
        self.assertGreater(len(big), web.JSON_LIMIT)
        self.assertEqual(self.json("PUT", f"{base}/source?file=big.md", raw=big)[0], 200)
        self.assertEqual((self.root / "books" / "kitap" / "source" / "tr.md").stat().st_size, len(big))  # replaces it

    def test_output_and_export_downloads(self):
        self.json("POST", "/api/tr/books", {"name": "kitap"})
        out = self.root / "books" / "kitap" / "output"
        out.mkdir()
        (out / "da.md").write_text("# Bog\n\nTekst.\n", encoding="utf-8")
        # Links in the page carry the key in the address (no header).
        key = f"token={self.app.token}"
        status, body, headers = self.call("GET", f"/api/tr/books/kitap/output/da/translation?{key}&download=1", token=False)
        self.assertEqual((status, body), (200, b"# Bog\n\nTekst.\n"))
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])  # Mehteran's answers, also here
        status, body, headers = self.call("GET", f"/api/tr/books/kitap/export/da/translation/md?{key}", token=False)
        self.assertEqual(status, 200)
        self.assertIn('filename="kitap-da.md"', headers["Content-Disposition"])
        self.assertEqual(self.call("GET", f"/api/tr/books/kitap/output/no/translation?{key}", token=False)[0], 404)

    def test_host_and_token_checks_come_first(self):
        self.assertEqual(self.call("GET", "/api/tr/books", token=False)[0], 403)
        self.assertEqual(self.call("GET", "/api/tr/books", token="wrong")[0], 403)
        self.assertEqual(self.call("GET", "/api/tr/books", host="evil.example")[0], 403)
        self.assertEqual(self.call("GET", "/api/tr/books", host=f"localhost:{self.port}")[0], 200)
        # The translation app's own key is Mehteran's: no second key works.
        self.assertEqual(self.app.translation.app.token, self.app.token)

    def test_interface_files_and_page(self):
        status, js, headers = self.call("GET", "/tr/app.js", token=False)
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/javascript"))
        self.assertEqual(js, (paths.REPO / "pipeline" / "ui" / "app.js").read_bytes())  # the same file, no copy
        self.assertIn(b"window.TranslationUI", js)
        status, css, headers = self.call("GET", "/tr/style.css", token=False)
        self.assertEqual((status, headers["Content-Type"].split(";")[0]), (200, "text/css"))
        self.assertEqual(self.call("GET", "/tr/index.html", token=False)[0], 404)  # only these two files
        status, page, headers = self.call("GET", "/", token=False)
        self.assertIn(b'<script src="/tr/app.js" defer></script>', page)
        self.assertLess(page.index(b'href="/tr/style.css"'), page.index(b'href="/style.css"'))
        csp = headers["Content-Security-Policy"]
        self.assertNotIn("frame-src", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("style-src 'self'", csp)
        self.assertFalse((paths.CODE / "ui" / "translation-embed.js").exists())

    def test_info_and_setup_count_the_translation_workflow(self):
        info = self.json("GET", "/api/info")[1]
        self.assertEqual(info["translation"], {"running": True, "error": "", "detail": "", "favorite": False})
        self.assertNotIn("translation_url", info)
        used = self.app._translation_used()
        self.assertTrue(used)
        self.assertTrue(used <= set(self.app.translation.app.proj.cfg["providers"]))


class WithoutTranslationTests(MehteranServerCase):
    with_translation = False

    def test_existing_book_and_favorite_require_explicit_embedding(self):
        root = self.tmp / "local-project"
        source = root / "books" / "my-book" / "source" / "chapter.txt"
        source.parent.mkdir(parents=True)
        source.write_text("chapter", encoding="utf-8")
        self.app._update_conf("library.json", "favorites", ["app:translation"])
        with mock.patch.object(web, "ROOT", root):
            self.assertFalse(self.app.book_translation_enabled())
            with mock.patch.object(web, "engine_options", return_value={"embed_book_translation": True}):
                self.assertTrue(self.app.book_translation_enabled())
        self.assertEqual(source.read_text(encoding="utf-8"), "chapter")
        self.assertIn("app:translation", self.app._favorites())

    def test_standalone_books_are_not_listed_in_main_history(self):
        with mock.patch("mehteran.usage.translation_runs") as books, \
                mock.patch("mehteran.usage.translation_activity") as activity:
            self.assertEqual(self.json("GET", "/api/translation/runs"), (200, []))
            self.assertEqual(self.json("GET", "/api/activity")[1]["translation"], [])
        books.assert_not_called()
        activity.assert_not_called()

    def test_api_says_why(self):
        status, data = self.json("GET", "/api/tr/books")
        self.assertEqual(status, 503)
        self.assertEqual(data["error"], "The book translation was not loaded with this server.")
        self.assertEqual(self.json("GET", "/api/info")[1]["translation"]["error"], "translation_not_started")
        self.assertEqual(self.app._translation_used(), set())

    def test_a_project_that_cannot_load_is_a_message(self):
        tr = Translation()
        (self.tmp / "project").mkdir()
        with mock.patch("pipeline.core.Project.load", side_effect=OSError("disk")):
            self.assertFalse(tr.start(self.tmp / "project"))
        self.assertEqual(tr.info(), {"running": False, "error": "translation_failed", "detail": "disk"})
        self.app.translation = tr
        status, data = self.json("GET", "/api/tr/books")
        self.assertEqual((status, data["error"]), (503, "The book translation cannot open: disk"))


class StampTests(unittest.TestCase):
    def test_stamp_covers_the_translation_apps_code(self):
        lines = []
        digest = mock.Mock(update=lambda b: lines.append(b.decode()), hexdigest=lambda: "0" * 64)
        with mock.patch.object(web.hashlib, "sha256", return_value=digest):
            web.code_stamp()
        names = {line.split(":")[0] for line in lines}
        for name in ("mehteran/web.py", "mehteran/ui/app.js", "pipeline/web.py", "pipeline/stages.py",
                     "pipeline/ui/app.js", "pipeline/ui/style.css", "pipeline/ui/index.html"):
            self.assertIn(name, names)
        self.assertEqual(translation.STATIC, paths.REPO / "pipeline" / "ui")


if __name__ == "__main__":
    unittest.main()
