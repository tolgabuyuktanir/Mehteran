"""What every AI tool adapter has, and the one call of a command-line tool (run).

An adapter (one module per tool in this package) says how Mehteran calls the tool: the program and Mehteran's own
safe flags, how the prompt goes in, how the answer and a usage limit come out, which environment variables would
bill an API account, where the text goes (vendor), the billing kind, the context size and the default number of
calls at once. The translation app (pipeline/) keeps its own commands in config.toml; nothing here changes them.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

SYSTEM_PROMPT = "You are a careful analyst. Follow the instructions in the user message exactly and output only what is requested."

# Environment variables that make a tool bill an API account instead of the user's subscription. The worker drops
# all of them, and gives a tool back its own ones only when the user allowed "API key (billed)" for it.
BILLED_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
               "GOOGLE_API_KEY")

BILLING_KINDS = ("subscription", "free", "local", "api_key")


class CallError(Exception):
    """The call failed; the message is shown on the step."""


class UsageLimit(CallError):
    """The tool reported a usage limit; until: epoch seconds when it resets."""

    def __init__(self, message: str, until: float):
        super().__init__(message)
        self.until = until


class Adapter:
    id = ""
    name = ""                 # what the user sees ("Claude Code")
    vendor = ""               # where the prompt goes ("Anthropic")
    tool: str | None = None   # the pipeline.tools id (install, sign-in, model list)
    program = ""              # the command
    billing = "subscription"  # the billing kind when signed in normally (BILLING_KINDS)
    keys: tuple = ()          # the BILLED_KEYS that this tool reads
    efforts: tuple = ()       # thinking levels it takes
    models: tuple = ()        # offered when the tool cannot list its models
    fast_model = ""           # auto:fast / auto:strong use these when the entry of the model order names no model
    strong_model = ""
    context = 200_000         # tokens the model takes in (an estimate for the run form)
    concurrency = 2           # calls at once over all runs (the user may change it)
    local = False             # the text stays on this computer
    stream_json = False       # stdout is JSON events (mehteran/toolstream.py shows their text)
    cli = True                # False: Mehteran calls an HTTP API itself (Ollama)

    # --- the call ---
    def argv(self, model: str, effort: str, out_file: Path) -> list[str]:
        raise NotImplementedError

    def agent_argv(self, model: str, effort: str, out_file: Path, mcp_file: Path, tools: list[str]) -> list[str] | None:
        """The command of an agent step (ai.agent): the tool with only the MCP server of mcp_file and only the
        named tools of it. None: this tool cannot run agent steps."""
        return None

    def stdin(self, prompt: str) -> str:
        return prompt

    def parse(self, code: int, stdout: str, stderr: str, out_file: Path) -> tuple[str, str]:
        """(answer, error text) of one call."""
        text = out_file.read_text(encoding="utf-8") if out_file.exists() else stdout
        return (text.strip() if code == 0 else ""), stderr

    def limit_until(self, stdout: str) -> float | None:
        """When the tool's own output says that a usage limit was hit: until when. None otherwise."""
        return None

    def usage_seen(self, stdout: str) -> dict | None:
        """The tool's own usage report in its output (Claude Code's rate_limit_event), or None."""
        return None

    # --- the Setup tab ---
    def list_models(self) -> list[str]:
        from pipeline import tools
        return tools.list_models(self.tool) if self.tool else list(self.models)

    def login(self) -> dict:
        """{signed_in, info, billing}: billing is what a call would use now (BILLING_KINDS)."""
        from pipeline import tools
        signed_in, info = tools.login_status(self.tool)
        return {"signed_in": signed_in, "info": info, "billing": self.billing}

    def model_is_local(self, model: str) -> bool:
        return self.local


def guarded_env(adapter_keys: tuple, allow_api_key: bool, base: dict | None = None) -> dict:
    """The environment for a tool: without the API keys that would bill an account, except the tool's own ones
    when the user allowed "API key (billed)" for it."""
    env = dict(os.environ if base is None else base)
    for key in BILLED_KEYS:
        if not (allow_api_key and key in adapter_keys):
            env.pop(key, None)
    return env


class Stopped(CallError):
    """guard() stopped the call (an agent step left its sites); the message says why."""


def _stream(argv: list, stdin: str, timeout: float, cwd: Path, env: dict, on_output,
            guard=None) -> tuple[int, str, str]:
    """Runs argv with stdin; each line of stdout goes to on_output(line) as it arrives (an error there never stops
    the call). Raises subprocess.TimeoutExpired after timeout seconds (the tool is killed). guard(line) -> a reason
    or None: a reason kills the tool at once and raises Stopped."""
    from pipeline.system import hidden_window
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            encoding="utf-8", errors="replace", cwd=cwd, env=env, **hidden_window())
    out, err = [], []
    stopped: list[str] = []

    def write_input() -> None:
        try:
            proc.stdin.write(stdin)
            proc.stdin.close()
        except OSError:  # the tool ended without reading all of it
            pass

    def read_output() -> None:
        for line in proc.stdout:
            out.append(line)
            reason = guard(line) if guard else None
            if reason and not stopped:
                stopped.append(reason)
                from pipeline import system
                system.stop_tree(proc.pid)  # the tool and the browser server it started
            if on_output:
                try:
                    on_output(line)
                except Exception:  # noqa: BLE001 - a live log must never break the call
                    pass

    readers = [threading.Thread(target=read_output, daemon=True),
               threading.Thread(target=lambda: err.append(proc.stderr.read()), daemon=True)]
    for thread in [threading.Thread(target=write_input, daemon=True), *readers]:
        thread.start()
    deadline = time.monotonic() + timeout
    for thread in readers:
        thread.join(max(0.0, deadline - time.monotonic()))
    if any(thread.is_alive() for thread in readers):
        proc.kill()
        proc.wait()
        raise subprocess.TimeoutExpired(argv, timeout)
    proc.wait(max(1.0, deadline - time.monotonic()))
    if stopped:
        raise Stopped(stopped[0])
    return proc.returncode, "".join(out), "".join(err)


def run(adapter: Adapter, spec: dict, model: str, effort: str, prompt: str, timeout: float, on_output=None,
        default_wait: float = 1800, agent: dict | None = None) -> tuple[str, str]:
    """One call of a command-line tool, in an empty temporary folder (it sees no project or instruction files) and
    with the guarded environment. Returns (answer, stdout). Raises UsageLimit or CallError.

    spec: the provider's settings frozen with the run: "program" (a list that replaces the program, for the tests),
    "api_key" (the user allowed "API key (billed)"). agent: {"mcp_file", "tools", "guard"} for an agent step: the
    tool gets that MCP server and those tools only, and guard(line) may stop it (Stopped)."""
    from pipeline.i18n import t
    from pipeline.providers import ACCOUNT_REFUSED, is_quota_message, quota_wait_seconds
    from pipeline.system import resolve
    with tempfile.TemporaryDirectory(prefix="mehteran-call-") as tmp:
        out_file = Path(tmp) / "output.txt"
        cwd = Path(tmp) / "empty"
        cwd.mkdir()
        if agent:
            argv = adapter.agent_argv(model or spec.get("model") or "", effort, out_file, Path(agent["mcp_file"]),
                                      agent["tools"])
            if argv is None:
                raise CallError(t("agent_needs_claude", name=adapter.name))
        else:
            argv = adapter.argv(model or spec.get("model") or "", effort, out_file)
        program = spec.get("program")
        if isinstance(program, list) and program:
            argv = [*program, *argv[1:]]
        argv = resolve(argv)
        env = guarded_env(adapter.keys, spec.get("api_key") is True)
        try:
            code, stdout, stderr = _stream(argv, adapter.stdin(prompt), timeout, cwd, env, on_output,
                                           agent.get("guard") if agent else None)
        except subprocess.TimeoutExpired:
            raise CallError(t("no_answer_in_time", seconds=int(timeout))) from None
        except FileNotFoundError:
            raise CallError(t("command_not_found", command=argv[0])) from None
        answer, error = adapter.parse(code, stdout, stderr, out_file)
    answer = (answer or "").strip()
    until = adapter.limit_until(stdout)
    failed = code != 0 or not answer
    # The prompt may be echoed in the error output; its text must not count as a limit message.
    message = (error + "\n" + (stdout if failed and not adapter.stream_json else "")).replace(prompt, "").strip()
    message = "\n".join(message.splitlines()[-20:])
    if until is None and (failed or len(answer) < 300) and is_quota_message(message if failed else answer, failed):
        until = time.time() + quota_wait_seconds(message if failed else answer, default_wait)
    if until is not None and (failed or len(answer) < 300):
        raise UsageLimit(message or "usage limit", until)
    if failed:
        refused = ACCOUNT_REFUSED.search(message)
        if refused:  # retrying cannot help: the account must change
            raise CallError(t("account_refused", name=adapter.id, reason=refused.group(0)))
        raise CallError(message[-500:] or t("empty_answer", code=code))
    return answer, stdout
