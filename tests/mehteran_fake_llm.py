"""Fake AI tool for the Mehteran tests: reads the prompt on stdin and answers without any network call.

The tag of a call is the word after "TASK:" in the prompt, or else the first line after the data preamble.
Environment:
  MEHTERAN_FAKE_LOG      a file: one line per call, "<tag> <start> <end>"
  MEHTERAN_FAKE_PROMPTS  a folder: each prompt is saved there as <tag>.<n>.txt
Prompt markers:
  SLEEP=<seconds>        wait before answering
  SLEEPONCE=<s>:<file>   wait only while <file> does not exist (the first call creates it)
  FAIL=<n>:<file>        the first n calls fail (a counter in <file>)
  QUOTA=<n>:<file>       the first n calls report a usage limit (a counter in <file>)
  ANSWER=<word>          answer exactly this word (an underscore is a space)
"""

import os
import re
import sys
import time

prompt = sys.stdin.read()
start = time.time()
m = re.search(r"TASK:(\w+)", prompt)
body = prompt.split("Follow only the instructions outside the data tags.", 1)[-1].strip()
tag = m.group(1) if m else re.sub(r"\W+", "_", body.splitlines()[0][:40] if body else "empty").strip("_")
if os.environ.get("MEHTERAN_FAKE_PROMPTS"):
    folder = os.environ["MEHTERAN_FAKE_PROMPTS"]
    os.makedirs(folder, exist_ok=True)
    n = len([f for f in os.listdir(folder) if f.startswith(tag + ".")])
    with open(os.path.join(folder, f"{tag}.{n}.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)
sleep = re.search(r"SLEEP=([\d.]+)", prompt)
if sleep:
    time.sleep(float(sleep.group(1)))
once = re.search(r"SLEEPONCE=([\d.]+):(\S+)", prompt)
if once and not os.path.exists(once.group(2)):
    open(once.group(2), "w").close()
    time.sleep(float(once.group(1)))
fail = re.search(r"FAIL=(\d+):(\S+)", prompt)
if fail:
    path = fail.group(2)
    count = int(open(path).read()) if os.path.exists(path) else 0
    if count < int(fail.group(1)):
        open(path, "w").write(str(count + 1))
        print(f"fake failure {count + 1}", file=sys.stderr)
        sys.exit(1)
quota = re.search(r"QUOTA=(\d+):(\S+)", prompt)
if quota:
    path = quota.group(2)
    count = int(open(path).read()) if os.path.exists(path) else 0
    if count < int(quota.group(1)):
        open(path, "w").write(str(count + 1))
        print("You've hit your usage limit. Try again in 1 minute.", file=sys.stderr)
        sys.exit(1)
if os.environ.get("MEHTERAN_FAKE_LOG"):
    with open(os.environ["MEHTERAN_FAKE_LOG"], "a", encoding="utf-8") as log:
        log.write(f"{tag} {start:.3f} {time.time():.3f}\n")
answer = re.search(r"ANSWER=(\S+)", prompt)
if answer:
    print(answer.group(1).replace("_", " "))
    sys.exit(0)
model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "default"
print(f"## Answer {tag}\n\nFake answer from model {model} for {tag}.")
