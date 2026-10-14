"""Turning numbers into words people can read at a glance."""

from __future__ import annotations

import math


def compact(x: float) -> str:
    """1234 -> '1,234', 12900 -> '12.9K', 4_200_000 -> '4.2M'."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    a = abs(x)
    sign = "-" if x < 0 else ""
    if a >= 1e9:
        return f"{sign}{_trim(a / 1e9, 1)}B"
    if a >= 1e6:
        return f"{sign}{_trim(a / 1e6, 1)}M"
    if a >= 1e4:
        return f"{sign}{_trim(a / 1e3, 1)}K"
    if a >= 100:
        return f"{sign}{a:,.0f}"
    if a >= 10:
        return f"{sign}{_trim(a, 1)}"
    if a >= 1:
        return f"{sign}{_trim(a, 2)}"
    if a == 0:
        return "0"
    return f"{sign}{_trim(a, 3)}"


def _trim(v: float, decimals: int) -> str:
    s = f"{v:,.{decimals}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def value(x: float, unit: dict | None = None) -> str:
    """Format a value using the column's unit (currency symbol or percent)."""
    unit = unit or {}
    kind = unit.get("kind")
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if kind == "currency":
        sym = unit.get("symbol", "$")
        s = compact(abs(x))
        return f"-{sym}{s}" if x < 0 else f"{sym}{s}"
    if kind == "percent":
        return f"{_trim(x, 1)}%"
    return compact(x)


def pct(x: float, decimals: int = 0) -> str:
    """0.237 -> '24%'."""
    if x is None or math.isnan(x):
        return "n/a"
    v = x * 100
    if decimals == 0 and 0 < abs(v) < 1:
        return "less than 1%"
    return f"{_trim(v, decimals)}%"


def count(n: int) -> str:
    return f"{int(n):,}"


def times(ratio: float) -> str:
    """2.04 -> 'about 2x'."""
    if ratio >= 10:
        return f"about {ratio:.0f}x"
    return f"about {_trim(ratio, 1)}x"


def chance_phrase(p: float) -> str:
    """Plain-English version of a p-value."""
    if p < 0.001:
        return "less than 1 time in 1,000"
    if p < 0.01:
        return "less than 1 time in 100"
    return "less than 1 time in 20"


def strength_word(r: float) -> str:
    a = abs(r)
    if a >= 0.7:
        return "strong"
    if a >= 0.5:
        return "clear"
    return "moderate"


def join_words(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
