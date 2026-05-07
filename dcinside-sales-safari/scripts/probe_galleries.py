#!/usr/bin/env python3
"""
dcinside 갤러리 후보 발굴 + 페르소나 검증 헬퍼.

검색 키워드로 DC 통합검색에서 후보 ID 수집 → 각 후보의 list 페이지에 접속해
page1 row 수와 갤 제목·샘플 제목을 함께 출력한다. 페르소나 불일치를 사람이
즉시 판단할 수 있게 하는 게 목적이다.

Usage:
  python probe_galleries.py 학원강사 과외 원장
  python probe_galleries.py --extra ptutor instructors gangsajang
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None  # type: ignore

UA = "Mozilla/5.0"
PATHS = ["board/lists", "mgallery/board/lists", "mini/board/lists"]


def search_dc(query: str) -> list[str]:
    """DC 통합검색에서 갤러리 ID 후보를 수집한다."""
    url = f"https://search.dcinside.com/combine/q/{urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[search:{query}] err: {e}", file=sys.stderr)
        return []
    gids = re.findall(r"/(?:mgallery/|mini/|m/)?board/lists/?\?id=([a-z0-9_]+)", html)
    # dcbest, dclottery 제거 (광고)
    return [g for g in dict.fromkeys(gids) if g not in {"dcbest", "dclottery"}]


def probe_gallery(gid: str) -> tuple[str, int, str, list[str]] | None:
    """갤러리 ID로 list 페이지 접근. (path, rows, title, sample_titles[5]) 반환.

    공지글과 dcinside 사이트 전역 인기글은 제외하고 실제 갤 게시글만 추출.
    """
    if BeautifulSoup is None:
        sys.exit("bs4 미설치. `pip install beautifulsoup4 lxml requests`")

    for p in PATHS:
        url = f"https://gall.dcinside.com/{p}/?id={gid}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        rows_iter = soup.select("tr.ub-content.us-post")
        rows = len(rows_iter)
        if rows == 0:
            continue
        title_tag = soup.find("title")
        title = title_tag.get_text().split(" - ")[0][:50] if title_tag else ""
        samples: list[str] = []
        for tr in rows_iter:
            if tr.get("data-type") == "icon_notice":
                continue
            tit_cell = tr.select_one("td.gall_tit")
            if not tit_cell:
                continue
            a = tit_cell.find("a")
            if not a:
                continue
            text = "".join(s for s in a.find_all(string=True) if s.strip())
            text = " ".join(text.split())
            if text:
                samples.append(text[:60])
            if len(samples) >= 5:
                break
        return p, rows, title, samples
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="*", help="검색 키워드 (예: 학원강사 과외)")
    ap.add_argument("--extra", nargs="*", default=[], help="검색 안 거치고 직접 프로빙할 갤 ID")
    ap.add_argument("--min-rows", type=int, default=10, help="page1 최소 row (활성도 필터)")
    args = ap.parse_args()

    candidates: dict[str, set[str]] = {}  # gid -> queries 추적
    for q in args.queries:
        gids = search_dc(q)
        for g in gids[:10]:  # 상위 10개만
            candidates.setdefault(g, set()).add(q)
    for g in args.extra:
        candidates.setdefault(g, set()).add("(직접지정)")

    print(f"=== 후보 {len(candidates)}개 프로빙 (min-rows={args.min_rows}) ===\n")
    results = []
    for gid, qs in candidates.items():
        r = probe_gallery(gid)
        if r and r[1] >= args.min_rows:
            results.append((r[1], gid, r[0], r[2], r[3], qs))

    # row 내림차순
    for rows, gid, path, title, samples, qs in sorted(results, reverse=True):
        print(f"[{rows:3d}] {gid:25s} @ {path:25s} {title}")
        print(f"      검색어: {sorted(qs)}")
        for s in samples:
            print(f"      ─ {s}")
        print()

    print("\n페르소나 검증 체크리스트:")
    print("  1. 제목 샘플이 실제 페르소나(예: 사장/강사)인가, 일반 소비자/팬덤인가?")
    print("  2. 갤 제목이 의도와 맞는가? (예: 'coffee'=커피마니아 ≠ 카페사장)")
    print("  3. 정치/혐오/잡담 비중이 절반 이상이면 제외")
    print("  4. 페이지1 row가 30+면 활성, 10 미만이면 죽은 갤")


if __name__ == "__main__":
    main()
