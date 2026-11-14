// A small Markdown renderer for the results of a run (the reader, the compare view): headings, paragraphs, bold,
// italic, strikethrough, lists, numbered lists, block quotes, code, GFM pipe tables, links and horizontal rules.
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
    const block = (b) => {
      switch (b.type) {
        case "heading": return el("h" + b.level, {dir: "auto"}, inlines(b.inlines));
        case "paragraph": return el("p", {dir: "auto"}, inlines(b.inlines));
        case "hr": return el("hr");
        case "code": return el("pre", {dir: "ltr", class: "md-code"}, [el("code", {"data-lang": b.lang || null}, [doc.createTextNode(b.text)])]);
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
    render: (text, opts) => toDom(parse(text), (opts && opts.document) || root.document, opts),
    // The top-level blocks of a text, each as one line without spacing (the compare view's paragraphs).
    blocks: (text) => parse(text).map((b) => b.src).filter(Boolean),
  };
})(typeof window !== "undefined" ? window : globalThis);
