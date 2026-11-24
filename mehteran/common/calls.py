"""What the command-line tools say, and one call of a provider that is given by its command.

- Usage limits: the messages that the tools print when a usage or rate limit is reached, and the reset time in them.
- parse_json: the JSON object of an answer; stream_json_answer: the answer of Antigravity CLI's stream-json output.
- call_command: one call of a provider of MEHTERAN_CONFIG or config.toml ([providers.<name>] command = [...]): the
  prompt on stdin, in an empty folder. The engine counts the attempts and waits for a usage limit itself.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ..i18n import t
from .core import UserError
from .system import hidden_window, resolve


class CommandError(UserError):
    pass


class QuotaError(CommandError):
    def __init__(self, message: str, until: float):
        super().__init__(message)
        self.until = until


# Messages that the tools print when a usage limit or rate limit is reached.
_QUOTA = re.compile(
    r"usage limit|rate[ _-]?limit|quota|resource[ _]exhausted|too many requests|\b429\b|limit reached|"
    r"hit your (usage )?limit|exceeded your|credit balance is too low", re.I)
# When the tool exits with success, only these unambiguous phrases count: a short legitimate answer (for example one
# that cites "error 429") must never be taken for a limit message.
_QUOTA_STRICT = re.compile(r"usage limit|rate[ _-]?limit|limit reached|hit your (usage )?limit|too many requests|"
                           r"resource[ _]exhausted|quota exceeded|exceeded your current quota", re.I)
_UNITS = {"s": 1, "sec": 1, "second": 1, "m": 60, "min": 60, "minute": 60, "h": 3600, "hr": 3600, "hour": 3600,
          "d": 86400, "day": 86400}
_MIN_WAIT, _MAX_WAIT = 30, 26 * 3600

# The service refuses this kind of account (for example: Google ended the Gemini CLI sign-in for personal accounts).
ACCOUNT_REFUSED = re.compile(r"This client is no longer supported[^\n']*|IneligibleTierError[^\n']*")

# Antigravity CLI keeps each conversation in its own folder; Mehteran removes the ones its calls made.
AGY_DIR = Path.home() / ".gemini" / "antigravity-cli"
_CONVERSATION_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


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


def stream_json_answer(stdout: str) -> tuple[str, str]:
    """(answer, error) of a stream-json run (Antigravity CLI): the "result" event carries both. The conversation that
    the run stored is deleted: each takes about 0.5 MB, and a workflow makes many calls."""
    result = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("event") == "result" and isinstance(event.get("result"), dict):
            result = event["result"]
    if result is None:
        return "", ""
    conversation = str(result.get("conversation_id", ""))
    if _CONVERSATION_ID.match(conversation):
        for path in AGY_DIR.joinpath("conversations").glob(f"{conversation}.db*"):
            path.unlink(missing_ok=True)
        shutil.rmtree(AGY_DIR / "brain" / conversation, ignore_errors=True)
    answer = result.get("response") if result.get("status") == "SUCCESS" else ""
    error = str(result.get("error") or "")
    if result.get("denied_actions") and not answer:
        error = (error + " " + t("tool_use_denied")).strip()
    return (answer if isinstance(answer, str) else ""), error


def call_command(name: str, spec: dict, model: str, effort: str, prompt: str, timeout: int,
                 default_wait: float = 1800) -> str:
    """One call of a provider given by its command; returns the answer. Raises QuotaError for a usage limit (with
    the time it resets), CommandError for any other failure."""
    with tempfile.TemporaryDirectory(prefix="mehteran-cmd-") as tmp:
        out_file = Path(tmp) / "output.txt"
        cwd = Path(tmp) / "empty"
        cwd.mkdir()
        argv = [arg.replace("{output}", str(out_file)) for arg in spec["command"]]
        if model or spec.get("model"):
            argv += ["--model", model or spec["model"]]
        if effort and spec.get("effort"):  # the tool's thinking-level option, for example ["--effort", "{effort}"]
            argv += [arg.replace("{effort}", effort) for arg in spec["effort"]]
        argv = resolve(argv)
        stream = spec.get("input") == "stream-json"
        stdin = json.dumps({"event": "user", "message": {"content": prompt}}, ensure_ascii=False) + "\n" if stream else prompt
        try:
            proc = subprocess.run(argv, input=stdin, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout, cwd=cwd, **hidden_window())
        except FileNotFoundError:
            raise CommandError(t("command_not_found", command=argv[0])) from None
        except subprocess.TimeoutExpired:
            raise CommandError(t("no_answer_in_time", seconds=timeout)) from None
        if stream:
            text, error = stream_json_answer(proc.stdout)
            code, stderr = (proc.returncode or (0 if text else 1)), (proc.stderr + "\n" + error).strip()
        else:
            text = out_file.read_text(encoding="utf-8") if out_file.exists() else proc.stdout
            code, stderr = proc.returncode, proc.stderr
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
    # Some tools echo the prompt in their error output: the document text must not count as a limit message.
    message = (stderr + "\n" + text).replace(prompt, "").strip() if failed else answer
    message = "\n".join(message.splitlines()[-20:])
    if failed and ACCOUNT_REFUSED.search(message):  # retrying cannot help: the account must change
        raise CommandError(t("account_refused", name=name, reason=ACCOUNT_REFUSED.search(message).group(0)))
    if (failed or len(answer) < 300) and is_quota_message(message, failed):
        until = time.time() + quota_wait_seconds(message, default_wait)
        raise QuotaError(t("quota_hit", name=name, time=time.strftime("%H:%M", time.localtime(until))), until)
    if failed:
        raise CommandError(message[-500:] or t("empty_answer", code=code))
    return answer
