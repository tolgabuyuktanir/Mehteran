"""The live log of a node: executions/<run>/nodes/<node>/log.txt, written while the node works and read in pieces by
the interface (offset in bytes, like `tail -f`).

Lines come from the engine (attempts, waits, heartbeats, model switches), from the worker (the model call; Ollama's
answer as it streams) and from loops (each part). Obvious secrets are masked before anything is written, and the file
stops growing at LIMIT bytes (a last line says so).
"""

from __future__ import annotations

import re
import time
from pathlib import Path

LIMIT = 2 * 1024 * 1024
READ_LIMIT = 64 * 1024
NAME = "log.txt"
SECRET = re.compile(r"\b(sk-(?:ant-)?[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
                    r"xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})|(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}", re.I)
CUT_NOTE = "\n[log cut: the log reached its size limit]\n"


def redact(text: str) -> str:
    return SECRET.sub(lambda m: (m.group(2) or "") + "[hidden]", text)


def append(path: Path, text: str, stamp: bool = False) -> None:
    """Adds text (with the time in front when stamp is set). Never raises: a log must not stop a node."""
    try:
        size = path.stat().st_size if path.exists() else 0
        if size >= LIMIT:
            return
        if stamp:
            text = time.strftime("[%H:%M:%S] ") + text + "\n"
        data = redact(text).encode("utf-8")
        if size + len(data) > LIMIT:
            data = data[:max(0, LIMIT - size - len(CUT_NOTE))] + CUT_NOTE.encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(data)
    except OSError:
        pass


def read(path: Path, offset: int = 0) -> tuple[str, int]:
    """(text from offset, the next offset), at most READ_LIMIT bytes, never cutting a UTF-8 character in two."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, offset))
            data = f.read(READ_LIMIT)
    except OSError:
        return "", max(0, offset)
    for cut in range(4):  # an incomplete character at the end waits for the next read
        try:
            text = data[:len(data) - cut].decode("utf-8")
            return text, max(0, offset) + len(data) - cut
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace"), max(0, offset) + len(data)
