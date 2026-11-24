"""Favorites of the workflow library: kept by the server in <data>/configurations/library.json, shown in the template
list, refused for an id that is not in the library. And the page's script for usage, live logs and activity."""

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402

from mehteran.web import App, make_handler  # noqa: E402


class FavoriteTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=None, token=True):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if token:
            req.add_header("X-Token", self.app.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read(), res.headers
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read(), e.headers

    def json(self, *args, **kwargs):
        status, body, _ = self.call(*args, **kwargs)
        return status, json.loads(body)

    def favorites(self):
        return {f"{t['source']}:{t['id']}" for t in self.json("GET", "/api/templates")[1] if t["favorite"]}

    def test_a_favorite_of_a_merged_template_moves_to_the_new_one(self):
        self.json("PUT", "/api/templates/builtin/multi-length-summary/favorite", body={"on": True})
        self.assertEqual(self.favorites(), {"builtin:document-summary"})
        self.app._write_conf("library.json", {"favorites": ["builtin:chapter-summaries", "builtin:document-summary"]})
        self.assertEqual(self.app._favorites(), ["builtin:document-summary"])

    def test_star_and_unstar(self):
        builtin = self.json("GET", "/api/templates")[1][0]
        ref = f"builtin:{builtin['id']}"
        self.assertEqual(self.favorites(), set())
        self.assertEqual(self.json("PUT", f"/api/templates/builtin/{builtin['id']}/favorite", body={"on": True}), (200, {"favorite": True}))
        self.assertEqual(self.favorites(), {ref})
        stored = json.loads((self.home / "configurations" / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["favorites"], [ref])
        # Twice on keeps one entry; a new server (a restart) reads the same file.
        self.json("PUT", f"/api/templates/builtin/{builtin['id']}/favorite", body={"on": True})
        app = App(self.engine())
        self.assertEqual(app._favorites(), [ref])
        self.assertEqual(self.json("PUT", f"/api/templates/builtin/{builtin['id']}/favorite", body={"on": False}), (200, {"favorite": False}))
        self.assertEqual(self.favorites(), set())

    def test_unknown_ids_are_refused_and_dropped(self):
        self.assertEqual(self.json("PUT", "/api/templates/builtin/no-such-flow/favorite", body={"on": True})[0], 404)
        self.assertEqual(self.json("PUT", "/api/templates/user/no-such-flow/favorite", body={"on": True})[0], 404)
        self.assertFalse((self.home / "configurations" / "library.json").exists())
        # A favorite whose template was deleted later is not listed, and is dropped at the next change.
        builtin = self.json("GET", "/api/templates")[1][0]["id"]
        (self.home / "configurations").mkdir(parents=True, exist_ok=True)
        (self.home / "configurations" / "library.json").write_text(json.dumps({"favorites": ["user:gone", 5]}), encoding="utf-8")
        self.assertEqual(self.favorites(), set())
        self.json("PUT", f"/api/templates/builtin/{builtin}/favorite", body={"on": True})
        stored = json.loads((self.home / "configurations" / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["favorites"], [f"builtin:{builtin}"])

    def test_the_book_translation_is_not_part_of_mehteran(self):
        """The book translation app was removed: its favorite, its runs and its interface are gone, and an old
        favorite of it is dropped."""
        self.assertNotIn("translation", self.json("GET", "/api/info")[1])
        self.assertEqual(self.json("PUT", "/api/templates/app/translation/favorite", body={"on": True})[0], 404)
        self.assertEqual(self.json("GET", "/api/translation/runs")[0], 404)
        self.assertEqual(self.call("GET", "/tr/app.js", token=False)[0], 404)
        (self.home / "configurations").mkdir(parents=True, exist_ok=True)
        (self.home / "configurations" / "library.json").write_text(json.dumps({"favorites": ["app:translation"]}), encoding="utf-8")
        self.assertEqual(self.favorites(), set())

    def test_live_script_is_served_before_the_page_script(self):
        status, body, headers = self.call("GET", "/live.js", token=False)
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/javascript"))
        self.assertIn(b"/api/activity", body)
        page = self.call("GET", "/", token=False)[1]
        self.assertLess(page.index(b'src="/live.js"'), page.index(b'src="/app.js"'))
        self.assertIn(b'id="activity"', page)
