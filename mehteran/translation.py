"""The translation app inside Mehteran: its interface in Mehteran's page, its API under /api/tr/ of Mehteran's server.

The translation app's code (pipeline/*.py) stays unchanged. Mehteran makes the translation app's App once, the way
"./translate ui" does (Project.load), without a server of its own. A request to /api/tr/<path> is answered by the
translation app's own request handling (pipeline.web.make_handler) as the request /api/<path>: the same routes,
checks, streamed uploads, downloads and error codes. Mehteran's Host and session-key checks come first, and the
translation app's App takes Mehteran's session key, so one key opens both.

The interface is the translation app's own file pipeline/ui/app.js (and style.css), served by Mehteran as
/tr/app.js and /tr/style.css and mounted in the Workflows tab ("Book translation"; TranslationUI.mount).
"./translate ui" keeps working on its own; both can run at once, and a book run is locked per book across processes
(pipeline/cli.py).
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from . import paths

PREFIX = "/api/tr"
STATIC = paths.REPO / "pipeline" / "ui"
FILES = {"/tr/app.js": ("app.js", "text/javascript"), "/tr/style.css": ("style.css", "text/css")}


class Translation:
    """The translation app's App inside Mehteran's server, and its state for the interface."""

    def __init__(self):
        self.app = None
        self.error = ""  # a message key of mehteran.i18n when the translation app could not load
        self.detail = ""
        self.handlers: dict[int, type] = {}

    def start(self, root: Path | None = None, token: str | None = None) -> bool:
        """Loads the translation project. False (and self.error) when it cannot."""
        from pipeline import tools, web as pipeline_web
        from pipeline.core import ROOT, PipelineError, Project
        root = root or ROOT
        try:
            tools.extend_path(root)  # as pipeline.web.serve
            (root / "books").mkdir(exist_ok=True)
            self.app = pipeline_web.App(Project.load(root))
        except (PipelineError, OSError) as e:
            self.error = "translation_failed"
            self.detail = str(e)
            return False
        if token:
            self.app.token = token
        return True

    def info(self) -> dict:
        return {"running": self.app is not None, "error": self.error, "detail": self.detail}

    def handle(self, handler, method: str, port: int) -> None:
        """Answers a request of Mehteran's server (handler) whose raw path starts with /api/tr/. The translation app's
        handler code runs on Mehteran's request object: it reads the body from it and answers through its send()."""
        from pipeline import web as pipeline_web
        cls = self.handlers.get(port)
        if cls is None:  # its Host check then accepts Mehteran's address
            cls = self.handlers[port] = pipeline_web.make_handler(self.app, port)
        url = urlparse(handler.path)
        handler.path = "/api" + url.path[len(PREFIX):] + (f"?{url.query}" if url.query else "")
        cls.handle_any(handler, method)
