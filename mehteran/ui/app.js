// Mehteran web interface: vanilla JavaScript, no build step. Every element is made with h() and text nodes: no HTML
// strings, so no text (a model's answer, a template) can become markup. Tabs and screens are chosen by the address hash:
//   #workflows                              the workflow library
//   #workflows/<source>/<id>[/run|about|runs]   one workflow's page: the run form
//                                           in place, the description and diagram, the workflow's runs
//   #workflows/import                       import a YAML file          #workflows/new             a new workflow
//   #workflows/edit/<source>/<id>           the visual editor (a built-in opens as your own unsaved copy)
//   #runs  #runs/<run>                      the run history and one run (live)
//   #setup                                  tools, installs and sign-ins
// The addresses of earlier versions still work: #templates[/...], #workflow/..., #runs/new/<source>/<id>.
// A run starts from the Run section of the workflow's page (openRun goes there): from a library card, the editor,
// a run's "Run again".
"use strict";

const TOKEN_META = document.querySelector('meta[name="token"]');
let TOKEN = TOKEN_META.content;
const FINAL = new Set(["succeeded", "failed", "cancelled", "interrupted"]);
const RETRYABLE = new Set(["failed", "rejected", "skipped", "cancelled", "interrupted"]);
const TABS = ["workflows", "runs", "setup"];
// LANG: the interface language; LANGUAGES: the language registry (GET /api/languages: code, native, english, flag,
// dir); UI_LANGS: the codes the interface can be shown in. A text that LANG has no translation for is shown in English.
let LANG = "tr", LANGUAGES = [], UI_LANGS = ["tr", "en"];
try { LANG = localStorage.getItem("mehteran.lang") || (navigator.language || "en").slice(0, 2).toLowerCase(); } catch { /* no storage */ }
let UI = {}, INFO = null, NODE_TYPES = {};  // NODE_TYPES: GET /api/node-types by type, in the server's order
const state = {tab: "", toolPoll: null, runPoll: null, signInUntil: 0, templates: [], tplQuery: "", tplCategory: "",
  runCanvas: null, selectedNode: null, hash: ""};

// --- helpers -------------------------------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);

// The strings come from the server (/api/strings). A missing one never shows as a raw key: the English text, else
// the key made readable, and a console warning (once per key).
const warned = new Set();
function S(key, values) {
  const entry = UI[key] || BOOT_TEXT[key];
  let text = entry && (entry[LANG] || entry.en);
  if (!text) {
    if (!warned.has(key)) { warned.add(key); console.warn(`Mehteran: no text for "${key}"`); }
    text = key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
  }
  for (const [k, v] of Object.entries(values || {})) text = text.split("{" + k + "}").join(v);
  return text;
}

// The only texts kept here: a server started before an update cannot serve them, and they say exactly that.
const BOOT_TEXT = {
  stale_title: {tr: "Mehteran güncellendi; bu pencerenin arkasındaki sunucu eski kodla çalışıyor.",
                en: "Mehteran was updated; the server behind this window still runs the old code."},
  stale_how: {tr: "Sunucunun terminal penceresini kapatın (ya da orada Ctrl+C), sonra yeniden başlatın: ./mehter ui (Windows: mehter ui) ya da \"Open Mehteran\". Ardından bu sayfayı yenileyin.",
              en: "Close the server's terminal window (or press Ctrl+C there), then start it again: ./mehter ui (Windows: mehter ui) or \"Open Mehteran\". Then reload this page."},
  stale_restart: {tr: "Yeniden başlat", en: "Restart"},
  stale_restarting: {tr: "Yeniden başlatılıyor…", en: "Restarting…"},
  stale_manual: {tr: "Bu sunucu kendini yeniden başlatamıyor; bir kez yukarıda yazıldığı gibi elle yeniden başlatın.",
                 en: "This server cannot restart itself; restart it once by hand as written above."},
};

function L(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value !== "object") return String(value);
  return value[LANG] || value.en || Object.values(value)[0] || "";  // a workflow text is a {tr, en} map: English for other languages
}

// --- languages: the registry, the names and the picker (langpicker.js) --------------------------------
const langInfo = (code) => LANGUAGES.find((lang) => lang.code === code);
const isLang = (code) => Boolean(langInfo(code));
// The texts of a workflow file are written in Turkish and English: the editor writes English for another language.
const textLang = () => (LANG === "tr" ? "tr" : "en");
// The name of a language in the interface language (the browser knows them); else its English name.
function langName(code) {
  try {
    const name = new Intl.DisplayNames([LANG], {type: "language"}).of(code);
    if (name && name !== code) return name;
  } catch { /* a browser without the names */ }
  return (langInfo(code) || {}).english || code;
}
// codes: the languages to offer, in that order (null: the whole registry).
function languagePicker({codes, value, label, onChange, id}) {
  return LangPicker.create({languages: codes ? codes.map(langInfo).filter(Boolean) : LANGUAGES, value, label, onChange, id,
    searchLabel: S("language_search"), emptyText: S("language_none"), otherName: langName});
}
// A choice input that asks for a language (every option is a language code): shown as the flag picker.
const isLanguageChoice = (spec) => spec.type === "choice" && /lang/i.test(spec.id) && spec.options.length > 1
  && spec.options.every((o) => isLang(typeof o === "string" ? o : o.value));

function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value == null || value === false) continue;
    if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (key === "class") el.className = value;
    else if (key === "value") el.value = value;
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.appendChild(typeof child === "string" || typeof child === "number" ? document.createTextNode(String(child)) : child);
  }
  return el;
}

// replaceChildren() would show null as the text "null": leave empty parts out.
function fill(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter((c) => c != null && c !== false));
}

async function api(method, path, body, raw) {
  const send = () => {
    const opts = {method, headers: {"X-Token": TOKEN, "X-Lang": LANG}};
    if (raw) opts.body = raw;
    else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
    return fetch(path, opts);
  };
  let res = await send();
  if (res.status === 403 && await refreshToken()) res = await send();
  const type = res.headers.get("Content-Type") || "";
  const data = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const error = new Error((data && data.error) || S("request_failed", {status: res.status}));
    error.problems = (data && data.problems) || [];
    error.status = res.status;
    throw error;
  }
  return data;
}

// After the interface was restarted, the page has an old session key: read the new one from the page itself.
async function refreshToken() {
  try {
    const html = await (await fetch("/", {cache: "no-store"})).text();
    const m = html.match(/<meta name="token" content="([^"]+)">/);
    if (!m || m[1] === TOKEN) return false;
    TOKEN = m[1];
    return true;
  } catch { return false; }
}

let toastTimer;
function toast(message, bad) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast" + (bad ? " bad" : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), bad ? 8000 : 4000);
}

async function act(button, fn) {
  if (button) button.disabled = true;
  try {
    const r = await fn();
    if (r && r.message) toast(r.message);
    return r;
  } catch (e) {
    toast(e.message, true);
    return null;
  } finally {
    if (button) button.disabled = false;
  }
}

function problemsBox(error) {
  const list = (error.problems && error.problems.length > 1) ? error.problems : [];
  return h("div", {class: "notice bad", role: "alert"}, h("b", {}, error.message),
    list.length ? h("ul", {class: "failures"}, list.map((p) => h("li", {}, typeof p === "string" ? p : p.message))) : null);
}

function fmtTime(epoch) {
  if (!epoch) return "–";
  const d = new Date(epoch * 1000);
  const time = d.toLocaleTimeString(LANG, {hour: "2-digit", minute: "2-digit"});
  return d.toDateString() === new Date().toDateString() ? time : `${d.toLocaleDateString(LANG)} ${time}`;
}

function duration(a, b) {
  if (!a) return "–";
  const s = Math.max(0, Math.round((b || Date.now() / 1000) - a));
  return s < 60 ? S("dur_s", {s}) : s < 3600 ? S("dur_ms", {m: Math.floor(s / 60), s: s % 60}) : S("dur_hm", {h: Math.floor(s / 3600), m: Math.floor(s % 3600 / 60)});
}

const STATUS_TONE = {succeeded: "good", failed: "bad", rejected: "bad", running: "warn", queued: "", waiting_approval: "warn", waiting_quota: "warn",
  cancelled: "warn", interrupted: "warn", skipped: "", pending: ""};
// A status word starts with a capital in a badge; in a sentence it stays as written.
const capital = (text) => text.charAt(0).toLocaleUpperCase(LANG) + text.slice(1);
const badge = (status) => h("span", {class: "badge " + (STATUS_TONE[status] || "")}, capital(S("status_" + status)));
const typeLabel = (type) => L(NODE_TYPES[type] && NODE_TYPES[type].label) || type;
const GLYPH = {"document.extract": "¶", "ai.cli": "✦", "text.merge": "⊕", "approval": "✓", "document.export": "⇩",
  "condition": "◇", "ai.map": "↻", "ai.agent": "◎", "share.x": "↗"};
// The second line of a box: the type and the id; only the id when the title already is the type.
const nodeSub = (n) => (L(n.label) && L(n.label) !== typeLabel(n.type) ? `${typeLabel(n.type)} · ${n.id}` : n.id);
// A branch port of a condition is shown as Yes / No (the port names stay true / false in the file).
// The other ports have a name too (text, comment, the file formats); a port without one shows as written.
const portLabel = (type, port) => (NODE_TYPES[type] && NODE_TYPES[type].branches && UI["branch_" + port] ? S("branch_" + port)
  : UI["port_" + port] ? S("port_" + port) : port);
const categoryLabel = (c) => (UI["category_" + c] ? S("category_" + c) : c || S("category_other"));
const fileUrl = (runId, rel, download) => `/api/runs/${runId}/files/${rel.split("/").map(encodeURIComponent).join("/")}?token=${encodeURIComponent(TOKEN)}` + (download ? "&download=1" : "");
const isEditorHash = (hash) => /^workflows\/(new|edit\/)/.test(hash || "");
const remember = (key, value) => { try { localStorage.setItem(key, value); } catch { /* no storage */ } };
const recall = (key) => { try { return localStorage.getItem(key); } catch { return null; } };

// --- frame: language, tabs and the address ------------------------------------------------------------
function applyStaticTexts() {
  document.documentElement.lang = LANG;
  document.documentElement.dir = (langInfo(LANG) || {}).dir || "ltr";
  document.title = S("app_title");
  const own = (sel) => document.querySelectorAll(sel);
  own("[data-i18n]").forEach((el) => (el.textContent = S(el.dataset.i18n)));
  own("[data-i18n-placeholder]").forEach((el) => (el.placeholder = S(el.dataset.i18nPlaceholder)));
  own("[data-i18n-label]").forEach((el) => el.setAttribute("aria-label", S(el.dataset.i18nLabel)));
  own("[data-i18n-title]").forEach((el) => el.setAttribute("title", S(el.dataset.i18nTitle)));
  fill($("#lang-switch"), languagePicker({codes: UI_LANGS, value: LANG, label: S("interface_language"), onChange: setLang, id: "ui-lang"}));
}

// A new interface language: its texts come from the server; the shown screen is drawn again.
async function setLang(lang) {
  LANG = lang;
  remember("mehteran.lang", LANG);
  try { UI = await api("GET", "/api/strings"); } catch (err) { toast(err.message, true); }
  applyStaticTexts();
  if (isEditorHash(state.hash) && Editor.dirty()) { Editor.relabel(); return; }
  route();
}

function go(hash) {
  if (location.hash === "#" + hash) route();
  else location.hash = hash;
}

// The first screen (and the brand link): Setup while the tools are not ready, else the tab used last.
function home() {
  if (!state.ready) return "setup";
  const last = recall("mehteran.tab");
  return TABS.includes(last) ? last : "workflows";
}

// Addresses of earlier versions, as parts of the current ones.
function current(parts) {
  const [first, ...rest] = parts;
  if (first === "templates") return ["workflows", ...rest];
  if (first === "translation") return ["workflows"];  // the book translation is no longer part of Mehteran
  if (first === "workflow") return !rest.length ? ["workflows"] : rest[0] === "new" ? ["workflows", "new"] : ["workflows", "edit", ...rest];
  return parts;
}

async function route() {
  let parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  // #runs/new/<source>/<id> of earlier versions: the Run section of the workflow's page
  if (parts[0] === "runs" && parts[1] === "new" && parts.length === 4) parts = ["workflows", parts[2], parts[3], "run"];
  parts = current(parts);
  if (parts[0] === "workflows" && parts[1] === "translation") parts = ["workflows"];
  if (!TABS.includes(parts[0])) parts = [home()];
  const hash = parts.map(encodeURIComponent).join("/");
  if (location.hash !== "#" + hash) history.replaceState(null, "", "#" + hash);
  // Leaving the editor with unsaved changes asks first; "no" puts the address back.
  if (isEditorHash(state.hash) && hash !== state.hash && window.Editor && Editor.dirty() && !confirm(S("confirm_discard"))) {
    history.replaceState(null, "", "#" + state.hash);
    return;
  }
  state.hash = hash;
  const tab = parts[0];
  state.tab = tab;
  remember("mehteran.tab", tab);
  const editing = isEditorHash(hash);
  document.body.classList.toggle("fill", editing);
  document.body.classList.toggle("editing", editing);
  clearTimeout(state.toolPoll);
  clearTimeout(state.runPoll);
  clearTimeout(state.localPoll);
  document.querySelectorAll(".tabs .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tab);
    t.setAttribute("aria-selected", String(t.dataset.tab === tab));
    t.tabIndex = t.dataset.tab === tab ? 0 : -1;
  });
  document.querySelectorAll("main > .panel").forEach((p) => (p.hidden = p.id !== tab));
  // null: not known yet in this browser (the first check of the tools answers in a few seconds): no banner until then
  $("#setup-banner").hidden = state.ready !== false || !(tab === "runs" || (tab === "workflows" && !editing));
  if (!(tab === "workflows" && parts[1] === "import")) closeDrawer();  // the drawer holds only the import now
  if (hash !== "workflows/new" && $("#new-dialog").open) $("#new-dialog").close();  // its name is asked only there
  try {
    if (tab === "setup") { loadLocal(); loadProviders(); loadBackground(); await loadTools(); }
    else if (tab === "runs") await showRuns(parts.slice(1));
    else await showWorkflows(parts.slice(1));
  } catch (err) {
    toast(err.message, true);
  }
}

// --- workflows: the library (cards), one workflow (drawer), import ----------------------------------------
async function loadTemplateList() {
  [state.templates, state.recentRuns] = await Promise.all([api("GET", "/api/templates"), api("GET", "/api/runs").catch(() => [])]);
  return state.templates;
}

// The workflows run last (from the run history), newest first; only those still in the library.
function recentTemplates(limit = 6) {
  const seen = new Set(), out = [];
  for (const run of state.recentRuns || []) {
    // a run of a merged template names its old id: the template lists it under "aliases"
    const item = (state.templates || []).find((t) => `${t.source}:${t.id}` === run.template
      || (t.source === "builtin" && (t.aliases || []).some((old) => `builtin:${old}` === run.template)));
    if (!item || !templateMatches(item) || seen.has(`${item.source}:${item.id}`)) continue;
    seen.add(`${item.source}:${item.id}`);
    out.push({item, at: run.created});
    if (out.length === limit) break;
  }
  return out;
}

function templateGroups(list) {
  const groups = new Map();
  for (const item of list) {
    const key = item.source === "user" ? "~mine" : (item.category || "~other");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  const order = [...groups.keys()].sort((a, b) => (a === "~mine" ? -1 : b === "~mine" ? 1 : categoryLabel(a).localeCompare(categoryLabel(b), LANG)));
  return order.map((key) => ({key, label: key === "~mine" ? S("my_templates") : key === "~other" ? S("category_other") : categoryLabel(key),
    items: groups.get(key).sort((a, b) => (L(a.name) || a.id).localeCompare(L(b.name) || b.id, LANG))}));
}

// Search ignores case and accents, also the Turkish ones: "is plani" finds "İş planı", "sozlesme" finds "Sözleşme".
function fold(text) {
  return String(text).replace(/[İIı]/g, "i").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function templateMatches(item) {
  const q = fold(state.tplQuery.trim());
  if (state.tplOnly && !(item.source === "builtin" && state.tplOnly.ids.includes(item.id))) return false;  // a welcome choice
  if (state.tplCategory === "~fav" ? !item.favorite : state.tplCategory === "~mine" ? item.source !== "user"
    : state.tplCategory && item.category !== state.tplCategory) return false;
  if (!q) return true;
  const both = (value) => (typeof value === "object" && value ? Object.values(value) : [value || ""]);  // tr and en
  const text = fold([item.id, item.category, categoryLabel(item.category), ...both(item.name), ...both(item.description)].join(" "));
  return q.split(/\s+/).every((word) => text.includes(word));
}

async function showWorkflows(parts) {
  const editing = parts[0] === "new" || (parts[0] === "edit" && parts.length === 3);
  const page = !editing && parts.length >= 2 && ["builtin", "user"].includes(parts[0]);
  $("#library").hidden = editing || page;
  $("#workflow-editor").hidden = !editing;
  $("#workflow-page").hidden = !page;
  if (editing) return Editor.open(parts[0] === "new" ? ["new"] : parts.slice(1));
  if (page) {
    if (!state.templates.length) fill($("#wf-body"), skeleton("cards"));  // live.js: shapes until the list comes
    await loadTemplateList();  // the favorite star and the title come from the list
    return showWorkflowPage(parts[0], parts[1], parts[2]);
  }
  if (!state.templates.length) fill($("#template-grid"), skeleton("cards"));  // live.js: shapes until the list comes
  Drafter.box();  // editor.js: "Describe it, I will build it", the first thing of the library
  await loadTemplateList();
  renderLibrary();
  showWelcome();  // the first-start welcome, above the library
  if (parts[0] === "import") return openDrawer(importView());
}

// The library has two views: "mine" (own workflows, drafts, favorites, the workflows run last) and "all" (the
// templates: a "start here" group, then one group per category). The first view is "mine"
// once there is anything of the user's own, else "all"; the choice is kept for the session.
function hasOwnWork() {
  return state.templates.some((t) => t.source === "user" || t.favorite) || (state.recentRuns || []).length > 0;
}

// "1 document · 2 model calls": what a run of the workflow asks for, from its file (docs, calls, loops, branches).
function needsLine(item) {
  if (!item.valid) return S("problems_found", {count: (item.problems || []).length});
  const parts = [item.docs ? S(item.docs === 1 ? "needs_doc_one" : "needs_doc_many", {count: item.docs}) : S("needs_text")];
  if (item.calls) parts.push(S(item.branches ? "needs_calls_max" : item.calls === 1 ? "needs_call_one" : "needs_calls_many", {count: item.calls}));
  if (item.loops) parts.push(S("needs_loop"));
  return parts.join(" · ");
}

function renderLibrary() {
  if (!state.libView) state.libView = hasOwnWork() ? "mine" : "all";
  const view = state.libView;
  const categories = [...new Set(state.templates.filter((t) => t.source === "builtin").map((t) => t.category || ""))]
    .sort((a, b) => categoryLabel(a).localeCompare(categoryLabel(b), LANG));
  const chip = (value, label, count) => h("button", {type: "button", class: "pick", "aria-pressed": String(state.tplCategory === value && !state.tplOnly),
    onclick: () => { state.tplCategory = value; state.tplOnly = null; renderLibrary(); }}, label, h("span", {class: "count"}, " " + count));
  const tab = (value, label) => h("button", {type: "button", class: "pick view-tab", "aria-pressed": String(view === value),
    onclick: () => { state.libView = value; state.tplCategory = ""; state.tplOnly = null; renderLibrary(); }}, label);
  const builtin = state.templates.filter((t) => t.source === "builtin");
  const categoriesOpen = Boolean(state.libCategories);
  const categoryList = h("div", {id: "category-list", class: "pick-chips cat-filter", role: "group",
    hidden: !categoriesOpen, "aria-label": S("filter_category")},
    chip("", S("all"), state.templates.length),
    categories.map((c) => chip(c, categoryLabel(c), builtin.filter((t) => t.category === c).length)),
    state.tplOnly ? h("button", {type: "button", class: "pick", "aria-pressed": "true",
      onclick: () => { state.tplOnly = null; renderLibrary(); }}, state.tplOnly.label, h("span", {class: "count"}, " ✕")) : null);
  fill($("#template-filters"), h("div", {class: "pick-chips view-switch", role: "group", "aria-label": S("library_view")},
    tab("mine", S("view_mine")), tab("all", S("view_templates")),
    view === "all" ? h("button", {type: "button", class: "btn small", "aria-expanded": String(categoriesOpen),
      "aria-controls": "category-list", onclick: (e) => {
        state.libCategories = categoryList.hidden;
        categoryList.hidden = !state.libCategories;
        e.currentTarget.setAttribute("aria-expanded", String(state.libCategories));
      }}, S("filter_category")) : null), view === "all" ? categoryList : null);
  $("#template-search").value = state.tplQuery;
  const searching = Boolean(state.tplQuery.trim());
  const group = (cls, title, items, extra) => h("section", {class: "lib-group " + cls}, h("h3", {class: "lib-group-title"}, title,
    h("span", {class: "muted small"}, S(state.libView === "mine" ? "count_workflows" : "count_templates", {count: items.length}))), extra || null, h("div", {class: "lib-grid"}, items.map((x) => (typeof x === "function" ? x() : templateCard(x)))));
  const sections = [];
  let total = 0;
  if (view === "mine") {
    const match = state.templates.filter(templateMatches);
    const favs = match.filter((t) => t.favorite), own = match.filter((t) => t.source === "user" && !t.draft && !t.favorite);
    const drafts = match.filter((t) => t.source === "user" && t.draft && !t.favorite);
    const recent = recentTemplates();
    total = recent.filter(({item}) => item.source !== "user" && !item.favorite).length;
    if (favs.length) { sections.push(group("lib-favorites", "★ " + S("favorites"), favs)); total += favs.length; }
    // Like the cards: "Open" goes to the workflow's page, where it is run.
    if (recent.length) sections.push(h("section", {class: "lib-recent"}, h("h3", {class: "lib-group-title"}, S("recently_used")),
      h("div", {class: "recent-row"}, recent.map(({item, at}) => {
        const open = () => go(`workflows/${item.source}/${item.id}`), name = L(item.name) || item.id;
        return h("span", {class: "recent-chip"},
          h("button", {type: "button", class: "linkish", onclick: open}, name, h("span", {class: "small muted"}, " · " + fmtTime(at))),
          h("button", {type: "button", class: "btn small", onclick: open, "aria-label": S("open") + ": " + name}, S("open")));
      }))));
    if (own.length) { sections.push(group("", S("my_templates"), own)); total += own.length; }
    if (drafts.length) { sections.push(group("", S("drafts"), drafts)); total += drafts.length; }
    if (!sections.length) sections.push(h("div", {class: "empty"}, searching ? S("no_templates_match") : S("mine_empty"),
      searching ? null : h("div", {class: "row"}, h("button", {type: "button", class: "btn small primary", onclick: () => { state.libView = "all"; renderLibrary(); }}, S("view_templates")))));
  } else {
    const visible = state.templates.filter(templateMatches);
    const plain = !state.tplCategory && !searching && !state.tplOnly;
    const start = plain ? state.templates.filter((t) => t.tier === "core" && t.source === "builtin") : [];
    if (start.length) sections.push(group("lib-start", S("start_here"), start));  // not counted: they are also in their category
    for (const g of templateGroups(visible)) { sections.push(group("", g.label, g.items)); total += g.items.length; }
    if (!visible.length && !sections.length) sections.push(h("div", {class: "empty"}, S("no_templates_match")));
  }
  // An empty "My workflows" view says so in its own box; "0 templates" next to it would only add noise.
  $("#library-count").textContent = view === "mine" && !total ? "" : S(view === "mine" ? "count_workflows" : "count_templates", {count: total});
  fill($("#template-grid"), ...sections);
  staggerOnce($("#template-grid"));  // live.js: the cards come in one after the other, the first time
}


// The same buttons on every card of the library: the star, "Edit" (the workflow's steps and instructions) and "Open"
// (the workflow's page; a run starts there). Running is never a card button, so every card reads the same way.
function cardActions(star, edit, open, name) {
  return h("span", {class: "row"}, star,
    h("button", {type: "button", class: "btn small", onclick: edit, "aria-label": S("edit") + ": " + name}, S("edit")),
    h("button", {type: "button", class: "btn small primary", onclick: open, "aria-label": S("open") + ": " + name}, S("open")));
}


function templateCard(item) {
  const open = () => go(`workflows/${item.source}/${item.id}`);
  const kind = item.source === "user" ? "mine" : item.category || "other";
  return h("article", {class: `tpl-card cat-${kind}`},
    h("button", {type: "button", class: "tpl-open", onclick: open, "aria-label": S("details_of", {name: L(item.name) || item.id})},
      // The group heading names the category of a built-in; one of your own shows its category here.
      h("span", {class: "tpl-head"}, iconTile(kind), h("span", {class: "tpl-badges"},
        item.draft ? h("span", {class: "badge warn"}, S("draft")) : null,
        item.tier === "experimental" ? h("span", {class: "badge warn", title: S("experimental_note")}, S("experimental")) : null,
        item.source === "user" && item.category ? h("span", {class: "badge"}, categoryLabel(item.category)) : null,
        item.valid || item.draft ? null : h("span", {class: "badge bad"}, S("invalid")))),
      h("span", {class: "tpl-name"}, L(item.name) || item.id),
      h("span", {class: "tpl-desc"}, L(item.description) || item.id)),
    h("div", {class: "tpl-foot"},
      h("span", {class: "small muted"}, needsLine(item)),
      cardActions(favoriteButton(item, renderLibrary),  // live.js
        () => go(`workflows/edit/${item.source}/${item.id}`), open, L(item.name) || item.id)));
}

// --- the first-start welcome: three choices above the library, until something was run or it was closed ----------
// GET /api/welcome says whether to show it and which providers each choice needs (PUT /api/welcome closes it for
// good; the server keeps that, so it holds for every browser). The state of the tools is the Setup tab's data
// (GET /api/tools); the install and sign-in buttons call the Setup tab's own addresses.
const welcome = {data: null, tools: null, toolsAt: 0, poll: null};

async function showWelcome() {
  const panel = $("#welcome-panel");
  if (!welcome.data || welcome.data.show) {  // asked again while it shows: a first run closes it
    try { welcome.data = await api("GET", "/api/welcome"); } catch { return; }
  }
  panel.hidden = !welcome.data.show;
  if (!welcome.data.show) { clearTimeout(welcome.poll); return; }
  drawWelcome();
  if (Date.now() - welcome.toolsAt > 10000) loadWelcomeTools();
}

async function loadWelcomeTools() {
  clearTimeout(welcome.poll);
  welcome.toolsAt = Date.now();
  try { welcome.tools = await api("GET", "/api/tools"); } catch { return; }
  if (!welcome.data || !welcome.data.show || state.tab !== "workflows") return;
  setReady(toolsReady(welcome.tools));
  drawWelcome();
  // As the Setup tab: often while an install runs, for two minutes after a sign-in was started.
  const busy = welcome.tools.tools.some((tool) => tool.job && tool.job.running);
  const watching = state.signInUntil > Date.now() && welcome.tools.tools.some((tool) => tool.installed && !tool.signed_in);
  if (busy || watching) welcome.poll = setTimeout(loadWelcomeTools, busy ? 2500 : 4000);
}

// One tool of a choice: its name, its state, and the next step right there (install, sign in) when it is not ready.
function welcomeTool(tool, terminal) {
  const id = encodeURIComponent(tool.id), job = tool.job, running = Boolean(job && job.running);
  let mark, action = null;
  if (!tool.installed) {
    mark = h("span", {class: "badge bad"}, S("not_installed"));
    action = h("button", {type: "button", class: "btn small primary", disabled: running, onclick: async (e) => {
      await act(e.currentTarget, () => api("POST", `/api/tools/${id}/install`));
      loadWelcomeTools();
    }}, S(running ? "installing" : "install"));
  } else if (!tool.signed_in) {
    mark = h("span", {class: "badge warn"}, S("not_signed_in"));
    const method = tool.id === "gemini" ? "google" : terminal ? "terminal" : "";  // an API key: on the Setup tab
    action = method ? h("button", {type: "button", class: "btn small primary", onclick: async (e) => {
      const r = await act(e.currentTarget, () => api("POST", `/api/tools/${id}/login`, {method}));
      if (r) state.signInUntil = Date.now() + 10 * 60 * 1000;
      loadWelcomeTools();
    }}, S("welcome_sign_in")) : null;
  } else mark = h("span", {class: "badge good"}, S("welcome_tool_ready"));
  return h("div", {class: "welcome-tool"}, h("span", {class: "welcome-tool-name"}, tool.name), mark, action,
    job && !running && job.code !== 0 ? h("span", {class: "small warn-text"}, S("welcome_install_failed")) : null);
}

function welcomeTools(providers) {
  const data = welcome.tools;
  if (!data) return h("div", {class: "welcome-tools"}, h("p", {class: "small muted"}, S("welcome_checking")));
  const tools = providers.map((p) => data.tools.find((tool) => tool.provider === p) || p);
  const ready = tools.every((tool) => typeof tool === "string" || (tool.installed && tool.signed_in));
  return h("div", {class: "welcome-tools"}, h("span", {class: "small fld-label"}, S("welcome_needs")),
    tools.length ? tools.map((tool) => (typeof tool === "string"  // a provider without a tool of its own (a local model)
      ? h("div", {class: "welcome-tool"}, h("span", {class: "welcome-tool-name"}, tool), localTag((INFO.providers || []).find((p) => p.name === tool)))
      : welcomeTool(tool, data.terminal)))
      : h("p", {class: "small muted"}, S("welcome_no_tool")),
    ready && tools.length ? null : h("button", {type: "button", class: "linkish small welcome-setup", onclick: () => go("setup")}, S("welcome_setup_link")));
}

// A choice's icon (a category's, live.js) and its texts.
function welcomeText(id) {
  return {
    document: ["documents", S("welcome_document_title"), S("welcome_document_text"), S("welcome_document_go")],
    writing: ["writing", S("welcome_writing_title"), S("welcome_writing_text"), S("welcome_show_go")],
    data: ["data", S("welcome_data_title"), S("welcome_data_text"), S("welcome_show_go")],
    education: ["education", S("welcome_education_title"), S("welcome_education_text"), S("welcome_show_go")],
    research: ["research", S("welcome_research_title"), S("welcome_research_text"), S("welcome_show_go")],
  }[id];
}

// What a choice does: the run window of its template or the library filtered to its workflows.
function welcomeGo(choice, title) {
  if (choice.action === "run") return openRun("builtin", choice.templates[0]);
  state.tplQuery = "";
  state.libView = "all";
  state.tplCategory = choice.action === "category" ? choice.category : "";
  state.libCategories = true;
  state.tplOnly = choice.action === "templates" ? {ids: choice.templates, label: title} : null;
  renderLibrary();
  $(".lib-tools").scrollIntoView({behavior: calm() ? "auto" : "smooth", block: "start"});
}

function drawWelcome() {
  const panel = $("#welcome-panel");
  const card = (choice) => {
    const text = welcomeText(choice.id);
    if (!text) return null;
    const [kind, title, about, label] = text;
    return h("article", {class: `tpl-card welcome-card cat-${kind}`},
      h("div", {class: "welcome-main"}, h("span", {class: "tpl-head"}, iconTile(kind), h("h4", {class: "tpl-name"}, title)),
        h("p", {class: "tpl-desc"}, about)),
      welcomeTools(choice.providers),
      h("div", {class: "tpl-foot"}, h("span", {class: "small muted"}, choice.templates.length > 1 ? S("count_templates", {count: choice.templates.length}) : ""),
        h("div", {class: "row"},
          // A first try without looking for a file: the run form opens with a short sample document in it.
          choice.id === "document" && choice.action === "run" ? h("button", {type: "button", class: "btn small", onclick: () => {
            state.sampleRun = true;
            welcomeGo(choice, title);
          }}, S("welcome_sample")) : null,
          h("button", {type: "button", class: "btn small primary", onclick: () => welcomeGo(choice, title)}, label))));
  };
  fill(panel,
    h("div", {class: "welcome-head"},
      h("div", {}, h("h3", {id: "welcome-title"}, S("welcome_title")), h("p", {class: "muted"}, S("welcome_intro"))),
      h("button", {type: "button", class: "btn small", onclick: async (e) => {
        if (!await act(e.currentTarget, () => api("PUT", "/api/welcome", {dismissed: true}))) return;
        welcome.data = {show: false};
        clearTimeout(welcome.poll);
        panel.hidden = true;
      }}, S("welcome_dismiss"))),
    h("div", {class: "welcome-grid"}, welcome.data.choices.map(card)));
}

// The drawer: one workflow, or the import form. Closing it (Esc, the close button) goes back to the library.
function openDrawer(...content) {
  const drawer = $("#drawer");
  fill($("#drawer-body"), content);
  if (!drawer.open) drawer.showModal();
  $("#drawer-body").scrollTop = 0;
}

function closeDrawer() {
  if ($("#drawer").open) $("#drawer").close();
}

// --- one workflow's page: ← Workflows, its icon and name, its sections ------------------------------------------
// Run: the run form in place (runForm). Instructions: the steps in plain words, each AI step with its instruction
// (editable on the user's own workflows), the diagram and the YAML folded. Runs: this workflow's runs. Beside the
// sections: the favorite star and "⋯" (open in the editor, duplicate, YAML, share, delete).
// The address names the section: #workflows/<source>/<id>/<run|steps|runs> ("about" of earlier versions: steps).
const WF_TABS = ["run", "steps", "runs"];
const WF_TAB_LABEL = {run: "run", steps: "wf_steps", runs: "tab_runs"};

async function showWorkflowPage(source, id, tab) {
  if (!WF_TABS.includes(tab)) {
    tab = tab === "about" ? "steps" : "run";
    history.replaceState(null, "", `#workflows/${source}/${id}/${tab}`);
    state.hash = `workflows/${source}/${id}/${tab}`;
  }
  const item = state.templates.find((t) => t.source === source && t.id === id) || {source, id};
  fill($("#wf-page-title"), iconTile(source === "user" ? "mine" : item.category || "other"), h("b", {}, L(item.name) || id));
  fill($("#wf-tabs"), WF_TABS.map((t) => h("button", {type: "button", role: "tab", class: "subtab" + (t === tab ? " active" : ""),
    "aria-selected": String(t === tab), onclick: () => go(`workflows/${source}/${id}/${t}`)}, S(WF_TAB_LABEL[t]))));
  const body = $("#wf-body");
  const key = `${source}/${id}`;
  if (body.dataset.key !== `${key}/${tab}`) fill(body, h("p", {class: "muted"}, S("loading")));
  if (($("#wf-extra").dataset.key || "") !== key) { fill($("#wf-extra")); fill($("#wf-actions")); }
  body.dataset.key = `${key}/${tab}`;
  let tpl;
  try { tpl = await api("GET", `/api/templates/${source}/${id}`); }
  catch (err) { return fill(body, problemsBox(err)); }
  if (state.hash !== `workflows/${source}/${id}/${tab}`) return;
  wfActions(tpl, source, id, item);
  if (tab === "runs") return fill(body, await workflowRuns(source, id));
  if (tab === "steps") return fill(body, h("div", {class: "wf-steps"}, stepsSection(tpl, source, id)));
  const steps = Array.isArray(tpl.model && tpl.model.nodes) ? tpl.model.nodes.length : 0;
  const built = state.built === key && source === "user" ? builtCard(tpl, source, id)
    : steps ? h("p", {class: "small wf-steps-line"}, S("steps_count", {count: steps}), " · ",
      h("button", {type: "button", class: "linkish", onclick: () => go(`workflows/${source}/${id}/steps`)}, S("view_instructions"))) : null;
  const experimental = item.tier === "experimental" ? h("p", {class: "notice warn small"}, h("b", {}, S("experimental")), " · ", S("experimental_note")) : null;
  fill(body, experimental, built, tpl.valid ? runForm(tpl, source, id)
    : [problemsBox({message: S(tpl.draft ? "draft_cannot_run" : "template_invalid", {count: (tpl.problems || []).length}), problems: tpl.problems || []}),
      h("button", {type: "button", class: "btn", onclick: () => go(`workflows/edit/${source}/${id}`)}, S("edit"))]);
}

// The star and the "⋯" menu beside the sections; the share box opens below the bar (#wf-extra).
function wfActions(tpl, source, id, item) {
  $("#wf-extra").dataset.key = `${source}/${id}`;
  const share = tpl.valid ? shareBox(source, id) : null;  // history.js
  if (share) fill($("#wf-extra"), share.box);
  const close = () => { menu.open = false; };
  const entry = (label, onclick, cls) => h("button", {type: "button", role: "menuitem", class: "menu-item" + (cls ? " " + cls : ""), onclick: (e) => { close(); onclick(e); }}, label);
  const menu = h("details", {class: "wf-more"},
    h("summary", {class: "btn small", "aria-label": S("wf_more"), title: S("wf_more")}, "⋯"),
    h("div", {class: "menu card", role: "menu"},
      entry(S("open_visual_editor"), () => go(`workflows/edit/${source}/${id}`)),
      entry(S("duplicate"), () => duplicateWorkflow(source, id)),
      h("a", {class: "menu-item", role: "menuitem", href: `/api/templates/${source}/${id}/download?token=${encodeURIComponent(TOKEN)}`, onclick: close}, S("export_yaml")),
      share ? entry(S("share"), () => { share.box.hidden = false; $("input", share.box).focus(); }) : null,
      source === "user" ? entry(S("delete"), async () => {
        if (!confirm(S("confirm_delete", {id}))) return;
        if (await act(null, () => api("DELETE", `/api/templates/user/${id}`))) { toast(S("deleted")); go("workflows"); }
      }, "danger") : null));
  document.addEventListener("click", (e) => { if (!menu.contains(e.target)) close(); });
  fill($("#wf-actions"), favoriteButton({...item, source, id, name: tpl.name}, () => wfActions(tpl, source, id, {...item, favorite: !item.favorite})), menu);  // live.js
}

// A copy of a workflow among the user's own, under the first free "<id>-copy" name; its Instructions open.
async function duplicateWorkflow(source, id) {
  const taken = new Set(state.templates.filter((t) => t.source === "user").map((t) => t.id));
  let copy = `${id}-copy`;
  for (let k = 2; taken.has(copy); k++) copy = `${id}-copy-${k}`;
  const r = await act(null, () => api("POST", `/api/templates/${source}/${id}/customize`, {id: copy}));
  if (r) { toast(S("customized", {id: r.id})); await loadTemplateList(); go(`workflows/user/${r.id}/steps`); }
}

// The Instructions section: the description, the steps, then the editor link, the diagram and the YAML (folded).
function stepsSection(tpl, source, id) {
  const graph = tpl.graph ? previewCanvas(tpl.graph) : null;
  return [
    tpl.description ? h("p", {class: "muted wf-desc"}, L(tpl.description)) : null,
    tpl.valid ? null : problemsBox({message: S(tpl.draft ? "draft_cannot_run" : "template_invalid", {count: tpl.problems.length}), problems: tpl.problems}),
    source === "builtin" ? h("p", {class: "small muted"}, S("builtin_edit_note")) : null,
    stepsList(tpl, source, id),
    h("div", {class: "row"}, h("button", {type: "button", class: "btn", onclick: () => go(`workflows/edit/${source}/${id}`)}, S("open_visual_editor"))),
    graph ? h("details", {class: "drawer-sec", ontoggle: (e) => { if (e.currentTarget.open) graph.fit(); }}, h("summary", {}, S("graph")), graph) : null,
    h("details", {class: "drawer-sec placeholders"}, h("summary", {}, S("yaml_source")),
      source === "user" ? yamlEditor(tpl.yaml, id) : h("pre", {class: "code"}, tpl.yaml))];
}

// The steps of a workflow in plain words, numbered. An AI step shows its instruction (three lines, then "more");
// on the user's own workflow it can be edited in place and saved (PUT /api/templates/user/<id>/model).
const instructionKey = (n) => (!n || typeof n.config !== "object" || !n.config ? null : typeof n.config.prompt === "string" ? "prompt"
  : n.type === "condition" && n.config.operator === "ai" && typeof n.config.question === "string" ? "question" : null);

async function saveWorkflowModel(id, model) {
  const res = await api("PUT", `/api/templates/user/${id}/model`, {model});
  // only an instruction changed: no comment can be lost, but the server asks when one would be
  return res.saved ? res : api("PUT", `/api/templates/user/${id}/model`, {model, drop_comments: true});
}

function stepsList(tpl, source, id) {
  const steps = (Array.isArray(tpl.model && tpl.model.nodes) ? tpl.model.nodes : []).filter((n) => n && typeof n === "object");
  const editable = source === "user";
  const instruction = (n, key) => {
    const box = h("div", {class: "step-instr"});
    const show = () => {
      const text = String(n.config[key] || "");
      const p = h("p", {class: "step-text clamp"}, text || S("instruction_empty"));
      const more = h("button", {type: "button", class: "linkish small", hidden: true, "aria-expanded": "false", onclick: () => {
        const open = p.classList.toggle("clamp") === false;
        more.textContent = S(open ? "show_less" : "show_more");
        more.setAttribute("aria-expanded", String(open));
      }}, S("show_more"));
      requestAnimationFrame(() => { more.hidden = p.scrollHeight <= p.clientHeight + 2; });
      fill(box, p, h("div", {class: "row step-acts"}, more,
        editable ? h("button", {type: "button", class: "linkish small", onclick: edit}, S("edit_instruction")) : null));
    };
    const edit = () => {
      const area = h("textarea", {rows: 8, "aria-label": S("instruction_of", {step: L(n.label) || n.id})});
      area.value = String(n.config[key] || "");
      const result = h("div", {"aria-live": "polite"});
      const save = async (e) => {
        if (area.value === String(n.config[key] || "")) return show();
        const before = n.config[key];
        n.config[key] = area.value;
        if (await act(e.currentTarget, () => saveWorkflowModel(id, tpl.model))) { toast(S("saved")); show(); }
        else n.config[key] = before;
      };
      fill(box, area, h("div", {class: "row"}, h("button", {type: "button", class: "btn small primary", onclick: save}, S("save")),
        h("button", {type: "button", class: "btn small", onclick: show}, S("cancel_action"))), result);
      area.focus();
    };
    show();
    return box;
  };
  return h("ol", {class: "steps-list"}, steps.map((n, i) => {
    const key = instructionKey(n);
    return h("li", {class: "step-item" + (key ? " has-instr" : "")},
      h("span", {class: "step-n", "aria-hidden": "true"}, String(i + 1)),
      h("div", {class: "step-main"},
        h("div", {class: "step-head"}, h("b", {}, L(n.label) || n.id), h("span", {class: "small muted"}, (GLYPH[n.type] ? GLYPH[n.type] + " " : "") + typeLabel(n.type))),
        key ? instruction(n, key) : null));
  }));
}

// "Here is what I built": the first view of a workflow that "Describe it" built (state.built), above its run form.
// The steps with their instructions, a change in one sentence (the model writes the workflow again), keep or delete.
function builtCard(tpl, source, id) {
  const change = h("input", {type: "text", maxlength: 1000, placeholder: S("built_change_placeholder"), "aria-label": S("built_change")});
  const progress = h("div", {class: "built-progress", "aria-live": "polite"});
  const keep = () => { state.built = null; showWorkflowPage(source, id, "run"); };
  return h("section", {class: "card built-card", "aria-labelledby": "built-title"},
    h("div", {class: "built-head"}, h("h3", {id: "built-title"}, S("built_title")), h("p", {class: "small muted"}, S("built_intro"))),
    stepsList(tpl, source, id),
    h("form", {class: "row built-change", onsubmit: (e) => {
      e.preventDefault();
      if (change.value.trim()) Drafter.change(tpl, id, change.value.trim(), progress, async () => { await loadTemplateList(); showWorkflowPage(source, id, "run"); });
    }}, change, h("button", {type: "submit", class: "btn"}, "✦ " + S("built_change"))),
    progress,
    h("div", {class: "row built-acts"},
      h("button", {type: "button", class: "btn primary", onclick: keep}, S("built_ok")),
      h("button", {type: "button", class: "btn danger", onclick: async (e) => {
        if (!confirm(S("confirm_delete", {id}))) return;
        if (await act(e.currentTarget, () => api("DELETE", `/api/templates/user/${id}`))) { state.built = null; toast(S("deleted")); go("workflows"); }
      }}, S("delete"))));
}

// The runs of one workflow, newest first: the rows of the Runs tab.
async function workflowRuns(source, id) {
  const runs = (await api("GET", "/api/runs")).filter((r) => r.template === `${source}:${id}`);
  if (!runs.length) return h("div", {class: "empty"}, S("wf_no_runs"),
    h("div", {class: "row"}, h("button", {type: "button", class: "btn small primary", onclick: () => go(`workflows/${source}/${id}/run`)}, "▶ " + S("run"))));
  const refresh = () => showWorkflowPage(source, id, "runs");
  return h("div", {class: "book-list wf-runs"}, h("ul", {}, runs.map((r) => historyRow(r, null, refresh))));  // history.js: the Runs tab's rows
}

// A read-only drawing of a template or run: the editor's canvas without editing.
function graphView(graph, statuses) {
  const ports = Object.fromEntries(graph.nodes.map((n) => [n.id, n.ports || []]));
  const nodes = graph.nodes.map((n) => ({id: n.id, type: n.type, title: L(n.label) || n.id, sub: nodeSub(n),
    glyph: GLYPH[n.type], ports: ports[n.id], status: statuses ? statuses[n.id] || "pending" : "", x: 0, y: 0}));
  const edges = graph.edges.map((e, index) => ({...e, index}));
  const auto = autoLayout(nodes, edges);
  for (const n of nodes) Object.assign(n, (graph.layout && graph.layout[n.id]) || auto[n.id]);
  return {nodes, edges};
}

function previewCanvas(graph) {
  const canvas = new GraphCanvas({labels: {status: (s) => S("status_" + s), port: portLabel}, onSelect: () => {}, minFit: 0.45});  // a preview shows it all
  canvas.el.classList.add("small-canvas");
  canvas.setView(graphView(graph));
  requestAnimationFrame(() => canvas.fit());
  canvas.el.fit = () => requestAnimationFrame(() => canvas.fit());  // drawn again when a folded box opens
  return canvas.el;
}

function yamlEditor(text, id) {
  const area = h("textarea", {class: "code", spellcheck: "false", autocapitalize: "off", autocomplete: "off", rows: 24, "aria-label": S("yaml_source")});
  area.value = text;
  const result = h("div", {"aria-live": "polite"});
  const save = async () => {
    try {
      await api("PUT", `/api/templates/user/${id}`, {yaml: area.value});
      result.replaceChildren(h("p", {class: "good-text"}, "✓ " + S("saved")));
      toast(S("saved"));
    } catch (err) {
      result.replaceChildren(problemsBox(err), err.status === 400 ? h("button", {type: "button", class: "btn", onclick: async () => {
        try {
          await api("PUT", `/api/templates/user/${id}/draft`, {yaml: area.value});
          toast(S("saved_draft"));
          go(`workflows/user/${id}/steps`);
        } catch (e) { result.replaceChildren(problemsBox(e)); }
      }}, S("save_as_draft")) : null);
    }
  };
  area.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
    if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); area.setRangeText("  ", area.selectionStart, area.selectionEnd, "end"); }
  });
  return h("div", {class: "stack"}, h("p", {class: "small muted"}, S("yaml_editor_hint")), area,
    h("div", {class: "row"}, h("button", {type: "button", class: "btn", onclick: async () => {
      const res = await api("POST", "/api/validate", {yaml: area.value});
      result.replaceChildren(res.valid ? h("p", {class: "good-text"}, "✓ " + S("valid")) : problemsBox({message: S("problems_found", {count: res.problems.length}), problems: res.problems}));
    }}, S("validate")), h("button", {type: "button", class: "btn primary", onclick: save}, S("save"))), result);
}

// text: the YAML to show again (the preview's "Back"). A file chosen here, or dropped on the library
// (state.importText), opens the preview first (history.js: showImportPreview); "Import" there adds it.
function importView(text) {
  const area = h("textarea", {class: "code", spellcheck: "false", rows: 18, "aria-label": S("yaml_source")});
  if (typeof text === "string") area.value = text;
  const result = h("div", {"aria-live": "polite"});
  const picker = h("input", {type: "file", accept: ".yaml,.yml", "aria-label": S("import_file"), onchange: async () => {
    const file = picker.files[0];
    if (file) { area.value = await file.text(); showImportPreview(area.value); }
  }});
  if (state.importText) {
    const dropped = state.importText;
    state.importText = null;
    setTimeout(() => showImportPreview(dropped));
  }
  return [h("div", {class: "drawer-head"}, h("h2", {id: "drawer-title"}, S("import_title")),
    h("button", {type: "button", class: "icon-btn drawer-x", "aria-label": S("close"), title: S("close"), onclick: () => go("workflows")}, "✕")),
  h("p", {class: "muted small"}, S("import_lede")),
  h("div", {class: "uploader"}, filePicker(picker, false)), area,
  h("div", {class: "row"},
    h("button", {type: "button", class: "btn", onclick: async () => {
      const res = await api("POST", "/api/validate", {yaml: area.value});
      result.replaceChildren(res.valid ? h("p", {class: "good-text"}, "✓ " + S("valid")) : problemsBox({message: S("problems_found", {count: res.problems.length}), problems: res.problems}));
    }}, S("validate")),
    h("button", {type: "button", class: "btn primary", onclick: () => {
      if (!area.value.trim()) return result.replaceChildren(h("p", {class: "small warn-text"}, S("import_empty")));
      showImportPreview(area.value);
    }}, S("preview_open"))), result];
}

// --- the run dialog: every input of a workflow, then the run starts and its page opens -----------------
// --- stream P: the model picker (`auto` and each tool with its state), the providers' Setup panel -----------------
// GET /api/providers: each tool's state, billing and calls at once, the model order, what each `auto` kind uses now.
const AUTO_KINDS = ["auto", "auto:fast", "auto:strong", "auto:local"];
const providerStates = {data: null, at: 0, loading: null};

async function loadProviderStates(force) {
  if (!force && providerStates.data && Date.now() - providerStates.at < 20000) return providerStates.data;
  if (!providerStates.loading) {
    providerStates.loading = api("GET", "/api/providers").then((data) => { providerStates.data = data; providerStates.at = Date.now(); return data; })
      .catch(() => providerStates.data).finally(() => { providerStates.loading = null; });
  }
  return providerStates.loading;
}

const providerInfo = (name) => ((providerStates.data && providerStates.data.providers) || []).find((p) => p.name === name) || null;
const autoChoice = (kind) => (providerStates.data && providerStates.data.auto && providerStates.data.auto[kind]) || null;
const canonicalProvider = (name) => (name === "chatgpt" ? "codex" : name);  // an older name for Codex
// Green means only "signed in" or "installed"; how a tool is paid is plain text, a paid API key the one caution.
const BILLING_LEVEL = {api_key: "warn"};
const billingBadge = (billing) => (billing ? h("span", {class: "badge billing " + (BILLING_LEVEL[billing] || "")}, S("billing_" + billing)) : null);

function providerField(spec) {
  const providers = (INFO && INFO.providers) || [];
  const def = typeof spec.default === "string" ? spec.default : "";
  const [defBase, defEffort = ""] = def.split("@");
  const defProvider = canonicalProvider(defBase.split("/")[0]), defModel = defBase.split("/").slice(1).join("/");
  const label = (p) => {
    const st = providerInfo(p.name);
    const base = p.label || p.name;
    return st ? `${base} · ${st.problem ? S(st.problem) : S("billing_" + st.billing)}` : base;
  };
  const toolOptions = providers.map((p) => h("option", {value: p.name, selected: p.name === defProvider}, label(p)));
  const pSel = h("select", {"aria-label": S("provider")},
    h("optgroup", {label: S("auto_group")}, AUTO_KINDS.map((k) => h("option", {value: k, selected: k === def}, S("auto_kind_" + k.replace(":", "_"))))),
    h("optgroup", {label: S("tools_group")}, toolOptions));
  const isAuto = () => AUTO_KINDS.includes(pSel.value);
  // The model: a list of the tool's models (the tool's default first); a name not in the list is kept as one more row.
  const model = h("select", {class: "mono", "aria-label": S("model")});
  const setModel = (name) => {
    if (name && ![...model.options].some((o) => o.value === name)) model.appendChild(h("option", {value: name}, name));
    model.value = name || "";
  };
  const effort = h("select", {"aria-label": S("effort")});
  const autoLine = h("span", {class: "usage-hint small auto-line"});
  const hint = usageHint();  // live.js: "5 saat: %54", in a warning colour near a limit
  const refresh = () => {
    const p = providers.find((x) => x.name === pSel.value) || {models: [], efforts: []};
    const keepModel = model.dataset.for === pSel.value ? model.value : pSel.value === defProvider ? defModel : "";
    model.dataset.for = pSel.value;
    model.replaceChildren(h("option", {value: ""}, S("model_default")), ...p.models.map((m) => h("option", {value: m}, m)));
    setModel(keepModel);
    const keep = effort.value || defEffort;
    effort.replaceChildren(h("option", {value: ""}, S("effort_default")), ...p.efforts.map((e) => h("option", {value: e, selected: e === keep}, S("effort_" + e))));
    model.hidden = isAuto();
    effort.hidden = isAuto() || !p.efforts.length;
    showHint();
  };
  const showHint = () => {
    // auto: "Otomatik: claude/haiku · 5 saat: %54"; a tool: its usage, or why it cannot run now
    if (isAuto()) {
      const chosen = autoChoice(pSel.value);
      const provider = chosen ? chosen.name.split("@")[0].split("/")[0] : "";
      autoLine.textContent = !providerStates.data ? "" : chosen
        ? [S("auto_now", {name: chosen.name}), usageHintText(provider), S(chosen.local ? "sent_to_local" : "sent_to", {vendor: chosen.vendor})].filter(Boolean).join(" · ")
        : S(pSel.value === "auto:local" ? "auto_none_local_ui" : "auto_none_ui");
      autoLine.className = "usage-hint small auto-line " + (chosen ? usageLevel(usageOf(provider)) : "warn-text");
      hint.hidden = true;
      autoLine.hidden = !autoLine.textContent;
      return;
    }
    const st = providerInfo(pSel.value);
    autoLine.textContent = st && st.problem ? S(st.problem) : st && st.billing === "api_key" ? S("billed_warning") : "";
    autoLine.className = "usage-hint small auto-line warn-text";
    autoLine.hidden = !autoLine.textContent;
    hint.show(pSel.value);
  };
  pSel.addEventListener("change", refresh);
  refresh();
  loadUsage().then(showHint);
  loadProviderStates().then(() => {
    toolOptions.forEach((o, i) => { o.textContent = label(providers[i]); });
    // The workflow's default tool cannot run here (not installed, not signed in, billed): start on `auto`.
    const st = providerInfo(pSel.value);
    if (!isAuto() && !wrap.touched && st && st.problem && autoChoice("auto")) {
      pSel.value = "auto";
      pSel.dispatchEvent(new Event("change", {bubbles: true}));
    } else showHint();
  });
  const wrap = h("div", {class: "provider-pick"}, pSel, model, effort, autoLine, hint);
  wrap.addEventListener("input", () => { wrap.touched = true; });
  pSel.addEventListener("pointerdown", () => { wrap.touched = true; });
  wrap.read = () => (isAuto() ? pSel.value : pSel.value + (model.value ? "/" + model.value : "") + (effort.value ? "@" + effort.value : ""));
  wrap.write = (value) => {
    const [base, level] = String(value).split("@");
    const [prov, ...rest] = base.split("/");
    if (AUTO_KINDS.includes(String(value))) { pSel.value = String(value); refresh(); return; }
    if (!providers.some((p) => p.name === canonicalProvider(prov))) return;
    pSel.value = canonicalProvider(prov);
    refresh();
    setModel(rest.join("/"));
    effort.value = level || "";
    showHint();
  };
  if (!providers.length) wrap.appendChild(h("p", {class: "small warn-text"}, S("no_providers")));
  return wrap;
}

// The estimate's steps: "Summary → Anthropic", in a fold; a step that privacy: local refuses is marked, open.
function estimateSteps(est) {
  const refused = est.refused || 0;
  return h("details", {class: "estimate-steps small", open: refused > 0},
    h("summary", {}, S("sent_to_title"), refused ? h("span", {class: "badge bad"}, S("privacy_refused_count", {count: refused})) : null),
    h("ul", {class: "plain"}, est.steps.map((s) => h("li", {class: s.refused ? "bad-text" : ""},
      h("b", {}, L(s.label) || s.node), ": ", h("code", {}, s.model || "–"), " → ",
      s.sent_to ? S(s.local ? "sent_to_local" : "sent_to", {vendor: s.sent_to}) : "–"))));
}

// The run window's privacy choice: "only models on this computer" (a workflow with "privacy: local" always is).
function privacyField(tpl, estimate) {
  const fixed = Boolean(tpl.model && tpl.model.privacy === "local");
  // A browser agent reads sites with Claude Code: such a workflow cannot keep everything on this computer.
  const web = !fixed && ((tpl.model && tpl.model.nodes) || []).some((n) => n && n.type === "ai.agent");
  const box = h("input", {type: "checkbox", checked: fixed, disabled: fixed || web, onchange: () => { estimate.privacy = box.checked ? "local" : ""; estimate.refresh(true); }});
  estimate.privacy = fixed ? "local" : "";
  const row = h("div", {class: "stack privacy-row"}, h("label", {class: "check"}, box, h("span", {}, S("privacy_local_label"))),
    h("span", {class: "small muted"}, S(fixed ? "privacy_local_fixed" : web ? "privacy_local_web" : "privacy_local_hint")));
  row.read = () => (box.checked ? "local" : "");
  return row;
}

// The run window's "Model for every step": one tool for all model steps, in place of the models the workflow sets
// (a person with only Codex runs a workflow written for Claude). Chosen, the workflow's own model fields are hidden.
function everyStepField(estimate, fields) {
  const providers = (INFO && INFO.providers) || [];
  const label = (p) => {
    const st = providerInfo(p.name);
    return st && st.problem ? `${p.label || p.name} · ${S(st.problem)}` : (p.label || p.name);
  };
  const select = h("select", {id: "in-every-step", onchange: () => {
    estimate.everyStep = select.value;
    for (const f of fields) if (f.spec.type === "provider") f.row.hidden = Boolean(select.value);
    estimate.refresh(true);
  }}, h("option", {value: ""}, S("every_step_workflow")),
    h("option", {value: "auto"}, S("every_step_auto")),
    providers.map((p) => h("option", {value: p.name}, label(p))));
  const row = h("div", {class: "stack run-field"}, h("label", {class: "fld-label", for: "in-every-step"}, S("every_step_label")),
    select, h("p", {class: "small muted"}, S("every_step_hint")));
  row.read = () => select.value;
  return row;
}

// The Setup tab's panel of the AI tools for workflows: the model order of `auto`, billing, calls at once.
async function loadProviders(force) {
  const el = $("#providers-panel");
  if (!el) return;
  let data;
  try { data = await loadProviderStates(force); } catch (e) { return fill(el, problemsBox(e)); }
  if (!data || state.tab !== "setup") return;
  const save = async (button, change) => {
    const res = await act(button, () => api("PUT", "/api/providers", change));
    if (res) { providerStates.data = res; providerStates.at = Date.now(); drawProviders(res); }
  };
  drawProviders(data, save);
}

function drawProviders(data, save) {
  const el = $("#providers-panel");
  save = save || el.save;
  el.save = save;
  const order = data.order.slice();
  const labelOf = (entry) => {
    const p = providerInfo(entry.split("@")[0].split("/")[0]);
    return p ? p.label : entry;
  };
  const move = (i, by) => (e) => {
    const next = order.slice();
    [next[i], next[i + by]] = [next[i + by], next[i]];
    save(e.currentTarget, {order: next});
  };
  const rows = order.map((entry, i) => {
    const p = providerInfo(entry.split("@")[0].split("/")[0]);
    return h("li", {class: "order-row"},
      h("span", {class: "order-n"}, String(i + 1)),
      h("span", {class: "order-name"}, h("b", {}, labelOf(entry)), " ", h("code", {}, entry)),
      p ? billingBadge(p.billing) : null,
      p && p.problem ? h("span", {class: "badge warn"}, S(p.problem)) : p && p.blocked_until ? h("span", {class: "badge warn"}, S("hint_limited", {time: fmtTime(p.blocked_until)})) : null,
      h("span", {class: "order-actions"},
        h("button", {type: "button", class: "icon-btn", disabled: i === 0, "aria-label": `${S("move_up")}: ${entry}`, title: S("move_up"), onclick: move(i, -1)}, "↑"),
        h("button", {type: "button", class: "icon-btn", disabled: i === order.length - 1, "aria-label": `${S("move_down")}: ${entry}`, title: S("move_down"), onclick: move(i, 1)}, "↓"),
        h("button", {type: "button", class: "icon-btn danger", "aria-label": `${S("remove")}: ${entry}`, title: S("remove"),
          onclick: (e) => save(e.currentTarget, {order: order.filter((_, j) => j !== i)})}, "✕")));
  });
  // Adding a model: a tool, then optionally its model.
  const usable = data.providers.filter((p) => p.installed);
  const addTool = h("select", {"aria-label": S("provider")}, usable.map((p) => h("option", {value: p.name}, p.label)));
  const addModel = h("select", {class: "mono", "aria-label": S("model")});
  const fillModels = () => {
    const info = ((INFO && INFO.providers) || []).find((x) => x.name === addTool.value);
    const p = providerInfo(addTool.value);
    addModel.replaceChildren(h("option", {value: ""}, S("model_default")),
      ...[...new Set([...((p && p.models) || []), ...((info && info.models) || [])])].map((m) => h("option", {value: m}, m)));
  };
  addTool.addEventListener("change", fillModels);
  fillModels();
  const add = h("form", {class: "row order-add", onsubmit: (e) => {
    e.preventDefault();
    const entry = addTool.value + (addModel.value ? "/" + addModel.value : "");
    save($("button", e.currentTarget), {order: [...order.filter((x) => x !== entry), entry]});
  }}, addTool, addModel, h("button", {type: "submit", class: "btn"}, "+ " + S("order_add")));
  const autoLine = (k) => {
    const chosen = data.auto && data.auto[k];
    return h("li", {}, h("b", {}, S("auto_kind_" + k.replace(":", "_"))), ": ",
      chosen ? [h("code", {}, chosen.name), " · ", S(chosen.local ? "sent_to_local" : "sent_to", {vendor: chosen.vendor})]
        : h("span", {class: "warn-text"}, S("auto_none_short")));
  };
  // One row per tool: its state and the two settings (calls at once, API key). How much is left is on the cards above.
  const tools = data.providers.map((p) => {
    const sizes = Array.from({length: 8}, (_, i) => i + 1);
    const conc = h("select", {"aria-label": `${S("concurrency")}: ${p.label}`, onchange: (e) => save(e.currentTarget, {providers: {[p.name]: {concurrency: Number(e.currentTarget.value)}}})},
      sizes.map((n) => h("option", {value: String(n), selected: n === p.concurrency}, String(n))));
    const key = p.default_billing !== "local" ? h("label", {class: "check small"},
      h("input", {type: "checkbox", checked: p.api_key_allowed, onchange: (e) => save(e.currentTarget, {providers: {[p.name]: {api_key: e.currentTarget.checked}}})}),
      h("span", {}, S("allow_api_key"))) : h("span", {class: "small muted"}, "–");
    const status = !p.installed ? h("span", {class: "badge"}, S("not_installed"))
      : p.problem ? h("span", {class: "badge warn"}, S(p.problem))
        : p.blocked_until ? h("span", {class: "badge warn"}, S("hint_limited", {time: fmtTime(p.blocked_until)}))
          : h("span", {class: "badge good"}, S("tool_state_ready"));
    return h("tr", {class: p.installed ? "" : "off"},
      h("th", {scope: "row"}, p.label, h("div", {class: "small muted"}, S(p.local ? "sent_to_local" : "sent_to", {vendor: p.vendor}))),
      h("td", {}, h("div", {class: "badges"}, status, p.billing === "api_key" && !p.problem ? billingBadge(p.billing) : null),
        p.installed && p.billing && p.billing !== "api_key" ? h("div", {class: "small muted"}, S("billing_" + p.billing)) : null,
        p.key_dropped ? h("div", {class: "small muted"}, S("key_dropped")) : null),
      h("td", {}, conc, p.in_use ? h("div", {class: "small muted"}, S("at_once", {count: p.in_use})) : null),
      h("td", {}, key));
  });
  fill(el,
    h("p", {class: "muted providers-lead"}, S("providers_intro")),
    // 1. Which model a workflow uses when it says "automatic": the order, and what it picks now.
    h("section", {class: "providers-block"},
      h("h3", {}, S("order_title")),
      h("p", {class: "small muted"}, S(data.order_is_default ? "order_default_note" : "order_note")),
      rows.length ? h("ol", {class: "plain order-list"}, rows) : h("p", {class: "small warn-text"}, S("order_empty")), add,
      h("ul", {class: "plain auto-list small"}, autoLine(AUTO_KINDS[0])),
      h("details", {class: "small"}, h("summary", {}, S("auto_more")),
        h("ul", {class: "plain auto-list"}, AUTO_KINDS.slice(1).map(autoLine)), h("p", {class: "muted"}, S("auto_explain")))),
    // 2. Per tool: calls at once and "API key (billed)".
    h("section", {class: "providers-block"},
      h("h3", {}, S("tool_settings_title")), h("p", {class: "small muted"}, S("tool_settings_intro")),
      h("div", {class: "table-wrap"}, h("table", {class: "providers-table"},
        h("thead", {}, h("tr", {}, h("th", {scope: "col"}, S("provider")), h("th", {scope: "col"}, S("tool_state_column")),
          h("th", {scope: "col"}, S("concurrency")), h("th", {scope: "col"}, S("api_key_column")))),
        h("tbody", {}, tools)))),
    // 3. Scheduled and batch runs.
    h("section", {class: "providers-block"}, unattendedForm(data, save)),
    // 4. A local OpenAI-compatible server: few people have one, so it is folded.
    h("details", {class: "providers-block providers-more"}, h("summary", {}, S("local_server_title")), localServerForm(data, save)),
    h("p", {class: "small muted"}, S("providers_file_note")));
}

// Scheduled and batch runs: only local models and API keys, unless the user allows subscriptions (Engine.unattended_problem).
const TERMS_URL = (lang) => `https://tolgabuyuktanir.github.io/Mehteran/docs.html?lang=${lang === "tr" ? "tr#tr-kosullar" : "en#terms"}`;

function unattendedForm(data, save) {
  return h("div", {class: "stack"}, h("h3", {}, S("unattended_title")),
    h("label", {class: "check"}, h("input", {type: "checkbox", checked: Boolean(data.unattended_subscriptions),
      onchange: (e) => save(e.currentTarget, {unattended_subscriptions: e.currentTarget.checked})}), h("span", {}, S("unattended_label"))),
    h("p", {class: "small muted"}, S("unattended_note"), " ",
      h("a", {href: TERMS_URL(LANG), target: "_blank", rel: "noopener noreferrer"}, S("unattended_terms_link"))));
}

// A local server with an OpenAI-compatible API (LM Studio, llama.cpp, vLLM): its address on this computer and model.
function localServerForm(data, save) {
  const p = data.providers.find((x) => x.name === "openai-local");
  if (!p) return null;
  const url = h("input", {type: "url", class: "mono", value: p.url || "", placeholder: "http://127.0.0.1:1234/v1", "aria-label": S("local_server_url")});
  const model = h("input", {type: "text", class: "mono", value: p.model || "", list: "local-server-models", placeholder: S("model_default"), "aria-label": S("model")});
  const result = h("span", {class: "small muted", "aria-live": "polite"});
  return h("form", {class: "stack local-server", onsubmit: (e) => {
    e.preventDefault();
    save($("button[type=submit]", e.currentTarget), {providers: {"openai-local": {url: url.value.trim(), model: model.value.trim()}}});
  }},
  h("p", {class: "small muted"}, S("local_server_intro")),
  h("div", {class: "row order-add"}, url, model, h("datalist", {id: "local-server-models"}, (p.models || []).map((m) => h("option", {value: m}))),
    h("button", {type: "submit", class: "btn"}, S("save")),
    h("button", {type: "button", class: "btn", disabled: !p.installed, onclick: async (e) => {
      const r = await act(e.currentTarget, () => api("POST", "/api/models/test", {name: "openai-local" + (model.value.trim() ? "/" + model.value.trim() : "")}));
      if (r) result.textContent = r.message;
    }}, S("test"))),
  h("span", {class: "small " + (p.installed ? "good-text" : "muted")}, p.url ? S(p.installed ? "local_server_ok" : "local_server_down", {count: (p.models || []).length}) : S("local_server_none")),
  result);
}

// The browser's own file button cannot be translated: a button of the page opens the real file input, which stays
// in the page (out of sight, not in the tab order) for the form, its "required" check and the file list.
function filePicker(input, multiple) {
  input.classList.add("file-native");
  input.tabIndex = -1;
  input.setAttribute("aria-hidden", "true");
  const chosen = h("span", {class: "small muted file-chosen"}, S("no_file_chosen"));
  input.addEventListener("change", () => {
    if (!multiple) chosen.textContent = input.files[0] ? input.files[0].name : S("no_file_chosen");
  });
  const button = h("button", {type: "button", class: "btn", onclick: () => input.click()}, "📎 " + S(multiple ? "choose_files" : "choose_file"));
  if (input.id) button.id = input.id + "-button";
  return h("span", {class: "file-pick"}, input, button, multiple ? null : chosen);
}

// The sample document (ui/sample-<lang>.md, Turkish or English) put into a file field as if the user had chosen it.
async function putSample(input) {
  const name = LANG === "tr" ? "sample-tr.md" : "sample-en.md";
  try {
    const res = await fetch(name);
    if (!res.ok) throw new Error(res.statusText);
    const file = new File([await res.blob()], S("sample_file_name"), {type: "text/markdown"});
    const list = new DataTransfer();
    list.items.add(file);
    input.files = list.files;
    input.dispatchEvent(new Event("change"));
  } catch (e) {
    toast(e.message, true);
  }
}

const fileSize = (bytes) => (bytes < 1024 * 1024 ? `${bytes ? Math.max(1, Math.round(bytes / 1024)) : 0} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`);

// A file input with "multiple: true": files are added (several at a time, or one after the other) and removed one
// by one; the count and the total size are shown against the limits of a run (INFO.max_files, INFO.files_limit_mb).
function multiFileField(spec, accept) {
  const chosen = [];
  const list = h("ul", {class: "file-list"});
  const note = h("p", {class: "small muted", "aria-live": "polite"});
  const total = () => chosen.reduce((sum, f) => sum + f.size, 0);
  const picker = h("input", {type: "file", multiple: true, accept, "aria-label": L(spec.label) || spec.id, onchange: () => {
    for (const f of picker.files) if (!chosen.some((c) => c.name === f.name && c.size === f.size)) chosen.push(f);
    picker.value = "";
    draw();
  }});
  const draw = () => {
    fill(list, chosen.map((f, i) => h("li", {}, h("span", {class: "file-name"}, f.name), h("span", {class: "small muted"}, fileSize(f.size)),
      h("button", {type: "button", class: "icon-btn danger", "aria-label": `${S("remove")}: ${f.name}`, title: S("remove"),
        onclick: () => { chosen.splice(i, 1); draw(); }}, "✕"))));
    note.textContent = S("files_summary", {count: chosen.length, max: INFO.max_files, size: fileSize(total()), limit: INFO.files_limit_mb});
    note.className = "small " + (wrap.check() && chosen.length ? "warn-text" : "muted");
  };
  const wrap = h("div", {class: "multi-file"}, filePicker(picker, true), list, note);
  wrap.read = () => chosen.slice();
  wrap.check = () => {
    if (chosen.length > INFO.max_files) return S("files_too_many", {max: INFO.max_files});
    if (total() > INFO.files_limit_mb * 1024 * 1024) return S("files_too_large_ui", {limit: INFO.files_limit_mb});
    const big = chosen.find((f) => f.size > INFO.upload_limit_mb * 1024 * 1024);
    if (big) return S("file_too_large_ui", {name: big.name, limit: INFO.upload_limit_mb});
    if (!chosen.length && spec.required !== false) return S("files_needed", {name: L(spec.label) || spec.id});
    return null;
  };
  draw();
  return wrap;
}

// --- the run dialog's estimate: the model calls of the run, per model, with the tool's usage now -------------------
// POST /api/templates/<source>/<id>/estimate with the form's model and choice values; asked again when one of them
// changes (another model). The counts come from the workflow: nothing here is a share of a usage limit.
function runEstimate(source, id, fields, priorRun) {
  const el = h("section", {class: "run-estimate", "aria-live": "polite"});
  let seq = 0, timer = null;
  const count = (item) => [item.calls || !item.loops ? String(item.calls) : null,
    item.loops ? S("estimate_per_part", {parts: item.max_parts}) : null].filter(Boolean).join(" + ");
  const draw = (est) => {
    el.last = est;
    if (el.onDraw) el.onDraw(est);
    if (!est.steps.length) return fill(el, h("p", {class: "small muted"}, S("estimate_none")));
    fill(el, h("div", {class: "estimate-head"}, h("b", {}, S("estimate_title")),
      h("span", {class: "small"}, S("estimate_calls", {calls: count(est)}), " · ", S("estimate_max", {count: est.max_calls}))),
    batchEstimateLine(est, el.times),  // history.js: × the files of a batch
    h("ul", {class: "plain estimate-models"}, est.models.map((m) => {
      const usage = usageHintText(m.provider);  // live.js: "5 saat: %54"
      const local = (INFO.providers || []).find((p) => p.name === m.provider);
      return h("li", {}, h("span", {class: "estimate-model"}, m.tool_name ? m.tool_name + " · " : "", h("code", {}, m.model || "–"), localTag(local),
        m.configured ? null : h("span", {class: "badge bad"}, S("estimate_not_configured")),
        m.auto ? h("span", {class: "muted small"}, " · " + S("auto_kind_" + m.auto.replace(":", "_"))) : null),
      h("span", {class: "small"}, S("estimate_calls", {calls: count(m)})),
      m.sent_to ? h("span", {class: "small sent-to"}, S(m.local ? "sent_to_local" : "sent_to", {vendor: m.sent_to})) : null,
      m.configured ? h("span", {class: "usage-hint small " + usageLevel(usageOf(m.provider))},
        usage ? S("estimate_usage_now", {text: usage}) : S("estimate_usage_none")) : null);
    })),
    estimateSteps(est),  // stream P: each step and where its prompt goes
    h("p", {class: "small muted"}, S("quota_policy_wait", {hours: est.quota_max_hours})),
    est.steps.some((s) => s.auto) ? h("p", {class: "small muted"}, S("quota_policy_auto")) : null,
    est.steps.filter((s) => s.fallback).map((s) => h("p", {class: "small muted"},
      S("quota_policy_fallback", {step: L(s.label) || s.node, model: s.fallback}))),
    est.conditional ? h("p", {class: "small muted"}, S("estimate_conditional", {count: est.conditional})) : null,
    h("p", {class: "small muted"}, S("estimate_no_cost")));
  };
  const ask = async () => {
    const mine = ++seq, values = {};
    for (const {spec, control} of fields) if (["provider", "choice"].includes(spec.type)) values[spec.id] = control.read();
    try {
      const url = priorRun ? `/api/runs/${priorRun.id}/estimate` : `/api/templates/${source}/${id}/estimate`;
      const [est] = await Promise.all([api("POST", url, {values, privacy: el.privacy || "", every_step: el.everyStep || ""}), loadUsage()]);
      if (mine === seq) draw(est);
    } catch (err) { if (mine === seq) fill(el, h("p", {class: "small muted"}, err.message)); }
  };
  el.refresh = (soon) => { clearTimeout(timer); timer = setTimeout(ask, soon ? 0 : 350); };
  el.times = 1;
  el.setTimes = (n) => { el.times = n; if (el.last) draw(el.last); };  // a batch: one run per file
  fill(el, h("p", {class: "small muted"}, S("loading")));
  el.refresh(true);
  return el;
}

// A run starts on the workflow's page, in its Run section.
function openRun(source, id) {
  go(`workflows/${source}/${id}/run`);
}

// The run form of the Run section: the inputs on the left; the estimate and "Start the run" beside them.
function runForm(tpl, source, id, priorRun) {
  const fields = [];
  for (const spec of tpl.input_specs) {
    let control;
    if (spec.type === "file") {
      const accept = (spec.formats || INFO.file_formats).map((f) => "." + f).join(",");
      if (spec.multiple) control = multiFileField(spec, accept);
      else {
        const input = h("input", {type: "file", accept, required: spec.required !== false});
        control = filePicker(input, false);
        control.read = () => input.files[0];
        if (state.sampleRun) {  // "Try with a sample document": the first file field gets the sample
          state.sampleRun = false;
          putSample(input);
        }
      }
    } else if (spec.type === "language" || isLanguageChoice(spec)) {
      // The output language: the flag picker. It starts at the interface language when the workflow offers it
      // (a "language" input offers every language), else at the workflow's default.
      const codes = spec.type === "language" ? null : spec.options.map((o) => (typeof o === "string" ? o : o.value));
      const start = spec.type === "language" ? (isLang(spec.default) ? spec.default : LANG)
        : codes.includes(LANG) ? LANG : codes.includes(spec.default) ? spec.default : codes[0];
      control = languagePicker({codes, value: start, label: L(spec.label) || spec.id});
      control.read = () => control.value;
      control.write = (v) => { if (control.setValue) control.setValue(v); };
    } else if (spec.type === "choice") {
      control = h("select", {}, spec.options.map((o) => {
        const value = typeof o === "string" ? o : o.value;
        return h("option", {value, selected: value === spec.default}, typeof o === "string" ? o : (L(o.label) || o.value));
      }));
      control.read = () => control.value;
      control.write = (v) => { if ([...control.options].some((o) => o.value === v)) control.value = v; };
    } else if (spec.type === "provider") {
      control = providerField(spec);
    } else {
      control = spec.type === "url" && spec.multiple ? h("textarea", {rows: 6, dir: "ltr", class: "mono", placeholder: "https://…\nhttps://…"})
        : spec.multiline ? h("textarea", {rows: 3})
        : h("input", spec.type === "url" ? {type: "url", placeholder: "https://…", dir: "ltr"} : {type: "text"});
      control.value = spec.default || "";
      if (spec.required !== false) control.required = true;
      control.read = () => control.value;
      control.write = (v) => { control.value = v; };
    }
    const fid = "in-" + spec.id;
    // The label names the control a person uses: the field, or the page's file button (several files: their group).
    const target = control.classList.contains("file-pick") || control.classList.contains("lang-pick") ? $("button", control)
      : control.tagName === "DIV" ? null : control;
    if (target) target.id = fid;
    if (control.tagName === "DIV") control.setAttribute("aria-label", L(spec.label) || spec.id);
    fields.push({spec, control, row: h("div", {class: "stack run-field"},
      h(target ? "label" : "span", {class: "fld-label", for: target ? fid : null},
        L(spec.label) || spec.id, spec.required === false ? h("span", {class: "muted"}, " · " + S("optional")) : null),
      control, spec.description ? h("p", {class: "small muted"}, L(spec.description)) : null)});
  }
  const lastRun = recallInputs(source, id);  // live.js: the values of the last run of this workflow
  // "Run again" on a run: its values are filled in at once (files are not: they are chosen again)
  const prefill = priorRun?.inputs;
  if (prefill) for (const {spec, control} of fields) if (spec.type !== "file" && spec.id in prefill && control.write) control.write(prefill[spec.id]);
  const estimate = runEstimate(source, id, fields, priorRun);
  const extras = runExtras(source, id, fields, estimate);  // history.js: once per file, save to a folder
  const privacy = privacyField(tpl, estimate);  // only models on this computer
  const everyStep = everyStepField(estimate, fields);  // one model for every step
  const status = h("div", {class: "small grow", "aria-live": "polite"});
  const submit = h("button", {class: "btn primary", type: "submit"}, "▶ " + S("start_run"));
  const summary = h("span", {class: "small muted run-summary", "aria-live": "polite"});
  estimate.onDraw = (est) => {
    const tools = [...new Set(est.models.map((m) => m.tool_name || m.provider).filter(Boolean))];
    const missing = est.models.some((m) => !m.configured);
    summary.className = "small run-summary " + (missing ? "warn-text" : "muted");
    summary.textContent = !est.steps.length ? S("estimate_none")
      : [S("estimate_calls", {calls: est.calls}), tools.join(", "), missing ? S("estimate_not_configured") : ""].filter(Boolean).join(" · ");
  };
  // history.js: run on a schedule instead of now (no file inputs: a schedule keeps only text values)
  const schedule = priorRun ? null : scheduleField(tpl, (on) => { submit.textContent = on ? "⏲ " + S("schedule_save") : "▶ " + S("start_run"); });
  const form = h("form", {class: "run-form run-page", "aria-label": S("new_run_title", {name: L(tpl.name) || id}), onsubmit: async (e) => {
    e.preventDefault();
    submit.disabled = true;
    status.replaceChildren();
    try {
      const values = {}, files = {};
      const extra = await extras.prepare();  // the folder checked (and confirmed once), the files of a batch
      const rule = schedule?.read();
      if (rule) {
        if (extra.batchFiles) throw new Error(S("schedule_needs_files"));
        const values = {};
        for (const {spec, control} of fields) if (spec.type !== "file") values[spec.id] = control.read();
        const body = {template: `${source}:${id}`, values, rule, name: schedule.name()};
        if (privacy.read()) body.privacy = privacy.read();
        if (everyStep.read()) body.every_step = everyStep.read();
        if (extra.output_dir) Object.assign(body, {output_dir: extra.output_dir, output_confirmed: true});
        const item = await api("POST", "/api/schedules", body);
        rememberInputs(source, id, fields);
        toast(S("schedule_saved", {when: fmtTime(item.next_at)}));
        return go("runs");
      }
      for (const {spec, control} of fields) {
        if (spec.id === extra.batchInput) continue;
        const value = control.read();
        if (spec.type === "file") {
          const problem = control.check && control.check();
          if (problem) throw new Error(problem);
          const list = Array.isArray(value) ? value : value ? [value] : [];
          if (!list.length) continue;
          const ids = [];
          for (const file of list) {
            status.replaceChildren(S("uploading", {name: file.name}));
            ids.push((await api("PUT", `/api/uploads?file=${encodeURIComponent(file.name)}`, undefined, file)).upload);
          }
          files[spec.id] = spec.multiple ? ids : ids[0];
        } else values[spec.id] = value;
      }
      const body = {template: `${source}:${id}`, values, files};
      if (priorRun) body.from_run = priorRun.id;
      if (privacy.read()) body.privacy = privacy.read();
      if (everyStep.read()) body.every_step = everyStep.read();
      if (extra.output_dir) Object.assign(body, {output_dir: extra.output_dir, output_confirmed: true});
      if (extra.batchFiles) {
        const ids = [];
        for (const file of extra.batchFiles) {
          status.replaceChildren(S("uploading", {name: file.name}));
          ids.push((await api("PUT", `/api/uploads?file=${encodeURIComponent(file.name)}`, undefined, file)).upload);
        }
        body.batch = {input: extra.batchInput, files: ids};
      }
      status.replaceChildren(S("starting"));
      const res = await api("POST", "/api/runs", body);
      rememberInputs(source, id, fields);  // live.js: for "Same as last time"
      toast(res.batch ? S("batch_started", {count: res.ids.length}) : S("run_started_toast"));
      go("runs/" + res.id);
    } catch (err) {
      status.replaceChildren(problemsBox(err));
      submit.disabled = false;
    }
  }},
  h("div", {class: "run-fields"}, tpl.description ? h("details", {},
    h("summary", {}, S("details")), h("p", {class: "muted"}, L(tpl.description))) : null,
    h("p", {class: "small muted"}, S("new_run_lede")),
    // warnings of the workflow (schema.warnings): shown before the run; they do not block it
    (tpl.warnings || []).length ? h("details", {class: "notice warn run-warnings"}, h("summary", {}, S("warnings_found", {count: tpl.warnings.length})),
      h("ul", {class: "failures"}, tpl.warnings.map((w) => h("li", {}, w.label ? h("b", {}, `“${w.label}”: `) : null, w.message)))) : null,
    lastRun && !prefill ? h("div", {class: "row last-run"}, h("button", {type: "button", class: "btn small", onclick: (e) => {
      for (const {spec, control} of fields) if (spec.id in lastRun && control.write) control.write(lastRun[spec.id]);
      e.currentTarget.disabled = true;
      estimate.refresh(true);
      toast(S("last_filled"));
    }}, "↺ " + S("same_as_last")), h("span", {class: "small muted"}, S("same_as_last_hint"))) : null,
    fields.length ? fields.filter((f) => f.spec.type !== "provider").map((f) => f.row) : h("p", {class: "muted"}, S("no_inputs")),
    // The options: the models (chosen by themselves; the line beside "Start" names them), a folder, a schedule.
    h("details", {class: "run-models"}, h("summary", {}, h("b", {}, S("run_options_title")), h("span", {class: "small muted"}, S("run_options_hint"))),
      h("div", {class: "stack"}, everyStep, fields.filter((f) => f.spec.type === "provider").map((f) => f.row), privacy, extras, schedule))),
  // "Start" at the end of the form, with one line of what the run calls; the whole estimate under "Details".
  h("div", {class: "run-foot"}, h("div", {class: "run-start"}, submit, summary), status,
    h("details", {class: "run-more"}, h("summary", {class: "small"}, S("details")), estimate)));
  // A changed value (another model, typed or chosen) gives a new estimate.
  for (const {spec, control} of fields) {
    if (!["provider", "choice"].includes(spec.type)) continue;
    control.addEventListener("change", () => estimate.refresh(true));
    control.addEventListener("input", () => estimate.refresh(false));
  }
  return form;
}


// --- results: the reader (formatted or plain), compare two runs, edit and export -----------------------------------
// A result's .md file is shown formatted (markdown.js) or as plain text; "mehteran.readerView" remembers the choice.
// "Edit" saves an edited copy next to the run (<run>/edited/<node>.<name>.md, PUT /api/runs/<run>/edits/<output>);
// the original output never changes, and the reader offers both. The edited copy is exported with document.export's
// code (POST /api/runs/<run>/edits/<output> {format}). "Compare" shows a result of this run next to the same result
// of another finished run of the same workflow, and marks the paragraphs that differ.
// The rich reader uses #reader-tools and #reader-body; on close the dialog is the plain reader again (#reader-text),
// as the guide (live.js) uses it.
const isMarkdown = (rel) => /\.md$/i.test(rel || "");
const isEditable = (rel) => /^nodes\/[a-z][a-z0-9_-]*\/[A-Za-z0-9][A-Za-z0-9_-]*\.md$/.test(rel || "");
const filePath = (rel) => rel.split("/").map(encodeURIComponent).join("/");
const reader = {view: recall("mehteran.readerView") === "plain" ? "plain" : "formatted", seq: 0};

// The workflow's results; a workflow that names none shows the files its steps saved (an export step's documents).
function runResults(run) {
  if ((run.outputs || []).length) return run.outputs.filter((o) => o.path);
  const upstream = new Set(run.graph.edges.map((edge) => edge.from));
  return run.graph.nodes.flatMap((g) => Object.entries(run.nodes[g.id].outputs || {})
    .filter(([port, path]) => (run.node_info[g.id].ports || {})[port] === "file" || (!upstream.has(g.id) && isMarkdown(path)))
    .map(([port, path]) => ({id: `${g.id}.${port}`, label: `${L(run.node_info[g.id].label) || g.id} · ${port}`, path})));
}

// The results of a run: the first text shown on the page once the run has ended, the other results to read, and one
// download per file the workflow saved ("Save as a document" steps: Word, Markdown, …).
const FORMAT_NAMES = {md: "Markdown", docx: "Word", html: "HTML", pdf: "PDF", epub: "EPUB", json: "JSON", csv: "CSV", txt: "Text"};

function resultsBox(run, runId, outputs) {
  const name = (o) => L(o.label) || o.id;
  const texts = outputs.filter((o) => isMarkdown(o.path));
  const saved = run.graph.nodes.filter((g) => (run.node_info[g.id] || {}).type === "document.export")
    .flatMap((g) => Object.entries(run.nodes[g.id].outputs || {}).filter(([port]) => (run.node_info[g.id].ports || {})[port] === "file")
      .map(([port, path]) => ({port, path})));
  const shown = FINAL.has(run.status) && texts.length ? texts[0] : null;
  return h("section", {class: "card box results-box"},
    h("div", {class: "row results-head"}, h("h3", {}, S("results")),
      shown ? h("button", {type: "button", class: "btn small", onclick: () => openCompare(run, texts[0].id)}, "⇄ " + S("compare_action")) : null),
    h("div", {class: "row result-files"},
      outputs.filter((o) => o !== shown).map((o) => isMarkdown(o.path)
        ? h("span", {class: "result-item"},
          h("button", {type: "button", class: "btn", title: S("read"), onclick: () => openReader(runId, o.path, name(o))}, name(o)),
          h("a", {class: "btn", href: fileUrl(runId, o.path, true), title: S("download"), "aria-label": `${S("download")}: ${name(o)}`}, "↓"))
        : h("a", {class: "btn", href: fileUrl(runId, o.path, true)}, "↓ " + name(o))),
      saved.filter((f) => !outputs.some((o) => o !== shown && o.path === f.path)).map((f) => h("a", {class: "btn small", href: fileUrl(runId, f.path, true), title: f.path.split("/").pop()}, "↓ " + (FORMAT_NAMES[f.port] || f.port))),
      shown && !saved.some((f) => f.path === shown.path) ? h("a", {class: "btn small", href: fileUrl(runId, shown.path, true)}, "↓ " + name(shown)) : null),
    shown ? resultPreview(runId, shown, name(shown)) : null);
}

// The first text result on the page, formatted; "Open in full" opens the reader (plain view, edit, export).
function resultPreview(runId, output, title) {
  const box = h("div", {class: "result-preview"}, h("p", {class: "muted small"}, S("loading")));
  api("GET", `/api/runs/${runId}/files/${filePath(output.path)}`).then((text) => {
    fill(box, h("div", {class: "result-preview-head"}, h("b", {}, title),
      h("button", {type: "button", class: "btn small", onclick: () => openReader(runId, output.path, title)}, S("open_full"))),
    resultView(typeof text === "string" ? text : JSON.stringify(text, null, 2), true, undefined, "formatted"));
  }).catch((err) => fill(box, h("p", {class: "small muted"}, err.message)));
  return box;
}

// The rich reader: open it (wide for the compare view) and give the plain one back when it closes.
function readerOpen(title, wide) {
  const dialog = $("#reader");
  reader.seq++;
  reader.editing = false;
  reader.dirty = false;
  reader.compare = null;
  $("#reader-title").textContent = title;
  $("#reader-text").hidden = true;
  $("#reader-body").hidden = false;
  $("#reader-tools").hidden = false;
  $("#reader-download").hidden = Boolean(wide);
  dialog.classList.toggle("wide", Boolean(wide));
  fill($("#reader-tools"));
  fill($("#reader-body"), h("p", {class: "muted reader-pane"}, S("loading")));
  if (!reader.hooked) {
    reader.hooked = true;
    // Unsaved edits are not lost by Esc or the close button without a question.
    const keep = () => reader.editing && reader.dirty && !confirm(S("edit_discard_confirm"));
    dialog.addEventListener("cancel", (e) => { if (keep()) e.preventDefault(); });
    $("#reader-close").addEventListener("click", (e) => { if (keep()) e.stopImmediatePropagation(); }, true);
  }
  if (!reader.open) {
    reader.open = true;
    dialog.addEventListener("close", () => {
      reader.open = false;
      reader.seq++;
      reader.editing = false;
      reader.compare = null;
      dialog.classList.remove("wide");
      fill($("#reader-tools"));
      fill($("#reader-body"));
      $("#reader-tools").hidden = true;
      $("#reader-body").hidden = true;
      $("#reader-text").hidden = false;
      $("#reader-download").hidden = false;
    }, {once: true});
  }
  if (!dialog.open) dialog.showModal();
}

// "Formatted / Plain text"; redraw: the view to draw again.
function viewToggle(redraw) {
  const pick = (view) => h("button", {type: "button", class: "tab" + (reader.view === view ? " active" : ""), "aria-pressed": String(reader.view === view),
    onclick: () => { reader.view = view; remember("mehteran.readerView", view); redraw(); }}, S(view === "formatted" ? "md_formatted" : "md_plain"));
  return h("div", {class: "seg", role: "group", "aria-label": S("md_view")}, pick("formatted"), pick("plain"));
}

// A text as the reader shows it; mark(src): true for a paragraph to mark as different (the compare view).
function resultView(text, markdown, mark, view = reader.view) {
  if (!text) return h("p", {class: "muted reader-pane"}, S("empty_output"));
  const json = jsonPretty(text);  // history.js: the answer of an AI step with "output: json"
  if (json) return h("pre", {class: "md-plain json-view reader-pane", dir: "ltr"}, json);
  if (markdown && view === "formatted") {
    const el = Markdown.render(text, {mark});
    el.classList.add("reader-pane");
    return el;
  }
  return h("div", {class: "md-plain reader-pane"}, text);
}

// The reader for one output (the results box, a step's outputs, a step's prompt).
async function openReader(runId, rel, title) {
  readerOpen(title);
  const seq = reader.seq;
  Object.assign(reader, {runId, rel, title, original: "", edited: null, editPath: "", limit: 0, version: "original", notice: null});
  $("#reader-download").href = fileUrl(runId, rel, true);
  try {
    const [text, edit] = await Promise.all([api("GET", `/api/runs/${runId}/files/${filePath(rel)}`),
      isEditable(rel) ? api("GET", `/api/runs/${runId}/edits/${filePath(rel)}`).catch(() => null) : null]);
    if (seq !== reader.seq) return;
    reader.original = typeof text === "string" ? text : JSON.stringify(text, null, 2);
    reader.edited = edit && edit.exists ? edit : null;
    reader.editPath = edit ? edit.path : "";
    reader.limit = edit ? edit.limit : 0;
    reader.version = reader.edited ? "edited" : "original";  // the user's own version first, when there is one
    drawReader();
  } catch (err) {
    if (seq === reader.seq) fill($("#reader-body"), h("div", {class: "notice bad reader-pane"}, err.message));
  }
}

function drawReader() {
  const r = reader;
  const edited = r.version === "edited" && r.edited;
  $("#reader-download").href = fileUrl(r.runId, edited ? r.edited.path : r.rel, true);
  $("#reader-download").hidden = r.editing;
  fill($("#reader-tools"), !r.editing && isMarkdown(r.rel) ? viewToggle(drawReader) : null,
    !r.editing && isEditable(r.rel) && r.limit ? h("button", {type: "button", class: "btn", onclick: startEdit}, "✎ " + S("edit_action")) : null);
  if (r.editing) return drawEditor();
  fill($("#reader-body"), r.limit || r.notice ? versionBar() : null, resultView(edited ? r.edited.text : r.original, isMarkdown(r.rel)));
}

// Original / Edited, when the user saved an edited version; and the export of the edited version.
function versionBar() {
  const r = reader;
  const status = h("p", {class: "small reader-status", role: "status", "aria-live": "polite"}, r.notice || "");
  r.notice = null;
  if (!r.limit) return h("div", {class: "reader-bar"}, status);
  const pick = (version) => h("button", {type: "button", class: "tab" + (r.version === version ? " active" : ""), "aria-pressed": String(r.version === version),
    onclick: () => { r.version = version; drawReader(); }}, S(version === "edited" ? "version_edited" : "version_original"));
  const names = {md: "Markdown (.md)", docx: "Word (.docx)", html: "HTML (.html)", pdf: "PDF (.pdf)", epub: "EPUB (.epub)",
    eml: S("format_eml"), json: "JSON (.json)", csv: "CSV (.csv)"};
  const format = h("select", {"aria-label": S("export_format")}, ((INFO && INFO.formats) || Object.keys(names)).map((f) => h("option", {value: f}, names[f] || f)));
  format.value = recall("mehteran.exportFormat") || "docx";
  if (!format.value) format.value = "md";
  const exportButton = h("button", {type: "button", class: "btn", onclick: async (e) => {
    const button = e.currentTarget, seq = reader.seq;
    remember("mehteran.exportFormat", format.value);
    button.disabled = true;
    status.className = "small reader-status muted";
    status.textContent = S("export_working");
    try {
      const out = await api("POST", `/api/runs/${r.runId}/edits/${filePath(r.rel)}`, {format: format.value, version: r.version});
      if (seq !== reader.seq) return;
      h("a", {href: fileUrl(r.runId, out.path, true)}).click();  // an attachment: the page stays
      status.className = "small reader-status good-text";
      status.textContent = S("export_done", {name: out.path.split("/").pop()});
    } catch (err) {
      status.className = "small reader-status warn-text";
      status.textContent = err.message;
    } finally { button.disabled = false; }
  }}, "⇩ " + S("export_action"));
  return h("div", {class: "reader-bar"},
    h("div", {class: "row"},
      r.edited ? h("div", {class: "seg", role: "group", "aria-label": S("version_label")}, pick("original"), pick("edited")) : null,
      r.edited ? h("span", {class: "small muted"}, S("edit_modified", {time: fmtTime(r.edited.modified)})) : null,
      h("span", {class: "grow"}),
      h("label", {class: "row export-row"}, h("span", {class: "small muted"}, S("export_label")), format), exportButton),
    status);
}

function startEdit() {
  const r = reader;
  const text = r.version === "edited" && r.edited ? r.edited.text : r.original;
  if (new TextEncoder().encode(text).length > r.limit) {
    r.notice = S("edit_too_big", {limit: Math.floor(r.limit / 1024)});
    return drawReader();
  }
  Object.assign(r, {editing: true, dirty: false, draft: text});
  drawReader();
}

// The editor: the text on one side, its formatted preview on the other (under it on a narrow screen: hidden).
function drawEditor() {
  const r = reader;
  const area = h("textarea", {class: "edit-area", dir: "auto", spellcheck: "true", "aria-label": S("edit_text_label")});
  area.value = r.draft;
  const preview = h("div", {class: "edit-preview"});
  const status = h("p", {class: "small muted grow", role: "status", "aria-live": "polite"}, S("edit_note", {path: r.editPath}));
  const show = () => fill(preview, resultView(area.value, isMarkdown(r.rel)));
  let timer;
  area.addEventListener("input", () => {
    r.draft = area.value;
    r.dirty = true;
    clearTimeout(timer);
    timer = setTimeout(show, 250);
  });
  show();
  const cancel = h("button", {type: "button", class: "btn", onclick: () => {
    if (r.dirty && !confirm(S("edit_discard_confirm"))) return;
    Object.assign(r, {editing: false, dirty: false});
    drawReader();
  }}, S("edit_cancel"));
  const save = h("button", {type: "button", class: "btn primary", onclick: async (e) => {
    const button = e.currentTarget, seq = reader.seq;
    if (new TextEncoder().encode(area.value).length > r.limit) {
      status.className = "small warn-text grow";
      status.textContent = S("edit_too_big", {limit: Math.floor(r.limit / 1024)});
      return;
    }
    button.disabled = true;
    try {
      const out = await api("PUT", `/api/runs/${r.runId}/edits/${filePath(r.rel)}`, {text: area.value});
      if (seq !== reader.seq) return;
      Object.assign(r, {edited: {...out, text: area.value}, version: "edited", editing: false, dirty: false, notice: S("edit_saved")});
      drawReader();
    } catch (err) {
      status.className = "small warn-text grow";
      status.textContent = err.message;
      button.disabled = false;
    }
  }}, "✓ " + S("edit_save"));
  fill($("#reader-body"),
    h("div", {class: "edit-grid"}, area, h("div", {class: "edit-preview-col"}, h("p", {class: "small muted"}, S("edit_preview")), preview)),
    h("div", {class: "row reader-foot"}, status, cancel, save));
  area.focus();
  area.setSelectionRange(0, 0);  // the text from its start
  area.scrollTop = 0;
}

// The compare view: this run's result next to the same result (same output id) of another finished run of the same
// workflow (GET /api/runs: the same template; a run without one: the same workflow id).
async function openCompare(run, outputId) {
  readerOpen(S("compare_title", {name: run.workflow_name}), true);
  const seq = reader.seq;
  let runs;
  try { runs = await api("GET", "/api/runs"); }
  catch (err) { fill($("#reader-body"), h("div", {class: "notice bad reader-pane"}, err.message)); return; }
  if (seq !== reader.seq) return;
  const others = runs.filter((r) => r.id !== run.id && FINAL.has(r.status)
    && (run.template ? r.template === run.template : r.workflow_id === run.workflow_id));
  const before = others.find((r) => r.created < run.created) || others[0];
  reader.compare = {run, outputId, others, otherId: before ? before.id : null, diff: true, runs: {[run.id]: run}, texts: {}};
  drawCompare();
}

async function compareText(runId, outputId) {
  const c = reader.compare;
  if (!c.runs[runId]) c.runs[runId] = await api("GET", `/api/runs/${runId}`);
  const output = runResults(c.runs[runId]).find((o) => o.id === outputId && isMarkdown(o.path));
  if (!output) return null;
  const key = `${runId}/${output.path}`;
  if (!(key in c.texts)) c.texts[key] = String(await api("GET", `/api/runs/${runId}/files/${filePath(output.path)}`));
  return c.texts[key];
}

async function drawCompare() {
  const c = reader.compare, seq = reader.seq;
  if (!c) return;
  const outputs = runResults(c.run).filter((o) => isMarkdown(o.path));
  fill($("#reader-tools"), viewToggle(drawCompare), h("label", {class: "check small compare-diff"},
    h("input", {type: "checkbox", checked: c.diff, disabled: reader.view !== "formatted", onchange: (e) => { c.diff = e.target.checked; drawCompare(); }}),
    S("compare_diff")));
  if (!c.others.length) {
    fill($("#reader-body"), h("p", {class: "notice reader-pane"}, S("compare_none")));
    return;
  }
  const label = (r) => `${fmtTime(r.created)} · ${capital(S("status_" + r.status))} · ${r.id}`;
  const runSelect = h("select", {id: "compare-run", onchange: (e) => { c.otherId = e.target.value; drawCompare(); }},
    c.others.map((r) => h("option", {value: r.id}, label(r))));
  runSelect.value = c.otherId;
  const outputSelect = outputs.length > 1 ? h("select", {id: "compare-output", onchange: (e) => { c.outputId = e.target.value; drawCompare(); }},
    outputs.map((o) => h("option", {value: o.id}, L(o.label) || o.id))) : null;
  if (outputSelect) outputSelect.value = c.outputId;
  const bar = h("div", {class: "reader-bar row"},
    h("label", {class: "row", for: "compare-run"}, h("span", {class: "small muted"}, S("compare_with")), runSelect),
    outputSelect ? h("label", {class: "row", for: "compare-output"}, h("span", {class: "small muted"}, S("compare_output")), outputSelect) : null);
  fill($("#reader-body"), bar, h("p", {class: "muted reader-pane"}, S("loading")));
  let mine, theirs;
  try { [mine, theirs] = await Promise.all([compareText(c.run.id, c.outputId), compareText(c.otherId, c.outputId)]); }
  catch (err) {
    if (seq === reader.seq && reader.compare === c) fill($("#reader-body"), bar, h("div", {class: "notice bad reader-pane"}, err.message));
    return;
  }
  if (seq !== reader.seq || reader.compare !== c || runSelect.value !== c.otherId) return;
  const other = c.runs[c.otherId];
  const marks = (text, against) => {
    if (!c.diff || text == null || against == null) return null;
    const set = new Set(Markdown.blocks(against));
    return (src) => !set.has(src);
  };
  const column = (r, title, text, against) => h("section", {class: "compare-col"},
    h("div", {class: "compare-head"}, h("b", {}, title), h("span", {class: "small muted"}, fmtTime(r.started || r.created)), badge(r.status)),
    text == null ? h("p", {class: "muted reader-pane"}, S("compare_missing")) : resultView(text, true, marks(text, against)));
  fill($("#reader-body"), bar,
    mine != null && mine === theirs ? h("p", {class: "small muted reader-status"}, S("compare_same")) : null,
    h("div", {class: "compare-grid"}, column(c.run, S("compare_this"), mine, theirs), column(other, S("compare_other"), theirs, mine)));
}

// --- a server older than the files on disk -----------------------------------------------------------
// The page and its scripts are read from disk at each request; the Python code and the texts are those of the running
// server. When the code changed after the server started, the page says so until the server is started again.
async function checkStale() {
  let stale = false;
  try {
    const res = await fetch("/api/version", {cache: "no-store"});
    stale = res.status === 404 || (res.ok && (await res.json()).stale === true);  // 404: a server older than this check
  } catch { return; }  // the server is not reachable now: nothing to say about its age
  $("#stale-banner").hidden = !stale;
}

// "Restart" on the banner: the server starts again with the code on disk (POST /api/restart; refused while a run goes
// on), then the page is loaded again. A server older than this button answers 404: it is restarted by hand once.
async function restartServer(button) {
  button.disabled = true;
  button.textContent = S("stale_restarting");
  const again = () => { button.disabled = false; button.textContent = S("stale_restart"); };
  try { await api("POST", "/api/restart", {}); } catch (err) {
    again();
    return toast(err.status === 404 ? S("stale_manual") : err.message, true);
  }
  for (let i = 0; i < 60; i++) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    try {
      const res = await fetch("/api/version", {cache: "no-store"});
      if (res.ok && (await res.json()).stale === false) return location.reload();
    } catch { /* not up yet */ }
  }
  again();
  toast(S("stale_manual"), true);
}

// --- start ---------------------------------------------------------------------------------------
async function boot() {
  checkStale();
  setInterval(checkStale, 20000);
  $("#stale-restart").addEventListener("click", (e) => restartServer(e.currentTarget));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) checkStale(); });
  // The height of the header, for the screens that fill the window (the editor) and the sticky parts below it.
  new ResizeObserver(() => document.documentElement.style.setProperty("--top-h", $("#top").offsetHeight + "px")).observe($("#top"));
  let types;
  const registry = await api("GET", "/api/languages");
  LANGUAGES = registry.languages;
  UI_LANGS = registry.ui;
  if (!UI_LANGS.includes(LANG)) LANG = "en";
  [UI, INFO, types] = await Promise.all([api("GET", "/api/strings"), api("GET", "/api/info"), api("GET", "/api/node-types")]);
  NODE_TYPES = Object.fromEntries(types.map((nt) => [nt.type, nt]));
  const ready = recall("mehteran.ready");
  state.ready = ready === null ? null : ready === "1";
  applyStaticTexts();
  document.querySelectorAll(".tabs .tab").forEach((t) => t.addEventListener("click", () => go(t.dataset.tab)));
  $(".tabs").addEventListener("keydown", (e) => {
    const tabs = [...$(".tabs").querySelectorAll(".tab")];
    const index = tabs.indexOf(e.target);
    if (index < 0) return;
    const direction = document.documentElement.dir === "rtl" ? -1 : 1;
    const offsets = {ArrowLeft: -direction, ArrowRight: direction, Home: -index, End: tabs.length - 1 - index};
    if (!(e.key in offsets)) return;
    e.preventDefault();
    const next = tabs[(index + offsets[e.key] + tabs.length) % tabs.length];
    next.focus();
    go(next.dataset.tab);
  });
  document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => go(b.dataset.goto)));
  $("#brand").addEventListener("click", (e) => { e.preventDefault(); go(home()); });
  $("#video-settings-details").addEventListener("toggle", (e) => { if (e.currentTarget.open) loadVideoSettings(); });
  $("#tools-refresh").addEventListener("click", () => { loadTools(); loadLocal(); loadProviders(true); });
  $("#reader-close").addEventListener("click", () => $("#reader").close());
  $("#template-search").addEventListener("input", (e) => { state.tplQuery = e.target.value; renderLibrary(); });
  $("#template-import").addEventListener("click", () => go("workflows/import"));
  // The drawer closed by Esc: back to the library address.
  $("#drawer").addEventListener("close", () => { if (/^workflows\/(builtin|user|import)/.test(state.hash)) go("workflows"); });
  $("#drawer").addEventListener("click", (e) => { if (e.target === e.currentTarget) go("workflows"); });  // the backdrop
  setUpActivity();  // live.js: the header's indicator of what runs now
  setUpUsageChip();  // live.js: the header's remaining usage of each AI tool
  document.querySelectorAll("[data-icon]").forEach((el) => el.replaceWith(iconTile(el.dataset.icon)));  // live.js
  setUpFooter();  // live.js: the footer (version, data folder, the guide)
  document.addEventListener("keydown", (e) => {
    if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || document.querySelector("dialog[open]")) return;
    const target = e.target;
    if (target.closest && target.closest("input, textarea, select, [contenteditable='true']")) return;
    const search = $("#template-search");
    if (!search || search.offsetParent === null) return;
    e.preventDefault();
    search.focus();
    search.select();
  });
  window.addEventListener("hashchange", route);
  window.addEventListener("beforeunload", (e) => { if (window.Editor && Editor.dirty()) { e.preventDefault(); e.returnValue = ""; } });
  Editor.init();
  await route();
  if (state.tab !== "setup") api("GET", "/api/tools").then((data) => setReady(toolsReady(data))).catch(() => {});
}

boot().catch((err) => { document.getElementById("toast").hidden = false; document.getElementById("toast").textContent = err.message; });
