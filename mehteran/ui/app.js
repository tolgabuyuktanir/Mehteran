// Mehteran web interface: vanilla JavaScript, no build step, the same design as the translation app's interface
// (pipeline/ui). Every element is made with h() and text nodes: no HTML strings, so no text (a model's answer, a
// template) can become markup. Tabs and screens are chosen by the address hash:
//   #workflows/translation[/books|workflow|prompts]   the book translation: the translation app's own interface
//                                           (/tr/app.js, mounted here; the old #translation[/...] leads there)
//   #workflows                              the workflow library        #workflows/<source>/<id>   one workflow (drawer)
//   #workflows/import                       import a YAML file          #workflows/new             a new workflow
//   #workflows/edit/<source>/<id>           the visual editor (a built-in opens as your own unsaved copy)
//   #runs  #runs/<run>                      the run history and one run (live)
//   #setup                                  tools, installs and sign-ins
// The addresses of earlier versions still work: #templates[/...], #workflow/..., #runs/new/<source>/<id>.
// A run starts from the run dialog (openRun): from a library card, a workflow's drawer or the editor.
"use strict";

const TOKEN_META = document.querySelector('meta[name="token"]');
let TOKEN = TOKEN_META.content;
const FINAL = new Set(["succeeded", "failed", "cancelled", "interrupted"]);
const RETRYABLE = new Set(["failed", "rejected", "skipped", "cancelled", "interrupted"]);
const TABS = ["workflows", "runs", "setup"];
const TR_TABS = ["books", "workflow", "prompts"];
// LANG: the interface language; LANGUAGES: the language registry (GET /api/languages: code, native, english, flag,
// dir); UI_LANGS: the codes the interface can be shown in. A text that LANG has no translation for is shown in English.
let LANG = "tr", LANGUAGES = [], UI_LANGS = ["tr", "en"];
try { LANG = localStorage.getItem("mehteran.lang") || (navigator.language || "en").slice(0, 2).toLowerCase(); } catch { /* no storage */ }
let UI = {}, INFO = null, NODE_TYPES = {};  // NODE_TYPES: GET /api/node-types by type, in the server's order
const state = {tab: "", toolPoll: null, runPoll: null, signInUntil: 0, templates: [], tplQuery: "", tplCategory: "",
  runCanvas: null, selectedNode: null, hash: "", trTab: "books", tr: null, trLang: "", trStrings: {}, trBooks: null, trBooksAt: 0};

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
// A status word starts with a capital in a badge (as in the book translation); in a sentence it stays as written.
const capital = (text) => text.charAt(0).toLocaleUpperCase(LANG) + text.slice(1);
const badge = (status) => h("span", {class: "badge " + (STATUS_TONE[status] || "")}, capital(S("status_" + status)));
const typeLabel = (type) => L(NODE_TYPES[type] && NODE_TYPES[type].label) || type;
const GLYPH = {"document.extract": "¶", "ai.cli": "✦", "text.merge": "⊕", "approval": "✓", "document.export": "⇩",
  "condition": "◇", "ai.map": "↻"};
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
  // Mehteran's own elements; the book translation's (.tr-app) have the translation app's texts.
  const own = (sel) => [...document.querySelectorAll(sel)].filter((el) => !el.closest(".tr-app"));
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
  if (first === "translation") return ["workflows", "translation", ...rest];  // the book translation is a workflow now
  if (first === "workflow") return !rest.length ? ["workflows"] : rest[0] === "new" ? ["workflows", "new"] : ["workflows", "edit", ...rest];
  return parts;
}

async function route() {
  let parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  let runFrom = null;  // #runs/new/<source>/<id>: the run dialog over the run list
  if (parts[0] === "runs" && parts[1] === "new" && parts.length === 4) { runFrom = parts.slice(2); parts = ["runs"]; }
  parts = current(parts);
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
  const translating = tab === "workflows" && parts[1] === "translation";
  document.body.classList.toggle("fill", editing);
  document.body.classList.toggle("editing", editing);
  clearTimeout(state.toolPoll);
  clearTimeout(state.runPoll);
  clearTimeout(state.localPoll);
  document.querySelectorAll(".tabs .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tab);
    t.setAttribute("aria-selected", String(t.dataset.tab === tab));
  });
  document.querySelectorAll("main > .panel").forEach((p) => (p.hidden = p.id !== tab));
  $("#setup-banner").hidden = state.ready || !(tab === "runs" || (tab === "workflows" && !editing && !translating));
  if (!(tab === "workflows" && parts.length > 1 && !editing && !translating)) closeDrawer();
  try {
    if (tab === "setup") { loadLocal(); await loadTools(); }
    else if (tab === "runs") await showRuns(parts.slice(1));
    else await showWorkflows(parts.slice(1));
  } catch (err) {
    toast(err.message, true);
  }
  if (runFrom) openRun(runFrom[0], runFrom[1]);
}

// --- the book translation: the translation app's own interface (pipeline/ui/app.js, served as /tr/app.js) -----
// Mounted once and kept: an open book or a text being edited stays while other tabs are used. Its requests go to
// /api/tr/ of this server (mehteran/translation.py) with this page's session key; its links to Setup open Mehteran's
// Setup tab; Mehteran's language switch changes it too.
function setSubtabs(sub) {
  document.querySelectorAll("#translation .subtab").forEach((b) => {
    b.classList.toggle("active", b.dataset.sub === sub);
    b.setAttribute("aria-selected", String(b.dataset.sub === sub));
  });
}

// The address follows the section the translation app shows (it can refuse to leave a text with unsaved changes).
function trShown(name) {
  state.trTab = name;
  setSubtabs(name);
  if (!state.hash.startsWith("workflows/translation")) return;
  state.hash = "workflows/translation/" + name;
  if (location.hash !== "#" + state.hash) history.replaceState(null, "", "#" + state.hash);
}

// The book translation's texts in a language other than Turkish and English (those two are in its own file).
async function trStrings(lang) {
  if (lang === "tr" || lang === "en") return null;
  if (!(lang in state.trStrings)) {
    try {
      const res = await fetch(`/tr/locales/${lang}.json`);
      state.trStrings[lang] = res.ok ? await res.json() : {};
    } catch { state.trStrings[lang] = {}; }
  }
  return state.trStrings[lang];
}

async function showTranslation(parts) {
  const sub = TR_TABS.includes(parts[0]) ? parts[0] : state.trTab;
  const info = INFO.translation;
  if (!info.running || !window.TranslationUI) {
    setSubtabs(sub);
    fill($("#translation-body"), h("div", {class: "tr-message"}, h("div", {class: "notice warn"},
      h("b", {}, S(info.error || "translation_not_started", {error: info.detail || ""})))));
    return;
  }
  const lang = LANG, strings = await trStrings(lang);
  if (!state.tr) {
    state.trLang = lang;
    state.tr = TranslationUI.mount($("#translation-body"), {apiBase: "/api/tr", token: () => TOKEN, refreshToken, lang, strings,
      tabs: TR_TABS, initial: sub, onTab: trShown, onSetup: () => go("setup"), toast});
  } else {
    if (state.trLang !== lang) { state.trLang = lang; state.tr.setLang(lang, strings); }
    state.tr.show(sub);
  }
  trShown(state.tr.tab());
}

// --- setup (the same tools, installs and sign-ins as the translation app) ---------------------------
async function loadTools() {
  clearTimeout(state.toolPoll);
  if (!$("#tools").children.length) fill($("#tools"), skeleton("tools"));  // live.js
  let data;
  try { data = await api("GET", "/api/tools"); } catch (e) {
    if (state.toolsBusy && state.tab === "setup") state.toolPoll = setTimeout(loadTools, 5000);
    else toast(e.message, true);
    return;
  }
  if (state.tab !== "setup") return;
  fill($("#onboarding"), ...onboarding(data));
  setReady(toolsReady(data));
  fill($("#tools"), ...data.tools.map((tool) => toolCard(tool, data.terminal)));
  fillUsageSlots();  // live.js: the usage of each AI tool
  $("#config-note").replaceChildren(S("config_note", {path: (INFO && INFO.config_source) || "config.toml"}));
  state.toolsBusy = data.tools.some((tool) => tool.job && tool.job.running) || Boolean(data.all_job && data.all_job.running);
  const watchingSignIn = state.signInUntil > Date.now() && data.tools.some((tool) => tool.installed && !tool.signed_in);
  if (state.toolsBusy) state.toolPoll = setTimeout(loadTools, 2500);
  else if (watchingSignIn) state.toolPoll = setTimeout(loadTools, 4000);
}

// A sign-in is needed for the tools that a template or the translation workflow uses.
const neededTools = (data) => data.tools.filter((tool) => tool.templates.length || tool.translation);
const toolsReady = (data) => data.tools.every((tool) => !tool.required || tool.installed) && neededTools(data).every((tool) => tool.signed_in);

function setReady(ready) {
  state.ready = ready;
  remember("mehteran.ready", ready ? "1" : "");
  $("#setup-banner").hidden = ready || !(state.tab === "runs" || (state.tab === "workflows" && !isEditorHash(state.hash)));
}

function onboarding(data) {
  const required = data.tools.filter((tool) => tool.required);
  const installed = required.filter((tool) => tool.installed).length;
  const needed = neededTools(data);
  const signedIn = needed.filter((tool) => tool.signed_in).length;
  const job = data.all_job, installing = Boolean(job && job.running);
  const steps = [
    {done: installed === required.length && !installing, title: S("step_install"), detail: S("step_install_done", {done: installed, total: required.length}),
      body: [h("p", {class: "small muted"}, S("step_install_hint")),
        h("div", {class: "row"}, h("button", {type: "button", class: "btn primary", disabled: installing, onclick: async (e) => {
          await act(e.currentTarget, () => api("POST", "/api/tools/install-missing"));
          loadTools();
        }}, S(installing ? "installing_all" : "install_missing"))),
        job ? h("pre", {class: "log"}, job.log.slice(-4000)) : null]},
    {done: signedIn === needed.length, title: S("step_signin"), detail: S("step_signin_done", {done: signedIn, total: needed.length}),
      body: [h("p", {class: "small muted"}, S(state.signInUntil > Date.now() ? "watching_signin" : "step_signin_hint"))]},
    {done: data.runs > 0, title: S("step_run"), detail: S("step_run_done", {count: data.runs}),
      body: [h("div", {class: "row"}, h("button", {type: "button", class: "btn primary", onclick: () => go("workflows")}, S("go_workflows")))]},
  ];
  const now = steps.findIndex((st) => !st.done);
  const doneLine = h("div", {class: "ready-line"}, h("span", {class: "jnode done", "aria-hidden": "true"}, "✓"),
    h("div", {}, h("b", {}, S("all_done"))),
    h("div", {class: "row"}, h("button", {type: "button", class: "btn", onclick: () => go("workflows/translation")}, S("go_translation")),
      h("button", {type: "button", class: "btn primary", onclick: () => go("workflows")}, S("go_workflows"))));
  if (now === -1) return [doneLine];
  return [h("h3", {}, S("start_title")), h("p", {class: "muted"}, S("start_intro")),
    h("ol", {class: "onboard"}, steps.map((st, i) => h("li", {class: `onboard-step ${st.done ? "done" : ""} ${i === now ? "current" : ""} ${i > now ? "later" : ""}`},
      h("span", {class: "check", "aria-hidden": "true"}, st.done ? "✓" : String(i + 1)),
      h("div", {class: "stack"}, h("div", {}, h("b", {}, st.title), " ", h("span", {class: "muted small"}, st.detail)),
        i === now ? st.body : null))))];
}

function toolCard(tool, terminal) {
  const job = tool.job, running = job && job.running;
  const id = encodeURIComponent(tool.id);
  const actions = [];
  const keyForm = h("form", {class: "keyform", hidden: true, onsubmit: async (e) => {
    e.preventDefault();
    const input = $("input", e.currentTarget);
    await act($("button", e.currentTarget), () => api("POST", `/api/tools/${id}/login`, {method: "key", key: input.value}));
    input.value = "";
    loadTools();
  }}, h("input", {type: "password", placeholder: S("api_key"), "aria-label": S("api_key"), autocomplete: "off", required: true}),
  h("button", {type: "submit", class: "btn primary"}, S("save")));
  if (!tool.installed || (job && !running && job.code !== 0)) {
    actions.push(h("button", {type: "button", class: "btn primary", disabled: running, onclick: async (e) => {
      await act(e.currentTarget, () => api("POST", `/api/tools/${id}/install`));
      loadTools();
    }}, S(running ? "installing" : "install")));
  }
  if (tool.installed && tool.provider) {
    const main = tool.signed_in ? "" : " primary";
    const login = async (e, method) => {
      const r = await act(e.currentTarget, () => api("POST", `/api/tools/${id}/login`, {method}));
      if (r) state.signInUntil = Date.now() + 2 * 60 * 1000;
      loadTools();
    };
    if (tool.id === "gemini") actions.push(h("button", {type: "button", class: "btn" + main, onclick: (e) => login(e, "google")}, S("with_google")));
    else actions.push(h("button", {type: "button", class: "btn" + main, disabled: !terminal, onclick: (e) => login(e, "terminal")},
      S({codex: "with_chatgpt", antigravity: "with_google"}[tool.id] || "with_claude")));
    if (["codex", "gemini"].includes(tool.id)) actions.push(h("button", {type: "button", class: "btn", onclick: () => {
      keyForm.hidden = !keyForm.hidden;
      if (!keyForm.hidden) $("input", keyForm).focus();
    }}, S("with_key")));
    if (tool.signed_in) actions.push(h("button", {type: "button", class: "btn", onclick: async (e) => {
      const b = e.currentTarget;
      b.textContent = S("testing");
      await act(b, () => api("POST", `/api/tools/${id}/test`));
      b.textContent = S("test");
    }}, S("test")));
  }
  // Who uses the tool: the translation workflow, then the templates.
  const names = [...(tool.translation ? [S("translation_card_title")] : []), ...(tool.templates || [])];
  const uses = !tool.provider ? S("pdf_uses") : !tool.configured ? S("not_configured")
    : names.length ? S("used_by", {names: names.slice(0, 3).join(", ") + (names.length > 3 ? " " + S("and_more", {count: names.length - 3}) : "")})
    : S("not_used");
  const q = tool.quota;
  const quota = q && q.since ? (q.until > Date.now() / 1000 && !(q.cleared > q.since)
    ? h("div", {class: "notice warn small"}, S("quota_now", {time: fmtTime(q.until)}))
    : h("div", {class: "small muted"}, S("quota_last", {time: fmtTime(q.since)}))) : null;
  return h("article", {class: "card tool", "data-id": tool.id},
    h("div", {class: "tool-head"}, h("h3", {}, tool.name), h("span", {class: "muted small"}, tool.version)),
    h("div", {class: "badges"},
      need(tool.required),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.installed && tool.provider ? h("span", {class: "badge " + (tool.signed_in ? "good" : "warn")},
        S(tool.signed_in ? "signed_in" : "not_signed_in") + (tool.signed_in && tool.sign_in_info ? " · " + tool.sign_in_info : "")) : null),
    h("div", {class: "uses"}, uses),
    h("div", {class: "small muted"}, tool.requirements),
    tool.installed && !tool.signed_in && tool.sign_in_help ? h("div", {class: "small"}, tool.sign_in_help) : null,
    quota,
    tool.provider ? usageSlot(tool.provider) : null,
    !terminal && tool.installed && !tool.signed_in && tool.provider ? h("p", {class: "small muted"}, S("run_command", {command: tool.login_command})) : null,
    keyForm,
    job ? h("pre", {class: "log"}, job.log.slice(-4000)) : null,
    h("div", {class: "actions"}, actions));
}

// A provider whose models run on this computer (Ollama).
const localTag = (p) => (p && p.local ? h("span", {class: "local-tag", title: S("local_hint")}, S("local")) : null);
// "Required" for the tools that the templates or the translation use (and the PDF reader); "optional" otherwise.
const need = (required) => h("span", {class: "need " + (required ? "required" : "optional")}, S(required ? "need_required" : "need_optional"));
const GB = 1024 * 1024 * 1024;
const gb = (bytes) => (bytes == null ? "–" : bytes >= GB ? `${(bytes / GB).toFixed(1)} GB` : fileSize(bytes));

// A confirmation in a dialog of the page (not the browser's confirm()): a title, lines of facts and two buttons.
function askConfirm(title, lines, ok) {
  const dialog = $("#confirm-dialog");
  return new Promise((resolve) => {
    const done = (answer) => { dialog.close(); resolve(answer); };
    fill(dialog, h("form", {method: "dialog", onsubmit: (e) => { e.preventDefault(); done(true); }},
      h("div", {class: "dialog-head"}, h("h3", {id: "confirm-title"}, title)),
      h("div", {class: "layout-body stack"}, lines.filter(Boolean).map((line) => h("p", {class: "small"}, line))),
      h("div", {class: "dialog-foot row"},
        h("button", {type: "button", class: "btn", onclick: () => done(false)}, S("cancel_action")),
        h("button", {type: "submit", class: "btn primary"}, ok))));
    dialog.addEventListener("cancel", () => resolve(false), {once: true});
    dialog.showModal();
    $("button.primary", dialog).focus();
  });
}

// --- setup: local models (Ollama) and text recognition (Tesseract OCR); both optional --------------------
async function loadLocal() {
  clearTimeout(state.localPoll);
  const seq = state.localSeq = (state.localSeq || 0) + 1;  // only the latest answer is drawn
  let data, models = null;
  try {
    data = await api("GET", "/api/local-tools");
    const ollama = data.tools.find((x) => x.id === "ollama");
    if (ollama.installed || ollama.running) models = await api("GET", "/api/ollama/models");
  } catch (e) {
    fill($("#local-tools"), problemsBox(e));
    return;
  }
  if (state.tab !== "setup" || seq !== state.localSeq) return;
  const pull = data.pull || {};
  const pulling = pull.name && !pull.done;
  // A finished download changes the models offered by the editor and the run window.
  if (state.pulling && !pulling) api("GET", "/api/info").then((info) => { INFO = info; }).catch(() => {});
  state.pulling = pulling;
  const [ollama, ocr] = [data.tools.find((x) => x.id === "ollama"), data.tools.find((x) => x.id === "ocr")];
  fill($("#local-tools"),
    h("div", {class: "panel-head local-head"}, h("div", {}, h("h2", {}, S("local_title")), h("p", {class: "muted"}, S("local_intro")))),
    h("div", {class: "local-grid"}, ollamaCard(ollama, models, pull), ocrCard(ocr),
      ...["typst", "pandoc", "speech", "qpdf"].map((id) => localToolCard(data.tools.find((x) => x.id === id)))));
  // An install job: the whole section again (its log grows). A download: only its progress line, so that the
  // buttons stay in place (a click on Cancel is not lost to a redraw); the section again when it ends.
  const jobs = data.tools.flatMap((x) => [x.job, x.languages_job, x.models_job]);
  if (jobs.some((j) => j && j.running)) state.localPoll = setTimeout(loadLocal, 1500);
  else if (pulling) state.localPoll = setTimeout(pollPull, 1000);
}

async function pollPull() {
  let pull;
  try { pull = await api("GET", "/api/ollama/pull"); } catch { state.localPoll = setTimeout(pollPull, 3000); return; }
  if (state.tab !== "setup") return;
  if (!pull.name || pull.done || !$(".pull-box")) return loadLocal();
  $(".pull-box .pull-text").textContent = pullText(pull);
  $(".pull-box .fill").style.width = (pull.percent || 0) + "%";
  $(".pull-box progress").value = pull.percent || 0;
  state.localPoll = setTimeout(pollPull, 1000);
}

const pullText = (pull) => (pull.error ? pull.error : pull.cancelled ? S("pull_cancelled") : pull.done ? S("pull_done")
  : `${pull.status || ""} · ${gb(pull.completed)} / ${gb(pull.total)} · ${Math.round(pull.percent || 0)}%`);

function jobBox(job, cancelKey) {
  if (!job) return null;
  return h("div", {class: "stack"}, h("pre", {class: "log"}, job.log.slice(-4000)),
    job.running ? h("div", {class: "row"}, h("button", {type: "button", class: "btn small danger", onclick: async (e) => {
      await act(e.currentTarget, () => api("POST", `/api/local-tools/${cancelKey}/cancel`));
      loadLocal();
    }}, S("cancel"))) : null);
}

function sourceText(tool) {
  return tool.source === "system" ? S("source_system") : tool.source === "mehteran" ? S("source_mehteran") : "";
}

function ollamaCard(tool, models, pull) {
  const running = tool.job && tool.job.running;
  const install = async (e) => {
    const ok = await askConfirm(S("ollama_install_title"), [
      S("ollama_install_what", {version: tool.pinned_version}),
      S("ollama_install_source"),
      S("install_where", {path: tool.install_dir}),
      S("disk_free_line", {free: gb(tool.disk_free)})], S("install"));
    if (!ok) return;
    await act(e.currentTarget, () => api("POST", "/api/local-tools/ollama/install"));
    loadLocal();
  };
  return h("article", {class: "card tool local-tool", "data-id": "ollama"},
    h("div", {class: "tool-head"}, h("h3", {}, tool.name), h("span", {class: "muted small"}, tool.version || "")),
    h("div", {class: "badges"}, need(false),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.installed || tool.running ? h("span", {class: "badge " + (tool.running ? "good" : "")}, S(tool.running ? "ollama_running" : "ollama_stopped")) : null,
      tool.source ? h("span", {class: "badge"}, sourceText(tool)) : null),
    h("p", {class: "small muted"}, S("ollama_about")),
    h("p", {class: "small notice warn"}, S("ollama_honest")),
    h("p", {class: "small muted"}, S("memory_line", {ram: gb(tool.memory), free: gb(tool.disk_free)}),
      tool.installed ? [" · ", S("models_dir_line", {path: tool.models_dir})] : null),
    jobBox(tool.job, "ollama"),
    !tool.installed || (tool.job && !running && tool.job.code !== 0)
      ? h("div", {class: "actions"}, h("button", {type: "button", class: "btn primary", disabled: running, onclick: install}, S(running ? "installing" : "install"))) : null,
    models ? modelManager(models, pull) : null);
}

function modelManager(models, pull) {
  const pulling = pull.name && !pull.done;
  const tooBig = (m) => (models.memory && m.ram > models.memory ? S("too_big_ram", {ram: gb(m.ram), have: gb(models.memory)})
    : models.disk_free != null && m.size > models.disk_free ? S("too_big_disk", {size: gb(m.size), free: gb(models.disk_free)}) : "");
  const start = async (button, name, force) => {
    try {
      const res = await api("POST", "/api/ollama/pull", {name, force: Boolean(force)});
      if (res.warnings && res.warnings.length) toast(res.warnings.join(" "));
    } catch (err) {
      if (err.status === 409 && err.problems.length && !force) {
        if (await askConfirm(err.message, err.problems, S("pull_anyway"))) return start(button, name, true);
      } else toast(err.message, true);
    }
    loadLocal();
  };
  const custom = h("input", {type: "text", class: "mono", placeholder: "qwen2.5:7b", "aria-label": S("custom_model"), spellcheck: "false",
    pattern: "[A-Za-z0-9][A-Za-z0-9._\\-]{0,63}(/[A-Za-z0-9][A-Za-z0-9._\\-]{0,63})?(:[A-Za-z0-9][A-Za-z0-9._\\-]{0,63})?", required: true});
  const progress = pull.name ? h("div", {class: "pull-box", role: "status"},
    h("div", {class: "row"}, h("b", {}, pull.name), h("span", {class: "small muted grow pull-text"}, pullText(pull)),
      pulling ? h("button", {type: "button", class: "btn small danger", onclick: async (e) => { await act(e.currentTarget, () => api("POST", "/api/ollama/pull/cancel")); loadLocal(); }}, S("cancel")) : null),
    h("div", {class: "track", "aria-hidden": "true"}, h("div", {class: "fill" + (pull.error ? " failed" : pull.cancelled ? " stopped" : ""), "data-w": pull.done && !pull.error ? 100 : pull.percent || 0})),
    h("progress", {max: 100, value: pull.percent || 0, class: "visually-hidden", "aria-label": S("pull_progress", {name: pull.name})})) : null;
  const el = h("section", {class: "models-box stack"},
    h("h4", {}, S("models_installed")),
    models.installed.length ? h("ul", {class: "plain model-list"}, models.installed.map((m) => h("li", {class: "row"},
      h("code", {}, m.name), h("span", {class: "small muted grow"}, `${gb(m.size)}${m.modified ? " · " + fmtTime(Date.parse(m.modified) / 1000) : ""}`),
      h("button", {type: "button", class: "btn small danger", onclick: async (e) => {
        if (!confirm(S("model_delete_confirm", {name: m.name}))) return;
        if (await act(e.currentTarget, () => api("POST", "/api/ollama/delete", {name: m.name}))) { toast(S("deleted")); loadLocal(); }
      }}, S("delete")))))
      : h("p", {class: "small muted"}, S(models.running ? "no_local_models" : "ollama_not_running")),
    progress,
    h("h4", {}, S("models_recommended")),
    h("div", {class: "rec-grid"}, models.recommended.map((m) => {
      const warn = tooBig(m);
      return h("div", {class: "rec-card" + (warn ? " too-big" : "")},
        h("div", {class: "row"}, h("code", {class: "grow"}, m.name),
          m.kind === "vision" || m.kind === "embedding" ? h("span", {class: "badge"}, S(m.kind === "vision" ? "model_kind_vision" : "model_kind_embedding")) : null,
          m.installed ? h("span", {class: "badge good"}, S("installed")) : null),
        h("div", {class: "small muted"}, S("model_facts", {size: gb(m.size), ram: gb(m.ram), languages: m.languages.join(", ")})),
        h("div", {class: "small"}, L(m.notes)),
        warn ? h("div", {class: "small warn-text"}, "⚠ " + warn) : null,
        m.installed ? null : h("button", {type: "button", class: "btn small" + (warn ? "" : " primary"), disabled: pulling,
          onclick: (e) => start(e.currentTarget, m.name)}, S("download")));
    })),
    h("form", {class: "row custom-model", onsubmit: (e) => { e.preventDefault(); start($("button", e.currentTarget), custom.value.trim()); }},
      h("label", {}, S("custom_model")), custom, h("button", {type: "submit", class: "btn", disabled: pulling}, S("download"))),
    h("p", {class: "small muted"}, S("one_pull_note")));
  el.querySelectorAll(".fill[data-w]").forEach((x) => (x.style.width = x.dataset.w + "%"));
  return el;
}

function ocrCard(tool) {
  const running = tool.job && tool.job.running, langRunning = tool.languages_job && tool.languages_job.running;
  const boxes = tool.available_languages.map((l) => h("label", {class: "check"},
    h("input", {type: "checkbox", value: l.code, checked: l.installed || ["tur", "eng"].includes(l.code), disabled: l.installed}),
    h("span", {}, `${S("ocr_lang_" + l.code)} (${l.code})`), h("span", {class: "small muted"}, l.installed ? " · " + S("installed") : ` · ${gb(l.size)}`)));
  const install = async (e) => {
    const ok = await askConfirm(S("ocr_install_title"), [S("ocr_install_what", {version: tool.pinned_version}), S("ocr_install_source")], S("install"));
    if (!ok) return;
    await act(e.currentTarget, () => api("POST", "/api/local-tools/ocr/install"));
    loadLocal();
  };
  const languages = async (e) => {
    const codes = boxes.map((b) => $("input", b)).filter((i) => i.checked && !i.disabled).map((i) => i.value);
    if (!codes.length) return toast(S("ocr_pick_languages"), true);
    await act(e.currentTarget, () => api("POST", "/api/local-tools/ocr-languages/install", {languages: codes}));
    loadLocal();
  };
  return h("article", {class: "card tool local-tool", "data-id": "ocr"},
    h("div", {class: "tool-head"}, h("h3", {}, tool.name), h("span", {class: "muted small"}, tool.version || "")),
    h("div", {class: "badges"}, need(false),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.source ? h("span", {class: "badge"}, sourceText(tool)) : null,
      tool.pdftoppm ? null : h("span", {class: "badge warn"}, S("ocr_no_poppler"))),
    h("p", {class: "small muted"}, S("ocr_about")),
    jobBox(tool.job, "ocr"),
    !tool.installed || (tool.job && !running && tool.job.code !== 0)
      ? h("div", {class: "actions"}, h("button", {type: "button", class: "btn primary", disabled: running, onclick: install}, S(running ? "installing" : "install"))) : null,
    tool.installed ? h("fieldset", {class: "plain stack"}, h("legend", {}, S("ocr_languages_title")), boxes,
      h("p", {class: "small muted"}, S("ocr_ottoman_note")),
      h("div", {class: "row"}, h("button", {type: "button", class: "btn", disabled: langRunning, onclick: languages}, S("ocr_install_languages"))),
      jobBox(tool.languages_job, "ocr-languages")) : null);
}

// Typst, Pandoc, speech to text (whisper.cpp + ffmpeg) and qpdf: one card each, as the OCR card (install with a
// confirmation of version, size and source; the job log with cancel). Speech to text also lists its models.
const TOOL_TEXT = {
  typst: {title: "Typst", about: "typst_about", ask: "typst_install_title", what: "typst_install_what", source: "typst_install_source"},
  pandoc: {title: "Pandoc", about: "pandoc_about", ask: "pandoc_install_title", what: "pandoc_install_what", source: "pandoc_install_source"},
  speech: {title: null, about: "speech_about", ask: "speech_install_title", what: "speech_install_what", source: "speech_install_source"},
  qpdf: {title: "qpdf", about: "qpdf_about", ask: "qpdf_install_title", what: "qpdf_install_what", source: "qpdf_install_source"},
};

function localToolCard(tool) {
  if (!tool) return null;
  const text = TOOL_TEXT[tool.id];
  const running = tool.job && tool.job.running;
  const install = async (e) => {
    const ok = await askConfirm(S(text.ask), [
      S(text.what, {version: tool.pinned_version, ffmpeg: tool.ffmpeg_version || ""}),
      S(text.source),
      S("download_size_line", {size: gb(tool.download_size)}),
      tool.poppler_first ? S("poppler_first_line") : null,
      S("install_where", {path: tool.install_dir}),
      S("disk_free_line", {free: gb(tool.disk_free)})], S("install"));
    if (!ok) return;
    await act(e.currentTarget, () => api("POST", `/api/local-tools/${tool.id}/install`));
    loadLocal();
  };
  const extra = [];
  if (tool.id === "typst" && tool.installed) extra.push(h("span", {class: "badge"}, S(tool.arabic_font ? "typst_font_ok" : "typst_font_system")));
  if (tool.id === "speech" && tool.path && !tool.ffmpeg) extra.push(h("span", {class: "badge warn"}, S("speech_no_ffmpeg")));
  return h("article", {class: "card tool local-tool", "data-id": tool.id},
    h("div", {class: "tool-head"}, h("h3", {}, text.title || S("speech_title")), h("span", {class: "muted small"}, tool.version || "")),
    h("div", {class: "badges"}, need(false),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.source ? h("span", {class: "badge"}, sourceText(tool)) : null, extra),
    h("p", {class: "small muted"}, S(text.about)),
    tool.id === "speech" && tool.ffmpeg ? h("p", {class: "small muted"}, S("speech_ffmpeg_line", {path: tool.ffmpeg})) : null,
    jobBox(tool.job, tool.id),
    !tool.installed || (tool.job && !running && tool.job.code !== 0)
      ? h("div", {class: "actions"}, h("button", {type: "button", class: "btn primary", disabled: running, onclick: install}, S(running ? "installing" : "install"))) : null,
    tool.id === "speech" && tool.installed ? speechModels(tool) : null);
}

function speechModels(tool) {
  const busy = tool.models_job && tool.models_job.running;
  const boxes = tool.available_models.map((m) => h("label", {class: "check"},
    h("input", {type: "checkbox", value: m.name, checked: m.installed, disabled: m.installed}),
    h("span", {}, m.name), h("span", {class: "small muted"}, m.installed ? " · " + S("installed") : ` · ${gb(m.size)}`)));
  const download = async (e) => {
    const names = boxes.map((b) => $("input", b)).filter((i) => i.checked && !i.disabled).map((i) => i.value);
    if (!names.length) return toast(S("speech_pick_models"), true);
    await act(e.currentTarget, () => api("POST", "/api/local-tools/speech-models/install", {models: names}));
    loadLocal();
  };
  return h("fieldset", {class: "plain stack"}, h("legend", {}, S("speech_models_title")), boxes,
    h("p", {class: "small muted"}, S("speech_models_note")),
    h("div", {class: "row"}, h("button", {type: "button", class: "btn", disabled: busy, onclick: download}, S("speech_install_models"))),
    jobBox(tool.models_job, "speech-models"));
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
    const item = (state.templates || []).find((t) => `${t.source}:${t.id}` === run.template);
    if (!item || seen.has(run.template)) continue;
    seen.add(run.template);
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
  if (state.tplCategory === "~fav" ? !item.favorite : state.tplCategory === "~mine" ? item.source !== "user"
    : state.tplCategory && item.category !== state.tplCategory) return false;
  if (!q) return true;
  const both = (value) => (typeof value === "object" && value ? Object.values(value) : [value || ""]);  // tr and en
  const text = fold([item.id, item.category, categoryLabel(item.category), ...both(item.name), ...both(item.description)].join(" "));
  return q.split(/\s+/).every((word) => text.includes(word));
}

async function showWorkflows(parts) {
  const editing = parts[0] === "new" || (parts[0] === "edit" && parts.length === 3);
  const translating = parts[0] === "translation";
  $("#library").hidden = editing || translating;
  $("#workflow-editor").hidden = !editing;
  $("#translation").hidden = !translating;
  if (translating) return showTranslation(parts.slice(1));
  if (editing) return Editor.open(parts[0] === "new" ? ["new"] : parts.slice(1));
  if (!state.templates.length) fill($("#template-grid"), skeleton("cards"));  // live.js: shapes until the list comes
  await loadTemplateList();
  renderLibrary();
  if (parts[0] === "import") return openDrawer(importView());
  if (parts.length === 2) return showTemplate(parts[0], parts[1]);
}

function renderLibrary() {
  const categories = [...new Set(state.templates.filter((t) => t.source === "builtin").map((t) => t.category || ""))]
    .sort((a, b) => categoryLabel(a).localeCompare(categoryLabel(b), LANG));
  const mine = state.templates.filter((t) => t.source === "user").length;
  const favorites = state.templates.filter((t) => t.favorite);
  const favCount = favorites.length + (INFO.translation.favorite ? 1 : 0);  // the book translation can be a favorite too
  if (state.tplCategory === "~fav" && !favCount) state.tplCategory = "";
  const chip = (value, label, count) => h("button", {type: "button", class: "pick", "aria-pressed": String(state.tplCategory === value),
    onclick: () => { state.tplCategory = value; renderLibrary(); }}, label, h("span", {class: "count"}, " " + count));
  fill($("#template-filters"), h("div", {class: "pick-chips cat-filter", role: "group", "aria-label": S("filter_category")},
    chip("", S("all"), state.templates.length + 1),  // + the book translation, pinned above
    favCount ? chip("~fav", "★ " + S("favorites"), favCount) : null,
    mine ? chip("~mine", S("my_templates"), mine) : null,
    categories.map((c) => chip(c, categoryLabel(c), state.templates.filter((t) => t.category === c && t.source === "builtin").length))));
  $("#template-search").value = state.tplQuery;
  const visible = state.templates.filter(templateMatches);
  const pinned = translationMatches() ? translationCard() : null;
  $("#library-count").textContent = S("count_templates", {count: visible.length + (pinned ? 1 : 0)});
  // Under the book translation: the favorites, then the workflows run last (not while a category or a search is chosen).
  const plain = !state.tplCategory && !state.tplQuery.trim();
  const favs = plain ? favorites : [];
  const recent = plain ? recentTemplates() : [];
  fill($("#template-grid"), pinned ? h("section", {class: "lib-group lib-pinned"}, h("h3", {class: "lib-group-title"}, S("pinned")),
    h("div", {class: "lib-grid"}, pinned)) : null,
    favs.length ? h("section", {class: "lib-group lib-favorites"}, h("h3", {class: "lib-group-title"}, "★ " + S("favorites"),
      h("span", {class: "muted small"}, S("count_templates", {count: favs.length}))), h("div", {class: "lib-grid"}, favs.map(templateCard))) : null,
    recent.length ? h("section", {class: "lib-recent"}, h("h3", {class: "lib-group-title"}, S("recently_used")),
      h("div", {class: "recent-row"}, recent.map(({item, at}) => h("span", {class: "recent-chip"},
        h("button", {type: "button", class: "linkish", onclick: () => go(`workflows/${item.source}/${item.id}`)}, L(item.name) || item.id,
          h("span", {class: "small muted"}, " · " + fmtTime(at))),
        h("button", {type: "button", class: "icon-btn", disabled: !item.valid, "aria-label": S("run") + ": " + (L(item.name) || item.id),
          title: S("run"), onclick: () => openRun(item.source, item.id)}, "▶"))))) : null,
    visible.length || pinned ? templateGroups(visible).map((g) => h("section", {class: "lib-group"},
    h("h3", {class: "lib-group-title"}, g.label, h("span", {class: "muted small"}, S("count_templates", {count: g.items.length}))),
    h("div", {class: "lib-grid"}, g.items.map(templateCard))))
    : h("div", {class: "empty"}, S("no_templates_match")));
  staggerOnce($("#template-grid"));  // live.js: the cards come in one after the other, the first time
}

// The book translation: the translation app, pinned at the top of the library. Found by the same search, in both
// languages ("çeviri", "translation", "kitap", "book"); hidden while a category is chosen.
function translationMatches() {
  if (state.tplCategory === "~fav" ? !INFO.translation.favorite : state.tplCategory) return false;
  const q = fold(state.tplQuery.trim());
  const text = fold(["translation", "translate", ...Object.values(UI.translation_card_title || {}), ...Object.values(UI.translation_card_text || {})].join(" "));
  return !q || q.split(/\s+/).every((word) => text.includes(word));
}

// The same card as a workflow's (icon, badges, name, description; favorite and the main action below), with a book.
function translationCard() {
  const open = () => go("workflows/translation");
  const live = h("span", {class: "badge translation-live", hidden: true});
  showTranslationState(live);
  refreshTranslationState();
  const item = {source: "app", id: "translation", name: UI.translation_card_title, favorite: INFO.translation.favorite};
  return h("article", {class: "tpl-card cat-translation"},
    h("button", {type: "button", class: "tpl-open", onclick: open, "aria-label": S("details_of", {name: S("translation_card_title")})},
      h("span", {class: "tpl-head"}, iconTile("translation"), h("span", {class: "tpl-badges"}, h("span", {class: "badge good"}, S("pinned")), live)),
      h("span", {class: "tpl-name"}, S("translation_card_title")),
      h("span", {class: "tpl-desc"}, S("translation_card_text"))),
    h("div", {class: "tpl-foot"}, h("span", {class: "small muted"}, S("translation_card_meta")),
      h("span", {class: "row"},
        favoriteButton(item, () => { INFO.translation.favorite = item.favorite; renderLibrary(); }),  // live.js
        h("button", {type: "button", class: "btn small primary", onclick: open}, S("open")))));
}

// The live state of the book translation on its card: how many books, how many are being translated now.
function showTranslationState(el) {
  const books = state.trBooks;
  el.hidden = !books;
  if (!books) return;
  const running = books.filter((b) => b.running).length;
  el.textContent = running ? S("translation_running", {count: running}) : S("translation_books", {count: books.length});
  el.className = "badge translation-live" + (running ? " warn" : "");
}

async function refreshTranslationState() {
  if (!INFO.translation.running || Date.now() - state.trBooksAt < 10000) return;
  state.trBooksAt = Date.now();
  try { state.trBooks = await api("GET", "/api/tr/books"); } catch { return; }
  document.querySelectorAll(".translation-live").forEach(showTranslationState);
}

function templateCard(item) {
  const open = () => go(`workflows/${item.source}/${item.id}`);
  const kind = item.source === "user" ? "mine" : item.category || "other";
  return h("article", {class: `tpl-card cat-${kind}`},
    h("button", {type: "button", class: "tpl-open", onclick: open, "aria-label": S("details_of", {name: L(item.name) || item.id})},
      // The group heading names the category of a built-in; one of your own shows its category here.
      h("span", {class: "tpl-head"}, iconTile(kind), h("span", {class: "tpl-badges"},
        item.draft ? h("span", {class: "badge warn"}, S("draft")) : null,
        item.source === "user" && item.category ? h("span", {class: "badge"}, categoryLabel(item.category)) : null,
        item.valid || item.draft ? null : h("span", {class: "badge bad"}, S("invalid")))),
      h("span", {class: "tpl-name"}, L(item.name) || item.id),
      h("span", {class: "tpl-desc"}, L(item.description) || item.id)),
    h("div", {class: "tpl-foot"},
      h("span", {class: "small muted"}, item.valid ? S("template_meta_short", {nodes: item.nodes, inputs: item.inputs})
        : S("problems_found", {count: (item.problems || []).length})),
      h("span", {class: "row"},
        favoriteButton(item, renderLibrary),  // live.js
        h("button", {type: "button", class: "btn small", onclick: open}, S("details")),
        h("button", {type: "button", class: "btn small primary", disabled: !item.valid, title: item.valid ? null : S("run_blocked", {count: (item.problems || []).length}),
          onclick: () => openRun(item.source, item.id)}, "▶ " + S("run")))));
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

async function showTemplate(source, id) {
  const tpl = await api("GET", `/api/templates/${source}/${id}`);
  if (state.hash !== `workflows/${source}/${id}`) return;
  const copyId = h("input", {type: "text", value: `${id}-copy`, "aria-label": S("new_id"), class: "mono", spellcheck: "false"});
  const duplicate = h("form", {class: "row dup-form", hidden: true, onsubmit: async (e) => {
    e.preventDefault();
    const r = await act($("button", e.currentTarget), () => api("POST", `/api/templates/${source}/${id}/customize`, {id: copyId.value.trim()}));
    if (r) { toast(S("customized", {id: r.id})); go(`workflows/user/${r.id}`); }
  }}, h("label", {}, S("customize_as")), copyId, h("button", {class: "btn primary", type: "submit"}, S("create")));
  const inputs = (tpl.input_specs || []).map((spec) => h("li", {},
    h("b", {}, L(spec.label) || spec.id), " ", h("span", {class: "small muted"}, S("input_type_" + spec.type) + (spec.required === false ? " · " + S("optional") : "")),
    spec.description ? h("div", {class: "small muted"}, L(spec.description)) : null));
  const outputs = (tpl.outputs || []).map((o) => h("li", {}, h("b", {}, L(o.label) || o.id), " ", h("code", {}, o.from)));
  openDrawer(
    h("div", {class: "drawer-head"},
      h("div", {class: "stack"},
        h("p", {class: "row small"}, h("span", {class: "badge " + (source === "user" ? "good" : "")}, S(source === "builtin" ? "builtin" : "mine")),
          tpl.draft ? h("span", {class: "badge warn"}, S("draft")) : null,
          tpl.category ? h("span", {class: "badge"}, categoryLabel(tpl.category)) : null,
          tpl.version ? h("span", {class: "muted"}, "v" + tpl.version) : null,
          tpl.based_on ? h("span", {class: "muted"}, S("based_on") + " " + tpl.based_on) : null),
        h("h2", {id: "drawer-title"}, L(tpl.name) || id)),
      h("button", {type: "button", class: "icon-btn drawer-x", "aria-label": S("close"), title: S("close"), onclick: () => go("workflows")}, "✕")),
    tpl.description ? h("p", {class: "drawer-desc"}, L(tpl.description)) : null,
    h("div", {class: "row drawer-actions"},
      h("button", {type: "button", class: "btn primary", disabled: !tpl.valid, onclick: () => openRun(source, id)}, "▶ " + S("run")),
      favoriteButton({...(state.templates.find((t) => t.source === source && t.id === id) || {}), source, id, name: tpl.name},
        () => { renderLibrary(); showTemplate(source, id); }),
      h("button", {type: "button", class: "btn", onclick: () => go(`workflows/edit/${source}/${id}`)}, S("edit")),
      h("button", {type: "button", class: "btn", "aria-expanded": "false", onclick: (e) => {
        duplicate.hidden = !duplicate.hidden;
        e.currentTarget.setAttribute("aria-expanded", String(!duplicate.hidden));
        if (!duplicate.hidden) copyId.focus();
      }}, S("duplicate")),
      h("a", {class: "btn", href: `/api/templates/${source}/${id}/download?token=${encodeURIComponent(TOKEN)}`}, S("export_yaml")),
      source === "user" ? h("button", {type: "button", class: "btn danger", onclick: async (e) => {
        if (!confirm(S("confirm_delete", {id}))) return;
        if (await act(e.currentTarget, () => api("DELETE", `/api/templates/user/${id}`))) { toast(S("deleted")); go("workflows"); }
      }}, S("delete")) : null),
    duplicate,
    source === "builtin" ? h("p", {class: "small muted"}, S("builtin_edit_note")) : null,
    tpl.valid ? null : problemsBox({message: S(tpl.draft ? "draft_cannot_run" : "template_invalid", {count: tpl.problems.length}), problems: tpl.problems}),
    tpl.graph ? h("section", {class: "drawer-sec"}, h("h3", {}, S("graph")), previewCanvas(tpl.graph)) : null,
    inputs.length ? h("section", {class: "drawer-sec"}, h("h3", {}, S("inputs")), h("ul", {class: "plain"}, inputs)) : null,
    outputs.length ? h("section", {class: "drawer-sec"}, h("h3", {}, S("outputs")), h("ul", {class: "plain"}, outputs)) : null,
    h("details", {class: "drawer-sec placeholders"}, h("summary", {}, S("yaml_source")),
      source === "user" ? yamlEditor(tpl.yaml, id) : h("pre", {class: "code"}, tpl.yaml)));
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
          go(`workflows/user/${id}`);
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

function importView() {
  const area = h("textarea", {class: "code", spellcheck: "false", rows: 18, "aria-label": S("yaml_source")});
  const result = h("div", {"aria-live": "polite"});
  const picker = h("input", {type: "file", accept: ".yaml,.yml", "aria-label": S("import_file"), onchange: async () => {
    const file = picker.files[0];
    if (file) area.value = await file.text();
  }});
  return [h("div", {class: "drawer-head"}, h("h2", {id: "drawer-title"}, S("import_title")),
    h("button", {type: "button", class: "icon-btn drawer-x", "aria-label": S("close"), title: S("close"), onclick: () => go("workflows")}, "✕")),
  h("p", {class: "muted small"}, S("import_lede")),
  h("div", {class: "uploader"}, filePicker(picker, false)), area,
  h("div", {class: "row"},
    h("button", {type: "button", class: "btn", onclick: async () => {
      const res = await api("POST", "/api/validate", {yaml: area.value});
      result.replaceChildren(res.valid ? h("p", {class: "good-text"}, "✓ " + S("valid")) : problemsBox({message: S("problems_found", {count: res.problems.length}), problems: res.problems}));
    }}, S("validate")),
    h("button", {type: "button", class: "btn primary", onclick: async () => {
      try { const res = await api("POST", "/api/templates/import", {yaml: area.value}); toast(S("imported", {id: res.id})); go(`workflows/user/${res.id}`); }
      catch (err) { result.replaceChildren(problemsBox(err)); }
    }}, S("import"))), result];
}

// --- the run dialog: every input of a workflow, then the run starts and its page opens -----------------
function providerField(spec) {
  const providers = (INFO && INFO.providers) || [];
  const def = typeof spec.default === "string" ? spec.default : "";
  const defProvider = def.split("@")[0].split("/")[0], defModel = def.split("@")[0].split("/")[1] || "", defEffort = def.split("@")[1] || "";
  const pSel = h("select", {"aria-label": S("provider")}, providers.map((p) => h("option", {value: p.name, selected: p.name === defProvider},
    p.local ? `${p.name} (${S("local")})` : p.name)));
  const listId = "models-" + spec.id;
  const model = h("input", {type: "text", list: listId, placeholder: S("model_default"), value: defModel, class: "mono", "aria-label": S("model")});
  const datalist = h("datalist", {id: listId});
  const effort = h("select", {"aria-label": S("effort")});
  const refresh = () => {
    const p = providers.find((x) => x.name === pSel.value) || {models: [], efforts: []};
    datalist.replaceChildren(...p.models.map((m) => h("option", {value: m})));
    const keep = effort.value || defEffort;
    effort.replaceChildren(h("option", {value: ""}, S("effort_default")), ...p.efforts.map((e) => h("option", {value: e, selected: e === keep}, S("effort_" + e))));
    effort.disabled = !p.efforts.length;
  };
  const hint = usageHint();  // live.js: "5 saat: %54", in a warning colour near a limit
  pSel.addEventListener("change", () => { refresh(); hint.show(pSel.value); });
  refresh();
  loadUsage().then(() => hint.show(pSel.value));
  const wrap = h("div", {class: "provider-pick"}, pSel, model, datalist, effort, hint);
  wrap.read = () => pSel.value + (model.value.trim() ? "/" + model.value.trim() : "") + (effort.value ? "@" + effort.value : "");
  wrap.write = (value) => {
    const [base, level] = String(value).split("@");
    const [prov, ...rest] = base.split("/");
    if (!providers.some((p) => p.name === prov)) return;
    pSel.value = prov;
    refresh();
    model.value = rest.join("/");
    effort.value = level || "";
    hint.show(prov);
  };
  if (!providers.length) wrap.appendChild(h("p", {class: "small warn-text"}, S("no_providers")));
  return wrap;
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

async function openRun(source, id) {
  let tpl;
  try { tpl = await api("GET", `/api/templates/${source}/${id}`); } catch (err) { return toast(err.message, true); }
  if (!tpl.valid) return toast(S("template_invalid"), true);
  const dialog = $("#run-dialog");
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
      }
    } else if (spec.type === "language" || isLanguageChoice(spec)) {
      // The output language: the flag picker. It starts at the interface language when the workflow offers it
      // (a "language" input offers every language), else at the workflow's default.
      const codes = spec.type === "language" ? null : spec.options.map((o) => (typeof o === "string" ? o : o.value));
      const start = spec.type === "language" ? (isLang(spec.default) ? spec.default : LANG)
        : codes.includes(LANG) ? LANG : codes.includes(spec.default) ? spec.default : codes[0];
      control = languagePicker({codes, value: start, label: L(spec.label) || spec.id});
      control.read = () => control.value;
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
      control = spec.multiline ? h("textarea", {rows: 3}) : h("input", {type: "text"});
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
  const status = h("div", {class: "small grow", "aria-live": "polite"});
  const submit = h("button", {class: "btn primary", type: "submit"}, "▶ " + S("start_run"));
  const form = h("form", {class: "run-form", onsubmit: async (e) => {
    e.preventDefault();
    submit.disabled = true;
    status.replaceChildren();
    try {
      const values = {}, files = {};
      for (const {spec, control} of fields) {
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
      status.replaceChildren(S("starting"));
      const res = await api("POST", "/api/runs", {template: `${source}:${id}`, values, files});
      rememberInputs(source, id, fields);  // live.js: for "Same as last time"
      dialog.close();
      toast(S("run_started_toast"));
      go("runs/" + res.id);
    } catch (err) {
      status.replaceChildren(problemsBox(err));
      submit.disabled = false;
    }
  }},
  h("div", {class: "dialog-head"}, h("div", {}, h("h3", {id: "run-title"}, S("new_run_title", {name: L(tpl.name) || id})),
    h("p", {class: "small muted"}, S("new_run_lede"))),
    h("button", {type: "button", class: "icon-btn", "aria-label": S("close"), title: S("close"), onclick: () => dialog.close()}, "✕")),
  h("div", {class: "layout-body run-fields"}, tpl.description ? h("p", {class: "muted small"}, L(tpl.description)) : null,
    lastRun ? h("div", {class: "row last-run"}, h("button", {type: "button", class: "btn small", onclick: (e) => {
      for (const {spec, control} of fields) if (spec.id in lastRun && control.write) control.write(lastRun[spec.id]);
      e.currentTarget.disabled = true;
      toast(S("last_filled"));
    }}, "↺ " + S("same_as_last")), h("span", {class: "small muted"}, S("same_as_last_hint"))) : null,
    fields.length ? fields.map((f) => f.row) : h("p", {class: "muted"}, S("no_inputs"))),
  h("div", {class: "dialog-foot row"}, status, h("button", {type: "button", class: "btn", onclick: () => dialog.close()}, S("cancel_action")), submit));
  fill(dialog, form);
  if (!dialog.open) dialog.showModal();
  const first = $(".run-fields input:not(.file-native), .run-fields select, .run-fields textarea, .run-fields .file-pick button", form);
  if (first) first.focus();
}

// --- runs: the history and one run (live) -----------------------------------------------------------
async function showRuns(parts) {
  const [runs, books] = await Promise.all([api("GET", "/api/runs"), api("GET", "/api/translation/runs").catch(() => [])]);
  state.trRuns = books;
  const selected = parts[0];
  renderRunList(runs, selected);
  if (selected) return showRun(selected);
  fill($("#run"), runs.length || books.length ? h("div", {class: "empty"}, S("pick_run"))
    : h("div", {class: "welcome"}, h("h2", {}, S("first_run_title")), h("p", {}, S("first_run_text")),
      h("button", {type: "button", class: "btn primary", onclick: () => go("workflows")}, S("go_workflows"))));
}

// The workflow runs, then the last run of each book of the book translation (it opens the translation's books).
// What runs has a stop button: a workflow run can be resumed later, a book translation continues where it stopped.
function renderRunList(runs, selected) {
  const books = state.trRuns || [];
  const refresh = () => showRuns(selected ? [selected] : []);
  const mark = (status, active) => (active || status === "queued" ? h("span", {class: "dot", title: S("status_" + status)}) : badge(status));
  const runItems = runs.map((r) => h("li", {class: "rl-item"}, h("button", {type: "button", class: r.id === selected ? "active" : "",
    "aria-current": r.id === selected ? "true" : null, onclick: () => go("runs/" + r.id)},
    h("span", {class: "rl-main"}, h("span", {class: "rl-name"}, r.workflow_name), h("span", {class: "small muted"}, fmtTime(r.created))),
    mark(r.status, r.status === "running")),
    FINAL.has(r.status) ? null : stopButton(S("stop_named", {name: r.workflow_name}), (b) => stopRun(b, r.id, refresh))));
  const bookItems = books.map((b) => h("li", {class: "rl-item"}, h("button", {type: "button", onclick: () => go("workflows/translation/books")},
    h("span", {class: "rl-main"}, h("span", {class: "rl-name"}, iconTile("translation"), b.book),
      h("span", {class: "small muted"}, b.started ? fmtTime(b.started) : "", b.stage && b.active ? " · " + b.stage : "")),
    mark(b.waiting_quota ? "waiting_quota" : b.status, b.active)),
    b.active ? stopButton(S("stop_named", {name: b.book}), (btn) => stopBook(btn, b.book, refresh)) : null));
  fill($("#run-list"), ...(runs.length || books.length ? [...runItems,
    bookItems.length ? h("li", {class: "rl-sep small muted"}, S("translation_card_title")) : null, ...bookItems]
    : [h("li", {class: "muted small pl-empty"}, S("no_runs"))]));
}

async function showRun(runId, keep) {
  if (!keep) { state.selectedNode = null; state.runCanvas = null; fill($("#run"), skeleton("run")); }
  let run;
  try { run = await api("GET", `/api/runs/${runId}`); }
  catch (err) { fill($("#run"), problemsBox(err)); return; }
  if (state.tab !== "runs" || state.hash !== "runs/" + runId) return;
  if (keep && run.status !== state.runStatus) api("GET", "/api/runs").then((runs) => renderRunList(runs, runId)).catch(() => {});
  state.runStatus = run.status;
  const statuses = Object.fromEntries(Object.entries(run.nodes).map(([k, v]) => [k, v.status]));
  const live = run.active || (!FINAL.has(run.status) && run.status !== "waiting_approval");
  const refresh = () => showRun(runId, true);
  const post = async (button, path, body, message) => {
    const r = await act(button, () => api("POST", path, body));
    if (r) { if (message) toast(message); refresh(); }
  };
  const pick = (id) => { state.selectedNode = state.selectedNode === id ? null : id; refresh(); };

  // The canvas is kept between refreshes, so that pan and zoom stay where the user put them.
  const view = graphView(run.graph, statuses);
  if (!state.runCanvas || state.runCanvas.runId !== runId) {
    state.runCanvas = new GraphCanvas({labels: {status: (s) => S("status_" + s), port: portLabel}, onSelect: (sel) => pick(sel && sel.kind === "node" ? sel.id : state.selectedNode)});
    state.runCanvas.runId = runId;
    state.runCanvas.first = true;
  }
  state.runCanvas.setView(view, state.selectedNode ? {kind: "node", id: state.selectedNode} : null);

  const actions = [];
  if (!FINAL.has(run.status)) actions.push(h("button", {type: "button", class: "btn danger", onclick: (e) => {
    if (confirm(S("confirm_cancel"))) post(e.currentTarget, `/api/runs/${runId}/cancel`, {}, S("cancel_sent"));
  }}, S("cancel")));
  if (!run.active && ["failed", "cancelled", "interrupted", "queued"].includes(run.status))
    actions.push(h("button", {type: "button", class: "btn primary", onclick: (e) => post(e.currentTarget, `/api/runs/${runId}/resume`, {}, S("resumed"))}, S("resume")));
  const [tplSource, tplId] = (run.template || "").split(":");
  if (tplSource && tplId) actions.push(h("button", {type: "button", class: "btn", onclick: () => openRun(tplSource, tplId)}, "▶ " + S("run_again")));

  // The workflow's results; a workflow that names none shows the files its steps saved (an export step's documents).
  let outputs = (run.outputs || []).filter((o) => o.path);
  if (!(run.outputs || []).length) {
    outputs = run.graph.nodes.flatMap((g) => Object.entries(run.nodes[g.id].outputs || {})
      .filter(([port]) => (run.node_info[g.id].ports || {})[port] === "file")
      .map(([port, path]) => ({id: `${g.id}.${port}`, label: `${L(run.node_info[g.id].label) || g.id} · ${port}`, path})));
  }
  const done = run.graph.nodes.filter((g) => run.nodes[g.id].status === "succeeded").length;
  // A loop (ai.map) reports "done/count" in its progress events; the bar follows the last one.
  const parts = (nodeId) => {
    const last = run.events.filter((ev) => ev.node_id === nodeId && ev.kind === "progress").pop();
    if (last && last.key === "map_progress" && last.params) return {done: Number(last.params.done), count: Number(last.params.count)};
    const m = last && /(\d+)\s*\/\s*(\d+)/.exec(last.message || "");  // older runs: the stored text
    return m ? {done: Number(m[1]), count: Number(m[2])} : null;
  };
  const waiting = run.graph.nodes.filter((g) => run.nodes[g.id].status === "waiting_quota");
  const timeline = run.graph.nodes.map((g) => {
    const n = run.nodes[g.id], info = run.node_info[g.id];
    const p = parts(g.id);
    const busy = n.status === "running" || n.status === "waiting_quota";
    const width = n.status === "succeeded" ? 100 : busy ? (p && p.count ? Math.round(100 * p.done / p.count) : 50)
      : FINAL.has(n.status) || n.status === "rejected" ? 100 : 0;
    return h("li", {class: "tl-row" + (state.selectedNode === g.id ? " sel" : "") + (n.status === "skipped" ? " skipped" : "")},
      h("button", {type: "button", class: "linkish", onclick: () => pick(g.id)}, L(info.label) || g.id,
        h("span", {class: "small muted"}, " · " + nodeSub({label: info.label, type: info.type, id: g.id}))),
      h("div", {class: "track", "aria-hidden": "true"}, h("div", {class: "fill " + (["failed", "rejected"].includes(n.status) ? "failed"
        : n.status === "waiting_quota" ? "wait" : n.status === "running" ? "active" : ""), "data-w": width})),
      h("span", {class: "tl-count"}, p && n.status !== "skipped" ? h("span", {class: "small muted parts", "data-done": p.done}, S("parts_done", p)) : null,
        n.attempts > 1 ? h("span", {class: "small muted"}, S("attempt_n", {n: n.attempts})) : null,
        badge(n.status), " ", n.started ? (n.finished ? duration(n.started, n.finished) : h("span", {"data-since": n.started}, duration(n.started, Date.now() / 1000))) : ""),
      n.status === "waiting_quota" && n.error ? h("div", {class: "small warn-text tl-reason"}, n.error) : null);
  });
  const finished = run.graph.nodes.filter((g) => ["succeeded", "skipped"].includes(run.nodes[g.id].status)).length;
  const overall = h("div", {class: "run-progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(run.graph.nodes.length),
    "aria-valuenow": String(finished), "aria-label": S("progress")}, h("div", {class: "fill" + (waiting.length ? " wait" : ""), "data-w": run.graph.nodes.length ? Math.round(100 * finished / run.graph.nodes.length) : 0}));
  fill($("#run"),
    h("div", {class: "run-head"},
      h("div", {class: "stack"},
        h("div", {class: "book-title"}, h("h2", {}, run.workflow_name), badge(run.status), live ? h("span", {class: "dot", title: S("live")}) : null),
        h("p", {class: "row small muted"}, h("span", {}, S("started"), ": ", fmtTime(run.started || run.created)),
          h("span", {}, S("col_duration"), ": ", duration(run.started, run.finished)),
          h("span", {}, S("nodes_done", {done, total: run.graph.nodes.length})), h("code", {}, run.id),
          run.template ? h("code", {}, run.template) : null)),
      actions.length ? h("div", {class: "row run-actions"}, actions) : null),
    run.error ? h("div", {class: "notice bad"}, h("b", {}, S("error")), " ", run.error) : null,
    live ? overall : null,
    waiting.length ? h("div", {class: "notice warn", role: "status"}, h("b", {}, S("status_waiting_quota")), " ",
      waiting.map((g) => `${L(run.node_info[g.id].label) || g.id}: ${run.nodes[g.id].error || ""}`).join(" · "), " ",
      h("button", {type: "button", class: "btn small switch-open", onclick: () => { state.selectedNode = waiting[0].id; state.switchOpen = `${runId}:${waiting[0].id}`; refresh(); }},
        S("switch_model"))) : null,
    outputs.length ? h("section", {class: "card box results-box"}, h("h3", {}, S("results")),
      h("div", {class: "row"}, outputs.map((o) => h("a", {class: "btn", href: fileUrl(runId, o.path, true)}, "↓ " + (L(o.label) || o.id))))) : null,
    h("div", {class: "run-cols"},
      h("div", {class: "run-main"},
        h("section", {class: "card box run-graph"}, h("div", {class: "row run-graph-head"}, h("h3", {}, S("graph")),
          h("button", {type: "button", class: "btn small", onclick: () => state.runCanvas.fit()}, S("fit"))),
          state.runCanvas.el, h("p", {class: "small muted"}, S("monitor_hint"))),
        h("section", {class: "card box timeline"}, h("h3", {}, S("progress")), h("ol", {class: "tl"}, timeline)),
        liveLogPanel(run, runId)),  // live.js: the selected (or working) step's log, kept between redraws
      h("aside", {class: "run-aside"}, nodePanel(run, runId, post))),
    // A file input's value is its stored path, or a list of paths for a several-files input.
    h("details", {class: "logbox"}, h("summary", {}, S("inputs_used")), h("ul", {class: "plain"}, Object.entries(run.inputs).map(([k, v]) =>
      h("li", {}, h("code", {}, k), ": ", (Array.isArray(v) ? v : [v]).map((x, i) => [i ? ", " : "",
        typeof x === "string" && x.startsWith("inputs/") ? h("a", {href: fileUrl(runId, x, true)}, x.split("/").pop()) : (String(x ?? "") || "–")]))))),
    h("details", {class: "logbox"}, h("summary", {}, S("all_files")), h("ul", {class: "plain"}, (run.artifacts || []).map((a) =>
      h("li", {}, h("a", {href: fileUrl(runId, a.path, true)}, a.path), h("span", {class: "small muted"}, ` ${Math.ceil(a.size / 1024)} KB`))))),
    h("details", {class: "logbox"}, h("summary", {}, S("events")), h("pre", {class: "log"}, run.events.map((ev) =>
      `${fmtTime(ev.time)} ${ev.node_id || ""} ${ev.kind}${ev.message ? " — " + ev.message : ""}`).join("\n"))));
  animateBars(document.querySelectorAll("#run .fill[data-w]"), runId);  // live.js: from the last width to the new one
  tickParts(document.querySelectorAll("#run .parts[data-done]"), runId);
  liveLogPlaced();
  if (state.runCanvas.first) { state.runCanvas.first = false; requestAnimationFrame(() => state.runCanvas.fit()); }
  clearTimeout(state.runPoll);
  const poll = () => {
    if (state.hash !== "runs/" + runId) return;
    // Not under the user's hands: a comment being written, a model being chosen.
    const typing = document.activeElement && document.activeElement.closest && document.activeElement.closest("#node-panel textarea, #node-panel select");
    if (typing) state.runPoll = setTimeout(poll, 1500);
    else refresh();
  };
  if (live) state.runPoll = setTimeout(poll, 1500);
}

function nodePanel(run, runId, post) {
  const id = state.selectedNode;
  const waiting = Object.entries(run.nodes).filter(([, n]) => n.status === "waiting_approval").map(([k]) => k);
  if (!id || !run.nodes[id]) {
    return h("section", {class: "card box", id: "node-panel"}, h("h3", {}, S("node_details")),
      h("p", {class: "small muted"}, S("node_pick_hint")),
      waiting.length ? h("div", {class: "approval"}, h("b", {}, S("approval_needed")),
        waiting.map((w) => h("button", {type: "button", class: "btn small", onclick: () => { state.selectedNode = w; showRun(runId, true); }},
          L(run.node_info[w].label) || w))) : null);
  }
  const n = run.nodes[id], info = run.node_info[id];
  const parts = [h("div", {class: "row prompt-head"}, h("div", {}, h("h3", {}, L(info.label) || id),
    h("p", {class: "small muted"}, typeLabel(info.type), " · ", h("code", {}, id),
      run.providers[id] ? h("span", {}, " · ", S("model"), ": ", h("code", {}, run.providers[id])) : null, " · ", S("attempts"), ": ", String(n.attempts))),
    // A skipped node of a finished run is a branch it did not take: nothing to retry.
    h("div", {class: "row"}, badge(n.status), RETRYABLE.has(n.status) && !run.active && !(n.status === "skipped" && run.status === "succeeded")
      ? h("button", {type: "button", class: "btn small", onclick: (e) => post(e.currentTarget, `/api/runs/${runId}/nodes/${id}/retry`, {}, S("retry_sent"))}, S("retry")) : null,
      h("button", {type: "button", class: "icon-btn", "aria-label": S("close"), title: S("close"), onclick: () => { state.selectedNode = null; showRun(runId, true); }}, "✕")))];
  if (n.error && n.status === "waiting_quota") parts.push(h("div", {class: "notice warn"}, n.error));
  else if (n.error) parts.push(h("div", {class: "notice bad"}, h("b", {}, S("error")), " ", n.error));
  parts.push(switchBox(run, runId, id, () => showRun(runId, true)), switchEvents(run, id));  // live.js
  if (n.status === "skipped") parts.push(h("p", {class: "small muted"}, S("skipped_hint")));
  if (n.status === "waiting_approval") {
    const comment = h("textarea", {rows: 3, placeholder: S("comment_placeholder"), "aria-label": S("comment")});
    parts.push(h("div", {class: "approval"}, h("h3", {}, S("approval_needed")),
      h("p", {}, info.instructions ? L(info.instructions) : S("approval_default_text")), comment,
      h("div", {class: "row"},
        h("button", {type: "button", class: "btn primary", onclick: (e) => post(e.currentTarget, `/api/runs/${runId}/nodes/${id}/approve`, {comment: comment.value}, S("approved"))}, "✓ " + S("approve")),
        h("button", {type: "button", class: "btn danger", onclick: (e) => post(e.currentTarget, `/api/runs/${runId}/nodes/${id}/reject`, {comment: comment.value}, S("rejected"))}, "✕ " + S("reject")))));
  }
  if (n.comment) parts.push(h("p", {class: "small"}, S("comment") + ": " + n.comment));
  for (const [port, rel] of Object.entries(n.outputs || {})) {
    const kind = info.ports[port] || "text";
    const text = kind === "text" || rel.endsWith(".md");
    parts.push(h("div", {class: "file-row"}, h("span", {class: "file-name"}, S("output"), " ", h("b", {}, portLabel(info.type, port)), " ", h("span", {class: "small muted"}, rel.split("/").pop())),
      h("div", {class: "row"}, text ? h("button", {type: "button", class: "btn small", onclick: () => openReader(runId, rel, `${L(info.label) || id} · ${portLabel(info.type, port)}`)}, S("read")) : null,
        h("a", {class: "btn small", href: fileUrl(runId, rel, true)}, S("download")))));
  }
  const prompt = (run.artifacts || []).find((a) => a.path === `nodes/${id}/prompt.txt`);
  if (prompt) parts.push(h("div", {class: "file-row"}, h("span", {class: "file-name"}, S("view_prompt")),
    h("button", {type: "button", class: "btn small", onclick: () => openReader(runId, prompt.path, `${L(info.label) || id} · ${S("prompt")}`)}, S("read"))));
  return h("section", {class: "card box", id: "node-panel"}, parts);
}

// The reader: a text output in a dialog, always as plain text.
async function openReader(runId, rel, title) {
  const dialog = $("#reader");
  $("#reader-title").textContent = title;
  $("#reader-download").href = fileUrl(runId, rel, true);
  $("#reader-text").textContent = S("loading");
  if (!dialog.open) dialog.showModal();
  try {
    const text = await api("GET", `/api/runs/${runId}/files/${rel.split("/").map(encodeURIComponent).join("/")}`);
    $("#reader-text").textContent = text || S("empty_output");
  } catch (err) { $("#reader-text").textContent = err.message; }
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

// --- start ---------------------------------------------------------------------------------------
async function boot() {
  checkStale();
  setInterval(checkStale, 20000);
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
  state.ready = recall("mehteran.ready") === "1";
  applyStaticTexts();
  document.querySelectorAll(".tabs .tab").forEach((t) => t.addEventListener("click", () => go(t.dataset.tab)));
  document.querySelectorAll("#translation .subtab").forEach((b) => b.addEventListener("click", () => go("workflows/translation/" + b.dataset.sub)));
  document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => go(b.dataset.goto)));
  $("#brand").addEventListener("click", (e) => { e.preventDefault(); go(home()); });
  $("#tools-refresh").addEventListener("click", () => { loadTools(); loadLocal(); });
  $("#reader-close").addEventListener("click", () => $("#reader").close());
  $("#template-search").addEventListener("input", (e) => { state.tplQuery = e.target.value; renderLibrary(); });
  $("#template-import").addEventListener("click", () => go("workflows/import"));
  // The drawer closed by Esc: back to the library address.
  $("#drawer").addEventListener("close", () => { if (/^workflows\/(builtin|user|import)/.test(state.hash)) go("workflows"); });
  $("#drawer").addEventListener("click", (e) => { if (e.target === e.currentTarget) go("workflows"); });  // the backdrop
  setUpActivity();  // live.js: the header's indicator of what runs now
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
