"""Antigravity CLI (agy): a personal Google account (Gemini models, free with limits).

Flags: stream-json in and out, --disable-slash-commands. Not added: --sandbox and
--mode plan (both in `agy --help`): checking that they leave a plain text answer unchanged needs a real model call,
and plan mode may answer with a plan instead of the text asked for. The call runs in an empty folder with no tools
asked for."""

from __future__ import annotations

import json
from pathlib import Path

from .base import Adapter


class Antigravity(Adapter):
    id, name, vendor, tool, program = "antigravity", "Antigravity CLI (Gemini)", "Google", "antigravity", "agy"
    billing = "free"
    keys = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    efforts = ("low", "medium", "high")
    context = 1_000_000
    concurrency = 1
    stream_json = True

    def argv(self, model: str, effort: str, out_file: Path) -> list[str]:
        argv = [self.program, "--input-format", "stream-json", "--output-format", "stream-json", "--disable-slash-commands"]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        return argv

    def stdin(self, prompt: str) -> str:
        return json.dumps({"event": "user", "message": {"content": prompt}}, ensure_ascii=False) + "\n"

    def parse(self, code: int, stdout: str, stderr: str, out_file: Path) -> tuple[str, str]:
        from ..common.calls import stream_json_answer  # also deletes the conversation the call stored
        answer, error = stream_json_answer(stdout)
        return answer, (stderr + "\n" + error).strip()
