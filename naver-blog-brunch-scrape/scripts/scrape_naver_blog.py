#!/usr/bin/env python3
"""네이버 블로그 검색어 batch 스크래퍼.

Open API 키 (환경변수 또는 ~/.naver_api_credentials) 가 있으면 Open API,
없으면 search.naver.com HTML 파싱으로 자동 fallback.

Usage:
  python scrape_naver_blog.py --queries "엑셀,CSV" --days 180 --output-dir raw/naver_blog
  python scrape_naver_blog.py --queries-file queries.txt --days 90
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

UA_PC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Version/14.0 Mobile/15E148 Safari/604.1"
KST = timezone(timedelta(hours=9))

OPEN_API_URL = "https://openapi.naver.com/v1/search/blog.json"
SEARCH_URL = "https://search.naver.com/search.naver"


def load_credentials() -> tuple[str, str] | None:
    """환경변수 → ~/.naver_api_credentials 순으로 탐색."""
    cid = os.environ.get("NAVER_OPEN_API_CLIENT_ID")
    csec = os.environ.get("NAVER_OPEN_API_CLIENT_SECRET")
    if cid and csec:
        return cid, csec
    cred_path = Path.home() / ".naver_api_credentials"
    if cred_path.exists():
        text = cred_path.read_text()
        cid_m = re.search(r"NAVER_OPEN_API_CLIENT_ID\s*=\s*(\S+)", text)
        csec_m = re.search(r"NAVER_OPEN_API_CLIENT_SECRET\s*=\s*(\S+)", text)
        if cid_m and csec_m:
            return cid_m.group(1), csec_m.group(1)
    return None


def strip_html(s: str) -> str:
    if not s: return ""
    s = re.sub(r"</?b>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return s.strip()


def parse_blog_url(url: str) -> tuple[str, str] | None:
    """blog.naver.com URL 에서 (bloggerid, logno) 추출."""
    # https://blog.naver.com/userid/12345 또는
    # https://blog.naver.com/PostView.naver?blogId=userid&logNo=12345
    m = re.search(r"blog\.naver\.com/([^/?]+)/(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"[?&]blogId=([^&]+).*?[?&]logNo=(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    return None


def postview_url(bid: str, lno: str) -> str:
    return f"https://blog.naver.com/PostView.naver?blogId={bid}&logNo={lno}&redirect=Dlog&widgetTypeCall=true"


def fetch_post_body(bid: str, lno: str, sess: requests.Session) -> str:
    """PostView.naver 에서 본문 텍스트 추출. 실패 시 빈 문자열."""
    try:
        r = sess.get(postview_url(bid, lno), headers={"User-Agent": UA_PC, "Referer": "https://search.naver.com/"}, timeout=15)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # 스마트에디터
        container = soup.select_one(".se-main-container") or soup.select_one("#postViewArea") or soup.select_one(".post_ct")
        if not container:
            # 모바일 fallback
            r2 = sess.get(f"https://m.blog.naver.com/{bid}/{lno}", headers={"User-Agent": UA_MOBILE}, timeout=15)
            if r2.status_code == 200:
                soup2 = BeautifulSoup(r2.text, "html.parser")
                container = soup2.select_one(".se-main-container, .post_ct, #viewTypeSelector")
        if not container:
            return ""
        text = container.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:30000]
    except Exception:
        return ""


def write_md(out_dir: Path, source: str, item: dict, body: str = "") -> Path:
    posted = item.get("posted_at_iso", "")
    yyyymm = posted[:7] if posted else "unknown"
    fid = item["id"]
    sub = out_dir / yyyymm
    sub.mkdir(parents=True, exist_ok=True)
    p = sub / f"{fid}.md"
    fm = [
        "---",
        f"source: {source}",
        f"search_q: {item.get('search_q','')}",
        f"url: {item.get('url','')}",
        f"title: {item.get('title','').replace(chr(10),' ')}",
        f"author: {item.get('author','')}",
        f"posted_at: {posted}",
        f"scraped_at: {datetime.now(KST).isoformat()}",
    ]
    if item.get("description"):
        # YAML 안전을 위해 한 줄로
        desc = re.sub(r"\s+", " ", item["description"])[:500]
        fm.append(f"description: {desc}")
    fm.append("---")
    fm.append("")
    fm.append(f"# {item.get('title','')}")
    fm.append("")
    if body.strip():
        fm.append(body)
    elif item.get("description"):
        fm.append(item["description"])
    p.write_text("\n".join(fm), encoding="utf-8")
    return p


def search_open_api(query: str, days: int, cred: tuple[str, str], sess: requests.Session, max_per_query: int = 200) -> list[dict]:
    cid, csec = cred
    cutoff = datetime.now(KST) - timedelta(days=days)
    items, seen = [], set()
    start = 1
    while start <= 1000 and len(items) < max_per_query:
        try:
            r = sess.get(OPEN_API_URL, headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec},
                         params={"query": query, "display": 100, "start": start, "sort": "date"}, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[err open api] {e}", flush=True); break
        results = data.get("items", [])
        if not results: break
        page_min = None
        for it in results:
            link = it.get("link", "")
            parsed = parse_blog_url(link)
            if not parsed: continue
            bid, lno = parsed
            fid = f"{bid}_{lno}"
            if fid in seen: continue
            postdate = it.get("postdate", "")
            try:
                dt = datetime.strptime(postdate, "%Y%m%d").replace(tzinfo=KST)
            except Exception:
                dt = None
            if dt:
                if page_min is None or dt < page_min: page_min = dt
                if dt < cutoff: continue
            seen.add(fid)
            items.append({
                "id": fid,
                "url": link,
                "title": strip_html(it.get("title", "")),
                "author": it.get("bloggername", "") or bid,
                "posted_at_iso": dt.date().isoformat() if dt else postdate,
                "description": strip_html(it.get("description", "")),
                "search_q": query,
                "_bid": bid, "_lno": lno,
            })
            if len(items) >= max_per_query: break
        print(f"[open api] q='{query}' start={start} got={len(results)} kept={len(items)} oldest={page_min}", flush=True)
        if page_min and page_min < cutoff: break
        if len(results) < 100: break
        start += 100
        time.sleep(0.3)
    return items


def search_html(query: str, days: int, sess: requests.Session, max_per_query: int = 200) -> list[dict]:
    """search.naver.com HTML fallback. nso=so:dd,p:6m 같은 기간 필터 적용."""
    nso_period = "1m" if days <= 31 else ("3m" if days <= 92 else ("6m" if days <= 183 else "1y"))
    items, seen = [], set()
    cutoff = datetime.now(KST) - timedelta(days=days)
    page_start = 1
    while page_start <= 1000 and len(items) < max_per_query:
        try:
            r = sess.get(SEARCH_URL, params={"where": "blog", "query": query, "sm": "tab_opt",
                                              "nso": f"so:dd,p:{nso_period}", "start": page_start},
                         headers={"User-Agent": UA_PC}, timeout=15)
            if r.status_code != 200: break
        except Exception as e:
            print(f"[err html] {e}", flush=True); break
        soup = BeautifulSoup(r.text, "html.parser")
        # 검색 결과 블록 — 마크업이 자주 바뀌므로 다양한 selector 시도
        blocks = soup.select(".view_wrap, .total_wrap, .bx") or soup.find_all("a", href=re.compile(r"blog\.naver\.com/"))
        new_count = 0
        for b in blocks:
            link_el = b.select_one("a.title_link, a.api_txt_lines, a[href*='blog.naver.com']") if hasattr(b, "select_one") else b
            if not link_el: continue
            href = link_el.get("href", "")
            parsed = parse_blog_url(href)
            if not parsed: continue
            bid, lno = parsed
            fid = f"{bid}_{lno}"
            if fid in seen: continue
            seen.add(fid)
            title = link_el.get_text(strip=True)
            desc_el = b.select_one(".dsc_txt, .api_txt_lines.dsc_txt_wrap") if hasattr(b, "select_one") else None
            desc = desc_el.get_text(strip=True) if desc_el else ""
            date_el = b.select_one(".sub_time, .sub_txt") if hasattr(b, "select_one") else None
            date_text = date_el.get_text(strip=True) if date_el else ""
            items.append({
                "id": fid, "url": f"https://blog.naver.com/{bid}/{lno}",
                "title": title, "author": bid,
                "posted_at_iso": date_text,  # "2026.01.15." 형태 그대로 저장
                "description": desc, "search_q": query,
                "_bid": bid, "_lno": lno,
            })
            new_count += 1
            if len(items) >= max_per_query: break
        print(f"[html] q='{query}' start={page_start} new={new_count} total={len(items)}", flush=True)
        if new_count == 0: break
        page_start += 30
        time.sleep(0.4)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", help="쉼표 분리 검색어 (예: '엑셀,CSV,VBA')")
    ap.add_argument("--queries-file", help="검색어 파일 (한 줄당 하나)")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--output-dir", default="raw/naver_blog")
    ap.add_argument("--max-per-query", type=int, default=200)
    ap.add_argument("--no-body", action="store_true", help="본문 fetch 생략 (메타만 저장)")
    ap.add_argument("--force-html", action="store_true", help="Open API 키 무시하고 HTML 만 사용")
    args = ap.parse_args()

    if args.queries:
        queries = [q.strip() for q in args.queries.split(",") if q.strip()]
    elif args.queries_file:
        queries = [l.strip() for l in Path(args.queries_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    else:
        ap.error("--queries 또는 --queries-file 필수")

    cred = None if args.force_html else load_credentials()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers["User-Agent"] = UA_PC

    mode = "open_api" if cred else "html"
    print(f"[mode] {mode}, queries={len(queries)}, days={args.days}, output={out_dir}", flush=True)

    seen_global, total = set(), 0
    for q in queries:
        items = search_open_api(q, args.days, cred, sess, args.max_per_query) if cred else search_html(q, args.days, sess, args.max_per_query)
        for it in items:
            if it["id"] in seen_global: continue
            seen_global.add(it["id"])
            body = ""
            if not args.no_body and it.get("_bid") and it.get("_lno"):
                body = fetch_post_body(it["_bid"], it["_lno"], sess)
                time.sleep(0.3)
            write_md(out_dir, "naver_blog", it, body)
            total += 1
            if total % 25 == 0:
                print(f"  [progress] saved {total}", flush=True)
    print(f"[done] saved {total} posts → {out_dir}", flush=True)


if __name__ == "__main__":
    main()
