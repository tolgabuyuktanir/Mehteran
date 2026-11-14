"""What a command-line AI tool prints while it works, as readable text in the node's live log (mehteran/worker.py).

The adapter's call (mehteran/providers/base.py run) gives each line of the tool's stdout as it arrives. A tool that
prints stream-json (Claude Code, Antigravity CLI: the adapter's stream_json) prints JSON events: only their text is shown, and a tool use as a short line
("· tool: Read"). Any other tool's lines are shown as they are. The answer that the call returns does not change.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from mehteran import livelog

FLUSH_AT = 200  # characters without a line end that are written before the line ends
_SPACE = re.compile(r"\s+")


def uses_stream_json(command: list) -> bool:
    """True when the command asks the tool for stream-json output (--output-format stream-json)."""
    return any(a == "--output-format" and b == "stream-json" for a, b in zip(command, command[1:]))


class EventText:
    """The readable text of stream-json events, one line at a time.

    Claude Code: the text of assistant messages ("assistant" events; with --include-partial-messages the text
    deltas of "stream_event" events instead), tool uses, and the error of a failed "result".
    Antigravity CLI: the text deltas of "step_update" events and the error of a failed "result"."""

    def __init__(self) -> None:
        self.partial = False  # text deltas were seen: the whole messages repeat them

    def feed(self, line: str) -> str:
        try:
            event = json.loads(line)
        except ValueError:
            return line if line.strip() else ""
        if not isinstance(event, dict):
            return ""
        kind = event.get("type")
        if kind == "stream_event":
            return self._partial(event.get("event") or {})
        if kind == "assistant" and not self.partial:
            return "".join(self._block(block) for block in (event.get("message") or {}).get("content") or []
                           if isinstance(block, dict))
        if kind == "result" and event.get("is_error"):
            return f"\n· {event.get('result') or event.get('subtype') or 'error'}\n"
        if event.get("event") == "step_update":
            delta = (event.get("step_update") or {}).get("text_delta")
            return delta if isinstance(delta, str) else ""
        if event.get("event") == "result":
            result = event.get("result") if isinstance(event.get("result"), dict) else {}
            if result.get("status") != "SUCCESS" or result.get("error"):
                return f"\n· {result.get('error') or result.get('status') or 'error'}\n"
        return ""

    def _partial(self, event: dict) -> str:
        if event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta" and isinstance(delta.get("text"), str):
                self.partial = True
                return delta["text"]
        if event.get("type") == "content_block_start":
            block = event.get("content_block") or {}
            if block.get("type") == "tool_use":
                self.partial = True
                return self._block(block)
        return ""

    @staticmethod
    def _block(block: dict) -> str:
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            return block["text"]
        if block.get("type") == "tool_use":
            return f"\n· tool: {block.get('name') or '?'}\n"
        return ""


class LiveOutput:
    """Writes the tool's output to the live log as it arrives (feed is the on_output of providers.base.run).

    Text is written by whole lines, so that livelog.redact sees a secret whole; a long line without a line end is
    written up to its last word but one. prefix (e.g. "part 3: ") goes in front of each line, and then only whole
    lines are written: the parts of a loop share one log."""

    def __init__(self, log: Path, command: list, prefix: str = "", stream_json: bool | None = None) -> None:
        self.log, self.prefix = log, prefix
        stream_json = uses_stream_json(command) if stream_json is None else stream_json
        self.events = EventText() if stream_json else None
        self.pending = ""
        self.shown: list[str] = []

    def feed(self, line: str) -> None:
        text = self.events.feed(line) if self.events else line
        if not text:
            return
        self.shown.append(text)
        self.pending += text
        end = self.pending.rfind("\n") + 1
        if not end and not self.prefix and len(self.pending) > FLUSH_AT:
            words = [m.start() for m in _SPACE.finditer(self.pending)]
            end = words[-2] if len(words) > 1 else 0
        if end:
            self._write(self.pending[:end])
            self.pending = self.pending[end:]

    def close(self) -> str:
        """Writes what is left and returns all the text shown."""
        if self.pending:
            self._write(self.pending + "\n")
            self.pending = ""
        return "".join(self.shown)

    def _write(self, text: str) -> None:
        if self.prefix:
            text = "".join(self.prefix + line for line in text.splitlines(True))
        livelog.append(self.log, text)


def same_text(shown: str, answer: str) -> bool:
    """True when the shown text ends with the answer (spaces and line ends aside): the log has the answer already."""
    answer = " ".join(answer.split())
    return bool(answer) and " ".join(shown.split()).endswith(answer)
