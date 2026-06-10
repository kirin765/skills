---
name: x-cdp-search
description: X (Twitter) 의 키워드 검색 결과를 SearchTimeline GraphQL endpoint 직접 호출로 수집해 구조화된 JSON 으로 저장하는 워크플로우. 사용자가 "X에서 ~~ 검색해줘", "트위터에서 ~~ 글 모아줘", "scrape X for ~~", "find tweets about ~~", "X 에서 페인 글 수집" 비슷한 요청을 할 때 발동. 페이지 스크롤·DOM 파싱 없이 첫 요청 한 번만 가로채 endpoint·헤더·cursor 를 추출하고 그 다음부터는 `context.request.get` 으로 페이지네이션. Chrome CDP (포트 9222) 를 통해 사용자의 인증된 X 세션을 그대로 사용하므로 X 로그인이 사전 조건. Read-only — 트윗 작성·DM·팔로우 등 쓰기 동작은 절대 하지 않음.
---

# X (Twitter) CDP 검색 스크랩

## 무엇을 하는 skill 인가

키워드 한 개 (Advanced Search 연산자 포함 가능) 를 받아 X 의 SearchTimeline 결과를 수집하고 JSON 으로 저장한다. 페이지 스크롤은 첫 요청 발사 한 번에만 쓰고, 이후 페이지네이션은 모두 인증된 컨텍스트의 직접 API 호출 (`context.request.get`) 로 처리한다.

## 왜 이 흐름인가 — 설계 배경

X 는 SPA 이고 모든 데이터는 내부 GraphQL endpoint (`x.com/i/api/graphql/{queryId}/SearchTimeline`) 가 반환한다. queryId 는 X 배포마다 바뀌므로 하드코딩 불가. 대신 검색 페이지를 한 번 열어 첫 요청을 가로채면 (a) 현재 queryId 가 박힌 URL 템플릿, (b) 정확한 헤더 (Bearer, csrf-token, client-uuid 등), (c) 첫 페이지 payload 를 모두 얻는다. 그 뒤로는 cursor 만 갈아끼우며 직접 호출 — 브라우저 렌더 비용 0, DOM 파싱 0, 화면 스크롤 0.

이 패턴은 같은 디렉토리의 `naver-cafe-scrape` skill 과 동일하다. 두 skill 은 같은 Chrome 프로파일 (`$HOME/chrome-cdp-profile`) 을 공유하도록 설계되어 있다.

## 사전 조건

스크랩 시작 전에 자동 probe 한다. 실패 시 사용자에게 명확히 안내하고 진행하지 않는다.

1. **Chrome CDP 가 9222 포트에서 응답** — `curl -s http://localhost:9222/json/version`
2. **X 로그인 상태** — `auth_token` + `ct0` 쿠키가 `x.com` 도메인에 존재하는지 검사

## CDP 띄우는 명령어 (사용자가 미리 실행)

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

이미 띄워져 있으면 새로 띄울 필요 없다. naver-cafe-scrape 와 같은 프로파일을 쓰므로, 둘 중 한 skill 용으로 이미 Chrome 이 떠 있다면 X 로그인만 확인하면 된다.

## 사용자 인풋에서 추출할 정보

| 항목 | 예시 | 필수 |
|---|---|---|
| 검색 쿼리 | `"쇼츠 자동화"`, `"min_faves:10 lang:ko 다채널 운영"` | 필수 |
| 최대 트윗 수 | `100`, `200` | 선택 (기본 100) |
| 출력 JSON 경로 | `/tmp/x_pain.json` | 선택 (기본 `/tmp/x_results.json`) |

Advanced Search 연산자 (`min_faves:`, `lang:ko`, `since:YYYY-MM-DD`, `until:YYYY-MM-DD`, `from:user`, `filter:media`, `-filter:replies` 등) 는 `--query` 안에 그대로 넣으면 된다.

## 핵심 스크립트

모든 로직은 `scripts/x_search.py` 한 파일에 있다.

### 1. 사전 조건 probe 만 (스크랩 안 함)

```bash
python ~/.claude/skills/x-cdp-search/scripts/x_search.py --probe
```

출력 예:
- ✅ X 로그인: X 로그인 쿠키 (ct0+auth_token) 확인됨

또는:
- ❌ X 로그인: 로그인 쿠키 부족 (auth_token 없음)

### 2. 본 스크랩

```bash
python ~/.claude/skills/x-cdp-search/scripts/x_search.py \
  --query "쇼츠 자동화" --max 100 --out /tmp/x_pain_shorts.json
```

### 3. Advanced Search 연산자

```bash
python ~/.claude/skills/x-cdp-search/scripts/x_search.py \
  --query "min_faves:10 lang:ko 다채널 SNS 운영" --max 200
```

## 권장 실행 흐름

1. **확인 단계** — `--probe` 로 CDP·로그인 검증.
2. **소량 테스트** — `--max 20` 으로 파일 형식·결과 품질 확인.
3. **본 스크랩** — `--max 100~200`. 한 번에 너무 많이 받지 말 것 (rate-limit).
4. **결과 요약** — 스크립트가 끝나면 JSON 을 읽어 사용자에게 트윗 총수, 상위 5개 (engagement 순), 자주 등장하는 키워드/문구 클러스터 요약 제시. 절대 raw JSON 을 채팅창에 붙여넣지 말 것 — 파일 경로 안내 + 요약만.

## 출력 형식

```json
[
  {
    "id": "1234567890",
    "author_handle": "someone",
    "author_name": "Some One",
    "text": "쇼츠 자동화 도구 추천 좀...",
    "created_at": "Fri Apr 11 10:23:45 +0000 2025",
    "likes": 42,
    "retweets": 5,
    "replies": 3,
    "quotes": 1,
    "views": 12345,
    "lang": "ko",
    "url": "https://x.com/someone/status/1234567890"
  }
]
```

## 트러블슈팅

### CDP 9222 미응답
- Chrome 종료된 상태. 사용자에게 위 CDP 명령어 다시 실행 요청.

### "로그인 쿠키 부족"
- 그 Chrome 창에서 X 에 다시 로그인. 종종 X 가 세션을 끊음.
- `--user-data-dir` 가 매번 동일한 경로 (`$HOME/chrome-cdp-profile`) 인지 확인 — 다른 경로면 새 빈 프로파일이라 로그인 안 됨.

### "SearchTimeline endpoint 캡처 실패"
- 로그인이 풀렸거나, X 가 검색을 차단했거나, 네트워크 문제. probe 부터 다시.
- 또는 X 가 GraphQL endpoint 명을 변경했을 수도 있음 (드물지만 가능). 그 경우 `SEARCH_TIMELINE_MARKER` 상수 점검.

### HTTP 401 / 403 응답
- 세션 만료 또는 CSRF 토큰 불일치. Chrome 창에서 X 페이지 새로고침해 새 ct0 발급받게 하고 retry.

### 결과가 너무 적음 (1~2 페이지에서 끊김)
- X 의 per-account 소프트 rate-limit. 10~30 분 기다린 뒤 retry. 절대 같은 쿼리 반복 호출하지 말 것 — rate-limit 가중.

## Rate-limit 위생 (중요)

이 skill 은 사용자 실 X 계정 세션을 사용한다. 계정은 희소 자원으로 취급.

- 페이지 사이 sleep: `PAGE_DELAY = (1.8, 3.4)` 초. 줄이지 말 것.
- 한 쿼리당 한 번 실행 후 최소 30 초 대기 후 다음 쿼리.
- 스케줄·cron 으로 반복 실행 요청 받으면 거부. 페인 리서치 도구는 on-demand 만.
- 결과가 적으면 retry 하지 말고 stop. retry 는 BAN 위험을 증가시킨다.

## 이 skill 이 하지 않는 것

- User timeline (특정 사용자의 트윗 수집) — 별도 endpoint (UserTweets) 필요. 향후 확장 여지.
- 단일 트윗 스레드·답글 펼치기 — 별도 endpoint (TweetDetail) 필요.
- 트렌드.
- **모든 쓰기 동작** (트윗·좋아요·팔로우·DM) — 이 skill 은 read-only. 이런 요청 받으면 거부.

사용자가 위 항목을 요청하면 skill 이 검색 전용임을 안내하고, 정 필요하면 명시적 요청 하에 별도 스크립트로 확장.
