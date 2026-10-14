"""Open Tally in its own clean app window (no tabs or address bar) when possible."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


def _candidates() -> list[str]:
    if sys.platform == "darwin":
        apps = ["Google Chrome", "Microsoft Edge", "Brave Browser", "Chromium", "Arc"]
        return [f"/Applications/{a}.app/Contents/MacOS/{a}" for a in apps] + [
            str(Path.home() / f"Applications/{a}.app/Contents/MacOS/{a}") for a in apps]
    if os.name == "nt":
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        rel = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
               r"BraveSoftware\Brave-Browser\Application\brave.exe"]
        return [str(Path(r) / x) for x in rel for r in roots if r]
    names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"]
    return [p for p in (shutil.which(n) for n in names) if p]


def open_window(url: str) -> None:
    if os.environ.get("TALLY_BROWSER_TAB"):
        webbrowser.open(url)
        return
    for exe in _candidates():
        if exe and Path(exe).exists():
            try:
                subprocess.Popen([exe, f"--app={url}", "--new-window", "--window-size=1280,860"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                return
            except OSError:
                continue
    webbrowser.open(url)
