#!/usr/bin/env bash
# Renders design/glance-app-store.html to App Store PNGs with headless Chrome.
#   design/export-store-shots.sh            -> design/app-store/1290x2796/01-home.png ... 08-limit.png
#   design/export-store-shots.sh 1320x2868  -> same set at the 6.9" size (the artboard scales to the window width)
# Set CHROME to use a different Chrome/Chromium binary.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
size="${1:-1290x2796}"; w="${size%x*}"; h="${size#*x}"
out="$here/app-store/${w}x${h}"; mkdir -p "$out"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
names=(home ask results quote blocked approve paid limit)
for i in "${!names[@]}"; do
  n=$((i+1)); f="$out/$(printf '%02d' "$n")-${names[$i]}.png"
  # no --user-data-dir: a fresh profile makes headless Chrome hang on first run. perl alarm = portable timeout;
  # headless Chrome occasionally stalls, so retry up to three times.
  for try in 1 2 3; do
    if perl -e 'alarm shift; exec @ARGV' 40 "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
         --window-size="$w,$h" --virtual-time-budget=12000 \
         --screenshot="$f" "file://$here/glance-app-store.html?shot=$n" 2>/dev/null; then
      echo "wrote ${f#$here/}"; break
    fi
    pkill -f "glance-app-store.html" 2>/dev/null || true
    [ "$try" = 3 ] && { echo "failed: $f" >&2; exit 1; }
    echo "retrying shot $n ($try)" >&2
  done
done
