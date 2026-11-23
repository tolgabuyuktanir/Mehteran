"""Premium media services used by the social video pipeline."""
import base64
import json
import os
import re
import tempfile
from . import paths
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

IMAGE_MODEL = "gpt-image-2.6-sunburst"
VOICE_MODEL = "eleven_v4"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


SETTINGS_FILE = "video-media.json"
FIELDS = {"openai_key": "OPENAI_API_KEY", "elevenlabs_key": "ELEVENLABS_API_KEY",
          "voice_id": "MEHTERAN_VIDEO_VOICE_ID"}


def saved_settings(home):
    file = home / "configurations" / SETTINGS_FILE
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Invalid video settings file.")
    return {key: raw[key] for key in FIELDS if isinstance(raw.get(key), str)}


def credentials(home=None):
    saved = saved_settings(home) if home is not None else {}
    return {key: saved.get(key) or os.environ.get(env, "") for key, env in FIELDS.items()}


def status(home):
    saved = saved_settings(home)
    return {"sources": {key: "saved" if saved.get(key) else "environment" if os.environ.get(env) else "default"
                        if key == "voice_id" else "missing" for key, env in FIELDS.items()},
            "voice_id": saved.get("voice_id") or os.environ.get(FIELDS["voice_id"]) or DEFAULT_VOICE}


def save(home, changes):
    if not changes or any(key not in FIELDS for key in changes):
        raise ValueError("Invalid video settings.")
    saved = saved_settings(home)
    for key, value in changes.items():
        if value is None:
            saved.pop(key, None)
            continue
        if not isinstance(value, str):
            raise ValueError("Invalid video setting.")
        value = value.strip()
        valid = (re.fullmatch(r"[A-Za-z0-9]{10,64}", value) if key == "voice_id"
                 else re.fullmatch(r"[!-~]{12,512}", value))
        if not valid:
            raise ValueError("Invalid video setting.")
        saved[key] = value
    folder = home / "configurations"
    folder.mkdir(parents=True, exist_ok=True)
    # NamedTemporaryFile creates the file with owner-only permissions on POSIX.
    with tempfile.NamedTemporaryFile(dir=folder, mode="w", encoding="utf-8", delete=False) as stream:
        tmp = folder / os.path.basename(stream.name)
        try:
            json.dump(saved, stream)
            stream.close()
            paths.replace(tmp, folder / SETTINGS_FILE)
        finally:
            tmp.unlink(missing_ok=True)


def voice_id(config):
    voice = config.get("voice_id") or DEFAULT_VOICE
    if not re.fullmatch(r"[A-Za-z0-9]{10,64}", voice):
        raise ValueError("MEHTERAN_VIDEO_VOICE_ID is invalid.")
    return voice


def check(config):
    missing = [provider for key, provider in (("openai_key", "OpenAI"), ("elevenlabs_key", "ElevenLabs"))
               if not config.get(key)]
    if missing:
        raise ValueError("Add API keys in Setup → Video services: " + ", ".join(missing))
    voice_id(config)


def _post(url, headers, payload, service, abort):
    if abort.is_set():
        raise InterruptedError()
    request = Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **headers})
    limit = 24 * 1024 * 1024
    try:
        with build_opener(NoRedirect()).open(request, timeout=65) as response:
            data = bytearray()
            while len(data) <= limit:
                if abort.is_set():
                    raise InterruptedError()
                chunk = response.read1(min(65536, limit + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
    except HTTPError as error:
        raise ValueError(f"{service}: HTTP {error.code}. Check API access, billing or quota.") from None
    except (URLError, TimeoutError):
        raise ValueError(f"{service}: connection failed or timed out.") from None
    if not data or len(data) > limit:
        raise ValueError(f"{service}: invalid media response size.")
    return data


def speech(line, language, destination, abort, config):
    check(config)
    data = _post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id(config)}?output_format=mp3_44100_128",
                 {"xi-api-key": config["elevenlabs_key"]},
                 {"text": line, "model_id": VOICE_MODEL, "language_code": language.split("-")[0]},
                 "ElevenLabs", abort)
    if not data.startswith(b"ID3") and not (data[0] == 255 and len(data) > 1 and data[1] & 224 == 224):
        raise ValueError("ElevenLabs did not return MP3 audio.")
    destination.write_bytes(data)


def image(prompt, portrait, destination, abort, config):
    check(config)
    data = _post("https://api.openai.com/v1/images/generations",
                 {"Authorization": "Bearer " + config["openai_key"]},
                 {"model": IMAGE_MODEL, "prompt": prompt, "n": 1, "quality": "high",
                  "size": "1024x1536" if portrait else "1536x1024", "output_format": "png"},
                 "OpenAI Images", abort)
    try:
        png = base64.b64decode(json.loads(data)["data"][0]["b64_json"], validate=True)
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError("OpenAI Images returned an invalid image.") from None
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("OpenAI Images did not return a PNG.")
    destination.write_bytes(png)
