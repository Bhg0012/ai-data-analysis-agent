"""Start Tally:  python -m tally  [--port 8765] [--no-window] [--auto-exit]"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import urllib.request

from . import APP_NAME, __version__
from .window import open_window


def is_tally(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as r:
            return "version" in json.loads(r.read())
    except Exception:  # noqa: BLE001
        return False


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main():
    ap = argparse.ArgumentParser(prog="tally")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-window", action="store_true", help="don't open the app window")
    ap.add_argument("--auto-exit", action="store_true", help="quit a while after the window is closed")
    args = ap.parse_args()

    port = args.port
    if is_tally(port):
        print(f"{APP_NAME} is already running. Opening it.")
        if not args.no_window:
            open_window(f"http://127.0.0.1:{port}")
        return
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
