#!/usr/bin/env bash
# Render the 3D transceiver and encode the files the topics embed:
#   tpu/media/osfp-turntable.gif   (HTML outputs; <image deliveryTarget="html5 webhelp">)
#   tpu/media/osfp-turntable.mp4   (<object type="video/mp4">)
#   tpu/media/osfp-hero.png        (PDF output; <image deliveryTarget="pdf">)
#
#   tools/render_media.sh            # needs: pip install bpy, and ffmpeg
#
# Run it locally after changing media/blender/osfp.py and commit the results, so writers see the
# media in Oxygen. CI can also run it on demand (Actions > corpus > Run workflow > render media)
# and attach the files as a build artifact for review.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRAMES="${FRAMES:-72}"
OUT="$ROOT/tpu/media"
TMP="$(mktemp -d)"
mkdir -p "$OUT"

python "$ROOT/media/blender/osfp.py" --frames "$FRAMES" --samples 16 --res 640x360 --out "$TMP"
python "$ROOT/media/blender/osfp.py" --still --res 1280x720 --samples 64 --out "$OUT/osfp-hero.png"

# GIF: 480 px wide, 12 fps, one palette for the whole loop (smaller and cleaner than per-frame).
ffmpeg -y -loglevel error -framerate 24 -i "$TMP/frame-%04d.png" \
  -vf "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  -loop 0 "$OUT/osfp-turntable.gif"

# MP4: H.264, three turns, plays in every current browser.
ffmpeg -y -loglevel error -stream_loop 2 -framerate 24 -i "$TMP/frame-%04d.png" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +faststart "$OUT/osfp-turntable.mp4"

rm -rf "$TMP"
ls -lh "$OUT"
