"""The editor's own model calls: "Describe it, I will build it" (a model writes a first draft of a workflow) and
"Test this step" (one step of the workflow in the editor runs alone).

Both are jobs (Jobs): a thread per job, the model call in its own process (nodes.ask_model -> mehteran.worker, as a
run does it), a live log (livelog.py) and a cancel. Nothing is saved into the library and no run is started: a
draft opens in the editor as an unsaved workflow; a step test shows the answer in the step's panel.

The draft:
1. The prompt: a compact summary of the workflow file made from the node registry (nodes.REGISTRY, the same data as
   GET /api/node-types), the rules of an instruction-only workflow, two short examples, and the user's description
   between data tags (it is data, not instructions).
2. The answer -> YAML (yamlio.load, the safe loader) -> forced style (normalize: every model step takes the run
   form's model input, there is a "language" input, no layout) -> the schema check.
3. An answer that does not pass gets one repair turn with the list of problems. If the second answer does not pass
   either, the result is the text with its problems: the editor opens it on the YAML tab.
"""

from __future__ import annotations

import copy
import re
import secrets
import shutil
import threading
import time
from pathlib import Path

from . import i18n, languages, livelog, nodes, paths, placeholders, schema, yamlio
from .i18n import t

DESCRIPTION_LIMIT = 4000
ANSWER_LIMIT = 200_000  # characters of a step test's answer sent to the page
KEEP_JOBS = 20          # finished jobs kept (their state and folder)
MAX_RUNNING = 2
TRYABLE = ("ai.cli", "condition")  # "Test this step": steps that make one model call


class DraftError(ValueError):
    """The request cannot be done as asked; the message is shown to the user."""


# --- jobs -------------------------------------------------------------------------------------------------

class Job:
    def __init__(self, job_id: str, kind: str, folder: Path):
        self.id, self.kind, self.folder = job_id, kind, folder
        self.log = folder / livelog.NAME
        self.abort = threading.Event()
        self.status = "running"   # running | done | failed | cancelled
        self.result: dict | None = None
        self.error = ""
        self.started = time.time()


class Jobs:
    """The editor jobs of this server, in memory; their files are in <data>/jobs/editor/<id>/ (removed with the job)."""

    def __init__(self, home: Path):
        self.root = home / "jobs" / "editor"
        self.items: dict[str, Job] = {}
        self.lock = threading.Lock()
        shutil.rmtree(self.root, ignore_errors=True)  # jobs of a server that ended: nobody reads them

    def start(self, kind: str, work) -> str:
        """Starts work(job) -> result in a thread. work raises nodes.NodeError (shown) or nodes.Aborted (cancelled)."""
        with self.lock:
            if sum(job.status == "running" for job in self.items.values()) >= MAX_RUNNING:
                raise DraftError(t("editor_job_busy"))
            for old in [j for j in self.items.values() if j.status != "running"][:-KEEP_JOBS]:
                shutil.rmtree(old.folder, ignore_errors=True)
                del self.items[old.id]
            job = Job(secrets.token_hex(8), kind, self.root / secrets.token_hex(8))
            job.folder.mkdir(parents=True)
            self.items[job.id] = job
        lang = i18n.current()

        def run():
            i18n.set_request(lang)
            try:
                job.result = work(job)
                job.status = "cancelled" if job.abort.is_set() and job.result is None else "done"
            except nodes.Aborted:
                job.status = "cancelled"
            except (nodes.NodeError, DraftError, schema.WorkflowError) as e:
                job.error, job.status = str(i18n.message_of(e)), "failed"
            except Exception as e:  # noqa: BLE001 - shown as the job's error; the server stays alive
                job.error, job.status = f"{type(e).__name__}: {e}", "failed"

        threading.Thread(target=run, name=f"editor-job-{job.id}", daemon=True).start()
        return job.id

    def get(self, job_id: str) -> Job:
        job = self.items.get(job_id)
        if job is None:
            raise DraftError(t("editor_job_missing"))
        return job

    def state(self, job_id: str, offset: int = 0) -> dict:
        job = self.get(job_id)
        status = job.status  # read first: a job that ends now is read fully by the next request
        text, next_offset = livelog.read(job.log, offset)
        return {"id": job.id, "kind": job.kind, "status": status, "log": text, "offset": next_offset,
                "seconds": round(time.time() - job.started), "error": job.error if status == "failed" else "",
                "result": job.result if status == "done" else None}

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job.status != "running":
            return False
        job.abort.set()
        return True


def ask(engine, job: Job, provider: str, prompt: str, stem: str) -> str:
    """One model call of a job, the way a run's step makes it (its own process, the live log, the usage count)."""
    cfg = engine.provider_cfg
    name = provider.partition("@")[0].partition("/")[0]
    ctx = nodes.Ctx(run_dir=job.folder, node_dir=job.folder, node_id=job.kind, config={}, value=lambda ref: "",
                    wrapped=lambda ref: "", provider=provider,
                    provider_cfg={"providers": {name: cfg["providers"][name]}, "general": cfg["general"]},
                    abort=job.abort, timeout=cfg["general"].get("timeout", 1200), attempt=1, lang=i18n.current(),
                    record=_recorder(engine, job), log=job.log)
    path = job.folder / f"{stem}.prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return nodes.ask_model(ctx, path, stem)


def _recorder(engine, job: Job):
    """The editor's calls count for the usage page like a run's ones (run "editor", step "draft" or "try")."""
    return lambda name, started, outcome, until=None, message="": engine.store.record_call(
        "editor", job.kind, name, started, outcome, until, message)


def checked_provider(engine, provider) -> str:
    provider = str(provider or "").strip()
    problem = engine.provider_problem(provider)
    if problem:
        raise DraftError(str(problem))
    chosen = engine.resolve_model(provider)  # `auto` and old names: the model a run would use now
    if not chosen:
        raise DraftError(t("auto_none_local" if provider == "auto:local" else "auto_none"))
    return chosen


# --- the draft: the prompt ----------------------------------------------------------------------------------

def schema_summary() -> str:
    """The node types and their settings as a short text, made from the registry."""
    lines = []
    for name, nt in nodes.REGISTRY.items():
        fields = []
        for key, f in nt.config.items():
            kind = "text" if f.kind == "template" else f.kind
            if f.kind == "choice":
                kind = "one of " + "|".join(value for value, _ in f.options)
            elif f.kind == "formats":
                kind = "list of " + "|".join(nodes.FORMATS)
            elif f.kind == "int":
                kind = f"int {f.low}..{f.high}"
            fields.append(f"{key}{'*' if f.required else ''} ({kind})")
        lines.append(f"- {name}: {nt.description.get('en', '')}\n  outputs: {', '.join(nt.outputs({}))}\n"
                     f"  config: {'; '.join(fields)}")
    return "\n".join(lines)


EXAMPLE_DOCUMENT = """\
schema_version: 1
id: meeting-notes-actions
name: Meeting notes to action list
description: Reads meeting notes and writes the decisions and an action list.
inputs:
  - {id: notes, type: file, label: Meeting notes, formats: [pdf, docx, md, txt]}
  - {id: model, type: provider, label: Model}
  - {id: language, type: language, label: Language of the answer}
nodes:
  - id: read
    type: document.extract
    label: Read the notes
    config: {file: "{{inputs.notes}}"}
  - id: actions
    type: ai.cli
    label: Find decisions and actions
    config:
      provider: "{{inputs.model}}"
      prompt: |
        These are the notes of a meeting. List the decisions that were taken. Then write a table of actions:
        what, who, until when. Write "not stated" where the notes do not say it. Do not invent anything.
  - id: save
    type: document.export
    label: Save the action list
    config: {formats: [md, docx]}
connections:
  - {from: read.text, to: actions}
  - {from: actions.text, to: save}
outputs:
  - {id: actions, from: actions.text, label: Action list}
"""

EXAMPLE_TEXT = """\
schema_version: 1
id: polite-reply
name: Polite reply to a message
description: Writes a reply to a message you paste, checks its tone, and saves it.
inputs:
  - {id: message, type: text, multiline: true, label: The message you received}
  - {id: wish, type: text, required: false, label: What you want to say}
  - {id: model, type: provider, label: Model}
  - {id: language, type: language, label: Language of the answer}
nodes:
  - id: reply
    type: ai.cli
    label: Write the reply
    config:
      provider: "{{inputs.model}}"
      prompt: |
        Write a polite, short reply to the message below. Keep to what the sender asked.
        What I want to say: {{inputs.wish}}

        The message:
        {{inputs.message}}
  - id: tone
    type: ai.cli
    label: Check the tone
    config:
      provider: "{{inputs.model}}"
      prompt: |
        Read this draft reply. Fix anything that sounds rude, unclear or too long. Output only the final reply.
  - id: save
    type: document.export
    label: Save the reply
    config: {formats: [md]}
connections:
  - {from: reply.text, to: tone}
  - {from: tone.text, to: save}
outputs:
  - {id: reply, from: tone.text, label: Reply}
"""

RULES = """\
Rules of the workflow file (YAML):
- Top keys: schema_version (always 1), id (lower case letters, digits and "-"), name, description, inputs, nodes,
  connections, outputs. No other top keys. No comments.
- inputs: what the person fills in before a run. Each has id, type and label. Types: file (with formats; add
  "multiple: true" for several files), text (add "multiline: true" for a long text), choice (with options),
  provider (the AI model), language (the language of the answer). "required: false" makes an input optional.
- Always include exactly one provider input with id "model" and one language input with id "language".
- nodes: the steps. Each has id, type, label and config. Use only the node types listed below.
- connections: {from: <node id>.<output>, to: <node id>}. A step receives the texts of the steps connected to it.
  Every step except the first ones needs an incoming connection; every step's result must be used by a
  connection or be saved.
- Instruction-only style: the prompt of an AI step is a plain instruction, written to the model as you would brief
  a capable colleague: what to do, what to pay attention to, what the result looks like. Write it in paragraphs
  (a YAML "|" block): never break a line inside a sentence; start a new line only for a new paragraph or a list item. Never write
  {{nodes.<id>.<output>}} in a prompt: the connected texts are added after the instruction automatically.
  A text input of the run form is used with {{inputs.<id>}}. A file input is never used in a prompt: a
  document.extract step reads it (config.file: "{{inputs.<id>}}") and is connected to the step that needs the text.
- For extraction or review, say which input supports each finding and how to handle missing evidence.
  For a creative step, specify audience and format. For an approval, tell the reviewer what to check and
  what approving starts. Keep these instructions specific to the requested workflow.
- Every step that calls a model has provider: "{{inputs.model}}".
- Do not tell the model which language to answer in: the "language" input does that.
- End with one document.export step (config.formats, e.g. [md, docx]) connected from the step with the final text,
  and list that final text under outputs: {id, from: <node id>.text, label}.
- Use the fewest steps that do the job well (usually 3 to 6). Use ai.map only for long documents that must be
  processed part by part, a condition only when two different paths are really needed, an approval only when a
  person must check a text before the next step.
- ai.cli and ai.map receive text. Use document.extract to read a supplied file. If the task requires browsing
  named sites, use ai.agent with its sites and mode settings. Use read mode for research. For an explicitly
  requested site change, connect an approval before the agent in act mode.
"""


def draft_prompt(description: str, lang: str) -> str:
    return (
        f"{nodes.DATA_PREAMBLE}You write a workflow file for Mehteran, a program that runs AI workflows on a person's own "
        f"computer. A person described the workflow they want (the data block at the end). Write the complete "
        f"workflow file for it.\n\n{RULES}\nNode types (* marks a required setting):\n{schema_summary()}\n\n"
        f"Example 1:\n```yaml\n{EXAMPLE_DOCUMENT}```\n\nExample 2:\n```yaml\n{EXAMPLE_TEXT}```\n\n"
        f"Write name, description, every label and every prompt in {languages.english_name(lang)}. "
        f"Output only the YAML file in one ```yaml block, nothing before or after it.\n\n"
        f"The person's description of the workflow:\n{nodes.wrap_data('description', description)}")


# A change of a file that exists: the rules above are for a new draft (one model input, every text in the person's
# language); a built-in may check one model's answer with another and keep its instructions in English.
CHANGE_RULES = """\
Rules of a change (they come first; where the rules above say otherwise, follow these):
- Change only what the request asks for. Keep everything else exactly as it is: every input, and every step's id,
  label, prompt, provider and other settings, every connection and every output.
- Keep every provider input and the provider of every step, also when the file has several provider inputs (for
  example a second model that checks the first one). A new step that calls a model uses the first provider input.
- Keep the language and the wording of the existing texts. Write the texts that you add or that the change
  rewrites in {language}.
"""

PREVIOUS_LIMIT = 60_000  # characters of the current workflow file sent with a change


def change_prompt(change: str, previous: str, lang: str) -> str:
    """A change of a workflow that a model wrote before ("Change: make it shorter"): the same rules, the current file
    and the change, both as data."""
    return (
        f"{nodes.DATA_PREAMBLE}You change a workflow file for Mehteran, a program that runs AI workflows on a person's own "
        f"computer. The current file and the change the person asked for are the data blocks at the end. Write the "
        f"complete changed workflow file.\n\n{RULES}\n"
        f"Node types (* marks a required setting):\n{schema_summary()}\n\n"
        f"{CHANGE_RULES.format(language=languages.english_name(lang))}\n"
        f"Output only the YAML file in one ```yaml block, nothing before or after it.\n\n"
        f"The current workflow file:\n{nodes.wrap_data('current_workflow', previous[:PREVIOUS_LIMIT])}\n\n"
        f"The change the person asked for:\n{nodes.wrap_data('change', change)}")


def repair_prompt(first: str, answer: str, problems: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in problems[:40])
    return (f"{first}\n\nYour previous answer was:\n{nodes.wrap_data('previous_answer', answer[:60_000])}\n\n"
            f"It does not pass the check of the workflow file. The problems:\n{listed}\n\n"
            f"Write the complete corrected YAML file again, in one ```yaml block, nothing before or after it.")


# --- the draft: the answer ------------------------------------------------------------------------------------

FENCE = re.compile(r"```[ \t]*(?:ya?ml)?[ \t]*\r?\n(.*?)(?:\r?\n)?```", re.S | re.I)


def extract_yaml(answer: str) -> str:
    """The YAML text of an answer: the largest fenced block that has "schema_version", else the text from the line
    that starts with "schema_version", else the answer as it is."""
    blocks = [m.group(1) for m in FENCE.finditer(answer) if "schema_version" in m.group(1)]
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    m = re.search(r"^schema_version\s*:", answer, re.M)
    return (answer[m.start():] if m else answer).strip() + "\n"


def slug(text: str) -> str:
    """A workflow id made from a name: Latin letters and digits, "-" for the rest ("workflow" when nothing is left)."""
    import unicodedata
    folded = unicodedata.normalize("NFD", str(text).replace("İ", "i").replace("I", "i").replace("ı", "i").lower())
    out = re.sub(r"[^a-z0-9]+", "-", "".join(c for c in folded if not unicodedata.combining(c)))
    return re.sub(r"^[^a-z]+", "", out).strip("-")[:56].strip("-") or "workflow"


def normalize(data, taken: set[str], provider: str, previous: dict | None = None):
    """Forces the style of a draft on the parsed answer, where its form allows (anything else is left for the check):
    no layout or based_on, a free id, one model input that every model step uses, a "language" input.
    previous (the parsed workflow that was changed): a change instead. Every step keeps the model it has (a workflow
    may check one model's answer with another); only a new model step without one gets the first model input. The
    layout of the steps that are still there and based_on come from previous; the language input is not touched."""
    if not isinstance(data, dict):
        return data
    data = copy.deepcopy(data)
    for key in ("layout", "based_on"):
        data.pop(key, None)
    if previous is not None:
        if isinstance(previous.get("based_on"), str):
            data["based_on"] = previous["based_on"]
        steps = data.get("nodes") if isinstance(data.get("nodes"), list) else []
        kept = {node.get("id") for node in steps if isinstance(node, dict)}
        layout = previous.get("layout") if isinstance(previous.get("layout"), dict) else {}
        if layout := {k: v for k, v in layout.items() if k in kept}:
            data["layout"] = layout
    data.setdefault("schema_version", schema.SCHEMA_VERSION)
    name = i18n.localized(data.get("name")) if isinstance(data.get("name"), (str, dict)) else ""
    base = data["id"] if isinstance(data.get("id"), str) and nodes.ID_RE.match(data["id"]) else slug(name)
    data["id"] = base
    for k in range(2, 1000):
        if data["id"] not in taken:
            break
        data["id"] = f"{base[:60]}-{k}"
    if data.get("inputs") is None:
        data["inputs"] = []
    inputs, steps = data["inputs"], data.get("nodes")
    if not isinstance(inputs, list) or not isinstance(steps, list):
        return data
    ids = {item.get("id") for item in inputs if isinstance(item, dict)}

    def free(wanted: str) -> str:
        return next(x for x in [wanted, *(f"{wanted}{k}" for k in range(2, 99))] if x not in ids)

    # the model: one provider input; every step that calls a model takes it
    calls = [node for node in steps if isinstance(node, dict) and isinstance(node.get("config"), dict)
             and "provider" in getattr(nodes.REGISTRY.get(node.get("type")) if isinstance(node.get("type"), str) else None,
                                       "config", {})
             and (node["type"] != "condition" or node["config"].get("operator") == "ai")]
    if calls and previous is not None:  # a change: only a model step without a model gets one
        missing = [node for node in calls if not str(node["config"].get("provider") or "").strip()]
        model = next((item for item in inputs if isinstance(item, dict) and item.get("type") == "provider"
                      and isinstance(item.get("id"), str)), None)
        for node in missing:
            node["config"]["provider"] = "{{inputs.%s}}" % model["id"] if model else "auto"
        return data
    if calls:
        model = next((item for item in inputs if isinstance(item, dict) and item.get("type") == "provider"
                      and isinstance(item.get("id"), str)), None)
        if model is None:
            model = {"id": free("model"), "type": "provider", "label": {"tr": "Model", "en": "Model"}}
            inputs.append(model)
            ids.add(model["id"])
        # `auto` (stream P): the user's model order; a draft written by a local model stays local by default
        from . import providers as adapters
        name, sub, _ = adapters.split(provider)
        model["default"] = "auto:local" if adapters.destination(name, sub)["local"] and name in adapters.ADAPTERS else "auto"
        model.pop("required", None)
        for node in calls:
            node["config"]["provider"] = "{{inputs.%s}}" % model["id"]
    if previous is not None:
        return data
    # the language of the answer: an input "language" of type language (nodes.language_line reads that id)
    language = next((item for item in inputs if isinstance(item, dict) and item.get("type") == "language"), None)
    named = next((item for item in inputs if isinstance(item, dict) and item.get("id") == "language"), None)
    if language is None and named is not None:  # e.g. a choice of languages: every language of the registry instead
        for key in ("options", "default", "multiline", "formats", "multiple"):
            named.pop(key, None)
        named["type"] = "language"
    elif language is None:
        inputs.append({"id": "language", "type": "language", "label": {"tr": "Cevabın dili", "en": "Language of the answer"}})
    elif named is None and isinstance(language.get("id"), str):
        try:
            data = schema.rename(data, "inputs", language["id"], "language")
        except schema.WorkflowError:
            pass
    return data


def _problems(error: schema.WorkflowError, lang: str) -> list[str]:
    """The problems as text in lang (the repair turn reads them in English; the page in its own language)."""
    before = i18n.current()
    i18n.set_request(lang)
    try:
        return [str(p.message()) for p in error.problems]
    finally:
        i18n.set_request(before)


def read_answer(answer: str, taken: set[str], provider: str, previous: dict | None = None) -> dict:
    """An answer -> {"valid", "model", "yaml", "problems" (in the request's language), "english" (for the repair)}.
    previous: the parsed workflow that the answer changes (normalize)."""
    text = extract_yaml(answer)
    try:
        if len(text) > 1_000_000:
            raise schema.WorkflowError([schema.Problem("", "yaml_too_large")])
        try:
            data = yamlio.load(text)
        except yamlio.YAMLError as e:
            raise schema.WorkflowError([schema.Problem("", "yaml_invalid", {"error": e})]) from None
        if not isinstance(data, dict):
            raise schema.WorkflowError([schema.Problem("", "not_a_mapping")])
    except schema.WorkflowError as e:
        return {"valid": False, "model": None, "yaml": text, "problems": _problems(e, i18n.current()),
                "english": _problems(e, "en")}
    data = normalize(data, taken, provider, previous)
    try:
        text = schema.dump(data)
    except Exception:  # noqa: BLE001 - a form the writer does not know: the answer's own text is shown
        pass
    try:
        schema.check(copy.deepcopy(data))
    except schema.WorkflowError as e:
        return {"valid": False, "model": data, "yaml": text, "problems": _problems(e, i18n.current()),
                "english": _problems(e, "en")}
    return {"valid": True, "model": data, "yaml": text, "problems": [], "english": []}


def draft(description: str, provider: str, taken: set[str], ask_model, lang: str | None = None, previous: str = "") -> dict:
    """The draft of a workflow for a description. ask_model(prompt, stem) -> the model's answer (one call each time).
    At most two calls: the draft, and one repair when the draft does not pass the check. previous: the YAML of a
    workflow to change; the description is then the change asked for."""
    description = str(description or "").strip()
    if not description:
        raise DraftError(t("draft_needs_description"))
    if len(description) > DESCRIPTION_LIMIT:
        raise DraftError(t("draft_too_long", limit=DESCRIPTION_LIMIT))
    lang = lang or i18n.current()
    previous = str(previous or "").strip()
    prompt = change_prompt(description, previous, lang) if previous else draft_prompt(description, lang)
    try:
        changed = yamlio.load(previous) if previous else None
    except yamlio.YAMLError:
        changed = None
    changed = changed if isinstance(changed, dict) else ({} if previous else None)
    answer = ask_model(prompt, "draft-1")
    found, calls = read_answer(answer, taken, provider, changed), 1
    if not found["valid"]:
        answer = ask_model(repair_prompt(prompt, answer, found["english"]), "draft-2")
        found, calls = read_answer(answer, taken, provider, changed), 2
    found.pop("english")
    return {**found, "calls": calls, "provider": provider}


def start_draft(jobs: Jobs, engine, description: str, provider: str, taken: set[str], previous: str = "") -> str:
    provider = checked_provider(engine, provider)
    description = str(description or "").strip()
    if not description:
        raise DraftError(t("draft_needs_description"))
    if len(description) > DESCRIPTION_LIMIT:
        raise DraftError(t("draft_too_long", limit=DESCRIPTION_LIMIT))
    return jobs.start("draft", lambda job: draft(description, provider, taken,
                                                  lambda prompt, stem: ask(engine, job, provider, prompt, stem),
                                                  previous=previous))


# --- "Test this step" ---------------------------------------------------------------------------------------

def _source_run(engine, wf: schema.Workflow, node_id: str, refs: list[str]) -> dict | None:
    """The newest run of one of the templates refs ("user:<id>") in which every step connected to node_id finished
    with an output."""
    refs = [r for r in refs if isinstance(r, str) and r]
    for run in engine.store.runs():
        if run["template"] not in refs:
            continue
        done = engine.store.nodes(run["id"])
        if all(done.get(up, {}).get("status") == "succeeded" and done[up].get("outputs") for up in wf.upstream[node_id]):
            return run
    return None


def _try_node(wf: schema.Workflow, node_id: str) -> dict:
    node = wf.nodes.get(node_id)
    if node is None:
        raise DraftError(t("unknown_node", id=node_id))
    if node["type"] not in TRYABLE or (node["type"] == "condition" and (node.get("config") or {}).get("operator") != "ai"):
        raise DraftError(t("try_not_supported"))
    return node


def _default_provider(wf: schema.Workflow, node: dict, run: dict | None) -> str:
    """The model the step would use: the run's value of its model input, else the input's default."""
    value = str((node.get("config") or {}).get("provider") or "").strip()
    ref = placeholders.only_reference(value)
    if ref is None:
        return value
    input_id = ref[7:]
    return str((run or {}).get("inputs", {}).get(input_id) or wf.inputs.get(input_id, {}).get("default") or "")


def try_source(engine, model: dict, node_id: str, refs: list[str]) -> dict:
    """What a test of this step would use: the source run (or none) and the model."""
    wf = schema.check(copy.deepcopy(model))
    node = _try_node(wf, node_id)
    found = _source_run(engine, wf, node_id, refs)
    run = engine.store.run(found["id"]) if found else None
    return {"run": {"id": found["id"], "created": found["created"], "status": found["status"]} if found else None,
            "upstream": [i18n.localized(wf.nodes[up].get("label")) or up for up in sorted(wf.upstream[node_id])],
            "provider": _default_provider(wf, node, run)}


def start_try(jobs: Jobs, engine, model: dict, node_id: str, provider: str, run_id: str = "", sample: str | None = None) -> str:
    """Runs one step alone. The texts of the steps connected to it come from the run run_id (their stored outputs),
    or are all the pasted sample. Nothing of that run changes."""
    wf = schema.check(copy.deepcopy(model))
    node = _try_node(wf, node_id)
    provider = checked_provider(engine, provider)
    lang = i18n.current()
    run = nodes_of = run_dir = None
    if sample is None:
        run = engine.get(run_id)  # RunError for an unknown id
        nodes_of, run_dir = run["nodes"], engine.run_dir(run_id)
    elif len(sample) > schema.TEXT_LIMIT:
        raise DraftError(t("input_too_long", id="sample"))

    def value(ref: str) -> str:
        kind, ident, port = placeholders.parse(ref)
        if kind == "inputs":
            spec = wf.inputs[ident]
            if spec["type"] == "file":
                return ""
            given = (run or {}).get("inputs", {}).get(ident) if run else None
            if isinstance(given, str) and given:
                return given
            if spec["type"] == "language":
                return spec.get("default") or lang
            if spec["type"] == "text" and sample is not None and not wf.upstream[node_id]:
                return sample  # a step that reads only the run form: the sample stands for the typed text
            return i18n.localized(spec.get("default"), lang)
        if sample is not None:
            return sample
        rel = (nodes_of.get(ident) or {}).get("outputs", {}).get(port)
        path = paths.inside(run_dir, rel) if rel else None
        if path is None or not path.is_file():
            raise nodes.NodeError(t("output_missing", ref=ref))
        return str(path) if wf.ports(ident).get(port) == "file" else path.read_text(encoding="utf-8")

    def wrapped(ref: str) -> str:
        text = value(ref)
        return nodes.wrap_data(ref, text) if ref.startswith("nodes.") else text

    def work(job: Job) -> dict:
        cfg = engine.provider_cfg
        name = provider.partition("@")[0].partition("/")[0]
        ctx = nodes.Ctx(run_dir=job.folder, node_dir=job.folder / "node", node_id=node_id, config=node.get("config") or {},
                        value=value, wrapped=wrapped, provider=provider,
                        provider_cfg={"providers": {name: cfg["providers"][name]}, "general": cfg["general"]},
                        abort=job.abort, timeout=node.get("timeout", cfg["general"].get("timeout", 1200)), attempt=1,
                        lang=lang, upstream=lambda: engine._upstream({"lang": lang}, wf, node_id),
                        input_types={i: spec["type"] for i, spec in wf.inputs.items()},
                        record=_recorder(engine, job), log=job.log)
        outputs = nodes.REGISTRY[node["type"]].run(ctx)
        if node["type"] == "condition":  # the branch taken; the model's own words are in the step's answer file
            answer = ctx.node_dir / "answer.md"
            return {"branch": next(iter(outputs)), "text": answer.read_text(encoding="utf-8") if answer.is_file() else "",
                    "provider": provider}
        return {"text": str(outputs.get("text", ""))[:ANSWER_LIMIT], "provider": provider}

    return jobs.start("try", work)
