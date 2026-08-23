#!/usr/bin/env python3
"""Naver Commerce (SmartStore) API client — type=SELF (own store).

Run with the skill venv: ~/.claude/skills/naver-commerce-api/.venv/bin/python

  ncommerce.py token                 # issue/refresh access token, print it
  ncommerce.py GET  <path> [--query k=v ...]
  ncommerce.py POST <path> [--body '<json>']
  ncommerce.py PUT  <path> [--body '<json>']
  ncommerce.py DELETE <path>

<path> is the API path after the host, e.g. /external/v1/product-orders.
Token is cached at ~/.cache/naver-commerce/token.json and auto-refreshed
on expiry or on a 401 GW.AUTHN gateway error.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import bcrypt

HOST = "https://api.commerce.naver.com"
TOKEN_URL = HOST + "/external/v1/oauth2/token"
ENV_FILE = Path.home() / ".naver-commerce.env"
CACHE = Path.home() / ".cache" / "naver-commerce" / "token.json"


def load_creds():
    cid = os.environ.get("NAVER_COMMERCE_CLIENT_ID")
    sec = os.environ.get("NAVER_COMMERCE_CLIENT_SECRET")
    if cid and sec:
        return cid, sec
    if ENV_FILE.exists():
        env = {}
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
        cid = cid or env.get("NAVER_COMMERCE_CLIENT_ID")
        sec = sec or env.get("NAVER_COMMERCE_CLIENT_SECRET")
    if not cid or not sec:
        sys.exit(f"missing creds: set NAVER_COMMERCE_CLIENT_ID/SECRET or {ENV_FILE}")
    return cid, sec


def sign(client_id, client_secret, timestamp):
    pw = f"{client_id}_{timestamp}".encode()
    hashed = bcrypt.hashpw(pw, client_secret.encode())
    return base64.b64encode(hashed).decode()


def issue_token():
    cid, sec = load_creds()
    ts = int(time.time() * 1000)
    body = urllib.parse.urlencode({
        "client_id": cid,
        "timestamp": ts,
        "client_secret_sign": sign(cid, sec, ts),
        "grant_type": "client_credentials",
        "type": "SELF",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"token error {e.code}: {e.read().decode(errors='replace')}")
    data["_expires_at"] = time.time() + int(data.get("expires_in", 10800)) - 60
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data))
    CACHE.chmod(0o600)
    return data["access_token"]


def get_token(force=False):
    if not force and CACHE.exists():
        try:
            data = json.loads(CACHE.read_text())
            if data.get("_expires_at", 0) > time.time():
                return data["access_token"]
        except (json.JSONDecodeError, KeyError):
            pass
    return issue_token()


def api_request(method, path, query=None, body=None, _retried=False):
    url = HOST + path
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)
    headers = {"Authorization": "Bearer " + get_token(),
               "Accept": "application/json"}
    data = None
    if body is not None:
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        if e.code == 401 and "GW.AUTHN" in raw and not _retried:
            get_token(force=True)
            return api_request(method, path, query, body, _retried=True)
        return e.code, raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument("method", help="token | GET | POST | PUT | DELETE")
    p.add_argument("path", nargs="?", help="API path, e.g. /external/v1/product-orders")
    p.add_argument("--query", nargs="*", default=[], help="k=v pairs")
    p.add_argument("--body", help="JSON string for request body")
    a = p.parse_args()

    if a.method == "token":
        print(get_token(force=True))
        return

    if not a.path:
        sys.exit("path required for HTTP methods")
    query = dict(kv.split("=", 1) for kv in a.query) if a.query else None
    status, raw = api_request(a.method.upper(), a.path, query, a.body)
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(raw)
    sys.exit(0 if 200 <= status < 300 else 1)


if __name__ == "__main__":
    main()
