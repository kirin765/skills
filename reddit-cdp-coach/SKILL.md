---
name: reddit-cdp-coach
description: Reddit 활동 코칭 워크플로우 — 사용자의 인증된 Chrome 세션(**Claude in Chrome 확장**, `mcp__Claude_in_Chrome__*`)으로 (1) 사용자가 댓글 달 만한 글 후보를 타겟 서브레딧에서 찾아 랭킹 (모드 B), 또는 (2) 특정 thread URL 을 받아 본인 톤에 맞는 댓글 초안 2~3개를 생성 (모드 C). 사용자가 "댓글 달만한 글 찾아줘", "오늘 r/FacelessYouTube hot 뭐?", "Reddit 어디 댓글 달까", "find Reddit threads to comment on", "이 글 댓글 달아줘 https://reddit.com/...", "이 thread 댓글 추천", "draft a comment for this Reddit post" 비슷한 표현을 쓸 때 발동. 본인 reddit history 와 함께 제공된 voice guide (`references/voice-guide.md`) 를 참고해 non-native English speaker 가 founder peer 톤으로 댓글 달 수 있게 도움. 인증된 reddit 세션 사용 — reddit 로그인 사전 조건. Read-only — 댓글·투표·게시 등 쓰기 동작 절대 X. 추천만 하고 사용자가 직접 reddit 에 게시.
---

# Reddit CDP Coach — 댓글 후보 찾기 & 댓글 초안

## 무엇을 하는 skill 인가

Reddit 에서 본인이 가치 있는 댓글을 달 수 있도록 두 단계로 돕는다:

- **모드 B (discovery)** — 타겟 서브레딧들에서 최근 24~48 시간 글 중 *댓글 달 만한* 후보를 랭킹. 너무 잠긴 megathread 도 아니고 너무 묻힌 dead post 도 아닌, mid-engagement 스윗스팟에서 본인이 가치 답글 가능한 글을 골라줌.
- **모드 C (draft)** — 사용자가 thread URL 을 주면 OP 글 + 기존 top 댓글 읽고, 본인 톤에 맞는 댓글 초안 2~3개 생성 (각도 다양하게).

읽기 전용. 추천만 하고 자동 게시 안 함. 모든 댓글은 사용자가 직접 reddit 에 paste · edit · 게시.

## 왜 이 흐름인가 — 설계 배경

Reddit 은 X 와 달리 `.json` suffix 만 붙이면 대부분 endpoint 가 안정적인 JSON 을 반환한다. GraphQL endpoint discovery·헤더 가로채기가 필요 없다 — **그래서 Claude in Chrome 확장으로 그 `.json` URL 을 새 탭에서 직접 열어 `get_page_text` 로 JSON 을 읽으면 된다.** 인증된 세션을 그대로 타므로(쿠키 자동 첨부) 높은 rate-limit·personalized 결과·hidden/saved subs 에 접근 가능.

> **이 스킬은 CDP·Playwright·포트 9222 를 쓰지 않는다.** 전적으로 Claude in Chrome 확장으로 동작.
> 물리 마우스를 뺏지 않고 전용 MCP 탭 그룹에서만 작업한다.

본인 reddit history 는 voice 학습의 1차 소스. non-native English speaker 의 founder peer 톤은 따로 정리한 voice guide (`references/voice-guide.md`) 가 보조.

## 사전 조건

1. **Chrome 확장 연결** — `mcp__Claude_in_Chrome__list_connected_browsers`. 0개면 사용자에게 확장 설치·연결 요청 후 멈춤. 2개+면 `AskUserQuestion` 으로 선택 → `select_browser`. 전용 프로파일이 있으면 메인 브라우저 방해를 피하려 그쪽을 권한다(단 그 프로파일에 reddit 로그인 필요 — 쿠키 비공유).
2. **Reddit 로그인 상태** — 0단계로 `https://www.reddit.com/api/me.json` 을 읽어 `data.name`(본인 username) 이 나오면 OK. 비거나 로그인 페이지면 멈추고 사용자에게 그 프로파일에서 reddit 로그인 요청. **자동 로그인 안 함.**

## 데이터 수집 — 확장으로 JSON endpoint 읽기

핵심 패턴(모든 모드 공통):
```
tabs_context_mcp(createIfEmpty: true)          # 격리된 MCP 탭 그룹 확보
tabs_create_mcp()                              # JSON 읽기용 새 탭
navigate(tabId, "<reddit .json URL>")          # SPA 라우터 회피 위해 새 탭 사용
get_page_text(tabId)                           # body = raw JSON → Claude 가 파싱
```
끝나면 `tabs_close_mcp` 로 정리. 같은 탭을 다음 URL 로 `navigate` 재사용해도 됨.

### 0. probe / username — 로그인 확인
`https://www.reddit.com/api/me.json` → `data.name` = 본인 username. 401/HTML 이면 로그인 안 됨.

### history — 본인 최근 글·댓글 수집 (voice 학습용)
- 댓글: `https://www.reddit.com/user/{username}/comments.json?limit=30`
- 글: `https://www.reddit.com/user/{username}/submitted.json?limit=10`
- 더 필요하면 응답의 `data.after` 를 `&after=<t1_xxx>` 로 붙여 다음 페이지.
각 항목에서 `data.children[].data` 의 body/title/selftext/subreddit/score/created_utc/permalink/num_comments 추출.

### discover (모드 B) — 댓글 달 만한 글 후보 찾기
타겟 sub 마다: `https://www.reddit.com/r/{sub}/new.json?limit=25`
기본 sub 6개 = `FacelessYouTube`, `SmallYouTubers`, `NewTubers`, `AIcontent`, `SideProject`, `microsaas`.
(사용자가 sub 좁히면 그것만. 최근 N시간 컷오프는 `created_utc` 로 Claude 가 필터 — 기본 48h.)
각 글 = `data.children[].data`: title/selftext/score/upvote_ratio/num_comments/created_utc/stickied/locked/link_flair_text/author/permalink/url.

### thread (모드 C) — 특정 thread 의 OP+댓글 fetch
thread URL 끝에 `.json` 을 붙이고 쿼리 추가: `{permalink}.json?limit=50&depth=2`
(`old.reddit.com`/`www.reddit.com`/`sh.reddit.com` 모두 `www` 로 정규화, 끝 슬래시 정리.)
응답은 배열 `[listing0, listing1]`: `listing0.data.children[0].data` = OP, `listing1.data.children[].data` = top 댓글(각 author/body/score/created_utc; OP author 와 같으면 `is_op_reply` 취급).

## 권장 실행 흐름

### 모드 B (discovery)
1. **사용자 인풋 파악** — "오늘 댓글 달 만한 글 찾아줘" → discover. 특정 sub 만이면 그것만.
2. **브라우저 선택 + 로그인 확인** (사전 조건).
3. **history** 가 stale(>3일) 이거나 미수집이면 새로 읽음. 1회 후 재사용.
4. **discover** — sub 마다 `/r/{sub}/new.json` 읽어 후보 모음.
5. **랭킹 + 출력** — 아래 "모드 B 랭킹 가이드" 따라 인라인 작성. raw JSON 채팅 출력 X.

### 모드 C (draft)
1. **URL 추출** — 사용자 메시지에서 reddit URL. 없으면 한 번 묻기.
2. **브라우저 선택 + 로그인 확인**.
3. **history** 가 stale 이면 새로 읽음.
4. **thread** — `{permalink}.json?limit=50&depth=2` 읽어 OP + top 댓글.
5. **드래프트 생성** — 아래 "모드 C 드래프트 가이드" 따라 인라인 작성. 각 후보 끝에 char count.

## 모드 B 랭킹 가이드 (Claude 가 직접 수행)

수집된 candidate JSON 과 history 를 받은 후:

### 1. 필터 (자동 제거)

- 모드레이터 pinned/announcement 글 (`stickied: true`)
- megathread (제목에 "Megathread", "Weekly", "Daily" 포함)
- locked thread (`locked: true`)
- 너무 오래된 글 (24~48h 컷오프, `created_utc` 기준)
- crosspost 만 있고 본문 없는 글
- comment 1000+ — 이미 묻힘
- comment 0 + age >12h — dead

### 2. 점수 (각 글에 0~100)

| 신호 | 가중 | 설명 |
|---|---|---|
| age 4~24h | +30 | 새로 올라온 활동 중인 글이 답글 reach 좋음 |
| comments 5~80 | +25 | mid-engagement 스윗스팟 |
| upvote ratio ≥ 0.85 | +15 | OP 가 신뢰받음 |
| 본인 history 키워드 매칭 | +20 | 답할 거리 있는 주제 |
| OP body 길이 100~600자 | +10 | 깊이 있는 질문이라 깊이 있는 답 가능 |
| 페인 신호 (banned/stuck/help/why/how) | +15 | 가치 답글 효과 큼 |
| 자가홍보 글 ("check out my X") | -20 | 답글 reach 약함 |
| 제목 ALL CAPS / 과장 표현 | -10 | low-quality 시그널 |

### 3. 출력 — top 5 후보

```
## 오늘 댓글 달 만한 글 — <YYYY-MM-DD>

### 1. r/<sub> · <score 점> · age <Nh> · comments <N>
**제목**: <원제목>
**OP 요약**: <본문 1~2줄 요약>
**왜 이 글**: <매칭 신호 1줄 — "사용자 history 의 X 주제와 직접 연관" 등>
**제안 각도**: <empathy / data / tool-compare 중 어느 톤이 어울릴지 1줄>
**URL**: <permalink>
**Sub 컨텍스트 주의**: <해당 sub 의 self-promo 룰 / karma 요구 / flair 필수 여부 등 알려진 거 한 줄>

### 2~5. (동일 구조)

---

추천: 위 5개 중 1~2개에만 댓글. quality > quantity. playbook §2.2 의 5 valuable comments/week 기준이면 하루 1개도 충분.
```

## 모드 C 드래프트 가이드 (Claude 가 직접 수행)

수집된 thread JSON (OP + top comments) 와 history 를 받은 후:

### 1. 컨텍스트 분석

- **OP 의 진짜 질문/페인 추출** — 제목 ≠ 본문일 때 본문 우선.
- **이미 나온 답 매핑** — top 댓글에서 핵심 주장 분류. 같은 각도로 또 답글 달면 묻힘.
- **OP 의 답글 패턴** — OP 가 어떤 답글에 reply 했는지 보면 어떤 톤 받아주는지 보임.
- **Sub 컨텍스트** — 해당 sub 의 self-promo / karma / 톤 룰. 사용자 channel-guard 작업 중이면 karma phase (wk1-3 NO promo, wk4+ asked-only) 인지 자동 체크.

### 2. 드래프트 2~3개 생성 — 각도 다양화

각 드래프트는 서로 다른 각도. 단순 문장 변형 X.

- **각도 1: empathy + actionable** — OP 페인 짧게 인정, 본인 경험 1~2 문장, 행동 가능한 팁 2~3개.
- **각도 2: data/policy citation** — 관련 사실·데이터·소스 링크. 의견 X 정보 O.
- **각도 3: tool comparison / community question** — 다른 도구·접근법 정직하게 언급, 또는 sub 에 던지는 후속 질문.

### 3. 본인 톤 모방 — 필수 단계

`references/voice-guide.md` 를 반드시 읽고 다음 적용:

- 본인 reddit history (history JSON) 에서 자주 쓰는 표현·구조·문장 길이 추출
- non-native English 가이드 따라 어색한 grammar / overly formal 톤 / 한국어식 영어 회피
- founder peer 톤 (terse, no excess politeness, code-switch 가능) 유지
- 거짓 사실·과장 절대 X. 모르는 부분은 `{PLACEHOLDER}` 로 남기고 사용자가 채우게 안내.

### 4. 출력 형식

```
## 댓글 초안 — <sub>: "<OP 제목 짧게>"

**OP 페인**: <한 줄>
**이미 나온 답들**: <어떤 각도가 이미 dominant 인지 한 줄>
**Sub 룰 주의**: <해당 sub 의 promo/karma/flair 룰 한 줄>
**본인 karma phase**: <NO promo / asked-only / OK> — channel-guard 작업 중이면 이걸 자동 결정

---

### 후보 1 — <각도 라벨> (<N chars>)

```
<draft 본문 — markdown OK, {PLACEHOLDER} 표시>
```

**왜 이 각도**: <1~2 줄 — 이미 나온 답 회피 + history 기반 voice 매칭>

### 후보 2 — ... (동일 구조)

### 후보 3 — ... (동일 구조)

---

추천: <후보 N 추천> — <왜>
주의: <답글 게시 후 24h 안에 OP 답 오면 1줄 follow-up reply 권장 (engagement loop 닫기)>
```

### 5. 반드시 지킬 것

- **거짓 숫자·거짓 사실 금지**. "I lost 3 channels" 같은 fabricated 경험 X. 모르는 부분은 `{PLACEHOLDER}`.
- **자동 게시 X**. 사용자가 reddit 에 직접 paste · edit · 게시.
- **Sub 룰 위반 시 거부**. 예: NO-promo phase 에 channel-guard 명시 추천 X. 룰 위반 가능성 보이면 1줄 경고 후 추천 거부 또는 수정.
- **OP 의 dignity 보호**. OP 페인 인용 시 verbatim quote 짧게 (1 sentence). 패러프레이즈 ≠ 인용 — 패러프레이즈로 충분하면 그것 우선.
- **본인 voice > 일반 AI 톤**. history 와 voice guide 에서 추출한 패턴이 우선.

## 파싱 결과 구조 (Claude 가 JSON 에서 뽑아 정리)

### history (voice 학습용)
```json
{
  "username": "myhandle",
  "comments": [{ "id": "abc", "body": "...", "subreddit": "FacelessYouTube",
                 "score": 3, "created_utc": 1715000000, "permalink": "/r/.../" }],
  "posts": [{ "id": "def", "title": "...", "selftext": "...", "subreddit": "...",
              "score": 12, "num_comments": 8, "created_utc": ..., "permalink": "..." }]
}
```

### candidates (모드 B)
```json
[
  { "id": "...", "subreddit": "FacelessYouTube", "title": "...", "selftext": "...",
    "score": 47, "upvote_ratio": 0.92, "num_comments": 23, "created_utc": ...,
    "stickied": false, "locked": false, "link_flair_text": "Question",
    "author": "...", "permalink": "...", "url": "..." }
]
```

### thread (모드 C)
```json
{
  "op": { "title": "...", "selftext": "...", "score": ..., "num_comments": ...,
          "subreddit": "...", "author": "...", "permalink": "...",
          "link_flair_text": "...", "created_utc": ... },
  "top_comments": [
    { "id": "...", "author": "...", "body": "...", "score": ...,
      "created_utc": ..., "is_op_reply": false }
  ]
}
```

## 트러블슈팅

### 연결된 브라우저 0개
확장 미설치/미연결. 사용자에게 설치·연결 요청.

### 로그인 안 됨 (`/api/me.json` 이 비거나 HTML)
그 프로파일에 reddit 로그인 없음. reddit.com 에서 로그인 후 재시도. (전용 프로파일은 메인 창과 쿠키 비공유.)

### `.json` 응답이 HTML(앱 셸)로 옴
같은 탭에서 이동해 SPA 가 가로챈 경우는 reddit 에선 드물지만, 반드시 **새 탭**에서 `.json` URL 을 연다.

### `{sub}.json` 403 / 404
- sub private/quarantined → 접근 권한 없음. 다른 sub 안내.
- 오타 → sub 이름 재확인.

### 결과 너무 적음
- 컷오프 48h → 168h(1주) 로 늘림.
- per-sub 25 → 50 으로 `?limit=` 늘림.
- 그래도 적으면 sub 자체가 dead 일 가능성(`r/microsaas` 처럼).

### username 추출 실패
`/api/me.json` 이 401 이면 로그인 만료. reddit.com 새로고침 후 retry. 그래도 안 되면 사용자에게 한 번 묻고 메모.

## Rate-limit 위생 (중요)

본인 reddit 계정 세션 사용. 계정은 희소 자원.

- sub 사이·thread fetch 사이 `navigate` 를 몰아치지 말 것 — 한 호흡 두고 순차 진행.
- 한 번 discover 후 최소 5분 대기 후 다음 discover.
- 같은 thread URL 반복 fetch 금지 (이미 읽은 JSON 재활용).
- 스케줄·cron 반복 실행 거부. on-demand 만.

## 이 skill 이 하지 않는 것

- **모든 쓰기 동작** — 댓글·답글·upvote·downvote·DM·게시·삭제. read-only.
- **자동 댓글 게시** — 추천만, 게시는 사용자 수동.
- **타인 username 분석** — 본인 reddit 만. 타인 계정 분석 요청 거부.
- **사실 fabrication** — 모르는 부분은 `{PLACEHOLDER}` 로.
- **karma farming / spam pattern 권유** — 가치 댓글만. 묻힌 thread 에 같은 댓글 반복 등 절대 X.
- **sub 룰 위반 권유** — 룰 어기는 댓글 추천 거부.
- **CDP·Playwright·포트 9222** — 안 씀. 전적으로 Claude in Chrome 확장.

사용자가 위 항목 요청 시 skill 이 read-only · 추천 전용임을 안내하고 거부.
