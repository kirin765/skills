#!/usr/bin/env python3
"""
X (Twitter) UserTweetsAndReplies GraphQL 직접 호출로 본인 타임라인 수집
(skill: x-account-coach).

Chrome CDP 로 사용자의 인증된 세션에 붙어, 로그인된 쿠키와 헤더를 그대로 써서
X 의 내부 GraphQL endpoint 를 직접 호출한다. 페이지 스크롤·DOM 파싱 없음.

전제: Chrome 이 다음 명령으로 미리 띄워져 있어야 한다.
  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
    --remote-debugging-port=9222 \\
    --user-data-dir="$HOME/chrome-cdp-profile"

사용 예:
  python x_user_timeline.py --probe
  python x_user_timeline.py --handle tvprogramlover --days 7 --max 50
  python x_user_timeline.py --handle tvprogramlover --days 14 --out /tmp/x_timeline.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import (parse_qs, quote, urlencode, urlparse, urlunparse)

from playwright.async_api import async_playwright

CDP = "http://localhost:9222"
TIMELINE_MARKER = "UserTweetsAndReplies"
PROFILE_PAGE_TPL = "https://x.com/{h}/with_replies"
PAGE_DELAY = (1.8, 3.4)
ENDPOINT_DISCOVER_TIMEOUT = 15.0
NO_PROGRESS_LIMIT = 3


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


def parse_twitter_time(s: str) -> datetime | None:
    """Twitter 'Fri May 09 12:00:00 +0000 2026' 형식 파싱."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return None


def categorize_tweet(legacy: dict, self_handle: str) -> str:
    """main / reply / thread_part 분류."""
    in_reply_to_id = legacy.get("in_reply_to_status_id_str")
    if not in_reply_to_id:
        return "main"
    in_reply_to_user = legacy.get("in_reply_to_screen_name") or ""
    if in_reply_to_user.lower() == self_handle.lower():
        return "thread_part"
    return "reply"


def extract_tweet_from_result(result: dict, self_handle: str) -> dict | None:
    """tweet_results.result 한 개에서 정규화된 트윗 dict 생성.

    UserTweetsAndReplies 응답에는 본인이 답글 단 *상대방 원글* 도 conversation
    컨텍스트로 함께 들어온다. 본인이 작성한 트윗만 통과시키기 위해 author 의
    screen_name 을 self_handle 과 비교한다. 일치하지 않으면 None 반환.
    """
    if not result:
        return None
    if "rest_id" not in result and "tweet" in result:
        result = result["tweet"]
    tweet_id = result.get("rest_id")
    if not tweet_id:
        return None

    legacy = result.get("legacy", {}) or {}
    user_result = (
        result.get("core", {})
        .get("user_results", {})
        .get("result", {})
    )
    # X 는 screen_name 위치를 user.legacy → user.core 로 옮기는 중이라 둘 다 본다.
    author_handle = (
        ((user_result.get("core") or {}).get("screen_name"))
        or ((user_result.get("legacy") or {}).get("screen_name"))
        or ""
    ).strip()
    if not author_handle or author_handle.lower() != self_handle.lower():
        # 컨텍스트 (다른 사람 원글 / 답글 부모) — 스킵.
        return None
    handle = author_handle
    views_obj = result.get("views") or {}
    views = views_obj.get("count") if isinstance(views_obj, dict) else None
    try:
        views = int(views) if views is not None else None
    except (TypeError, ValueError):
        views = None

    return {
        "id": tweet_id,
        "text": legacy.get("full_text"),
        "created_at": legacy.get("created_at"),
        "category": categorize_tweet(legacy, self_handle),
        "in_reply_to": legacy.get("in_reply_to_status_id_str"),
        "in_reply_to_user": legacy.get("in_reply_to_screen_name"),
        "likes": legacy.get("favorite_count"),
        "retweets": legacy.get("retweet_count"),
        "replies": legacy.get("reply_count"),
        "quotes": legacy.get("quote_count"),
        "views": views,
        "lang": legacy.get("lang"),
        "url": f"https://x.com/{handle}/status/{tweet_id}",
    }


def extract_tweets(payload: dict, self_handle: str, seen_ids: set) -> tuple[list, str | None]:
    """UserTweetsAndReplies 응답에서 트윗 리스트 + bottom cursor 추출."""
    tweets: list[dict] = []
    cursor: str | None = None
    try:
        timeline = (
            payload["data"]["user"]["result"]["timeline_v2"]["timeline"]
        )
        instructions = timeline.get("instructions", [])
    except (KeyError, TypeError):
        # 일부 X 배포는 timeline (v1) 키만 있음
        try:
            timeline = payload["data"]["user"]["result"]["timeline"]["timeline"]
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
                content = entry.get("content", {}) or {}
                etype = content.get("entryType") or content.get("__typename")

                # case 1: 단일 트윗
                if etype in ("TimelineTimelineItem", "TimelineItem"):
                    item = content.get("itemContent", {}) or {}
                    if item.get("itemType") != "TimelineTweet":
                        continue
                    result = item.get("tweet_results", {}).get("result", {})
                    t = extract_tweet_from_result(result, self_handle)
                    if t and t["id"] not in seen_ids:
                        seen_ids.add(t["id"])
                        tweets.append(t)

                # case 2: thread / conversation module — 여러 트윗 묶음
                elif etype in ("TimelineTimelineModule", "TimelineModule"):
                    items = content.get("items", []) or []
                    for it in items:
                        item_content = (it.get("item") or {}).get("itemContent", {}) or {}
                        if item_content.get("itemType") != "TimelineTweet":
                            continue
                        result = item_content.get("tweet_results", {}).get("result", {})
                        t = extract_tweet_from_result(result, self_handle)
                        if t and t["id"] not in seen_ids:
                            seen_ids.add(t["id"])
                            tweets.append(t)

                # case 3: cursor
                elif etype in ("TimelineTimelineCursor", "TimelineCursor"):
                    if content.get("cursorType") == "Bottom":
                        cursor = content.get("value")

        elif itype == "TimelineReplaceEntry":
            entry = inst.get("entry", {}) or {}
            content = entry.get("content", {}) or {}
            if content.get("cursorType") == "Bottom":
                cursor = content.get("value")

    return tweets, cursor


def build_next_url(template_url: str, cursor: str) -> str:
    """첫 요청 URL을 템플릿 삼아 variables JSON 의 cursor 만 갈아끼움."""
    parsed = urlparse(template_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "variables" in qs:
        try:
            variables = json.loads(qs["variables"][0])
        except json.JSONDecodeError:
            variables = {}
        variables["cursor"] = cursor
        qs["variables"] = [json.dumps(variables, separators=(",", ":"))]
    new_query = urlencode(qs, doseq=True, quote_via=quote)
    return urlunparse(parsed._replace(query=new_query))


# ===== CDP / Probe =====
async def probe_login(context) -> tuple[bool, str]:
    cookies = await context.cookies("https://x.com")
    have = {c["name"] for c in cookies}
    if "ct0" in have and "auth_token" in have:
        return True, "X 로그인 쿠키 (ct0+auth_token) 확인됨"
    missing = [c for c in ("ct0", "auth_token") if c not in have]
    return False, f"로그인 쿠키 부족 ({', '.join(missing)} 없음)"


async def discover_endpoint(page, handle: str) -> dict:
    captured = {"url": None, "headers": None, "payload": None}

    async def on_request(request):
        if TIMELINE_MARKER in request.url and captured["url"] is None:
            captured["url"] = request.url
            try:
                captured["headers"] = await request.all_headers()
            except Exception:
                captured["headers"] = dict(request.headers)

    async def on_response(response):
        if TIMELINE_MARKER in response.url and captured["payload"] is None:
            try:
                captured["payload"] = await response.json()
            except Exception:
                pass

    page.on("request", on_request)
    page.on("response", on_response)

    await page.goto(
        PROFILE_PAGE_TPL.format(h=quote(handle)),
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
    ok, info = await probe_login(context)
    print(f"  {'✅' if ok else '❌'} X 로그인: {info}")
    if not ok:
        print(
            "\n→ Chrome 띄우고 X 에 로그인하세요:"
            "\n   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\"
            "\n     --remote-debugging-port=9222 \\"
            '\n     --user-data-dir="$HOME/chrome-cdp-profile"'
        )
    return ok


async def collect_timeline(
    context, handle: str, days: int, max_tweets: int
) -> list[dict]:
    seen: set[str] = set()
    tweets: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    page = await context.new_page()
    print(f"  → endpoint discover: handle=@{handle}", file=sys.stderr)
    cap = await discover_endpoint(page, handle)
    await page.close()

    if not cap["url"] or not cap["payload"]:
        raise RuntimeError(
            f"UserTweetsAndReplies endpoint 캡처 실패 — 핸들 @{handle} 이 정확한지, "
            "로그인이 살아있는지 확인."
        )

    api_headers = headers_from_intercept(cap["headers"])
    template_url = cap["url"]

    initial, cursor = extract_tweets(cap["payload"], handle, seen)
    tweets.extend(initial)
    print(
        f"  initial: {len(tweets)} tweets, cursor={cursor[:24] + '…' if cursor else None}",
        file=sys.stderr,
    )

    no_progress = 0
    while (
        len(tweets) < max_tweets
        and cursor
        and no_progress < NO_PROGRESS_LIMIT
    ):
        # 7-일 컷: 가장 최근 페이지 끝의 트윗이 cutoff 이전이면 stop
        last_in_window = any(
            (parse_twitter_time(t["created_at"]) or datetime.min.replace(tzinfo=timezone.utc))
            >= cutoff
            for t in tweets[-20:]
        )
        if not last_in_window and tweets:
            print("  cutoff window exceeded; stop", file=sys.stderr)
            break

        await asyncio.sleep(random.uniform(*PAGE_DELAY))
        next_url = build_next_url(template_url, cursor)
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

        new_tweets, new_cursor = extract_tweets(payload, handle, seen)
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

    # 최종 7-일 필터링 + 최대 max_tweets 컷
    filtered = []
    for t in tweets:
        ts = parse_twitter_time(t["created_at"])
        if ts and ts >= cutoff:
            filtered.append(t)

    # 본인 작성한 것만 (retweet 표시는 별도 처리 필요시 향후 확장)
    return filtered[:max_tweets]


# ===== Entry =====
async def main():
    ap = argparse.ArgumentParser(description="X 본인 타임라인 CDP 수집")
    ap.add_argument("--handle", help="본인 X 핸들 (@ 없이)")
    ap.add_argument("--days", type=int, default=7, help="최근 N 일 (기본 7)")
    ap.add_argument("--max", type=int, default=50, help="최대 트윗 수 (기본 50)")
    ap.add_argument("--out", default="/tmp/x_my_timeline.json", help="출력 JSON 경로")
    ap.add_argument("--cdp", default=CDP, help="CDP endpoint")
    ap.add_argument("--probe", action="store_true", help="로그인만 확인하고 종료")
    args = ap.parse_args()

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            print(f"❌ CDP {args.cdp} 연결 실패: {e}", file=sys.stderr)
            print(
                "→ Chrome 띄우세요:"
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

        if not args.handle:
            print("❌ --handle 필수 (예: --handle tvprogramlover)", file=sys.stderr)
            sys.exit(1)

        ok = await run_probe_only(context)
        if not ok:
            sys.exit(2)

        print(
            f"\n=== 수집 시작: @{args.handle}, last {args.days}d, max {args.max} ==="
        )
        started = datetime.now()
        try:
            tweets = await collect_timeline(context, args.handle, args.days, args.max)
        except Exception as e:
            print(f"\n❌ 수집 실패: {e}", file=sys.stderr)
            sys.exit(2)
        elapsed = (datetime.now() - started).total_seconds()

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(tweets, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 카테고리 별 카운트 stderr 에 출력 (요약용)
        cats: dict[str, int] = {}
        for t in tweets:
            cats[t["category"]] = cats.get(t["category"], 0) + 1
        print(
            f"\n=== DONE: {len(tweets)} tweets ({cats}) in {elapsed:.1f}s → {out_path} ===",
            file=sys.stderr,
        )


if __name__ == "__main__":
    asyncio.run(main())
