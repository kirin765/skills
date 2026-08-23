# AdMob 무인 셋업 — Claude in Chrome 콘솔 레시피

§1.5의 실행 디테일. **목표: 사용자에게 ID를 받거나 콘솔을 떠넘기지 않는다.** 가입 1회만 사용자, 그 뒤는 전부 여기 레시피대로 Claude in Chrome.

## 계정 사실 (happylife2080100 — 헌팅 금지)
- AdMob **이미 셋업 완료**(2026-06 확인): Payments ✅, 광고단위 ≥1개 존재, 앱 존재. 가입·결제 다 끝남 — **추가 수동 게이트 없음**.
- AdMob 게시자 ID: **`pub-5811631777061641`** (앱/광고단위 ID는 `ca-app-pub-5811631777061641~…` / `…/…` 형태)
- 국가 대한민국 · 통화 USD · 개인 · 김기완 · AdSense 연결됨.

## ⚠️ authuser 강제 — 제일 흔한 함정
`apps.admob.com`을 그냥 열면 **다른 계정(gksrkdls1982 등)으로 열려** "이 계정으로 계속 하시겠습니까?" signup 게이트가 뜬다. 이건 "AdMob 미완"이 아니라 **잘못된 계정**이다. 반드시 happylife2080100로:
- URL에 **`?authuser=5`** 붙여 진입: `https://apps.admob.com/v2/home?authuser=5` (이 Chrome에서 happylife2080100=authuser 5, 2026-06 실증 — 단 프로필마다 다를 수 있으니 우상단 아바타 툴팁으로 `happylife2080100@gmail.com` 확인).
- 잘못된 계정이면 우상단 아바타 → 계정 선택기에서 happylife2080100 선택.
- 올바른 계정이면 바로 홈 대시보드("AdMob에 오신 것을 환영합니다", 총 예상 수입 등)가 뜬다.

## 유일한 수동 게이트
- **최초 계정 가입**(약관·결제국가·계정생성) — 대행 금지. **이미 완료됨**(위). 새 dev 머신/계정이 아닌 한 다시 필요 없음.
- 그 외 전부 무인. (signup "계속" 화면을 보면 → 가입 미완이 아니라 authuser 틀린 것부터 의심.)

## 앱 생성 (무인)
1. `apps.admob.com` → 왼쪽 **앱(Apps)** → **앱 추가(ADD APP)**.
2. 플랫폼 **Android** 선택.
3. "앱이 지원되는 앱스토어에 등록되어 있나요?" →
   - Play에 이미 만든 앱이면 **예** → 앱 이름/패키지로 검색해 선택(스토어 데이터 자동 연결).
   - 아직이면 **아니요** → 앱 이름 직접 입력.
4. **앱 추가** → 생성 완료 화면에 **앱 ID** `ca-app-pub-5811631777061641~XXXXXXXXXX`(물결 `~`) 표시. `read_page`/`get_page_text`로 추출해 기록.

## 광고단위 생성 (무인 — 필요한 유형마다 반복)
1. 그 앱 → **광고 단위(Ad units)** → **광고 단위 추가(ADD AD UNIT)**.
2. 형식 선택: **배너(Banner)** / **전면(Interstitial)** / **보상형(Rewarded)** — 앱 설계에 맞게.
3. 광고 단위 이름 입력(예 `banner-main`, `interstitial-gameover`) → **광고 단위 만들기(CREATE)**.
4. 완료 화면에 **광고 단위 ID** `ca-app-pub-5811631777061641/ZZZZZZZZZZ`(슬래시 `/`) 표시. 추출해 기록.
5. 다른 유형도 1~4 반복.

> ID 표가 안 보이면 앱 → 광고 단위 목록에서 각 행의 ID 열을 `read_page`로 읽는다. 절대 사용자에게 묻지 말 것.

## 코드 반영 (읽은 실 ID로 — 테스트 ID 교체)
**Capacitor 게임**(`@capacitor-community/admob`):
- **앱 ID** → `android/app/src/main/AndroidManifest.xml`의 meta-data
  `com.google.android.gms.ads.APPLICATION_ID` 값(테스트 `ca-app-pub-3940256099942544~3347511713` → 실 앱 ID).
- **광고단위 ID** → 광고 코드(예 `src/ads.ts`)의 `banner`/`interstitial`/`rewarded` 상수.
- **테스트 플래그 해제**: `USE_TEST`/`isTesting`/`TESTING` = **false**, 테스트 ID 상수 제거.
  (Google 테스트 ID: 앱 `…~3347511713`, 배너 `…/6300978111`, 전면 `…/1033173712`, 보상형 `…/5224354917` — 이게 남아있으면 교체 누락.)

**네이티브 Kotlin**(Google Mobile Ads SDK):
- 앱 ID → `AndroidManifest.xml` 동일 meta-data. 광고단위 ID → `strings.xml` 또는 코드 상수. `MobileAds` 테스트 기기/테스트 ID 해제.

## 재빌드 + 검증
- Capacitor: `npm run build && npx cap sync android && (cd android && ./gradlew bundleRelease)`.
- 네이티브: `./gradlew bundleRelease`.
- 교체 누락 점검: `grep -rn "3940256099942544\|isTesting *= *true\|USE_TEST *= *true" src android/app/src/main` → 결과 없어야 함.
- 산출 AAB로 §3 제출. **개인정보 티어 B**(`apps-privacy-one.vercel.app/ads.html`) + Play 데이터안전 「기기 또는 기타 ID」 광고 수집·공유 + 콘텐츠선언 "광고 있음".

## 출시 후 조회 (선택)
`scripts/admob_api.py` — 첫 1회 OAuth 동의(`~/.config/play-publisher/admob_oauth_client.json` + 토큰). 이후 앱·광고단위·수익 리포트 읽기.
