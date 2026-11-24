"""The AI tools that Mehteran may call, for the workflows.

- Mehteran's own adapters (mehteran/providers/): claude, codex, antigravity, gemini, ollama, with the user's settings
  of <data>/configurations/providers.toml. The old name "chatgpt" means codex.
- Providers given by their command: the [providers.*] sections (command = [...]) of a TOML file, which also holds
  [general] (timeout, retries, usage-limit waits). They run through mehteran.common.calls.call_command. The file is
  MEHTERAN_CONFIG, else <data>/configurations/config.toml, else the config.toml in the code folder that an older
  Mehteran with the book translation read. Sections named like an adapter (claude, chatgpt, antigravity, gemini) are
  skipped, except in MEHTERAN_CONFIG, whose providers win over the adapters (the tests use it for a fake tool).
  Mehteran never writes these files.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from . import paths
from . import providers as adapters
from .providers import SYSTEM_PROMPT  # noqa: F401 - imported from here by older code

GENERAL_KEYS = ("timeout", "retries", "quota_wait_minutes", "quota_max_hours")
GENERAL_DEFAULTS = {"timeout": 1200, "retries": 1, "quota_wait_minutes": 30, "quota_max_hours": 24}


def config_path() -> Path:
    if os.environ.get("MEHTERAN_CONFIG"):
        return Path(os.environ["MEHTERAN_CONFIG"]).expanduser()
    own = paths.home() / "configurations" / "config.toml"
    legacy = paths.REPO / "config.toml"
    return legacy if legacy.is_file() and not own.is_file() else own


def _neutral(command: list) -> list:
    """The command with Mehteran's own system prompt: a config.toml of the book translation describes a translator of
    religious books, which does not fit a paper review or a comparison. The file is not changed."""
    return [SYSTEM_PROMPT if i and command[i - 1] == "--system-prompt" else arg for i, arg in enumerate(command)]


def provider_config() -> dict:
    """{"providers": {name: spec}, "general": {...}, "order": [...], "source": path}. A missing or broken file gives
    only the adapters."""
    path = config_path()
    try:
        with path.open("rb") as f:
            cfg = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        cfg = {}
    general = cfg.get("general") if isinstance(cfg.get("general"), dict) else {}
    user = adapters.read_settings(paths.home())
    providers = adapters.specs(user)
    explicit = bool(os.environ.get("MEHTERAN_CONFIG"))
    for name, spec in (cfg.get("providers") or {}).items():
        if not (isinstance(spec, dict) and isinstance(spec.get("command"), list) and spec["command"]):
            continue
        if explicit or adapters.canonical(name) not in adapters.ADAPTERS:
            providers[name] = {**spec, "command": _neutral(spec["command"])}
    return {"providers": providers, "general": {k: general.get(k, GENERAL_DEFAULTS[k]) for k in GENERAL_KEYS},
            "order": user["order"], "source": str(path)}


def own_providers() -> dict:
    """The adapters that Mehteran calls without a command-line tool (Ollama), with the user's settings."""
    user = adapters.read_settings(paths.home())
    return {name: adapters.spec(name, user) for name, a in adapters.ADAPTERS.items() if not a.cli}


def provider_choices(cfg: dict) -> list[dict]:
    """What the run form offers: each provider with its models and thinking levels. For Ollama: its installed
    models (none while it does not run)."""
    out = []
    for name, spec in cfg["providers"].items():
        models = [m for m in spec.get("models") or [] if isinstance(m, str)]
        if spec.get("api") == "ollama":
            from . import ollama
            models = [m["name"] for m in ollama.installed_models() if ollama.MODEL_RE.match(m["name"])
                      and "/" not in m["name"]]  # "provider/model": a model name with "/" cannot be written
        if spec.get("adapter") == "openai-local":  # the local server's models (none while it does not answer)
            models = [m for m in adapters.ADAPTERS["openai-local"].list_models(spec.get("url", "")) if "/" not in m]
        out.append({"name": name, "models": models, "local": spec.get("api") in ("ollama", "openai"), "adapter": spec.get("adapter"),
                    "efforts": [e for e in spec.get("efforts") or [] if isinstance(e, str)]
                    if spec.get("effort") or spec.get("adapter") else []})
    return out
