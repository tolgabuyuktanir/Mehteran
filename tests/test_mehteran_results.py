"""A run's results on the web: the edited copy of a result (read, save, export) and the Markdown renderer.

The edits routes keep the original output unchanged, refuse paths outside a step's Markdown outputs, limit the size,
refuse unknown formats and say which tool to install. The renderer (mehteran/ui/markdown.js) is tested with Node.js
(tests/mehteran_markdown_test.mjs) when Node.js is installed; the test is skipped otherwise.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import ROOT, HomeCase, ai, workflow  # noqa: E402

from mehteran import pandoc, typst, web  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

FLOW = workflow(ai("write", "TASK:write"), [], inputs="  - {id: language, type: language, default: ar}\n")


class EditTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.run_id = self.app.engine.start(FLOW)
        self.assertEqual(self.app.engine.wait(self.run_id, 30), "succeeded")
        self.run_dir = self.app.engine.run_dir(self.run_id)
        self.original = (self.run_dir / "nodes" / "write" / "text.md").read_text(encoding="utf-8")
        self.edits = f"/api/runs/{self.run_id}/edits/nodes/write/text.md"

    def call(self, method, path, body=None, raw=None, token=True):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if token:
            req.add_header("X-Token", self.app.token)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def json(self, *args, **kwargs):
        status, body = self.call(*args, **kwargs)
        return status, json.loads(body)

    def test_save_keeps_the_original_and_reads_back(self):
        status, data = self.json("GET", self.edits)
        self.assertEqual((status, data["exists"], data["path"]), (200, False, "edited/write.text.md"))
        self.assertEqual(data["limit"], web.EDIT_LIMIT)
        text = "# Düzenlendi\n\nنص **معدل**.\n"
        status, data = self.json("PUT", self.edits, {"text": text})
        self.assertEqual(status, 200, data)
        self.assertEqual((self.run_dir / "edited" / "write.text.md").read_text(encoding="utf-8"), text)
        self.assertEqual((self.run_dir / "nodes" / "write" / "text.md").read_text(encoding="utf-8"), self.original)
        status, data = self.json("GET", self.edits)
        self.assertEqual((data["exists"], data["text"]), (True, text))
        # The edited copy is a file of the run: listed and served like the others.
        status, run = self.json("GET", f"/api/runs/{self.run_id}")
        self.assertIn("edited/write.text.md", [a["path"] for a in run["artifacts"]])
        status, body = self.call("GET", f"/api/runs/{self.run_id}/files/edited/write.text.md")
        self.assertEqual(body.decode("utf-8"), text)
        self.assertEqual(list((self.run_dir / "edited").glob("*.tmp")), [])

    def test_only_a_steps_markdown_outputs_are_editable(self):
        base = f"/api/runs/{self.run_id}/edits/"
        for rel in ("nodes/../workflow.yaml", "nodes/%2e%2e/workflow.yaml", "nodes/write/../../workflow.yaml",
                    "workflow.yaml", "inputs/x.md", "edited/write.text.md", "nodes/write/missing.md", "nodes/write/log.txt",
                    "nodes/write//text.md", "/etc/passwd", "nodes/Write/text.md"):
            for method, body in (("GET", None), ("PUT", {"text": "x"}), ("POST", {"format": "md"})):
                status, data = self.json(method, base + rel, body)
                self.assertEqual(status, 404, (method, rel, data))
        self.assertFalse((self.run_dir / "edited").exists())
        self.assertEqual(self.json("GET", "/api/runs/20990101-000000-abcdef/edits/nodes/write/text.md")[0], 404)
        self.assertEqual(self.json("GET", "/api/runs/../../edits/nodes/write/text.md")[0], 404)

    @unittest.skipUnless(os.name == "posix", "symbolic links")
    def test_an_edited_folder_that_links_elsewhere_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (self.run_dir / "edited").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.json("PUT", self.edits, {"text": "x"})[0], 404)
        self.assertEqual(list(outside.iterdir()), [])

    def test_token_is_required(self):
        self.assertEqual(self.call("GET", self.edits, token=False)[0], 403)
        self.assertEqual(self.call("PUT", self.edits, {"text": "x"}, token=False)[0], 403)
        self.assertFalse((self.run_dir / "edited").exists())

    def test_size_and_body_checks(self):
        with mock.patch.object(web, "EDIT_LIMIT", 10):
            status, data = self.json("PUT", self.edits, {"text": "ü" * 6})  # 12 bytes in UTF-8
        self.assertEqual(status, 413)
        self.assertIn("too large", data["error"])
        with mock.patch.object(web, "JSON_LIMIT", 50):
            self.assertEqual(self.json("PUT", self.edits, {"text": "x" * 100})[0], 413)
        self.assertEqual(self.json("PUT", self.edits, {"text": 5})[0], 400)
        self.assertEqual(self.json("PUT", self.edits, {})[0], 400)
        self.assertFalse((self.run_dir / "edited").exists())

    def test_export_needs_a_saved_edit_and_a_known_format(self):
        status, data = self.json("POST", self.edits, {"format": "docx"})
        self.assertEqual(status, 404)
        self.assertEqual(data["error"], "Save the edited version first.")
        self.json("PUT", self.edits, {"text": "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"})
        for value in ("odt", "../md", None, ["md"]):
            status, data = self.json("POST", self.edits, {"format": value})
            self.assertEqual(status, 400, value)
            self.assertIn("md, docx, html, pdf, epub", data["error"])

    def test_export_formats_with_the_export_nodes_code(self):
        self.json("PUT", self.edits, {"text": "# Başlık\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"})
        status, data = self.json("POST", self.edits, {"format": "md"})
        self.assertEqual((status, data["path"]), (200, "edited/write.text.md"))
        with mock.patch.object(pandoc, "binary", return_value=(None, None)):
            status, data = self.json("POST", self.edits, {"format": "docx"})
        self.assertEqual((status, data["path"]), (200, "edited/write.text.docx"))
        self.assertEqual((self.run_dir / data["path"]).read_bytes()[:2], b"PK")
        status, data = self.json("POST", self.edits, {"format": "html"})
        page = (self.run_dir / data["path"]).read_text(encoding="utf-8")
        self.assertIn('lang="ar"', page, "the run's language input")
        self.assertIn("<table", page, "Markdown tables become tables (tables.to_html)")
        self.assertEqual(status, 200)
        self.assertEqual((self.run_dir / "nodes" / "write" / "text.md").read_text(encoding="utf-8"), self.original)

    def test_export_original_without_a_saved_edit(self):
        status, original = self.json("POST", self.edits, {"format": "html", "version": "original"})
        self.assertEqual(status, 200)
        self.assertIn("## Answer", self.original)
        self.assertIn("<h2>Answer write</h2>", (self.run_dir / original["path"]).read_text(encoding="utf-8"))
        self.assertFalse((self.run_dir / "edited" / "write.text.md").exists())
        self.json("PUT", self.edits, {"text": "## Edited"})
        status, edited = self.json("POST", self.edits, {"format": "html", "version": "edited"})
        self.assertEqual(status, 200)
        self.assertNotEqual(original["path"], edited["path"])
        self.assertIn("<h2>Edited</h2>", (self.run_dir / edited["path"]).read_text(encoding="utf-8"))

    def test_missing_tool_says_what_to_install(self):
        self.json("PUT", self.edits, {"text": "Text."})
        with mock.patch.object(typst, "binary", return_value=(None, None)):
            status, data = self.json("POST", self.edits, {"format": "pdf"})
        self.assertEqual(status, 400)
        self.assertIn("Install Typst on the Setup tab", data["error"])
        with mock.patch.object(pandoc, "binary", return_value=(None, None)):
            status, data = self.json("POST", self.edits, {"format": "epub"})
        self.assertEqual(status, 400)
        self.assertIn("Install Pandoc on the Setup tab", data["error"])
        self.assertEqual(sorted(p.name for p in (self.run_dir / "edited").iterdir()), ["write.text.md"])

    def test_renderer_is_served_before_the_app(self):
        status, body = self.call("GET", "/markdown.js", token=False)
        self.assertEqual(status, 200)
        self.assertIn(b"root.Markdown", body)
        page = self.call("GET", "/", token=False)[1].decode("utf-8")
        self.assertLess(page.index('src="/markdown.js"'), page.index('src="/app.js"'))
        for element in ('id="reader-tools"', 'id="reader-body"', 'id="reader-text"'):
            self.assertIn(element, page)


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class RendererTests(unittest.TestCase):
    def test_markdown_renderer(self):
        done = subprocess.run(["node", str(ROOT / "tests" / "mehteran_markdown_test.mjs")], capture_output=True, text=True,
                              timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        self.assertTrue(done.stdout.startswith("ok "), done.stdout)


if __name__ == "__main__":
    unittest.main()
