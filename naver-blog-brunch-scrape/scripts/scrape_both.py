#!/usr/bin/env python3
"""네이버 블로그 + 브런치 두 채널 batch 수집 wrapper.

Usage:
  python scrape_both.py --queries "엑셀,CSV" --days 180 --output-dir raw
  → raw/naver_blog/YYYY-MM/{id}.md + raw/brunch/YYYY-MM/{id}.md
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent


def run(script: str, args: list[str]) -> int:
    cmd = [sys.executable, str(HERE / script), *args]
    print(f"\n>>> {' '.join(cmd)}\n", flush=True)
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", help="쉼표 분리 검색어")
    ap.add_argument("--queries-file", help="검색어 파일")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--output-dir", default="raw")
    ap.add_argument("--max-per-query", type=int, default=200)
    ap.add_argument("--source", default="both", choices=["both", "naver_blog", "brunch"])
    ap.add_argument("--no-body", action="store_true", help="네이버 블로그 본문 fetch 생략")
    args = ap.parse_args()

    if not args.queries and not args.queries_file:
        ap.error("--queries 또는 --queries-file 필수")

    base = Path(args.output_dir)
    common = ["--days", str(args.days), "--max-per-query", str(args.max_per_query)]
    if args.queries: common += ["--queries", args.queries]
    if args.queries_file: common += ["--queries-file", args.queries_file]

    rc = 0
    if args.source in ("both", "naver_blog"):
        nb_args = common + ["--output-dir", str(base / "naver_blog")]
        if args.no_body: nb_args.append("--no-body")
        rc |= run("scrape_naver_blog.py", nb_args)
    if args.source in ("both", "brunch"):
        br_args = common + ["--output-dir", str(base / "brunch")]
        rc |= run("scrape_brunch.py", br_args)

    print(f"\n[scrape_both done] exit code: {rc}", flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
