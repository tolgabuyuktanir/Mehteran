"""Run with Playwright and local Chrome: python tests/mehteran_runs_browser.py."""

import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mehteran.engine import Engine
from mehteran.web import App, make_handler
from tests.mehteran_support import ai, fake_cfg, ready_tools, workflow

with TemporaryDirectory() as tmp:
    engine = Engine(Path(tmp), fake_cfg())
    engine.awake = False
    engine.tool_states = ready_tools
    archived = workflow(ai("a", "TASK:old {{inputs.topic}}"), [], inputs="  - {id: topic, type: text}\n")
    original = engine.start(archived, {"topic": "Saved topic"}, template="user:removed")
    assert engine.wait(original, 20) == "succeeded"
    app = App(engine)
    with ThreadingHTTPServer(("127.0.0.1", 0), None) as server:
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(app, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="chrome", headless=True)
                for width in (320, 375, 414, 768, 1280):
                    page = browser.new_page(locale="en-US", viewport={"width": width, "height": 820})
                    errors = []
                    page.on("pageerror", lambda err: errors.append(str(err)))
                    page.goto(f"http://127.0.0.1:{port}/#runs")
                    page.wait_for_load_state("networkidle")
                    search = page.locator(".run-search")
                    search.fill("unmatched-search")
                    page.get_by_text("No run matches the search.", exact=True).wait_for()
                    assert not page.locator("#run .welcome").is_visible()
                    search.fill("")
                    page.locator(".rl-item button").first.click()
                    page.locator(".run-head").wait_for()
                    assert not search.is_visible()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.locator(".run-back").click()
                    search.wait_for()

                    def waiting(route):
                        detail = route.fetch().json()
                        detail.update(status="running", active=True)
                        detail["nodes"]["a"].update(status="waiting_quota", quota_until=time.time() + 120)
                        route.fulfill(json=detail)

                    page.route("**/api/usage", lambda route: route.fulfill(json={"providers": []}))
                    page.route(f"**/api/runs/{original}", waiting)
                    page.locator(".rl-item button").first.click()
                    notice = page.locator(".quota-notice")
                    notice.wait_for()
                    assert "trying again at" in notice.inner_text()
                    assert not notice.locator("[data-until]").count()
                    notice.get_by_role("button").click()
                    page.locator("#node-panel .switch-pick select").wait_for()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    assert page.evaluate("""() => {
                      const now = Date.now() / 1000;
                      const usage = {resets_at: now - 5, tool_reported: {windows: [
                        {name: "primary", used_percent: 99, resets_at: now - 10},
                        {name: "secondary", used_percent: 50, resets_at: now + 120},
                        {name: "invalid", used_percent: "unknown"}
                      ]}};
                      usageState.data = {providers: [{provider: "test", ...usage}]};
                      const box = usageBox("test");
                      return reportedWindows(usage).length === 2 && usageLevel(usage) === ""
                        && box.textContent.includes("50% used") && !box.textContent.includes("99%")
                        && box.querySelectorAll(".usage-bar .fill").length === 1;
                    }""")
                    assert not errors, errors
                    page.close()
                    print(f"{width}px: history, search, return navigation and quota notice passed", flush=True)
                browser.close()
        finally:
            server.shutdown()
            app.automation.stop()
