"use strict";

// --- setup: installing the tools and signing in ------------------------------------------------------
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
  $("#config-note").replaceChildren(S("config_note_workflows", {path: (INFO && INFO.config_source) || "config.toml"}));
  state.toolsBusy = data.tools.some((tool) => tool.job && tool.job.running) || Boolean(data.all_job && data.all_job.running);
  const watchingSignIn = state.signInUntil > Date.now() && data.tools.some((tool) => tool.installed && !tool.signed_in);
  if (state.toolsBusy) state.toolPoll = setTimeout(loadTools, 2500);
  else if (watchingSignIn) state.toolPoll = setTimeout(loadTools, 4000);
}

// A sign-in is needed for the tools that a template uses.
const neededTools = (data) => data.tools.filter((tool) => tool.templates.length);
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
    h("div", {class: "row"},
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
  // Who uses the tool: the templates.
  const names = tool.templates || [];
  const uses = !tool.provider ? S("pdf_uses") : !tool.configured ? S("not_configured")
    : names.length ? S("used_by", {names: names.slice(0, 3).join(", ") + (names.length > 3 ? " " + S("and_more", {count: names.length - 3}) : "")})
    : S("not_used");
  const q = tool.quota;
  const quota = q && q.since ? (q.until > Date.now() / 1000 && !(q.cleared > q.since)
    ? h("div", {class: "notice warn small"}, S("quota_now", {time: fmtTime(q.until)}))
    : h("div", {class: "small muted"}, S("quota_last", {time: fmtTime(q.since)}))) : null;
  // A tool that is ready: its name, one status line and "Test"; the rest under "Details".
  const ready = tool.installed && (!tool.provider || tool.signed_in) && !running && !(job && job.code !== 0);
  if (ready) {
    const test = actions.find((b) => b.textContent === S("test"));
    return h("article", {class: "card tool compact", "data-id": tool.id},
      h("div", {class: "tool-head"}, h("h3", {}, tool.name), h("span", {class: "muted small"}, tool.version)),
      h("div", {class: "badges"}, h("span", {class: "badge good"}, S(tool.provider ? "signed_in" : "installed") + (tool.sign_in_info ? " · " + tool.sign_in_info : "")),
        tool.billing ? billingBadge(tool.billing) : null),
      quota && q.until > Date.now() / 1000 ? quota : null,
      tool.provider ? usageMini(canonicalProvider(tool.provider)) : null,  // live.js: what is left of its limit, without opening Details
      h("details", {class: "tool-more"}, h("summary", {class: "small"}, S("details")),
        h("div", {class: "stack"}, h("div", {class: "uses"}, uses), h("div", {class: "small muted"}, tool.requirements),
          tool.provider ? usageSlot(canonicalProvider(tool.provider)) : null, keyForm, h("div", {class: "actions"}, actions.filter((b) => b !== test)))),
      test ? h("div", {class: "actions"}, test) : null);
  }
  return h("article", {class: "card tool", "data-id": tool.id},
    h("div", {class: "tool-head"}, h("h3", {}, tool.name), h("span", {class: "muted small"}, tool.version)),
    h("div", {class: "badges"},
      need(tool.required),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.installed && tool.provider ? h("span", {class: "badge " + (tool.signed_in ? "good" : "warn")},
        S(tool.signed_in ? "signed_in" : "not_signed_in") + (tool.signed_in && tool.sign_in_info ? " · " + tool.sign_in_info : "")) : null,
      tool.installed && tool.billing ? billingBadge(tool.billing) : null),  // stream P: what a call would use
    h("div", {class: "uses"}, uses),
    h("div", {class: "small muted"}, tool.requirements),
    tool.installed && !tool.signed_in && tool.sign_in_help ? h("div", {class: "small"}, tool.sign_in_help) : null,
    quota,
    tool.provider ? usageSlot(canonicalProvider(tool.provider)) : null,
    !terminal && tool.installed && !tool.signed_in && tool.provider ? h("p", {class: "small muted"}, S("run_command", {command: tool.login_command})) : null,
    keyForm,
    job ? h("pre", {class: "log"}, job.log.slice(-4000)) : null,
    h("div", {class: "actions"}, actions));
}

// A provider whose models run on this computer (Ollama).
const localTag = (p) => (p && p.local ? h("span", {class: "local-tag", title: S("local_hint")}, S("local")) : null);
// "Required" for the tools that the templates use (and the PDF reader); "optional" otherwise.
const need = (required) => h("span", {class: "need " + (required ? "required" : "optional")}, S(required ? "need_required" : "need_optional"));
const GB = 1024 * 1024 * 1024;
const gb = (bytes) => (bytes == null ? "–" : bytes >= GB ? `${(bytes / GB).toFixed(1)} GB` : fileSize(bytes));

// A confirmation in a dialog of the page (not the browser's confirm()): a title, lines of facts and two buttons.
// danger: the action deletes something (a red button instead of the green one).
function askConfirm(title, lines, ok, danger) {
  const dialog = $("#confirm-dialog");
  return new Promise((resolve) => {
    const done = (answer) => { dialog.close(); resolve(answer); };
    fill(dialog, h("form", {method: "dialog", onsubmit: (e) => { e.preventDefault(); done(true); }},
      h("div", {class: "dialog-head"}, h("h3", {id: "confirm-title"}, title)),
      h("div", {class: "layout-body stack"}, lines.filter(Boolean).map((line) => h("p", {class: "small"}, line))),
      h("div", {class: "dialog-foot row"},
        h("button", {type: "button", class: "btn", onclick: () => done(false)}, S("cancel_action")),
        h("button", {type: "submit", class: danger ? "btn danger confirm-ok" : "btn primary confirm-ok"}, ok))));
    dialog.addEventListener("cancel", () => resolve(false), {once: true});
    dialog.showModal();
    $("button.confirm-ok", dialog).focus();
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
      ...["typst", "pandoc", "speech", "qpdf", "browser"].map((id) => localToolCard(data.tools.find((x) => x.id === id)))));
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
  browser: {title: null, about: "browser_about", ask: "browser_install_title", what: "browser_install_what", source: "browser_install_source"},
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
  if (tool.id === "browser" && !tool.node) extra.push(h("span", {class: "badge warn"}, S("browser_no_node")));
  if (tool.id === "browser" && !tool.chrome) extra.push(h("span", {class: "badge warn"}, S("browser_no_chrome")));
  return h("article", {class: "card tool local-tool", "data-id": tool.id},
    h("div", {class: "tool-head"}, h("h3", {}, text.title || S(tool.id + "_title")), h("span", {class: "muted small"}, tool.version || "")),
    h("div", {class: "badges"}, need(false),
      h("span", {class: "badge " + (tool.installed ? "good" : "bad")}, S(tool.installed ? "installed" : "not_installed")),
      tool.source ? h("span", {class: "badge"}, sourceText(tool)) : null, extra),
    h("p", {class: "small muted"}, S(text.about)),
    tool.id === "speech" && tool.ffmpeg ? h("p", {class: "small muted"}, S("speech_ffmpeg_line", {path: tool.ffmpeg})) : null,
    jobBox(tool.job, tool.id),
    !tool.installed || (tool.job && !running && tool.job.code !== 0)
      ? h("div", {class: "actions"}, h("button", {type: "button", class: "btn primary", disabled: running, onclick: install}, S(running ? "installing" : "install"))) : null,
    tool.id === "speech" && tool.installed ? speechModels(tool) : null,
    tool.id === "browser" && tool.installed ? browserSignin(tool) : null);
}

// The browser of agent steps: Chrome with Mehteran's own profile; the person signs in to the sites there once.
function browserSignin(tool) {
  const url = h("input", {type: "url", dir: "ltr", placeholder: "https://x.com/login", "aria-label": S("browser_signin_url")});
  const open = async (e) => {
    const res = await act(e.currentTarget, () => api("POST", "/api/browser/signin", {url: url.value.trim()}));
    if (res) toast(S("browser_signin_opened"));
  };
  return h("fieldset", {class: "plain stack"}, h("legend", {}, S("browser_signin_title")),
    h("p", {class: "small muted"}, S("browser_signin_note", {path: tool.profile || ""})),
    h("div", {class: "row"}, url, h("button", {type: "button", class: "btn", disabled: !tool.chrome, onclick: open}, S("browser_signin_open"))));
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

// Saved API keys are write-only. The server returns their source and the selected voice ID.
async function loadVideoSettings() {
  const panel = $("#video-settings");
  if (panel.dataset.loaded) return;
  panel.dataset.loaded = "1";
  fill(panel, h("p", {class: "muted"}, S("loading")));
  try {
    drawVideoSettings(await api("GET", "/api/video-settings"));
  } catch (err) {
    delete panel.dataset.loaded;
    fill(panel, problemsBox(err), h("button", {type: "button", class: "btn", onclick: loadVideoSettings}, S("retry")));
  }
}

function drawVideoSettings(settings, notice = "") {
  const fields = [
    ["openai_key", "video_openai_key"],
    ["elevenlabs_key", "video_elevenlabs_key"],
    ["voice_id", "video_voice_id"],
  ];
  const controls = new Map();
  const status = h("p", {class: "small", role: "status"}, notice);
  const update = async (button, changes) => {
    button.disabled = true;
    status.textContent = S("video_settings_saving");
    try {
      const updated = await api("PUT", "/api/video-settings", changes);
      drawVideoSettings(updated, S("video_settings_saved"));
      $("#video-settings button[type=submit]").focus();
    } catch (err) {
      status.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  };
  const form = h("form", {class: "stack video-settings-form", onsubmit: (event) => {
    event.preventDefault();
    const changes = Object.fromEntries([...controls].map(([key, input]) => [key, input.value.trim()]).filter(([, value]) => value));
    if (Object.keys(changes).length) update(event.submitter, changes);
  }},
  h("p", {class: "small muted"}, S("video_settings_help")),
  fields.map(([key, label]) => {
    const voice = key === "voice_id";
    const id = "video-setting-" + key;
    const input = h("input", {id, type: voice ? "text" : "password", maxlength: voice ? 64 : 512,
      autocomplete: "off", spellcheck: "false", dir: "ltr", placeholder: voice ? settings.voice_id : S("video_paste_key")});
    controls.set(key, input);
    const source = settings.sources[key];
    return h("div", {class: "stack video-settings-field"},
      h("label", {class: "fld-label", for: id}, S(label)),
      h("div", {class: "row"}, input,
        source === "saved" ? h("button", {type: "button", class: "btn small", onclick: (event) =>
          update(event.currentTarget, {[key]: null})}, S(voice ? "video_voice_reset" : "video_key_remove")) : null),
      h("span", {class: "small muted"}, S("video_source_" + source)));
  }),
  h("div", {class: "row"}, h("button", {type: "submit", class: "btn primary"}, S("save")), status));
  fill($("#video-settings"), form);
}
