#!/usr/bin/env python3
"""뽐뿌·클리앙 공개 게시판 스크래퍼.

두 사이트 모두 로그인 불필요 (공개 HTML). CDP 불필요.
- clien: 목록/검색 모두 서버사이드 지원. 댓글은 본문 HTML에 포함.
- ppomppu: 검색 endpoint 는 봇 차단(403) → 목록 페이지네이션 + 로컬 키워드 필터로 대체.
  세션 쿠키 없거나 요청 간격이 짧으면 간헐 403 → Session + delay + 1회 재시도.
  댓글은 AJAX 로딩이라 v1 미수집 (comment_count 메타만 저장).

출력: {out}/{site}/{label}/{YYYY-MM}/{id}.md (frontmatter + 본문)
중복 방지: {out}/INDEX_{site}_{label}.json 에 수집한 id 기록.
"""

import argparse
import html as html_mod
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CLIEN = "https://www.clien.net"
PPOMPPU = "https://www.ppomppu.co.kr"


def log(msg):
    print(msg, flush=True)


def make_session(site):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    if site == "ppomppu":
        # 첫 방문 쿠키가 없으면 zboard 가 간헐적으로 403 을 낸다
        try:
            s.get(PPOMPPU + "/", timeout=15)
        except requests.RequestException:
            pass
    return s


def fetch(sess, url, site, delay, retries=2):
    time.sleep(delay)
    for attempt in range(retries + 1):
        try:
            r = sess.get(url, timeout=20)
        except requests.RequestException as e:
            if attempt == retries:
                raise
            log(f"  ⚠ {e.__class__.__name__} — {10 * (attempt + 1)}s 후 재시도")
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 200:
            # zboard HTML 은 euc-kr 인데 헤더에 charset 이 없다. RSS 는 UTF-8 선언됨.
            if site == "ppomppu" and "utf-8" not in r.headers.get("Content-Type", "").lower():
                r.encoding = "cp949"
            return r
        if r.status_code == 403 and attempt < retries:
            log(f"  ⚠ 403 — {15 * (attempt + 1)}s 대기 후 재시도")
            time.sleep(15 * (attempt + 1))
            continue
        r.raise_for_status()
    raise RuntimeError(f"unreachable: {url}")


def clean_text(el):
    for bad in el.select("script, style"):
        bad.decompose()
    text = el.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


# ---------------- clien ----------------

def clien_list_page(sess, board, page, delay):
    url = f"{CLIEN}/service/board/{board}?po={page}&od=T31"
    soup = BeautifulSoup(fetch(sess, url, "clien", delay).text, "html.parser")
    posts = []
    for row in soup.select('[data-role="list-row"]'):
        pid = row.get("data-board-sn")
        title_el = row.select_one("span.subject_fixed")
        if not pid or not title_el:
            continue
        ts = row.select_one("span.timestamp")
        nick = row.select_one("span.nickname")
        hit = row.select_one("span.hit")
        posts.append({
            "id": pid,
            "title": title_el.get_text(strip=True),
            "nick": nick.get_text(strip=True) if nick else "",
            "posted_at": ts.get_text(strip=True) if ts else "",
            "views": hit.get_text(strip=True) if hit else "",
            "comment_count": int(row.get("data-comment-count") or 0),
            "url": f"{CLIEN}/service/board/{board}/{pid}",
            "board": board,
        })
    return posts


def clien_search_page(sess, query, page, delay, board=""):
    url = (f"{CLIEN}/service/search?q={requests.utils.quote(query)}"
           f"&sort=recency&p={page}&boardCd={board}&isBoard={'true' if board else 'false'}")
    soup = BeautifulSoup(fetch(sess, url, "clien", delay).text, "html.parser")
    posts = []
    for item in soup.select(".list_item"):
        a = item.select_one("a.subject_fixed, a.list_subject")
        if not a or not a.get("href"):
            continue
        m = re.search(r"/service/board/([^/]+)/(\d+)", a["href"])
        if not m:
            continue
        ts = item.select_one("span.timestamp")
        nick = item.select_one("span.nickname")
        posts.append({
            "id": m.group(2),
            "title": a.get_text(strip=True),
            "nick": nick.get_text(strip=True) if nick else "",
            "posted_at": ts.get_text(strip=True) if ts else "",
            "views": "",
            "comment_count": 0,
            "url": f"{CLIEN}/service/board/{m.group(1)}/{m.group(2)}",
            "board": m.group(1),
        })
    return posts


def clien_article(sess, post, delay):
    soup = BeautifulSoup(fetch(sess, post["url"], "clien", delay).text, "html.parser")
    body_el = soup.select_one("div.post_article")
    body = clean_text(body_el) if body_el else ""
    comments = []
    for row in soup.select("div.comment_row"):
        cv = row.select_one("div.comment_view")
        cn = row.select_one("span.nickname")
        if cv:
            comments.append({
                "nick": cn.get_text(strip=True) if cn else "",
                "text": clean_text(cv),
            })
    return body, comments


# ---------------- ppomppu ----------------

def ppomppu_list_page(sess, board, page, delay):
    url = f"{PPOMPPU}/zboard/zboard.php?id={board}&page={page}"
    soup = BeautifulSoup(fetch(sess, url, "ppomppu", delay).text, "html.parser")
    posts = []
    for row in soup.select("tr.baseList"):
        a = row.select_one("a.baseList-title")
        numb = row.select_one("td.baseList-numb")
        if not a or not numb or not numb.get_text(strip=True).isdigit():
            continue
        pid = numb.get_text(strip=True)
        nick = row.select_one(".baseList-name")
        time_td = row.select_one("time.baseList-time, td.baseList-time")
        cmt = row.select_one("span.baseList-c")
        posts.append({
            "id": pid,
            "title": a.get_text(strip=True),
            "nick": nick.get_text(strip=True) if nick else "",
            "posted_at": time_td.get_text(strip=True) if time_td else "",
            "views": "",
            "comment_count": int(cmt.get_text(strip=True)) if cmt and cmt.get_text(strip=True).isdigit() else 0,
            "url": f"{PPOMPPU}/zboard/view.php?id={board}&no={pid}",
            "board": board,
        })
    return posts


def ppomppu_article(sess, post, delay):
    soup = BeautifulSoup(fetch(sess, post["url"], "ppomppu", delay).text, "html.parser")
    # 본문은 td.han 여러 개 중 가장 긴 것 (구형 zboard 구조)
    body = ""
    for td in soup.select("td.han"):
        t = clean_text(td)
        if len(t) > len(body):
            body = t
    info = soup.select_one("ul.topTitle-mainbox")
    if info:
        m = re.search(r"등록일\s*([\d\-: ]+)", info.get_text(" ", strip=True))
        if m:
            post["posted_at"] = m.group(1).strip()
        v = re.search(r"조회수\s*(\d+)", info.get_text(" ", strip=True))
        if v:
            post["views"] = v.group(1)
    cmt = soup.select_one("h1 span#comment")
    if cmt and cmt.get_text(strip=True).isdigit():
        post["comment_count"] = int(cmt.get_text(strip=True))
    return body, []  # 댓글은 AJAX — v1 미수집


def ppomppu_rss(sess, board, delay):
    url = f"{PPOMPPU}/rss.php?id={board}"
    soup = BeautifulSoup(fetch(sess, url, "ppomppu", delay).text, "xml")
    posts = []
    for item in soup.select("item"):
        link = item.link.get_text(strip=True) if item.link else ""
        m = re.search(r"no=(\d+)", link)
        if not m:
            continue
        posts.append({
            "id": m.group(1),
            "title": html_mod.unescape(item.title.get_text(strip=True)) if item.title else "",
            "nick": item.author.get_text(strip=True) if item.author else "",
            "posted_at": item.pubDate.get_text(strip=True) if item.pubDate else "",
            "views": "",
            "comment_count": 0,
            "url": f"{PPOMPPU}/zboard/view.php?id={board}&no={m.group(1)}",
            "board": board,
            "rss_description": html_mod.unescape(item.description.get_text(strip=True)) if item.description else "",
        })
    return posts


# ---------------- 공통 파이프라인 ----------------

def parse_posted_at(s):
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    if re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", s):  # 오늘 글 (뽐뿌 목록)
        now = datetime.now()
        parts = [int(x) for x in s.split(":")]
        return now.replace(hour=parts[0], minute=parts[1], second=0, microsecond=0)
    m = re.fullmatch(r"(\d{2})[./-](\d{2})", s)  # 이전 글 MM/DD
    if m:
        now = datetime.now()
        d = datetime(now.year, int(m.group(1)), int(m.group(2)))
        return d if d <= now else d.replace(year=now.year - 1)
    return None


def save_post(out_dir, site, label, post, body, comments):
    dt = parse_posted_at(post.get("posted_at", ""))
    month = dt.strftime("%Y-%m") if dt else "unknown"
    d = out_dir / site / label / month
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{post['id']}.md"
    fm = [
        "---",
        f"source: {site}",
        f"board: {post['board']}",
        f"article_id: {post['id']}",
        f"url: {post['url']}",
        f"title: {json.dumps(post['title'], ensure_ascii=False)}",
        f"posted_at: {post.get('posted_at', '')}",
        f"scraped_at: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"writer_nick: {json.dumps(post.get('nick', ''), ensure_ascii=False)}",
        f"views: {post.get('views', '')}",
        f"comment_count: {post.get('comment_count', 0)}",
        "---",
        "",
        f"# {post['title']}",
        "",
        body or post.get("rss_description", ""),
    ]
    if comments:
        fm += ["", "## 댓글", ""]
        for c in comments:
            fm.append(f"- **{c['nick']}**: {c['text']}")
    path.write_text("\n".join(fm), encoding="utf-8")
    return path


def load_index(out_dir, site, label):
    p = out_dir / f"INDEX_{site}_{label}.json"
    if p.exists():
        return p, set(json.loads(p.read_text()))
    return p, set()


def keyword_match(post, body, keywords):
    if not keywords:
        return True
    hay = (post["title"] + " " + body).lower()
    return any(k.lower() in hay for k in keywords)


def main():
    ap = argparse.ArgumentParser(description="뽐뿌·클리앙 게시판 스크래퍼")
    ap.add_argument("--site", choices=["clien", "ppomppu"], required=True)
    ap.add_argument("--board", help="게시판 ID (clien: park 등 / ppomppu: freeboard 등)")
    ap.add_argument("--query", help="clien 전용: 서버사이드 검색어")
    ap.add_argument("--rss", action="store_true", help="ppomppu 전용: RSS 로 최신글만")
    ap.add_argument("--pages", type=int, default=3, help="목록 페이지 수 (기본 3)")
    ap.add_argument("--limit", type=int, help="최대 저장 글 수")
    ap.add_argument("--days", type=int, help="N일 이내 글만 (cutoff 도달 시 중단)")
    ap.add_argument("--keyword", help="로컬 필터: 쉼표 구분, 제목+본문 OR 매치")
    ap.add_argument("--no-body", action="store_true", help="본문 fetch 생략 (목록 메타만)")
    ap.add_argument("--out", default="./raw", help="출력 디렉토리 (기본 ./raw)")
    ap.add_argument("--delay", type=float, help="요청 간격 초 (기본 clien 0.8 / ppomppu 1.5)")
    ap.add_argument("--probe", action="store_true", help="접근성 확인만")
    args = ap.parse_args()

    delay = args.delay if args.delay is not None else (1.5 if args.site == "ppomppu" else 0.8)
    keywords = [k.strip() for k in args.keyword.split(",") if k.strip()] if args.keyword else []
    sess = make_session(args.site)

    if args.probe:
        board = args.board or ("park" if args.site == "clien" else "freeboard")
        if args.site == "clien":
            posts = clien_list_page(sess, board, 0, delay)
        else:
            posts = ppomppu_list_page(sess, board, 1, delay)
        log(f"✅ {args.site}/{board}: 목록 1페이지 {len(posts)}건 파싱")
        if posts:
            log(f"   최신: [{posts[0]['posted_at']}] {posts[0]['title'][:40]}")
        return

    if not args.board and not args.query:
        ap.error("--board 또는 --query (clien) 필요")

    label = args.query.replace(" ", "_") if args.query else args.board
    out_dir = Path(args.out)
    index_path, seen = load_index(out_dir, args.site, label)
    cutoff = datetime.now() - timedelta(days=args.days) if args.days else None

    saved = skipped = 0
    stop = False
    page_iter = range(0, args.pages) if args.site == "clien" else range(1, args.pages + 1)

    for page in page_iter:
        if stop:
            break
        if args.site == "clien":
            if args.query:
                posts = clien_search_page(sess, args.query, page, delay, args.board or "")
            else:
                posts = clien_list_page(sess, args.board, page, delay)
        elif args.rss:
            posts = ppomppu_rss(sess, args.board, delay)
            stop = True  # RSS 는 단일 페이지
        else:
            posts = ppomppu_list_page(sess, args.board, page, delay)

        if not posts:
            log(f"page {page}: 글 없음 — 중단")
            break

        for post in posts:
            if post["id"] in seen:
                skipped += 1
                continue
            dt = parse_posted_at(post.get("posted_at", ""))
            if cutoff and dt and dt < cutoff:
                stop = True
                break
            body, comments = "", []
            if not args.no_body:
                try:
                    if args.site == "clien":
                        body, comments = clien_article(sess, post, delay)
                    else:
                        body, comments = ppomppu_article(sess, post, delay)
                except Exception as e:
                    log(f"  ⚠ 본문 실패 {post['id']}: {e}")
            if not keyword_match(post, body, keywords):
                seen.add(post["id"])
                continue
            path = save_post(out_dir, args.site, label, post, body, comments)
            seen.add(post["id"])
            saved += 1
            log(f"  저장 [{post.get('posted_at','')}] {post['title'][:44]} → {path}")
            if args.limit and saved >= args.limit:
                stop = True
                break

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(sorted(seen)))
        log(f"page {page} 완료 — 누적 저장 {saved}, 중복 스킵 {skipped}")

    log(f"\n✅ 완료: 저장 {saved}건, 중복 {skipped}건 → {out_dir}/{args.site}/{label}/")


if __name__ == "__main__":
    main()
