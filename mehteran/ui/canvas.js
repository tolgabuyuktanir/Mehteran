// The workflow canvas: nodes as boxes with one handle per output port, connections as curves, pan and zoom.
// Used by the editor (editable) and by the run monitor (read-only, with node statuses). No framework: the boxes
// are elements in a "world" layer that is moved and scaled with a CSS transform; the curves are one SVG in it.
//
// view = {nodes: [{id, type, title, sub, glyph, ports: [port], x, y, problem, status}],
//         edges: [{from, port, to, index}]}       port "" = the connection takes the whole node (no port)
// opts = {editable, onSelect(sel), onMove(id, x, y, final), onConnect(from, port, to), labels: {status, port, ...}, minFit}
// sel  = {kind: "node", id} | {kind: "edge", index} | null
"use strict";

const NODE_W = 228, HEAD_H = 58, PORT_H = 24, PORT_PAD = 10, MIN_FIT = 0.75;
const SVG_NS = "http://www.w3.org/2000/svg";
let canvasCount = 0;

const nodeHeight = (ports) => HEAD_H + Math.max(ports.length, 1) * PORT_H + PORT_PAD;

function svgNode(tag, attrs, parent) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
}

class GraphCanvas {
  constructor(opts) {
    this.opts = opts || {};
    this.view = {nodes: [], edges: []};
    this.sel = null;
    this.t = {x: 40, y: 40, k: 1};
    this.marker = "gc-arrow-" + (++canvasCount);
    this.el = document.createElement("div");
    this.el.className = "gcanvas" + (this.opts.editable ? " editable" : "");
    this.el.tabIndex = -1;
    this.world = document.createElement("div");
    this.world.className = "gworld";
    this.svg = svgNode("svg", {class: "gedges", width: 1, height: 1, "aria-hidden": "true"});
    const marker = svgNode("marker", {id: this.marker, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7,
      orient: "auto-start-reverse"}, svgNode("defs", {}, this.svg));
    svgNode("path", {d: "M0,0 L10,5 L0,10 z", class: "garrow"}, marker);
    this.edgeLayer = svgNode("g", {}, this.svg);
    this.world.appendChild(this.svg);
    this.nodeLayer = document.createElement("div");
    this.world.appendChild(this.nodeLayer);
    this.el.appendChild(this.world);
    this.el.addEventListener("pointerdown", (e) => this.down(e));
    this.el.addEventListener("wheel", (e) => this.wheel(e), {passive: false});
    this.el.addEventListener("keydown", (e) => this.key(e));
    // Focusing a box (Tab) would scroll this clipped element and shift the drawing: the view moves only by pan.
    this.el.addEventListener("scroll", () => { this.el.scrollLeft = 0; this.el.scrollTop = 0; });
    this.apply();
  }

  // --- geometry -----------------------------------------------------------------------------------
  rect(n) { return {x: n.x, y: n.y, w: NODE_W, h: nodeHeight(n.ports)}; }
  byId(id) { return this.view.nodes.find((n) => n.id === id); }
  outPoint(n, port) {
    const i = n.ports.indexOf(port);
    return {x: n.x + NODE_W, y: i < 0 ? n.y + HEAD_H / 2 : n.y + HEAD_H + i * PORT_H + PORT_H / 2};
  }
  inPoint(n) { return {x: n.x, y: n.y + HEAD_H / 2}; }

  // A curve from a to b that avoids the boxes in between where it can: the plain curve first; if that crosses a
  // box, a curve through a point above or below the boxes it crosses; a connection that goes back to the left
  // makes a loop under both boxes.
  route(a, b, skip) {
    const others = this.view.nodes.filter((n) => !skip.includes(n.id)).map((n) => this.rect(n));
    const cubic = (p, c1, c2, q) => (t) => {
      const u = 1 - t;
      return {x: u * u * u * p.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * q.x,
              y: u * u * u * p.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t * t * t * q.y};
    };
    const hits = (fns) => {
      const hit = new Set();
      for (const f of fns) for (let i = 1; i < 24; i++) {
        const p = f(i / 24);
        others.forEach((r, k) => { if (p.x > r.x - 6 && p.x < r.x + r.w + 6 && p.y > r.y - 6 && p.y < r.y + r.h + 6) hit.add(k); });
      }
      return [...hit].map((k) => others[k]);
    };
    if (b.x < a.x + 24) {
      // Backwards (or nearly): out to the right, along a channel, into the input from the left. The channel runs
      // between the two boxes when one is above the other, else under both.
      const [ra, rb] = skip.map((id) => this.rect(this.byId(id)));
      const yc = rb.y > ra.y + ra.h + 16 ? (ra.y + ra.h + rb.y) / 2 : ra.y > rb.y + rb.h + 16 ? (rb.y + rb.h + ra.y) / 2
        : Math.max(ra.y + ra.h, rb.y + rb.h) + 34;
      const r = Math.min(24, Math.abs(yc - a.y) / 2, Math.abs(yc - b.y) / 2);
      const ox = a.x + 26, ix = b.x - 26;
      return `M${a.x},${a.y} L${ox - r},${a.y} Q${ox},${a.y} ${ox},${a.y + Math.sign(yc - a.y) * r} L${ox},${yc - Math.sign(yc - a.y) * r} ` +
        `Q${ox},${yc} ${ox - r},${yc} L${ix + r},${yc} Q${ix},${yc} ${ix},${yc + Math.sign(b.y - yc) * r} ` +
        `L${ix},${b.y - Math.sign(b.y - yc) * r} Q${ix},${b.y} ${ix + r},${b.y} L${b.x},${b.y}`;
    }
    const dx = Math.max(40, (b.x - a.x) / 2);
    const plain = cubic(a, {x: a.x + dx, y: a.y}, {x: b.x - dx, y: b.y}, b);
    const crossed = hits([plain]);
    if (!crossed.length) return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
    // The plain curve crosses a box: an orthogonal route with rounded corners. It leaves the source into the gap
    // after its column, runs along a free horizontal lane (above, below or between the boxes it would cross) and
    // goes down or up into the target in the gap before its column. The lane with the fewest crossed boxes wins,
    // then the shortest.
    const ox = a.x + 18, ix = b.x - 18;
    const span = others.filter((r) => r.x < ix && r.x + r.w > ox);
    const lanes = new Set([a.y, b.y]);
    for (const r of span) { lanes.add(r.y - 20); lanes.add(r.y + r.h + 20); }
    const crosses = (yc) => {
      let n = 0;
      for (const r of others) {
        const pad = 6;
        const box = {x0: r.x - pad, x1: r.x + r.w + pad, y0: r.y - pad, y1: r.y + r.h + pad};
        const hSeg = (x0, x1, y) => y > box.y0 && y < box.y1 && Math.max(x0, box.x0) < Math.min(x1, box.x1);
        const vSeg = (x, y0, y1) => x > box.x0 && x < box.x1 && Math.max(Math.min(y0, y1), box.y0) < Math.min(Math.max(y0, y1), box.y1);
        if (hSeg(a.x, ox, a.y) || vSeg(ox, a.y, yc) || hSeg(ox, ix, yc) || vSeg(ix, yc, b.y) || hSeg(ix, b.x, b.y)) n++;
      }
      return n;
    };
    const best = [...lanes].map((yc) => ({yc, n: crosses(yc), cost: Math.abs(yc - a.y) + Math.abs(yc - b.y)}))
      .sort((p, q) => p.n - q.n || p.cost - q.cost)[0];
    const yc = best.yc;
    const corner = (x, y0, y1) => Math.min(16, Math.abs(y1 - y0) / 2);
    const r1 = corner(ox, a.y, yc), r2 = corner(ix, yc, b.y);
    const s1 = Math.sign(yc - a.y), s2 = Math.sign(b.y - yc);
    return `M${a.x},${a.y} L${ox - r1},${a.y} Q${ox},${a.y} ${ox},${a.y + s1 * r1} L${ox},${yc - s1 * r1} Q${ox},${yc} ${ox + r1},${yc} ` +
      `L${ix - r2},${yc} Q${ix},${yc} ${ix},${yc + s2 * r2} L${ix},${b.y - s2 * r2} Q${ix},${b.y} ${ix + r2},${b.y} L${b.x},${b.y}`;
  }

  // --- drawing ------------------------------------------------------------------------------------
  setView(view, sel) {
    this.view = view;
    if (sel !== undefined) this.sel = sel;
    this.render();
  }

  render() {
    const L = this.opts.labels || {};
    const focused = document.activeElement && this.nodeLayer.contains(document.activeElement) ? document.activeElement.dataset.id : null;
    // The boxes are drawn anew at each refresh of a run: the endless animations (a working step's pulse) keep their
    // phase through --phase, and a status change since the last drawing is marked "fresh" (its one-time animation).
    this.el.style.setProperty("--phase", `-${Date.now() % 2400}ms`);
    const before = this.lastStatus || {};
    this.lastStatus = {};
    this.nodeLayer.replaceChildren(...this.view.nodes.map((n) => {
      const selected = this.sel && this.sel.kind === "node" && this.sel.id === n.id;
      const box = document.createElement("div");
      const fresh = n.status && before[n.id] !== undefined && before[n.id] !== n.status;
      this.lastStatus[n.id] = n.status;
      box.className = `gnode kind-${n.type.replace(/\W/g, "-")}` + (selected ? " selected" : "") + (n.problem ? " invalid" : "")
        + (n.status ? " s-" + n.status : "") + (fresh ? " fresh" : "");
      box.dataset.id = n.id;
      box.tabIndex = 0;
      box.setAttribute("role", "button");
      box.setAttribute("aria-pressed", String(Boolean(selected)));
      box.setAttribute("aria-label", `${n.title} · ${n.sub}` + (n.status ? ` · ${L.status ? L.status(n.status) : n.status}` : "")
        + (n.problem ? ` · ${n.problem}` : ""));
      box.style.transform = `translate(${n.x}px, ${n.y}px)`;
      box.style.height = nodeHeight(n.ports) + "px";
      const head = document.createElement("div");
      head.className = "gnode-head";
      const glyph = document.createElement("span");
      glyph.className = "node-glyph";
      glyph.textContent = n.glyph || "•";
      const titles = document.createElement("div");
      titles.className = "gnode-titles";
      const b = document.createElement("b");
      b.textContent = n.title;
      const sub = document.createElement("span");
      sub.className = "gnode-sub";
      sub.textContent = n.sub;
      titles.append(b, sub);
      head.append(glyph, titles);
      if (n.problem) {
        const warn = document.createElement("span");
        warn.className = "node-warn bad";
        warn.textContent = "!";
        warn.title = n.problem;
        head.appendChild(warn);
      }
      if (n.status) {
        const dot = document.createElement("span");
        dot.className = "gstatus";
        dot.title = L.status ? L.status(n.status) : n.status;
        head.appendChild(dot);
      }
      box.appendChild(head);
      const input = document.createElement("span");
      input.className = "gport-in";
      input.title = L.input ? L.input(n) : "";
      box.appendChild(input);
      n.ports.forEach((port) => {
        const row = document.createElement("div");
        row.className = "gport-row port-" + port.replace(/\W/g, "-");
        const name = document.createElement("span");
        name.textContent = L.port ? L.port(n.type, port) : port;
        const handle = document.createElement("span");
        handle.className = "gport-out";
        handle.dataset.port = port;
        handle.title = L.connect ? L.connect(n, port) : `${n.id}.${port}`;
        row.append(name, handle);
        box.appendChild(row);
      });
      return box;
    }));
    this.renderEdges();
    if (focused) this.nodeLayer.querySelector(`[data-id="${CSS.escape(focused)}"]`)?.focus({preventScroll: true});
  }

  renderEdges() {
    const paths = [];
    for (const e of this.view.edges) {
      const a = this.byId(e.from), b = this.byId(e.to);
      if (!a || !b) continue;
      const d = this.route(this.outPoint(a, e.port), this.inPoint(b), [a.id, b.id]);
      const selected = this.sel && this.sel.kind === "edge" && this.sel.index === e.index;
      const done = a.status === "succeeded";
      const feeding = done && b.status === "running";  // its text flows into the step that works now
      const g = svgNode("g", {class: "gedge" + (selected ? " selected" : "") + (done ? " done" : "") + (feeding ? " feeding" : "")
        + (e.problem ? " invalid" : "")});
      svgNode("path", {d, class: "gedge-line", "marker-end": `url(#${this.marker})`}, g);
      const hit = svgNode("path", {d, class: "gedge-hit"}, g);
      hit.dataset.index = e.index;
      svgNode("title", {}, hit).textContent = `${e.from}${e.port ? "." + e.port : ""} → ${e.to}`;
      paths.push(g);
    }
    if (this.temp) paths.push(this.temp);
    this.edgeLayer.replaceChildren(...paths);
  }

  // --- view: pan and zoom -------------------------------------------------------------------------
  apply() {
    this.world.style.transform = `translate(${this.t.x}px, ${this.t.y}px) scale(${this.t.k})`;
    this.el.style.setProperty("--zoom", this.t.k);
    if (this.opts.onView) this.opts.onView(this.t);
  }

  toWorld(cx, cy) {
    const r = this.el.getBoundingClientRect();
    return {x: (cx - r.left - this.t.x) / this.t.k, y: (cy - r.top - this.t.y) / this.t.k};
  }

  center() {
    const r = this.el.getBoundingClientRect();
    return this.toWorld(r.left + r.width / 2, r.top + r.height / 2);
  }

  zoomAt(k, cx, cy) {
    const r = this.el.getBoundingClientRect();
    if (cx === undefined) { cx = r.left + r.width / 2; cy = r.top + r.height / 2; }
    k = Math.min(2, Math.max(0.3, k));
    const p = this.toWorld(cx, cy);
    this.t = {k, x: cx - r.left - p.x * k, y: cy - r.top - p.y * k};
    this.apply();
  }

  fit() {
    const r = this.el.getBoundingClientRect();
    if (!this.view.nodes.length || !r.width) { this.t = {x: 40, y: 40, k: 1}; return this.apply(); }
    const rects = this.view.nodes.map((n) => this.rect(n));
    const x0 = Math.min(...rects.map((q) => q.x)), y0 = Math.min(...rects.map((q) => q.y));
    const x1 = Math.max(...rects.map((q) => q.x + q.w)), y1 = Math.max(...rects.map((q) => q.y + q.h)) + 40;
    // Never smaller than MIN_FIT: the text must stay readable. A flow that does not fit then starts at its first
    // column (and at the top), and the rest is a pan away.
    const k = Math.min(1.1, Math.max(this.opts.minFit || MIN_FIT, Math.min((r.width - 48) / (x1 - x0), (r.height - 48) / (y1 - y0))));
    const fitsX = (x1 - x0) * k <= r.width - 48, fitsY = (y1 - y0) * k <= r.height - 24;
    this.t = {k, x: fitsX ? (r.width - (x1 - x0) * k) / 2 - x0 * k : 24 - x0 * k,
              y: fitsY ? (r.height - (y1 - y0 - 40) * k) / 2 - y0 * k : 24 - y0 * k};
    this.apply();
  }

  wheel(e) {
    e.preventDefault();
    this.zoomAt(this.t.k * Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015)), e.clientX, e.clientY);
  }

  // --- pointer: select, move, connect, pan ---------------------------------------------------------
  down(e) {
    if (e.button !== 0) return;
    const handle = e.target.closest(".gport-out");
    const box = e.target.closest(".gnode");
    const hit = e.target.closest(".gedge-hit");
    const start = {x: e.clientX, y: e.clientY};
    let moved = false, onMove, onUp;
    if (handle && box && this.opts.editable) {
      e.preventDefault();
      const n = this.byId(box.dataset.id), port = handle.dataset.port;
      const a = this.outPoint(n, port);
      this.temp = svgNode("path", {class: "gedge-temp"});
      this.el.classList.add("connecting");
      onMove = (ev) => {
        const p = this.toWorld(ev.clientX, ev.clientY);
        this.temp.setAttribute("d", `M${a.x},${a.y} C${a.x + 60},${a.y} ${p.x - 60},${p.y} ${p.x},${p.y}`);
        this.edgeLayer.appendChild(this.temp);
        this.el.querySelectorAll(".gnode.drop").forEach((x) => x.classList.remove("drop"));
        const over = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".gnode");
        if (over && over.dataset.id !== n.id) over.classList.add("drop");
      };
      onUp = (ev) => {
        this.temp.remove();
        this.temp = null;
        this.el.classList.remove("connecting");
        const over = document.elementFromPoint(ev.clientX, ev.clientY)?.closest(".gnode");
        this.el.querySelectorAll(".gnode.drop").forEach((x) => x.classList.remove("drop"));
        if (over && over.dataset.id !== n.id && this.el.contains(over)) this.opts.onConnect(n.id, port, over.dataset.id);
      };
    } else if (box) {
      e.preventDefault();  // no text selection while dragging; the box takes the focus itself
      box.focus({preventScroll: true});
      const n = this.byId(box.dataset.id);
      const origin = {x: n.x, y: n.y};
      if (!(this.sel && this.sel.kind === "node" && this.sel.id === n.id)) this.select({kind: "node", id: n.id});
      if (!this.opts.editable) return;
      onMove = (ev) => {
        const dx = (ev.clientX - start.x) / this.t.k, dy = (ev.clientY - start.y) / this.t.k;
        if (!moved && Math.hypot(dx, dy) < 3) return;
        if (!moved) this.el.classList.add("moving");
        moved = true;
        const cur = this.byId(n.id) || n;  // the view may have been drawn anew (the click selected the box)
        cur.x = Math.round(origin.x + dx);
        cur.y = Math.round(origin.y + dy);
        this.nodeLayer.querySelector(`[data-id="${CSS.escape(n.id)}"]`).style.transform = `translate(${cur.x}px, ${cur.y}px)`;
        this.renderEdges();  // the connections follow the box while it moves
        this.opts.onMove(n.id, cur.x, cur.y, false);
      };
      onUp = () => {
        this.el.classList.remove("moving");
        const cur = this.byId(n.id) || n;
        if (moved) this.opts.onMove(n.id, cur.x, cur.y, true);
      };
    } else if (hit) {
      this.select({kind: "edge", index: Number(hit.dataset.index)});
      return;
    } else {
      const origin = {...this.t};
      this.el.classList.add("panning");
      onMove = (ev) => {
        if (!moved && Math.hypot(ev.clientX - start.x, ev.clientY - start.y) < 3) return;
        moved = true;
        this.t = {...origin, x: origin.x + ev.clientX - start.x, y: origin.y + ev.clientY - start.y};
        this.apply();
      };
      onUp = () => { this.el.classList.remove("panning"); if (!moved) this.select(null); };
    }
    const up = (ev) => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      onUp(ev);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  }

  select(sel) {
    this.sel = sel;
    if (this.opts.onSelect) this.opts.onSelect(sel);
    else this.render();
  }

  key(e) {
    const box = e.target.closest && e.target.closest(".gnode");
    if (!box) return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); this.select({kind: "node", id: box.dataset.id}); return; }
    const step = e.shiftKey ? 40 : 10;
    const move = {ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step]}[e.key];
    if (!move || !this.opts.editable) return;
    e.preventDefault();
    const n = this.byId(box.dataset.id);
    this.opts.onMove(n.id, n.x + move[0], n.y + move[1], true);
  }
}

// The automatic layered layout: a column per step of the longest path from a start node; inside a column the
// boxes follow the average height of the boxes they come from (fewer crossings).
function autoLayout(nodes, edges, keep) {
  const ids = nodes.map((n) => n.id);
  const ups = Object.fromEntries(ids.map((id) => [id, new Set()]));
  for (const e of edges) if (ups[e.to] && ids.includes(e.from) && e.from !== e.to) ups[e.to].add(e.from);
  const layer = {};
  const visit = (id, seen) => {
    if (layer[id] !== undefined) return layer[id];
    if (seen.has(id)) return 0;  // a cycle: the check reports it; the drawing just stops here
    seen.add(id);
    layer[id] = Math.max(-1, ...[...ups[id]].map((u) => visit(u, seen))) + 1;
    return layer[id];
  };
  ids.forEach((id) => visit(id, new Set()));
  const columns = [];
  for (const n of nodes) (columns[layer[n.id]] = columns[layer[n.id]] || []).push(n);
  const pos = {};
  const heights = columns.map((col) => col.reduce((s, n) => s + nodeHeight(n.ports) + 36, -36));
  const tallest = Math.max(0, ...heights);
  columns.forEach((col, c) => {
    if (!col) return;
    col.sort((a, b) => {
      const avg = (n) => { const u = [...ups[n.id]].filter((x) => pos[x]); return u.length ? u.reduce((s, x) => s + pos[x].y, 0) / u.length : 0; };
      return avg(a) - avg(b);
    });
    let y = (tallest - heights[c]) / 2;
    for (const n of col) {
      pos[n.id] = keep && keep[n.id] ? keep[n.id] : {x: c * (NODE_W + 96), y: Math.round(y)};
      y += nodeHeight(n.ports) + 36;
    }
  });
  return pos;
}
