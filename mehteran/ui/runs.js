"use strict";

// --- runs: the history and one run (live) -----------------------------------------------------------
function historyUrl(before = "") {
  return "/api/runs?" + new URLSearchParams({q: runHistory.query.trim(), before});
}

async function showRuns(parts) {
  const query = runHistory.query;
  const [runs, books, plans] = await Promise.all([api("GET", historyUrl()), api("GET", "/api/translation/runs").catch(() => []),
    api("GET", "/api/schedules").catch(() => [])]);
  if (state.tab !== "runs" || query !== runHistory.query) return;
  state.trRuns = books;
  state.schedules = plans;
  runHistory.older = [];
  runHistory.end = runs.length < 200;
  const selected = parts[0];
  renderRunList(runs, selected);
  if (selected) return parts[1] === "again" ? showSavedRunForm(selected) : showRun(selected);
  fill($("#run"), runs.length || books.length ? h("div", {class: "empty"}, S("pick_run"))
    : h("div", {class: "welcome"}, h("h2", {}, S("first_run_title")), h("p", {}, S("first_run_text")),
      h("button", {type: "button", class: "btn primary", onclick: () => go("workflows")}, S("go_workflows"))));
}

async function showSavedRunForm(id) {
  const body = $("#run");
  fill(body, skeleton("run"));
  try {
    const run = await api("GET", `/api/runs/${id}`);
    if (state.hash !== `runs/${id}/again`) return;
    const [source, template] = run.template.split(":");
    fill(body, h("button", {type: "button", class: "btn small", onclick: () => go("runs/" + id)}, S("cancel_action")),
      h("h2", {}, run.workflow_name), h("p", {class: "muted"}, S("saved_run_version")),
      runForm({name: run.workflow_name, description: run.description, input_specs: run.input_specs,
        model: {privacy: run.local_only ? "local" : ""}}, source || "user", template || run.workflow_id, run));
  } catch (err) {
    if (state.hash === `runs/${id}/again`) fill(body, problemsBox(err));
  }
}

// The workflow runs, then the last run of each book of the book translation (it opens the translation's books).
// What runs has a stop button: a workflow run can be resumed later, a book translation continues where it stopped.
// history.js draws it: a search field, a group per workflow (a batch as one row), the book translations' group.
function renderRunList(runs, selected) {
  historyList(runs, selected);
}

async function showRun(runId, keep) {
  if (!keep) { state.selectedNode = null; state.runCanvas = null; fill($("#run"), skeleton("run")); }
  let run;
  try { run = await api("GET", `/api/runs/${runId}`); }
  catch (err) { fill($("#run"), problemsBox(err)); return; }
  if (state.tab !== "runs" || state.hash !== "runs/" + runId) return;
  if (keep && run.status !== state.runStatus) api("GET", historyUrl()).then((runs) => {
    const recent = new Set(runs.map((r) => r.id));
    renderRunList([...runs, ...runHistory.older.filter((r) => !recent.has(r.id))], runId);
  }).catch(() => {});
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
  actions.push(h("button", {type: "button", class: "btn", onclick: () => go(`runs/${runId}/again`)},
    "▶ " + S("run_again")));
  actions.push(...runManage(run, runId).filter(Boolean));  // history.js: rename, delete

  const outputs = runResults(run);  // the results box: resultsBox() (the reader, compare, edit and export)
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
        h("div", {class: "book-title"}, h("h2", {}, run.label || run.workflow_name), badge(run.status), live ? h("span", {class: "dot", title: S("live")}) : null),
        Object.entries(run.nodes).filter(([, n]) => n.status === "waiting_quota")
          .map(([id, n]) => h("p", {class: "small warn-text"}, run.providers[id], " · ", n.error,
            n.quota_until ? [" · ", h("span", {"data-until": n.quota_until},
              duration(Date.now() / 1000, Math.max(Date.now() / 1000, Number(n.quota_until))))] : null)),
        h("p", {class: "row small muted"}, h("span", {}, S("started"), ": ", fmtTime(run.started || run.created)),
          h("span", {}, S("col_duration"), ": ", duration(run.started, run.finished)),
          h("span", {}, S("nodes_done", {done, total: run.graph.nodes.length})), h("code", {}, run.id),
          run.template ? h("code", {}, run.template) : null),
        runNotes(run)),  // history.js: the run's name and note, where its results were saved
      actions.length ? h("div", {class: "row run-actions"}, actions) : null),
    run.error ? h("div", {class: "notice bad"}, h("b", {}, S("error")), " ", run.error) : null,
    live ? overall : null,
    waiting.length ? h("div", {class: "notice warn", role: "status"}, h("b", {}, S("status_waiting_quota")), " ",
      waiting.map((g) => `${L(run.node_info[g.id].label) || g.id}: ${run.nodes[g.id].error || ""}`).join(" · "), " ",
      h("button", {type: "button", class: "btn small switch-open", onclick: () => { state.selectedNode = waiting[0].id; state.switchOpen = `${runId}:${waiting[0].id}`; refresh(); }},
        S("switch_model"))) : null,
    (run.shares || []).map((s) => h("section", {class: "card box share-box"}, h("h3", {}, L(s.label) || S("share_on_x")),
      h("p", {class: "share-text"}, s.text),
      h("div", {class: "row"}, h("a", {class: "btn primary", href: s.url, target: "_blank", rel: "noopener noreferrer"}, "↗ " + S("share_on_x")),
        h("span", {class: "small muted"}, S("share_on_x_hint"))))),
    outputs.length ? resultsBox(run, runId, outputs) : null,
    flowFold(run, runId, h("div", {class: "run-cols"},  // history.js: one line for a finished run
      h("div", {class: "run-main"},
        h("section", {class: "card box run-graph"}, h("div", {class: "row run-graph-head"}, h("h3", {}, S("graph")),
          h("button", {type: "button", class: "btn small", onclick: () => state.runCanvas.fit()}, S("fit"))),
          state.runCanvas.el, h("p", {class: "small muted"}, S("monitor_hint"))),
        h("section", {class: "card box timeline"}, h("h3", {}, S("progress")), h("ol", {class: "tl"}, timeline)),
        liveLogPanel(run, runId)),  // live.js: the selected (or working) step's log, kept between redraws
      h("aside", {class: "run-aside"}, nodePanel(run, runId, post)))),
    // A file input's value is its stored path, or a list of paths for a several-files input.
    h("details", {class: "logbox"}, h("summary", {}, S("inputs_used")), h("ul", {class: "plain"}, Object.entries(run.inputs).map(([k, v]) =>
      h("li", {}, h("code", {}, k), ": ", (Array.isArray(v) ? v : [v]).map((x, i) => [i ? ", " : "",
        typeof x === "string" && x.startsWith("inputs/") ? h("a", {href: fileUrl(runId, x, true)}, x.split("/").pop()) : (String(x ?? "") || "–")]))))),
    h("details", {class: "logbox"}, h("summary", {}, S("all_files")), h("ul", {class: "plain"}, (run.artifacts || []).map((a) =>
      h("li", {}, h("a", {href: fileUrl(runId, a.path, true)}, a.path), h("span", {class: "small muted"}, ` ${Math.ceil(a.size / 1024)} KB`))))),
    eventHistory(runId, run.events));
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
  else if (n.error) {  // the last meaningful line (server: error_summary); the full tool text stays under details
    const brief = n.error_summary || n.error;
    parts.push(h("div", {class: "notice bad"}, h("b", {}, S("error")), " ", brief,
      brief !== n.error ? h("details", {}, h("summary", {}, S("error_details")), h("pre", {class: "small"}, n.error)) : null));
  }
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
