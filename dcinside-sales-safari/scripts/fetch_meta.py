#!/usr/bin/env python3
"""
dcinside 마이너 갤러리 list 페이지 메타 스캔.

페이지를 순차로 긁어 각 글의 메타데이터를 JSONL로 저장한다.
- 공지(notice)는 건너뜀
- 12개월 컷오프 도달 시 중단

Usage:
  python fetch_meta.py --gall sajang --months 12
  python fetch_meta.py --gall smartstore --max-pages 5  # 페이지 한도
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
KIND_PATHS = {
    "mgallery": "mgallery",
    "mini": "mini",
    "gallery": "",
}
KST = timezone(timedelta(hours=9))


def list_url(kind: str) -> str:
    seg = KIND_PATHS[kind]
    return f"https://gall.dcinside.com/{seg+'/' if seg else ''}board/lists/"


def view_url(kind: str, gall: str, post_num: str) -> str:
    seg = KIND_PATHS[kind]
    return f"https://gall.dcinside.com/{seg+'/' if seg else ''}board/view/?id={gall}&no={post_num}"


@dataclass
class PostMeta:
    post_num: str
    title: str
    writer_nick: str
    writer_ip: str        # 앞두 옥텟 (유동) — 로그인이면 빈 문자열
    writer_uid: str       # 고정ID — 비로그인이면 빈 문자열
    date_full: str        # "2026-05-02 01:58:02" (KST)
    view: int
    recommend: int
    comment_count: int
    post_type: str        # icon_txt, icon_pic, icon_notice ...
    subject_label: str    # "일반", "공지", 말머리 등
    url: str


def fetch_list_page(gall: str, page: int, session: requests.Session, kind: str) -> str:
    url = list_url(kind)
    r = session.get(
        url,
        params={"id": gall, "page": page},
        headers={"User-Agent": UA, "Referer": f"{url}?id={gall}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.text


def parse_list(html: str, gall: str, kind: str) -> list[PostMeta]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("tr.ub-content.us-post")
    out: list[PostMeta] = []
    for r in rows:
        post_type = r.get("data-type", "")
        if post_type == "icon_notice":
            continue
        post_num = r.get("data-no", "").strip()
        if not post_num:
            continue
        subject_label = (r.select_one("td.gall_subject") or "").get_text(strip=True) if r.select_one("td.gall_subject") else ""
        tit_cell = r.select_one("td.gall_tit")
        if not tit_cell:
            continue
        a = tit_cell.find("a")
        # 제목: a 안의 텍스트에서 icon img 제외
        title_node = a.find(string=True, recursive=False)
        if title_node is None:
            title = a.get_text(" ", strip=True)
        else:
            # a의 모든 텍스트 합치되 reply_numbox 안 텍스트는 제외
            title = "".join(t for t in a.find_all(string=True))
            title = " ".join(title.split())
        # 댓글
        rep = tit_cell.select_one("span.reply_num")
        comment_count = 0
        if rep:
            txt = rep.get_text(strip=True).strip("[]")
            try:
                comment_count = int(txt)
            except ValueError:
                comment_count = 0
        # 작성자
        wcell = r.select_one("td.gall_writer")
        writer_nick = wcell.get("data-nick", "") if wcell else ""
        writer_ip = wcell.get("data-ip", "") if wcell else ""
        writer_uid = wcell.get("data-uid", "") if wcell else ""
        # 날짜
        dcell = r.select_one("td.gall_date")
        date_full = dcell.get("title", "") if dcell else ""
        # 조회/추천
        try:
            view = int((r.select_one("td.gall_count") or "").get_text(strip=True))
        except (ValueError, AttributeError):
            view = 0
        try:
            recommend = int((r.select_one("td.gall_recommend") or "").get_text(strip=True))
        except (ValueError, AttributeError):
            recommend = 0
        url = view_url(kind, gall, post_num)
        out.append(PostMeta(
            post_num=post_num,
            title=title,
            writer_nick=writer_nick,
            writer_ip=writer_ip,
            writer_uid=writer_uid,
            date_full=date_full,
            view=view,
            recommend=recommend,
            comment_count=comment_count,
            post_type=post_type,
            subject_label=subject_label,
            url=url,
        ))
    return out


def parse_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    except ValueError:
        return None


def scan_gallery(gall: str, months: int, max_pages: int | None, sleep: float, kind: str) -> Iterator[PostMeta]:
    session = requests.Session()
    cutoff = datetime.now(tz=KST) - timedelta(days=months * 30)
    page = 1
    seen_post_nums: set[str] = set()
    consecutive_old = 0
    while True:
        if max_pages and page > max_pages:
            print(f"[{gall}] max-pages 도달 (page={page})", file=sys.stderr)
            return
        try:
            html = fetch_list_page(gall, page, session, kind)
        except requests.HTTPError as e:
            print(f"[{gall}] HTTPError page={page}: {e}", file=sys.stderr)
            return
        rows = parse_list(html, gall, kind)
        if not rows:
            print(f"[{gall}] empty page {page} — 종료", file=sys.stderr)
            return
        new_count = 0
        old_in_page = 0
        for m in rows:
            if m.post_num in seen_post_nums:
                continue
            seen_post_nums.add(m.post_num)
            d = parse_date(m.date_full)
            if d and d < cutoff:
                old_in_page += 1
                continue
            new_count += 1
            yield m
        # 12개월 이전 글이 페이지의 절반 이상이면 컷오프 도달로 판단
        if old_in_page >= len(rows) // 2 and old_in_page > 0:
            consecutive_old += 1
            if consecutive_old >= 2:
                print(f"[{gall}] 12개월 컷오프 도달 (page={page})", file=sys.stderr)
                return
        else:
            consecutive_old = 0
        if page % 10 == 0:
            print(f"[{gall}] page {page} 진행중 (수집 {len(seen_post_nums)})", file=sys.stderr)
        page += 1
        time.sleep(sleep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gall", required=True, help="갤러리 ID (예: sajang, smartstore, freel)")
    ap.add_argument("--kind", default="mgallery", choices=list(KIND_PATHS.keys()),
                    help="갤러리 종류: mgallery(마이너) | mini | gallery(일반)")
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args()

    out_path = RAW_DIR / f"{args.gall}_meta.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w") as f:
        for m in scan_gallery(args.gall, args.months, args.max_pages, args.sleep, args.kind):
            f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")
            n += 1
    print(f"[{args.gall}] 저장 완료: {out_path} ({n}건)")


if __name__ == "__main__":
    main()
