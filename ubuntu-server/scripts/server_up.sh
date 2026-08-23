#!/usr/bin/env bash
# 서버 켜기: 플러그 OFF → 대기 → ON 으로 AC 를 재인가해 BIOS 자동부팅을 걸고 SSH 를 기다린다.
# 이미 켜져 있으면(SSH OK) 그대로 통과.
# BIOS 자동부팅은 AC 인가 "전환" 시점에만 걸리므로, 이미 ON 인 플러그에 on 을 또 보내면 no-op 이다.
# 그래서 항상 OFF 를 먼저 보낸다 — 단, 전력이 높으면(=무언가 가동 중, 대개 Windows) 끊지 않고 중단한다.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/../venv/bin/python"
PLUG="$PY $DIR/plug.py"
HOST=ubuntu-server
BOOT_TIMEOUT=180   # BIOS POST + 부팅 대기 상한(초)
IDLE_WATTS=20      # 이 값 미만이면 정지 상태로 본다 (실측: 정지 2~5W / 가동 102.4W)
AC_OFF_SECONDS=12  # AC 전환을 확실히 만들기 위한 OFF 유지 시간

ssh_up() { ssh -o ConnectTimeout=5 -o BatchMode=yes "$HOST" true >/dev/null 2>&1; }

if ssh_up; then
  echo "[up] 이미 켜져 있음 (SSH OK)"
  exit 0
fi

watts="$($PLUG watts)"
echo "[up] 소비전력 ${watts}W"

if awk "BEGIN{exit !($watts >= $IDLE_WATTS)}"; then
  cat >&2 <<MSG
[up] 중단: ${watts}W 가 흐르는데 SSH 가 안 됩니다 — 무언가 가동 중입니다.
     이 머신은 듀얼부팅이라 사용자가 Windows 를 쓰고 있을 가능성이 높습니다.
     지금 플러그를 끊으면 그 세션을 하드 전원차단하게 됩니다.
     사용자에게 "지금 서버에서 Windows 쓰고 계신가요?" 라고 묻고, Ubuntu 로 재부팅을 요청하세요.
MSG
  exit 2
fi

echo "[up] 정지 상태 확인. 플러그 OFF → ${AC_OFF_SECONDS}s 대기 → ON"
$PLUG off
sleep "$AC_OFF_SECONDS"
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
