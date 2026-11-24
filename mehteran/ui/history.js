// Mehteran: the run history and its automation (mehteran/history.py, mehteran/sharing.py).
// - The Runs tab's list: search, groups per workflow (collapsible), batch rows with progress; a run's name and note,
//   deleting a run, "delete runs older than".
// - The run page: a finished run's diagram and progress fold into one line.
// - The run window: "once per file" (a batch) and "also save the results to a folder".
// - The workflow drawer's "Share", and the preview before an import (also by dropping a file on the library).
// Loaded before app.js; it uses app.js's helpers (h, S, api, ...) only when called.

const runHistory = {query: "", folded: null, openBatches: new Set(), flowOpen: {}, end: false};

function foldedGroups() {
  if (!runHistory.folded) {
    try { runHistory.folded = new Set(JSON.parse(recall("mehteran.runGroups") || "[]")); } catch { runHistory.folded = new Set(); }
  }
  return runHistory.folded;
}

const runTitle = (r) => r.label || r.workflow_name;

function eventHistory(runId, initial) {
  let events = initial;
  const format = (ev) => [fmtTime(ev.time), ev.node_id, ev.kind, ev.message].filter(Boolean).join(" ");
  const log = h("pre", {class: "log"}, events.map(format).join("\n"));
  const more = h("button", {type: "button", class: "btn small", hidden: events.length < 300,
    onclick: async (e) => {
      const older = await act(e.currentTarget, () => api("GET", `/api/runs/${runId}/events?before=${events[0].id}`));
      if (!older) return;
      events = [...older, ...events];
      log.textContent = events.map(format).join("\n");
      more.hidden = older.length < 300;
    }}, S("events_load_older"));
  return h("details", {class: "logbox"}, h("summary", {}, S("events")), more, log);
}

// --- the list ---------------------------------------------------------------------------------------------
function historyTools(refresh) {
  const box = $("#run-tools");
  if (!box || box.dataset.ready) return;
  box.dataset.ready = "1";
  const search = h("input", {type: "search", class: "run-search", placeholder: S("runs_search"), "aria-label": S("runs_search"),
    value: runHistory.query, oninput: (e) => {
      runHistory.query = e.target.value;
      clearTimeout(runHistory.searchTimer);
      runHistory.searchTimer = setTimeout(() => {
        if (state.hash === "runs") showRuns([]);
      }, 200);
    }});
  const days = h("select", {"aria-label": S("runs_cleanup_age")}, [30, 90, 365].map((d) => h("option", {value: d}, S("runs_older_days", {days: d}))));
  const prune = h("input", {type: "checkbox"});
  const clean = h("button", {type: "button", class: "btn small", onclick: (e) =>
    cleanupRuns(e.currentTarget, Number(days.value), refresh, prune.checked)}, S("runs_cleanup"));
  const trashItems = h("ul", {class: "plain"});
  const trash = h("details", {ontoggle: async (e) => {
    if (!e.currentTarget.open) return;
    try {
      const runs = await api("GET", "/api/runs/trash");
      fill(trashItems, runs.length ? runs.map((r) => h("li", {class: "row"}, r.name,
        h("button", {type: "button", class: "btn small", onclick: async (ev) => {
          if (await act(ev.currentTarget, () => api("POST", `/api/runs/${r.id}/restore`, {}))) {
            trash.open = false;
            refresh(true);
          }
        }}, S("run_restore")))) : h("li", {}, S("no_runs")));
    } catch (err) { fill(trashItems, h("li", {}, err.message)); }
  }}, h("summary", {class: "small muted"}, S("runs_trash")), trashItems);
  const storage = h("p", {class: "small muted", role: "status"});
  box.append(search, trash, h("details", {class: "run-cleanup", ontoggle: async (e) => {
    if (!e.currentTarget.open) return;
    try {
      const space = await api("GET", "/api/storage");
      storage.textContent = S("run_storage_space", {used: fileSize(space.used), free: fileSize(space.free)});
    } catch (err) { storage.textContent = err.message; }
  }}, h("summary", {class: "small muted"}, S("runs_cleanup_title")),
    storage, h("p", {class: "small muted"}, S("run_storage_sensitive")),
    h("div", {class: "row"}, days, clean), h("label", {class: "row"}, prune, S("usage_prune_old"))));
}

async function cleanupRuns(button, days, refresh, pruneUsage) {
  const preview = await act(button, () => api("POST", "/api/runs/cleanup", {days, dry_run: true}));
  if (!preview) return;
  if (!preview.count && !pruneUsage) return toast(S("runs_cleanup_none", {days}));
  const ok = await askConfirm(S("runs_cleanup_confirm_title"), [S("runs_cleanup_confirm", {count: preview.count, days, size: fileSize(preview.size)}),
    pruneUsage ? S("usage_prune_old") : S("runs_delete_note")], S("delete"), true);
  if (!ok) return;
  const done = await act(button, () => api("POST", "/api/runs/cleanup", {days, prune_usage: pruneUsage}));
  if (!done) return;
  toast(S("runs_cleanup_done", {count: done.deleted, size: fileSize(done.size)}));
  refresh(true);
}

// One run of the list: its name (or the workflow's), its main input and its time; a stop button while it works.
function historyRow(r, selected, refresh) {
  const mark = badge(r.waiting_quota ? "waiting_quota" : r.status);
  const sub = [r.main_input, fmtTime(r.created)].filter(Boolean).join(" · ");
  return h("li", {class: "rl-item"}, h("button", {type: "button", class: r.id === selected ? "active" : "", title: r.note || null,
    "aria-current": r.id === selected ? "true" : null, onclick: () => go("runs/" + r.id)},
    h("span", {class: "rl-main"}, h("span", {class: "rl-name"}, r.label || r.main_input || r.workflow_name),
      h("span", {class: "small muted rl-sub"}, r.label ? sub : fmtTime(r.created))),
    mark),
    FINAL.has(r.status) ? null : stopButton(S("stop_named", {name: runTitle(r)}), (b) => stopRun(b, r.id, refresh)));
}

// The runs of one batch: one row with the progress; opened, the runs under it.
function batchRow(runs, selected, refresh) {
  const id = runs[0].batch, done = runs.filter((r) => FINAL.has(r.status)).length;
  const failed = runs.filter((r) => ["failed", "cancelled", "interrupted"].includes(r.status)).length;
  const open = runHistory.openBatches.has(id) || runs.some((r) => r.id === selected);
  const toggle = () => { if (open) runHistory.openBatches.delete(id); else runHistory.openBatches.add(id); refresh(); };
  return h("li", {class: "rl-batch"},
    h("button", {type: "button", class: "rl-batch-head", "aria-expanded": String(open), onclick: toggle},
      h("span", {class: "rl-main"}, h("span", {class: "rl-name"}, (open ? "▾ " : "▸ ") + S("batch_row", {count: runs.length})),
        h("span", {class: "small muted"}, S("batch_progress", {done, total: runs.length}), failed ? " · " + S("batch_failed", {count: failed}) : "",
          " · ", fmtTime(runs[runs.length - 1].created))),
      done < runs.length ? h("span", {class: "dot"}) : badge(failed ? "failed" : "succeeded")),
    h("div", {class: "track rl-track", "aria-hidden": "true"}, h("div", {class: "fill" + (failed ? " failed" : ""), "data-w": Math.round(100 * done / runs.length)})),
    open ? h("ul", {class: "rl-batch-runs"}, runs.map((r) => historyRow(r, selected, refresh))) : null);
}

function historyGroup(key, title, items, count, refresh, icon) {
  const folded = foldedGroups();
  const closed = folded.has(key) && !runHistory.query.trim();
  const toggle = () => {
    if (folded.has(key)) folded.delete(key); else folded.add(key);
    remember("mehteran.runGroups", JSON.stringify([...folded]));
    refresh();
  };
  return [h("li", {class: "rl-group"}, h("button", {type: "button", class: "rl-group-head", "aria-expanded": String(!closed), onclick: toggle},
    h("span", {class: "rl-name"}, closed ? "▸ " : "▾ ", icon || null, title), h("span", {class: "count small muted"}, String(count)))),
  ...(closed ? [] : items)];
}

// The Runs tab's list (renderRunList in app.js calls it).
function historyList(runs, selected) {
  const draw = (reload) => (reload ? showRuns(selected ? [selected] : []) : historyList(runs, selected));
  historyTools(draw);
  const groups = new Map();
  for (const r of runs) {
    const key = r.template || r.workflow_id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const items = [];
  for (const [key, list] of groups) {
    const rows = [], seen = new Set();
    for (const r of list) {
      if (r.batch) {
        if (seen.has(r.batch)) continue;
        seen.add(r.batch);
        rows.push(batchRow(list.filter((x) => x.batch === r.batch).reverse(), selected, draw));
      } else rows.push(historyRow(r, selected, draw));
    }
    items.push(...historyGroup("w:" + key, list[0].workflow_name, rows, list.length, draw));
  }
  const plans = (state.schedules || []).filter((p) => !runHistory.query.trim() || fold(p.name).includes(fold(runHistory.query.trim())));
  if (plans.length) items.unshift(...historyGroup("schedules", S("schedules_title"), plans.map((p) => scheduleRow(p, draw)), plans.length, draw));
  const q = fold(runHistory.query.trim());
  if (!items.length && q) items.push(h("li", {class: "muted pl-empty", role: "status"}, S("runs_no_match")));
  if (runs.length && !runHistory.end) items.push(h("li", {},
    h("button", {type: "button", class: "btn small", onclick: async (e) => {
      const query = runHistory.query;
      const older = await act(e.currentTarget, () => api("GET", historyUrl(runs.at(-1).id)));
      if (!older || state.hash !== "runs" || query !== runHistory.query) return;
      runHistory.end = older.length < 200;
      historyList([...runs, ...older], selected);
    }}, S("runs_load_older"))));
  fill($("#run-list"), items);
  animateBars(document.querySelectorAll("#run-list .fill[data-w]"), "run-list");
}

// --- scheduled runs (mehteran/schedules.py) ---------------------------------------------------------------
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];  // 0 is Monday

function ruleText(rule) {
  if (rule.every_hours) return S("schedule_every_hours", {hours: rule.every_hours});
  const days = rule.days.length === 7 ? S("schedule_every_day")
    : rule.days.length === 5 && rule.days.every((d) => d < 5) ? S("schedule_weekdays")
    : rule.days.map((d) => S("weekday_" + d)).join(", ");
  return `${days} · ${rule.time}`;
}

// One schedule in the Runs tab's list: its rule and next time; pause or resume, run now, delete.
function scheduleRow(p, refresh) {
  const sub = [ruleText(p.rule), p.enabled ? S("schedule_next", {when: fmtTime(p.next_at)}) : S("schedule_paused")].join(" · ");
  const toggle = async (b) => {
    if (await act(b, () => api("PUT", `/api/schedules/${p.id}`, {enabled: !p.enabled}))) refresh(true);
  };
  const runNow = async (b) => {
    const res = await act(b, () => api("POST", `/api/schedules/${p.id}/run`, {}));
    if (res) { toast(S("run_started_toast")); go("runs/" + res.id); }
  };
  const remove = async (b) => {
    if (!(await askConfirm(S("schedule_delete_title", {name: p.name}), [S("schedule_delete_text")], S("delete"), true))) return;
    if (await act(b, () => api("DELETE", `/api/schedules/${p.id}`, {}))) { toast(S("schedule_deleted")); refresh(true); }
  };
  return h("li", {class: "rl-item rl-schedule"},
    h("button", {type: "button", title: p.last_error || null, onclick: () => (p.last_run ? go("runs/" + p.last_run) : null)},
      h("span", {class: "rl-main"}, h("span", {class: "rl-name"}, "⏲ " + p.name),
        h("span", {class: "small muted rl-sub"}, sub),
        p.last_error ? h("span", {class: "small warn-text"}, p.last_error) : null),
      p.last_status ? badge(p.last_status) : null),
    h("div", {class: "row rl-schedule-actions"},
      h("button", {type: "button", class: "btn small", onclick: (e) => toggle(e.currentTarget)}, S(p.enabled ? "schedule_pause" : "schedule_resume")),
      h("button", {type: "button", class: "btn small", onclick: (e) => runNow(e.currentTarget)}, "▶ " + S("schedule_run_now")),
      h("button", {type: "button", class: "btn small danger", onclick: (e) => remove(e.currentTarget)}, S("delete"))));
}

// The run window's "Run on a schedule": the days and the time, or every N hours. read(): the rule, or null.
function scheduleField(tpl, onChange) {
  const files = (tpl.input_specs || []).some((s) => s.type === "file" && s.required !== false);
  const on = h("input", {type: "checkbox", id: "sched-on", disabled: files, onchange: () => { box.hidden = !on.checked; onChange(on.checked); }});
  const kind = h("select", {id: "sched-kind", "aria-label": S("schedule_kind"), onchange: () => draw()},
    h("option", {value: "days"}, S("schedule_kind_days")), h("option", {value: "hours"}, S("schedule_kind_hours")));
  const days = WEEKDAYS.map((d) => h("input", {type: "checkbox", value: d, checked: true, "aria-label": S("weekday_" + d)}));
  const at = h("input", {type: "time", value: "08:00", "aria-label": S("schedule_time"), required: true});
  const hours = h("input", {type: "number", min: 1, max: 168, value: 6, "aria-label": S("schedule_hours")});
  const name = h("input", {type: "text", id: "sched-name", maxlength: 120, placeholder: L(tpl.name) || ""});
  const dayRow = h("div", {class: "row sched-days"}, days.map((box, i) => h("label", {class: "check small"}, box, S("weekday_" + i))), at);
  const hourRow = h("div", {class: "row", hidden: true}, h("span", {class: "small"}, S("schedule_every")), hours, h("span", {class: "small"}, S("schedule_hours")));
  const draw = () => { dayRow.hidden = kind.value !== "days"; hourRow.hidden = kind.value !== "hours"; };
  const box = h("div", {class: "stack sched-box", hidden: true}, kind, dayRow, hourRow,
    h("label", {class: "fld-label", for: "sched-name"}, S("schedule_name")), name,
    h("p", {class: "small muted"}, S("schedule_hint")));
  // A workflow that needs a file cannot be scheduled (a schedule keeps only text values): no choice is shown.
  const el = h("section", {class: "run-extras stack", hidden: files},
    h("label", {class: "check", for: "sched-on"}, on, S("schedule_on")), box);
  el.read = () => {
    if (!on.checked) return null;
    if (kind.value === "hours") return {every_hours: Number(hours.value)};
    const chosen = days.filter((d) => d.checked).map((d) => Number(d.value));
    if (!chosen.length) throw new Error(S("schedule_no_days"));
    return {days: chosen, time: at.value};
  };
  el.name = () => name.value.trim();
  return el;
}

// The Setup tab's "Run in the background" (mehteran/background.py).
async function loadBackground() {
  const panel = $("#background-panel");
  if (!panel) return;
  let st;
  try { st = await api("GET", "/api/background"); } catch (err) { return fill(panel, problemsBox(err)); }
  const change = async (b, enabled) => {
    if (!enabled && st.this_server && !(await askConfirm(S("background_stop_title"), [S("background_stop_text")], S("background_turn_off"), true))) return;
    const res = await act(b, () => api("PUT", "/api/background", {enabled}));
    if (!res) return;
    toast(S(enabled ? (res.running ? "background_on_toast" : "background_on_later") : "background_off_toast"));
    if (!(st.this_server && !enabled)) loadBackground();
  };
  fill(panel, h("div", {class: "tool-head"}, h("h3", {}, S("background_title")),
      h("span", {class: "badge " + (st.enabled ? "good" : "")}, S(st.enabled ? "background_enabled" : "background_disabled"))),
    h("p", {class: "small muted"}, S("background_about")),
    st.this_server ? h("p", {class: "small good-text"}, "✓ " + S("background_this")) : null,
    st.enabled && !st.this_server ? h("p", {class: "small muted"}, S("background_waiting")) : null,
    st.supported ? h("div", {class: "actions"}, h("button", {type: "button", class: st.enabled ? "btn danger" : "btn primary",
      onclick: (e) => change(e.currentTarget, !st.enabled)}, S(st.enabled ? "background_turn_off" : "background_turn_on")))
      : h("p", {class: "small warn-text"}, S("background_unsupported")),
    h("p", {class: "small muted"}, S("background_log", {path: st.log})));
}

// --- one run: its name and note, delete, where its results were saved -------------------------------------
function runManage(run, runId) {
  const rename = h("button", {type: "button", class: "btn", onclick: () => renameRun(run, runId)}, "✎ " + S("run_rename"));
  const remove = FINAL.has(run.status) && !run.active ? h("button", {type: "button", class: "btn danger", onclick: (e) => deleteRun(e.currentTarget, run, runId)},
    S("delete")) : null;
  return [rename, remove];
}

function renameRun(run, runId) {
  const dialog = $("#confirm-dialog");
  const label = h("input", {type: "text", id: "run-label", maxlength: 120, value: run.label || "", placeholder: run.workflow_name});
  const note = h("textarea", {id: "run-note", rows: 4, maxlength: 2000});
  note.value = run.note || "";
  const status = h("p", {class: "small warn-text", role: "status"});
  fill(dialog, h("form", {onsubmit: async (e) => {
    e.preventDefault();
    try {
      await api("PUT", `/api/runs/${runId}/label`, {label: label.value, note: note.value});
      dialog.close();
      toast(S("saved"));
      showRuns([runId]);
    } catch (err) { status.textContent = err.message; }
  }},
  h("div", {class: "dialog-head"}, h("h3", {id: "confirm-title"}, S("run_rename_title"))),
  h("div", {class: "layout-body stack"},
    h("label", {class: "fld-label", for: "run-label"}, S("run_label")), label, h("p", {class: "small muted"}, S("run_label_hint")),
    h("label", {class: "fld-label", for: "run-note"}, S("run_note")), note, status),
  h("div", {class: "dialog-foot row"}, h("button", {type: "button", class: "btn", onclick: () => dialog.close()}, S("cancel_action")),
    h("button", {type: "submit", class: "btn primary"}, S("save")))));
  dialog.showModal();
  label.focus();
}

async function deleteRun(button, run, runId) {
  const info = await act(button, () => api("DELETE", `/api/runs/${runId}`, {dry_run: true}));
  if (!info) return;
  if (!info.deletable) return toast(S("run_delete_busy"), true);
  const ok = await askConfirm(S("run_delete_title", {name: runTitle(run)}),
    [S("run_trash_text")], S("runs_trash"), true);
  if (!ok) return;
  if (await act(button, () => api("DELETE", `/api/runs/${runId}`, {trash: true}))) {
    toast(S("runs_trash"));
    go("runs");
  }
}

// The name and the note under the title; where the results were saved (or why not).
function runNotes(run) {
  const saved = run.output_state ? (() => { try { return JSON.parse(run.output_state); } catch { return null; } })() : null;
  return [run.label ? h("p", {class: "small muted run-of"}, S("run_of", {name: run.workflow_name})) : null,
    run.note ? h("p", {class: "run-note"}, run.note) : null,
    run.output_dir && !saved && run.status !== "succeeded" ? h("p", {class: "small muted"}, S("output_waiting", {path: run.output_dir})) : null,
    saved && saved.error ? h("div", {class: "notice warn"}, S("output_failed", {path: saved.folder || run.output_dir, error: saved.error})) : null,
    saved && !saved.error ? h("p", {class: "small good-text"}, "✓ " + S("output_saved", {count: (saved.saved || []).length, path: saved.folder})) : null];
}

// A finished run: the diagram, the steps and the log fold into one line, so the results get the room. A run that
// did not succeed stays open (its steps can be retried there); a step chosen on the page opens it too.
function flowFold(run, runId, content) {
  if (!FINAL.has(run.status)) return content;
  const steps = run.graph.nodes.length;
  const done = run.graph.nodes.filter((g) => ["succeeded", "skipped"].includes(run.nodes[g.id].status)).length;
  const key = runId;
  const open = key in runHistory.flowOpen ? runHistory.flowOpen[key] : run.status !== "succeeded" || Boolean(state.selectedNode);
  const box = h("details", {class: "flow-fold", open},
    h("summary", {}, h("span", {}, S("flow_line", {done, total: steps, time: duration(run.started, run.finished)})),
      h("span", {class: "linkish small"}, S(open ? "flow_hide" : "flow_show"))),
    content);
  box.addEventListener("toggle", () => {
    runHistory.flowOpen[key] = box.open;
    $(".linkish", box.firstChild).textContent = S(box.open ? "flow_hide" : "flow_show");
    if (box.open && state.runCanvas) requestAnimationFrame(() => state.runCanvas.fit());
  });
  return box;
}

// --- the run window: once per file, save to a folder --------------------------------------------------------
// fields: openRun's [{spec, control, row}]; estimate: the runEstimate element (its count is shown × the files).
function runExtras(source, id, fields, estimate) {
  const target = fields.find((f) => f.spec.type === "file" && !f.spec.multiple);
  const chosen = [];
  let batch = null;
  if (target) {
    const list = h("ul", {class: "file-list"});
    const note = h("p", {class: "small muted", "aria-live": "polite"});
    const accept = (target.spec.formats || INFO.file_formats).map((f) => "." + f).join(",");
    const picker = h("input", {type: "file", multiple: true, accept, "aria-label": S("batch_files"), onchange: () => {
      for (const f of picker.files) if (!chosen.some((c) => c.name === f.name && c.size === f.size)) chosen.push(f);
      picker.value = "";
      draw();
    }});
    const draw = () => {
      fill(list, chosen.map((f, i) => h("li", {}, h("span", {class: "file-name"}, f.name), h("span", {class: "small muted"}, fileSize(f.size)),
        h("button", {type: "button", class: "icon-btn danger", "aria-label": `${S("remove")}: ${f.name}`, title: S("remove"),
          onclick: () => { chosen.splice(i, 1); draw(); }}, "✕"))));
      note.textContent = S("batch_summary", {count: chosen.length, max: 50, parallel: 2});
      if (estimate.setTimes) estimate.setTimes(on.checked ? Math.max(chosen.length, 1) : 1);
    };
    const multi = h("div", {class: "multi-file batch-files", hidden: true}, filePicker(picker, true), list, note);
    const single = $("input[type=file]", target.control);
    const on = h("input", {type: "checkbox", id: "batch-on", onchange: () => {
      multi.hidden = !on.checked;
      target.control.hidden = on.checked;
      if (single) single.required = !on.checked && target.spec.required !== false;  // the form's own check
      draw();
    }});
    target.row.insertBefore(multi, target.control.nextSibling);
    target.row.appendChild(h("label", {class: "check small", for: "batch-on"}, on, S("batch_each")));
    batch = {on, input: target.spec.id, files: chosen};
  }
  const folder = h("input", {type: "text", id: "out-dir", class: "mono", spellcheck: "false", autocomplete: "off",
    placeholder: S("output_placeholder"), "aria-describedby": "out-dir-note"});
  const save = h("input", {type: "checkbox", id: "out-on", onchange: () => { folderRow.hidden = !save.checked; if (save.checked) folder.focus(); }});
  const problem = h("p", {class: "small warn-text", id: "out-dir-note", "aria-live": "polite"});
  const folderRow = h("div", {class: "stack", hidden: true}, folder, problem, h("p", {class: "small muted"}, S("output_hint")));
  api("GET", `/api/output-folders/${source}/${id}`).then((r) => { if (r.path) folder.value = r.path; }).catch(() => {});
  const el = h("section", {class: "run-extras stack"},
    h("label", {class: "check", for: "out-on"}, save, S("output_save")), folderRow);
  // Before the files are sent: the folder is checked, and confirmed once by the user.
  el.prepare = async () => {
    const out = {};
    if (save.checked) {
      const check = await api("POST", "/api/output-folders/check", {path: folder.value});
      if (check.problem) { problem.textContent = check.problem; folder.focus(); throw new Error(check.problem); }
      problem.textContent = "";
      if (!check.confirmed) {
        const ok = await askConfirm(S("output_confirm_title"), [S("output_confirm_text", {path: check.path}), S("output_confirm_note")], S("output_confirm_ok"));
        if (!ok) throw new Error(S("output_not_confirmed"));
      }
      Object.assign(out, {output_dir: check.path, output_confirmed: true});
    }
    if (batch && batch.on.checked) {
      if (!chosen.length) throw new Error(S("batch_none"));
      if (chosen.length > 50) throw new Error(S("batch_many", {max: 50}));
      out.batchFiles = chosen.slice();
      out.batchInput = batch.input;
    }
    return out;
  };
  el.batchOn = () => Boolean(batch && batch.on.checked);
  return el;
}

// "× N runs" under the estimate (runEstimate in app.js calls it when the count of files changes).
function batchEstimateLine(est, times) {
  if (!(times > 1) || !est || !est.steps || !est.steps.length) return null;
  return h("p", {class: "small estimate-batch"}, S("estimate_batch", {runs: times, calls: est.calls * times, max: est.max_calls * times}));
}

// --- results as JSON: shown pretty-printed ------------------------------------------------------------------
function jsonPretty(text) {
  const t = String(text || "").trim();
  if (!/^[[{]/.test(t) || !/[\]}]$/.test(t) || t.length > 2000000) return null;
  try { return JSON.stringify(JSON.parse(t), null, 2); } catch { return null; }
}

// --- share and the import preview ---------------------------------------------------------------------------
function shareBox(source, id) {
  const author = h("input", {type: "text", id: "share-author", maxlength: 80, value: recall("mehteran.author") || "", placeholder: S("share_author_hint")});
  const link = h("a", {class: "btn primary", href: "#", onclick: (e) => {
    remember("mehteran.author", author.value.trim());
    e.currentTarget.href = `/api/templates/${source}/${id}/share?token=${encodeURIComponent(TOKEN)}&author=${encodeURIComponent(author.value.trim())}`;
  }}, "⇩ " + S("share_download"));
  const box = h("div", {class: "share-box stack", hidden: true},
    h("p", {class: "small muted"}, S("share_text")),
    h("label", {class: "fld-label", for: "share-author"}, S("share_author")), h("div", {class: "row"}, author, link));
  const button = h("button", {type: "button", class: "btn", "aria-expanded": "false", onclick: () => {
    box.hidden = !box.hidden;
    button.setAttribute("aria-expanded", String(!box.hidden));
    if (!box.hidden) author.focus();
  }}, "↗ " + S("share"));
  return {button, box};
}

const LOCAL_NAMES = {typst: "Typst (PDF)", pandoc: "Pandoc", ocr: "Tesseract OCR", speech: "whisper.cpp"};

async function showImportPreview(text) {
  openDrawer(h("p", {class: "muted"}, S("loading")));
  let p, tools, local;
  try {
    [p, tools, local] = await Promise.all([api("POST", "/api/templates/preview", {yaml: text}),
      api("GET", "/api/tools").catch(() => null), api("GET", "/api/local-tools").catch(() => null)]);
  } catch (err) { return openDrawer(problemsBox(err)); }
  const newId = h("input", {type: "text", class: "mono", id: "import-id", value: p.id ? p.id + "-2" : "", spellcheck: "false", "aria-label": S("new_id")});
  const result = h("div", {"aria-live": "polite"});
  const toolOf = (provider) => tools && tools.tools.find((tool) => tool.provider === provider);
  const modelRow = (m) => {
    const tool = toolOf(m.provider);
    const ready = tool ? tool.installed && tool.signed_in : (INFO.providers || []).some((x) => x.name === m.provider);
    return h("li", {}, h("code", {}, m.model || m.provider || "–"), " ", m.tool_name ? h("span", {class: "small muted"}, m.tool_name + " ") : null,
      !m.configured ? h("span", {class: "badge bad"}, S("estimate_not_configured"))
        : h("span", {class: "badge " + (ready ? "good" : "warn")}, S(ready ? "preview_ready" : tool && !tool.installed ? "not_installed" : "not_signed_in")));
  };
  const localRow = (name) => {
    const item = local && local.tools.find((x) => x.id === name);
    return h("li", {}, LOCAL_NAMES[name] || name, " ", item ? h("span", {class: "badge " + (item.installed ? "good" : "warn")},
      S(item.installed ? "preview_ready" : "not_installed")) : null);
  };
  const add = h("button", {type: "button", class: "btn primary", disabled: !p.valid, onclick: async (e) => {
    const body = {yaml: text};
    if (p.exists) body.id = newId.value.trim();
    const r = await act(e.currentTarget, () => api("POST", "/api/templates/import", body));
    if (r) { toast(S("imported", {id: r.id})); await loadTemplateList(); go(`workflows/user/${r.id}`); }
  }}, "＋ " + S("preview_add"));
  openDrawer(
    h("div", {class: "drawer-head"},
      h("div", {class: "stack"}, h("p", {class: "row small"}, h("span", {class: "badge"}, S("preview_badge")),
        p.version ? h("span", {class: "muted"}, "v" + p.version) : null,
        p.author ? h("span", {class: "muted"}, S("preview_author", {name: String(p.author)})) : null,
        p.based_on ? h("span", {class: "muted"}, S("based_on") + " " + p.based_on) : null),
      h("h2", {id: "drawer-title"}, L(p.name) || p.id || S("import_title"))),
      h("button", {type: "button", class: "icon-btn drawer-x", "aria-label": S("close"), title: S("close"), onclick: () => go("workflows")}, "✕")),
    p.description ? h("p", {class: "drawer-desc"}, L(p.description)) : null,
    h("p", {class: "small muted"}, S("preview_lede")),
    p.valid ? null : problemsBox({message: S("problems_found", {count: p.problems.length}), problems: p.problems}),
    p.exists ? h("div", {class: "notice warn stack"}, h("span", {}, S("preview_exists", {id: p.id})),
      h("label", {class: "row"}, h("span", {class: "small"}, S("new_id")), newId)) : null,
    h("div", {class: "row drawer-actions"}, add, h("button", {type: "button", class: "btn", onclick: () => openDrawer(importView(text))}, S("preview_back")), result),
    p.graph ? h("section", {class: "drawer-sec"}, h("h3", {}, S("graph")), previewCanvas(p.graph)) : null,
    p.valid ? h("section", {class: "drawer-sec"}, h("h3", {}, S("preview_needs")),
      h("ul", {class: "plain"}, (p.models || []).map(modelRow), (p.local_tools || []).map(localRow),
        p.reads_web ? h("li", {class: "small"}, S("preview_web")) : null,
        !(p.models || []).length && !(p.local_tools || []).length && !p.reads_web ? h("li", {class: "small muted"}, S("preview_needs_none")) : null)) : null,
    (p.input_specs || []).length ? h("section", {class: "drawer-sec"}, h("h3", {}, S("inputs")), h("ul", {class: "plain"}, p.input_specs.map((spec) =>
      h("li", {}, h("b", {}, L(spec.label) || spec.id), " ", h("span", {class: "small muted"}, S("input_type_" + spec.type)))))) : null,
    (p.prompts || []).length ? h("section", {class: "drawer-sec"}, h("h3", {}, S("preview_prompts", {count: p.prompts.length})),
      p.prompts.map((x) => h("div", {class: "preview-prompt"}, h("p", {class: "small"}, h("b", {}, L(x.label) || x.node), " · ", L(x.field_label) || x.field),
        h("pre", {class: "code"}, x.text)))) : null);
}

// A workflow file dropped on the library: its preview.
function setUpLibraryDrop() {
  const zone = document.getElementById("library");
  if (!zone) return;
  zone.addEventListener("dragover", (e) => {
    if (![...(e.dataTransfer.items || [])].some((i) => i.kind === "file")) return;
    e.preventDefault();
    zone.classList.add("drop-on");
  });
  zone.addEventListener("dragleave", (e) => { if (e.target === zone) zone.classList.remove("drop-on"); });
  zone.addEventListener("drop", async (e) => {
    zone.classList.remove("drop-on");
    const file = [...(e.dataTransfer.files || [])][0];
    if (!file) return;
    e.preventDefault();
    if (!/\.ya?ml$/i.test(file.name) || file.size > 1000000) return toast(S("drop_not_yaml"), true);
    const text = await file.text();
    if (state.hash !== "workflows/import") { state.importText = text; go("workflows/import"); } else showImportPreview(text);
  });
}

document.addEventListener("DOMContentLoaded", setUpLibraryDrop);
