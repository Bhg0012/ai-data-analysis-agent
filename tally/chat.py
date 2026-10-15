"""'Ask Tally' - questions about the data, answered with real calculations.

The AI is given a few calculator tools that run on the actual table. It must use
them for any number it says; answers that contain numbers the tools never
produced are rejected and retried.
"""

from __future__ import annotations

import difflib
import json

import numpy as np
import pandas as pd
from scipy import stats

from . import fmt
from .narrate import allowed_numbers, numbers_ok, style, tidy
from .ollama import Ollama, OllamaError

OPS = {"equals", "not_equals", "greater_than", "less_than", "contains", "between"}

TOOLS = [
    {"type": "function", "function": {
        "name": "group_summary",
        "description": "Summarise a number column split by a category (or by month/year for a date column). "
                       "Use for questions like 'which store sells the most' or 'revenue by month'.",
        "parameters": {"type": "object", "properties": {
            "measure": {"type": "string", "description": "Number column to summarise, or 'rows' to count rows."},
            "by": {"type": "string", "description": "Column to group by."},
            "statistic": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max"]},
            "filters": {"type": "array", "description": "Optional filters.", "items": {"type": "object", "properties": {
                "column": {"type": "string"}, "op": {"type": "string", "enum": sorted(OPS)},
                "value": {"type": "string"}, "value2": {"type": "string"}}}},
        }, "required": ["measure", "by", "statistic"]}}},
    {"type": "function", "function": {
        "name": "column_summary",
        "description": "Describe one column: range, average, total, most common values, missing values.",
        "parameters": {"type": "object", "properties": {
            "column": {"type": "string"},
            "filters": {"type": "array", "items": {"type": "object", "properties": {
                "column": {"type": "string"}, "op": {"type": "string", "enum": sorted(OPS)},
                "value": {"type": "string"}, "value2": {"type": "string"}}}},
        }, "required": ["column"]}}},
    {"type": "function", "function": {
        "name": "count_rows",
        "description": "Count rows that match filters, and what share of all rows that is.",
        "parameters": {"type": "object", "properties": {
            "filters": {"type": "array", "items": {"type": "object", "properties": {
                "column": {"type": "string"}, "op": {"type": "string", "enum": sorted(OPS)},
                "value": {"type": "string"}, "value2": {"type": "string"}}}},
        }, "required": ["filters"]}}},
    {"type": "function", "function": {
        "name": "relationship",
        "description": "Check whether two columns are related, with a proper statistical test.",
        "parameters": {"type": "object", "properties": {
            "column_a": {"type": "string"}, "column_b": {"type": "string"}},
            "required": ["column_a", "column_b"]}}},
]


class ToolError(Exception):
    pass


class DataTools:
    def __init__(self, df: pd.DataFrame, prof):
        self.df = df
        self.prof = prof
        self.last_chart: dict | None = None
        self.trace: list[str] = []

    def col(self, name: str) -> str:
        if name in self.df.columns:
            return name
        lower = {c.lower(): c for c in self.df.columns}
        if name and name.lower() in lower:
            return lower[name.lower()]
        hit = difflib.get_close_matches(name or "", list(self.df.columns), n=1, cutoff=0.6)
        if hit:
            return hit[0]
        hit = difflib.get_close_matches((name or "").lower(), list(lower), n=1, cutoff=0.6)
        if hit:
            return lower[hit[0]]
        raise ToolError(f"There's no column called '{name}'. Columns are: {', '.join(self.df.columns)}")

    def unit(self, c):
        col = self.prof.columns.get(c)
        return col.unit if col else None

    def filtered(self, filters) -> pd.DataFrame:
        df = self.df
        for f in filters or []:
            c = self.col(f.get("column", ""))
            op = f.get("op", "equals")
            val = f.get("value")
            s = df[c]
            if pd.api.types.is_numeric_dtype(s) and op in ("equals", "not_equals", "greater_than", "less_than", "between"):
                v = float(str(val).replace(",", "").replace("$", ""))
            elif pd.api.types.is_datetime64_any_dtype(s) and op != "contains":
                v = pd.to_datetime(val)
            else:
                v = str(val)
            if op == "equals":
                m = s.astype(str).str.lower() == v.lower() if isinstance(v, str) else s == v
            elif op == "not_equals":
                m = s.astype(str).str.lower() != v.lower() if isinstance(v, str) else s != v
            elif op == "greater_than":
                m = s > v
            elif op == "less_than":
                m = s < v
            elif op == "between":
                v2 = f.get("value2")
                v2 = float(v2) if pd.api.types.is_numeric_dtype(s) else pd.to_datetime(v2)
                m = (s >= v) & (s <= v2)
            elif op == "contains":
                m = s.astype(str).str.contains(str(val), case=False, regex=False)
            else:
                raise ToolError(f"Unknown filter '{op}'")
            df = df[m.fillna(False)]
        return df

    # ------------------------------------------------------------ tools
    def group_summary(self, measure, by, statistic="sum", filters=None):
        df = self.filtered(filters)
        by = self.col(by)
        key = df[by]
        if pd.api.types.is_datetime64_any_dtype(key):
            span = (key.max() - key.min()).days if key.notna().any() else 0
            key = key.dt.to_period("Y" if span > 365 * 4 else "M").astype(str)
        if measure in ("rows", "count", "", None) or statistic == "count":
            g = df.groupby(key).size().astype(float)
            mname, unit, statistic = "rows", None, "count"
        else:
            m = self.col(measure)
            if not pd.api.types.is_numeric_dtype(df[m]):
                raise ToolError(f"'{m}' isn't a number column.")
            g = df.groupby(key)[m].agg(statistic)
            mname, unit = m, self.unit(m)
        g = g.dropna()
        is_time = pd.api.types.is_datetime64_any_dtype(df[by])
        g = g.sort_index() if is_time else g.sort_values(ascending=False)
        shown = g.head(25 if is_time else 15)
        self.trace.append(f"{statistic} of {mname} by {by}" + (f" (filtered: {_ftxt(filters)})" if filters else ""))
        self.last_chart = {"type": "line" if is_time else "bar", "categories": [str(i) for i in shown.index],
                           "x": [str(i) for i in shown.index], "y": shown.tolist(), "values": shown.tolist(),
                           "unit": unit, "highlight": [] if is_time else [0],
                           "value_label": f"{statistic} of {mname}", "y_label": f"{statistic} of {mname}",
                           "keep_order": is_time}
        return {"statistic": statistic, "measure": mname, "by": by, "groups_total": int(len(g)),
                "results": {str(k): fmt.value(float(v), unit) for k, v in shown.items()},
                "note": f"showing {len(shown)} of {len(g)} groups" if len(g) > len(shown) else ""}

    def column_summary(self, column, filters=None):
        df = self.filtered(filters)
        c = self.col(column)
        s = df[c]
        u = self.unit(c)
        self.trace.append(f"summary of {c}" + (f" (filtered: {_ftxt(filters)})" if filters else ""))
        out = {"column": c, "rows": int(len(s)), "missing": int(s.isna().sum())}
        s = s.dropna()
        if pd.api.types.is_numeric_dtype(s) and len(s):
            out.update({"total": fmt.value(float(s.sum()), u), "average": fmt.value(float(s.mean()), u),
                        "median": fmt.value(float(s.median()), u), "min": fmt.value(float(s.min()), u),
                        "max": fmt.value(float(s.max()), u)})
        elif pd.api.types.is_datetime64_any_dtype(s) and len(s):
            out.update({"earliest": f"{s.min():%b %d, %Y}", "latest": f"{s.max():%b %d, %Y}"})
        else:
            vc = s.value_counts()
            out.update({"distinct_values": int(len(vc)),
                        "most_common": {str(k): f"{int(v)} rows ({fmt.pct(v / max(len(s), 1))})" for k, v in vc.head(8).items()}})
        return out

    def count_rows(self, filters=None):
        df = self.filtered(filters)
        self.trace.append(f"count rows where {_ftxt(filters)}")
        return {"matching_rows": fmt.count(len(df)), "all_rows": fmt.count(len(self.df)),
                "share": fmt.pct(len(df) / max(len(self.df), 1), 1)}

    def relationship(self, column_a, column_b):
        a, b = self.col(column_a), self.col(column_b)
        df = self.df[[a, b]].dropna()
        num_a, num_b = (pd.api.types.is_numeric_dtype(df[x]) for x in (a, b))
        self.trace.append(f"relationship between {a} and {b}")
        if len(df) < 10:
            return {"result": "Not enough rows with both values to test this."}
        if num_a and num_b:
            rho, p = stats.spearmanr(df[a], df[b])
            related = p < 0.05 and abs(rho) >= 0.2
            return {"test": "Spearman correlation", "related": bool(related), "direction": "same" if rho > 0 else "opposite",
                    "strength": fmt.strength_word(rho) if related else "none/weak", "rows": fmt.count(len(df)),
                    "chance_of_fluke": fmt.chance_phrase(p) if p < 0.05 else "too likely to be chance"}
        if num_a != num_b:
            cat, num = (b, a) if num_a else (a, b)
            levels = df[cat].value_counts()
            levels = levels[levels >= 3].index[:12]
            groups = [df.loc[df[cat] == lv, num] for lv in levels]
            if len(groups) < 2:
                return {"result": "Not enough groups to compare."}
            h, p = stats.kruskal(*groups)
            means = {str(lv): fmt.value(float(g.mean()), self.unit(num)) for lv, g in zip(levels, groups)}
            return {"test": "Kruskal-Wallis", "related": bool(p < 0.05), "average_by_group": means,
                    "chance_of_fluke": fmt.chance_phrase(p) if p < 0.05 else "too likely to be chance"}
        tab = pd.crosstab(df[a], df[b])
        chi2, p, *_ = stats.chi2_contingency(tab)
        v = float(np.sqrt(chi2 / tab.to_numpy().sum() / max(min(tab.shape) - 1, 1)))
        return {"test": "Chi-square", "related": bool(p < 0.05 and v >= 0.1), "strength": f"Cramer's V {v:.2f}",
                "chance_of_fluke": fmt.chance_phrase(p) if p < 0.05 else "too likely to be chance"}

    @property
    def steps(self) -> list[str]:
        return list(dict.fromkeys(self.trace))

    def call(self, name: str, args: dict):
        fn = {"group_summary": self.group_summary, "column_summary": self.column_summary,
              "count_rows": self.count_rows, "relationship": self.relationship}.get(name)
        if not fn:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**{k: v for k, v in (args or {}).items() if v not in (None, "")})
        except ToolError as e:
            return {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"That calculation failed: {e}"}


def _ftxt(filters) -> str:
    return ", ".join(f"{f.get('column')} {f.get('op', 'equals').replace('_', ' ')} {f.get('value')}" for f in filters or [])


def answer(client: Ollama, model: str, df: pd.DataFrame, prof, report: dict, history: list[dict], question: str) -> dict:
    tools = DataTools(df, prof)
    cols = "\n".join(
        f"- {c['name']} ({c['role']}{', ' + c['summary'] if c.get('summary') else ''})"
        for c in report["dataset"]["column_list"]
    )
    findings = "\n".join(f"- {i['headline']}" for i in report["insights"])
    system = (
        style() + "\n\nYou are answering questions about the user's spreadsheet. "
        "ALWAYS call a tool to get any number before you mention it. Never guess or calculate numbers yourself. "
        "If the data can't answer the question, say so plainly and suggest what data would help. "
        "Answer in 1 to 4 short sentences. If you mention a relationship, remember it's not proof of cause.\n\n"
        f"The table has {len(df)} rows. Columns:\n{cols}\n\n"
        f"Findings already proven in the report:\n{findings or '- none'}"
        + (f"\n\nWhat the user told us about the data: {report['context']}" if report.get("context") else "")
    )
    msgs = [{"role": "system", "content": system}]
    for h in history[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            msgs.append({"role": h["role"], "content": str(h["content"])[:2000]})
    msgs.append({"role": "user", "content": question})

    tool_text: list[str] = [findings, str(len(df))]
    use_tools = True
    for _ in range(6):
        try:
            msg = client.chat(model, msgs, tools=TOOLS if use_tools else None, temperature=0.1)
        except OllamaError as e:
            if use_tools and "tool" in str(e).lower():
                use_tools = False  # this model can't use tools: answer from the report only
                continue
            raise
        calls = msg.get("tool_calls") or []
        if not calls:
            text = tidy(msg.get("content", ""))
            allowed = allowed_numbers(*tool_text)
            if text and not numbers_ok(text, allowed):
                msgs.append({"role": "assistant", "content": text})
                msgs.append({"role": "user", "content": (
                    "Some numbers in that answer didn't come from a tool result. Call a tool to get the exact "
                    "numbers, or answer without numbers.")})
                tool_text.append("")
                if len(msgs) > 30:
                    break
                continue
            return {"reply": text or "Sorry, I couldn't work that out.", "chart": tools.last_chart,
                    "steps": tools.steps, "verified": True}
        msgs.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": calls})
        for call in calls:
            fn = call.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            result = tools.call(fn.get("name", ""), args)
            payload = json.dumps(result, default=str)
            tool_text.append(payload)
            msgs.append({"role": "tool", "content": payload, "tool_name": fn.get("name", "")})
    return {"reply": "I couldn't get a reliable answer to that one. Try asking it a different way, "
                     "or name the column you're curious about.",
            "chart": None, "steps": tools.steps, "verified": False}
