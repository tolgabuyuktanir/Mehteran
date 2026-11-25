// A small Markdown renderer for the results of a run (the reader, the compare view): headings, paragraphs, bold,
// italic, strikethrough, lists, numbered lists, block quotes, code, GFM pipe tables, links, horizontal rules and
// figures (a code block marked "figure", drawn as SVG from its JSON data).
// It works in two steps: parse() makes a tree of plain objects, toDom() builds elements with createElement and text
// nodes only (the page's Content-Security-Policy; no HTML string ever becomes markup). Raw HTML in the text stays
// text. A link opens only an http or https address, in a new tab, without the opener and the referrer. Each block
// has dir="auto": an Arabic paragraph reads right to left, an English one left to right, on any page. A line break
// inside a paragraph is kept (as document.export's Pandoc reading does: markdown+hard_line_breaks).
// Node.js loads this file too (tests/mehteran_markdown_test.mjs): it uses no browser global at load time.
"use strict";

(function (root) {
  const FENCE = /^ {0,3}(`{3,}|~{3,})\s*([^\s`]*)[^`]*$/;
  const HEADING = /^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$/;
  const RULE = /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/;
  const QUOTE = /^ {0,3}> ?/;
  const ITEM = /^( {0,3})([-*+]|\d{1,9}[.)])([ \t]+|$)(.*)$/;
  const DELIMITER = /^ {0,3}\|?[ \t]*:?-+:?[ \t]*(\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;
  const SETEXT = /^ {0,3}(=+|-+)[ \t]*$/;
  const blank = (line) => !line.trim();

  // --- blocks ------------------------------------------------------------------------------------
  function parse(text) {
    return blocks(String(text == null ? "" : text).replace(/\r\n?/g, "\n").replace(/\t/g, "    ").split("\n"));
  }

  // A pipe table: a header row, then a delimiter row with as many cells.
  const tableStart = (line, next) => line.includes("|") && next != null && DELIMITER.test(next) && next.includes("-")
    && cells(next).length === cells(line).length;

  // A line that starts another block ends a paragraph. A numbered item does so only when it is "1." (as in
  // CommonMark): "2024. was a good year" goes on.
  function startsBlock(line, next) {
    const item = ITEM.exec(line);
    return FENCE.test(line) || HEADING.test(line) || RULE.test(line) || QUOTE.test(line) || tableStart(line, next)
      || Boolean(item && item[4].trim() && (!/\d/.test(item[2]) || parseInt(item[2], 10) === 1));
  }

  function blocks(lines) {
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i], start = i;
      let m, block;
      if (blank(line)) { i++; continue; }
      if ((m = FENCE.exec(line))) {
        const mark = m[1], body = [];
        const closes = (l) => { const c = /^ {0,3}(`{3,}|~{3,})\s*$/.exec(l); return c && c[1][0] === mark[0] && c[1].length >= mark.length; };
        i++;
        while (i < lines.length && !closes(lines[i])) body.push(lines[i++]);
        i++;  // the closing fence (or the end of the text)
        block = {type: "code", lang: m[2], text: body.join("\n")};
      } else if ((m = HEADING.exec(line))) {
        block = {type: "heading", level: m[1].length, inlines: inline(m[2] || "")};
        i++;
      } else if (RULE.test(line)) {
        block = {type: "hr"};
        i++;
      } else if (QUOTE.test(line)) {
        const body = [];
        while (i < lines.length && !blank(lines[i]) && (QUOTE.test(lines[i]) || !startsBlock(lines[i], lines[i + 1]))) {
          body.push(lines[i].replace(QUOTE, ""));
          i++;
        }
        block = {type: "quote", blocks: blocks(body)};
      } else if (ITEM.test(line)) {
        [block, i] = list(lines, i);
      } else if (tableStart(line, lines[i + 1])) {
        [block, i] = table(lines, i);
      } else {
        const body = [line.trim()];
        i++;
        let level = 0;
        while (i < lines.length && !blank(lines[i])) {
          if ((m = SETEXT.exec(lines[i]))) { level = m[1][0] === "=" ? 1 : 2; i++; break; }
          if (startsBlock(lines[i], lines[i + 1])) break;
          body.push(lines[i++].trim());
        }
        block = level ? {type: "heading", level, inlines: inline(body.join(" "))} : {type: "paragraph", inlines: inline(body.join("\n"))};
      }
      // The block's own lines, without spacing: the compare view finds the paragraphs that differ by it.
      block.src = lines.slice(start, i).join("\n").replace(/\s+/g, " ").trim();
      out.push(block);
    }
    return out;
  }

  function list(lines, i) {
    const first = ITEM.exec(lines[i]);
    const ordered = /\d/.test(first[2]);
    const marker = ordered ? first[2].slice(-1) : first[2];
    const items = [];
    while (i < lines.length) {
      const m = ITEM.exec(lines[i]);
      if (!m || /\d/.test(m[2]) !== ordered || (ordered ? m[2].slice(-1) : m[2]) !== marker) break;
      const indent = m[1].length + m[2].length + Math.max(1, Math.min(m[3].length, 4));
      const body = [m[4]];
      i++;
      while (i < lines.length) {
        const line = lines[i];
        if (blank(line)) {
          let j = i;
          while (j < lines.length && blank(lines[j])) j++;
          if (j < lines.length && lines[j].search(/\S/) >= indent) { while (i < j) { body.push(""); i++; } continue; }
          break;
        }
        const lead = line.search(/\S/);
        if (lead >= indent) body.push(line.slice(indent));
        else if (!ITEM.test(line) && !startsBlock(line, lines[i + 1]) && !blank(body[body.length - 1])) body.push(line.trim());  // a lazy line
        else break;
        i++;
      }
      items.push(blocks(body));
      // A blank line between two items of the same list keeps the list.
      let j = i;
      while (j < lines.length && blank(lines[j])) j++;
      if (j > i && j < lines.length && ITEM.test(lines[j])) i = j;
    }
    return [{type: "list", ordered, start: ordered ? parseInt(first[2], 10) : 1, items}, i];
  }

  function cells(line) {
    let row = line.trim();
    if (row.startsWith("|")) row = row.slice(1);
    if (row.endsWith("|") && !row.endsWith("\\|")) row = row.slice(0, -1);
    const out = [];
    let cell = "", code = false;
    for (let k = 0; k < row.length; k++) {
      const c = row[k];
      if (c === "\\" && row[k + 1] === "|") { cell += "|"; k++; continue; }
      if (c === "`") code = !code;
      if (c === "|" && !code) { out.push(cell.trim()); cell = ""; continue; }
      cell += c;
    }
    out.push(cell.trim());
    return out;
  }

  function table(lines, i) {
    const head = cells(lines[i]);
    const align = cells(lines[i + 1]).map((c) => (c.startsWith(":") && c.endsWith(":") ? "center" : c.endsWith(":") ? "right" : c.startsWith(":") ? "left" : ""));
    i += 2;
    const rows = [];
    while (i < lines.length && !blank(lines[i]) && lines[i].includes("|")) {
      const row = cells(lines[i++]);
      rows.push(head.map((_, k) => inline(row[k] || "")));
    }
    return [{type: "table", align: head.map((_, k) => align[k] || ""), head: head.map((c) => inline(c)), rows}, i];
  }

  // --- inline text -----------------------------------------------------------------------------------
  const PUNCT = /[!-/:-@[-`{-~]/;
  const URL_RE = /^https?:\/\/[^\s<>]*[^\s<>.,:;"'!?)\]*_~]/i;
  const safeUrl = (url) => (/^https?:\/\/[^\s]+$/i.test(url) ? url : null);

  function inline(text) {
    const out = [];
    let plain = "";
    const push = (node) => { if (plain) { out.push({type: "text", text: plain}); plain = ""; } out.push(node); };
    let i = 0;
    while (i < text.length) {
      const c = text[i];
      let m;
      if (c === "\\" && text[i + 1] === "\n") { push({type: "br"}); i += 2; continue; }
      if (c === "\\" && PUNCT.test(text[i + 1] || "")) { plain += text[i + 1]; i += 2; continue; }
      if (c === "\n") { plain = plain.replace(/ +$/, ""); push({type: "br"}); i++; continue; }
      if (c === "`") {
        const run = /^`+/.exec(text.slice(i))[0];
        const end = text.indexOf(run, i + run.length);
        if (end > 0 && text[end + run.length] !== "`") {
          let code = text.slice(i + run.length, end).replace(/\n/g, " ");
          if (/^ .*[^ ].* $/.test(code)) code = code.slice(1, -1);
          push({type: "code", text: code});
          i = end + run.length;
          continue;
        }
        plain += run;
        i += run.length;
        continue;
      }
      if (c === "<" && (m = /^<(https?:\/\/[^\s<>]+)>/i.exec(text.slice(i)))) {
        push({type: "link", href: m[1], children: [{type: "text", text: m[1]}]});
        i += m[0].length;
        continue;
      }
      if ((c === "[" || (c === "!" && text[i + 1] === "[")) && (m = link(text, c === "!" ? i + 1 : i))) {
        const children = inline(m.label);
        const href = safeUrl(m.href);
        if (href) push({type: "link", href, children});
        else if (children.length) children.forEach((child) => push(child));  // not a web address: only its text
        i = m.end;
        continue;
      }
      if ((c === "h" || c === "H") && !/[\w/]/.test(text[i - 1] || "") && (m = URL_RE.exec(text.slice(i)))) {
        push({type: "link", href: m[0], children: [{type: "text", text: m[0]}]});
        i += m[0].length;
        continue;
      }
      if (c === "*" || c === "_" || (c === "~" && text[i + 1] === "~")) {
        const found = emphasis(text, i);
        if (found) { push(found.node); i = found.end; continue; }
        const run = new RegExp("^\\" + c + "+").exec(text.slice(i))[0];
        plain += run;
        i += run.length;
        continue;
      }
      plain += c;
      i++;
    }
    if (plain) out.push({type: "text", text: plain});
    return out;
  }

  // [label](href "title"): the label's end (brackets may nest), then the address up to its closing parenthesis.
  function link(text, i) {
    let depth = 0, k = i;
    for (; k < text.length; k++) {
      if (text[k] === "\\") { k++; continue; }
      if (text[k] === "[") depth++;
      else if (text[k] === "]" && --depth === 0) break;
    }
    if (k >= text.length || text[k + 1] !== "(") return null;
    const label = text.slice(i + 1, k);
    let j = k + 2, parens = 0, href = "";
    while (j < text.length && text[j] === " ") j++;
    if (text[j] === "<") {
      const close = text.indexOf(">", j);
      if (close < 0) return null;
      href = text.slice(j + 1, close);
      j = close + 1;
    } else {
      for (; j < text.length && !/\s/.test(text[j]); j++) {
        if (text[j] === "(") parens++;
        else if (text[j] === ")" && parens-- === 0) break;
        href += text[j];
      }
    }
    const rest = /^\s*(?:"[^"]*"|'[^']*')?\s*\)/.exec(text.slice(j));
    if (!rest) return null;
    return {label, href, end: j + rest[0].length};
  }

  // **strong**, *em*, ***both***, __strong__, _em_, ~~del~~: an opening run not followed by a space, and a closing
  // run of the same length not after a space. An underscore inside a word (snake_case) is not emphasis.
  function emphasis(text, i) {
    const c = text[i];
    const run = new RegExp("^\\" + c + "+").exec(text.slice(i))[0];
    const n = c === "~" ? 2 : Math.min(run.length, 3);
    if (c === "~" && run.length !== 2) return null;
    if (/\s/.test(text[i + run.length] || " ")) return null;
    if (c === "_" && /[\p{L}\p{N}]/u.test(text[i - 1] || "")) return null;
    for (let k = i + run.length; k < text.length; k++) {
      if (text[k] === "\\") { k++; continue; }
      if (text[k] === "`") {  // a code span inside is skipped as a whole
        const tick = /^`+/.exec(text.slice(k))[0], end = text.indexOf(tick, k + tick.length);
        if (end > 0) { k = end + tick.length - 1; continue; }
      }
      if (text[k] !== c) continue;
      const close = new RegExp("^\\" + c + "+").exec(text.slice(k))[0];
      if (close.length === run.length && !/\s/.test(text[k - 1]) && !(c === "_" && /[\p{L}\p{N}]/u.test(text[k + close.length] || ""))) {
        const children = inline(text.slice(i + run.length, k));
        const node = c === "~" ? {type: "del", children} : n === 1 ? {type: "em", children} : n === 2 ? {type: "strong", children}
          : {type: "strong", children: [{type: "em", children}]};
        return {node, end: k + close.length};
      }
      k += close.length - 1;
    }
    return null;
  }

  // --- figures ------------------------------------------------------------------------------------
  // A code block marked "figure" holds one JSON object that describes a coordinate plane ("plot") or a bar chart
  // ("bar"). figure(spec) returns the SVG as nested [tag, attrs, children]; it throws for an invalid figure, which then
  // stays a code block. The rules are those of mehteran/common/figure.py (the HTML export), which documents them;
  // tests/test_mehteran_figure.py compares the two.
  const FIG = (function () {
    const MAX_ITEMS = 40, MAX_POINTS = 2000, MAX_BARS = 24, SAMPLES = 240, COLORS = 4;
    const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
    const get = (o, k, d) => (has(o, k) ? o[k] : d);
    const bad = (why) => { throw new Error(why); };
    const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
    const num = (v) => { const t = v.toFixed(2).replace(/\.?0+$/, ""); return t === "-0" || t === "" ? "0" : t; };
    const number = (v, name) => (typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= 1e6 ? v : bad(name + ": not a number"));
    const text = (v, name, limit) => {
      if (v == null) return "";
      if (typeof v !== "string" || v.length > limit) bad(name + ": not a short text");
      return v.split(/\s+/).filter(Boolean).join(" ");
    };
    const range = (v, name) => {
      if (!Array.isArray(v) || v.length !== 2) bad(name + ": not [min, max]");
      const lo = number(v[0], name), hi = number(v[1], name);
      if (!(hi > lo)) bad(name + ": max is not above min");
      return [lo, hi];
    };
    const flag = (v, name) => (typeof v === "boolean" ? v : bad(name + ": true or false"));
    function niceStep(span, target) {
      const raw = span / (target || 8), mag = Math.pow(10, Math.floor(Math.log10(raw)));
      for (const k of [1, 2, 5, 10]) if (raw <= k * mag * 1.0000001) return k * mag;
      return 10 * mag;
    }
    const labelled = (v, every) => Math.abs(v / every - Math.round(v / every)) < 1e-6;
    function ticks(lo, hi, step) {
      const out = [];
      for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + 1e-9 * step && out.length < 201; k++) out.push(Math.abs(k * step) < 1e-9 * step ? 0 : k * step);
      return out;
    }

    // A function of x, parsed by hand (see compile_fn in figure.py).
    const FUNCTIONS = {sqrt: Math.sqrt, abs: Math.abs, sin: Math.sin, cos: Math.cos, tan: Math.tan, exp: Math.exp, ln: Math.log, log: Math.log10};
    function compileFn(expr) {
      if (typeof expr !== "string" || !expr.trim() || expr.length > 160) bad("fn: not a short text");
      const src = expr.toLowerCase().replace(/·|×/g, "*").replace(/−/g, "-").replace(/²/g, "^2").replace(/³/g, "^3");
      const toks = [];
      const re = /\s*(?:(\d+\.?\d*|\.\d+)|([a-z]+)|(.))/y;
      let m;
      while (re.lastIndex < src.length && (m = re.exec(src)) && m[0].length) {
        if (m[1]) toks.push(["num", m[1]]);
        else if (m[2]) toks.push(["name", m[2]]);
        else if (m[3].trim()) { if (!"+-*/^()".includes(m[3])) bad("fn: unknown sign"); toks.push(["op", m[3]]); }
      }
      let pos = 0;
      const peek = () => (pos < toks.length ? toks[pos] : ["end", ""]);
      const is = (kind, value) => peek()[0] === kind && peek()[1] === value;
      const expect = (value) => { if (!is("op", value)) bad("fn: " + value + " expected"); pos++; };
      const finite = (v) => (typeof v === "number" ? v : NaN);
      function expression() {
        let node = term();
        while (is("op", "+") || is("op", "-")) {
          const op = toks[pos++][1], a = node, b = term();
          node = op === "+" ? (x) => a(x) + b(x) : (x) => a(x) - b(x);
        }
        return node;
      }
      function term() {
        let node = unary();
        for (;;) {
          const [kind, value] = peek();
          if (kind === "op" && (value === "*" || value === "/")) {
            pos++;
            const a = node, b = unary();
            node = value === "*" ? (x) => a(x) * b(x) : (x) => { const d = b(x); return d !== 0 ? a(x) / d : NaN; };
          } else if (kind === "num" || kind === "name" || (kind === "op" && value === "(")) {
            const a = node, b = power();
            node = (x) => a(x) * b(x);
          } else return node;
        }
      }
      function unary() {
        if (is("op", "-")) { pos++; const inner = unary(); return (x) => -inner(x); }
        if (is("op", "+")) { pos++; return unary(); }
        return power();
      }
      function power() {
        const base = atom();
        if (is("op", "^")) { pos++; const exponent = unary(); return (x) => finite(Math.pow(base(x), exponent(x))); }
        return base;
      }
      function atom() {
        const [kind, value] = pos < toks.length ? toks[pos++] : ["end", ""];
        if (kind === "num") { const v = parseFloat(value); return () => v; }
        if (kind === "name") {
          if (value === "x") return (x) => x;
          if (value === "pi" || value === "e") { const v = value === "pi" ? Math.PI : Math.E; return () => v; }
          if (has(FUNCTIONS, value)) {
            const fn = FUNCTIONS[value];
            expect("(");
            const inner = expression();
            expect(")");
            return (x) => fn(inner(x));
          }
          bad("fn: unknown name");
        }
        if (kind === "op" && value === "(") { const inner = expression(); expect(")"); return inner; }
        return bad("fn: incomplete");
      }
      const result = expression();
      if (pos !== toks.length) bad("fn: extra text");
      return result;
    }

    const el = (tag, attrs, children) => {
      const clean = {};
      for (const [k, v] of Object.entries(attrs || {})) if (v != null && v !== "") clean[k] = v;
      return [tag, clean, children || []];
    };
    function points(v, name, budget, labels) {
      if (!Array.isArray(v) || !v.length) bad(name + ": not a list of points");
      budget.left -= v.length;
      if (budget.left < 0) bad("too many points");
      return v.map((p) => {
        if (!Array.isArray(p) || !(labels ? [2, 3] : [2]).includes(p.length)) bad(name + ": not [x, y]");
        return [number(p[0], name), number(p[1], name), p.length === 3 ? text(p[2], name, 32) : ""];
      });
    }
    function color(item, fallback) {
      const c = get(item, "color", fallback);
      if (typeof c !== "number" || ![0, 1, 2, 3].includes(c)) bad("color: 0 to 3");
      return c;
    }
    function clipSegments(pts, lo, hi) {
      const runs = [];
      let run = [], prev = null;
      for (const [x, y] of pts) {
        const inside = Number.isFinite(y) && lo <= y && y <= hi;
        if (inside) {
          if (!run.length && prev && Number.isFinite(prev[1])) {
            const edge = prev[1] > hi ? hi : lo;
            run.push([prev[0] + (x - prev[0]) * (edge - prev[1]) / (y - prev[1]), edge]);
          }
          run.push([x, y]);
        } else {
          if (run.length && Number.isFinite(y)) {
            const [px, py] = run[run.length - 1], edge = y > hi ? hi : lo;
            run.push([px + (x - px) * (edge - py) / (y - py), edge]);
          }
          if (run.length) runs.push(run);
          run = [];
        }
        prev = [x, y];
      }
      if (run.length) runs.push(run);
      return runs.filter((r) => r.length > 1);
    }
    const frame = (width, height, alt, children) => el("svg", {xmlns: "http://www.w3.org/2000/svg", class: "fig",
      viewBox: `0 0 ${num(width)} ${num(height)}`, width: num(width), height: num(height), role: "img", "aria-label": alt},
    [el("title", {}, [alt]), ...children]);

    function plot(spec, alt) {
      const [x0, x1] = range(get(spec, "x"), "x"), [y0, y1] = range(get(spec, "y"), "y");
      const axes = flag(get(spec, "axes", true), "axes");
      const equal = flag(get(spec, "equal", !axes), "equal");
      const items = get(spec, "items", []);
      if (!Array.isArray(items) || items.length > MAX_ITEMS) bad("items: a list of at most " + MAX_ITEMS);
      const xlabel = text(get(spec, "xlabel", axes ? "x" : ""), "xlabel", 60);
      const ylabel = text(get(spec, "ylabel", axes ? "y" : ""), "ylabel", 60);
      let grid = get(spec, "grid", null);
      if (grid != null) { grid = number(grid, "grid"); if (grid < 0) bad("grid: not negative"); }
      const [ml, mr, mt, mb] = axes ? [40, 24, 22, 30] : [14, 14, 14, 14];
      let sx, sy, pw, ph;
      if (equal) {
        const s = Math.min(440 / (x1 - x0), 340 / (y1 - y0));
        sx = sy = s; pw = (x1 - x0) * s; ph = (y1 - y0) * s;
      } else {
        pw = 440; ph = 320; sx = pw / (x1 - x0); sy = ph / (y1 - y0);
      }
      const X = (x) => ml + (x - x0) * sx, Y = (y) => mt + (y1 - y) * sy;
      const width = ml + pw + mr, height = mt + ph + mb;
      const out = [];
      if (axes) {
        const stepX = grid && (x1 - x0) / grid <= 40 ? grid : niceStep(x1 - x0);
        const stepY = grid && (y1 - y0) / grid <= 40 ? grid : niceStep(y1 - y0);
        const tx = ticks(x0, x1, stepX), ty = ticks(y0, y1, stepY);
        if (grid !== 0) out.push(el("path", {class: "fig-grid", d: tx.map((x) => `M${num(X(x))} ${num(Y(y0))}V${num(Y(y1))}`).join("")
          + ty.map((y) => `M${num(X(x0))} ${num(Y(y))}H${num(X(x1))}`).join("")}));
        const ax = y0 <= 0 && 0 <= y1 ? 0 : y0, ay = x0 <= 0 && 0 <= x1 ? 0 : x0;
        out.push(el("path", {class: "fig-axis", d: `M${num(X(x0))} ${num(Y(ax))}H${num(X(x1) + 8)}M${num(X(ay))} ${num(Y(y0))}V${num(Y(y1) - 8)}`}));
        out.push(el("path", {class: "fig-arrow", d: `M${num(X(x1) + 12)} ${num(Y(ax))}l-7 -3.5v7zM${num(X(ay))} ${num(Y(y1) - 12)}l-3.5 7h7z`}));
        const everyX = Math.max(1, Math.ceil(tx.length / 12)), everyY = Math.max(1, Math.ceil(ty.length / 12));
        tx.forEach((x) => { if (labelled(x, stepX * everyX) && !(x === 0 && ay === 0)) out.push(el("text", {class: "fig-tick", x: num(X(x)), y: num(Y(ax) + 15), "text-anchor": "middle"}, [num(x)])); });
        ty.forEach((y) => { if (labelled(y, stepY * everyY) && !(y === 0 && ax === 0)) out.push(el("text", {class: "fig-tick", x: num(X(ay) - 6), y: num(Y(y) + 4), "text-anchor": "end"}, [num(y)])); });
        if (ax === 0 && ay === 0) out.push(el("text", {class: "fig-tick", x: num(X(0) - 6), y: num(Y(0) + 15), "text-anchor": "end"}, ["0"]));
        if (xlabel) out.push(el("text", {class: "fig-label", x: num(X(x1) + 12), y: num(Y(ax) - 8), "text-anchor": "end"}, [xlabel]));
        if (ylabel) out.push(el("text", {class: "fig-label", x: num(X(ay) + 8), y: num(Y(y1) - 6), "text-anchor": "start"}, [ylabel]));
      }
      const budget = {left: MAX_POINTS}, marks = [];
      let curves = 0;
      for (const item of items) {
        if (!isObj(item)) bad("items: objects only");
        const label = text(get(item, "label"), "label", 60);
        const dash = flag(get(item, "dash", false), "dash");
        if (has(item, "fn")) {
          const fn = compileFn(item.fn);
          let [a, b] = has(item, "domain") ? range(item.domain, "domain") : [x0, x1];
          a = Math.max(a, x0); b = Math.min(b, x1);
          const c = color(item, curves % COLORS);
          curves++;
          if (b <= a) continue;
          const pts = [];
          for (let k = 0; k <= SAMPLES; k++) { const x = a + (b - a) * k / SAMPLES; pts.push([x, fn(x)]); }
          const runs = clipSegments(pts, y0, y1);
          const d = runs.map((r) => "M" + r.map(([x, y]) => `${num(X(x))} ${num(Y(y))}`).join("L")).join("");
          if (d) out.push(el("path", {class: `fig-line fig-c${c}` + (dash ? " fig-dash" : ""), d}));
          if (label && runs.length) {
            const last = runs[runs.length - 1], [lx, ly] = last[last.length - 1];
            marks.push(el("text", {class: `fig-text fig-t${c}`, x: num(Math.min(X(lx) + 4, width - 4)), y: num(Math.max(Y(ly) - 6, 12)),
              "text-anchor": X(lx) > width - 60 ? "end" : "start"}, [label]));
          }
        } else if (has(item, "line")) {
          const pts = points(item.line, "line", budget, false);
          const closed = flag(get(item, "closed", false), "closed"), fill = flag(get(item, "fill", false), "fill");
          if (pts.length < 2) bad("line: two points at least");
          const c = color(item, 0);
          const d = "M" + pts.map(([x, y]) => `${num(X(x))} ${num(Y(y))}`).join("L") + (closed ? "Z" : "");
          out.push(el("path", {class: `fig-line fig-c${c}` + (dash ? " fig-dash" : "") + (closed && fill ? ` fig-fill fig-f${c}` : ""), d}));
          if (label) {
            const mx = pts.reduce((s, p) => s + p[0], 0) / pts.length, my = pts.reduce((s, p) => s + p[1], 0) / pts.length;
            marks.push(el("text", {class: `fig-text fig-t${c}`, x: num(X(mx)), y: num(Y(my) - 6), "text-anchor": "middle"}, [label]));
          }
        } else if (has(item, "points")) {
          const pts = points(item.points, "points", budget, true);
          const c = color(item, 0);
          // A label stands outside the shape: away from the middle of the item's points (the vertices of a figure).
          const mx = pts.reduce((s, p) => s + X(p[0]), 0) / pts.length, my = pts.reduce((s, p) => s + Y(p[1]), 0) / pts.length;
          for (const [x, y, name] of pts) {
            marks.push(el("circle", {class: `fig-dot fig-d${c}`, cx: num(X(x)), cy: num(Y(y)), r: "3.5"}));
            if (!name) continue;
            const dx = X(x) - mx, dy = Y(y) - my, length = Math.hypot(dx, dy);
            if (pts.length < 3 || length < 1) { marks.push(el("text", {class: "fig-text", x: num(X(x) + 6), y: num(Y(y) - 6)}, [name])); continue; }
            const ux = dx / length, uy = dy / length;
            marks.push(el("text", {class: "fig-text", x: num(X(x) + 9 * ux), y: num(Y(y) + 9 * uy + 4 + 4 * uy),
              "text-anchor": ux > 0.35 ? "start" : ux < -0.35 ? "end" : "middle"}, [name]));
          }
        } else if (has(item, "circle")) {
          const v = item.circle;
          if (!Array.isArray(v) || v.length !== 3) bad("circle: [x, y, r]");
          const [cx, cy, r] = v.map((n) => number(n, "circle"));
          if (r <= 0) bad("circle: r above 0");
          const c = color(item, 0);
          out.push(el("ellipse", {class: `fig-line fig-c${c}` + (dash ? " fig-dash" : ""), cx: num(X(cx)), cy: num(Y(cy)), rx: num(r * sx), ry: num(r * sy)}));
          if (label) marks.push(el("text", {class: `fig-text fig-t${c}`, x: num(X(cx)), y: num(Y(cy + r) - 6), "text-anchor": "middle"}, [label]));
        } else if (has(item, "text")) {
          const words = text(item.text, "text", 80), at = get(item, "at");
          if (!Array.isArray(at) || at.length !== 2) bad("at: [x, y]");
          marks.push(el("text", {class: "fig-text", x: num(X(number(at[0], "at"))), y: num(Y(number(at[1], "at"))), "text-anchor": "middle"}, [words]));
        } else bad("item: fn, line, points, circle or text");
      }
      return frame(width, height, alt, out.concat(marks));
    }

    function bar(spec, alt) {
      const bars = get(spec, "bars");
      if (!Array.isArray(bars) || !bars.length || bars.length > MAX_BARS) bad("bars: a list of 1 to " + MAX_BARS);
      const rows = bars.map((b) => { if (!Array.isArray(b) || b.length !== 2) bad("bars: [label, value]"); return [text(b[0], "bars", 32), number(b[1], "bars")]; });
      const ylabel = text(get(spec, "ylabel"), "ylabel", 60), xlabel = text(get(spec, "xlabel"), "xlabel", 60);
      let y0, y1;
      if (has(spec, "y")) [y0, y1] = range(spec.y, "y");
      else {
        const lo = Math.min(0, ...rows.map((r) => r[1]));
        let hi = Math.max(0, ...rows.map((r) => r[1]));
        hi = hi > lo ? hi : lo + 1;
        const step = niceStep(hi - lo, 6);
        y0 = Math.floor(lo / step) * step; y1 = Math.ceil(hi * 1.08 / step) * step;
      }
      const ml = 48, mr = 16, mt = ylabel ? 26 : 16, mb = xlabel ? 40 : 28;
      const pw = Math.max(300, Math.min(480, 64 * rows.length)), ph = 260, sy = ph / (y1 - y0);
      const Y = (y) => mt + (y1 - Math.min(Math.max(y, y0), y1)) * sy;
      const ty = ticks(y0, y1, niceStep(y1 - y0, 6));
      const out = [el("path", {class: "fig-grid", d: ty.map((y) => `M${num(ml)} ${num(Y(y))}H${num(ml + pw)}`).join("")})];
      ty.forEach((y) => out.push(el("text", {class: "fig-tick", x: num(ml - 6), y: num(Y(y) + 4), "text-anchor": "end"}, [num(y)])));
      const slot = pw / rows.length, base = Y(Math.max(y0, 0));
      rows.forEach(([name, value], n) => {
        const x = ml + slot * n + slot * 0.18, top = Y(value);
        out.push(el("rect", {class: "fig-bar", x: num(x), y: num(Math.min(top, base)), width: num(slot * 0.64), height: num(Math.abs(base - top))}));
        out.push(el("text", {class: "fig-value", x: num(x + slot * 0.32), y: num(Math.min(top, base) - 5), "text-anchor": "middle"}, [num(value)]));
        out.push(el("text", {class: "fig-tick", x: num(x + slot * 0.32), y: num(mt + ph + 16), "text-anchor": "middle"}, [name]));
      });
      out.push(el("path", {class: "fig-axis", d: `M${num(ml)} ${num(mt)}V${num(mt + ph)}H${num(ml + pw)}`}));
      if (ylabel) out.push(el("text", {class: "fig-label", x: num(ml - 40), y: num(mt - 10), "text-anchor": "start"}, [ylabel]));
      if (xlabel) out.push(el("text", {class: "fig-label", x: num(ml + pw / 2), y: num(mt + ph + 34), "text-anchor": "middle"}, [xlabel]));
      return frame(ml + pw + mr, mt + ph + mb, alt, out);
    }

    function figure(spec) {
      if (!isObj(spec)) bad("not an object");
      const kind = get(spec, "type", "plot"), alt = text(get(spec, "alt"), "alt", 600);
      if (!alt) bad("alt: missing");
      text(get(spec, "caption"), "caption", 200);
      if (kind === "bar") return bar(spec, alt);
      if (kind !== "plot") bad("type: plot or bar");
      return plot(spec, alt);
    }
    // The figure of a block's text: {svg, caption}, or null when it is not a valid figure.
    function load(source) {
      try {
        const spec = JSON.parse(source);
        return {svg: figure(spec), caption: text(get(spec, "caption"), "caption", 200)};
      } catch (err) {
        return null;
      }
    }
    return {figure, load};
  })();

  // --- elements ------------------------------------------------------------------------------------
  // A list, a quote or a table holds blocks with their own dir="auto", which dir="auto" on the container skips: the
  // container takes the direction of the first strong letter of its text (its markers, border and columns follow it).
  const RTL_LETTER = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/;
  const LTR_LETTER = /[A-Za-z\u00C0-\u024F\u0370-\u03FF\u0400-\u04FF]/;
  function textOf(node) {
    if (Array.isArray(node)) return node.map(textOf).join(" ");
    if (!node || typeof node !== "object" || node.type === "code") return "";  // code is left to right anyway
    return node.text || textOf(node.children || node.inlines || node.blocks || node.items || [...(node.head || []), ...(node.rows || [])]);
  }
  function direction(node) {
    for (const ch of textOf(node)) {
      if (RTL_LETTER.test(ch)) return "rtl";
      if (LTR_LETTER.test(ch)) return "ltr";
    }
    return "auto";
  }

  // doc: the document (the page's, or a test's stand-in); opts.mark(src): true for a block to mark as different.
  function toDom(tree, doc, opts) {
    const options = opts || {};
    const el = (tag, attrs, children) => {
      const node = doc.createElement(tag);
      for (const [key, value] of Object.entries(attrs || {})) if (value != null && value !== "") node.setAttribute(key, String(value));
      for (const child of children || []) node.appendChild(child);
      return node;
    };
    const inlines = (items) => items.map((item) => {
      switch (item.type) {
        case "text": return doc.createTextNode(item.text);
        case "br": return el("br");
        case "code": return el("code", {}, [doc.createTextNode(item.text)]);
        case "strong": return el("strong", {}, inlines(item.children));
        case "em": return el("em", {}, inlines(item.children));
        case "del": return el("del", {}, inlines(item.children));
        case "link": return el("a", {href: item.href, target: "_blank", rel: "noopener noreferrer"}, inlines(item.children));
        default: return doc.createTextNode("");
      }
    });
    const svg = (node) => {
      if (typeof node === "string") return doc.createTextNode(node);
      const [tag, attrs, children] = node;
      const e = doc.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [key, value] of Object.entries(attrs)) if (key !== "xmlns") e.setAttribute(key, String(value));
      for (const child of children) e.appendChild(svg(child));
      return e;
    };
    const figure = (b) => {
      const found = b.lang === "figure" && FIG.load(b.text);
      if (!found) return null;
      const caption = found.caption ? [el("figcaption", {dir: "auto"}, [doc.createTextNode(found.caption)])] : [];
      return el("figure", {class: "md-figure"}, [svg(found.svg), ...caption]);
    };
    const block = (b) => {
      switch (b.type) {
        case "heading": return el("h" + b.level, {dir: "auto"}, inlines(b.inlines));
        case "paragraph": return el("p", {dir: "auto"}, inlines(b.inlines));
        case "hr": return el("hr");
        case "code": return figure(b) || el("pre", {dir: "ltr", class: "md-code"}, [el("code", {"data-lang": b.lang || null}, [doc.createTextNode(b.text)])]);
        case "quote": return el("blockquote", {dir: direction(b)}, b.blocks.map(block));
        case "list": return el(b.ordered ? "ol" : "ul", {dir: direction(b), start: b.ordered && b.start !== 1 ? b.start : null},
          b.items.map((item) => el("li", {dir: "auto"}, item.length === 1 && item[0].type === "paragraph" ? inlines(item[0].inlines) : item.map(block))));
        case "table": {
          const cell = (tag, content, k) => el(tag, {dir: "auto", class: b.align[k] ? "md-" + b.align[k] : null}, inlines(content));
          return el("div", {class: "md-table"}, [el("table", {dir: direction(b)}, [
            el("thead", {}, [el("tr", {}, b.head.map((c, k) => cell("th", c, k)))]),
            el("tbody", {}, b.rows.map((row) => el("tr", {}, row.map((c, k) => cell("td", c, k)))))])]);
        }
        default: return doc.createTextNode("");
      }
    };
    return el("div", {class: "md"}, tree.map((b) => {
      const node = block(b);
      if (options.mark && b.src && options.mark(b.src) && node.setAttribute) node.setAttribute("class", `${node.getAttribute("class") || ""} md-diff`.trim());
      return node;
    }));
  }

  root.Markdown = {
    parse,
    toDom,
    figure: FIG.figure,
    render: (text, opts) => toDom(parse(text), (opts && opts.document) || root.document, opts),
    // The top-level blocks of a text, each as one line without spacing (the compare view's paragraphs).
    blocks: (text) => parse(text).map((b) => b.src).filter(Boolean),
  };
})(typeof window !== "undefined" ? window : globalThis);
