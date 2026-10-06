#!/usr/bin/env bash
# Checks the tools, then creates a reel project with HyperFrames, GSAP and the brand fonts.
# Usage: setup.sh <project-dir> [brand.json]
# brand.json defaults to ~/.reels-bemo-yadayich/brand.json. Prints the project path on the last line.
set -euo pipefail

PROJ="${1:?usage: setup.sh <project-dir> [brand.json]}"
BRAND="${2:-$HOME/.reels-bemo-yadayich/brand.json}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"

missing=()
command -v node >/dev/null || missing+=("node (גרסה 22 ומעלה): https://nodejs.org")
command -v ffmpeg >/dev/null || missing+=("ffmpeg: מק: brew install ffmpeg · ווינדוס: winget install ffmpeg")
command -v python3 >/dev/null || missing+=("python3: https://www.python.org")
if [ ${#missing[@]} -gt 0 ]; then
  echo "חסרים כלים, צריך להתקין פעם אחת:"; printf ' - %s\n' "${missing[@]}"; exit 1
fi
node -e 'process.exit(+process.versions.node.split(".")[0] >= 22 ? 0 : 1)' || { echo "צריך Node 22 ומעלה (יש $(node -v))"; exit 1; }
[ -f "$BRAND" ] || { echo "אין קובץ מותג ב-$BRAND. קודם עושים את שאלות הפתיחה (ראו SKILL.md)."; exit 1; }

mkdir -p "$PROJ" && cd "$PROJ"
[ -f package.json ] || echo '{"private":true}' > package.json

# fonts named in brand.json, as @fontsource packages (Hebrew + Latin subsets)
PKGS=$(python3 - "$BRAND" <<'PY'
import json, sys
b = json.load(open(sys.argv[1], encoding="utf8"))
print(" ".join(sorted({f["package"] for f in b["fonts"].values()})))
PY
)
npm i -s hyperframes@0.8.106 gsap@3.14.2 $(for p in $PKGS; do printf '@fontsource/%s ' "$p"; done) >/dev/null 2>&1
npx hyperframes browser ensure >/dev/null 2>&1 || true
pip3 install -q faster-whisper numpy 2>/dev/null || python3 -m pip install -q faster-whisper numpy || true

mkdir -p fonts media
python3 - "$BRAND" <<'PY'
import json, shutil, sys, os
b = json.load(open(sys.argv[1], encoding="utf8"))
for role, f in b["fonts"].items():
    for sub in ("hebrew", "latin"):
        src = f"node_modules/@fontsource/{f['package']}/files/{f['package']}-{sub}-{f['weight']}-normal.woff2"
        if os.path.exists(src):
            shutil.copy(src, "fonts/")
        elif sub == "hebrew":
            print(f"אזהרה: לגופן {f['package']} במשקל {f['weight']} אין עברית. לבחור גופן אחר.")
PY
cp node_modules/gsap/dist/gsap.min.js .
cp "$SKILL/template/template.txt" "$SKILL/template/build.py" .
cp "$BRAND" brand.json
[ -f reel.json ] || cp "$SKILL/template/reel.example.json" reel.json
logo=$(python3 -c "import json;print(json.load(open('brand.json',encoding='utf8')).get('logo',''))")
[ -n "$logo" ] && [ -f "$logo" ] && cp "$logo" media/logo.png || true

echo "$(pwd)"
