#!/usr/bin/env python3
"""
네이버 카페 SPA 내부 JSON API 를 통한 일괄 스크랩 (skill: naver-cafe-scrape).

Chrome CDP 로 사용자의 인증된 세션에 붙어 카페 게시판 글을 수집한다.
카페 종류와 무관하게 인자만 바꿔 재사용 가능하다.

전제: Chrome 이 다음 명령으로 미리 띄워져 있어야 한다.
  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
    --remote-debugging-port=9222 \\
    --user-data-dir="$HOME/chrome-cdp-profile"

사용 예:
  python scrape_naver_cafe.py --cafe tazza4 --boards 59,135,94 --probe
  python scrape_naver_cafe.py --cafe tazza4 --boards 59,135,94 --days 180
  python scrape_naver_cafe.py --cafe tazza4 --boards 59 --limit 500
  python scrape_naver_cafe.py --cafe tazza4 --probe-article 334844
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

CDP = "http://localhost:9222"
PAGE_SIZE = 50
LIST_DELAY = (0.8, 1.6)
ARTICLE_DELAY = (0.5, 1.2)

LIST_API_TPL = "https://apis.naver.com/cafe-web/cafe-boardlist-api/v1/cafes/{clubid}/menus/{menuid}/articles"
ARTICLE_API_TPL = "https://article.cafe.naver.com/gw/v4/cafes/{clubid}/articles/{articleid}"


def launch_cdp_chrome_macos() -> tuple[bool, str]:
    """CDP 전용 Chrome(chrome-cdp-profile, 9222) 을 백그라운드로 자동 기동한다(backup).
    사용자의 평소 Chrome(Default 프로파일)은 별도 --user-data-dir 라 손대지 않는다."""
    import os
    import subprocess
    import time
    import urllib.request

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    profile_dir = os.path.expanduser("~/chrome-cdp-profile")
    try:
        subprocess.Popen(
            [chrome_bin, "--remote-debugging-port=9222", f"--user-data-dir={profile_dir}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return False, f"CDP Chrome 기동 실패: {e}"

    for _ in range(15):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://localhost:9222/json/version", timeout=3)
            return True, "CDP Chrome 자동 기동 성공"
        except Exception:
            continue
    return False, "CDP Chrome 을 띄웠지만 15초 내 9222 응답 없음"


# ===== Helpers =====
def parse_cafe_arg(s: str) -> str:
    """URL 또는 카페 이름 모두 받아 cafe_name 만 반환."""
    s = s.strip().rstrip("/")
    m = re.search(r"cafe\.naver\.com/([^/?#]+)", s)
    return m.group(1) if m else s


def headers_for(club_id: str) -> dict:
    return {
        "Referer": f"https://cafe.naver.com/f-e/cafes/{club_id}/menus/0?viewType=L",
        "Origin": "https://cafe.naver.com",
        "x-cafe-product": "pc",
        "Accept": "*/*",
    }


def html_to_text(html: str) -> str:
    if not html:
        return ""
    s = html
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</(p|div|li)>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ")
           .replace("&amp;", "&")
           .replace("&lt;", "<")
           .replace("&gt;", ">")
           .replace("&quot;", '"')
           .replace("&bull;", "•")
           .replace("&#x27;", "'"))
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def is_filtered(item: dict) -> str | None:
    if item.get("blindArticle"): return "blind"
    if item.get("marketArticle"): return "market"
    if item.get("restrictMenu"): return "restrictMenu"
    subject = (item.get("subject") or "").lstrip()
    if subject.startswith("《"): return "sticky"
    return None


def slugify_label(label: str) -> str:
    """게시판 라벨 → 디렉토리 이름 안전하게 변환."""
    s = re.sub(r"[•\s]+", "_", label.strip())
    s = re.sub(r"[^\w가-힣_-]", "", s)
    return s or "board"


# ===== Index =====
def load_index(index_file: Path) -> dict:
    if not index_file.exists():
        return {}
    return json.loads(index_file.read_text())


def save_index(index_file: Path, idx: dict):
    index_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2))


def board_state(idx: dict, board_key: str) -> dict:
    return idx.setdefault(board_key, {"last_page": 0, "done": []})


# ===== CDP / Probe =====
async def probe_cdp_and_login(context) -> tuple[bool, str]:
    """네이버 로그인 상태 확인. (ok, info) 반환."""
    page = context.pages[0] if context.pages else await context.new_page()
    try:
        await page.goto("https://cafe.naver.com", wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        return False, f"네이버 카페 페이지 접근 실패: {e}"
    info = await page.evaluate("""() => {
        const m = document.documentElement.innerHTML.match(/"loginId"\\s*:\\s*"([^"]+)"/);
        if (m) return m[1];
        const a = document.querySelector('a[href*="logout"], #gnb_logout_button');
        if (a) return 'logged-in (id unknown)';
        return null;
    }""")
    return (bool(info), info or "로그인 안 됨")


async def probe_cafe_membership(context, cafe_name: str) -> tuple[bool, str | None, str]:
    """
    카페 페이지에서 club_id 추출 + 가입 여부 확인.
    (ok, club_id, info) 반환.
    """
    page = context.pages[0] if context.pages else await context.new_page()
    try:
        await page.goto(f"https://cafe.naver.com/{cafe_name}", wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        return False, None, f"카페 페이지 접근 실패: {e}"
    club_id = await page.evaluate("""() => {
        return document.documentElement.innerHTML.match(/clubid[\"']?\\s*[:=]\\s*[\"']?(\\d+)/i)?.[1] || null;
    }""")
    if not club_id:
        return False, None, "클럽 ID 추출 실패 — 카페 URL 또는 카페 이름 확인 필요"
    # 가입 여부 — 게시글 작성 버튼 또는 가입하기 버튼 검출
    member_status = await page.evaluate("""() => {
        const html = document.documentElement.innerHTML;
        if (/가입하기|join/i.test(html.substring(0, 50000)) && !/회원가입 완료|이미 가입/i.test(html)) {
            // 가입 버튼이 dominant 면 미가입
            const joinBtn = document.querySelector('a[href*="join"], button[class*="join"]');
            if (joinBtn && joinBtn.offsetParent !== null) return 'not-member';
        }
        return 'member-or-public';
    }""")
    return True, club_id, f"club_id={club_id}, status={member_status}"


async def probe_board(context, club_id: str, menuid: int) -> tuple[bool, str, str]:
    """
    한 게시판에 접근 가능한지 확인. (ok, board_label, info) 반환.
    """
    url = LIST_API_TPL.format(clubid=club_id, menuid=menuid)
    try:
        r = await context.request.get(url, params={
            "page": 1, "pageSize": 5, "sortBy": "TIME", "viewType": "L",
        }, headers=headers_for(club_id))
    except Exception as e:
        return False, "", f"http err: {e}"
    if r.status == 401:
        return False, "", "HTTP 401 (등업 부족 또는 권한 없음)"
    if r.status != 200:
        return False, "", f"HTTP {r.status}: {(await r.text())[:120]}"
    data = await r.json()
    msg = data.get("message", {})
    if msg.get("status") and msg["status"] != "200":
        return False, "", f"API err: {msg}"
    items = data.get("result", {}).get("articleList", [])
    if not items:
        return False, "", "응답은 정상이나 글 없음"
    first = items[0].get("item", {})
    label = first.get("menuName") or f"menuid_{menuid}"
    label = re.sub(r"&bull;\s*", "• ", label).strip() or f"menuid_{menuid}"
    return True, label, f"OK ({len(items)}건 응답)"


async def probe_board_labels_from_page(context, club_id: str, menuids: list[int]) -> dict[int, str]:
    """카페 메인 페이지 좌측 메뉴에서 menuid → 라벨 매핑 추출."""
    page = context.pages[0] if context.pages else await context.new_page()
    menus = await page.evaluate("""() => {
        const items = document.querySelectorAll('a[href*="search.menuid="], a[href*="menuid="]');
        const out = {};
        items.forEach(a => {
            const m = a.href.match(/menuid=(\\d+)/);
            if (m) {
                const txt = a.textContent.trim();
                if (txt && !out[m[1]]) out[m[1]] = txt;
            }
        });
        return out;
    }""")
    return {int(k): v for k, v in (menus or {}).items() if int(k) in menuids}


# ===== Article fetch =====
async def fetch_list_page(context, club_id: str, menuid: int, page: int):
    url = LIST_API_TPL.format(clubid=club_id, menuid=menuid)
    r = await context.request.get(url, params={
        "page": page, "pageSize": PAGE_SIZE, "sortBy": "TIME", "viewType": "L",
    }, headers=headers_for(club_id))
    if r.status != 200:
        raise RuntimeError(f"list http {r.status}: {(await r.text())[:200]}")
    data = await r.json()
    msg = data.get("message", {})
    if msg.get("status") and msg["status"] != "200":
        raise RuntimeError(f"list api err: {msg}")
    return data["result"]["articleList"]


async def fetch_article(context, club_id: str, article_id: str):
    url = ARTICLE_API_TPL.format(clubid=club_id, articleid=article_id)
    r = await context.request.get(url, params={
        "query": "", "useCafeId": "true", "requestFrom": "A",
    }, headers=headers_for(club_id))
    if r.status != 200:
        raise RuntimeError(f"article http {r.status}")
    data = await r.json()
    return data["result"]["article"]


# ===== Persist =====
def write_post(out_dir: Path, cafe_name: str, board_key: str, board_label: str,
               article_id: str, posted_at: datetime, list_item: dict, art: dict, club_id: str):
    month_dir = out_dir / cafe_name / board_key / posted_at.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)

    body_text = html_to_text(art.get("contentHtml", ""))
    title = art.get("subject") or list_item.get("subject", "")
    writer = art.get("writer") or {}

    lines = [
        "---",
        f"source: cafe.naver.com/{cafe_name}",
        f"board_key: {board_key}",
        f"board_label: {board_label}",
        f"article_id: {article_id}",
        f"url: https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}",
        f"posted_at: {posted_at.isoformat()}",
        f"scraped_at: {datetime.now().isoformat(timespec='seconds')}",
        f"writer_nick: {writer.get('nick', '')}",
        f"writer_level: {writer.get('memberLevelName', '')}",
        f"views: {art.get('readCount', '')}",
        f"likes: {art.get('likeCount', '')}",
        f"comment_count: {art.get('commentCount', 0)}",
        "---",
        "",
        f"# {title}",
        "",
        body_text,
        "",
    ]
    (month_dir / f"{article_id}.md").write_text("\n".join(lines), encoding="utf-8")


# ===== Per-board scrape =====
async def scrape_board(context, club_id: str, cafe_name: str,
                       menuid: int, board_label: str,
                       out_dir: Path, idx: dict, index_file: Path,
                       days: int | None, limit: int) -> int:
    board_key = slugify_label(board_label) or f"menuid_{menuid}"
    state = board_state(idx, board_key)
    done = set(state.get("done", []))
    page_num = state.get("last_page", 0) + 1

    cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp() * 1000 if days else None

    saved = 0
    skipped = {"blind": 0, "market": 0, "restrictMenu": 0, "sticky": 0, "done": 0}
    started = datetime.now()

    print(f"\n=== [{board_key}] {board_label} (menuid={menuid}) ===")
    print(f"start: page {page_num}, {'days='+str(days) if days else 'limit='+str(limit)}")

    while True:
        if not days and saved >= limit:
            print(f"  limit {limit} reached; stop")
            break
        try:
            items = await fetch_list_page(context, club_id, menuid, page_num)
        except Exception as e:
            print(f"  list page {page_num} error: {e}; stop")
            break
        if not items:
            print(f"  empty page {page_num}; stop")
            break

        stop = False
        for entry in items:
            it = entry.get("item", {})
            if not it: continue
            reason = is_filtered(it)
            if reason:
                skipped[reason] += 1; continue
            aid = str(it["articleId"])
            if aid in done:
                skipped["done"] += 1; continue
            ts = it.get("writeDateTimestamp")
            if cutoff_ts and ts and ts < cutoff_ts:
                print(f"  cutoff reached at {datetime.fromtimestamp(ts/1000).date()}; stop")
                stop = True; break
            posted_at = datetime.fromtimestamp(ts / 1000) if ts else datetime.now()
            try:
                art = await fetch_article(context, club_id, aid)
                write_post(out_dir, cafe_name, board_key, board_label, aid, posted_at, it, art, club_id)
                done.add(aid); saved += 1
                print(f"  ✓ p{page_num} {aid} {posted_at.date()} {it.get('subject', '')[:40]}", flush=True)
            except Exception as e:
                print(f"  ✗ p{page_num} {aid}: {e}", flush=True)
            await asyncio.sleep(random.uniform(*ARTICLE_DELAY))
            if not days and saved >= limit:
                stop = True; break

        state["last_page"] = page_num
        state["done"] = sorted(done)
        save_index(index_file, idx)
        if stop: break
        page_num += 1
        await asyncio.sleep(random.uniform(*LIST_DELAY))

    elapsed = (datetime.now() - started).total_seconds()
    print(f"  done {board_key}: saved {saved} ({elapsed/60:.1f} min) skipped {skipped}")
    return saved


# ===== Single article probe (디버깅) =====
async def probe_article_dump(context, club_id: str, article_id: str):
    url = ARTICLE_API_TPL.format(clubid=club_id, articleid=article_id)
    r = await context.request.get(url, params={
        "query": "", "useCafeId": "true", "requestFrom": "A",
    }, headers=headers_for(club_id))
    print(f"GET {url}\nstatus: {r.status}")
    if r.status != 200:
        print((await r.text())[:1500]); return
    data = await r.json()
    art = data.get("result", {}).get("article", {})
    print(f"subject: {art.get('subject', '')[:60]}")
    print(f"commentCount: {art.get('commentCount')}")
    print(f"readCount:    {art.get('readCount')}")
    body = html_to_text(art.get("contentHtml", ""))
    print(f"\nbody ({len(body)} chars):\n{body[:600]}\n...")


# ===== Top-level flow =====
async def run_probe_only(context, cafe_name: str, menuids: list[int]):
    print(f"=== 사전 조건 probe: cafe={cafe_name}, boards={menuids} ===\n")
    # 1. 로그인
    ok, info = await probe_cdp_and_login(context)
    print(f"  {'✅' if ok else '❌'} 네이버 로그인: {info}")
    if not ok:
        print("\n→ 다음 명령으로 Chrome 다시 띄우고 네이버에 로그인하세요:")
        print('   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n     --remote-debugging-port=9222 \\\n     --user-data-dir="$HOME/chrome-cdp-profile"')
        return False, None, []
    # 2. 카페 가입 + club_id
    ok, club_id, info = await probe_cafe_membership(context, cafe_name)
    print(f"  {'✅' if ok else '❌'} 카페 ({cafe_name}): {info}")
    if not ok:
        return False, None, []
    if "not-member" in info:
        print("\n→ 카페 가입 후 다시 시도하세요.")
        return False, club_id, []
    # 3. 게시판별 라벨 추출
    labels = await probe_board_labels_from_page(context, club_id, menuids)
    # 4. 게시판별 접근 가능 여부
    board_results = []
    for mid in menuids:
        ok_b, lbl_b, info_b = await probe_board(context, club_id, mid)
        # 메뉴에서 가져온 라벨이 더 정확함 (게시판 메뉴명 노출 안 될 때 대비)
        label = labels.get(mid) or lbl_b
        emoji = "✅" if ok_b else "❌"
        print(f"  {emoji} board {mid} ({label or '?'}): {info_b}")
        board_results.append((mid, ok_b, label, info_b))
    accessible = [b for b in board_results if b[1]]
    if not accessible:
        print("\n→ 접근 가능한 게시판이 없습니다. 등업·가입 상태 확인 필요.")
        return False, club_id, []
    return True, club_id, board_results


async def run_scrape(context, cafe_name: str, menuids: list[int],
                     out_dir: Path, days: int | None, limit: int, do_reset: bool):
    ok, club_id, board_results = await run_probe_only(context, cafe_name, menuids)
    if not ok:
        sys.exit(2)
    accessible = [(mid, lbl) for mid, okb, lbl, _ in board_results if okb]
    blocked = [(mid, info) for mid, okb, lbl, info in board_results if not okb]
    if blocked:
        print(f"\n⚠ 접근 불가 게시판 {len(blocked)}개 — 건너뜀:")
        for mid, info in blocked:
            print(f"     menuid={mid}: {info}")

    out_dir.mkdir(parents=True, exist_ok=True)
    index_file = out_dir / f"INDEX_{cafe_name}.json"
    if do_reset and index_file.exists():
        index_file.unlink()
        print(f"\nreset: removed {index_file.name}")
    idx = load_index(index_file)

    print(f"\n=== 스크랩 시작: {len(accessible)} boards, days={days}, limit={limit} ===")
    started = datetime.now()
    total_saved = 0
    for mid, lbl in accessible:
        try:
            total_saved += await scrape_board(
                context, club_id, cafe_name, mid, lbl, out_dir, idx, index_file, days, limit
            )
        except Exception as e:
            print(f"[menuid={mid}] fatal: {e}", file=sys.stderr)
        save_index(index_file, idx)
    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n=== ALL DONE. total saved: {total_saved} in {elapsed/60:.1f} min ===")


# ===== Entry =====
async def main():
    ap = argparse.ArgumentParser(description="네이버 카페 SPA 스크랩")
    ap.add_argument("--cafe", required=True, help="카페 이름 또는 URL (예: tazza4 또는 https://cafe.naver.com/tazza4)")
    ap.add_argument("--boards", help="게시판 menuid 콤마 구분 (예: 59,135,94)")
    ap.add_argument("--out", default=None, help="출력 디렉토리 (기본: ./raw)")
    ap.add_argument("--probe", action="store_true", help="사전 조건만 확인")
    ap.add_argument("--probe-article", help="단일 글 응답 구조 덤프")
    ap.add_argument("--limit", type=int, default=2000, help="글 수 cap (--days 미지정 시)")
    ap.add_argument("--days", type=int, default=None, help="기간 cutoff (일 수)")
    ap.add_argument("--reset", action="store_true", help="진행 인덱스 초기화 후 시작")
    args = ap.parse_args()

    cafe_name = parse_cafe_arg(args.cafe)
    out_dir = Path(args.out) if args.out else Path("./raw")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP)
        except Exception as e:
            print(f"❌ CDP {CDP} 연결 실패: {e}", file=sys.stderr)
            connected = False
            if sys.platform == "darwin":
                print("⏳ CDP 전용 Chrome(chrome-cdp-profile) 자동 기동 시도 중...", file=sys.stderr)
                launch_ok, launch_msg = launch_cdp_chrome_macos()
                print(("✅ " if launch_ok else "❌ ") + launch_msg, file=sys.stderr)
                if launch_ok:
                    try:
                        browser = await p.chromium.connect_over_cdp(CDP)
                        connected = True
                    except Exception as e2:
                        print(f"❌ 자동 기동 후에도 CDP 연결 실패: {e2}", file=sys.stderr)
            if not connected:
                print("→ 자동 기동도 실패(또는 macOS 아님) — 다음 명령으로 Chrome 띄우고 네이버 로그인 후 다시 시도하세요:", file=sys.stderr)
                print('   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n     --remote-debugging-port=9222 \\\n     --user-data-dir="$HOME/chrome-cdp-profile"', file=sys.stderr)
                sys.exit(1)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        if args.probe_article:
            # club_id 만 빠르게 추출
            _, club_id, _ = await probe_cafe_membership(context, cafe_name)
            if not club_id:
                print("club_id 추출 실패", file=sys.stderr); sys.exit(1)
            await probe_article_dump(context, club_id, args.probe_article)
            return

        if not args.boards:
            print("❌ --boards 필수 (예: --boards 59,135,94)", file=sys.stderr); sys.exit(1)
        menuids = [int(x.strip()) for x in args.boards.split(",") if x.strip()]

        if args.probe:
            await run_probe_only(context, cafe_name, menuids)
            return

        await run_scrape(context, cafe_name, menuids, out_dir, args.days, args.limit, args.reset)


if __name__ == "__main__":
    asyncio.run(main())
