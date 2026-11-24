"""The evaluation set: built-in templates run with real models on fixed inputs, and their results checked by rules.

    ./mehter eval [--model claude/haiku] [--case summary-tr ...] [--out folder]
    ./mehter eval --compare before.json after.json

The cases are in evals/cases.json (next to this code folder), each with its template, its inputs and its checks:
- language: "tr" or "en": the result must be in that language (counted from common words and Turkish letters),
- any_of: [[a, b], ...]: each group needs one of its texts in the result (case and accents ignored),
- not_contains / not_regex: texts or patterns that must not appear (an invented fact, an instruction hidden in the
  document),
- min_chars / max_chars: the length of the result.
The result is the Markdown of the workflow's export step (else the text of its last model step). An approval step is
approved without a comment. The runs use a temporary data folder with a copy of the Setup tab's settings, so the run
history stays clean. Every run makes real model calls with the tools of the Setup tab: it uses their usage limits.

A report (JSON) is written to the output folder; --compare shows what changed between two reports, for example
before and after a change of the instructions. The checks are rules, not a judge: a passed case can still read badly.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
from pathlib import Path

from . import paths, templates

CASES = paths.REPO / "evals" / "cases.json"
TR_WORDS = {"ve", "bir", "bu", "için", "ile", "olarak", "da", "de", "çok", "daha", "ancak", "değil", "olan", "gibi"}
EN_WORDS = {"the", "and", "of", "to", "is", "for", "with", "that", "this", "are", "not", "be", "on", "it"}


def fold(text: str) -> str:
    """Lower case without accents (Turkish dotted and dotless i included), for the text checks."""
    text = text.replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def language_of(text: str) -> str:
    words = re.findall(r"[^\W\d_]+", text.lower())
    tr = sum(w in TR_WORDS for w in words) + len(re.findall(r"[çğışöü]", text.lower())) / 4
    en = sum(w in EN_WORDS for w in words)
    return "tr" if tr > en else "en"


def check(text: str, rules: dict) -> list[str]:
    """The failed checks of a result, as short sentences (empty: every check passed)."""
    failed, folded = [], fold(text)
    if rules.get("language") and language_of(text) != rules["language"]:
        failed.append(f"language is {language_of(text)}, not {rules['language']}")
    for group in rules.get("any_of", []):
        if not any(fold(option) in folded for option in group):
            failed.append("missing: " + " / ".join(group))
    for bad in rules.get("not_contains", []):
        if fold(bad) in folded:
            failed.append(f"must not contain: {bad}")
    for pattern in rules.get("not_regex", []):
        if re.search(pattern, folded):
            failed.append(f"must not match: {pattern}")
    if rules.get("min_chars") and len(text) < rules["min_chars"]:
        failed.append(f"too short: {len(text)} < {rules['min_chars']} characters")
    if rules.get("max_chars") and len(text) > rules["max_chars"]:
        failed.append(f"too long: {len(text)} > {rules['max_chars']} characters")
    return failed


def result_text(engine, run_id: str) -> str:
    """The Markdown of the export step, else the text of the last model step that finished."""
    run = engine.get(run_id)
    folder = engine.run_dir(run_id)
    outputs = [info.get("outputs") or {} for info in run["nodes"].values() if info["status"] == "succeeded"]
    for found in outputs:
        if found.get("md"):
            return (folder / found["md"]).read_text(encoding="utf-8")
    texts = [found["text"] for found in outputs if found.get("text")]
    return (folder / texts[-1]).read_text(encoding="utf-8") if texts else ""


def run_case(engine, case: dict, model: str, timeout: float) -> dict:
    base = CASES.parent
    values = {key: str(value) for key, value in (case.get("values") or {}).items()}
    for key, rel in (case.get("texts") or {}).items():
        values[key] = (base / rel).read_text(encoding="utf-8")
    files = {key: [base / p for p in rel] if isinstance(rel, list) else base / rel for key, rel in (case.get("files") or {}).items()}
    started = time.time()
    run_id = engine.start(templates.read("builtin", case["template"], engine.home), values, files,
                          template=f"builtin:{case['template']}", every_step=model)
    status = ""
    while time.time() - started < timeout:
        status = engine.wait(run_id, max(1.0, timeout - (time.time() - started)))
        if status != "waiting_approval":
            break
        for node_id, info in engine.get(run_id)["nodes"].items():
            if info["status"] == "waiting_approval":
                engine.decide(run_id, node_id, True, "")
    if status not in ("succeeded", "failed", "cancelled", "interrupted"):
        engine.cancel(run_id)
        status = "timeout"
    text = result_text(engine, run_id) if status == "succeeded" else ""
    errors = [f"{node_id}: {info.get('error_summary') or info.get('error')}" for node_id, info in engine.get(run_id)["nodes"].items()
              if info["status"] == "failed"]
    failed = check(text, case.get("checks") or {}) if status == "succeeded" else [f"run {status}", *errors]
    total = len(case.get("checks", {}).get("any_of", [])) + len(case.get("checks", {}).get("not_contains", [])) + \
        len(case.get("checks", {}).get("not_regex", [])) + sum(1 for k in ("language", "min_chars", "max_chars")
                                                                if case.get("checks", {}).get(k))
    return {"id": case["id"], "template": case["template"], "status": status, "passed": not failed, "failed": failed,
            "checks": total, "seconds": round(time.time() - started, 1), "chars": len(text), "result": text}


def run(model: str = "", only: list[str] | None = None, out: Path | None = None, timeout: float = 1800,
        say=print, provider_cfg: dict | None = None) -> dict:
    """Runs the cases; model: one model for every step of every case ("" = the templates' own models)."""
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    if only:
        unknown = sorted(set(only) - {c["id"] for c in cases})
        if unknown:
            raise ValueError("unknown case: " + ", ".join(unknown))
        cases = [c for c in cases if c["id"] in only]
    real = paths.home()
    with tempfile.TemporaryDirectory(prefix="mehteran-eval-") as tmp:
        if (real / "configurations").is_dir():  # the Setup tab's settings: the model order, "API key (billed)"
            shutil.copytree(real / "configurations", Path(tmp) / "configurations", dirs_exist_ok=True)
        before = os.environ.get("MEHTERAN_HOME")
        os.environ["MEHTERAN_HOME"] = tmp
        try:
            from .engine import Engine
            engine = Engine(Path(tmp), provider_cfg)
            results = []
            for case in cases:
                say(f"… {case['id']} ({case['template']})")
                found = run_case(engine, case, model, timeout)
                say(f"{'✓' if found['passed'] else '✗'} {case['id']}: {found['seconds']} s"
                    + "".join(f"\n    - {f}" for f in found["failed"]))
                results.append(found)
        finally:
            if before is None:
                os.environ.pop("MEHTERAN_HOME", None)
            else:
                os.environ["MEHTERAN_HOME"] = before
    report = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model or "(template defaults)",
              "passed": sum(r["passed"] for r in results), "cases": len(results), "results": results}
    folder = Path(out) if out else paths.home() / "evals"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"report-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    report["path"] = str(path)
    say(f"{report['passed']}/{report['cases']} cases passed · {path}")
    return report


def compare(before: dict, after: dict) -> list[str]:
    """One line per case whose outcome or failed checks changed."""
    old = {r["id"]: r for r in before["results"]}
    lines = []
    for new in after["results"]:
        prev = old.get(new["id"])
        if prev is None:
            lines.append(f"+ {new['id']}: {'passed' if new['passed'] else 'failed'} (new case)")
        elif prev["passed"] != new["passed"] or prev["failed"] != new["failed"]:
            mark = "↑" if new["passed"] and not prev["passed"] else "↓" if prev["passed"] and not new["passed"] else "~"
            lines.append(f"{mark} {new['id']}: {len(prev['failed'])} → {len(new['failed'])} failed checks"
                         + "".join(f"\n    - {f}" for f in new["failed"]))
    return lines or ["no change"]
