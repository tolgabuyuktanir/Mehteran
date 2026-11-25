// The visual workflow editor (Workflow tab): palette, canvas, inspector, workflow panel and a YAML tab.
//
// The editor works on the workflow itself (the same mapping as the YAML file, plus the optional "layout" key) and
// never decides validity on its own: every change is sent to the server check (/api/editor/check), whose
// problems carry their place ("nodes.review.config.prompt"); the editor marks that node and field.
//
// Rules the editor keeps (see docs/mehteran.md):
// - References and connections: inserting {{nodes.a.x}} for a node that is not connected yet adds the
//   connection a.x -> this node. The editor never changes text the user wrote: deleting a connection (or a node)
//   leaves the references to it, says so, and the check marks them until they are reconnected or removed.
// - Saving: only a workflow without problems is saved (the same rule as the YAML editor and templates.save).
// - Built-in templates open as your own unsaved copy (a new id, based_on set as "Customize" does): everything can be
//   edited at once, the built-in file never changes, and the first Save creates the copy. An unchanged copy runs
//   the built-in itself.
// - Comments: the visual save writes the file anew; the file's header comment is kept, other comments would be
//   lost, so the user is asked once before such a save.
"use strict";

const Editor = (() => {
  const ed = {model: null, source: "", id: "", isNew: false, fresh: false, origin: null, readOnly: false, saved: "", storedYaml: null, history: [], future: [],
    sel: null, problems: [], valid: false, ports: {}, mode: "visual", yamlBase: "", lastField: null, checkSeq: 0, checkTimer: null,
    lastKey: "", lastTime: 0, canvas: null, modelsLoaded: false};
  const SHORT = {"document.extract": "extract", "ai.cli": "ai", "text.merge": "merge", "approval": "approval", "document.export": "export",
    "condition": "condition", "ai.map": "loop", "ai.agent": "agent", "share.x": "share"};
  const arr = (v) => (Array.isArray(v) ? v : []);
  const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : null);
  const nodes = () => arr(ed.model && ed.model.nodes).filter((n) => obj(n) && typeof n.id === "string");
  const nodeById = (id) => nodes().find((n) => n.id === id);
  const conns = () => arr(ed.model.connections).filter(obj);
  const splitFrom = (from) => { const s = String(from || ""); const i = s.indexOf("."); return i < 0 ? [s, ""] : [s.slice(0, i), s.slice(i + 1)]; };
  // The node types come from the server (GET /api/node-types): the palette, the ports and the inspector forms are
  // made from them, so a new node type needs no code here.
  const typeInfo = (type) => NODE_TYPES[type];
  const portsOf = (n) => (ed.ports[n.id] ? Object.keys(ed.ports[n.id]) : ((typeInfo(n.type) || {}).outputs || []).map((o) => o.name));
  const titleOf = (n) => L(n.label) || n.id;
  const isText = (el) => el && (el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && !["checkbox", "radio", "button"].includes(el.type)) || el.tagName === "SELECT");

  // --- loading -----------------------------------------------------------------------------------
  function init() {
    document.addEventListener("keydown", onKey);
    $("#new-form").addEventListener("submit", createNew);
    $("#new-cancel").addEventListener("click", () => { $("#new-dialog").close(); if (!ed.model) go("workflows"); });
    // The id follows the name until the user writes one under "Advanced".
    $("#new-name").addEventListener("input", () => { if (!$("#new-id").dataset.own) $("#new-id").value = freeId(slugOf($("#new-name").value)); });
    $("#new-id").addEventListener("input", () => { $("#new-id").dataset.own = $("#new-id").value.trim() ? "1" : ""; });
  }

  // "Haftalık İş Raporu" -> "haftalik-is-raporu": letters folded as the library search does (app.js: fold), anything
  // else a "-"; starts with a letter; at most 64 characters. A name without Latin letters gives "workflow".
  function slugOf(name) {
    const slug = fold(name).replace(/[^a-z0-9]+/g, "-").replace(/^[^a-z]+/, "").replace(/-+$/, "").slice(0, 56).replace(/-+$/, "");
    return slug || "workflow";
  }
  // The id with a number added while a workflow of the library has it.
  function freeId(id) {
    const taken = new Set(state.templates.map((t) => t.id));
    let out = id;
    for (let k = 2; taken.has(out); k++) out = `${id}-${k}`;
    return out;
  }

  async function open(parts) {
    if (parts[0] === "new") {
      if (ed.isNew && ed.model) return render();
      if (!state.templates.length) await loadTemplateList();
      if (ed.isNew && ed.model) return render();  // created meanwhile (two routes at start)
      if (!$("#new-dialog").open) {
        $("#new-id").value = "";
        $("#new-id").dataset.own = "";
        $("#new-name").value = "";
        $("#new-advanced").open = false;
        $("#new-problem").textContent = "";
        $("#new-dialog").showModal();
      }
      if (!ed.model) renderEmpty();
      return;
    }
    if (parts.length === 2) {
      if (ed.model && ed.source === parts[0] && ed.id === parts[1] && !ed.isNew) return render();
      if (ed.model && ed.origin && ed.origin.source === parts[0] && ed.origin.id === parts[1]) return render();
      return load(parts[0], parts[1]);
    }
    if (ed.model) return go(ed.origin ? `workflows/edit/${ed.origin.source}/${ed.origin.id}` : ed.isNew ? "workflows/new" : `workflows/edit/${ed.source}/${ed.id}`);
    renderEmpty();
  }

  async function load(source, id) {
    const tpl = await api("GET", `/api/templates/${source}/${id}`);
    Object.assign(ed, {source, id, isNew: false, fresh: false, origin: null, readOnly: false, storedYaml: tpl.yaml, sel: null, draft: Boolean(tpl.draft),
      mode: "visual", history: [], future: [], problems: [], warnings: [], ports: {}, canvas: null, wfTab: "general", draftBy: "", palOpen: false, tries: {}});
    ed.model = obj(tpl.model) || {schema_version: 1, id, name: id, nodes: []};
    if (!obj(tpl.model)) { ed.mode = "yaml"; ed.yamlBase = tpl.yaml; }
    if (source === "builtin") {
      // Copy on edit: the editor works on a copy with a free id; the first Save creates it as your template.
      if (!state.templates.length) await loadTemplateList();
      const taken = new Set(state.templates.map((t) => t.id));
      let copyId = `${id}-copy`;
      for (let k = 2; taken.has(copyId); k++) copyId = `${id}-copy-${k}`;
      const version = ed.model.version;
      ed.model = {...ed.model, id: copyId, based_on: `builtin:${id}` + (version != null && version !== "" ? `@${version}` : "")};
      Object.assign(ed, {source: "user", id: copyId, isNew: true, origin: {source, id, name: tpl.name}, storedYaml: null, draft: false});
      if (ed.mode === "yaml") ed.yamlBase = tpl.yaml.replace(/^id:.*$/m, `id: ${copyId}`);
    }
    ensureLayout();
    ed.saved = JSON.stringify(ed.model);
    ed.history = [ed.saved];
    render();
    check();
    loadModels();
  }

  function createNew(e) {
    e.preventDefault();
    const name = $("#new-name").value.trim();
    if (!name) { $("#new-problem").textContent = S("new_name_needed"); return; }
    // The id: the one written under "Advanced" (checked as written), else made from the name (always free).
    const own = $("#new-id").dataset.own ? $("#new-id").value.trim() : "";
    const id = own || freeId(slugOf(name));
    const problem = !/^[a-z][a-z0-9_-]{0,63}$/.test(id) ? S("new_id_rule") : state.templates.some((t) => t.id === id) ? S("template_exists_ui", {id}) : "";
    if (problem) { $("#new-advanced").open = true; $("#new-problem").textContent = problem; $("#new-id").focus(); return; }
    $("#new-dialog").close();
    startNew({schema_version: 1, id, name: {tr: name, en: name}, nodes: [], connections: [], layout: {}});
  }

  // An unsaved workflow of the user in the editor: an empty one ("New workflow"), or a draft that a model wrote
  // (draftBy: the model's name; yaml and problems: a draft that did not pass the check opens on the YAML tab).
  function startNew(model, opts = {}) {
    const id = String(model.id || "");
    Object.assign(ed, {source: "user", id, isNew: true, fresh: true, origin: null, draft: false, readOnly: false, storedYaml: null, sel: null, mode: "visual", problems: [], warnings: [], wfTab: "general",
      ports: {}, canvas: null, model, draftBy: opts.draftBy || "", palOpen: true, tries: {}, valid: false});
    if (nodes().length) ensureLayout(true);
    if (opts.yaml != null) { ed.mode = "yaml"; ed.yamlBase = opts.yaml; }
    ed.saved = "";
    ed.history = [JSON.stringify(ed.model)];
    ed.future = [];
    if (location.hash !== "#workflows/new") history.replaceState(null, "", "#workflows/new");
    state.hash = "workflows/new";
    render();
    if (opts.yaml != null && opts.problems) {
      fill($("#yaml-problems"), h("div", {class: "notice bad", role: "alert"}, h("b", {}, S("draft_invalid", {model: opts.draftBy || ""})),
        h("ul", {class: "failures"}, opts.problems.map((p) => h("li", {}, p)))));
    }
    check();
    loadModels();
  }

  // The model lists of the tools; the editor works before they arrive.
  async function loadModels() {
    if (ed.modelsLoaded) return;
    ed.modelsLoaded = true;
    await Promise.all((INFO.providers || []).filter((p) => p.tool).map(async (p) => {
      try {
        const res = await api("GET", `/api/tools/${encodeURIComponent(p.tool)}/models`);
        p.models = [...new Set([...res.models, ...p.models])];
      } catch { /* keeps the configured list */ }
    }));
    if (ed.model && isEditorHash(state.hash)) { renderPalette(); renderInspector(); }
  }

  // Positions for nodes that have none: the automatic layered layout (all of them when there is no layout).
  function ensureLayout(force) {
    const m = ed.model;
    const list = nodes();
    const layout = obj(m.layout) || {};
    const valid = (p) => obj(p) && Number.isInteger(p.x) && Number.isInteger(p.y);
    if (!force && list.every((n) => valid(layout[n.id]))) return;
    const view = list.map((n) => ({id: n.id, ports: portsOf(n)}));
    const edges = conns().map((c) => ({from: splitFrom(c.from)[0], to: c.to}));
    const keep = force ? null : Object.fromEntries(list.filter((n) => valid(layout[n.id])).map((n) => [n.id, layout[n.id]]));
    const pos = autoLayout(view, edges, keep && Object.keys(keep).length ? keep : null);
    m.layout = Object.fromEntries(list.map((n) => [n.id, {x: Math.round(pos[n.id].x), y: Math.round(pos[n.id].y)}]));
  }

  const dirty = () => Boolean(ed.model && !ed.readOnly && (ed.fresh || JSON.stringify(ed.model) !== ed.saved
    || (ed.mode === "yaml" && $("#yaml-text") && $("#yaml-text").value !== ed.yamlBase)));

  // --- history -------------------------------------------------------------------------------------
  // Every change is one step; typing in one field within 1.5 s is one step.
  function changed(opts = {}) {
    const snap = JSON.stringify(ed.model);
    if (snap !== ed.history[ed.history.length - 1]) {
      const now = Date.now();
      if (opts.coalesce && opts.coalesce === ed.lastKey && now - ed.lastTime < 1500 && ed.history.length > 1) ed.history[ed.history.length - 1] = snap;
      else ed.history.push(snap);
      if (ed.history.length > 300) ed.history.shift();
      ed.lastKey = opts.coalesce || "";
      ed.lastTime = now;
      ed.future = [];
    }
    renderCanvas();
    if (!opts.keepInspector) renderInspector();
    renderStatus();
    scheduleCheck();
  }

  function undo() {
    if (ed.history.length < 2 || ed.readOnly) return;
    ed.future.push(ed.history.pop());
    restore();
  }

  function redo() {
    if (!ed.future.length || ed.readOnly) return;
    ed.history.push(ed.future.pop());
    restore();
  }

  function restore() {
    ed.model = JSON.parse(ed.history[ed.history.length - 1]);
    ed.lastKey = "";
    if (ed.sel && ed.sel.kind === "node" && !nodeById(ed.sel.id)) ed.sel = null;
    if (ed.sel && ed.sel.kind === "edge" && !conns()[ed.sel.index]) ed.sel = null;
    renderCanvas();
    renderInspector();
    renderStatus();
    scheduleCheck(0);
  }

  // --- the server check ----------------------------------------------------------------------------
  function scheduleCheck(delay = 350) {
    clearTimeout(ed.checkTimer);
    ed.checkTimer = setTimeout(check, delay);
  }

  async function check() {
    const seq = ++ed.checkSeq;
    let res;
    try { res = await api("POST", "/api/editor/check", {model: ed.model}); } catch (err) { toast(err.message, true); return; }
    if (seq !== ed.checkSeq) return;  // a newer check is on its way
    const portsChanged = JSON.stringify(res.ports) !== JSON.stringify(ed.ports);
    Object.assign(ed, {problems: res.problems, warnings: res.warnings || [], valid: res.valid, ports: res.ports});
    renderCanvas();
    if (portsChanged) renderInspectorChips();
    renderProblems();
    markFields();
    renderStatus();
  }

  const problemsAt = (prefix) => ed.problems.filter((p) => p.where === prefix || p.where.startsWith(prefix + ".") || p.where.startsWith(prefix + "["));
  function nodeOfProblem(where) {
    const m = /^(?:nodes|layout)\.([^.[\]]+)/.exec(where);
    return m && nodeById(m[1]) ? m[1] : null;
  }

  // --- rendering -----------------------------------------------------------------------------------
  function renderEmpty() {
    fill($("#workflow-body"), h("div", {class: "welcome"}, h("h2", {}, S("editor_empty_title")), h("p", {}, S("editor_empty_text")),
      h("div", {class: "row"}, h("button", {type: "button", class: "btn primary", onclick: () => go("workflows/new")}, S("new_workflow")),
        h("button", {type: "button", class: "btn", onclick: () => go("workflows")}, S("go_workflows")))));
  }

  // The palette is folded to a narrow strip of step icons; the choice is kept (folded by default on narrow windows).
  // Below 1440 px the palette starts as an icon rail, so the canvas keeps its room next to the inspector; opening or
  // folding it by hand holds for this session.
  const paletteChoice = () => { try { return sessionStorage.getItem("mehteran.palette"); } catch { return null; } };
  // A new workflow starts with the palette open (its steps with their names), whatever the width.
  const paletteFolded = () => { const v = paletteChoice(); return v ? v === "folded" : ed.palOpen && window.innerWidth >= 1100 ? false : window.innerWidth < 1680; };
  window.addEventListener("resize", () => {
    const board = $("#board");
    if (board && !paletteChoice() && board.classList.contains("pal-folded") !== paletteFolded()) { board.classList.toggle("pal-folded", paletteFolded()); renderPalette(); }
  });
  function togglePalette() {
    try { sessionStorage.setItem("mehteran.palette", paletteFolded() ? "open" : "folded"); } catch { /* no storage */ }
    $("#board").classList.toggle("pal-folded", paletteFolded());
    renderPalette();
  }

  // The editor fills the window: a toolbar, then the palette, the canvas and the inspector side by side (each
  // scrolls on its own), or the YAML text.
  function render() {
    if (!ed.canvas) {
      ed.canvas = new GraphCanvas({editable: !ed.readOnly, labels: {
        connect: (n, port) => S("port_title", {port: portLabel(n.type, port), node: n.title}), input: (n) => S("input_title", {node: n.title}),
        status: (s) => S("status_" + s), port: portLabel},
        onSelect: (sel) => select(sel), onMove: moveNode, onConnect: connect});
      ed.canvas.first = true;
    }
    const toolbar = h("div", {class: "ed-toolbar"},
      h("button", {type: "button", class: "btn small", onclick: () => go("workflows"), title: S("back_to_library")}, "← " + S("tab_workflows")),
      h("div", {class: "ed-titles"},
        h("h2", {id: "wf-title"}, L(ed.model.name) || ed.id || S("new_workflow"),
          " ", h("span", {class: "badge warn", id: "ed-draft", hidden: !ed.draft}, S("draft"))),
        h("p", {id: "wf-sub", class: "small muted"}, ed.origin ? S("copy_note_short", {name: L(ed.origin.name) || ed.origin.id}) : h("code", {}, ed.id))),
      h("div", {class: "seg", role: "tablist", "aria-label": S("view_mode")},
        h("button", {type: "button", role: "tab", class: "tab" + (ed.mode === "visual" ? " active" : ""), "aria-selected": String(ed.mode === "visual"),
          onclick: () => setMode("visual")}, S("mode_visual")),
        h("button", {type: "button", role: "tab", class: "tab" + (ed.mode === "yaml" ? " active" : ""), "aria-selected": String(ed.mode === "yaml"),
          onclick: () => setMode("yaml")}, S("mode_yaml"))),
      ed.readOnly ? null : h("button", {type: "button", class: "icon-btn tb", id: "ed-undo", onclick: undo, title: S("undo") + " · Ctrl/⌘+Z", "aria-label": S("undo")}, "↶"),
      ed.readOnly ? null : h("button", {type: "button", class: "icon-btn tb", id: "ed-redo", onclick: redo, title: S("redo") + " · Ctrl/⌘+Shift+Z", "aria-label": S("redo")}, "↷"),
      h("span", {class: "grow"}),
      h("span", {id: "board-status", class: "small muted", role: "status", "aria-live": "polite"}),
      h("button", {type: "button", class: "btn", id: "ed-run", onclick: runIt}, "▶ " + S("run")),
      h("button", {type: "button", class: "btn primary", id: "ed-save", onclick: save, title: "Ctrl/⌘+S"}, S("save")));
    const yamlPane = h("section", {class: "card prompt-editor yaml-pane", id: "yaml-pane", hidden: ed.mode !== "yaml"},
      ed.origin ? h("p", {class: "small muted"}, S("copy_note", {name: L(ed.origin.name) || ed.origin.id, id: ed.id})) : null,
      h("p", {class: "small muted"}, S(ed.readOnly ? "yaml_readonly" : "yaml_tab_hint")),
      h("textarea", {id: "yaml-text", class: "code", spellcheck: "false", autocapitalize: "off", "aria-label": S("yaml_source"), readonly: ed.readOnly}),
      h("div", {id: "yaml-problems", "aria-live": "polite"}));
    const board = h("div", {class: "ed-board" + (paletteFolded() ? " pal-folded" : ""), id: "board", hidden: ed.mode !== "visual"},
      h("aside", {class: "palette", id: "palette", "aria-label": S("palette_steps")}),
      h("div", {class: "ed-stage"},
        h("div", {class: "canvas-wrap"}, ed.canvas.el,
          h("div", {class: "canvas-tools", role: "group", "aria-label": S("canvas_tools")},
            h("button", {type: "button", class: "icon-btn", onclick: () => ed.canvas.zoomAt(ed.canvas.t.k * 1.2), "aria-label": S("zoom_in"), title: S("zoom_in")}, "+"),
            h("button", {type: "button", class: "icon-btn", onclick: () => ed.canvas.zoomAt(ed.canvas.t.k / 1.2), "aria-label": S("zoom_out"), title: S("zoom_out")}, "−"),
            h("button", {type: "button", class: "icon-btn", onclick: () => ed.canvas.fit(), title: S("fit")}, S("fit")),
            ed.readOnly ? null : h("button", {type: "button", class: "icon-btn", onclick: arrange, title: S("auto_arrange_hint")}, S("auto_arrange")),
            ed.readOnly ? null : h("button", {type: "button", class: "icon-btn danger", id: "ed-delete", onclick: deleteSelection, title: S("delete_hint")}, S("delete_selected"))),
          h("div", {id: "board-warnings", class: "board-warnings"}))),
      h("aside", {class: "ed-side", "aria-label": S("inspector")}, h("section", {class: "inspector", id: "inspector"})));
    fill($("#workflow-body"), toolbar, board, yamlPane);
    if (ed.mode === "yaml") $("#yaml-text").value = ed.yamlBase;
    renderPalette();
    renderCanvas();
    renderInspector();
    renderProblems();
    renderStatus();
    if (ed.canvas.first && ed.mode === "visual") { ed.canvas.first = false; requestAnimationFrame(() => ed.canvas.fit()); }
  }

  function renderStatus() {
    const parts = [];
    if (ed.origin && ed.isNew) parts.push(dirty() ? S("unsaved") : S("copy_unchanged"));
    else if (ed.isNew) parts.push(S("not_saved_yet"));
    else parts.push(dirty() ? S("unsaved") : S("saved_state"));
    const empty = !nodes().length && ed.mode === "visual";  // before the first step nothing is a problem yet
    parts.push(empty ? S("status_no_steps") : ed.valid ? "✓ " + S("valid_short") + (ed.warnings.length ? ` · ${S("warnings_short", {count: ed.warnings.length})}` : "")
      : S("problems_found", {count: ed.problems.length}));
    if (!$("#board-status")) return;
    $("#board-status").textContent = parts.join(" · ");
    $("#board-status").className = "small " + (empty ? "muted" : !ed.valid ? "warn-text" : dirty() ? "warn-text" : "muted");
    if ($("#ed-draft")) $("#ed-draft").hidden = !ed.draft;
    // With problems the workflow can still be kept: as a draft, which cannot run until it passes the check.
    const save = $("#ed-save");
    if (save) {
      const asDraft = !ed.valid && ed.mode === "visual";
      save.disabled = ed.mode === "visual" && !(dirty() || ed.isNew);  // the YAML text is checked when it is saved
      save.textContent = S(asDraft ? "save_as_draft" : "save");
      save.className = "btn" + (asDraft ? "" : " primary");
      save.title = asDraft ? S("draft_hint", {count: ed.problems.length}) : "Ctrl/⌘+S";
    }
    const run = $("#ed-run");
    if (run) {
      run.disabled = !ed.valid;
      run.title = ed.valid ? "" : S("run_blocked", {count: ed.problems.length});
    }
    if ($("#ed-undo")) $("#ed-undo").disabled = ed.history.length < 2;
    if ($("#ed-redo")) $("#ed-redo").disabled = !ed.future.length;
    if ($("#ed-delete")) $("#ed-delete").disabled = !ed.sel;
  }

  function view() {
    const layout = obj(ed.model.layout) || {};
    const list = nodes().map((n) => {
      const where = problemsAt("nodes." + n.id).concat(problemsAt("layout." + n.id));
      const p = obj(layout[n.id]) || {x: 0, y: 0};
      return {id: n.id, type: String(n.type || ""), title: titleOf(n), sub: nodeSub(n), glyph: GLYPH[n.type] || "?",
        ports: portsOf(n), x: Number(p.x) || 0, y: Number(p.y) || 0, problem: where.length ? where.map((q) => q.message).join(" ") : ""};
    });
    const edges = arr(ed.model.connections).map((c, index) => {
      if (!obj(c)) return null;
      const [from, port] = splitFrom(c.from);
      return {from, port, to: c.to, index, problem: problemsAt(`connections[${index}]`).length > 0};
    }).filter(Boolean);
    return {nodes: list, edges};
  }

  function renderCanvas() {
    if (ed.canvas) ed.canvas.setView(view(), ed.sel);
    renderStarters();
  }

  function renderProblems() {
    const box = $("#board-warnings");
    if (!box) return;
    renderStarters();
    // A model wrote this draft: say so until the user closes the note or saves.
    const by = ed.draftBy && ed.isNew ? h("div", {class: "notice warn draft-by", role: "status"}, h("span", {}, S("draft_by", {model: ed.draftBy})),
      h("button", {type: "button", class: "icon-btn", "aria-label": S("close"), title: S("close"), onclick: () => { ed.draftBy = ""; renderProblems(); }}, "✕")) : null;
    // Nothing is called a problem before the first step: the empty canvas offers the starters instead.
    if (!nodes().length || (!ed.problems.length && !ed.warnings.length)) return fill(box, by);
    const line = (p) => h("li", {}, h("button", {type: "button", class: "linkish", onclick: () => focusProblem(p.where)},
      placeOf(p.where) ? h("b", {}, placeOf(p.where) + ": ") : null, p.message));
    // Folded to one line by default, so that the list never covers the boxes being built; the choice is kept.
    const list = ed.problems.length ? h("details", {class: "notice bad problems-list", open: ed.problemsOpen,
      ontoggle: (e) => { ed.problemsOpen = e.currentTarget.open; }},
      h("summary", {}, S(ed.readOnly ? "problems_found" : "draft_problems", {count: ed.problems.length})),
      h("ul", {class: "failures"}, ed.problems.map(line))) : null;
    // Warnings (schema.warnings): the workflow can be saved and run; they name what probably is not meant.
    const warn = ed.warnings.length ? h("details", {class: "notice warn problems-list warnings-list", open: ed.warningsOpen,
      ontoggle: (e) => { ed.warningsOpen = e.currentTarget.open; }},
      h("summary", {}, S("warnings_found", {count: ed.warnings.length})),
      h("ul", {class: "failures"}, ed.warnings.map(line))) : null;
    fill(box, by, list, warn);
  }

  // The place of a problem in the words of the page: the step's title and the field's label, not "nodes.a.config.prompt".
  function placeOf(where) {
    const parts = String(where || "").split(".");
    const node = /^(nodes|layout)$/.test(parts[0]) ? nodeById(parts[1]) : null;
    if (node) {
      const spec = parts[2] === "config" && typeInfo(node.type) ? typeInfo(node.type).config.find((f) => f.name === parts[3]) : null;
      const fieldName = spec ? (spec.name === "prompt" ? S("instruction") : L(spec.label) || spec.name)
        : parts[2] === "label" ? S("node_label") : parts[2] === "fallback_provider" ? S("fallback_provider") : parts[2] && parts[2] !== "config" ? parts[2] : "";
      return `“${titleOf(node)}”` + (fieldName ? ` · ${fieldName}` : "");
    }
    const input = parts[0] === "inputs" && arr(ed.model.inputs).find((i) => obj(i) && i.id === parts[1]);
    if (input) return `${S("place_input")} “${L(input.label) || input.id}”`;
    const edge = /^connections\[(\d+)\]/.exec(where);
    if (edge && conns()[Number(edge[1])]) {
      const c = conns()[Number(edge[1])], from = nodeById(splitFrom(c.from)[0]), to = nodeById(c.to);
      return `${S("connection")} ${from ? titleOf(from) : c.from} → ${to ? titleOf(to) : c.to}`;
    }
    const top = {name: S("workflow_name"), description: S("workflow_description"), id: S("workflow_id"), outputs: S("outputs"), inputs: S("inputs"),
      connections: S("place_connections"), nodes: S("palette_steps")}[parts[0].replace(/\[.*/, "")];
    return top || where || "";
  }

  // The empty canvas: three ways to start. Each is one step of the history, so "Undo" brings the empty canvas back.
  function renderStarters() {
    const wrap = $(".canvas-wrap");
    if (!wrap) return;
    const old = $(".starters", wrap);
    const show = !ed.readOnly && ed.mode === "visual" && !nodes().length;
    if (!show) { if (old) old.remove(); return; }
    if (old) return;
    wrap.appendChild(h("div", {class: "starters"},
      h("h3", {}, S("starters_title")), h("p", {class: "muted small"}, S("starters_text")),
      h("div", {class: "starter-row"},
        h("button", {type: "button", class: "starter", onclick: () => starter("document")}, h("span", {class: "starter-flow"}, "¶ → ✦ → ⇩"), h("b", {}, S("starter_document")),
          h("span", {class: "small muted"}, S("starter_document_text"))),
        h("button", {type: "button", class: "starter", onclick: () => starter("text")}, h("span", {class: "starter-flow"}, "✎ → ✦ → ⇩"), h("b", {}, S("starter_text")),
          h("span", {class: "small muted"}, S("starter_text_text"))),
        h("button", {type: "button", class: "starter describe", onclick: () => Drafter.open()}, h("span", {class: "starter-flow"}, "✦"), h("b", {}, S("starter_describe")),
          h("span", {class: "small muted"}, S("starter_describe_text"))))));
  }

  // A starter: read a document (or take a text typed into the run form), ask a model, save the answer. The
  // instruction is a first suggestion in the page's language; the user changes it.
  function starter(kind) {
    const m = ed.model;
    const lang = textLang(), text = (key) => (UI[key] && UI[key][lang]) || S(key);
    const label = (type) => JSON.parse(JSON.stringify(typeInfo(type).label));
    m.inputs = [kind === "document" ? {id: "document", type: "file", label: {tr: "Belge", en: "Document"}}
      : {id: "text", type: "text", multiline: true, label: {tr: "Metin", en: "Text"}}];
    m.nodes = [];
    const model = modelInput();
    m.inputs.push({id: "language", type: "language", label: {tr: "Cevabın dili", en: "Language of the answer"}});
    if (kind === "document") m.nodes.push({id: "extract", type: "document.extract", label: label("document.extract"), config: {file: "{{inputs.document}}"}});
    m.nodes.push({id: "ai", type: "ai.cli", label: label("ai.cli"), config: {provider: `{{inputs.${model}}}`,
      prompt: kind === "document" ? text("starter_document_prompt") : text("starter_text_prompt") + "\n\n{{inputs.text}}"}});
    m.nodes.push({id: "export", type: "document.export", label: label("document.export"), config: {formats: ["md", "docx"]}});
    m.connections = [...(kind === "document" ? [{from: "extract.text", to: "ai"}] : []), {from: "ai.text", to: "export"}];
    m.outputs = [{id: "result", from: "ai.text", label: {tr: "Sonuç", en: "Result"}}];
    ensureLayout(true);
    ed.sel = {kind: "node", id: "ai"};
    changed();
    requestAnimationFrame(() => ed.canvas.fit());
  }

  // --- selection and the inspector ------------------------------------------------------------------
  function select(sel) {
    ed.sel = sel;
    ed.lastField = null;
    renderCanvas();
    renderInspector();
    renderStatus();
  }

  function focusProblem(where) {
    const nodeId = nodeOfProblem(where);
    const edge = /^connections\[(\d+)\]/.exec(where);
    if (nodeId) select({kind: "node", id: nodeId});
    else if (edge && conns()[Number(edge[1])]) select({kind: "edge", index: Number(edge[1])});
    else { ed.wfTab = wfTabOf(where); select(null); }
    // The most precise field that has a place: "nodes.a.config.prompt" before "nodes.a".
    const fields = [...document.querySelectorAll("#inspector [data-where]")];
    const best = fields.filter((el) => where === el.dataset.where || where.startsWith(el.dataset.where + ".") || where.startsWith(el.dataset.where + "["))
      .sort((a, b) => b.dataset.where.length - a.dataset.where.length)[0];
    const folded = best && best.closest("details.advanced:not([open])");
    if (folded) folded.open = true;  // a problem in a folded field: show it
    const target = best && (best.matches("input, textarea, select") ? best : best.querySelector("input, textarea, select, button"));
    if (target) { target.focus(); target.scrollIntoView({block: "center", behavior: "smooth"}); }
    else $("#inspector").scrollIntoView({block: "nearest"});
  }

  function markFields() {
    document.querySelectorAll("#inspector [data-where]").forEach((el) => {
      const own = ed.problems.filter((p) => p.where === el.dataset.where || (el.dataset.deep && (p.where.startsWith(el.dataset.where + ".") || p.where.startsWith(el.dataset.where + "["))));
      el.classList.toggle("invalid", own.length > 0);
      const note = el.querySelector(":scope > .field-problem");
      if (note) note.textContent = own.map((p) => p.message).join(" ");
    });
    // A folded section says how many of its fields have a problem.
    document.querySelectorAll("#inspector details.advanced").forEach((box) => {
      const count = box.querySelectorAll(".invalid").length;
      const badge = box.querySelector(".adv-count");
      badge.hidden = !count;
      badge.textContent = String(count);
    });
  }

  function renderInspector() {
    const box = $("#inspector");
    if (!box) return;
    const focus = document.activeElement && box.contains(document.activeElement) && document.activeElement.dataset.key;
    const n = ed.sel && ed.sel.kind === "node" ? nodeById(ed.sel.id) : null;
    const c = ed.sel && ed.sel.kind === "edge" ? conns()[ed.sel.index] : null;
    fill(box, ...(n ? nodeInspector(n) : c ? edgeInspector(c, ed.sel.index) : workflowPanel()));
    if (ed.readOnly) box.querySelectorAll("input, textarea, select").forEach((el) => { el.disabled = el.tagName === "SELECT" || el.type === "checkbox"; el.readOnly = true; });
    if (ed.readOnly) box.querySelectorAll("button[data-edit]").forEach((el) => (el.disabled = true));
    markFields();
    if (focus) box.querySelector(`[data-key="${CSS.escape(focus)}"]`)?.focus({preventScroll: true});
  }

  function renderInspectorChips() {
    document.querySelectorAll("#inspector .ref-chips").forEach((el) => el.replaceWith(refChips(el.dataset.node)));
  }

  // A labelled field. where: the check's place for it (problems show under the field).
  function field(label, control, where, opts = {}) {
    return h("label", {class: "fld" + (opts.wide ? " wide" : ""), "data-where": where || null, "data-deep": opts.deep ? "1" : null},
      h("span", {class: "fld-label"}, label, opts.hint ? h("span", {class: "muted small"}, " · " + opts.hint) : null),
      control, opts.after || null, h("span", {class: "field-problem small", "aria-live": "polite"}));
  }

  function textControl(get, set, key, opts = {}) {
    const el = opts.area ? h("textarea", {rows: opts.rows || 3, spellcheck: opts.spell ? "true" : "false", "data-key": key})
      : h("input", {type: opts.type || "text", "data-key": key, placeholder: opts.placeholder || null, min: opts.min, max: opts.max, class: opts.mono ? "mono" : null});
    const value = get();
    el.value = value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
    el.addEventListener("input", () => { set(el.value); changed({coalesce: key, keepInspector: true}); });
    if (opts.template) {
      const remember = () => { ed.lastField = {key, start: el.selectionStart, end: el.selectionEnd}; };
      ["focus", "keyup", "click", "select", "blur"].forEach((ev) => el.addEventListener(ev, remember));
      el.dataset.template = "1";
    }
    return el;
  }

  function setOrDelete(target, key, value) {
    if (value === "" || value == null) delete target[key];
    else target[key] = value;
  }

  // A {tr, en} text. A plain string becomes a map when one language is edited.
  function localizedPair(target, key, where, label, opts = {}) {
    const get = (lang) => { const v = target[key]; return typeof v === "string" ? v : obj(v) ? v[lang] || "" : ""; };
    // opts.only "main": one field, in the page's language (English for a third one); what is written there is the
    // text of the other language too while that one has none of its own. opts.only "other": the other language
    // alone (shown under "Advanced settings"). Without it: both, side by side.
    const main = textLang(), other = main === "tr" ? "en" : "tr";
    const set = (lang, value) => {
      const v = target[key];
      const map = typeof v === "string" ? {tr: v, en: v} : {...(obj(v) || {})};
      const before = map[lang];
      if (value.trim()) map[lang] = value; else delete map[lang];
      if (opts.only === "main" && (!map[other] || map[other] === before)) { if (value.trim()) map[other] = value; else delete map[other]; }
      if (Object.keys(map).length) target[key] = map; else delete target[key];
    };
    const langs = opts.only === "main" ? [main] : opts.only === "other" ? [other] : ["tr", "en"];
    return h("div", {class: "pair" + (opts.wide ? " wide" : "") + (opts.only === "main" ? " single" : ""), "data-where": where, "data-deep": "1"},
      h("span", {class: "fld-label"}, label, opts.required ? h("span", {class: "muted small"}, " · " + S("required")) : null),
      h("div", {class: "pair-row"}, langs.map((lang) => h("span", {class: "pair-cell"}, opts.only === "main" ? null : h("span", {class: "lang-tag"}, lang.toUpperCase()),
        textControl(() => get(lang), (v) => set(lang, v), `${where}:${lang}`, {area: opts.area, rows: opts.rows, spell: true})))),
      h("span", {class: "field-problem small"}));
  }

  // The node panel is simple by default: the step's title, its instruction and its model (the fields that the
  // node type marks "basic" in GET /api/node-types). Everything else (id, both labels, references, retries, timeout,
  // the other fields) is under "Advanced settings", folded.
  const BASIC_FALLBACK = {"ai.cli": ["prompt", "provider"], "ai.map": ["prompt", "provider", "split"], "document.export": ["formats"],
    "condition": ["question", "provider"]};  // for a server without the "basic" flags
  // Shown in the simple panel too: how a loop splits its text, and which file of the run form a step reads.
  const ALSO_BASIC = {"ai.map": ["split"], "document.extract": ["file"]};
  const isBasic = (n, spec) => (ALSO_BASIC[n.type] || []).includes(spec.name)
    || (spec.basic !== undefined ? spec.basic === true : (BASIC_FALLBACK[n.type] || []).includes(spec.name));

  function titleControl(n, where) {
    const lang = textLang(), other = lang === "tr" ? "en" : "tr";  // a workflow's texts are Turkish and English
    const input = h("input", {type: "text", class: "title-input", value: titleOf(n), "data-key": where + ".label:title", "aria-label": S("step_title"),
      placeholder: typeLabel(n.type)});
    input.addEventListener("input", () => {
      // The title in the page's language (English for a third one); the other language gets it too while it has none of its own.
      const label = typeof n.label === "string" ? {tr: n.label, en: n.label} : {...(obj(n.label) || {})};
      const before = label[lang];
      const value = input.value.trim();
      if (value) label[lang] = value; else delete label[lang];
      if (value && (!label[other] || label[other] === before)) label[other] = value;
      if (Object.keys(label).length) n.label = label; else delete n.label;
      changed({coalesce: where + ".label", keepInspector: true});
    });
    return input;
  }

  function nodeInspector(n) {
    const info = typeInfo(n.type);
    const where = "nodes." + n.id;
    if (!obj(n.config)) n.config = {};
    const config = info ? info.config : [];
    // The instruction (or question) first, the model last: what the step does, then who does it.
    const rank = (spec) => (spec.widget === "provider" ? 2 : spec.kind === "template" || spec.kind === "localized" ? 0 : 1);
    const basic = config.filter((spec) => isBasic(n, spec)).sort((a, b) => rank(a) - rank(b));
    const advanced = config.filter((spec) => !isBasic(n, spec));
    const note = UI["node_simple_" + n.type.replace(/\W/g, "_")] ? S("node_simple_" + n.type.replace(/\W/g, "_")) : info ? L(info.description) : S("unknown_type");
    const head = h("div", {class: "inspector-head simple-head", "data-where": where + ".label", "data-deep": "1"},
      h("span", {class: "node-glyph"}, GLYPH[n.type] || "?"),
      h("div", {class: "grow"}, titleControl(n, where), h("p", {class: "muted small"}, typeLabel(n.type))),
      h("button", {type: "button", class: "icon-btn danger", "data-edit": "1", onclick: deleteSelection, title: S("remove_node"), "aria-label": S("remove_node")}, "🗑"));
    const idInput = h("input", {type: "text", class: "mono", value: n.id, "data-key": where + ".id", spellcheck: "false"});
    idInput.addEventListener("change", () => rename("nodes", n.id, idInput.value.trim(), idInput));
    const more = [
      h("div", {class: "grid2"}, field(S("node_id"), idInput, where + ".id", {hint: S("rename_hint")}),
        field(S("node_type"), h("input", {type: "text", value: n.type, readonly: true, class: "mono", tabindex: "-1"}), where + ".type")),
      localizedPair(n, "label", where + ".label", S("other_language_of", {field: S("node_label")}), {only: "other"}),
      basic.filter((spec) => spec.kind === "localized").map((spec) => localizedPair(n.config, spec.name, `${where}.config.${spec.name}`,
        S("other_language_of", {field: L(spec.label) || spec.name}), {area: true, rows: 3, wide: true, only: "other"})),
      advanced.map((spec) => configField(n, spec, `${where}.config.${spec.name}`)),
      basic.some((spec) => spec.kind === "template" && spec.widget !== "provider") ? h("div", {class: "fld"},
        h("span", {class: "fld-label"}, S("references_title")), h("p", {class: "small muted"}, S("references_hint")), refChips(n.id)) : null];
    if (info && info.takes_retries) {
      more.push(h("div", {class: "grid2"},
        field(S("retries"), textControl(() => n.retries, (v) => setOrDelete(n, "retries", v === "" ? "" : Number(v)), where + ".retries",
          {type: "number", min: 0, max: 10, placeholder: String(info.default_retries)}), where + ".retries", {hint: S("default_value", {value: info.default_retries})}),
        field(S("timeout"), textControl(() => n.timeout, (v) => setOrDelete(n, "timeout", v === "" ? "" : Number(v)), where + ".timeout",
          {type: "number", min: 1, max: 86400, placeholder: String(info.default_timeout)}), where + ".timeout", {hint: S("seconds_default", {value: info.default_timeout})})));
    }
    // A step that takes a model may name a fallback model for a usage limit (off while empty): a model name or a
    // model input of the run form ("{{inputs.backup}}").
    if (config.some((spec) => spec.widget === "provider")) {
      const listId = "fallback-names-" + n.id;
      const names = [...AUTO_KINDS, ...(INFO.providers || []).flatMap((p) => [p.name, ...(p.models || []).map((x) => `${p.name}/${x}`)]),
        ...arr(ed.model.inputs).filter((i) => obj(i) && i.type === "provider" && typeof i.id === "string").map((i) => `{{inputs.${i.id}}}`)];
      const input = textControl(() => n.fallback_provider, (v) => setOrDelete(n, "fallback_provider", v.trim()), where + ".fallback_provider", {mono: true});
      input.setAttribute("list", listId);
      more.push(field(S("fallback_provider"), input, where + ".fallback_provider",
        {hint: S("fallback_provider_hint"), after: h("datalist", {id: listId}, names.map((x) => h("option", {value: x})))}));
    }
    return [head, h("p", {class: "simple-note"}, note),
      // "Test this step" stands right under the instruction (or the condition's question): the answer shows there.
      h("div", {class: "node-settings simple"}, basic.map((spec) => [simpleField(n, spec, `${where}.config.${spec.name}`),
        (spec.name === "prompt" || spec.name === "question") && canTry(n) ? tryBox(n) : null])),
      advancedBox("node:" + n.id, more)];
  }

  // --- "Test this step": one step runs alone (POST /api/editor/try), nothing is saved ------------------------
  // The texts of the steps before it come from the last run of this workflow, or are a pasted sample. The state of
  // a test is kept per step while the editor is open (ed.tries), so the answer stays when the panel is drawn again.
  const canTry = (n) => !ed.readOnly && (n.type === "ai.cli" || (n.type === "condition" && obj(n.config) && n.config.operator === "ai"));

  function redrawTry(id) {
    const el = document.getElementById("try-" + id), n = nodeById(id);
    if (el && n && ed.sel && ed.sel.kind === "node" && ed.sel.id === id) el.replaceWith(tryBox(n));
  }

  async function openTry(n) {
    const st = ed.tries[n.id];
    st.open = true;
    st.source = null;
    st.problem = "";
    redrawTry(n.id);
    try {
      st.source = await api("POST", "/api/editor/try/source", {model: ed.model, node: n.id,
        templates: [`user:${ed.id}`, ...(ed.origin ? [`${ed.origin.source}:${ed.origin.id}`] : [])]});
      if (!st.source.run) st.mode = "sample";
    } catch (err) { st.problem = err.problems && err.problems.length ? S("try_needs_valid") : err.message; }
    redrawTry(n.id);
  }

  async function startTry(n, provider) {
    const st = ed.tries[n.id];
    Object.assign(st, {problem: "", result: null, log: "", offset: 0, provider});
    try {
      const body = {model: ed.model, node: n.id, provider};
      if (st.mode === "sample") body.sample = st.sample || ""; else body.run = st.source.run.id;
      st.usedSource = st.mode === "sample" ? S("try_from_sample") : S("try_from_run", {time: fmtTime(st.source.run.created)});
      st.job = (await api("POST", "/api/editor/try", body)).id;
    } catch (err) { st.problem = [err.message, ...(err.problems || [])].filter((x, i, all) => all.indexOf(x) === i).join(" "); return redrawTry(n.id); }
    redrawTry(n.id);
    await followJob(st.job, (state) => {
      st.log += state.log;
      const pre = document.querySelector(`#try-${CSS.escape(n.id)} .job-log`);
      if (pre) { pre.textContent = st.log; pre.scrollTop = pre.scrollHeight; }
    }, (state) => {
      st.job = null;
      if (state.status === "done") st.result = state.result;
      else st.problem = state.status === "cancelled" ? S("try_cancelled") : state.error || S("try_failed");
      redrawTry(n.id);
    });
  }

  function tryBox(n) {
    ed.tries = ed.tries || {};
    const st = ed.tries[n.id] || (ed.tries[n.id] = {open: false, mode: "run", sample: "", source: null, job: null, log: "", result: null, problem: ""});
    const box = (...children) => h("div", {class: "try-box" + (st.open ? " open" : ""), id: "try-" + n.id}, children);
    if (!st.open) {
      return box(h("button", {type: "button", class: "btn small", onclick: () => openTry(n)}, "▷ " + S("try_step")),
        h("span", {class: "small muted"}, S("try_step_hint")));
    }
    const head = h("div", {class: "row try-head"}, h("b", {}, S("try_step")), h("span", {class: "grow"}),
      h("button", {type: "button", class: "icon-btn", "aria-label": S("close"), title: S("close"), disabled: Boolean(st.job),
        onclick: () => { st.open = false; redrawTry(n.id); }}, "✕"));
    if (!st.source) return box(head, h("p", {class: "small " + (st.problem ? "warn-text" : "muted")}, st.problem || S("try_loading")));
    const run = st.source.run;
    const name = "try-src-" + n.id;
    const pick = (mode, label, disabled) => h("label", {class: "check"}, h("input", {type: "radio", name, checked: st.mode === mode, disabled: disabled || Boolean(st.job),
      onchange: () => { st.mode = mode; redrawTry(n.id); }}), label);
    const sample = h("textarea", {rows: 4, "aria-label": S("try_sample"), placeholder: S("try_sample_placeholder"), disabled: Boolean(st.job)});
    sample.value = st.sample;
    sample.addEventListener("input", () => { st.sample = sample.value; });
    // The model: the run form's picker (the tool's name, its models, and how much of its usage limit is used now).
    const model = providerField({id: "try-model-" + n.id, default: st.provider || st.source.provider || ""});
    ["change", "input"].forEach((ev) => model.addEventListener(ev, () => { st.provider = model.read(); }));
    const go = h("button", {type: "button", class: "btn primary small", disabled: Boolean(st.job), onclick: () => startTry(n, model.read())}, "▷ " + S("try_run"));
    const cancel = st.job ? h("button", {type: "button", class: "btn small", onclick: () => api("POST", `/api/editor/jobs/${st.job}/cancel`).catch(() => {})}, S("cancel_action")) : null;
    const answer = st.result ? h("div", {class: "try-result"},
      h("p", {class: "small muted"}, S("try_answer_of", {model: st.result.provider, source: st.usedSource})),
      st.result.branch ? h("p", {}, h("span", {class: "badge " + (st.result.branch === "true" ? "good" : "warn")}, S("try_branch", {branch: portLabel(n.type, st.result.branch)}))) : null,
      h("div", {class: "try-answer"}, resultView(st.result.text, true))) : null;
    return box(head,
      h("div", {class: "stack try-source"}, h("span", {class: "fld-label"}, S("try_source")),
        pick("run", run ? h("span", {}, S("try_from_run", {time: fmtTime(run.created)}), " ",
          h("a", {href: "#runs/" + run.id, class: "small"}, S("try_open_run"))) : h("span", {class: "muted"}, S("try_no_run")), !run),
        pick("sample", S("try_from_sample")),
        st.mode === "sample" ? sample : null),
      h("div", {class: "stack"}, h("span", {class: "fld-label"}, S("model")), model),
      h("p", {class: "small muted"}, S("try_note")),
      h("div", {class: "row"}, go, cancel, st.job ? h("span", {class: "small muted", role: "status"}, S("try_working")) : null),
      st.problem ? h("p", {class: "small warn-text", role: "alert"}, st.problem) : null,
      st.job || (st.log && !st.result) ? h("pre", {class: "job-log", "aria-label": S("live_log")}, st.log) : null,
      answer);
  }

  // Follows an editor job (drafting.Jobs): onPiece for each state while it runs, onEnd with the last one.
  async function followJob(id, onPiece, onEnd) {
    let offset = 0;
    for (;;) {
      let state;
      try { state = await api("POST", `/api/editor/jobs/${id}`, {offset}); } catch (err) { return onEnd({status: "failed", error: err.message}); }
      offset = state.offset;
      onPiece(state);
      if (state.status !== "running") {
        if (state.log) continue;  // the rest of the log first
        return onEnd(state);
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
  }

  // Which file of the run form the step reads: one of the workflow's file inputs, or a new one made here.
  function fileInputPicker(n, key, w, label) {
    const files = arr(ed.model.inputs).filter((i) => obj(i) && i.type === "file" && typeof i.id === "string");
    const current = /^\{\{\s*inputs\.([a-z][a-z0-9_-]*)\s*\}\}$/.exec(String(n.config[key] || "").trim());
    const add = () => {
      if (!Array.isArray(ed.model.inputs)) ed.model.inputs = [];
      const taken = new Set(ed.model.inputs.map((i) => obj(i) && i.id));
      let id = "document";
      for (let k = 2; taken.has(id); k++) id = `document${k}`;
      ed.model.inputs.push({id, type: "file", label: {tr: "Belge", en: "Document"}});
      n.config[key] = `{{inputs.${id}}}`;
      changed();
    };
    return h("div", {class: "fld", "data-where": w},
      h("span", {class: "fld-label"}, label),
      files.length ? h("select", {"data-key": w, onchange: (e) => { setOrDelete(n.config, key, e.target.value ? `{{inputs.${e.target.value}}}` : ""); changed({keepInspector: true}); }},
        h("option", {value: ""}, "–"),
        files.map((i) => h("option", {value: i.id, selected: Boolean(current && current[1] === i.id)}, `${L(i.label) || i.id}${i.multiple ? " · " + S("multiple_files") : ""}`))) : null,
      h("button", {type: "button", class: "btn small", "data-edit": "1", onclick: add}, "+ " + S("add_file_input")),
      h("span", {class: "small muted fld-help"}, S("file_input_hint")),
      h("span", {class: "field-problem small"}));
  }

  // A folded "Advanced settings" section; it stays open or closed per thing while the editor is open, and its
  // summary counts the problems inside it.
  function advancedBox(key, children) {
    ed.advanced = ed.advanced || {};
    return h("details", {class: "advanced", open: Boolean(ed.advanced[key]), ontoggle: (e) => { ed.advanced[key] = e.currentTarget.open; }},
      h("summary", {}, S("advanced_settings"), h("span", {class: "tab-count bad adv-count", hidden: true})),
      h("div", {class: "node-settings"}, children));
  }

  // A basic field: an instruction or question as a large plain text box (no {{...}} needed: the engine gives the step
  // the texts connected to it), the model as today, a choice, formats.
  function simpleField(n, spec, w) {
    const key = spec.name;
    if (spec.kind === "template" && spec.widget === "provider") return modelPicker(n, key, w, L(spec.label) || S("model"));
    if (n.type === "document.extract" && key === "file") return fileInputPicker(n, key, w, L(spec.label) || key);
    if (spec.kind === "template" || spec.kind === "localized") {
      const label = key === "prompt" ? S("instruction") : key === "question" ? S("condition_question") : L(spec.label) || key;
      const hint = L(spec.help) || (key === "prompt" ? S("instruction_hint") : "");
      if (spec.kind === "localized") return localizedPair(n.config, key, w, label, {area: true, rows: 3, wide: true, only: "main"});
      return field(label, textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v), w,
        {area: true, rows: key === "prompt" ? 10 : 4, template: true, spell: true}), w,
        {wide: true, after: [hint ? h("span", {class: "small muted fld-help"}, hint) : null,
          spec.item_fields ? itemChips(n, key, w, spec.item_fields) : null]});
    }
    return configField(n, spec, w);
  }

  // One config field of a node, made from its description (kind, widget, options, limits, help).
  function configField(n, spec, w) {
    const key = spec.name;
    const label = L(spec.label) || key;
    const hint = spec.kind === "bool" ? null : spec.required ? S("required") : S("optional");
    const help = L(spec.help) ? h("span", {class: "small muted fld-help"}, L(spec.help)) : null;
    if (spec.kind === "template" && spec.widget === "provider") return modelPicker(n, key, w, label);
    if (spec.kind === "template") {
      return field(label, textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v), w,
        {area: spec.widget === "area", rows: key === "prompt" ? 12 : 6, template: true, mono: spec.widget !== "area"}), w,
        {hint, wide: true, after: [help, spec.item_fields ? itemChips(n, key, w, spec.item_fields) : null, refChips(n.id)]});
    }
    if (spec.kind === "localized") return localizedPair(n.config, key, w, label, {area: true, rows: 2, wide: true});
    if (spec.kind === "int") {
      return field(label, textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v === "" ? "" : Number(v)), w,
        {type: "number", min: spec.min ?? 1, max: spec.max, placeholder: spec.default != null ? String(spec.default) : null}), w, {hint, after: help});
    }
    if (spec.kind === "choice") {
      const current = n.config[key] ?? spec.default ?? "";
      return field(label, h("select", {"data-key": w, onchange: (e) => { setOrDelete(n.config, key, e.target.value); changed({keepInspector: true}); }},
        spec.required || spec.default != null ? null : h("option", {value: ""}, "–"),
        spec.options.map((o) => h("option", {value: o.value, selected: o.value === current}, L(o.label) || o.value))), w, {hint, after: help});
    }
    if (spec.kind === "formats") {
      const current = () => (Array.isArray(n.config[key]) ? n.config[key] : spec.default || []);
      return h("fieldset", {class: "plain fld", "data-where": w}, h("legend", {}, label),
        h("div", {class: "checks"}, INFO.formats.map((f) => h("label", {}, h("input", {type: "checkbox", checked: current().includes(f), "data-key": `${w}:${f}`,
          onchange: (e) => {
            n.config[key] = INFO.formats.filter((x) => (x === f ? e.target.checked : current().includes(x)));
            changed({keepInspector: true});
          }}), f))), help, h("span", {class: "field-problem small"}));
    }
    if (spec.kind === "id") return field(label, textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v.trim()), w, {mono: true, placeholder: n.id}), w, {hint, after: help});
    if (spec.kind === "bool") {
      const on = n.config[key] === undefined ? spec.default === true : n.config[key] === true;
      return h("div", {class: "fld", "data-where": w}, h("label", {class: "check"}, h("input", {type: "checkbox", checked: on, "data-key": w,
        onchange: (e) => { if (e.target.checked === (spec.default === true)) delete n.config[key]; else n.config[key] = e.target.checked; changed({keepInspector: true}); }}),
      label), help, h("span", {class: "field-problem small"}));
    }
    // A kind this page does not know yet: its value as text, so nothing is lost.
    return field(label, textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v), w, {mono: true}), w, {hint, after: help});
  }

  // The per-part fields of a loop's prompt ({{item.text}} ...): inserted into this field only, no connection needed.
  function itemChips(n, key, w, fields) {
    return h("div", {class: "ref-chips item-chips"}, h("span", {class: "small muted"}, S("item_refs_title")),
      fields.map((f) => h("button", {type: "button", class: "ref-chip item", "data-edit": "1", onclick: () => {
        const el = document.querySelector(`#inspector [data-key="${CSS.escape(w)}"]`);
        const own = ed.lastField && ed.lastField.key === w;
        const text = `{{${f}}}`;
        el.setRangeText(text, own ? ed.lastField.start : el.value.length, own ? ed.lastField.end : el.value.length, "end");
        n.config[key] = el.value;
        ed.lastField = {key: w, start: el.selectionStart, end: el.selectionEnd};
        changed({keepInspector: true});
        el.focus({preventScroll: true});
      }}, `{{${f}}}`)));
  }

  // The references a template field of node id can use: every input, the outputs of connected nodes, and the
  // outputs of other nodes (inserting one of those connects it first). Nodes after this one are not offered:
  // that would make a cycle.
  function references(id) {
    const out = arr(ed.model.inputs).filter((i) => obj(i) && typeof i.id === "string")
      .map((i) => ({ref: `inputs.${i.id}`, title: L(i.label) || i.id, kind: "input"}));
    const linked = new Set();
    for (const c of conns().filter((c) => c.to === id)) {
      const [from, port] = splitFrom(c.from);
      const src = nodeById(from);
      if (!src) continue;
      for (const p of port ? [port] : portsOf(src)) linked.add(`${from}.${p}`);
    }
    const after = downstream(id);
    for (const src of nodes()) {
      if (src.id === id || after.has(src.id)) continue;
      for (const p of portsOf(src)) {
        const key = `${src.id}.${p}`;
        out.push({ref: `nodes.${key}`, title: `${titleOf(src)} · ${portLabel(src.type, p)}`, kind: linked.has(key) ? "linked" : "unlinked", from: key});
      }
    }
    return out.sort((a, b) => ["input", "linked", "unlinked"].indexOf(a.kind) - ["input", "linked", "unlinked"].indexOf(b.kind));
  }

  function downstream(id) {
    const seen = new Set(), todo = [id];
    while (todo.length) {
      const cur = todo.pop();
      for (const c of conns()) if (splitFrom(c.from)[0] === cur && !seen.has(c.to)) { seen.add(c.to); todo.push(c.to); }
    }
    return seen;
  }

  function refChips(id) {
    const refs = references(id);
    return h("div", {class: "ref-chips", "data-node": id},
      h("span", {class: "small muted"}, S(ed.readOnly ? "refs_title_ro" : "refs_title")),
      refs.length ? refs.map((r) => h("button", {type: "button", class: "ref-chip " + r.kind, "data-edit": "1",
        title: r.kind === "unlinked" ? S("ref_connects", {from: r.from, to: id}) : r.title,
        onclick: (e) => insertRef(id, r, e.currentTarget)}, r.kind === "unlinked" ? "+ " : "", `{{${r.ref}}}`)) : h("span", {class: "small muted"}, S("refs_none")));
  }

  function insertRef(id, r, chip) {
    const n = nodeById(id);
    // The field to insert into: the last template field used, else the one this chip row belongs to.
    const own = chip.closest(".fld").querySelector("[data-template]") || document.querySelector("#inspector [data-template]");
    const key = ed.lastField && document.querySelector(`#inspector [data-key="${CSS.escape(ed.lastField.key)}"]`) ? ed.lastField.key : own.dataset.key;
    const el = document.querySelector(`#inspector [data-key="${CSS.escape(key)}"]`);
    const configKey = key.split(".config.")[1];
    const start = ed.lastField && ed.lastField.key === key ? ed.lastField.start : el.value.length;
    const end = ed.lastField && ed.lastField.key === key ? ed.lastField.end : el.value.length;
    const text = `{{${r.ref}}}`;
    el.setRangeText(text, start, end, "end");
    n.config[configKey] = el.value;
    ed.lastField = {key, start: start + text.length, end: start + text.length};
    if (r.kind === "unlinked") {
      if (!Array.isArray(ed.model.connections)) ed.model.connections = [];
      ed.model.connections.push({from: r.from, to: id});
      toast(S("ref_connected", {from: r.from, to: id}));
    }
    changed({keepInspector: r.kind !== "unlinked"});
    const again = document.querySelector(`#inspector [data-key="${CSS.escape(key)}"]`);
    if (again) { again.focus({preventScroll: true}); again.setSelectionRange(ed.lastField.start, ed.lastField.end); }
  }

  // The model of an AI step: one list (an input of the run form, the automatic choices, the tools). The tool's
  // model, its thinking level and the written value are under "Advanced", for those who want them.
  function modelPicker(n, key, where, label) {
    const value = String(n.config[key] || "").trim();
    const set = (v) => { setOrDelete(n.config, key, v); changed(); };
    const inputRef = /^\{\{\s*inputs\.([a-z][a-z0-9_-]*)\s*\}\}$/.exec(value);
    const base = value.split("@")[0], effort = value.split("@")[1] || "";
    const providers = INFO.providers || [];
    const provInputs = arr(ed.model.inputs).filter((i) => obj(i) && i.type === "provider" && typeof i.id === "string");
    const toolName = base.split("/")[0], modelName = base.split("/").slice(1).join("/");
    const chosen = !inputRef && !AUTO_KINDS.includes(value) ? providers.find((p) => p.name === toolName) : null;
    const main = inputRef ? value : AUTO_KINDS.includes(value) ? value : toolName;
    const option = (v, text) => h("option", {value: v, selected: v === main}, text);
    const known = new Set([...provInputs.map((i) => `{{inputs.${i.id}}}`), ...AUTO_KINDS, ...providers.map((p) => p.name)]);
    const select = h("select", {"aria-label": label, "data-edit": "1", onchange: (e) => {
      const p = providers.find((x) => x.name === e.target.value);
      set(e.target.value + (p && effort && (p.efforts || []).includes(effort) ? "@" + effort : ""));
    }},
      main && !known.has(main) ? option(main, main) : null,
      !main ? option("", "–") : null,
      provInputs.length ? h("optgroup", {label: S("from_run_form")}, provInputs.map((i) => option(`{{inputs.${i.id}}}`, L(i.label) || i.id))) : null,
      h("optgroup", {label: S("auto_group")}, AUTO_KINDS.map((k) => option(k, S("auto_kind_" + k.replace(":", "_"))))),
      providers.length ? h("optgroup", {label: S("tools_group")}, providers.map((p) => option(p.name, p.label || p.name))) : null);
    const pick = (aria, options, current, onchange) => h("select", {"aria-label": aria, "data-edit": "1", onchange: (e) => onchange(e.target.value)},
      options.map(([v, text]) => h("option", {value: v, selected: v === current}, text)));
    const models = chosen ? [["", S("default_model")], ...chosen.models.map((m) => [m, m])] : [];
    if (chosen && modelName && !chosen.models.includes(modelName)) models.push([modelName, modelName]);
    const testName = inputRef ? (provInputs.find((i) => i.id === inputRef[1]) || {}).default : value;
    const raw = textControl(() => n.config[key], (v) => setOrDelete(n.config, key, v.trim()), where, {mono: true, placeholder: "claude/opus@high"});
    raw.addEventListener("change", () => renderInspector());
    const advanced = h("details", {class: "model-advanced", open: Boolean(modelName || effort) || undefined},
      h("summary", {class: "small"}, S("details")),
      h("div", {class: "stack"},
        chosen ? h("div", {class: "model-tool"},
          pick(S("model"), models, modelName, (v) => set(toolName + (v ? "/" + v : "") + (effort ? "@" + effort : ""))),
          chosen.efforts.length ? pick(S("effort_title"), [["", S("effort_default")], ...chosen.efforts.map((e) => [e, S("effort_" + e)])], effort,
            (v) => set(base + (v ? "@" + v : ""))) : null) : null,
        h("div", {class: "row model-raw"}, raw, h("button", {type: "button", class: "btn small", disabled: !testName, onclick: (e) => testModel(e.currentTarget, testName)},
          S("test_model")))));
    return h("fieldset", {class: "role-pick fld", "data-where": where},
      h("legend", {}, label, h("span", {class: "parallel-tag"}, S("model_hint"))),
      providers.length ? select : h("p", {class: "small warn-text"}, S("no_providers")),
      advanced,
      h("span", {class: "field-problem small"}));
  }

  async function testModel(button, name) {
    const label = button.textContent;
    button.textContent = S("testing");
    await act(button, () => api("POST", "/api/models/test", {name}));
    button.textContent = label;
  }

  function edgeInspector(c, index) {
    const [from, port] = splitFrom(c.from);
    const target = nodeById(c.to);
    const pattern = new RegExp(`\\{\\{\\s*nodes\\.${from.replace(/[-]/g, "\\-")}\\.${port ? port.replace(/[-]/g, "\\-") : "[a-z0-9_-]+"}\\s*\\}\\}`);
    const uses = target && obj(target.config) ? Object.entries(target.config).filter(([, v]) => typeof v === "string" && pattern.test(v)).map(([k]) => k) : [];
    return [h("div", {class: "inspector-head"}, h("div", {}, h("h3", {}, S("connection")), h("p", {class: "muted small"}, `${c.from} → ${c.to}`)),
      h("div", {class: "row"}, h("button", {type: "button", class: "btn small danger", "data-edit": "1", onclick: deleteSelection}, S("remove_connection")))),
    h("p", {class: "small"}, uses.length ? S("connection_used", {fields: uses.join(", "), node: c.to}) : S("connection_unused", {node: c.to})),
    h("div", {"data-where": `connections[${index}]`, "data-deep": "1"}, h("span", {class: "field-problem small"}))];
  }

  // --- the workflow panel (nothing selected): General, Inputs and Results as tabs ---------------------------
  const wfTabOf = (where) => (/^inputs\b/.test(where) ? "inputs" : /^outputs\b/.test(where) ? "results" : "general");

  function workflowPanel() {
    const m = ed.model;
    const tab = ed.wfTab || "general";
    const count = (name) => ed.problems.filter((p) => !nodeOfProblem(p.where) && !/^connections\[/.test(p.where) && wfTabOf(p.where) === name).length;
    const tabs = h("div", {class: "seg wf-tabs", role: "tablist", "aria-label": S("workflow_panel")},
      [["general", S("wf_tab_general")], ["inputs", S("inputs")], ["results", S("outputs")]].map(([name, label]) =>
        h("button", {type: "button", role: "tab", class: "tab" + (tab === name ? " active" : ""), "aria-selected": String(tab === name),
          onclick: () => { ed.wfTab = name; renderInspector(); }}, label, count(name) ? h("span", {class: "tab-count bad"}, String(count(name))) : null)));
    const head = h("div", {class: "inspector-head"}, h("div", {}, h("h3", {}, S("workflow_panel")), h("p", {class: "muted small"}, S("workflow_panel_hint"))));
    if (tab === "inputs") return [head, tabs, h("div", {class: "node-settings"}, inputsEditor())];
    if (tab === "results") return [head, tabs, h("div", {class: "node-settings"}, outputsEditor())];
    const idControl = h("input", {type: "text", class: "mono", value: String(m.id || ""), "data-key": "id", readonly: !ed.isNew, spellcheck: "false"});
    if (ed.isNew) idControl.addEventListener("input", () => { m.id = idControl.value.trim(); ed.id = m.id; changed({coalesce: "id", keepInspector: true}); });
    const categories = [...new Set(state.templates.map((t) => t.category).filter(Boolean))];
    const category = textControl(() => m.category, (v) => setOrDelete(m, "category", v.trim()), "category", {});
    category.setAttribute("list", "category-list");
    return [head, tabs,
      h("div", {class: "node-settings"},
        localizedPair(m, "name", "name", S("workflow_name"), {required: true, only: "main"}),
        localizedPair(m, "description", "description", S("workflow_description"), {area: true, rows: 3, only: "main"})),
      advancedBox("workflow", [
        localizedPair(m, "name", "name", S("other_language_of", {field: S("workflow_name")}), {only: "other"}),
        localizedPair(m, "description", "description", S("other_language_of", {field: S("workflow_description")}), {area: true, rows: 3, only: "other"}),
        field(S("workflow_id"), idControl, "id", {hint: ed.isNew ? S("required") : S("id_fixed")}),
        h("div", {class: "grid2"},
          field(S("version"), textControl(() => m.version, (v) => setOrDelete(m, "version", v.trim()), "version", {}), "version"),
          field(S("category"), h("span", {}, category, h("datalist", {id: "category-list"}, categories.map((c) => h("option", {value: c}, categoryLabel(c))))), "category"))])];
  }

  function move(list, i, d) {
    const j = i + d;
    if (j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
    changed();
  }

  function inputsEditor() {
    const m = ed.model;
    const list = arr(m.inputs);
    const typeSel = h("select", {"aria-label": S("input_type")}, INFO.input_types.map((t) => h("option", {value: t}, S("input_type_" + t))));
    const add = h("div", {class: "row"}, typeSel, h("button", {type: "button", class: "btn small", "data-edit": "1", onclick: () => {
      if (!Array.isArray(m.inputs)) m.inputs = [];
      const taken = new Set(m.inputs.map((i) => obj(i) && i.id));
      let id = typeSel.value === "provider" ? "model" : typeSel.value === "file" ? "document" : typeSel.value;
      for (let k = 2; taken.has(id); k++) id = `${typeSel.value}_${k}`;
      const name = "input_type_" + typeSel.value;
      const item = {id, type: typeSel.value, label: {[textLang()]: (UI[name] && UI[name][textLang()]) || S(name)}};
      if (typeSel.value === "choice") item.options = [];
      m.inputs.push(item);
      changed();
    }}, "+ " + S("add_input")));
    return h("section", {class: "sub-box"}, h("h4", {}, S("inputs")), h("p", {class: "small muted"}, S("inputs_hint")),
      list.map((item, i) => obj(item) ? inputCard(item, i, list) : null), add);
  }

  function inputCard(item, i, list) {
    const where = typeof item.id === "string" && /^[a-z][a-z0-9_-]*$/.test(item.id) ? `inputs.${item.id}` : `inputs[${i}]`;
    const idInput = h("input", {type: "text", class: "mono", value: String(item.id || ""), "data-key": where + ".id", spellcheck: "false"});
    idInput.addEventListener("change", () => rename("inputs", item.id, idInput.value.trim(), idInput));
    const typeSel = h("select", {"data-key": where + ".type", onchange: (e) => {
      item.type = e.target.value;
      for (const [k, only] of [["formats", "file"], ["multiple", "file"], ["options", "choice"], ["multiline", "text"]]) if (item.type !== only && !(k === "multiple" && item.type === "url")) delete item[k];
      if (item.type === "file") delete item.default;
      else if ("default" in item && item.type !== "text") delete item.default;
      if (item.type === "choice" && !Array.isArray(item.options)) item.options = [];
      changed();
    }}, INFO.input_types.map((t) => h("option", {value: t, selected: t === item.type}, S("input_type_" + t))));
    const required = h("input", {type: "checkbox", checked: item.required !== false, onchange: (e) => {
      if (e.target.checked) delete item.required; else item.required = false;
      changed({keepInspector: true});
    }});
    const extra = [];
    if (item.type === "file") {
      const current = () => (Array.isArray(item.formats) ? item.formats : INFO.file_formats);
      extra.push(h("fieldset", {class: "plain fld", "data-where": where + ".formats"}, h("legend", {}, S("file_formats")),
        h("div", {class: "checks"}, INFO.file_formats.map((f) => h("label", {}, h("input", {type: "checkbox", checked: current().includes(f), onchange: (e) => {
          const next = INFO.file_formats.filter((x) => (x === f ? e.target.checked : current().includes(x)));
          item.formats = next;
          changed({keepInspector: true});
        }}), f))), h("span", {class: "field-problem small"})));
      extra.push(h("label", {class: "check", "data-where": where + ".multiple"}, h("input", {type: "checkbox", checked: item.multiple === true, onchange: (e) => {
        setOrDelete(item, "multiple", e.target.checked || "");
        changed({keepInspector: true});
      }}), S("multiple_files"), h("span", {class: "small muted"}, " · " + S("multiple_files_hint", {count: INFO.max_files || 20}))));
    } else if (item.type === "url") {
      extra.push(h("label", {class: "check", "data-where": where + ".multiple"}, h("input", {type: "checkbox", checked: item.multiple === true, onchange: (e) => {
        setOrDelete(item, "multiple", e.target.checked || "");
        changed({keepInspector: true});
      }}), S("multiple_urls"), h("span", {class: "small muted"}, " · " + S("multiple_urls_hint", {count: INFO.max_urls || 30}))));
    } else if (item.type === "text") {
      extra.push(h("label", {class: "check"}, h("input", {type: "checkbox", checked: item.multiline === true, onchange: (e) => {
        setOrDelete(item, "multiline", e.target.checked || "");
        changed();
      }}), S("multiline")));
      extra.push(localizedPair(item, "default", where + ".default", S("default"),
        {area: item.multiline === true, rows: 2, wide: true}));
    } else if (item.type === "provider") {
      const names = [...AUTO_KINDS, ...(INFO.providers || []).flatMap((p) => [p.name, ...p.models.map((x) => `${p.name}/${x}`)])];
      const def = textControl(() => item.default, (v) => setOrDelete(item, "default", v.trim()), where + ".default", {mono: true, placeholder: "auto"});
      def.setAttribute("list", "provider-names");
      extra.push(field(S("default_model_field"), h("span", {class: "row"}, def, h("datalist", {id: "provider-names"}, names.map((x) => h("option", {value: x}))),
        h("button", {type: "button", class: "btn small", onclick: (e) => item.default && testModel(e.currentTarget, item.default)}, S("test_model"))), where + ".default"));
    } else if (item.type === "language") {
      // Any language of the registry. Without a default, the run window starts at the interface language.
      extra.push(field(S("default"), h("select", {"data-key": where + ".default", onchange: (e) => { setOrDelete(item, "default", e.target.value); changed({keepInspector: true}); }},
        h("option", {value: ""}, S("language_default_ui")),
        LANGUAGES.map((lang) => h("option", {value: lang.code, selected: lang.code === item.default}, `${lang.native} · ${lang.code}`))), where + ".default"));
      extra.push(h("p", {class: "small muted wide"}, S("language_input_hint")));
    } else if (item.type === "choice") {
      const options = arr(item.options);
      extra.push(h("div", {class: "fld wide", "data-where": where + ".options", "data-deep": "1"}, h("span", {class: "fld-label"}, S("options")),
        options.map((o, k) => {
          const opt = obj(o) ? o : {value: String(o)};
          if (!obj(o)) options[k] = opt;
          const get = (lang) => (typeof opt.label === "string" ? opt.label : obj(opt.label) ? opt.label[lang] || "" : "");
          const setLabel = (lang, v) => {
            const map = typeof opt.label === "string" ? {tr: opt.label, en: opt.label} : {...(obj(opt.label) || {})};
            if (v.trim()) map[lang] = v; else delete map[lang];
            if (Object.keys(map).length) opt.label = map; else delete opt.label;
          };
          return h("div", {class: "option-row"},
            textControl(() => opt.value, (v) => (opt.value = v), `${where}.options[${k}].value`, {mono: true, placeholder: S("option_value")}),
            ["tr", "en"].map((lang) => textControl(() => get(lang), (v) => setLabel(lang, v), `${where}.options[${k}].label:${lang}`, {placeholder: `${S("option_label")} (${lang.toUpperCase()})`})),
            h("button", {type: "button", class: "icon-btn", "data-edit": "1", "aria-label": S("remove"), onclick: () => { options.splice(k, 1); changed(); }}, "×"));
        }),
        h("button", {type: "button", class: "btn small", "data-edit": "1", onclick: () => { options.push({value: `option${options.length + 1}`}); item.options = options; changed(); }}, "+ " + S("add_option")),
        h("span", {class: "field-problem small"})));
      extra.push(field(S("default"), h("select", {"data-key": where + ".default", onchange: (e) => { setOrDelete(item, "default", e.target.value); changed({keepInspector: true}); }},
        h("option", {value: ""}, "–"), options.map((o) => h("option", {value: obj(o) ? o.value : o, selected: (obj(o) ? o.value : o) === item.default}, obj(o) ? o.value : o))), where + ".default"));
    }
    return h("article", {class: "input-card", "data-where": where, "data-deep": null},
      h("div", {class: "row input-card-head"},
        h("span", {class: "badge"}, S("input_type_" + item.type) || item.type),
        h("code", {}, `{{inputs.${item.id}}}`),
        h("span", {class: "grow"}),
        h("button", {type: "button", class: "icon-btn", "data-edit": "1", "aria-label": S("move_up"), title: S("move_up"), disabled: i === 0, onclick: () => move(list, i, -1)}, "↑"),
        h("button", {type: "button", class: "icon-btn", "data-edit": "1", "aria-label": S("move_down"), title: S("move_down"), disabled: i === list.length - 1, onclick: () => move(list, i, 1)}, "↓"),
        h("button", {type: "button", class: "icon-btn danger", "data-edit": "1", "aria-label": S("remove"), title: S("remove"), onclick: () => { list.splice(i, 1); changed(); }}, "×")),
      h("div", {class: "grid3"}, field(S("input_id"), idInput, where + ".id"), field(S("input_type"), typeSel, where + ".type"),
        h("label", {class: "check"}, required, S("required"))),
      localizedPair(item, "label", where + ".label", S("input_label"), {only: "main"}),
      localizedPair(item, "description", where + ".description", S("input_description"), {only: "main"}),
      extra,
      advancedBox("input:" + item.id, [
        localizedPair(item, "label", where + ".label", S("other_language_of", {field: S("input_label")}), {only: "other"}),
        localizedPair(item, "description", where + ".description", S("other_language_of", {field: S("input_description")}), {only: "other"})]),
      h("span", {class: "field-problem small"}));
  }

  function outputsEditor() {
    const m = ed.model;
    const list = arr(m.outputs);
    const sources = nodes().flatMap((n) => portsOf(n).map((p) => `${n.id}.${p}`));
    return h("section", {class: "sub-box"}, h("h4", {}, S("outputs")), h("p", {class: "small muted"}, S("outputs_hint")),
      list.map((o, i) => {
        if (!obj(o)) return null;
        const where = typeof o.id === "string" && /^[a-z][a-z0-9_-]*$/.test(o.id) ? `outputs.${o.id}` : `outputs[${i}]`;
        return h("div", {class: "input-card", "data-where": where, "data-deep": "1"},
          h("div", {class: "grid3"},
            field(S("output_id"), textControl(() => o.id, (v) => (o.id = v.trim()), where + ".id", {mono: true}), where + ".id"),
            field(S("output_from"), h("select", {"data-key": where + ".from", onchange: (e) => { o.from = e.target.value; changed({keepInspector: true}); }},
              h("option", {value: ""}, "–"), [...new Set([...sources, o.from].filter(Boolean))].map((s) => h("option", {value: s, selected: s === o.from}, s))), where + ".from"),
            h("div", {class: "row end"}, h("button", {type: "button", class: "icon-btn danger", "data-edit": "1", "aria-label": S("remove"), onclick: () => { list.splice(i, 1); changed(); }}, "×"))),
          localizedPair(o, "label", where + ".label", S("output_label"), {only: "main"}),
          advancedBox("output:" + o.id, [localizedPair(o, "label", where + ".label", S("other_language_of", {field: S("output_label")}), {only: "other"})]),
          h("span", {class: "field-problem small"}));
      }),
      h("button", {type: "button", class: "btn small", "data-edit": "1", disabled: !sources.length, onclick: () => {
        if (!Array.isArray(m.outputs)) m.outputs = [];
        const taken = new Set(m.outputs.map((o) => obj(o) && o.id));
        let id = "result";
        for (let k = 2; taken.has(id); k++) id = `result_${k}`;
        m.outputs.push({id, from: sources[sources.length - 1]});
        changed();
      }}, "+ " + S("add_output")));
  }

  // --- edits ---------------------------------------------------------------------------------------
  async function rename(kind, old, next, input) {
    if (next === old) return;
    try {
      const res = await api("POST", "/api/editor/rename", {model: ed.model, kind, old, new: next});
      ed.model = res.model;
      if (kind === "nodes" && ed.sel && ed.sel.kind === "node" && ed.sel.id === old) ed.sel = {kind: "node", id: next};
      if (kind === "nodes" && ed.ports[old]) { ed.ports[next] = ed.ports[old]; delete ed.ports[old]; }
      changed();
      toast(S("renamed", {old, new: next}));
    } catch (err) {
      toast(err.message, true);
      input.value = old;
    }
  }

  function addNode(type, at) {
    if (ed.readOnly) return;
    const m = ed.model;
    if (!Array.isArray(m.nodes)) m.nodes = [];
    const base = SHORT[type] || "step";
    const taken = new Set(nodes().map((n) => n.id));
    let id = base;
    for (let k = 2; taken.has(id); k++) id = `${base}${k}`;
    const info = typeInfo(type);
    const config = {};
    for (const spec of info.config) if (spec.default != null && spec.kind !== "bool") config[spec.name] = JSON.parse(JSON.stringify(spec.default));
    // A new node starts with the type's initial settings (GET /api/node-types "initial_config"), e.g. a condition
    // that asks a model a question; a server without them: the same for a condition that offers that mode.
    Object.assign(config, JSON.parse(JSON.stringify(info.initial_config || {})));
    // A new condition asks a model a question (the simple panel's way), when the server offers that mode.
    const operator = info.branches && info.config.find((f) => f.name === "operator");
    if (operator && operator.options.some((o) => o.value === "ai")) config.operator = "ai";
    // A step that reads a file reads the run form's file input: the only one there is, or a new one.
    if (type === "document.extract" && !config.file) {
      if (!Array.isArray(m.inputs)) m.inputs = [];
      const files = m.inputs.filter((i) => obj(i) && i.type === "file" && typeof i.id === "string");
      let input = files.length === 1 ? files[0].id : null;
      if (!files.length) {
        const taken = new Set(m.inputs.map((i) => obj(i) && i.id));
        input = "document";
        for (let k = 2; taken.has(input); k++) input = `document${k}`;
        m.inputs.push({id: input, type: "file", label: {tr: "Belge", en: "Document"}});
      }
      if (input) config.file = `{{inputs.${input}}}`;
    }
    // A step that takes a model takes the run form's model: the workflow's model input, or a new one.
    const modelKey = (info.config.find((f) => f.widget === "provider") || {}).name;
    if (modelKey && !config[modelKey] && (type !== "condition" || config.operator === "ai")) config[modelKey] = `{{inputs.${modelInput()}}}`;
    // Correct by construction: the new step is connected from the selected step (a click on the palette: else from
    // the step added last) when that step gives a text and this one takes one, and it stands to the right of it.
    const from = type === "document.extract" ? null : ed.sel && ed.sel.kind === "node" ? nodeById(ed.sel.id) : at ? null : nodes()[nodes().length - 1];
    const port = from ? freeTextPort(from) : "";
    m.nodes.push({id, type, label: JSON.parse(JSON.stringify(info.label)), config});
    if (!obj(m.layout)) m.layout = {};
    const pos = at ? {x: at.x - NODE_W / 2, y: at.y - HEAD_H / 2} : port ? rightOf(from.id) : nodes().length > 1 ? freeSpot(ed.canvas.center()) : {x: 40, y: 80};
    m.layout[id] = {x: Math.round(pos.x), y: Math.round(pos.y)};
    if (port) {
      if (!Array.isArray(m.connections)) m.connections = [];
      m.connections.push({from: `${from.id}.${port}`, to: id});
    }
    ed.sel = {kind: "node", id};
    changed();  // one step of the history: the node, its inputs and its connection
    toast(port ? S("node_added_connected", {name: L(info.label), from: titleOf(from)}) : S("node_added", {name: L(info.label)}));
    if (!at) requestAnimationFrame(() => ed.canvas.fit());
  }

  // The id of the workflow's model input (the first one), made when there is none.
  function modelInput() {
    const m = ed.model;
    if (!Array.isArray(m.inputs)) m.inputs = [];
    const found = m.inputs.find((i) => obj(i) && i.type === "provider" && typeof i.id === "string");
    if (found) return found.id;
    const taken = new Set(m.inputs.map((i) => obj(i) && i.id));
    let id = "model";
    for (let k = 2; taken.has(id); k++) id = `model${k}`;
    const first = (INFO.providers || [])[0];
    m.inputs.push({id, type: "provider", label: {tr: "Model", en: "Model"}, ...(first ? {default: first.name} : {})});
    return id;
  }

  // The text port of a step that a new step can be connected from: "text"; for a condition its first branch that
  // leads nowhere yet. "" when the step gives files only (an export).
  function freeTextPort(n) {
    const kinds = ed.ports[n.id] || Object.fromEntries(((typeInfo(n.type) || {}).outputs || []).map((o) => [o.name, o.kind]));
    const texts = portsOf(n).filter((p) => kinds[p] === "text");
    if (!(typeInfo(n.type) || {}).branches) return texts.includes("text") ? "text" : texts[0] || "";
    return texts.find((p) => !conns().some((c) => c.from === `${n.id}.${p}`)) || "";
  }

  // A free place for a new box: to the right of the box id, lower while another box stands there.
  function rightOf(id) {
    const p = obj(ed.model.layout[id]) || {x: 0, y: 0};
    return freeSpot({x: (Number(p.x) || 0) + NODE_W + 96 + NODE_W / 2, y: (Number(p.y) || 0) + HEAD_H / 2});
  }
  function freeSpot(center) {
    const pos = {x: center.x - NODE_W / 2, y: center.y - HEAD_H / 2};
    const boxes = nodes().map((n) => obj(ed.model.layout[n.id])).filter(Boolean);
    while (boxes.some((b) => Math.abs(b.x - pos.x) < NODE_W + 24 && Math.abs(b.y - pos.y) < 130)) pos.y += 150;
    return pos;
  }

  function moveNode(id, x, y, final) {
    if (!obj(ed.model.layout)) ed.model.layout = {};
    ed.model.layout[id] = {x: Math.round(x), y: Math.round(y)};
    if (final) changed({keepInspector: true});
  }

  function connect(from, port, to) {
    if (ed.readOnly) return;
    const source = `${from}.${port}`;
    if (conns().some((c) => c.to === to && (c.from === source || c.from === from))) return toast(S("already_connected"), true);
    if (downstream(to).has(from) || to === from) return toast(S("would_cycle"), true);
    if (!Array.isArray(ed.model.connections)) ed.model.connections = [];
    ed.model.connections.push({from: source, to});
    ed.sel = {kind: "edge", index: ed.model.connections.length - 1};
    changed();
  }

  function deleteSelection() {
    if (ed.readOnly || !ed.sel) return;
    const m = ed.model;
    let dangling = [];
    if (ed.sel.kind === "node") {
      const id = ed.sel.id;
      dangling = nodes().filter((n) => n.id !== id && obj(n.config) && Object.values(n.config).some((v) => typeof v === "string" && new RegExp(`\\{\\{\\s*nodes\\.${id}\\.`).test(v))).map((n) => n.id);
      m.nodes = arr(m.nodes).filter((n) => !(obj(n) && n.id === id));
      m.connections = arr(m.connections).filter((c) => !(obj(c) && (splitFrom(c.from)[0] === id || c.to === id)));
      if (obj(m.layout)) delete m.layout[id];
    } else {
      const c = conns()[ed.sel.index];
      const [from, port] = splitFrom(c.from);
      const target = nodeById(c.to);
      const re = new RegExp(`\\{\\{\\s*nodes\\.${from}\\.${port || "[a-z0-9_-]+"}\\s*\\}\\}`);
      if (target && obj(target.config) && Object.values(target.config).some((v) => typeof v === "string" && re.test(v))) dangling = [c.to];
      m.connections = arr(m.connections).filter((x) => x !== c);
    }
    ed.sel = null;
    changed();
    if (dangling.length) toast(S("dangling_refs", {nodes: dangling.join(", ")}), true);
  }

  function arrange() {
    ensureLayout(true);
    changed({keepInspector: true});
    requestAnimationFrame(() => ed.canvas.fit());
  }

  // --- palette: node types (from the server's registry) and the models of the tools -------------------
  function renderPalette() {
    const pal = $("#palette");
    if (!pal) return;
    const folded = paletteFolded();
    const toggle = h("button", {type: "button", class: "icon-btn pal-toggle", "aria-expanded": String(!folded), onclick: togglePalette,
      title: S(folded ? "palette_show" : "palette_hide"), "aria-label": S(folded ? "palette_show" : "palette_hide")}, folded ? "»" : "«");
    if (folded) {
      // Folded: one labelled button that opens the list of steps.
      pal.replaceChildren(h("button", {type: "button", class: "pal-add", "aria-expanded": "false", onclick: togglePalette, disabled: ed.readOnly},
        h("span", {class: "pal-add-plus", "aria-hidden": "true"}, "+"), h("span", {class: "pal-add-text"}, S("add_step"))));
      return;
    }
    const types = Object.values(NODE_TYPES).map(({type, ...info}) => h("div", {class: "step-type kind-" + type.replace(/\W/g, "-"), role: "button",
      tabindex: ed.readOnly ? "-1" : "0", "aria-disabled": String(ed.readOnly), "data-type": type, title: S("palette_hint"),
      onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); addNode(type); } },
      onpointerdown: (e) => paletteDrag(e, {type})},
    h("span", {class: "glyph", "aria-hidden": "true"}, GLYPH[type] || "?"),
    h("span", {}, h("b", {}, L(info.label)), h("span", {class: "small"}, L(info.description)))));
    // The steps only: a step's model is chosen in its panel (modelPicker).
    pal.replaceChildren(h("div", {class: "pal-head"}, h("h3", {class: "palette-title"}, S("palette_steps")), toggle),
      h("section", {class: "card palette-group steps-group"}, types,
      h("p", {class: "muted small"}, S(ed.readOnly ? "palette_readonly" : "palette_hint"))));
  }

  // The config field of a node that takes a model (widget "provider": an AI step, a loop), or null.
  function modelField(n) {
    const field = n && typeInfo(n.type) && typeInfo(n.type).config.find((f) => f.widget === "provider");
    return field ? field.name : null;
  }

  // Dragging from the palette: a node type onto the canvas makes a node there (a click adds it in the middle);
  // a model onto an AI step sets that step's model.
  function paletteDrag(e, what) {
    if (ed.readOnly || e.button !== 0) return;
    const startX = e.clientX, startY = e.clientY;
    let ghost = null;
    const move = (ev) => {
      if (!ghost && Math.hypot(ev.clientX - startX, ev.clientY - startY) < 5) return;
      if (!ghost) {
        ghost = h("div", {class: "drag-ghost"}, what.type ? L(typeInfo(what.type).label) : what.model);
        document.body.appendChild(ghost);
        document.body.classList.add("dragging-step");
      }
      ghost.style.transform = `translate(${ev.clientX + 12}px, ${ev.clientY + 8}px)`;
      const over = document.elementFromPoint(ev.clientX, ev.clientY);
      ed.canvas.el.classList.toggle("drop-target", Boolean(what.type && over && over.closest(".gcanvas") === ed.canvas.el));
      document.querySelectorAll(".gnode.drop").forEach((x) => x.classList.remove("drop"));
      const node = what.model && over && over.closest(".gnode");
      if (node && modelField(nodeById(node.dataset.id))) node.classList.add("drop");
    };
    const up = (ev) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      ed.canvas.el.classList.remove("drop-target");
      document.body.classList.remove("dragging-step");
      document.querySelectorAll(".gnode.drop").forEach((x) => x.classList.remove("drop"));
      if (!ghost) { if (what.type) addNode(what.type); return; }
      ghost.remove();
      const over = document.elementFromPoint(ev.clientX, ev.clientY);
      if (what.type && over && over.closest(".gcanvas") === ed.canvas.el) addNode(what.type, ed.canvas.toWorld(ev.clientX, ev.clientY));
      if (what.model && over && over.closest(".gnode")) {
        const n = nodeById(over.closest(".gnode").dataset.id);
        const key = modelField(n);
        if (key) {
          if (!obj(n.config)) n.config = {};
          n.config[key] = what.model;
          ed.sel = {kind: "node", id: n.id};
          changed();
          toast(S("model_set", {model: what.model, node: n.id}));
        } else toast(S("model_drop_ai"), true);
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  // --- visual <-> YAML -------------------------------------------------------------------------------
  async function setMode(mode) {
    if (mode === ed.mode) return;
    if (mode === "yaml") {
      // An unchanged template shows its file as stored (with comments); otherwise the server writes the model.
      ed.yamlBase = !dirty() && ed.storedYaml != null && !ed.isNew ? ed.storedYaml : (await api("POST", "/api/editor/yaml", {model: ed.model})).yaml;
      ed.mode = "yaml";
      render();
      $("#yaml-text").focus();
      return;
    }
    const text = $("#yaml-text").value;
    if (text !== ed.yamlBase) {
      let res;
      try { res = await api("POST", "/api/editor/parse", {yaml: text}); } catch (err) {
        // Text that is not a YAML mapping stays here with its problems: nothing is lost.
        fill($("#yaml-problems"), problemsBox({message: S("yaml_cannot_switch"), problems: err.problems.length ? err.problems : [err.message]}));
        return;
      }
      ed.model = res.model;
      if (typeof ed.model.id === "string" && ed.isNew) ed.id = ed.model.id;
      ensureLayout();
      ed.sel = null;
      ed.mode = "visual";
      render();
      changed();
      return;
    }
    ed.mode = "visual";
    render();
  }

  // --- save and run ---------------------------------------------------------------------------------
  async function save() {
    if (ed.readOnly) return;
    if (ed.mode === "yaml") return saveYaml();
    const draft = !ed.valid;  // saved as a draft: kept with its problems, cannot run yet
    if (draft && !(dirty() || ed.isNew)) return;
    try {
      if (ed.isNew) {
        const res = await api("POST", "/api/templates/new", {model: ed.model, draft});
        ed.saved = JSON.stringify(ed.model);
        Object.assign(ed, {isNew: false, fresh: false, origin: null, id: res.id, draft});
        toast(S(draft ? "saved_draft" : "saved"));
        await loadTemplateList();
        return go(`workflows/edit/user/${res.id}`);
      }
      // Comments are kept next to their key; only those of removed or renamed keys would be lost: ask first.
      let res = await api("PUT", `/api/templates/user/${ed.id}/model`, {model: ed.model, draft});
      if (!res.saved) {
        if (!confirm(S("comments_confirm", {count: res.comments}))) return;
        res = await api("PUT", `/api/templates/user/${ed.id}/model`, {model: ed.model, draft, drop_comments: true});
      }
      ed.saved = JSON.stringify(ed.model);
      ed.storedYaml = null;
      ed.draft = draft;
      toast(S(draft ? "saved_draft" : "saved"));
      renderStatus();
    } catch (err) {
      toast(err.message, true);
    }
  }

  async function saveYaml() {
    const text = $("#yaml-text").value;
    try {
      if (ed.isNew) {
        const res = await api("POST", "/api/templates/import", {yaml: text});
        Object.assign(ed, {isNew: false, fresh: false, origin: null, saved: ""});
        await loadTemplateList();
        ed.model = null;
        toast(S("saved"));
        return go(`workflows/edit/user/${res.id}`);
      }
      await api("PUT", `/api/templates/user/${ed.id}`, {yaml: text});
      toast(S("saved"));
      await load("user", ed.id);
      ed.mode = "yaml";
      ed.yamlBase = ed.storedYaml;
      render();
    } catch (err) {
      // Text that is YAML but has problems can still be kept as a draft.
      fill($("#yaml-problems"), problemsBox(err), err.status === 400 ? h("div", {class: "row"},
        h("button", {type: "button", class: "btn", onclick: () => saveYamlDraft(text)}, S("save_as_draft")),
        h("span", {class: "small muted"}, S("draft_hint", {count: err.problems.length || 1}))) : null);
    }
  }

  async function saveYamlDraft(text) {
    try {
      if (ed.isNew) {
        const parsed = await api("POST", "/api/editor/parse", {yaml: text});
        const res = await api("POST", "/api/templates/new", {model: parsed.model, draft: true});
        Object.assign(ed, {isNew: false, fresh: false, origin: null, saved: ""});
        await loadTemplateList();
        ed.model = null;
        toast(S("saved_draft"));
        return go(`workflows/edit/user/${res.id}`);
      }
      await api("PUT", `/api/templates/user/${ed.id}/draft`, {yaml: text});
      toast(S("saved_draft"));
      await load("user", ed.id);
      ed.mode = "yaml";
      ed.yamlBase = ed.storedYaml;
      render();
    } catch (err) {
      fill($("#yaml-problems"), problemsBox(err));
    }
  }

  function runIt() {
    // An unchanged copy of a built-in runs the built-in itself.
    if (ed.origin && !dirty()) return openRun(ed.origin.source, ed.origin.id);
    if (ed.isNew || dirty()) return toast(S("save_before_run"), true);
    if (!ed.valid) { toast(S("run_blocked", {count: ed.problems.length}), true); return focusProblem(ed.problems[0].where); }
    openRun(ed.source, ed.id);
  }

  function onKey(e) {
    if (!isEditorHash(state.hash) || !ed.model || $("dialog[open]")) return;
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); save(); return; }
    if (ed.mode !== "visual") return;
    const typing = isText(document.activeElement);
    if (mod && e.key.toLowerCase() === "z" && !typing) { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
    if (mod && e.key.toLowerCase() === "y" && !typing) { e.preventDefault(); redo(); return; }
    if ((e.key === "Delete" || e.key === "Backspace") && !typing && ed.sel) { e.preventDefault(); deleteSelection(); return; }
    if (e.key === "Escape" && !typing && ed.sel) select(null);
  }

  function relabel() { if (ed.model) render(); }

  return {init, open, dirty, relabel, startNew, followJob, current: () => (ed.model && ed.isNew && !nodes().length ? {id: ed.id, name: ed.model.name} : null)};
})();

// "Describe it, I will build it": the user writes what the workflow should do, a model writes a first draft
// (POST /api/editor/draft, mehteran/drafting.py: one model call, a second one only when the first answer does not
// pass the check). From the editor (open) the draft opens there, unsaved. From the library (build) a draft that
// passes the check is saved at once and its page opens on Run; one that does not opens in the editor with its
// problems. Nothing runs by itself.
const Drafter = (() => {
  const st = {dialog: null, text: "", job: null, log: "", problem: "", keep: null, boxText: "", boxBusy: false};

  function dialog() {
    if (!st.dialog) {
      st.dialog = h("dialog", {id: "draft-dialog", class: "draft-dialog", "aria-labelledby": "draft-title"});
      document.body.appendChild(st.dialog);
      st.dialog.addEventListener("close", () => { if (st.job) api("POST", `/api/editor/jobs/${st.job}/cancel`).catch(() => {}); });
    }
    return st.dialog;
  }

  function open() {
    dialog();
    st.keep = Editor.current();  // an empty new workflow: the draft takes its name and id
    st.problem = "";
    draw();
    if (!st.dialog.open) st.dialog.showModal();
    const area = $("textarea", st.dialog);
    if (area) area.focus();
  }

  function draw() {
    const head = h("div", {class: "dialog-head"}, h("div", {}, h("h3", {id: "draft-title"}, S("describe_title")), h("p", {class: "small muted"}, S("describe_intro"))),
      h("button", {type: "button", class: "icon-btn", "aria-label": S("close"), title: S("close"), onclick: () => st.dialog.close()}, "✕"));
    if (st.job) {
      return fill(st.dialog, head, h("div", {class: "layout-body stack"},
        h("p", {role: "status"}, S("describe_working")),
        h("pre", {class: "job-log", "aria-label": S("live_log")}, st.log)),
      h("div", {class: "dialog-foot row"}, h("button", {type: "button", class: "btn", onclick: () => api("POST", `/api/editor/jobs/${st.job}/cancel`).catch(() => {})}, S("describe_stop"))));
    }
    const area = h("textarea", {id: "draft-text", rows: 8, maxlength: 4000, required: true, placeholder: S("describe_placeholder")});
    area.value = st.text;
    area.addEventListener("input", () => { st.text = area.value; });
    const model = providerField({id: "draft-model", default: recall("mehteran.draftModel") || ""});
    const form = h("form", {class: "draft-form", onsubmit: (e) => { e.preventDefault(); start(model.read()); }},
      head,
      h("div", {class: "layout-body stack"},
        h("label", {class: "fld-label", for: "draft-text"}, S("describe_label")), area,
        examples((text) => { st.text = area.value = text; area.focus(); }),
        h("span", {class: "fld-label"}, S("describe_model")), model,
        h("p", {class: "small muted"}, S("describe_one_call")),
        st.problem ? h("div", {class: "notice bad", role: "alert"}, st.problem) : null),
      h("div", {class: "dialog-foot row"}, h("button", {type: "button", class: "btn", onclick: () => st.dialog.close()}, S("cancel_action")),
        h("button", {type: "submit", class: "btn primary"}, "✦ " + S("describe_start"))));
    fill(st.dialog, form);
  }

  const examples = (use) => h("div", {class: "describe-examples"}, h("span", {class: "small muted"}, S("describe_examples")),
    [1, 2, 3].map((k) => h("button", {type: "button", class: "linkish small", onclick: () => use(S("describe_example_" + k))}, "“" + S("describe_example_" + k) + "”")));

  async function start(provider) {
    if (!st.text.trim()) return;
    if (Editor.dirty() && !st.keep && !confirm(S("describe_replace_confirm"))) return;
    remember("mehteran.draftModel", provider);
    st.problem = "";
    st.log = "";
    try { st.job = (await api("POST", "/api/editor/draft", {description: st.text, provider})).id; } catch (err) { st.problem = err.message; return draw(); }
    draw();
    await Editor.followJob(st.job, (state) => {
      st.log += state.log;
      const pre = $(".job-log", st.dialog);
      if (pre) { pre.textContent = st.log; pre.scrollTop = pre.scrollHeight; }
    }, (state) => {
      st.job = null;
      if (state.status !== "done") {
        st.problem = state.status === "cancelled" ? S("describe_cancelled") : state.error || S("describe_failed");
        return st.dialog.open ? draw() : null;
      }
      finish(state.result);
    });
  }

  function finish(result) {
    const model = result.model || {schema_version: 1, id: "draft", name: S("new_workflow"), nodes: []};
    if (st.keep && result.model) Object.assign(model, {id: st.keep.id, name: st.keep.name});
    let yaml = result.valid ? null : result.yaml;
    if (yaml != null && st.keep && result.model) yaml = yaml.replace(/^id:.*$/m, `id: ${st.keep.id}`);
    if (st.dialog && st.dialog.open) st.dialog.close();
    st.text = "";
    Editor.startNew(model, {draftBy: result.provider, yaml, problems: result.valid ? null : result.problems});
    if (!isEditorHash(location.hash.slice(1))) go("workflows/new");
    toast(S(result.valid ? "describe_done" : "describe_done_invalid"));
  }

  // A draft job shown in place (the library's box, the "Here is what I built" card): one line, "Stop", and the tool's
  // transcript as it works (its text and tool uses, from the live log: toolstream.py), open so that the wait shows
  // what is happening; it can be folded. onEnd gets the job's last state.
  async function inline(body, el, onEnd) {
    let job;
    try { job = (await api("POST", "/api/editor/draft", body)).id; } catch (err) { return onEnd({status: "failed", error: err.message}); }
    const log = h("pre", {class: "job-log transcript", "aria-label": S("describe_transcript"), "aria-live": "off"}, S("describe_transcript_wait"));
    let first = true;
    fill(el, h("div", {class: "job-line"}, h("span", {class: "spinner", "aria-hidden": "true"}), h("span", {role: "status"}, S("describe_working_short")),
      h("button", {type: "button", class: "btn small", onclick: () => api("POST", `/api/editor/jobs/${job}/cancel`).catch(() => {})}, S("describe_stop"))),
    h("details", {class: "job-details", open: true}, h("summary", {class: "small muted"}, S("describe_transcript")), log));
    await Editor.followJob(job, (state) => {
      if (!state.log) return;
      if (first) { log.textContent = ""; first = false; }
      const stick = log.scrollHeight - log.scrollTop - log.clientHeight < 40;  // follow the end unless the user scrolled up
      log.textContent += state.log;
      if (stick) log.scrollTop = log.scrollHeight;
    }, onEnd);
  }

  const failure = (state) => (state.status === "cancelled" ? S("describe_cancelled") : state.error || S("describe_failed"));
  const provider = () => recall("mehteran.draftModel") || "auto";

  // The library's box: the first thing on the Workflows tab. A workflow that passes the check is saved and its page
  // opens with "Here is what I built"; one that does not opens in the editor with its problems.
  function box() {
    const el = $("#describe-box");
    if (st.boxBusy) return;  // a build is going on in it
    const area = h("textarea", {id: "describe-box-text", rows: 2, maxlength: 4000, placeholder: S("describe_placeholder"), "aria-labelledby": "describe-box-title"});
    area.value = st.boxText || "";
    area.addEventListener("input", () => { st.boxText = area.value; });
    const auto = h("p", {class: "small muted describe-auto"});
    const showAuto = () => {
      const chosen = autoChoice(provider());
      auto.textContent = chosen ? S("describe_auto_line", {name: (providerInfo(chosen.name.split("@")[0].split("/")[0]) || {}).label || chosen.name}) : "";
    };
    loadProviderStates().then(showAuto);
    const chips = h("div", {class: "describe-chips"}, [1, 2, 3].map((k) => h("button", {type: "button", class: "chip",
      onclick: () => { area.value = st.boxText = S("describe_example_" + k); area.focus(); }}, S("describe_chip_" + k))));
    const work = h("div", {class: "describe-work", "aria-live": "polite"});
    const start = async () => {
      const text = area.value.trim();
      if (!text) return area.focus();
      st.boxBusy = true;
      form.hidden = true;
      await inline({description: text, provider: provider()}, work, async (end) => {
        st.boxBusy = false;
        if (end.status !== "done") { form.hidden = false; return fill(work, h("div", {class: "notice bad", role: "alert"}, failure(end))); }
        const result = end.result;
        if (result.valid && result.model) {
          try {
            const res = await api("POST", "/api/templates/new", {model: result.model, draft: false});
            st.boxText = "";
            state.built = `user/${res.id}`;  // app.js: the page opens with "Here is what I built"
            toast(S("describe_saved", {name: L(result.model.name) || res.id}));
            return go(`workflows/user/${res.id}/run`);
          } catch (err) { toast(err.message, true); }  // not saved: it opens in the editor, to be saved from there
        }
        st.boxText = "";
        finish(result);
      });
    };
    const form = h("form", {class: "describe-box-form", onsubmit: (e) => { e.preventDefault(); start(); }},
      h("div", {class: "describe-box-head"}, h("h3", {id: "describe-box-title"}, "✦ " + S("describe_title")), h("p", {class: "small muted"}, S("describe_lib_intro"))),
      h("div", {class: "describe-row"}, area, h("button", {type: "submit", class: "btn primary"}, S("describe_build"))),
      h("div", {class: "describe-foot"}, chips, auto));
    fill(el, form, work);
  }

  // "Change: …" on "Here is what I built": the model writes the workflow again from its file and the sentence; one
  // that passes the check replaces it (same id); otherwise it stays as it was.
  function change(tpl, id, text, el, done) {
    inline({description: text, provider: provider(), previous: tpl.yaml}, el, async (end) => {
      if (end.status !== "done") return fill(el, h("div", {class: "notice bad", role: "alert"}, failure(end)));
      if (!end.result.valid || !end.result.model) return fill(el, problemsBox({message: S("built_change_invalid"), problems: end.result.problems || []}));
      try {
        await saveWorkflowModel(id, {...end.result.model, id});  // app.js
        toast(S("built_changed"));
        done();
      } catch (err) { fill(el, problemsBox(err)); }
    });
  }

  return {open, box, change};
})();
