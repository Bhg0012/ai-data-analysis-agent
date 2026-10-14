"""Reading messy real-world files and tidying them up.

Every change made to the data is written to a plain-English cleaning log so
the user can see exactly what happened. Nothing is changed silently.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

SUPPORTED = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".xls", ".json"}

MISSING_MARKERS = {
    "", "na", "n/a", "nan", "null", "none", "nil", "-", "--", "---", "?",
    "#n/a", "#na", "#value!", "#ref!", "#div/0!", "#num!", "#name?", "#null!",
    "missing", "(blank)", "blank",
}
TOTAL_RE = re.compile(r"^\s*(grand\s+total|sub[\s-]?total|total|totals|sum)\s*[:.]?\s*$", re.I)
CURRENCY_SYMBOLS = "$€£¥₹"
NUM_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
DATEISH_RE = re.compile(
    r"(?:\d{1,4}[-/.]\d{1,2}(?:[-/.]\d{1,4})?)|"
    r"(?:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,4})|"
    r"(?:\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec))",
    re.I,
)
BOOL_MAP = {"yes": "Yes", "no": "No", "y": "Yes", "n": "No", "true": "Yes", "false": "No"}


class LoadError(Exception):
    """A problem we can explain to the user in plain words."""


@dataclass
class Loaded:
    df: pd.DataFrame
    units: dict[str, dict] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    raw_rows: int = 0


# ---------------------------------------------------------------- reading

def list_sheets(path: Path) -> list[dict]:
    """Return the sheets in a file with their rough size (CSV has one)."""
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xlsm", ".xls"}:
        try:
            book = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
        except Exception as e:  # noqa: BLE001 - shown to the user
            raise LoadError(f"I couldn't open this workbook ({e}).") from e
        out = []
        for name, raw in book.items():
            raw = raw.dropna(how="all").dropna(axis=1, how="all")
            out.append({"name": str(name), "rows": int(len(raw)), "columns": int(raw.shape[1])})
        return out
    return [{"name": "Data", "rows": None, "columns": None}]


def best_sheet(sheets: list[dict]) -> str:
    return max(sheets, key=lambda s: (s["rows"] or 0) * max(s["columns"] or 1, 1))["name"]


def read_raw(path: Path, sheet: str | None = None) -> pd.DataFrame:
    """Read everything as raw cells with no header so we can find the real header."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise LoadError(
            f"I can't read '{ext}' files yet. Try a CSV or Excel file (.csv, .xlsx, .xls)."
        )
    try:
        if ext in {".xlsx", ".xlsm", ".xls"}:
            if sheet is None:
                sheet = best_sheet(list_sheets(path))
            return pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        if ext == ".json":
            data = pd.read_json(path)
            header = pd.DataFrame([list(data.columns)], columns=range(data.shape[1]))
            data.columns = range(data.shape[1])
            return pd.concat([header, data.astype(object)], ignore_index=True)
        return _read_text_table(path, tab=ext == ".tsv")
    except LoadError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LoadError(f"I couldn't read this file ({e}).") from e


def _read_text_table(path: Path, tab: bool) -> pd.DataFrame:
    blob = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = blob.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise LoadError("I couldn't work out the text encoding of this file.")
    if tab:
        sep = "\t"
    else:
        sample = text[:65536]
        try:
            sep = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            sep = ","
    # rows can have different lengths (titles above the table), so size by the widest row
    width = max((len(r) for r in csv.reader(io.StringIO(text), delimiter=sep)), default=1)
    return pd.read_csv(
        io.StringIO(text), sep=sep, header=None, names=range(width), dtype=str,
        keep_default_na=False, skip_blank_lines=False,
    )


# ---------------------------------------------------------------- cleaning

def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and np.isnan(v):
        return True
    if v is pd.NaT:
        return True
    if isinstance(v, str) and v.strip().lower() in MISSING_MARKERS:
        return True
    return False


def _is_texty(v) -> bool:
    if not isinstance(v, str):
        return False
    s = v.strip()
    return bool(s) and _parse_number(s)[0] is None


def find_header_row(raw: pd.DataFrame) -> int | None:
    """Spreadsheets often start with a title or notes. Find the real header row."""
    look = raw.head(30)
    counts = look.apply(lambda r: sum(not _blank(v) for v in r), axis=1)
    if counts.empty or counts.max() == 0:
        return None
    widest = counts.max()
    for i in look.index:
        n = counts[i]
        if n < max(2, 0.6 * widest) and not (widest == 1 and n == 1):
            continue
        cells = [v for v in look.loc[i] if not _blank(v)]
        texty = sum(_is_texty(v) for v in cells)
        if texty / len(cells) >= 0.7:
            return int(i)
        # first wide row is numbers: there is no header row
        return None
    return None


def _clean_name(v, idx: int) -> str:
    if _blank(v):
        return f"Column {idx + 1}"
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d")
    s = re.sub(r"\s+", " ", str(v)).strip()
    if isinstance(v, float) and v.is_integer():
        s = str(int(v))
    return s or f"Column {idx + 1}"


def _parse_number(s: str):
    """Parse '$1,234.50', '(12)', '45%', '1.2e3'. Returns (value, flags)."""
    t = s.strip()
    flags = set()
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1].strip()
    if t.endswith("%"):
        flags.add("percent")
        t = t[:-1].strip()
    if t[:1] in "+-" and len(t) > 1 and t[1] in CURRENCY_SYMBOLS:
        neg = neg or t[0] == "-"
        t = t[1:]
    for sym in CURRENCY_SYMBOLS:
        if t.startswith(sym) or t.endswith(sym):
            flags.add("currency:" + sym)
            t = t.strip(sym).strip()
    for code in ("USD", "EUR", "GBP"):
        if t.upper().endswith(code) or t.upper().startswith(code):
            flags.add("currency:" + {"USD": "$", "EUR": "€", "GBP": "£"}[code])
            t = re.sub(code, "", t, flags=re.I).strip()
    t = t.replace(" ", "")
    if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    if not NUM_RE.match(t):
        return None, flags
    try:
        val = float(t)
    except ValueError:
        return None, flags
    return (-val if neg else val), flags


def _convert_numeric(s: pd.Series):
    """Try to read a text column as numbers. Returns (series, unit, n_failed) or None."""
    vals = s.dropna()
    if vals.empty:
        return None
    py_nums = vals.map(lambda v: isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool))
    if py_nums.all():
        return pd.to_numeric(s, errors="coerce"), None, 0
    strs = vals.astype(str)
    # decimal commas like "12,5" (common in European exports)
    if strs.str.fullmatch(r"\D{0,4}-?\d+,\d{1,2}\D{0,4}").mean() > 0.3 and not strs.str.contains(r"\.").any():
        strs = strs.str.replace(",", ".", regex=False)
    parsed = []
    flag_counts: dict[str, int] = {}
    for v in strs:
        num, flags = _parse_number(v)
        parsed.append(num)
        for f in flags:
            flag_counts[f] = flag_counts.get(f, 0) + 1
    ok = sum(p is not None for p in parsed)
    if ok == 0 or ok / len(parsed) < 0.95:
        return None
    out = pd.Series(np.nan, index=s.index, dtype=float)
    out.loc[vals.index] = [np.nan if p is None else p for p in parsed]
    unit = None
    if flag_counts.get("percent", 0) >= 0.5 * ok:
        unit = {"kind": "percent"}
    else:
        cur = max((f for f in flag_counts if f.startswith("currency:")), key=flag_counts.get, default=None)
        if cur and flag_counts[cur] >= 0.5 * ok:
            unit = {"kind": "currency", "symbol": cur.split(":", 1)[1]}
    return out, unit, len(parsed) - ok


def _convert_datetime(s: pd.Series):
    vals = s.dropna()
    if vals.empty:
        return None
    is_dt = vals.map(lambda v: isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "year") and hasattr(v, "month"))
    if is_dt.mean() >= 0.9:
        return pd.to_datetime(s.where(s.map(lambda v: not isinstance(v, str))), errors="coerce")
    strs = vals.astype(str).str.strip()
    if strs.str.contains(DATEISH_RE).mean() < 0.9:
        return None
    first = strs.str.extract(r"^(\d{1,2})[/.-](\d{1,2})[/.-]\d{2,4}")
    dayfirst = False
    if not first.dropna().empty:
        a = pd.to_numeric(first[0], errors="coerce")
        b = pd.to_numeric(first[1], errors="coerce")
        dayfirst = bool((a > 12).any() and not (b > 12).any())
    try:
        out = pd.to_datetime(s.astype("string"), errors="coerce", format="mixed", dayfirst=dayfirst)
    except (ValueError, TypeError):
        out = pd.to_datetime(s.astype("string"), errors="coerce", dayfirst=dayfirst)
    if out.notna().sum() / len(vals) < 0.9:
        return None
    return out


def clean(raw: pd.DataFrame) -> Loaded:
    notes: list[str] = []
    raw = raw.copy()
    raw_rows = len(raw)

    raw = raw.dropna(how="all")
    raw = raw.loc[:, ~raw.apply(lambda c: c.map(_blank).all())]
    raw = raw.loc[~raw.apply(lambda r: r.map(_blank).all(), axis=1)]
    if raw.empty:
        raise LoadError("This file looks empty. I couldn't find any data in it.")

    h = find_header_row(raw.reset_index(drop=True))
    raw = raw.reset_index(drop=True)
    if h is None:
        names = [f"Column {i + 1}" for i in range(raw.shape[1])]
        body = raw
        notes.append("The file had no header row, so I named the columns Column 1, Column 2, and so on.")
    else:
        names = [_clean_name(v, i) for i, v in enumerate(raw.iloc[h])]
        body = raw.iloc[h + 1:]
        if h > 0:
            notes.append(f"Skipped {h} line{'s' if h != 1 else ''} above the table (titles or notes) to find the real column names.")

    seen: dict[str, int] = {}
    unique_names = []
    for n in names:
        if n in seen:
            seen[n] += 1
            unique_names.append(f"{n} ({seen[n]})")
        else:
            seen[n] = 1
            unique_names.append(n)
    body = body.copy()
    body.columns = unique_names
    body = body.reset_index(drop=True)

    # normalise blanks and whitespace
    body = body.apply(lambda c: c.map(lambda v: np.nan if _blank(v) else (re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v)))
    body = body.dropna(how="all")

    # remove total / subtotal rows so nothing is counted twice
    def is_total_row(r) -> bool:
        texts = [v for v in r if isinstance(v, str)]
        return any(TOTAL_RE.match(t) for t in texts[:3])
    total_mask = body.apply(is_total_row, axis=1) if len(body) else pd.Series(dtype=bool)
    n_total = int(total_mask.sum()) if len(total_mask) else 0
    if n_total:
        body = body.loc[~total_mask]
        notes.append(f"Removed {n_total} 'Total' row{'s' if n_total != 1 else ''} so nothing gets counted twice.")

    # repeated header rows (common when sheets are pasted together)
    rep = body.apply(lambda r: sum(str(v) == c for v, c in zip(r, body.columns)) >= max(2, 0.6 * len(body.columns)), axis=1) if len(body) else pd.Series(dtype=bool)
    if len(rep) and rep.sum():
        body = body.loc[~rep]
        notes.append(f"Removed {int(rep.sum())} repeated header row{'s' if rep.sum() != 1 else ''} found inside the data.")

    if body.empty:
        raise LoadError("I found column names but no rows of data underneath them.")

    units: dict[str, dict] = {}
    out = pd.DataFrame(index=body.index)
    fixed_numbers, fixed_dates, merged_case = [], [], []
    for col in body.columns:
        s = body[col]
        num = _convert_numeric(s)
        if num is not None:
            series, unit, failed = num
            out[col] = series
            if unit:
                units[col] = unit
            if s.dropna().map(lambda v: isinstance(v, str) and bool(re.search(r"[,$€£¥₹%()]|[A-Za-z]{3}$", v))).any():
                fixed_numbers.append(col)
            if failed:
                notes.append(f"In '{col}', {failed} value{'s' if failed != 1 else ''} weren't numbers, so I left {'them' if failed != 1 else 'it'} blank.")
            continue
        dt = _convert_datetime(s)
        if dt is not None:
            out[col] = dt
            if s.dropna().map(lambda v: isinstance(v, str)).any():
                fixed_dates.append(col)
            continue
        text = s.map(lambda v: v if _blank(v) else str(v))
        low = text.dropna().str.lower()
        if not low.empty and set(low.unique()) <= set(BOOL_MAP):
            out[col] = text.map(lambda v: BOOL_MAP.get(v.lower()) if isinstance(v, str) else v)
            continue
        # merge 'north' / 'North' / 'NORTH' into the most common spelling
        if not low.empty and low.nunique() < text.dropna().nunique():
            canon = text.dropna().groupby(low).agg(
                lambda x: max(x.value_counts().items(), key=lambda kv: (kv[1], kv[0][:1].isupper(), not kv[0].isupper()))[0])
            text = text.map(lambda v: canon[v.lower()] if isinstance(v, str) else v)
            merged_case.append(col)
        out[col] = text

    if fixed_numbers:
        notes.append(f"Turned text like '$1,200' or '45%' into real numbers in {_names(fixed_numbers)}.")
    if fixed_dates:
        notes.append(f"Recognised dates in {_names(fixed_dates)}.")
    if merged_case:
        notes.append(f"Merged spellings that only differed by capital letters (like 'north' and 'North') in {_names(merged_case)}.")

    # Exact copies only look suspicious when rows are normally unique (e.g. there's an ID,
    # a timestamp or a precise amount). In a table of a few categories, repeats are expected.
    dupes = int(out.duplicated().sum())
    rows_unique = any(out[c].nunique() > 0.5 * len(out) for c in out.columns) if len(out) else False
    if dupes and rows_unique:
        notes.append(
            f"{dupes} row{'s are' if dupes != 1 else ' is'} an exact copy of another row. "
            "I kept them in case they're real, but you may want to double-check."
        )
    out = out.reset_index(drop=True)
    return Loaded(df=out, units=units, notes=notes, raw_rows=raw_rows)


def _names(cols: list[str]) -> str:
    quoted = [f"'{c}'" for c in cols]
    if len(quoted) > 4:
        return ", ".join(quoted[:3]) + f" and {len(quoted) - 3} more columns"
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + " and " + quoted[-1]


def load(path: Path, sheet: str | None = None) -> Loaded:
    return clean(read_raw(path, sheet))
