/* Tally app shell: pages, uploads, progress, history, settings and chat. */
(function () {
  const T = window.Tally;
  const $ = (s, r = document) => r.querySelector(s);
  const e = T.fmt.esc;
  const app = $("#app");
  const state = { status: null, upload: null, sheet: null, context: "", report: null };

  // ------------------------------------------------------------ api
  async function api(path, opts = {}) {
    const res = await fetch(path, Object.assign({ headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {} }, opts));
    if (!res.ok) {
      let msg = `Something went wrong (${res.status}).`;
      try { msg = (await res.json()).detail || msg; } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  }
  const post = (path, body) => api(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body || {}) });

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2600);
  }

  // ------------------------------------------------------------ chrome
  $("#brand").innerHTML = T.mascot(28, "idle") + "<span>Tally</span>";
  $("#settings-btn").innerHTML = T.icons.gear;
  $("#settings-btn").onclick = () => openSettings();
  $("#ai-pill").onclick = () => openSettings();

  function currentTheme() {
    const t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function setTheme(t) {
    if (t === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("tally-theme", t); } catch (_) {}
    paintThemeBtn();
    T.charts.rerenderAll();
  }
  function paintThemeBtn() { $("#theme-btn").innerHTML = currentTheme() === "dark" ? T.icons.sun : T.icons.moon; }
  $("#theme-btn").onclick = () => setTheme(currentTheme() === "dark" ? "light" : "dark");
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { paintThemeBtn(); T.charts.rerenderAll(); });
  paintThemeBtn();

  async function refreshStatus() {
    try {
      state.status = await api("/api/status");
    } catch (_) {
      state.status = null;
    }
    if (state.status) applyMascotPrefs(state.status.settings);
    const pill = $("#ai-pill");
    const o = state.status && state.status.ollama;
    const useAi = state.status && state.status.settings.use_ai;
    let cls = "warn", txt = "AI not connected";
    if (o && o.ready && useAi) { cls = "ok"; txt = "AI ready · " + o.model; }
    else if (o && o.ready && !useAi) { cls = ""; txt = "AI switched off"; }
    else if (o && o.reachable) { txt = "AI needs a model"; }
    pill.innerHTML = `<span class="dot ${cls}"></span><span class="txt">${e(txt)}</span>`;
    return state.status;
  }
  function applyMascotPrefs(set) {
    const prefs = { look: set.mascot_look || "classic", holidays: set.holiday_costumes !== false };
    const changed = JSON.stringify(prefs) !== JSON.stringify(T.mascotPrefs) || !applyMascotPrefs.done;
    T.mascotPrefs = prefs;
    applyMascotPrefs.done = true;
    if (changed) {
      $("#brand").innerHTML = T.mascot(28, "idle") + "<span>Tally</span>";
      T.refreshFavicon();
      const hero = document.querySelector(".hero .mascot");
      if (hero) hero.outerHTML = T.mascot(84, "idle");
    }
  }

  setInterval(refreshStatus, 20000);
  setInterval(() => fetch("/api/heartbeat", { method: "POST" }).catch(() => {}), 30000);
  fetch("/api/heartbeat", { method: "POST" }).catch(() => {});

  // ------------------------------------------------------------ router
  async function route() {
    const h = location.hash.replace(/^#\/?/, "");
    const [page, arg] = h.split("/");
    document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === (page || "home")));
    T.charts.disposeIn(app);
    window.scrollTo(0, 0);
    if (page === "working") return working(arg);
    if (page === "report") return reportPage(arg);
    if (page === "history") return historyPage();
    return home();
  }
  window.addEventListener("hashchange", route);

  // ------------------------------------------------------------ home
  async function home() {
    const u = state.upload;
    app.innerHTML = `
      <div class="page">
        <section class="hero">
          ${T.mascot(84, "idle")}
          <h1>Drop in a spreadsheet.<br>I'll find the story.</h1>
          <p>Tally reads every row, tests every pattern with real statistics, and explains what matters in plain English. Your data never leaves this computer.</p>
        </section>
        <div id="pick"></div>
        <div class="trust">
          <span>${T.icons.lock} Stays on your computer</span>
          <span>${T.icons.shield} Every finding is tested</span>
          <span>${T.icons.spark} Plain-English answers</span>
        </div>
        <div id="recent"></div>
      </div>`;
    paintPicker();
    try {
      const list = (await api("/api/reports")).slice(0, 3);
      if (list.length) {
        $("#recent").innerHTML = `<section class="recent"><h3>Recent</h3><div class="recent-list">${list
          .map((r) => `<a class="card recent-item" href="#/report/${e(r.id)}"><span class="t">${e(r.title)}</span><span class="d">${e(T.fmt.ago(r.created_at))}</span></a>`)
          .join("")}</div></section>`;
      }
    } catch (_) {}
    void u;
  }

  function paintPicker() {
    const box = $("#pick");
    if (!box) return;
    const u = state.upload;
    if (!u) {
      box.innerHTML = `
        <label class="drop" id="drop">
          <span class="drop-icon">${T.icons.upload}</span>
          <strong>Drop your file here, or click to choose</strong>
          <span class="formats">Excel (.xlsx, .xls), CSV, TSV or JSON</span>
          <input type="file" id="file" accept=".csv,.tsv,.txt,.xlsx,.xlsm,.xls,.json">
        </label>
        <div class="home-foot">No file handy? <button class="link-btn" id="sample">Try it with sample coffee shop data</button></div>`;
      const drop = $("#drop");
      ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (x) => { x.preventDefault(); drop.classList.add("over"); }));
      ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
      drop.addEventListener("drop", (x) => { x.preventDefault(); if (x.dataTransfer.files[0]) upload(x.dataTransfer.files[0]); });
      $("#file").onchange = (x) => x.target.files[0] && upload(x.target.files[0]);
      $("#sample").onclick = async () => {
        try { setUpload(await post("/api/sample")); } catch (err) { toast(err.message); }
      };
      return;
    }
    const multi = u.sheets.length > 1;
    box.innerHTML = `
      <div class="card file-chip">
        <span class="fi">${T.icons.sheet}</span>
        <div style="min-width:0;flex:1"><div class="name">${e(u.file_name)}</div><div class="meta">${multi ? `${u.sheets.length} sheets` : "Ready to analyse"}</div></div>
        <button class="btn ghost small" id="change">Change file</button>
      </div>
      <div class="setup">
        ${multi ? `<div class="field"><label>Which sheet should I look at?</label><div class="sheet-pick">${u.sheets
          .map((s) => `<button class="chip ${s.name === state.sheet ? "on" : ""}" data-sheet="${e(s.name)}">${e(s.name)}<small>${s.rows ?? ""} rows</small></button>`)
          .join("")}</div></div>` : ""}
        <div class="field">
          <label for="ctx">Anything I should know? <span class="muted" style="font-weight:400">(optional)</span></label>
          <textarea class="input" id="ctx" placeholder="e.g. This is our café's sales for the last two years. I mostly care about revenue and which store is doing best.">${e(state.context)}</textarea>
        </div>
        <div><button class="btn primary big" id="go">${T.icons.spark} Find the story</button></div>
      </div>`;
    $("#change").onclick = () => { state.upload = null; paintPicker(); };
    box.querySelectorAll("[data-sheet]").forEach((b) => (b.onclick = () => { state.sheet = b.dataset.sheet; state.context = $("#ctx").value; paintPicker(); }));
    $("#go").onclick = start;
    $("#ctx").addEventListener("keydown", (x) => { if (x.key === "Enter" && (x.metaKey || x.ctrlKey)) start(); });
  }

  function setUpload(u) {
    state.upload = u;
    state.sheet = u.suggested;
    paintPicker();
  }

  async function upload(file) {
    const box = $("#pick");
    box.innerHTML = `<div class="card file-chip"><span class="fi">${T.icons.file}</span><div style="flex:1"><div class="name">${e(file.name)}</div><div class="meta">Opening…</div></div></div>`;
    const fd = new FormData();
    fd.append("file", file);
    try {
      setUpload(await post("/api/upload", fd));
    } catch (err) {
      state.upload = null;
      paintPicker();
      toast(err.message);
    }
  }

  async function start() {
    const u = state.upload;
    state.context = ($("#ctx") && $("#ctx").value) || "";
    try {
      const { job_id } = await post("/api/analyze", { upload_id: u.upload_id, file_name: u.file_name, sheet: state.sheet, context: state.context });
      state.workingName = u.file_name;
      location.hash = "#/working/" + job_id;
    } catch (err) {
      toast(err.message);
    }
  }

  // ------------------------------------------------------------ working
  const TIPS = [
    "Every finding is checked with a statistical test before it's shown.",
    "I correct for running lots of tests, so lucky flukes don't sneak in.",
    "Totals and subtotal rows are removed so nothing gets counted twice.",
    "If nothing real turns up, I'll say so instead of making something up.",
    "The AI only rewords findings. It can't change the numbers.",
  ];

  async function working(jid) {
    app.innerHTML = `
      <div class="page working">
        <div id="wm">${T.mascot(92, "think")}</div>
        <h2 id="wt">Reading ${e(state.workingName || "your data")}</h2>
        <p class="detail" id="wd">Getting started</p>
        <div class="pct" id="wp" aria-live="polite">0%</div>
        <div class="bar"><i id="wb"></i></div>
        <ul class="steps" id="ws"></ul>
        <p class="tip" id="tip">${TIPS[0]}</p>
      </div>`;
    const here = () => location.hash.startsWith("#/working/" + jid);
    let tipI = 0;
    const tipTimer = setInterval(() => {
      const t = $("#tip");
      if (!t || !here()) return clearInterval(tipTimer);
      t.classList.add("fade");
      setTimeout(() => { t.textContent = TIPS[++tipI % TIPS.length]; t.classList.remove("fade"); }, 250);
    }, 5000);

    // The server reports where it is (target) and where the current sub-step ends (next).
    // The counter glides toward the target and keeps creeping toward "next" while it waits,
    // so it never freezes and never jumps backwards.
    const p = { target: 0, next: 10, pace: 2, since: performance.now(), shown: 0, done: false, last: performance.now() };
    let finished = false;
    const frame = (now) => {
      if (!here()) return;
      const dt = now - p.last;
      p.last = now;
      let goal;
      if (p.done) goal = 100;
      else {
        const waited = (now - p.since) / 1000;
        // creeps toward the end of the current step, slowing down but never fully stopping
        goal = p.target + (p.next - p.target) * 0.95 * (waited / (waited + p.pace));
      }
      p.shown = Math.max(p.shown, p.shown + (goal - p.shown) * (1 - Math.exp(-dt / (p.done ? 120 : 260))));
      const shown = Math.min(100, p.done && p.shown > 99.4 ? 100 : p.shown);
      $("#wp").textContent = Math.floor(shown) + "%";
      $("#wb").style.width = shown + "%";
      if (p.done && shown >= 100 && !finished) { finished = true; celebrate(); return; }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);

    let built = false;
    let reportId = null;
    const paintSteps = (steps) => {
      const ul = $("#ws");
      if (!built) {
        ul.innerHTML = steps.map((s) => `<li data-k="${e(s.key)}"><span class="st"></span>${e(s.label)}</li>`).join("");
        built = true;
      }
      steps.forEach((s) => {
        const li = ul.querySelector(`[data-k="${s.key}"]`);
        if (!li || li.classList.contains(s.state)) return;
        li.className = s.state;
        li.querySelector(".st").innerHTML = s.state === "done" ? T.icons.check : "";
      });
    };
    const setDetail = (text) => {
      const d = $("#wd");
      if (!text || d.dataset.text === text) return;
      d.dataset.text = text;
      d.classList.add("fade");
      setTimeout(() => { d.textContent = text; d.classList.remove("fade"); }, 160);
    };
    const celebrate = () => {
      clearInterval(tipTimer);
      $("#wm").innerHTML = T.mascot(92, "happy");
      $("#wt").textContent = "Found it!";
      setDetail("Opening your story…");
      setTimeout(() => { if (here()) location.hash = "#/report/" + reportId; }, 900);
    };

    const tick = async () => {
      if (!here()) { clearInterval(tipTimer); return; }
      let j;
      try { j = await api("/api/jobs/" + jid); } catch (err) {
        clearInterval(tipTimer);
        return fail("I lost track of that analysis (the app may have restarted). Please try again.");
      }
      paintSteps(j.steps);
      if (j.progress !== p.target || j.progress_next !== p.next) {
        p.target = j.progress;
        p.next = Math.max(j.progress_next ?? j.progress, j.progress);
        p.pace = j.pace || 2;
        p.since = performance.now();
      }
      if (j.status === "done") {
        reportId = j.report_id;
        p.done = true;
        return;
      }
      setDetail(j.detail);
      if (j.status === "error") { clearInterval(tipTimer); return fail(j.error); }
      setTimeout(tick, 400);
    };
    const fail = (msg) => {
      p.done = false;
      $("#wm").innerHTML = T.mascot(92, "oops");
      $("#wt").textContent = "Hmm, I got stuck";
      $("#wd").textContent = "";
      ["#wp", ".bar", "#ws"].forEach((sel) => { const el = $(sel); if (el) el.remove(); });
      $("#tip").outerHTML = `<div class="error-box"><p>${e(msg)}</p><p style="margin-top:12px"><a class="btn" href="#/">Try another file</a></p></div>`;
    };
    tick();
  }

  // ------------------------------------------------------------ report
  async function reportPage(rid) {
    app.innerHTML = `<div class="page working">${T.mascot(64, "think")}</div>`;
    let r;
    try { r = await api("/api/reports/" + rid); } catch (err) {
      app.innerHTML = `<div class="page working">${T.mascot(72, "oops")}<h2>I couldn't find that report</h2><p class="detail">${e(err.message)}</p><p style="margin-top:18px"><a class="btn" href="#/history">Back to history</a></p></div>`;
      return;
    }
    state.report = r;
    const sheets = r.has_source !== false && r.other_sheets && r.other_sheets.length
      ? `<div class="card sheets-note" data-noexport><span>This workbook has other sheets:</span>${r.other_sheets.map((s) => `<button class="chip" data-other="${e(s)}">${e(s)}</button>`).join("")}</div>` : "";
    T.report.render(app, r, { extraAfterNext: sheets });
    wireReport(app, r);
    mountChat(app.querySelector("[data-chat-slot]"), r);
  }

  function wireReport(root, r) {
    const menu = root.querySelector("[data-menu]");
    const close = (ev) => { if (!ev.target.closest(".menu")) { menu.classList.add("hidden"); document.removeEventListener("click", close); } };
    root.querySelector('[data-act="export-menu"]').onclick = () => {
      menu.classList.toggle("hidden");
      if (!menu.classList.contains("hidden")) setTimeout(() => document.addEventListener("click", close));
    };
    const run = async (label, fn) => {
      menu.classList.add("hidden");
      toast(label);
      try { await fn(); } catch (err) { console.error(err); toast("Sorry, saving failed: " + err.message); }
    };
    root.querySelector('[data-act="export-pdf"]').onclick = () => run("Making your PDF…", () => T.exporter.pdf(root, r));
    root.querySelector('[data-act="export-png"]').onclick = () => run("Making your image…", () => T.exporter.png(root, r));
    root.querySelector('[data-act="export-html"]').onclick = () => run("Packing your interactive file…", () => T.exporter.html(r));
    root.querySelector('[data-act="ask"]').onclick = () => {
      const c = root.querySelector(".chat");
      c.scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(() => { const i = c.querySelector("input"); if (i) i.focus(); }, 500);
    };
    root.querySelector('[data-act="rename"]').onclick = () => {
      const h = root.querySelector("[data-title]");
      h.contentEditable = "true";
      h.focus();
      document.getSelection().selectAllChildren(h);
      const save = async () => {
        h.contentEditable = "false";
        const title = h.textContent.trim();
        if (title && title !== r.story.title) {
          await api("/api/reports/" + r.id, { method: "PATCH", body: JSON.stringify({ title }), headers: { "Content-Type": "application/json" } });
          r.story.title = title;
          toast("Renamed");
        } else h.textContent = r.story.title;
      };
      h.onblur = save;
      h.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); h.blur(); } if (ev.key === "Escape") { h.textContent = r.story.title; h.blur(); } };
    };
    root.querySelectorAll("[data-other]").forEach((b) => (b.onclick = async () => {
      try {
        const { job_id } = await post(`/api/reports/${r.id}/reanalyze`, { sheet: b.dataset.other });
        state.workingName = `${r.file_name} · ${b.dataset.other}`;
        location.hash = "#/working/" + job_id;
      } catch (err) { toast(err.message); }
    }));
  }

  // ------------------------------------------------------------ chat
  function suggestions(r) {
    const cols = r.dataset.column_list;
    const main = r.dataset.main_metric;
    const cat = cols.find((c) => c.role === "category");
    const time = cols.find((c) => c.role === "time");
    const out = [];
    if (main && cat) out.push(`Which ${cat.name} has the highest ${main}?`);
    if (main && time) out.push(`How did ${main} change over time?`);
    if (main) out.push(`What's the average ${main}?`);
    out.push("What should I look at first?");
    return out.slice(0, 4);
  }

  function mountChat(slot, r) {
    if (!slot) return;
    slot.outerHTML = `<section class="card chat" id="chat" data-noexport>
        <div class="chat-head">${T.mascot(36, "idle")}<div><h2>Ask Tally about this data</h2><p>I'll calculate the answer from your actual rows.</p></div></div>
        <div class="msgs" id="msgs"></div>
        <div class="suggest" id="suggest">${suggestions(r).map((s) => `<button class="chip">${e(s)}</button>`).join("")}</div>
        <form class="chat-form" id="chat-form" autocomplete="off">
          <input class="input" id="chat-in" placeholder="Ask anything, like “Which month was best?”" maxlength="500">
          <button class="btn primary" type="submit" title="Send">${T.icons.send}</button>
        </form>
        <div id="chat-off"></div>
      </section>`;
    const msgs = $("#msgs");
    const history = [];
    const add = (role, text, extra = {}) => {
      const d = document.createElement("div");
      d.className = "msg " + (role === "user" ? "user" : "bot");
      d.innerHTML = `<div>${e(text)}</div>`;
      if (extra.chart) {
        const c = document.createElement("div");
        c.className = "chart";
        d.appendChild(c);
        msgs.appendChild(d);
        T.charts.render(c, extra.chart);
      }
      if (extra.steps && extra.steps.length) {
        const s = document.createElement("div");
        s.className = "steps-used";
        s.textContent = "Calculated: " + extra.steps.join("; ");
        d.appendChild(s);
      }
      msgs.appendChild(d);
      return d;
    };
    (r.chat || []).forEach((m) => { add(m.role, m.content, m); history.push({ role: m.role, content: m.content }); });

    const ready = state.status && state.status.ollama.ready;
    if (r.has_source === false) {
      $("#chat-form").classList.add("hidden");
      $("#suggest").classList.add("hidden");
      $("#chat-off").innerHTML = `<div class="chat-off">This is an older report, so Tally only kept the summary to save space. Add the file again (New, top left) to ask questions about it.</div>`;
    } else if (!ready) {
      $("#chat-off").innerHTML = `<div class="chat-off">Chat needs the local AI. <button class="link-btn" id="chat-setup">Connect it in Settings</button> (takes about 5 minutes the first time).</div>`;
      $("#chat-setup").onclick = () => openSettings();
    }

    const ask = async (q) => {
      q = q.trim();
      if (!q) return;
      $("#suggest").classList.add("hidden");
      add("user", q);
      const typing = document.createElement("div");
      typing.className = "msg bot typing";
      typing.innerHTML = `<span class="typing-dots"><i></i><i></i><i></i></span> Crunching the numbers`;
      msgs.appendChild(typing);
      typing.scrollIntoView({ behavior: "smooth", block: "nearest" });
      try {
        const res = await post(`/api/reports/${r.id}/chat`, { question: q, history });
        typing.remove();
        add("assistant", res.reply, res).scrollIntoView({ behavior: "smooth", block: "nearest" });
        history.push({ role: "user", content: q }, { role: "assistant", content: res.reply });
      } catch (err) {
        typing.remove();
        add("assistant", err.message);
      }
    };
    $("#chat-form").onsubmit = (ev) => { ev.preventDefault(); const i = $("#chat-in"); ask(i.value); i.value = ""; };
    $("#suggest").querySelectorAll(".chip").forEach((b) => (b.onclick = () => ask(b.textContent)));
  }

  // ------------------------------------------------------------ history
  async function historyPage() {
    app.innerHTML = `<div class="page wide"><div class="h-head"><div><h1>History</h1><p class="muted" style="margin-top:6px">Every report is saved on this computer. Open one to explore it again.</p></div><a class="btn primary" href="#/">${T.icons.upload} New analysis</a></div><div id="hlist"></div></div>`;
    let list = [];
    try { list = await api("/api/reports"); } catch (err) { toast(err.message); }
    const box = $("#hlist");
    if (!list.length) {
      box.innerHTML = `<div class="card empty-state">${T.mascot(64, "idle")}<h2 style="margin-top:8px">Nothing here yet</h2><p>Your reports will show up here after your first analysis.</p><p style="margin-top:16px"><a class="btn" href="#/">Analyse a file</a></p></div>`;
      return;
    }
    const total = list.reduce((a, r) => a + r.size, 0);
    $(".h-head p").textContent = `${list.length} report${list.length === 1 ? "" : "s"} saved on this computer, using ${bytes(total)}. ` +
      "Every report is kept. Only the 10 newest also keep a copy of your file, so you can still ask questions about them.";
    box.innerHTML = `<div class="h-grid">${list.map((r) => `
      <a class="card h-card" href="#/report/${e(r.id)}">
        <div class="t">${e(r.title)}</div>
        <div class="f">${e(r.file_name)}${r.sheet ? " · " + e(r.sheet) : ""}</div>
        <div class="m"><span>${r.n_insights} findings</span><span>${bytes(r.size)}</span><span>${e(T.fmt.ago(r.created_at))}</span></div>
        <button class="icon-btn del" title="Delete" data-del="${e(r.id)}">${T.icons.trash}</button>
      </a>`).join("")}</div>`;
    box.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      if (!confirm("Delete this report? This can't be undone.")) return;
      await api("/api/reports/" + b.dataset.del, { method: "DELETE" });
      toast("Deleted");
      historyPage();
    }));
  }

  function bytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return Math.max(1, Math.round(n / 1024)) + " KB";
    return (n / 1024 / 1024).toFixed(1) + " MB";
  }

  // ------------------------------------------------------------ settings
  async function openSettings() {
    const root = $("#drawer-root");
    root.innerHTML = `<div class="scrim"></div><aside class="drawer" role="dialog" aria-label="Settings"><div class="row"><h2>Settings</h2><button class="icon-btn" id="dclose" title="Close">${T.icons.close}</button></div><div id="dbody"><p class="muted" style="margin-top:20px">Checking your AI…</p></div></aside>`;
    const closeIt = () => (root.innerHTML = "");
    $(".scrim", root).onclick = closeIt;
    $("#dclose").onclick = closeIt;
    document.addEventListener("keydown", function esc(ev) { if (ev.key === "Escape") { closeIt(); document.removeEventListener("keydown", esc); } });
    await refreshStatus();
    paintSettings();
  }

  function paintSettings() {
    const body = $("#dbody");
    if (!body) return;
    const s = state.status;
    if (!s) { body.innerHTML = `<p class="muted">Couldn't reach the Tally server.</p>`; return; }
    const o = s.ollama;
    const set = s.settings;
    let statusHtml;
    if (o.ready) statusHtml = `<div class="card status-card"><span class="dot ok" style="margin-top:7px"></span><div><b>Connected</b><p>Using <code>${e(o.model)}</code>. Explanations and chat are on.</p></div></div>`;
    else if (o.reachable) statusHtml = `<div class="card status-card"><span class="dot warn" style="margin-top:7px"></span><div><b>Ollama is running, but has no model yet</b><p>Download one below. The first one is the best pick for most computers.</p></div></div>`;
    else statusHtml = `<div class="card status-card"><span class="dot warn" style="margin-top:7px"></span><div><b>Ollama isn't running</b><p>Tally still works without it: you'll get every chart and finding, just with simpler wording and no chat.</p></div></div>`;

    const howto = o.reachable ? "" : `
      <section><div class="section-label">Set up the AI (one time, about 5 minutes)</div>
        <ol class="steps-howto">
          <li>Go to <b>ollama.com</b> and click <b>Download</b>. Install it like any other app.</li>
          <li>Open the Ollama app once. On a Mac you'll see a little llama in the menu bar; on Windows it's in the system tray.</li>
          <li>Come back here and press <b>Check again</b>. Then download a model below.</li>
        </ol>
        <p class="muted" style="font-size:13.5px">More detail is in the <b>HOW TO INSTALL.txt</b> file in the Tally folder.</p>
        <div><button class="btn" id="recheck">${T.icons.refresh} Check again</button></div>
      </section>`;

    const installed = new Set(o.models.map((m) => (m.includes(":") ? m : m + ":latest")));
    const models = o.reachable ? `
      <section><div class="section-label">AI models</div>
        ${o.models.length ? `<div class="field"><label for="msel">Model to use</label><select class="input" id="msel">${o.models.map((m) => `<option ${m === o.model ? "selected" : ""}>${e(m)}</option>`).join("")}</select></div>` : ""}
        <div class="model-list">${s.recommended.map((m, i) => `
          <div class="card model"><div class="top"><b>${e(m.name)}</b>${i === 0 ? '<span class="badge">Recommended</span>' : ""}<span class="spacer"></span>${installed.has(m.name) ? '<span class="muted" style="font-size:13px">Installed</span>' : `<button class="btn small" data-pull="${e(m.name)}">${T.icons.download} Download</button>`}</div>
          <div class="why">${e(m.why)}</div><div class="meta">Download ${e(m.size)} · works best with ${e(m.ram)} of memory</div><div class="prog hidden"><i></i></div></div>`).join("")}</div>
      </section>` : "";

    body.innerHTML = `
      <section>${statusHtml}</section>
      ${howto}
      ${models}
      <section><div class="section-label">Writing</div>
        <div class="row"><div><b style="font-weight:560">Use AI to write explanations</b><p class="muted" style="font-size:13.5px">Numbers always come from the statistics engine either way.</p></div>
        <label class="switch"><input type="checkbox" id="useai" ${set.use_ai ? "checked" : ""}><span></span></label></div>
      </section>
      <section><div class="section-label">Tally's look</div>
        <div class="look-pick" id="looks">${Object.entries(T.mascotLooks).map(([k, name]) =>
          `<button data-look="${k}" class="${(set.mascot_look || "classic") === k ? "on" : ""}">${T.mascot(44, "idle", { look: k })}${e(name)}</button>`).join("")}</div>
        <div class="row"><div><b style="font-weight:560">Dress up for holidays</b><p class="muted" style="font-size:13.5px">Pumpkins in October, a Santa hat in December, and more.</p></div>
        <label class="switch"><input type="checkbox" id="holi" ${set.holiday_costumes !== false ? "checked" : ""}><span></span></label></div>
        ${costumeLine(set)}
      </section>
      <section><div class="section-label">Appearance</div>
        <div class="seg" id="seg">${["system", "light", "dark"].map((t) => `<button data-t="${t}" class="${(localStorage.getItem("tally-theme") || "system") === t ? "on" : ""}">${t[0].toUpperCase() + t.slice(1)}</button>`).join("")}</div>
      </section>
      <section><div class="section-label">Advanced</div>
        <div class="field"><label for="ourl">Ollama address</label><input class="input" id="ourl" value="${e(set.ollama_url)}"></div>
        <div><button class="btn small" id="saveurl">Save address</button></div>
        <p class="muted" style="font-size:12.5px">Tally ${e(s.version)}</p>
      </section>`;

    const save = async (patch) => { await post("/api/settings", patch); await refreshStatus(); paintSettings(); };
    const rc = $("#recheck"); if (rc) rc.onclick = async () => { rc.disabled = true; await refreshStatus(); paintSettings(); };
    const ms = $("#msel"); if (ms) ms.onchange = () => save({ model: ms.value });
    $("#useai").onchange = (ev) => save({ use_ai: ev.target.checked });
    $("#saveurl").onclick = () => save({ ollama_url: $("#ourl").value.trim() });
    document.querySelectorAll("#seg button").forEach((b) => (b.onclick = () => { setTheme(b.dataset.t); paintSettings(); }));
    document.querySelectorAll("#looks button").forEach((b) => (b.onclick = () => save({ mascot_look: b.dataset.look })));
    $("#holi").onchange = (ev) => save({ holiday_costumes: ev.target.checked });
    document.querySelectorAll("[data-pull]").forEach((b) => (b.onclick = () => pullModel(b)));
  }

  function costumeLine(set) {
    if (set.holiday_costumes === false) return "";
    const now = T.costumeFor();
    if (now) {
      return `<div class="costume-row">${T.mascot(40, "idle", { costume: now })}<p>Tally is dressed up for <b>${e(T.mascotCostumes[now])}</b> right now.</p></div>`;
    }
    const next = T.nextCostume();
    if (!next) return "";
    const when = next.from.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    return `<div class="costume-row">${T.mascot(40, "idle", { costume: next.id })}<p>Next costume: <b>${e(next.name)}</b>, from ${e(when)}.</p></div>`;
  }

  async function pullModel(btn) {
    const card = btn.closest(".model");
    const bar = card.querySelector(".prog");
    bar.classList.remove("hidden");
    btn.disabled = true;
    btn.textContent = "Starting…";
    try {
      const { job_id } = await post("/api/ollama/pull", { model: btn.dataset.pull });
      const poll = async () => {
        const j = await api("/api/jobs/" + job_id);
        bar.querySelector("i").style.width = j.progress + "%";
        btn.textContent = j.progress ? j.progress + "%" : "Starting…";
        if (j.status === "done") { toast("Model ready!"); await refreshStatus(); paintSettings(); return; }
        if (j.status === "error") { toast("Download failed: " + j.error); btn.disabled = false; btn.textContent = "Try again"; return; }
        setTimeout(poll, 800);
      };
      poll();
    } catch (err) {
      toast(err.message);
      btn.disabled = false;
    }
  }

  refreshStatus().then(route);
})();
