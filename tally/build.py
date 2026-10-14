"""A fingerprint of the Tally files on disk.

When Tally updates itself, an older copy may still be running in the background.
Comparing fingerprints lets the launcher spot that and restart it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_id() -> str:
    h = hashlib.sha1()
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and f.suffix in {".py", ".js", ".css", ".html", ".svg"} and "__pycache__" not in f.parts:
            h.update(str(f.relative_to(ROOT)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]
