#!/bin/bash
# Starts Tally on Linux. Same steps as the Mac launcher.
main() {
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$ROOT" || exit 1
  UV="$HOME/.local/bin/uv"
  [ -x "$UV" ] || UV="$(command -v uv 2>/dev/null)"
  if [ -z "$UV" ] || [ ! -x "$UV" ]; then
    echo "  Installing the helper that runs Tally (uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null || exit 1
    UV="$HOME/.local/bin/uv"
  fi
  "$UV" run --quiet --no-project --python 3.12 python launchers/update.py
  exec "$UV" run --quiet --python 3.12 python -m tally "$@"
}
main "$@"
exit
