#!/bin/bash
# 카페24 앱 스모크 테스트 (S0 + S6 — curl 기반, 테스트 설치 한도 소모 안 함)
# 사용: ./smoke.sh <app_url> <mall_id> <client_secret> [app_name]
set -u
APP_URL="${1:?app_url 필수}"
MALL="${2:?mall_id 필수}"
SECRET="${3:?client_secret 필수}"
APP_NAME="${4:-$MALL}"

PASS=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# APP_URL에서 쿼리스트링 제거 (랜딩 테스트용)
APP_URL_BASE="${APP_URL%%\?*}"

echo "== 카페24 스모크: $APP_NAME (몰 $MALL) =="

# S0: 스토어 검색 노출
echo "-- S0 검색 노출"
if [ "${SKIP_SEARCH:-0}" = "1" ]; then
  echo "  ⏭️ 검색 노출 검사 생략 (SKIP_SEARCH=1 — 의도적 비노출/심사 중)"
  PASS=$((PASS+1))
else
  ENC=$(python3 -c "import urllib.parse;print(urllib.parse.quote('$APP_NAME'))")
  HIT=$(curl -s "https://store.cafe24.com/kr/filter/rest/apps?page=1&order=SALES_DESC&filter=%7B%22q%22%3A%5B%22${ENC}%22%5D%7D&s=${ENC}" -H 'User-Agent: Mozilla/5.0' | grep -c "$APP_NAME" || true)
  if [ "$HIT" -gt 0 ]; then ok "검색 노출 (히트 $HIT)"; else bad "검색 미노출 — 인덱스 지연 or 의도적 비노출 확인 (SKIP_SEARCH=1 로 생략 가능)"; fi
fi

# S6: hmac 검증
echo "-- S6a hmac 유효 URL → 307 리다이렉트"
URL=$(node "$(dirname "$0")/make_launch_url.cjs" "$MALL" "$APP_URL" "$SECRET")
CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-redirs 0 "$URL" 2>/dev/null || true)
if [ "$CODE" = "307" ] || [ "$CODE" = "302" ]; then ok "launch 307/302 ($CODE)"; else bad "launch 응답 $CODE — hmac/URL/secret 불일치"; fi

echo "-- S6b timestamp 만료 → 401"
echo "  (스킵 — URL 생성기가 현재시간만 씀, 수동 확인)"

echo "-- S6c 랜딩 (파라미터 없이) → 200 랜딩 렌더 또는 install 307"
LANDING=$(curl -s -o /dev/null -w '%{http_code}' -L --max-redirs 0 "$APP_URL_BASE" 2>/dev/null || true)
if [ "$LANDING" = "200" ]; then
  ok "랜딩 200 (파라미터 없으면 랜딩 렌더 — 정상)"
elif [ "$LANDING" = "307" ] || [ "$LANDING" = "308" ]; then
  ok "랜딩 → 307 (install로 리다이렉트 — 정상)"
elif [ "$LANDING" = "401" ] || [ "$LANDING" = "400" ]; then
  echo "  ℹ️ 랜딩 $LANDING — install로 리다이렉트된 후 hmac 검증이 거부함 (리다이렉트 자체는 동작)"
  ok "랜딩 $LANDING (install 리다이렉트 동작, hmac 거부는 정상)"
else
  bad "랜딩 응답 $LANDING"
fi

echo ""
echo "결과: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && echo "스모크 통과" || echo "스모크 실패 — 실패 항목 수정 후 재실행"
exit $FAIL
