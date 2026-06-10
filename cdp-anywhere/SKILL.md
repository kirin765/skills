---
name: cdp-anywhere
description: 범용 인증세션 브라우저 자동화 워크플로우. 사용자의 인증된 Chrome 세션을 그대로 빌려, 전용 스킬이 없는 임의 사이트(LinkedIn·Notion·GitHub·임의 SaaS·내부 어드민 등)에서 (a) 내부 JSON/GraphQL endpoint 로 데이터 수집, (b) DOM 스크랩, (c) 클릭·폼 채우기·네비게이션 같은 인터랙티브 자동화를 처리. **기본 엔진은 Claude in Chrome 확장(`mcp__Claude_in_Chrome__*`)** 이고, 응답 가로채기/인증 POST·GraphQL 리플레이가 꼭 필요할 때만 CDP+Playwright(포트 9222) 를 쓴다. 사용자가 "지금 로그인된 ~~ 에서 ~~ 긁어줘", "내 Chrome 세션으로 ~~ 자동화", "이 사이트에 로그인된 상태로 ~~", "CDP 로 ~~", "Playwright 로 ~~", "이 페이지 자동으로 채워줘", "Linkedin/Notion/Github/임의의-내부-서비스 에서 ~~" 같은 표현을 쓸 때 반드시 발동. 더 좁은 전용 스킬(x-cdp-search, reddit-cdp-coach, naver-cafe-scrape) 이 매칭되면 그쪽 우선; 그 외 사이트는 이 스킬. Default read-only — 쓰기 동작(게시·전송·결제·삭제) 은 사용자가 명시적으로 요청할 때만, 그것도 영향과 함께 한 번 확인받고 수행.
---

# cdp-anywhere

## 무엇을 하는 skill 인가

사용자의 인증된 Chrome 세션을 그대로 빌려 임의 사이트에서 작업한다. 별도 로그인 자동화·캡차 우회·헤드리스 재구동 없음. 사용자가 평소 쓰는 그 세션의 쿠키·localStorage 를 그대로 쓴다.

세 가지 작업 모드:

- **수집 (collect)** — SPA 내부 JSON/GraphQL endpoint 또는 DOM 에서 데이터 추출.
- **단발 확인 (peek)** — 지금 페이지에 보이는 무언가만 빠르게 읽기.
- **인터랙션 (act)** — 클릭·폼·네비게이션 시퀀스 자동화.

## 두 개의 엔진 — 어느 걸 쓸지 먼저 결정

| 엔진 | 도구 | 언제 |
|---|---|---|
| **A. Claude in Chrome 확장 (기본)** | `mcp__Claude_in_Chrome__*` | 인터랙션, DOM 스크랩, 단발 확인, **그리고 이미 아는 GET JSON/REST endpoint 읽기**(새 탭에서 navigate + get_page_text). 대부분의 작업. |
| **B. CDP + Playwright (특수)** | `connect_over_cdp`, 포트 9222 | **딱 두 경우만** — (1) 모르는 내부 endpoint 를 *처음 가로채* URL·헤더·payload 를 알아내야 할 때(`page.on("response")`), (2) 인증 헤더(Bearer/csrf 등)를 실은 **POST/GraphQL 요청을 cursor 페이지네이션으로 리플레이**해야 할 때(`context.request.post/get`). 확장은 이 둘을 못 한다. |

> **결정 규칙**: 먼저 Engine A 로 가능한지 본다. "응답을 가로채야 한다" 또는 "인증 헤더를 실어 POST/GraphQL 을 반복 호출해야 한다" 가 *아니면* Engine A. 그 둘 중 하나가 필수일 때만 Engine B.

확장은 물리 마우스를 뺏지 않고 전용 MCP 탭 그룹에서 동작한다. 메인 브라우저 방해를 피하려면 전용 프로파일을 권한다.

## 왜 이렇게 — 설계 배경

내부 API 직접 호출은 DOM 파싱보다 안정적이다(마크업 변화에 안 깨짐). 과거엔 이걸 전부 CDP+Playwright 로 했지만, Chrome 148 에서 `connect_over_cdp` 가 깨지는 등 Playwright↔CDP 브릿지가 fragile 했다. 그래서 **가로채기·인증 POST 리플레이가 진짜 필요한 경우만 CDP 로 좁히고**, 나머지(클릭/폼/DOM/GET-endpoint 읽기) 는 유지보수되는 확장으로 옮겼다. 핵심 통찰: 많은 내부 endpoint 는 **GET 이라 인증된 세션에서 새 탭으로 그 URL 을 열기만 하면 쿠키가 자동 첨부돼 JSON 이 그대로 나온다**(perplexity `/rest/thread`, reddit `.json` 에서 검증됨) — 이 경우 가로채기가 아예 불필요.

전용 스킬이 있는 사이트(X, Reddit, 네이버 카페) 는 양보한다. 이 스킬은 그 외 전부.

## 사용자 인풋에서 추출할 정보

- **대상 URL/도메인** — 사이트 전체인지 특정 페이지인지.
- **목표** — (a) 데이터 수집(어떤 필드·페이지네이션) / (b) 인터랙션(어떤 클릭/입력) / (c) 단발 확인.
- **수량** — 없으면 "처음 N개 / 첫 페이지" 로 시작 후 확대.
- **출력 형식·저장 위치** — 기본 `/tmp/cdp-anywhere/{도메인}-{timestamp}.json`.
- **쓰기 권한** — 기본 read-only. 쓰기는 명시 요청 + 영향 확인 후에만.

---

## Engine A — Claude in Chrome 확장 (기본 경로)

### A0. 프리플라이트
1. `list_connected_browsers` — 0개면 확장 설치·연결 요청 후 멈춤. 2개+면 `AskUserQuestion` 으로 선택 → `select_browser`.
2. `tabs_context_mcp(createIfEmpty: true)` 로 격리된 MCP 탭 그룹 확보.
3. 대상 도메인 로그인 확인 — `navigate` 후 `get_page_text`/`find` 로 로그인 벽 여부 판단. 안 돼 있으면 그 프로파일에서 로그인 요청 후 멈춤(자동 로그인 X).

### A-collect (수집) — 우선순위 순서
1. **이미 아는 GET endpoint** 가 있으면(또는 사이트 문서/관찰로 유추되면): `tabs_create_mcp` → 그 endpoint URL 로 `navigate` → `get_page_text` 로 JSON body 수거. 페이지네이션은 URL 의 cursor/offset/after 파라미터를 바꿔 새 탭 navigate 반복. **SPA 라우터가 같은 탭의 `/api`·`/rest` 이동을 가로채므로 반드시 새 탭에서.**
2. **endpoint 를 모르면**: 먼저 대상 페이지를 `navigate` 한 뒤 `read_network_requests(urlPattern: "/api")` 로 어떤 요청이 오갔는지 *메타데이터* 를 본다. URL 패턴을 알아내면 1번으로. (단 응답 body 가 필요한데 GET 으로 직접 못 열거나 POST/헤더가 필요하면 → Engine B 로 전환.)
3. **내부 API 가 없거나 SSR/RSC**: DOM 스크랩 — `navigate` → `get_page_text`(본문) 또는 `find`+`read_page`(특정 요소). 무한 스크롤은 `computer(action:"scroll")` 후 다시 읽기. "더보기" 는 `find`+`computer` 클릭.

### A-peek (단발 확인)
`navigate`(또는 기존 탭) → `get_page_text` 한 번. 끝.

### A-act (인터랙션)
`find` 로 요소 찾기 → `computer` 클릭/타이핑 또는 `form_input` → 필요 시 `file_upload`. contenteditable 은 `form_input` 이 안 먹을 수 있으니 `computer` 클릭+type, screenshot 으로 입력 확인. **비가역 지점(폼 제출·결제·전송·삭제) 직전엔 반드시 멈춰 영향을 보고하고 동의받기.**

### A 정리
작업으로 연 MCP 탭을 `tabs_close_mcp` 로 닫는다.

---

## Engine B — CDP + Playwright (가로채기 / 인증 POST 리플레이 전용)

Engine A 로 안 되는 두 경우에만. 사전 조건·코드 스니펫은 references 참고.

### B 사전 조건
1. **CDP 9222 응답** — `curl -s http://localhost:9222/json/version`. 실패면 [chrome-setup](references/chrome-setup.md) 명령으로 띄워달라고 요청.
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"
   ```
   > Chrome 148+ 는 탭 0개면 `connect_over_cdp` 가 깨진다 — 붙기 전 `PUT /json/new` 로 탭 하나를 미리 만들어라(`ensure_page_target` 패턴).
2. **Playwright 설치** — `python3 -c "import playwright"` 또는 Node `playwright`.
3. **대상 도메인 로그인** — `scripts/probe.py --host <도메인>` 으로 CDP·쿠키 확인. 추정 금지.

### B 작업
- **API capture**: `page.on("request"/"response")` 로 도메인 + `application/json` 매칭, 첫 요청에서 URL 템플릿·헤더·payload 추출. 이후 `context.request.get/post(url, headers=...)` 로 cursor 페이지네이션.
- 코드 스니펫(Python/Node), endpoint 휴리스틱, WS/SSE hook: [references/connect-snippets.md](references/connect-snippets.md).

---

## 출력 저장

기본 경로: `/tmp/cdp-anywhere/{호스트}-{YYYYMMDD-HHMM}.json`(수집) 또는 `...-actions-{timestamp}.log`(인터랙션). 길어질 수 있으면 JSONL(중간에 끊겨도 생존). 수집은 metadata 블록 동반: `{captured_at, host, source_url, endpoint, item_count, cursor_state}` — 재실행 시 cursor 이어받기.

## 권장 실행 흐름

1. **엔진 결정** — 위 결정 규칙. 대부분 Engine A.
2. **프리플라이트** — A0(확장) 또는 B 사전 조건. 실패 시 사용자에게 알리고 멈춤.
3. **소량 dry-run** — 첫 1 페이지/1 액션만 실행해 형식 검증 + 사용자 확인.
4. **본 실행** — 대량 수집은 background 권장. 인터랙션은 foreground 가 안전.
5. **장시간 작업** — background 면 `ScheduleWakeup` 으로 진척 점검. cutoff/요청량 도달 시 정상 종료.
6. **요약 보고** — 저장 경로, 건수, 다음 액션(cursor/미완) 명시.

## Rate-limit 위생 (중요)

"사용자가 평소 쓰는 속도" 를 자동화하는 것이지 봇 트래픽이 아니다.

- 페이지 호출/탭 navigate 사이 몰아치지 말 것 — 한 호흡 두고 순차 진행(고정 sleep 금지, 자연스러운 간격).
- HTTP 429/5xx 보이면 즉시 stop + 사용자 보고. 자동 backoff 재시도는 한 차례만.
- 수천 건 단위는 사용자 확인 후. 기본 N=100 에서 시작.
- 사이트가 봇/스크랩을 명시 금지(robots.txt+ToS) 하면 사용자에게 알리고 "본인 데이터에 한정해 진행할지" 확인.

## 이 skill 이 하지 않는 것

- **타인 명의 쓰기 동작** — 거부. 본인 계정 쓰기도 명시 요청 + 영향 확인 후에만.
- **결제·송금·거래 실행** — 글로벌 CLAUDE.md 와 일치. 조회·카테고라이즈만, 실제 거래는 사용자 손으로.
- **캡차 우회** — 사용자에게 그 창에서 직접 풀어달라 요청.
- **봇 탐지 회피(UA spoof, fingerprint mask, proxy chain)** — 명시 거부. 사용자 평소 세션을 빌릴 뿐.
- **타인 비공개 데이터 수집** — 본인이 접근 가능한 페이지만.
- **사이트 ToS 명백 위반** — 위험하면 한 번 멈춰 확인.

자세한 기준: [references/safety.md](references/safety.md).

## 트러블슈팅

### Engine A
- **"This site is not allowed due to safety restrictions"** — 확장은 일부 사이트(예: `naver.com`/`cafe.naver.com` 전체) 로의 navigate 를 안전정책으로 차단한다. 이런 사이트는 Engine A 로 불가 → **Engine B(CDP) 로 전환**. (네이버 계열 작업은 전부 CDP.)
- **연결된 브라우저 0개** — 확장 미설치/미연결. 설치·연결 요청.
- **로그인 벽** — 그 프로파일에 도메인 로그인 없음(전용 프로파일은 메인 창과 쿠키 비공유). 로그인 후 재시도.
- **`/api`·`/rest` 가 HTML(앱 셸)로 옴** — 같은 탭 이동을 SPA 가 가로챈 것. 반드시 **새 탭**에서 endpoint URL 을 연다.
- **GET 인데 401/403** — 그 endpoint 가 GET 이 아니거나 커스텀 헤더(Referer/CSRF 등) 를 요구 → Engine A 로는 불가, Engine B 로 전환.
- **인터랙티브 셀렉터 깨짐** — text·role·aria-label 우선. CSS class 는 빌드 해시라 최후 수단.

### Engine B
- **CDP 9222 미응답** — 위 명령으로 재기동. `lsof -i :9222` 로 프로세스 확인.
- **`connect_over_cdp` timeout / "context management not supported"** — 탭 0개 상태. `PUT /json/new` 로 탭 선생성 후 재연결.
- **endpoint 캡처 실패** — 첫 요청 트리거 액션(스크롤/더보기) 이 실제 발생했는지 확인. SSR/RSC 면 JSON API 없음 → Engine A 의 DOM 스크랩으로. WS/SSE 는 `page.on("websocket")`.
- **401/403** — 세션 만료. 도메인 새로고침 + 재로그인.

## 다른 스킬과의 관계

- **x-cdp-search · reddit-cdp-coach · naver-cafe-scrape** — 각 사이트 전용. 매칭되면 그쪽 우선. (x-cdp-search 는 GraphQL 가로채기라 CDP 기반; reddit-cdp-coach 는 확장 기반.)
- **firecrawl / firecrawl-scrape** — 인증 불필요한 공개 페이지 단발 스크랩이면 더 가볍다. 인증 세션 필요하면 이 스킬.
- **playwright-dev** — 헤드리스·별도 브라우저로 새 자동화 코드 개발. 이 스킬은 사용자 평소 세션 빌리기 전용.

## 워크스페이스별 규약

작업 디렉토리에 `CLAUDE.md` 가 있으면 그 규칙 우선(출력 경로·세션 요약 위치 등).
