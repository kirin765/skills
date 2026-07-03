# Play Store 등록/업데이트 → 검토 제출

AAB를 Google Play Console에 등록·업데이트하고 프로덕션 검토까지 보내는 워크플로우. **업로드·등록정보·검토제출은 Play Developer API로 무인 처리**가 기본. Chrome 클릭은 API에 없는 신규-앱 셋업 부분에서만 쓰며, 그때 화면을 일일이 분석하지 않게 **정답표**를 내장한다.

## ⭐ 엔진 선택 — 작업 시작 전 먼저 분기 (제일 중요)

> **철칙: 제출은 무조건 Play API.** 업로드·이미지·등록정보·트랙·**출시노트·검토 제출(`edits.commit`)**은 어떤 경우에도 `play_upload.py`(API)로 한다. **CDP/Chrome 콘솔은 API에 엔드포인트가 진짜 없는 신규-앱 셋업 3가지 — ① 앱 최초 생성 ② 콘텐츠 선언 10개 ③ 카테고리 — 에만 쓴다.** 그 외(특히 "검토 제출")를 CDP로 하지 말 것. 콘솔은 API가 실제로 실패(403 등)할 때만 폴백.

| 작업 | 엔진 | 비고 |
|------|------|------|
| **기존 앱 업데이트** (새 버전 AAB·등록정보·그래픽·출시노트·검토제출) | **100% API** (`play_upload.py`) | Chrome 안 씀. 아래 "API 경로" 한 방. |
| **신규 앱 — 앱 생성·콘텐츠 선언 10개·카테고리** | **Chrome MCP (콘솔)** | API에 엔드포인트 없음(구글 한계). 아래 "콘솔 경로" 2·4·7단계만. |
| **신규 앱 — 맨 처음 AAB** | **API** (`releaseStatus: "draft"`) | 첫 AAB도 API로 됨(2026-06 실증). 미게시 앱은 `"releaseStatus": "draft"` 필수 — `completed`면 validate 실패. Play App Signing은 앱 생성 직후 자동 활성. **API가 실제로 거부할 때만** 사용자가 콘솔에서 첫 AAB 1회 수동 업로드. |
| **신규 앱 — 이미지·등록정보·이후 버전·출시노트·검토제출** | **API** | 콘솔 뼈대(위 3가지) 완료 후 전부 API. **검토 제출도 `edits.commit`으로 API에서 끝낸다.** |
| **신규 앱 — 국가/지역** | **API 우선** (`countryTargeting`) | API가 막히면 그때만 콘솔에서 추가. |

**기본 동작:** 업로드/등록정보/트랙/출시노트/커밋은 **무조건 API**. Chrome `file_upload`로 바이너리·이미지를 올리려 하지 말 것(영구 차단, 아래 금지 목록). 신규 앱이라 콘솔 뼈대가 필요하면 그 최소 부분만 Chrome으로 하고 나머지는 전부 API로 넘긴다.

---

# API 경로 (`play_upload.py`) — 업로드·등록정보·트랙·검토제출

브라우저를 안 쓰는 `androidpublisher` v3 REST. 서비스 계정 키로 edit 트랜잭션(insert → 작업 → validate → commit)을 돌린다.

- **스크립트**: `~/.claude/skills/android-app-builder/scripts/play_upload.py`
- **실행 venv**: `~/.config/play-publisher/venv/bin/python`
- **서비스 계정 키**: `~/.config/play-publisher/sa.json` · SA 이메일 `play-publisher@claude-for-android.iam.gserviceaccount.com`
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
  "releaseStatus": "draft",                       // 신규 미게시 앱의 첫 AAB면 필수. 게시된 앱은 생략(=completed)
  "releaseNotes": { "ko-KR": "최초 출시", "en-US": "Initial release" },
  "images": {                                     // imageType별 전량 교체(deleteall→upload)
    "icon": "/abs/icon-512.png",
    "featureGraphic": "/abs/feature-1024x500.png",
    "phoneScreenshots": ["/abs/framed/01.png", "/abs/framed/02.png"]
  },
  "graphicsLanguage": "ko-KR",                    // 이미지는 기본언어에만 올리면 자동 공유
  "listings": {                                   // aso-audit 카피 그대로
    // video(선택): 프로모션 동영상 YouTube URL. update는 전체 교체라, 등록정보를 손대면서
    // 기존 동영상을 유지하려면 video도 함께 넣는다(빼면 지워짐).
    "ko-KR": {"title": "...", "shortDescription": "≤80", "fullDescription": "≤4000", "video": "https://youtu.be/..."},
    "en-US": {"title": "...", "shortDescription": "...", "fullDescription": "..."}
  }
}
```

**규칙:**
- **아이콘 일치 게이트 (AAB를 올리는 제출·업데이트면 `--commit` 전 필수):** release AAB에 실제로 들어간 런처 아이콘을 꺼내 업로드할 `icon-512.png`와 같은 아트인지 눈으로 대조 — `references/app-icon.md`의 "검증 게이트". 다르거나 템플릿 아이콘(X·별)이 보이면 **제출 중단**, 아이콘 재생성 후 AAB 재빌드. (컬러 메모리 "스토어 등록정보 불일치" 반려 재발 방지 — 이 게이트를 건너뛰지 말 것.)
- 항상 **dry run 먼저** → `validate OK` 확인 후에만 `--commit`.
- `--commit` 없이는 edit가 폐기되어 아무것도 반영 안 됨(안전). `--commit`은 검토 전송(비가역)이라 **"출시까지" 명시 때만**.
- 이미지는 imageType별 전량 교체. `phoneScreenshots`는 배열로 2~8장.
- 403이 나면 → 서비스 계정이 그 앱에 Play Console 권한이 없거나 앱/패키지가 아직 없는 것. `play-publishing-api.md`의 "사용자 1회 액션"(API 액세스 링크 + SA 초대) 안내 후 폴백.
- 입력 에셋(아이콘·framed 스크린샷·피처)과 카피는 §2 에셋·§2.5 ASO 산출물을 그대로 쓴다.

## 에셋·ASO 준비 (업로드 전 1회 — 신규/그래픽 교체 시)

`~/Downloads/<app>-store-assets/` 한 폴더에 모음. 스크립트 예시는 `references/asset-scripts.md`.

- **아이콘 512px**, **스크린샷 2~8장(폰 프레임 + 헤드라인 카피 마케팅 컷 — 항상 이 형식, raw 금지)**, **피처그래픽 1024×500**.
- **개인정보처리방침 URL**: SKILL.md §6 "데이터 거동 티어" 규칙으로 결정(무수집=A 공통 / 광고=B 공통 / 그외=C 앱별). 선택 URL은 Play 데이터 보안 선언과 일치해야 함.
- **ASO 카피**: 등록정보 텍스트 확정 전 **`aso-audit` 스킬 호출**(ko/en). 산출 카피를 config `listings`에 그대로. **언어 정책(항상): 기본 ko-KR + en-US 항상 추가.**

---

# 콘솔 경로 (Chrome MCP) — API에 없는 부분만

**언제만:** 신규 앱의 ① 앱 생성(2단계) ② 콘텐츠 선언 10개(4단계) ③ 카테고리/연락처(7단계). AAB·이미지·등록정보·검토제출은 콘솔에서 하지 말고 API로.

## 콘솔 토큰 절약 핵심 규칙
1. **좌표 클릭 금지, ref 클릭 우선.** `find`/`read_page(filter:"interactive")`로 ref를 얻어 `computer{action:"left_click", ref:"ref_N"}`. 스크린샷 불필요.
2. **스크린샷은 "결정 지점·검증"에서만.** 매 batch 끝마다 찍지 말 것.
3. **상태 확인은 `read_page` 텍스트 또는 `javascript_tool`로.**
4. **정답을 미리 안다 → 질문 안 읽고 일괄 처리.** 아래 정답표 사용.
5. **바이너리/이미지는 콘솔에서 올리지 말 것.** 첫 AAB 포함 전부 API.

## 업로드 자동화 시도 금지 목록 (전부 차단 확인됨, 재시도 금지)
- ❌ Playwright `connectOverCDP` + `setInputFiles` 로컬 스크립트 — "Auto-Mode Bypass" 거부.
- ❌ `mcp__claude-in-chrome__file_upload` 에 로컬 경로 — "사용자가 공유한 파일만" 받음. 로컬 경로 거부.
- ❌ 네이티브 파일 다이얼로그를 백그라운드/세컨더리 모니터 CDP 탭에서 — 제어 탭이 foreground+가시 창이어야 열림.
- ✅ 첫 AAB도 API로 올라간다(`releaseStatus: "draft"`). API가 실제로 거부하는 예외에서만 사용자가 그 탭에서 직접 파일 선택(수동 폴백).

## 알려진 값 (이 개발자 계정 — 헌팅 금지, 바로 deep-link)
`/u/N/` 인덱스를 순차로 돌지 말 것. devId·appId·package는 세션·Chrome 프로필과 무관하게 고정.

- **개발자 계정**: `happylife2080100@gmail.com` (개발자명 happylife2080) · **devId `8303647010319569479`**
- **앱 예시 — QuickTodo**: `com.kiwan.quicktodo` · appId `4973743514636442357` (앱별 값; 신규 앱은 생성 후 URL에서 확보)
- 앱 대시보드 직행: `…/u/{N}/developers/8303647010319569479/app/<appId>/app-dashboard`

### 올바른 계정 인덱스(N) 찾기 — 1~2회로 끝낸다
1. `navigate` → `…/console/u/0/developers/8303647010319569479/app/<appId>/app-dashboard`.
2. `get_page_text` 1회. 앱 대시보드가 뜨면 끝(N=0).
3. 틀리면 `…/console`에서 **"개발자 계정 선택" 피커의 `happylife2080` 항목 직접 클릭** → URL의 `/u/N/` 읽어 이후 deep-link에 박음.

**이 계정이 연결된 Chrome 어디에도 없으면 추측·계정 생성 금지, 즉시 사용자 핸드오프**("happylife2080100 계정으로 Play Console 로그인 후 알려달라").

## 콘솔 환경 전제
- 사용자의 Chrome(claude-in-chrome MCP)이 Play Console에 로그인돼 있어야 함. `list_connected_browsers` → 확인 → `select_browser`.
- Chrome은 read-tier라 `computer-use`로 못 누름. 반드시 **claude-in-chrome MCP**(`navigate`, `find`, `computer`)로.

## 2단계: 앱 생성 (콘솔 — API 없음)
`navigate` → `.../developers/<devId>/app-list` → "앱 만들기". 폼: 앱이름, **패키지명**, 기본언어(한국어 ko-KR), **앱/게임 중 실제 유형**, **무료**, 선언 체크박스 2개(개발자정책+미국수출법) → "앱 만들기". 생성 후 URL에서 `<appId>` 확보.

> **앱 vs 게임:** 아래 정답표는 "단순 오프라인 게임" 기준. 일반 앱(생산성·유틸리티)이면: 앱 유형 "앱", 카테고리 일반(예: 생산성), 콘텐츠 등급 설문도 "게임" 대신 "기타 앱 유형" 흐름. 데이터 보안은 실제 수집/전송에 맞춰. 인터넷 권한 없는 앱은 자세한 설명에 "인터넷 권한 없음, 모든 데이터 기기 내 보관" 명시하면 심사 수월.

## 3단계: 맨 처음 AAB (API — `releaseStatus: "draft"`)
첫 AAB도 콘솔이 아니라 **API로** (2026-06 실증):
```json
{ "packageName": "...", "aab": "/abs/app-release.aab", "track": "production", "releaseStatus": "draft" }
```
미게시 앱에서 `releaseStatus` 생략(`completed`) 시 validate가 `Only releases with status draft may be created on draft app`로 실패 — `"draft"`로 dry run → `--commit`. **출시노트(한/영)도 config `releaseNotes`로 API에서 함께** — 콘솔 textarea 금지.

**API가 실제로 거부할 때만 수동 폴백:** 프로덕션 트랙 → 새 버전 만들기 → "업로드" → 제어 탭 foreground에서 사용자가 직접 AAB 선택(첫 1회). 이후 버전은 `releaseStatus` 없이 API.

## 4단계: 앱 콘텐츠 선언 10개 — 정답표 (콘솔 — API 없음)
`.../app-content/overview`에서 각 "선언 시작" 클릭. **단순 오프라인 게임 정답:**

| 선언 | 답 |
|------|-----|
| 개인정보처리방침 | URL 입력(§6 티어 규칙으로 결정한 URL) |
| 광고 | 광고 유무에 맞게(AdMob 붙였으면 **예, 광고 있음**) |
| 광고 ID | AdMob 있으면 **예**, 없으면 아니요 |
| 앱 액세스(로그인 세부정보) | 아니요(제한 없음) |
| 콘텐츠 등급 | 설문 시작 → 이메일 → **게임** → IARC동의 → **14문항 전부 아니요** → 저장 → 요약 저장. 결과: 전체이용가/PEGI3 |
| 타겟층 및 콘텐츠 | 13~15·16~17·18세 이상 체크(아동 제외) → 요약 저장 |
| 데이터 보안 | 실제 거동대로. 무수집=수집/공유 안 함. AdMob=「기기 또는 기타 ID」 광고 목적 수집·공유 |
| 금융 기능 | "금융 기능 제공하지 않음" → 다음 → 저장 |
| 정부 앱 | 아니요 |
| 건강 앱 | "건강 기능 없음" → 다음 → 저장 |

**콘텐츠등급 14문항 팁:** 질문이 순차로 펼쳐짐. `find "아니요 radio"`로 ref 모아 클릭하되 응답→펼침→재조회 반복. `다음`이 disabled여도 `저장`이 활성이면 그걸로.

## 5단계: 스토어 등록정보 → **API로 처리** (콘솔 클릭 X)
등록정보 텍스트(ko-KR + en-US)·그래픽은 콘솔 입력/업로드 말고 **`play_upload.py`의 `listings`·`images`**로. 그래픽은 `graphicsLanguage` 기본언어에만 올리면 자동 공유.
**프로모션 동영상(YouTube)**: `listings.<lang>.video`에 watch URL을 넣으면 등록정보에 반영된다(app-launch-promo가 YouTube에 올린 홍보영상 링크를 그대로 쓰면 된다). update는 전체 교체라, 등록정보를 수정하면서 기존 동영상을 유지하려면 `video`도 같이 넣는다.

## 6단계: 국가/지역
API 우선(`countryTargeting`). 첫 게시 가용성이 API로 안 잡히면 콘솔: 프로덕션 트랙 → "국가/지역" 탭 → 추가 → 전체선택 → 저장.

## 7단계: 스토어 설정 — 카테고리·연락처 (콘솔 — 카테고리는 API 없음)
`.../store-settings`. **앱 카테고리** 저장(API 미지원, 콘솔 필수). **연락처** 이메일(필수)+웹사이트 저장.

## 8단계: 검토 제출 (비가역 — "출시까지" 명시 때만)
**제출은 API로 끝낸다.** `play_upload.py --commit`이 `edits.commit`으로 검토 전송까지 무인. 상태가 **"검토 중인 변경사항"**이 되면 완료.
- **콘솔 폴백은 `edits.commit`이 실제 실패할 때만:** `.../releases/1/review` → "출시 준비됨" 확인 → 저장 → 게시 개요 → "검토를 위해 변경사항 전송". (commit 실패 원인은 보통 콘텐츠 선언/카테고리 미완 — 콘솔에서 채우고 다시 `--commit`.)

---

# 기존 앱 수정/업데이트 — **100% API, Chrome 안 씀**
- **새 버전(AAB):** `versionCode` 증가 → 서명 AAB 재빌드 → config에 `aab`+`track` → dry run → `--commit`. 콘솔 UI 함정(draft 충돌·중복 삭제) 없음.
- **등록정보만:** config `listings`만. **그래픽만:** config `images`만. **여러 앱:** 앱별 config 순차 실행.
- 콘솔에서만 가능한 변경(데이터보안/등급 답·카테고리)일 때만 해당 선언 다시.

## 완료 후
Telegram 완료 알림(전역 CLAUDE.md). 검토 대기·자동게시·거부 사유 안내.

## 주의
- 첫 등록은 개발자 계정($25 1회) 필요 — 없으면 사용자가 직접 가입(결제 대행 금지).
- API 403 → `play-publishing-api.md`의 1회 액션 안내 후 콘솔 폴백.
- Google이 콘솔 UI 문구/순서를 바꿀 수 있으니 콘솔 단계 진입 시 1회만 가볍게 검증.
