---
name: android-app-builder
description: 안드로이드 앱을 아이디어부터 Google Play Console 검토 제출까지 끝내는 단일 스킬. 새 앱 개발은 컨텍스트로 분기 — **게임**(탭/플래피/아케이드/러너/닷지)은 Phaser 4 + Vite + Capacitor로, **그 외 유틸/생산성 앱**은 네이티브 Kotlin으로 만든다. AdMob 수익화·스토어 에셋(폰 프레임+카피 스크린샷)·Play Console 등록·검토 제출까지 한 스킬에서 처리하고, 기존 앱 업데이트(새 버전 AAB·등록정보·그래픽 수정)와 읽기 전용 조회(리뷰·평점·트랙·versionCode·등록정보 현황)도 포함한다. 사용자가 "안드로이드 앱 만들자", "탭 게임/플래피 같은 거 만들어줘", "코틀린 앱 만들어서 플레이스토어까지", "Play Store에 올려줘", "새 버전 AAB 업로드", "스토어 등록정보 수정", "AdMob 광고 붙여줘", "내 앱 리뷰/평점/트랙 상태 봐줘" 같이 *안드로이드 앱 개발·게임 개발·Play Store 등록/업데이트/조회·앱 수익화* 중 무엇이든 말할 때 발동. 모든 dev 작업은 happylife2080100@gmail.com 계정 + GCP 프로젝트 claude-for-android로 통일. 단순 아이디어 검증만 원하면 stress-test-idea, 등록정보 카피 최적화만 원하면 aso-audit를 직접 쓴다. iOS·Swift·순수 웹앱·Unity·Godot는 이 스킬이 아니다.
---

# Android App Builder — 아이디어 → Play Console 검토 제출 (단일 스킬)

게임이든 유틸이든, 신규든 업데이트든, 안드로이드 앱 일을 한 스킬에서 끝낸다. 구현 디테일은 `references/`에 두고 필요할 때만 읽는다(progressive disclosure). 글로벌 CLAUDE.md의 goal-driven 원칙을 따른다 — 각 단계는 다음으로 넘어가기 전 **검증 가능한 결과물**을 확인한다.

## 라우팅 — 제일 먼저 컨텍스트로 분기

| 사용자 의도 | 경로 |
|---|---|
| 리뷰·평점·트랙·versionCode·등록정보 **현황 조회** | `references/play-read.md` + `scripts/play_read.py`. 빌드 흐름 없이 바로 답. |
| **기존 앱 업데이트** (새 버전 AAB·등록정보·그래픽) | `references/play-submit.md`의 "기존 앱 수정" — 100% API, Chrome 안 씀. |
| **신규 앱 전체 빌드** | 아래 0→3 단계 흐름. |
| **AdMob만 붙이기** | §1.5 직행. |

작업 시작 시 TodoWrite로 해당 경로의 단계를 등록하고, 완료 즉시 체크한다.

## 공용 사실 (단일 출처 — 모든 경로가 여기서 읽는다)

- **dev 계정**: `happylife2080100@gmail.com` (개발자명 happylife2080, devId `8303647010319569479`) — Play Console·AdMob·Cloud Console 전부 동일.
- **GCP 프로젝트**: `claude-for-android` (authuser=1). API 인증 셋업은 `references/google-cloud-setup.md`(1회, 앱 무관).
- **서비스 계정 키**: `~/.config/play-publisher/sa.json` · SA `play-publisher@claude-for-android.iam.gserviceaccount.com`
- **실행 venv**: `~/.config/play-publisher/venv/bin/python`
- **신규 repo**: 앱마다 `kirin765/<app-name>` 새로 생성(아래 1.0). 키스토어·`sa.json`·`local.properties`는 커밋 금지.

---

## 0단계: 인텍트 — 한 장짜리 spec

코드 전에 아래를 확정. 대화에 이미 있으면 추출해 확인만, 모르면 묻는다(추측 금지).

| 항목 | 설명 |
|------|------|
| 앱 한 줄 정의 | "누구를 위한 무슨 앱" |
| 앱 유형 | **게임 / 유틸·생산성·기타** (개발 경로를 가른다) |
| MVP 핵심 기능 | 최소 1~3개. 그 이상 금지(범위 팽창 방지) |
| 타겟 | 한국/글로벌, 연령대 |
| 제약·데이터 거동 | 오프라인 전용? 인터넷 권한? 로그인? **데이터 수집/전송? 광고(AdMob)?** (개인정보 티어를 가른다) |
| 패키지명 | `com.<dev>.<app>` |
| 앱 이름 | 한국어(기본) + 영어 |

아이디어가 미검증이고 사용자가 "이거 될까"류 불확실을 보이면 코드 전에 `stress-test-idea`를 권한다(사용자가 "그냥 만들어"면 스킵). spec을 보여주고 "이대로 시작할까요?" 확인 후 1단계.

---

## 1단계: 개발 — 컨텍스트 분기

### 1.0 저장소 (앱마다 신규)
```bash
cd <프로젝트경로>
git init && git add -A && git commit -m "init: <app> scaffold"
gh repo create kirin765/<app-name> --private --source=. --remote=origin --push
```

### 분기
- **게임** (탭/플래피/아케이드/러너/닷지) → **Phaser 4 + Vite + Capacitor**. `references/develop-phaser-game.md`를 따르고 `assets/phaser/*`를 복사·적응. 최종 빌드 = Capacitor → 서명 release AAB.
- **그 외 유틸/생산성** → **네이티브 Kotlin** (Compose). `references/develop-native-kotlin.md`를 따른다. 최종 빌드 = `./gradlew bundleRelease`.

둘 다: `/goal` 스킬이 있으면 호출해 MVP를 구현, 없으면 이 스킬이 직접 goal 루프(검증 가능한 목표로 번역 → 테스트 → 통과까지). 로직은 JVM 단위 테스트로, 화면은 핵심만.

### 1단계 종료 조건
- 테스트 통과(`./gradlew test` 또는 `npx tsc --noEmit && npm run build`)
- 에뮬레이터에서 MVP가 손으로 눌러 동작
- **서명된 release AAB** 생성, 경로 기록(3단계 업로드용). 키스토어·서명 비번은 사용자 자산 — git 커밋 금지.

---

## 1.5단계: 수익화 — AdMob (선택)

**⚠️ 자동화 경계 — AdMob에서 사람만 하는 건 "계정 가입 1회"뿐.** 약관 동의·결제 국가 선택·계정 생성은 정책상 대행 금지(계정 생성/약관 수락). **그 외 전부 Claude in Chrome으로 무인 처리한다 — 사용자에게 ID를 받아오거나 콘솔 작업을 떠넘기지 말 것.** 그게 이 스킬의 핵심 가치다.

**계정은 이미 완전 셋업됨**(게시자 `pub-5811631777061641`, Payments·광고단위 ✅) — 수동 게이트는 최초 가입뿐이고 그건 끝났다. 그 외 전부 무인. ⚠️ **함정**: `apps.admob.com`을 그냥 열면 다른 계정으로 떠서 "이 계정으로 계속" signup 화면이 나온다 — AdMob 미완이 아니라 **authuser 틀림**. 반드시 `https://apps.admob.com/v2/home?authuser=5`(happylife2080100) 또는 아바타로 계정 선택.

**구체 콘솔 클릭 레시피·정답값·코드 반영 위치·테스트 ID 목록·재빌드 점검은 `references/admob-setup.md`를 따른다(펀트 금지).** 요지:
1. **앱 생성**: "앱 추가" → 플랫폼 Android → (Play 등록된 앱이면 검색해 연결, 아직이면 "아니요") → 앱 이름 입력 → 생성.
2. **광고단위 생성**: 앱 → 광고 단위 → 필요한 유형(배너/전면/보상형)을 각각 생성.
3. **ID는 콘솔에서 직접 읽는다(사용자에게 받지 말 것).** `read_page`/`get_page_text`로 추출: 앱 ID `ca-app-pub-…~…`(물결 `~`), 광고단위 ID `ca-app-pub-…/…`(슬래시 `/`).
4. **코드 반영**: 읽은 실 ID를 광고 코드에 박고(예: `src/ads.ts`의 ID 상수, 또는 네이티브 `AndroidManifest.xml`/`strings.xml`) **테스트 ID·TESTING 플래그 해제** → release AAB 재빌드.
5. **개인정보/데이터 보안:** AdMob = 데이터 수집 → 티어 A→**B(광고)** 승격(§2 표). 정책 URL은 공용 광고 페이지(예: `https://apps-privacy-one.vercel.app/ads.html`). Play 데이터 보안에 「기기 또는 기타 ID」 광고 목적 수집·공유 + "광고 포함" 선언.
6. (선택) `admob_api.py` OAuth 1회 인증 → 출시 후 수익/광고단위 조회.

연동 코드 위치: **Capacitor 게임** → AdMob Capacitor 플러그인(`src/ads.ts` 류, 배너=메뉴·게임오버 하단·플레이 중 숨김, 전면=게임오버 N판마다); **네이티브 Kotlin** → Google Mobile Ads SDK.

---

## 2단계: 에셋 — 폰 프레임 + 카피 스크린샷

스토어 컷은 항상 **"스마트폰 목업 프레임 + 헤드라인 카피"** 마케팅 컷. raw 캡처 그대로 올리지 않는다.
1. **raw 캡처**: 네이티브/게임 모두 에뮬레이터에서 `adb exec-out screencap`으로 1080×1920(`references/develop-native-kotlin.md`의 "에뮬레이터 스크린샷").
2. **프레임+카피 합성**: `references/asset-scripts.md`의 "폰 프레임 + 카피 스크린샷"(raw를 HTML에 박아 `page.setContent`→1242×2208 렌더). 헤드라인은 §2.5 `aso-audit` 결과(한국어 기본).

같은 폴더(`~/Downloads/<app>-store-assets/`)에 아이콘 512·피처 1024×500·스크린샷을 모아 3단계 업로드를 한 번에 묶는다.

### 개인정보처리방침 URL — 데이터 거동 티어로 분기 (앱 유형 무관)
정책 내용은 유틸/게임이 아니라 **무엇을 수집/공유하느냐**가 결정한다. 대부분 공통 2개로 수렴:

| 티어 | 거동 | URL |
|---|---|---|
| **A. 무수집** | 전송·광고·분석·로그인·결제 없음, 기기 내 저장만 | `https://apps-privacy-one.vercel.app` (기존 공용, 재사용) |
| **B. 광고(AdMob)만** | AdMob 외 수집 0 (광고ID·기기정보, 광고/측정) | **공용 광고 URL** — `~/apps-privacy`에 광고 티어 페이지 추가 후 1회 배포, 모든 광고앱 공유 |
| **C. 그 외 수집** | 분석·계정·클라우드·IAP·서버 전송 | 앱별 신규 Vercel URL(`public/privacy.html` 배포) |

**규칙: 선택 URL의 명시 내용 = 그 앱의 Play 데이터 보안 선언과 일치**(불일치 시 반려). AdMob을 붙이면 자동으로 A→B. 분석/계정 등이 끼면 C(앱별). C는 이 repo의 `public/`에 두고 Vercel 연결 배포.

---

## 2.5단계: ASO — `aso-audit` 호출
등록정보 텍스트(앱이름·간단한 설명 ≤80·자세한 설명 ≤4000·키워드)와 스크린샷 헤드라인은 직접 작문하지 말고 **`/aso-audit`을 호출**해 ko/en 최적화 카피를 받아 그대로 쓴다. **언어 정책(항상): 기본 ko-KR + en-US 항상 추가.**

---

## 3단계: 제출 — `references/play-submit.md`
업로드·이미지·등록정보·트랙·출시노트·검토제출(`edits.commit`)은 전부 **Play API(`play_upload.py`)** 무인. **Chrome 콘솔은 API에 엔드포인트가 없는 신규-앱 3가지에만** — ① 앱 최초 생성 ② 콘텐츠 선언 10개 ③ 카테고리.

**최초 신규 제출 처리** (흔한 오해 — "첫 제출은 API로 안 됨"): 앱 생성·선언·카테고리는 원래부터 콘솔이고, **첫 AAB는 `releaseStatus:"draft"`로 API 업로드가 됨**(2026-06 실증). 만약 Google이 첫 바이너리를 거부하면 Chrome은 바이너리 업로드가 영구 차단이므로 **사용자가 콘솔에서 첫 AAB 1회만 수동 업로드** → 이후 전부 API. 정답표·금지목록·deep-link 값은 `references/play-submit.md`.

### 완료 기준
Play Console 상태가 **"검토 중인 변경사항"**이 되면 완료. 검토 제출(`--commit`)은 공개 게시로 이어지는 비가역 동작 — 0단계에서 사용자가 **"출시까지" 명시**했을 때만. 아니면 dry run "validate OK"에서 멈추고 확인받는다. 완료 후 Telegram 1회 알림(글로벌 CLAUDE.md).

---

## 인계 우선 원칙

| 필요 | 누가 |
|------|------|
| 아이디어 검증(불확실할 때만, 0단계 전) | `stress-test-idea` |
| 개발 goal 루프 | `/goal` 있으면 호출, 없으면 자체 |
| 게임 Phaser 구현 / 네이티브 Kotlin | 이 스킬(`references/develop-*.md` + `assets/phaser/`) |
| 스크린샷 프레임+카피 합성 | 이 스킬(`references/asset-scripts.md`) |
| ASO 카피 | `aso-audit` (2.5단계) |
| Cloud/Play/AdMob API 셋업 | 이 스킬(`references/google-cloud-setup.md`, 1회) |
| Play 등록·업로드·검토제출·조회 | 이 스킬(`references/play-submit.md`·`play-read.md` + `scripts/`) |

새로 구현하려는 충동이 들면 먼저 위에서 이미 있는지 확인한다.
