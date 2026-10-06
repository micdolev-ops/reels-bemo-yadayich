"""Builds index.html from reel.json + brand.json + template.txt.

Usage: python3 build.py
Optional files next to it: custom.html, custom.css, custom.js (the reel's own effect;
custom.js can use `tl` and `T`). Then: npx hyperframes lint && npx hyperframes render -o out.mp4 --quiet
"""
import html
import json
import os


def read(p, default=""):
    return open(p, encoding="utf8").read() if os.path.exists(p) else default


def main():
    brand = json.load(open("brand.json", encoding="utf8"))
    reel = json.load(open("reel.json", encoding="utf8"))
    c, f = brand["colors"], brand["fonts"]

    faces = []
    for role in f.values():
        for sub, rng in (("hebrew", ""), ("latin", " unicode-range: U+0000-00FF;")):
            fn = f"fonts/{role['package']}-{sub}-{role['weight']}-normal.woff2"
            if os.path.exists(fn):
                faces.append(f'      @font-face {{ font-family: "{role["family"]}"; font-weight: {role["weight"]}; src: url("{fn}") format("woff2");{rng} }}')

    big = [[a, b] for a, b in reel.get("big", [])]
    in_big = lambda a, b: any(a < (e if e is not None else 1e9) and b > s for s, e in big)

    caps = []
    for i, cap in enumerate(reel["captions"]):
        rows = []
        for row in cap["rows"]:
            k = row["kind"]
            ws = "".join(
                f'<span class="w {k}{" accent" if w.get("accent") else ""}" data-t="{w["t"]}">{html.escape(w["text"])}</span>'
                for w in row["words"])
            rows.append(f'<div class="row {k}-row">{ws}</div>')
        cls = "cap hook" if in_big(cap["start"], cap["end"]) else "cap"
        caps.append(f'      <div class="{cls}" id="cap{i}">{"".join(rows)}</div>')

    broll = []
    for k, b in enumerate(reel.get("broll", [])):
        bid = f"b{k + 1}"
        a, e = b["start"], b["end"]
        if b["src"].lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            inner = f'<img class="m" src="{b["src"]}" alt="">'
        else:
            dur = min(e - a + 0.6, b.get("len", 1e9))
            inner = (f'<video class="m" id="{bid}v" src="{b["src"]}" muted playsinline data-start="{a - 0.2:.2f}" '
                     f'data-duration="{dur:.2f}" data-track-index="{k + 2}"></video>')
        broll.append(f'      <div class="card" id="{bid}">{inner}</div>')

    cta = reel.get("cta")
    cta_html = ""
    if cta:
        cta_html = f'      <div id="cta"><span>{html.escape(cta["text"])}</span></div>'
        if cta.get("arrow"):
            d1 = "M583 15 C 540 130, 470 200, 366 200 C 290 198, 235 150, 238 90 C 240 30, 280 2, 305 14 C 345 32, 322 110, 255 142 C 190 176, 100 176, 12 126"
            d2 = "M45 133 L 10 125 L 35 160"
            cta_html += (f'\n      <svg id="arrow" viewBox="0 0 600 220"><path class="under" id="ushaft" pathLength="1" d="{d1}"/>'
                         f'<path class="under" id="uhead" pathLength="1" d="{d2}"/><path class="over" id="ashaft" pathLength="1" d="{d1}"/>'
                         f'<path class="over" id="ahead" pathLength="1" d="{d2}"/></svg>')
    logo = reel.get("logo")
    logo_html = '      <img id="logo" src="media/logo.png" alt="">' if logo else ""

    s = reel["subject"]
    TL = {"caps": [{"start": c_["start"], "end": c_["end"]} for c_ in reel["captions"]],
          "broll": [[f"b{k + 1}", b["start"], b["end"]] for k, b in enumerate(reel.get("broll", []))],
          "joins": reel.get("joins", []), "big": big,
          "bigScale": reel.get("bigScale", 1.4), "bigY": reel.get("bigY", -310), "bigOrigin": reel.get("bigOrigin", 1320),
          "cta": {"at": cta["at"], "until": cta["until"], "arrow": bool(cta.get("arrow"))} if cta else None,
          "end": reel.get("fadeOut"), "logo": logo["at"] if logo else None}

    rep = {"%%FONTFACES%%": "\n".join(faces), "%%BG%%": c["background"], "%%PRIMARY%%": c["primary"],
           "%%ACCENT%%": c["accent"], "%%TEXT%%": c["text"],
           "%%THIN_FAMILY%%": f["thin"]["family"], "%%THIN_WEIGHT%%": str(f["thin"]["weight"]),
           "%%HEAVY_FAMILY%%": f["heavy"]["family"], "%%HEAVY_WEIGHT%%": str(f["heavy"]["weight"]),
           "%%SUBJECT%%": s["src"], "%%SUBJECT_TOP%%": str(s.get("top", 80)), "%%SUBJECT_DUR%%": str(s["duration"]),
           "%%DUR%%": str(reel["duration"]), "%%CAPS%%": "\n".join(caps), "%%BROLL%%": "\n".join(broll),
           "%%CTA%%": cta_html, "%%LOGO%%": logo_html, "%%TL%%": json.dumps(TL, ensure_ascii=False),
           "%%CUSTOM_HTML%%": read("custom.html"), "%%CUSTOM_CSS%%": read("custom.css"), "%%CUSTOM_JS%%": read("custom.js")}
    out = read("template.txt")  # .txt so HyperFrames does not see a second composition
    for k, v in rep.items():
        out = out.replace(k, v)
    open("index.html", "w", encoding="utf8").write(out)
    print(f"index.html: {len(caps)} captions, {len(broll)} cutaways, {len(TL['joins'])} joins")
    # checks for the mistakes that are easy to miss in a still
    if cta and not in_big(cta["at"], cta["until"]):
        print("warning: the button sits at chest height of the big framing. Without a big period around it, it covers the face.")
    if reel.get("fadeOut") and reel["fadeOut"] + 0.7 > s["duration"]:
        print(f"warning: the speaker fades out until {reel['fadeOut'] + 0.7:.2f}s but her video ends at {s['duration']}s; "
              f"set fadeOut to {s['duration'] - 0.75:.2f} or earlier, or the end will jump.")
    covers = [(b["start"], b["end"]) for b in reel.get("broll", [])]
    for a, e in big:
        for t in [a, e]:
            if t not in (None, 0) and not any(s0 - 0.01 <= t <= e0 + 0.2 for s0, e0 in covers):
                print(f"warning: the framing changes at {t}s with no cutaway covering it; the jump will show.")


if __name__ == "__main__":
    main()
