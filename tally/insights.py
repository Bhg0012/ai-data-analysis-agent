"""The statistics engine.

Every finding here is computed with plain, deterministic maths (pandas + scipy).
The AI never invents numbers: it only re-words what this module proves.

How we stay honest:
  * every pattern is checked with a proper statistical test,
  * all p-values from the whole run are corrected together (Benjamini-Hochberg),
    so testing lots of columns doesn't produce lucky "discoveries",
  * a pattern must also be big enough to matter (an effect-size floor),
  * obvious links (e.g. Revenue = Quantity x Price) are detected and skipped.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from . import fmt
from .profile import Profile

ALPHA = 0.05
MIN_GROUP = 5
MAX_LEVELS = 10
MAX_INSIGHTS = 7

SECTIONS = [
    ("big-picture", "The big picture"),
    ("time", "Changes over time"),
    ("composition", "Where it comes from"),
    ("groups", "What makes a difference"),
    ("together", "Things that move together"),
    ("surprises", "Worth a closer look"),
]
SECTION_ORDER = {k: i for i, (k, _) in enumerate(SECTIONS)}
SECTION_TITLE = dict(SECTIONS)
KIND_WEIGHT = {
    "drivers": 1.25, "trend": 1.15, "composition": 1.0, "group": 1.0, "rhythm": 0.95,
    "correlation": 0.9, "association": 0.75, "outliers": 0.7, "spike": 0.75, "mix": 0.6,
}


@dataclass
class Candidate:
    kind: str
    section: str
    columns: list[str]
    p: float | None
    strength: float          # 0..1, how big the pattern is
    passes_effect: bool      # big enough to matter?
    test: str
    effect_text: str
    n: int
    title: str = ""
    headline: str = ""
    explanation: str = ""
    ideas: list[str] = field(default_factory=list)
    chart: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)
    q: float | None = None
    score: float = 0.0
    measure: str | None = None
    key: tuple = ()          # candidates with the same key tell the same story
    rows: frozenset = frozenset()


# ------------------------------------------------------------------ helpers

def bh_adjust(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg false-discovery-rate adjustment."""
    m = len(pvals)
    if m == 0:
        return []
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order] * m / (np.arange(m) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0, 1)
    return out.tolist()


def _nice(name: str) -> str:
    return name


def _stat_word(skewed: bool) -> str:
    return "typical" if skewed else "average"


def _central(s: pd.Series, skewed: bool) -> float:
    return float(s.median() if skewed else s.mean())


def _is_skewed(s: pd.Series) -> bool:
    s = s.dropna()
    if len(s) < 8 or s.nunique() < 3:
        return False
    return abs(float(stats.skew(s))) > 2


def _label(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return f"#{int(v)}"
    if isinstance(v, (int, np.integer)):
        return f"#{v}"
    return str(v)


def _period_label(p: pd.Period, freq: str) -> str:
    ts = p.start_time
    if freq == "D":
        return f"{ts:%b} {ts.day}, {ts:%Y}"
    if freq == "W":
        return f"Week of {ts:%b} {ts.day}, {ts:%Y}"
    if freq == "M":
        return f"{ts:%b %Y}"
    if freq == "Q":
        return f"Q{p.quarter} {p.year}"
    return f"{p.year}"


FREQ_WORD = {"D": "day", "W": "week", "M": "month", "Q": "quarter", "Y": "year"}


class Engine:
    def __init__(self, df: pd.DataFrame, prof: Profile, progress=None):
        self.df = df
        self.prof = prof
        self.cands: list[Candidate] = []
        self.tests_run = 0
        self.all_p: list[float] = []
        self.health: list[str] = []
        self.derived: dict[str, tuple[str, str, str]] = {}
        self.progress = progress or (lambda *_: None)

    # ---------------------------------------------------------------- utils
    def unit(self, col):
        c = self.prof.columns.get(col)
        return c.unit if c else None

    def v(self, x, col):
        return fmt.value(x, self.unit(col))

    def add(self, c: Candidate):
        if c.p is not None:
            self.tests_run += 1
        self.cands.append(c)

    def counted(self, n: int = 1):
        self.tests_run += n

    def label_for(self, col: str) -> str:
        return col

    # ---------------------------------------------------------------- run
    def run(self) -> list[Candidate]:
        steps = [
            ("Looking for columns calculated from other columns", self.find_derived),
            ("Checking changes over time", self.trends),
            ("Checking weekly and seasonal rhythms", self.rhythms),
            ("Comparing groups", self.groups),
            ("Seeing where the totals come from", self.composition),
            ("Testing which numbers move together", self.correlations),
            ("Checking how categories overlap", self.associations),
            ("Hunting for unusual values", self.outliers),
        ]
        for label, fn in steps:
            self.progress(label)
            try:
                fn()
            except Exception as e:  # noqa: BLE001 - one bad check must not sink the report
                self.health.append(f"One check ('{label}') was skipped because of an unexpected problem: {e}")
        self._fdr()
        self.drivers()
        return self.cands

    def _fdr(self):
        tested = [c for c in self.cands if c.p is not None]
        qs = bh_adjust([c.p for c in tested])
        # The adjustment must account for *every* test we ran, including ones that
        # never became candidates. Re-scale by the total number of tests.
        m_cands = len(tested)
        m_total = max(self.tests_run, m_cands)
        for c, q in zip(tested, qs):
            c.q = min(1.0, q * m_total / m_cands) if m_cands else q

    # ---------------------------------------------------------------- derived
    def find_derived(self):
        ms = [m for m in self.prof.measures]
        if len(ms) < 3:
            return
        df = self.df
        for target in ms:
            t = df[target]
            for i, a in enumerate(ms):
                for b in ms[i + 1:]:
                    if target in (a, b):
                        continue
                    sub = pd.concat([t, df[a], df[b]], axis=1).dropna()
                    if len(sub) < 10:
                        continue
                    tt, aa, bb = sub.iloc[:, 0], sub.iloc[:, 1], sub.iloc[:, 2]
                    scale = np.maximum(np.abs(tt), 1e-9)
                    for op, est in (("x", aa * bb), ("+", aa + bb), ("-", aa - bb), ("-", bb - aa)):
                        close = (np.abs(est - tt) <= 0.02 * scale + 0.01).mean()
                        if close >= 0.95:
                            self.derived[target] = (a, op, b)
                            break
                    if target in self.derived:
                        break
                if target in self.derived:
                    break
        for t, (a, op, b) in self.derived.items():
            word = {"x": "times", "+": "plus", "-": "minus"}[op]
            self.health.append(
                f"'{t}' looks like it's calculated as '{a}' {word} '{b}', so I didn't report the obvious link between them."
            )

    def _is_trivial_pair(self, a: str, b: str) -> bool:
        for t, (x, _, y) in self.derived.items():
            if (a == t and b in (x, y)) or (b == t and a in (x, y)):
                return True
        return False

    # ---------------------------------------------------------------- time
    def _time_key(self, tcol: str):
        """Pick a sensible period size and return (period series, freq, full period index)."""
        s = self.df[tcol]
        col = self.prof.columns[tcol]
        if col.detail.get("year_only"):
            years = pd.to_datetime(s.astype("Int64").astype("string"), format="%Y", errors="coerce")
            return years.dt.to_period("Y"), "Y"
        smin, smax = s.min(), s.max()
        span = (smax - smin).days
        n_rows = s.notna().sum()
        for freq in ("D", "W", "M", "Q", "Y"):
            periods = {"D": span + 1, "W": span / 7 + 1, "M": span / 30.4 + 1, "Q": span / 91 + 1, "Y": span / 365 + 1}[freq]
            if periods <= 60 and n_rows / max(periods, 1) >= 3:
                break
        pfreq = {"W": "W-SUN"}.get(freq, freq)
        per = s.dt.to_period(pfreq)
        return per, freq

    def series_for(self, tcol: str, measure: str | None):
        """Aggregate a measure (or row counts) per period, dropping half-finished edge periods."""
        per, freq = self._time_key(tcol)
        df = self.df
        mask = per.notna()
        if measure is None:
            g = df[mask].groupby(per[mask]).size().astype(float)
            agg = "count"
        else:
            col = self.prof.columns[measure]
            mask &= df[measure].notna()
            agg = col.agg
            g = df[mask].groupby(per[mask])[measure].agg(agg)
        if g.empty:
            return None
        full = pd.period_range(g.index.min(), g.index.max(), freq=g.index.freq)
        g = g.reindex(full)
        if agg in ("sum", "count"):
            g = g.fillna(0.0)
        dropped = []
        if not self.prof.columns[tcol].detail.get("year_only"):
            s = df[tcol]
            if len(g) > 3:
                first, last = g.index[0], g.index[-1]
                days = lambda p: (p.end_time - p.start_time).days + 1  # noqa: E731
                cov_last = ((s.max() - last.start_time).days + 1) / days(last)
                cov_first = ((first.end_time - s.min()).days + 1) / days(first)
                if freq != "D" and cov_last < 0.8:
                    g = g.iloc[:-1]
                    dropped.append("last")
                if freq != "D" and cov_first < 0.8:
                    g = g.iloc[1:]
                    dropped.append("first")
        return g, freq, agg, dropped

    def trends(self):
        if not self.prof.times:
            return
        tcol = self._main_time()
        targets = list(self.prof.measures)
        if not any(self.prof.columns[m].additive for m in targets):
            targets.append(None)  # row counts become "activity over time"
        for m in targets:
            res = self.series_for(tcol, m)
            if res is None:
                continue
            g, freq, agg, dropped = res
            y = g.dropna()
            if len(y) < 6:
                continue
            x = np.arange(len(g))[g.notna().to_numpy()]
            tau, p = stats.kendalltau(x, y.to_numpy())
            if np.isnan(p):
                continue
            slope, intercept, *_ = stats.theilslopes(y.to_numpy(), x)
            f_start = intercept + slope * x[0]
            f_end = intercept + slope * x[-1]
            rel = (f_end - f_start) / abs(f_start) if abs(f_start) > 1e-9 else np.nan
            big_enough = abs(tau) >= 0.3 and (np.isnan(rel) or abs(rel) >= 0.10)
            labels = [_period_label(pp, freq) for pp in g.index]
            name = m or "Number of records"
            word = FREQ_WORD[freq]
            up = slope > 0
            what = ("Total " if agg == "sum" else "Average " if agg == "mean" else "") + (m or "number of records")
            if m is None:
                what = "Number of records"
            peak_i = int(np.nanargmax(g.to_numpy()))
            low_i = int(np.nanargmin(g.to_numpy()))
            vfmt = (lambda val: self.v(val, m)) if m else fmt.compact
            change_txt = fmt.pct(abs(rel)) if not np.isnan(rel) else None
            facts = {
                "metric": what, "direction": "up" if up else "down", "period": word,
                "from_period": labels[0], "to_period": labels[-1],
                "start_value_trend": vfmt(f_start), "end_value_trend": vfmt(f_end),
                "percent_change": change_txt, "periods_compared": str(len(y)),
                "highest_period": labels[peak_i], "highest_value": vfmt(g.iloc[peak_i]),
            }
            dir_word = "grown" if up else "dropped"
            title = f"{name} {'is rising' if up else 'is falling'} over time"
            if change_txt:
                headline = f"{what} has {dir_word} by about {change_txt} from {labels[0]} to {labels[-1]}."
            else:
                headline = f"{what} has {dir_word} steadily from {labels[0]} to {labels[-1]}."
            expl = (
                f"Looking {word} by {word}, the line keeps heading {'up' if up else 'down'}. "
                f"This isn't just one lucky {word}: it's a steady pattern across {len(y)} {word}s. "
                f"The trend line goes from about {vfmt(f_start)} to about {vfmt(f_end)} per {word}."
            )
            if dropped:
                expl += f" (I left out the {' and '.join(dropped)} {word} because it only had part of a {word} of data, which would make it look misleadingly low.)"
            ideas = (
                [f"Find out what's been driving the growth and see if you can do more of it.",
                 f"Plan ahead for continued growth (stock, staff, budget)."]
                if up else
                [f"Look at what changed around {labels[0]} to {labels[-1]} to understand the drop.",
                 f"Compare the best and worst {word}s to see what was different."]
            )
            chart = {
                "type": "line", "x": labels,
                "y": [None if pd.isna(v) else float(v) for v in g.to_numpy()],
                "trend": [float(intercept + slope * i) for i in range(len(g))],
                "unit": self.unit(m) if m else None, "y_label": what, "x_label": word.capitalize(),
                "highlight": [{"index": peak_i, "label": "Highest"}],
            }
            self.add(Candidate(
                kind="trend", section="time", columns=[tcol] + ([m] if m else []), p=float(p),
                strength=min(1.0, abs(tau) * 1.6), passes_effect=big_enough, test="Mann-Kendall trend test",
                effect_text=f"Kendall's tau = {tau:.2f}", n=len(y), title=title, headline=headline,
                explanation=expl, ideas=ideas, chart=chart, facts=facts, measure=m, key=("trend", tcol),
            ))
            self._spike(g, freq, labels, m, what, vfmt, tcol, low_i)

    def _spike(self, g, freq, labels, m, what, vfmt, tcol, low_i):
        """One period that sits far away from its neighbours."""
        y = g.to_numpy(dtype=float)
        if len(y) < 8 or np.isnan(y).any():
            return
        base = pd.Series(y).rolling(5, center=True, min_periods=3).median().to_numpy()
        resid = y - base
        mad = np.median(np.abs(resid - np.median(resid))) * 1.4826
        if mad <= 0:
            return
        z = resid / mad
        i = int(np.argmax(np.abs(z)))
        if abs(z[i]) < 4.5:
            return
        word = FREQ_WORD[freq]
        hi = z[i] > 0
        facts = {"metric": what, "period": labels[i], "value": vfmt(y[i]), "usual_value": vfmt(base[i]),
                 "direction": "higher" if hi else "lower", "_index": i}
        self.add(Candidate(
            kind="spike", section="surprises", columns=[tcol] + ([m] if m else []), p=None,
            strength=min(1.0, abs(z[i]) / 10), passes_effect=True, test="Robust outlier check (median-based z-score)",
            effect_text=f"robust z = {z[i]:.1f}", n=len(y),
            title=f"{labels[i]} stands out",
            headline=f"{what} in {labels[i]} was {vfmt(y[i])}, far {'above' if hi else 'below'} the usual {vfmt(base[i])} around that time.",
            explanation=(
                f"Most {word}s follow a fairly smooth pattern, but {labels[i]} breaks it. "
                f"Something unusual probably happened then, like a promotion, a big one-off deal, an outage, or a data entry problem."
            ),
            ideas=[f"Check what happened in {labels[i]}. If it was a success, it might be worth repeating.",
                   "If it was a mistake in the data, fixing it will make every other number more accurate."],
            chart={"type": "line", "x": labels, "y": [float(v) for v in y], "unit": self.unit(m) if m else None,
                   "y_label": what, "x_label": word.capitalize(),
                   "highlight": [{"index": i, "label": "Unusual"}], "emphasize_point": True},
            facts=facts, measure=m, key=("spike", tcol, labels[i]),
        ))

    def _main_time(self) -> str:
        ts = self.prof.times
        return min(ts, key=lambda t: self.prof.columns[t].missing)

    # ---------------------------------------------------------------- rhythms
    def rhythms(self):
        """Day-of-week and month-of-year patterns."""
        if not self.prof.times:
            return
        tcol = self._main_time()
        if self.prof.columns[tcol].detail.get("year_only"):
            return
        s = self.df[tcol]
        dates = s.dt.normalize()
        span = (s.max() - s.min()).days
        targets = [m for m in self.prof.measures] or [None]
        if self.prof.main_metric:
            targets = [self.prof.main_metric] + [m for m in targets if m != self.prof.main_metric][:2]
        else:
            targets = targets[:3]
        if span >= 28 and dates.dt.dayofweek.nunique() >= 5:
            order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for m in targets:
                self._rhythm(tcol, m, "day of the week", lambda d: d.dt.day_name(), order, "D")
        if span >= 730:
            order = ["January", "February", "March", "April", "May", "June", "July", "August",
                     "September", "October", "November", "December"]
            for m in targets:
                self._rhythm(tcol, m, "month of the year", lambda d: d.dt.month_name(), order, "M")

    def _rhythm(self, tcol, m, label, keyfn, order, unit_freq):
        df = self.df
        s = df[tcol]
        if m is None:
            agg = "count"
        else:
            agg = self.prof.columns[m].agg
        mask = s.notna() & (df[m].notna() if m else True)
        sub = df[mask]
        if agg in ("sum", "count"):
            # compare totals per calendar day (or month), not per row
            per = sub[tcol].dt.to_period(unit_freq)
            daily = sub.groupby(per)[m].sum() if m else sub.groupby(per).size().astype(float)
            full = pd.period_range(daily.index.min(), daily.index.max(), freq=daily.index.freq)
            daily = daily.reindex(full, fill_value=0.0)
            keys = keyfn(pd.Series(daily.index.start_time))
            values = pd.Series(daily.to_numpy(), index=keys.to_numpy())
            unit_word = "day" if unit_freq == "D" else "month"
        else:
            keys = keyfn(sub[tcol])
            values = pd.Series(sub[m].to_numpy(), index=keys.to_numpy())
            unit_word = "row"
        groups = {k: values[values.index == k] for k in order if (values.index == k).sum() >= 3}
        if len(groups) < 3:
            return
        arrs = [g.to_numpy(dtype=float) for g in groups.values()]
        try:
            h, p = stats.kruskal(*arrs)
        except ValueError:
            return
        n = sum(len(a) for a in arrs)
        eps2 = h * (n + 1) / (n ** 2 - 1)
        skewed = _is_skewed(values)
        means = {k: _central(g, skewed) for k, g in groups.items()}
        top = max(means, key=means.get)
        low = min(means, key=means.get)
        what = (f"total {m} per {unit_word}" if agg == "sum" else f"{_stat_word(skewed)} {m}" if m else f"records per {unit_word}")
        vf = (lambda x: self.v(x, m)) if m else fmt.compact
        ratio = means[top] / means[low] if means[low] > 0 else None
        thing = "s" if unit_freq == "D" else ""
        cmp = f", {fmt.times(ratio)} {low}{thing}" if ratio and ratio >= 1.15 else f", compared with {vf(means[low])} on {low}{thing}"
        facts = {"metric": what, "best": top, "best_value": vf(means[top]), "worst": low, "worst_value": vf(means[low]),
                 "pattern": label}
        self.add(Candidate(
            kind="rhythm", section="groups", columns=[tcol] + ([m] if m else []), p=float(p),
            strength=min(1.0, math.sqrt(max(eps2, 0)) * 1.6), passes_effect=eps2 >= 0.04,
            test="Kruskal-Wallis test", effect_text=f"epsilon-squared = {eps2:.3f}", n=n,
            title=f"{top}{thing} are the strongest {'days' if unit_freq == 'D' else 'months'}",
            headline=f"{top}{thing} have the highest {what} ({vf(means[top])}){cmp}.",
            explanation=(
                f"There's a real {label} pattern here. {top}{thing} consistently come out on top, "
                f"while {low}{thing} are the quietest. This held up across the whole period, not just a few lucky {'days' if unit_freq == 'D' else 'months'}."
            ),
            ideas=[f"Plan staff, stock, or promotions around busy {top}{thing}.",
                   f"You could try a special offer on {low}{thing} to lift the slowest time."],
            chart={"type": "bar", "categories": list(groups.keys()), "values": [means[k] for k in groups],
                   "unit": self.unit(m) if m else None, "highlight": [list(groups).index(top)],
                   "value_label": what, "keep_order": True,
                   "reference": {"value": _central(values, skewed), "label": "Overall"}},
            facts=facts, measure=m, key=("rhythm", label),
        ))

    # ---------------------------------------------------------------- groups
    def _levels(self, cat: str, mask=None):
        s = self.df[cat] if mask is None else self.df.loc[mask, cat]
        vc = s.value_counts()
        vc = vc[vc >= MIN_GROUP]
        return list(vc.index[:MAX_LEVELS])

    def groups(self):
        for cat in self.prof.categories:
            for m in self.prof.measures:
                sub = self.df[[cat, m]].dropna()
                levels = [lv for lv in self._levels(cat) if (sub[cat] == lv).sum() >= MIN_GROUP]
                if len(levels) < 2:
                    continue
                sub = sub[sub[cat].isin(levels)]
                arrs = [sub.loc[sub[cat] == lv, m].to_numpy(dtype=float) for lv in levels]
                n = sum(len(a) for a in arrs)
                try:
                    if len(arrs) == 2:
                        u, p = stats.mannwhitneyu(arrs[0], arrs[1], alternative="two-sided")
                        r = 1 - 2 * u / (len(arrs[0]) * len(arrs[1]))
                        eff, eff_txt, ok = abs(r), f"rank-biserial r = {r:.2f}", abs(r) >= 0.2
                        test = "Mann-Whitney U test"
                    else:
                        h, p = stats.kruskal(*arrs)
                        e2 = h * (n + 1) / (n ** 2 - 1)
                        eff, eff_txt, ok = math.sqrt(max(e2, 0)), f"epsilon-squared = {e2:.3f}", e2 >= 0.04
                        test = "Kruskal-Wallis test"
                except ValueError:
                    continue
                if np.isnan(p):
                    continue
                skewed = _is_skewed(sub[m])
                cent = {lv: _central(pd.Series(a), skewed) for lv, a in zip(levels, arrs)}
                ordered = sorted(cent, key=cent.get, reverse=True)
                top, low = ordered[0], ordered[-1]
                word = _stat_word(skewed)
                vt, vl = self.v(cent[top], m), self.v(cent[low], m)
                if cent[low] > 0 and cent[top] / cent[low] >= 1.15:
                    cmp = f"{fmt.times(cent[top] / cent[low])} {low} ({vl})"
                else:
                    cmp = f"compared with {vl} for {low}"
                overall = _central(sub[m], skewed)
                facts = {"metric": f"{word} {m}", "group_column": cat, "best": str(top), "best_value": vt,
                         "worst": str(low), "worst_value": vl, "overall_value": self.v(overall, m),
                         "groups_compared": str(len(levels))}
                if self._is_trivial_pair(cat, m):
                    continue
                more = " ('typical' means the middle value, so a few extreme rows can't distort it)" if skewed else ""
                self.add(Candidate(
                    kind="group", section="groups", columns=[cat, m], p=float(p), strength=min(1.0, eff * 1.6),
                    passes_effect=ok, test=test, effect_text=eff_txt, n=n, measure=m,
                    title=f"{top} leads on {m}",
                    headline=f"{top} has the highest {word} {m} ({vt}), {cmp}.",
                    explanation=(
                        f"When you split the data by {cat}, the {m} values are clearly different between groups{more}. "
                        f"The gap is big enough, and based on enough rows ({fmt.count(n)}), that it's very unlikely to be random."
                    ),
                    ideas=[f"Lean into what's working with {top}, and look at whether any of it could help {low}.",
                           f"Before acting, check whether {top} and {low} also differ in other ways (size, timing, who they serve)."],
                    chart={"type": "bar", "categories": [str(x) for x in ordered], "values": [cent[x] for x in ordered],
                           "unit": self.unit(m), "highlight": [0], "value_label": f"{word.capitalize()} {m}",
                           "reference": {"value": overall, "label": "Overall"}},
                    facts=facts, key=("group", cat),
                ))

    # ---------------------------------------------------------------- composition
    def composition(self):
        for m in self.prof.measures:
            col = self.prof.columns[m]
            if not col.additive:
                continue
            for cat in self.prof.categories:
                sub = self.df[[cat, m]].dropna()
                if len(sub) < 20:
                    continue
                totals = sub.groupby(cat)[m].sum().sort_values(ascending=False)
                k = len(totals)
                if k < 3 or (totals < 0).any() or totals.sum() <= 0:
                    continue
                share = totals / totals.sum()
                top1 = float(share.iloc[0])
                n20 = max(1, math.ceil(0.2 * k))
                top20 = float(share.iloc[:n20].sum())
                notable = top1 >= max(0.3, 1.6 / k) or (k >= 5 and top20 >= 0.6)
                # Is this more than chance? Either rows pile up in one group,
                # or values are bigger in one group. Bonferroni x2 for the two checks.
                counts = sub[cat].value_counts()
                try:
                    p1 = stats.chisquare(counts.to_numpy()).pvalue
                    lvls = [lv for lv in counts.index[:MAX_LEVELS] if counts[lv] >= MIN_GROUP]
                    p2 = stats.kruskal(*[sub.loc[sub[cat] == lv, m].to_numpy() for lv in lvls]).pvalue if len(lvls) >= 2 else 1.0
                except ValueError:
                    continue
                p = min(1.0, 2 * min(p1, p2))
                self.counted(1)  # we ran two checks, one is already counted via add()
                shown = totals.iloc[:8]
                cats = [str(x) for x in shown.index]
                vals = shown.tolist()
                if k > 8:
                    cats.append(f"Other ({k - 8})")
                    vals.append(float(totals.iloc[8:].sum()))
                top = str(totals.index[0])
                if k >= 5 and top20 >= 0.6 and n20 > 1:
                    headline = f"Just {n20} of {k} {cat} groups bring in {fmt.pct(top20)} of all {m}."
                    names = fmt.join_words([str(x) for x in totals.index[:n20]])
                    expl = f"A small number of groups do most of the work: {names}. The other {k - n20} share what's left."
                else:
                    headline = f"{top} brings in {fmt.pct(top1)} of all {m}, more than any other {cat}."
                    expl = f"If {m} was spread evenly, each of the {k} groups would have about {fmt.pct(1 / k)}. {top} is well above that."
                expl += " This comes straight from adding up your data, so the shares are exact."
                facts = {"metric": m, "group_column": cat, "top": top, "top_share": fmt.pct(top1),
                         "top_total": self.v(float(totals.iloc[0]), m), "grand_total": self.v(float(totals.sum()), m),
                         "groups": str(k)}
                self.add(Candidate(
                    kind="composition", section="composition", columns=[cat, m], p=float(p),
                    strength=min(1.0, (top1 - 1 / k) / (1 - 1 / k) * 1.5 + (0.2 if top20 >= 0.6 else 0)),
                    passes_effect=notable, test="Chi-square + Kruskal-Wallis check that the split isn't chance",
                    effect_text=f"top group share = {top1:.2f} (even split would be {1 / k:.2f})", n=len(sub),
                    measure=m, title=f"Where {m} comes from", headline=headline, explanation=expl,
                    ideas=[f"Protect what's working with {top}: it carries a big part of the total.",
                           f"Relying heavily on a few groups is a risk. It might be worth growing the others too."],
                    chart={"type": "bar", "categories": cats, "values": vals, "unit": self.unit(m),
                           "highlight": [0], "value_label": f"Total {m}", "share_of": float(totals.sum())},
                    facts=facts,
                ))

    # ---------------------------------------------------------------- correlations
    def correlations(self):
        ms = [m for m in self.prof.measures if self.df[m].nunique() >= 3]
        df = self.df
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                sub = df[[a, b]].dropna()
                if len(sub) < 15:
                    continue
                if self._is_trivial_pair(a, b):
                    continue
                rho, p = stats.spearmanr(sub[a], sub[b])
                if np.isnan(p):
                    continue
                if abs(rho) > 0.97:
                    self.health.append(f"'{a}' and '{b}' move almost perfectly together, so one is probably calculated from the other. I didn't count that as a discovery.")
                    continue
                main = self.prof.main_metric
                x, y = (b, a) if a == main else (a, b)
                sub = sub[[x, y]]
                q_lo, q_hi = sub[x].quantile(0.25), sub[x].quantile(0.75)
                lo = sub.loc[sub[x] <= q_lo, y]
                hi = sub.loc[sub[x] >= q_hi, y]
                skewed = _is_skewed(sub[y])
                vlo, vhi = _central(lo, skewed), _central(hi, skewed)
                word = _stat_word(skewed)
                up = rho > 0
                facts = {"x": x, "y": y, "direction": "same" if up else "opposite", "strength": fmt.strength_word(rho),
                         "y_when_x_high": self.v(vhi, y), "y_when_x_low": self.v(vlo, y), "rows": fmt.count(len(sub))}
                sample = sub.sample(n=min(len(sub), 1500), random_state=7)
                slope, intercept, *_ = stats.linregress(sub[x], sub[y]) if sub[x].nunique() > 1 else (0, 0)
                x0, x1 = float(sub[x].min()), float(sub[x].max())
                self.add(Candidate(
                    kind="correlation", section="together", columns=[x, y], p=float(p), strength=min(1.0, abs(rho)),
                    passes_effect=abs(rho) >= 0.3, test="Spearman rank correlation", effect_text=f"Spearman rho = {rho:.2f}",
                    n=len(sub), measure=y,
                    title=f"More {x} goes with {'more' if up else 'less'} {y}",
                    headline=(f"When {x} is high, {y} tends to be {'higher' if up else 'lower'}: "
                              f"{word} {self.v(vhi, y)} for the top quarter of {x}, vs {self.v(vlo, y)} for the bottom quarter."),
                    explanation=(
                        f"Each dot is one row. As you move right ({x} goes up), the dots tend to drift {'up' if up else 'down'}. "
                        f"It's a {fmt.strength_word(rho)} link across {fmt.count(len(sub))} rows. "
                        f"Keep in mind this shows they move together, not that one causes the other."
                    ),
                    ideas=[f"Test it: try changing {x} on a small scale and watch whether {y} follows.",
                           f"Use {x} as an early signal for where {y} is heading."],
                    chart={"type": "scatter", "points": sample[[x, y]].to_numpy().tolist(),
                           "trend": [[x0, intercept + slope * x0], [x1, intercept + slope * x1]],
                           "x_label": x, "y_label": y, "x_unit": self.unit(x), "unit": self.unit(y)},
                    facts=facts,
                ))

    # ---------------------------------------------------------------- associations
    def associations(self):
        cats = [c for c in self.prof.categories if 2 <= self.prof.columns[c].n_unique <= 30]
        df = self.df
        for i, a in enumerate(cats):
            for b in cats[i + 1:]:
                la, lb = self._levels(a)[:8], self._levels(b)[:8]
                if len(la) < 2 or len(lb) < 2:
                    continue
                sub = df[df[a].isin(la) & df[b].isin(lb)]
                tab = pd.crosstab(sub[a], sub[b])
                if tab.shape[0] < 2 or tab.shape[1] < 2:
                    continue
                chi2, p, dof, exp = stats.chi2_contingency(tab)
                if (exp >= 5).mean() < 0.8:
                    continue
                n = tab.to_numpy().sum()
                r, k = tab.shape
                phi2 = chi2 / n
                phi2c = max(0, phi2 - (k - 1) * (r - 1) / (n - 1))
                rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
                v = math.sqrt(phi2c / max(min(kc - 1, rc - 1), 1e-9))
                # biggest "lift": a value of b that is over-represented in a level of a
                share_in = tab.div(tab.sum(axis=1), axis=0)
                overall = tab.sum(axis=0) / n
                lift = share_in - overall
                ai, bi = np.unravel_index(np.argmax(lift.to_numpy()), lift.shape)
                la_, lb_ = str(tab.index[ai]), str(tab.columns[bi])
                col_share = share_in.iloc[:, bi]
                facts = {"column_a": a, "column_b": b, "group": la_, "value": lb_,
                         "share_in_group": fmt.pct(share_in.iloc[ai, bi]), "share_overall": fmt.pct(overall.iloc[bi])}
                self.add(Candidate(
                    kind="association", section="groups", columns=[a, b], p=float(p), strength=min(1.0, v * 1.5),
                    passes_effect=v >= 0.2, test="Chi-square test of independence", effect_text=f"Cramer's V = {v:.2f}",
                    n=int(n), title=f"{la_} leans toward {lb_}",
                    headline=f"{fmt.pct(share_in.iloc[ai, bi]).capitalize()} of {la_} rows are {lb_}, compared with {fmt.pct(overall.iloc[bi])} overall.",
                    explanation=(f"{a} and {b} aren't independent: knowing one tells you something about the other. "
                                 f"The clearest example is {la_}, where {lb_} shows up much more often than usual."),
                    ideas=[f"If you target {la_}, lead with {lb_}: it's what that group already leans toward.",
                           f"Ask why {lb_} is less common in the other groups. There may be an opportunity there."],
                    chart={"type": "bar", "categories": [str(x) for x in col_share.sort_values(ascending=False).index],
                           "values": col_share.sort_values(ascending=False).tolist(), "unit": {"kind": "share"},
                           "highlight": [0], "value_label": f"Share that is {lb_}",
                           "reference": {"value": float(overall.iloc[bi]), "label": "Overall"}},
                    facts=facts,
                ))
        # single-category distribution (mainly useful when there are no numbers)
        if not self.prof.measures:
            for c in self.prof.categories:
                vc = df[c].value_counts()
                k = len(vc)
                if k < 3 or vc.sum() < 20:
                    continue
                res = stats.chisquare(vc.to_numpy())
                w = math.sqrt(res.statistic / vc.sum())
                top = str(vc.index[0])
                share = vc.iloc[0] / vc.sum()
                shown = vc.iloc[:8]
                self.add(Candidate(
                    kind="mix", section="composition", columns=[c], p=float(res.pvalue), strength=min(1.0, w),
                    passes_effect=w >= 0.3 and share >= 1.5 / k, test="Chi-square goodness-of-fit test",
                    effect_text=f"Cohen's w = {w:.2f}", n=int(vc.sum()), title=f"Most {c} is {top}",
                    headline=f"{top} makes up {fmt.pct(share)} of all rows, the biggest share of any {c}.",
                    explanation=f"If every {c} was equally common, each would have about {fmt.pct(1 / k)}. {top} is far above that.",
                    ideas=[f"Make sure {top} gets the attention its size deserves.",
                           "Check whether the smaller groups are small by choice or by accident."],
                    chart={"type": "bar", "categories": [str(x) for x in shown.index], "values": shown.astype(float).tolist(),
                           "unit": None, "highlight": [0], "value_label": "Rows"},
                    facts={"column": c, "top": top, "share": fmt.pct(share), "groups": str(k)},
                ))

    # ---------------------------------------------------------------- outliers
    def outliers(self):
        df = self.df
        id_col = next(iter(self.prof.by_role("id")), None)
        for m in self.prof.measures:
            s = df[m].dropna()
            if len(s) < 30:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr <= 0:
                continue
            # Start with the classic 3 x IQR rule; if that flags too many rows, the data is
            # just naturally spread out, so widen the fence until only the true oddballs remain.
            out, mult = None, None
            for mult in (3, 5, 8, 12):
                hi_fence, lo_fence = q3 + mult * iqr, q1 - mult * iqr
                cand = s[(s > hi_fence) | (s < lo_fence)]
                if 0 < len(cand) <= max(2, min(25, int(0.005 * len(s)))):
                    out = cand
                    break
                if len(cand) == 0:
                    break
            if out is None:
                continue
            k = len(out)
            med = float(s.median())
            extreme = out.abs().max()
            hi_side = (out > hi_fence).sum() >= (out < lo_fence).sum()
            ratio = extreme / abs(med) if med else float("inf")
            notable = ratio >= 3
            top = out.sort_values(ascending=not hi_side).head(10)
            labels = [_label(df.at[i, id_col]) if id_col else f"Row {i + 1}" for i in top.index]
            col = self.prof.columns[m]
            share_txt = ""
            facts = {"metric": m, "count": str(k), "typical": self.v(med, m),
                     "most_extreme": self.v(float(top.iloc[0]), m)}
            if col.additive and s.sum() > 0 and (s >= 0).all():
                share = out.sum() / s.sum()
                share_txt = f" Together they add up to {fmt.pct(share)} of all {m}."
                facts["share_of_total"] = fmt.pct(share)
            rows_word = "row has" if k == 1 else "rows have"
            self.add(Candidate(
                kind="outliers", section="surprises", columns=[m], p=None,
                strength=min(1.0, math.log10(max(ratio, 1)) / 2) if math.isfinite(ratio) else 1.0,
                passes_effect=notable, test=f"Tukey far-out fences ({mult} x IQR)", effect_text=f"largest is {ratio:.1f}x the median",
                n=len(s), measure=m, title=f"A few {m} values are way off the charts" if hi_side else f"A few {m} values are unusually low",
                headline=f"{k} {rows_word} an unusually {'high' if hi_side else 'low'} {m}: up to {self.v(float(top.iloc[0]), m)}, when a typical value is {self.v(med, m)}.",
                explanation=(f"Most {m} values sit in a fairly narrow range, but these are far outside it.{share_txt} "
                             "They could be special cases (big deals, VIP customers) or simple typing mistakes."),
                ideas=["Look at these rows one by one: are they real, or a typo like an extra zero?",
                       "If they're real, learn what made them so different. That could be worth repeating."],
                chart={"type": "bar", "categories": labels, "values": top.astype(float).tolist(), "unit": self.unit(m),
                       "highlight": list(range(len(labels))), "value_label": m, "accent": "attention",
                       "reference": {"value": med, "label": "Typical"}},
                facts=facts, rows=frozenset(out.index), key=("outliers", m),
            ))

    # ---------------------------------------------------------------- drivers
    def drivers(self):
        main = self.prof.main_metric
        if not main:
            return
        links = {}
        for c in self.cands:
            if c.q is None or c.q >= ALPHA or not c.passes_effect:
                continue
            if c.kind in ("group", "correlation") and main in c.columns:
                other = [x for x in c.columns if x != main][0]
                links[other] = max(links.get(other, 0), c.strength)
            if c.kind == "rhythm" and c.measure == main:
                links["Day of the week" if c.facts.get("pattern") == "day of the week" else "Time of year"] = c.strength
        if len(links) < 2:
            return
        ordered = sorted(links.items(), key=lambda kv: kv[1], reverse=True)[:8]
        names = [k for k, _ in ordered]
        words = ["strong" if v >= 0.7 else "clear" if v >= 0.45 else "moderate" for _, v in ordered]
        self.cands.append(Candidate(
            kind="drivers", section="big-picture", columns=[main] + names, p=None, strength=1.0, passes_effect=True,
            test="Summary of the tests below", effect_text="strength scaled 0 to 1", n=len(self.df), measure=main,
            title=f"What {main} depends on most",
            headline=f"Out of everything I tested, {names[0]} has the biggest connection to {main}" + (f", followed by {names[1]}." if len(names) > 1 else "."),
            explanation=(f"I checked every column against {main}. These are the ones with a real, proven link, longest bar first. "
                         f"Columns that aren't listed didn't show a reliable connection."),
            ideas=[f"Focus first on {names[0]}: it's the lever most connected to {main}.",
                   "Use the chapters below to see exactly how each one plays out."],
            chart={"type": "drivers", "categories": names, "highlight": [0], "values": [v for _, v in ordered], "words": words,
                   "value_label": f"Connection to {main}"},
            facts={"metric": main, "top_driver": names[0], "drivers_in_order": ", ".join(names)},
        ))


# ------------------------------------------------------------------ selection

def confidence(c: Candidate) -> dict:
    if c.kind == "drivers":
        return {"level": "high", "label": "Proven links only",
                "how": "Only columns whose link passed the statistical checks in this report are shown here."}
    if c.p is None:
        if c.kind == "outliers":
            mult = c.test.split("(")[-1].split(" x")[0] if "(" in c.test else "3"
            how = (f"These rows sit more than {mult} times the 'usual spread' (interquartile range) beyond the middle half "
                   "of the data. That's a strict, standard rule for spotting extreme values.")
        else:
            how = "This stands far outside the normal ups and downs around it, using a strict median-based check."
        return {"level": "high", "label": "Exact from your data", "how": how}
    q = c.q if c.q is not None else c.p
    if q < 0.001 and c.n >= 30:
        level, label = "high", "Very sure"
    elif q < 0.01:
        level, label = "medium", "Pretty sure"
    else:
        level, label = "medium", "Fairly sure"
    how = (f"I checked this with a {c.test}. If there were really no pattern, a result this strong would show up "
           f"{fmt.chance_phrase(q)} by pure chance, even after accounting for every other check I ran.")
    return {"level": level, "label": label, "how": how}


def _merge_spike(trend: Candidate, spike: Candidate) -> None:
    f = spike.facts
    i = f["_index"]
    hl = trend.chart.setdefault("highlight", [])
    hl[:] = [h for h in hl if h["index"] != i]
    hl.append({"index": i, "label": "Unusual"})
    trend.chart["emphasize_point"] = True
    trend.explanation += (f" One {trend.facts.get('period', 'period')} stands out: {f['period']} was {f['value']}, "
                          f"far {'above' if f['direction'] == 'higher' else 'below'} the usual {f['usual_value']} around then. "
                          "It's worth checking what happened.")
    trend.facts["unusual_period"] = f"{f['period']} ({f['value']} vs usual {f['usual_value']})"


def select(cands: list[Candidate], prof: Profile, max_n: int = MAX_INSIGHTS) -> list[Candidate]:
    ok = [c for c in cands if c.passes_effect and (c.p is None or (c.q is not None and c.q < ALPHA))]
    main = prof.main_metric
    for c in ok:
        s = c.strength * KIND_WEIGHT.get(c.kind, 0.7)
        if main and main in c.columns:
            s *= 1.6
        if c.q is not None:
            s *= 1.0 + min(0.3, -math.log10(max(c.q, 1e-300)) / 40)
        c.score = s
    ok.sort(key=lambda c: c.score, reverse=True)
    chosen: list[Candidate] = []
    use: dict[str, int] = {}
    pairs: set[frozenset] = set()
    pool = list(ok)
    keys: set[tuple] = set()
    while pool and len(chosen) < max_n:
        def adj(c):
            pen = 1.0
            for col in c.columns:
                if col != main and col not in prof.times:
                    pen *= 0.7 ** use.get(col, 0)
            if frozenset(c.columns) in pairs:
                pen *= 0.35
            if c.key and c.key in keys:
                pen *= 0.3  # same story told with a different number
            if sum(1 for x in chosen if x.kind == c.kind) >= 2:
                pen *= 0.6
            return c.score * pen
        best = max(pool, key=adj)
        pool.remove(best)
        # A spike on a line we already show becomes a note on that chart, not its own chapter.
        if best.kind in ("spike", "trend"):
            other_kind = "trend" if best.kind == "spike" else "spike"
            twin = next((x for x in chosen if x.kind == other_kind and x.columns == best.columns), None)
            if twin is not None:
                trend, spike = (twin, best) if best.kind == "spike" else (best, twin)
                _merge_spike(trend, spike)
                if best.kind == "spike":
                    continue
                chosen.remove(spike)
        if best.rows and any(x.rows and len(best.rows & x.rows) >= 0.5 * len(best.rows) for x in chosen):
            continue  # the same odd rows, already shown
        chosen.append(best)
        if best.kind not in ("trend", "spike", "rhythm"):
            pairs.add(frozenset(best.columns))
        if best.key:
            keys.add(best.key)
        if best.kind != "drivers":
            for col in best.columns:
                use[col] = use.get(col, 0) + 1
    chosen.sort(key=lambda c: (SECTION_ORDER.get(c.section, 99), -c.score))
    return chosen
