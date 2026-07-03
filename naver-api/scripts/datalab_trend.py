#!/usr/bin/env python3
"""Standalone Naver DataLab search-trend fetcher — no project, no pip deps.

Calls https://openapi.naver.com/v1/datalab/search and prints relative search
popularity (0-100 ratio) over time for one or more keyword groups.

Credentials: NAVER_DATALAB_CLIENT_ID / NAVER_DATALAB_CLIENT_SECRET env vars.
Register a free app at https://developers.naver.com/apps/ with the 데이터랩(검색어트렌드)
API enabled to get a client id/secret.

Examples
  # one group, last 12 months (monthly)
  python datalab_trend.py 한글 훈민정음

  # named groups, weekly, last 26 weeks
  python datalab_trend.py --group "아이폰:아이폰,iphone" --group "갤럭시:갤럭시,galaxy" \
      --unit week --weeks 26

  # explicit dates + mobile only + save JSON
  python datalab_trend.py --group "다이어트:다이어트,식단" \
      --start 2024-01-01 --end 2024-12-31 --unit month --device mo --out trend.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ENDPOINT = "https://openapi.naver.com/v1/datalab/search"

def creds() -> tuple[str, str]:
    cid = os.environ.get("NAVER_DATALAB_CLIENT_ID")
    secret = os.environ.get("NAVER_DATALAB_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit(
            "Missing credentials. Set NAVER_DATALAB_CLIENT_ID / NAVER_DATALAB_CLIENT_SECRET.\n"
            "Register a free app at https://developers.naver.com/apps/ with the\n"
            "데이터랩(검색어트렌드) API enabled."
        )
    return cid, secret


def default_range(unit: str, weeks: int, months: int) -> tuple[str, str]:
    end = date.today()
    if unit == "week":
        start = end - timedelta(weeks=weeks)
    elif unit == "date":
        start = end - timedelta(days=max(weeks, 4) * 7)
    else:  # month
        m = end.month - months
        y = end.year + (m - 1) // 12
        start = date(y, (m - 1) % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def parse_groups(args) -> list[dict]:
    groups: list[dict] = []
    for spec in args.group or []:
        if ":" in spec:
            name, kws = spec.split(":", 1)
        else:
            name, kws = spec, spec
        keywords = [k.strip() for k in kws.split(",") if k.strip()]
        if keywords:
            groups.append({"groupName": name.strip() or keywords[0], "keywords": keywords[:20]})
    if args.keywords:  # bare positional keywords => single group
        groups.append({"groupName": args.keywords[0], "keywords": args.keywords[:20]})
    return groups[:5]  # DataLab allows max 5 groups


def fetch(payload: dict) -> dict:
    cid, csecret = creds()
    req = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Naver-Client-Id": cid,
            "X-Naver-Client-Secret": csecret,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.stderr.write(f"HTTP {e.code} from DataLab API:\n{body}\n")
        if e.code == 401:
            sys.stderr.write(
                "\n401 = the Client ID/Secret are rejected. Check that the app on "
                "developers.naver.com has the '데이터랩(검색어트렌드)' API added, or override "
                "with NAVER_DATALAB_CLIENT_ID / NAVER_DATALAB_CLIENT_SECRET.\n"
            )
        sys.exit(1)
    except URLError as e:
        sys.stderr.write(f"Network error reaching DataLab API: {e.reason}\n")
        sys.exit(1)


def render(data: dict) -> str:
    lines = [f"# DataLab search trend  {data['startDate']} → {data['endDate']}  ({data['timeUnit']})", ""]
    for res in data.get("results", []):
        lines.append(f"== {res['title']}  [{', '.join(res['keywords'])}] ==")
        peak = max((p["ratio"] for p in res["data"]), default=0)
        for p in res["data"]:
            bar = "█" * round(p["ratio"] / 5) if peak else ""
            lines.append(f"  {p['period']}  {p['ratio']:6.2f}  {bar}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Naver DataLab search-trend (standalone)")
    ap.add_argument("keywords", nargs="*", help="bare keywords -> one group (named after the first)")
    ap.add_argument("--group", action="append", help='"name:kw1,kw2" (repeatable, max 5 groups)')
    ap.add_argument("--unit", choices=["date", "week", "month"], default="month")
    ap.add_argument("--start", help="YYYY-MM-DD")
    ap.add_argument("--end", help="YYYY-MM-DD")
    ap.add_argument("--weeks", type=int, default=26, help="lookback when --unit week (default 26)")
    ap.add_argument("--months", type=int, default=12, help="lookback when --unit month (default 12)")
    ap.add_argument("--device", choices=["pc", "mo"], help="filter by device")
    ap.add_argument("--gender", choices=["m", "f"], help="filter by gender")
    ap.add_argument("--ages", help="comma age codes 1-11 (e.g. 3,4,5)")
    ap.add_argument("--out", help="also write raw JSON to this path")
    ap.add_argument("--json", action="store_true", help="print raw JSON instead of a table")
    args = ap.parse_args()

    groups = parse_groups(args)
    if not groups:
        ap.error("provide keywords or at least one --group")

    start = args.start
    end = args.end
    if not (start and end):
        ds, de = default_range(args.unit, args.weeks, args.months)
        start = start or ds
        end = end or de

    payload: dict = {"startDate": start, "endDate": end, "timeUnit": args.unit, "keywordGroups": groups}
    if args.device:
        payload["device"] = args.device
    if args.gender:
        payload["gender"] = args.gender
    if args.ages:
        payload["ages"] = [a.strip() for a in args.ages.split(",") if a.strip()]

    data = fetch(payload)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        sys.stderr.write(f"saved JSON -> {args.out}\n")

    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
