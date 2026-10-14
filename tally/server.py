"""The local web server that the Tally window talks to."""

from __future__ import annotations

import os
import shutil
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, analysis, chat, config, history, loader
from .ollama import RECOMMENDED_MODELS, Ollama, OllamaError

STATIC = Path(__file__).parent / "static"
SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "coffee_shop_sales.csv"

app = FastAPI(title="Tally", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

JOBS: dict[str, dict] = {}
FRAMES: OrderedDict[str, tuple] = OrderedDict()
LAST_SEEN = {"t": time.time()}
LOCK = threading.Lock()

# Each stage's slice of the 0-100% progress bar.
STAGE_SPAN = {"read": (0, 10), "profile": (10, 15), "stats": (15, 55), "pick": (55, 60), "write": (60, 99)}

STEPS = [
    ("read", "Reading your file"),
    ("profile", "Understanding the columns"),
    ("stats", "Running statistical checks"),
    ("pick", "Keeping only what's real"),
    ("write", "Writing it in plain English"),
]


# ------------------------------------------------------------------ helpers

def _upload_path(upload_id: str) -> Path:
    if not history.SAFE_ID.match(upload_id.split(".")[0]):
        raise HTTPException(404, "That upload has expired. Please add the file again.")
    for f in history.uploads_dir().glob(upload_id + ".*"):
        return f
    raise HTTPException(404, "That upload has expired. Please add the file again.")


def _clean_old_uploads():
    cutoff = time.time() - 24 * 3600
    for f in history.uploads_dir().glob("*"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


NO_SOURCE = ("This is an older report, so Tally only kept the summary to save space on your computer. "
             "Add the file again to ask questions about it.")


def _frame(rid: str):
    if not history.has_source(rid):
        raise HTTPException(410, NO_SOURCE)
    with LOCK:
        if rid in FRAMES:
            FRAMES.move_to_end(rid)
            return FRAMES[rid]
    rep = history.load(rid)
    df, prof = analysis.load_frame(history.source_file(rid), rep.get("sheet"), rep.get("context", ""))
    with LOCK:
        FRAMES[rid] = (df, prof)
        while len(FRAMES) > 4:
            FRAMES.popitem(last=False)
    return df, prof


def _new_job(kind: str) -> dict:
    jid = uuid.uuid4().hex[:12]
    job = {"id": jid, "kind": kind, "status": "running", "step": None, "label": "Starting",
           "steps": [{"key": k, "label": lbl, "state": "todo"} for k, lbl in STEPS],
           "detail": "", "report_id": None, "error": None, "progress": 0, "progress_next": 10, "pace": 2.0,
           "started": time.time()}
    JOBS[jid] = job
    return job


def _run_analysis(job: dict, path: Path, file_name: str, sheet: str | None, context: str, other_sheets):
    def step(key, label, frac=0.0, frac_next=None):
        """Move the progress bar. Each stage owns a slice of 0-100, sub-steps fill it in."""
        keys = [k for k, _ in STEPS]
        if key == "done":
            for s in job["steps"]:
                s["state"] = "done"
            job["progress"] = job["progress_next"] = 100
            return
        idx = keys.index(key) if key in keys else 0
        for i, s in enumerate(job["steps"]):
            s["state"] = "done" if i < idx else "active" if i == idx else "todo"
        lo, hi = STAGE_SPAN[key]
        nxt = 1.0 if frac_next is None else frac_next
        job["step"], job["detail"] = key, label
        job["progress"] = max(job["progress"], round(lo + (hi - lo) * frac, 1))
        job["progress_next"] = max(job["progress"], round(lo + (hi - lo) * nxt, 1))
        # how long this sub-step usually takes, so the counter can keep moving smoothly
        job["pace"] = 12.0 if key == "write" else 2.0  # AI writing takes several seconds per finding
    try:
        settings = config.load_settings()
        report = analysis.analyze(path, file_name=file_name, sheet=sheet, context=context, settings=settings,
                                  step=step, other_sheets=other_sheets)
        history.save(report, path)
        job["report_id"] = report["id"]
        job["status"] = "done"
        job["progress"] = 100
    except loader.LoadError as e:
        job["status"], job["error"] = "error", str(e)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        job["status"], job["error"] = "error", f"Something went wrong while analysing this file: {e}"


# ------------------------------------------------------------------ pages

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.post("/api/heartbeat")
def heartbeat():
    LAST_SEEN["t"] = time.time()
    return {"ok": True}


@app.get("/api/status")
def status():
    s = config.load_settings()
    o = Ollama(s["ollama_url"]).status(s.get("model"))
    return {"version": __version__, "settings": s, "ollama": o, "recommended": RECOMMENDED_MODELS}


class SettingsIn(BaseModel):
    ollama_url: str | None = None
    model: str | None = None
    use_ai: bool | None = None
    mascot_look: str | None = None
    holiday_costumes: bool | None = None


@app.post("/api/settings")
def set_settings(body: SettingsIn):
    return config.save_settings({k: v for k, v in body.model_dump().items() if v is not None})


# ------------------------------------------------------------------ uploads & analysis

@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "data.csv").name
    ext = Path(name).suffix.lower()
    if ext not in loader.SUPPORTED:
        raise HTTPException(400, "I can read CSV, Excel (.xlsx, .xls), TSV, TXT and JSON files. Try saving your file as one of those.")
    _clean_old_uploads()
    uid = uuid.uuid4().hex[:16]
    dest = history.uploads_dir() / f"{uid}{ext}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return _describe_upload(uid, dest, name)


def _describe_upload(uid: str, dest: Path, name: str) -> dict:
    try:
        sheets = loader.list_sheets(dest)
    except loader.LoadError as e:
        raise HTTPException(400, str(e)) from e
    usable = [s for s in sheets if s["rows"] is None or s["rows"] > 1]
    if not usable:
        raise HTTPException(400, "This file looks empty. I couldn't find any data in it.")
    return {"upload_id": uid, "file_name": name, "sheets": usable, "suggested": loader.best_sheet(usable)}


@app.post("/api/sample")
def sample():
    uid = uuid.uuid4().hex[:16]
    dest = history.uploads_dir() / f"{uid}.csv"
    shutil.copy2(SAMPLE, dest)
    return _describe_upload(uid, dest, "Coffee shop sales (sample).csv")


class AnalyzeIn(BaseModel):
    upload_id: str
    file_name: str
    sheet: str | None = None
    context: str = ""


@app.post("/api/analyze")
def analyze(body: AnalyzeIn):
    path = _upload_path(body.upload_id)
    is_book = path.suffix.lower() in (".xlsx", ".xlsm", ".xls")
    sheets = loader.list_sheets(path)
    sheet = (body.sheet or loader.best_sheet(sheets)) if is_book else None
    others = [s["name"] for s in sheets if is_book and s["name"] != sheet and (s["rows"] or 0) > 1]
    job = _new_job("analyze")
    threading.Thread(target=_run_analysis, args=(job, path, body.file_name, sheet, body.context[:2000], others),
                     daemon=True).start()
    return {"job_id": job["id"]}


class ReanalyzeIn(BaseModel):
    sheet: str | None = None
    context: str | None = None


@app.post("/api/reports/{rid}/reanalyze")
def reanalyze(rid: str, body: ReanalyzeIn):
    try:
        rep = history.load(rid)
        if not history.has_source(rid):
            raise HTTPException(410, NO_SOURCE)
        src = history.source_file(rid)
    except KeyError as e:
        raise HTTPException(404, "Report not found") from e
    uid = uuid.uuid4().hex[:16]
    dest = history.uploads_dir() / f"{uid}{src.suffix}"
    shutil.copy2(src, dest)
    return analyze(AnalyzeIn(upload_id=uid, file_name=rep["file_name"], sheet=body.sheet or rep.get("sheet"),
                             context=rep.get("context", "") if body.context is None else body.context))


@app.get("/api/jobs/{jid}")
def job_status(jid: str):
    job = JOBS.get(jid)
    if not job:
        raise HTTPException(404, "Unknown job")
    return job


# ------------------------------------------------------------------ history

@app.get("/api/reports")
def reports():
    return history.listing()


@app.get("/api/storage")
def storage():
    items = history.listing()
    return {"reports": len(items), "bytes": sum(i["size"] for i in items),
            "with_file": sum(1 for i in items if i["has_source"]), "keep_files_for": history.KEEP_SOURCES}


@app.get("/api/reports/{rid}")
def report(rid: str):
    try:
        rep = history.load(rid)
        rep["has_source"] = history.has_source(rid)
        return JSONResponse(rep)
    except KeyError as e:
        raise HTTPException(404, "Report not found") from e


class RenameIn(BaseModel):
    title: str


@app.patch("/api/reports/{rid}")
def rename(rid: str, body: RenameIn):
    try:
        rep = history.load(rid)
    except KeyError as e:
        raise HTTPException(404, "Report not found") from e
    rep["story"]["title"] = body.title.strip()[:120] or rep["story"]["title"]
    history.update(rep)
    return {"ok": True}


@app.delete("/api/reports/{rid}")
def delete(rid: str):
    try:
        history.delete(rid)
    except KeyError as e:
        raise HTTPException(404, "Report not found") from e
    FRAMES.pop(rid, None)
    return {"ok": True}


# ------------------------------------------------------------------ chat

class ChatIn(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/reports/{rid}/chat")
def ask(rid: str, body: ChatIn):
    s = config.load_settings()
    client = Ollama(s["ollama_url"])
    st = client.status(s.get("model"))
    if not st["ready"]:
        raise HTTPException(409, "The AI isn't connected yet. Open Settings to connect Ollama, then try again.")
    try:
        rep = history.load(rid)
        df, prof = _frame(rid)
    except KeyError as e:
        raise HTTPException(404, "Report not found") from e
    try:
        out = chat.answer(client, st["model"], df, prof, rep, body.history, body.question.strip()[:2000])
    except OllamaError as e:
        raise HTTPException(502, f"The AI had a problem: {e}") from e
    rep.setdefault("chat", []).extend([
        {"role": "user", "content": body.question.strip()[:2000]},
        {"role": "assistant", "content": out["reply"], "chart": out.get("chart"), "steps": out.get("steps")},
    ])
    history.update(rep)
    return out


# ------------------------------------------------------------------ models

class PullIn(BaseModel):
    model: str


@app.post("/api/ollama/pull")
def pull(body: PullIn):
    s = config.load_settings()
    job = _new_job("pull")
    job["label"] = f"Downloading {body.model}"

    def run():
        try:
            def prog(ev):
                total, done = ev.get("total"), ev.get("completed")
                job["detail"] = ev.get("status", "")
                if total and done:
                    job["progress"] = round(100 * done / total)
            Ollama(s["ollama_url"]).pull(body.model, prog)
            config.save_settings({"model": body.model})
            job["status"], job["progress"] = "done", 100
        except Exception as e:  # noqa: BLE001
            job["status"], job["error"] = "error", str(e)
    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job["id"]}


def start_idle_watchdog(minutes: float):
    """Quit when no Tally window has checked in for a while (the user closed it)."""
    def watch():
        while True:
            time.sleep(30)
            busy = any(j["status"] == "running" for j in JOBS.values())
            if not busy and time.time() - LAST_SEEN["t"] > minutes * 60:
                os._exit(0)
    threading.Thread(target=watch, daemon=True).start()
