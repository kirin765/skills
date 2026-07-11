#!/usr/bin/env bash
# 서버 켜기: 플러그 ON → BIOS 자동부팅 → SSH 뜰 때까지 대기.
# 이미 켜져 있으면 그대로 통과.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/../venv/bin/python"
PLUG="$PY $DIR/plug.py"
HOST=ubuntu-server
BOOT_TIMEOUT=180   # BIOS POST + 부팅 대기 상한(초)

ssh_up() { ssh -o ConnectTimeout=5 -o BatchMode=yes "$HOST" true >/dev/null 2>&1; }

if ssh_up; then
  echo "[up] 이미 켜져 있음 (SSH OK)"
  exit 0
fi

echo "[up] 플러그 ON..."
$PLUG on

echo "[up] 부팅 대기 (최대 ${BOOT_TIMEOUT}s)..."
waited=0
while ! ssh_up; do
  sleep 5; waited=$((waited+5))
  if [ "$waited" -ge "$BOOT_TIMEOUT" ]; then
    echo "[up] 타임아웃: ${BOOT_TIMEOUT}s 안에 SSH가 안 뜸. BIOS 'Restore after AC Power Loss=Power On' 설정을 확인하세요." >&2
    exit 1
  fi
  printf '.'
done
echo ""
echo "[up] 준비완료 (${waited}s)"
