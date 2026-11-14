"""The run history and its automation: names and notes, deleting runs, batches ("once per file") and saving the
results of a run to a folder of the user's choice.

- A run's main input (the first file name, or the start of the first text or address input) is computed once from
  its stored inputs and kept in the runs table (main_input).
- Deleting removes the database rows and the run folder. Only a finished run that nobody drives is deleted: the run
  lock (executions/<run>/.lock) is taken first, and only paths inside the data folder's executions/ are removed.
- A batch is N runs of one workflow, one per chosen file. They are created "queued" and started BATCH_PARALLEL at a
  time by the Automation thread of the web server.
- Saving to a folder: after a run succeeded, its results are copied into the folder. Nothing is overwritten (a name
  that exists gets " (2)", " (3)", ...). The folder must be an absolute path to an existing, writable folder that is
  not a system folder, not the program's folder and not the data folder.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from pipeline import system

from . import paths, schema, yamlio
from .engine import RunError, _as_list, safe_filename
from .i18n import t
from .store import FINISHED_RUN

BATCH_PARALLEL = 2  # runs of one batch at once (no per-provider limit exists yet to follow)
MAX_BATCH = 50      # files of one batch
LABEL_LIMIT, NOTE_LIMIT = 120, 2000
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


# --- the main input of a run -------------------------------------------------------------------------

def main_input(inputs: dict, workflow_yaml: str) -> str:
    """The first file name of the run, else the first 40 characters of its first text (or address) input."""
    try:
        specs = (yamlio.load(workflow_yaml) or {}).get("inputs") or []
    except yamlio.YAMLError:
        specs = []
    kinds = {s.get("id"): s.get("type") for s in specs if isinstance(s, dict)}
    for key, kind in kinds.items():
        if kind == "file":
            names = [Path(str(rel)).name for rel in _as_list(inputs.get(key)) if rel]
            if names:
                return names[0] + (f" +{len(names) - 1}" if len(names) > 1 else "")
    for key, kind in kinds.items():
        value = inputs.get(key)
        if kind in ("text", "url") and isinstance(value, str) and value.strip():
            text = " ".join(value.split())
            return text[:40].rstrip() + ("…" if len(text) > 40 else "")
    return ""


def fill_main_inputs(store) -> None:
    """main_input of the runs that do not have it yet (runs made before it, or just created)."""
    for row in store._rows("SELECT id, inputs, workflow_yaml FROM runs WHERE main_input IS NULL"):
        try:
            value = main_input(json.loads(row["inputs"] or "{}"), row["workflow_yaml"] or "")
        except ValueError:
            value = ""
        store.update_run(row["id"], main_input=value)


def listing(engine) -> list[dict]:
    """engine.list() with the history fields; output_state parsed."""
    fill_main_inputs(engine.store)
    runs = engine.list()
    for run in runs:
        try:
            run["output_state"] = json.loads(run["output_state"]) if run.get("output_state") else None
        except ValueError:
            run["output_state"] = None
    return runs


# --- name and note -------------------------------------------------------------------------------------

def clean_text(value, limit: int, multiline: bool = False) -> str:
    text = CONTROL.sub("", str(value or "")).replace("\r\n", "\n")
    if not multiline:
        text = " ".join(text.split())
    if len(text) > limit:
        raise RunError([t("label_too_long", limit=limit)])
    return text.strip()


def set_label(engine, run_id: str, label, note) -> dict:
    engine.get(run_id)  # the run exists
    fields = {"label": clean_text(label, LABEL_LIMIT) or None, "note": clean_text(note, NOTE_LIMIT, True) or None}
    engine.store.update_run(run_id, **fields)
    return fields


# --- deleting ---------------------------------------------------------------------------------------------

def folder_size(folder: Path) -> int:
    """The bytes of the files under folder (links are not followed)."""
    total = 0
    for root, dirs, files in os.walk(folder, followlinks=False):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def _run_folder(engine, run_id: str) -> Path | None:
    """The run's folder inside <data>/executions (None when it is missing or is a link)."""
    base = engine.home / "executions"
    folder = engine.run_dir(run_id)
    if folder.is_symlink() or not folder.is_dir():
        return None
    inside = paths.inside(base, run_id)
    if inside is None or inside != folder.resolve() or inside.parent != base.resolve():
        raise RunError([t("run_delete_unsafe")])
    return folder


def run_size(engine, run_id: str) -> int:
    folder = _run_folder(engine, run_id)
    return folder_size(folder) if folder else 0


def deletable(engine, run: dict) -> bool:
    return run["status"] in FINISHED_RUN and not engine.is_active(run["id"])


def delete_run(engine, run_id: str) -> int:
    """Deletes a finished run that nobody drives: its rows and its folder. Returns the bytes freed."""
    run = engine.get(run_id)
    if not deletable(engine, run):
        raise RunError([t("run_delete_active")])
    folder = _run_folder(engine, run_id)
    if folder is not None and folder.is_symlink():
        raise RunError([t("run_delete_unsafe")])
    handle = open(folder / ".lock", "a+") if folder else None
    try:
        if handle and not system.try_lock(handle):
            raise RunError([t("run_delete_active")])
        # A resume may have come between the check above and the lock.
        if engine.store.run(run_id)["status"] not in FINISHED_RUN or engine.thread_alive(run_id):
            raise RunError([t("run_delete_active")])
        size = folder_size(folder) if folder else 0
        engine.store.delete_run(run_id)
        if folder:
            for child in folder.iterdir():
                if child.name == ".lock":
                    continue
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
    finally:
        if handle:
            handle.close()
    if folder:
        (folder / ".lock").unlink(missing_ok=True)
        shutil.rmtree(folder, ignore_errors=True)
    return size


def old_runs(engine, days: int) -> list[dict]:
    """The finished runs that ended (or were created) more than days ago."""
    cutoff = time.time() - days * 86400
    rows = engine.store._rows("SELECT id, status, created, finished FROM runs WHERE COALESCE(finished, created) < ?",
                              (cutoff,))
    return [row for row in rows if row["status"] in FINISHED_RUN]


def cleanup(engine, days: int, dry_run: bool) -> dict:
    """Deletes (or with dry_run only counts) the finished runs older than days. Active runs are kept."""
    found = [row for row in old_runs(engine, days) if not engine.is_active(row["id"])]
    if dry_run:
        return {"count": len(found), "size": sum(run_size(engine, row["id"]) for row in found)}
    deleted, size, kept = 0, 0, 0
    for row in found:
        try:
            size += delete_run(engine, row["id"])
            deleted += 1
        except (RunError, OSError):
            kept += 1
    return {"deleted": deleted, "size": size, "kept": kept}


# --- the folder to save results to ------------------------------------------------------------------------

def _system_folders() -> list[Path]:
    if sys.platform == "win32":
        names = [os.environ.get(k) for k in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData")]
        return [Path(n) for n in names if n]
    return [Path(p) for p in ("/bin", "/sbin", "/usr", "/etc", "/var", "/private", "/System", "/Library",
                              "/Applications", "/dev", "/opt", "/boot", "/proc", "/sys", "/root", "/lib", "/lib64",
                              "/snap", "/srv", "/run", "/cores", "/Network")]


def _within(path: Path, base: Path) -> bool:
    try:
        base = base.resolve()
    except OSError:
        return False
    return path == base or path.is_relative_to(base)


def folder_problem(text, home: Path) -> tuple[Path | None, str | None]:
    """(the folder, None) when results may be saved there; else (None, the reason)."""
    value = str(text or "").strip()
    if not value or len(value) > 1000 or "\x00" in value:
        return None, t("folder_not_absolute")
    path = Path(value).expanduser()
    if not path.is_absolute():
        return None, t("folder_not_absolute")
    try:
        path = path.resolve()
    except OSError:
        return None, t("folder_missing", path=value)
    if not path.is_dir():
        return None, t("folder_missing", path=str(path))
    if _within(path, paths.REPO) or _within(path, home):
        return None, t("folder_app", path=str(path))
    temp = [Path(tempfile.gettempdir())] + ([Path("/tmp")] if sys.platform != "win32" else [])  # inside a temp folder
    allowed = _within(path, Path.home()) and path != Path.home().resolve() or any(_within(path, p) and path != p.resolve()
                                                                               for p in temp)
    root = Path(path.anchor)
    if path == root or (not allowed and any(_within(path, s) for s in _system_folders())) \
            or (_within(path, Path.home() / "Library") and sys.platform == "darwin"):
        return None, t("folder_system", path=str(path))
    if not os.access(path, os.W_OK):
        return None, t("folder_not_writable", path=str(path))
    return path, None


def unique_target(folder: Path, name: str) -> Path:
    """folder/name, or folder/"name (2).ext", ... for a name that is taken. Created empty, so no other run takes it."""
    name = safe_filename(name)
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    for n in range(1, 1000):
        candidate = folder / (name if n == 1 else f"{stem} ({n})" + (f".{ext}" if ext else ""))
        try:
            with open(candidate, "xb"):  # exclusive: an existing file (or link) is never opened
                return candidate
        except FileExistsError:
            continue
    raise OSError("no free name")


def results(engine, run: dict) -> list[tuple[str, str]]:
    """(name for the folder, path in the run folder) of each result: the workflow's outputs, or else the files that
    its steps saved (as the run page shows them)."""
    wf = schema.parse(run["workflow_yaml"])
    out = []
    for item in wf.data.get("outputs") or []:
        node, _, port = item["from"].partition(".")
        rel = (run["nodes"].get(node) or {}).get("outputs", {}).get(port)
        if rel:
            suffix = Path(rel).suffix
            out.append((f"{item['id']}{suffix}" if Path(rel).name == f"{port}.md" else Path(rel).name, rel))
    if out:
        return out
    for node_id in wf.order:
        for port, rel in ((run["nodes"].get(node_id) or {}).get("outputs") or {}).items():
            if wf.ports(node_id).get(port) == "file":
                out.append((Path(rel).name, rel))
    return out


def save_results(engine, run_id: str, folder_text: str) -> dict:
    """Copies the results of a succeeded run into the folder. {"saved": [names]} or {"error": text}."""
    folder, problem = folder_problem(folder_text, engine.home)
    if problem:
        return {"error": str(problem), "folder": folder_text}
    run = engine.get(run_id)
    prefix = ""
    if run.get("batch"):
        stem = Path(run.get("main_input") or main_input(run["inputs"], run["workflow_yaml"])).stem or run_id
        prefix = f"{stem} - "
    saved = []
    try:
        for name, rel in results(engine, run):
            source = engine.artifact(run_id, rel)
            target = unique_target(folder, prefix + name)
            with open(source, "rb") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            saved.append(target.name)
    except (OSError, RunError) as e:
        return {"error": str(e), "folder": str(folder), "saved": saved}
    return {"saved": saved, "folder": str(folder)}


# --- the automation thread of the web server: batch starts and saves after success -------------------------

class Automation:
    def __init__(self, engine):
        self.engine = engine
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.again = False
        self.launched: set[str] = set()
        self.interval = 1.0

    def kick(self) -> None:
        with self.lock:
            if self.thread and self.thread.is_alive():
                self.again = True
                return
            self.thread = threading.Thread(target=self._loop, name="mehteran-automation", daemon=True)
            self.thread.start()

    def _loop(self) -> None:
        while True:
            try:
                more = self.step()
            except Exception as e:  # noqa: BLE001 - the thread must not die; shown in the terminal
                print(f"[mehteran automation] {type(e).__name__}: {e}", flush=True)
                more = True
            with self.lock:
                if not more and not self.again:
                    self.thread = None
                    return
                self.again = False
            time.sleep(self.interval)

    def step(self) -> bool:
        """One pass. True while there is something to wait for."""
        store = self.engine.store
        finished = tuple(FINISHED_RUN)
        marks = ",".join("?" * len(finished))
        # Saves: each succeeded run with a folder, once.
        for row in store._rows("SELECT id, output_dir FROM runs WHERE output_dir IS NOT NULL AND output_state IS NULL "
                               "AND status='succeeded'"):
            state = save_results(self.engine, row["id"], row["output_dir"])
            store.update_run(row["id"], output_state=json.dumps(state, ensure_ascii=False))
        # Batches: start the queued runs, BATCH_PARALLEL at a time.
        rows = store._rows(f"SELECT id, batch, status FROM runs WHERE batch IS NOT NULL AND status NOT IN ({marks}) "
                           "ORDER BY created, id", finished)
        groups: dict[str, list[dict]] = {}
        for row in rows:
            groups.setdefault(row["batch"], []).append(row)
        for runs in groups.values():
            busy = [r for r in runs if r["status"] == "running" or self.engine.is_active(r["id"])
                    or (r["status"] == "queued" and r["id"] in self.launched)]
            waiting = [r for r in runs if r["status"] == "queued" and r not in busy]
            for row in waiting[:max(0, BATCH_PARALLEL - len(busy))]:
                self.launched.add(row["id"])
                self.engine.launch(row["id"])
        self.launched &= {r["id"] for r in rows if r["status"] == "queued"}
        pending = store._rows(f"SELECT COUNT(*) AS n FROM runs WHERE output_dir IS NOT NULL AND output_state IS NULL "
                              f"AND status NOT IN ({marks})", finished)[0]["n"]
        return bool(rows) or bool(pending)


def start_batch(engine, text: str, template: str, values: dict, shared: dict, input_id: str, files: list[Path],
                output_dir: str | None) -> tuple[str, list[str]]:
    """N queued runs of the workflow, one per file of input_id (a single-file input); the other file inputs (shared)
    go to every run. Returns the batch id and the run ids. The Automation starts them."""
    import secrets
    wf = schema.parse(text)
    spec = wf.inputs.get(input_id)
    if not spec or spec["type"] != "file" or spec.get("multiple"):
        raise RunError([t("batch_bad_input", id=input_id)])
    if not 1 <= len(files) <= MAX_BATCH:
        raise RunError([t("batch_too_many", limit=MAX_BATCH)])
    formats = spec.get("formats", list(schema.FILE_FORMATS))
    for path in files:
        if path.suffix.lower().lstrip(".") not in formats:
            raise RunError([t("input_bad_format", id=input_id, formats=", ".join(formats))])
    batch = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    created: list[str] = []
    try:
        for path in files:
            run_id = engine.start(text, values, {**shared, input_id: path}, template=template, launch=False)
            created.append(run_id)
            engine.store.update_run(run_id, batch=batch, output_dir=output_dir)
    except BaseException:
        for run_id in created:  # never launched: nobody holds them
            engine.store.delete_run(run_id)
            shutil.rmtree(engine.run_dir(run_id), ignore_errors=True)
        raise
    return batch, created
