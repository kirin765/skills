# cdp-anywhere — connect & capture 스니펫

이 파일은 `cdp-anywhere` SKILL.md 가 모드별로 참조하는 코드 조각 모음. 사용자 작업에 맞춰 골라서 단발 스크립트로 조립해 쓴다. Python (대다수) + Node (필요 시) 양쪽 제공.

## 목차
- [기본 연결 — connectOverCDP](#기본-연결--connectovercdp)
- [API capture — 첫 요청 가로채기](#api-capture--첫-요청-가로채기)
- [페이지네이션 — context.request 직접 호출](#페이지네이션--contextrequest-직접-호출)
- [DOM scrape (폴백)](#dom-scrape-폴백)
- [Interactive — click / fill / navigate](#interactive--click--fill--navigate)
- [캡차 대응 — human-in-the-loop 릴레이](#캡차-대응--human-in-the-loop-릴레이)
- [WebSocket / SSE 캡처](#websocket--sse-캡처)
- [공통 유틸](#공통-유틸)

## 기본 연결 — connectOverCDP

### Python
```python
from playwright.async_api import async_playwright

CDP = "http://localhost:9222"

async def attach():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP)
    # 기존 user-data 컨텍스트 (사용자가 평소 쓰는 그 창) 의 첫 번째.
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    return pw, browser, context

async def open_page(context, url: str):
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    return page
```

기존 탭을 그대로 쓰고 싶을 때 (사용자가 이미 띄워둔 페이지):
```python
# context.pages 에 열린 탭 목록. URL 매칭으로 골라 잡기.
for p in context.pages:
    if "example.com" in p.url:
        page = p
        break
else:
    page = await context.new_page()
    await page.goto("https://example.com")
```

### Node
```js
import { chromium } from 'playwright';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const context = browser.contexts()[0] ?? await browser.newContext();
const page = await context.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded' });
```

종료 시 `browser.close()` 호출 금지 — 사용자의 평소 Chrome 을 닫아버린다. `pw.stop()` 만.

## API capture — 첫 요청 가로채기

핵심 아이디어: 관심 데이터를 트리거하는 액션 (스크롤·검색 버튼·다음 페이지) 을 한 번 수행하고, 그 사이 발생하는 네트워크 요청 중 도메인 + 응답 타입 + 경로 패턴이 맞는 것을 골라 URL · 헤더 · payload 를 캡처.

### Python — request + response 동시 hook
```python
async def capture_first_api(page, marker: str, timeout_s: float = 15.0, action=None):
    """
    marker: 관심 endpoint URL 의 부분 문자열. 예: '/api/graphql/UserPosts', '/cafe-web/wcapi/'.
    action: 캡처를 트리거할 async callable (예: 스크롤, 검색 버튼 클릭).
    """
    captured = {"url": None, "headers": None, "payload": None, "method": None}
    done = asyncio.Event()

    async def on_request(req):
        if marker in req.url and captured["url"] is None:
            captured["url"] = req.url
            captured["method"] = req.method
            try:
                captured["headers"] = await req.all_headers()
            except Exception:
                captured["headers"] = dict(req.headers)

    async def on_response(resp):
        if marker in resp.url and captured["payload"] is None:
            ct = (resp.headers.get("content-type") or "").lower()
            if "json" in ct:
                try:
                    captured["payload"] = await resp.json()
                    done.set()
                except Exception:
                    pass

    page.on("request", on_request)
    page.on("response", on_response)

    if action:
        await action()
    else:
        # 기본 트리거: 스크롤 한 번
        await page.evaluate("window.scrollBy(0, 1500)")

    try:
        await asyncio.wait_for(done.wait(), timeout=timeout_s)
    except asyncio.TimeoutError:
        pass

    return captured
```

### 식별 휴리스틱 — 어떤 URL 이 "내부 API" 인가
- `application/json` 응답
- 경로에 `/api/`, `/graphql`, `/wcapi/`, `/v[0-9]/`, `/_data/` 같은 신호
- 응답 본문에 도메인 데이터의 식별자 필드 (`id`, `cursor`, `next`, `pageInfo`) 가 다수
- 화면 렌더보다 명백히 작은 요청 (HTML / CSS / 이미지 제외)

여러 후보가 잡히면 — 가장 큰 JSON payload 또는 사용자가 보는 항목 수와 매치되는 항목 개수를 가진 것을 채택.

### GraphQL POST 인 경우
헤더와 함께 body 도 캡처 필요:
```python
async def on_request(req):
    if marker in req.url and req.method == "POST":
        captured["body"] = req.post_data
        captured["headers"] = await req.all_headers()
        captured["url"] = req.url
```
재호출 시 `context.request.post(url, headers=..., data=body)` 로 보낸다. `variables` 안의 `cursor` / `offset` 만 갈아끼우면 페이지네이션.

## 페이지네이션 — context.request 직접 호출

브라우저 렌더 없이 인증된 컨텍스트의 fetch API 를 직접 호출. 첫 요청에서 받은 헤더 그대로 사용 (cookie 는 컨텍스트가 자동 동봉).

### Python — GET (cursor query 갈아끼우기)
```python
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
import json

def with_cursor(template_url: str, cursor: str, cursor_key: str = "cursor",
                variables_key: str | None = "variables") -> str:
    parsed = urlparse(template_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if variables_key and variables_key in qs:
        # GraphQL 패턴: variables 가 JSON 문자열
        try:
            variables = json.loads(qs[variables_key][0])
        except json.JSONDecodeError:
            variables = {}
        variables[cursor_key] = cursor
        qs[variables_key] = [json.dumps(variables, separators=(",", ":"))]
    else:
        qs[cursor_key] = [cursor]
    new_q = urlencode(qs, doseq=True, quote_via=quote)
    return urlunparse(parsed._replace(query=new_q))

async def paginate(context, first_url: str, headers: dict, extract,
                   max_items: int = 100, delay=(1.5, 3.5)):
    import random, asyncio
    url = first_url
    items, seen_cursor, no_progress = [], None, 0
    while len(items) < max_items:
        r = await context.request.get(url, headers=headers, timeout=20000)
        if r.status != 200:
            print(f"HTTP {r.status} — stop", flush=True)
            break
        data = await r.json()
        page_items, cursor = extract(data)
        items.extend(page_items)
        if not cursor or cursor == seen_cursor:
            no_progress += 1
            if no_progress >= 2:
                break
        else:
            no_progress = 0
        seen_cursor = cursor
        if not cursor:
            break
        await asyncio.sleep(random.uniform(*delay))
        url = with_cursor(first_url, cursor)
    return items
```

`extract` 는 사이트별 응답 파싱 람다. 예: `lambda d: (d["items"], d.get("nextCursor"))`.

### offset / page 번호 패턴
```python
def with_offset(template_url: str, offset: int, offset_key: str = "offset") -> str:
    parsed = urlparse(template_url)
    qs = parse_qs(parsed.query)
    qs[offset_key] = [str(offset)]
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
```

## DOM scrape (폴백)

내부 API 가 안 보이거나 너무 묶여있을 때.

### Playwright locator
```python
await page.goto(url, wait_until="domcontentloaded")
await page.wait_for_selector("[data-testid='post-card']", timeout=10000)
cards = await page.locator("[data-testid='post-card']").all()
out = []
for c in cards:
    title = await c.locator("h3").inner_text()
    link = await c.locator("a").get_attribute("href")
    out.append({"title": title.strip(), "url": link})
```

### Accessibility snapshot (구조 빠르게 보기)
```python
snap = await page.accessibility.snapshot()
# snap 은 트리. 분석 시 ctx_execute 같은 데서 따로 처리 권장 (덤프 크면 위험).
```

### 무한 스크롤
```python
last_count = 0
for _ in range(20):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    count = await page.locator("[data-testid='post-card']").count()
    if count == last_count:
        break
    last_count = count
```

### "다음 페이지" 클릭
```python
while True:
    # 현재 페이지 카드 수집
    ...
    next_btn = page.locator("a[rel='next']").first
    if not await next_btn.is_visible():
        break
    await next_btn.click()
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(random.uniform(1500, 3500))
```

## Interactive — click / fill / navigate

사용자가 명시적으로 요청한 시퀀스만. 비가역 단계 (제출·전송·결제·삭제) 직전에는 반드시 한 번 멈춰 영향 보고 + 동의 확인.

### 단계별 wrapper (확인 게이트 포함)
```python
async def step(name: str, fn, *, irreversible: bool = False, confirm=None):
    """
    name: 단계 라벨 (로그에 남음)
    fn: 실제 동작 async callable
    irreversible: True 면 confirm() 콜백을 통해 사용자에게 한 번 더 물어야 함.
                  confirm() 는 True/False 반환.
    """
    print(f"[step] {name} (irreversible={irreversible})")
    if irreversible:
        ok = await confirm(name) if confirm else False
        if not ok:
            print(f"[step] {name} — cancelled by user")
            return False
    await fn()
    return True
```

스킬 사용 시 `confirm` 은 사용자에게 다시 물어보는 인터랙티브 함수로 연결. 자동 yes 금지.

### selector 우선순위
1. `getByRole`, `getByLabel`, `getByText` — 의미 기반, 강함
2. `[data-testid=...]`, `[aria-label=...]` — 사이트가 명시한 hook
3. CSS class — 빌드 해시 들어가는 경우 많아 약함. 최후 수단

```python
# 좋음
await page.get_by_role("button", name="Save").click()
await page.get_by_label("이메일").fill("a@b.com")

# 나쁨 (빌드마다 깨질 수 있음)
await page.locator("button.css-1a2b3c").click()
```

### 폼 채우기
```python
await page.get_by_label("제목").fill("...")
await page.get_by_label("본문").fill("...")
# 제출은 별도 step 으로 — irreversible=True
```

### 새 탭 / 팝업 대응
```python
async with context.expect_page() as new_page_info:
    await page.get_by_role("link", name="새창").click()
new_page = await new_page_info.value
```

### 파일 업로드
```python
async with page.expect_file_chooser() as fc:
    await page.get_by_role("button", name="첨부").click()
chooser = await fc.value
await chooser.set_files("/path/to/file")
```

## 캡차 대응 — human-in-the-loop 릴레이

자동 풀이(OCR/서비스/매크로) 금지. 텍스트형 캡차를 만나면 스크린샷을 사용자 본인에게
전송하고 답을 받아 입력·제출한다. 전체 워크플로우·채널 자격증명: `references/captcha-relay.md`.
전송·폴링은 `scripts/captcha_relay.py` 가 담당하고, 아래는 캡처 부분만.

### 캡차 감지 + 캡처
```python
CAPTCHA_SELECTORS = (
    "[id*='captcha']", "[name*='captcha']", "[data-sitekey]",
    "iframe[src*='recaptcha']", "iframe[src*='hcaptcha']",
    "iframe[src*='turnstile']", "iframe[src*='challenges.cloudflare']",
)

async def detect_and_capture(page, out_png: str) -> bool:
    """캡차 요소/iframe 이 보이면 스크롤 후 스크린샷. 발견 여부 반환."""
    found = False
    for sel in CAPTCHA_SELECTORS:
        loc = page.locator(sel).first
        if await loc.count():
            found = True
            try:
                await loc.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            break
    if not found:
        return False
    await page.wait_for_timeout(500)
    try:
        await page.locator(",".join(CAPTCHA_SELECTORS)).first.screenshot(path=out_png)
        if not (await asyncio.to_thread(lambda: __import__("os").path.getsize(out_png) > 500)):
            raise RuntimeError("blank")
    except Exception:
        # cross-origin iframe(OOPIF) 은 요소 캡처가 빈 이미지 → 뷰포트 폴백
        await page.screenshot(path=out_png)
    return True
```

### 릴레이 + 답 받기 (스크립트 위임)
```bash
python3 scripts/captcha_relay.py ask \
  --site example.com \
  --image /tmp/cdp-anywhere/challenge-example.png \
  --prompt "이미지 속 문자를 입력하세요" \
  --timeout 300
# 성공: ANSWER=<정규화된 답> (exit 0) / 답 없음: exit 2 / 채널 불가: exit 1
```

### 답 입력 + 제출 + 검증
```python
# 입력란 후보 → fill, 안 되면 click 후 press_sequentially
inp = page.locator("input[name*='captcha'], input[name*='answer'], input[autocomplete='off']").first
try:
    await inp.fill(answer)
except Exception:
    await inp.click()
    await inp.press_sequentially(answer)
# 제출 버튼 (텍스트 기반 우선)
btn = page.get_by_role("button", name="Verify").first
if not await btn.count():
    btn = page.get_by_role("button", name="확인").first
await btn.click()
# 검증: 성공이면 다음 단계 진행 / "틀림·다시 시도" 면 같은 --id 로 한 번 재시도 후 보고
```

## WebSocket / SSE 캡처

일부 사이트 (채팅, 실시간 피드) 는 데이터를 WebSocket / Server-Sent Events 로 받는다.

### WebSocket
```python
async def on_ws(ws):
    print(f"WS open: {ws.url}")
    ws.on("framereceived", lambda payload: handle(payload))
    ws.on("framesent", lambda payload: print(f"out: {payload[:80]}"))

page.on("websocket", on_ws)
```

### SSE (text/event-stream)
일반 fetch 응답으로 잡힘. `response.body()` 로 raw stream 받아 라인 단위 파싱.

## 공통 유틸

### probe 단독 실행
```bash
python ~/.claude/skills/cdp-anywhere/scripts/probe.py --host example.com
```

### 단발 스크립트 템플릿
스킬은 보통 사용자 요청마다 `/tmp/cdp-anywhere/run-{timestamp}.py` 에 단발 스크립트를 생성해 실행한다. 모듈 구조 잡지 말고 단발로.

```python
#!/usr/bin/env python3
"""단발 스크립트 — cdp-anywhere skill 이 생성."""
from __future__ import annotations
import asyncio, json, random, sys
from pathlib import Path
from playwright.async_api import async_playwright

CDP = "http://localhost:9222"
OUT = Path("/tmp/cdp-anywhere/{호스트}-{stamp}.json")

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP)
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    try:
        # ... 작업 본문 ...
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"saved {len(result)} items → {OUT}")
    finally:
        await pw.stop()  # browser.close() 금지

asyncio.run(main())
```

### 재시작 가능하게 — cursor 저장
장시간 수집은 페이지마다 cursor 와 누적 카운트를 `*.progress.json` 으로 저장. 중간 실패 시 그 cursor 부터 재개.

```python
PROGRESS = OUT.with_suffix(".progress.json")

def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"cursor": None, "count": 0}

def save_progress(state):
    PROGRESS.write_text(json.dumps(state))
```
