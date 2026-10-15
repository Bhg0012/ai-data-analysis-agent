"""Letting the local AI re-word findings in friendly language, safely.

The AI is only allowed to *rephrase* facts the statistics engine already proved.
Every sentence it writes goes through `numbers_ok`: if it mentions a number we
didn't give it, that sentence is thrown away and the plain template is used.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .ollama import Ollama, OllamaError

GUIDE = Path(__file__).resolve().parent.parent / "docs" / "DATA_STORYTELLING_GUIDE.md"

# Used only if the guide file can't be read.
FALLBACK_RULES = (
    "The reader has never seen this spreadsheet and is not comfortable with numbers or charts. "
    "They must understand each chapter within about 5 seconds.\n"
    "1. Lead with the conclusion in plain words, then the one number that proves it.\n"
    "2. Tell the reader where to look, using the chart's colors from the chart key.\n"
    "3. Explain what each column means in everyday words. Short sentences, no jargon, no em dashes.\n"
    "4. Only use the facts given. Never invent numbers, causes, or time periods."
)


def writer_rules() -> str:
    """The 'Rules for the writer' from docs/DATA_STORYTELLING_GUIDE.md, read fresh every time."""
    try:
        text = GUIDE.read_text("utf-8")
        m = re.search(r"<!-- TALLY-LLM-RULES:START -->(.*?)<!-- TALLY-LLM-RULES:END -->", text, re.S)
        if m and m.group(1).strip():
            return m.group(1).strip()
    except OSError:
        pass
    return FALLBACK_RULES


def style() -> str:
    return (
        "You are Tally, a warm, sharp data analyst. Your job is to turn each finding into something the reader "
        "understands instantly, like a friend pointing at a chart and saying exactly what it shows. "
        "Follow Tally's data storytelling rules, which are based on research about how people read charts:\n\n"
        + writer_rules()
        + "\n\nUse the column descriptions and the user's notes to work out what things mean in real life.\n"
        "EXAMPLE of bad vs good:\n"
        "BAD: 'Category has the biggest connection to Revenue, followed by Day of the week.'\n"
        "GOOD: 'What people buy matters most for how much money an order brings in. A typical merch order brings in "
        "$34.9, while a typical pastry order brings in $6.38.'"
    )


# Kept for code that imports it; the live version is style().
STYLE = style()

INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "headline": {"type": "string"},
        "explanation": {"type": "string"},
        "ideas": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "headline", "explanation", "ideas"],
}

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "intro": {"type": "string"},
        "takeaways": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "intro", "takeaways", "next_steps"],
}

NUM_TOKEN = re.compile(r"(?<![A-Za-z])[-+]?\$?\d[\d,]*(?:\.\d+)?")


def _numbers_in(text: str) -> list[float]:
    out = []
    for tok in NUM_TOKEN.findall(text or ""):
        t = tok.replace("$", "").replace(",", "")
        try:
            out.append(abs(float(t)))
        except ValueError:
            pass
    return out


def allowed_numbers(*texts: str) -> set[float]:
    nums: set[float] = set()
    for t in texts:
        for n in _numbers_in(t):
            nums.add(n)
    return nums


def numbers_ok(text: str, allowed: set[float]) -> bool:
    for n in _numbers_in(text):
        if n <= 12 and float(n).is_integer():
            continue  # small counts like "2 groups" or "top 3"
        if 1900 <= n <= 2100 and float(n).is_integer():
            if n in allowed:
                continue
            return False
        if not any(abs(n - a) <= max(0.006 * a, 0.051) for a in allowed):
            return False
    return True


def tidy(text: str) -> str:
    text = (text or "").replace("\u2014", " - ").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _ask(client: Ollama, model: str, prompt: str, schema: dict) -> dict | None:
    try:
        msg = client.chat(model, [{"role": "system", "content": style()}, {"role": "user", "content": prompt}],
                          schema=schema, temperature=0.3)
    except OllamaError:
        return None
    raw = msg.get("content") or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def rewrite_insight(client: Ollama, model: str, ins: dict, context: str, data_brief: str = "") -> dict:
    """Return a copy of the insight with friendlier wording where it passed the checks."""
    facts_txt = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in ins["facts"].items() if v)
    allowed = allowed_numbers(facts_txt, ins["headline"], ins["explanation"], " ".join(ins["ideas"]))
    key_txt = "\n".join(f"- {k['text']}" for k in ins.get("chart", {}).get("key", []))
    prompt = (
        (f"What the user told us about their data: {context}\n\n" if context else "")
        + (f"About the spreadsheet:\n{data_brief}\n\n" if data_brief else "")
        + f"Finding type: {ins['kind']}\nProven facts:\n{facts_txt}\n\n"
        + (f"Chart key (what the colors on the chart mean):\n{key_txt}\n\n" if key_txt else "")
        + f"A plain draft you must make clearer and friendlier:\nTitle: {ins['title']}\nHeadline: {ins['headline']}\n"
        + f"Explanation: {ins['explanation']}\nIdeas: {' | '.join(ins['ideas'])}\n\n"
        + "Return JSON with:\n"
          "title: at most 7 words. A plain statement of what's true (like 'Weekends bring in the most money'), not a label.\n"
          "headline: one sentence. The conclusion in everyday words, plus the key number.\n"
          "explanation: exactly 3 short sentences. (1) What the reader is looking at, using the chart colors. "
          "(2) What it means in real life, in everyday words, explaining what the columns mean. "
          "(3) Any caution from the draft (like 'this shows they move together, not that one causes the other', "
          "or a month that stands out), or why it matters.\n"
          "ideas: 1 or 2 short, practical, gentle suggestions tailored to this data and the user's notes."
    )
    out = _ask(client, model, prompt, INSIGHT_SCHEMA)
    if not out:
        return ins
    new = dict(ins)
    used_ai = False
    for key in ("title", "headline", "explanation"):
        val = tidy(str(out.get(key, "")))
        if val and numbers_ok(val, allowed) and len(val) < 600:
            new[key] = val
            used_ai = True
    ideas = [tidy(str(i)) for i in (out.get("ideas") or []) if isinstance(i, str)]
    ideas = [i for i in ideas if i and numbers_ok(i, allowed) and len(i) < 300][:2]
    if ideas:
        new["ideas"] = ideas
        used_ai = True
    new["ai_written"] = used_ai
    return new


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "clear": {"type": "boolean"},
        "problems": {"type": "array", "items": {"type": "string"}},
        "title": {"type": "string"},
        "headline": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["clear", "problems"],
}

JARGON = re.compile(
    r"\b(p-?value|statistically significant|significance|correlat\w*|coefficient|variance|regression|median|"
    r"distribution|dataset|insight|variable|metric|epsilon|kruskal|spearman|quartile|standard deviation)\b", re.I)


def readability_flags(ins: dict) -> list[str]:
    """Simple, mechanical checks that point the reviewer at obvious problems."""
    flags = []
    text = " ".join([ins["title"], ins["headline"], ins["explanation"]])
    for word in sorted({m.group(0).lower() for m in JARGON.finditer(text)}):
        flags.append(f"Uses the technical word '{word}'.")
    for sent in re.split(r"(?<=[.!?])\s+", ins["headline"] + " " + ins["explanation"]):
        if len(sent.split()) > 25:
            flags.append(f"This sentence is long ({len(sent.split())} words): '{sent[:80]}...'")
    if not re.search(r"\b(blue|gray|grey|orange|dashed|dot|dots|line|bar|bars)\b", ins["explanation"], re.I):
        flags.append("The explanation doesn't tell the reader what to look at on the chart (which color or shape).")
    return flags


def _chart_summary(chart: dict) -> str:
    t = chart.get("type")
    if t in ("bar", "drivers"):
        pairs = list(zip(chart.get("categories", []), chart.get("words") or chart.get("values", [])))[:10]
        hl = [chart["categories"][i] for i in chart.get("highlight", []) if i < len(chart.get("categories", []))]
        return f"A bar chart. Bars: {', '.join(str(c) for c, _ in pairs)}. Highlighted: {', '.join(map(str, hl)) or 'none'}."
    if t == "line":
        return f"A line chart over time, from {chart['x'][0]} to {chart['x'][-1]}."
    if t == "scatter":
        return f"A dot chart: {chart.get('x_label')} across, {chart.get('y_label')} up and down, with a trend line."
    return "A chart."


def review_insight(client: Ollama, model: str, ins: dict, context: str, data_brief: str = "") -> dict:
    """Re-read a finished chapter as a first-time reader would, and fix anything that isn't instantly clear."""
    facts_txt = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in ins["facts"].items() if v)
    allowed = allowed_numbers(facts_txt, ins["headline"], ins["explanation"])
    key_txt = "\n".join(f"- {k['text']}" for k in ins.get("chart", {}).get("key", []))
    flags = readability_flags(ins)
    prompt = (
        (f"What the user told us about their data: {context}\n\n" if context else "")
        + (f"About the spreadsheet:\n{data_brief}\n\n" if data_brief else "")
        + f"The chart: {_chart_summary(ins.get('chart', {}))}\n"
        + (f"Chart key (what the colors mean):\n{key_txt}\n" if key_txt else "")
        + f"\nProven facts:\n{facts_txt}\n\n"
        + f"The finished chapter:\nTitle: {ins['title']}\nHeadline: {ins['headline']}\nExplanation: {ins['explanation']}\n\n"
        + (f"Automatic checks found:\n- " + "\n- ".join(flags) + "\n\n" if flags else "")
        + "Now re-read this chapter slowly, as someone who has never seen this spreadsheet and is not good with numbers "
          "or charts. Ask yourself honestly:\n"
          "1. Is this easily understandable?\n"
          "2. Would anyone be able to read it and instantly know what the chart is telling them, at first glance?\n"
          "3. Does it say which color or shape on the chart to look at, and does that match the chart key?\n"
          "4. Does it explain what the columns mean in everyday words, instead of just naming them?\n"
          "5. Is every sentence short, with no technical words?\n"
          "Return JSON. Set clear to true ONLY if the answer to every question is yes. List any problems. "
          "If it is not clear, also return a fixed title (max 7 words), headline (one sentence) and explanation "
          "(3 short sentences) that solve every problem, using only the facts and copying numbers exactly."
    )
    out = _ask(client, model, prompt, REVIEW_SCHEMA)
    new = dict(ins)
    review = {"checked": True, "clear": True, "fixed": False, "problems": flags}
    if out is None:
        review["checked"] = False
        new["review"] = review
        return new
    problems = [tidy(str(p)) for p in (out.get("problems") or []) if str(p).strip()][:5]
    review["problems"] = problems or flags
    if out.get("clear") and not flags:
        new["review"] = review
        return new
    review["clear"] = False
    for key, limit in (("title", 90), ("headline", 300), ("explanation", 600)):
        val = tidy(str(out.get(key, "")))
        if val and numbers_ok(val, allowed) and len(val) < limit and val != ins[key]:
            new[key] = val
            review["fixed"] = True
    new["review"] = review
    return new


def write_story(client: Ollama, model: str, report: dict, context: str) -> dict | None:
    heads = "\n".join(f"{i + 1}. {x['headline']}" for i, x in enumerate(report["insights"]))
    if not heads:
        return None
    ds = report["dataset"]
    allowed = allowed_numbers(heads, str(ds["rows"]), str(ds["columns"]), report["story"]["intro"])
    prompt = (
        (f"What the user told us about their data: {context}\n\n" if context else "")
        + f"File: {report['file_name']} ({ds['rows']} rows, {ds['columns']} columns).\n"
        + f"Columns: {', '.join(c['name'] for c in ds['column_list'][:40])}\n\n"
        + f"Proven findings, in story order:\n{heads}\n\n"
        + "Write the opening of a short data story for a beginner. Return JSON with:\n"
          "title: a friendly, specific report title, at most 8 words, no colon.\n"
          "intro: 2 sentences that say what this data is about and what the story will show.\n"
          "takeaways: exactly 3 very short bullet points (max 14 words each), each one faithfully restating one finding above.\n"
          "next_steps: 2 or 3 gentle, practical ideas for what to do next."
    )
    out = _ask(client, model, prompt, STORY_SCHEMA)
    if not out:
        return None
    story = {}
    t = tidy(str(out.get("title", "")))
    if t and numbers_ok(t, allowed) and len(t) < 90:
        story["title"] = t
    i = tidy(str(out.get("intro", "")))
    if i and numbers_ok(i, allowed):
        story["intro"] = i
    tk = [tidy(x) for x in out.get("takeaways") or [] if isinstance(x, str)]
    tk = [x for x in tk if x and numbers_ok(x, allowed)][:3]
    if len(tk) >= 2:
        story["takeaways"] = tk
    ns = [tidy(x) for x in out.get("next_steps") or [] if isinstance(x, str)]
    ns = [x for x in ns if x and numbers_ok(x, allowed)][:3]
    if ns:
        story["next_steps"] = ns
    return story
