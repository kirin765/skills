#!/usr/bin/env python3
"""토스쇼핑 Open API 클라이언트 (표준 라이브러리만 사용).

OAuth2 client_credentials 로 access token 을 발급/캐시하고, Bearer 인증으로
API 를 호출한다. 토큰은 유효기간이 길고(약 1년) 과도한 재발급은 이용이 제한될 수
있으므로 ~/.toss-shopping-token.json 에 환경별로 캐시하고, 만료 임박/401 일 때만
새로 발급한다.

Usage:
    toss_shopping.py GET  "<path>" [--query k=v ...]
    toss_shopping.py POST "<path>" [--query k=v ...] [--body '<json>']
    toss_shopping.py PUT  "<path>" [--query k=v ...] [--body '<json>']
    toss_shopping.py DELETE "<path>" [--query k=v ...] [--body '<json>']
    toss_shopping.py token            # 토큰 강제 발급 후 출력 (디버그)

옵션:
    --env test        alpha 테스트 환경 사용 (기본: prod, TOSS_ENV 로도 지정 가능)
    --body @file.json  파일에서 바디 읽기
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_FILE = os.path.expanduser("~/.toss-shopping.env")
TOKEN_FILE = os.path.expanduser("~/.toss-shopping-token.json")

HOSTS = {
    "prod": {"api": "https://shopping-fep.toss.im", "oauth": "https://oauth2.cert.toss.im"},
    "test": {"api": "https://shopping-fep-alpha.toss.im", "oauth": "https://oauth2-alpha.cert.toss.im"},
}
SCOPE = "toss-shopping-fep:write"
# 만료까지 이만큼(초) 남으면 미리 재발급
REFRESH_MARGIN = 60 * 60 * 24


def load_env():
    if not os.path.exists(ENV_FILE):
        sys.exit(f"자격증명 파일이 없습니다: {ENV_FILE}")
    creds = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip().strip('"').strip("'")
    if not creds.get("TOSS_ACCESS_KEY") or not creds.get("TOSS_SECRET_KEY"):
        sys.exit("TOSS_ACCESS_KEY / TOSS_SECRET_KEY 가 env 파일에 없습니다.")
    return creds


def read_body(bytes_):
    try:
        buf = bytes_
        if buf[:2] == b"\x1f\x8b":
            buf = gzip.decompress(buf)
        return buf.decode("utf-8")
    except Exception:
        return bytes_.decode("utf-8", "replace")


def issue_token(creds, env):
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": creds["TOSS_ACCESS_KEY"],
        "client_secret": creds["TOSS_SECRET_KEY"],
        "scope": SCOPE,
    }).encode()
    req = urllib.request.Request(
        HOSTS[env]["oauth"] + "/token",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(read_body(resp.read()))
    except urllib.error.HTTPError as e:
        sys.exit(f"토큰 발급 실패 {e.code}: {read_body(e.read())}")
    payload["_env"] = env
    payload["_expires_at"] = int(time.time()) + int(payload.get("expires_in", 0))
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f)
    return payload["access_token"]


def get_token(creds, env, force=False):
    if not force and os.path.exists(TOKEN_FILE):
        try:
            cached = json.load(open(TOKEN_FILE))
            if (cached.get("_env") == env
                    and cached.get("_expires_at", 0) - time.time() > REFRESH_MARGIN
                    and cached.get("access_token")):
                return cached["access_token"]
        except Exception:
            pass
    return issue_token(creds, env)


def call(method, path, query, body, creds, env, token, retry=True):
    url = HOSTS[env]["api"] + path
    if query:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode(query)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = body.encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, read_body(resp.read())
    except urllib.error.HTTPError as e:
        text = read_body(e.read())
        if e.code == 401 and retry:
            token = issue_token(creds, env)
            return call(method, path, query, body, creds, env, token, retry=False)
        return e.code, text


def main():
    p = argparse.ArgumentParser(description="토스쇼핑 Open API 클라이언트")
    p.add_argument("method", help="GET/POST/PUT/DELETE 또는 token")
    p.add_argument("path", nargs="?", help="API 경로 (예: /api/v3/shopping-fep/products/v2)")
    p.add_argument("--query", nargs="*", default=[], help="쿼리 파라미터 k=v ...")
    p.add_argument("--body", help="JSON 바디 문자열 또는 @파일경로")
    p.add_argument("--env", choices=["prod", "test"], help="환경 (기본 prod)")
    args = p.parse_args()

    creds = load_env()
    env = args.env or ("test" if creds.get("TOSS_ENV") == "test" else "prod")

    if args.method.lower() == "token":
        print(get_token(creds, env, force=True))
        return

    method = args.method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE"):
        sys.exit(f"지원하지 않는 메서드: {method}")
    if not args.path:
        sys.exit("path 가 필요합니다.")

    query = {}
    for kv in args.query:
        if "=" not in kv:
            sys.exit(f"잘못된 쿼리 형식: {kv} (k=v 여야 함)")
        k, v = kv.split("=", 1)
        query[k] = v

    body = args.body
    if body and body.startswith("@"):
        body = open(os.path.expanduser(body[1:])).read()
    if body is not None:
        try:
            json.loads(body)  # 유효성만 확인
        except Exception as e:
            sys.exit(f"바디가 유효한 JSON 이 아닙니다: {e}")

    token = get_token(creds, env)
    status, text = call(method, args.path, query, body, creds, env, token)
    try:
        print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
    except Exception:
        print(text)
    sys.exit(0 if 200 <= status < 300 else 1)


if __name__ == "__main__":
    main()
