/* Renders a report (the story). Used by the app AND by exported interactive files,
   so it must not depend on the server. */
(function () {
  const T = (window.Tally = window.Tally || {});
  const e = (s) => T.fmt.esc(s);
  const I = () => T.icons;

  function header(r, opts) {
    const d = new Date(r.created_at);
    const bits = [
      `<span>${e(r.file_name)}${r.sheet ? " · " + e(r.sheet) : ""}</span>`,
      `<span>${d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span>`,
    ];
    const play = r.insights.length ? `<button class="btn play" data-act="story">${I().play} Play the story</button>` : "";
    const actions = opts.standalone ? `<div class="r-actions" data-noexport>${play}</div>` : `
      <div class="r-actions" data-noexport>
        ${play}
        <div class="menu">
          <button class="btn" data-act="export-menu">${I().download} Save or share</button>
          <div class="menu-list hidden" data-menu>
            <button data-act="export-pdf">${I().pdf}<div><b>PDF document</b><span>Best for printing, email and slides</span></div></button>
            <button data-act="export-png">${I().image}<div><b>Image (PNG)</b><span>The whole report as one picture</span></div></button>
            <button data-act="export-html">${I().globe}<div><b>Interactive file</b><span>Opens in any browser, charts stay hoverable</span></div></button>
          </div>
        </div>
        <button class="btn" data-act="ask">${I().chat} Ask a question</button>
        <button class="btn ghost" data-act="rename">${I().pencil} Rename</button>
      </div>`;
    return `
      <header class="r-head" data-block>
        <div class="eyebrow">${bits.join("")}</div>
        <h1 data-title>${e(r.story.title)}</h1>
        <p class="intro">${e(r.story.intro)}</p>
        ${actions}
      </header>`;
  }

  function kpis(r) {
    return `<div class="kpis" data-block>${r.kpis
      .map((k) => `<div class="card kpi"><div class="l">${e(k.label)}</div><div class="v">${e(k.value)}</div><div class="s">${e(k.sub || "")}</div></div>`)
      .join("")}</div>`;
  }

  function takeaways(r) {
    if (!r.story.takeaways || !r.story.takeaways.length) return "";
    return `<section class="card takeaways" data-block>
      <div class="section-label">The short version</div>
      <ol>${r.story.takeaways.map((t) => `<li><span>${e(t)}</span></li>`).join("")}</ol>
    </section>`;
  }

  /* "How to read this chart": each color on the chart, in plain words. */
  function chartKey(chart) {
    const key = (chart && chart.key) || [];
    if (!key.length) return "";
    return `<ul class="chart-key" aria-label="How to read this chart">${key
      .map((k) => `<li><span class="sw sw-${e(k.swatch)}" aria-hidden="true"></span>${e(k.text)}</li>`).join("")}</ul>`;
  }

  function insightCard(ins, i) {
    const tech = ins.stats.p !== null && ins.stats.p !== undefined
      ? `Test: ${e(ins.stats.test)} · ${e(ins.stats.effect)} · rows: ${ins.stats.n.toLocaleString()} · adjusted p: ${ins.stats.q < 0.0001 ? "< 0.0001" : (+ins.stats.q).toFixed(4)}`
      : `Method: ${e(ins.stats.test)} · ${e(ins.stats.effect)}`;
    return `
      <section class="chapter" id="ch-${ins.id}" data-block>
        <div class="chapter-head"><span class="num">${String(i + 1).padStart(2, "0")}</span><span class="sec">${e(ins.section_title)}</span></div>
        <article class="card insight">
          <h2>${e(ins.title)}</h2>
          <p class="headline">${e(ins.headline)}</p>
          ${chartKey(ins.chart)}
          <div class="chart-box">
            <div class="chart-tools" data-noexport>
              <button class="icon-btn" title="Save this chart as an image" data-act="chart-png">${I().image}</button>
            </div>
            <div class="chart" data-chart="${ins.id}"></div>
          </div>
          <div class="table-view hidden"></div>
          <p class="explain">${e(ins.explanation)}</p>
          ${ins.ideas && ins.ideas.length ? `<div class="ideas"><div class="lbl">${I().bulb} Ideas you could try</div><ul>${ins.ideas.map((x) => `<li>${e(x)}</li>`).join("")}</ul></div>` : ""}
          <div class="i-foot">
            <span class="conf">${I().shield} ${e(ins.confidence.label)}</span>
            <button class="link-btn" data-act="how" data-noexport>How do we know?</button>
            <button class="link-btn" data-act="table" data-noexport>See the numbers</button>
          </div>
          <div class="how hidden"><div>${e(ins.confidence.how)}</div><div class="tech">${tech}</div></div>
        </article>
      </section>`;
  }

  function nextSteps(r) {
    if (!r.story.next_steps || !r.story.next_steps.length) return "";
    return `<section class="card next" data-block>
      <h2>Where to go from here</h2>
      <ul>${r.story.next_steps.map((x) => `<li>${e(x)}</li>`).join("")}</ul>
    </section>`;
  }

  function about(r) {
    const roleWord = { measure: "number", category: "group", time: "date", id: "ID", text: "text", constant: "same everywhere", geo: "map" };
    const cols = r.dataset.column_list
      .map((c) => `<span class="col-tag" title="${e(c.summary || "")}">${e(c.name)}<i>${roleWord[c.role] || c.role}</i></span>`)
      .join("");
    const clean = r.cleaning.length ? `<div><b>What I tidied up</b><ul>${r.cleaning.map((x) => `<li>${e(x)}</li>`).join("")}</ul></div>` : `<div><b>What I tidied up</b><p>Nothing needed fixing. Nice clean data.</p></div>`;
    const missing = r.health.missing.length
      ? `<div><b>Gaps in the data</b><ul>${r.health.missing.map((m) => `<li>'${e(m.column)}' is empty in ${e(m.share)} of rows. Findings about it use only the rows that have a value.</li>`).join("")}</ul></div>` : "";
    const notes = r.health.notes.length ? `<div><b>Good to know</b><ul>${r.health.notes.map((x) => `<li>${e(x)}</li>`).join("")}</ul></div>` : "";
    const skipped = r.health.skipped.length ? `<p>Not analysed (IDs, free text, or the same value everywhere): ${r.health.skipped.map(e).join(", ")}.</p>` : "";
    const cc = r.method.clarity_check;
    const ai = r.model
      ? `Explanations were written by the local AI model <code>${e(r.model)}</code>, and checked so it can't change any numbers.` +
        (cc ? ` Afterwards, Tally re-read all ${cc.checked} chapters as a first-time reader would, asking "would anyone instantly understand this?", and rewrote ${cc.rewritten} of them to make them clearer.` : "")
      : "Explanations were written by Tally's built-in templates (the local AI wasn't connected).";
    return `<details class="card about" data-block>
      <summary>${I().chevron} About your data and how I checked it</summary>
      <div class="body">
        <div><b>Your columns</b><div class="cols">${cols}</div></div>
        ${clean}${missing}${notes}
        <div><b>How the checks work</b><p style="margin-top:6px">${e(r.method.summary)} I ran ${r.method.tests_run.toLocaleString()} checks, ${r.method.passed} passed, and the ${r.method.shown} clearest are shown above. ${ai}</p>${skipped}</div>
      </div>
    </details>`;
  }

  function toc(r) {
    const items = r.insights.map((ins, i) => `<a href="#ch-${ins.id}" data-toc="ch-${ins.id}"><span class="n">${String(i + 1).padStart(2, "0")}</span><span>${e(ins.title)}</span></a>`).join("");
    return `<nav class="toc" aria-label="Chapters">${items}</nav>`;
  }

  function render(container, r, opts = {}) {
    T.charts.disposeIn(container);
    const empty = !r.insights.length
      ? `<section class="card empty-state" data-block>${T.mascot(64, "idle")}<h2 style="margin-top:8px">No strong patterns this time</h2>
         <p>I tested everything and nothing passed the bar for "real and big enough to matter". That's genuinely useful: it means apparent differences in this data are most likely random noise. More rows or more columns usually help.</p></section>`
      : "";
    container.innerHTML = `
      <div class="report-wrap">
        ${toc(r)}
        <article class="report" id="report-root">
          ${header(r, opts)}
          ${kpis(r)}
          ${takeaways(r)}
          ${empty}
          ${r.insights.map(insightCard).join("")}
          ${nextSteps(r)}
          ${opts.extraAfterNext || ""}
          ${about(r)}
          ${opts.standalone ? `<p class="muted" style="margin-top:28px;font-size:13px;text-align:center">Made with Tally · ${e(new Date(r.created_at).toLocaleString())}</p>` : ""}
          <div data-chat-slot></div>
        </article>
      </div>`;

    const byId = Object.fromEntries(r.insights.map((x) => [x.id, x]));
    // draw charts as they scroll into view, so each one animates in
    const charts = [...container.querySelectorAll("[data-chart]")];
    const draw = (el) => { if (!el._drawn) { el._drawn = true; T.charts.render(el, byId[el.dataset.chart].chart); } };
    if ("IntersectionObserver" in window && !opts.drawAll) {
      const io = new IntersectionObserver((ents) => ents.forEach((en) => { if (en.isIntersecting) { draw(en.target); io.unobserve(en.target); } }), { rootMargin: "120px" });
      charts.forEach((c) => io.observe(c));
    } else charts.forEach(draw);
    container._drawAll = () => charts.forEach(draw);

    container.querySelectorAll(".insight").forEach((card) => {
      const chartEl = card.querySelector("[data-chart]");
      const ins = byId[chartEl.dataset.chart];
      card.querySelector('[data-act="how"]').onclick = (ev) => {
        const h = card.querySelector(".how");
        h.classList.toggle("hidden");
        ev.target.textContent = h.classList.contains("hidden") ? "How do we know?" : "Hide the details";
      };
      card.querySelector('[data-act="table"]').onclick = (ev) => {
        const tv = card.querySelector(".table-view");
        if (!tv.innerHTML) tv.innerHTML = T.charts.table(ins.chart);
        tv.classList.toggle("hidden");
        ev.target.textContent = tv.classList.contains("hidden") ? "See the numbers" : "Hide the numbers";
      };
      card.querySelector('[data-act="chart-png"]').onclick = () => {
        draw(chartEl);
        const url = T.charts.image(chartEl);
        if (url) T.download(url, slug(ins.title) + ".png");
      };
    });

    const playBtn = container.querySelector('[data-act="story"]');
    if (playBtn && T.story) playBtn.onclick = () => T.story.open(r);

    // highlight the chapter you're reading in the side list
    const links = [...container.querySelectorAll("[data-toc]")];
    if (links.length && "IntersectionObserver" in window) {
      const spy = new IntersectionObserver((ents) => {
        ents.forEach((en) => {
          if (en.isIntersecting) links.forEach((a) => a.classList.toggle("on", a.dataset.toc === en.target.id));
        });
      }, { rootMargin: "-40% 0px -55% 0px" });
      container.querySelectorAll(".chapter").forEach((c) => spy.observe(c));
      links.forEach((a) => (a.onclick = (ev) => { ev.preventDefault(); document.getElementById(a.dataset.toc).scrollIntoView({ behavior: "smooth", block: "start" }); }));
    }
  }

  function slug(s) {
    return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "tally";
  }

  T.download = function (url, name) {
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  T.slug = slug;
  T.report = { render };
})();
