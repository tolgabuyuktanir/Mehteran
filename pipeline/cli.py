"""Command-line interface: ./translate <command>"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import tomllib
from pathlib import Path

from . import i18n, stages, system, tools
from .core import ROOT, PipelineError, Project, say, split_name
from .i18n import t
from .providers import run as run_llm
from .runstatus import STATUS


def cmd_setup(proj: Project, args) -> int:
    used = {}
    for stage in stages.llm_stages(proj):
        for name in proj.providers_for(stage):
            used.setdefault(split_name(name)[0], []).append(stage)
    ok = True
    for name, spec in proj.cfg["providers"].items():
        role = ", ".join(used.get(name, [])) or t("unused")
        exe = spec["command"][0]
        if not shutil.which(exe):
            say(f"✗ {name:8} {t('tool_missing', command=exe, hint=spec.get('install_hint', '-'))}   [{role}]")
            ok = ok and name not in used
            continue
        try:
            answer = run_llm(proj, name, "Reply with exactly this word and nothing else: OK")
            say(f"✓ {name:8} {t('tool_ok', answer=repr(answer[:40]))}   [{role}]")
        except PipelineError as e:
            say(f"✗ {name:8} {t('tool_no_answer', error=e)}   [{role}]")
            ok = ok and name not in used
    say("\n" + t("all_ready" if ok else "fix_and_retry"))
    return 0 if ok else 1


def cmd_new(proj: Project, args) -> int:
    book_dir = proj.book_dir(args.book)
    for sub in ("source", "references"):
        (book_dir / sub).mkdir(parents=True, exist_ok=True)
    say(t("book_created", path=book_dir, source=book_dir / "source", references=book_dir / "references", book=args.book))
    return 0


def _lock_book(book_dir: Path):
    """Two runs of the same book must not write the shared files (preparation, alignment, glossary) at once.

    The lock is held on work/.lock until the process ends; work/run.pid tells the web interface which process to stop.
    """
    (book_dir / "work").mkdir(parents=True, exist_ok=True)
    handle = open(book_dir / "work" / ".lock", "a+")
    if not system.try_lock(handle):
        handle.close()
        raise PipelineError(t("book_busy"))
    (book_dir / "work" / "run.pid").write_text(str(os.getpid()), encoding="utf-8")
    return handle


def cmd_run(proj: Project, args) -> int:
    book_dir = proj.book_dir(args.book)
    if not (book_dir / "source").is_dir():
        raise PipelineError(t("book_not_found", path=book_dir, book=args.book))
    proj.language_name(args.target)

    refs = args.refs.split(",") if args.refs else stages.available_refs(book_dir)
    refs = [r for r in refs if r and r != args.target]
    for ref in refs:
        proj.language_name(ref)

    order = stages.all_stages(proj)
    if args.until not in order:
        raise PipelineError(t("stage_not_in_flow", stage=args.until, stages=", ".join(order)))
    if args.redo and args.redo not in order[1:-1]:
        raise PipelineError(t("stage_not_in_flow", stage=args.redo, stages=", ".join(order[1:-1])))
    todo = order[:order.index(args.until) + 1]
    if not refs:
        say(t("no_references_warning"))
    llm_stages = [s for s in todo if s in order[1:-1] and (s != "align" or refs)]
    needed = {split_name(name)[0] for stage in llm_stages for name in proj.providers_for(stage)}
    missing = [n for n in sorted(needed) if not shutil.which(proj.cfg["providers"].get(n, {}).get("command", [n])[0])]
    if missing:
        raise PipelineError(t("tools_not_installed", names=", ".join(missing)))

    lock = _lock_book(book_dir)
    STATUS.start(book_dir / "work" / "run.json", proj.root / ".jobs" / "quota.json", pid=os.getpid(),
                 target=args.target, refs=refs, segments=args.segments or "", until=args.until,
                 awake=_keep_awake(proj), parallel=args.parallel or proj.cfg["general"]["parallel"])
    # The web interface stops a run with SIGTERM: finish the current calls cleanly and record the stop.
    previous_handler = signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        result = _run_book(proj, args, refs, todo)
        STATUS.finish("finished")
        return result
    except KeyboardInterrupt:
        STATUS.stopping = True
        STATUS.finish("stopped")
        raise
    except Exception as e:
        STATUS.finish("failed", str(e))
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        lock.close()


def _on_sigterm(signum, frame):
    STATUS.stopping = True
    raise KeyboardInterrupt


def _keep_awake(proj: Project) -> bool:
    return proj.cfg["general"].get("keep_awake", True) and system.keep_awake()


def _run_book(proj: Project, args, refs: list[str], todo: list[str]) -> int:
    ids = stages.prepare(proj, args.book, refs)
    run = stages.Run(
        proj=proj, book=args.book, target=args.target, refs=refs, ids=ids,
        selected=stages.select_segments(args.segments, ids) if args.segments else ids,
        workers=args.parallel or proj.cfg["general"]["parallel"],
    )
    say(t("run_header", book=args.book, language=proj.language_name(args.target), selected=len(run.selected),
          total=len(ids), refs=", ".join(refs) or "-"))
    if args.redo:
        stages.reset(run, args.redo)
    nodes = stages.flow(proj)
    for stage in todo[1:]:
        if stage in nodes:
            # The nodes of the flow run together: a checkpoint can send a segment back to an earlier one.
            if stage == nodes[0]:
                stages.run_flow(run, until=todo[-1] if todo[-1] in nodes else None)
            continue
        stages.runner(stage)(run)
    return 0


def cmd_status(proj: Project, args) -> int:
    books = [args.book] if args.book else sorted(p.name for p in (proj.root / "books").glob("*") if p.is_dir())
    if not books:
        say(t("no_books"))
    for book in books:
        status = stages.book_status(proj, book)
        total = status["segments"]
        say(f"{book}: " + (t("segments_count", count=total) if total else t("not_prepared")))
        for ref, info in status["alignment"].items():
            say("  " + t("status_alignment", ref=ref, aligned=info["aligned"], total=total))
            if info["missing"]:
                say("    " + t("status_unaligned", segments=", ".join(info["missing"])))
        for lang, info in status["languages"].items():
            say(f"  {lang}: " + " · ".join(f"{stage} {n}/{m}" for stage, (n, m) in info["stages"].items()))
            out = proj.book_dir(book) / "output" / f"{lang}.md"
            say(f"    {t('output_translation')}: {out if info['output'] else '-'}")
    return 0


def cmd_update(proj: Project, args) -> int:
    from . import update
    return update.update(proj.root)


def cmd_install(proj: Project, args) -> int:
    from . import runtime, tools
    tools.extend_path(proj.root)
    for tool in args.tools:
        name = t(f"tool_name_{tool}") if tools.TOOLS[tool]["provider"] is None else tools.TOOLS[tool]["name"]
        say(f"=== {name} ===")
        runtime.install_tool(tool, proj.root)
        tools.extend_path(proj.root)
        say(t("tool_installed", name=name))
    return 0


# What a shared copy contains. Everything else in the folder stays on this computer: books and translations,
# installed tools (.runtime), logs (.jobs) and session notes.
PACKAGE_FILES = ["README.md", "README.tr.md", "config.default.toml", "config.toml", ".gitignore", "translate", "translate.cmd",
                 "Open Interface.command", "Open Interface.bat"]
PACKAGE_FOLDERS = ["docs", "pipeline", "prompts", "scripts", "tests", "glossary"]
PACKAGE_SKIP = {"__pycache__", ".DS_Store", "Thumbs.db"}


def cmd_package(proj: Project, args) -> int:
    """Writes a zip of the application for sharing. Executable permissions are kept in the zip."""
    import zipfile
    out = Path(args.out) if args.out else proj.root / "dist" / "translation-pipeline.zip"
    files = [proj.root / name for name in PACKAGE_FILES if (proj.root / name).is_file()]
    for folder in PACKAGE_FOLDERS:
        files += sorted(p for p in (proj.root / folder).rglob("*")
                        if p.is_file() and not PACKAGE_SKIP & set(p.relative_to(proj.root).parts) and p.suffix != ".pyc")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            info = zipfile.ZipInfo.from_file(path, "TranslationPipeline/" + path.relative_to(proj.root).as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
    say(t("package_done", count=len(files), path=out))
    return 0


def cmd_ui(proj: Project, args) -> int:
    from .web import serve
    serve(proj, args.port, open_browser=not args.no_browser)
    return 0


def _initial_language(argv: list[str], root: Path) -> str:
    """--lang argument, else TP_LANG, else [general] language in config.toml, else Turkish."""
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    if os.environ.get("TP_LANG"):
        return os.environ["TP_LANG"]
    try:
        with (root / "config.toml").open("rb") as f:
            return tomllib.load(f).get("general", {}).get("language", "tr")
    except (OSError, tomllib.TOMLDecodeError):
        return "tr"


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    i18n.set_default(_initial_language(argv, root))

    parser = argparse.ArgumentParser(prog="translate", description=t("cli_description"))
    parser.add_argument("--lang", dest="ui_lang", choices=i18n.LANGUAGES, help=t("cli_lang"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help=t("cli_setup"))

    p = sub.add_parser("new", help=t("cli_new"))
    p.add_argument("book", help=t("cli_book"))

    p = sub.add_parser("run", help=t("cli_run"))
    p.add_argument("book")
    p.add_argument("target", help=t("cli_target"))
    p.add_argument("--refs", help=t("cli_refs"))
    p.add_argument("--segments", help=t("cli_segments"))
    p.add_argument("--until", default="assemble", help=t("cli_until"))
    p.add_argument("--redo", help=t("cli_redo"))
    p.add_argument("--parallel", type=int, help=t("cli_parallel"))

    p = sub.add_parser("status", help=t("cli_status"))
    p.add_argument("book", nargs="?")

    p = sub.add_parser("install", help=t("cli_install"))
    p.add_argument("tools", nargs="+", choices=list(tools.TOOLS))

    sub.add_parser("update", help=t("cli_update"))

    p = sub.add_parser("package", help=t("cli_package"))
    p.add_argument("--out", help=t("cli_package_out"))

    p = sub.add_parser("ui", help=t("cli_ui"))
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true", help=t("cli_no_browser"))

    args = parser.parse_args(argv)
    commands = {"setup": cmd_setup, "new": cmd_new, "run": cmd_run, "status": cmd_status, "ui": cmd_ui,
                "install": cmd_install, "package": cmd_package, "update": cmd_update}
    try:
        proj = Project.load(root)
        if args.command in ("setup", "run"):
            from .tools import extend_path
            extend_path(proj.root)  # tools that the interface installed into <root>/.runtime
        return commands[args.command](proj, args)
    except PipelineError as e:
        say(f"{t('error')}: {e}")
        return 1
    except KeyboardInterrupt:
        say("\n" + t("interrupted"))
        return 130
