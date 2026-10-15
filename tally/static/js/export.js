/* Saving a report as a PDF, a PNG image, or a self-contained interactive HTML file. */
(function () {
  const T = (window.Tally = window.Tally || {});
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  async function prepare(container) {
    const html = document.documentElement;
    const prevTheme = html.getAttribute("data-theme");
    html.setAttribute("data-theme", "light");
    document.body.classList.add("exporting");
    const about = container.querySelector("details.about");
    const wasOpen = about && about.open;
    if (about) about.open = true;
    if (container._drawAll) container._drawAll();
    T.charts.rerenderAll();
    await wait(900); // let the chart animations finish
    return () => {
      if (prevTheme) html.setAttribute("data-theme", prevTheme);
      else html.removeAttribute("data-theme");
      document.body.classList.remove("exporting");
      if (about) about.open = wasOpen;
      T.charts.rerenderAll();
    };
  }

  function blocks(container) {
    return [...container.querySelectorAll("#report-root > [data-block]")];
  }

  async function snap(el, scale = 2) {
    return html2canvas(el, {
      scale, backgroundColor: "#f6f5f1", useCORS: true, logging: false,
      ignoreElements: (n) => n.hasAttribute && n.hasAttribute("data-noexport"),
    });
  }

  async function pdf(container, report) {
    const restore = await prepare(container);
    try {
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ unit: "pt", format: "a4", compress: true });
      const W = doc.internal.pageSize.getWidth();
      const H = doc.internal.pageSize.getHeight();
      const M = 34;
      const paint = () => { doc.setFillColor(246, 245, 241); doc.rect(0, 0, W, H, "F"); };
      paint();
      let y = M;
      for (const el of blocks(container)) {
        const c = await snap(el);
        let w = W - 2 * M;
        let h = (c.height * w) / c.width;
        const maxH = H - 2 * M - 14;
        if (h > maxH) { w = (w * maxH) / h; h = maxH; }
        if (y + h > H - M - 14) { doc.addPage(); paint(); y = M; }
        doc.addImage(c.toDataURL("image/jpeg", 0.92), "JPEG", (W - w) / 2, y, w, h, undefined, "FAST");
        y += h + 10;
      }
      const pages = doc.getNumberOfPages();
      for (let i = 1; i <= pages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(137, 135, 129);
        doc.text(`Tally  ·  ${ascii(report.story.title)}  ·  page ${i} of ${pages}`, M, H - 16);
      }
      doc.save(T.slug(report.story.title) + ".pdf");
    } finally {
      restore();
    }
  }

  async function png(container, report) {
    const restore = await prepare(container);
    try {
      const root = container.querySelector("#report-root");
      const h = root.scrollHeight;
      const scale = Math.max(1, Math.min(2, 30000 / h));
      const c = await html2canvas(root, {
        scale, backgroundColor: "#f6f5f1", logging: false,
        ignoreElements: (n) => n.hasAttribute && (n.hasAttribute("data-noexport") || n.hasAttribute("data-chat-slot")),
      });
      T.download(c.toDataURL("image/png"), T.slug(report.story.title) + ".png");
    } finally {
      restore();
    }
  }

  async function html(report) {
    const files = ["/static/css/app.css", "/static/vendor/echarts.min.js", "/static/js/format.js", "/static/js/icons.js",
      "/static/js/mascot.js", "/static/js/charts.js", "/static/js/report-view.js", "/static/js/story.js"];
    const [css, ...js] = await Promise.all(files.map((f) => fetch(f).then((r) => r.text())));
    const safe = (s) => s.replace(/<\/script/gi, "<\\/script");
    const data = JSON.stringify(Object.assign({}, report, { chat: undefined })).replace(/</g, "\\u003c");
    const page = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${T.fmt.esc(report.story.title)} · Tally</title>
<style>${css}</style></head>
<body>
<header class="topbar"><span class="brand" id="brand"></span><span class="spacer"></span><span class="muted" style="font-size:13px">Interactive report</span></header>
<main id="app"></main>
${js.map((s) => `<script>${safe(s)}<\/script>`).join("\n")}
<script>window.TALLY_REPORT = ${data};
document.getElementById("brand").innerHTML = Tally.mascot(26) + "Tally";
Tally.report.render(document.getElementById("app"), window.TALLY_REPORT, { standalone: true });<\/script>
</body></html>`;
    const blob = new Blob([page], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    T.download(url, T.slug(report.story.title) + ".html");
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  function ascii(s) {
    return String(s).replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/[^\x20-\x7E]/g, "");
  }

  T.exporter = { pdf, png, html };
})();
