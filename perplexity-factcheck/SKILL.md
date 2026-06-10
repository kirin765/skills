---
name: perplexity-factcheck
description: >
  Claude 가 산출한 주장·수치·사실을 Perplexity 로 교차 검증하는 워크플로우. 사용자의 인증된
  Chrome 세션에 **Claude in Chrome 확장**(`mcp__Claude_in_Chrome__*`)으로 붙어 perplexity.ai
  에 New thread 를 만들고 질문을 던진 뒤, 내부 REST 엔드포인트에서 답변 + 출처 링크를 구조화
  JSON 으로 받아온다. 사용자가 "perplexity 로 팩트체크", "이거 perplexity 에 물어봐", "이 주장
  검증해줘", "출처 확인해줘", "fact-check this with perplexity", "퍼플렉시티로 확인" 같은 표현을
  쓸 때 발동. 또한 Claude 자신이 방금 생성한 사실 주장(특히 수치·날짜·수수료율·정책·통계처럼
  틀리면 사용자에게 손해가 되는 것)의 신빙성이 불확실해 외부 검증이 필요하다고 판단할 때 사전적으로
  사용. 답변·출처는 Claude 의 내부 검증용이며 사용자가 따로 저장할 필요는 없다(요청 시 저장 가능).
  Read-only — perplexity 에 글 작성·공유 등 쓰기 동작은 하지 않는다. 더 일반적인 임의 사이트
  브라우저 자동화는 cdp-anywhere 스킬.
---

# perplexity-factcheck

## 목적

Claude 가 만든 산출물의 **사실·수치·출처를 Perplexity 로 교차 검증**한다. 결과물의 신빙성이
걱정되는 주장(수수료율, 날짜, 정책 변경, 통계, 고유명사 등)을 그대로 두지 말고, 사용자의
Perplexity 세션을 빌려 질문을 던지고 **답변 + 출처 URL** 을 받아 대조한다.

핵심 설계: perplexity.ai 는 답변을 SSE 로 스트리밍하지만, 스레드가 완성되면 내부 REST
엔드포인트 `/rest/thread/{uuid}?with_schematized_response=true` 가 **답변(markdown, 인라인
`[N]` 인용 마커 포함) + 출처(web_results: name/url/snippet)** 를 구조화 JSON 으로 돌려준다.
DOM 스크랩(깨지기 쉬움) 대신 이 엔드포인트를 **새 탭에서 직접 열어** 읽으므로 안정적이다.

> **이 스킬은 Playwright·CDP·포트 9222 를 쓰지 않는다.** 전적으로 Claude in Chrome 확장
> (`mcp__Claude_in_Chrome__*`) 으로 사용자의 인증된 Chrome 을 운전한다. 물리적 마우스를 뺏지
> 않고(DOM 레벨 동작), 전용 MCP 탭 그룹에서만 작업한다.

## 사전 조건

1. **Chrome 확장 연결** — `mcp__Claude_in_Chrome__list_connected_browsers` 로 연결된 브라우저를
   확인한다. 0개면 사용자에게 Claude in Chrome 확장 설치·연결을 요청하고 멈춘다.

2. **perplexity.ai 로그인** — 작업에 쓸 프로파일에서 perplexity.ai 에 로그인돼 있어야 한다.
   로그인 안 돼 있으면 멈추고 사용자에게 로그인을 요청한다. **자동 로그인은 하지 않는다.**

> **권장: 전용 프로파일에서 돌려 메인 브라우저 방해를 없앤다.** 사용자가 평소 웹서핑하는
> 메인 Chrome 에서 돌리면 새 탭 생성 시 포커스가 튈 수 있다. 사용자가 별도 프로파일
> (예: "CDP용")을 갖고 있고 거기 perplexity 로그인이 돼 있으면 그쪽을 쓴다. 백그라운드
> 프로파일이라 사용자 작업과 충돌하지 않는다.

## 워크플로우

### 0. 브라우저 선택 — 무조건 먼저

`list_connected_browsers` 결과가 **2개 이상**이면 `AskUserQuestion` 으로 사용자에게 어느
브라우저에서 돌릴지 묻는다(각 브라우저를 display name + deviceId 로 나열). 사용자가 고른
deviceId 로 `select_browser` 한다. 1개뿐이면 그걸 `select_browser`. **임의로 고르지 말 것.**

전용 프로파일이 있으면 "메인 브라우저 방해를 피하려면 전용 프로파일 + perplexity 로그인"을
권한다.

### 1. 작업 탭 준비 + 로그인 확인

```
tabs_context_mcp(createIfEmpty: true)   # 격리된 MCP 탭 그룹에 탭 확보
navigate(tabId, "https://www.perplexity.ai/")
find(tabId, "main ask/search input box")
```

`find` 가 입력창(placeholder "Ask anything…")을 못 찾고 로그인 벽이 보이면 → 멈추고
사용자에게 그 프로파일에서 perplexity 로그인을 요청한다. **추정으로 진행하지 말 것.**

### 2. 검증 질문 던지기

검증할 주장을 **자기완결적인 질문**으로 바꿔 던진다. 좋은 질문은 (a) 검증 대상을 구체적으로
지목하고, (b) 시점·범위를 명시한다. 예: "쿠팡 로켓그로스 판매수수료는 2025년 기준 카테고리별로
다른가? 공식 수치와 출처."

입력 박스는 contenteditable(textarea 아님)이라 `form_input` 이 React 상태에 안 먹을 수 있다.
**`computer` 액션으로 클릭→타이핑→제출**한다:

```
computer(action: "left_click", ref: <ask box ref>)   # 또는 coordinate
computer(action: "type", text: "<질문>")
# 타이핑이 박스에 들어갔는지 screenshot 으로 1회 확인(빈 채로 제출되는 사고 방지)
computer(action: "left_click", coordinate: <제출 화살표 버튼>)   # 또는 key "Return"
```

제출되면 탭 URL 이 `/search/new/{uuid}` → 잠시 후 `/search/{uuid}` 로 바뀐다.

### 3. thread UUID 추출

`tabs_context_mcp` (또는 직전 navigate 결과)의 탭 URL 에서 `/search/{uuid}` 의 36자
UUID 를 뽑는다. 답변이 완성되면 URL 이 `/search/new/...` 에서 최종 `/search/{uuid}` 로 안정된다 —
**최종 UUID** 를 쓴다.

### 4. REST 엔드포인트에서 구조화 JSON 수거

SPA 라우터가 같은 탭의 `/rest/` 이동을 가로채므로, **새 탭**에서 직접 연다:

```
tabs_create_mcp()
navigate(newTabId, "https://www.perplexity.ai/rest/thread/{uuid}?with_parent_info=true&with_schematized_response=true&version=2.18&source=default&limit=10&offset=0&from_first=true")
get_page_text(newTabId)   # body 가 raw JSON
```

`get_page_text` 결과의 `entries[0].status` 를 확인:
- `COMPLETED` → 파싱(5단계)으로.
- `PENDING`/그 외 → 답변 생성 중. `computer(action:"wait", duration:3~8)` 후 같은 탭을
  다시 `navigate`(같은 REST URL) + `get_page_text` 로 재확인. 기본 90초, 심층/Pro 검색이면
  최대 180초까지 폴링. 그래도 미완료면 `timeout_or_incomplete` 로 보고.

### 5. 파싱 — answer + sources

JSON `entries[0]` 에서:
- **answer**: `blocks[].markdown_block.answer` 중 **가장 긴 것**(Pro 검색은 중간 단계
  markdown_block 이 여럿일 수 있음). 인라인 `[N]` 인용 마커 포함.
- **sources**: `blocks[].web_result_block.web_results[]` 를 블록 순서대로 합치되 **url 중복
  제거**. 각 원소 → `{n, title(name), url, snippet}`. **`[N]` 마커는 sources 의 N번째
  (1-based)** 에 매핑된다 — 어떤 주장이 어떤 출처에서 나왔는지 추적 가능.

### 6. 정리

작업으로 연 MCP 탭들을 `tabs_close_mcp` 로 닫는다(스레드는 서버에 저장돼 `thread_url`
= `https://www.perplexity.ai/search/{uuid}` 로 다시 볼 수 있음). 사용자가 브라우저에서 직접
보고 싶다고 하면 결과 탭은 남긴다.

## 출력 해석 + 대조

- **Claude 가 할 일**: 자신의 원래 산출물과 `answer` 를 대조해 일치/불일치/추가확인 필요를
  판단한다. 불일치하면 어느 부분이 어떻게 다른지, 어떤 출처가 뒷받침하는지 사용자에게 보고하고
  원래 산출물을 수정한다.
- Perplexity 답변도 100% 정답은 아니다. **출처 URL 의 신뢰도**(공식 도메인 vs 블로그)를 같이
  보고 판단한다. 결정적 수치는 공식 출처를 우선한다.

## 결과 보고 형식

검증 후 사용자에게 짧게 보고한다:
- ✅ 일치: "방금 말한 X 는 Perplexity 도 동일하게 확인 — 출처: <공식 URL>"
- ⚠️ 불일치/수정: "X 라고 했는데 검증해보니 Y 가 맞음. 원래 답변 수정함. 근거: <URL>"
- ❓ 불확실: "출처가 블로그뿐이라 단정 어려움. 공식 확인 권장."

## 이 스킬이 하지 않는 것

- **쓰기 동작 없음** — perplexity 에 댓글·공유·collection 저장 등 안 함. 질문 던지고 읽기만.
- **자동 로그인·캡차 우회 없음** — 로그인 안 돼 있으면 사용자에게 요청하고 멈춘다.
- **사용자 기존 탭 임의 조작 없음** — 전용 MCP 탭 그룹에 자체 탭을 열어 작업하고 끝나면 닫는다.
- **CDP·Playwright·포트 9222 안 씀** — 전적으로 Claude in Chrome 확장으로 동작.

## 트러블슈팅

- **연결된 브라우저 0개** — 확장 미설치/미연결. 사용자에게 설치·연결 요청.
- **로그인 벽(입력창 못 찾음)** — 그 프로파일에 perplexity 로그인 없음. 로그인 후 재시도.
  (전용 프로파일은 메인 창과 쿠키 공유 안 됨에 유의.)
- **타이핑이 빈 채로 제출됨** — contenteditable 포커스 실패. 좌표로 직접 `left_click` 후
  `type`, screenshot 으로 텍스트 확인 후 제출.
- **`/search/` URL 미생성(no_thread)** — 제출이 안 먹음. 입력창 다시 클릭/제출 또는
  perplexity.ai 새로고침 후 재시도.
- **REST 가 HTML(앱 셸)을 돌려줌** — 같은 탭에서 `/rest/` 로 이동해 SPA 가 가로챈 경우.
  반드시 **새 탭**에서 REST URL 을 연다.
- **status 가 계속 PENDING(timeout_or_incomplete)** — 답변이 제한 시간 내 미완료. 폴링
  시간을 늘리거나(180s) 질문을 단순화.
- **answer 는 오는데 sources 가 빔** — 단순 산술/상식 질문이라 웹 검색을 안 한 경우. 검증엔
  부적합하니 출처가 필요한 형태로 질문을 바꾼다.

## 다른 스킬과의 관계

- **cdp-anywhere** — 임의 사이트 범용 브라우저 자동화. perplexity 전용 검증은 이 스킬이 우선.
- **firecrawl-search / WebSearch** — 인증 불필요한 일반 웹 검색. Perplexity 의 종합·인용
  답변이 필요할 때, 또는 사용자의 Perplexity Pro 를 쓰고 싶을 때 이 스킬.
