#!/usr/bin/env bash
# Render the home-screen / dock icons from tools/icon-source.html.
#
# Headless Chrome is used rather than an image library so the emoji comes out
# of the same font stack the site itself uses. Re-run after changing the logo.
set -euo pipefail

cd "$(dirname "$0")/.."

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "Google Chrome not found at $CHROME"; exit 1; }

mkdir -p icons
SRC="file://$PWD/tools/icon-source.html"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

shot () { # shot <url> <out>
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --default-background-color=00000000 \
    --screenshot="$2" --window-size=512,512 "$1" >/dev/null 2>&1
}

shot "$SRC"        "$TMP/master.png"
shot "$SRC?safe"   "$TMP/maskable.png"

# iOS home screen wants a plain opaque square — it applies its own rounding.
sips -z 180 180 "$TMP/master.png"   --out icons/apple-touch-icon.png >/dev/null
sips -z 192 192 "$TMP/master.png"   --out icons/icon-192.png         >/dev/null
sips -z 512 512 "$TMP/master.png"   --out icons/icon-512.png         >/dev/null
sips -z 512 512 "$TMP/maskable.png" --out icons/icon-maskable.png    >/dev/null
sips -z 32 32   "$TMP/master.png"   --out icons/favicon-32.png       >/dev/null
sips -z 16 16   "$TMP/master.png"   --out icons/favicon-16.png       >/dev/null

echo "written:"
ls -la icons/
