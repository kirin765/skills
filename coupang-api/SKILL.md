---
name: coupang-api
description: Call the Coupang Open API (쿠팡 오픈 API / Wing) for the user's OWN store "온누리문방구" (vendorId A01569984). Covers every store read/write — 상품 생성·등록(로켓그로스 포함)·목록·조회·수정, 가격·재고, 주문 조회·발주서(ordersheets), 배송·송장, 반품·교환, 출고지·반품지, 정산·매출. Trigger on "쿠팡 API", "쿠팡 상품/주문/재고/가격/정산/송장 …", "온누리문방구 주문 가져와", "로켓그로스 상품 생성", "Coupang Wing API" — even if the API isn't named. A bundled script handles per-request HMAC-SHA256 (CEA) signing. Distinct from naver-commerce-api (SmartStore). GOTCHA — IP allowlist enforced; calls only work from an IP registered in Wing 연동정보, otherwise every call returns 403 FORBIDDEN regardless of correct signing.
---

# Coupang Open API — 온누리문방구 (vendorId A01569984)

쿠팡 본인 스토어 데이터를 공식 Open API로 읽고/수정하는 스킬. 까다로운 요청별 HMAC-SHA256(CEA) 서명은 번들 스크립트가 처리하므로, 너는 엔드포인트(메서드·경로·바디)만 고르면 된다.

## 준비물 (이미 설정됨)

- 자격증명: `~/.coupang.env` (chmod 600) — `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`, `COUPANG_VENDOR_ID=A01569984`. SKILL.md·git에 시크릿을 절대 넣지 말 것.
- 클라이언트: `scripts/coupang.py` — 표준 라이브러리만 쓰므로 시스템 `python3`로 바로 실행한다 (venv·외부 패키지 불필요). 토큰 개념이 없고, 매 호출마다 서명을 새로 만든다.

## ⚠️ IP 허용목록 (가장 흔한 실패 원인)

쿠팡 게이트웨이는 **Wing 연동정보에 등록된 IP에서 온 요청만 허용**한다. 등록 안 된 IP에서 호출하면 서명이 완벽해도 항상 이렇게 막힌다:

```json
{ "error":"FORBIDDEN", "status":403,
  "message":"Your ip address X.X.X.X is not allowed for this request. ..." }
```

- 현재 등록 IP는 `209.71.88.82` (sajangbu.com 서버) 한 곳이다.
- 이 403이 나오면 서명 문제가 아니라 **IP 문제**다. 추측으로 우회하려 하지 말고, 사용자에게 알린다: Wing → 판매자정보 → 안전인증/Open API → 연동정보 "수정"에서 호출하는 머신의 공인 IP를 허용목록에 추가하거나, 등록된 서버(209.71.88.82)에서 호출해야 한다. 메시지의 `Your ip address ...`에 차단된 IP가 그대로 찍히니 그 IP를 사용자에게 알려주면 된다.

## 기본 사용법

```bash
cd ~/.claude/skills/coupang-api
PY=python3

# GET (쿼리는 경로에 붙여도 되고 --query 로 줘도 된다 — 서명에 동일하게 반영됨)
$PY scripts/coupang.py GET "<path>" --query k=v k=v

# POST / PUT (JSON 바디)
$PY scripts/coupang.py POST "<path>" --body '{"...":"..."}'
$PY scripts/coupang.py PUT  "<path>" --body '<json>'

# DELETE
$PY scripts/coupang.py DELETE "<path>"

# 디버그: 서명 대상 문자열·Authorization 헤더·최종 URL만 출력 (호출 안 함)
$PY scripts/coupang.py sign GET "<path>" --query k=v
```

- `<path>`는 호스트(`https://api-gateway.coupang.com`) 뒤 경로. 경로 안의 `{vendorId}`는 설정된 업체코드로 자동 치환된다.
- 응답 JSON을 그대로 출력하고, 2xx면 exit 0 / 그 외 exit 1. gzip/deflate 응답은 자동 해제한다.

## 검증된 동작 (실측 ✅ 라이브 200)

등록 IP(`218.237.176.17`)에서 실호출로 확인 완료:
- 상품 목록: `GET /v2/providers/seller_api/apis/api/v1/marketplace/seller-products?vendorId=A01569984&maxPerPage=2` → 온누리문방구 실제 상품 반환.
- 반품지 목록: `GET /v2/providers/openapi/apis/api/v4/vendors/{vendorId}/returnShippingCenters` → 실제 반품지 반환.
- CEA HMAC-SHA256 서명, gzip 자동 해제 모두 정상.

## 경로 구조 주의 — 두 번째로 흔한 실패 원인

모든 경로는 `/v2/providers/{provider}/apis/api/v{n}/...` 형태다. **항상 `apis`** 이고(`apps` 아님 — `apps`로 쓰면 `"Provider id is not specified correctly."` 라우팅 실패), `provider`와 버전만 계열마다 다르다:

- **상품**: `/v2/providers/seller_api/apis/api/v1/marketplace/...`
- **주문·반품·교환·출고지/반품지·정산**: `/v2/providers/openapi/apis/api/v{n}/vendors/{vendorId}/...` — 버전이 엔드포인트마다 다름(`v1`/`v4`/`v5`…).

버전 번호와 `provider`만 맞추면 된다. 정확한 경로·버전·메서드는 호출 전 `references/endpoints.md`에서 확인하고, 거기 없거나 불확실하면 공식 문서로 검증한다(아래). 메서드가 틀리면 `PRECONDITION_FAILED`(예: 출고지 조회는 POST).

## 엔드포인트 찾기

자주 쓰는 경로·메서드·필수 파라미터는 `references/endpoints.md`를 읽는다. 거기 없거나 버전·바디 스키마가 불확실하면 공식 문서에서 확인:
- 개발자 포털: https://developers.coupangcorp.com/hc/ko
- 로켓그로스(RFM) 상품 생성은 마켓플레이스 상품 생성과 플로우·필드가 다르다 — 반드시 로켓그로스 전용 문서로 경로·바디를 확인한 뒤 호출한다.

## 쓰기 작업 시 안전수칙

상품 생성/수정, 가격·재고 변경, 발주서 확인처리, 송장 등록처럼 스토어 상태를 바꾸는 호출(POST/PUT/DELETE)은 되돌리기 어렵다. 실행 전 무엇을 바꾸는지(대상 식별자, 바뀌는 필드·값)를 사용자에게 한 줄로 확인받고 진행한다. 상품 수정은 먼저 GET으로 현재 객체를 받아 바꿀 필드만 교체해 PUT 하는 게 안전하다(전체 객체를 요구하는 엔드포인트가 많음). 잘못된 vendorId 반복 호출은 IP·업체코드 차단으로 이어질 수 있으니 vendorId는 항상 설정값을 쓴다.
