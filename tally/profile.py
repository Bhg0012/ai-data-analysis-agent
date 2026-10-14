"""Working out what each column *is* (a date, a money amount, a category...)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ID_NAME = re.compile(
    r"(^id$|^#$|[\s_-]id$|^id[\s_-]|\bid\b|identifier|uuid|guid|\bkey$|"
    r"(order|invoice|transaction|txn|record|row|ticket|receipt|reference|ref|account|customer|employee|sku|serial)[\s_-]*(no|num|number|#|code)\b|"
    r"phone|zip|postal|postcode|e-?mail)",
    re.I,
)
GEO_NAME = re.compile(r"^(lat|latitude|lon|lng|long|longitude)$", re.I)
YEAR_NAME = re.compile(r"^(year|yr|fiscal year|fy)$", re.I)
NON_ADDITIVE = re.compile(
    r"(price|\brates?\b|ratio|percent|pct|%|score|rating|\bage\b|avg|average|\bmean\b|median|margin|"
    r"temperature|\btemp\b|satisfaction|\bnps\b|\bindex\b|probability|\bshare\b|\bper\b|latitude|longitude|"
    r"duration|\bdays\b|\bhours\b|\bminutes\b|weight|height|\bsize\b|\blevel\b|\bgrade\b|\brank\b|stars)",
    re.I,
)
ADDITIVE = re.compile(
    r"(sales|revenue|amount|total|cost|profit|spend|quantity|qty|units|count|volume|income|"
    r"expense|sold|orders|visits|clicks|impressions|sessions|downloads|fee|tax|budget|value|"
    r"gmv|payment|paid|earnings|turnover|loss|deposits|leads|signups|conversions|views|calls|"
    r"tickets|bookings|hires|donations|subscribers)",
    re.I,
)
MAIN_METRIC_PRIORITY = [
    r"profit", r"revenue", r"sales", r"income", r"amount", r"total", r"salary|wage|pay\b|compensation",
    r"spend|cost",
    r"conversion", r"score|rating|satisfaction", r"quantity|units|qty", r"price",
]


@dataclass
class Column:
    name: str
    role: str  # measure | category | time | id | text | constant | geo
    unit: dict | None = None
    additive: bool = False
    n_unique: int = 0
    missing: int = 0
    is_integer: bool = False
    detail: dict = field(default_factory=dict)

    @property
    def agg(self) -> str:
        return "sum" if self.additive else "mean"


@dataclass
class Profile:
    columns: dict[str, Column]
    n_rows: int
    main_metric: str | None = None

    def by_role(self, role: str) -> list[str]:
        return [c.name for c in self.columns.values() if c.role == role]

    @property
    def measures(self) -> list[str]:
        return self.by_role("measure")

    @property
    def categories(self) -> list[str]:
        return self.by_role("category")

    @property
    def times(self) -> list[str]:
        return self.by_role("time")


def classify(df: pd.DataFrame, units: dict[str, dict], context: str = "") -> Profile:
    n = len(df)
    cols: dict[str, Column] = {}
    for name in df.columns:
        s = df[name]
        nonnull = s.dropna()
        nu = int(nonnull.nunique())
        col = Column(name=name, role="text", unit=units.get(name), n_unique=nu, missing=int(s.isna().sum()))
        if nu <= 1:
            col.role = "constant"
        elif pd.api.types.is_datetime64_any_dtype(s):
            col.role = "time"
            col.detail = {"min": nonnull.min(), "max": nonnull.max()}
        elif pd.api.types.is_numeric_dtype(s):
            col.is_integer = bool(np.all(np.mod(nonnull, 1) == 0))
            if GEO_NAME.search(name):
                col.role = "geo"
            elif YEAR_NAME.search(name) and col.is_integer and nonnull.between(1900, 2100).all():
                col.role = "time"
                col.detail = {"year_only": True, "min": nonnull.min(), "max": nonnull.max()}
            elif ID_NAME.search(name) and (nu > 0.5 * len(nonnull) or nu > 50):
                col.role = "id"
            elif col.is_integer and nu == len(nonnull) and len(nonnull) >= 20 and _is_sequence(nonnull):
                col.role = "id"
            elif col.is_integer and nu <= 12 and nonnull.min() >= 0 and ID_NAME.search(name) is None and _looks_coded(name):
                col.role = "category"
            else:
                col.role = "measure"
                col.additive = _is_additive(name, col.unit, nonnull)
        else:
            ratio = nu / max(len(nonnull), 1)
            avg_len = nonnull.astype(str).str.len().mean()
            if ID_NAME.search(name) and ratio > 0.5:
                col.role = "id"
            elif nu <= 50 and (ratio < 0.5 or len(nonnull) < 40) and avg_len < 60:
                col.role = "category"
            elif ratio > 0.9 and avg_len < 40 and len(nonnull) >= 20:
                col.role = "id"
            else:
                col.role = "text"
        cols[name] = col
    prof = Profile(columns=cols, n_rows=n)
    prof.main_metric = pick_main_metric(prof, context)
    return prof


def _is_sequence(s: pd.Series) -> bool:
    v = np.sort(s.to_numpy())
    d = np.diff(v)
    return bool(len(d) and np.all(d == d[0]))


def _looks_coded(name: str) -> bool:
    return bool(re.search(r"(code|type|group|class|segment|tier|category|level|quarter|month|weekday|day of week|region|store|zone)", name, re.I))


def _is_additive(name: str, unit: dict | None, s: pd.Series) -> bool:
    if unit and unit.get("kind") == "percent":
        return False
    if NON_ADDITIVE.search(name):
        # 'Total price' is still a sum, 'Unit price' isn't
        return bool(re.search(r"total|amount|revenue|sales", name, re.I)) and not re.search(r"unit|avg|average|\bper\b", name, re.I)
    if ADDITIVE.search(name):
        return True
    if unit and unit.get("kind") == "currency":
        return True
    return False


def pick_main_metric(prof: Profile, context: str = "") -> str | None:
    measures = prof.measures
    if not measures:
        return None
    ctx = (context or "").lower()
    if ctx:
        mentioned = [m for m in measures if m.lower() in ctx]
        if mentioned:
            return max(mentioned, key=len)
        for m in measures:
            words = [w for w in re.split(r"[\s_-]+", m.lower()) if len(w) > 3]
            if any(re.search(rf"\b{re.escape(w)}", ctx) for w in words):
                return m
    for pat in MAIN_METRIC_PRIORITY:
        hits = [m for m in measures if re.search(pat, m, re.I)]
        if hits:
            return min(hits, key=lambda m: prof.columns[m].missing)
    return min(measures, key=lambda m: prof.columns[m].missing)


def describe_columns(df: pd.DataFrame, prof: Profile) -> list[dict]:
    """A short, friendly description of each column for the report and the AI."""
    from . import fmt

    out = []
    for name, c in prof.columns.items():
        s = df[name].dropna()
        d = {"name": name, "role": c.role, "missing": c.missing, "unique": c.n_unique, "unit": c.unit}
        if c.role == "measure" and len(s):
            d["summary"] = (
                f"from {fmt.value(s.min(), c.unit)} to {fmt.value(s.max(), c.unit)}, "
                f"typically {fmt.value(s.median(), c.unit)}"
            )
            d["agg"] = c.agg
        elif c.role == "category":
            top = s.value_counts().head(5)
            d["summary"] = f"{c.n_unique} groups, like " + ", ".join(str(x) for x in top.index[:3])
            d["levels"] = [str(x) for x in s.value_counts().index[:15]]
        elif c.role == "time" and len(s):
            if c.detail.get("year_only"):
                d["summary"] = f"years {int(s.min())} to {int(s.max())}"
            else:
                d["summary"] = f"{s.min():%b %d, %Y} to {s.max():%b %d, %Y}"
        elif c.role == "id":
            d["summary"] = "an ID or label for each row (not analysed)"
        elif c.role == "text":
            d["summary"] = "free text (not analysed)"
        elif c.role == "constant":
            d["summary"] = "the same value in every row (skipped)"
        elif c.role == "geo":
            d["summary"] = "map coordinates (skipped)"
        out.append(d)
    return out
