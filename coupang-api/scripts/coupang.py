#!/usr/bin/env python3
"""Coupang Open API client — 온누리문방구 (vendorId A01569984).

Per-request HMAC-SHA256 (CEA) signing. No token, no extra deps (stdlib only),
so the system python is fine — no venv needed.

  coupang.py GET  <path> [--query k=v ...]
  coupang.py POST <path> [--body '<json>']
  coupang.py PUT  <path> [--body '<json>']
  coupang.py DELETE <path> [--body '<json>']
  coupang.py sign GET <path> [--query ...]   # debug: print the signed message + headers

<path> is everything after the host, e.g.
  /v2/providers/seller_api/apps/api/v1/marketplace/seller-products
A query string may be embedded in <path> ("?a=1&b=2") or passed via --query;
both are folded into one query string that is signed exactly as sent.
{vendorId} in a path is substituted with the configured vendor id.
Prints the response JSON; exit 0 on 2xx, else 1.
"""
import argparse
import gzip
import hashlib
import hmac
import json
import os
import sys
import time
import zlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST = "https://api-gateway.coupang.com"
ENV_FILE = Path.home() / ".coupang.env"


def load_creds():
    access = os.environ.get("COUPANG_ACCESS_KEY")
    secret = os.environ.get("COUPANG_SECRET_KEY")
    vendor = os.environ.get("COUPANG_VENDOR_ID")
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k == "COUPANG_ACCESS_KEY" and not access:
                access = v
            elif k == "COUPANG_SECRET_KEY" and not secret:
                secret = v
            elif k == "COUPANG_VENDOR_ID" and not vendor:
                vendor = v
    if not access or not secret:
        sys.exit(f"missing creds: set COUPANG_ACCESS_KEY/SECRET in {ENV_FILE}")
    return access, secret, vendor


def build_query(path, extra):
    """Split a query off <path>, fold in --query pairs, return (path, query_str)."""
    if "?" in path:
        path, embedded = path.split("?", 1)
    else:
        embedded = ""
    parts = [embedded] if embedded else []
    if extra:
        parts.append(urllib.parse.urlencode([tuple(kv.split("=", 1)) for kv in extra]))
    return path, "&".join(p for p in parts if p)


def sign(method, path, query, access, secret):
    # CEA: message = signedDate + method + path + query (query without '?').
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = signed_date + method + path + query
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    auth = (f"CEA algorithm=HmacSHA256, access-key={access}, "
            f"signed-date={signed_date}, signature={signature}")
    return auth, message


def request(method, path, query, body, access, secret):
    auth, _ = sign(method, path, query, access, secret)
    url = HOST + path + (("?" + query) if query else "")
    headers = {"Authorization": auth, "Content-Type": "application/json;charset=UTF-8",
               "Accept": "application/json"}
    data = None
    if body is not None:
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, _decode(r.read(), r.headers.get("Content-Encoding"))
    except urllib.error.HTTPError as e:
        return e.code, _decode(e.read(), e.headers.get("Content-Encoding"))


def _decode(body, encoding):
    if encoding == "gzip":
        body = gzip.decompress(body)
    elif encoding == "deflate":
        body = zlib.decompress(body)
    return body.decode(errors="replace")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("method", help="GET | POST | PUT | DELETE | sign")
    p.add_argument("path", nargs="?", help="API path after the host")
    p.add_argument("--query", nargs="*", default=[], help="k=v pairs, appended to the query string")
    p.add_argument("--body", help="JSON string for the request body")
    a = p.parse_args()

    access, secret, vendor = load_creds()

    method = a.method.upper()
    debug = method == "SIGN"
    if debug:
        method = (a.path or "GET").upper()
        a.path = a.query.pop(0) if a.query else None
    if not a.path:
        sys.exit("path required")
    path = a.path.replace("{vendorId}", vendor or "{vendorId}")
    path, query = build_query(path, a.query)

    if debug:
        auth, message = sign(method, path, query, access, secret)
        print("message-to-sign:\n" + message + "\n\nAuthorization:\n" + auth)
        print("\nURL:\n" + HOST + path + (("?" + query) if query else ""))
        return

    status, raw = request(method, path, query, a.body, access, secret)
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(raw)
    sys.exit(0 if 200 <= status < 300 else 1)


if __name__ == "__main__":
    main()
