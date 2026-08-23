---
name: cafe24-app-test
description: 카페24 앱의 E2E·스모크 테스트를 CDP로 실행하는 워크플로우 — 설치 완주(OAuth)·삭제 후 재설치·"앱 관리하기" 재접속·Admin API 실측·웹훅 검증. 개발자센터 "앱 테스트" 버튼으로 테스트 몰에 설치하고 실제 흐름을 검증한다. "카페24 앱 테스트", "E2E 돌려줘", "스모크", "설치 안 되는데", "앱 실행이 랜딩만 나와요", "테스트 몰에 설치" 류 요청에 발동. cafe24-app-dev(개발 절차)와 짝 — 개발 후 이 스킬로 검증.
---

# Cafe24 App E2E / Smoke Test — 운영 카드

> 카페24 앱(리뷰이사·순수익·계측기 3종)에서 **실측으로 얻은** 테스트 절차와 함정.
> 카페24 앱은 반복 패턴(OAuth 설치·launch hmac·Admin API·웹훅)이라 스모크·E2E 테스트를 **새 앱마다** 만들어 쓰지 말고 이 스킬로 재사용한다.

## 0. 핵심 원칙

1. **테스트 설치 한도가 유한하다** — 몰별이 아니라 **앱 전체 누적**(기본 5회, 문의로 증설). 테스트를 최소 호출로 설계하고, 반복 실패는 코드 버그일 가능성이 높다(한도 소진 탓으로 오판 금지).
2. **CDP(브라우저)로 실제 흐름 검증** — 개발자센터 콘솔 → "앱 테스트" → 테스트 몰 설치 → 동의 → 콜백 → 대시보드. 스크립트로 hmac URL을 만들어 curl 검증과 병행.
3. **함정은 실측으로 기록** (TEST-GUIDE의 6가지 함정 — 아래 §5). 새 앱에서 재발하면 이 문서에 추가.
4. **⚠️ 에이전트 자체 QA 금지 (2026-08-21)**: 이 스킬의 CDP E2E·설치·실발송 QA는 **사람(개발자)이 실행**한다. 에이전트는 원인 판정용 읽기(코드·env·설정 조회)와 QA.md 작성까지만 하고, 설치·동의·재접속·SMS 실발송 반복 실행을 자동으로 돌리지 않는다 — 설치 한도를 태우고 세션이 오래 끈다. 사용자가 QA를 요청하면 QA.md 기반 체크리스트를 넘겨주고, 사용자가 직접 돌린 결과를 받는다.

## 1. 사전 조건

- Chrome CDP 9222 (`curl -s http://localhost:9222/json/version` — 응답 확인)
- 카페24 개발자센터 로그인 (`.env`의 `CAFE24_CONSOLE_ID/PW`)
- 테스트 몰 2개 (`.env`의 `CAFE24_TEST_MALL_1/2` — onnurimun·onnuri2test)
- **테스트 설치 한도 잔여 확인** — 개발자센터 콘솔에서 확인, 소진 시 문의 게시판에 리셋/증설 요청
- 앱이 등록·배포돼 있고, App URL·Redirect URI·Scope가 콘솔 값과 일치 (불일치 시 hmac 401)

## 2. 테스트 환경

`.env` (⚠️ 절대 커밋 금지 — git auto-push → GitHub 노출):

```
CAFE24_CONSOLE_ID / CAFE24_CONSOLE_PW   # 개발자센터
CAFE24_TEST_MALL_1 / CAFE24_TEST_MALL_2 # 테스트 몰
CAFE24_TEST_ADMIN_ID / CAFE24_TEST_ADMIN_PW
```

앱별 시크릿(`CAFE24_CLIENT_ID/SECRET/REDIRECT_URI/WEBHOOK_KEY`)은 **앱 프로젝트의 `.env`** 에 있다 — 이 스킬이 읽는다.

## 3. 테스트 시나리오 (앱별로 실행)

### S0. 사전 점검 — 검색 노출 확인 (계측기 게이트 선행)

스토어 검색 REST로 앱이 검색에 뜨는지 확인 (리뷰이사 교훈 — 등록=노출 아님):

```bash
curl -s "https://store.cafe24.com/kr/filter/rest/apps?page=1&order=SALES_DESC&filter=%7B%22q%22%3A%5B%22%EC%95%B1%EB%AA%85%22%5D%7D&s=%EC%95%B1%EB%AA%85" -H 'User-Agent: Mozilla/5.0' | grep -o "앱명"
```

미노출 시: 인덱스 반영 대기 또는 의도적 비노출(예: PG 심사 중)인지 개발자센터 확인.

### S1. 최초 설치 완주 (OAuth) — 스모크 필수

CDP로 실제 흐름:
1. 개발자센터 → 앱 관리 → **테스트 실행** → 테스트 몰 ID 입력 → 실행
2. App URL(`/api/auth/install`) → hmac 통과 → OAuth authorize 307
3. 동의 화면에서 **동의**
4. 콜백 → `/admin` 307 → 대시보드 렌더
5. 통과 기준: 콜백 307 · `/admin`에 UI+몰 ID 표시 · DB에 토큰 저장 · Vercel 로그 200

### S2. hmac URL 직접 검증 (curl — 한도 안 씀)

```bash
node scripts/make_launch_url.mjs <mall_id> <app_url> <secret>
# 예상: 토큰 있음→307 /admin, 없음→307 OAuth, hmac 불일치→401
```

### S3. "앱 관리하기" 재접속 — OAuth 안 타는지 (3회 반려 교훈)

설치된 몰 관리자 → 앱 관리하기 → **즉시 /admin 307** (OAuth 동의 화면이 뜨면 실패). 이 경로는 테스트 한도 소모 안 함.

### S4. 삭제 후 재설치 — 웹훅이 토큰 지우는지 (2회 반려 교훈)

몰에서 앱 삭제 → 웹훅 수신 → 토큰 폐기 확인 → 재설치 완주.

### S5. Admin API 실측 (앱별 데이터 포인트)

- 주문 목록·상품 목록·재고(`embed=variants,inventories`)·게시판 등 **앱이 쓰는 리소스만** 실측
- 개인정보 필드(`fields`)를 요청하지 않는지 확인 (심사)

### S6. 스모크 체크리스트 (출시 전 필수)

- [ ] launch 파라미터(`hmac`·`mall_id`·`timestamp`) 없이 `/` 방문 → **랜딩만 나오면 안 됨** — install로 리다이렉트해야 함 (실측 버그: App URL을 랜딩으로 등록하면 실행해도 랜딩만)
- [ ] hmac 불일치 → 401
- [ ] timestamp ±2시간 밖 → 401
- [ ] OAuth 콜백 error → HTML 안내 페이지 (raw JSON 금지)
- [ ] 토큰 자동 갱신 (액세스 2시간) — 만료 5분 전 갱신
- [ ] 웹훅 삭제 → 토큰 폐기
- [ ] `X-Cafe24-Api-Version` 헤더 고정
- [ ] API 실측 값이 UI에 반영 (실데이터 1건)

## 4. 스크립트

- `scripts/make_launch_url.cjs` — hmac launch URL 생성 (S2)
- `scripts/smoke.sh` — S0+S6 스모크 자동 실행 (curl 기반, 한도 안 씀)
- `scripts/e2e_cdp.cjs` — CDP E2E (개발자센터·몰 접속, S1 보조)
- `scripts/register_app.cjs` — 개발정보 설정·Secret 발급 (CDP). **신규 앱 등록은 수동 (§4.5)**

## 4.5 개발자센터 신규 앱 등록 (⚠️ 수동 — CDP 금지)

> **2026-08-20 규칙 확정: 신규 앱 등록은 CDP 자동화를 쓰지 않고 사용자가 수동으로 한다.**
> 자동화를 시도하면 위험한 실측 2건이 있었다:
> 1. **등록 모달 input이 `product_name` → `app_name`으로 바뀌어** `register_app.cjs new`가 실패(클라이언트 id 미발급)했다.
> 2. **이전 앱의 client id가 그대로 반환되는** 함정 — 기존 앱(cafe24-profit)의 개발정보 링크를 새 앱으로 오인해,
>    스토어 등록(STEP 03)을 **이전 앱의 콘텐츠로 덮어쓰는 사고**가 났다. (cafe24-stock 세션 실측)
> → 등록은 사용자 수동으로: `admin/apps/front/manage` → **ADD PRODUCT** → Web 유형 → 관리 상품명 입력 → 저장.
> 앱 생성 후 **Client ID를 사용자에게 받아** `.env`에 기록한다. `register_app.cjs new`는 사용하지 않는다.

### 개발정보 설정 (App URL·Redirect·Scope·심사체크)

```bash
node scripts/register_app.cjs config <client_id> <app_url> <redirect_uri>
# → App URL·Redirect 입력, 심사 체크리스트 4개 체크, 저장
```

- **실측 필드**: `app_url`(text) · `redirect_url`(textarea) · 심사 체크리스트 checkbox 4개
  (① Redirect URI 일치 구현 ② 인증코드→액세스토큰 교환 ③ 갱신토큰 재발급 ④ 가이드 동의).
- **Scope (권한선택)**: "권한선택 (쇼핑몰 운영자)" — 카테고리 select `#select_authority` + 권한 select(`select.authority_mode`).
  ⚠️ **함정 C5**: 카테고리를 바꿔도 권한 select가 안 따라간다 (DOM에 이미 추가된 카테고리 select만 남음).
  **신규 앱은 `#select_authority`를 `option:selected`로 바꾼 뒤** `#js-add-authority` 클릭 — `addScopes(선택값)` 호출.
  Playwright `selectOption`으로 실제 selectedIndex를 바꾼 뒤에만 클릭이 `addScopes('product')`를 호출한다 (실측 2026-08-20).
  그리고 **저장 후 리로드로 확정** — 저장 안 하면 scope가 사라져 `invalid_scope`로 설치가 거부된다.
  재고 앱 = `mall.read_product`(상품) + `mall.read_store`(상점). 필요한 권한만 — 초과 권한은 심사 거부.
- **WebHook 등록도 수동**: 이벤트 90077(앱 삭제)·90078(앱 만료) → `https://<app>.vercel.app/api/webhook/app`.
  검증코드(`CAFE24_WEBHOOK_KEY`)는 개발정보 화면의 WebHook 검증코드를 복사해 env에 넣는다.

### 개발정보 설정 (App URL·Redirect·Scope·심사체크)

```bash
node scripts/register_app.cjs config <client_id> <app_url> <redirect_uri>
# → App URL·Redirect 입력, 심사 체크리스트 4개 체크, 저장
```

- **실측 필드**: `app_url`(text) · `redirect_url`(textarea) · 심사 체크리스트 checkbox 4개
  (① Redirect URI 일치 구현 ② 인증코드→액세스토큰 교환 ③ 갱신토큰 재발급 ④ 가이드 동의).
- **Scope (권한선택)**: "권한선택 (쇼핑몰 운영자)" — 카테고리 `select.fSelect` nth(1) + 권한 select nth(2).
  ⚠️ **함정 C5**: 카테고리를 바꿔도 권한 select가 안 따라간다 → **권한 select를 직접 `mall.read_xxx`로 설정** 후 "추가". 그리고 **저장 후 리로드로 확정** — 저장 안 되면 코드가 요청하는 scope가 콘솔에 없어 `invalid_scope`로 설치가 거부된다.
  재고 앱 = `mall.read_product`(상품) + `mall.read_store`(상점). 필요한 권한만 — 초과 권한은 심사 거부.

### Client Secret 발급

```bash
node scripts/register_app.cjs secret <client_id>
# → "Client Secret Key 보기" 클릭 → 값 확보
```

⚠️ Secret은 `.env`(커밋 금지)에 저장. 절대 git에 커밋하지 않는다 (auto-push → GitHub 노출).

## 4.6 심사 제출 — 테스트 계정 메일 발송 (필수)

> 리뷰이사 전례 (2026-07-28): 심사팀 **eco_bizops@cafe24corp.com**에 메일을 보내면 당일 회신.
> 앱마다 테스트 관리자 계정을 **메일 본문에 명시**해야 심사역이 직접 테스트한다.

**메일 발송 내용 (필수 3종):**
1. **Client ID** — 앱 식별
2. **테스트 방법** — 설치 단계별 절차 (심사 체크리스트 4개가 구현됐음을 보여주는 시나리오)
3. **테스트 관리자 계정** — `test2onnuri@cafe24.com` (리뷰이사 제출 시 사용, 저장됨)

**테스트 계정 준비 규칙:**
- 개발자센터/몰 어드민 로그인은 E2E·스모크 테스트에서 **테스트 관리자 계정으로** 수행
- 이 계정은 심사 메일에도 그대로 기재 → 심사역이 같은 계정으로 직접 테스트 가능
- 계정 정보는 `.env`에 보관 (커밋 금지)

## 5. 알려진 함정 (전부 실측 확인됨)

| # | 함정 | 증상 | 해결 |
|---|---|---|---|
| 1 | Vercel env 비어 있음 | hmac 401, OAuth URL 깨짐 | 실제 값으로 재세팅 |
| 2 | `%20` vs `+` 인코딩 | `invalid launch request` | `searchParams`→`encodeURIComponent` 재조립 |
| 3 | 테스트 설치 한도는 **앱 전체 누적** | 새 몰도 `install limit` | 콘솔 문의로 리셋/증설 |
| 4 | 웹훅이 토큰 지우면 "앱 관리하기"도 재동의 | 재접속이 OAuth 탐 | 재접속 검증 전 토큰 살아있는지 |
| 5 | `isTokenLive` 과민 | 네트워크 오류를 죽은 토큰으로 오판→OAuth 반복→한도 소진 | 401/403만 죽음으로 판정 |
| 6 | `c24_mall` 쿠키 10분 만료 | 콜백 `code/mall_id missing` | `state`에 mall_id 내장 + 쿠키 1시간 |
| 7 | `expires_at` KST | timestamptz UTC로 9시간 밀림 | `+09:00` 붙여 저장 |
| 8 | 주문 상태 N코드 필드 없음 | 전 주문 누락 | `paid`/`canceled` 플래그로 판정 |
| 9 | 목록 `embed=items` 빈 배열 | 품목 누락 | 주문별 `GET /orders/{id}/items` |
| 10 | `product_no` 숫자 타입 | Map 키 문자열과 불일치 | `String(product_no)` 정규화 |
| 11 | **App URL 랜딩 버그** | 실행해도 랜딩만 | 랜딩이 launch 파라미터 받으면 install로 리다이렉트 |
| 12 | **앱 간 토큰 테이블 공유** | 두 앱이 서로 덮어씀 | 앱마다 테이블 분리 |

### CDP 조작 함정 (2026-08-20 실측 — 개발자센터 자동화)

| # | 함정 | 증상 | 해결 |
|---|---|---|---|
| C1 | **`.mjs`에서 `require`** | `ERR_MODULE_NOT_FOUND`·`ReferenceError: require is not defined`·`ERR_AMBIGUOUS_MODULE_SYNTAX` | CDP 스크립트는 **`.cjs`** (CommonJS)로 작성. `require(process.env.HOME + '/.local/pw/node_modules/playwright')` |
| C2 | **로그인 폼 선택자** — `input[type=text]`가 hidden을 먼저 잡음 | fill이 보이지 않는 요소에 타임아웃 | 개발자센터 로그인 = `#idLoginId`·`#idLoginPasswd`. 몰(eclogin) 로그인 = `#mall_id`·`#userpasswd` |
| C3 | **개발자센터 직접 URL 접근 시 세션 만료** | `develop?client_id=...` 직행이 로그인 페이지로 리다이렉트 | `developers.cafe24.com/` → 어드민 버튼 확인 → 그 후 페이지 이동. 로그인 세션은 쿠키 유지 |
| C4 | **scope 권한 select가 카테고리를 안 따라감** | `select.fSelect` nth(1)을 '상품(Product)'으로 바꿔도 nth(2)는 여전히 `mall.read_order` 옵션 | ✅ **해결 (2026-08-20)**: 권한 select는 **카테고리별로 이미 전부 존재**한다. `nth(2)`=상품(`mall.read_product`)·`nth(3)`=주문·`nth(4)`=상점. 카테고리 select(nth 1)를 바꾸면 **권한 select는 그대로**(이미 그 카테고리 것). "추가"는 **카테고리 select 값 + 해당 권한 select 값** 조합을 추가. 카테고리를 product로 두고 nth(2)를 그대로 두면 상품이 추가된다 |
| C5 | **scope "추가" 후 저장이 커밋 안 됨** | 테이블에 상품이 보여도 **리로드하면 사라짐** → 코드의 `mall.read_product` 요청이 `invalid_scope` | 저장 버튼 = `button.js-btn-save`(type=submit). 추가 → 저장 → **리로드로 확정** 3단계 필수. 자동화가 안 되면 **수동으로 한 번** (카페24 콘솔 UI가 React 상태를 자동화에서 놓칠 수 있음 — 2026-08-20 실측) |
| C6 | **`textContent`로 버튼 찾으면 숨김 버튼에 걸림** | `실행` 버튼이 x=0,y=0 (visible:false)에 매칭 | **`offsetParent` 유무로 visible 필터** + 실제 테스트 실행은 `a.btnSubmit.eModal` 링크 (상단 "저장 테스트 실행" 그룹) |
| C7 | **새 탭 대신 기존 탭 리로드** | 탭이 계속 쌓임 | `ctx.pages().find(p=>p.url().includes(...))` 재사용, 없을 때만 newPage |
| C8 | **STEP 03 판매정보 폼 — `page.fill`이 일부 필드에 안 먹힘** | `#js-brief_description`(대표설명) 등 `data-name` 직렬화 필드가 저장 안 됨 | React/직렬화 value setter로 값 주입 + `input`/`change` 디스패치. 저장 후 **재로드로 확정** |
| C9 | **메타태그 추가 — `dispatchEvent` Enter가 안 먹힘** | `KeyboardEvent` 디스패치로는 행이 안 늘어남 | `page.keyboard.type` + `page.keyboard.press('Enter')` **실제 키 입력**만 동작. 추가는 네트워크 호출 없이 행만 늘리고, `a.js-save-storeinfo`가 커밋 |
| C10 | **스크린샷 업로드 — `setInputFiles` 직접 주입이 안 먹힘** | 파일이 반영 안 됨 | **"등록/변경" 버튼(`js-btn-screenshot-crud`) 클릭 + `filechooser` 이벤트**로 업로드. 삭제는 `data-crud="d"` 클릭 → 저장 |
| C11 | **대표아이콘 업로드 — 파일 input이 레이어 안에 있음** | `input[type=file]`가 노출돼 있지 않음 | `.eLayerClick[href="#layerDelegateImage"]`로 레이어 열기 → `#js-image-upload-editor` 파일 주입 → `#js-icon-editor-submit` |
| C12 | **FAQ 삭제/등록 — confirm·모달** | 삭제 시 confirm, 등록 시 `#layerFAQregister` 모달 | 삭제: 체크박스(`.js-app-faq-no`) → `.js-btn-faq-del` → **`dialog` 이벤트 자동 수락**. 등록: `#js-btn-faq-open-layer`로 모달 → `#js-faq-title`·`#js-faq-contents` → `#js-btn-faq-submit` |
| C13 | **STEP 03 저장 버튼** | `저장` 텍스트 버튼이 여럿 | **`a.js-save-storeinfo`** 클릭 → `POST /admin/apps/action/storeinfo`. FAQ 저장은 `#js-btn-faq-submit`(별도) |

> **설치 흐름 (테스트 실행)**: 개발정보 → 상단 `a.btnSubmit.eModal`("테스트 실행") 클릭 → 모달에 `#js-mall-id`(쇼핑몰 ID) 입력 → 실행 → **새 탭에 eclogin 몰 로그인**(`#mall_id`·`#userpasswd`) → OAuth 동의 → `/api/auth/callback` → `/admin`.
>
> **스토어 등록 (STEP 03 판매정보, `admin/apps/front/detail`)**: 폼이 **cafe24-profit의 콘텐츠로 이미 채워진 채** 클론돼 있다 (복제 유산). 심사 전 이 앱 것으로 전부 교체 — 판매명(`input[data-name="display_name"]`)·대표설명(`#js-brief_description`)·샘플사이트·메인타이틀(`input[name="main_title[]"]`)·핵심포인트(`input[data-name="key_pointN"]`)·메타태그(C9)·상세설명(Froala, `#detailed_description` value 직접 주입)·FAQ(C12)·이미지(C10·C11). 에셋 제작 = cafe24-review/cafe24-profit의 `store-assets/` 파이프라인 재사용 (Playwright 2x 렌더 → `public/store/detail-NN.png` → Vercel 배포 후 상세설명에 URL).
> ⚠️ 이 흐름은 **테스트 설치 한도(앱 전체 누적)를 소모**한다 — 실패 반복 전에 코드·scope·URL을 먼저 확인 (C5가 한도 소진의 흔한 원인).

## 6. 게이트 연동 (계측기 3종)

계측기 앱(재고·운송장·장바구니)은 [[cafe24-instrument-apps-2026-08-20]]의 게이트를 따른다:
- 출시 전: S0(검색 노출) + S6(스모크) 통과
- 출시 후 2주: 설치 ≥30 AND D7 재방문 ≥15 (개발자센터 콘솔 판독 — 외부 비공개)
- 판정: GO → Pro 전환, KILL → 슬롯 종료

## 7. 이 스킬의 한계

- **설치 수·사용량은 외부 비공개** — 개발자센터 콘솔에서만 판독 (판매순 SALES_DESC는 대용 지표, [[cafe24-app-metrics-2026-08-20]])
- 테스트 한도 소진 시 설치 관련 시나리오(S1·S3·S4)는 콘솔 문의 후 재시도
