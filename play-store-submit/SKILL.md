---
name: play-store-submit
description: Google Play Console에 앱(PWA/TWA·웹게임·네이티브 앱)을 신규 등록하거나 기존 앱을 수정·업데이트(새 버전 AAB, 등록정보 수정 등)하고 프로덕션 검토까지 제출하는 전 과정 워크플로우. 사용자가 "플레이스토어 출시", "Play Store에 올려줘", "안드로이드 앱 등록", "AAB 업로드하고 출시까지", "PWABuilder 패키지 올려줘", "기존 앱 수정", "새 버전 올려줘", "스토어 등록정보 수정" 같은 표현을 쓸 때 발동. **업로드(AAB·이미지)·등록정보·트랙·검토제출은 Chrome이 아니라 Play Developer API(`play_upload.py`)로 무인 처리**하는 게 기본 경로다. 신규 앱의 *앱 생성 + 콘텐츠 선언 10개 + 카테고리*만 API에 없어 Chrome MCP(claude-in-chrome, read-tier) 콘솔 조작으로 하며, 그 부분의 결정적 순서·정답표·ref우선 클릭 규칙을 담는다. 콘솔 클릭은 사용자의 CDP Chrome 세션(Play Console 로그인 상태)에서 수행. 검토 전송은 공개 게시로 이어지는 비가역 동작이므로 사용자가 "출시까지" 명시했을 때만 최종 전송.
---

# Play Store 등록/업데이트 → 검토 제출

PWABuilder가 만든 AAB(또는 임의의 AAB)를 Google Play Console에 등록·업데이트하고 프로덕션 검토까지 보내는 워크플로우. **업로드·등록정보·검토제출은 Play Developer API로 무인 처리**가 기본. Chrome 클릭은 API에 없는 신규-앱 셋업 부분에서만 쓰며, 그때 화면을 일일이 분석하지 않게 **정답표**를 내장한다.

## ⭐ 엔진 선택 — 작업 시작 전 먼저 분기 (제일 중요)

| 작업 | 엔진 | 비고 |
|------|------|------|
| **기존 앱 업데이트** (새 버전 AAB·등록정보·그래픽·검토제출) | **100% API** (`play_upload.py`) | Chrome 안 씀. 아래 "API 경로" 한 방. |
| **신규 앱 — 앱 생성·콘텐츠 선언 10개·카테고리** | **Chrome MCP (콘솔)** | API에 없음. 아래 "콘솔 경로" 2·4·7단계만. |
| **신규 앱 — 맨 처음 AAB 1개** | **사용자 수동(콘솔)** | Play App Signing이 이때만 콘솔에서 잡힘. 이후 버전부터 API. |
| **신규 앱 — 이미지·등록정보·이후 버전·검토제출** | **API** | 콘솔 뼈대 완료 후 전부 API. |

**기본 동작:** 업로드/등록정보/트랙/커밋은 **무조건 API 먼저**. Chrome `file_upload`로 바이너리·이미지를 올리려 하지 말 것(영구 차단, 아래 금지 목록). 신규 앱이라 콘솔 뼈대가 필요하면 그 최소 부분만 Chrome으로 하고 나머지는 API로 넘긴다.

---

# API 경로 (`play_upload.py`) — 업로드·등록정보·트랙·검토제출

브라우저를 안 쓰는 `androidpublisher` v3 REST. 서비스 계정 키로 edit 트랜잭션(insert → 작업 → validate → commit)을 돌린다. 한 edit에 AAB·이미지·등록정보·트랙을 묶어 올린다.

- **스크립트**: `~/.claude/skills/android-app-builder/scripts/play_upload.py`
- **실행 venv**: `~/.config/play-publisher/venv/bin/python`
- **서비스 계정 키**: `~/.config/play-publisher/sa.json` · SA 이메일 `claude-google-play@claude-android-upload.iam.gserviceaccount.com`
- **전체 정의·스키마·셋업**: `~/.claude/skills/android-app-builder/references/play-publishing-api.md`

```bash
# dry run (validate 후 edit 폐기 — 아무것도 반영 안 됨, 항상 먼저 이걸로 확인)
~/.config/play-publisher/venv/bin/python \
  ~/.claude/skills/android-app-builder/scripts/play_upload.py --config <app>.json
# 실제 반영 + 검토 제출 (비가역, 사용자가 "출시까지" 명시 때만 --commit)
… --config <app>.json --commit
```

**설정 JSON 스키마** (필요한 키만 넣으면 됨 — 없으면 해당 작업 스킵):

```json
{
  "packageName": "com.kiwan.quicktodo",
  "aab": "/abs/path/app-release.aab",          // 새 버전 올릴 때만
  "track": "production",                          // aab 있을 때만 적용
  "images": {                                     // imageType별 전량 교체(deleteall→upload)
    "icon": "/abs/icon-512.png",
    "featureGraphic": "/abs/feature-1024x500.png",
    "phoneScreenshots": ["/abs/framed/01.png", "/abs/framed/02.png"]
  },
  "graphicsLanguage": "ko-KR",                    // 이미지는 기본언어에만 올리면 자동 공유
  "listings": {                                   // aso-audit 카피 그대로
    "ko-KR": {"title": "...", "shortDescription": "≤80", "fullDescription": "≤4000"},
    "en-US": {"title": "...", "shortDescription": "...", "fullDescription": "..."}
  }
}
```

**규칙:**
- 항상 **dry run 먼저** → `validate OK` 확인 후에만 `--commit`.
- `--commit` 없이는 edit가 폐기되어 아무것도 반영 안 됨(안전). `--commit`은 검토 전송(비가역)이라 **"출시까지" 명시 때만**.
- 이미지는 imageType별 전량 교체. `phoneScreenshots`는 배열로 2~8장.
- 403이 나면 → 서비스 계정이 그 앱에 Play Console 권한이 없거나 앱/패키지가 아직 없는 것. `play-publishing-api.md`의 "사용자 1회 액션"(API 액세스 링크 + SA 초대) 안내 후 폴백.
- 입력 에셋(아이콘·framed 스크린샷·피처)과 카피는 아래 "에셋·ASO 준비"에서 만든 산출물을 그대로 쓴다.

## 에셋·ASO 준비 (업로드 전 1회 — 신규/그래픽 교체 시)

라이브 앱에서 Playwright로 캡처/생성해 **한 폴더**(`~/Downloads/<app>-store-assets/`)에 모음. 스크립트 예시는 `references/asset-scripts.md`.

- **아이콘 512px**: PWA의 `pwa-512x512.png` 복사 (또는 `npx @vite-pwa/assets-generator --preset minimal public/icon.svg`)
- **스크린샷 2~8장 (폰 프레임 + 카피 문구 — 항상 이 형식)**: raw 그대로 올리지 말 것. ① 라이브 앱 `1080×1920` raw 캡처(`shots/`) → ② 각 raw를 **스마트폰 목업 프레임 + 상단 헤드라인/서브카피 마케팅 컷**으로 합성(`framed/`). HTML 배너를 `page.setContent` 후 `1242×2208`로 렌더해 합성. 헤드라인은 아래 `aso-audit` 결과(한국어 기본)에서. 레시피: `references/asset-scripts.md`의 "폰 프레임 + 카피 스크린샷".
- **피처그래픽 1024×500**: HTML 배너를 `page.setContent` 후 viewport 1024×500으로 `screenshot`.
- **개인정보처리방침**: `public/privacy.html`(한/영, "데이터 수집 없음" 표준문구, 연락 이메일) → git push → 배포 → URL 확정(`https://<app>.vercel.app/privacy.html`). HTTP 200 확인. (URL 입력은 콘솔 4단계 선언에서 사용.)

### ASO 최적화 — `aso-audit` 스킬 호출 (등록정보 텍스트 확정 전 필수)

등록정보 텍스트(앱이름·간단한 설명·자세한 설명)를 짜기 전에 **`aso-audit` 스킬을 먼저 호출**해 한국어·영어 카피를 뽑는다. 기존 앱 수정 시에도 손대기 전 현재 리스팅을 점검 → 개선분만 반영. 산출 카피를 위 config JSON `listings`에 그대로 넣는다. **언어 정책(항상): 기본 ko-KR + en-US 항상 추가.**

---

# 콘솔 경로 (Chrome MCP) — API에 없는 부분만

**언제만:** 신규 앱의 ① 앱 생성(2단계) ② 콘텐츠 선언 10개(4단계) ③ 카테고리/연락처(7단계) ④ 맨 처음 AAB 1개 수동. 그 외 업로드·등록정보·검토제출은 콘솔에서 하지 말고 API로.

## 콘솔 토큰 절약 핵심 규칙 (콘솔 조작 시 준수)

1. **좌표 클릭 금지, ref 클릭 우선.** `find`/`read_page(filter:"interactive")`로 ref를 얻어 `computer{action:"left_click", ref:"ref_N"}`로 클릭. 레이아웃이 바뀌어도 견고하고 스크린샷 불필요.
2. **스크린샷은 "결정 지점·검증"에서만.** 매 batch 끝마다 찍지 말 것. 저장 토스트/다음 단계 진입만 1회 확인.
3. **상태 확인은 `read_page` 텍스트 또는 `javascript_tool`로.** 스크린샷(1.1~1.6k)보다 훨씬 가볍다. 미응답 라디오·버튼 disabled는 JS로.
4. **정답을 미리 안다 → 질문을 읽지 말고 일괄 처리.** 아래 정답표 사용.
5. **바이너리/이미지는 콘솔에서 올리지 말 것.** 맨 처음 AAB 1개(수동)를 제외하면 전부 API(`play_upload.py`). 콘솔 `file_upload`는 영구 차단(아래 금지 목록).

## 업로드 자동화 시도 금지 목록 (콘솔 경로 — 전부 차단 확인됨, 재시도 금지)

바이너리(AAB)·이미지(아이콘·피처·스크린샷)를 **Chrome으로** 올리려는 아래 시도는 모두 안전계층/MCP에 의해 차단된다. **정답은 API(`play_upload.py`)** 이고, 차단된 우회를 다시 시도하지 말 것:

- ❌ Playwright `connectOverCDP` + `setInputFiles` 로컬 스크립트 — "Auto-Mode Bypass" 거부. settings.local.json allow 규칙을 Claude가 추가하는 것 자체가 "Self-Modification"으로 차단됨.
- ❌ `mcp__claude-in-chrome__file_upload` 에 로컬 경로 전달 — "사용자가 이 세션에 공유한 파일만" 받음. 모든 로컬 경로 거부.
- ❌ 네이티브 파일 다이얼로그를 백그라운드/세컨더리 모니터 CDP 탭에서 띄우기 — 제어 탭이 foreground+가시 창이어야만 열림.
- ✅ **맨 처음 AAB 1개**(API로 못 함)만 사용자가 그 탭에서 직접 선택. 나머지(이미지·등록정보·이후 버전)는 전부 API.

## 알려진 값 (이 개발자 계정 — 헌팅 금지, 바로 deep-link)

`/u/N/` 인덱스를 **순차로 돌며 navigate+get_page_text 하지 말 것** (이전 세션에서 u/0~u/5까지 12회 왕복하며 토큰 낭비). devId·appId·package는 **세션·Chrome 프로필과 무관하게 고정**이므로 아래 값으로 곧장 deep-link. 바뀌는 건 `/u/N/`의 N뿐.

- **개발자 계정**: `happylife2080100@gmail.com` (개발자명 happylife2080) · **devId `8303647010319569479`**
- **앱 — 빠른 할 일 / QuickTodo**: `com.kiwan.quicktodo` · **appId `4973743514636442357`**
- 앱 대시보드 직행: `…/u/{N}/developers/8303647010319569479/app/4973743514636442357/app-dashboard`

### 올바른 계정 인덱스(N) 찾기 — 1~2회로 끝낸다
1. `navigate` → `…/console/u/0/developers/8303647010319569479/app/4973743514636442357/app-dashboard`.
2. `get_page_text` 1회. 앱 대시보드가 뜨면 끝(N=0). "계정 만들기/signup"·다른 앱이면 N이 틀린 것.
3. 틀리면 `…/console` 로 가서 **"개발자 계정 선택" 피커의 `happylife2080` 항목을 직접 클릭**(`find`→ref 클릭) — 인덱스 순회보다 항상 싸다. 클릭 후 URL의 `/u/N/`을 읽어 이후 deep-link에 박아 쓴다.

**이 계정이 연결된 Chrome 어디에도 없으면(미로그인·개발자 계정 없음) 추측·계정 생성 금지, 즉시 사용자 핸드오프**("happylife2080100 계정으로 Play Console 로그인 후 알려달라").

## 콘솔 환경 전제

- 사용자의 CDP Chrome(claude-in-chrome MCP)이 Play Console에 로그인돼 있어야 함. `list_connected_browsers` → 사용자에게 어느 브라우저인지 확인(AskUserQuestion) → `select_browser`.
- Chrome은 **read-tier**라 `computer-use`로는 못 누름. 반드시 **claude-in-chrome MCP**(`navigate`, `find`, `computer`)로 조작.

## 0단계: 사전 준비 (PWA라면)

웹앱이 PWA가 아니면 `vite-plugin-pwa`로 manifest+service worker+아이콘 세팅 후 배포. PWABuilder(https://www.pwabuilder.com)에 배포 URL 입력 → AAB+서명키 패키지 다운로드. 패키지 안 `assetlinks.json`에서 `package_name` 확인(예: `app.vercel.<sub>.twa`).

## 2단계: 앱 생성 (콘솔 — API 없음)

`navigate` → `.../developers/<devId>/app-list` → "앱 만들기". 폼: 앱이름, **패키지명**(assetlinks 값), 기본언어(한국어 ko-KR), **앱/게임 중 실제 유형 선택**, **무료** 선택, 선언 체크박스 2개(개발자정책+미국수출법) 체크 → "앱 만들기". 생성 후 URL에서 `<appId>` 확보.

> **앱 vs 게임:** 정답표는 "단순 오프라인 게임" 기준. 일반 앱(생산성·유틸리티 등 비게임)이면: 앱 유형 "앱", 카테고리는 게임 대신 일반(예: 생산성), 콘텐츠 등급 설문도 "게임" 대신 "기타 앱 유형/참조 앱" 흐름. 데이터 보안은 실제 수집/전송에 맞춰(완전 오프라인이면 "수집/공유 안 함"). 인터넷 권한 없는 앱은 자세한 설명에 "인터넷 권한 없음, 모든 데이터 기기 내 보관" 명시하면 심사 수월.

## 3단계: 맨 처음 AAB 1개 (콘솔 — 사용자 수동, 신규 앱 1회만)

프로덕션 트랙 → 새 버전 만들기 → "업로드" 버튼 → **제어 탭이 foreground**인 상태에서 사용자가 그 탭에서 AAB 선택. 출시노트는 한/영 둘 다. **이후 버전부터는 콘솔 말고 API(`play_upload.py`의 `aab`)로.**

## 4단계: 앱 콘텐츠 선언 10개 — 정답표 (콘솔 — API 없음)

`.../app-content/overview`에서 각 "선언 시작" 클릭. 직접 URL은 일부 홈으로 리디렉션되니 overview에서 ref/클릭 진행. **단순 오프라인 게임 정답:**

| 선언 | 답 |
|------|-----|
| 개인정보처리방침 | URL 입력(준비단계 배포본) |
| 광고 | 아니요, 광고 없음 |
| 광고 ID | 아니요 |
| 앱 액세스(로그인 세부정보) | 아니요(제한 없음) |
| 콘텐츠 등급 | 설문 시작 → 이메일 → **게임** → IARC동의 → **14문항 전부 아니요** → 저장(다음 아닌 **저장** 버튼이 활성) → 요약 저장. 결과: 전체이용가/PEGI3 |
| 타겟층 및 콘텐츠 | 13~15·16~17·18세 이상 체크(아동 제외) → 2~4단계 자동스킵 → 요약 저장 |
| 데이터 보안 | 개요 다음 → "수집/공유 안 함" 아니요 → 미리보기(수집없음·공유없음·개인정보처리방침 연결됨) 저장 |
| 금융 기능 | "앱에서 금융 기능 제공하지 않음" 체크 → 다음 → 추가문서 불필요 저장 |
| 정부 앱 | 아니요 |
| 건강 앱 | "앱에 건강 기능 없음" 체크 → 다음 → 저장 |

**콘텐츠등급 14문항 팁:** 질문이 순차로 펼쳐짐. `find "아니요 radio"`로 ref 모아 클릭하되, 펼쳐진 것만 등록되므로 응답→펼침→재조회 반복. 미완은 `javascript_tool`로 `radio checkedCount`(=질문수면 완료) 확인. `다음`은 disabled여도 `저장`이 활성이면 그걸로 저장.

## 5단계: 스토어 등록정보 → **API로 처리** (콘솔 클릭 X)

등록정보 텍스트(ko-KR 기본 + en-US)와 그래픽(아이콘·피처·스크린샷)은 콘솔에서 입력/업로드하지 말고 **`play_upload.py`의 `listings`·`images`** 로 올린다. 그래픽은 `graphicsLanguage` 기본언어에만 올리면 다른 언어에 자동 공유. (콘솔 "번역 관리" 수동 추가·"애셋 추가→업로드" 불필요.)

## 6단계: 국가/지역 (콘솔)

프로덕션 트랙 → "국가/지역" 탭 → "국가/지역 추가" → 헤더 전체선택 체크박스 → 저장(전체 177개). *API의 트랙 `countryTargeting`으로도 일부 가능하나 첫 게시 가용성은 콘솔이 확실.*

## 7단계: 스토어 설정 — 카테고리·연락처 (콘솔 — 카테고리는 API 없음)

`.../store-settings`. **앱 카테고리** 수정 → 게임/카테고리(예: 보드) 저장(API 미지원, 콘솔 필수). **연락처 세부정보** 수정 → 이메일(필수)+웹사이트 저장. *"초기 설정 1/5"로 막혔다면 보통 여기 미완.*

## 8단계: 검토 제출 (비가역 — 사용자가 "출시까지" 명시했을 때만)

- **API 경로(기본):** `play_upload.py --commit` 가 `edits.commit`으로 검토 전송까지 끝낸다. 콘솔 클릭 불필요.
- **콘솔 경로(콘솔에서 변경분이 남았을 때):** `.../releases/1/review` → "출시 준비됨"(녹색) 확인 → **저장** → "개요로 이동" → 게시 개요(`.../publishing`) → **"검토를 위해 변경사항 N개 전송"** → 확인 다이얼로그. 상태가 **"검토 중인 변경사항"**이면 완료. 승인 시 자동 게시(보통 7일 내).

남은 오류가 "대시보드 단계 완료"면 → 대시보드 체크리스트 미완 항목(보통 7단계 카테고리) 처리.

---

# 기존 앱 수정/업데이트 — **100% API, Chrome 안 씀**

위 콘솔 전 과정을 다시 타지 말 것. `play_upload.py` 한 번으로 바뀐 부분만 처리:

- **새 버전(AAB) 배포:** 로컬에서 `versionCode` 증가(`build.gradle` 범프 후 서명 AAB 재빌드) → config JSON에 `aab`+`track` 넣고 → `play_upload.py`(dry run → `--commit`). 콘텐츠 선언/등급/데이터보안은 변경 없으면 안 건드림.
  - draft 상태 충돌·"새 버전 만들기 disabled"·구버전 번들 중복 삭제 같은 **콘솔 UI 함정이 API에선 전부 없음** — edit가 versionCodes를 명시 배정한다.
- **등록정보(텍스트)만 수정:** config `listings`(ko/en)만 넣고 `play_upload.py`. (`aab` 없으면 트랙 안 건드림.)
- **그래픽만 교체:** config `images`(imageType별 전량 교체)만 넣고 실행.
- **여러 앱 일괄:** 앱별 config JSON을 만들어 순차 실행.

> 콘솔에서만 가능한 변경(데이터보안/콘텐츠 등급 답 변경, 카테고리 변경)이 필요할 때만 위 "콘솔 경로"의 해당 선언만 다시 → 저장. 그 외엔 API.

## 완료 후

Telegram 완료 알림(전역 CLAUDE.md 규칙). 사용자에게 검토 대기·자동게시·거부 시 사유 전달 안내.

## 주의

- 첫 등록은 개발자 계정($25 1회) 필요 — 없으면 사용자가 직접 가입(결제 대행 금지).
- API 403 → SA가 그 앱에 Play Console 권한 없음/앱 미존재. `play-publishing-api.md`의 1회 액션(API 액세스 링크 + SA 초대) 안내 후, 권한 붙기 전엔 콘솔 핸드오프로 폴백.
- 콘솔 좌표가 꼭 필요한 순간(네이티브 다이얼로그 위치)에만 스크린샷.
- Google이 콘솔 UI 문구/순서를 바꿀 수 있으니 콘솔 단계 진입 시 1회만 가볍게 검증.
