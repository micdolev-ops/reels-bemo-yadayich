"""Turns a word-level transcript into a first draft of the captions in reel.json.

Usage: python3 draft_captions.py <clip.mp4.words.json> [reel.json]
Groups words into captions at pauses (>0.35s) or every 6 words, puts the first
1-3 words on a thin row and the rest on a heavy row, and marks no accent word.
This is only a draft: Claude then fixes the spelling against the approved script,
picks the one emotional word per caption (accent), and merges or splits captions.
"""
import json
import re
import sys


def clean(w):
    # on-screen captions drop commas, full stops and ellipses; a question mark stays
    return re.sub(r"[.,…:;\"]+", "", w).strip()


def main():
    words = json.load(open(sys.argv[1], encoding="utf8"))
    target = sys.argv[2] if len(sys.argv) > 2 else "reel.json"
    groups, cur = [], []
    words = [[a, b, clean(w)] for a, b, w in words if clean(w)]
    for i, w in enumerate(words):
        if cur and (w[0] - cur[-1][1] > 0.35 or len(cur) >= 6):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)

    caps = []
    for k, g in enumerate(groups):
        n_thin = 1 if len(g) <= 3 else min(3, len(g) // 2)
        thin, heavy = g[:n_thin], g[n_thin:]
        rows = [{"kind": "thin", "words": [{"t": thin[0][0], "text": " ".join(w[2] for w in thin)}]}]
        if heavy:
            rows.append({"kind": "heavy", "words": [{"t": w[0], "text": w[2]} for w in heavy]})
        end = groups[k + 1][0][0] - 0.05 if k + 1 < len(groups) else g[-1][1] + 0.4
        caps.append({"start": round(g[0][0] - 0.05, 2), "end": round(end, 2), "rows": rows})

    try:
        reel = json.load(open(target, encoding="utf8"))
    except FileNotFoundError:
        reel = {}
    reel["captions"] = caps
    json.dump(reel, open(target, "w", encoding="utf8"), ensure_ascii=False, indent=2)
    print(f"{len(caps)} captions drafted into {target}")
    for c in caps:
        print(f"{c['start']:6.2f}-{c['end']:6.2f}  " + " | ".join(" ".join(w["text"] for w in r["words"]) for r in c["rows"]))


if __name__ == "__main__":
    main()
