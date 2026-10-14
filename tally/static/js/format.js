/* Number formatting that matches the Python side (tally/fmt.py). */
(function () {
  const T = (window.Tally = window.Tally || {});

  function trim(v, d) {
    let s = v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
    if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s;
  }

  function compact(x) {
    if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
    const a = Math.abs(x);
    const sign = x < 0 ? "-" : "";
    if (a >= 1e9) return sign + trim(a / 1e9, 1) + "B";
    if (a >= 1e6) return sign + trim(a / 1e6, 1) + "M";
    if (a >= 1e4) return sign + trim(a / 1e3, 1) + "K";
    if (a >= 100) return sign + trim(a, 0);
    if (a >= 10) return sign + trim(a, 1);
    if (a >= 1) return sign + trim(a, 2);
    if (a === 0) return "0";
    return sign + trim(a, 3);
  }

  function value(x, unit) {
    if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
    const kind = unit && unit.kind;
    if (kind === "currency") {
      const s = compact(Math.abs(x));
      return (x < 0 ? "-" : "") + (unit.symbol || "$") + s;
    }
    if (kind === "percent") return trim(x, 1) + "%";
    if (kind === "share") return trim(x * 100, x * 100 < 10 ? 1 : 0) + "%";
    return compact(x);
  }

  function pct(x) {
    return trim(x * 100, 0) + "%";
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function ago(iso) {
    const d = new Date(iso);
    const s = (Date.now() - d.getTime()) / 1000;
    if (s < 60) return "just now";
    if (s < 3600) return Math.floor(s / 60) + " min ago";
    if (s < 86400) return Math.floor(s / 3600) + " h ago";
    if (s < 86400 * 7) return Math.floor(s / 86400) + " d ago";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  T.fmt = { compact, value, pct, esc, ago };
})();
