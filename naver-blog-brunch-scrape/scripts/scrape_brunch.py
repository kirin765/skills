#!/usr/bin/env python3
"""브런치 검색어 batch 스크래퍼.

공식 검색 응용프로그램 인터페이스 사용 (인증 불필요):
  https://api.brunch.co.kr/v1/search/article?q={query}&page={n}&pageSize=20

본문 직접 fetch 는 카카오 자동 로그인 redirect 로 차단됨.
대신 검색 응답의 `contentSummary` (220자 발췌) 를 본문 자리에 저장.

Usage:
  python scrape_brunch.py --queries "엑셀,CSV" --days 180 --output-dir raw/brunch
"""
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SEARCH_API = "https://api.brunch.co.kr/v1/search/article"
KST = timezone(timedelta(hours=9))


def strip_html(s: str) -> str:
    if not s: return ""
    s = re.sub(r"</?b>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return s.strip()


def write_md(out_dir: Path, item: dict) -> Path:
    posted = item.get("posted_at_iso", "")
    yyyymm = posted[:7] if posted else "unknown"
    fid = item["id"]
    sub = out_dir / yyyymm
    sub.mkdir(parents=True, exist_ok=True)
    p = sub / f"{fid}.md"
    summary = item.get("description", "")
    fm = [
        "---",
        f"source: brunch",
        f"search_q: {item.get('search_q','')}",
        f"url: {item.get('url','')}",
        f"title: {item.get('title','').replace(chr(10),' ')}",
        f"author: {item.get('author','')}",
        f"posted_at: {posted}",
        f"scraped_at: {datetime.now(KST).isoformat()}",
        "---",
        "",
        f"# {item.get('title','')}",
        "",
        summary or "(본문 없음 — 카카오 로그인 필요. 검색 응용프로그램 인터페이스에서 본문 발췌 미제공)",
    ]
    p.write_text("\n".join(fm), encoding="utf-8")
    return p


def search(q: str, days: int, sess: requests.Session, max_per_query: int = 200) -> list[dict]:
    cutoff = datetime.now(KST) - timedelta(days=days)
    items, seen = [], set()
    for page in range(1, 200):
        if len(items) >= max_per_query: break
        try:
            r = sess.get(SEARCH_API, params={"q": q, "page": page, "pageSize": 20,
                                              "highlighter": "y", "escape": "y", "sort": "score"}, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[err] q='{q}' p{page} {e}", flush=True); break
        articles = data.get("data", []) if isinstance(data.get("data"), list) else None
        if articles is None:
            # data 가 dict 인 경우 articleList 또는 article_list 찾기
            d = data.get("data", {})
            articles = d.get("articleList") or d.get("article_list") or []
        if not articles:
            # 다른 위치도 시도
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if isinstance(v, list) and v and isinstance(v[0], dict) and ("articleNo" in v[0] or "no" in v[0]):
                            return v
                        r = walk(v)
                        if r: return r
                elif isinstance(o, list):
                    for v in o:
                        r = walk(v)
                        if r: return r
            articles = walk(data) or []
        if not articles:
            print(f"[empty] q='{q}' p{page}", flush=True); break
        page_min = None
        new_count = 0
        for a in articles:
            aid = str(a.get("articleNo") or a.get("no") or a.get("id") or "")
            uid = a.get("userId") or a.get("user_id") or (a.get("user") or {}).get("id") or ""
            if not aid or not uid: continue
            fid = f"{uid}_{aid}"
            if fid in seen: continue
            pt = a.get("publishTime") or a.get("publish_time") or a.get("createTime") or 0
            dt = None
            if pt:
                try:
                    pt = int(pt)
                    dt = datetime.fromtimestamp(pt/1000 if pt > 1e12 else pt, KST)
                except Exception:
                    dt = None
            if dt:
                if page_min is None or dt < page_min: page_min = dt
                if dt < cutoff: continue
            seen.add(fid)
            items.append({
                "id": fid,
                "url": f"https://brunch.co.kr/@{uid}/{aid}",
                "title": strip_html(a.get("title", "")),
                "author": a.get("userName") or uid,
                "posted_at_iso": dt.date().isoformat() if dt else "",
                "description": strip_html(a.get("contentSummary", "")),
                "search_q": q,
            })
            new_count += 1
            if len(items) >= max_per_query: break
        print(f"[brunch] q='{q}' p{page} got={len(articles)} new={new_count} total={len(items)} oldest={page_min}", flush=True)
        if page_min and page_min < cutoff: break
        if len(articles) < 20: break
        time.sleep(0.4)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", help="쉼표 분리 검색어")
    ap.add_argument("--queries-file", help="검색어 파일 (한 줄당 하나)")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--output-dir", default="raw/brunch")
    ap.add_argument("--max-per-query", type=int, default=200)
    args = ap.parse_args()

    if args.queries:
        queries = [q.strip() for q in args.queries.split(",") if q.strip()]
    elif args.queries_file:
        queries = [l.strip() for l in Path(args.queries_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    else:
        ap.error("--queries 또는 --queries-file 필수")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Referer": "https://brunch.co.kr/", "Origin": "https://brunch.co.kr"})

    print(f"[brunch] queries={len(queries)}, days={args.days}, output={out_dir}", flush=True)

    seen_global, total = set(), 0
    for q in queries:
        items = search(q, args.days, sess, args.max_per_query)
        for it in items:
            if it["id"] in seen_global: continue
            seen_global.add(it["id"])
            write_md(out_dir, it)
            total += 1
    print(f"[done] saved {total} posts → {out_dir}", flush=True)


if __name__ == "__main__":
    main()
