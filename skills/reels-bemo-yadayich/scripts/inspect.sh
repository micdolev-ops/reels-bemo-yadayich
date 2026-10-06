#!/usr/bin/env bash
# Measures a raw clip before editing: size, speech segments, a 1fps contact sheet,
# and a strip of the face over the first 1.6s (for choosing a calm first frame).
# Usage: inspect.sh <clip.mp4> <out-dir>
set -euo pipefail

CLIP="${1:?usage: inspect.sh <clip.mp4> <out-dir>}"
OUT="${2:?usage: inspect.sh <clip.mp4> <out-dir>}"
mkdir -p "$OUT"

echo "== stream"
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact "$CLIP"

for db in 30 26; do
  echo "== silences at -${db}dB (speech is between them)"
  ffmpeg -i "$CLIP" -af "silencedetect=noise=-${db}dB:d=0.06" -f null - 2>&1 \
    | grep -oE "silence_(start|end): [0-9.]+" | tr '\n' ' '
  echo
done

ffmpeg -v error -y -i "$CLIP" -vf "fps=1,scale=270:-1,tile=5x2" -frames:v 1 "$OUT/sheet.png"
# upper-centre crop: in a seated wide shot the face sits around 25-35% of the height
ffmpeg -v error -y -i "$CLIP" -vf "trim=0:1.6,select='not(mod(n\,2))',crop=iw*0.3:iw*0.3:iw*0.35:ih*0.23,scale=150:150,drawtext=text='%{pts\:flt}':x=4:y=4:fontsize=14:fontcolor=red,tile=6x3" -frames:v 1 "$OUT/first-frames.png"
ffmpeg -v error -y -i "$CLIP" -filter_complex "showwavespic=s=1200x200" -frames:v 1 "$OUT/wave.png"
echo "== wrote $OUT/sheet.png $OUT/first-frames.png $OUT/wave.png"
