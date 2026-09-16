---
name: google-tasks
description: >-
  사용자 Google Tasks에 메모·할 일을 공식 Tasks REST API로 생성/조회하는 스킬
  (OAuth 데스크톱 플로우, loopback 자동 수신, 토큰 캐시 재사용). 사용자가
  "Google Tasks에 메모해줘", "memo this to Google Tasks", "할 일/메모/리마인더
  등록해줘", "tasks.google.com에 올려줘" 같은 요청을 하면 사용한다 — 할 일 목록
  작성 요청과도 겹쳐도 된다. 번들 스크립트 scripts/google_tasks.mjs가 인증부터
  insert/list까지 처리한다. 자격증명: ~/.config/rb-gtasks/client.json (OAuth
  데스크톱 클라이언트 JSON), 토큰 캐시: ~/.config/rb-gtasks/token.json.
  GOTCHA: Cloud 프로젝트에서 "Google Tasks API"를 Enable 해야 하고, 동의 코드는
  1회용이라 중간 크래시 시 재동의, loopback 포트 8599.
---

# Google Tasks — 메모/할 일 생성 (공식 API)

사용자 구글 계정의 Tasks에 task를 만드는 스킬. 공식 REST API(`tasks.googleapis.com/tasks/v1`)를 쓰며, OAuth 인증의 번거로움은 번들 스크립트가 처리한다.

## 준비물 (이미 설정됨 — 변경 없이 사용)

- 자격증명: `~/.config/rb-gtasks/client.json` — Google Cloud Console에서 만든 **데스크톱 앱** OAuth 클라이언트 JSON. (SKILL.md·git에 시크릿을 넣지 말 것.)
- 토큰 캐시: `~/.config/rb-gtasks/token.json` — 최초 1회 인증 후 자동 저장/갱신(offline access + refresh 토큰).
- 실행기: Node 20+ (시스템 `node`로 직접 실행, 의존성 없음).

## 사용법

```bash
# 생성 (제목 필수, 메모/기한/리스트 선택)
node ~/.dsh/skills/google-tasks/scripts/google_tasks.mjs create \
  --title "제목" --notes "메모..." --due 2026-09-04

# 조회
node ~/.dsh/skills/google-tasks/scripts/google_tasks.mjs list --limit 10
node ~/.dsh/skills/google-tasks/scripts/google_tasks.mjs lists
```

- `--due`는 `2026-09-04`(KST 자정) 또는 `2026-09-04T09:00:00+09:00` 형식.
- `--list` 기본값 `@default`(기본 목록). `lists` 명령으로 다른 목록 id 확인 가능.

## 첫 실행 흐름 (1회)

1. 스크립트가 콘솔에 인증 URL을 출력하고 `localhost:8599`에서 대기한다.
2. **사용자에게 URL을 열어 동의하라고 안내** — 브라우저에서 계정 선택 → Allow.
3. 동의 완료 시 코드가 자동 복귀 → 토큰 저장 → task 생성.
4. 이후 실행은 토큰 재사용(만료 시 자동 refresh), 추가 동의 불필요.

> 스크립트를 백그라운드로 돌렸다면 `job_output`으로 URL을 뽑아 사용자에게 전달하고, 완료될 때까지 기다린다.

## 흔한 실패 패턴

| 증상 | 원인/처치 |
|---|---|
| `403` / Tasks API 사용 안 됨 | Cloud 프로젝트에서 **Google Tasks API를 Enable** 안 함. 사용자가 콘솔에서 활성화하면 됨. |
| `invalid_grant` / `redirect_uri_mismatch` | 동의 코드는 **1회용**. 스크립트가 중간에 죽으면 처음부터 재실행 + 재동의. loopback은 `http://localhost:8599` 고정 — 포트를 바꾸면 다시 안내. |
| 브라우저가 안 열림 | URL을 직접 복사해 사용자에게 전달. |

## 원칙

- 사용자 계정 데이터는 읽기/쓰기 모두 사용자가 명시적으로 요청한 task에만.
- 시크릿(클라이언트 시크릿·토큰)을 출력·로그·프롬프트에 노출하지 말 것.
- 제목·메모는 사용자 언어(한국어) 그대로, 날짜는 KST 기준으로 해석.