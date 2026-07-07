---
name: tiktok-upload
description: TikTok에 영상을 무인 업로드하는 워크플로우 — mp4 + 캡션(+ 선택적 AI라벨·공개범위)을 받아 계정별 전용 Chromium 프로파일로 게시하고 결과(성공/watch URL)를 반환한다. 사용자가 "틱톡에 올려줘", "TikTok 업로드", "이 영상 틱톡에 게시", "릴/쇼츠 틱톡에도 올려줘", "upload to TikTok", "틱톡 자동 게시" 같은 표현을 쓰거나, 방금 만든 영상(HyperFrames/Remotion/game-shorts 렌더 결과 등)을 TikTok에 올리자고 할 때 반드시 발동. 최초 1회 `node login.mjs --account <name>` 으로 로그인이 필요하고(2FA 수동), 이후 무인 게시. Playwright + 전용 persistent 프로파일(`~/.tiktok-upload/<account>/`)을 쓰며 사용자의 라이브 Chrome/포트 9222는 건드리지 않는다. 게시는 비가역이라 실전 전 `--dry-run` 검증을 권장. 영상 제작·다운로드·분석은 이 스킬이 아니다(그건 hyperframes/general-video 등). YouTube 업로드는 youtube-upload, Instagram 릴스는 ig-android.
---

# tiktok-upload

TikTok에 mp4 하나를 캡션과 함께 게시한다. game-shorts 파이프라인에서 매일 돌던 검증된 업로드 로직을 독립 스킬로 일반화한 것.

## 세션 모델 — 전용 프로파일 (라이브 Chrome 안 건드림)

계정별 persistent Chromium 프로파일 `~/.tiktok-upload/<account>/`. 최초 1회 대화형 로그인 후, 그 프로파일 쿠키로 무인 게시. 포트 9222·사용자 메인 Chrome과 무관.

## 사전 조건

1. **의존성 설치 (스킬 폴더에서 1회)**
   ```bash
   cd ~/.claude/skills/tiktok-upload && npm install && npx playwright install chromium
   ```
2. **계정 로그인 (계정당 1회, 사용자가 자리에 있을 때)**
   ```bash
   node login.mjs --account aigroove99
   ```
   브라우저가 열리면 해당 계정으로 로그인(2FA 포함) → 자동 감지 후 창이 닫히고 세션 저장. 이후 무인 업로드 가능.

## 업로드

```bash
node upload.mjs --account <name> --video /path/clip.mp4 --caption "본문 #해시태그" \
  [--ai-label] [--visibility public|friends|private] [--dry-run]
```

- `--account` (필수) — 로그인해 둔 프로파일명.
- `--video` (필수) — 게시할 mp4 절대경로.
- `--caption` — 캡션/본문. 줄바꿈 포함 가능. 해시태그 자동완성 팝업은 자동으로 Escape 처리.
- `--ai-label` — "AI 생성 콘텐츠" 토글 ON. AI 자동생성 클립이면 켜서 TikTok 정책 준수.
- `--visibility` — `public`(모두) / `friends`(친구) / `private`(나만). 생략 시 TikTok 기본값.
- `--dry-run` — Post 버튼 enabled 상태까지 가서 **클릭 직전 멈추고** 전체 스크린샷(`/tmp/tiktok-dryrun-*.png`). 게시 안 함.

성공 시 stdout에 JSON 한 줄: `{"ok":true,"url":"..."}` (dry-run은 `{"ok":true,"dryRun":true,"screenshot":"..."}`).

## 게시는 비가역 — 규율

TikTok 게시는 되돌리기 어렵다. 실전 게시 전:

1. **처음 쓰는 계정/옵션 조합이면 `--dry-run` 먼저.** 특히 `--ai-label`·`--visibility` 셀렉터는 TikTok DOM 변화에 취약 — dry-run 스크린샷으로 토글/드롭다운이 의도대로 걸렸는지 눈으로 확인한 뒤 실게시.
2. 대량/반복 게시는 사용자 확인 후. 봇 트래픽처럼 몰아치지 말 것.
3. 캡션·해시태그·공개범위를 사용자와 한 번 맞추고 게시.

## 셀렉터 안정성 노트

- **파일 첨부·캡션·게시(1·2단계)** — game-shorts에서 검증된 로직. 안정적.
- **AI라벨·공개범위(3·4단계)** — text-anchored 셀렉터(한/영 폴백) + `role=switch`/`role=option`. TikTok Studio UI가 바뀌면 여기가 먼저 깨진다. 실패 시 에러 메시지가 "verify selectors with --dry-run"을 안내하니, dry-run 스크린샷으로 실제 DOM을 보고 `lib/tiktok.mjs`의 `enableAiLabel`/`setVisibility` 셀렉터를 조정.
- 로그인 만료(`sessionid` 쿠키 소실) 시 `login.mjs` 재실행.

## 이 스킬이 하지 않는 것

- **영상 제작/편집/다운로드** — hyperframes·general-video·music-to-video 등이 담당. 이 스킬은 완성된 mp4를 받아 올리기만.
- **캡차/봇탐지 우회** — 안 함. 캡차는 login.mjs 창에서 사용자가 직접.
- **다른 플랫폼** — YouTube=youtube-upload, Instagram 릴스=ig-android.

## 관련 파일

- `lib/tiktok.mjs` — 프로파일 오픈, 로그인 확인, 업로드 코어(캡션·AI라벨·공개범위·dry-run).
- `login.mjs` — 최초 대화형 로그인.
- `upload.mjs` — 무인 업로드 CLI.
