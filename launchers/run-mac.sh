#!/bin/bash
# Starts Tally on a Mac: installs the Python helper (uv) the first time,
# pulls the latest version from GitHub, then opens the app window.
# Everything lives in a function so updating this file mid-run is safe.

main() {
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$ROOT" || exit 1
  QUIET=""
  [ "$1" = "--quiet" ] && QUIET=1

  echo ""
  echo "   Tally"
  echo "   -----"
  echo ""

  UV="$HOME/.local/bin/uv"
  [ -x "$UV" ] || UV="$(command -v uv 2>/dev/null)"
  if [ -z "$UV" ] || [ ! -x "$UV" ]; then
    echo "  First-time setup: installing a small helper that runs Tally (uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null || {
      echo ""
      echo "  Sorry, I couldn't download the helper. Check your internet connection and try again."
      [ -z "$QUIET" ] && read -r -p "  Press Enter to close."
      exit 1
    }
    UV="$HOME/.local/bin/uv"
  fi

  "$UV" run --quiet --no-project --python 3.12 python launchers/update.py

  # If the app icon changed in an update, tell macOS so Finder, the Dock and
  # Desktop shortcuts stop showing the old one.
  ICON="$ROOT/Tally.app/Contents/Resources/AppIcon.icns"
  SUM_FILE="$ROOT/.icon-sum"
  if [ -f "$ICON" ]; then
    SUM="$(shasum "$ICON" 2>/dev/null | cut -d' ' -f1)"
    if [ -n "$SUM" ] && [ "$SUM" != "$(cat "$SUM_FILE" 2>/dev/null)" ]; then
      touch "$ROOT/Tally.app" "$ROOT/Tally.app/Contents/Info.plist"
      /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
        -f "$ROOT/Tally.app" >/dev/null 2>&1 || true
      echo "$SUM" > "$SUM_FILE"
    fi
  fi

  if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "  Getting everything ready. The first start takes a minute or two..."
  fi

  if [ -n "$QUIET" ]; then
    exec "$UV" run --quiet --python 3.12 python -m tally --auto-exit
  else
    "$UV" run --quiet --python 3.12 python -m tally || {
      echo ""
      echo "  Tally stopped because of a problem (see the messages above)."
      read -r -p "  Press Enter to close."
    }
  fi
}

main "$@"
exit
