"""Bring Tally up to date with the latest version on GitHub.

Runs with plain Python (no extra packages). It never blocks Tally from starting:
if anything goes wrong (no internet, GitHub down), it just says so and carries on.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

REPO = os.environ.get("TALLY_REPO", "bhg0012/ai-data-analysis-agent")
BRANCH = os.environ.get("TALLY_BRANCH", "main")
ROOT = Path(__file__).resolve().parent.parent
KEEP = {".git", ".venv", ".tally-version"}


def say(msg: str) -> None:
    print(f"  {msg}", flush=True)


def update_with_git() -> None:
    try:
        before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        r = subprocess.run(["git", "pull", "--ff-only", "--quiet"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        say("Couldn't check for updates right now. Starting the version you have.")
        return
    if r.returncode != 0:
        say("Couldn't update automatically (maybe no internet, or files were changed by hand). Starting the version you have.")
    elif before != after:
        say("Updated Tally to the latest version.")
    else:
        say("Tally is up to date.")


def fetch(url: str, timeout: float = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Tally-updater", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def update_with_zip() -> None:
    marker = ROOT / ".tally-version"
    try:
        info = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"))
        latest = info["sha"]
        date = info["commit"]["committer"]["date"]
    except Exception:  # noqa: BLE001
        say("Couldn't check for updates right now. Starting the version you have.")
        return
    # .tally-version holds the commit id on line 1 and when it was published on line 2
    current = marker.read_text().splitlines()[0].strip() if marker.exists() and marker.read_text().strip() else ""
    if current == latest:
        say("Tally is up to date.")
        return
    say("Downloading the latest version of Tally...")
    try:
        blob = fetch(f"https://codeload.github.com/{REPO}/zip/{latest}", timeout=120)
        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(io.BytesIO(blob)).extractall(tmp)
            src = next(Path(tmp).iterdir())
            for item in src.iterdir():
                if item.name in KEEP:
                    continue
                dest = ROOT / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
        for exe in ("Start Tally (Mac).command", "launchers/run-mac.sh", "Tally.app/Contents/MacOS/Tally", "launchers/run-linux.sh"):
            p = ROOT / exe
            if p.exists():
                p.chmod(0o755)
        marker.write_text(f"{latest}\n{date}\n")
        say("Updated Tally to the latest version.")
    except Exception as e:  # noqa: BLE001
        say(f"The update didn't finish ({e}). Starting the version you have.")


def installed_version() -> str:
    """'a42cac6, published Oct 14, 2026 at 3:36 PM' for the copy now on this computer."""
    sha = date = ""
    try:
        if (ROOT / ".git").exists() and shutil.which("git"):
            out = subprocess.run(["git", "log", "-1", "--format=%h %cI"], cwd=ROOT, capture_output=True,
                                 text=True, timeout=5).stdout.split()
            sha, date = out[0], out[1]
        elif (ROOT / ".tally-version").exists():
            lines = (ROOT / ".tally-version").read_text().split()
            sha, date = lines[0][:7], lines[1] if len(lines) > 1 else ""
    except (OSError, IndexError, subprocess.SubprocessError):
        return ""
    if not sha:
        return ""
    try:
        d = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone()
        hour = d.hour % 12 or 12
        when = f"{d:%b} {d.day}, {d.year} at {hour}:{d:%M} {'AM' if d.hour < 12 else 'PM'}"
        return f"{sha}, published {when}"
    except ValueError:
        return sha


def main() -> None:
    if os.environ.get("TALLY_NO_UPDATE"):
        say("Skipping the update check.")
        return
    say("Checking for updates...")
    if (ROOT / ".git").exists() and shutil.which("git"):
        update_with_git()
    else:
        update_with_zip()
    v = installed_version()
    if v:
        say(f"You're running version {v}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        say(f"Update check skipped ({e}).")
    sys.exit(0)
