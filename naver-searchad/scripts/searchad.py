#!/usr/bin/env python3
"""Naver Search Ads API client — HMAC-signed REST, stdlib only.

Credentials are read from ~/niche-finder/.env (NAVER_ADS_CUSTOMER_ID /
NAVER_ADS_API_KEY / NAVER_ADS_SECRET_KEY). Env vars of the same name override
the file, so nothing is hardcoded here.

Read commands (campaigns, adgroups, keywords, stats, keywordtool, get) are
safe. Write commands (bid, on, off, post, put, delete) change a live account
that spends real money — only run them when the user has asked for that exact
change.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.searchad.naver.com"
ENV_PATH = os.path.expanduser("~/niche-finder/.env")


def load_creds():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v.strip().strip('"').strip("'")
    cid = os.environ.get("NAVER_ADS_CUSTOMER_ID") or env.get("NAVER_ADS_CUSTOMER_ID")
    key = os.environ.get("NAVER_ADS_API_KEY") or env.get("NAVER_ADS_API_KEY")
    sec = os.environ.get("NAVER_ADS_SECRET_KEY") or env.get("NAVER_ADS_SECRET_KEY")
    if not (cid and key and sec):
        sys.exit(
            f"Missing credentials. Set NAVER_ADS_CUSTOMER_ID / NAVER_ADS_API_KEY / "
            f"NAVER_ADS_SECRET_KEY in {ENV_PATH} or the environment."
        )
    return cid, key, sec


CID, API_KEY, SECRET = load_creds()


def _sign(timestamp, method, uri):
    msg = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def request(method, uri, params=None, body=None):
    """Signed request. `uri` is the path only (no query) — the signature must
    not include the query string. Returns parsed JSON (or None on 204)."""
    method = method.upper()
    url = BASE_URL + uri
    if params:
        url += "?" + urllib.parse.urlencode(params)
    ts = str(round(time.time() * 1000))
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Timestamp", ts)
    req.add_header("X-API-KEY", API_KEY)
    req.add_header("X-Customer", str(CID))
    req.add_header("X-Signature", _sign(ts, method, uri))
    if data is not None:
        req.add_header("Content-Type", "application/json; charset=UTF-8")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "replace")
        sys.exit(f"HTTP {e.code} {method} {uri}\n{body_txt}")


# ---------- output helpers ----------

def out(obj, as_json):
    print(json.dumps(obj, ensure_ascii=False, indent=2) if as_json else obj)


def table(rows, cols):
    if not rows:
        print("(none)")
        return
    widths = [max(len(str(r.get(c, ""))) for r in rows + [{c: c}]) for c in cols]
    line = lambda vals: "  ".join(str(v).ljust(w) for v, w in zip(vals, widths))
    print(line(cols))
    print(line(["-" * w for w in widths]))
    for r in rows:
        print(line([r.get(c, "") for c in cols]))


# ---------- commands ----------

def cmd_campaigns(a):
    data = request("GET", "/ncc/campaigns")
    if a.json:
        return out(data, True)
    table(data, ["nccCampaignId", "campaignTp", "name", "status", "dailyBudget"])


def cmd_adgroups(a):
    data = request("GET", "/ncc/adgroups", {"nccCampaignId": a.campaign_id})
    if a.json:
        return out(data, True)
    table(data, ["nccAdgroupId", "name", "status", "bidAmt", "dailyBudget"])


def cmd_keywords(a):
    data = request("GET", "/ncc/keywords", {"nccAdgroupId": a.adgroup_id})
    if a.json:
        return out(data, True)
    table(data, ["nccKeywordId", "keyword", "status", "bidAmt", "useGroupBidAmt", "qualityKeyword"])


def cmd_keywordtool(a):
    params = {"hintKeywords": ",".join(k.replace(" ", "") for k in a.keywords), "showDetail": "1"}
    data = request("GET", "/keywordstool", params)
    rows = data.get("keywordList", [])
    if a.json:
        return out(rows, True)
    table(rows[: a.limit], ["relKeyword", "monthlyPcQcCnt", "monthlyMobileQcCnt", "compIdx", "plAvgDepth"])


def cmd_stats(a):
    fields = a.fields.split(",") if a.fields else [
        "impCnt", "clkCnt", "ctr", "cpc", "salesAmt", "ccnt", "avgRnk"
    ]
    params = {"id": a.id, "fields": json.dumps(fields)}
    if a.since and a.until:
        params["timeRange"] = json.dumps({"since": a.since, "until": a.until})
    elif a.preset:
        params["datePreset"] = a.preset
    if a.daily:
        params["timeIncrement"] = "1"
    data = request("GET", "/stats", params)
    out(data, True)  # stats shape varies; always raw JSON


def cmd_bid(a):
    body = {"nccKeywordId": a.keyword_id, "bidAmt": a.amount, "useGroupBidAmt": False}
    data = request("PUT", f"/ncc/keywords/{a.keyword_id}", {"fields": "bidAmt"}, body)
    out(data, True)


def cmd_groupbid(a):
    body = {"nccAdgroupId": a.adgroup_id, "bidAmt": a.amount}
    data = request("PUT", f"/ncc/adgroups/{a.adgroup_id}", {"fields": "bidAmt"}, body)
    out(data, True)


def cmd_toggle(a, enable):
    entity, eid = a.entity, a.id
    path = {"campaign": "/ncc/campaigns/", "adgroup": "/ncc/adgroups/", "keyword": "/ncc/keywords/"}[entity]
    idfield = {"campaign": "nccCampaignId", "adgroup": "nccAdgroupId", "keyword": "nccKeywordId"}[entity]
    body = {idfield: eid, "userLock": not enable}
    data = request("PUT", path + eid, {"fields": "userLock"}, body)
    out(data, True)


def cmd_raw(a):
    body = json.loads(a.body) if a.body else None
    params = dict(p.split("=", 1) for p in a.param) if a.param else None
    data = request(a.method.upper(), a.uri, params, body)
    out(data, True)


def main():
    p = argparse.ArgumentParser(description="Naver Search Ads API client")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("campaigns", help="list campaigns")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_campaigns)

    s = sub.add_parser("adgroups", help="list adgroups in a campaign")
    s.add_argument("campaign_id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_adgroups)

    s = sub.add_parser("keywords", help="list keywords (with bids) in an adgroup")
    s.add_argument("adgroup_id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_keywords)

    s = sub.add_parser("keywordtool", help="keyword tool: search volume + related keywords")
    s.add_argument("keywords", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_keywordtool)

    s = sub.add_parser("stats", help="performance stats for an entity id")
    s.add_argument("id", help="campaign/adgroup/keyword/ad id")
    s.add_argument("--since", help="YYYY-MM-DD")
    s.add_argument("--until", help="YYYY-MM-DD")
    s.add_argument("--preset", help="e.g. last7days, last30days, lastMonth")
    s.add_argument("--fields", help="comma list e.g. impCnt,clkCnt,salesAmt,ctr,cpc")
    s.add_argument("--daily", action="store_true", help="break down by day")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("bid", help="[WRITE] set a keyword's bid (won)")
    s.add_argument("keyword_id")
    s.add_argument("amount", type=int)
    s.set_defaults(fn=cmd_bid)

    s = sub.add_parser("groupbid", help="[WRITE] set an adgroup's default bid (won)")
    s.add_argument("adgroup_id")
    s.add_argument("amount", type=int)
    s.set_defaults(fn=cmd_groupbid)

    s = sub.add_parser("on", help="[WRITE] enable a campaign/adgroup/keyword")
    s.add_argument("entity", choices=["campaign", "adgroup", "keyword"])
    s.add_argument("id")
    s.set_defaults(fn=lambda a: cmd_toggle(a, True))

    s = sub.add_parser("off", help="[WRITE] pause a campaign/adgroup/keyword")
    s.add_argument("entity", choices=["campaign", "adgroup", "keyword"])
    s.add_argument("id")
    s.set_defaults(fn=lambda a: cmd_toggle(a, False))

    s = sub.add_parser("raw", help="generic signed request to any endpoint")
    s.add_argument("method")
    s.add_argument("uri", help="path only, e.g. /ncc/ads?... use --param for query")
    s.add_argument("--param", action="append", help="key=value query param (repeatable)")
    s.add_argument("--body", help="JSON request body")
    s.set_defaults(fn=cmd_raw)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
