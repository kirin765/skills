---
name: cdp-anywhere
description: 범용 인증세션 브라우저 자동화 — 전용 스킬이 없는 임의 사이트(LinkedIn·Notion·GitHub·SaaS·내부 어드민)에서 사용자의 로그인된 Chrome 세션으로 (a) 내부 JSON/GraphQL 데이터 수집, (b) DOM 스크랩, (c) 클릭·폼·네비게이션 자동화. 유일한 엔진은 CDP+Playwright(포트 9222) — `scripts/probe.py` 로 전용 프로파일 브라우저 확보 후 `connect_over_cdp` 로 작업. 캡차(텍스트형)를 만나면 스크린샷을 사용자 본인에게 릴레이(텔레그램→네이버메일→파일)하고 답을 받아 입력·제출하는 human-in-the-loop 지원(자동 풀이 아님, `scripts/captcha_relay.py`). "지금 로그인된 ~에서 ~긁어줘", "내 Chrome 세션으로 자동화", "CDP/Playwright 로 ~", "이 페이지 자동으로 채워줘" 류 요청에 발동. 더 좁은 전용 스킬(x-cdp-search, reddit-cdp-coach, naver-cafe-scrape)이 매칭되면 그쪽 우선. Default read-only — 쓰기(게시·전송·결제·삭제)는 명시 요청 시에만, 영향 고지 후 한 번 확인받고 수행.
---

# cdp-anywhere

## 무엇을 하는 skill 인가

사용자의 인증된 Chrome 세션을 그대로 빌려 임의 사이트에서 작업한다. 별도 로그인 자동화·자동 캡차 풀이·헤드리스 재구동 없음. 사용자가 평소 쓰는 그 세션의 쿠키·localStorage 를 그대로 쓴다. 캡차는 자동으로 풀지 않고 사용자 본인에게 스크린샷을 릴레이해 답을 받는다([캡차 대응](#캡차-대응--human-in-the-loop-릴레이-자동-풀이-아님)).

세 가지 작업 모드:

- **수집 (collect)** — SPA 내부 JSON/GraphQL endpoint 또는 DOM 에서 데이터 추출.
- **단발 확인 (peek)** — 지금 페이지에 보이는 무언가만 빠르게 읽기.
- **인터랙션 (act)** — 클릭·폼·네비게이션 시퀀스 자동화.

## 엔진 — CDP + Playwright (포트 9222, 유일한 경로)

이 스킬은 확장(MCP) 없이 **오직 CDP+Playwright** 로 동작한다. 사용자 평소 창과
분리된 전용 프로파일(`$HOME/chrome-cdp-profile`) 을 `--remote-debugging-port=9222`
로 띄우고 `connect_over_cdp` 로 붙는다.

| 작업 | 방법 |
|---|---|
| 내부 GET JSON/REST endpoint 읽기 | 인증된 세션 쿠키는 컨텍스트가 자동 동봉 → `context.request.get(url, headers=...)` 또는 `page.goto(endpoint)`. |
| 모르는 내부 endpoint 발굴 | `page.on("request"/"response")` 로 첫 요청 가로채기(URL·헤더·payload). |
| 인증 POST/GraphQL 페이지네이션 | `context.request.post/get(url, headers=..., data=...)` 로 cursor 리플레이. |
| DOM 스크랩 / 인터랙션 | `page.locator` · `get_by_*` · `click` / `fill`. |
| 캡차(텍스트형) | [캡차 대응](#캡차-대응--human-in-the-loop-릴레이-자동-풀이-아님) 으로 릴레이. |

> **이 머신엔 항상 브라우저가 두 개 있을 수 있다 — 절대 혼동하지 말 것.**
> - **메인 Chrome** — 사용자가 평소 쓰는 창(Default 프로파일). CDP 포트 없음.
>   이 스킬의 작업에서 이 창은 신경 쓸 필요도, 건드릴 필요도 없다.
> - **CDP Chrome** — `$HOME/chrome-cdp-profile` 전용 프로파일로
>   `--remote-debugging-port=9222` 로 뜬 것. 이 스킬(그리고 다른 cdp-* 스킬) 이
>   붙는 유일한 대상.
> - 둘을 구분하는 유일한 기준은 **`curl :9222` 응답 여부**다. `pgrep "Google
>   Chrome"`/`ps aux | grep Chrome` 로 "떠 있나"를 판단하지 말 것 — 메인 Chrome 은
>   항상 떠 있을 수 있고, 그것과 CDP Chrome 이 떠 있는지는 무관하다.

## 왜 이렇게 — 설계 배경

내부 API 직접 호출은 DOM 파싱보다 안정적이다(마크업 변화에 안 깨짐). 핵심 통찰:
많은 내부 endpoint 는 **GET 이라 인증된 세션에서 그 URL 을 열기만 하면 쿠키가 자동
첨부돼 JSON 이 그대로 나온다**(perplexity `/rest/thread`, reddit `.json` 에서
검증됨). 가로채기·POST 리플레이까지 하려면 Playwright↔CDP 브릿지가 필요해졌고,
`connect_over_cdp`(Chrome 148 에서 한 번 깨짐) 는 프리플라이트(`probe.py`)와 탭
선보장으로 관리한다. 전용 스킬이 있는 사이트(X, Reddit, 네이버 카페) 는 양보한다.
이 스킬은 그 외 전부.

## 사용자 인풋에서 추출할 정보

- **대상 URL/도메인** — 사이트 전체인지 특정 페이지인지.
- **목표** — (a) 데이터 수집(어떤 필드·페이지네이션) / (b) 인터랙션(어떤 클릭/입력) / (c) 단발 확인.
- **수량** — 없으면 "처음 N개 / 첫 페이지" 로 시작 후 확대.
- **출력 형식·저장 위치** — 기본 `/tmp/cdp-anywhere/{도메인}-{timestamp}.json`.
- **쓰기 권한** — 기본 read-only. 쓰기는 명시 요청 + 영향 확인 후에만.

---

## 사전 조건

1. **CDP 9222 확보** — `python3 scripts/probe.py` 를 먼저 돌린다. 미응답이면 스크립트가 **CDP 전용 브라우저를 자동으로 백그라운드 기동**하고(메인 브라우저는 건드리지 않음) 최대 15초 재확인한다. macOS 는 Google Chrome, Linux(Omarchy/Hyprland) 는 chromium + `--class=cdpchrome` 으로 띄운다(아래 환경 노트). 그래도 실패하면 그때만 [chrome-setup](references/chrome-setup.md) 의 수동 명령으로 사용자에게 직접 띄워달라고 요청 — 매번 먼저 물어보지 말고 자동 기동을 먼저 시도.
   ```bash
   # 자동 기동이 실패했을 때만 사용자에게 요청할 수동 명령
   # macOS:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"
   # Linux(Omarchy/Hyprland) — --class=cdpchrome 필수:
   chromium --class=cdpchrome --remote-debugging-port=9222 \
     --user-data-dir="$HOME/chrome-cdp-profile" &
   ```
   > Chrome 148+ 는 탭 0개면 `connect_over_cdp` 가 깨진다 — 붙기 전 `PUT /json/new` 로 탭 하나를 미리 만들어라(`ensure_page_target` 패턴, `probe.py` 가 자동 처리).
2. **Playwright 설치** — `python3 -c "import playwright"` 또는 Node `playwright`.
3. **대상 도메인 로그인** — `scripts/probe.py --host <도메인>` 으로 CDP·쿠키 확인. 추정 금지. 쿠키 0개면 CDP Chrome 프로파일에 그 도메인 로그인이 안 된 것 — 메인 Chrome 에 로그인돼 있어도 소용없다(별도 프로파일이라 쿠키 비공유).

### 환경 노트 — Omarchy/Hyprland (Linux, 실측 2026-08-23)

이 환경에선 CDP 전용 chromium 을 **반드시 `--class=cdpchrome` 으로 띄운다**. 메인
브라우저도 같은 chromium 바이너리라, 클래스가 같으면 Hyprland 가 두 창을 구분하지
못해 CDP 창이 열릴 때마다 포커스·작업공간을 뺏는다. `~/.config/hypr/hyprland.lua`
에 아래 규칙이 있어야 하고(사용자 환경에 이미 적용됨), 이 규칙은 클래스가
`cdpchrome` 일 때만 걸린다:

```lua
-- CDP 전용 chromium: 열릴 때 포커스 안 뺏음, 작업공간 2로 격리 (실측 검증)
o.window("cdpchrome", { no_initial_focus = true, float = true, workspace = "2 silent" })
```

- `probe.py` 자동 기동도 이 방식(`--class=cdpchrome`)으로 띄운다. 직접 띄울 때도
  반드시 붙인다. 빼먹으면 포커스 뺏김 문제가 되살아난다.
- 클래스 확인: `hyprctl clients | grep "class: cdpchrome"` — 아무것도 안 나오면
  규칙 미적용 상태.
- `probe.py` preflight(2026-08-31): 9222 가 이미 떠 있는데 `--class=cdpchrome`
  없이 띄운 창이면(다른 에이전트/도구의 실수) 경고 후 자동 종료·재기동으로
  바로잡는다. `--no-autofix` 로 경고만 할 수 있다.
- 안전망(2026-08-31): hyprland.lua 에 `chromium` 클래스(플래그 없는 창) 전체를
  ws 2 silent 로 격리하는 규칙도 있다. 플래그를 빼먹어도 포커스 뺏김은 없다.
- 이 규칙이 없는 다른 Linux 데스크톱은 `--headless=new`(창 없음) 또는 Xvfb(가상
  디스플레이) 로 대체 가능. 상세: [chrome-setup](references/chrome-setup.md).

## 작업 — 모드별 절차

### 수집 (collect)
1. **이미 아는 GET endpoint** 가 있으면(또는 사이트 문서/관찰로 유추되면):
   `context.request.get(url, headers=...)` 로 JSON body 수거(쿠키는 자동 동봉).
   페이지네이션은 URL 의 cursor/offset/after 파라미터를 갈아끼워 반복. **SPA 가
   같은 탭의 `/api`·`/rest` 이동을 가로채면 HTML(앱 셸)이 오므로**, 렌더가 필요한
   경우엔 새 탭에서 그 endpoint 를 연다.
2. **endpoint 를 모르면**: 대상 페이지를 연 뒤 `page.on("request"/"response")` 로
   어떤 요청이 오갔는지 URL·헤더·payload 를 가로챈다. URL 패턴을 알아내면 1번으로.
   응답 body 가 필요하고 GET 으로 직접 못 열면 POST/헤더 그대로 리플레이.
3. **내부 API 가 없거나 SSR/RSC**: DOM 스크랩 — `page.locator` 로 본문/요소 수집.
   무한 스크롤은 `window.scrollTo` 후 재읽기. "더보기" 는 클릭.

### 단발 확인 (peek)
`page.goto`(또는 기존 페이지) → `page.locator("body").inner_text()` 또는
`accessibility.snapshot()` 한 번. 끝.

### 인터랙션 (act)
`get_by_role`/`get_by_label`/`get_by_text` 로 요소 찾기 → `click`/`fill`
(contenteditable 은 `click` 후 `press_sequentially` + 스크린샷으로 입력 확인).
`file_upload` 는 `expect_file_chooser`. **비가역 지점(폼 제출·결제·전송·삭제)
직전엔 반드시 멈춰 영향을 보고하고 동의받기.** 캡차가 나오면
[캡차 대응](#캡차-대응--human-in-the-loop-릴레이-자동-풀이-아님) 으로 전환.

캡차 차단 시 흐름: 스크린샷 → `scripts/captcha_relay.py ask` → 답 입력·제출.
CDP 창은 ws 2 격리/headless 일 수 있어 "직접 풀어달라" 대신 릴레이가 기본.

코드 스니펫(Python/Node), endpoint 휴리스틱, WS/SSE hook:
[references/connect-snippets.md](references/connect-snippets.md). 캡차 캡처·릴레이
상세: [references/captcha-relay.md](references/captcha-relay.md).

---

## 출력 저장

기본 경로: `/tmp/cdp-anywhere/{호스트}-{YYYYMMDD-HHMM}.json`(수집) 또는 `...-actions-{timestamp}.log`(인터랙션). 길어질 수 있으면 JSONL(중간에 끊겨도 생존). 수집은 metadata 블록 동반: `{captured_at, host, source_url, endpoint, item_count, cursor_state}` — 재실행 시 cursor 이어받기.

## 권장 실행 흐름

1. **프리플라이트** — `scripts/probe.py`(및 필요 시 `--host <도메인>`) 로 CDP 9222·대상 도메인 쿠키 확인. 실패 시 사용자에게 알리고 멈춤.
2. **소량 dry-run** — 첫 1 페이지/1 액션만 실행해 형식 검증 + 사용자 확인.
3. **본 실행** — 대량 수집은 background 권장. 인터랙션은 foreground 가 안전.
4. **장시간 작업** — background 면 `ScheduleWakeup` 으로 진척 점검. cutoff/요청량 도달 시 정상 종료.
5. **요약 보고** — 저장 경로, 건수, 다음 액션(cursor/미완) 명시.

## 탭 재사용 — 새 탭은 필요할 때만 (중요, 사용자 피드백 2026-08-22)

**매 스크립트마다 새 탭/새 페이지를 열지 말 것. 같은 작업은 기존 페이지를 재사용한다.**
한 스크립트는 **한 `page`** 를 쓰고, 다음 단계로 넘어갈 때는 `page.goto()` 다시
탐색(=reload) 또는 `page.reload()`. `ctx.new_page()` 를 반복 호출하지 않는다.

**새 탭을 열어야 하는 경우는 정말 필요할 때뿐이다.**
- SPA 가 같은 탭의 `/api`·`/rest` 이동을 가로채서 렌더가 필요한 경우(앱 셸이
  옴). 그 경우만 새 탭으로 endpoint URL 을 열고 끝나면 닫는다.

이유: 반복 `new_page()` 는 CDP Chrome 에 탭을 무한히 쌓고(실측 한 세션에서 30개),
사용자 브라우저에 쓰레기를 남긴다. **하나의 작업 흐름(예: 폼 채우기 → 저장 →
제출)은 같은 페이지에서 reload 로 진행**하고, 끝나면 연 탭을 닫는다. 작업이 연
탭은 마지막에 반드시 정리(`/json/close/<id>`).

## Rate-limit 위생 (중요)

"사용자가 평소 쓰는 속도" 를 자동화하는 것이지 봇 트래픽이 아니다.

- 페이지 호출/탭 navigate 사이 몰아치지 말 것 — 한 호흡 두고 순차 진행(고정 sleep 금지, 자연스러운 간격).
- HTTP 429/5xx 보이면 즉시 stop + 사용자 보고. 자동 backoff 재시도는 한 차례만.
- 수천 건 단위는 사용자 확인 후. 기본 N=100 에서 시작.
- 사이트가 봇/스크랩을 명시 금지(robots.txt+ToS) 하면 사용자에게 알리고 "본인 데이터에 한정해 진행할지" 확인.

## 캡차 대응 — human-in-the-loop 릴레이 (자동 풀이 아님)

캡차를 **자동으로 푸는 기능은 없다**(OCR·풀이 서비스·클릭 매크로 금지). 대신
**사람(계정 주인)이 푸는 것**을 릴레이한다:

1. **감지** — iframe(`recaptcha`/`hcaptcha`/`turnstile`/`challenges.cloudflare`),
   `[id*=captcha]`, `input[name*=captcha]`, 화면 문구("로봇이 아닙니다",
   "Enter the characters", "보안 문자"...).
2. **캡처** — 캡차 요소/프레임 또는 보이는 뷰포트 전체를 스크린샷으로 저장.
   크로스-오리진 iframe 은 요소 캡처가 빈 이미지가 될 수 있음 → 뷰포트 캡처 폴백.
3. **릴레이** — `python3 scripts/captcha_relay.py ask --site <host> --image <png> --prompt "<지시문>"`.
   텔레그램으로 전송 후 답 폴링 → 네이버 메일 fallback → 파일 inbox(`--channel` 로
   지정/순서 변경). 성공 시 `ANSWER=...` 로 출력.
4. **입력·제출·검증** — 답을 캡차 입력란에 채우고 제출. "틀림/다시 시도" 면 새
   스크린샷으로 **한 번만** 재시도 후 보고.
5. **정리** — `~/.cdp-anywhere/captcha/<id>.*` 임시 파일 삭제.

**체크박스형**(reCAPTCHA "로봇이 아닙니다" 체크, Turnstile 클릭) 은 릴레이 불가 —
CDP 창이 보이면 사용자가 직접 클릭, headless 면 그 단계는 자동화 불가로 보고.
전체 워크플로우·캡처 스니펫·채널 자격증명·트러블슈팅: [references/captcha-relay.md](references/captcha-relay.md).

## 이 skill 이 하지 않는 것

- **타인 명의 쓰기 동작** — 거부. 본인 계정 쓰기도 명시 요청 + 영향 확인 후에만.
- **결제·송금·거래 실행** — 글로벌 CLAUDE.md 와 일치. 조회·카테고라이즈만, 실제 거래는 사용자 손으로.
- **캡차 자동 우회** — OCR·캡차 풀이 서비스·클릭 매크로로 스스로 푸는 건 절대 거부.
- **캡차 human-in-the-loop 릴레이** — 단, 텍스트형 캡차를 만나면 사용자 **본인**에게
  스크린샷을 전송(텔레그램 → 네이버 메일 → 파일) 하고 답을 받아 입력·제출한다.
  사람이 푸는 것이지 자동 풀이가 아니다. 체크박스형은 릴레이 불가(직접 클릭).
  상세: [captcha-relay](references/captcha-relay.md).
- **봇 탐지 회피(UA spoof, fingerprint mask, proxy chain)** — 명시 거부. 사용자 평소 세션을 빌릴 뿐.
- **타인 비공개 데이터 수집** — 본인이 접근 가능한 페이지만.
- **사이트 ToS 명백 위반** — 위험하면 한 번 멈춰 확인.

자세한 기준: [references/safety.md](references/safety.md).

## 트러블슈팅

- **CDP 9222 미응답** — `scripts/probe.py` 가 자동 기동을 시도한다(위 참고). 그래도 안 되면 `lsof -i :9222` 로 이미 다른 프로파일이 그 포트를 점유했는지 확인 후 [chrome-setup 트러블슈팅](references/chrome-setup.md#자주-겪는-문제) 참고. **메인 Chrome 이 떠 있다는 사실은 CDP 상태와 무관** — 그것만 보고 "Chrome 떠 있으니 됐다"고 판단하지 말 것.
- **`connect_over_cdp` timeout / "context management not supported"** — 탭 0개 상태. `PUT /json/new` 로 탭 선생성 후 재연결.
- **로그인 벽** — CDP Chrome 프로파일에 그 도메인 로그인 없음(메인 창과 쿠키 비공유). 로그인 후 재시도.
- **`/api`·`/rest` 가 HTML(앱 셸)로 옴** — 같은 탭 이동을 SPA 가 가로챈 것. 반드시 **새 탭**에서 endpoint URL 을 연다.
- **GET 인데 401/403** — 그 endpoint 가 GET 이 아니거나 커스텀 헤더(Referer/CSRF 등) 를 요구 → `page.on` 가로채기로 실제 요청 헤더를 캡처해 리플레이.
- **endpoint 캡처 실패** — 첫 요청 트리거 액션(스크롤/더보기) 이 실제 발생했는지 확인. SSR/RSC 면 JSON API 없음 → DOM 스크랩으로. WS/SSE 는 `page.on("websocket")`.
- **401/403** — 세션 만료. 도메인 새로고침 + 재로그인.
- **인터랙티브 셀렉터 깨짐** — text·role·aria-label 우선. CSS class 는 빌드 해시라 최후 수단.
- **캡차 차단** — [캡차 대응](#캡차-대응--human-in-the-loop-릴레이-자동-풀이-아님) 절차로 릴레이. 요소/iframe 캡처가 빈 이미지면 뷰포트 전체 캡처 폴백(cross-origin OOPIF). 체크박스형은 CDP 창에서 직접 클릭 요청.

## 다른 스킬과의 관계

- **x-cdp-search · reddit-cdp-coach · naver-cafe-scrape** — 각 사이트 전용. 매칭되면 그쪽 우선.
- **firecrawl / firecrawl-scrape** — 인증 불필요한 공개 페이지 단발 스크랩이면 더 가볍다. 인증 세션 필요하면 이 스킬.
- **playwright-dev** — 헤드리스·별도 브라우저로 새 자동화 코드 개발. 이 스킬은 사용자 평소 세션 빌리기 전용.

## 워크스페이스별 규약

작업 디렉토리에 `CLAUDE.md` 가 있으면 그 규칙 우선(출력 경로·세션 요약 위치 등).