# 계정 맵 + 세션 검증

각 채널은 정해진 계정으로만 발행한다. 한 Chrome 프로필에 여러 계정(특히 구글 2개:
happylife2080 ↔ gksrkdls1982)이 섞여 있어 **발행 직전 계정 확인이 이 스킬에서 가장 깨지기 쉬운 부분**이다.
틀린 계정으로 나가면 되돌리기 어렵다.

| 채널 | 계정 | 로그인 URL |
|---|---|---|
| Instagram | happylife2080@gmail.com (IG: happylife2080100) | instagram.com |
| Threads | happylife2080100 (Meta, IG 연동) | threads.net / threads.com |
| X | Giwan | x.com |
| TikTok | @aigroove99 | tiktok.com |
| YouTube | gksrkdls1982@gmail.com | (API — 브라우저 무관) |
| inpock | happylife2080@gmail.com | link.inpock.co.kr/admin |
| disquiet | 런타임 확인 (보통 happylife2080100) | disquiet.io |

## 검증 절차 (발행 전 채널마다)

**IG·Threads·TikTok** — `social-video-upload`의 `whoami`로 확인한다. 각 (플랫폼,계정)은
전용 영구 프로필을 쓰므로 한 프로필에서 계정이 섞이지 않는다.

```bash
NODE_PATH=/opt/homebrew/lib/node_modules \
  node ~/.claude/skills/social-video-upload/scripts/upload.mjs <platform> whoami --account <표의 계정>
```

`RESULT`의 `handle`이 표와 일치하면 발행. 불일치/`null`이면 건너뛰고 리포트에 기록한 뒤
`login` 명령으로 사용자가 직접 로그인하도록 안내.

**X** — Claude in Chrome으로 x.com 홈/프로필을 열어 `get_page_text`/`find`로 핸들 확인.

공통 원칙:
- **비밀번호 자동 입력·자동 로그인 시도 금지.** 로그인·계정 전환은 사용자가 직접 한다.
- 불일치 시 "X 채널이 <틀린계정>으로 로그인됨(또는 로그아웃). <맞는계정>으로 login 하면
  그 채널만 다시 올릴게"라고 안내.

## 멀티 구글 계정 주의

IG/Threads/inpock(happylife2080)와 YouTube(gksrkdls1982)는 서로 다른 구글 계정이다.
YouTube는 API라 브라우저 계정과 무관(토큰이 gksrkdls1982 채널에 묶여 있음). 브라우저 쪽에서
구글 계정 전환이 일어나도 YouTube 업로드에는 영향 없다.
