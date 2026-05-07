#!/usr/bin/env python3
"""
필터 통과한 글의 본문+댓글 정밀 수집.

입력: raw/{gall}_meta.jsonl
필터: comment_count >= 6 OR recommend >= 2
출력: raw/{gall}_full.jsonl (메타 + body + comments[])

모바일(m.dcinside.com) 단일 요청으로 본문+댓글 inline 수집.

Usage:
  python fetch_detail.py --gall sajang
  python fetch_detail.py --gall smartstore --min-comments 6 --min-recommend 2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"
M_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


M_PATHS = {"mgallery": "board", "gallery": "board", "mini": "mini"}


def fetch_mobile(gall: str, post_num: str, session: requests.Session, kind: str = "mgallery") -> str | None:
    seg = M_PATHS.get(kind, "board")
    url = f"https://m.dcinside.com/{seg}/{gall}/{post_num}"
    for attempt in range(3):
        try:
            r = session.get(url, headers={"User-Agent": M_UA}, timeout=20)
            if r.status_code == 200:
                return r.text
            if r.status_code in (403, 429):
                time.sleep(2 ** attempt)
                continue
            return None
        except requests.RequestException as e:
            print(f"  retry {attempt+1}/3 {post_num}: {e}", file=sys.stderr)
            time.sleep(1 + attempt)
    return None


def parse_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    body_el = soup.select_one("div.thum-txtin")
    body = body_el.get_text("\n", strip=True) if body_el else ""

    comments: list[dict] = []
    lst = soup.select_one(".all-comment-lst")
    if lst:
        for li in lst.select("li"):
            cls = " ".join(li.get("class", []))
            if "comment" not in cls:
                continue
            nick_btn = li.select_one("button.nick")
            nick = ""
            if nick_btn:
                nick = nick_btn.get_text(" ", strip=True)
                num = nick_btn.select_one(".nicknum")
                if num:
                    nick = nick.replace(num.get_text(strip=True), "").strip()
            ip_el = li.select_one(".blockCommentIp, .ip")
            ip = ip_el.get_text(strip=True).strip("()") if ip_el else ""
            txt_el = li.select_one("p.txt")
            text = txt_el.get_text("\n", strip=True) if txt_el else ""
            date_el = li.select_one(".date")
            date = date_el.get_text(strip=True) if date_el else ""
            kind = "reply" if "comment-add" in cls else "comment"
            if not text:
                continue
            comments.append({
                "nick": nick,
                "ip": ip,
                "text": text,
                "date": date,
                "kind": kind,
            })
    return {"body": body, "comments": comments}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gall", required=True)
    ap.add_argument("--kind", default="mgallery", choices=list(M_PATHS.keys()))
    ap.add_argument("--min-comments", type=int, default=6)
    ap.add_argument("--min-recommend", type=int, default=2)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=None, help="처음 N건만 (테스트용)")
    args = ap.parse_args()

    meta_path = RAW_DIR / f"{args.gall}_meta.jsonl"
    if not meta_path.exists():
        print(f"meta 파일 없음: {meta_path}", file=sys.stderr)
        sys.exit(1)

    rows = [json.loads(l) for l in meta_path.open()]
    targets = [r for r in rows if r["comment_count"] >= args.min_comments or r["recommend"] >= args.min_recommend]
    if args.limit:
        targets = targets[: args.limit]
    print(f"[{args.gall}] 대상 {len(targets)}건 / 전체 {len(rows)}건")

    out_path = RAW_DIR / f"{args.gall}_full.jsonl"
    session = requests.Session()
    n_ok = 0
    n_fail = 0
    with out_path.open("w") as f:
        for i, meta in enumerate(targets, 1):
            html = fetch_mobile(args.gall, meta["post_num"], session, args.kind)
            if html is None:
                n_fail += 1
                print(f"  [{i}/{len(targets)}] fail {meta['post_num']}", file=sys.stderr)
                time.sleep(args.sleep)
                continue
            detail = parse_detail(html)
            rec = {**meta, **detail}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_ok += 1
            if i % 50 == 0:
                print(f"  [{i}/{len(targets)}] ok={n_ok} fail={n_fail}", file=sys.stderr)
            time.sleep(args.sleep)
    print(f"[{args.gall}] 저장 완료: {out_path} (ok={n_ok}, fail={n_fail})")


if __name__ == "__main__":
    main()
