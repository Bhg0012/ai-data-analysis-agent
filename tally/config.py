"""Where Tally keeps its files, and the user's settings."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "ollama_url": "http://localhost:11434",
    "model": "",          # empty = pick the best installed model automatically
    "use_ai": True,       # write explanations with the local AI when it's available
}


def data_dir() -> Path:
    override = os.environ.get("TALLY_DATA_DIR")
    if override:
        p = Path(override)
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "Tally"
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", Path.home())) / "Tally"
    else:
        p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "tally"
    p.mkdir(parents=True, exist_ok=True)
    return p


def settings_path() -> Path:
    return data_dir() / "settings.json"


def load_settings() -> dict:
    s = dict(DEFAULTS)
    try:
        s.update(json.loads(settings_path().read_text("utf-8")))
    except (OSError, json.JSONDecodeError):
        pass
    if os.environ.get("OLLAMA_HOST") and s["ollama_url"] == DEFAULTS["ollama_url"]:
        host = os.environ["OLLAMA_HOST"]
        s["ollama_url"] = host if host.startswith("http") else f"http://{host}"
    return s


def save_settings(new: dict) -> dict:
    s = load_settings()
    for k in DEFAULTS:
        if k in new:
            s[k] = new[k]
    settings_path().write_text(json.dumps(s, indent=2), "utf-8")
    return s
