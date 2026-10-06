"""Word-level Hebrew transcription with ivrit.ai's Whisper model.

Usage: python3 transcribe.py <clip.mp4> [cache-dir]
Writes <clip.mp4>.words.json as [[start, end, word], ...] and prints it.

Needs `pip install faster-whisper`. The first run downloads the model (about 1.6GB).
On a 4-core CPU: model load ~25s, a 10s clip transcribes in ~9s.

Whisper word starts run early, and the first word after a silence can start
inside the silence (a clip that began speaking at 1.13s reported 0.00s).
Starts that fall inside a measured silence are moved to where the speech begins.
"""
import json
import re
import subprocess
import sys

from faster_whisper import WhisperModel

MODEL = "ivrit-ai/whisper-large-v3-turbo-ct2"


def silences(path, db=-30, min_len=0.06):
    log = subprocess.run(
        ["ffmpeg", "-i", path, "-af", f"silencedetect=noise={db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    return list(zip(starts, ends))


def main():
    clip = sys.argv[1]
    cache = sys.argv[2] if len(sys.argv) > 2 else None
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=cache)
    segments, _ = model.transcribe(clip, language="he", word_timestamps=True)
    words = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segments for w in s.words]

    gaps = silences(clip)
    for w in words:
        for a, b in gaps:
            if a <= w[0] < b and b < w[1]:
                w[0] = round(b, 2)

    with open(clip + ".words.json", "w", encoding="utf8") as f:
        json.dump(words, f, ensure_ascii=False)
    for w in words:
        print(f"{w[0]:6.2f} {w[1]:6.2f}  {w[2]}")


if __name__ == "__main__":
    main()
