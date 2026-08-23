---
name: cafe24-app-dev
description: 카페24(Cafe24) 앱스토어 앱 개발 — OAuth 설치·Admin API·심사 제출까지의 검증된 절차와 함정을 담은 운영 카드. "카페24 앱 만들기", "카페24 API 연동", "cafe24-review", "cafe24-profit", "앱 실행이 랜딩만 나와요", "카페24 심사" 류 요청에 발동. 쿠팡 API는 coupang-api, 스마트스토어는 naver-commerce-api 스킬.
---

# Cafe24 App Development — 운영 카드

> 이 저장소의 Cafe24 앱(리뷰이사 `cafe24-review` · 순수익 `cafe24-profit`)에서 **실측으로 얻은** 절차와 함정.
> 공식 문서(developers.cafe24.com)와 원장(brain)의 기록을 재사용. 함정은 대부분 실제로 겪어서 수정한 것들.

## 0. 핵심 구조

```
카페24 앱 = Web App (Next.js + Vercel) + Postgres(토큰 저장) + Admin API
몰 관리자 "앱 실행" → App URL + launch 파라미터(hmac·mall_id·timestamp) → install 라우트 검증
  → OAuth 동의 → /api/auth/callback → 토큰 저장 → /admin 대시보드
```

- 개발자 등록: **개인사업자 가능** (네이버 커머스솔루션마켓은 법인만이라 닫힘). 개인·개인사업자·법인 모두 가능.
- 수수료: 판매대금의 **20%** (실수령 = 가격 × 0.8). 월 정산(익월 말).
- 심사: 준법성·완성도·유해성·선정성. 반려 시 당일 재제출로 1일 내 왕복 가능(리뷰이사 2회 반려 모두 당일 해결).
- 스토어 설치 수는 **외부 비공개** — 개발자센터 콘솔에서만 판독.

## 1. 앱 등록 (개발자센터)

- 유형 **Web**. App URL + Redirect URI + Scope를 설정.
- **App URL — ⚠️ 함정(실측 버그)**: 몰 관리자 "앱 실행" 시 카페24가 launch 파라미터(`hmac`·`mall_id`·`timestamp`)를 **App URL 뒤에 붙여** 보낸다. 이걸 처리하는 건 `/api/auth/install` 라우트다. **App URL을 랜딩(`/`)으로 등록하면 실행해도 랜딩만 나온다.**
  - 해결책 ①: App URL = `https://<app>.vercel.app/api/auth/install` 로 등록.
  - 해결책 ②(추천, 견고): **랜딩(`/`)이 launch 파라미터를 받으면 install 라우트로 리다이렉트** — App URL이 랜딩이든 install이든 동작. `cafe24-profit/src/app/page.tsx` 참고:
    ```tsx
    if (hmac && mall_id && timestamp) redirect(`/api/auth/install?hmac=...&mall_id=...&timestamp=...`);
    ```
  - **⚠️ 함정 ②'(2026-08-21 실측 — hmac 401의 함정)**: 해결책 ②의 리다이렉트가 **`hmac·mall_id·timestamp` 3개만** 골라 이어붙이면, 카페24가 보낸 나머지 파라미터(`is_multi_shop`·`lang`·`nation`·`shop_no`·`user_id`·`user_name`·`user_type`)가 사라져 **hmac 서명 검증이 깨진다** — 카페24는 **전체 파라미터에 서명**한다. 증상: "앱 관리하기" 실행이 `invalid launch request`, 직접 `/api/auth/install`로 만들면 통과(파라미터 전체 유지라서). **랜딩은 모든 쿼리 파라미터를 그대로 보존해서 리다이렉트**해야 한다. (cafe24-cart 실측으로 발견 — 스톡은 App URL을 `/api/auth/install` 직접 등록이라 겉으로 안 보였다)
- **Redirect URI** = `https://<app>.vercel.app/api/auth/callback`
- **Scope**: 최소로. 순수익 앱 = `mall.read_store,mall.read_order`. 리뷰 앱 = `mall.read_store,mall.read_product,mall.read_community,mall.write_community,mall.read_application,mall.write_application`(위젯 scripttags용). **필요한 것만** 요청해야 심사·동의 마찰이 적다.
- **Client ID/Secret**: 앱마다 별도. `cafe24.ts`에서 `process.env.CAFE24_CLIENT_ID!` 등으로 읽는다.

## 2. 설치(launch) — hmac 검증 (심사 필수)

App URL로 온 요청에서:
- `hmac`: 파라미터를 **알파벳순 정렬**(`hmac` 제외)한 원본 쿼리스트링을 client secret으로 HMAC-SHA256 → base64. URLSearchParams로 파싱 후 `encodeURIComponent`로 재조립해 서명 원문 복원(공백 `%20` → `+` 정규화 함정 — 실측 401).
- `timestamp`: ±2시간 이내여야 함 (Replay Attack 방어).
- 검증 통과 → OAuth authorize URL로 리다이렉트 + `c24_state`(CSRF)·`c24_mall` 쿠키 설정. state에 `mallId:uuid`를 담아 쿠키 만료에도 몰 복원.
- 저장 토큰이 살아있으면 재동의 없이 바로 `/admin`. 죽은 토큰이면(401/403) 재동의로. ⚠️ 네트워크 오류·5xx를 "죽음"으로 오판하면 테스트 설치 한도(기본 5회)를 태워 반려될 수 있음.

## 3. OAuth + 토큰 (리뷰이사 코드 재사용 `src/lib/cafe24.ts`·`token.ts`)

- authorize: `https://{mall}.cafe24api.com/api/v2/oauth/authorize?response_type=code&client_id=...&redirect_uri=...&scope=...`
- token: `POST /api/v2/oauth/token` (Authorization: Basic base64(client:secret))
- **`expires_at`은 타임존 없는 KST** — Postgres timestamptz가 UTC로 읽어 9시간 밀리는 버그 실측. `+09:00` 붙여 저장.
- 액세스 2시간 / 리프레시 2주. 만료 5분 전 자동 갱신.
- **⚠️ 앱마다 토큰 테이블을 분리** (`cafe24_token` vs `cafe24_profit_token`). 같은 테이블 공유 시 같은 몰에 두 앱이 설치되면 서로 토큰을 덮어쓴다 — 실측 버그.
- 개인정보 필드(구매자명·연락처·주소)는 `fields` 파라미터로 **요청조차 하지 않는다** (개인정보보호법·심사).

## 4. Admin API — 실측 포인트

| 항목 | 값 |
|---|---|
| Base | `https://{mall}.cafe24api.com/api/v2/admin` |
| 버전 헤더 | `X-Cafe24-Api-Version: 2026-03-01` — **고정 필수**. 안 박으면 카페24가 최신으로 붙여 조용히 깨짐 |
| 주문 목록 | `GET /orders?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=100&offset=0&fields=...` |
| 주문 검색 범위 | **한 호출에 3개월 이내** (그보다 크면 422). 월 단위 요청이면 무해 |
| **주문 기간 필수 ⚠️** | `start_date`·`end_date` **둘 다 필수** — 하나만 주면 422 `parameter.end_date`. (2026-08-21 실측 — 장바구니 계측기 스윕이 `end_date` 누락으로 전 이탈 판정 실패) |
| **주문 상태 ⚠️** | 응답에 `order_status`(N코드) **필드가 없다.** `paid`("T"=결제완료)·`canceled`("T"=취소) 플래그로 판정해야 한다 (실측 버그: N코드 필드를 읽어 전 주문이 누락). item 레벨에만 `order_status`·`status_code`가 있음 |
| **품목 조회 ⚠️** | 목록 API의 `embed=items`는 **빈 배열을 반환**한다. 주문별 `GET /orders/{order_id}/items`로 조회해야 한다. 품주 `payment_amount`=품주별 실결제금액, `product_no`·`product_name`·`quantity` |
| 상품별 분석 | `GET /orders/{id}/items` → 품주별 `product_no`·`product_name`·`quantity`·`payment_amount` |
| **매출통계 API** | `read_salesreport`는 **"특정 클라이언트만 사용 가능(개발센터 문의)"** 제한. 순수익은 주문 API로 집계하면 됨 — 심사 마찰 회피 |

## 5. 심사 제출 (리뷰이사 2회 반려 교훈)

- **상세 설명 이미지 필수** (반려 1순위) — 대시보드·기능 화면 스크린샷 3~5장. 실데이터 없는 몰은 **데모 데이터 모드**(`?demo=1`, 합성 데이터·세션 불필요)로 캡처.
- 기능 완성도: 심사역이 직접 테스트함. 파라미터 누락(작성일·평점 등) 반려 사례 있음.
- 개인정보처리방침 URL 필수.
- 심사팀 eco_bizops@cafe24corp.com에 Client ID·테스트 방법·샘플 데이터 메일 발송 → 당일 회신 가능.
- 반려 대기 일수만큼 게이트 순연 (brain 원장 규칙).
- **아이콘·피처 이미지 — ⚠️ 이전 앱 에셋 혼입 함정 (2026-08-20 실측)**: 개발자센터의 앱 아이콘·피처 이미지 업로드는 앱마다 개별인데, **새 앱을 만들 때 이전 앱(cafe24-profit·cafe24-review)이 쓴 이미지를 그대로 올리면 이전 앱 에셋이 그대로 남아 심사에 들어간다.** 프로젝트 복제로 시작할 때 `store-assets/`·`public/store/` 폴더가 **이전 앱 것**인지 먼저 확인(URL이 이전 앱 도메인을 가리키는지)하고, 이 앱 전용 아이콘·피처·상세 이미지를 새로 만들어 업로드한다. 실측: cafe24-stock 프로젝트의 `store-assets/`·`public/store/*.png`가 cafe24-review(`cafe24-review-gamma.vercel.app`) 것임.

## 6. 테스트 방법

- 테스트 몰에 주문이 없으면 대시보드가 빈 상태. **실데이터 검증 = 스토어프론트에서 실주문 1~2건 생성**(무통장입금 → 관리자 입금확인) → status 코드·집계 확인.
- 데모 모드(`?demo=1`)로 전체 UI·상품별 이익·광고비 미리보기.
- launch 테스트: client secret으로 직접 hmac 계산해 launch URL을 만들어 검증 가능 (테스트 전용).

## 7. 새 앱 QA.md (필수 산출물)

- **새 카페24 앱 개발을 시작하면 앱 저장소 루트에 `QA.md`를 만들어 쓴다** — 사람(개발자)이 직접 돌리는 수동 QA 체크리스트. 출시·스토어 등록 전 필수 통과 관문.
- 항목은 이 앱의 실제 동작(보안·설치·재접속·데이터·토큰·웹훅·검색노출)에서 뽑고, **설치 한도(앱 전체 누적 기본 5회) 소모 여부를 항목마다 표기**하고, 항목별 통과 기준을 기대값으로 적는다.
- 원형: `cafe24-stock/QA.md` (§0~§6 시나리오의 수동 버전).
- 개발 완료 후 QA.md 기반 수동 테스트 → cafe24-app-test 스킬(S0~S6)으로 E2E·스모크 보강.

### ⚠️ QA는 사람이 한다 — 에이전트가 CDP로 자체 QA하지 않는다 (2026-08-21 규칙)

- 에이전트(Claude/opencode)는 **QA.md 작성까지만** 한다. **CDP(브라우저 자동화)로 설치·재접속·실발송 QA를 스스로 돌려 반복 디버깅하지 않는다.**
- 이유(실측): ① 테스트 설치 한도(앱 누적 5회)를 에이전트 디버깅이 태운다. ② 카페24 콘솔·몰 DOM이 자주 바뀌어 자동화가 깨지고 한 프리젠스가 오래 끈다(설치 후 "앱 관리하기" launch 파라미터 차이 같은 런타임 이슈는 에이전트가 원인 판정에만 쓰고, 반복 QA는 사람에게 넘긴다). ③ QA는 실데이터(실주문·실장바구니·실SMS)가 필요한데 그건 개발자 계정·몰에서만 가능하다.
- **에이전트의 QA 역할**: 코드·환경변수·배포·스모크(비용 없는 curl 기반 S6)·DB 토큰 저장 확인까지만. **설치·동의·실발송 검증은 사용자(개발자)가 몰에서 직접** 확인하고 결과를 알려준다.
- 의심 버그가 보이면 에이전트는 **원인 판정(코드·환경 실측)과 QA.md에 재현 단계 기록**만 하고, 반복 실행은 사용자에게 맡긴다.

## 8. 이 앱의 함정 메모 (2026-08-19 실측)

- **App URL 랜딩 버그**: 실행해도 랜딩만 나옴 → 랜딩의 launch 리다이렉트로 견고화 (§1).
- **토큰 테이블 공유 버그**: 두 앱이 한 테이블 공유 → 서로 덮어씀 → 테이블 분리 (§3).
- **expires_at KST**: 타임존 안 붙이면 9시간 밀림 → `+09:00` (§3).
- **빈 DATABASE_URL**: Vercel env에 `""` 값이 들어가면 `postgres('')` → 빌드 ERR_INVALID_URL. 빈 값이 아니라 실 값 필요.
- **주문 상태 판정 버그**: `order_status`(N코드) 필드를 읽어 전 주문 누락 → `paid`/`canceled` 플래그로 판정 (§4). 실주문으로 검증.
- **품목 embed 버그**: 목록 API `embed=items` 빈 배열 → `GET /orders/{id}/items`로 주문별 조회 (§4).
- **product_no 타입 버그**: Cafe24가 `product_no`를 **숫자**로 준다. DB 키(Map)가 문자열이면 `Map.get(10)`이 `"10"`을 못 찾아 저장값이 반영 안 됨 → 항상 `String(product_no)`로 정규화할 것.
