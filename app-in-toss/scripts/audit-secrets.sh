#!/usr/bin/env bash
# Pre-upload / pre-commit secret & privacy audit.
# Usage: audit-secrets.sh [dir]   (default: current dir; '.' scans the whole tree)
# Scans for env/credential files and secret-looking content. Reports only
# file:line:pattern-kind — never the matched value. Exit 1 when anything found.
#
# Run this before uploading a skill to a public repo, or before committing
# any project that touches apps-in-toss (API keys, promo codes, ad group ids).

DIR="${1:-.}"
cd "$DIR" 2>/dev/null || { echo "✗ cannot cd to $DIR"; exit 1; }

FOUND=0
warn() { echo "⚠ $1"; FOUND=1; }

# Skip vendor dirs and git.
EXCLUDE=(node_modules .git dist build .playwright-cli .playwright-mcp .claude)
EXC=()
for d in "${EXCLUDE[@]}"; do EXC+=(-not -path "*/$d/*"); done
EXC+=(-not -name "*.min.js" -not -name "*.min.css" -not -name "audit-secrets.sh")

echo "== [1/3] credential/private files =="
find . -type f \( -name ".env*" -o -name "*.pem" -o -name "*.key" -o -name "*.jks" -o -name "*.p12" -o -name "*.pfx" -o -name "keystore.properties" -o -name "*.p8" -o -name "*.mobileprovision" \) "${EXC[@]}" -print | while read -r f; do
  warn "credential file: $f (must stay out of the repo; reference by name only)"
done

echo "== [2/3] secret patterns in tracked text files =="
PATTERNS=( \
  'sk-[A-Za-z0-9]{20,}' \
  'AKIA[0-9A-Z]{16}' \
  '-----BEGIN (RSA |EC |PRIVATE |OPENSSH )' \
  'client_secret' \
  'api[_-]?key[[:space:]]*[:=][[:space:]]*[^[:space:]"'"'"',;}]{8,}' \
  'password[[:space:]]*[:=][[:space:]]*[^[:space:]"'"'"',;}]{6,}' \
  'secret[[:space:]]*[:=][[:space:]]*[^[:space:]"'"'"',;}]{8,}' \
  'Bearer [A-Za-z0-9._-]{20,}' \
)
# Scan one pattern at a time so one giant regex can't blow up memory.
for pat in "${PATTERNS[@]}"; do
  while IFS=: read -r file line; do
    [ -z "$file" ] && continue
    warn "possible secret ($pat) at $file:$line (value redacted)"
  done < <(grep -rInE --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.mjs' --include='*.cjs' --include='*.json' --include='*.md' --include='*.sh' --include='*.yaml' --include='*.yml' --include='*.toml' --include='*.env*' "${EXC[@]}" "$pat" . 2>/dev/null | head -50)
done

echo "== [3/3] long hex/base64 tokens (possible keys/ids/group ids) =="
while IFS=: read -r file line; do
  [ -z "$file" ] && continue
  warn "long token/group-id at $file:$line (if this is a project-specific ad group id / key, move to env, do not commit)"
done < <(grep -rInE --include='*.ts' --include='*.tsx' --include='*.js' --include='*.mjs' --include='*.json' --include='*.md' "${EXC[@]}" '[a-z0-9]{32,}' . 2>/dev/null | head -30)

echo "== summary =="
if [ "$FOUND" -eq 1 ]; then
  echo "✗ audit failed — remove/externalize flagged items, then re-run."
  exit 1
else
  echo "✓ clean — nothing sensitive found."
fi