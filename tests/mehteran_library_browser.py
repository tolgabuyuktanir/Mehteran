"""Run with Playwright and local Chrome: python tests/mehteran_library_browser.py."""

import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mehteran.engine import Engine
from mehteran.web import App, make_handler
from tests.mehteran_support import fake_cfg, ready_tools

with TemporaryDirectory() as folder:
    engine = Engine(Path(folder), fake_cfg())
    engine.tool_states = ready_tools
    app = App(engine)
    with ThreadingHTTPServer(("127.0.0.1", 0), None) as server:
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(app, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="chrome", headless=True)
                for width in (375, 1280):
                    page = browser.new_page(viewport={"width": width, "height": 800}, locale="tr-TR")
                    run = {"id": "old-run", "template": "builtin:document-summary", "created": 1700000000}
                    page.route("**/api/runs", lambda route: route.fulfill(json=[run]))
                    page.goto(f"http://127.0.0.1:{port}/#workflows")
                    page.wait_for_load_state("networkidle")
                    recent = page.locator(".recent-chip")
                    assert recent.count() == 1
                    search = page.locator("#template-search")
                    search.fill("document-summary")
                    assert recent.count() == 1, "Searching hides matching recent workflows"
                    assert "1" in page.locator("#library-count").inner_text()
                    search.fill("no match here")
                    assert recent.count() == 0
                    page.locator(".view-tab").last.click()
                    toggle = page.locator('[aria-controls="category-list"]')
                    if toggle.get_attribute("aria-expanded") == "true":
                        toggle.click()
                    search.fill("document")
                    assert toggle.get_attribute("aria-expanded") == "false", "Search reopened collapsed categories"
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    print(f"{width}px OK")
                    page.close()
                browser.close()
        finally:
            server.shutdown()
            app.automation.stop()
