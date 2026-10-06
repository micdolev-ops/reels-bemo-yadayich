"""Turns the sound down between your words, so a voice in the room, a fridge or traffic
in the pauses disappears. Speech that overlaps your own words cannot be removed this way.

Usage: python3 clean_pauses.py <clip.mp4> <out.wav> [floor=0.02]
Needs <clip.mp4>.words.json from transcribe.py (times in this clip).
Each word is kept with 0.07s on either side; everything else drops to `floor` (2%)
with 40ms ramps so nothing clicks.
"""
import json
import subprocess
import sys

import numpy as np

SR = 48000


def main():
    clip, out = sys.argv[1], sys.argv[2]
    floor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02
    words = json.load(open(clip + ".words.json", encoding="utf8"))
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", clip, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).copy()
    g = np.full(len(x), floor, np.float32)
    for a, b, _ in words:
        g[max(0, int((a - 0.07) * SR)):int((b + 0.07) * SR)] = 1.0
    k = int(0.04 * SR)
    g = np.convolve(g, np.ones(k, np.float32) / k, mode="same")
    y = (x * g).astype(np.float32)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", out], input=y.tobytes(), check=True)
    quiet = sum(1 for i in range(1, len(words)) if words[i][0] - words[i - 1][1] > 0.3)
    print(f"{out}  ({quiet} pauses quieted)")


if __name__ == "__main__":
    main()
