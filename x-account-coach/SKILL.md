---
name: x-account-coach
description: 본인 X (Twitter) 계정의 최근 타임라인 (main + replies + thread 펼침, 기본 7일치) 을 Chrome CDP 인증 세션으로 수집하고, 현재 작업 디렉토리의 마케팅 플레이북·캘린더 (예 `docs/NON-DEV-PLAYBOOK.md`, `docs/NON-DEV-CALENDAR.md`) 와 결합해 다음에 올릴 트윗 후보 3개를 추천하는 워크플로우. 사용자가 "내 다음 X 트윗 뭐 올려?", "다음 X post 추천해줘", "내 트위터 최근 거 보고 다음 거 추천", "next tweet for my X account", "what should I post next on X" 비슷한 마케팅 목적 표현을 쓸 때 발동. 단순 트윗 작성 도우미가 아니라 *프로젝트 컨텍스트* (요일별 테마, 주차별 focus, 톤 가이드, founder positioning) 를 반영한 추천이 핵심. Chrome CDP (포트 9222) 의 인증된 X 세션을 사용하므로 X 로그인이 사전 조건. Read-only — 트윗 작성·DM·팔로우 등 쓰기 동작은 절대 X.
---

# X Account Coach — 다음 트윗 추천

## 무엇을 하는 skill 인가

본인 X 계정의 최근 활동을 보고, 현재 작업 디렉토리의 마케팅 자료를 합쳐서 **다음에 올릴 트윗 후보 3개를 깊이 있게 추천**한다. 단순한 카피 생성이 아니라:

- 최근 7일 내 무엇을 이미 올렸는지 (각도 중복 회피)
- 어떤 게 잘 됐고 (likes/RT/views) 어떤 게 묻혔는지 (engagement 학습)
- 오늘이 주차 몇 째, 무슨 요일인지 → 캘린더의 슬롯 테마 선택
- 플레이북의 founder positioning · 톤 가이드 · 콘텐츠 mix 비율 준수

읽기 전용. 추천만 하고 절대 자동 게시 안 함.

## 왜 이 흐름인가 — 설계 배경

X 는 SPA 이고 모든 데이터는 내부 GraphQL endpoint 에서 온다. `UserTweetsAndReplies` (= 본인 main + replies + thread 부분 모두 포함) 가 핵심. queryId 는 X 배포마다 바뀌므로 하드코딩 불가 — 본인 프로필 페이지 한 번 열어 첫 요청을 가로채면 (a) queryId 박힌 URL 템플릿, (b) 정확한 헤더 (Bearer / csrf-token / client-uuid 등), (c) 첫 페이지 payload 모두 얻는다. 그 뒤로는 cursor 만 갈아끼우며 직접 호출.

이 패턴은 같은 Chrome 프로파일 (`$HOME/chrome-cdp-profile`) 을 공유하는 자매 skill `x-cdp-search`, `naver-cafe-scrape` 와 동일하다.

## 사전 조건

자동 probe 한다. 실패 시 사용자에게 안내하고 진행 안 함.

1. **Chrome CDP 9222 포트 응답** — `curl -s http://localhost:9222/json/version`
2. **X 로그인 상태** — `auth_token` + `ct0` 쿠키가 `x.com` 도메인에 존재
3. **프로젝트 컨텍스트 (선택)** — `docs/NON-DEV-PLAYBOOK.md`, `docs/NON-DEV-CALENDAR.md` 또는 비슷한 마케팅 자료가 cwd 에 있으면 자동 활용. 없으면 추천 깊이가 얕아짐을 사용자에게 고지.

## CDP 띄우는 명령어 (사용자가 미리 실행)

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

이미 띄워져 있으면 새로 띄울 필요 없다. `x-cdp-search` 또는 `naver-cafe-scrape` 용으로 떠 있으면 X 로그인만 확인하면 된다.

## 사용자 인풋에서 추출할 정보

| 항목 | 예시 | 필수 |
|---|---|---|
| 본인 X 핸들 | `tvprogramlover` | 필수 (한 번 알려주면 메모 가능) |
| 최근 며칠 | `7`, `14` | 선택 (기본 7) |
| 트윗 최대 수 | `50`, `100` | 선택 (기본 50) |

핸들은 사용자가 처음 호출할 때 안 알려주면 한 번 묻는다. 그 후 같은 세션에선 묻지 말 것.

## 핵심 스크립트

`scripts/x_user_timeline.py` 한 파일. CDP 인증 세션으로 본인 타임라인 수집해 JSON 으로 저장.

### 1. 사전 조건 probe 만

```bash
python ~/.claude/skills/x-account-coach/scripts/x_user_timeline.py --probe
```

### 2. 본 수집

```bash
python ~/.claude/skills/x-account-coach/scripts/x_user_timeline.py \
  --handle tvprogramlover --days 7 --max 50 --out /tmp/x_my_timeline.json
```

옵션:
- `--handle <name>` — 본인 핸들 (필수, `@` 빼고)
- `--days <N>` — 최근 N 일 이내 트윗만 (기본 7)
- `--max <N>` — 최대 트윗 수 안전상한 (기본 50)
- `--out <path>` — 출력 JSON 경로 (기본 `/tmp/x_my_timeline.json`)
- `--probe` — 로그인만 확인하고 종료

## 권장 실행 흐름

1. **확인 단계** — `--probe` 로 CDP·로그인 검증.
2. **타임라인 수집** — 위 본 수집 명령. 보통 5–30 초 소요.
3. **프로젝트 컨텍스트 로드** — cwd 에서 다음 파일을 자동 검색해 읽는다 (있는 것만):
   - `docs/NON-DEV-PLAYBOOK.md`
   - `docs/NON-DEV-CALENDAR.md`
   - `docs/specs/*.md` (있으면 design spec)
   - `README.md` (제품 설명)
4. **분석 + 추천 생성** — 아래 "추천 생성 가이드" 섹션 따라 인라인으로 작성.
5. **출력** — 채팅창에 추천 후보 3개, 각각 char count·근거·이미지 제안 포함. 절대 raw JSON 을 채팅에 붙여넣지 말 것.

## 출력 형식 (수집된 JSON)

```json
[
  {
    "id": "1234567890",
    "text": "Week 1/16 building channel-guard 🧵 ...",
    "created_at": "Fri May 09 12:00:00 +0000 2026",
    "category": "main" | "reply" | "thread_part",
    "in_reply_to": "1234567889" | null,
    "likes": 42, "retweets": 5, "replies": 3, "quotes": 1, "views": 12345,
    "lang": "en",
    "url": "https://x.com/tvprogramlover/status/1234567890"
  }
]
```

## 추천 생성 가이드 (Claude 가 이 단계를 직접 수행)

타임라인 JSON 과 프로젝트 컨텍스트가 준비된 후, 다음 순서로 추천을 만든다:

### 1. 오늘의 슬롯 결정

- 오늘 날짜 (`date +%Y-%m-%d`, 시스템 tz = KST) 와 요일 확인.
- 캘린더에서 현재 주차 (예: Week N/16) 와 그 주의 focus 추출.
- 캘린더의 "Day-of-week routine" 표 또는 플레이북 §2.1 의 콘텐츠 mix 에서 오늘 요일의 테마 슬롯 추출 (예: 월 = dev progress, 금 = weekly recap, 토 = personal story).
- 캘린더·플레이북이 없으면 사용자에게 "프로젝트 컨텍스트 없이 일반 추천만 가능" 고지.

### 2. 최근 7일 활동 분석

수집된 JSON 에서:

- **각도 분류**: main 트윗을 dev / pain / policy / story / recap 등 테마로 자동 분류 (텍스트 키워드 기반).
- **engagement 통계**: 평균 likes/RT/views, 상위 3개 / 하위 3개 트윗.
- **반복 위험**: 마지막 N 일 내 같은 테마·같은 후크가 2회 이상이면 회피 대상으로 표시.

### 3. 후보 3개 생성 — 다음 원칙 준수

각 후보는 서로 다른 각도. 단순 문장 변형 X.

- **오늘 슬롯 테마 1차 매칭** — 오늘이 화요일 = pain quote 슬롯이면 후보 3개 중 최소 2개는 pain quote 변종.
- **각도 중복 회피** — 최근 7일 내 이미 다룬 후크·구조 그대로 재사용 X.
- **잘 된 패턴 강화** — 상위 3개 트윗의 공통 구조 (예: 짧은 후크 + 숫자 + 한 줄 결론) 가 있으면 그 구조 활용.
- **묻힌 패턴 회피** — 하위 3개 트윗의 공통 약점 (예: 너무 길거나, 해시태그 4개 이상이거나, 링크 본문 포함) 피하기.
- **founder positioning** 일관성 — 플레이북 §2.1 에 박힌 톤 (build-in-public, 솔직한 실패담, operator 척 X) 그대로. 반대 방향 후보는 제외.
- **char count 명시** — 각 후보 끝에 `(N chars)` 표기. 280 자 (X Premium 미사용 가정) 이하.
- **placeholder 허용** — 본인이 채워넣어야 할 부분 (`{N}` 같은 숫자, `{LINK}`) 은 그대로 둔다. 본 데이터 모를 때 거짓 숫자 만들지 말 것.
- **이미지 제안** — 텍스트 only / 스크린샷 종류 / GIF / 데이터 차트 등 한 줄 제안.

### 4. 출력 템플릿

다음 형식으로 채팅에 출력:

```
## 다음 X 포스트 추천 — <YYYY-MM-DD> <요일>

**오늘 슬롯**: <테마 이름> (예: weekly-recap)
**현재 주차**: Week <N>/<TOTAL> — <focus 요약 1줄>
**최근 7일 활동**: <main N개 / reply N개 / thread N개>, 평균 likes <N>, 상위 트윗 후크: <한 줄>

---

### 후보 1 — <각도 라벨> (<N chars>)

```
<draft 본문>
```

근거: <왜 이 각도인지 1-2줄 — 어떤 슬롯·어떤 successful pattern 활용·어떤 회피 함>
이미지: <한 줄 제안>

### 후보 2 — ... (동일 구조)

### 후보 3 — ... (동일 구조)

---

추천 톤 일관성 체크: <플레이북 §2.1 기준 통과 여부 한 줄>
```

### 5. 반드시 지킬 것

- **거짓 숫자·거짓 사실 금지**. 본인이 안 한 일 (예: "lost 3 channels") 절대 후보에 넣지 말 것. 모르는 부분은 `{PLACEHOLDER}` 로.
- **자동 게시 X**. 출력은 추천만. 사용자가 직접 X 에 붙여넣어 게시.
- **JSON 본문 채팅 출력 X**. 파일 경로 안내 + 분석 결과만.
- **사용자 톤 모방** > 일반 AI 톤. 수집된 트윗에서 founder voice 추출해 그 voice 로 작성.

## 트러블슈팅

### CDP 9222 미응답
Chrome 종료. 위 CDP 명령어로 다시 띄우라고 사용자에게 요청.

### 로그인 쿠키 부족
그 Chrome 창에서 X 다시 로그인. `--user-data-dir` 가 매번 동일한 경로 (`$HOME/chrome-cdp-profile`) 인지 확인.

### "UserTweetsAndReplies endpoint 캡처 실패"
- 로그인 풀림, X 가 access 차단, 또는 핸들이 잘못됨.
- 핸들이 정확한지 (오타·대소문자) 사용자에게 확인 요청.
- probe 부터 다시.

### HTTP 401 / 403 응답
세션 만료 또는 CSRF 토큰 불일치. Chrome 창에서 X 페이지 새로고침해 새 ct0 발급받게 하고 retry.

### 결과 너무 적음 (1–2 페이지에서 끊김)
정상일 수 있음 — 본인 트윗이 7일 내 적으면 그게 다임. 또는 X 의 per-account soft rate-limit. 10–30 분 대기 후 retry. 절대 같은 호출 반복하지 말 것.

### 프로젝트 컨텍스트 파일 없음
플레이북·캘린더 부재 → 일반 추천만 가능. 사용자에게 고지하고 진행 여부 묻기. 추천 깊이가 얕아짐을 명시.

## Rate-limit 위생 (중요)

이 skill 은 사용자 실 X 계정 세션을 사용한다. 계정은 희소 자원으로 취급.

- 페이지 사이 sleep: `PAGE_DELAY = (1.8, 3.4)` 초. 줄이지 말 것.
- 한 번 수집 후 최소 30 초 대기 후 다음 호출.
- 스케줄·cron 으로 반복 실행 요청 받으면 거부. 마케팅 도구는 on-demand 만.
- 결과가 적으면 retry 하지 말고 stop.

## 이 skill 이 하지 않는 것

- **모든 쓰기 동작** — 트윗 작성·삭제·좋아요·RT·팔로우·DM. read-only.
- **타인 계정 분석** — 본인만. 타인 분석은 별도 도구 (e.g., `x-cdp-search` 의 핸들 검색) 활용.
- **자동 스케줄 게시** — 추천만, 게시는 사용자가 수동.
- **숫자·사실 fabrication** — 모르는 부분은 placeholder 로 남기고 사용자에게 채우라고 안내.

사용자가 위 항목을 요청하면 skill 이 추천 전용임을 안내하고 거부.
