"""The full pipeline: file -> clean table -> proven findings -> friendly story."""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path


from . import fmt, insights, loader, narrate
from .ollama import Ollama
from .profile import classify, describe_columns


def analyze(path: Path, *, file_name: str, sheet: str | None, context: str, settings: dict,
            step=lambda *_: None, other_sheets: list[str] | None = None) -> dict:
    step("read", "Reading your file")
    loaded = loader.load(path, sheet)
    df = loaded.df

    step("profile", "Figuring out what each column means")
    prof = classify(df, loaded.units, context)

    step("stats", "Running statistical checks")
    engine = insights.Engine(df, prof, progress=lambda label, frac, nxt: step("stats", label, frac, nxt))
    cands = engine.run()
    chosen = insights.select(cands, prof)

    step("pick", "Picking the findings that really matter")
    report = build_report(df, prof, loaded, engine, cands, chosen, file_name=file_name, sheet=sheet,
                          context=context, other_sheets=other_sheets or [])

    client = Ollama(settings["ollama_url"])
    status = client.status(settings.get("model")) if settings.get("use_ai", True) else {"ready": False}
    if status.get("ready") and report["insights"]:
        model = status["model"]
        total = len(report["insights"])
        brief = data_brief(report, prof)
        step("write", "Waking up the AI model", 0.0, 0.1)
        client.warm(model)
        new = []
        for i, ins in enumerate(report["insights"]):
            step("write", f"Writing it in plain English ({i + 1} of {total})",
                 0.1 + 0.9 * i / (total + 1), 0.1 + 0.9 * (i + 1) / (total + 1))
            new.append(narrate.rewrite_insight(client, model, ins, context, brief))
        report["insights"] = new
        step("write", "Writing the story", 0.1 + 0.9 * total / (total + 1), 1.0)
        story = narrate.write_story(client, model, report, context)
        if story:
            report["story"].update(story)
            report["story"]["ai_written"] = True
        report["model"] = model
    else:
        step("write", "Writing it in plain English", 0.0, 1.0)
    step("done", "Done")
    return report


def data_brief(report: dict, prof) -> str:
    """A short description of the spreadsheet so the AI can explain what columns mean."""
    lines = [f"Each row is one {prof.row_noun} ({report['dataset']['rows']} rows)."]
    for c in report["dataset"]["column_list"]:
        if c["role"] in ("measure", "category", "time"):
            unit = c.get("unit") or {}
            u = " (money)" if unit.get("kind") == "currency" else " (a percent)" if unit.get("kind") == "percent" else ""
            if c.get("levels"):
                desc = f"{c['unique']} groups: {', '.join(c['levels'][:6])}"
            else:
                desc = c.get("summary", "")
            lines.append(f"- {c['name']}{u}: {desc}")
    return "\n".join(lines[:40])


def build_report(df, prof, loaded, engine, cands, chosen, *, file_name, sheet, context, other_sheets) -> dict:
    main = prof.main_metric
    rows, cols = df.shape
    ins = []
    for i, c in enumerate(chosen):
        ins.append({
            "id": f"i{i + 1}", "kind": c.kind, "section": c.section,
            "section_title": insights.SECTION_TITLE.get(c.section, ""),
            "title": c.title, "headline": c.headline, "explanation": c.explanation, "ideas": c.ideas,
            "chart": c.chart, "facts": {k: v for k, v in c.facts.items() if not k.startswith("_")}, "columns": c.columns,
            "confidence": insights.confidence(c),
            "stats": {"test": c.test, "p": c.p, "q": c.q, "effect": c.effect_text, "n": c.n},
            "ai_written": False,
        })

    tested = [c for c in cands if c.p is not None]
    passed = [c for c in cands if c.passes_effect and (c.p is None or (c.q is not None and c.q < insights.ALPHA))]

    kpis = [{"label": "Rows analysed", "value": fmt.count(rows), "sub": f"{cols} columns"}]
    if prof.times:
        t = df[prof.times[0]].dropna()
        if prof.columns[prof.times[0]].detail.get("year_only"):
            kpis.append({"label": "Time covered", "value": f"{int(t.max()) - int(t.min()) + 1} years", "sub": f"{int(t.min())} to {int(t.max())}"})
        else:
            kpis.append({"label": "Time covered", "value": _span(t.min(), t.max()), "sub": f"{t.min():%b %Y} to {t.max():%b %Y}"})
    if main:
        s = df[main].dropna()
        unit = prof.columns[main].unit
        if prof.columns[main].additive:
            kpis.append({"label": f"Total {main}", "value": fmt.value(float(s.sum()), unit), "sub": f"average {fmt.value(float(s.mean()), unit)} per row"})
        else:
            kpis.append({"label": f"Average {main}", "value": fmt.value(float(s.mean()), unit), "sub": f"middle value {fmt.value(float(s.median()), unit)}"})
    kpis.append({"label": "Checks run", "value": fmt.count(engine.tests_run), "sub": f"{len(chosen)} worth your time"})

    takeaways = [x["headline"] for x in ins if x["kind"] != "drivers"][:3]
    name = Path(file_name).stem.replace("_", " ").replace("-", " ").strip()
    if ins:
        intro = (f"I went through all {fmt.count(rows)} rows of {name}, ran {fmt.count(engine.tests_run)} statistical checks, "
                 f"and kept only the {len(ins)} pattern{'s' if len(ins) != 1 else ''} that are both real and big enough to matter.")
        title = f"What {name} is telling you"
        next_steps = [x["ideas"][0] for x in ins[:3] if x["ideas"]]
    else:
        intro = (f"I went through all {fmt.count(rows)} rows of {name} and ran {fmt.count(engine.tests_run)} statistical checks. "
                 "Nothing stood out strongly enough to call it a real pattern. That's a result too: "
                 "it means the differences you might see by eye are most likely just random ups and downs.")
        title = f"A first look at {name}"
        next_steps = ["Add more rows (more time, more customers) so smaller patterns can show up.",
                      "Tell me what you care about in the context box, then run it again."]

    health_missing = []
    for c in prof.columns.values():
        if c.missing and c.missing / max(rows, 1) >= 0.05 and c.role in ("measure", "category", "time"):
            health_missing.append({"column": c.name, "share": fmt.pct(c.missing / rows), "count": c.missing})
    skipped = [c.name for c in prof.columns.values() if c.role in ("id", "text", "constant", "geo")]

    return {
        "id": dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6],
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "file_name": file_name, "sheet": sheet, "other_sheets": other_sheets, "context": context,
        "model": None,
        "dataset": {
            "rows": rows, "columns": cols, "main_metric": main, "row_noun": prof.row_noun,
            "column_list": describe_columns(df, prof),
        },
        "story": {"title": title, "intro": intro, "takeaways": takeaways, "next_steps": next_steps, "ai_written": False},
        "kpis": kpis,
        "insights": ins,
        "cleaning": loaded.notes,
        "health": {"missing": health_missing, "skipped": skipped, "notes": engine.health},
        "method": {
            "tests_run": engine.tests_run, "tested_candidates": len(tested), "passed": len(passed),
            "shown": len(ins), "alpha": insights.ALPHA,
            "summary": ("Every pattern was checked with a proper statistical test. All results were corrected together "
                        "for the number of checks (Benjamini-Hochberg), so running lots of tests doesn't create lucky "
                        "'discoveries'. A pattern also had to be big enough to matter, not just technically real."),
        },
    }


def _span(a, b) -> str:
    days = (b - a).days + 1
    if days < 60:
        return f"{days} days"
    months = round(days / 30.44)
    if months < 24:
        return f"{months} months"
    years = days / 365.25
    return f"{years:.1f} years".replace(".0 ", " ")


def load_frame(path: Path, sheet: str | None, context: str = ""):
    loaded = loader.load(path, sheet)
    prof = classify(loaded.df, loaded.units, context)
    return loaded.df, prof



