"""Runs the LLM command-line tools (claude, gemini, codex)."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .core import PipelineError, Project, say, split_name
from .i18n import t
from .runstatus import STATUS
from .system import hidden_window, resolve


class LLMError(PipelineError):
    pass


class QuotaError(LLMError):
    def __init__(self, message: str, until: float):
        super().__init__(message)
        self.until = until


# Messages that the tools print when a usage limit or rate limit is reached.
_QUOTA = re.compile(
    r"usage limit|rate[ _-]?limit|quota|resource[ _]exhausted|too many requests|\b429\b|limit reached|"
    r"hit your (usage )?limit|exceeded your|credit balance is too low", re.I)
# When the tool exits with success, only these unambiguous phrases count: a short legitimate answer
# (for example a segment that cites hadith number 429) must never be taken for a limit message.
_QUOTA_STRICT = re.compile(r"usage limit|rate[ _-]?limit|limit reached|hit your (usage )?limit|too many requests|"
                           r"resource[ _]exhausted|quota exceeded|exceeded your current quota", re.I)
_UNITS = {"s": 1, "sec": 1, "second": 1, "m": 60, "min": 60, "minute": 60, "h": 3600, "hr": 3600, "hour": 3600,
          "d": 86400, "day": 86400}
_MIN_WAIT, _MAX_WAIT = 30, 26 * 3600

# Shared by all threads: until when each provider is blocked by a quota.
_blocked: dict[str, float] = {}
_blocked_lock = threading.Lock()


def quota_wait_seconds(message: str, default: float) -> float:
    """Reads the reset time from a quota message ("try again in 2 hours 13 minutes", "retry in 34s",
    "limit reached|1731234567"). Returns the default when the message does not say."""
    epoch = re.search(r"\|(\d{10})\b", message)
    if epoch:
        return min(max(int(epoch.group(1)) - time.time(), _MIN_WAIT), _MAX_WAIT)
    m = re.search(r"(?:try again|retry|reset[s]?)\s+(?:in|after)\s+((?:[\d.]+\s*[a-z]+[\s,and]*){1,3})", message, re.I)
    if m:
        total = 0.0
        for number, unit in re.findall(r"([\d.]+)\s*([a-z]+)", m.group(1), re.I):
            unit = unit.lower().rstrip("s") if len(unit) > 1 else unit.lower()
            if unit in _UNITS:
                total += float(number) * _UNITS[unit]
        if total:
            return min(max(total + 15, _MIN_WAIT), _MAX_WAIT)
    return default


def is_quota_message(text: str, failed: bool = True) -> bool:
    return bool((_QUOTA if failed else _QUOTA_STRICT).search(text or ""))


def parse_json(text: str) -> dict:
    """Reads the text between the first '{' and the last '}' as JSON (tolerates code fences and extra lines)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON in the answer")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("the JSON is not an object")
    return data


def _wait_while_blocked(name: str, max_until: float) -> None:
    while True:
        with _blocked_lock:
            until = _blocked.get(name, 0)
        if until <= time.time():
            return
        if STATUS.stopping:
            raise LLMError(t("stopped"))
        if until > max_until:
            raise LLMError(t("quota_gave_up", name=name))
        time.sleep(min(5, until - time.time()))


# The service refuses this kind of account (for example: Google ended the Gemini CLI sign-in for personal accounts).
ACCOUNT_REFUSED = re.compile(r"This client is no longer supported[^\n']*|IneligibleTierError[^\n']*")


def _call(proj: Project, spec: dict, model: str, prompt: str, timeout: int) -> tuple[int, str, str]:
    """One call of the tool, in an empty folder: it sees neither the project files nor any instruction files."""
    with tempfile.TemporaryDirectory(prefix="tp-") as tmp:
        out_file = Path(tmp) / "output.txt"
        cwd = Path(tmp) / "empty"
        cwd.mkdir()
        argv = [arg.replace("{output}", str(out_file)) for arg in spec["command"]]
        if model or spec.get("model"):
            argv += ["--model", model or spec["model"]]
        argv = resolve(argv)
        try:
            proc = subprocess.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout, cwd=cwd, **hidden_window())
        except FileNotFoundError:
            raise PipelineError(t("command_not_found", command=argv[0])) from None
        text = out_file.read_text(encoding="utf-8") if out_file.exists() else proc.stdout
        return proc.returncode, text, proc.stderr


def run(proj: Project, name: str, prompt: str, wait_for_quota: bool = True, attempts: int | None = None,
        timeout: int | None = None) -> str:
    """Sends the prompt on stdin and returns the model's answer. name: "provider" or "provider/model".

    Retries on errors and empty answers. When the tool reports a usage limit, every call to this provider
    waits until the limit resets and then continues (wait_for_quota=False raises QuotaError instead).
    """
    full_name = name
    name, model = split_name(name)  # usage limits belong to the provider (the account), not to one model
    spec = proj.cfg["providers"].get(name)
    if spec is None:
        raise PipelineError(t("provider_not_configured", name=name))
    general = proj.cfg["general"]
    default_wait = general.get("quota_wait_minutes", 30) * 60
    max_until = time.time() + general.get("quota_max_hours", 24) * 3600
    attempts = attempts or general["retries"]
    timeout = timeout or general["timeout"]
    error = ""
    attempt = 0
    while attempt < attempts:
        if wait_for_quota:
            _wait_while_blocked(name, max_until)
        if STATUS.stopping:
            raise LLMError(t("stopped"))
        started = time.time()
        try:
            code, text, stderr = _call(proj, spec, model, prompt, timeout)
        except subprocess.TimeoutExpired:
            error = t("no_answer_in_time", seconds=timeout)
            attempt += 1
            continue

        answer = text.strip()
        if code == 0 and spec.get("json_field"):
            try:
                data = parse_json(text)
                value = data.get(spec["json_field"])
                # A JSON answer that reports an error, or has no text, is a failed call.
                answer = value.strip() if isinstance(value, str) and not data.get("error") else ""
            except ValueError:
                answer = ""
        # A failed call, or a short answer that is only a limit message (some tools exit with 0 then).
        failed = code != 0 or not answer
        # Some tools echo the prompt in their error output; the book text must not count as a limit message
        # (a segment citing "hadith 429" would otherwise stop the provider).
        message = (stderr + "\n" + text).replace(prompt, "").strip() if failed else answer
        message = "\n".join(message.splitlines()[-20:])
        if failed and ACCOUNT_REFUSED.search(message):  # retrying cannot help: the account must change
            raise LLMError(t("account_refused", name=name, reason=ACCOUNT_REFUSED.search(message).group(0)))
        if (failed or len(answer) < 300) and is_quota_message(message, failed):
            until = time.time() + quota_wait_seconds(message, default_wait)
            if not wait_for_quota:
                raise QuotaError(t("quota_hit", name=name, time=time.strftime("%H:%M", time.localtime(until))), until)
            with _blocked_lock:
                first = _blocked.get(name, 0) < until - 60  # parallel calls report the same limit only once
                if first:
                    _blocked[name] = until
            if first:
                say(f"[quota] {t('quota_waiting', name=name, time=time.strftime('%H:%M', time.localtime(until)))}")
                STATUS.quota_wait(name, until, message.splitlines()[-1] if message else "")
            continue  # a quota wait is not counted as a failed attempt
        if not failed:
            STATUS.call_finished(time.time() - started)
            with _blocked_lock:
                cleared = _blocked.pop(name, None) is not None
            if cleared:
                STATUS.quota_clear(name)
            return answer
        error = message[-500:] or t("empty_answer", code=code)
        attempt += 1
        if attempt < attempts:
            for _ in range(15 * attempt):  # interruptible pause before the next attempt
                if STATUS.stopping:
                    raise LLMError(t("stopped"))
                time.sleep(1)
    raise LLMError(t("llm_failed", name=full_name, error=error))


def ask(proj: Project, name: str, prompt: str, parse, attempts: int = 2):
    """Decodes the answer with parse(text); asks again if the format is wrong or the answer is rejected."""
    error = None
    for _ in range(attempts):
        text = run(proj, name, prompt)
        try:
            return parse(text)
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            error = e
    raise LLMError(t("bad_format", name=name, error=error))
