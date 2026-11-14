"""The AI tools that Mehteran may call: the [providers.*] sections of the translation app's config.toml.

Mehteran only reads that file; it never writes it. MEHTERAN_CONFIG names another TOML file with the same sections
(the tests use it for a fake tool). Without config.toml, config.default.toml is used.

Mehteran adds providers of its own that call a local HTTP API instead of a command: "ollama" (local models). Their
settings may be changed in <data>/configurations/providers.toml ([providers.ollama]: model, options); a provider of
config.toml with the same name wins.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from . import paths

# Providers that Mehteran calls itself (mehteran/worker.py), not through a command-line tool.
OWN_PROVIDERS = {"ollama": {"api": "ollama", "command": ["ollama"], "models": [], "model": ""}}
OWN_KEYS = {"model", "options"}  # what <data>/configurations/providers.toml may set
OPTION_KEYS = {"num_ctx": int, "temperature": float, "top_p": float, "seed": int}

GENERAL_KEYS = ("timeout", "retries", "quota_wait_minutes", "quota_max_hours")
GENERAL_DEFAULTS = {"timeout": 1200, "retries": 1, "quota_wait_minutes": 30, "quota_max_hours": 24}


def config_path() -> Path:
    if os.environ.get("MEHTERAN_CONFIG"):
        return Path(os.environ["MEHTERAN_CONFIG"]).expanduser()
    from pipeline.core import ROOT  # TP_ROOT moves the translation app's data folder; follow it
    for path in (ROOT / "config.toml", paths.REPO / "config.toml", paths.REPO / "config.default.toml"):
        if path.exists():
            return path
    return paths.REPO / "config.default.toml"


SYSTEM_PROMPT = "You are a careful analyst. Follow the instructions in the user message exactly and output only what is requested."


def _neutral(command: list) -> list:
    """The command with Mehteran's own system prompt: the translation app's one describes a translator of Islamic
    books, which does not fit a paper review or a comparison. The translation app's file is not changed."""
    return [SYSTEM_PROMPT if i and command[i - 1] == "--system-prompt" else arg for i, arg in enumerate(command)]


def provider_config() -> dict:
    """{"providers": {name: spec}, "general": {...}, "source": path}. A missing or broken file gives no providers."""
    path = config_path()
    try:
        with path.open("rb") as f:
            cfg = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        cfg = {}
    general = cfg.get("general") if isinstance(cfg.get("general"), dict) else {}
    providers = {name: {**spec, "command": _neutral(spec["command"])} for name, spec in (cfg.get("providers") or {}).items()
                 if isinstance(spec, dict) and isinstance(spec.get("command"), list) and spec["command"]}
    providers = {**own_providers(), **providers}
    return {"providers": providers, "general": {k: general.get(k, GENERAL_DEFAULTS[k]) for k in GENERAL_KEYS},
            "source": str(path)}


def own_providers() -> dict:
    """Mehteran's own providers with the settings of <data>/configurations/providers.toml (only known keys)."""
    out = {name: dict(spec) for name, spec in OWN_PROVIDERS.items()}
    try:
        with (paths.home() / "configurations" / "providers.toml").open("rb") as f:
            data = tomllib.load(f).get("providers") or {}
    except (OSError, tomllib.TOMLDecodeError, AttributeError):
        data = {}
    for name, spec in data.items() if isinstance(data, dict) else []:
        if name not in out or not isinstance(spec, dict):
            continue
        if isinstance(spec.get("model"), str):
            out[name]["model"] = spec["model"]
        options = spec.get("options") if isinstance(spec.get("options"), dict) else {}
        out[name]["options"] = {k: kind(v) for k, v in options.items() if k in OPTION_KEYS
                                and isinstance(v, (int, float)) and not isinstance(v, bool)
                                for kind in [OPTION_KEYS[k]]}
    return out


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
        out.append({"name": name, "models": models, "local": spec.get("api") == "ollama",
                    "efforts": [e for e in spec.get("efforts") or [] if isinstance(e, str)] if spec.get("effort") else []})
    return out
