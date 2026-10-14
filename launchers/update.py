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
    req = urllib.request.Request(url, headers={"User-Agent": "Tally-updater", "Accept": "application/vnd.github.sha"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def update_with_zip() -> None:
    marker = ROOT / ".tally-version"
    try:
        latest = fetch(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}").decode().strip()
    except Exception:  # noqa: BLE001
        say("Couldn't check for updates right now. Starting the version you have.")
        return
    if len(latest) < 7 or latest.startswith("{"):
        try:
            latest = json.loads(latest)["sha"]
        except Exception:  # noqa: BLE001
            say("Couldn't read the latest version info. Starting the version you have.")
            return
    current = marker.read_text().strip() if marker.exists() else ""
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
        marker.write_text(latest)
        say("Updated Tally to the latest version.")
    except Exception as e:  # noqa: BLE001
        say(f"The update didn't finish ({e}). Starting the version you have.")


def main() -> None:
    if os.environ.get("TALLY_NO_UPDATE"):
        say("Skipping the update check.")
        return
    say("Checking for updates...")
    if (ROOT / ".git").exists() and shutil.which("git"):
        update_with_git()
    else:
        update_with_zip()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        say(f"Update check skipped ({e}).")
    sys.exit(0)
