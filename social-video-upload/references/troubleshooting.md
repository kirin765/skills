# Troubleshooting

플랫폼 UI가 바뀌면 셀렉터 기반 발행이 깨진다. 증상별 진단·복구.

## 공통

- **실행은 되는데 아무 일도 안 일어남 / `RESULT {"ok":false,"error":...}`** — 에러 메시지를 먼저 본다.
  대부분 "not logged in"(→ `login` 재실행) 또는 셀렉터 미발견(→ 아래 플랫폼별).
- **`Cannot find package 'playwright'`** — `NODE_PATH=/opt/homebrew/lib/node_modules`를 빠뜨렸다.
  글로벌 playwright 경로가 다르면 `npm root -g`로 확인해 맞춘다.
- **프로필이 잠김(`SingletonLock`/`profile is already in use`)** — 같은 프로필을 쓰는 Chrome이
  이미 떠 있다. 그 창을 닫거나, 해당 계정 발행이 동시에 두 번 실행되지 않게 한다.
- **로그인이 풀림** — IG/TikTok은 주기적으로 재인증을 요구한다. `whoami`로 확인하고 필요시 `login`.

## Instagram

- **`Create SVG not found`** — 좌측 내비의 만들기/Create 아이콘 aria-label이 바뀌었다.
  `/tmp/ig-fail-no-create-svg-*/dom.html`에서 현재 aria-label을 찾아 `lib/instagram.mjs`의
  `createSvg` 셀렉터에 추가한다.
- **`composer file input never appeared`** — 컴포저가 안 떴거나 인터스티셜 모달이 막았다.
  `/tmp/ig-fail-*`의 스크린샷 확인. 새 모달 버튼 텍스트를 `dismissInterstitials`의 labels에 추가.
- **`caption editable never appeared`** — 영상 처리가 8스텝 안에 안 끝났거나 `다음/Next` 라벨이
  바뀌었다. 루프 횟수/대기 시간 또는 next 버튼 셀렉터를 조정.
- **`IG account mismatch`** — `--expect`로 막힌 정상 동작. 프로필이 다른 계정으로 로그인됨.
  의도한 계정으로 `login`하거나 `--account`를 맞춘다.

## Threads

- **`composer trigger not found`** — 글쓰기 진입 버튼 텍스트가 바뀌었다(영문/한글 도킹·모달).
  현재 화면의 버튼 텍스트를 `lib/threads.mjs`의 셀렉터 목록에 추가.
- **`Post button not found/enabled`** — 미디어 처리가 안 끝났거나 게시 버튼이 비활성.
  업로드 후 대기(`sleep`)를 늘리거나 재시도 루프 횟수를 올린다.

## TikTok

- **`Checking in progress`가 13분 넘게 안 끝남** — 콘텐츠 검사가 비정상적으로 길다.
  `~/.social-upload/shots/tiktok_3_ready.png` 확인. 발행을 미루거나 수동 게시.
- **`POST UNCONFIRMED`** — 클릭은 했으나 성공 토스트/리다이렉트를 못 봤다.
  `~/.social-upload/shots/tiktok_5_after.png`로 실제 게시 여부 확인. 종종 실제로는 올라가 있다.
- **투어 오버레이가 클릭을 막음** — `dismissTours`가 react-joyride 포털을 제거한다.
  새 온보딩 형태면 포털 셀렉터를 갱신.
