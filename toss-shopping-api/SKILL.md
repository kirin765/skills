---
name: toss-shopping-api
description: Call the Toss Shopping Open API (토스쇼핑 오픈 API / 토스쇼핑 파트너스) for the user's own store using the registered Access/Secret Key. Use this skill whenever the user wants to read or change anything in their Toss Shopping store via API — browse categories(카테고리 조회), register/list/edit/delete products(상품 등록·목록·조회·수정·삭제), change sale/origin price or stock(판매가·정상가·재고 수정), show/hide products(노출 상태 변경), query orders(주문 조회·주문내역), change order status or register invoices(주문 상태·송장 등록·배송정보), handle claims(클레임·취소·반품·교환 승인/거절/완료), manage delivery groups and return locations(배송비 묶음·교환반품지), look up seller penalties/holidays(페널티·휴무일), or pull settlement(정산 내역) — even if they don't name the API. Trigger on phrases like "토스쇼핑 API", "토스쇼핑 상품 등록/조회/수정", "토스쇼핑 주문 가져와", "토스쇼핑 재고/가격 바꿔줘", "토스쇼핑 정산", "토스 파트너스 API", "Toss Shopping API". This handles OAuth2 token issuance/caching and Bearer auth for you via a bundled script. IMPORTANT GOTCHA: Toss enforces an IP allowlist tied to the key — calls only work from the IP registered when the key was issued (218.237.176.17), otherwise access is denied regardless of a valid token.
---

# 토스쇼핑 Open API

토스쇼핑 본인 스토어 데이터를 공식 Open API로 읽고/수정하는 스킬. OAuth2 토큰 발급·캐시·Bearer 인증은 번들 스크립트가 처리하므로, 너는 엔드포인트(메서드·경로·바디)만 고르면 된다.

## 준비물 (이미 설정됨)

- 자격증명: `~/.toss-shopping.env` (chmod 600) — `TOSS_ACCESS_KEY`, `TOSS_SECRET_KEY`. SKILL.md·git에 시크릿을 절대 넣지 말 것.
- 클라이언트: `scripts/toss_shopping.py` — 표준 라이브러리만 쓰므로 시스템 `python3`로 바로 실행한다 (venv·외부 패키지 불필요).
- 토큰 캐시: `~/.toss-shopping-token.json` (chmod 600). 토스 토큰은 유효기간이 길고(약 1년) 과도한 재발급은 이용이 제한될 수 있어, 스크립트가 만료 임박/401 일 때만 새로 발급한다. 손대지 말 것.

## ⚠️ IP 허용목록 (가장 흔한 실패 원인)

토스쇼핑 키는 **발급 시 등록한 IP에서 온 요청만 허용**한다. 등록 안 된 IP에서 호출하면 토큰이 유효해도 막힌다.

- 현재 등록 IP는 `218.237.176.17` (사용자 머신)이다.
- 접근 거부(403/`FORBIDDEN` 류)가 나면 서명이 아니라 **IP 문제**다. 추측으로 우회하지 말고 사용자에게 알린다: 토스쇼핑 파트너스 → 가맹점·계정 관리 → 자체 개발에서 호출 머신의 공인 IP를 등록하거나, 등록된 IP에서 호출해야 한다.

## 기본 사용법

```bash
cd ~/.claude/skills/toss-shopping-api
PY=python3

# GET (쿼리는 --query 로 준다)
$PY scripts/toss_shopping.py GET "/api/v3/shopping-fep/products/v2" --query size=20

# POST / PUT (JSON 바디)
$PY scripts/toss_shopping.py POST "/api/v3/shopping-fep/products/hide" --body '{"productIds":["..."]}'
$PY scripts/toss_shopping.py PUT  "/api/v3/shopping-fep/product-items/{id}/sale-price" --body '<json>'
$PY scripts/toss_shopping.py POST "<path>" --body @/path/to/body.json   # 큰 바디는 파일로

# DELETE
$PY scripts/toss_shopping.py DELETE "<path>" --body '<json>'

# 토큰 강제 발급 후 출력 (디버그)
$PY scripts/toss_shopping.py token
```

- `<path>`는 `/api/v3/shopping-fep/...` 부터의 경로. 호스트(`https://shopping-fep.toss.im`)는 스크립트가 붙인다.
- 경로의 `{productId}`, `{claimId}` 등은 실제 ID로 직접 치환해서 넘긴다.
- 응답 JSON을 그대로 출력하고, 2xx면 exit 0 / 그 외 exit 1. gzip 응답은 자동 해제한다.
- 테스트(alpha) 환경은 `--env test` (또는 env 파일에 `TOSS_ENV=test`). 기본은 prod.

## 엔드포인트 찾기

경로·메서드·필수 파라미터는 호출 전 `references/endpoints.md`를 읽는다. 거기 없거나 바디 스키마(특히 상품 등록)가 불확실하면 공식 문서에서 확인:
- 개발자 문서: https://shopping-docs.toss.im/dev
- 각 페이지에 전체 OpenAPI 스펙(JSON)이 들어있어 `.md`로 바로 조회 가능. 예:
  `curl -sL https://shopping-docs.toss.im/dev/api-2/product.md`
- 상품 등록 필드 상세: https://shopping-docs.toss.im/dev/api-1/register-product

## 쓰기 작업 시 안전수칙

상품 등록/수정/삭제, 가격·재고 변경, 노출 상태 변경, 주문 상태 변경·송장 등록, 클레임 승인/거절처럼 스토어 상태를 바꾸는 호출(POST/PUT/DELETE)은 되돌리기 어렵다. 실행 전 무엇을 바꾸는지(대상 식별자, 바뀌는 필드·값)를 사용자에게 한 줄로 확인받고 진행한다. 상품 수정은 먼저 GET으로 현재 객체를 받아 바꿀 필드만 교체해 PUT 하는 게 안전하다. 클레임 승인/완료 같은 상태 전이는 순서·전제조건이 있으니 목록 조회로 현재 상태를 먼저 확인한다.
