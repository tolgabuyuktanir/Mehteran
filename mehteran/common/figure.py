"""Figures in a result: a fenced code block marked "figure" that holds one JSON object, which Mehteran draws as SVG.

A model writes data, not markup: a coordinate plane ("plot": functions, broken lines, polygons, points, circles,
labels; "axes": false for a geometric figure) or a bar chart ("bar"). Mehteran makes every element itself, so a
result cannot carry a script, a link or a style into the page. mehteran/ui/markdown.js draws the same figure for the
reader with the same rules (tests/test_mehteran_figure.py compares the two).

tree(spec) -> [tag, attrs, children] or ValueError; svg(text) -> the SVG markup, or None when the block is not a valid
figure (it is then shown as code); alt_text(text) -> the description, for Word and PDF; as_text(markdown) -> the
Markdown with each figure replaced by its description in italics.
"""

import html
import json
import math
import re
from decimal import ROUND_HALF_UP, Decimal

MAX_ITEMS = 40
MAX_POINTS = 2000  # all the points of a figure together
MAX_BARS = 24
SAMPLES = 240  # points of a function's curve
COLORS = 4

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*figure[ \t]*\n(.*?)\n {0,3}\1[`~]*[ \t]*$", re.M | re.S)


# --- numbers ---------------------------------------------------------------------------------------

def num(v: float) -> str:
    """A coordinate with at most two decimals, as JavaScript's toFixed(2) rounds it (half away from zero)."""
    text = str(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    text = text.rstrip("0").rstrip(".") if "." in text else text
    return "0" if text in ("-0", "") else text


def _number(v, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1e6:
        raise ValueError(f"{name}: not a number")
    return float(v)


def _text(v, name: str, limit: int) -> str:
    if v is None:
        return ""
    if not isinstance(v, str) or len(v) > limit:
        raise ValueError(f"{name}: not a short text")
    return " ".join(v.split())


def _range(v, name: str) -> tuple[float, float]:
    if not isinstance(v, list) or len(v) != 2:
        raise ValueError(f"{name}: not [min, max]")
    lo, hi = _number(v[0], name), _number(v[1], name)
    if not hi > lo:
        raise ValueError(f"{name}: max is not above min")
    return lo, hi


def nice_step(span: float, target: int = 8) -> float:
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for k in (1, 2, 5, 10):
        if raw <= k * mag * 1.0000001:
            return k * mag
    return 10 * mag


def _labelled(v: float, every: float) -> bool:
    """A tick has a label when it is a multiple of the label step (with many ticks: every second one, from 0)."""
    return abs(v / every - round(v / every)) < 1e-6


def ticks(lo: float, hi: float, step: float) -> list[float]:
    first = math.ceil(lo / step - 1e-9)
    out = []
    k = first
    while k * step <= hi + 1e-9 * step and len(out) < 201:
        out.append(0.0 if abs(k * step) < 1e-9 * step else k * step)
        k += 1
    return out


# --- expressions -----------------------------------------------------------------------------------
# A function of x: numbers, x, pi, e, + - * / ^, parentheses, implicit multiplication (2x, 3(x+1)) and
# sqrt abs sin cos tan exp ln log. Parsed by hand; nothing is evaluated as code.

FUNCTIONS = {"sqrt": math.sqrt, "abs": abs, "sin": math.sin, "cos": math.cos, "tan": math.tan, "exp": math.exp,
             "ln": math.log, "log": math.log10}
_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|([a-z]+)|(.))", re.A)


def _tokens(expr: str) -> list[tuple[str, str]]:
    out, i = [], 0
    while i < len(expr):
        m = _TOKEN.match(expr, i)
        if not m or m.end() == i:
            break
        i = m.end()
        if m.group(1):
            out.append(("num", m.group(1)))
        elif m.group(2):
            out.append(("name", m.group(2)))
        elif m.group(3).strip():
            if m.group(3) not in "+-*/^()":
                raise ValueError(f"fn: unknown sign {m.group(3)!r}")
            out.append(("op", m.group(3)))
    return out


def compile_fn(expr: str):
    """A function f(x) -> float from the text, or ValueError. A value that cannot be computed is nan."""
    if not isinstance(expr, str) or not expr.strip() or len(expr) > 160:
        raise ValueError("fn: not a short text")
    toks = _tokens(expr.lower().replace("·", "*").replace("×", "*").replace("−", "-").replace("²", "^2").replace("³", "^3"))
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else ("end", "")

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def expect(value):
        if peek() != ("op", value):
            raise ValueError(f"fn: {value!r} expected")
        take()

    def expression():
        node = term()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            left, right = node, term()
            node = (lambda a, b: lambda x: a(x) + b(x))(left, right) if op == "+" else \
                (lambda a, b: lambda x: a(x) - b(x))(left, right)
        return node

    def term():
        node = unary()
        while True:
            kind, value = peek()
            if (kind, value) in (("op", "*"), ("op", "/")):
                take()
                left, right = node, unary()
                node = (lambda a, b: lambda x: a(x) * b(x))(left, right) if value == "*" else \
                    (lambda a, b: lambda x: _div(a(x), b(x)))(left, right)
            elif kind in ("num", "name") or (kind, value) == ("op", "("):  # implicit: 2x, 3(x + 1), x sin(x)
                left, right = node, power()
                node = (lambda a, b: lambda x: a(x) * b(x))(left, right)
            else:
                return node

    def unary():
        if peek() == ("op", "-"):
            take()
            inner = unary()
            return lambda x: -inner(x)
        if peek() == ("op", "+"):
            take()
            return unary()
        return power()

    def power():
        base = atom()
        if peek() == ("op", "^"):
            take()
            exponent = unary()
            return lambda x: _pow(base(x), exponent(x))
        return base

    def atom():
        kind, value = take() if pos < len(toks) else ("end", "")
        if kind == "num":
            v = float(value)
            return lambda x: v
        if kind == "name":
            if value == "x":
                return lambda x: x
            if value in ("pi", "e"):
                v = math.pi if value == "pi" else math.e
                return lambda x: v
            if value in FUNCTIONS:
                fn = FUNCTIONS[value]
                expect("(")
                inner = expression()
                expect(")")
                return lambda x: _call(fn, inner(x))
            raise ValueError(f"fn: unknown name {value!r}")
        if (kind, value) == ("op", "("):
            inner = expression()
            expect(")")
            return inner
        raise ValueError("fn: incomplete")

    result = expression()
    if pos != len(toks):
        raise ValueError("fn: extra text")
    return result


def _div(a: float, b: float) -> float:
    return a / b if b != 0 else math.nan


def _pow(a: float, b: float) -> float:
    try:
        v = a ** b
    except (OverflowError, ZeroDivisionError):
        return math.nan
    return v if isinstance(v, float) or isinstance(v, int) else math.nan  # a complex result: no real value


def _call(fn, v: float) -> float:
    try:
        return float(fn(v))
    except (ValueError, OverflowError):
        return math.nan


# --- the figure ------------------------------------------------------------------------------------

def _el(tag: str, attrs: dict | None = None, children: list | None = None) -> list:
    return [tag, {k: v for k, v in (attrs or {}).items() if v is not None and v != ""}, children or []]


def _points(v, name: str, budget: list[int], labels: bool = False) -> list[tuple]:
    if not isinstance(v, list) or not v:
        raise ValueError(f"{name}: not a list of points")
    budget[0] -= len(v)
    if budget[0] < 0:
        raise ValueError("too many points")
    out = []
    for p in v:
        if not isinstance(p, list) or len(p) not in ((2, 3) if labels else (2,)):
            raise ValueError(f"{name}: not [x, y]")
        out.append((_number(p[0], name), _number(p[1], name), _text(p[2], name, 32) if len(p) == 3 else ""))
    return out


def _color(item: dict, default: int) -> int:
    c = item.get("color", default)
    if isinstance(c, bool) or not isinstance(c, (int, float)) or c not in range(COLORS):
        raise ValueError("color: 0 to 3")
    return int(c)


def _clip_segments(pts: list[tuple[float, float]], lo: float, hi: float) -> list[list[tuple[float, float]]]:
    """Runs of a sampled curve inside lo <= y <= hi; a run that leaves the range ends on its edge."""
    runs, run = [], []
    prev = None
    for x, y in pts:
        inside = math.isfinite(y) and lo <= y <= hi
        if inside:
            if not run and prev is not None and math.isfinite(prev[1]):  # enters from outside: start on the edge
                edge = hi if prev[1] > hi else lo
                run.append((prev[0] + (x - prev[0]) * (edge - prev[1]) / (y - prev[1]), edge))
            run.append((x, y))
        else:
            if run and math.isfinite(y):  # leaves: end on the edge
                px, py = run[-1]
                edge = hi if y > hi else lo
                run.append((px + (x - px) * (edge - py) / (y - py), edge))
            if run:
                runs.append(run)
            run = []
        prev = (x, y)
    if run:
        runs.append(run)
    return [r for r in runs if len(r) > 1]


def tree(spec) -> list:
    """The SVG of a figure as nested [tag, attrs, children] (a child is a list or a text); ValueError if not valid."""
    if not isinstance(spec, dict):
        raise ValueError("not an object")
    kind = spec.get("type", "plot")
    alt = _text(spec.get("alt"), "alt", 600)
    if not alt:
        raise ValueError("alt: missing")
    _text(spec.get("caption"), "caption", 200)
    if kind == "bar":
        return _bar(spec, alt)
    if kind != "plot":
        raise ValueError("type: plot or bar")
    return _plot(spec, alt)


def _frame(width: float, height: float, alt: str, children: list) -> list:
    return _el("svg", {"xmlns": "http://www.w3.org/2000/svg", "class": "fig", "viewBox": f"0 0 {num(width)} {num(height)}",
                       "width": num(width), "height": num(height), "role": "img", "aria-label": alt},
               [_el("title", {}, [alt]), *children])


def _plot(spec: dict, alt: str) -> list:
    x0, x1 = _range(spec.get("x"), "x")
    y0, y1 = _range(spec.get("y"), "y")
    axes = spec.get("axes", True)
    if not isinstance(axes, bool):
        raise ValueError("axes: true or false")
    equal = spec.get("equal", not axes)
    if not isinstance(equal, bool):
        raise ValueError("equal: true or false")
    items = spec.get("items", [])
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError(f"items: a list of at most {MAX_ITEMS}")
    xlabel = _text(spec.get("xlabel", "x" if axes else ""), "xlabel", 60)
    ylabel = _text(spec.get("ylabel", "y" if axes else ""), "ylabel", 60)
    grid = spec.get("grid", None)
    if grid is not None:
        grid = _number(grid, "grid")
        if grid < 0:
            raise ValueError("grid: not negative")

    ml, mr, mt, mb = (40, 24, 22, 30) if axes else (14, 14, 14, 14)
    if equal:
        s = min(440 / (x1 - x0), 340 / (y1 - y0))
        sx = sy = s
        pw, ph = (x1 - x0) * s, (y1 - y0) * s
    else:
        pw, ph = 440.0, 320.0
        sx, sy = pw / (x1 - x0), ph / (y1 - y0)

    def X(x):
        return ml + (x - x0) * sx

    def Y(y):
        return mt + (y1 - y) * sy

    width, height = ml + pw + mr, mt + ph + mb
    out: list = []
    if axes:
        step_x = grid if grid and (x1 - x0) / grid <= 40 else nice_step(x1 - x0)
        step_y = grid if grid and (y1 - y0) / grid <= 40 else nice_step(y1 - y0)
        tx, ty = ticks(x0, x1, step_x), ticks(y0, y1, step_y)
        if grid != 0:
            lines = [f"M{num(X(x))} {num(Y(y0))}V{num(Y(y1))}" for x in tx] + \
                    [f"M{num(X(x0))} {num(Y(y))}H{num(X(x1))}" for y in ty]
            out.append(_el("path", {"class": "fig-grid", "d": "".join(lines)}))
        ax = 0.0 if y0 <= 0 <= y1 else y0  # the height of the x-axis
        ay = 0.0 if x0 <= 0 <= x1 else x0  # the place of the y-axis
        out.append(_el("path", {"class": "fig-axis",
                                "d": f"M{num(X(x0))} {num(Y(ax))}H{num(X(x1) + 8)}M{num(X(ay))} {num(Y(y0))}V{num(Y(y1) - 8)}"}))
        out.append(_el("path", {"class": "fig-arrow", "d": f"M{num(X(x1) + 12)} {num(Y(ax))}l-7 -3.5v7z"
                                                            f"M{num(X(ay))} {num(Y(y1) - 12)}l-3.5 7h7z"}))
        every_x = max(1, math.ceil(len(tx) / 12))
        every_y = max(1, math.ceil(len(ty) / 12))
        labels = []
        for x in tx:
            if not _labelled(x, step_x * every_x) or (x == 0 and ay == 0):
                continue
            labels.append(_el("text", {"class": "fig-tick", "x": num(X(x)), "y": num(Y(ax) + 15), "text-anchor": "middle"}, [num(x)]))
        for y in ty:
            if not _labelled(y, step_y * every_y) or (y == 0 and ax == 0):
                continue
            labels.append(_el("text", {"class": "fig-tick", "x": num(X(ay) - 6), "y": num(Y(y) + 4), "text-anchor": "end"}, [num(y)]))
        if ax == 0 and ay == 0:
            labels.append(_el("text", {"class": "fig-tick", "x": num(X(0) - 6), "y": num(Y(0) + 15), "text-anchor": "end"}, ["0"]))
        if xlabel:
            labels.append(_el("text", {"class": "fig-label", "x": num(X(x1) + 12), "y": num(Y(ax) - 8), "text-anchor": "end"}, [xlabel]))
        if ylabel:
            labels.append(_el("text", {"class": "fig-label", "x": num(X(ay) + 8), "y": num(Y(y1) - 6), "text-anchor": "start"}, [ylabel]))
        out.extend(labels)

    budget = [MAX_POINTS]
    curves = 0
    marks: list = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("items: objects only")
        label = _text(item.get("label"), "label", 60)
        dash = item.get("dash", False)
        if not isinstance(dash, bool):
            raise ValueError("dash: true or false")
        if "fn" in item:
            fn = compile_fn(item["fn"])
            a, b = _range(item["domain"], "domain") if "domain" in item else (x0, x1)
            a, b = max(a, x0), min(b, x1)
            color = _color(item, curves % COLORS)
            curves += 1
            if b <= a:
                continue
            pts = [(a + (b - a) * k / SAMPLES, fn(a + (b - a) * k / SAMPLES)) for k in range(SAMPLES + 1)]
            runs = _clip_segments(pts, y0, y1)
            d = "".join("M" + "L".join(f"{num(X(x))} {num(Y(y))}" for x, y in r) for r in runs)
            if d:
                out.append(_el("path", {"class": f"fig-line fig-c{color}" + (" fig-dash" if dash else ""), "d": d}))
            if label and runs:
                lx, ly = runs[-1][-1]
                marks.append(_el("text", {"class": f"fig-text fig-t{color}", "x": num(min(X(lx) + 4, width - 4)),
                                          "y": num(max(Y(ly) - 6, 12)), "text-anchor": "end" if X(lx) > width - 60 else "start"}, [label]))
        elif "line" in item:
            pts = _points(item["line"], "line", budget)
            closed = item.get("closed", False)
            fill = item.get("fill", False)
            if not isinstance(closed, bool) or not isinstance(fill, bool):
                raise ValueError("closed, fill: true or false")
            if len(pts) < 2:
                raise ValueError("line: two points at least")
            color = _color(item, 0)
            d = "M" + "L".join(f"{num(X(x))} {num(Y(y))}" for x, y, _ in pts) + ("Z" if closed else "")
            cls = f"fig-line fig-c{color}" + (" fig-dash" if dash else "") + (f" fig-fill fig-f{color}" if closed and fill else "")
            out.append(_el("path", {"class": cls, "d": d}))
            if label:
                mx = sum(p[0] for p in pts) / len(pts)
                my = sum(p[1] for p in pts) / len(pts)
                marks.append(_el("text", {"class": f"fig-text fig-t{color}", "x": num(X(mx)), "y": num(Y(my) - 6),
                                          "text-anchor": "middle"}, [label]))
        elif "points" in item:
            pts = _points(item["points"], "points", budget, labels=True)
            color = _color(item, 0)
            # A label stands outside the shape: away from the middle of the item's points (the vertices of a figure).
            mx, my = sum(X(p[0]) for p in pts) / len(pts), sum(Y(p[1]) for p in pts) / len(pts)
            for x, y, name in pts:
                marks.append(_el("circle", {"class": f"fig-dot fig-d{color}", "cx": num(X(x)), "cy": num(Y(y)), "r": "3.5"}))
                if name:
                    dx, dy = X(x) - mx, Y(y) - my
                    length = math.hypot(dx, dy)
                    if len(pts) < 3 or length < 1:
                        marks.append(_el("text", {"class": "fig-text", "x": num(X(x) + 6), "y": num(Y(y) - 6)}, [name]))
                        continue
                    ux, uy = dx / length, dy / length
                    anchor = "start" if ux > 0.35 else "end" if ux < -0.35 else "middle"
                    marks.append(_el("text", {"class": "fig-text", "x": num(X(x) + 9 * ux), "y": num(Y(y) + 9 * uy + 4 + 4 * uy),
                                              "text-anchor": anchor}, [name]))
        elif "circle" in item:
            c = item["circle"]
            if not isinstance(c, list) or len(c) != 3:
                raise ValueError("circle: [x, y, r]")
            cx, cy, r = (_number(v, "circle") for v in c)
            if r <= 0:
                raise ValueError("circle: r above 0")
            color = _color(item, 0)
            out.append(_el("ellipse", {"class": f"fig-line fig-c{color}" + (" fig-dash" if dash else ""),
                                       "cx": num(X(cx)), "cy": num(Y(cy)), "rx": num(r * sx), "ry": num(r * sy)}))
            if label:
                marks.append(_el("text", {"class": f"fig-text fig-t{color}", "x": num(X(cx)), "y": num(Y(cy + r) - 6),
                                          "text-anchor": "middle"}, [label]))
        elif "text" in item:
            words = _text(item["text"], "text", 80)
            at = item.get("at")
            if not isinstance(at, list) or len(at) != 2:
                raise ValueError("at: [x, y]")
            marks.append(_el("text", {"class": "fig-text", "x": num(X(_number(at[0], "at"))), "y": num(Y(_number(at[1], "at"))),
                                      "text-anchor": "middle"}, [words]))
        else:
            raise ValueError("item: fn, line, points, circle or text")
    return _frame(width, height, alt, out + marks)


def _bar(spec: dict, alt: str) -> list:
    bars = spec.get("bars")
    if not isinstance(bars, list) or not bars or len(bars) > MAX_BARS:
        raise ValueError(f"bars: a list of 1 to {MAX_BARS}")
    rows = []
    for b in bars:
        if not isinstance(b, list) or len(b) != 2:
            raise ValueError("bars: [label, value]")
        rows.append((_text(b[0], "bars", 32), _number(b[1], "bars")))
    ylabel = _text(spec.get("ylabel"), "ylabel", 60)
    xlabel = _text(spec.get("xlabel"), "xlabel", 60)
    if "y" in spec:
        y0, y1 = _range(spec["y"], "y")
    else:
        lo, hi = min(0.0, *(v for _, v in rows)), max(0.0, *(v for _, v in rows))
        hi = hi if hi > lo else lo + 1
        step = nice_step(hi - lo, 6)
        y0, y1 = math.floor(lo / step) * step, math.ceil(hi * 1.08 / step) * step
    ml, mr, mt, mb = 48, 16, 26 if ylabel else 16, 40 if xlabel else 28
    pw, ph = max(300.0, min(480.0, 64.0 * len(rows))), 260.0
    sy = ph / (y1 - y0)

    def Y(y):
        return mt + (y1 - min(max(y, y0), y1)) * sy

    step = nice_step(y1 - y0, 6)
    ty = ticks(y0, y1, step)
    out: list = [_el("path", {"class": "fig-grid", "d": "".join(f"M{num(ml)} {num(Y(y))}H{num(ml + pw)}" for y in ty)})]
    out += [_el("text", {"class": "fig-tick", "x": num(ml - 6), "y": num(Y(y) + 4), "text-anchor": "end"}, [num(y)]) for y in ty]
    slot = pw / len(rows)
    base = Y(max(y0, 0.0))
    for n, (name, value) in enumerate(rows):
        x = ml + slot * n + slot * 0.18
        top = Y(value)
        out.append(_el("rect", {"class": "fig-bar", "x": num(x), "y": num(min(top, base)), "width": num(slot * 0.64),
                                "height": num(abs(base - top))}))
        out.append(_el("text", {"class": "fig-value", "x": num(x + slot * 0.32), "y": num(min(top, base) - 5), "text-anchor": "middle"}, [num(value)]))
        out.append(_el("text", {"class": "fig-tick", "x": num(x + slot * 0.32), "y": num(mt + ph + 16), "text-anchor": "middle"}, [name]))
    out.append(_el("path", {"class": "fig-axis", "d": f"M{num(ml)} {num(mt)}V{num(mt + ph)}H{num(ml + pw)}"}))
    if ylabel:
        out.append(_el("text", {"class": "fig-label", "x": num(ml - 40), "y": num(mt - 10), "text-anchor": "start"}, [ylabel]))
    if xlabel:
        out.append(_el("text", {"class": "fig-label", "x": num(ml + pw / 2), "y": num(mt + ph + 34), "text-anchor": "middle"}, [xlabel]))
    return _frame(ml + pw + mr, mt + ph + mb, alt, out)


# --- output ----------------------------------------------------------------------------------------

def load(text: str) -> dict | None:
    """The figure object of a block's text, or None when it is not valid JSON or not a valid figure."""
    try:
        spec = json.loads(text)
        tree(spec)
    except (ValueError, TypeError, RecursionError):
        return None
    return spec


def serialize(node) -> str:
    if isinstance(node, str):
        return html.escape(node, quote=False)
    tag, attrs, children = node
    attributes = "".join(f' {k}="{html.escape(str(v))}"' for k, v in attrs.items())
    return f"<{tag}{attributes}>{''.join(serialize(c) for c in children)}</{tag}>"


def svg(text: str) -> str | None:
    """The SVG markup of a figure block's text, or None when it is not a valid figure."""
    spec = load(text)
    return serialize(tree(spec)) if spec is not None else None


def caption(spec: dict) -> str:
    """The caption of a figure that load() accepted ("" when it has none)."""
    return _text(spec.get("caption"), "caption", 200)


def alt_text(text: str) -> str | None:
    spec = load(text)
    return None if spec is None else " ".join(spec["alt"].split())


def as_text(markdown: str) -> str:
    """The Markdown with each valid figure block replaced by its description in italics (Word, PDF, e-mail)."""
    def replace(m: re.Match) -> str:
        alt = alt_text(m.group(2))
        return m.group(0) if alt is None else "*" + alt.replace("*", "∗") + "*"
    return FENCE.sub(replace, markdown)
