"""Times the captions of a reel with no voice (text only), at a comfortable reading pace.

Usage: python3 text_captions.py <script.txt> [reel.json] [--pace 1.0]
script.txt: one caption per block, a blank line between blocks.
  A line that starts with "~" is a thin row (small connecting words); any other line is heavy.
  *word* marks the one emotional word of the caption (accent colour).
  Example:
    ~ שונאת
    *לערוך* רילים?

    ~ אז למה שתערכי
    אותם בכלל?
The thin row comes in first, then the heavy words one by one, then the caption stays long
enough to read it twice. --pace 1.3 is slower, 0.8 is faster. Writes "captions" and
"duration" into reel.json (2.4s left after the last caption for the button or logo).
"""
import json
import re
import sys

IN_GAP, WORD_GAP, MIN_HOLD, PER_WORD, BETWEEN, TAIL = 0.3, 0.26, 1.3, 0.24, 0.15, 2.4


def parse(text):
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    out = []
    for b in blocks:
        rows = []
        for line in b.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kind = "thin" if line.startswith("~") else "heavy"
            rows.append((kind, line.lstrip("~").strip()))
        if rows:
            out.append(rows)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pace = float(sys.argv[sys.argv.index("--pace") + 1]) if "--pace" in sys.argv else 1.0
    if "--pace" in sys.argv:
        args.remove(sys.argv[sys.argv.index("--pace") + 1])
    src, target = args[0], (args[1] if len(args) > 1 else "reel.json")
    caps, t = [], 0.3
    for rows in parse(open(src, encoding="utf8").read()):
        start, out_rows, n = t, [], 0
        for kind, line in rows:
            words = line.split()
            n += len(words)
            if kind == "thin":
                # the thin row comes in as one piece
                text = " ".join(w.replace("*", "") for w in words)
                out_rows.append({"kind": "thin", "words": [{"t": round(t, 2), "text": text}]})
                t += IN_GAP * pace
            else:
                ws = []
                for w in words:
                    m = re.match(r"^\*(.+?)\*([?!.,]*)$", w)
                    item = {"t": round(t, 2), "text": m.group(1) + m.group(2) if m else w.replace("*", "")}
                    if m:
                        item["accent"] = True
                    ws.append(item)
                    t += WORD_GAP * pace
                out_rows.append({"kind": "heavy", "words": ws})
        end = t + max(MIN_HOLD, PER_WORD * n) * pace
        caps.append({"start": round(start - 0.05, 2), "end": round(end, 2), "rows": out_rows})
        t = end + BETWEEN

    try:
        reel = json.load(open(target, encoding="utf8"))
    except FileNotFoundError:
        reel = {}
    reel.pop("subject", None)
    reel["captions"] = caps
    reel["duration"] = round(caps[-1]["end"] + TAIL, 2)
    json.dump(reel, open(target, "w", encoding="utf8"), ensure_ascii=False, indent=2)
    print(f"{len(caps)} captions, reel {reel['duration']}s, written to {target}")
    for c in caps:
        print(f"{c['start']:6.2f}-{c['end']:6.2f}  " + " | ".join(" ".join(w["text"] for w in r["words"]) for r in c["rows"]))


if __name__ == "__main__":
    main()
