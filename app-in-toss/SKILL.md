---
name: app-in-toss
description: Build, deploy, and monetize Apps in Toss (앱인토스) mini-apps end to end. Use this skill whenever the user wants to do anything with 앱인토스 / Apps in Toss / "토스 미니앱" / "App In Toss" — build the .ait bundle (앱 번들), register/deploy/submit the app in the 앱인토스 콘솔, fill the 앱 정보 or 챌린지 신청폼, set up monetization (인앱 결제 IAP 상품 · 전면/리워드/배너 인앱 광고 with 광고 그룹 ID), decide where to place ads, wire TossAds/GoogleAdMob/IAP/Promotion/Share SDK calls in a WebView or React Native project, test via QR/CI-CD/샌드박스, or measure a payment gate. Triggers: "앱인토스", "앱 인 토스", "App in Toss", "Apps in Toss", "토스 미니앱", ".ait 빌드", "미니앱 배포", "토스 IAP", "토스 광고 그룹", "혜택탭 프로모션". This skill never stores console credentials, API keys, or promotion codes — such values live only in the user's local env files (e.g. .env.local, npx ait token) and must never be written into the skill or committed.
---

# 앱인토스 (Apps in Toss) 미니앱 — 빌드 → 배포 → 제출 → 수익화

토스 앱 안에 웹뷰/React Native 미니앱을 올리는 플랫폼. `.ait` 번들을 만들어 콘솔에 올리고, 검토 → 출시까지 가는 전 과정과 수익화(인앱 결제 + 인앱 광고 3종)를 한 스킬로 다룬다.

운영 원칙 3가지:

1. **앱 번들은 코드로 만들고, 시크릿은 코드 밖에 둔다.** API 키·프로모션 코드·토큰은 `.env.local`(gitignore) 또는 `npx ait token`에만 둔다. 스킬과 git에 절대 넣지 않는다.
2. **검수는 숫자 싸움이다.** 앱 정보 검토 1~2영업일, 버전 검토 최대 3영업일(카테고리에 따라 7일+). 물리적 병목(사업자 등록 · 검수)이 게이트를 잠식하므로 역산해서 시작한다.
3. **측정은 채널과 오퍼를 나눈다.** 유입(혜택탭 프로모션·푸시)과 전환(결제)을 한 숫자로 섞지 않는다. 게이트가 결제액이면 분모(마케팅 도구 집행)를 사전에 고정하고, 광고·결제 성과는 별도 지표로 본다.

## 언제 쓰는가 (트리거)

- `.ait` 빌드, 번들 업로드, 테스트, 검토 요청, 출시, 롤백
- 콘솔 앱 등록 / 앱 정보(기본 정보·카테고리·노출·등급분류) 작성·검토 요청
- 챌린지(바이브코딩) 신청폼 작성·출품
- 인앱 결제 상품 등록 / IAP SDK 연동
- 인앱 광고: 광고 그룹 생성, 광고 그룹 ID 수집·코드 배선, 전면·리워드·배너 배치 설계
- 마케팅: 혜택탭 프로모션(Promotion.grantReward), 스마트 발송(푸시), 공유 리워드

## 작업 흐름

### 1단계 — 입력 수집

- 프로젝트 디렉터리(웹뷰: Vite/웹빌드, 또는 React Native)와 `appName`(영문, `intoss://` 스킴, **등록 후 변경 불가**)
- 콘솔 접속 여부: 토스 비즈니스 계정(만 19세+, 본인 명의 토스 앱) · 워크스페이스(사업자당 1개) · 사업자 등록/정산 정보 상태
- 게이트가 정해진 베팅이면: kill 숫자와 분모(혜택탭 프로모션 1회 + 세그먼트 푸시 등)를 확인하고 흐리지 않는다

### 2단계 — `.ait` 빌드

1. 프로젝트 루트에 `apps-in-toss.config.ts` 확인 (`defineConfig` from `@apps-in-toss/web-framework/config`). 필수는 `appName`. 그 외 `brand.primaryColor` · `permissions` · `webView` · `webBundleDir`(기본 `dist`).
2. 빌드 명령 실행 (웹뷰): `npm run build` → vite 빌드 + `ait.js build`가 `.ait` 생성. 패키지 스크립트로 묶어 두는 걸 권장(예: `"build:ait": "npm run build && node node_modules/@apps-in-toss/web-framework/bin/ait.js build"`).
3. 산출물 검증 — `scripts/ait-build.sh` 실행: `.ait` 존재 · `bundle.json`·`project-package.json` 포함 · appName 일치 · 압축 해제 기준 100MB 이하 · `node_modules`/시크릿 미포함.
4. `.ait`는 zip 구조: `sources/**`(빌드 결과) + `bundle.json`(deploymentId·config·SDK 버전) + `project-package.json`.

### 3단계 — 테스트 (출시 전 검증)

| 경로 | 방법 | 언제 |
|---|---|---|
| 콘솔 QR | 콘솔 → 버전 업로드 → '테스트하기' → QR → 토스 앱(워크스페이스 멤버·만 19+) | 기본. **테스트 1회 이상 완료해야 검토 요청 활성화** |
| CI/CD | `npx ait token add` 후 `npx ait deploy -m "메모"` (또는 `npx ait deploy --api-key {키}`) | 반복 배포 |
| 샌드박스 앱 | 전용 앱 설치(Android 7+/iOS 16+). **3.x는 샌드박스 앱 미제공 — devtools로 브라우저 개발** | 로그인·토스페이·인앱결제·리더보드 테스트. **인앱 광고·분석·공유리워드는 샌드박스 불가** |

테스트 환경 주의:
- IAP는 샌드박스에서 테스트 가능. **인앱 광고는 샌드박스 불가 → 콘솔 QR로 테스트, 반드시 테스트용 광고 그룹 ID 사용**(운영 ID로 테스트하면 제재).
- CORS: SDK 3.x는 실서비스 `https://<appName>.web.tossmini.com`, QR 테스트 `https://<appName>.private-web.tossmini.com`. 힌트: 2026-08-25 이후 업로드되는 SDK 3.x 번들은 `apps.tossmini.com` Origin으로 서빙된다는 안내가 있음 — 배포 시점 문서에서 재확인할 것.
- iOS 서드파티 쿠키 차단 → 쿠키 로그인 금지, 토큰 인증 사용. 라이브는 HTTPS만.

### 4단계 — 콘솔 제출 (앱 정보 + 챌린지 신청폼)

- 앱 등록: 앱 이름(한글 노출명 + 영문명 규칙), `appName`, 앱 유형(게임/비게임). → `references/console-submission.md`
- 앱 정보: 부제 · 상세 설명('접속→행동→결과' 흐름) · 고객문의 이메일 · 카테고리 · 앱 로고(600×600 PNG, 배경 필수) · 썸네일(게임, 1932×828) · 스크린샷(세로 636×1048 최소 3장 / 가로 1504×741 최소 1장) · 리더보드(게임)
- 게임 등급분류: Play 출시작이면 스토어 URL + 자체등급분류 게임물 정보(등록자명·사업자명·분류일자·분류번호·이용등급·내용정보·인감/사인·플레이 화면 2+2). 등록자명≠사업자명이면 반려. → `references/console-submission.md`
- 채점/출품(챌린지): 신청폼의 appName은 **콘솔과 정확히 일치**해야 함. → `templates/submission-form.md`로 데이터 작성
- 미리 채울 데이터가 있으면 `templates/submission-form.md` 템플릿을 채워 제출 전 검토.

### 5단계 — 수익화 설계 (IAP + 광고 3종)

**인앱 결제 상품** — `references/monetization.md`
- 유형: 소모품 / 비소모품 / 자동 갱신 구독. 상품 수 제한: 게임 80, 비게임 30.
- 상품명(과장 금지) · 이미지 1024×1024 · 공급가(400~1,400,000원, 10원 단위, VAT 제외 — 판매가는 자동 계산)
- 수수료: 앱마켓 15% + 토스 5%. 환불: iOS는 Apple 전권, Android는 콘솔 승인/반려(최종 Google Play).
- SDK: `IAP.createOneTimePurchaseOrder({ options: { sku, processProductGrant }, onEvent, onError })` — 지급은 orderId 키로 멱등 처리.

**인앱 광고 3종 + 광고 그룹 ID** — `references/monetization.md`
- 콘솔 → 광고 그룹 생성(유형 선택: 전면형/리워드/배너, 리워드는 보상명·수량 입력, 미디에이션 자동) → **상세 화면에서 광고 그룹 ID 확인**(구글 등록까지 최대 2시간).
- 광고 그룹 ID를 받으면 **그룹별로 배치를 결정**한다(아래 표). ID는 코드 상수 또는 `VITE_*_AD_GROUP_ID` env로 배선해 dev/live 전환을 쉽게 한다.
- 개발 테스트용 공식 ID: 전면 `ait-ad-test-interstitial-id` · 리워드 `ait-ad-test-rewarded-id` · 배너(리스트형) `ait-ad-test-banner-id`.

| 광고 | 특성 | 배치 원칙(어디에, 왜) | eCPM·노출 |
|---|---|---|---|
| 전면형 | 강제 노출 | 화면 전환·레벨 완료·결과→다음 단계 같은 자연스러운 멈춤 지점. **인트로/로딩/컷신/팝업 금지**(출시 가이드). 프리로드 후 show — `load → show → (다음 load)` | 노출 중간 · eCPM 중간 |
| 리워드 | 자발적 시청, 집중도 최고 | 보상 순간: 부활, 추가 생명/하트, 보너스, '광고 보고 혜택'. **시청 완료(userEarnedReward)에만 보상** — 클릭 보상은 정책 위반 | 노출 낮음 · eCPM 최고 |
| 배너 | 상시 노출, 자동 트래픽 | 메인/리스트/플레이 화면 상단 또는 하단 고정(96px 컨테이너). 게임 조작 영역·CTA 인접 배치 금지, 동일 화면 동일 포맷 2개 금지 | 노출 최다 · eCPM 최저 |

- 광고 그룹 이름 규칙(운영 편의): `{지면}_{유형}` — 예: `게임종료_전면`, `리바이브_리워드`, `홈_배너`.
- 정책(위반 시 광고 제한·정산 보류): Ad 표기 유지 · SDK 이벤트 변조 금지 · 광고 영역 refresh 금지 · 보상·참여형 클릭 유도 금지 · 광고 은닉/겹침 금지 · 광고 재생 중 앱 사운드 일시정지.
- **IAP와 광고의 상충 설계**: 리워드 광고가 소모품 매출을 잠식한다. 같은 가치(예: 하트)를 광고로 공짜 주면 IAP 판매가 죽는다 — 광고는 소액/일회성 보상, IAP는 대량/영구 가치로 분리하거나, 광고 보상과 결제 상품을 다른 재화로 나눈다.
- SDK 패턴: `loadFullScreenAd`/`showFullScreenAd`(v3, adGroupId 기반 — 광고 타입은 **그룹 ID로 자동 결정**) + 구형 `GoogleAdMob.loadAppsInTossAdMob`/`showAppsInTossAdMob`(v2 폴백). 배너는 `TossAds.initialize` → `TossAds.attachBanner(groupId, container, { theme, variant, callbacks })`. 앱 밖(브라우저)에서는 전부 no-op 처리. → `references/sdk-notes.md`

**Promotion/혜택탭** (유입 분모 도구)
- `Promotion.grantReward({ promotionCode, amount })` — 코드는 `VITE_PROMOTION_CODE` 등 env에서 읽는다. 테스트 코드(TEST_...)는 샌드박스 전용, 실제 코드로 교체·재배포 필요.
- 프로모션 등록(예산·기간) → 분모 실측. 스마트 발송(푸시) 세그먼트는 조건 조합(성별·연령·거래·활동)으로 구성. 푸시 문구는 creative-review API로 검증(서비스명 그대로/임의 축약/명령형 거부 — '명사형~하기'만 통과하는 경우가 많음).

### 6단계 — 출시 + 사후

- 검토 요청은 테스트 1회 완료 후 활성화, 한 번에 한 버전. 반려 시 '반려 사유 보기' → 새 번들 재업로드. 출시하기 → 전체 사용자 즉시 반영. 롤백 가능(앱 출시 메뉴). 사후 검수·긴급 운영 중단 가능.
- 출시 후 모니터링: 로그·Sentry·API 실패율·신고 내역. 광고 성과(노출·eCPM·예상수익, 매일 10시 갱신), IAP 성과(D+1 8시, 결제율·재결제).

### 7단계 — 업로드/발행 전 시크릿 감사 (반드시)

어떤 코드든 커밋·업로드 전에 `scripts/audit-secrets.sh <디렉터리>` 실행:
- `.env*` · `*.pem` · `*.key` · `*.jks` · `*.p12` · `keystore.properties` 파일 존재 여부
- `sk-` · `AKIA` · `-----BEGIN` · `client_secret` · `api[_-]?key` · `password` · `token` · `Bearer` 등 시크릿 패턴
- 긴 hex/base64 문자열(광고 그룹 ID처럼 보이는 값 포함 — 프로젝트별 ID는 빌드 산출물이나 env에만 두고 스킬/공용 위키에는 넣지 말 것)
경고가 나오면 파일을 정리한 뒤 다시 검사하고, 그래야 커밋한다.

## 참조 파일

- `references/console-submission.md` — 콘솔 가입·워크스페이스·앱 등록·앱 정보 필드·게임 등급분류·검토/출시 절차 (공식 문서 요약)
- `references/monetization.md` — IAP 상품 규칙 + 광고 3종·광고 그룹·배치·정책 + 기여 구조
- `references/sdk-notes.md` — `@apps-in-toss/web-framework` API 패턴, env 감지, .ait 구조, CORS, 실측 게이트 규칙
- `templates/submission-form.md` — 앱 정보/챌린지 신청폼 채우기 템플릿
- `scripts/ait-build.sh` — .ait 빌드+검증
- `scripts/audit-secrets.sh` — 업로드 전 시크릿 감사

## 시크릿 규칙 (이 스킬 자체의 금지 목록)

- 콘솔 API 키, OAuth 토큰, 프로모션 코드 값, 결제 키, 개인정보 — 본 문서·references·scripts·templates 어디에도 값 형태로 넣지 않는다. 환경변수 이름만 참조한다.
- 사용자의 프로젝트별 광고 그룹 ID·SKU 이름은 이 스킬에 하드코딩하지 않는다. 예시는 공식 테스트 ID 또는 `위치_유형` 형식의 자리표시자만 쓴다.
- `audit-secrets.sh`는 파일·패턴 검사만 하고 값 자체를 로그에 남기지 않는다.