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

# Workflow: preparation (alignment, glossary) → first translation → the nodes of the flow → assembly → human.
# The flow ([stages] flow in config.toml) is the ordered list of nodes that the user builds on the canvas:
#   "review<n>"                          reviewers (up to 4, in parallel) write findings reports; the text is unchanged
#   "revise<n>", "reconcile", "apply<n>" applies the findings reported since the last text, weighed against the source
#   "source_check[<n>]"                  compares the text with the Turkish source from the start and corrects it
#   "custom<n>"                          the user's own instructions; it reports findings or corrects the text
#   "gate<n>"                            a checkpoint: a model looks for serious problems; a segment with such problems
#                                        is sent back to an earlier node, at most a set number of times
# Each node works on the latest text of the segment. A node can run more than once for a segment (after a checkpoint
# sent it back); each further visit writes to its own folder ("review1.2" for the second visit of review1).
# Options of custom nodes and checkpoints are in [nodes]; the instructions of a custom node in prompts/custom/<id>.md.
DEFAULT_FLOW = ["review1", "revise1", "source_check", "review2", "reconcile"]
FLOW_STEP_RE = re.compile(r"^(review[1-9][0-9]?|revise[1-9][0-9]?|reconcile|apply[1-9][0-9]?|"
                          r"source_check([2-9]|[1-9][0-9])?|custom[1-9][0-9]?|gate[1-9][0-9]?)$")
MAX_FLOW_STEPS = 30
MAX_LOOPS = 5          # how often a checkpoint can send a segment back
MAX_REPORTERS = 4      # models of a review node or a reporting custom node
TITLE_LIMIT = 60
INSTRUCTIONS_LIMIT = 20000
PREP_STAGES = ["align", "glossary"]
# Folder names of the first two review rounds' apply steps (kept so that the work of existing books stays valid).
APPLY_NAMES = {"review1": "revise1", "review2": "reconcile"}
# The text each stage of the original diagram read; fingerprints written before the flow was editable lack this.
LEGACY_FROM = {"review1": "translate", "revise1": "translate", "source_check": "revise1",
               "review2": "source_check", "reconcile": "source_check"}
REF_PARAGRAPH_LIMIT = 2000  # alignment works with numbered reference paragraphs
SEVERITIES = ("critical", "major", "minor")
SERIOUS = ("critical", "major")
ISSUE_TYPES = ("omission", "addition", "mistranslation", "terminology", "religious", "names", "format", "language")
SHARED_WORK_FOLDERS = {"segments", "references", "alignment"}  # the other folders under work/ are languages


# --- the flow ---------------------------------------------------------------

def apply_stage(review_stage: str) -> str:
    """The apply node that an old-style flow put after a review round."""
    return APPLY_NAMES.get(review_stage) or "revise" + review_stage[len("review"):]


def kind(stage: str) -> str:
    """prepare, align, glossary, translate, review, apply, source_check, custom, gate or assemble.
    A visit folder ("review1.2") has the kind of its node."""
    stage = node_of(stage)
    if stage.startswith("review"):
        return "review"
    if stage.startswith(("revise", "apply")) or stage == "reconcile":
        return "apply"
    for name in ("source_check", "custom", "gate"):
        if stage.startswith(name):
            return name
    return stage


def node_of(folder: str) -> str:
    """The node of a visit folder: "review1.2" → "review1"."""
    return folder.split(".")[0]


def visit_folder(node: str, visit: int) -> str:
    """The folder of a node's visit (0 for the first)."""
    return node if visit == 0 else f"{node}.{visit + 1}"


def node_options(cfg: dict, node: str) -> dict:
    options = cfg.get("nodes", {}).get(node, {})
    return options if isinstance(options, dict) else {}


def role(cfg: dict, node: str) -> str:
    """"report" (writes findings), "text" (writes a new text) or "gate"."""
    k = kind(node)
    if k == "review":
        return "report"
    if k == "custom":
        return "report" if node_options(cfg, node).get("mode") == "report" else "text"
    return "gate" if k == "gate" else "text"


def _old_flow(steps: list[str]) -> list[str]:
    """A flow written before the nodes could be placed freely: each review round implies its apply node."""
    out = []
    for step in steps:
        out += [step, apply_stage(step)] if kind(step) == "review" else [step]
    return out


def flow_problem(steps, cfg: dict) -> str | None:
    """Why a flow cannot run (a message key with its values), or None.

    - every finding must be applied: a reporting node needs an apply node later, before the text changes otherwise;
    - a checkpoint sends back to an earlier node, not past the checkpoint before it (loops do not overlap)."""
    if (not isinstance(steps, list) or len(steps) > MAX_FLOW_STEPS or len(set(map(str, steps))) != len(steps)
            or not all(isinstance(s, str) and FLOW_STEP_RE.match(s) for s in steps)):
        return "flow_invalid"
    pending = None
    last_gate = -1
    for i, node in enumerate(steps):
        r = role(cfg, node)
        options = node_options(cfg, node)
        if kind(node) == "custom":
            title = options.get("title", "")
            if options.get("mode") not in ("report", "rewrite") or not isinstance(title, str) or len(title) > TITLE_LIMIT:
                return "flow_custom_invalid"
        if r == "report":
            pending = pending or node
        elif r == "text":
            if pending and kind(node) != "apply":
                return f"flow_unapplied:{pending}"
            pending = None
        else:
            back, loops = options.get("back_to"), options.get("max")
            if back not in steps[last_gate + 1:i] or not isinstance(loops, int) or not 1 <= loops <= MAX_LOOPS:
                return f"flow_gate_invalid:{node}"
            last_gate = i
    if pending:
        return f"flow_unapplied:{pending}"
    return None


def flow_error(steps, cfg: dict) -> str | None:
    """The message of flow_problem in the current language."""
    problem = flow_problem(steps, cfg)
    if problem is None:
        return None
    key, _, node = problem.partition(":")
    return t(key, node=node) if node else t(key)


def flow(proj: Project) -> list[str]:
    steps = proj.cfg["stages"].get("flow", DEFAULT_FLOW)
    if isinstance(steps, list) and not any(kind(s) == "apply" for s in steps if isinstance(s, str)):
        steps = _old_flow(steps)
    error = flow_error(steps, proj.cfg)
    if error:
        raise PipelineError(error)
    return steps


def llm_stages(proj: Project) -> list[str]:
    stages = PREP_STAGES + ["translate"] + flow(proj)
    missing = [s for s in stages if s not in proj.cfg["stages"]]
    if missing:
        raise PipelineError(t("stage_not_assigned", stages=", ".join(missing)))
    return stages


def all_stages(proj: Project) -> list[str]:
    return ["prepare"] + llm_stages(proj) + ["assemble"]


def review_stages(proj: Project) -> list[str]:
    return [s for s in flow(proj) if kind(s) == "review"]


def instructions_path(root: Path, node: str) -> Path:
    return root / "prompts" / "custom" / f"{node}.md"


def instructions(proj: Project, node: str) -> str:
    path = instructions_path(proj.root, node)
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


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
DEFAULT_CALL_SECONDS = {"align": 25, "glossary": 40, "translate": 120, "review": 60, "apply": 120, "source_check": 150,
                        "custom": 120, "gate": 60}


def estimate(proj: Project, book: str, target: str, refs: list[str], segments: str = "",
             durations: dict | None = None) -> dict:
    """Counts the model calls that a run still needs, per provider, and estimates the time.

    Finished work is not counted. Before the book is prepared, the number of segments is estimated from the source.
    Each node is counted once: how often a checkpoint sends segments back is not known beforehand.
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
    for stage in llm_stages(proj):
        providers = proj.providers_for(stage)
        if stage == "align":
            for ref in refs:
                done = read_json(work / "alignment" / f"{ref}.json", {})
                n = sum(1 for sid in selected if sid not in done)
                calls[providers[0]] = calls.get(providers[0], 0) + n
                per_stage[stage] = max(per_stage.get(stage, 0), n)  # the references are aligned in parallel
            continue
        review = stage not in ("glossary", "translate") and role(proj.cfg, stage) != "text"  # one call per model
        for provider in (providers if review else providers[:1]):
            if review:
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
        each = measured[1] / measured[0] if measured and measured[0] else DEFAULT_CALL_SECONDS[kind(stage)]
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


# --- input fingerprints -----------------------------------------------------
# A text of a segment is produced from the instructions, the glossary rows that match the segment and the reference
# passages. Their fingerprint is stored beside the text ("<segment>.in"). When one of them changes later, the segment
# is reported as produced from older inputs. The second line names the folder of the text it worked on: after a change
# of the flow, a segment that worked on another text is reported in the same way.
# It is produced again only when the user asks for it (--redo).
TEMPLATES = {"translate": "translate", "review": "review", "apply": "revise", "source_check": "source_check",
             "gate": "gate"}


def template(cfg: dict, node: str) -> str:
    """The prompt file of a node."""
    if kind(node) == "custom":
        return "custom_report" if role(cfg, node) == "report" else "custom_rewrite"
    return TEMPLATES[kind(node)]


def _fingerprint(run: Run, stage: str, gloss: str, refs: str, templates: dict | None = None) -> str:
    node = node_of(stage)
    name = template(run.proj.cfg, node)
    templates = {} if templates is None else templates
    key = name + "/" + node
    if key not in templates:
        extra = "\0" + instructions(run.proj, node) if kind(node) == "custom" else ""
        templates[key] = (run.proj.root / "prompts" / f"{name}.md").read_text(encoding="utf-8") + "\0" + run.proj.rules() + extra
    uses_refs = name not in ("review", "custom_report", "gate")
    return hashlib.sha256("\0".join([templates[key], gloss, refs if uses_refs else ""]).encode("utf-8")).hexdigest()


def _save_inputs(run: Run, folder: str, stem: str, gloss: str, refs: str = "", source: str | None = None) -> None:
    lines = [_fingerprint(run, folder, gloss, refs)]
    if source:
        lines.append(f"from {source}")
    write_text(run.lang_dir / folder / f"{stem}.in", "\n".join(lines) + "\n")


# --- the path of a segment through the flow -----------------------------------
# A segment goes through the nodes in order. A checkpoint can send it back; then the nodes from there run again for
# this segment (a new visit, a new folder). The path depends only on the files on disk, so a stopped run takes the
# same path again and continues where it stopped.

@dataclass
class Job:
    sid: str
    folder: str                # where this visit writes
    text: str                  # the folder of the text it works on
    reports: list[str] = field(default_factory=list)  # report folders since that text (an apply node uses them)


@dataclass
class _Cursor:
    pos: int = 0
    text: str = "translate"
    reports: list[str] = field(default_factory=list)
    visits: dict = field(default_factory=dict)
    loops: dict = field(default_factory=dict)

    def job(self, sid: str, node: str) -> Job:
        return Job(sid, visit_folder(node, self.visits.get(node, 0)), self.text, list(self.reports))


def _advance(cfg: dict, steps: list[str], cur: _Cursor, node: str, folder: str, failed: bool = False) -> None:
    """Moves a segment past a node: a report waits for the next apply, a text becomes the current text, a checkpoint
    that found serious problems sends the segment back (its findings go to the next apply)."""
    cur.visits[node] = cur.visits.get(node, 0) + 1
    r = role(cfg, node)
    if r == "report":
        cur.reports.append(folder)
    elif r == "text":
        cur.text, cur.reports = folder, []
    elif failed and cur.loops.get(node, 0) < node_options(cfg, node)["max"]:
        cur.loops[node] = cur.loops.get(node, 0) + 1
        cur.reports.append(folder)
        cur.pos = steps.index(node_options(cfg, node)["back_to"])
        return
    cur.pos += 1


def _report_files(run: Run, folder: str, sid: str) -> list[Path]:
    return [run.lang_dir / folder / f"{sid}.{slug(m)}.json" for m in run.proj.providers_for(node_of(folder))]


def _done(run: Run, node: str, folder: str, sid: str) -> bool:
    if role(run.proj.cfg, node) == "text":
        return (run.lang_dir / folder / f"{sid}.md").exists()
    return all(f.exists() for f in _report_files(run, folder, sid))


def _failed(run: Run, folder: str, sid: str) -> bool:
    """A checkpoint found a critical or major problem."""
    return any(i.get("severity") in SERIOUS for f in _report_files(run, folder, sid) for i in review_issues(f))


@dataclass
class Visit:
    node: str
    folder: str
    text: str        # the folder of the text it worked on
    done: bool


def path_on_disk(run: Run, sid: str, steps: list[str] | None = None) -> tuple[list[Visit], bool, str]:
    """The visits of a segment as far as the files on disk go: (visits, complete, final text folder).

    A node that has not run yet is passed over (its visit is listed as not done), so that the later nodes are still
    compared with the text they should work on. The path ends at a checkpoint that has not run: its decision is
    not known."""
    steps = flow(run.proj) if steps is None else steps
    cfg = run.proj.cfg
    cur, visits, complete = _Cursor(), [], (run.lang_dir / "translate" / f"{sid}.md").exists()
    while cur.pos < len(steps):
        node = steps[cur.pos]
        folder = visit_folder(node, cur.visits.get(node, 0))
        done = _done(run, node, folder, sid)
        visits.append(Visit(node, folder, cur.text, done))
        complete = complete and done
        if role(cfg, node) == "gate" and not done:
            return visits, False, cur.text
        _advance(cfg, steps, cur, node, folder, role(cfg, node) == "gate" and _failed(run, folder, sid))
    return visits, complete, cur.text


def run_flow(run: Run, until: str | None = None) -> None:
    """Runs the nodes of the flow for the selected segments. The segments that are at the earliest node go first;
    a segment sent back by a checkpoint runs the nodes again while the others wait after the checkpoint."""
    steps = flow(run.proj)
    end = steps.index(until) + 1 if until else len(steps)
    cursors = {sid: _Cursor() for sid in run.selected if (run.lang_dir / "translate" / f"{sid}.md").exists()}
    while True:
        waiting = [sid for sid, cur in cursors.items() if cur.pos < end]
        if not waiting:
            return
        pos = min(cursors[sid].pos for sid in waiting)
        node = steps[pos]
        jobs = [cursors[sid].job(sid, node) for sid in waiting if cursors[sid].pos == pos]
        NODE_RUNNERS[kind(node)](run, node, jobs)
        for job in jobs:
            failed = role(run.proj.cfg, node) == "gate" and _failed(run, job.folder, job.sid)
            if failed:
                say(f"[{job.folder}] {t('gate_sent_back', id=job.sid, node=node_options(run.proj.cfg, node)['back_to'])}"
                    if cursors[job.sid].loops.get(node, 0) < node_options(run.proj.cfg, node)["max"]
                    else f"[{job.folder}] {t('gate_limit', id=job.sid)}")
            _advance(run.proj.cfg, steps, cursors[job.sid], node, job.folder, failed)


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
        gloss, refs = glossary_block(entries, source), run.references_block(sid)
        prompt = run.proj.prompt(
            "translate", target_lang=run.proj.language_name(run.target), ref_langs=ref_langs, context=context,
            glossary=gloss, references=refs, source=source,
        )
        def parse(text: str) -> str:
            answer = _strip_fence(text)
            _require_complete(source, answer)
            return answer

        answer = ask(run.proj, provider, prompt, parse, attempts=3)
        _save_inputs(run, "translate", sid, gloss, refs)
        write_text(run.lang_dir / "translate" / f"{sid}.md", answer + "\n")

    parallel("translate", [(sid, sid) for sid in run.pending("translate")], one, run.workers)


# --- reporting nodes: review, a reporting custom node, a checkpoint ----------

def _issue(item: dict) -> dict:
    return {
        "type": item.get("type") if item.get("type") in ISSUE_TYPES else "mistranslation",
        "severity": item.get("severity") if item.get("severity") in SEVERITIES else "major",
        "source": str(item.get("source", "")),
        "translation": str(item.get("translation", "")),
        "explanation": str(item.get("explanation", "")),
        "suggestion": str(item.get("suggestion", "")),
    }


def _text(run: Run, folder: str, sid: str) -> str:
    return (run.lang_dir / folder / f"{sid}.md").read_text(encoding="utf-8").strip()


def _tagged(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.S)
    if not m or not m.group(1):
        raise ValueError(f"no <{tag}> section in the answer")
    return m.group(1)


def review_issues(path: Path) -> list[dict]:
    """The findings of one report file. Files written before the reading proof was required hold a plain list."""
    data = read_json(path, [])
    return data["issues"] if isinstance(data, dict) else data


def report(run: Run, node: str, jobs: list[Job]) -> None:
    """Independent reports: each model of the node compares the text with the Turkish source and writes findings.

    A review looks for every problem, a checkpoint only for serious ones, a custom node follows its instructions.
    The model must also return the last words of every paragraph it read: an empty findings list is accepted
    only together with this proof, so that "no problems" cannot stand for "did not look".
    """
    entries = load_glossary(run.glossary_path)
    name = template(run.proj.cfg, node)
    extra = {"instructions": instructions(run.proj, node) or "(none)"} if kind(node) == "custom" else {}

    def one(task: tuple[Job, str]) -> None:
        job, model = task
        source = run.seg(job.sid)
        translation = _text(run, job.text, job.sid)
        gloss = glossary_block(entries, source)
        prompt = run.proj.prompt(
            name, target_lang=run.proj.language_name(run.target), note_lang=note_language(),
            glossary=gloss, source=source, translation=translation, **extra,
        )

        def parse(text: str) -> dict:
            data = parse_json(text)
            issues = [_issue(i) for i in data["issues"]]
            problems = checks.coverage_problems(translation, data.get("checked"))
            if problems:
                raise ValueError(t("answer_rejected", problems="; ".join(problems)))
            return {"paragraphs": len(data["checked"]), "issues": issues}

        result = ask(run.proj, model, prompt, parse, attempts=3)
        _save_inputs(run, job.folder, f"{job.sid}.{slug(model)}", gloss, source=job.text)
        write_json(run.lang_dir / job.folder / f"{job.sid}.{slug(model)}.json", result)

    tasks = [
        (f"{job.sid} ({model})", (job, model)) for job in jobs for model in run.proj.providers_for(node)
        if not (run.lang_dir / job.folder / f"{job.sid}.{slug(model)}.json").exists()
    ]
    parallel(_label(jobs, node), tasks, one, run.workers)


def _label(jobs: list[Job], node: str) -> str:
    """The progress label: the node, or its visit folder when all segments are on the same later visit."""
    folders = {job.folder for job in jobs}
    return folders.pop() if len(folders) == 1 else node


# --- applying the findings ----------------------------------------------------

def revise(run: Run, node: str, jobs: list[Job]) -> None:
    """Weighs the findings reported since the last text against the Turkish source and applies the correct ones."""
    provider = run.proj.providers_for(node)[0]
    entries = load_glossary(run.glossary_path)

    def one(job: Job) -> None:
        source = run.seg(job.sid)
        translation = _text(run, job.text, job.sid)
        issues = []
        for folder in job.reports:
            names = {slug(m): m for m in run.proj.providers_for(node_of(folder))}
            for path in _report_files(run, folder, job.sid):
                reviewer = names.get(path.name[len(job.sid) + 1:-len(".json")], "")
                for item in review_issues(path):
                    issues.append({"id": len(issues) + 1, "stage": folder, "reviewer": reviewer, **item})

        if issues:
            gloss, refs = glossary_block(entries, source), run.references_block(job.sid)
            prompt = run.proj.prompt(
                "revise", target_lang=run.proj.language_name(run.target), note_lang=note_language(),
                glossary=gloss, references=refs, source=source,
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
            _save_inputs(run, job.folder, job.sid, gloss, refs, source=job.text)
            for issue in issues:
                issue["decision"] = by_id[issue["id"]]["decision"]
                issue["reason"] = str(by_id[issue["id"]].get("reason", ""))

        write_json(run.lang_dir / job.folder / f"{job.sid}.json", issues)
        write_text(run.lang_dir / job.folder / f"{job.sid}.md", translation + "\n")  # written last: marks it done

    pending = [job for job in jobs if not (run.lang_dir / job.folder / f"{job.sid}.md").exists()]
    parallel(_label(jobs, node), [(job.sid, job) for job in pending], one, run.workers)


# --- nodes that correct the text: source_check, a correcting custom node ------

def source_check(run: Run, node: str, jobs: list[Job]) -> None:
    """Compares the text with the Turkish source from the start (or follows the instructions of a custom node),
    corrects the errors and records the changes."""
    provider = run.proj.providers_for(node)[0]
    entries = load_glossary(run.glossary_path)
    name = template(run.proj.cfg, node)
    extra = {"instructions": instructions(run.proj, node) or "(none)"} if kind(node) == "custom" else {}

    def one(job: Job) -> None:
        source = run.seg(job.sid)
        previous = _text(run, job.text, job.sid)
        gloss, refs = glossary_block(entries, source), run.references_block(job.sid)
        prompt = run.proj.prompt(
            name, target_lang=run.proj.language_name(run.target), note_lang=note_language(),
            glossary=gloss, references=refs, source=source, translation=previous, **extra,
        )

        def parse(text: str):
            changes = [_issue(i) for i in parse_json(_tagged(text, "changes"))["issues"]]
            answer = _tagged(text, "translation")
            _require_complete(source, answer, previous)
            return answer, changes

        translation, changes = ask(run.proj, provider, prompt, parse, attempts=3)
        _save_inputs(run, job.folder, job.sid, gloss, refs, source=job.text)
        issues = [
            {"id": n, "stage": job.folder, "reviewer": provider, **change, "decision": "accepted", "reason": ""}
            for n, change in enumerate(changes, 1)
        ]
        write_json(run.lang_dir / job.folder / f"{job.sid}.json", issues)
        write_text(run.lang_dir / job.folder / f"{job.sid}.md", translation + "\n")

    pending = [job for job in jobs if not (run.lang_dir / job.folder / f"{job.sid}.md").exists()]
    parallel(_label(jobs, node), [(job.sid, job) for job in pending], one, run.workers)


def _custom(run: Run, node: str, jobs: list[Job]) -> None:
    (report if role(run.proj.cfg, node) == "report" else source_check)(run, node, jobs)


NODE_RUNNERS = {"review": report, "gate": report, "apply": revise, "source_check": source_check, "custom": _custom}


# --- produced from older inputs ------------------------------------------------

def stale_inputs(run: Run) -> dict[str, list[str]]:
    """{node: [segments]}: selected segments whose instructions, glossary rows, reference passages or input text
    (after a change of the flow) changed after a node produced them. A segment is listed at its first such node:
    redoing that node renews the later ones."""
    entries = load_glossary(run.glossary_path)
    templates: dict = {}
    steps = flow(run.proj)
    out: dict[str, list[str]] = {}
    for sid in run.selected:
        gloss = refs = None
        visits, _, _ = path_on_disk(run, sid, steps)
        for visit in [Visit("translate", "translate", "", True)] + visits:
            files = list((run.lang_dir / visit.folder).glob(f"{sid}.*in"))
            if not files:
                continue
            if gloss is None:
                gloss, refs = glossary_block(entries, run.seg(sid)), run.references_block(sid)
            current = _fingerprint(run, visit.folder, gloss, refs, templates)

            def changed(f: Path) -> bool:
                lines = f.read_text(encoding="utf-8").split("\n")
                source = lines[1][len("from "):] if len(lines) > 1 and lines[1].startswith("from ") else LEGACY_FROM.get(visit.folder)
                return lines[0].strip() != current or (visit.node != "translate" and source not in (None, visit.text))

            if any(changed(f) for f in files):
                out.setdefault(visit.node, []).append(sid)
                break
    return out


def stale_for(proj: Project, book: str, target: str, refs: list[str], segments: str = "") -> dict[str, list[str]]:
    """stale_inputs for a book that is not running (used by the interface before a run)."""
    total = read_json(proj.book_dir(book) / "work" / "prep.json", {}).get("source", {}).get("segments", 0)
    ids = [f"{i:04d}" for i in range(1, total + 1)]
    if not ids:
        return {}
    selected = select_segments(segments, ids) if segments else ids
    return stale_inputs(Run(proj=proj, book=book, target=target, refs=refs, ids=ids, selected=selected, workers=1))


# --- reviewer audit ---------------------------------------------------------

QUIET_RATIO = 0.8    # a reviewer silent in this share of the segments is reported
QUIET_MIN_SEGMENTS = 5


def review_audit(proj: Project, lang_dir: Path, sids: list[str] | None = None) -> list[dict]:
    """Per review node and reviewer (first visits): segments, segments without findings, findings, and "missed"
    segments.

    A missed segment is one where the reviewer wrote nothing, but a later check found critical or major errors:
    an accepted finding of another reviewer in the same apply step, or a source check right after that apply step.
    """
    steps = flow(proj)
    rows = []
    for stage in review_stages(proj):
        index = steps.index(stage)
        apply = next((s for s in steps[index + 1:] if kind(s) == "apply"), None)
        following = steps[steps.index(apply) + 1] if apply and steps.index(apply) + 1 < len(steps) else ""
        check = following if kind(following) == "source_check" else None
        names = {slug(r): r for r in proj.providers_for(stage)}
        found: dict[str, dict[str, list]] = {}
        wanted = None if sids is None else set(sids)
        for path in sorted((lang_dir / stage).glob("*.json")):
            sid, _, rest = path.name.partition(".")
            if wanted is None or sid in wanted:
                found.setdefault(rest[:-len(".json")], {})[sid] = review_issues(path)
        for key, by_sid in found.items():
            silent = [sid for sid, issues in by_sid.items() if not issues]
            missed, by_check = [], False
            for sid in silent:
                others = [i for i in (read_json(lang_dir / apply / f"{sid}.json", []) if apply else [])
                          if i.get("decision") == "accepted" and slug(str(i.get("reviewer", ""))) != key]
                checked = read_json(lang_dir / check / f"{sid}.json", []) if check else []
                if any(i.get("severity") in SERIOUS for i in checked):
                    missed.append(sid)
                    by_check = True
                elif any(i.get("severity") in SERIOUS for i in others):
                    missed.append(sid)
            quiet = len(by_sid) >= QUIET_MIN_SEGMENTS and len(silent) >= QUIET_RATIO * len(by_sid)
            rows.append({"stage": stage, "reviewer": names.get(key, key), "segments": len(by_sid), "empty": len(silent),
                         "issues": sum(len(v) for v in by_sid.values()), "missed": missed, "quiet": quiet,
                         "missed_by": "source_check" if by_check else "other"})
    return rows


# --- assemble ---------------------------------------------------------------

def _segment_issues(run: Run, sid: str, visits: list[Visit]) -> list[dict]:
    """The findings to report for a segment: the decisions of every text node on its path, and the findings of a
    checkpoint that still saw serious problems when it could send the segment back no more."""
    cfg = run.proj.cfg
    out = []
    last_gate_visit = {}
    for visit in visits:
        if role(cfg, visit.node) == "gate":
            last_gate_visit[visit.node] = visit
        elif role(cfg, visit.node) == "text":
            out += read_json(run.lang_dir / visit.folder / f"{sid}.json", [])
    for visit in last_gate_visit.values():
        names = {slug(m): m for m in run.proj.providers_for(visit.node)}
        for path in _report_files(run, visit.folder, sid):
            for item in review_issues(path):
                if item.get("severity") in SERIOUS:
                    reviewer = names.get(path.name[len(sid) + 1:-len(".json")], "")
                    out.append({"stage": visit.folder, "reviewer": reviewer, **item, "decision": None})
    return out


def assemble(run: Run) -> None:
    """Joins the final texts, runs the mechanical checks and writes the report for the human translator."""
    steps = flow(run.proj)
    paths = {sid: path_on_disk(run, sid, steps) for sid in run.ids}
    finished = [sid for sid in run.ids if paths[sid][1]]
    if not finished:
        raise PipelineError(t("nothing_to_assemble"))
    out_dir = run.proj.book_dir(run.book) / "output"
    texts = {sid: _text(run, paths[sid][2], sid) for sid in finished}
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

    issues = {sid: _segment_issues(run, sid, paths[sid][0]) for sid in finished}
    flat = [i for items in issues.values() for i in items]

    def summary(stage: str) -> str:
        items = [i for i in flat if node_of(str(i.get("stage", ""))) == stage]
        count = lambda key, value: sum(1 for i in items if i.get(key) == value)  # noqa: E731
        return t("report_summary", total=len(items), critical=count("severity", "critical"),
                 major=count("severity", "major"), minor=count("severity", "minor"),
                 accepted=count("decision", "accepted"), rejected=count("decision", "rejected"))

    def line(step: str) -> str:
        name = t("report_" + kind(step), stage=step) if kind(step) != "custom" else t(
            "report_custom", stage=step, title=node_options(run.proj.cfg, step).get("title") or step)
        if kind(step) == "gate":
            sent = sum(1 for sid in finished for v in paths[sid][0] if v.node == step and v.folder != step)  # visits again
            last = {sid: [v for v in paths[sid][0] if v.node == step][-1] for sid in finished}
            left = sum(1 for sid, v in last.items() if _failed(run, v.folder, sid))  # serious problems at the last check
            return f"- {name}: {t('report_gate_summary', sent=sent, left=left)}"
        return f"- {name}: {summary(step)}"

    lines = [f"# {t('report_title', book=run.book, language=run.proj.language_name(run.target), code=run.target)}", ""]
    if len(finished) < len(run.ids):
        lines += [f"> **{t('report_incomplete', done=len(finished), total=len(run.ids))}**", "",
                  f"- {t('report_missing_segments', segments=', '.join(missing))}", ""]
    lines += [
        f"- {t('report_segments', done=len(finished), total=len(run.ids))}",
        f"- {t('report_references', refs=', '.join(run.refs) or '-')}",
    ]
    lines += [line(step) for step in steps if kind(step) != "apply"]  # its decisions count under each finding's node
    lines.append(f"- {t('report_warnings', count=sum(1 for w in warnings.values() if w))}")
    for ref in run.refs:
        spans = read_json(run.work / "alignment" / f"{ref}.json", {})
        unaligned = [sid for sid in finished if not spans.get(sid)]
        if unaligned:
            lines.append(f"- {t('report_unaligned', ref=ref, segments=', '.join(unaligned))}")
    stale = stale_inputs(run)
    for stage, sids in stale.items():
        lines.append(f"- **{t('report_stale', stage=stage, segments=', '.join(sids))}**")
        say(f"[assemble] {t('report_stale', stage=stage, segments=', '.join(sids))}")
    audit = review_audit(run.proj, run.lang_dir, finished)
    if audit:
        lines += ["", f"## {t('report_audit')}", "", t("report_audit_intro"), ""]
        for row in audit:
            lines.append(f"- {t('report_audit_row', **{k: row[k] for k in ('stage', 'reviewer', 'segments', 'empty', 'issues')})}")
            if row["quiet"]:
                lines.append(f"  - **{t('report_audit_quiet', reviewer=row['reviewer'], percent=round(100 * row['empty'] / row['segments']))}**")
            if row["missed"]:
                by = t("report_audit_by_" + row["missed_by"])
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


def _visit_folders(lang_dir: Path, node: str) -> list[Path]:
    """The folders of all visits of a node."""
    return [lang_dir / node] + sorted(lang_dir.glob(f"{node}.*"))


def reset(run: Run, stage: str) -> None:
    """Deletes the output of the given stage and of all later stages (every visit), for the selected segments."""
    stages = llm_stages(run.proj)
    for name in stages[stages.index(stage):]:
        if name == "align":
            for ref in run.refs:
                path = run.work / "alignment" / f"{ref}.json"
                spans = read_json(path, {})
                kept = {sid: span for sid, span in spans.items() if sid not in run.selected}
                if len(kept) != len(spans):
                    write_json(path, kept)
        else:
            for folder in _visit_folders(run.lang_dir, name):
                for sid in run.selected:
                    for f in folder.glob(f"{sid}.*"):
                        f.unlink()
    say(f"[redo] {t('reset_done', count=len(run.selected), stage=stage)}")


def book_status(proj: Project, book: str) -> dict:
    """Returns the preparation, alignment and per-language stage progress (first visits) of a book."""
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
        for stage in llm_stages(proj)[1:]:
            report_node = stage not in ("glossary", "translate") and role(proj.cfg, stage) != "text"
            pattern = "*.json" if report_node or stage == "glossary" else "*.md"
            expected = total * (len(proj.providers_for(stage)) if report_node else 1)
            progress[stage] = [len(list((lang_dir / stage).glob(pattern))), expected]
        output = book_dir / "output" / f"{lang_dir.name}.md"
        languages[lang_dir.name] = {"stages": progress, "output": output.exists(), "reviews": review_audit(proj, lang_dir)}
    return {"segments": total, "alignment": alignment, "languages": languages}


def runner(stage: str):
    """The function that runs a preparation stage, the first translation or the assembly."""
    return {"align": align, "glossary": glossary, "translate": translate, "assemble": assemble}[stage]
