"""Command line: python -m mehteran <command>   (launchers: ./mehter, mehter.cmd)

  ui [--port 8766] [--no-browser]      the web interface
  templates                            the template library
  validate <file.yaml>                 checks a workflow file and lists every problem
  run <template or file> --input k=v   runs a workflow in the foreground (file inputs: k=path/to/file; an input
                                       with "multiple: true" takes --input k=... once per file)
  runs                                 the run history
  resume <run> [--node <id>]           continues a run (or retries one failed node)
  cancel <run>                         stops a run
  approve|reject <run> <node>          decides a waiting approval node
  install <tool> ...                   installs tools into <code folder>/.runtime, shared with the translation app
                                       (used by the Setup tab; pipeline.runtime does the work)
  install-local ollama|ocr|ocr-languages|typst|pandoc|speech|speech-models|qpdf [name ...]
                                       installs Ollama, Tesseract OCR (and OCR languages), Typst, Pandoc, whisper.cpp
                                       (and speech models) or qpdf into the same .runtime (pinned versions, checked
                                       SHA-256 sums; started by the Setup tab)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from . import i18n, paths, schema, templates
from .engine import Engine, RunError
from .i18n import localized, t

EXIT = {"succeeded": 0, "waiting_approval": 3}


def _print(text: str = "") -> None:
    print(text, flush=True)


def _workflow_text(ref: str, home: Path) -> tuple[str, str]:
    """(YAML text, template ref) of a file path or a template id."""
    path = Path(ref)
    if path.suffix.lower() in (".yaml", ".yml") and path.is_file():
        return path.read_text(encoding="utf-8"), ""
    source, template_id = templates.resolve(ref, home)
    return templates.read(source, template_id, home), f"{source}:{template_id}"


def _follow(engine: Engine, run_id: str) -> int:
    """Prints node status changes until the run ends or waits for a person. Ctrl+C cancels the run."""
    shown: dict[str, str] = {}
    try:
        while True:
            run = engine.get(run_id)
            for node_id, info in run["nodes"].items():
                if shown.get(node_id) != info["status"]:
                    shown[node_id] = info["status"]
                    extra = f" ({info['error']})" if info["error"] and info["status"] != "succeeded" else ""
                    _print(t("cli_node", node=node_id, status=t("status_" + info["status"])) + extra)
            if run["status"] in ("succeeded", "failed", "cancelled", "interrupted", "waiting_approval") \
                    and not engine.thread_alive(run_id):
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        _print(t("cli_stopping"))
        engine.cancel(run_id)
        engine.wait(run_id, timeout=30)
        run = engine.get(run_id)
    if run["status"] == "waiting_approval":
        for node_id, info in run["nodes"].items():
            if info["status"] == "waiting_approval":
                _print(t("cli_waiting", node=node_id, run=run_id,
                         path=engine.run_dir(run_id) / info["outputs"].get("text", "")))
    _print(t("cli_result", status=t("status_" + run["status"]), path=engine.run_dir(run_id)))
    if run["error"]:
        _print(run["error"])
    return EXIT.get(run["status"], 1)


def cmd_ui(args, home: Path) -> int:
    from .web import serve
    serve(port=args.port, open_browser=not args.no_browser)
    return 0


def cmd_templates(args, home: Path) -> int:
    for item in templates.listing(home):
        mark = "" if item["valid"] else "  [!]"
        _print(f"{item['ref']:45} {localized(item.get('name'))}{mark}")
    return 0


def cmd_validate(args, home: Path) -> int:
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        _print(f"{t('cli_error')}: {e}")
        return 1
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        _print(t("cli_invalid", count=len(e.problems)))
        for message in e.messages():
            _print(f"- {message}")
        return 1
    _print(t("cli_valid", id=wf.id, nodes=len(wf.nodes)))
    return 0


def cmd_run(args, home: Path) -> int:
    text, ref = _workflow_text(args.workflow, home)
    wf = schema.parse(text)
    values, files = {}, {}
    for item in args.input or []:
        key, sep, value = item.partition("=")
        if not sep:
            _print(t("cli_bad_input", value=item))
            return 2
        if key in wf.inputs and wf.inputs[key]["type"] == "file" and wf.inputs[key].get("multiple"):
            files.setdefault(key, []).append(Path(value).expanduser())  # --input docs=a.pdf --input docs=b.pdf
        elif key in wf.inputs and wf.inputs[key]["type"] == "file":
            files[key] = [*files[key], Path(value).expanduser()] if key in files else Path(value).expanduser()
        else:
            values[key] = value
    engine = Engine(home)
    run_id = engine.start(text, values, files, template=ref)
    _print(t("cli_started", id=run_id))
    return _follow(engine, run_id)


def cmd_runs(args, home: Path) -> int:
    runs = Engine(home).list()
    if not runs:
        _print(t("cli_no_runs"))
    for run in runs:
        created = time.strftime("%Y-%m-%d %H:%M", time.localtime(run["created"]))
        _print(f"{run['id']}  {created}  {t('status_' + run['status']):18} {run['workflow_name']}")
    return 0


def cmd_resume(args, home: Path) -> int:
    engine = Engine(home)
    engine.resume(args.run, args.node)
    return _follow(engine, args.run)


def cmd_cancel(args, home: Path) -> int:
    Engine(home).cancel(args.run)
    _print(t("cli_cancel_sent", id=args.run))
    return 0


def cmd_decide(args, home: Path) -> int:
    engine = Engine(home)
    engine.decide(args.run, args.node, args.command == "approve", args.comment or "")
    return _follow(engine, args.run)


def cmd_install(args, home: Path) -> int:
    """The translation app's installer (pipeline.runtime, read-only) without loading its project: that may write
    the translation app's config.toml, which Mehteran never changes."""
    from pipeline import i18n as pipeline_i18n
    from pipeline import runtime, tools
    from pipeline.core import ROOT, PipelineError
    pipeline_i18n.set_default(i18n.pipeline_lang())
    tools.extend_path(ROOT)
    for tool in args.tools:
        name = pipeline_i18n.t(f"tool_name_{tool}") if tools.TOOLS[tool]["provider"] is None else tools.TOOLS[tool]["name"]
        _print(f"=== {name} ===")
        try:
            runtime.install_tool(tool, ROOT)
        except PipelineError as e:
            _print(f"{t('cli_error')}: {e}")
            return 1
        tools.extend_path(ROOT)
        _print(t("tool_installed", name=name))
    return 0


LOCAL_TARGETS = ["ollama", "ocr", "ocr-languages", "typst", "pandoc", "speech", "speech-models", "qpdf"]


def cmd_install_local(args, home: Path) -> int:
    from pipeline import i18n as pipeline_i18n

    from . import ocr, ollama, pandoc, qpdf, speech, typst
    pipeline_i18n.set_default(i18n.pipeline_lang())  # the download progress of pipeline.runtime: Turkish or English
    try:
        if args.target == "ollama":
            ollama.install()
        elif args.target == "ocr":
            ocr.install(args.names or None)
        elif args.target == "ocr-languages":
            ocr.install_languages(args.names or ocr.DEFAULT_LANGUAGES)
        elif args.target == "speech":
            speech.install(args.names or None)
        elif args.target == "speech-models":
            speech.install_models(args.names or speech.DEFAULT_MODELS)
        else:
            {"typst": typst, "pandoc": pandoc, "qpdf": qpdf}[args.target].install()
    except Exception as e:  # noqa: BLE001 - ToolError, PipelineError of pipeline.runtime, OSError: the log shows it
        _print(f"{t('cli_error')}: {e}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mehter", description="Mehteran: local AI workflows")
    parser.add_argument("--lang", choices=i18n.LANGUAGES, help="message language (tr, en, ...; a text that a language lacks is shown in English)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ui")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-browser", action="store_true")
    sub.add_parser("templates")
    sub.add_parser("validate").add_argument("file")
    p = sub.add_parser("run")
    p.add_argument("workflow", help="template id (builtin:<id>, user:<id>) or a .yaml file")
    p.add_argument("--input", "-i", action="append", metavar="NAME=VALUE")
    sub.add_parser("runs")
    p = sub.add_parser("resume")
    p.add_argument("run")
    p.add_argument("--node")
    sub.add_parser("cancel").add_argument("run")
    for name in ("approve", "reject"):
        p = sub.add_parser(name)
        p.add_argument("run")
        p.add_argument("node")
        p.add_argument("--comment", default="")
    from pipeline.tools import TOOLS
    sub.add_parser("install").add_argument("tools", nargs="+", choices=list(TOOLS))
    p = sub.add_parser("install-local")
    p.add_argument("target", choices=LOCAL_TARGETS)
    p.add_argument("names", nargs="*", help="OCR languages or speech models")
    args = parser.parse_args(argv)
    i18n.set_default(args.lang or (os.environ.get("TP_LANG") if os.environ.get("TP_LANG") in i18n.LANGUAGES else None))
    home = paths.home()
    handlers = {"ui": cmd_ui, "templates": cmd_templates, "validate": cmd_validate, "run": cmd_run, "runs": cmd_runs,
                "resume": cmd_resume, "cancel": cmd_cancel, "approve": cmd_decide, "reject": cmd_decide,
                "install": cmd_install, "install-local": cmd_install_local}
    try:
        return handlers[args.command](args, home)
    except (RunError, templates.TemplateError) as e:
        for message in e.messages:
            _print(f"{t('cli_error')}: {message}")
        return 1
    except schema.WorkflowError as e:
        _print(t("cli_invalid", count=len(e.problems)))
        for message in e.messages():
            _print(f"- {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
