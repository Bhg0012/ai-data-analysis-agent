"""Start Tally:  python -m tally  [--port 8765] [--no-window] [--auto-exit]"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import urllib.request

from . import APP_NAME, __version__
from .build import build_id
from .window import open_window


def tally_status(port: int) -> dict | None:
    """The status of a Tally already running on this port, or None."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as r:
            data = json.loads(r.read())
            return data if "version" in data else None
    except Exception:  # noqa: BLE001
        return None


def is_tally(port: int) -> bool:
    return tally_status(port) is not None


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def stop_old(port: int) -> None:
    """Ask an out-of-date Tally to quit, and wait briefly for it to go."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/shutdown", method="POST", data=b"")
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:  # noqa: BLE001 - very old versions can't be asked; we just use another port
        return
    for _ in range(25):
        if port_free(port):
            return
        time.sleep(0.2)


def main():
    ap = argparse.ArgumentParser(prog="tally")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-window", action="store_true", help="don't open the app window")
    ap.add_argument("--auto-exit", action="store_true", help="quit a while after the window is closed")
    args = ap.parse_args()

    current = build_id()
    port = args.port
    # Reuse a Tally that's already running, but only if it's this exact version.
    for p in range(args.port, args.port + 10):
        st = tally_status(p)
        if st is None:
            continue
        if st.get("build") == current:
            print(f"{APP_NAME} is already running. Opening it.")
            if not args.no_window:
                open_window(f"http://127.0.0.1:{p}")
            return
        print(f"An older {APP_NAME} was still running. Restarting it with the new version...")
        stop_old(p)
    while not port_free(port):
        port += 1

    import uvicorn

    from .server import app, start_idle_watchdog

    url = f"http://127.0.0.1:{port}"
    print(f"\n  {APP_NAME} {__version__} is running at {url}")
    print("  Keep this window open while you use Tally. Close it to quit.\n")

    if args.auto_exit:
        start_idle_watchdog(minutes=20)
    if not args.no_window:
        def opener():
            for _ in range(100):
                if is_tally(port):
                    open_window(url)
                    return
                time.sleep(0.2)
        threading.Thread(target=opener, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
