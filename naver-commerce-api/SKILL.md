---
name: naver-commerce-api
description: Call the Naver Commerce (스마트스토어 / SmartStore) API for the user's OWN store "온누리문방구" using the registered application credentials (type=SELF). Use this skill whenever the user wants to read or change anything in their SmartStore via API — list/search their products(상품 목록/검색), look up or edit a product's price·stock·detail(상품 조회·수정·등록), pull orders(주문 조회), check changed/new orders, process dispatch/cancel/return, or query settlement(정산) — even if they don't name the API. Trigger on phrases like "스마트스토어 API", "내 스토어 상품 조회/수정", "온누리문방구 주문 가져와", "커머스API", "네이버 커머스 주문/상품/재고/가격 API로 바꿔줘", "스마트스토어 재고 업데이트", "Naver Commerce API". This handles the tricky bcrypt電子서명 auth + token caching for you via a bundled script. It is for the user's own store data through the official Commerce API — distinct from naver-api (read-only search/trend demand), naver-searchad (search-ad account), and naver-seo (on-page SEO). Note: only API groups granted to the app work; an ungranted group returns GW.AUTHN and must be enabled in the 커머스API센터 first.
---

# Naver Commerce API (스마트스토어) — 온누리문방구, type=SELF

스마트스토어 본인 스토어 데이터를 공식 커머스API로 읽고/수정하는 스킬. 까다로운 bcrypt 전자서명 인증과 토큰 캐싱은 번들 스크립트가 처리하므로, 너는 엔드포인트만 고르면 된다.

## 준비물 (이미 설정됨)

- 자격증명: `~/.naver-commerce.env` (CLIENT_ID / CLIENT_SECRET, chmod 600). SKILL.md·git에 시크릿을 절대 넣지 말 것.
- 실행 파이썬: 이 스킬 전용 venv `~/.claude/skills/naver-commerce-api/.venv/bin/python` (bcrypt 설치됨). 시스템 파이썬은 PEP668로 막혀 있으니 반드시 이 venv를 쓴다.
- 클라이언트: `scripts/ncommerce.py`

## 기본 사용법

작업 디렉터리를 스킬 폴더로 두고 venv 파이썬으로 실행한다:

```bash
cd ~/.claude/skills/naver-commerce-api
PY=./.venv/bin/python

# 토큰만 발급/갱신해 출력 (보통 직접 부를 일 없음 — 자동 처리됨)
$PY scripts/ncommerce.py token

# GET
$PY scripts/ncommerce.py GET <path> [--query k=v k=v ...]

# POST / PUT (JSON 바디)
$PY scripts/ncommerce.py POST <path> --body '{"page":1,"size":50}'
$PY scripts/ncommerce.py PUT  <path> --body '<json>'

# DELETE
$PY scripts/ncommerce.py DELETE <path>
```

`<path>`는 호스트 뒤 경로 (예: `/external/v1/products/search`). 응답 JSON을 그대로 출력하고, 2xx면 exit 0 / 그 외 exit 1. 토큰은 자동 캐싱되고 만료·`GW.AUTHN` 401 시 자동 재발급한다.

## 검증된 동작 (실측)

- 토큰 발급 ✅ / 인증 헤더 ✅
- `POST /external/v1/products/search` → 온누리문방구 실제 상품 반환 ✅

## 권한(스코프) 주의 — 중요

이 앱은 **현재 "상품" API 그룹만 허용**돼 있다. 주문(`/external/v1/pay-order/...`)·판매자정보(`/external/v1/seller/...`) 그룹은 호출 시 `GW.AUTHN`("요청을 보낼 권한이 없습니다")을 반환한다.

- `GW.AUTHN` = 토큰 문제가 아니라 **그 API 그룹이 앱에 미허용**. 사용자가 커머스API센터(어드민) → 애플리케이션 → API 사용 권한에서 해당 그룹을 추가해야 열린다. 이건 사용자만 할 수 있으니, 이 오류가 나면 추측으로 우회하지 말고 사용자에게 "그 API 그룹 권한을 앱에 추가해야 한다"고 알린다.
- `GW.NOT_FOUND` = 경로 오류. `references/endpoints.md` 또는 공식 인덱스에서 정확한 경로를 확인한다.

## 엔드포인트 찾기

자주 쓰는 경로와 권한 현황은 `references/endpoints.md`를 읽는다. 거기 없는 엔드포인트나 정확한 파라미터·바디 스키마는 공식 레퍼런스에서 확인:
https://apicenter.commerce.naver.com/docs/commerce-api/current

## 쓰기 작업 시 안전수칙

상품 수정·주문 처리처럼 스토어 상태를 바꾸는 호출(PUT/POST/DELETE)은 되돌리기 어렵다. 실행 전 무엇을 바꾸는지(대상 상품번호, 바뀌는 필드/값)를 사용자에게 한 줄로 확인받고 진행한다. 상품 수정은 먼저 GET으로 현재 객체를 받아 바꿀 필드만 교체해 그대로 PUT 하는 게 안전하다 (전체 객체를 요구하는 엔드포인트가 많음).
