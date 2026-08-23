#!/usr/bin/env python3
"""ASOMobile API client — handles the two-step async (ticket) flow for any endpoint.

Every ASOMobile data endpoint works the same way:
  1. Request:  GET/POST /{path}?params   -> {"code":201,"data":{"ticket_id":N}}
  2. Result:   GET /{path}/result?ticket_id=N  -> {"code":200,"data":{...}}  (once computed)

This wrapper does both: fires the request, then polls the result until the data is
ready (the computation is async, so the first poll is often "not ready"). You give it
the request path + query; it derives the result path automatically.

Auth: Bearer token from ASOMOBILE_TOKEN env, else the baked-in default.
Usage is metered — each request costs account tokens (see app.asomobile.net/api-dashboard).

Examples
  # keyword research (search volume/traffic, competition, KEI, suggestions, top apps)
  python asomobile.py "/keyword-check/?platform=ANDROID&country=US&keyword=mini golf"
  # an app's tracked keywords (iOS)
  python asomobile.py "/app-keywords/?app_id=id284882215&platform=IOS&ios_device=IPHONE&country=US"
  # competitors of an app (Android)
  python asomobile.py "/apps/competitors/?app_id=com.kiwankim.tapgame&platform=ANDROID&country=US"
  # a POST endpoint with a body
  python asomobile.py /keyword-suggest --method POST --data '{"keyword":"golf","country":"US","platform":"ANDROID"}'
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

BASE = "https://app.asomobile.net/asomobile-public-api"
DEFAULT_TOKEN = "PASTE_ASOMOBILE_TOKEN_HERE"


def token() -> str:
    return os.environ.get("ASOMOBILE_TOKEN", DEFAULT_TOKEN)


def call(path: str, method: str, data: str | None):
    raw_path = path if path.startswith("/") else "/" + path
    url = BASE + quote(raw_path, safe="/?&=:@%+,;")  # encode spaces etc., keep URL structure
    body = data.encode("utf-8") if data else None
    headers = {"Authorization": "Bearer " + token(), "Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}
    except URLError as e:
        sys.stderr.write(f"Network error reaching ASOMobile: {e.reason}\n")
        sys.exit(1)


def result_path(request_path: str) -> str:
    base = request_path.split("?", 1)[0].rstrip("/")
    return base + "/result"


def explain_and_exit(status: int, payload: dict):
    code = payload.get("code", status)
    msg = payload.get("message", payload.get("raw", ""))
    sys.stderr.write(f"ASOMobile error {code}: {msg}\n")
    if code == 401:
        sys.stderr.write("401 = token invalid. Check ASOMOBILE_TOKEN / the baked default.\n")
    elif code == 403 and "limit" in str(msg).lower():
        sys.stderr.write(
            "403 'Request limit reached' = the account's metered token quota is used up. "
            "Check or top up at app.asomobile.net/api-dashboard; quota may also reset on a cycle.\n"
        )
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="ASOMobile async API client")
    ap.add_argument("path", help="request endpoint path + query, e.g. /keyword-check/?platform=ANDROID&country=US&keyword=golf")
    ap.add_argument("--method", default="GET", help="HTTP method for the request step (GET or POST)")
    ap.add_argument("--data", help="JSON body for POST endpoints (keyword-suggest, world-wide-check, ...)")
    ap.add_argument("--timeout", type=int, default=90, help="max seconds to wait for the async result")
    ap.add_argument("--interval", type=float, default=3.0, help="seconds between result polls")
    ap.add_argument("--out", help="write the result data JSON to this path")
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()

    # 1. fire the request -> ticket_id
    status, payload = call(args.path, args.method, args.data)
    if status >= 400 or payload.get("code", 200) >= 400:
        explain_and_exit(status, payload)
    ticket = (payload.get("data") or {}).get("ticket_id")
    if ticket is None:
        sys.stderr.write(f"No ticket_id in response: {json.dumps(payload)[:300]}\n")
        sys.exit(1)

    # 2. poll the result until the async computation is ready
    rpath = result_path(args.path)
    deadline = time.time() + args.timeout
    data = None
    while time.time() < deadline:
        time.sleep(args.interval)
        st, pl = call(f"{rpath}?ticket_id={ticket}", "GET", None)
        code = pl.get("code", st)
        if code == 403 and "limit" in str(pl.get("message", "")).lower():
            explain_and_exit(st, pl)
        if st == 200 and code == 200 and pl.get("data"):
            data = pl["data"]
            break
        # otherwise still computing — keep polling
    if data is None:
        sys.stderr.write(f"Result not ready within {args.timeout}s (ticket {ticket}). Re-poll later: {rpath}?ticket_id={ticket}\n")
        sys.exit(1)

    out = json.dumps(data, ensure_ascii=False, indent=None if args.compact else 2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        sys.stderr.write(f"saved -> {args.out}\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
