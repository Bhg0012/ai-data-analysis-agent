/* "Play the story": the report as a fun, full-screen, Wrapped-style slideshow.
   One bite-sized idea per slide: a big number that counts up, then the chart that proves it.
   The reader taps Next when they're ready. Works in the app and in exported files. */
(function () {
  const T = (window.Tally = window.Tally || {});
  const e = (s) => T.fmt.esc(s);

  // Bold backgrounds that all keep white text readable.
  const COLORS = ["#2A78D6", "#16171A", "#D9541E", "#0F8A5F", "#5B47C9", "#C2416F"];

  // ------------------------------------------------------------ the big number for each finding
  function hero(ins) {
    const f = ins.facts || {};
    const low = (s) => String(s || "").toLowerCase();
    switch (ins.kind) {
      case "trend":
        if (f.percent_change) return { value: f.percent_change, arrow: f.direction === "up" ? "up" : "down",
          label: `${f.metric} went ${f.direction}`, sub: `from ${f.from_period} to ${f.to_period}` };
        break;
      case "group":
        return { value: f.best_value, label: `${low(f.metric)} for ${f.best}`, sub: `compared with ${f.worst_value} for ${f.worst}` };
      case "rhythm":
        return { value: f.best_value, label: `${low(f.metric)} on ${f.best}s`, sub: `compared with ${f.worst_value} on ${f.worst}s` };
      case "composition":
        return { value: f.top_share, label: `of all ${low(f.metric)} comes from ${f.top}`, sub: `${f.top_total} out of ${f.grand_total}` };
      case "correlation":
        return { value: f.y_when_x_high, label: `typical ${low(f.y)} when ${low(f.x)} is high`, sub: `compared with ${f.y_when_x_low} when it's low` };
      case "outliers":
        return { value: f.count, label: `${low(f.metric)} values way bigger than the rest`, sub: `the biggest is ${f.most_extreme}, when ${f.typical} is typical` };
      case "spike":
        return { value: f.value, label: `${low(f.metric)} in ${f.period}`, sub: `when about ${f.usual_value} was normal` };
      case "drivers":
        return { value: f.top_driver, text: true, label: `makes the biggest difference to ${low(f.metric)}`, sub: f.example || "" };
      case "association":
        return { value: f.share_in_group, label: `of ${f.group} are ${f.value}`, sub: `compared with ${f.share_overall} overall` };
      case "mix":
        return { value: f.share, label: `of everything is ${f.top}`, sub: "" };
    }
    return { value: ins.title, text: true, label: "", sub: "" };
  }

  /* "$34.9" -> {pre:"$", num:34.9, dec:1, post:""} so it can count up. */
  function parseNum(v) {
    const m = String(v).match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
    if (!m) return null;
    const raw = m[2].replace(/,/g, "");
    return { pre: m[1], num: parseFloat(raw), dec: (raw.split(".")[1] || "").length, post: m[3], comma: m[2].includes(",") };
  }

  function countUp(el, value, ms = 1300) {
    const p = parseNum(value);
    if (!p || matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = value; return; }
    const start = performance.now();
    const fmt = (n) => {
      const s = n.toFixed(p.dec);
      return p.pre + (p.comma ? Number(s).toLocaleString("en-US", { minimumFractionDigits: p.dec, maximumFractionDigits: p.dec }) : s) + p.post;
    };
    const step = (now) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = fmt(p.num * eased);
      if (t < 1 && document.body.contains(el)) requestAnimationFrame(step);
      else el.textContent = value;
    };
    requestAnimationFrame(step);
  }

  // ------------------------------------------------------------ slides
  function buildSlides(r) {
    const slides = [];
    const n = r.insights.length;
    const name = r.story.title;

    slides.push({
      color: COLORS[0],
      html: `<div class="st-center">
          <div class="s-in" style="--d:0">${T.mascot(132, "happy")}</div>
          <p class="st-kicker s-in" style="--d:1">Your data story</p>
          <h1 class="st-big-title s-in" style="--d:2">${e(name)}</h1>
          <div class="st-stats s-in" style="--d:3">
            <div><b data-count="${e(Number(r.dataset.rows).toLocaleString("en-US"))}">0</b><span>rows read</span></div>
            <div><b data-count="${e(Number(r.method.tests_run).toLocaleString("en-US"))}">0</b><span>checks run</span></div>
            <div><b data-count="${n}">0</b><span>things worth knowing</span></div>
          </div>
        </div>`,
      next: n ? "Let's go" : "Next",
    });

    r.insights.forEach((ins, i) => {
      const h = hero(ins);
      const color = COLORS[(i + 1) % COLORS.length];
      const num = h.arrow ? `<span class="st-arrow ${h.arrow}">${h.arrow === "up" ? "&#8599;" : "&#8600;"}</span>` : "";
      slides.push({
        color,
        html: `<div class="st-center">
            <p class="st-kicker s-in" style="--d:0">#${i + 1} &middot; ${e(ins.section_title)}</p>
            <div class="st-hero s-in ${h.text ? "is-text" : ""}" style="--d:1">${num}<span ${h.text ? "" : `data-count="${e(h.value)}"`}>${h.text ? e(h.value) : "0"}</span></div>
            ${h.label ? `<p class="st-label s-in" style="--d:2">${e(h.label)}</p>` : ""}
            ${h.sub ? `<p class="st-sub s-in" style="--d:3">${e(h.sub)}</p>` : ""}
          </div>`,
        next: "Show me",
      });
      const key = (ins.chart.key || []).map((k) => `<li><span class="sw sw-${e(k.swatch)}"></span>${e(k.text)}</li>`).join("");
      slides.push({
        color,
        html: `<div class="st-chart-slide">
            <h2 class="st-title s-in" style="--d:0">${e(ins.title)}</h2>
            <p class="st-headline s-in" style="--d:1">${e(ins.headline)}</p>
            <div class="st-card s-in" style="--d:2">
              ${key ? `<ul class="chart-key">${key}</ul>` : ""}
              <div class="chart st-chart"></div>
            </div>
          </div>`,
        chart: ins.chart,
        next: i === n - 1 ? "Almost done" : "Next",
      });
    });

    const ideas = r.insights.map((x) => x.ideas && x.ideas[0]).filter(Boolean).slice(0, 4);
    if (ideas.length) {
      slides.push({
        color: COLORS[4],
        html: `<div class="st-center st-left">
            <p class="st-kicker s-in" style="--d:0">So what now?</p>
            <h2 class="st-title s-in" style="--d:1">A few ideas you could try</h2>
            <ol class="st-ideas">${ideas.map((t, i) => `<li class="s-in" style="--d:${i + 2}">${e(t)}</li>`).join("")}</ol>
          </div>`,
        next: "Next",
      });
    }

    const top = (r.story.takeaways || []).slice(0, 3);
    slides.push({
      color: COLORS[0],
      confetti: true,
      html: `<div class="st-center">
          <div class="s-in" style="--d:0">${T.mascot(120, "happy")}</div>
          <h2 class="st-title s-in" style="--d:1">That's your story!</h2>
          ${top.length ? `<p class="st-kicker s-in" style="--d:2">Your top ${top.length}</p>
            <ol class="st-top">${top.map((t, i) => `<li class="s-in" style="--d:${i + 3}">${e(t)}</li>`).join("")}</ol>` : ""}
        </div>`,
      next: "Done",
      last: true,
    });
    return slides;
  }

  // ------------------------------------------------------------ player
  function open(r) {
    close();
    const slides = buildSlides(r);
    const root = document.createElement("div");
    root.id = "story";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", "Your data story");
    root.innerHTML = `
      <div class="st-bars">${slides.map(() => `<i><b></b></i>`).join("")}</div>
      <button class="st-close" aria-label="Close the story">${T.icons.close}</button>
      <div class="st-blob a"></div><div class="st-blob b"></div><div class="st-blob c"></div>
      <div class="st-stage" aria-live="polite"></div>
      <div class="st-nav">
        <button class="st-back" aria-label="Previous">Back</button>
        <button class="st-next"></button>
      </div>
      <div class="st-confetti"></div>`;
    document.body.appendChild(root);
    document.body.classList.add("story-open");
    let i = -1;

    const show = (to) => {
      if (to < 0 || to >= slides.length) return;
      const dir = to > i ? 1 : -1;
      i = to;
      const s = slides[i];
      root.style.setProperty("--st-bg", s.color);
      root.querySelectorAll(".st-bars i").forEach((bar, k) => bar.classList.toggle("done", k <= i));
      const stage = root.querySelector(".st-stage");
      T.charts.disposeIn(stage);
      const slide = document.createElement("div");
      slide.className = "st-slide " + (dir > 0 ? "from-right" : "from-left");
      slide.innerHTML = s.html;
      stage.innerHTML = "";
      stage.appendChild(slide);
      requestAnimationFrame(() => slide.classList.add("on"));
      root.querySelector(".st-next").textContent = s.next;
      root.querySelector(".st-back").style.visibility = i === 0 ? "hidden" : "visible";
      root.classList.toggle("blobs-alt", i % 2 === 1);
      setTimeout(() => slide.querySelectorAll("[data-count]").forEach((el) => countUp(el, el.dataset.count)), 350);
      if (s.chart) setTimeout(() => { const c = slide.querySelector(".st-chart"); if (c) T.charts.render(c, s.chart); }, 450);
      root.querySelector(".st-confetti").innerHTML = s.confetti ? confetti() : "";
      root.querySelector(".st-next").focus({ preventScroll: true });
    };

    const next = () => (slides[i].last ? close() : show(i + 1));
    root.querySelector(".st-next").onclick = next;
    root.querySelector(".st-back").onclick = () => show(i - 1);
    root.querySelector(".st-close").onclick = close;
    root._keys = (ev) => {
      if (ev.key === "Escape") close();
      else if (ev.key === "ArrowRight" || ev.key === " " || ev.key === "Enter") { ev.preventDefault(); next(); }
      else if (ev.key === "ArrowLeft") show(i - 1);
    };
    document.addEventListener("keydown", root._keys);
    show(0);
  }

  function close() {
    const root = document.getElementById("story");
    if (!root) return;
    document.removeEventListener("keydown", root._keys);
    T.charts.disposeIn(root);
    root.remove();
    document.body.classList.remove("story-open");
  }

  function confetti() {
    const colors = ["#FAD36B", "#FFFFFF", "#EB6834", "#1BAF7A", "#E87BA4", "#86B6EF"];
    let out = "";
    for (let k = 0; k < 90; k++) {
      const left = Math.random() * 100, delay = Math.random() * 0.8, dur = 2.4 + Math.random() * 1.8;
      const size = 6 + Math.random() * 7, rot = Math.random() * 360, round = Math.random() < 0.35 ? "50%" : "2px";
      out += `<i style="left:${left}%;width:${size}px;height:${size * 0.6}px;background:${colors[k % colors.length]};border-radius:${round};animation-delay:${delay}s;animation-duration:${dur}s;transform:rotate(${rot}deg)"></i>`;
    }
    return out;
  }

  T.story = { open, close, hero };
})();
