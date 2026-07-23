#!/usr/bin/env bash
# Regenera PNG desde el SVG escalable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SVG="$ROOT/packaging/icons/hicolor/scalable/apps/io.jebstudios.Workset.svg"
DATA="$ROOT/src/workset/data/icons"

cp "$SVG" "$DATA/io.jebstudios.Workset.svg"
cp "$ROOT/packaging/icons/hicolor/symbolic/apps/io.jebstudios.Workset-symbolic.svg" \
  "$DATA/io.jebstudios.Workset-symbolic.svg"

for s in 16 24 32 48 64 128 256 512; do
  dir="$ROOT/packaging/icons/hicolor/${s}x${s}/apps"
  mkdir -p "$dir"
  rsvg-convert -w "$s" -h "$s" "$SVG" -o "$dir/io.jebstudios.Workset.png"
  if (( s <= 128 )); then
    cp "$dir/io.jebstudios.Workset.png" "$DATA/io.jebstudios.Workset-${s}.png"
  fi
done
cp "$ROOT/packaging/icons/hicolor/128x128/apps/io.jebstudios.Workset.png" \
  "$DATA/io.jebstudios.Workset.png"
echo "Icons rendered."
