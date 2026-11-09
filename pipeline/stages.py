"""Pipeline stages. Each stage writes one file per segment; an existing file is not produced again."""

from __future__ import annotations

import bisect
import hashlib
import itertools
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from . import checks
from .core import PipelineError, Project, read_json, say, slug, write_json, write_text
from .documents import SUPPORTED, read_blocks, segment, split_long
from .i18n import note_language, t
from .providers import ask, parse_json
from .runstatus import STATUS

# Workflow: 1 first translation → 2 review → 3 apply the review → 4 source check from the start →
# 5 second independent review (in parallel) → 6 reconcile the two reviews → 7 human translator and editor.
STAGES = ["prepare", "align", "glossary", "translate", "review1", "revise1", "source_check",
          "review2", "reconcile", "assemble"]
LLM_STAGES = STAGES[1:-1]
REVIEW_STAGES = ("review1", "review2")  # one report file per reviewer
FINAL = "reconcile"  # the stage that holds the final text
ISSUE_FOLDERS = ["revise1", "source_check", "reconcile"]  # where findings and decisions are recorded
REF_PARAGRAPH_LIMIT = 2000  # alignment works with numbered reference paragraphs
SEVERITIES = ("critical", "major", "minor")
ISSUE_TYPES = ("omission", "addition", "mistranslation", "terminology", "religious", "names", "format", "language")
SHARED_WORK_FOLDERS = {"segments", "references", "alignment"}  # the other folders under work/ are languages


@dataclass
class Run:
    proj: Project
    book: str
    target: str
    refs: list[str]
    ids: list[str]       # all segments of the book
    selected: list[str]  # the segments this run processes
    workers: int
    _paras: dict = field(default_factory=dict)

    @property
    def work(self) -> Path:
        return self.proj.book_dir(self.book) / "work"

    @property
    def lang_dir(self) -> Path:
        return self.work / self.target

    @property
    def glossary_path(self) -> Path:
        return self.proj.root / "glossary" / f"{self.target}.tsv"

    def seg(self, sid: str) -> str:
        return (self.work / "segments" / f"{sid}.md").read_text(encoding="utf-8")

    def ref_paras(self, ref: str) -> list[str]:
        if ref not in self._paras:
            text = (self.work / "references" / f"{ref}.md").read_text(encoding="utf-8")
            self._paras[ref] = text.split("\n\n")
        return self._paras[ref]

    def references_block(self, sid: str) -> str:
        parts = []
        for ref in self.refs:
            span = read_json(self.work / "alignment" / f"{ref}.json", {}).get(sid)
            if span:
                passage = "\n\n".join(self.ref_paras(ref)[span[0]:span[1] + 1])
                parts.append(f'<reference language="{self.proj.language_name(ref)}">\n{passage}\n</reference>')
        return "\n\n".join(parts) or "(No reference passage is available for this segment.)"

    def pending(self, folder: str, suffix: str = ".md") -> list[str]:
        return [sid for sid in self.selected if not (self.lang_dir / folder / f"{sid}{suffix}").exists()]


def parallel(label: str, tasks: list[tuple[str, object]], fn, workers: int, units: int | None = None) -> None:
    """tasks: a list of (name, argument). Errors are collected; finished work stays on disk.

    units: when one task covers several segments (alignment: one task per reference), the progress total;
    the task then reports each finished segment itself with STATUS.task_done.
    """
    if not tasks:
        say(f"[{label}] {t('nothing_to_do')}")
        return
    STATUS.stage(label, units if units is not None else len(tasks))

    def task(arg):
        STATUS.set_thread_stage(label)
        return fn(arg)

    failed = []
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(task, arg): name for name, arg in tasks}
    try:
        for n, future in enumerate(as_completed(futures), 1):
            name = futures[future]
            try:
                future.result()
                if units is None:
                    STATUS.task_done(label, name)
                say(f"[{label}] {n}/{len(tasks)}  {name}")
            except Exception as e:  # thread boundary: one failed segment does not stop the others
                failed.append(name)
                STATUS.task_done(label, name, str(e))
                say(f"[{label}] {n}/{len(tasks)}  {name}  {t('error')}: {e}")
    except KeyboardInterrupt:
        # Ctrl+C or a stop from the web interface: start no new calls; running ones end at their next check.
        STATUS.stopping = True
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    pool.shutdown(wait=True)
    if failed:
        raise PipelineError(t("stage_failed", stage=label, count=len(failed), names=", ".join(sorted(failed))))


# --- segment selection and estimate -----------------------------------------

def select_segments(spec: str, ids: list[str]) -> list[str]:
    """Turns '3', '1-5' or '1-5,9' into segment ids."""
    chosen = set()
    try:
        for part in spec.split(","):
            first, _, last = part.partition("-")
            chosen.update(range(int(first), int(last or first) + 1))
    except ValueError:
        raise PipelineError(t("bad_segments", spec=spec)) from None
    selected = [sid for sid in ids if int(sid) in chosen]
    if not selected:
        raise PipelineError(t("no_such_segments", spec=spec, total=len(ids)))
    return selected


# Rough duration of one call, in seconds, used until the run has measured its own speed.
DEFAULT_CALL_SECONDS = {"align": 25, "glossary": 40, "translate": 120, "review1": 60, "revise1": 120,
                        "source_check": 150, "review2": 60, "reconcile": 120}


def estimate(proj: Project, book: str, target: str, refs: list[str], segments: str = "",
             durations: dict | None = None) -> dict:
    """Counts the model calls that a run still needs, per provider, and estimates the time.

    Finished work is not counted. Before the book is prepared, the number of segments is estimated from the source.
    durations: measured {stage: [calls, seconds]} of the current run; they replace the default call durations.
    """
    book_dir = proj.book_dir(book)
    work = book_dir / "work"
    total = read_json(work / "prep.json", {}).get("source", {}).get("segments", 0)
    prepared = bool(total)
    if not prepared:
        sources = [f for f in sorted((book_dir / "source").glob("*")) if f.suffix.lower() in SUPPORTED]
        chars = sum(len(b) for b in read_blocks(sources[0])) if len(sources) == 1 else 0
        total = max(1, round(chars / proj.cfg["general"]["segment_size"] * 1.1)) if chars else 0
    ids = [f"{i:04d}" for i in range(1, total + 1)]
    selected = select_segments(segments, ids) if segments and ids else ids
    lang_dir = work / target

    calls: dict[str, int] = {}
    per_stage: dict[str, int] = {}
    for stage in LLM_STAGES:
        providers = proj.providers_for(stage)
        if stage == "align":
            for ref in refs:
                done = read_json(work / "alignment" / f"{ref}.json", {})
                n = sum(1 for sid in selected if sid not in done)
                calls[providers[0]] = calls.get(providers[0], 0) + n
                per_stage[stage] = max(per_stage.get(stage, 0), n)  # the references are aligned in parallel
            continue
        for provider in (providers if stage in REVIEW_STAGES else providers[:1]):
            if stage in REVIEW_STAGES:
                n = sum(1 for sid in selected if not (lang_dir / stage / f"{sid}.{slug(provider)}.json").exists())
            else:
                suffix = ".json" if stage == "glossary" else ".md"
                n = sum(1 for sid in selected if not (lang_dir / stage / f"{sid}{suffix}").exists())
            calls[provider] = calls.get(provider, 0) + n
            per_stage[stage] = per_stage.get(stage, 0) + n

    workers = proj.cfg["general"]["parallel"]
    seconds = 0.0
    for stage, n in per_stage.items():
        measured = (durations or {}).get(stage)
        each = measured[1] / measured[0] if measured and measured[0] else DEFAULT_CALL_SECONDS[stage]
        seconds += n * each / (1 if stage == "align" else workers)  # alignment of one reference is sequential
    return {"segments": total, "selected": len(selected), "prepared": prepared, "calls": calls,
            "total_calls": sum(calls.values()), "seconds": round(seconds)}


# --- prepare ----------------------------------------------------------------

def available_refs(book_dir: Path) -> list[str]:
    return sorted({f.stem for f in (book_dir / "references").glob("*") if f.suffix.lower() in SUPPORTED})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(proj: Project, book: str, refs: list[str]) -> list[str]:
    """Converts the source and the references to text and splits the source into segments. Returns segment ids."""
    book_dir = proj.book_dir(book)
    work = book_dir / "work"
    meta_path = work / "prep.json"
    meta = read_json(meta_path, {})
    limit = proj.cfg["general"]["segment_size"]

    sources = [f for f in sorted((book_dir / "source").glob("*")) if f.suffix.lower() in SUPPORTED]
    if len(sources) != 1:
        raise PipelineError(t("need_one_source", folder=book_dir / "source", supported=", ".join(SUPPORTED), found=len(sources)))
    source = sources[0]
    digest = _sha(source)
    if "source" not in meta:
        blocks = split_long(read_blocks(source), limit)
        if not blocks:
            raise PipelineError(t("no_text", name=source.name))
        segments = segment(blocks, limit)
        write_text(work / "source.md", "\n\n".join(blocks) + "\n")
        for i, text in enumerate(segments, 1):
            write_text(work / "segments" / f"{i:04d}.md", text + "\n")
        meta["source"] = {"file": source.name, "sha256": digest, "segments": len(segments)}
        say(f"[prepare] {t('prepared_source', name=source.name, count=len(segments))}")
    elif meta["source"]["sha256"] != digest:
        raise PipelineError(t("source_changed", name=source.name, work=work))

    for ref in refs:
        matches = [f for f in sorted((book_dir / "references").glob(f"{ref}.*")) if f.suffix.lower() in SUPPORTED]
        if len(matches) != 1:
            raise PipelineError(t("need_one_reference", folder=book_dir / "references", ref=ref, found=len(matches)))
        digest = _sha(matches[0])
        known = meta.setdefault("references", {}).get(ref)
        if known is None:
            blocks = split_long(read_blocks(matches[0]), REF_PARAGRAPH_LIMIT)
            if not blocks:
                raise PipelineError(t("no_text", name=matches[0].name))
            write_text(work / "references" / f"{ref}.md", "\n\n".join(blocks) + "\n")
            meta["references"][ref] = digest
            say(f"[prepare] {t('prepared_reference', name=matches[0].name, count=len(blocks))}")
        elif known != digest:
            raise PipelineError(t("reference_changed", name=matches[0].name, ref=ref, work=work, meta=meta_path))

    write_json(meta_path, meta)
    return [f"{i:04d}" for i in range(1, meta["source"]["segments"] + 1)]


# --- align ------------------------------------------------------------------

def align(run: Run) -> None:
    """Finds where each Turkish segment is in the reference translation (a range of paragraphs)."""
    if not run.refs:
        say(f"[align] {t('align_skipped')}")
        return
    provider = run.proj.providers_for("align")[0]
    lengths = {sid: len(run.seg(sid)) for sid in run.ids}
    source_total = sum(lengths.values())

    def one_ref(ref: str) -> None:
        paras = run.ref_paras(ref)
        cumulative = list(itertools.accumulate(len(p) for p in paras))
        ratio = cumulative[-1] / source_total
        path = run.work / "alignment" / f"{ref}.json"
        done = read_json(path, {})

        def attempt(seg: str, start: int, budget: float, expected_size: float):
            end, size = start, 0
            while end < len(paras) and size < budget:
                size += len(paras[end])
                end += 1
            if end == start:
                return None
            window = "\n\n".join(f"[{i + 1}] {paras[i]}" for i in range(start, end))
            prompt = run.proj.prompt("align", ref_lang=run.proj.language_name(ref), segment=seg, window=window)

            def parse(text: str):
                data = parse_json(text)
                first, last = data["start"], data["end"]
                if first is None or last is None:
                    return None
                if not start < first <= last <= end:
                    raise ValueError(f"range outside the window: {first}-{last}")
                return [first - 1, last - 1]

            span = ask(run.proj, provider, prompt, parse)
            if span:
                # A passage far shorter or longer than expected is a wrong match; it would also shift the next windows.
                size = cumulative[span[1]] - (cumulative[span[0] - 1] if span[0] else 0)
                if not 0.3 * expected_size <= size <= 3 * expected_size + 400:
                    return None
            return span

        cursor = None  # the reference paragraph where the next segment is expected to start (None: unknown)
        offset = 0     # number of source characters before this segment
        for sid in run.ids:
            proportional = bisect.bisect_left(cumulative, max(0, offset * ratio - lengths[sid] * ratio - 1500))
            if sid in done:
                cursor = done[sid][1] + 1 if done[sid] else None
            elif sid in run.selected:
                seg = run.seg(sid)
                expected = lengths[sid] * ratio
                # After an aligned segment, continue where it ended; otherwise start at the proportional position.
                first = max(0, cursor - 2) if cursor is not None else proportional
                span = attempt(seg, first, expected * 2 + 3000, expected)
                if span is None and proportional != first:
                    span = attempt(seg, proportional, expected * 3 + 3000, expected)
                done[sid] = span
                write_json(path, done)
                STATUS.task_done("align", f"{sid} ({ref})")
                cursor = span[1] + 1 if span else None
                result = t("paragraphs", first=span[0] + 1, last=span[1] + 1) if span else t("align_not_found")
                say(f"[align:{ref}] {sid} → {result}")
            offset += lengths[sid]

    todo = [ref for ref in run.refs if set(run.selected) - set(read_json(run.work / "alignment" / f"{ref}.json", {}))]
    units = sum(len(set(run.selected) - set(read_json(run.work / "alignment" / f"{ref}.json", {}))) for ref in todo)
    parallel("align", [(ref, ref) for ref in todo], one_ref, len(run.refs), units=units)


# --- glossary ---------------------------------------------------------------

def tr_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


def load_glossary(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    lines = path.read_text(encoding="utf-8").lstrip("\ufeff").splitlines()
    if lines and lines[0].split("\t")[0].strip().lower() == "tr":
        lines = lines[1:]  # header row
    for line in lines:
        cols = line.split("\t")
        if len(cols) >= 2 and cols[0].strip() and cols[1].strip():
            entries.append({"tr": cols[0].strip(), "target": cols[1].strip(), "note": cols[2].strip() if len(cols) > 2 else ""})
    return entries


def glossary_block(entries: list[dict], text: str) -> str:
    """Entries whose Turkish term occurs in the text. A term must start a word (Turkish adds suffixes at the end)."""
    lowered = tr_lower(text)
    lines = [
        f"- {e['tr']} → {e['target']}" + (f"  ({e['note']})" if e["note"] else "")
        for e in entries if re.search(r"(?<!\w)" + re.escape(tr_lower(e["tr"])), lowered)
    ]
    return "\n".join(lines) or "(No glossary entries apply to this segment.)"


def glossary(run: Run) -> None:
    """Extracts terms from the segments and adds only NEW terms to glossary/<lang>.tsv."""
    provider = run.proj.providers_for("glossary")[0]
    cache = run.lang_dir / "glossary"
    target_lang = run.proj.language_name(run.target)

    def clean(value) -> str:
        return " ".join(str(value).split())

    def one(sid: str) -> None:
        prompt = run.proj.prompt(
            "glossary", target_lang=target_lang, note_lang=note_language(), source=run.seg(sid),
            references=run.references_block(sid),
        )

        def parse(text: str):
            return [
                {"tr": clean(term["tr"]), "target": clean(term["target"]), "note": clean(term.get("note", ""))}
                for term in parse_json(text)["terms"] if clean(term["tr"]) and clean(term["target"])
            ]

        write_json(cache / f"{sid}.json", ask(run.proj, provider, prompt, parse))

    parallel("glossary", [(sid, sid) for sid in run.pending("glossary", ".json")], one, run.workers)

    # Existing rows (edited by hand, or from earlier books) are kept.
    entries = load_glossary(run.glossary_path)
    known = {tr_lower(e["tr"]) for e in entries}
    added = 0
    for sid in run.ids:
        for term in read_json(cache / f"{sid}.json", []):
            if tr_lower(term["tr"]) not in known:
                known.add(tr_lower(term["tr"]))
                entries.append(term)
                added += 1
    if added or not run.glossary_path.exists():
        lines = [f"tr\t{run.target}\tnote"] + [f"{e['tr']}\t{e['target']}\t{e['note']}" for e in entries]
        write_text(run.glossary_path, "\n".join(lines) + "\n")
    say(f"[glossary] {t('glossary_done', added=added, total=len(entries), path=run.glossary_path)}")


# --- translate --------------------------------------------------------------

def _require_complete(source: str, answer: str, previous: str | None = None) -> None:
    """Completeness gate: an answer that lost paragraphs, footnotes or sentences is not accepted (ask() retries)."""
    problems = checks.completeness_problems(source, answer, previous)
    if problems:
        raise ValueError(t("answer_rejected", problems="; ".join(problems)))


def _strip_fence(text: str) -> str:
    m = re.fullmatch(r"```[\w-]*\n(.*?)\n```", text.strip(), re.S)
    return (m.group(1) if m else text).strip()


def translate(run: Run) -> None:
    provider = run.proj.providers_for("translate")[0]
    entries = load_glossary(run.glossary_path)
    ref_langs = ", ".join(run.proj.language_name(r) for r in run.refs) or "none"

    def one(sid: str) -> None:
        source = run.seg(sid)
        index = run.ids.index(sid)
        context = run.seg(run.ids[index - 1]).strip().split("\n\n")[-1][-800:] if index else "(This is the beginning of the book.)"
        prompt = run.proj.prompt(
            "translate", target_lang=run.proj.language_name(run.target), ref_langs=ref_langs, context=context,
            glossary=glossary_block(entries, source), references=run.references_block(sid), source=source,
        )
        def parse(text: str) -> str:
            answer = _strip_fence(text)
            _require_complete(source, answer)
            return answer

        write_text(run.lang_dir / "translate" / f"{sid}.md", ask(run.proj, provider, prompt, parse, attempts=3) + "\n")

    parallel("translate", [(sid, sid) for sid in run.pending("translate")], one, run.workers)


# --- review1 / review2 ------------------------------------------------------

def _issue(item: dict) -> dict:
    return {
        "type": item.get("type") if item.get("type") in ISSUE_TYPES else "mistranslation",
        "severity": item.get("severity") if item.get("severity") in SEVERITIES else "major",
        "source": str(item.get("source", "")),
        "translation": str(item.get("translation", "")),
        "explanation": str(item.get("explanation", "")),
        "suggestion": str(item.get("suggestion", "")),
    }


def _text(run: Run, stage: str, sid: str) -> str:
    return (run.lang_dir / stage / f"{sid}.md").read_text(encoding="utf-8").strip()


def _tagged(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.S)
    if not m or not m.group(1):
        raise ValueError(f"no <{tag}> section in the answer")
    return m.group(1)


def review_issues(path: Path) -> list[dict]:
    """The findings of one review file. Files written before the reading proof was required hold a plain list."""
    data = read_json(path, [])
    return data["issues"] if isinstance(data, dict) else data


def review(run: Run, stage: str, text_stage: str) -> None:
    """Independent review: the models compare the text with the Turkish source and write a findings report.

    The reviewer must also return the last words of every paragraph it read: an empty findings list is accepted
    only together with this proof, so that "no problems" cannot stand for "did not look".
    """
    entries = load_glossary(run.glossary_path)
    folder = run.lang_dir / stage

    def one(task: tuple[str, str]) -> None:
        sid, reviewer = task
        source = run.seg(sid)
        translation = _text(run, text_stage, sid)
        prompt = run.proj.prompt(
            "review", target_lang=run.proj.language_name(run.target), note_lang=note_language(),
            glossary=glossary_block(entries, source), source=source, translation=translation,
        )

        def parse(text: str) -> dict:
            data = parse_json(text)
            issues = [_issue(i) for i in data["issues"]]
            problems = checks.coverage_problems(translation, data.get("checked"))
            if problems:
                raise ValueError(t("answer_rejected", problems="; ".join(problems)))
            return {"paragraphs": len(data["checked"]), "issues": issues}

        write_json(folder / f"{sid}.{slug(reviewer)}.json", ask(run.proj, reviewer, prompt, parse, attempts=3))

    tasks = [
        (f"{sid} ({r})", (sid, r)) for sid in run.selected for r in run.proj.providers_for(stage)
        if not (folder / f"{sid}.{slug(r)}.json").exists()
    ]
    parallel(stage, tasks, one, run.workers)


# --- revise1 / reconcile ----------------------------------------------------

def revise(run: Run, stage: str, text_stage: str, review_stage: str) -> None:
    """Weighs the review findings against the Turkish source and applies the ones that are correct."""
    provider = run.proj.providers_for(stage)[0]
    reviewers = run.proj.providers_for(review_stage)
    entries = load_glossary(run.glossary_path)
    folder = run.lang_dir / stage

    def one(sid: str) -> None:
        source = run.seg(sid)
        translation = _text(run, text_stage, sid)
        issues = []
        for reviewer in reviewers:
            for item in review_issues(run.lang_dir / review_stage / f"{sid}.{slug(reviewer)}.json"):
                issues.append({"id": len(issues) + 1, "stage": review_stage, "reviewer": reviewer, **item})

        if issues:
            prompt = run.proj.prompt(
                "revise", target_lang=run.proj.language_name(run.target), note_lang=note_language(),
                glossary=glossary_block(entries, source), references=run.references_block(sid), source=source,
                translation=translation, issues=json.dumps(issues, ensure_ascii=False, indent=1),
            )

            previous = translation

            def parse(text: str):
                decisions = parse_json(_tagged(text, "decisions"))["decisions"]
                answer = _tagged(text, "translation")
                _require_complete(source, answer, previous)
                by_id = {int(d["id"]): d for d in decisions}
                # A finding without a decision was silently skipped: ask again instead of passing it on.
                undecided = [i["id"] for i in issues if by_id.get(i["id"], {}).get("decision") not in ("accepted", "rejected")]
                if undecided:
                    raise ValueError(t("answer_rejected", problems=t("gate_decisions_missing", ids=", ".join(map(str, undecided)))))
                return answer, by_id

            translation, by_id = ask(run.proj, provider, prompt, parse, attempts=3)
            for issue in issues:
                issue["decision"] = by_id[issue["id"]]["decision"]
                issue["reason"] = str(by_id[issue["id"]].get("reason", ""))

        write_json(folder / f"{sid}.json", issues)
        write_text(folder / f"{sid}.md", translation + "\n")  # the .md is written last: it marks the segment as done

    parallel(stage, [(sid, sid) for sid in run.pending(stage)], one, run.workers)


# --- source_check -----------------------------------------------------------

def source_check(run: Run) -> None:
    """Compares the text with the Turkish source from the start, corrects the errors and records the changes."""
    stage = "source_check"
    provider = run.proj.providers_for(stage)[0]
    entries = load_glossary(run.glossary_path)
    folder = run.lang_dir / stage

    def one(sid: str) -> None:
        source = run.seg(sid)
        previous = _text(run, "revise1", sid)
        prompt = run.proj.prompt(
            "source_check", target_lang=run.proj.language_name(run.target), note_lang=note_language(),
            glossary=glossary_block(entries, source), references=run.references_block(sid), source=source,
            translation=previous,
        )

        def parse(text: str):
            changes = [_issue(i) for i in parse_json(_tagged(text, "changes"))["issues"]]
            answer = _tagged(text, "translation")
            _require_complete(source, answer, previous)
            return answer, changes

        translation, changes = ask(run.proj, provider, prompt, parse, attempts=3)
        issues = [
            {"id": n, "stage": stage, "reviewer": provider, **change, "decision": "accepted", "reason": ""}
            for n, change in enumerate(changes, 1)
        ]
        write_json(folder / f"{sid}.json", issues)
        write_text(folder / f"{sid}.md", translation + "\n")

    parallel(stage, [(sid, sid) for sid in run.pending(stage)], one, run.workers)


# --- reviewer audit ---------------------------------------------------------

QUIET_RATIO = 0.8    # a reviewer silent in this share of the segments is reported
QUIET_MIN_SEGMENTS = 5


def review_audit(proj: Project, lang_dir: Path, sids: list[str] | None = None) -> list[dict]:
    """Per review stage and reviewer: segments, segments without findings, findings, and "missed" segments.

    A missed segment is one where the reviewer wrote nothing, but a later check found critical or major errors:
    for review1 the source check, for review2 an accepted finding of another reviewer.
    """
    serious = ("critical", "major")
    rows = []
    for stage in REVIEW_STAGES:
        names = {slug(r): r for r in proj.providers_for(stage)}
        found: dict[str, dict[str, list]] = {}
        wanted = None if sids is None else set(sids)
        for path in sorted((lang_dir / stage).glob("*.json")):
            sid, _, rest = path.name.partition(".")
            if wanted is None or sid in wanted:
                found.setdefault(rest[:-len(".json")], {})[sid] = review_issues(path)
        for key, by_sid in found.items():
            silent = [sid for sid, issues in by_sid.items() if not issues]
            missed = []
            for sid in silent:
                if stage == "review1":
                    later = read_json(lang_dir / "source_check" / f"{sid}.json", [])
                else:
                    later = [i for i in read_json(lang_dir / FINAL / f"{sid}.json", [])
                             if i.get("decision") == "accepted" and slug(str(i.get("reviewer", ""))) != key]
                if any(i.get("severity") in serious for i in later):
                    missed.append(sid)
            quiet = len(by_sid) >= QUIET_MIN_SEGMENTS and len(silent) >= QUIET_RATIO * len(by_sid)
            rows.append({"stage": stage, "reviewer": names.get(key, key), "segments": len(by_sid), "empty": len(silent),
                         "issues": sum(len(v) for v in by_sid.values()), "missed": missed, "quiet": quiet})
    return rows


# --- assemble ---------------------------------------------------------------

def assemble(run: Run) -> None:
    """Joins the final texts, runs the mechanical checks and writes the report for the human translator."""
    finished = [sid for sid in run.ids if (run.lang_dir / FINAL / f"{sid}.md").exists()]
    if not finished:
        raise PipelineError(t("nothing_to_assemble"))
    out_dir = run.proj.book_dir(run.book) / "output"
    texts = {sid: _text(run, FINAL, sid) for sid in finished}
    missing = [sid for sid in run.ids if sid not in texts]
    out_text = out_dir / f"{run.target}.md"
    out_report = out_dir / f"{run.target}.report.md"
    # A missing segment stays visible in the output, so that a partial book is never mistaken for a complete one.
    parts = [texts[sid] if sid in texts else t("missing_segment_marker", id=sid) for sid in run.ids]
    write_text(out_text, "\n\n".join(parts) + "\n")

    warnings = {sid: checks.check_segment(run.seg(sid), texts[sid]) for sid in finished}
    outliers = checks.length_outliers({sid: (len(run.seg(sid)), len(texts[sid])) for sid in finished})
    for sid, message in outliers.items():
        warnings[sid].append(message)

    issues = {
        sid: [i for name in ISSUE_FOLDERS for i in read_json(run.lang_dir / name / f"{sid}.json", [])]
        for sid in finished
    }
    flat = [i for items in issues.values() for i in items]

    def summary(stage: str) -> str:
        items = [i for i in flat if i["stage"] == stage]
        count = lambda key, value: sum(1 for i in items if i.get(key) == value)  # noqa: E731
        return t("report_summary", total=len(items), critical=count("severity", "critical"),
                 major=count("severity", "major"), minor=count("severity", "minor"),
                 accepted=count("decision", "accepted"), rejected=count("decision", "rejected"))

    lines = [f"# {t('report_title', book=run.book, language=run.proj.language_name(run.target), code=run.target)}", ""]
    if len(finished) < len(run.ids):
        lines += [f"> **{t('report_incomplete', done=len(finished), total=len(run.ids))}**", "",
                  f"- {t('report_missing_segments', segments=', '.join(missing))}", ""]
    lines += [
        f"- {t('report_segments', done=len(finished), total=len(run.ids))}",
        f"- {t('report_references', refs=', '.join(run.refs) or '-')}",
        f"- {t('report_review1')}: {summary('review1')}",
        f"- {t('report_source_check')}: {summary('source_check')}",
        f"- {t('report_review2')}: {summary('review2')}",
        f"- {t('report_warnings', count=sum(1 for w in warnings.values() if w))}",
    ]
    for ref in run.refs:
        spans = read_json(run.work / "alignment" / f"{ref}.json", {})
        missing = [sid for sid in finished if not spans.get(sid)]
        if missing:
            lines.append(f"- {t('report_unaligned', ref=ref, segments=', '.join(missing))}")
    audit = review_audit(run.proj, run.lang_dir, finished)
    if audit:
        lines += ["", f"## {t('report_audit')}", "", t("report_audit_intro"), ""]
        for row in audit:
            lines.append(f"- {t('report_audit_row', **{k: row[k] for k in ('stage', 'reviewer', 'segments', 'empty', 'issues')})}")
            if row["quiet"]:
                lines.append(f"  - **{t('report_audit_quiet', reviewer=row['reviewer'], percent=round(100 * row['empty'] / row['segments']))}**")
            if row["missed"]:
                by = t("report_audit_by_source_check" if row["stage"] == "review1" else "report_audit_by_other")
                lines.append(f"  - **{t('report_audit_missed', reviewer=row['reviewer'], by=by, segments=', '.join(row['missed']))}**")
    lines += ["", f"## {t('report_attention')}", "", t("report_attention_intro", lang=run.target), ""]

    listed = 0
    for sid in finished:
        notable = [
            i for i in issues[sid]
            if i["severity"] == "critical" or (i.get("decision") != "accepted" and i["severity"] == "major")
        ]
        if not warnings[sid] and not notable:
            continue
        listed += 1
        lines += [f"### {t('report_segment', id=sid)}", ""]
        lines += [f"- {t('report_warning')}: {w}" for w in warnings[sid]]
        for i in notable:
            decision = t({"accepted": "decision_accepted", "rejected": "decision_rejected"}.get(i.get("decision"), "decision_none"))
            one = {key: " ".join(str(i.get(key, "")).split()) for key in ("explanation", "source", "translation", "suggestion", "reason")}
            lines.append(
                f"- [{t('severity_' + i['severity'])} · {t('type_' + i['type'])} · {i['stage']}/{i['reviewer']} · {decision}] "
                f"{one['explanation']} {t('report_source')}: «{one['source']}» {t('report_translation')}: «{one['translation']}»"
                + (f" {t('report_suggestion')}: «{one['suggestion']}»" if one["suggestion"] else "")
                + (f" {t('report_reason')}: {one['reason']}" if one["reason"] else "")
            )
        lines.append("")
    if not listed:
        lines += [t("report_nothing"), ""]

    write_text(out_report, "\n".join(lines))
    say(f"[assemble] {t('output_translation')}: {out_text}")
    say(f"[assemble] {t('output_report')}: {out_report}")
    if len(finished) < len(run.ids):
        say(f"[assemble] {t('output_incomplete', done=len(finished), total=len(run.ids))}")


def reset(run: Run, stage: str) -> None:
    """Deletes the output of the given stage and of all later stages, for the selected segments."""
    for name in LLM_STAGES[LLM_STAGES.index(stage):]:
        if name == "align":
            for ref in run.refs:
                path = run.work / "alignment" / f"{ref}.json"
                spans = read_json(path, {})
                kept = {sid: span for sid, span in spans.items() if sid not in run.selected}
                if len(kept) != len(spans):
                    write_json(path, kept)
        else:
            for sid in run.selected:
                for f in (run.lang_dir / name).glob(f"{sid}.*"):
                    f.unlink()
    say(f"[redo] {t('reset_done', count=len(run.selected), stage=stage)}")


def book_status(proj: Project, book: str) -> dict:
    """Returns the preparation, alignment and per-language stage progress of a book."""
    book_dir = proj.book_dir(book)
    work = book_dir / "work"
    total = read_json(work / "prep.json", {}).get("source", {}).get("segments", 0)
    alignment = {}
    for ref in available_refs(book_dir):
        spans = read_json(work / "alignment" / f"{ref}.json", {})
        alignment[ref] = {"aligned": sum(1 for span in spans.values() if span),
                          "missing": sorted(sid for sid, span in spans.items() if not span)}
    languages = {}
    for lang_dir in sorted(p for p in work.glob("*") if p.is_dir() and p.name not in SHARED_WORK_FOLDERS):
        progress = {}
        for stage in LLM_STAGES[1:]:
            pattern = "*.json" if stage in REVIEW_STAGES or stage == "glossary" else "*.md"
            expected = total * (len(proj.providers_for(stage)) if stage in REVIEW_STAGES else 1)
            progress[stage] = [len(list((lang_dir / stage).glob(pattern))), expected]
        output = book_dir / "output" / f"{lang_dir.name}.md"
        languages[lang_dir.name] = {"stages": progress, "output": output.exists(), "reviews": review_audit(proj, lang_dir)}
    return {"segments": total, "alignment": alignment, "languages": languages}


RUNNERS = {
    "align": align,
    "glossary": glossary,
    "translate": translate,                                                        # 1
    "review1": lambda run: review(run, "review1", "translate"),                     # 2
    "revise1": lambda run: revise(run, "revise1", "translate", "review1"),          # 3
    "source_check": source_check,                                                  # 4
    "review2": lambda run: review(run, "review2", "source_check"),                 # 5a, 5b
    "reconcile": lambda run: revise(run, "reconcile", "source_check", "review2"),  # 6
    "assemble": assemble,
}
