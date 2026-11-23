"""HTTP endpoints for run history and local storage."""

import shutil
import time

from . import history
from .engine import display_name
from .http_errors import HTTPError
from .i18n import t


def run_list(app, m, body) -> list:
    return history.listing(app.engine, body.get("before", ""), body.get("q", "")[:200].strip())


def run_label(app, m, body) -> dict:
    return history.set_label(app.engine, m[1], body.get("label"), body.get("note"))


def run_delete(app, m, body) -> dict:
    """{"dry_run": true}: the size and whether it can be deleted; else deletes the run and its files."""
    if body.get("dry_run") is True:
        run = app.engine.get(m[1])
        return {"size": history.run_size(app.engine, m[1]), "deletable": history.deletable(app.engine, run)}
    if body.get("trash") is True:
        history.trash_run(app.engine, m[1])
        return {"trashed": True}
    return {"deleted": True, "size": history.delete_run(app.engine, m[1])}


def run_trash(app, m, body) -> list:
    return [{"id": r["id"], "name": r["label"] or r["main_input"] or display_name(r["workflow_name"])}
            for r in app.engine.store.runs(trash=True)]


def storage(app, m, body) -> dict:
    return {"used": history.folder_size(app.home), "free": shutil.disk_usage(app.home).free}


def run_restore(app, m, body) -> dict:
    if not app.engine.store.restore_run(m[1]):
        raise HTTPError(404, t("not_found"))
    app.automation.kick()
    return {"ok": True}


def run_cleanup(app, m, body) -> dict:
    days = body.get("days")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 3650:
        raise HTTPError(400, t("bad_request"))
    dry_run = body.get("dry_run") is True
    result = history.cleanup(app.engine, days, dry_run)
    if not dry_run and body.get("prune_usage") is True:
        result["calls_deleted"] = app.engine.store.prune_calls(time.time() - days * 86400)
    return result


def routes(run: str) -> list:
    return [
        ("GET", r"/api/runs", run_list),
        ("GET", r"/api/runs/trash", run_trash),
        ("GET", r"/api/storage", storage),
        ("POST", rf"/api/runs/{run}/restore", run_restore),
        ("PUT", rf"/api/runs/{run}/label", run_label),
        ("DELETE", rf"/api/runs/{run}", run_delete),
        ("POST", r"/api/runs/cleanup", run_cleanup),
    ]
