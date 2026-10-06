"""Cuts the chosen takes and joins them into one clip, with soft joins.

Usage: python3 join.py <segs.txt> <out.mp4> [--no-dissolve]
segs.txt, one take per line:  <file> <start-seconds> <end-seconds>
Every take is normalized to 1080x1920, 30fps, 48kHz (phone clips are often HEVC,
rotated, or a slightly variable frame rate). Each cut gets a 20ms audio fade so it
does not click. At each join the last frame of the previous take fades out over
the new one for 0.35s, so a jump cut reads as a soft change instead of a jump.
Writes <out.mp4> and <out.mp4>.joins.json (the join times, for a blur in the template).
"""
import json
import os
import subprocess
import sys
import tempfile

FPS, FADE = 30, 0.35


def run(cmd):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + cmd, check=True)


def main():
    segs_file, out = sys.argv[1], sys.argv[2]
    dissolve = "--no-dissolve" not in sys.argv
    base = os.path.dirname(os.path.abspath(segs_file))
    segs = []
    for line in open(segs_file, encoding="utf8"):
        if line.strip() and not line.startswith("#"):
            f, a, b = line.rsplit(None, 2)
            segs.append((f if os.path.isabs(f) else os.path.join(base, f), float(a), float(b)))

    tmp = tempfile.mkdtemp()
    parts, joins, t = [], [], 0.0
    for i, (f, a, b) in enumerate(segs):
        n = round((b - a) * FPS)  # whole frames, so the join times are exact
        d = n / FPS
        p = os.path.join(tmp, f"p{i}.mp4")
        run(["-ss", str(a), "-i", f, "-t", f"{d:.4f}",
             "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},format=yuv420p",
             "-af", f"aresample=48000,afade=t=in:d=0.02,afade=t=out:st={d - 0.02:.3f}:d=0.02",
             "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-ac", "2", p])
        parts.append(p)
        if i:
            joins.append(round(t, 3))
        t += d

    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    joined = os.path.join(tmp, "joined.mp4") if dissolve and joins else out
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])

    if dissolve and joins:
        inputs, chain, last = ["-i", joined], [], "[0:v]"
        for k, j in enumerate(joins):
            png = os.path.join(tmp, f"j{k}.png")
            run(["-ss", f"{j - 1 / FPS:.4f}", "-i", joined, "-frames:v", "1", png])
            inputs += ["-loop", "1", "-t", f"{j + FADE + 0.1:.3f}", "-i", png]
            chain.append(f"[{k + 1}:v]format=rgba,fade=t=out:st={j:.3f}:d={FADE}:alpha=1[f{k}]")
            chain.append(f"{last}[f{k}]overlay=enable='between(t,{j:.3f},{j + FADE + 0.01:.3f})'[v{k}]")
            last = f"[v{k}]"
        run(inputs + ["-filter_complex", ";".join(chain), "-map", last, "-map", "0:a",
                      "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy", out])

    json.dump(joins, open(out + ".joins.json", "w"))
    print(f"{out}  {t:.2f}s  joins: {joins}")


if __name__ == "__main__":
    main()
