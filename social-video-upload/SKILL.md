---
name: social-video-upload
description: 사용자가 준 영상(세로 9:16 권장)을 Instagram Reels·Threads·TikTok에 Playwright 브라우저 자동화로 무인 업로드하는 스킬. 플랫폼별로 여러 계정을 가질 수 있고, 각 (플랫폼,계정)은 전용 영구 Chrome 프로필로 로그인을 유지하므로 호출 시 --account로 어느 계정에 올릴지 항상 지정한다. 사용자가 "이 영상 인스타 릴스에 올려줘", "틱톡에 업로드", "스레드에 영상 게시", "릴스/틱톡/스레드에 영상 올려줘", "cookie.sweet.cat 계정에 릴스", "happylife2080100으로 인스타 올려", "이 mp4 SNS에 발행" 같이 *완성된 영상 파일을 IG Reels·Threads·TikTok 중 한 곳 이상에 게시*하려 할 때 반드시 발동한다. 영상 파일 경로는 사용자가 제공해야 한다(영상 제작·다운로드는 별도 스킬). YouTube 업로드는 youtube-upload 스킬, X(트위터)는 별도, 단일 이미지 게시는 이 스킬이 아니다. 여러 채널 + inpock·disquiet까지 한 번에 도는 앱 출시 홍보는 app-launch-promo가 이 스킬을 내부적으로 호출한다.
---

# Social Video Upload

영상 파일 하나를 **Instagram Reels / Threads / TikTok**에 올리는 재사용 업로더다.
계정은 하드코딩하지 않는다 — `--account`로 매번 명시하고, 각 (플랫폼,계정)은 전용
영구 Chrome 프로필을 쓴다. 덕분에 같은 플랫폼에 여러 계정(예: 홍보용 IG와 고양이 IG)을
동시에 로그인 상태로 둘 수 있고, 계정 전환 시 뜨는 이메일 인증을 피한다.

## 엔진

- **Playwright** `launchPersistentContext` + 설치된 Google Chrome(`channel:'chrome'`).
  브라우저 다운로드 불필요. 셋 다 동일한 프로필 모델로 통일했다.
- Playwright는 글로벌(`/opt/homebrew/lib/node_modules`)에 있으므로 **`NODE_PATH`를 지정해
  실행**한다. 모든 명령 앞에 `NODE_PATH=/opt/homebrew/lib/node_modules`를 붙인다.
- 프로필은 `~/.social-upload/profiles/<platform>__<account>/`에 저장된다
  (`SOCIAL_UPLOAD_PROFILES`로 변경 가능).

## CLI

```bash
NODE_PATH=/opt/homebrew/lib/node_modules \
  node ~/.claude/skills/social-video-upload/scripts/upload.mjs \
  <platform> <command> [args] --account <name> [--auto] [--expect <handle>]
```

- `<platform>` — `instagram` | `threads` | `tiktok`
- `<command>`:
  - `login` — 1회성 대화형 로그인(브라우저 창이 뜨면 사용자가 직접 로그인, 쿠키가 프로필에 저장됨)
  - `whoami` — 현재 로그인된 핸들 출력(발행 전 계정 검증용)
  - `post <video> "<caption>"` — 영상 + 캡션 업로드
- 옵션:
  - `--account <name>` — **필수.** 어느 프로필/계정을 쓸지 선택
  - `--auto` — 실제 [공유]/[Post] 클릭까지 수행. **없으면 발행 직전에 멈춤(supervised)**
  - `--expect <handle>` — (instagram) 로그인된 계정이 이 핸들과 다르면 발행 중단(오발행 방지)
- 출력: 마지막 줄에 `RESULT {json}` 한 줄. `posted`(또는 `ok`)와 `url`을 보고 성공 판정.

### 안전 기본값 — supervised

`post`는 기본적으로 **발행 직전에 멈춘다**(영상 첨부 + 캡션 입력까지만). 무인 발행은
되돌리기 어려우므로, 실제로 게시하려면 `--auto`를 명시한다. 자동화 파이프라인
(app-launch-promo 등)은 `--auto`를 붙여 호출한다.

## 사용 흐름

### 1) 최초 1회: 계정별 로그인

각 (플랫폼, 계정) 조합마다 한 번만 로그인하면 이후 무인 발행된다.

```bash
NODE_PATH=/opt/homebrew/lib/node_modules node .../upload.mjs instagram login --account happylife2080100
NODE_PATH=/opt/homebrew/lib/node_modules node .../upload.mjs threads   login --account happylife2080100
NODE_PATH=/opt/homebrew/lib/node_modules node .../upload.mjs tiktok    login --account aigroove99
```

로그인 창이 열리면 사용자가 직접 로그인한다(비밀번호 자동입력 안 함 — 보안). 최대 5분 대기.

### 2) 발행 전 계정 확인 (권장)

```bash
NODE_PATH=... node .../upload.mjs instagram whoami --account happylife2080100
# → RESULT {"ok":true,...,"handle":"happylife2080100"}
```

핸들이 기대와 다르면 그 계정은 로그아웃됐거나 잘못된 프로필이다 — 발행하지 말고 다시 login.

### 3) 발행

```bash
# 캡션은 셸 이스케이프 사고를 막기 위해 임시파일+`$(cat)`을 쓰는 것이 안전하다.
CAP="$(cat /tmp/caption.txt)"
NODE_PATH=/opt/homebrew/lib/node_modules node .../upload.mjs \
  instagram post /path/to/video.mp4 "$CAP" --account happylife2080100 --expect happylife2080100 --auto
```

플랫폼은 한 번에 하나씩 호출한다. 한 플랫폼이 실패해도 다음 플랫폼 발행을 막지 않는다 —
결과 JSON을 모아 채널별 성공/실패를 리포트한다.

## 플랫폼별 특이사항

- **Instagram** — Create→Post 진입 중 인터스티셜 모달(로그인 정보 저장/알림/약관)을
  자동으로 닫고, "릴스로 공유됩니다" 안내(확인)도 처리. 영상 처리 시간 동안 `다음/Next`를
  최대 8회 적응적으로 누른 뒤 캡션을 넣는다. `--expect`로 오발행을 막는다. 실패 시
  `/tmp/ig-fail-*`에 스크린샷+DOM 덤프.
- **Threads** — 도킹형 컴포저(New thread / 만들기 / "새로운 소식이 있나요?")를 연 뒤
  캡션 입력 → 파일 업로드 → 처리 대기 → Post.
- **TikTok** — TikTok Studio 업로드 페이지. 첫 실행 시 react-joyride 투어 오버레이를 제거한다.
  **저작권/콘텐츠 검사가 끝날 때까지 기다린 뒤** Post를 누른다(검사 중 발행하면 "나만 보기/검토중"으로
  고정될 수 있음 — 최대 ~13분). 검사 미완료 모달이 뜨면 "Post now"로 확인. 진행 스크린샷은
  `~/.social-upload/shots/`.

셀렉터·발행 흐름은 플랫폼 UI 변경으로 깨질 수 있다. 깨졌을 때의 진단·복구는
`references/troubleshooting.md` 참고.

## 실패 처리 원칙

- **계정 격리** — 한 계정/플랫폼 실패가 다른 발행을 막지 않는다. 기록하고 계속.
- **로그인 자동 시도 금지** — 로그아웃 상태면 그 계정은 건너뛰고 `login` 필요를 알린다(비번 자동입력 X).
- **되돌리기 없음** — 이미 나간 게시물은 자동 삭제하지 않는다. 잘못 나갔으면 명시하고 사용자가 직접 내린다.
