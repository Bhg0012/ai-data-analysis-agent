#!/bin/bash
# One-line installer for Mac:
#   curl -fsSL https://raw.githubusercontent.com/bhg0012/ai-data-analysis-agent/main/install/install-mac.sh | bash
# Puts Tally in ~/Tally, adds a Tally icon to your Desktop, and starts it.
set -e
REPO="${TALLY_REPO:-bhg0012/ai-data-analysis-agent}"
BRANCH="${TALLY_BRANCH:-main}"
DEST="${TALLY_HOME:-$HOME/Tally}"

echo ""
echo "  Installing Tally into $DEST"
if [ -d "$DEST/tally" ]; then
  echo "  Tally is already installed. Starting it (it will update itself)."
elif command -v git >/dev/null 2>&1 && git --version >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$DEST"
else
  TMP="$(mktemp -d)"
  curl -fsSL "https://codeload.github.com/$REPO/zip/refs/heads/$BRANCH" -o "$TMP/tally.zip"
  unzip -q "$TMP/tally.zip" -d "$TMP"
  mkdir -p "$DEST"
  cp -R "$TMP"/*/. "$DEST"/
  rm -rf "$TMP"
fi
chmod +x "$DEST/Start Tally (Mac).command" "$DEST/launchers/"*.sh "$DEST/Tally.app/Contents/MacOS/Tally" 2>/dev/null || true

# A Desktop alias to Tally.app (keeps the icon, works like any app)
osascript -e "tell application \"Finder\" to make alias file to POSIX file \"$DEST/Tally.app\" at POSIX file \"$HOME/Desktop\"" >/dev/null 2>&1 \
  && echo "  Added Tally to your Desktop." || true

exec bash "$DEST/launchers/run-mac.sh"
