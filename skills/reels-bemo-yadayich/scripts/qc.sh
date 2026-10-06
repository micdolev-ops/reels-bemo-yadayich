#!/usr/bin/env bash
# Checks a finished reel before it is sent: streams and duration, loudness,
# black / frozen / silent stretches, and sudden jumps between frames.
# Usage: qc.sh <final.mp4> [expected-seconds]
set -euo pipefail

F="${1:?usage: qc.sh <final.mp4> [expected-seconds]}"
EXP="${2:-}"

echo "== streams"
ffprobe -v error -show_entries format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate -of compact "$F"
if [ -n "$EXP" ]; then
  python3 - "$F" "$EXP" <<'E'
import subprocess, sys
d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", sys.argv[1]],
                         capture_output=True, text=True).stdout)
e = float(sys.argv[2])
print(f"duration {d:.2f}s, expected {e:.2f}s", "OK" if abs(d - e) < 0.5 else "MISMATCH")
E
fi

echo "== loudness (target about -14 LUFS)"
ffmpeg -nostdin -hide_banner -i "$F" -af ebur128=framelog=quiet -f null - 2>&1 | grep -E "^\s+I:" || true

echo "== black (>0.5s), frozen (>2s), silent (>2s)"
ffmpeg -nostdin -hide_banner -nostats -i "$F" \
  -vf "blackdetect=d=0.5:pic_th=0.98:pix_th=0.10,freezedetect=n=-60dB:d=2" \
  -af "silencedetect=n=-50dB:d=2" -f null - 2>&1 \
  | grep -E "black_start|freeze_start|freeze_duration|silence_start|silence_end" || echo "none"

echo "== jumps (one frame much larger than its neighbours; a fade spreads over several frames and is not listed)"
python3 - "$F" <<'E'
import subprocess, sys
import numpy as np
f = sys.argv[1]
fps = eval(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
                           "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip())
raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", f, "-vf", "scale=96:170,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
a = np.frombuffer(raw, np.uint8).reshape(-1, 170, 96).astype(float)
d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
med = np.median(d)
hits = [i for i, v in enumerate(d) if v > 8 * med and v > 6 and v > 2.5 * max(d[max(i - 2, 0):i].max(initial=0), d[i + 1:i + 3].max(initial=0))]
print(f"median change {med:.2f}")
print("\n".join(f"  {(i + 1) / fps:6.2f}s  change {d[i]:.1f}" for i in hits) or "  none")
E
