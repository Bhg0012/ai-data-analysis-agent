"""Letting the local AI re-word findings in friendly language, safely.

The AI is only allowed to *rephrase* facts the statistics engine already proved.
Every sentence it writes goes through `numbers_ok`: if it mentions a number we
didn't give it, that sentence is thrown away and the plain template is used.
"""

from __future__ import annotations

import json
import re

from .ollama import Ollama, OllamaError

STYLE = (
    "You are Tally, a warm, sharp data analyst who explains findings to people who are NOT technical. "
    "Write like you're talking to a smart friend: short sentences, everyday words, no jargon. "
    "Never say: p-value, statistically significant, correlation coefficient, variance, regression, dataset, insight. "
    "Never use the em dash character. Use a comma, a period, or a simple hyphen instead. "
    "No emojis. No hype words like 'amazing', 'game-changer', 'unlock', 'delve', 'leverage'. "
    "ONLY use the facts you are given. Never invent or estimate a number. Copy numbers exactly as written in the facts. "
    "Ideas must be gentle suggestions ('You could...', 'It might be worth...'), never promises. "
    "Do not add any new claims, causes, or links to other columns that are not in the facts. "
    "Avoid words that claim cause and effect (drives, causes, factor, because of, leads to) unless the facts say so. "
    "Keep time periods exactly as given (for example 'from Jan 2024 to Dec 2025', not 'last year')."
)

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
        msg = client.chat(model, [{"role": "system", "content": STYLE}, {"role": "user", "content": prompt}],
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


def rewrite_insight(client: Ollama, model: str, ins: dict, context: str) -> dict:
    """Return a copy of the insight with friendlier wording where it passed the checks."""
    facts_txt = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in ins["facts"].items() if v)
    allowed = allowed_numbers(facts_txt, ins["headline"], ins["explanation"], " ".join(ins["ideas"]))
    prompt = (
        (f"What the user told us about their data: {context}\n\n" if context else "")
        + f"Finding type: {ins['kind']}\nProven facts:\n{facts_txt}\n\n"
        + f"A plain draft you can improve:\nTitle: {ins['title']}\nHeadline: {ins['headline']}\n"
        + f"Explanation: {ins['explanation']}\nIdeas: {' | '.join(ins['ideas'])}\n\n"
        + "Rewrite this for a beginner. Return JSON with:\n"
          "title: at most 7 words, plain and specific (no colon).\n"
          "headline: one sentence with the key number.\n"
          "explanation: 2 or 3 short sentences explaining what the chart shows and why it matters. Keep every point and caution from the draft (including any period that stands out).\n"
          "ideas: 1 or 2 short, practical, gentle suggestions tailored to this data (and to the user's context if given)."
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
