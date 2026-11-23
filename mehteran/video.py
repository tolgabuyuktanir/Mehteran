"""Render short narrated topic videos from a bounded, declarative storyboard."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from .localtools import run
from .speech import ffmpeg


def narration_voice(language):
    if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?", language):
        raise ValueError("Invalid narration language.")
    speaker = shutil.which("espeak-ng")
    voice = language
    if not speaker and shutil.which("say"):
        voices = subprocess.check_output(["say", "-v", "?"], text=True, timeout=10)
        match = re.search(r"^(.+?)\s+" + re.escape(language.split("-")[0]) + r"_[A-Z]+\s+#", voices, re.M)
        if match:
            speaker, voice = shutil.which("say"), match[1].strip()
    if not speaker:
        raise ValueError("Install eSpeak NG, or a macOS system voice for " + language)
    return speaker, voice


def narration_command(speaker, voice, folder):
    if Path(speaker).name == "say":
        audio = folder / "voice.aiff"
        return [speaker, "-v", voice, "-o", str(audio), "-f", str(folder / "line.txt")], audio
    audio = folder / "voice.wav"
    return [speaker, "-v", voice, "-w", str(audio), "-f", str(folder / "line.txt")], audio


def preview_voice(plan, language, folder, abort):
    try:
        line = plan[0][0]["narration"]
    except (KeyError, TypeError, IndexError):
        raise ValueError("The storyboard needs a first spoken sentence.") from None
    validate_line(line)
    encoder, _ = ffmpeg()
    if not encoder:
        raise ValueError("Voice preview requires FFmpeg.")
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        work = Path(tmp)
        (work / "line.txt").write_text(line, encoding="utf-8")
        cmd, audio = narration_command(*narration_voice(language), work)
        for args in (cmd, [encoder, "-nostdin", "-loglevel", "error", "-i", str(audio), "-ar", "22050",
                           "-ac", "1", str(work / "preview.wav")]):
            code, error = run(args, abort, 120)
            if code:
                raise ValueError(error)
        target = folder / "preview.wav"
        (work / "preview.wav").replace(target)
        return target


def validate_line(line):
    if not isinstance(line, str) or not 1 <= len(line.strip()) <= 180 or any(ord(c) < 32 or c in "[]<>" for c in line):
        raise ValueError("Expected one short plain-text narration per scene.")


def validate_topics(topics):
    titles = [line.strip() for line in topics.splitlines() if line.strip()]
    if not 1 <= len(titles) <= 8:
        raise ValueError("Enter 1–8 topics, one per line.")
    return titles


def video_tools(language):
    encoder, _ = ffmpeg()
    probe = shutil.which("ffprobe", path=str(encoder.parent)) if encoder else None
    probe = probe or shutil.which("ffprobe")
    captioner = shutil.which("pango-view")
    if not probe or not captioner:
        raise ValueError("Video rendering requires ffprobe and pango-view (Pango).")
    if not encoder:
        raise ValueError("Video rendering requires FFmpeg.")
    speaker, voice = narration_voice(language)
    return encoder, probe, captioner, speaker, voice


def render_series(plan, topics, language, platform, mode, folder, abort):
    titles = validate_topics(topics)
    # Some local models wrap each scene separately even for a single requested topic.
    if len(titles) == 1 and isinstance(plan, list) and len(plan) > 1 and all(isinstance(part, list) for part in plan):
        plan = [[scene for part in plan for scene in part]]
    if not isinstance(plan, list) or len(plan) != len(titles):
        raise ValueError("Expected one storyboard per topic (1–8 topics).")
    if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?", language) or mode not in ("short", "standard") or platform not in ("instagram", "youtube", "tiktok", "whatsapp"):
        raise ValueError("Invalid narration language or video layout.")
    encoder, probe, captioner, speaker, voice = video_tools(language)
    width, height = (720, 1280) if mode == "short" or platform in ("tiktok", "whatsapp") else (1280, 720)
    cache = folder / "scenes"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        work = Path(tmp)

        def execute(args):
            code, error = run(args, abort, 120, cwd=work)
            if code:
                raise ValueError(Path(args[0]).name + ": " + error)

        ff = [encoder, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
        with zipfile.ZipFile(work / "videos.zip", "w") as archive:
            for index, (title, scenes) in enumerate(zip(titles, plan), 1):
                if not isinstance(scenes, list) or not 1 <= len(scenes) <= 8:
                    raise ValueError("Expected 1–8 scenes per topic.")
                seconds = (20 if mode == "short" else 40) / len(scenes)
                clips = []
                for scene in scenes:
                    if abort.is_set():
                        raise InterruptedError()
                    if not isinstance(scene, dict):
                        raise ValueError("Invalid scene.")
                    line, bg, boxes = (scene.get(k) for k in ("narration", "background", "boxes"))
                    validate_line(line)
                    if not isinstance(bg, str) or not re.fullmatch("[0-9A-Fa-f]{6}", bg) or not isinstance(boxes, list) or not 1 <= len(boxes) <= 32:
                        raise ValueError("Invalid scene background or illustration.")
                    filters = []
                    for box in boxes:
                        if not isinstance(box, list) or len(box) != 5 or not all(type(v) is int and 0 <= v <= 100 for v in box[:4]):
                            raise ValueError("Expected a rectangle in percentage coordinates.")
                        x, y, w, h, color = box
                        if not w or not h or not isinstance(color, str) or not re.fullmatch("[0-9A-Fa-f]{6}", color):
                            raise ValueError("Invalid rectangle size or color.")
                        filters.append(f"drawbox={width*x//100}:{height*y//100}:{max(1,width*w//100)}:{max(1,height*h//100)}:0x{color}:t=fill")
                    key = hashlib.sha256(json.dumps([scene, width, height, seconds, speaker, voice], sort_keys=True).encode()).hexdigest()
                    clip = cache / (key + ".mp4")
                    clips.append("file '../scenes/" + clip.name + "'")
                    if clip.exists():
                        continue
                    (work / "line.txt").write_text(line, encoding="utf-8")
                    cmd, audio = narration_command(speaker, voice, work)
                    execute(cmd)
                    spoken = float(subprocess.check_output([probe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(work / audio)], text=True, timeout=10))
                    if not 0 < spoken <= seconds * 1.6:
                        raise ValueError("Narration is empty or too long for this scene. Shorten the script or check the voice.")
                    execute([captioner, "--no-display", "--pixels", "--font=Sans 27", "--align=center",
                             "--wrap=word-char", f"--width={int(width*.72)}", "--margin=12",
                             "--background=#13201e", "--foreground=white", "--output=caption.png", "line.txt"])
                    filters.append("format=yuv420p")
                    graph = "[0:v]" + ",".join(filters) + "[art];[art][2:v]overlay=(W-w)/2:H*0.78-h/2[v]"
                    execute(ff + ["-f", "lavfi", "-i", f"color=c=0x{bg}:s={width}x{height}:r=24", "-i", audio,
                                  "-i", "caption.png", "-filter_complex", graph, "-map", "[v]", "-map", "1:a",
                                  "-af", f"atempo={max(1, spoken/seconds):.6f},apad", "-t", f"{seconds:.6f}",
                                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
                                  "-ac", "1", "captioned.mp4"])
                    (work / "captioned.mp4").replace(clip)
                (work / "clips.txt").write_text("\n".join(clips), encoding="utf-8")
                execute(ff + ["-f", "concat", "-safe", "0", "-i", "clips.txt", "-map", "0", "-c", "copy",
                              "-movflags", "+faststart", "topic.mp4"])
                slug = re.sub(r"[^\w-]+", "-", title).strip("-")[:64] or "topic"
                archive.write(work / "topic.mp4", f"{index:02}-{slug}-{platform}-{mode}.mp4")
        result = folder / "videos.zip"
        (work / "videos.zip").replace(result)
        return result
