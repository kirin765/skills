#!/usr/bin/env bash
# Build and validate an Apps in Toss (.ait) mini-app bundle.
# Usage: ait-build.sh [project-dir]   (default: current dir)
# Steps: 1) verify apps-in-toss.config.ts + build script, 2) run the build,
#        3) validate the produced .ait (contents, appName match, size, no secrets).
#
# Note: .ait files carry a prologue of extra bytes before the zip payload, so
# command-line `unzip` may reject them; validation uses Python zipfile instead.

set -uo pipefail

DIR="${1:-$(pwd)}"
cd "$DIR" || { echo "✗ cannot cd to $DIR"; exit 1; }

echo "== [1/4] config check =="
[ -f apps-in-toss.config.ts ] || { echo "✗ apps-in-toss.config.ts missing — run 'npm i @apps-in-toss/web-framework' first"; exit 1; }
APPNAME=$(grep -o 'appName: *["'"'"'][^"'"'"']*["'"'"']' apps-in-toss.config.ts | head -1 | sed -E 's/.*["'"'"']([^"'"'"']*)["'"'"'].*/\1/')
if [ -z "$APPNAME" ]; then echo "✗ appName not found in apps-in-toss.config.ts"; exit 1; fi
echo "   appName: $APPNAME"

# Prefer a dedicated build:ait script; fall back to official build.
if grep -q '"build:ait"' package.json 2>/dev/null; then
  BUILD_CMD="npm run build:ait"
elif grep -q '"build"' package.json 2>/dev/null; then
  BUILD_CMD="npm run build"
else
  echo "✗ no build script in package.json"; exit 1
fi
echo "   build command: $BUILD_CMD"

echo "== [2/4] build =="
eval "$BUILD_CMD" || { echo "✗ build failed"; exit 1; }

echo "== [3/4] locate + inspect .ait =="
AIT=$(ls -1t ./*.ait 2>/dev/null | head -1)
if [ -z "$AIT" ]; then echo "✗ no .ait produced"; exit 1; fi
echo "   bundle: $AIT ($(du -h "$AIT" | cut -f1))"

# Validate via Python zipfile (handles .ait prologue bytes).
REPORT=$(python3 - "$AIT" <<'PY'
import json, re, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
names = z.namelist()
missing = [n for n in ("bundle.json", "project-package.json") if n not in names]
has_sources = any(n.startswith("sources/") for n in names)
node_modules = [n for n in names if "node_modules" in n]
total = sum(i.file_size for i in z.infolist())
appname = ""
try:
    appname = json.loads(z.read("bundle.json"))["config"].get("appName", "")
except Exception:
    appname = ""
pat = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|PRIVATE|EC))")
hits = 0
for n in names:
    if n.startswith("sources/") and n.endswith((".js", ".mjs", ".html", ".css", ".json", ".txt")):
        try:
            data = z.read(n).decode("utf-8", "ignore")
        except Exception:
            continue
        hits += len(pat.findall(data))
print(f"REPORT: missing={','.join(missing) or '-'} sources={has_sources} node_modules={','.join(node_modules) or '-'} total={total} appname={appname} sechits={hits}")
PY
) || { echo "✗ .ait is not a readable zip"; exit 1; }
echo "   $REPORT"

MISSING=$(echo "$REPORT" | sed -E 's/.*missing=([^ ]+).*/\1/')
HAS_SRC=$(echo "$REPORT" | sed -E 's/.*sources=([^ ]+).*/\1/')
NM=$(echo "$REPORT" | sed -E 's/.*node_modules=([^ ]+).*/\1/')
TOTAL=$(echo "$REPORT" | sed -E 's/.*total=([0-9]+).*/\1/')
BUNDLE_APPNAME=$(echo "$REPORT" | sed -E 's/.*appname=([^ ]*).*/\1/')
SECHITS=$(echo "$REPORT" | sed -E 's/.*sechits=([0-9]+).*/\1/')

echo "== [4/4] validation =="
[ "$MISSING" = "-" ] || { echo "✗ missing entries: $MISSING"; exit 1; }
[ "$HAS_SRC" = "True" ] || { echo "✗ sources/ missing from .ait"; exit 1; }
[ "$NM" = "-" ] || { echo "✗ node_modules inside .ait — do not bundle dependencies"; exit 1; }
if [ -n "$BUNDLE_APPNAME" ] && [ "$BUNDLE_APPNAME" != "$APPNAME" ]; then
  echo "✗ bundle appName($BUNDLE_APPNAME) != config appName($APPNAME)"; exit 1
fi
echo "   bundle appName: ${BUNDLE_APPNAME:-unreadable} (config: $APPNAME)"
echo "   uncompressed size: $TOTAL bytes"
if [ "$TOTAL" -gt 104857600 ]; then echo "✗ >100MB uncompressed (limit)"; exit 1; fi
if [ "$SECHITS" -gt 0 ]; then echo "✗ secret-looking patterns inside .ait sources"; exit 1; fi

echo "✓ OK — ready to upload: ${DIR}/${AIT}"
echo "  Upload: console(버전 탭) or: cd $DIR && npx ait deploy -m '메모'"