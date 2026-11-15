"""The browser of agent steps (ai.agent): Playwright MCP driving Google Chrome with Mehteran's own profile.

- The tool: @playwright/mcp at the version and integrity sums of mehteran/browser_mcp/package-lock.json, installed
  only when the user asks (the Setup tab, `mehter install-local browser`) with `npm ci --ignore-scripts` into
  <code folder>/.runtime/browser-mcp. It needs Node.js (npm) and Google Chrome on this computer.
- The profile: <data>/browser/profile, a Chrome profile of its own. The person signs in there once (Setup: "Open the
  browser to sign in"); agent steps then use those sign-ins. The person's own Chrome profile is never used.
- The tools: a "read" step gets the tools that look and move around (navigate, read the page, click a link); an
  "act" step also gets the tools that type, fill forms and choose options. Running code in the page, uploading files
  and dropping files are never given. Claude Code refuses every other tool (--permission-mode dontAsk).
- The sites: a step names the sites it may open. Playwright's own origin list is not a security boundary, so the
  worker also stops the step when it navigates to another site (guard()).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from . import paths
from .i18n import t
from .localtools import ToolError, dir_size, disk_free, find_program, run

VERSION = "0.0.84"
LOCK_DIR = Path(__file__).resolve().parent / "browser_mcp"
DOWNLOAD_SIZE = 18_000_000  # node_modules of the three locked packages, about (measured on macOS arm64)
TIMEOUT = 600
SERVER = "browser"  # the MCP server's name: its tools are mcp__browser__<tool>

READ_TOOLS = ("browser_navigate", "browser_navigate_back", "browser_snapshot", "browser_find", "browser_click",
              "browser_hover", "browser_tabs", "browser_wait_for", "browser_take_screenshot", "browser_close",
              "browser_handle_dialog")
ACT_TOOLS = READ_TOOLS + ("browser_type", "browser_fill_form", "browser_press_key", "browser_select_option")
NAVIGATING = {"browser_navigate", "browser_tabs"}  # tools whose input may hold an address to check
PAGE_URL = re.compile(r"Page URL: (\S+?)(?:\\n|\s|$)")  # in a tool's result (a link click may leave the sites)
# Heavy pages (hotel and listing sites) are not ready in Playwright MCP's default 5 s per action: the agent's clicks
# and searches timed out. Ads and trackers are not requested at all, so the pages load sooner.
TIMEOUT_ACTION_MS = 20_000
TIMEOUT_NAVIGATION_MS = 90_000
BLOCKED_ORIGINS = ("https://*.doubleclick.net", "https://*.googlesyndication.com", "https://*.google-analytics.com",
                   "https://*.googletagmanager.com", "https://*.googleadservices.com", "https://*.facebook.net",
                   "https://*.hotjar.com", "https://*.criteo.com", "https://*.criteo.net", "https://*.taboola.com",
                   "https://*.outbrain.com", "https://*.adnxs.com", "https://*.scorecardresearch.com")


def prefix() -> Path:
    return paths.runtime() / "browser-mcp"


def cli_path() -> Path:
    return prefix() / "node_modules" / "@playwright" / "mcp" / "cli.js"


def node() -> tuple[Path | None, str | None]:
    return find_program("node", [])


def npm() -> tuple[Path | None, str | None]:
    return find_program("npm.cmd" if sys.platform == "win32" else "npm", [])


def chrome() -> Path | None:
    """Google Chrome, where its installer puts it (Playwright's "chrome" channel uses the same one)."""
    if sys.platform == "darwin":
        candidates = [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                      Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif sys.platform == "win32":
        candidates = [Path(os.environ.get(v, "")) / "Google/Chrome/Application/chrome.exe"
                      for v in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA") if os.environ.get(v)]
    else:
        candidates = [Path(p) for p in (shutil.which("google-chrome"), shutil.which("google-chrome-stable")) if p]
    return next((p for p in candidates if p.is_file()), None)


def profile_dir(home: Path) -> Path:
    return Path(home) / "browser" / "profile"


def installed_version() -> str | None:
    try:
        return json.loads((cli_path().parent / "package.json").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def status(home: Path | None = None) -> dict:
    program, _ = node()
    version = installed_version()
    return {"id": "browser", "name": "Playwright MCP", "installed": version is not None, "source": "mehteran" if version else None,
            "version": version, "pinned_version": VERSION, "path": str(cli_path()) if version else None,
            "size": dir_size(prefix()), "download_size": DOWNLOAD_SIZE, "install_dir": str(prefix()),
            "disk_free": disk_free(prefix()), "node": str(program) if program else None,
            "chrome": str(chrome()) if chrome() else None,
            "profile": str(profile_dir(home)) if home else None}


def install() -> None:
    """npm ci of the locked packages (no install scripts), then a check that the pinned version is there."""
    program, _ = npm()
    if program is None:
        raise ToolError(t("browser_needs_node"))
    target = prefix()
    target.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(LOCK_DIR / name, target / name)
    code, errors = run([str(program), "ci", "--ignore-scripts", "--no-audit", "--no-fund", "--omit=dev"], None, TIMEOUT,
                       cwd=target)
    if code != 0 or installed_version() != VERSION:
        raise ToolError(t("tool_install_failed", name="Playwright MCP") + (f"\n{errors.strip()}" if errors.strip() else ""))
    print(t("tool_installed", name="Playwright MCP", version=VERSION, path=cli_path()), flush=True)


def open_signin(home: Path, url: str = "") -> None:
    """Opens Chrome with Mehteran's profile, so that the person can sign in to the sites agent steps use.
    Only an http(s) address is opened, after "--": Chrome never reads it as one of its switches."""
    from . import urlfetch
    problem = url and urlfetch.url_problem(url)
    if problem:
        raise ToolError(problem)
    program = chrome()
    if program is None:
        raise ToolError(t("browser_needs_chrome"))
    profile = profile_dir(home)
    profile.mkdir(parents=True, exist_ok=True)
    from pipeline import system
    subprocess.Popen([str(program), f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
                      "--", url or "about:blank"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **system.new_process_group())


# --- one agent step -----------------------------------------------------------------------------------------

def site_hosts(text: str) -> list[str]:
    """"x.com", "https://news.ycombinator.com/news" and the like, one per line (or comma) -> host names."""
    hosts = []
    for item in text.replace(",", "\n").splitlines():
        item = item.strip().lower()
        if not item or item.startswith("#"):
            continue
        host = urlsplit(item if "://" in item else f"https://{item}").hostname or ""
        host = host.removeprefix("www.")
        if host and host not in hosts:
            hosts.append(host)
    return hosts


PLAIN_HOST = re.compile(r"[a-z0-9.-]+")


def host_allowed(url: str, hosts: list[str]) -> bool:
    """True for about:blank and for an http(s) address on one of the hosts or their subdomains.

    An address that a browser can read differently from urlsplit is refused: a backslash (Chrome reads it as "/"),
    white space or a control character (Chrome drops tabs and line breaks), a user part ("@"), a host that is not
    plain letters, digits, dots and hyphens (percent-encoding). So "https://evil.org\\@example.com" does not pass."""
    url = url.strip()
    if url in ("", "about:blank"):
        return True
    if "\\" in url or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        return False
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").removeprefix("www.")
    except ValueError:
        return False
    if "@" in parts.netloc or not PLAIN_HOST.fullmatch(host):
        return False
    return parts.scheme in ("http", "https") and any(host == h or host.endswith("." + h) for h in hosts)


def mcp_config(home: Path, out_dir: Path, hosts: list[str], headless: bool) -> dict:
    program, _ = node()
    if program is None:
        raise ToolError(t("browser_needs_node"))
    if not cli_path().is_file():
        raise ToolError(t("browser_not_installed"))
    if chrome() is None:
        raise ToolError(t("browser_needs_chrome"))
    profile = profile_dir(home)
    profile.mkdir(parents=True, exist_ok=True)
    args = [str(cli_path()), "--browser", "chrome", "--user-data-dir", str(profile), "--output-dir", str(out_dir),
            "--block-service-workers", "--image-responses", "omit", "--timeout-action", str(TIMEOUT_ACTION_MS),
            "--timeout-navigation", str(TIMEOUT_NAVIGATION_MS), "--blocked-origins", ";".join(BLOCKED_ORIGINS)]
    if headless:
        args.append("--headless")
    return {"mcpServers": {SERVER: {"command": str(program), "args": args}}}


def allowed_tools(mode: str) -> list[str]:
    return [f"mcp__{SERVER}__{name}" for name in (ACT_TOOLS if mode == "act" else READ_TOOLS)]


def guard(hosts: list[str]):
    """A check of each line of Claude Code's stream-json output: the reason to stop the step (an address outside the
    sites), or None. Also returns the line of the action log ("navigate https://...")."""
    def check(line: str) -> tuple[str | None, str | None]:
        try:
            event = json.loads(line)
        except ValueError:
            return None, None
        if isinstance(event, dict) and event.get("type") == "user":  # a tool's result: the page it ended on
            text = json.dumps((event.get("message") or {}).get("content") or [], ensure_ascii=False)
            for url in PAGE_URL.findall(text):
                if not host_allowed(url, hosts):
                    return t("agent_site_refused", url=url[:200], sites=", ".join(hosts)), None
            return None, None
        if not isinstance(event, dict) or event.get("type") != "assistant":
            return None, None
        stop, actions = None, []
        for part in (event.get("message") or {}).get("content") or []:
            if not isinstance(part, dict) or part.get("type") != "tool_use":
                continue
            name = str(part.get("name") or "").rpartition("__")[2]
            data = part.get("input") if isinstance(part.get("input"), dict) else {}
            shown = data.get("url") or data.get("element") or data.get("text") or data.get("action") or ""
            actions.append(f"{name} {str(shown)[:160]}".strip())
            url = data.get("url")
            if name in NAVIGATING and isinstance(url, str) and not host_allowed(url, hosts):
                stop = t("agent_site_refused", url=url[:200], sites=", ".join(hosts))
        return stop, "\n".join(actions) or None
    return check
