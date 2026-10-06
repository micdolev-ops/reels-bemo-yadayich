#!/usr/bin/env bash
# Removes the background behind the speaker and lays her on the brand background, lower in
# the frame, so the top third is free for captions.
# Usage: cutout.sh <project-dir> <clip.mp4> [top-offset-px=560]
# Writes <project>/media/subject.mp4 (opaque, renders fast). Takes about 1s per frame on CPU.
# A transparent webm placed straight into the template renders far too slowly, so we composite here.
set -euo pipefail
PROJ="$1"; CLIP="$2"; TOP="${3:-560}"
cd "$PROJ"
BG=$(python3 -c "import json;print(json.load(open('brand.json',encoding='utf8'))['colors']['background'].lstrip('#'))")
npx hyperframes remove-background "$CLIP" -o media/subject.webm --device cpu
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CLIP")
ffmpeg -nostdin -v error -y -f lavfi -i "color=c=0x$BG:s=1080x1920:r=30:d=$D" -c:v libvpx-vp9 -i media/subject.webm \
  -filter_complex "[1:v]scale=1080:-2[s];[0:v][s]overlay=0:$TOP:shortest=1,format=yuv420p" \
  -c:v libx264 -crf 15 -preset medium -an media/subject.mp4
echo "$PROJ/media/subject.mp4"
