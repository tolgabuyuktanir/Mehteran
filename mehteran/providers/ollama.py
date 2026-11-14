"""Ollama: models on this computer, through Ollama's HTTP API on 127.0.0.1 (mehteran/ollama.py). A model whose name
ends with ":cloud" runs on Ollama's servers: it is not local."""

from __future__ import annotations

from .base import Adapter


class Ollama(Adapter):
    id, name, vendor, tool, program = "ollama", "Ollama", "Ollama", None, "ollama"  # local: the page says "stays here"
    billing = "local"
    context = 8192  # what Mehteran asks for by default (num_ctx)
    concurrency = 1
    local = True
    cli = False

    def list_models(self) -> list[str]:
        from mehteran import ollama
        return [m["name"] for m in ollama.installed_models() if ollama.MODEL_RE.match(m["name"]) and "/" not in m["name"]]

    def login(self) -> dict:
        from mehteran import ollama
        return {"signed_in": True, "info": "", "billing": "local", "running": bool(ollama.installed_models())}

    def model_is_local(self, model: str) -> bool:
        return not is_cloud(model)


def is_cloud(model: str) -> bool:
    """Ollama's cloud models: "gpt-oss:120b-cloud", "qwen3-coder:480b-cloud", "deepseek-v3.1:671b-cloud", ":cloud"."""
    tag = (model or "").rpartition(":")[2]
    return tag == "cloud" or tag.endswith("-cloud")
