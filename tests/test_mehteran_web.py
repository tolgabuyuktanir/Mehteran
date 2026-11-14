"""Mehteran web server: Host and token checks, limits, path traversal, uploads, and a run from start to download."""

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402

from mehteran import web  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402


class WebTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
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
            req.add_header("X-Token", self.app.token if token is True else token)
        if host:
            req.add_header("Host", host)
        req.add_header("X-Lang", lang)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read(), res.headers
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read(), e.headers

    def json(self, *args, **kwargs):
        status, body, _ = self.call(*args, **kwargs)
        return status, json.loads(body)

    def test_page_carries_token_and_safe_headers(self):
        status, body, headers = self.call("GET", "/", token=False)
        self.assertEqual(status, 200)
        self.assertIn(self.app.token.encode(), body)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.call("GET", "/app.js", token=False)[0], 200)
        self.assertEqual(self.call("GET", "/../web.py", token=False)[0], 404)

    def test_token_and_host_are_required(self):
        self.assertEqual(self.json("GET", "/api/templates", token=False)[0], 403)
        self.assertEqual(self.json("GET", "/api/templates", token="wrong")[0], 403)
        status, data = self.json("GET", "/api/templates", host="evil.example:80")
        self.assertEqual(status, 403)
        self.assertEqual(data["error"], "Address not allowed.")
        self.assertEqual(self.call("GET", "/", token=False, host="attacker.test")[0], 403)
        self.assertEqual(self.json("GET", "/api/templates", host=f"localhost:{self.port}")[0], 200)
        # The query token (used by download links) is checked the same way.
        self.assertEqual(self.call("GET", "/api/templates?token=nope", token=False)[0], 403)
        self.assertEqual(self.call("GET", f"/api/templates?token={self.app.token}", token=False)[0], 200)
        _, data = self.json("GET", "/api/templates", token=False, lang="tr")
        self.assertIn("Oturum anahtarı", data["error"])

    def test_json_limit(self):
        with mock.patch.object(web, "JSON_LIMIT", 100):
            status, data = self.json("POST", "/api/validate", body={"yaml": "x" * 500})
        self.assertEqual(status, 413)
        self.assertEqual(self.json("POST", "/api/validate", raw=b"[1, 2]")[0], 400)
        self.assertEqual(self.json("POST", "/api/validate", raw=b"{not json")[0], 400)

    def test_uploads_are_checked_and_names_sanitised(self):
        status, data = self.json("PUT", "/api/uploads?file=../../../etc/evil.md", raw=b"# hello")
        self.assertEqual(status, 200)
        stored = list((self.home / "executions" / ".uploads" / data["upload"]).iterdir())
        self.assertEqual([p.name for p in stored], ["evil.md"])
        self.assertEqual(self.json("PUT", "/api/uploads?file=run.exe", raw=b"MZ")[0], 400)
        self.assertEqual(self.json("PUT", "/api/uploads?file=a.md", raw=b"")[0], 413)
        with mock.patch.object(web, "UPLOAD_LIMIT", 10):
            self.assertEqual(self.json("PUT", "/api/uploads?file=a.md", raw=b"x" * 50)[0], 413)
        status, data = self.json("POST", "/api/runs", body={"template": "builtin:document-comparison",
                                                            "files": {"first": "../../databases"}})
        self.assertEqual(status, 400)

    def run_comparison(self) -> str:
        uploads = {}
        for key, name, text in (("first", "old.md", "Notice: 30 days."), ("second", "new.md", "Notice: 7 days.")):
            status, data = self.json("PUT", f"/api/uploads?file={name}", raw=text.encode())
            self.assertEqual(status, 200)
            uploads[key] = data["upload"]
        status, data = self.json("POST", "/api/runs", body={
            "template": "builtin:document-comparison", "files": uploads,
            "values": {"language": "en", "analyst_model": "fake/small@high", "writer_model": "claude"}})
        self.assertEqual(status, 200, data)
        return data["id"]

    def test_run_from_upload_to_download(self):
        status, items = self.json("GET", "/api/templates")
        self.assertLessEqual({"builtin:academic-paper-review", "builtin:document-comparison"}, {i["ref"] for i in items})
        run_id = self.run_comparison()
        end = time.time() + 60
        while time.time() < end:
            status, run = self.json("GET", f"/api/runs/{run_id}")
            if run["status"] in ("succeeded", "failed"):
                break
            time.sleep(0.2)
        self.assertEqual(run["status"], "succeeded", run.get("error"))
        self.assertEqual(run["providers"]["compare"], "fake/small@high")
        self.assertNotIn("provider_cfg", run)
        docx = next(o for o in run["outputs"] if o["id"] == "report_docx")["path"]
        status, body, headers = self.call("GET", f"/api/runs/{run_id}/files/{docx}?download=1&token={self.app.token}", token=False)
        self.assertEqual(status, 200)
        self.assertEqual(body[:2], b"PK")
        self.assertIn("attachment", headers["Content-Disposition"])
        # Model-written HTML is never rendered by this server, only downloaded.
        html = next(o for o in run["outputs"] if o["id"] == "report_html")["path"]
        status, _, headers = self.call("GET", f"/api/runs/{run_id}/files/{html}")
        self.assertIn("attachment", headers["Content-Disposition"])
        status, body, headers = self.call("GET", f"/api/runs/{run_id}/files/nodes/compare/text.md")
        self.assertTrue(headers["Content-Type"].startswith("text/plain"))
        self.assertIn(b"## Answer", body)
        status, runs = self.json("GET", "/api/runs")
        self.assertEqual(runs[0]["id"], run_id)
        # The uploads became the run's inputs; nothing is left in the upload folder.
        self.assertEqual(list((self.home / "executions" / ".uploads").iterdir()), [])
        self.assertEqual(self.json("POST", f"/api/runs/{run_id}/resume")[0], 400)  # nothing to resume

    def test_no_path_traversal(self):
        run_id = self.run_comparison()
        self.app.engine.wait(run_id, 60)
        for path in ("../../databases/mehteran.sqlite3", "..%2F..%2Fdatabases%2Fmehteran.sqlite3", "%2e%2e/%2e%2e/x",
                     "/etc/passwd", ".lock", "nodes/compare/attempt-1.job.json", "inputs/../../../../../etc/hosts"):
            status, _, _ = self.call("GET", f"/api/runs/{run_id}/files/{path}")
            self.assertEqual(status, 404, path)
        self.assertEqual(self.json("GET", "/api/runs/..%2F..%2Fx")[0], 404)
        self.assertEqual(self.json("GET", "/api/templates/user/..%2F..%2Fx")[0], 404)
        self.assertEqual(self.json("GET", "/api/templates/system/x")[0], 404)

    def test_template_management(self):
        status, data = self.json("POST", "/api/templates/builtin/document-comparison/customize", body={"id": "my-compare"})
        self.assertEqual((status, data["ref"]), (200, "user:my-compare"))
        status, tpl = self.json("GET", "/api/templates/user/my-compare")
        self.assertTrue(tpl["valid"])
        self.assertEqual(len(tpl["graph"]["nodes"]), 6)
        bad = tpl["yaml"] + "surprise: 1\nnodes2: []\n"
        status, data = self.json("PUT", "/api/templates/user/my-compare", body={"yaml": bad})
        self.assertEqual(status, 400)
        self.assertEqual(len(data["problems"]), 2)
        self.assertEqual(self.json("PUT", "/api/templates/user/my-compare", body={"yaml": tpl["yaml"]})[0], 200)
        self.assertEqual(self.json("DELETE", "/api/templates/builtin/document-comparison")[0], 403)
        status, body, headers = self.call("GET", "/api/templates/user/my-compare/download")
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertIn(b"id: my-compare", body)
        self.assertEqual(self.json("DELETE", "/api/templates/user/my-compare")[0], 200)
        status, data = self.json("POST", "/api/validate", body={"yaml": "schema_version: 1\n"})
        self.assertFalse(data["valid"])
        self.assertGreaterEqual(len(data["problems"]), 3)

    def test_info_lists_the_configured_providers(self):
        status, info = self.json("GET", "/api/info")
        fake = next(p for p in info["providers"] if p["name"] == "fake")
        self.assertEqual(fake["models"], ["small", "large"])
        self.assertEqual(fake["efforts"], ["low", "high"])
        self.assertNotIn("translation_url", info)  # the book translation is part of this page now
        # The page's texts: in the asked language, and in English for a key that language lacks.
        status, strings = self.json("GET", "/api/strings", lang="tr")
        self.assertEqual(strings["approve"], {"tr": "Onayla", "en": "Approve"})
        status, strings = self.json("GET", "/api/strings", lang="de")
        self.assertEqual(strings["approve"], {"de": "Genehmigen", "en": "Approve"})
        status, registry = self.json("GET", "/api/languages")
        self.assertIn({"code": "ar", "native": "العربية", "english": "Arabic", "flag": "sa", "dir": "rtl", "ui": True}, registry["languages"])
        self.assertEqual(registry["ui"][:2], ["tr", "en"])


if __name__ == "__main__":
    unittest.main()
