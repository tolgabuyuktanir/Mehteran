"""Codex CLI (codex exec): the user's ChatGPT plan.

Flags (from the Codex CLI reference, developers.openai.com/codex/cli/reference; Codex is not installed on the
computer where this was written): --sandbox read-only, --ephemeral (no session files), --ignore-user-config (no
$CODEX_HOME/config.toml: no MCP servers or profiles of the user), --skip-git-repo-check, --color never, -o <file>
(the last message). The prompt goes on stdin."""

from __future__ import annotations

from pathlib import Path

from .base import Adapter


class Codex(Adapter):
    id, name, vendor, tool, program = "codex", "Codex CLI (ChatGPT)", "OpenAI", "codex", "codex"
    keys = ("CODEX_API_KEY", "OPENAI_API_KEY")
    efforts = ("low", "medium", "high", "xhigh")
    fast_model, strong_model = "", ""

    def argv(self, model: str, effort: str, out_file: Path) -> list[str]:
        argv = [self.program, "exec", "--sandbox", "read-only", "--ephemeral", "--ignore-user-config",
                "--skip-git-repo-check", "--color", "never", "-o", str(out_file)]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["-c", f"model_reasoning_effort={effort}"]
        return argv

    def login(self) -> dict:
        """`codex login status` names the mode: "Logged in using ChatGPT" or "... using an API key"."""
        out = super().login()
        if "api key" in str(out.get("info") or "").lower():
            out["billing"] = "api_key"
        return out
