#!/usr/bin/env python3
"""Appfigures API v2 client — one thin authenticated wrapper for the whole API.

Appfigures has dozens of endpoints with path-based params; rather than wrap each
one, this calls ANY endpoint with Bearer (Personal Access Token) auth and pretty-
prints the JSON. Build the path from the endpoint reference in SKILL.md.

Auth resolves: APPFIGURES_PAT env var first, else the baked-in default below.

Examples
  python appfigures.py /products/search/habit+tracker
  python appfigures.py /products/google_play/com.whatsapp
  python appfigures.py "/reviews?products=29521&stars=1,2&count=20&lang=en"
  python appfigures.py "/reports/ratings?products=29521&start_date=-90&group_by=date"
  python appfigures.py "/ranks/29521/daily/-14/0?countries=US,KR"
  python appfigures.py /data/categories
  python appfigures.py /reviews/REVIEWID/response --method POST --data '{"content":"Thanks!"}'
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://api.appfigures.com/v2"

# Personal Access Token (create at appfigures.com -> account -> API).
DEFAULT_PAT = "PASTE_APPFIGURES_PAT_HERE"


def token() -> str:
    return os.environ.get("APPFIGURES_PAT", DEFAULT_PAT)


def call(path: str, method: str, data: str | None):
    pat = token()
    if not pat or pat == "PASTE_APPFIGURES_PAT_HERE":
        sys.stderr.write(
            "No Appfigures token. Create a Personal Access Token at appfigures.com "
            "(account -> API), then export APPFIGURES_PAT=... or bake it into this script.\n"
        )
        sys.exit(2)

    url = BASE + (path if path.startswith("/") else "/" + path)
    body = data.encode("utf-8") if data else None
    headers = {"Authorization": "Bearer " + pat, "Accept": "application/json", "User-Agent": "appfigures-skill/1.0"}
    if body:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, raw
    except HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        sys.stderr.write(f"HTTP {e.code} from {url}\n{raw[:500]}\n")
        if e.code == 401:
            sys.stderr.write("\n401 = token rejected. Check the PAT is valid / not revoked.\n")
        elif e.code == 403:
            sys.stderr.write("\n403 = the token lacks access to this data, or the resource isn't in your account.\n")
        elif e.code == 429:
            sys.stderr.write("\n429 = rate limited. Wait and retry; don't hammer it.\n")
        sys.exit(1)
    except URLError as e:
        sys.stderr.write(f"Network error reaching Appfigures: {e.reason}\n")
        sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Appfigures API v2 client")
    ap.add_argument("path", help="endpoint path, e.g. /products/search/term or /reviews?products=...")
    ap.add_argument("--method", default="GET", help="HTTP method (default GET)")
    ap.add_argument("--data", help="JSON body for POST/PUT")
    ap.add_argument("--out", help="also write the raw response JSON to this path")
    ap.add_argument("--compact", action="store_true", help="print compact JSON (no indent)")
    args = ap.parse_args()

    status, raw = call(args.path, args.method, args.data)

    try:
        parsed = json.loads(raw)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=None if args.compact else 2)
    except json.JSONDecodeError:
        pretty = raw  # some endpoints (e.g. CSV export) aren't JSON

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(raw)
        sys.stderr.write(f"saved -> {args.out}\n")

    print(pretty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
