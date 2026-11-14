"""Fake Claude Code for the adapter tests: `claude -p ... --output-format stream-json` without any network call.

It runs the fake AI tool (mehteran_fake_llm.py, the same prompt markers) and prints what it prints as Claude Code's
stream-json events, line by line as they come: an "assistant" event per line, a "rate_limit_event", then the
"result". A usage limit of the fake tool (QUOTA=) becomes a rejected rate_limit_event and a failed result.
Environment: MEHTERAN_FAKE_ARGV, a file: the arguments of each call, one JSON list per line.
Prompt marker ENVCHECK: the answer names the API key variables that the call's environment has.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

prompt = sys.stdin.read()
args = sys.argv[1:]
if os.environ.get("MEHTERAN_FAKE_ARGV"):
    with open(os.environ["MEHTERAN_FAKE_ARGV"], "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\n")


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


emit({"type": "system", "subtype": "init", "tools": [], "model": "fake"})
if "ENVCHECK" in prompt:
    keys = [k for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                        "GOOGLE_API_KEY") if k in os.environ]
    answer = "keys: " + (",".join(keys) or "none")
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": answer}]}})
    emit({"type": "result", "subtype": "success", "is_error": False, "result": answer})
    sys.exit(0)
model = args[args.index("--model") + 1] if "--model" in args else None
fake = [sys.executable, str(Path(__file__).with_name("mehteran_fake_llm.py"))] + (["--model", model] if model else [])
proc = subprocess.Popen(fake, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        encoding="utf-8")
proc.stdin.write(prompt)
proc.stdin.close()
lines = []
for line in proc.stdout:
    lines.append(line)
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": line}]}})
error = proc.stderr.read()
code = proc.wait()
if code == 0:
    emit({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "resetsAt": int(time.time()) + 3600,
                                                          "rateLimitType": "five_hour"}})
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "".join(lines)})
    sys.exit(0)
if "usage limit" in error:
    emit({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": int(time.time()) + 90,
                                                          "rateLimitType": "five_hour"}})
emit({"type": "result", "subtype": "error_during_execution", "is_error": True, "result": error.strip()})
sys.exit(1)
