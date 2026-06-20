---
name: youtube-upload
description: YouTube Data API v3로 영상을 사용자 채널에 무인 업로드하는 워크플로우 — 영상 파일 + 제목/설명/태그 + 커스텀 썸네일을 받아 업로드하고 watch URL을 반환한다. 사용자가 "유튜브에 올려줘", "YouTube 업로드", "이 영상 유튜브에 게시", "프로모 영상 업로드", "upload to YouTube", "유튜브 자동 업로드" 같은 표현을 쓰거나, 방금 만든 영상(HyperFrames/Remotion 렌더 결과 등)을 YouTube에 올리자고 할 때 반드시 발동. 브라우저 없이 OAuth 리프레시 토큰 + REST로 처리. 기본 공개범위 unlisted. 영상 다운로드·분석·SEO는 이 스킬이 아니다.
---

# YouTube Upload

영상 파일과 메타데이터를 받아 YouTube Data API v3 `videos.insert`(resumable)로 업로드한다.
Play Store 업로드(`android-app-builder`)와 달리 **서비스 계정은 못 쓴다** — YouTube 채널은
Google 계정 귀속이라 OAuth 2.0 리프레시 토큰이 유일한 경로다.

## 고정 경로

| 항목 | 값 |
|---|---|
| GCP 프로젝트 | `claude-android-upload` (YouTube OAuth 전용; Play API는 claude-for-android로 분리) |
| venv | `~/.config/youtube-upload/venv` |
| 토큰 | `~/.config/youtube-upload/token.json` (yt_auth.py가 생성) |
| 스크립트 | 이 스킬의 `scripts/yt_auth.py`, `scripts/yt_upload.py` |

## 업로드 워크플로우

1. **메타데이터 수집** — 대화에서 받는다. 필수: 영상 경로, 제목(≤100자). 선택: 설명, 태그,
   썸네일, 공개범위. 사용자가 안 정한 값의 기본: **privacy=unlisted**, category=22,
   language=ko, made-for-kids=false. 설명이 여러 줄이면 임시 파일에 쓰고
   `--description-file`로 넘긴다 (셸 이스케이프 사고 방지).
2. **사전 점검** — `token.json` 없으면 아래 "1회성 셋업"으로. 썸네일은 2MB 초과 시 먼저 압축.
3. **실행**:
   ```bash
   ~/.config/youtube-upload/venv/bin/python \
     ~/.claude/skills/youtube-upload/scripts/yt_upload.py \
     --video <path> --title "<제목>" --description-file /tmp/desc.txt \
     --tags "태그1,태그2" --thumbnail <png> --privacy unlisted
   ```
4. **결과 보고** — 스크립트가 출력한 `https://youtu.be/<id>` URL을 사용자에게 전달.
   여러 편 업로드 시 표로 정리.

### public 업로드 주의

미인증(unaudited) API 프로젝트로 올린 public 영상은 YouTube가 **private으로 강제 잠금**할
수 있다. 그래서 기본이 unlisted다. 사용자가 public을 원하면: unlisted로 올리고 사용자가
Studio에서 수동 전환하는 쪽을 권하되, 직접 public 업로드를 고집하면 올린 뒤 영상 상태를
확인해 잠겼는지 보고한다.

### 쿼터

업로드 1건 = 1,600 유닛, 일일 한도 10,000 → **하루 약 6편**. `quotaExceeded` 에러가 나면
태평양 시간 자정에 리셋된다고 안내하고 남은 작업을 다음 날로 미룬다.

## 1회성 셋업 (token.json 없을 때만)

1. **YouTube Data API v3 활성화** — 사용자에게 링크 안내:
   https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=claude-android-upload
2. **Desktop 타입 OAuth 클라이언트 생성** — 기존 web 타입 클라이언트는 redirect URI 미등록이라
   못 쓴다. Credentials > Create Credentials > OAuth client ID > **Desktop app**으로 새로 만들고
   JSON 다운로드. https://console.cloud.google.com/apis/credentials?project=claude-android-upload
3. **동의화면 확인** — 게시 상태가 "테스트"면 리프레시 토큰이 **7일 만에 만료**된다.
   "프로덕션 게시"로 전환 권장(심사 없이 게시 가능, scope 경고 화면만 뜸). 테스트 유지 시
   업로드할 채널의 Google 계정을 테스트 사용자에 추가해야 한다.
4. **venv 생성**:
   ```bash
   python3 -m venv ~/.config/youtube-upload/venv
   ~/.config/youtube-upload/venv/bin/pip install google-api-python-client google-auth-oauthlib
   ```
5. **토큰 발급** — 브라우저 동의가 필요하므로 사용자가 자리에 있을 때 실행.
   채널을 소유한 Google 계정으로 승인해야 한다:
   ```bash
   ~/.config/youtube-upload/venv/bin/python \
     ~/.claude/skills/youtube-upload/scripts/yt_auth.py \
     --client-secret <다운로드한 Desktop client JSON>
   ```
6. 성공하면 client_secret JSON을 `~/.config/youtube-upload/`로 옮겨 보관 (Downloads 방치 금지).

## 실패 시

- `401 invalid_grant` — 토큰 만료/철회. 동의화면이 테스트 모드면 7일 만료가 원인.
  yt_auth.py 재실행으로 복구하고, 프로덕션 게시 전환을 다시 권한다.
- `403 quotaExceeded` — 위 쿼터 절 참조.
- `400 invalidTitle/invalidDescription` — 제목 100자, 설명 5,000자 한도. `<`, `>` 문자 불가.
- 업로드는 됐는데 처리 안 끝남 — 정상. YouTube 측 인코딩은 수 분 걸린다. URL만 전달하면 된다.
