"""Mehteran's own AI tool adapters (one module per tool) and the user's provider settings.

- The adapters: claude, codex, antigravity, gemini, ollama (base.py says what each one declares). Old names keep
  working: "chatgpt" (an older name for Codex) means "codex".
- The user's settings: <data>/configurations/providers.toml. No secrets are kept there.
      order = ["claude", "codex/gpt-5.5@high", "ollama/qwen3:8b"]   # the model order of `auto`
      [providers.claude]
      api_key = false      # "API key (billed)": the tool may use an API key from the environment
      concurrency = 2      # calls at once over all runs
      [providers.ollama]
      model = "gemma3:4b"  # the default local model
      options = {num_ctx = 8192}
- `auto` providers: "auto", "auto:strong", "auto:fast", "auto:local" are resolved when a run starts, from the model
  order (only installed, signed-in tools that do not bill an API key; Ollama models that run on this computer for
  auto:local) and frozen into the run with the other candidates, so a usage limit moves the step to the next one.
"""

from __future__ import annotations

import json
import re
import shutil
import threading
import time
import tomllib
from pathlib import Path

from .antigravity import Antigravity
from .base import BILLED_KEYS, BILLING_KINDS, SYSTEM_PROMPT, Adapter, CallError, UsageLimit, guarded_env  # noqa: F401
from .claude import Claude
from .codex import Codex
from .gemini import Gemini
from .ollama import Ollama, is_cloud
from .openai_local import OpenAILocal, loopback_url

ADAPTERS: dict[str, Adapter] = {a.id: a for a in (Claude(), Codex(), Antigravity(), Ollama(), OpenAILocal(), Gemini())}
NEEDS_MODEL = ("ollama", "openai-local")  # a local server: the order entry, the setting or its first model
ALIASES = {"chatgpt": "codex"}
AUTO = ("auto", "auto:strong", "auto:fast", "auto:local")
OPTION_KEYS = {"num_ctx": int, "temperature": float, "top_p": float, "seed": int}
ENTRY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}(/[A-Za-z0-9._:][A-Za-z0-9._:-]{0,80})?(@[a-z]{1,10})?\Z")
MAX_CONCURRENCY = 8


def settings_path(home: Path) -> Path:
    return Path(home) / "configurations" / "providers.toml"


def canonical(name: str, configured: dict | None = None) -> str:
    """"chatgpt/gpt-5@high" -> "codex/gpt-5@high" (unless "chatgpt" is configured under its own name)."""
    head, sep, rest = (name or "").partition("/")
    base, at, effort = head.partition("@")
    if base in ALIASES and not (configured and base in configured):
        return ALIASES[base] + at + effort + sep + rest
    return name


def split(name: str) -> tuple[str, str, str]:
    """"codex/gpt-5@high" -> ("codex", "gpt-5", "high")."""
    base, _, effort = (name or "").partition("@")
    provider, _, model = base.partition("/")
    return provider, model, effort


# --- the user's settings ------------------------------------------------------------------

def read_settings(home: Path) -> dict:
    """{"order": [entry], "unattended_subscriptions": bool, "providers": {id: {api_key, concurrency, model, options}}}:
    only known keys and values. unattended_subscriptions: scheduled and batch runs may use a tool signed in with a
    consumer subscription or a free account (off: only local models and API keys; see Engine.unattended_check)."""
    try:
        with settings_path(home).open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        data = {}
    order = [canonical(e) for e in data.get("order") or [] if isinstance(e, str) and ENTRY_RE.match(e)] \
        if isinstance(data.get("order"), list) else []
    out = {"order": list(dict.fromkeys(e for e in order if split(e)[0] in ADAPTERS)),
           "unattended_subscriptions": data.get("unattended_subscriptions") is True, "providers": {}}
    raw = data.get("providers") if isinstance(data.get("providers"), dict) else {}
    for name, spec in raw.items():
        name = canonical(name)
        if name not in ADAPTERS or not isinstance(spec, dict):
            continue
        clean = {}
        if isinstance(spec.get("api_key"), bool):
            clean["api_key"] = spec["api_key"]
        if isinstance(spec.get("concurrency"), int) and not isinstance(spec["concurrency"], bool):
            clean["concurrency"] = min(max(spec["concurrency"], 1), MAX_CONCURRENCY)
        if name in NEEDS_MODEL and isinstance(spec.get("model"), str):
            clean["model"] = spec["model"]
        if name == "openai-local" and loopback_url(spec.get("url")):
            clean["url"] = loopback_url(spec["url"])
        if name == "ollama" and isinstance(spec.get("options"), dict):
            clean["options"] = {k: OPTION_KEYS[k](v) for k, v in spec["options"].items() if k in OPTION_KEYS
                                and isinstance(v, (int, float)) and not isinstance(v, bool)}
        out["providers"][name] = clean
    return out


def _toml(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)  # a JSON string is a TOML basic string
    if isinstance(value, list):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k} = {_toml(v)}" for k, v in value.items()) + "}"
    raise TypeError(type(value))


def write_settings(home: Path, data: dict) -> dict:
    """Writes the settings (only known keys, as read_settings keeps them) and returns them as read back."""
    from mehteran import paths
    text = "# Mehteran's AI tool settings (the Setup tab writes this file). No secrets here.\n"
    text += f"order = {_toml([e for e in data.get('order') or [] if isinstance(e, str) and ENTRY_RE.match(e)])}\n"
    if data.get("unattended_subscriptions") is True:
        text += "unattended_subscriptions = true\n"
    for name, spec in (data.get("providers") or {}).items():
        if name in ADAPTERS and isinstance(spec, dict) and spec:
            text += f"\n[providers.{name}]\n" + "".join(f"{k} = {_toml(v)}\n" for k, v in spec.items())
    path = settings_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{time.time_ns()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    paths.replace(tmp, path)
    return read_settings(home)


# --- the specs that a run freezes -----------------------------------------------------------

def spec(name: str, user: dict) -> dict:
    """The settings of one adapter as a run keeps them (provider_cfg["providers"][name])."""
    adapter = ADAPTERS[name]
    mine = user["providers"].get(name, {})
    out = {"adapter": name, "models": list(adapter.models), "efforts": list(adapter.efforts), "model": "",
           "api_key": mine.get("api_key", False), "concurrency": mine.get("concurrency", adapter.concurrency),
           "billing": adapter.billing, "local": adapter.local, "context": adapter.context}
    if name == "ollama":  # Mehteran calls Ollama's HTTP API itself (worker.py); "api" as the older runs have it
        out.update({"api": "ollama", "command": ["ollama"], "model": mine.get("model", ""),
                    "options": mine.get("options", {})})
    if name == "openai-local":  # a local server with an OpenAI-compatible API (worker.py calls it)
        out.update({"api": "openai", "url": mine.get("url", ""), "model": mine.get("model", "")})
    return out


def specs(user: dict) -> dict:
    return {name: spec(name, user) for name in ADAPTERS}


def destination(provider: str, model: str, cfg_spec: dict | None = None) -> dict:
    """Where the text of a call goes: {vendor, local}. A provider of config.toml: its command's name."""
    adapter = ADAPTERS.get(provider)
    if adapter is None:
        command = (cfg_spec or {}).get("command") or []
        return {"vendor": Path(str(command[0])).name if command else provider, "local": False}
    if provider == "ollama" and is_cloud(model):
        return {"vendor": "Ollama Cloud", "local": False}
    return {"vendor": adapter.vendor, "local": adapter.model_is_local(model)}


# --- the state of each tool (installed, signed in, billing), kept for a short time ------------

_status: dict[str, tuple[float, dict]] = {}
_status_lock = threading.Lock()
STATUS_TTL = 30.0


def status(name: str, fresh: bool = False) -> dict:
    """{installed, signed_in, info, billing, models?}; the answer is kept for STATUS_TTL seconds."""
    with _status_lock:
        known = _status.get(name)
    if known and not fresh and time.time() - known[0] < STATUS_TTL:
        return known[1]
    adapter = ADAPTERS[name]
    if name == "ollama":
        from mehteran import ollama
        installed = ollama.binary()[0] is not None or ollama.running()
        out = {"installed": installed, "signed_in": installed, "info": "", "billing": "local",
               "models": adapter.list_models() if installed else []}
    elif name == "openai-local":  # "installed": the server at the user's address answers
        url = read_settings(_home())["providers"].get(name, {}).get("url", "")
        models = adapter.list_models(url) if url else []
        out = {"installed": bool(models), "signed_in": bool(models), "info": url, "billing": "local", "models": models}
    else:
        installed = shutil.which(adapter.program) is not None
        out = {"installed": installed, "signed_in": False, "info": "", "billing": adapter.billing}
        if installed:
            try:
                out.update(adapter.login())
            except Exception as e:  # noqa: BLE001 - shown as "not signed in"
                out["info"] = f"{type(e).__name__}"
    with _status_lock:
        _status[name] = (time.time(), out)
    return out


def _home() -> Path:
    from mehteran import paths
    return paths.home()


def forget_status(name: str | None = None) -> None:
    """The next status() asks again (the user changed a setting)."""
    with _status_lock:
        _status.clear() if name is None else _status.pop(name, None)


def statuses(names=None, fresh: bool = False) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from ..common import tools
    tools.extend_path()
    names = list(names or ADAPTERS)
    with ThreadPoolExecutor(max_workers=max(1, len(names))) as pool:
        return dict(zip(names, pool.map(lambda n: status(n, fresh), names)))


def effective_billing(name: str, st: dict, user: dict) -> str:
    """What a call would use: an API key in the environment does not count when the worker removes it."""
    billing = st.get("billing") or ADAPTERS[name].billing
    allowed = user["providers"].get(name, {}).get("api_key", False)
    if billing == "api_key" and st.get("key_source") in BILLED_KEYS and not allowed:
        return ADAPTERS[name].billing  # the key is in the environment only: the worker does not pass it
    return billing


def problem(name: str, st: dict, user: dict) -> str | None:
    """Why a tool cannot be used by `auto` now (a message key), or None."""
    if not st.get("installed"):
        return "provider_not_installed"
    if not st.get("signed_in"):
        return "provider_not_signed_in"
    if effective_billing(name, st, user) == "api_key":
        return "provider_billed"
    return None


# --- auto ---------------------------------------------------------------------------------

def default_order(states: dict, user: dict) -> list[str]:
    """The model order when the user did not set one: the usable tools in the adapters' order; Ollama with its
    default model, or its first installed one."""
    out = []
    for name in ADAPTERS:
        st = states.get(name) or {}
        if problem(name, st, user):
            continue
        if name in NEEDS_MODEL:
            model = _local_model(name, st, user)
            if model:
                out.append(f"{name}/{model}")
            continue
        out.append(name)
    return out


def _local_model(name: str, st: dict, user: dict) -> str:
    """A local server's model when the order names none: the user's setting, else its first local model."""
    return user["providers"].get(name, {}).get("model") or next(
        (m for m in st.get("models") or [] if not is_cloud(m)), "")


def order(states: dict, user: dict) -> list[str]:
    return list(user["order"]) or default_order(states, user)


def _shape(entry: str, kind: str) -> str:
    """The entry for a kind of auto: fast and strong take the tool's fast or strong model (or a low or high
    thinking level) when the entry names none."""
    provider, model, effort = split(entry)
    adapter = ADAPTERS[provider]
    if kind in ("auto:fast", "auto:strong") and not model:
        model = adapter.fast_model if kind == "auto:fast" else adapter.strong_model
        if not model and not effort and adapter.efforts:
            effort = "low" if kind == "auto:fast" else "high"
    return provider + (f"/{model}" if model else "") + (f"@{effort}" if effort else "")


def candidates(kind: str, states: dict, user: dict, local_only: bool = False) -> list[str]:
    """The models that `kind` may use now, best first."""
    out = []
    for entry in order(states, user):
        provider, model, _ = split(entry)
        if provider not in ADAPTERS or problem(provider, states.get(provider) or {}, user):
            continue
        if provider in NEEDS_MODEL and not model:
            model = _local_model(provider, states.get(provider) or {}, user)
            if not model:
                continue
            entry = f"{provider}/{model}" + (f"@{split(entry)[2]}" if split(entry)[2] else "")
        if (kind == "auto:local" or local_only) and not ADAPTERS[provider].model_is_local(model):
            continue
        out.append(_shape(entry, kind))
    return list(dict.fromkeys(out))


# --- usage limits known from earlier calls (all runs, the Setup test) -----------------------------

def blocked(store, now: float | None = None, exclude: tuple[str, str] | None = None) -> dict[str, float]:
    """{provider: until} for the providers whose last usage limit has not reset yet (no successful call since).
    exclude: (run id, node id) whose own calls do not count."""
    now = time.time() if now is None else now
    out: dict[str, float] = {}
    for row in store.calls(now - 2 * 86400):
        if exclude and (row["run_id"], row["node_id"]) == exclude:
            continue
        name = canonical(row["provider"])
        if row["outcome"] == "ok":
            out.pop(name, None)
        elif row["outcome"] == "quota" and row["until"] and row["until"] > now:
            out[name] = max(out.get(name, 0), row["until"])
    return out


# --- calls at once, over all runs of this process ---------------------------------------------

_slots: dict[str, tuple[int, threading.BoundedSemaphore]] = {}
_slots_lock = threading.Lock()


def slot(provider: str, size: int) -> threading.BoundedSemaphore:
    """The semaphore that limits the calls at once to one provider (all runs of this Mehteran process)."""
    size = min(max(int(size or 1), 1), MAX_CONCURRENCY)
    with _slots_lock:
        known = _slots.get(provider)
        if known is None or known[0] != size:  # a new size applies to the calls that start from now on
            known = _slots[provider] = (size, threading.BoundedSemaphore(size))
        return known[1]


def busy() -> dict[str, dict]:
    """{provider: {size, in_use}} for the Setup tab."""
    with _slots_lock:
        return {name: {"size": size, "in_use": size - sem._value} for name, (size, sem) in _slots.items()}
