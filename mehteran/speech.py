"""Speech to text on this computer: whisper.cpp writes down what is said in an audio or video file; ffmpeg first turns
the file into the 16 kHz mono WAV that whisper.cpp reads.

- Finding them: Mehteran's own copies in <code folder>/.runtime/speech first, then PATH (whisper-cli, ffmpeg).
- Installing them: only when the user asks (the Setup tab, `mehter install-local speech`). The pinned conda-forge
  packages (micromamba checks every package against the channel's SHA-256 sums) go into .runtime/speech; ffmpeg only
  when the computer has none. conda-forge builds both for macOS (arm64, x64), Linux (x64, arm64) and Windows x64.
- Models: the multilingual ggml models of the official whisper.cpp repository on Hugging Face (ggerganov/whisper.cpp),
  at a pinned revision, each checked against the SHA-256 sum written below (computed from the downloaded files; they
  match the repository's own LFS sums). They go to .runtime/whisper-models.
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

from . import paths
from .i18n import t
from .localtools import (ToolError, conda_bin, conda_install, dir_size, disk_free, download_verified, exe, find_program,
                         micromamba_missing, program_version, run)

WHISPER_SPEC = "whisper.cpp=1.9.3"
FFMPEG_SPEC = "ffmpeg=9.0.2"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-{name}.bin"
MODELS = {  # name: (SHA-256, size); all multilingual. The order is the order of "auto".
    "base": ("60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe", 147951465),
    "small": ("1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b", 487601967),
    "large-v3-turbo-q5_0": ("394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2", 574041195),
    "medium": ("6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208", 1533763059),
    "tiny": ("be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21", 77691713),
}
DEFAULT_MODELS = ["base"]
FORMATS = ("mp3", "wav", "m4a", "ogg", "opus", "flac", "aac", "mp4", "webm", "mov", "mkv")
LANGUAGES = ("auto", "tr", "en", "ar", "fa", "ur", "de", "fr", "es", "it", "ru", "az", "nl", "pt", "zh", "ja")
# The download with the libraries they need, about (measured on macOS arm64; other systems differ a little).
WHISPER_DOWNLOAD, FFMPEG_DOWNLOAD = 13_000_000, 96_000_000
CONVERT_TIMEOUT = 1800
TRANSCRIBE_TIMEOUT = 6 * 3600


def prefix() -> Path:
    return paths.runtime() / "speech"


def models_dir() -> Path:
    return paths.runtime() / "whisper-models"


def whisper() -> tuple[Path | None, str | None]:
    return find_program("whisper-cli", [conda_bin(prefix()) / exe("whisper-cli")])


def ffmpeg() -> tuple[Path | None, str | None]:
    return find_program("ffmpeg", [conda_bin(prefix()) / exe("ffmpeg")])


def installed_models() -> list[str]:
    return [name for name, (_, size) in MODELS.items()
            if (models_dir() / f"ggml-{name}.bin").is_file() and (models_dir() / f"ggml-{name}.bin").stat().st_size == size]


def _whisper_version(program: Path | None, source: str | None) -> str | None:
    if source == "mehteran":
        found = sorted((prefix() / "conda-meta").glob("whisper.cpp-*.json"))
        return found[0].name.split("-")[1] if found else None
    return program_version(program, "--version") if program else None


def status() -> dict:
    program, source = whisper()
    convert, convert_source = ffmpeg()
    have = installed_models()
    return {"id": "speech", "name": "whisper.cpp", "installed": bool(program and convert), "source": source,
            "path": str(program) if program else None, "version": _whisper_version(program, source),
            "pinned_version": WHISPER_SPEC.partition("=")[2], "ffmpeg": str(convert) if convert else None,
            "ffmpeg_source": convert_source, "ffmpeg_version": FFMPEG_SPEC.partition("=")[2],
            "size": (dir_size(prefix()) or 0) + (dir_size(models_dir()) or 0) or None,
            "download_size": WHISPER_DOWNLOAD + (FFMPEG_DOWNLOAD if convert is None else 0) + sum(MODELS[m][1] for m in DEFAULT_MODELS),
            "install_dir": str(prefix()), "disk_free": disk_free(prefix()), "poppler_first": micromamba_missing(), "models": have,
            "available_models": [{"name": name, "size": size, "installed": name in have} for name, (_, size) in MODELS.items()]}


def install(models: list[str] | None = None) -> None:
    """whisper.cpp (and ffmpeg when the computer has none) into .runtime/speech, then the models (default: base)."""
    specs = [WHISPER_SPEC] + ([] if ffmpeg()[0] is not None else [FFMPEG_SPEC])
    conda_install(prefix(), specs)
    if not (conda_bin(prefix()) / exe("whisper-cli")).is_file():
        raise ToolError(t("tool_install_failed", name="whisper.cpp"))
    install_models([m for m in (models or DEFAULT_MODELS) if m not in installed_models()])


def install_models(names: list[str]) -> None:
    for name in names:  # checked first: an unknown name downloads nothing
        if name not in MODELS:
            raise ToolError(t("speech_unknown_model", name=name, known=", ".join(MODELS)))
    for name in names:
        target = models_dir() / f"ggml-{name}.bin"
        if target.is_file() and target.stat().st_size == MODELS[name][1]:
            continue
        print(t("speech_model_downloading", name=name, size=round(MODELS[name][1] / 1e6)), flush=True)
        download_verified(MODEL_URL.format(name=name), target, MODELS[name][0])
    print(t("speech_ready", models=", ".join(installed_models()) or "-"), flush=True)


# --- transcribing -------------------------------------------------------------------------

def pick_model(choice: str) -> Path:
    have = installed_models()
    if choice and choice != "auto":
        if choice not in have:
            raise ToolError(t("speech_model_missing", name=choice))
        name = choice
    elif have:
        name = have[0]
    else:
        raise ToolError(t("speech_no_model"))
    return models_dir() / f"ggml-{name}.bin"


def transcribe(path: Path, model: str = "auto", language: str = "auto", abort: threading.Event | None = None) -> str:
    """The spoken text of an audio or video file."""
    program, _ = whisper()
    convert, _ = ffmpeg()
    if program is None or convert is None:
        raise ToolError(t("speech_missing", name=path.name))
    model_file = pick_model(model)
    language = language if language in LANGUAGES else "auto"
    with tempfile.TemporaryDirectory(prefix="mehteran-speech-") as tmp:
        wav, out = Path(tmp) / "audio.wav", Path(tmp) / "transcript"
        code, errors = run([str(convert), "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn",
                            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], abort, CONVERT_TIMEOUT)
        if code != 0 or not wav.is_file():
            raise ToolError(t("speech_failed", name=path.name, error=errors.strip()[-300:]))
        threads = str(max(1, min(8, (os.cpu_count() or 4))))
        code, errors = run([str(program), "-m", str(model_file), "-f", str(wav), "-l", language, "-t", threads,
                            "-otxt", "-of", str(out), "-np"], abort, TRANSCRIBE_TIMEOUT)
        result = out.with_suffix(".txt")
        if code != 0 or not result.is_file():
            raise ToolError(t("speech_failed", name=path.name, error=errors.strip()[-300:]))
        lines = [line.strip() for line in result.read_text(encoding="utf-8", errors="replace").splitlines()]
    return "\n".join(line for line in lines if line)
