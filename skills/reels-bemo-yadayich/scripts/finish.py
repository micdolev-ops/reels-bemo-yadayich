"""Final audio pass: voice + sound cues, loudness to -14 LUFS, muxed onto the render.

Usage: python3 finish.py <render.mp4> <voice-source.mp4> <out.mp4> [cues.json]
cues.json: [{"file": "pop.wav", "at": 3.25, "gain": 0.5}, ...]
  file  a name from ../assets/sfx (or a path), at  seconds in the edit, gain  0..1

The output is as long as the render: the voice is padded with silence at the end.
The voice is never processed on its own; cues sit under it (0.4-0.6 for the
quiet style), then the whole mix is normalized once. Output audio is forced to
48 kHz because loudnorm otherwise writes 192 kHz.
"""
import json
import os
import subprocess
import sys

SFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sfx")


def main():
    render, voice, out = sys.argv[1:4]
    cues = json.load(open(sys.argv[4], encoding="utf8")) if len(sys.argv) > 4 else []

    cmd = ["ffmpeg", "-v", "error", "-y", "-i", render, "-i", voice]
    # the voice is padded with silence, so the reel keeps the logo after the last word
    chains, labels = ["[1:a]aresample=48000,apad[v]"], ["[v]"]
    for i, c in enumerate(cues):
        path = c["file"] if os.path.sep in c["file"] else os.path.join(SFX, c["file"])
        cmd += ["-i", path]
        ms = int(round(c["at"] * 1000))
        chains.append(f"[{i + 2}:a]aresample=48000,adelay={ms}|{ms},volume={c.get('gain', 0.5)}[s{i}]")
        labels.append(f"[s{i}]")
    mix = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first," if cues else f"{labels[0]}"
    chains.append(f"{mix}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")

    cmd += ["-filter_complex", ";".join(chains), "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
