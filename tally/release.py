"""Which version of Tally is on disk, and when it was published on GitHub.

Shown in the corner of the home screen so it's easy to check that an update arrived.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent


def release_info() -> dict:
    info = {"version": __version__, "commit": None, "published": None, "source": "unknown"}
    if (REPO_ROOT / ".git").exists():
        try:
            out = subprocess.run(["git", "log", "-1", "--format=%H%n%cI"], cwd=REPO_ROOT,
                                 capture_output=True, text=True, timeout=5)
            sha, date = out.stdout.split()[:2]
            info.update(commit=sha[:7], published=date, source="git")
            return info
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    marker = REPO_ROOT / ".tally-version"
    if marker.exists():
        lines = marker.read_text().split()
        if lines:
            info.update(commit=lines[0][:7], source="download")
        if len(lines) > 1:
            info["published"] = lines[1]
            return info
    # last resort: when the app's files were last changed on this computer
    newest = max((f.stat().st_mtime for f in Path(__file__).parent.rglob("*") if f.is_file()), default=None)
    if newest:
        info["published"] = datetime.fromtimestamp(newest, tz=timezone.utc).isoformat()
    return info
