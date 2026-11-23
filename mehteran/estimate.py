"""What a run will ask of the AI tools, counted before it starts: how many model calls, on which models.

Counted from the workflow file and the chosen models only. No file is read and no model is called. The tools do not
tell what one call costs, so nothing here is a share of a usage limit.

- ai.cli: one call per attempt.
- condition with the operator "ai": one call per attempt, and one more when the answer is not a clear yes or no.
- ai.map (a loop): one call per part. The number of parts depends on the text, so it is not counted: the step is
  reported as a loop with its largest number of parts (max_items).
- A step after a condition runs only on the branch that is taken: it is counted and marked "conditional".

"calls" is one pass in which every step runs once, without the loop parts. "max_calls" is the upper bound: every
attempt of every step is used (retries + 1), every loop has its largest number of parts, and each "ai" condition
asks twice. A wait for a usage limit repeats a call without using an attempt; it is not part of the bound.
"""

from __future__ import annotations

from . import placeholders, schema
from .nodes import MAP_LIMIT, PROVIDER_RE, REGISTRY


def _calls(node: dict) -> tuple[int, int, int] | None:
    """(calls in one pass, calls per attempt at most, largest number of loop parts) of a node; None when it calls no
    model."""
    config = node.get("config") or {}
    if node["type"] == "ai.cli":  # "output: json" asks once more when the answer is not valid JSON
        return 1, 2 if config.get("output") == "json" else 1, 0
    if node["type"] == "ai.agent":
        return 1, 1, 0
    if node["type"] == "condition" and (config.get("operator") or "contains") == "ai":
        return 1, 2, 0
    if node["type"] == "ai.map":
        parts = config.get("max_items")
        parts = min(parts, MAP_LIMIT) if isinstance(parts, int) and not isinstance(parts, bool) and parts > 0 else 50
        return 0, parts, parts
    return None


def _concrete(model: str, cfg: dict, resolve, privacy: str) -> tuple[str, str | None]:
    """(the model a run would use, the `auto` kind that chose it or None). resolve(kind) -> a model or "": what
    `auto` would choose now (the web interface asks the tools; without it `auto` stays as it is)."""
    from . import providers
    model = providers.canonical(model, cfg["providers"])
    if model not in providers.AUTO:
        return model, None
    kind = "auto:local" if privacy == "local" else model
    return ((resolve(kind) if resolve else "") or kind), kind


def _sent_to(model: str, cfg: dict, privacy: str) -> dict:
    """{sent_to: where the prompt goes ("Anthropic", "this computer (Ollama)"), local, refused (privacy: local)}."""
    from . import providers
    name, sub, _ = providers.split(model)
    if not PROVIDER_RE.match(model) or name not in cfg["providers"]:
        return {"sent_to": None, "local": False, "refused": False}
    spec = cfg["providers"][name]
    where = providers.destination(name, sub or spec.get("model") or "", spec)
    return {"sent_to": where["vendor"], "local": where["local"], "refused": privacy == "local" and not where["local"]}


def estimate(wf: schema.Workflow, values: dict, cfg: dict, resolve=None, privacy: str = "", every_step: str = "") -> dict:
    """The model calls of a run of wf with the given input values (a missing value: the input's default).
    Each step says where its prompt goes (sent_to, local); an `auto` model is shown as resolve(kind) chooses it.
    privacy "local" (or the workflow's "privacy: local"): a step that would leave this computer is "refused".
    every_step: one model for every step (Engine.start's every_step).

    {steps: [{node, label, type, provider, model, retries, calls, per_part, max_parts, conditional, max_calls}],
     models: [{provider, model, configured, calls, loops, max_parts, max_calls}],
     calls, loops, max_parts, conditional, max_calls}
    provider: the tool's name in the configuration ("claude"); model: the full choice ("claude/opus@high")."""
    privacy = privacy or wf.data.get("privacy") or ""
    inputs = {}
    for input_id, spec in wf.inputs.items():
        value = values.get(input_id, spec.get("default"))
        inputs[input_id] = value if isinstance(value, str) else ""
    after_condition = set()
    for node_id, node in wf.nodes.items():
        if node["type"] == "condition":
            after_condition |= wf.downstream(node_id)
    steps, models = [], {}
    for node_id in wf.order:
        node = wf.nodes[node_id]
        counted = _calls(node)
        if counted is None:
            continue
        once, per_attempt, parts = counted
        template = (node.get("config") or {}).get("provider")
        if isinstance(template, str) and every_step.strip():
            template = every_step
        model = placeholders.render(template.strip(), lambda ref: inputs.get(ref[7:], "")).strip() \
            if isinstance(template, str) else ""
        model, chosen_by = _concrete(model, cfg, resolve, privacy)
        provider = model.partition("@")[0].partition("/")[0] if PROVIDER_RE.match(model) else ""
        retries = node.get("retries", REGISTRY[node["type"]].default_retries)
        step = {"node": node_id, "label": node.get("label"), "type": node["type"], "provider": provider, "model": model,
                "retries": retries, "calls": once, "per_part": bool(parts), "max_parts": parts,
                "conditional": node_id in after_condition, "max_calls": per_attempt * (retries + 1),
                **_sent_to(model, cfg, privacy), "auto": chosen_by}
        if fallback := node.get("fallback_provider"):
            fallback, _ = _concrete(every_step or fallback, cfg, resolve, privacy)
            if fallback != model:
                step["fallback"] = fallback
        steps.append(step)
        group = models.setdefault(model, {"provider": provider, "model": model,
                                          "configured": provider in cfg["providers"], "calls": 0, "loops": 0,
                                          "max_parts": 0, "max_calls": 0, "sent_to": step["sent_to"],
                                          "local": step["local"], "auto": step["auto"]})
        group["calls"] += once
        group["loops"] += 1 if parts else 0
        group["max_parts"] += parts
        group["max_calls"] += step["max_calls"]
    return {"steps": steps, "models": list(models.values()),
            "calls": sum(s["calls"] for s in steps), "loops": sum(1 for s in steps if s["per_part"]),
            "max_parts": sum(s["max_parts"] for s in steps),
            "conditional": sum(1 for s in steps if s["conditional"]),
            "max_calls": sum(s["max_calls"] for s in steps),
            "privacy": privacy, "refused": sum(1 for s in steps if s["refused"]),
            **({"quota_max_hours": cfg.get("general", {}).get("quota_max_hours", 24)} if steps else {})}
