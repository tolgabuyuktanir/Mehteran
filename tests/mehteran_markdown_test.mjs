// Tests of the results' Markdown renderer (mehteran/ui/markdown.js), run with Node.js by tests/test_mehteran_results.py.
// The renderer is loaded in a fresh context; a small stand-in document records the elements it builds and refuses
// innerHTML. Prints "ok <count>" and exits 0, or names the first failure and exits 1.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../mehteran/ui/markdown.js", import.meta.url), "utf8");
const context = {};
vm.runInNewContext(source, context);
const Markdown = context.Markdown;

const doc = {
  createElement(tag) {
    const node = {tag, attrs: {}, children: [],
      setAttribute(key, value) { this.attrs[key] = String(value); },
      getAttribute(key) { return key in this.attrs ? this.attrs[key] : null; },
      appendChild(child) { this.children.push(child); return child; }};
    Object.defineProperty(node, "innerHTML", {set() { throw new Error("innerHTML used"); }});
    return node;
  },
  createElementNS(ns, tag) { const node = this.createElement(tag); node.ns = ns; return node; },
  createTextNode(text) { return {text: String(text)}; },
};

// The elements as a short HTML-like string (text escaped), for readable assertions.
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function show(node) {
  if ("text" in node) return esc(node.text);
  const attrs = Object.entries(node.attrs).map(([k, v]) => ` ${k}="${v}"`).join("");
  return `<${node.tag}${attrs}>${node.children.map(show).join("")}</${node.tag}>`;
}
const html = (text, opts) => show(Markdown.render(text, {document: doc, ...opts})).replace(/^<div class="md">|<\/div>$/g, "");

let count = 0;
function test(name, fn) {
  try { fn(); count++; } catch (err) { console.error(`FAIL ${name}\n${err.message}`); process.exit(1); }
}

test("headings and paragraphs", () => {
  assert.equal(html("# Title\n\nSome text."), '<h1 dir="auto">Title</h1><p dir="auto">Some text.</p>');
  assert.equal(html("### Three ###"), '<h3 dir="auto">Three</h3>');
  assert.equal(html("Setext\n==="), '<h1 dir="auto">Setext</h1>');
  assert.equal(html("Second\n---"), '<h2 dir="auto">Second</h2>');
  assert.equal(html("#no heading"), '<p dir="auto">#no heading</p>');
});

test("line breaks inside a paragraph are kept", () => {
  assert.equal(html("one\ntwo"), '<p dir="auto">one<br></br>two</p>');
});

test("bold, italic, strikethrough, code", () => {
  assert.equal(html("**b** *i* ***bi*** __u__ _e_ ~~d~~ `c*d`"),
    '<p dir="auto"><strong>b</strong> <em>i</em> <strong><em>bi</em></strong> <strong>u</strong> <em>e</em> <del>d</del> <code>c*d</code></p>');
  assert.equal(html("*a **b** c*"), '<p dir="auto"><em>a <strong>b</strong> c</em></p>');
  assert.equal(html("snake_case_name and 2 * 3 * 4"), '<p dir="auto">snake_case_name and 2 * 3 * 4</p>');
  assert.equal(html("\\*not em\\*"), '<p dir="auto">*not em*</p>');
});

test("lists", () => {
  assert.equal(html("- a\n- b\n  continued\n- c"), '<ul dir="ltr"><li dir="auto">a</li><li dir="auto">b<br></br>continued</li><li dir="auto">c</li></ul>');
  assert.equal(html("3. three\n4. four"), '<ol dir="ltr" start="3"><li dir="auto">three</li><li dir="auto">four</li></ol>');
  assert.equal(html("1. one\n   - inner\n2. two"),
    '<ol dir="ltr"><li dir="auto"><p dir="auto">one</p><ul dir="ltr"><li dir="auto">inner</li></ul></li><li dir="auto">two</li></ol>');
  assert.equal(html("- a\n\n- b"), '<ul dir="ltr"><li dir="auto">a</li><li dir="auto">b</li></ul>');
  assert.equal(html("Year\n2024. was good"), '<p dir="auto">Year<br></br>2024. was good</p>', "only 1. interrupts a paragraph");
});

test("block quotes and code blocks", () => {
  assert.equal(html("> quoted\n> **more**"), '<blockquote dir="ltr"><p dir="auto">quoted<br></br><strong>more</strong></p></blockquote>');
  assert.equal(html("```js\nlet a = '<b>';\n\n*x*\n```\nafter"),
    '<pre dir="ltr" class="md-code"><code data-lang="js">let a = \'&lt;b&gt;\';\n\n*x*</code></pre><p dir="auto">after</p>');
  assert.equal(html("~~~\nunclosed"), '<pre dir="ltr" class="md-code"><code>unclosed</code></pre>');
});

test("pipe tables", () => {
  assert.equal(html("| A | B |\n|:--|--:|\n| 1 | **2** |\n| x \\| y |"),
    '<div class="md-table"><table dir="ltr"><thead><tr><th dir="auto" class="md-left">A</th><th dir="auto" class="md-right">B</th></tr></thead>'
    + '<tbody><tr><td dir="auto" class="md-left">1</td><td dir="auto" class="md-right"><strong>2</strong></td></tr>'
    + '<tr><td dir="auto" class="md-left">x | y</td><td dir="auto" class="md-right"></td></tr></tbody></table></div>');
  assert.equal(html("a | b\n--|--\n1 | 2").startsWith('<div class="md-table">'), true, "without outer pipes");
  assert.equal(html("a | b\n---"), '<h2 dir="auto">a | b</h2>', "no delimiter row with the same cells: not a table");
});

test("links: only http and https, a new tab without opener and referrer", () => {
  const attrs = 'target="_blank" rel="noopener noreferrer"';
  assert.equal(html("[site](https://example.org/a_(b))"), `<p dir="auto"><a href="https://example.org/a_(b)" ${attrs}>site</a></p>`);
  assert.equal(html("see https://example.org/x."), `<p dir="auto">see <a href="https://example.org/x" ${attrs}>https://example.org/x</a>.</p>`);
  assert.equal(html("<http://a.test/>"), `<p dir="auto"><a href="http://a.test/" ${attrs}>http://a.test/</a></p>`);
  assert.equal(html("[x](javascript:alert(1)) [y](data:text/html,hi) [z](/local) [w](file:///etc/passwd)"),
    '<p dir="auto">x y z w</p>', "other addresses keep only their text");
  assert.equal(html("![alt](https://img.test/a.png)"), `<p dir="auto"><a href="https://img.test/a.png" ${attrs}>alt</a></p>`, "no images");
});

test("raw HTML stays text", () => {
  assert.equal(html('<script>alert(1)</script> <img src=x onerror="y">'),
    '<p dir="auto">&lt;script&gt;alert(1)&lt;/script&gt; &lt;img src=x onerror="y"&gt;</p>');
});

test("horizontal rules", () => {
  assert.equal(html("a\n\n---\n\n* * *\n\nb"), '<p dir="auto">a</p><hr></hr><hr></hr><p dir="auto">b</p>');
});

test("right-to-left text gets dir=auto on every block", () => {
  const out = html("# عنوان\n\nهذا نص **عربي**.\n\n- بند\n\n| عمود | ب |\n|---|---|\n| ١ | ٢ |");
  assert.match(out, /<h1 dir="auto">عنوان<\/h1>/);
  assert.match(out, /<p dir="auto">هذا نص <strong>عربي<\/strong>.<\/p>/);
  assert.match(out, /<ul dir="rtl"><li dir="auto">بند<\/li><\/ul>/);
  assert.match(out, /<table dir="rtl">/);
});

test("a list, a quote or a table takes the direction of its first letter", () => {
  assert.match(html("> ملاحظة: English after"), /^<blockquote dir="rtl">/);
  assert.match(html("1. English first: ملاحظة"), /^<ol dir="ltr">/);
  assert.match(html("- `code` ١٢٣ نص"), /^<ul dir="rtl">/, "code and digits are skipped");
  assert.match(html("- 123"), /^<ul dir="auto">/, "no letter: the browser decides");
});

test("blocks and marks for the compare view", () => {
  assert.deepEqual([...Markdown.blocks("# T\n\nOne\ntwo.\n\n- a\n- b")], ["# T", "One two.", "- a - b"]);
  const other = new Set(Markdown.blocks("# T\n\nChanged."));
  assert.equal(html("# T\n\nOne.", {mark: (src) => !other.has(src)}), '<h1 dir="auto">T</h1><p dir="auto" class="md-diff">One.</p>');
});

test("empty and odd input", () => {
  assert.equal(html(""), "");
  assert.equal(html(null), "");
  assert.equal(html("**unclosed and `tick"), '<p dir="auto">**unclosed and `tick</p>');
  assert.equal(html("[a](b"), '<p dir="auto">[a](b</p>');
  assert.equal(html("a\r\nb"), '<p dir="auto">a<br></br>b</p>');
});

test("figures are drawn as SVG elements; an invalid one stays code", () => {
  const spec = {alt: "A <line>", caption: "Fig. 1", x: [0, 4], y: [0, 4], items: [{line: [[0, 0], [4, 4]]}, {text: "<b>", at: [1, 1]}]};
  const page = Markdown.render("```figure\n" + JSON.stringify(spec) + "\n```", {document: doc});
  const fig = page.children[0], svg = fig.children[0];
  assert.equal(fig.tag, "figure");
  assert.equal(svg.tag, "svg");
  assert.equal(svg.ns, "http://www.w3.org/2000/svg");
  assert.equal(svg.attrs.role, "img");
  assert.equal(svg.attrs["aria-label"], "A <line>");
  assert.equal("xmlns" in svg.attrs, false);
  assert.match(show(page), /<text class="fig-text"[^>]*>&lt;b&gt;<\/text>/);
  assert.match(show(page), /<figcaption dir="auto">Fig. 1<\/figcaption>/);
  assert.equal(html("```figure\n{\"alt\": \"a\"}\n```"), '<pre dir="ltr" class="md-code"><code data-lang="figure">{"alt": "a"}</code></pre>');
});

console.log(`ok ${count}`);
