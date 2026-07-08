#!/usr/bin/env python3
"""Sonar (trysonar.app) ASO API client — Google Play / App Store keyword
difficulty + popularity, keyword suggestions, monthly revenue estimates, and reviews.

Reads SONAR_API_KEY from ../.env or env. Bearer auth. Each call spends account
credits (keywords/search ~10, keywords/metrics ~1 per keyword). 50 free on signup.
All commands here are stateless — they work on ANY app/keyword, no account setup.

Usage:
  sonar.py keywords <query>       [--store android|ios] [--country us] [--json]
  sonar.py metrics  <kw...>       [--store] [--country] [--json]   # up to 25, 1 credit/kw
  sonar.py suggest  <seed>        [--store] [--country] [--json]   # cheap, no difficulty
  sonar.py revenue  <store_id...> [--store] [--json]               # any app, monthly $ estimate
  sonar.py reviews  <store_id>    [--store] [--country] [--stars low|high] [--json]
"""
import sys, os, json, argparse, urllib.request, urllib.parse, urllib.error

BASE = "https://trysonar.app/api/v1"

def load_key():
    k = os.environ.get("SONAR_API_KEY")
    if not k:
        envp = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(envp):
            for line in open(envp):
                line = line.strip()
                if line.startswith("SONAR_API_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("Missing SONAR_API_KEY (.env or env var).")
    return k

KEY = None
def call(path, params):
    url = f"{BASE}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + KEY, "User-Agent": "sonar-skill"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")

def n(v):
    return "-" if v is None else (f"{v:,}" if isinstance(v, (int, float)) else str(v))

def kwtable(rows):
    print(f"{'keyword':<34}{'diff':>6}{'pop':>6}{'#apps':>8}")
    for it in rows:
        print(f"{str(it.get('keyword'))[:33]:<34}{n(it.get('difficulty')):>6}"
              f"{n(it.get('popularity')):>6}{n(it.get('results_count')):>8}")

def cmd_keywords(a):
    rows = call("/keywords/search", {"q": a.query, "store": a.store, "country": a.country}).get("data") or []
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    print(f"# keyword research '{a.query}'  store={a.store} country={a.country}  (~10 credits)")
    kwtable(rows)

def cmd_metrics(a):
    p = {"store": a.store, "country": a.country}
    if len(a.keywords) == 1:
        p["q"] = a.keywords[0]
    else:
        p["qs"] = ",".join(a.keywords[:25])
    rows = call("/keywords/metrics", p).get("data") or []
    if isinstance(rows, dict):
        rows = [rows]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    print(f"# metrics ({len(rows)} kw, ~1 credit each)  store={a.store} country={a.country}")
    kwtable(rows)

def cmd_suggest(a):
    rows = call("/keywords/suggestions", {"q": a.seed, "store": a.store, "country": a.country}).get("data") or []
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    print(f"# suggestions '{a.seed}'  store={a.store}  ({len(rows)})")
    for it in rows:
        print(f"  {it.get('term')}   (priority {n(it.get('priority'))})")

def cmd_revenue(a):
    p = {"store": a.store}
    if len(a.ids) == 1:
        p["id"] = a.ids[0]
    else:
        p["ids"] = ",".join(a.ids[:25])
    d = call("/apps/revenue", p).get("data")
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2)); return
    items = d if isinstance(d, list) else [d]
    print(f"# monthly revenue estimate  store={a.store}")
    for it in items:
        app = it.get("app", {}) or {}
        rev = it.get("revenue", {}) or {}
        print(f"  {app.get('name') or app.get('store_id')}: "
              f"{rev.get('monthly_formatted') or n(rev.get('monthly'))}  (model: {rev.get('model')})")

def cmd_reviews(a):
    p = {"store": a.store, "id": a.id, "country": a.country}
    if a.stars:
        p["stars"] = a.stars
    rows = call("/apps/reviews", p).get("data") or []
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    print(f"# reviews {a.id}  store={a.store}  ({len(rows)})")
    for it in rows[:50]:
        star = it.get("rating") or it.get("stars") or "-"
        title = it.get("title") or ""
        body = it.get("text") or it.get("body") or it.get("content") or ""
        print(f"  [{star}★] {title} — {str(body)[:160]}")

def main():
    global KEY
    p = argparse.ArgumentParser(description="Sonar ASO API client")
    sub = p.add_subparsers(dest="cmd", required=True)
    def common(sp):
        sp.add_argument("--store", default="android", choices=["android", "ios"])
        sp.add_argument("--country", default="us")
        sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("keywords"); sp.add_argument("query"); common(sp)
    sp = sub.add_parser("metrics"); sp.add_argument("keywords", nargs="+"); common(sp)
    sp = sub.add_parser("suggest"); sp.add_argument("seed"); common(sp)
    sp = sub.add_parser("revenue"); sp.add_argument("ids", nargs="+")
    sp.add_argument("--store", default="android", choices=["android", "ios"]); sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("reviews"); sp.add_argument("id"); common(sp); sp.add_argument("--stars", choices=["low", "high"])
    a = p.parse_args()
    KEY = load_key()
    {"keywords": cmd_keywords, "metrics": cmd_metrics, "suggest": cmd_suggest,
     "revenue": cmd_revenue, "reviews": cmd_reviews}[a.cmd](a)

if __name__ == "__main__":
    main()
