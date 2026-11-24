// Mehteran web interface: what runs now and what the AI tools have used. Loaded before app.js and called by it; it
// uses app.js's helpers (S, h, fill, api, act, toast, fmtTime, duration, go, state, INFO) when its functions run.
//   - usage of each tool (GET /api/usage, POST /api/usage/probe/<provider>): the header's remaining-usage chip,
//     Setup cards and the tool table, hints next to model pickers
//   - switching the model of a step (POST /api/runs/<run>/nodes/<node>/switch)
//   - a step's live log (GET /api/runs/<run>/log?node=&offset=), elapsed timers
//   - the header's activity indicator (GET /api/activity)
//   - favorites and the run form's last values
//   - stopping a workflow run, and the cards' icons
"use strict";

// --- icons: one line drawing (24x24, stroked) per category ---------------------------------------------------
const ICONS = {
  business: ["M4 8h16v11H4Z", "M9 8V5.5h6V8", "M4 13h16"],
  data: ["M4 20h16", "M6.5 20v-7", "M11 20V6", "M15.5 20v-10", "M20 20V9"],
  documents: ["M6 3h8l4 4v14H6Z", "M14 3v4h4", "M9 12h6", "M9 16h6"],
  education: ["M2.5 9 12 4.5 21.5 9 12 13.5Z", "M6.5 11v5c3 2.6 8 2.6 11 0v-5", "M21.5 9v5"],
  developers: ["M8.5 8 4 12l4.5 4", "M15.5 8 20 12l-4.5 4", "M13.5 5.5l-3 13"],
  exams: ["M6 3.5h12v17H6Z", "M9 8.5l1.5 1.5L13.5 7", "M9 14.5l1.5 1.5 3-3", "M15 9h1.5", "M15 15h1.5"],
  everyday: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2.5v2", "M12 19.5v2", "M2.5 12h2", "M19.5 12h2", "M5.3 5.3l1.4 1.4", "M17.3 17.3l1.4 1.4", "M5.3 18.7l1.4-1.4", "M17.3 6.7l1.4-1.4"],
  legal: ["M12 4v16", "M8 20h8", "M5 7h14", "M5 7 2.5 13c1.5 1.4 3.5 1.4 5 0Z", "M19 7l-2.5 6c1.5 1.4 3.5 1.4 5 0Z"],
  research: ["M11 5a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z", "M20 20l-4.7-4.7"],
  writing: ["M4 20l1-4.5L16 4.5l3.5 3.5L8.5 19Z", "M13.5 7l3.5 3.5"],
  web: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z", "M3 12h18", "M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9", "M12 3c-2.5 2.6-3.7 5.6-3.7 9s1.2 6.4 3.7 9"],
  mine: ["M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M4.5 20.5c1-3.8 4-5.5 7.5-5.5s6.5 1.7 7.5 5.5"],
  other: ["M4 4h7v7H4Z", "M13 4h7v7h-7Z", "M4 13h7v7H4Z", "M13 13h7v7h-7Z"],
};

function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [k, v] of Object.entries({viewBox: "0 0 24 24", width: "20", height: "20", fill: "none", stroke: "currentColor",
    "stroke-width": "1.7", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false"})) svg.setAttribute(k, v);
  for (const d of ICONS[name] || ICONS.other) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  }
  return svg;
}

// The icon tile at the top of a card: the category's icon in the category's colour.
const iconTile = (name) => h("span", {class: `tpl-icon icon-${ICONS[name] ? name : "other"}`}, icon(name));

// --- stopping a workflow run (it can be resumed later) -----------------------------------------------------------
async function stopRun(button, runId, after) {
  if (!confirm(S("confirm_cancel"))) return;
  if (await act(button, () => api("POST", `/api/runs/${runId}/cancel`))) { toast(S("cancel_sent")); pollActivity(); if (after) after(); }
}

const stopButton = (label, onclick) => h("button", {type: "button", class: "icon-btn danger stop-btn", "aria-label": label, title: label,
  onclick: (e) => { e.stopPropagation(); onclick(e.currentTarget); }}, "■");

// --- timers: every element with data-since (elapsed) or data-until (countdown) is updated each second ------------
setInterval(() => {
  const now = Date.now() / 1000;
  document.querySelectorAll("[data-since]").forEach((el) => { el.textContent = duration(Number(el.dataset.since), now); });
  document.querySelectorAll("[data-until]").forEach((el) => {
    const until = Number(el.dataset.until);
    el.textContent = until > now ? S("resets_in", {time: duration(now, until)}) : S("reset_passed");
  });
}, 1000);

// --- usage ----------------------------------------------------------------------------------------------------
const usageState = {data: null, at: 0, loading: null};

async function loadUsage(force) {
  if (!force && usageState.data && Date.now() - usageState.at < 15000) return usageState.data;
  if (!usageState.loading) {
    usageState.loading = api("GET", "/api/usage").then((data) => { usageState.data = data; usageState.at = Date.now(); return data; })
      .catch(() => usageState.data).finally(() => { usageState.loading = null; });
  }
  return usageState.loading;
}

const usageOf = (provider) => ((usageState.data && usageState.data.providers) || []).find((p) => p.provider === provider) || null;

// The windows a tool reports itself, as [{label, percent, resets}] (percent 0-100), or [] when it reports none.
function reportedWindows(entry) {
  const rep = entry && entry.tool_reported;
  if (!rep || !Array.isArray(rep.windows)) return [];
  const name = {primary: "window_5h", secondary: "window_week", five_hour: "window_5h", seven_day: "window_week", seven_day_model: "window_week_model"};
  return rep.windows.map((w) => ({label: S(name[w.name] || "window_other", {name: w.model || w.name}),
    percent: w.used_percent != null ? Number(w.used_percent) : w.utilization != null ? Math.round(Number(w.utilization) * 100) : null,
    resets: typeof w.resets_at === "number" ? w.resets_at : w.resets_at ? Date.parse(w.resets_at) / 1000 : null,
    expired: Boolean(w.expired)})).filter((w) => Number.isFinite(w.percent) && w.percent >= 0 && w.percent <= 100)
    .map((w) => ({...w, expired: w.expired || Boolean(w.resets && w.resets <= Date.now() / 1000)}));
}

// What is left of a window: "%28 kaldı". The tools report the used share; people ask how much is left.
const percentText = (value) => (value / 100).toLocaleString(LANG, {style: "percent"});
function usageLeft(reported) {
  return S("usage_percent_left", {percent: percentText(100 - reported.percent)});
}

// The remaining usage of one tool as bars (full = everything left): its own report, newest first known.
// compact: no "seen at" line. Returns [] when the tool reports nothing.
// The window closest to its limit: the one that decides how much can still be done now.
const tightest = (windows) => windows.filter((w) => !w.expired).reduce((a, w) => (!a || w.percent > a.percent ? w : a), null);

function usageBars(entry, compact) {
  let windows = reportedWindows(entry);
  if (!windows.length) return [];
  if (compact) windows = [tightest(windows) || windows[0]];  // a tool card: one bar; all of them under "Details"
  const rep = entry.tool_reported;
  const seen = rep.observed_at ? (typeof rep.observed_at === "number" ? rep.observed_at : Date.parse(rep.observed_at) / 1000) : null;
  const bars = windows.map((w) => h("div", {class: "usage-bar " + (w.expired ? "" : w.percent >= 95 ? "bad" : w.percent >= 80 ? "warn" : "")},
    h("span", {class: "small usage-bar-text"}, h("span", {}, w.label + ": ", h("b", {}, w.expired ? S("usage_window_reset") : usageLeft(w))),
      w.resets && !w.expired ? h("span", {class: "muted", "data-until": w.resets}, S("resets_in", {time: duration(Date.now() / 1000, w.resets)})) : null),
    w.expired ? null : h("span", {class: "track", role: "img", "aria-label": `${w.label}: ${usageLeft(w)}`}, h("span", {class: "fill", "data-w": 100 - w.percent}))));
  bars.forEach((bar) => bar.querySelectorAll("[data-w]").forEach((el) => (el.style.width = el.dataset.w + "%")));
  return compact || !seen ? bars : [...bars, h("p", {class: "small muted"}, S("usage_observed", {time: fmtTime(seen)}))];
}

// Near a limit: "bad" while a limit is active or a window is at 95 %, "warn" from 80 %.
function usageLevel(entry) {
  if (!entry) return "";
  if (entry.resets_at > Date.now() / 1000) return "bad";
  const top = Math.max(-1, ...reportedWindows(entry).filter((w) => !w.expired).map((w) => w.percent));
  return top >= 95 ? "bad" : top >= 80 ? "warn" : "";
}

// A short text for a model picker: "5 saat: %46 kaldı", or the limit, or Mehteran's own count of the last 5 hours.
function usageHintText(provider) {
  const entry = usageOf(provider);
  if (!entry) return "";
  if (entry.resets_at > Date.now() / 1000) return S("hint_limited", {time: fmtTime(entry.resets_at)});
  const windows = reportedWindows(entry).filter((w) => !w.expired);
  if (windows.length) return windows.map((w) => `${w.label}: ${usageLeft(w)}`).join(" · ");
  const five = entry.windows && entry.windows["5h"];
  return five && five.calls ? S("hint_calls_5h", {count: five.calls}) : "";
}

// A hint element that follows a provider choice: hint.show("claude").
function usageHint() {
  const el = h("span", {class: "usage-hint small"});
  el.show = (provider) => {
    const text = usageHintText(provider);
    el.textContent = text;
    el.hidden = !text;
    el.className = "usage-hint small " + usageLevel(usageOf(provider));
  };
  return el;
}

// The usage part of a Setup tool card; filled when GET /api/usage answers.
function usageSlot(provider) {
  return h("div", {class: "usage-slot", "data-provider": provider});
}

// The remaining usage on a ready tool's card, outside "Details": filled with the same answer.
function usageMini(provider) {
  return h("div", {class: "usage-mini", "data-provider": provider});
}

async function fillUsageSlots(force) {
  const slots = document.querySelectorAll(".usage-slot, .usage-mini, .usage-cell");
  if (!slots.length) return;
  await loadUsage(force);
  document.querySelectorAll(".usage-slot").forEach((slot) => fill(slot, usageBox(slot.dataset.provider)));
  document.querySelectorAll(".usage-mini").forEach((slot) => fill(slot, usageBars(usageOf(slot.dataset.provider), true)));
  document.querySelectorAll(".usage-cell").forEach((slot) => fill(slot, usageCell(slot.dataset.provider)));
  drawUsageChip();
}

// A cell of the Setup panel's tool table: the bars, or why there are none.
function usageCell(provider) {
  const entry = usageOf(provider);
  const bars = usageBars(entry, false);
  if (bars.length) return bars;
  if (entry && entry.resets_at > Date.now() / 1000) return h("span", {class: "small bad-text"}, S("hint_limited", {time: fmtTime(entry.resets_at)}));
  const five = entry && entry.windows && entry.windows["5h"];
  return h("span", {class: "small muted"}, (providerInfo(provider) || {}).local ? S("usage_left_local")
    : [S("usage_left_none"), five && five.calls ? " " + S("hint_calls_5h", {count: five.calls}) : ""]);
}

// Asks the tools again now (Claude Code: its own "/usage" report, no model call).
async function refreshUsage(button) {
  const claude = ((usageState.data && usageState.data.providers) || []).filter((p) => p.tool === "claude" && p.configured);
  await act(button, async () => {
    for (const p of claude) await api("POST", `/api/usage/probe/${encodeURIComponent(p.provider)}`);
    return true;
  });
  await fillUsageSlots(true);
}

function usageBox(provider) {
  const entry = usageOf(provider);
  if (!usageState.data) return h("p", {class: "small muted"}, S("usage_unknown"));
  const counts = (w) => (w ? [S("usage_calls", {count: w.calls}), w.failed ? S("usage_failed", {count: w.failed}) : null,
    w.quota ? S("usage_quota_hits", {count: w.quota}) : null, w.seconds ? duration(1, 1 + w.seconds) : null].filter(Boolean).join(" · ") : "–");
  const rows = entry?.calls ? ["today", "5h", "7d"].map((key) => h("tr", {},
    h("th", {scope: "row"}, S("usage_window_" + key)), h("td", {}, counts(entry.windows?.[key])))) : [];
  const parts = [h("h4", {}, S("usage_title")),
    entry && entry.calls ? h("table", {class: "usage-table"}, h("tbody", {}, rows)) : h("p", {class: "small muted"}, S("usage_none"))];
  const quota = entry && (entry.last_quota || null);
  if (quota) {
    const limited = entry.resets_at > Date.now() / 1000;
    parts.push(h("div", {class: "small " + (limited ? "notice warn" : "muted")},
      S("usage_last_limit", {time: fmtTime(quota.at)}),
      limited ? [" · ", h("b", {"data-until": entry.resets_at}, S("resets_in", {time: duration(Date.now() / 1000, entry.resets_at)}))] : null,
      quota.message ? h("div", {class: "muted"}, quota.message) : null));
  }
  // What the tool reports itself: Codex from its session logs, Claude Code from its "/usage"; "unknown" otherwise.
  const tool = entry ? entry.tool : null;
  const bars = usageBars(entry, false);
  parts.push(h("div", {class: "usage-reported"}, h("span", {class: "small fld-label"}, S("usage_left_title")),
    bars.length ? bars : h("p", {class: "small muted"}, S("usage_unknown")),
    tool === "codex" && !bars.length ? h("p", {class: "small muted"}, S("usage_codex_note")) : null));
  if (tool === "claude") {
    parts.push(h("div", {class: "row"}, h("button", {type: "button", class: "btn small", onclick: (e) => refreshUsage(e.currentTarget)}, S("usage_check")),
      h("span", {class: "small muted"}, S("usage_check_note"))));
  }
  return h("section", {class: "usage-box"}, parts);
}

// --- switching the model of a step ----------------------------------------------------------------------------
const SWITCHABLE = new Set(["waiting_quota", "failed", "cancelled", "interrupted"]);

// Every configured model, grouped by tool, without the current one; the usage hint in each tool's label.
function modelChoices(current, selected, localOnly) {
  const providers = (INFO && INFO.providers) || [];
  return providers.map((p) => {
    if (localOnly && !p.local) return null;
    const hint = usageHintText(p.name);
    const names = [p.name, ...(p.models || []).map((m) => `${p.name}/${m}`)].filter((n) => n !== current);
    return names.length ? h("optgroup", {label: p.name + (hint ? ` (${hint})` : "")},
      names.map((n) => h("option", {value: n, selected: n === selected}, n))) : null;
  });
}

function switchBox(run, runId, nodeId, refresh) {
  const n = run.nodes[nodeId];
  const current = run.providers[nodeId];
  if (!current || !SWITCHABLE.has(n.status) || !run.node_info[nodeId] || !(INFO.providers || []).length) return null;
  const key = `${runId}:${nodeId}`;
  const open = state.switchOpen === key;
  const waiting = n.status === "waiting_quota";
  const head = h("div", {class: "row switch-head"},
    waiting ? h("button", {type: "button", class: "btn small" + (open ? "" : " primary"), "aria-pressed": String(!open),
      onclick: () => { state.switchOpen = null; refresh(); }}, S("keep_waiting")) : null,
    h("button", {type: "button", class: "btn small" + (open ? " primary" : ""), "aria-expanded": String(open),
      onclick: () => { state.switchOpen = open ? null : key; loadUsage().then(refresh); }}, S("switch_model")));
  const parts = [h("p", {class: "small"}, S(waiting ? "switch_waiting_hint" : "switch_failed_hint", {model: current})), head];
  if (open) {
    const select = h("select", {"aria-label": S("switch_to"), onchange: (e) => { state.switchChoice = e.currentTarget.value; hint.show(e.currentTarget.value.split("/")[0]); }},
      modelChoices(current, state.switchChoice, run.local_only));
    const hint = usageHint();
    if (!state.switchChoice || state.switchChoice === current) state.switchChoice = select.value;
    hint.show(select.value.split("/")[0]);
    parts.push(h("div", {class: "row switch-pick"}, h("label", {class: "small"}, S("switch_to"), " ", select), hint,
      h("button", {type: "button", class: "btn primary small switch-go", disabled: !select.value, onclick: async (e) => {
        const button = e.currentTarget;
        const provider = select.value;
        const name = provider.split("/")[0];
        const target = INFO.providers.find((p) => p.name === name);
        const from = INFO.providers.find((p) => p.name === current.split("/")[0]);
        if (from?.local && target && !target.local &&
          !await askConfirm(S("switch_model"), [S("switch_cloud_confirm", {provider: target.name})], S("switch_go"))) return;
        const r = await act(button, () => api("POST", `/api/runs/${runId}/nodes/${nodeId}/switch`, {provider}));
        if (r) { toast(S("switched_toast", {model: provider})); state.switchOpen = null; state.switchChoice = null; refresh(); }
      }}, S("switch_go"))));
  }
  return h("div", {class: "switch-box notice " + (waiting ? "warn" : "")}, parts);
}

// The model changes of a step, from the run's events.
function switchEvents(run, nodeId) {
  const events = run.events.filter((ev) => ev.node_id === nodeId && ev.kind === "provider_switched");
  return events.length ? h("ul", {class: "plain small switch-events"}, events.map((ev) => h("li", {}, fmtTime(ev.time), " · ", ev.message))) : null;
}

// --- a step's live log ----------------------------------------------------------------------------------------
// One panel element, kept between the run page's redraws (its text, its scroll position); its own reader asks only
// for the new bytes, often while the step works and slowly while the window is hidden.
const liveLog = {runId: null, node: null, offset: 0, text: "", done: false, follow: true, scroll: 0, timer: null, el: null};

function liveLogPanel(run, runId) {
  const busy = run.graph.nodes.map((g) => g.id).find((id) => ["running", "waiting_quota"].includes(run.nodes[id].status));
  const started = run.graph.nodes.map((g) => g.id).filter((id) => run.nodes[id].started);
  const node = state.selectedNode && run.nodes[state.selectedNode] ? state.selectedNode : busy || started[started.length - 1];
  if (!node) return null;
  if (liveLog.runId !== runId || liveLog.node !== node || !liveLog.el) startLiveLog(runId, node);
  const n = run.nodes[node], info = run.node_info[node];
  fill(liveLog.title, S("live_log"), " · ", (info && L(info.label)) || node, " ", badge(n.status));
  liveLog.timing.replaceChildren(...(n.started ? [S("elapsed"), ": ", n.finished ? duration(n.started, n.finished)
    : h("span", {"data-since": n.started}, duration(n.started, Date.now() / 1000))] : []),
  n.attempts > 1 ? ` · ${S("attempts")}: ${n.attempts}` : "");
  if (!liveLog.done && !liveLog.timer) liveLog.timer = setTimeout(pollLiveLog);  // once the page has placed the panel
  if (run.active) nudgeActivity();  // the header learns of a run that started a moment ago
  return liveLog.el;
}

function startLiveLog(runId, node) {
  clearTimeout(liveLog.timer);
  Object.assign(liveLog, {runId, node, offset: 0, text: "", done: false, follow: true, scroll: 0, timer: null});
  const pre = h("pre", {class: "log live-pre", tabindex: "0", "aria-live": "off"});
  const jump = h("button", {type: "button", class: "btn small live-jump", hidden: true, onclick: () => {
    liveLog.follow = true;
    jump.hidden = true;
    pre.scrollTop = pre.scrollHeight;
  }}, S("log_follow"));
  pre.addEventListener("scroll", () => {
    if (liveLog.restoring) return;
    const atEnd = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 24;
    liveLog.follow = atEnd;
    liveLog.scroll = pre.scrollTop;
    jump.hidden = atEnd;
  });
  const copy = h("button", {type: "button", class: "btn small", onclick: async () => {
    try { await navigator.clipboard.writeText(liveLog.text); confirmPop(copy); toast(S("copied")); }
    catch {
      const range = document.createRange();
      range.selectNodeContents(pre);
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      toast(S("copy_select"));
    }
  }}, S("copy"));
  liveLog.title = h("h3", {});
  liveLog.timing = h("span", {class: "small muted"});
  liveLog.pre = pre;
  liveLog.jump = jump;
  liveLog.el = h("section", {class: "card box live-log"}, h("div", {class: "row live-head"}, liveLog.title, liveLog.timing,
    h("span", {class: "grow"}), jump, copy), pre);
  pre.textContent = S("loading");
}

// After the page put the panel back (a redraw): its scroll position again.
function liveLogPlaced() {
  if (!liveLog.el || !liveLog.el.isConnected) return;
  liveLog.restoring = true;
  liveLog.pre.scrollTop = liveLog.follow ? liveLog.pre.scrollHeight : liveLog.scroll;
  requestAnimationFrame(() => { liveLog.restoring = false; });
}

async function pollLiveLog() {
  liveLog.timer = null;
  const {runId, node} = liveLog;
  if (!liveLog.el || !liveLog.el.isConnected || state.hash !== "runs/" + runId) return;
  let part;
  try { part = await api("GET", `/api/runs/${runId}/log?node=${encodeURIComponent(node)}&offset=${liveLog.offset}`); }
  catch { part = null; }
  if (liveLog.runId !== runId || liveLog.node !== node) return;  // another step was chosen meanwhile
  if (part) {
    if (!liveLog.offset) liveLog.pre.textContent = "";
    if (part.text) {
      liveLog.text += part.text;
      if (liveLog.text.length > 400000) liveLog.text = liveLog.text.slice(-300000);  // the page keeps the end
      liveLog.pre.textContent = liveLog.text;
    } else if (!liveLog.text) liveLog.pre.textContent = S(part.done ? "log_empty" : "log_waiting");
    liveLog.offset = part.offset;
    liveLog.done = part.done;
    if (liveLog.follow) liveLog.pre.scrollTop = liveLog.pre.scrollHeight;
  }
  if (liveLog.done) return;
  liveLog.timer = setTimeout(pollLiveLog, document.hidden ? 5000 : part && part.text ? 700 : 1500);
}

// --- the header's activity indicator ----------------------------------------------------------------------------
const activity = {data: null, timer: null};

async function pollActivity() {
  clearTimeout(activity.timer);
  activity.at = Date.now();
  try { activity.data = await api("GET", "/api/activity"); } catch { /* keeps the last answer */ }
  drawActivity();
  const busy = activity.data && activity.data.runs.length;
  // Often while something works; rarely when nothing does; slower again while the window is hidden.
  activity.timer = setTimeout(pollActivity, (busy ? 4000 : 20000) * (document.hidden ? 4 : 1));
}

// Asks again soon when the last answer is older than a few seconds (a run was just started or opened).
function nudgeActivity() {
  if (Date.now() - (activity.at || 0) > 3000) pollActivity();
}

function drawActivity() {
  const button = document.getElementById("activity");
  const pop = document.getElementById("activity-pop");
  if (!button || !activity.data) return;
  const {runs} = activity.data;
  const count = runs.length;
  const waiting = runs.some((r) => r.waiting_quota);
  button.hidden = !count;
  button.className = "activity-btn" + (waiting ? " warn" : "");
  fill(button, h("span", {class: "dot", "aria-hidden": "true"}), S("activity_count", {count}));
  button.setAttribute("aria-label", S("activity_label", {count}));
  if (!count) pop.hidden = true;
  const now = Date.now() / 1000;
  fill(pop, h("h3", {}, S("activity_title")),
    runs.length ? h("ul", {class: "plain activity-list"},
      runs.map((r) => h("li", {}, h("div", {class: "activity-head"}, h("button", {type: "button", class: "linkish", onclick: () => { pop.hidden = true; go("runs/" + r.id); }},
        h("b", {}, r.workflow_name)), stopButton(S("stop_named", {name: r.workflow_name}), (b) => stopRun(b, r.id))),
        h("div", {class: "small muted"}, S(r.waiting_quota ? "status_waiting_quota" : "status_" + r.status), " · ",
          S("nodes_done", {done: r.done, total: r.total}), " · ", r.started ? h("span", {"data-since": r.started}, duration(r.started, now)) : ""),
        r.nodes.map((n) => h("div", {class: "small"}, "· ", n.id, n.progress ? ` (${n.progress})` : "", n.waiting_reason ? h("span", {class: "warn-text"}, " — " + n.waiting_reason) : "")))))
      : h("p", {class: "small muted"}, S("activity_none")));
}

function setUpActivity() {
  const button = document.getElementById("activity");
  const pop = document.getElementById("activity-pop");
  button.addEventListener("click", () => {
    pop.hidden = !pop.hidden;
    button.setAttribute("aria-expanded", String(!pop.hidden));
    if (!pop.hidden) pollActivity();
  });
  document.addEventListener("click", (e) => {
    if (!pop.hidden && !pop.contains(e.target) && !button.contains(e.target)) { pop.hidden = true; button.setAttribute("aria-expanded", "false"); }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !pop.hidden) { pop.hidden = true; button.setAttribute("aria-expanded", "false"); button.focus(); }
  });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) pollActivity(); });
  pollActivity();
}

// --- the header's remaining-usage chip ------------------------------------------------------------------------------
// "Kalan: Claude Code %28 · Codex %7": the smallest remaining share of each tool that reports one. Its list shows
// every window with its reset time. Hidden while no tool reports anything.
const usageChip = {timer: null};

async function pollUsage() {
  clearTimeout(usageChip.timer);
  const data = await loadUsage(true);
  drawUsageChip();
  document.querySelectorAll(".usage-mini").forEach((slot) => fill(slot, usageBars(usageOf(slot.dataset.provider), true)));
  document.querySelectorAll(".usage-cell").forEach((slot) => fill(slot, usageCell(slot.dataset.provider)));
  // The server asks Claude Code in the background when its last report is old: the answer is there a moment later.
  usageChip.timer = setTimeout(pollUsage, data && data.refreshing ? 5000 : 60000 * (document.hidden ? 4 : 1));
}

function drawUsageChip() {
  const button = document.getElementById("usage-chip");
  const pop = document.getElementById("usage-pop");
  if (!button || !usageState.data) return;
  const label = (name) => { const p = providerInfo(name) || ((INFO && INFO.providers) || []).find((x) => x.name === name); return (p && p.label) || name; };
  const tools = usageState.data.providers.filter((p) => p.configured).map((p) => ({entry: p, name: label(p.provider),
    live: reportedWindows(p).filter((w) => !w.expired), limited: p.resets_at > Date.now() / 1000}))
    .filter((t) => t.live.length || t.limited || reportedWindows(t.entry).length);
  button.hidden = !tools.length;
  if (!tools.length) { pop.hidden = true; return; }
  const levels = tools.map((t) => usageLevel(t.entry));
  button.className = "activity-btn usage-chip " + (levels.includes("bad") ? "bad" : levels.includes("warn") ? "warn" : "");
  // "Claude %31 · 5 saat": each share with its window, so that a 5-hour and a weekly share are not read as one scale.
  const short = tools.filter((t) => t.live.length || t.limited).map((t) => {
    const top = tightest(t.live);
    return h("span", {class: "usage-chip-tool " + usageLevel(t.entry)}, t.name.replace(/ \(.*\)$/, "").replace(/ (Code|CLI)$/, "") + " ",
      h("b", {}, t.limited || !top ? "0%" : percentText(100 - top.percent)),
      top && !t.limited ? h("span", {class: "usage-chip-window"}, " · " + top.label) : null);
  });
  fill(button, h("span", {class: "usage-chip-title"}, S("usage_left_short")), short.length ? short : h("span", {}, "–"));
  button.setAttribute("aria-label", S("usage_left_title") + ": " + button.textContent);
  fill(pop, h("div", {class: "activity-head"}, h("h3", {}, S("usage_left_title")),
    h("button", {type: "button", class: "btn small", onclick: (e) => refreshUsage(e.currentTarget)}, S("usage_refresh"))),
    h("ul", {class: "plain usage-pop-list"}, tools.map((t) => h("li", {}, h("b", {}, t.name),
      t.limited ? h("div", {class: "small bad-text"}, S("hint_limited", {time: fmtTime(t.entry.resets_at)})) : null, usageBars(t.entry, false)))),
    h("p", {class: "small muted"}, S("usage_left_note")),
    h("button", {type: "button", class: "linkish small", onclick: () => { pop.hidden = true; button.setAttribute("aria-expanded", "false"); go("setup"); }}, S("usage_open_setup")));
}

function setUpUsageChip() {
  const button = document.getElementById("usage-chip");
  const pop = document.getElementById("usage-pop");
  if (!button) return;
  const close = () => { pop.hidden = true; button.setAttribute("aria-expanded", "false"); };
  button.addEventListener("click", () => {
    pop.hidden = !pop.hidden;
    button.setAttribute("aria-expanded", String(!pop.hidden));
    if (!pop.hidden) pollUsage();
  });
  document.addEventListener("click", (e) => { if (!pop.hidden && !pop.contains(e.target) && !button.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !pop.hidden) { close(); button.focus(); } });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) pollUsage(); });
  loadProviderStates().catch(() => null).then(pollUsage);  // app.js: the tools' names
}

// --- favorites -------------------------------------------------------------------------------------------------
function favoriteButton(item, onChange) {
  const on = Boolean(item.favorite);
  return h("button", {type: "button", class: "icon-btn star" + (on ? " on" : ""), "aria-pressed": String(on),
    "aria-label": S(on ? "favorite_remove" : "favorite_add", {name: L(item.name) || item.id}), title: S(on ? "favorite_remove" : "favorite_add", {name: L(item.name) || item.id}),
    onclick: async (e) => {
      e.stopPropagation();
      const r = await act(e.currentTarget, () => api("PUT", `/api/templates/${item.source}/${item.id}/favorite`, {on: !on}));
      if (!r) return;
      for (const t of state.templates || []) if (t.source === item.source && t.id === item.id) t.favorite = r.favorite;
      item.favorite = r.favorite;
      if (onChange) onChange();
      const again = document.querySelector(`.icon-btn.star[aria-label*="${CSS.escape(L(item.name) || item.id)}"]`);
      if (again && r.favorite) confirmPop(again);
    }}, on ? "★" : "☆");
}

// --- the run form's last values (not files; nothing that looks like a secret) ------------------------------------
const SECRETISH = /key|token|password|parola|secret|şifre/i;
const lastKey = (source, id) => `mehteran.last.${source}:${id}`;

function rememberInputs(source, id, fields) {
  const values = {};
  for (const {spec, control} of fields) {
    if (spec.type === "file" || SECRETISH.test(spec.id) || SECRETISH.test(JSON.stringify(spec.label || ""))) continue;
    const value = control.read();
    if (typeof value === "string" && value.length <= 20000) values[spec.id] = value;
  }
  try { localStorage.setItem(lastKey(source, id), JSON.stringify(values)); } catch { /* no storage */ }
}

function recallInputs(source, id) {
  try {
    const data = JSON.parse(localStorage.getItem(lastKey(source, id)) || "null");
    return data && typeof data === "object" && Object.keys(data).length ? data : null;
  } catch { return null; }
}

// --- motion: progress bars that grow, counters that tick, skeletons, a first stagger, small confirmations -------
// Every movement is skipped when the system asks for less motion (the CSS keeps its animations in a
// prefers-reduced-motion: no-preference block too). Only transform and opacity move.
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const barMemory = new Map();

// Progress bars drawn anew at each refresh grow from where they were: scaleX from the last value to the new one.
// scope: what the bars belong to (a run), so that their order is their key.
function animateBars(els, scope) {
  // the endless animations of the page (a sheen, a pulse) keep their phase through the redraws
  document.getElementById("run")?.style.setProperty("--phase", `-${Date.now() % 2400}ms`);
  [...els].forEach((el, i) => {
    const key = `${scope}:${i}`;
    const to = Math.max(0, Math.min(100, Number(el.dataset.w) || 0));
    const from = barMemory.get(key);
    barMemory.set(key, to);
    el.classList.add("scaled");
    el.style.width = "100%";
    if (from == null || from === to || calm()) { el.style.transform = `scaleX(${to / 100})`; return; }
    el.style.transform = `scaleX(${from / 100})`;
    requestAnimationFrame(() => requestAnimationFrame(() => { el.style.transform = `scaleX(${to / 100})`; }));
  });
}

// A loop's part counter ("3/10") counts up from the last value it showed.
const partMemory = new Map();
function tickParts(els, scope) {
  [...els].forEach((el, i) => {
    const key = `${scope}:${i}`;
    const to = Number(el.dataset.done);
    const from = partMemory.get(key);
    partMemory.set(key, to);
    if (from == null || from >= to || calm()) return;
    const text = el.textContent, start = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - start) / 450);
      el.textContent = text.replace(String(to), String(Math.round(from + (to - from) * k)));
      if (k < 1 && el.isConnected) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

// Grey shapes in the place of what is being read: "cards" (the library), "tools" (Setup), "run" (a run page).
function skeleton(kind) {
  const line = (w) => h("span", {class: "sk-line", "data-sk": w});
  const card = () => h("div", {class: "sk-card", "aria-hidden": "true"}, line(60), line(90), line(75));
  const el = kind === "run"
    ? h("div", {class: "skeleton sk-run", "aria-hidden": "true"}, h("div", {class: "sk-line sk-title"}), line(40), h("div", {class: "sk-block"}),
      h("div", {class: "sk-cols"}, h("div", {class: "sk-block"}), h("div", {class: "sk-block short"})))
    : h("div", {class: "skeleton sk-grid " + kind, "aria-hidden": "true"}, Array.from({length: kind === "tools" ? 3 : 6}, card));
  el.querySelectorAll("[data-sk]").forEach((x) => (x.style.width = x.dataset.sk + "%"));
  return h("div", {class: "sk-wrap", role: "status", "aria-label": S("loading")}, el);
}

// The library's cards come in one after the other, once per page load.
function staggerOnce(grid) {
  if (staggerOnce.done || calm()) return;
  staggerOnce.done = true;
  grid.querySelectorAll(".tpl-card").forEach((card, i) => card.style.setProperty("--i", Math.min(i, 14)));
  grid.classList.add("stagger");
  setTimeout(() => grid.classList.remove("stagger"), 1600);
}

// A button that did its job (copied, saved) shows a short check.
function confirmPop(button) {
  if (!button) return;
  button.classList.remove("did");
  void button.offsetWidth;  // restarts the animation
  button.classList.add("did");
  setTimeout(() => button.classList.remove("did"), 1300);
}

// --- the footer ------------------------------------------------------------------------------------------------
const footerState = {stamp: "", stale: false};

async function drawFooter() {
  const foot = document.getElementById("footer");
  if (!foot || !INFO) return;
  const path = h("code", {class: "foot-path"}, INFO.home || "");
  const copy = h("button", {type: "button", class: "btn small", onclick: async (e) => {
    const b = e.currentTarget;
    try { await navigator.clipboard.writeText(INFO.home || ""); confirmPop(b); toast(S("footer_path_copied")); }
    catch { getSelection().selectAllChildren(path); toast(S("copy_select")); }
  }}, S("copy"));
  const lang = document.querySelector(".top .lang-pick-btn");
  fill(foot, h("div", {class: "foot-inner"},
    h("div", {class: "foot-brand"}, h("img", {src: "/icon.svg", alt: "", width: "44", height: "44"}),
      h("div", {}, h("b", {}, S("app_title")), h("p", {class: "small muted"}, S("footer_tagline")))),
    h("nav", {class: "foot-col", "aria-label": S("footer_links")}, h("h4", {}, S("footer_links")),
      h("button", {type: "button", class: "linkish", onclick: openDocs}, S("footer_docs")),
      h("a", {href: "#setup"}, S("tab_setup")),
      lang ? h("button", {type: "button", class: "linkish", onclick: () => { scrollTo({top: 0, behavior: calm() ? "auto" : "smooth"}); lang.click(); }},
        S("footer_language")) : null),
    h("div", {class: "foot-col"}, h("h4", {}, S("footer_data")), path, h("div", {class: "row"}, copy),
      h("p", {class: "small muted"}, S("footer_local"))),
    h("div", {class: "foot-col"}, h("h4", {}, S("footer_version")),
      h("p", {class: "small"}, `v${INFO.version}`, footerState.stamp ? h("code", {class: "small muted"}, " · " + footerState.stamp) : null),
      h("p", {class: "small " + (footerState.stale ? "warn-text" : "muted")}, S(footerState.stale ? "footer_stale" : "footer_updates")))));
}

async function setUpFooter() {
  try {
    const v = await (await fetch("/api/version", {cache: "no-store"})).json();
    footerState.stamp = v.stamp || "";
    footerState.stale = Boolean(v.stale);
  } catch { /* the footer without them */ }
  drawFooter();
  // A new language: the footer's texts again (the page sets <html lang>).
  new MutationObserver(drawFooter).observe(document.documentElement, {attributes: true, attributeFilter: ["lang"]});
}

// The user guide, in the reader dialog (docs/mehteran.md, or its Turkish copy).
// Formatted by markdown.js in the rich reader of app.js (readerOpen); the reader gives the plain one back on close.
async function openDocs() {
  readerOpen(S("footer_docs"));
  const seq = reader.seq;
  document.getElementById("reader-download").hidden = true;
  try {
    const text = (await api("GET", "/api/docs")).text;
    if (seq !== reader.seq) return;
    const page = Markdown.render(text);
    page.classList.add("reader-pane", "docs-page");
    fill(document.getElementById("reader-body"), page);
  } catch (err) {
    if (seq === reader.seq) fill(document.getElementById("reader-body"), h("div", {class: "notice bad reader-pane"}, err.message));
  }
}
