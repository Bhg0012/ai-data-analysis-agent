"""Saved reports live in the user's data folder so they can be reopened later."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .config import data_dir

SAFE_ID = re.compile(r"^[a-z0-9-]{6,64}$")


def reports_dir() -> Path:
    p = data_dir() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def uploads_dir() -> Path:
    p = data_dir() / "uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def report_path(rid: str) -> Path:
    if not SAFE_ID.match(rid):
        raise KeyError(rid)
    return reports_dir() / rid


def save(report: dict, source_file: Path) -> None:
    d = report_path(report["id"])
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, d / ("source" + source_file.suffix.lower()))
    (d / "report.json").write_text(json.dumps(report, default=str), "utf-8")


def update(report: dict) -> None:
    (report_path(report["id"]) / "report.json").write_text(json.dumps(report, default=str), "utf-8")


def load(rid: str) -> dict:
    p = report_path(rid) / "report.json"
    if not p.exists():
        raise KeyError(rid)
    return json.loads(p.read_text("utf-8"))


def source_file(rid: str) -> Path:
    d = report_path(rid)
    for f in d.iterdir():
        if f.name.startswith("source"):
            return f
    raise KeyError(rid)


def listing() -> list[dict]:
    out = []
    for d in reports_dir().iterdir():
        f = d / "report.json"
        if not f.exists():
            continue
        try:
            r = json.loads(f.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "id": r["id"], "title": r["story"]["title"], "file_name": r["file_name"],
            "sheet": r.get("sheet"), "created_at": r["created_at"], "rows": r["dataset"]["rows"],
            "n_insights": len(r["insights"]),
            "kinds": [i["chart"].get("type") for i in r["insights"][:4]],
        })
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


def delete(rid: str) -> None:
    shutil.rmtree(report_path(rid), ignore_errors=True)
