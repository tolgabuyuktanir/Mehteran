"""Installation, sign-in status and sign-in of the command-line tools (claude, codex, agy, gemini) and of the PDF reader."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import runtime, system
from .core import ROOT, PipelineError, write_text
from .i18n import t

HOME = Path.home()
GEMINI_DIR = HOME / ".gemini"
AGY_DIR = GEMINI_DIR / "antigravity-cli"

# "provider": the [providers.*] name in config.toml
TOOLS = {
    "claude": {
        "name": "Claude Code", "command": "claude", "provider": "claude",
        # Aliases that "claude --model" accepts for the latest model of each family.
        "models": ["fable", "opus", "sonnet", "haiku"],
        "login": "claude auth login",
    },
    "codex": {
        "name": "Codex CLI (ChatGPT)", "command": "codex", "provider": "chatgpt",
        "login": "codex login",
    },
    "antigravity": {
        "name": "Antigravity CLI (Gemini)", "command": "agy", "provider": "antigravity",
        "login": "agy",
    },
    "gemini": {
        "name": "Gemini CLI", "command": "gemini", "provider": "gemini",
        "login": "gemini",
    },
    # Not a model: reads PDF books. provider None = no sign-in.
    "pdf": {
        "name": "PDF reader (Poppler)", "command": "pdftotext", "provider": None,
        "login": "",
    },
}


def extend_path(root: Path = ROOT) -> None:
    """Adds the usual install folders to PATH, so that newly installed tools are found.

    The tools that the application installed itself (<root>/.runtime) come first.
    """
    parts = os.environ.get("PATH", "").split(os.pathsep)
    own = [str(folder) for folder in runtime.bin_dirs(root)]
    parts = own + [part for part in parts if part not in own]
    os.environ["PATH"] = os.pathsep.join(parts)
    candidates = [HOME / ".local" / "bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    if system.IS_WINDOWS and os.environ.get("APPDATA"):
        candidates.append(Path(os.environ["APPDATA"]) / "npm")
    if system.IS_WINDOWS and os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "agy" / "bin")
    npm = shutil.which("npm")
    if npm:
        try:
            prefix = subprocess.run([npm, "config", "get", "prefix"], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=20, **system.hidden_window()).stdout.strip()
            if prefix:
                candidates.append(Path(prefix) if system.IS_WINDOWS else Path(prefix) / "bin")
        except (OSError, subprocess.TimeoutExpired):
            pass
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for folder in candidates:
        if folder.is_dir() and str(folder) not in parts:
            parts.append(str(folder))
    os.environ["PATH"] = os.pathsep.join(parts)


def _run(argv: list[str], timeout: int = 30, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(system.resolve(argv), input=stdin, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=HOME,
                          stdin=None if stdin is not None else subprocess.DEVNULL, **system.hidden_window())


def _gemini_settings() -> dict:
    path = GEMINI_DIR / "settings.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise PipelineError(t("gemini_settings_invalid", path=path)) from None


def _gemini_auth_type() -> str | None:
    try:
        return _gemini_settings().get("security", {}).get("auth", {}).get("selectedType")
    except PipelineError:
        return None


def _gemini_has_key() -> bool:
    if os.environ.get("GEMINI_API_KEY"):
        return True
    env = GEMINI_DIR / ".env"
    # Only checks that a key is present; the value is never passed anywhere.
    return env.exists() and re.search(r"^GEMINI_API_KEY=\S", env.read_text(encoding="utf-8"), re.M) is not None


def codex_has_credentials() -> bool:
    """Only checks that Codex stored a sign-in (the file is never read)."""
    home = Path(os.environ.get("CODEX_HOME") or HOME / ".codex")
    try:
        return (home / "auth.json").stat().st_size > 2
    except OSError:
        return False


def login_status(tool: str) -> tuple[bool, str]:
    """Returns (signed in, description)."""
    exe = TOOLS[tool]["command"]
    try:
        if tool == "claude":
            proc = _run([exe, "auth", "status"])
            try:
                data = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return False, t("status_unreadable")
            if data.get("loggedIn"):
                method = data.get("authMethod") or ""
                return True, t("claude_subscription") if method == "claude.ai" else method
            return False, t("not_signed_in")
        if tool == "codex":
            proc = _run([exe, "login", "status"])
            text = (proc.stdout + proc.stderr).strip().splitlines()
            if proc.returncode != 0 and codex_has_credentials():
                return True, t("stored_sign_in")  # the status command failed (seen on Windows), but a sign-in is stored
            return proc.returncode == 0, (text[-1] if text else "")
    except (OSError, subprocess.TimeoutExpired):
        return False, t("status_unreadable")
    if tool == "antigravity":
        # The token is in the system keyring, which cannot be read here; the CLI writes this file after the first
        # sign-in. Asking the CLI itself could open a sign-in page in the browser. "Test" checks the account.
        return (True, t("google_account")) if agy_signed_in() else (False, t("not_signed_in"))

    auth = _gemini_auth_type()
    if auth == "oauth-personal" and (GEMINI_DIR / "oauth_creds.json").exists():
        return True, t("google_account")
    if _gemini_has_key() and auth in (None, "gemini-api-key"):
        return True, t("api_key")
    if (GEMINI_DIR / "oauth_creds.json").exists():
        return False, t("google_not_selected")
    return False, t("not_signed_in")


def agy_signed_in() -> bool:
    return (AGY_DIR / "cache" / "onboarding.json").exists()


def status(tool: str) -> dict:
    spec = TOOLS[tool]
    path = shutil.which(spec["command"])
    info = {"id": tool, "name": spec["name"], "provider": spec["provider"], "installed": bool(path),
            "version": "", "signed_in": False, "sign_in_info": "", "login_command": spec["login"]}
    if path:
        try:
            if tool == "pdf":  # pdftotext writes its version to stderr, for "-v"
                info["version"] = _run([path, "-v"]).stderr.strip().splitlines()[0][:60]
            else:
                info["version"] = _run([path, "--version"]).stdout.strip().splitlines()[0][:60]
        except (OSError, subprocess.TimeoutExpired, IndexError):
            pass
        info["signed_in"], info["sign_in_info"] = (True, "") if spec["provider"] is None else login_status(tool)
    return info


def install_command(tools: list[str]) -> list[str]:
    """The command that installs the tools in order (see runtime.install_tool); it needs no Node.js or admin rights."""
    import sys
    return [sys.executable, "-m", "pipeline", "install", *tools]


MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


def list_models(tool: str) -> list[str]:
    """The models that the tool offers, read from the tool itself. Empty when the list cannot be read.

    claude: the aliases that the CLI resolves to its latest models. codex: the model list that Codex keeps in its
    own folder after it ran once. gemini: the output of "gemini --list-models".
    """
    names: list[str] = []
    try:
        if tool == "codex":
            home = Path(os.environ.get("CODEX_HOME") or HOME / ".codex")
            data = json.loads((home / "models_cache.json").read_text(encoding="utf-8"))
            names = [str(m.get("slug", "")) for m in data.get("models", []) if isinstance(m, dict) and m.get("visibility") == "list"]
        elif tool == "antigravity" and shutil.which("agy") and agy_signed_in():
            out = _run(["agy", "models"], timeout=60).stdout
            # "gemini-4-argon-high" is the model "gemini-4-argon" at the level "high": the level is chosen apart.
            names = [re.sub(r"-(low|medium|high|xhigh|max)$", "", name) for name in re.findall(r"^(\S+)\t", out, re.M)]
        elif tool == "gemini" and shutil.which("gemini"):
            out = _run(["gemini", "--list-models"], timeout=60).stdout
            names = [name for name in re.findall(r"^(\S+) \(", out, re.M) if name != "auto"]  # "auto" is the default
        else:
            names = list(TOOLS[tool].get("models", []))
    except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
        return []
    return [name for name in dict.fromkeys(names) if MODEL_NAME.match(name)]


def open_terminal(command: str, root: Path = ROOT, note: str = "") -> str:
    """Runs the sign-in command in a new terminal window. When that is not possible, the user runs it."""
    dirs = [str(d) for d in runtime.bin_dirs(root) if d.is_dir()] + [str(HOME / ".local" / "bin")]
    if not system.open_terminal(command, dirs, note):
        raise PipelineError(t("run_in_terminal", command=system.terminal_command(command, dirs)))
    return t("terminal_opened")


def _set_gemini_auth(kind: str) -> None:
    settings = _gemini_settings()
    settings.setdefault("security", {}).setdefault("auth", {})["selectedType"] = kind
    write_text(GEMINI_DIR / "settings.json", json.dumps(settings, ensure_ascii=False, indent=2) + "\n")


def _clean_key(key: str) -> str:
    key = (key or "").strip()
    if not re.fullmatch(r"[\x21-\x7e]{20,300}", key):
        raise PipelineError(t("invalid_key"))
    return key


def login(tool: str, method: str, key: str = "") -> str:
    """Signs in. method: terminal | google | key"""
    if not shutil.which(TOOLS[tool]["command"]):
        raise PipelineError(t("install_first"))
    if method == "terminal":
        return open_terminal(TOOLS[tool]["login"], note=t(f"terminal_note_{tool}"))

    if tool == "gemini" and method == "google":
        _set_gemini_auth("oauth-personal")
        if (GEMINI_DIR / "oauth_creds.json").exists():
            return t("google_selected")
        return open_terminal("gemini", note=t("terminal_note_gemini"))

    if tool == "gemini" and method == "key":
        key = _clean_key(key)
        env = GEMINI_DIR / ".env"
        lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
        lines = [line for line in lines if not line.startswith("GEMINI_API_KEY=")] + [f"GEMINI_API_KEY={key}"]
        # Created with owner-only permissions from the start: the file holds a secret.
        env.parent.mkdir(parents=True, exist_ok=True)
        tmp = env.with_name(".env.tmp")
        tmp.unlink(missing_ok=True)
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, env)
        env.chmod(0o600)
        _set_gemini_auth("gemini-api-key")
        return t("gemini_key_saved")

    if tool == "codex" and method == "key":
        proc = _run([TOOLS[tool]["command"], "login", "--with-api-key"], timeout=60, stdin=_clean_key(key) + "\n")
        if proc.returncode != 0:
            raise PipelineError(t("codex_key_rejected"))
        return t("codex_key_saved")

    raise PipelineError(t("login_method_unsupported"))
