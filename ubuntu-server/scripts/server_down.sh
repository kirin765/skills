#!/usr/bin/env bash
# 서버 끄기: ssh 'sudo poweroff' → 완전히 halt 확인 → 플러그 OFF(대기전력 차단).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/../venv/bin/python"
PLUG="$PY $DIR/plug.py"
HOST=ubuntu-server
HOST_IP=100.113.73.17     # Tailscale IP (halt 감지용 ping)
HALT_TIMEOUT=90

ssh_up() { ssh -o ConnectTimeout=5 -o BatchMode=yes "$HOST" true >/dev/null 2>&1; }
host_pingable() { ping -c 1 -t 2 "$HOST_IP" >/dev/null 2>&1; }

if ! ssh_up; then
  echo "[down] SSH 응답 없음 — 이미 꺼졌다고 보고 플러그만 OFF."
  $PLUG off
  exit 0
fi

echo "[down] 정상 종료 요청 (sudo poweroff)..."
# poweroff 는 연결을 끊으므로 ssh 종료코드는 무시.
ssh -o ConnectTimeout=5 "$HOST" 'sudo poweroff' >/dev/null 2>&1 || true

echo "[down] halt 대기 (최대 ${HALT_TIMEOUT}s)..."
waited=0
while host_pingable; do
  sleep 5; waited=$((waited+5))
  if [ "$waited" -ge "$HALT_TIMEOUT" ]; then
    echo "[down] 경고: ${HALT_TIMEOUT}s 안에 ping이 안 끊김. 그래도 플러그를 끕니다(디스크는 이미 sync/언마운트됐을 가능성 큼)." >&2
    break
  fi
  printf '.'
done
echo ""

echo "[down] 플러그 OFF..."
$PLUG off
echo "[down] 완료"
