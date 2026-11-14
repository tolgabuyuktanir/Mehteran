"""The URL input (mehteran/urlfetch.py, document.extract): a local test server for the allowed path (loopback is
allowed for it by a patch of address_allowed), and the refusals of the real guard: loopback, private, link-local and
IPv6 loopback addresses, a redirect to a private address, too many redirects, a page that is too large, a type that is
not read, and addresses with another scheme or with credentials. No request leaves this computer.
"""

import ipaddress
import json
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import schema, urlfetch  # noqa: E402
from mehteran.engine import RunError  # noqa: E402

PAGE = (b"<!doctype html><html><head><title>Test page</title><style>.x{color:red}</style>"
        b"<script>alert('no')</script></head><body><nav>Menu Home About</nav><h1>Heading</h1>"
        b"<p>First <b>paragraph</b>.</p><ul><li>one</li><li>two</li></ul><noscript>enable js</noscript></body></html>")


class Pages(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        port = self.server.server_address[1]
        routes = {
            "/page": (200, "text/html; charset=utf-8", PAGE),
            "/plain": (200, "text/plain; charset=utf-8", "Düz metin.".encode()),
            "/image": (200, "image/png", b"\x89PNG...."),
            "/big": (200, "text/plain", b"x" * (urlfetch.MAX_BYTES + 10)),
            "/empty": (200, "text/html", b"<html><body><script>render()</script></body></html>"),
        }
        if self.path == "/to-page":
            return self.redirect(f"http://127.0.0.1:{port}/page")
        if self.path == "/to-private":
            return self.redirect("http://10.1.2.3/secret")
        if self.path == "/to-metadata":
            return self.redirect("http://169.254.169.254/latest/meta-data/")
        if self.path.startswith("/loop"):
            return self.redirect(f"http://127.0.0.1:{port}/loop{len(self.path)}")
        code, kind, body = routes.get(self.path, (404, "text/plain", b"missing"))
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:  # the reader stopped (the page that is too large)
            pass

    def redirect(self, where):
        self.send_response(302)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()


LOOPBACK = ipaddress.ip_address("127.0.0.1")
real_allowed = urlfetch.address_allowed


def loopback_too(ip):
    return ip == LOOPBACK or real_allowed(ip)


class GuardTests(unittest.TestCase):
    def test_address_rules(self):
        for text in ("127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.1", "169.254.169.254", "::1", "fe80::1",
                     "224.0.0.1", "0.0.0.0", "100.64.0.1", "::ffff:127.0.0.1", "fc00::1"):
            self.assertFalse(urlfetch.address_allowed(ipaddress.ip_address(text)), text)
        for text in ("93.184.216.34", "2606:4700::1111"):
            self.assertTrue(urlfetch.address_allowed(ipaddress.ip_address(text)), text)

    def test_refused_before_any_connection(self):
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("connected")):
            for url in ("http://127.0.0.1/", "http://10.0.0.1/", "http://169.254.169.254/", "http://[::1]/",
                        "http://localhost/", "https://192.168.0.1:8443/x"):
                with self.assertRaises(urlfetch.FetchError, msg=url):
                    urlfetch.fetch(url)

    def test_address_form(self):
        self.assertIsNone(urlfetch.url_problem("https://example.org/a?b=1"))
        for url in ("ftp://example.org/", "file:///etc/passwd", "http://user:pw@example.org/", "javascript:alert(1)",
                    "http://exa mple.org/", "example.org", "http://example.org:99999/"):
            self.assertIsNotNone(urlfetch.url_problem(url), url)

    def test_html_text(self):
        text = urlfetch.html_text(PAGE.decode())
        self.assertEqual(text, "# Test page\n\n# Heading\n\nFirst paragraph.\n\n- one\n- two")


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Pages)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        patch = mock.patch.object(urlfetch, "address_allowed", loopback_too)
        patch.start()
        self.addCleanup(patch.stop)

    def test_reads_html_plain_and_follows_a_redirect(self):
        self.assertIn("First paragraph.", urlfetch.read_url(self.base + "/page"))
        self.assertNotIn("alert", urlfetch.read_url(self.base + "/page"))
        self.assertNotIn("Menu", urlfetch.read_url(self.base + "/page"))
        self.assertEqual(urlfetch.read_url(self.base + "/plain"), "Düz metin.")
        self.assertIn("Heading", urlfetch.read_url(self.base + "/to-page"))

    def test_refusals(self):
        for path in ("/to-private", "/to-metadata", "/loop", "/big", "/image", "/missing"):
            with self.assertRaises(urlfetch.FetchError, msg=path):
                urlfetch.read_url(self.base + path)
        with self.assertRaises(urlfetch.FetchError):  # another loopback address is not part of the patch
            urlfetch.read_url(self.base.replace("127.0.0.1", "127.0.0.2") + "/page")

    def test_no_proxy_from_the_environment(self):
        with mock.patch.dict("os.environ", {"http_proxy": "http://10.9.9.9:3128", "HTTP_PROXY": "http://10.9.9.9:3128"}):
            self.assertIn("Heading", urlfetch.read_url(self.base + "/page"))


class WorkflowTests(HomeCase):
    FLOW = workflow("  - {id: read, type: document.extract}\n" + ai("sum", "TASK:sum Summarize."), [("read", "sum")],
                    inputs="  - {id: page, type: url}\n")

    def test_schema_accepts_a_url_input(self):
        wf = schema.parse(self.FLOW)
        self.assertEqual(wf.inputs["page"]["type"], "url")
        with self.assertRaises(schema.WorkflowError):
            schema.parse(self.FLOW.replace("type: url}", "type: url, default: 'ftp://x'}"))

    def test_run_reads_the_page(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Pages)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        engine = self.engine()
        with mock.patch.object(urlfetch, "address_allowed", loopback_too):
            run_id = engine.start(self.FLOW, {"page": f"http://127.0.0.1:{server.server_address[1]}/page"})
            self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertIn("First paragraph.", (engine.run_dir(run_id) / "nodes" / "read" / "text.md").read_text(encoding="utf-8"))
        self.assertIn("First paragraph.", self.prompt_of("sum"))

    def test_run_refuses_a_private_address(self):
        engine = self.engine()
        run_id = engine.start(self.FLOW, {"page": "http://192.168.1.1/admin"})
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("192.168.1.1", engine.get(run_id)["nodes"]["read"]["error"])
        with self.assertRaises(RunError):
            engine.start(self.FLOW, {"page": "file:///etc/passwd"})


if __name__ == "__main__":
    unittest.main()
