"""Gemini CLI: shown as "API key, billed" (the user's decision: personal Google accounts lost the free Gemini CLI
sign-in in 2026; the free Google path is Antigravity CLI). It is never chosen by `auto`."""

from __future__ import annotations

from pathlib import Path

from .base import Adapter


class Gemini(Adapter):
    id, name, vendor, tool, program = "gemini", "Gemini CLI", "Google", "gemini", "gemini"
    billing = "api_key"
    keys = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    context = 1_000_000

    def argv(self, model: str, effort: str, out_file: Path) -> list[str]:
        argv = [self.program, "-p", "Follow the instructions given above exactly.", "-o", "json", "--skip-trust"]
        return argv + (["--model", model] if model else [])

    def parse(self, code: int, stdout: str, stderr: str, out_file: Path) -> tuple[str, str]:
        from pipeline.providers import parse_json
        try:
            data = parse_json(stdout)
        except ValueError:
            return "", (stderr + "\n" + stdout[-1000:]).strip()
        value = data.get("response")
        if code != 0 or data.get("error") or not isinstance(value, str):
            return "", (stderr + "\n" + str(data.get("error") or "")).strip()
        return value, stderr

    def login(self) -> dict:
        return {**super().login(), "billing": "api_key"}
