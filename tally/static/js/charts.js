/* Charts, drawn with Apache ECharts. Calm by design:
   one highlight colour for the point of the story, quiet grey for everything else,
   hairline grids, values at the bar tips, and a tooltip on everything. */
(function () {
  const T = (window.Tally = window.Tally || {});
  const live = new Map(); // element -> {spec, chart}

  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function theme() {
    return {
      ink: css("--ink"), ink2: css("--ink-2"), muted: css("--muted"), grid: css("--grid"), axis: css("--axis"),
      data: css("--data"), rest: css("--data-rest"), attention: css("--attention"), surface: css("--surface"),
      soft: css("--data-soft"), font: css("--sans") || "system-ui", line: css("--line"),
    };
  }

  const SHORT = {
    Monday: "Mon", Tuesday: "Tue", Wednesday: "Wed", Thursday: "Thu", Friday: "Fri", Saturday: "Sat", Sunday: "Sun",
    January: "Jan", February: "Feb", March: "Mar", April: "Apr", May: "May", June: "Jun", July: "Jul",
    August: "Aug", September: "Sep", October: "Oct", November: "Nov", December: "Dec",
  };
  const clip = (s, n = 22) => (String(s).length > n ? String(s).slice(0, n - 1) + "…" : String(s));

  function base(th) {
    return {
      animationDuration: 650,
      animationEasing: "cubicOut",
      textStyle: { fontFamily: th.font, color: th.ink2 },
      tooltip: {
        backgroundColor: th.surface, borderColor: th.line, borderWidth: 1, padding: [8, 12],
        textStyle: { color: th.ink, fontSize: 13, fontFamily: th.font },
        extraCssText: "border-radius:10px; box-shadow:0 6px 24px rgba(0,0,0,.12);",
      },
    };
  }

  function axisCommon(th) {
    return {
      axisLine: { lineStyle: { color: th.axis } },
      axisTick: { show: false },
      axisLabel: { color: th.muted, fontSize: 12 },
      splitLine: { lineStyle: { color: th.grid, width: 1, type: "solid" } },
    };
  }

  /* ---------------------------------------------------------------- bar */
  function barOption(spec, th) {
    const f = (v) => T.fmt.value(v, spec.unit);
    const cats = spec.categories.map(String);
    const vertical = spec.keep_order && cats.length <= 12 && spec.type !== "drivers";
    const hl = new Set(spec.highlight || []);
    const hlColor = spec.accent === "attention" ? th.attention : th.data;
    const total = spec.share_of;
    const isDrivers = spec.type === "drivers";
    const data = spec.values.map((v, i) => ({
      value: v,
      itemStyle: { color: hl.has(i) ? hlColor : th.rest, borderRadius: vertical ? [4, 4, 0, 0] : [0, 4, 4, 0] },
    }));
    const label = {
      show: true,
      position: vertical ? "top" : "right",
      color: th.ink2, fontSize: 12.5, distance: 6,
      formatter: (p) => {
        if (isDrivers) return spec.words[p.dataIndex];
        if (vertical && !hl.has(p.dataIndex)) return "";
        return total ? `${f(p.value)}  ·  ${T.fmt.pct(p.value / total)}` : f(p.value);
      },
    };
    const series = {
      type: "bar", data, barMaxWidth: 22, barCategoryGap: "38%", label,
      emphasis: { focus: "none", itemStyle: { opacity: 0.85 } },
    };
    if (spec.reference && spec.reference.value !== undefined && spec.reference.value !== null) {
      series.markLine = {
        silent: true, symbol: "none",
        lineStyle: { color: th.muted, width: 1, type: [4, 4] },
        label: { color: th.muted, fontSize: 11.5, formatter: `${spec.reference.label}: ${f(spec.reference.value)}`, position: vertical ? "insideStartTop" : "start" },
        data: [vertical ? { yAxis: spec.reference.value } : { xAxis: spec.reference.value }],
      };
    }
    const valAxis = Object.assign({}, axisCommon(th), {
      type: "value",
      axisLabel: { color: th.muted, fontSize: 11.5, hideOverlap: true, formatter: (v) => (isDrivers ? "" : f(v)) },
      splitNumber: vertical ? 5 : 4,
      axisLine: { show: false },
      max: isDrivers ? 1 : undefined,
      splitLine: { show: !isDrivers, lineStyle: { color: th.grid } },
    });
    const catAxis = Object.assign({}, axisCommon(th), {
      type: "category", data: cats, inverse: !vertical,
      axisLabel: { color: th.ink2, fontSize: 12.5, formatter: (v) => (vertical ? SHORT[v] || clip(v, 10) : clip(v, 24)) },
      splitLine: { show: false },
    });
    const longest = Math.max(...cats.map((c) => clip(c, 24).length));
    return Object.assign(base(th), {
      grid: vertical
        ? { left: 8, right: 16, top: 30, bottom: 6, containLabel: true }
        : { left: 8, right: isDrivers ? 120 : total ? 120 : 76, top: spec.reference ? 24 : 8, bottom: 6, containLabel: true },
      xAxis: vertical ? catAxis : valAxis,
      yAxis: vertical ? valAxis : catAxis,
      tooltip: Object.assign(base(th).tooltip, {
        trigger: "item",
        formatter: (p) => {
          const v = isDrivers ? spec.words[p.dataIndex] : f(p.value) + (total ? ` (${T.fmt.pct(p.value / total)} of total)` : "");
          return `<b>${T.fmt.esc(p.name)}</b><br>${T.fmt.esc(spec.value_label || "")}: ${v}`;
        },
      }),
      series: [series],
      _height: vertical ? null : Math.max(170, cats.length * 38 + 40 + (spec.reference ? 16 : 0) + (longest > 18 ? 6 : 0)),
    });
  }

  /* ---------------------------------------------------------------- line */
  function lineOption(spec, th) {
    const f = (v) => T.fmt.value(v, spec.unit);
    const x = spec.x || spec.categories;
    const y = spec.y || spec.values;
    const hlColor = spec.emphasize_point ? th.attention : th.data;
    const marks = (spec.highlight || []).map((h) => ({
      coord: [h.index, y[h.index]], value: y[h.index],
      symbol: "circle", symbolSize: 10,
      itemStyle: { color: hlColor, borderColor: th.surface, borderWidth: 2 },
      label: { show: true, position: "top", distance: 8, color: th.ink, fontSize: 12, fontWeight: 600, formatter: `${h.label}: ${f(y[h.index])}` },
    }));
    const series = [{
      name: spec.y_label || "Value", type: "line", data: y, showSymbol: x.length <= 16, symbolSize: 6,
      lineStyle: { width: 2, color: th.data }, itemStyle: { color: th.data },
      areaStyle: { color: th.soft }, connectNulls: false,
      markPoint: { data: marks, animation: true },
    }];
    if (spec.trend) {
      series.push({
        name: "Trend line", type: "line", data: spec.trend, showSymbol: false, silent: true,
        lineStyle: { width: 1.5, color: th.muted, type: [5, 4] }, itemStyle: { color: th.muted },
      });
    }
    return Object.assign(base(th), {
      grid: { left: 8, right: 20, top: spec.trend && !spec.key ? 42 : 30, bottom: 6, containLabel: true },
      legend: spec.trend && !spec.key ? { top: 0, right: 0, icon: "roundRect", itemWidth: 14, itemHeight: 3, textStyle: { color: th.ink2, fontSize: 12 } } : undefined,
      xAxis: Object.assign({}, axisCommon(th), { type: "category", data: x, boundaryGap: false, splitLine: { show: false },
        axisLabel: { color: th.muted, fontSize: 11.5, hideOverlap: true } }),
      yAxis: Object.assign({}, axisCommon(th), { type: "value", axisLine: { show: false }, scale: false,
        axisLabel: { color: th.muted, fontSize: 11.5, formatter: (v) => f(v) } }),
      tooltip: Object.assign(base(th).tooltip, {
        trigger: "axis", axisPointer: { type: "line", lineStyle: { color: th.axis } },
        formatter: (ps) => {
          const head = `<b>${T.fmt.esc(ps[0].axisValue)}</b>`;
          return head + ps.map((p) => `<br>${p.marker} ${T.fmt.esc(p.seriesName)}: ${f(p.value)}`).join("");
        },
      }),
      series,
    });
  }

  /* ---------------------------------------------------------------- scatter */
  function scatterOption(spec, th) {
    const fx = (v) => T.fmt.value(v, spec.x_unit);
    const fy = (v) => T.fmt.value(v, spec.unit);
    return Object.assign(base(th), {
      grid: { left: 8, right: 20, top: 40, bottom: 26, containLabel: true },
      legend: spec.key ? undefined : { top: 0, right: 0, itemWidth: 12, itemHeight: 8, textStyle: { color: th.ink2, fontSize: 12 } },
      xAxis: Object.assign({}, axisCommon(th), { type: "value", scale: true, name: spec.x_label, nameLocation: "middle", nameGap: 28,
        nameTextStyle: { color: th.ink2, fontSize: 12.5 }, axisLabel: { color: th.muted, fontSize: 11.5, formatter: fx } }),
      yAxis: Object.assign({}, axisCommon(th), { type: "value", scale: true, axisLine: { show: false },
        axisLabel: { color: th.muted, fontSize: 11.5, formatter: fy } }),
      tooltip: Object.assign(base(th).tooltip, {
        trigger: "item",
        formatter: (p) => p.seriesType === "scatter"
          ? `${T.fmt.esc(spec.x_label)}: <b>${fx(p.value[0])}</b><br>${T.fmt.esc(spec.y_label)}: <b>${fy(p.value[1])}</b>` : "Trend",
      }),
      series: [
        { name: "Each dot is one row", type: "scatter", data: spec.points, symbolSize: 7,
          itemStyle: { color: th.data, opacity: 0.38, borderColor: th.surface, borderWidth: 0.5 },
          emphasis: { itemStyle: { opacity: 1 } }, large: spec.points.length > 1200 },
        { name: "Trend", type: "line", data: spec.trend, showSymbol: false, silent: true,
          lineStyle: { width: 2.5, color: th.ink }, itemStyle: { color: th.ink }, z: 5 },
      ],
    });
  }

  function optionFor(spec, th) {
    if (spec.type === "line") return lineOption(spec, th);
    if (spec.type === "scatter") return scatterOption(spec, th);
    return barOption(spec, th);
  }

  function render(el, spec) {
    if (!window.echarts || !spec || !spec.type) return null;
    const prev = live.get(el);
    if (prev) prev.chart.dispose();
    const th = theme();
    const opt = optionFor(spec, th);
    if (opt._height) el.style.height = opt._height + "px";
    delete opt._height;
    const chart = echarts.init(el, null, { renderer: "canvas" });
    chart.setOption(opt);
    live.set(el, { spec, chart });
    if (window.ResizeObserver && !el._ro) {
      el._ro = new ResizeObserver(() => chart.isDisposed() || chart.resize());
      el._ro.observe(el);
    }
    return chart;
  }

  function rerenderAll() {
    for (const [el, { spec }] of [...live.entries()]) {
      if (!document.body.contains(el)) { live.get(el).chart.dispose(); live.delete(el); continue; }
      render(el, spec);
    }
  }

  function disposeIn(root) {
    for (const [el, { chart }] of [...live.entries()]) {
      if (!root || root.contains(el) || !document.body.contains(el)) { chart.dispose(); live.delete(el); }
    }
  }

  function image(el) {
    const item = live.get(el);
    if (!item) return null;
    return item.chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: theme().surface });
  }

  /* A plain table twin for every chart, so no number is hidden behind a hover. */
  function table(spec) {
    const e = T.fmt.esc;
    let head, rows;
    if (spec.type === "scatter") {
      head = [spec.x_label, spec.y_label];
      rows = spec.points.slice(0, 200).map((p) => [T.fmt.value(p[0], spec.x_unit), T.fmt.value(p[1], spec.unit)]);
    } else if (spec.type === "line") {
      head = ["Period", spec.y_label || "Value"].concat(spec.trend ? ["Trend line"] : []);
      rows = (spec.x || spec.categories).map((x, i) => [x, T.fmt.value((spec.y || spec.values)[i], spec.unit)].concat(spec.trend ? [T.fmt.value(spec.trend[i], spec.unit)] : []));
    } else if (spec.type === "drivers") {
      head = ["Column", "Connection"];
      rows = spec.categories.map((c, i) => [c, spec.words[i]]);
    } else {
      head = ["", spec.value_label || "Value"].concat(spec.share_of ? ["Share"] : []);
      rows = spec.categories.map((c, i) => [c, T.fmt.value(spec.values[i], spec.unit)].concat(spec.share_of ? [T.fmt.pct(spec.values[i] / spec.share_of)] : []));
    }
    const note = spec.type === "scatter" && spec.points.length > 200 ? `<p class="muted" style="font-size:13px;margin-top:6px">Showing the first 200 of ${spec.points.length} sampled rows.</p>` : "";
    return `<div class="table-scroll"><table class="data-table"><thead><tr>${head.map((h, i) => `<th class="${i ? "num" : ""}">${e(h)}</th>`).join("")}</tr></thead><tbody>${rows
      .map((r) => `<tr>${r.map((c, i) => `<td class="${i ? "num" : ""}">${e(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>${note}`;
  }

  window.addEventListener("resize", () => live.forEach(({ chart }) => chart.isDisposed() || chart.resize()));
  T.charts = { render, rerenderAll, disposeIn, image, table };
})();
