"""Fake LLM for the tests: reads the prompt on stdin and writes an answer in the format the stage expects."""

import json
import os
import re
import sys

prompt = sys.stdin.read()
if os.environ.get("FAKE_LLM_ARGS_LOG"):  # records the --model argument of each call
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "-"
    with open(os.environ["FAKE_LLM_ARGS_LOG"], "a", encoding="utf-8") as log:
        log.write(model + "\n")
# FAKE_LLM_QUOTA_ONCE=<file>: the first call reports a usage limit (and creates the file), later calls answer.
quota_flag = os.environ.get("FAKE_LLM_QUOTA_ONCE")
if quota_flag and not os.path.exists(quota_flag):
    open(quota_flag, "w").close()
    with open(os.environ["FAKE_LLM_LOG"], "a", encoding="utf-8") as log:
        log.write("quota\n")
    print("ERROR: You've hit your usage limit. Try again in 1s.", file=sys.stderr)
    sys.exit(1)
if os.environ.get("FAKE_LLM_REFUSED"):  # the service refuses the account, as Gemini does for personal Google accounts
    with open(os.environ["FAKE_LLM_LOG"], "a", encoding="utf-8") as log:
        log.write("refused\n")
    print("Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code Assist "
          "for individuals.\n    at throwIneligibleOrProjectIdError (file:///x.js:1:1)", file=sys.stderr)
    sys.exit(1)
if os.environ.get("FAKE_LLM_DELAY"):
    import time
    time.sleep(float(os.environ["FAKE_LLM_DELAY"]))


def between(tag: str) -> str:
    start = prompt.rfind(f"<{tag}>\n") + len(tag) + 3
    return prompt[start:prompt.rfind(f"\n</{tag}>")]


def marked(tag: str, mark: str) -> str:
    return "\n\n".join(block + mark for block in between(tag).strip().split("\n\n"))


def once(variable: str) -> bool:
    """True the first time for the flag file named in the environment variable."""
    flag = os.environ.get(variable)
    if not flag or os.path.exists(flag):
        return False
    open(flag, "w").close()
    return True


# The note language that the pipeline asked for ("Turkish" or "English").
note_lang = "English" if "in English" in prompt else "Turkish"
note = "Missing sentence." if note_lang == "English" else "Cümle atlanmış."

if "<window>" in prompt:
    kind = "align"
    numbers = [int(n) for n in re.findall(r"^\[(\d+)\] ", between("window"), re.M)]
    reply = json.dumps({"start": numbers[0], "end": numbers[0]})
elif "<changes>" in prompt:
    kind = "source_check"
    changes = {"issues": [{
        "type": "omission", "severity": "critical", "source": "terk etmez", "translation": "",
        "explanation": note, "suggestion": "added",
    }]}
    reply = f"<translation>\n{marked('current_translation', '+k')}\n</translation>\n<changes>\n{json.dumps(changes)}\n</changes>"
elif "<issues>" in prompt:
    kind = "revise"
    ids = [issue["id"] for issue in json.loads(between("issues"))]
    decisions = [{"id": i, "decision": "accepted" if n == 0 else "rejected", "reason": "reason"} for n, i in enumerate(ids)]
    if once("FAKE_LLM_UNDECIDED_ONCE"):  # the first revision leaves a finding without a decision
        decisions, kind = decisions[1:], "revise-undecided"
    reply = (f"<translation>\n{marked('current_translation', '+u')}\n</translation>\n"
             f"<decisions>\n{json.dumps({'decisions': decisions})}\n</decisions>")
elif '"issues"' in prompt:
    kind = "review"
    # The reading proof: the last three words of each translation paragraph.
    checked = [" ".join(block.split()[-3:]) for block in between("translation").strip().split("\n\n")]
    issues = [{
        "type": "terminology", "severity": "major", "source": "namaz", "translation": "bønn",
        "explanation": "Glossary term not used.", "suggestion": "namaz",
    }]
    if "--silent" in sys.argv:  # this reviewer never reports anything
        issues = []
    if once("FAKE_LLM_NO_PROOF_ONCE"):  # the first review comes without the reading proof
        checked, kind = [], "review-noproof"
    reply = "```json\n" + json.dumps({"checked": checked, "issues": issues}) + "\n```"
elif '"terms"' in prompt:
    kind = "glossary"
    reply = json.dumps({"terms": [{"tr": "namaz", "target": "namaz", "note": f"note in {note_lang}"}]})
else:
    kind = "translate"
    reply = marked("source", " (no)")
    # FAKE_LLM_TRUNCATE=<file>:<n>: the first n translations lose their last paragraph.
    if os.environ.get("FAKE_LLM_TRUNCATE"):
        path, limit = os.environ["FAKE_LLM_TRUNCATE"].rsplit(":", 1)
        count = int(open(path).read()) if os.path.exists(path) else 0
        if count < int(limit):
            open(path, "w").write(str(count + 1))
            reply = "\n\n".join(reply.split("\n\n")[:-1])
            kind = "translate-truncated"

with open(os.environ["FAKE_LLM_LOG"], "a", encoding="utf-8") as log:
    log.write(kind + "\n")
print(reply)
