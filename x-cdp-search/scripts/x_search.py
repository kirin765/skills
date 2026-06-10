#!/usr/bin/env python3
"""
X (Twitter) SearchTimeline GraphQL 직접 호출 스크랩 (skill: x-cdp-search).

Chrome CDP 로 사용자의 인증된 세션에 붙어, 로그인된 쿠키와 헤더를 그대로 써서
X 의 내부 GraphQL endpoint 를 직접 호출한다. 페이지 스크롤·DOM 파싱 없음.

전제: Chrome 이 다음 명령으로 미리 띄워져 있어야 한다.
  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
    --remote-debugging-port=9222 \\
    --user-data-dir="$HOME/chrome-cdp-profile"

사용 예:
  python x_search.py --probe
  python x_search.py --query "쇼츠 자동화" --max 100
  python x_search.py --query "min_faves:10 lang:ko 다채널 운영" --max 200 --out /tmp/x_pain.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import (parse_qs, quote, urlencode, urlparse, urlunparse)

from playwright.async_api import async_playwright

CDP = "http://localhost:9222"
SEARCH_TIMELINE_MARKER = "SearchTimeline"
SEARCH_PAGE_TPL = "https://x.com/search?q={q}&src=typed_query&f=live"
PAGE_DELAY = (1.8, 3.4)            # API 페이지 호출 사이 sleep
ENDPOINT_DISCOVER_TIMEOUT = 15.0   # 첫 SearchTimeline 캡처 대기 (초)
NO_PROGRESS_LIMIT = 3              # cursor 진행 안 될 때 stop 임계


# ===== Helpers =====
def headers_from_intercept(raw_headers: dict) -> dict:
    """가로챈 요청 헤더 중 GraphQL 호출에 필요한 것만 통과."""
    keep = {
        "authorization", "x-csrf-token", "x-twitter-active-user",
        "x-twitter-auth-type", "x-twitter-client-language",
        "content-type", "accept", "accept-language",
        "x-client-uuid", "x-client-transaction-id",
        "user-agent",
    }
    out = {}
    for k, v in (raw_headers or {}).items():
        if k.lower() in keep:
            out[k] = v
    return out


def extract_tweets(payload: dict, seen_ids: set) -> tuple[list, str | None]:
    """SearchTimeline 응답에서 트윗 + bottom cursor 추출."""
    tweets: list[dict] = []
    cursor: str | None = None
    try:
        timeline = payload["data"]["search_by_raw_query"]["search_timeline"]["timeline"]
        instructions = timeline.get("instructions", [])
    except (KeyError, TypeError):
        return tweets, cursor

    for inst in instructions:
        itype = inst.get("type")
        if itype in ("TimelineAddEntries", "TimelinePinEntry"):
            entries = inst.get("entries") or ([inst.get("entry")] if inst.get("entry") else [])
            for entry in entries:
                if not entry:
                    continue
                content = entry.get("content", {})
                etype = content.get("entryType") or content.get("__typename")
                if etype in ("TimelineTimelineItem", "TimelineItem"):
                    item = content.get("itemContent", {})
                    if item.get("itemType") != "TimelineTweet":
                        continue
                    result = item.get("tweet_results", {}).get("result", {})
                    if "rest_id" not in result and "tweet" in result:
                        result = result["tweet"]
                    tweet_id = result.get("rest_id")
                    if not tweet_id or tweet_id in seen_ids:
                        continue
                    seen_ids.add(tweet_id)

                    legacy = result.get("legacy", {})
                    user_result = (
                        result.get("core", {})
                        .get("user_results", {})
                        .get("result", {})
                    )
                    user_legacy = user_result.get("legacy", {}) or {}
                    user_core = user_result.get("core", {}) or {}
                    # X migrated user objects: screen_name now lives in core (post-2025),
                    # legacy path still works for older endpoints. Try both.
                    handle = (
                        user_core.get("screen_name")
                        or user_legacy.get("screen_name")
                        or user_result.get("screen_name")
                        or ""
                    )
                    name = (
                        user_core.get("name")
                        or user_legacy.get("name")
                        or user_result.get("name")
                    )
                    views_obj = result.get("views")
                    views = views_obj.get("count") if isinstance(views_obj, dict) else None

                    tweets.append({
                        "id": tweet_id,
                        "author_handle": handle,
                        "author_name": name,
                        "text": legacy.get("full_text"),
                        "created_at": legacy.get("created_at"),
                        "likes": legacy.get("favorite_count"),
                        "retweets": legacy.get("retweet_count"),
                        "replies": legacy.get("reply_count"),
                        "quotes": legacy.get("quote_count"),
                        "views": views,
                        "lang": legacy.get("lang"),
                        "url": f"https://x.com/{handle}/status/{tweet_id}" if handle else f"https://x.com/i/web/status/{tweet_id}",
                    })
                elif etype in ("TimelineTimelineCursor", "TimelineCursor"):
                    if content.get("cursorType") == "Bottom":
                        cursor = content.get("value")
        elif itype == "TimelineReplaceEntry":
            entry = inst.get("entry", {}) or {}
            content = entry.get("content", {})
            if content.get("cursorType") == "Bottom":
                cursor = content.get("value")
    return tweets, cursor


def build_next_url(template_url: str, query: str, cursor: str) -> str:
    """첫 요청 URL을 템플릿 삼아 variables JSON 의 rawQuery·cursor 만 갈아끼움."""
    parsed = urlparse(template_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "variables" in qs:
        try:
            variables = json.loads(qs["variables"][0])
        except json.JSONDecodeError:
            variables = {}
        variables["rawQuery"] = query
        variables["cursor"] = cursor
        # 일부 X 배포는 product/querySource 도 variables 에 있음 — 유지
        qs["variables"] = [json.dumps(variables, separators=(",", ":"))]
    new_query = urlencode(qs, doseq=True, quote_via=quote)
    return urlunparse(parsed._replace(query=new_query))


# ===== CDP / Probe =====
def ensure_page_target(cdp_base: str = CDP) -> None:
    """connect_over_cdp는 page target이 0개면 setDownloadBehavior에서 깨진다
    (창을 모두 닫아 windowless로 떠 있는 Chrome). 탭 하나를 보장한다."""
    import urllib.request
    try:
        tabs = json.load(urllib.request.urlopen(f"{cdp_base}/json", timeout=5))
    except Exception:
        return  # CDP 미응답이면 connect 단계에서 에러 처리
    if any(t.get("type") == "page" for t in tabs):
        return
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"{cdp_base}/json/new?about:blank", method="PUT"),
            timeout=8,
        )
    except Exception:
        pass  # 실패해도 connect가 시도하고 보고한다


async def probe_cdp_and_login(context) -> tuple[bool, str]:
    """X 로그인 상태 확인. ct0 쿠키 존재 + auth_token 존재 검사."""
    cookies = await context.cookies("https://x.com")
    have = {c["name"] for c in cookies}
    if "ct0" in have and "auth_token" in have:
        return True, "X 로그인 쿠키 (ct0+auth_token) 확인됨"
    missing = [c for c in ("ct0", "auth_token") if c not in have]
    return False, f"로그인 쿠키 부족 ({', '.join(missing)} 없음)"


async def discover_search_endpoint(page, query: str) -> dict:
    """검색 페이지 한 번 열어 첫 SearchTimeline 요청 URL+헤더+payload 캡처."""
    captured = {"url": None, "headers": None, "payload": None}

    async def on_request(request):
        if SEARCH_TIMELINE_MARKER in request.url and captured["url"] is None:
            captured["url"] = request.url
            try:
                captured["headers"] = await request.all_headers()
            except Exception:
                captured["headers"] = dict(request.headers)

    async def on_response(response):
        if SEARCH_TIMELINE_MARKER in response.url and captured["payload"] is None:
            try:
                captured["payload"] = await response.json()
            except Exception:
                pass

    page.on("request", on_request)
    page.on("response", on_response)

    await page.goto(
        SEARCH_PAGE_TPL.format(q=quote(query)),
        wait_until="domcontentloaded",
        timeout=20000,
    )

    waited = 0.0
    while waited < ENDPOINT_DISCOVER_TIMEOUT:
        if captured["url"] and captured["payload"] and captured["headers"]:
            break
        await page.wait_for_timeout(500)
        waited += 0.5
    return captured


# ===== Top-level flow =====
async def run_probe_only(context):
    print("=== 사전 조건 probe ===\n")
    ok, info = await probe_cdp_and_login(context)
    print(f"  {'✅' if ok else '❌'} X 로그인: {info}")
    if not ok:
        print(
            "\n→ 다음 명령으로 Chrome 띄우고 X 에 로그인하세요:"
            "\n   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\"
            "\n     --remote-debugging-port=9222 \\"
            '\n     --user-data-dir="$HOME/chrome-cdp-profile"'
        )
    return ok


async def search_x(context, query: str, max_tweets: int) -> list[dict]:
    seen: set[str] = set()
    tweets: list[dict] = []

    # endpoint discovery — 페이지 1회 오픈
    page = await context.new_page()
    print(f"  → endpoint discover: query={query!r}", file=sys.stderr)
    cap = await discover_search_endpoint(page, query)
    await page.close()

    if not cap["url"] or not cap["payload"]:
        raise RuntimeError(
            "SearchTimeline endpoint 캡처 실패 — 로그인 풀렸거나 X 가 검색을 막았을 수 있음"
        )

    api_headers = headers_from_intercept(cap["headers"])
    template_url = cap["url"]

    initial, cursor = extract_tweets(cap["payload"], seen)
    tweets.extend(initial)
    print(
        f"  initial: {len(tweets)} tweets, cursor={cursor[:24] + '…' if cursor else None}",
        file=sys.stderr,
    )

    # API 페이지네이션
    no_progress = 0
    while len(tweets) < max_tweets and cursor and no_progress < NO_PROGRESS_LIMIT:
        await asyncio.sleep(random.uniform(*PAGE_DELAY))
        next_url = build_next_url(template_url, query, cursor)
        try:
            r = await context.request.get(next_url, headers=api_headers)
        except Exception as e:
            print(f"  request err: {e}; stop", file=sys.stderr)
            break
        if r.status != 200:
            body = (await r.text())[:200]
            print(f"  http {r.status}: {body}; stop", file=sys.stderr)
            break
        try:
            payload = await r.json()
        except Exception as e:
            print(f"  json parse err: {e}; stop", file=sys.stderr)
            break

        new_tweets, new_cursor = extract_tweets(payload, seen)
        if not new_tweets:
            no_progress += 1
        else:
            no_progress = 0
        tweets.extend(new_tweets)
        cursor = new_cursor
        print(
            f"  +{len(new_tweets)} (total {len(tweets)}) cursor={cursor[:24] + '…' if cursor else None}",
            file=sys.stderr,
        )
        if not cursor:
            print("  no more cursor; stop", file=sys.stderr)
            break

    return tweets[:max_tweets]


# ===== Entry =====
async def main():
    ap = argparse.ArgumentParser(description="X (Twitter) CDP 인증 세션 기반 검색 스크랩")
    ap.add_argument("--query", help="검색 쿼리 (Advanced Search 연산자 OK)")
    ap.add_argument("--max", type=int, default=100, help="최대 트윗 수 (기본 100)")
    ap.add_argument("--out", default="/tmp/x_results.json", help="출력 JSON 경로")
    ap.add_argument("--cdp", default=CDP, help="CDP endpoint")
    ap.add_argument("--probe", action="store_true", help="로그인만 확인하고 종료")
    args = ap.parse_args()

    async with async_playwright() as p:
        ensure_page_target(args.cdp)
        try:
            browser = await p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            print(f"❌ CDP {args.cdp} 연결 실패: {e}", file=sys.stderr)
            print(
                "→ 다음 명령으로 Chrome 띄우고 X 에 로그인 후 다시 시도하세요:"
                "\n   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\"
                "\n     --remote-debugging-port=9222 \\"
                '\n     --user-data-dir="$HOME/chrome-cdp-profile"',
                file=sys.stderr,
            )
            sys.exit(1)

        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        if args.probe:
            ok = await run_probe_only(context)
            sys.exit(0 if ok else 2)

        if not args.query:
            print("❌ --query 필수 (예: --query \"쇼츠 자동화\")", file=sys.stderr)
            sys.exit(1)

        ok = await run_probe_only(context)
        if not ok:
            sys.exit(2)

        print(f"\n=== 스크랩 시작: query={args.query!r}, max={args.max} ===")
        started = datetime.now()
        try:
            tweets = await search_x(context, args.query, args.max)
        except Exception as e:
            print(f"\n❌ 스크랩 실패: {e}", file=sys.stderr)
            sys.exit(2)
        elapsed = (datetime.now() - started).total_seconds()

        # Enrich missing handles via public syndication API (no auth required)
        missing = [t for t in tweets if not t.get("author_handle")]
        if missing:
            print(f"  → enriching {len(missing)} tweets w/ missing handles via syndication API", file=sys.stderr)
            import urllib.request as _u, urllib.error as _ue
            for t in missing:
                tid = t.get("id")
                if not tid:
                    continue
                syn_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=4cdvwd6n4ud"
                try:
                    req = _u.Request(syn_url, headers={"User-Agent": "Mozilla/5.0"})
                    with _u.urlopen(req, timeout=8) as r:
                        d = json.loads(r.read())
                    u = d.get("user", {}) or {}
                    sn = u.get("screen_name")
                    if sn:
                        t["author_handle"] = sn
                        t["author_name"] = t.get("author_name") or u.get("name")
                        t["url"] = f"https://x.com/{sn}/status/{tid}"
                except Exception:
                    continue

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(tweets, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            f"\n=== DONE: {len(tweets)} tweets in {elapsed:.1f}s → {out_path} ===",
            file=sys.stderr,
        )


if __name__ == "__main__":
    asyncio.run(main())
