"""Fake AI tool for the drafting tests: answers with prepared texts, in order, without any network call.

Environment:
  MEHTERAN_FAKE_DRAFTS       a folder with the answers 1.txt, 2.txt, ... (the n-th call prints the n-th file; a call
                             without a file fails); each prompt is saved there as prompt-<n>.txt
  MEHTERAN_FAKE_DRAFT_SLEEP  seconds to wait before answering
"""

import os
import sys
import time

folder = os.environ["MEHTERAN_FAKE_DRAFTS"]
prompt = sys.stdin.read()
n = len([f for f in os.listdir(folder) if f.startswith("prompt-")]) + 1
with open(os.path.join(folder, f"prompt-{n}.txt"), "w", encoding="utf-8") as f:
    f.write(prompt)
time.sleep(float(os.environ.get("MEHTERAN_FAKE_DRAFT_SLEEP") or 0))
answer = os.path.join(folder, f"{n}.txt")
if not os.path.exists(answer):
    print(f"no prepared answer {n}", file=sys.stderr)
    sys.exit(1)
with open(answer, encoding="utf-8") as f:
    sys.stdout.write(f.read())
