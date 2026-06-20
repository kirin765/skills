---
name: app-launch-promo
description: 신규 앱(또는 앱 업데이트)이 나왔을 때 한 번에 멀티채널로 홍보하는 오케스트레이션 스킬. 사용자가 제공한 홍보영상 + 앱 정보를 받아 (1) Instagram·Threads·X·TikTok에 플랫폼별 카피와 함께 게재하고, YouTube는 youtube-upload 스킬(API)로 업로드, (2) inpock(link.inpock.co.kr/admin)에 신규 앱 링크 추가, (3) disquiet에 프로젝트 추가 후 메이커 로그 작성까지 끝낸다. 사용자가 "새 앱 홍보해줘", "앱 출시 홍보", "신규 앱 SNS에 다 올려줘", "앱 런칭했으니 홍보 돌려줘", "이 앱 인스타·스레드·틱톡·X에 올리고 inpock·disquiet에도 등록해줘", "프로모 영상 다 뿌려줘" 같이 *완성된 앱/영상을 여러 채널에 한 번에 홍보·등록*하려 할 때 반드시 발동한다. 카피(글)는 이 스킬이 플랫폼별로 생성하지만 홍보영상은 사용자가 경로로 제공해야 한다(영상 제작은 hyperframes 등 별도 스킬). 한 플랫폼만 올리는 단순 발행은 해당 전용 스킬(youtube-upload 등)을, 영상 제작은 영상 스킬을 직접 쓴다.
---

# App Launch Promo

완성된 앱과 홍보영상을 받아 **다섯 개 SNS 채널 + inpock 링크허브 + disquiet**에 한 번에 뿌리는
오케스트레이터다. 카피는 플랫폼마다 새로 쓰고, 영상은 사용자가 준 파일을 그대로 쓴다.

## 엔진 분담 (중요 — 처음에 확정하고 시작)

| 대상 | 엔진 | 계정 |
|---|---|---|
| **Instagram** | **`social-video-upload` 스킬 (Playwright)** | happylife2080100 |
| **Threads** | **`social-video-upload` 스킬 (Playwright)** | happylife2080100 |
| X | Claude in Chrome (`mcp__Claude_in_Chrome__*`) | Giwan |
| **TikTok** | **`social-video-upload` 스킬 (Playwright)** | aigroove99 |
| **YouTube** | **`youtube-upload` 스킬 (API)** | gksrkdls1982 |
| inpock | Claude in Chrome | happylife2080 |
| disquiet | **CDP + Playwright (포트 9222)** | 런타임 확인 (보통 happylife2080100) |

IG·Threads·TikTok 영상 발행은 **`social-video-upload` 스킬**(Playwright + (플랫폼,계정)별 전용 영구 프로필)에
위임한다 — DOM 업로드를 직접 다루지 않고 검증된 무인 업로더에 영상·캡션·계정만 넘긴다.
계정은 호출 시 `--account`로 지정한다(위 표가 기본값, 필요하면 변경). 각 (플랫폼,계정)은
`social-video-upload` 프로필에 1회 로그인돼 있어야 하며, 미로그인이면 그 채널은 건너뛰고 리포트에 기록한다.
X·inpock은 Claude in Chrome 확장으로, **disquiet만 CDP+Playwright(포트 9222)**로 돈다 — 프로덕트 등록의
이미지 업로드(썸네일+갤러리)·contenteditable 로그 에디터·"관련 프로덕트" 드롭다운 선택을 결정적으로 다루기
위해서다. **검증된 셀렉터·2단계 위저드 흐름은 `references/disquiet.md`에 그대로 들어 있으니 그 파일을 단일
출처로 따른다**(SKILL.md에 셀렉터를 중복 기재하지 않는다).
YouTube만 예외로 무인 API 업로드(`youtube-upload`)를 쓴다 — DOM 업로드보다 안정적이라 그렇다.
계정 세부와 세션 검증은 `references/accounts.md`.

## 실행 모드

사용자가 **확인 없이 즉시 자동 발행**을 택했다. 그래서 각 단계에서 발행 전 멈춰 묻지 않는다.
다만 발행은 되돌리기 어려우니, **2단계에서 생성한 카피 전부를 발행 전에 transcript에 한 번 출력**해
사용자가 무엇이 나가는지 눈으로 볼 수 있게 한다. 이건 블로킹 확인이 아니라 가시성 확보다.

## 워크플로우

순서대로 진행한다. 한 단계(특히 한 플랫폼)가 실패해도 **전체를 멈추지 말고** 실패를 기록한 뒤
다음으로 넘어간다 — 5개 중 1개가 깨졌다고 나머지 홍보를 포기할 이유가 없다.

### 0. 입력 수집 + 사전점검

수집할 입력(대화에서 받거나 `assets/input-template.md` 채워 받는다):

- **앱 이름** (ko / en)
- **한 줄 훅** — 가장 강한 한 문장
- **설명** — 2~4문장, 핵심 기능 포함
- **스토어/랜딩 URL** — Play/App Store/웹 (CTA·inpock·disquiet에 쓰임). **IG·Threads·TikTok CTA엔
  Play Store URL이 필수**이며 사전점검 5에서 유효성을 검증한다.
- **핵심 기능 3~5개 / 키워드(태그)**
- **홍보영상 경로(필수)** — 세로(9:16) 1개는 IG·TikTok·YouTube Shorts·X용. 가로(16:9)가 따로
  있으면 YouTube 롱폼에 쓴다. 없으면 세로 하나로 전부 처리.
- **썸네일/스크린샷(선택)** — YouTube 썸네일, 부족하면 영상 첫 프레임으로 대체 안내.

사전점검(여기서 막히면 멈추고 사용자에게 알린다):

1. `mcp__Claude_in_Chrome__list_connected_browsers`로 Chrome 확장 연결 확인(X·inpock용). 안 되면 설치/연결 요청.
   disquiet는 확장이 아니라 **CDP(포트 9222)**를 쓰니 `curl -s http://localhost:9222/json/version`로 따로 확인한다.
2. 영상 파일이 실제로 존재하는지 경로 확인.
3. **IG·Threads·TikTok 계정 로그인 확인** — `social-video-upload`의 `whoami`로 각 (플랫폼,계정)이
   로그인돼 있고 핸들이 표와 일치하는지 본다(아래 4단계 명령 참고). 미로그인/불일치면 그 채널은
   건너뛰고 리포트에 "login 필요"로 기록(자동 로그인 시도 안 함). X 계정 확인은 `references/accounts.md`.
4. YouTube는 `~/.config/youtube-upload/token.json` 존재 확인. 없으면 `youtube-upload` 스킬의
   1회성 셋업이 먼저 필요하다고 안내.
5. **Play Store 링크 유효성 검증(중요)** — 이 링크가 IG·Threads·TikTok 카피의 CTA로 들어가므로,
   죽은 링크가 나가면 모든 발행이 헛수고다. Play Store는 `<title>`·`og:title`·`og:description`을
   **서버렌더**하므로 브라우저 없이 `curl`만으로 충분하고 더 견고하다(`connect_over_cdp`는 Chrome 149에서
   불안정). HTTP 200이어도 본문이 에러일 수 있으니 **상태코드가 아니라 본문 내용으로 판정**한다:
   ```bash
   curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36" \
     -H "Accept-Language: ko-KR,ko;q=0.9" "<PLAY_URL>" -o /tmp/play.html
   # 유효 조건: <title>/og:title에 앱 이름이 뜨고(= "...- Google Play 앱"), "설치/Install" 마커가 있으며,
   #          "요청하신 URL을 찾을 수 없 / requested URL was not found / Item not found / 404"가 없다.
   ```
   무효면(앱 이름 대신 에러 문구) **발행을 멈추고 사용자에게 알린다**(아직 심사 중이거나 패키지명/URL 오타일 수 있음).
   curl이 막히는 환경이면 Claude in Chrome `navigate`+`get_page_text`로 같은 본문 판정을 한다(폴백).

### 1. (참고) 엔진 재확인

위 표대로 IG·Threads·TikTok=`social-video-upload`(Playwright), X·inpock=Claude in Chrome,
disquiet=CDP, YouTube=API. 변동 없으면 그대로 진행.

### 2. 플랫폼별 카피 생성

`references/copy-guidelines.md`를 읽고 플랫폼마다 카피를 만든다. 같은 글을 5곳에 복붙하지 않는다 —
플랫폼마다 글자수·해시태그 문화·톤·링크 위치가 다르다. 한국어가 1차, 필요하면 영어 병기.
**링크 규칙**: IG·Threads·TikTok 카피엔 검증된 **Play Store 링크**를 CTA로 넣는다. X 카피는 끝에
**YouTube 링크 자리**를 비워두고 3단계(YouTube 업로드) 후 `$YT_URL`을 주입해 완성한다(YouTube가 X보다 먼저인 이유).
**생성한 카피 전부를 여기서 transcript에 출력**한다(위 "실행 모드" 참고).

### 3. YouTube 업로드 (먼저 — X가 이 링크에 의존)

**YouTube를 SNS보다 먼저 올린다.** X 카피에 YouTube 홍보영상 링크가 반드시 들어가므로, 그 watch URL을
여기서 확보해야 X를 발행할 수 있다. `youtube-upload` 스킬에 위임한다(직접 명령 재작성 X):

```bash
~/.config/youtube-upload/venv/bin/python \
  ~/.claude/skills/youtube-upload/scripts/yt_upload.py \
  --video <세로영상 또는 가로영상> --title "<≤100자 제목>" \
  --description-file /tmp/yt_desc.txt --tags "태그1,태그2" \
  --thumbnail <png> --privacy unlisted
```

- 제목·설명·태그는 2단계 카피의 YouTube 버전을 쓴다. 설명은 임시 파일(`/tmp/yt_desc.txt`)에 써서
  `--description-file`로 넘긴다(셸 이스케이프 사고 방지). 설명 끝에 스토어/랜딩 URL을 넣는다.
- 기본 `privacy=unlisted`. 사용자가 public을 원하면 youtube-upload 스킬의 주의사항을 따른다.
- 세로 영상만 있으면 Shorts로 올라간다(60초 이하 9:16). **출력된 watch URL을 캡처해 `$YT_URL`로 보관** —
  4단계 X 카피와 disquiet(6단계)의 YouTube 영상 필드에 쓴다.
- **업로드 실패로 watch URL을 못 얻으면**: X(4-2)는 발행 보류하고 리포트에 "YT 링크 없어 보류"로 기록한다.
  나머지 채널은 영향 없이 진행(채널 격리).

### 4. SNS 발행 루프

플랫폼은 한 번에 하나씩, 실패해도 다음으로 넘어간다. 각 발행 후 **결과 URL을 캡처**한다.

**4-1. IG·Threads·TikTok → `social-video-upload` 스킬에 위임**

DOM을 직접 다루지 말고 업로더 CLI에 영상·캡션·계정을 넘긴다. **각 캡션 파일에는 0단계에서 검증한
Play Store 링크가 CTA로 들어가 있어야 한다**(2단계 카피 생성 시 포함). 캡션은 셸 이스케이프 사고를
막기 위해 임시파일에 쓰고 `$(cat ...)`로 전달한다. `--auto`로 실제 발행까지 수행한다
(이 스킬은 "확인 없이 즉시 발행" 모드). 발행 전 `whoami`로 계정을 한 번 더 확인한다.

```bash
SVU=~/.claude/skills/social-video-upload/scripts/upload.mjs
NP=/opt/homebrew/lib/node_modules

# 계정 확인 (사전점검 3에서 이미 했으면 생략 가능)
NODE_PATH=$NP node $SVU instagram whoami --account happylife2080100

# Instagram Reels (오발행 방지로 --expect) — 캡션에 Play Store 링크 포함
NODE_PATH=$NP node $SVU instagram post "$VIDEO" "$(cat /tmp/cap_ig.txt)" \
  --account happylife2080100 --expect happylife2080100 --auto

# Threads — 캡션에 Play Store 링크 포함
NODE_PATH=$NP node $SVU threads post "$VIDEO" "$(cat /tmp/cap_threads.txt)" \
  --account happylife2080100 --auto

# TikTok (콘텐츠 검사 대기로 수 분 걸릴 수 있음) — 설명에 Play Store 링크 포함
NODE_PATH=$NP node $SVU tiktok post "$VIDEO" "$(cat /tmp/cap_tiktok.txt)" \
  --account aigroove99 --auto
```

각 호출의 마지막 줄 `RESULT {json}`에서 `posted`/`url`을 읽어 성공·URL을 리포트에 기록한다.
`error`에 "not logged in"이면 그 채널은 `login` 필요로 표시하고 건너뛴다(자동 로그인 안 함).
계정·특이사항·셀렉터 깨짐 대응은 `social-video-upload`의 SKILL.md와 troubleshooting을 따른다.

**4-2. X → Claude in Chrome**

`references/platforms/x.md` 플레이북을 따른다(계정 재확인 → compose → 영상 첨부 → 카피 →
게시 → URL 캡처). **X 카피엔 3단계의 `$YT_URL`(YouTube 홍보영상 링크)을 반드시 포함한다** — 캡션 파일을
만들 때 끝에 `$YT_URL`을 넣는다. `$YT_URL`이 없으면(YouTube 실패) X는 발행하지 말고 보류로 기록한다.
셀렉터는 `find`/`get_page_text`로 현재 화면을 보고 적응한다.

### 5. inpock 링크 추가

`references/inpock.md`를 따라 `link.inpock.co.kr/admin`에서 신규 앱 링크를 추가한다
(라벨 = 앱 이름, URL = 스토어/랜딩 URL). 추가 후 링크허브에 노출됐는지 확인.

### 6. disquiet 프로덕트 등록 + 메이커 로그

**`references/disquiet.md`의 검증된 CDP+Playwright 플레이북을 그대로 따른다** — 셀렉터·단계·예외 처리는
그 파일이 단일 출처(라이브 DOM + 2단계 화면으로 검증 완료). 시작 전
`curl -s http://localhost:9222/json/version`로 CDP가 살아있는지 확인한다(없으면 사용자에게 Chrome을
`--remote-debugging-port=9222`로 띄워달라고 요청). 이 단계만 CDP+Playwright(포트 9222)다.

요지(상세·셀렉터는 disquiet.md):

- **프로덕트 등록** (`/new-product`, **2단계 위저드**) — Step1: 이름·한 줄 소개·링크·토픽\*(≤3)·설명\*·
  썸네일 이미지\*(240×240) → **"추가 정보"**. Step2: 갤러리 이미지\*(≤5, 1200×900)·YouTube 영상(선택)·
  메이커 정보\*("제가 / 우리 팀이 만들었어요") → **"프로덕트 공유하기"**. 썸네일·갤러리 이미지가 **둘 다 필수**라
  없으면 등록 불가 — 0단계에서 받은 아이콘/스크린샷을 쓰고, 하나도 없으면 멈춰 사용자에게 요청한다.
- **메이커 로그** (홈 작성창) — 본문 작성 → **"관련 프로덕트"** 드롭다운에서 방금 만든 프로덕트를 **이름으로 클릭**
  (검색창 아님, 내 프로덕트 목록) → 연결 칩 확인 → **"로그 남기기"**(띄어쓰기) 제출.
- 같은 앱이 "관련 프로덕트" 목록에 이미 있으면 등록을 건너뛰고 재사용. **프로덕트 URL·로그 URL을 캡처**.
- **disquiet 에러는 무시하고 전진** — 제출 액션을 한 번 보냈으면 에러 토스트가 떠도 성공으로 간주, **재시도 금지**
  (중복 생성됨). 성공 여부는 에러 메시지가 아니라 URL·목록 반영으로 확인. 상세는 disquiet.md 실패·안전 규칙.

### 7. 리포트 + 텔레그램 알림

결과를 표로 정리한다:

| 채널 | 상태 | URL / 비고 |
|---|---|---|
| Instagram | ✅/❌ | … |
| Threads | … | … |
| X | … | … |
| TikTok | … | … |
| YouTube | … | … |
| inpock | … | … |
| disquiet | … | … |

그다음 `telegram-bot` 스킬로 완료 알림을 보낸다(global CLAUDE.md 규칙: 작업 완료 또는 블로킹 시 발송).
일부 실패가 있으면 ⚠로 표시하고 실패 채널·원인을 요약한다.

## 실패 처리 원칙

- **채널 격리** — 한 채널 실패가 다른 채널을 막지 않는다. 기록하고 계속.
- **자동 로그인 시도 금지** — 계정이 틀리면 그 채널만 건너뛰고 사용자에게 알린다(보안상 비번 자동입력 X).
- **되돌리기 없음** — 이미 나간 게시물은 자동 삭제하지 않는다. 잘못 나갔으면 리포트에 명시하고
  사용자가 직접 내리도록 안내.
- **파일 업로드 막힘** — IG·Threads·TikTok은 `social-video-upload`가 파일 input을 직접 다루므로
  보통 문제없다. 셀렉터가 깨지면 그 스킬의 troubleshooting을 따른다. X는 Claude in Chrome의
  `file_upload`/`upload_image`가 input을 못 잡으면 플레이북의 대체 경로(드래그·수동 첨부)를 따른다.
