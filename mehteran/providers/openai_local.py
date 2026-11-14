"""A local server with an OpenAI-compatible API (LM Studio, llama.cpp's llama-server, vLLM, ...), on this computer only.

The address is the user's setting ([providers.openai-local] url = "http://127.0.0.1:1234/v1"); only a loopback host
is accepted (127.0.0.1, localhost, ::1), no proxy is used and no redirect is followed, so the text cannot leave the
computer through this adapter. The call is POST <url>/chat/completions with "stream": true (server-sent events), and
the text goes to the live log as it arrives. stdlib urllib only."""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .base import Adapter, CallError, UsageLimit

LOOPBACK_NAMES = ("localhost",)


def loopback_url(url: str) -> str | None:
    """The url without a trailing "/", when it is http(s) to a loopback host on a port; else None."""
    try:
        parts = urlparse(str(url or "").strip())
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or parts.username or parts.password or parts.query or parts.fragment:
        return None
    try:
        local = host in LOOPBACK_NAMES or ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    return parts.geturl().rstrip("/") if local and port else None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect could lead away from this computer
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _open(url: str, body: dict | None, timeout: float):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
    return _OPENER.open(request, timeout=timeout)


class OpenAILocal(Adapter):
    id, name, vendor, tool, program = "openai-local", "Local OpenAI-compatible server", "OpenAI-compatible server", None, ""
    billing = "local"
    context = 8192
    concurrency = 1
    local = True
    cli = False

    def list_models(self, url: str = "") -> list[str]:
        base = loopback_url(url)
        if not base:
            return []
        try:
            with _open(base + "/models", None, 3) as res:
                data = json.loads(res.read())
        except (OSError, ValueError):
            return []
        return [str(m["id"]) for m in data.get("data") or [] if isinstance(m, dict) and isinstance(m.get("id"), str)][:200]

    def chat(self, url: str, model: str, prompt: str, system_prompt: str, timeout: float, on_text=None) -> str:
        """The answer of one call; on_text(piece) gets the text as it streams. Raises CallError or UsageLimit."""
        import time
        base = loopback_url(url)
        if not base:
            raise CallError("the local server's address must be http://127.0.0.1:<port>/... (Setup tab)")
        body = {"model": model or "default", "stream": True,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]}
        pieces: list[str] = []
        try:
            with _open(base + "/chat/completions", body, timeout) as res:
                for raw in res:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except ValueError:
                        continue
                    if event.get("error"):
                        raise CallError(str(event["error"])[:500])
                    for choice in event.get("choices") or []:
                        text = ((choice or {}).get("delta") or {}).get("content") or ""
                        if text:
                            pieces.append(text)
                            if on_text:
                                on_text(text)
        except urllib.error.HTTPError as e:
            detail = e.read(2000).decode("utf-8", "replace")
            if e.code == 429:
                raise UsageLimit(detail or "429 Too Many Requests", time.time() + 60) from None
            raise CallError(f"HTTP {e.code}: {detail[:500]}") from None
        except (OSError, ValueError) as e:
            raise CallError(f"the local server at {base} does not answer: {e}") from None
        answer = "".join(pieces).strip()
        if not answer:
            raise CallError("the local server gave an empty answer")
        return answer
