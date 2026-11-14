"""Shared helpers of the Mehteran tests: a temporary data folder (MEHTERAN_HOME), a fake AI tool, small workflows.

Nothing here calls a real model or the network, and the user's real data folder is never touched.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mehteran import i18n  # noqa: E402
from mehteran.engine import Engine  # noqa: E402

FAKE = [sys.executable, str(ROOT / "tests" / "mehteran_fake_llm.py")]


def fake_cfg() -> dict:
    spec = {"command": FAKE, "models": ["small", "large"], "effort": ["--effort", "{effort}"], "efforts": ["low", "high"]}
    return {"providers": {"fake": spec, "claude": {"command": FAKE}, "chatgpt": {"command": FAKE}},
            "general": {"timeout": 60, "retries": 1, "quota_wait_minutes": 1, "quota_max_hours": 1}}


def fake_config_toml(path: Path) -> Path:
    """The same fake tools as a TOML file, for a separate process (MEHTERAN_CONFIG)."""
    command = json.dumps(FAKE)
    path.write_text(f"[general]\ntimeout = 60\nretries = 1\n\n[providers.fake]\ncommand = {command}\n\n"
                    f"[providers.claude]\ncommand = {command}\n\n[providers.chatgpt]\ncommand = {command}\n",
                    encoding="utf-8")
    return path


class HomeCase(unittest.TestCase):
    """Each test gets its own data folder in MEHTERAN_HOME and its own fake tool log."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mehteran-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.log = self.tmp / "calls.log"
        self.prompts = self.tmp / "prompts"
        env = mock.patch.dict(os.environ, {"MEHTERAN_HOME": str(self.home), "MEHTERAN_FAKE_LOG": str(self.log),
                                           "MEHTERAN_FAKE_PROMPTS": str(self.prompts)})
        env.start()
        self.addCleanup(env.stop)
        i18n.set_default("en")
        self.addCleanup(i18n.set_default, "tr")

    def engine(self, **kwargs) -> Engine:
        kwargs.setdefault("retry_delay", 0)
        return Engine(self.home, fake_cfg(), **kwargs)

    def calls(self) -> list[tuple[str, float, float]]:
        if not self.log.exists():
            return []
        out = []
        for line in self.log.read_text(encoding="utf-8").splitlines():
            tag, start, end = line.split()
            out.append((tag, float(start), float(end)))
        return out

    def tags(self) -> list[str]:
        return [c[0] for c in self.calls()]

    def prompt_of(self, tag: str, n: int = 0) -> str:
        return (self.prompts / f"{tag}.{n}.txt").read_text(encoding="utf-8")

    def doc(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def wait_for(self, condition, timeout: float = 20.0):
        end = time.time() + timeout
        while time.time() < end:
            value = condition()
            if value:
                return value
            time.sleep(0.05)
        self.fail("condition not reached in time")


def ai(node_id: str, prompt: str, provider: str = "fake", **extra) -> str:
    """One ai.cli node in YAML flow style."""
    more = "".join(f", {k}: {v}" for k, v in extra.items())
    return f"  - {{id: {node_id}, type: ai.cli{more}, config: {{provider: {provider}, prompt: {json.dumps(prompt)}}}}}\n"


def workflow(nodes: str, connections: list[tuple[str, str]], inputs: str = "", head: str = "") -> str:
    text = "schema_version: 1\nid: test-flow\nname: Test flow\n" + head
    if inputs:
        text += "inputs:\n" + inputs
    text += "nodes:\n" + nodes
    if connections:
        text += "connections:\n" + "".join(f"  - {{from: {a}, to: {b}}}\n" for a, b in connections)
    return text
