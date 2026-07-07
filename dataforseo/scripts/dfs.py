#!/usr/bin/env python3
"""DataForSEO ASO client — keyword volume, app keywords, suggestions, difficulty.

Reads creds from ../.env (DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD) or env vars.
All calls use the synchronous /live endpoints. Pay-as-you-go — each call costs money.

Usage:
  dfs.py balance
  dfs.py volume <kw...> [--geo US|KR|JP|GB|..] [--lang en|ko|..] [--json]
  dfs.py app-keywords <play_app_id> [--geo] [--lang] [--limit N] [--json]
  dfs.py suggest <seed> [--geo] [--lang] [--limit N] [--json]
  dfs.py difficulty <kw...> [--geo] [--lang] [--json]
  dfs.py app-competitors <play_app_id> [--geo] [--lang] [--limit N] [--json]
"""
import sys, os, json, base64, argparse, urllib.request, urllib.error

BASE = "https://api.dataforseo.com/v3"
# location_code, default language for common geos
GEO = {
    "US": (2840, "en"), "KR": (2410, "ko"), "JP": (2392, "ja"), "GB": (2826, "en"),
    "DE": (2276, "de"), "FR": (2250, "fr"), "CA": (2124, "en"), "AU": (2036, "en"),
    "IN": (2356, "en"), "BR": (2076, "pt"), "ID": (2360, "id"), "TW": (2158, "zh-TW"),
}

def load_creds():
    login = os.environ.get("DATAFORSEO_LOGIN")
    pw = os.environ.get("DATAFORSEO_PASSWORD")
    if not (login and pw):
        envp = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(envp):
            for line in open(envp):
                line = line.strip()
                if line.startswith("DATAFORSEO_LOGIN="): login = line.split("=", 1)[1]
                elif line.startswith("DATAFORSEO_PASSWORD="): pw = line.split("=", 1)[1]
    if not (login and pw):
        sys.exit("Missing DataForSEO creds (.env or env vars).")
    return base64.b64encode(f"{login}:{pw}".encode()).decode()

AUTH = None
def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data else "GET",
        headers={"Authorization": "Basic " + AUTH, "Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")
    if r.get("status_code") != 20000:
        sys.exit(f"API error {r.get('status_code')}: {r.get('status_message')}")
    task = r["tasks"][0]
    if task.get("status_code") != 20000:
        sys.exit(f"Task error {task.get('status_code')}: {task.get('status_message')}")
    return task.get("result") or []

def geo(args):
    if args.geo:
        g = args.geo.upper()
        if g in GEO:
            loc, lang = GEO[g]
            return loc, (args.lang or lang)
        return int(args.geo), (args.lang or "en")  # raw location_code
    return 2840, (args.lang or "en")

def n(v):
    return "-" if v is None else (f"{v:,}" if isinstance(v, (int, float)) else str(v))

def cmd_balance(args):
    r = call("/appendix/user_data")[0]
    print(f"balance: ${r['money']['balance']}  |  login: {r.get('login')}")

def cmd_volume(args):
    loc, lang = geo(args)
    res = call("/keywords_data/google_ads/search_volume/live",
               [{"keywords": args.keywords, "location_code": loc, "language_code": lang}])
    items = res[0].get("items") or res  # live returns result array of keyword objects
    rows = items if isinstance(items, list) and items and "keyword" in (items[0] or {}) else res
    if args.json: print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    print(f"# search volume  geo={args.geo or 'US'}  lang={lang}")
    print(f"{'keyword':<28}{'volume':>10}{'comp':>10}{'idx':>6}{'cpc_low':>9}{'cpc_high':>9}")
    for it in rows:
        print(f"{(it.get('keyword') or '')[:27]:<28}{n(it.get('search_volume')):>10}"
              f"{str(it.get('competition') or '-'):>10}{n(it.get('competition_index')):>6}"
              f"{n(it.get('low_top_of_page_bid')):>9}{n(it.get('high_top_of_page_bid')):>9}")

def cmd_app_keywords(args):
    loc, lang = geo(args)
    res = call("/dataforseo_labs/google_play/keywords_for_app/live",
               [{"app_id": args.app_id, "location_code": loc, "language_code": lang, "limit": args.limit}])
    items = (res[0].get("items") if res else None) or []
    if args.json: print(json.dumps(items, ensure_ascii=False, indent=2)); return
    print(f"# keywords app={args.app_id}  geo={args.geo or 'US'}  ({len(items)})")
    print(f"{'keyword':<30}{'volume':>10}{'comp':>8}{'diff':>6}")
    for it in items:
        ki = it.get("keyword_data", {}).get("keyword_info", {}) if it.get("keyword_data") else it
        kw = it.get("keyword") or it.get("keyword_data", {}).get("keyword", "")
        vol = ki.get("search_volume")
        comp = ki.get("competition")
        diff = (it.get("keyword_data", {}).get("keyword_properties", {}) or {}).get("keyword_difficulty")
        print(f"{str(kw)[:29]:<30}{n(vol):>10}{str(comp or '-'):>8}{n(diff):>6}")

def cmd_suggest(args):
    loc, lang = geo(args)
    res = call("/dataforseo_labs/google/keyword_suggestions/live",
               [{"keyword": args.seed, "location_code": loc, "language_code": lang, "limit": args.limit}])
    items = (res[0].get("items") if res else None) or []
    if args.json: print(json.dumps(items, ensure_ascii=False, indent=2)); return
    print(f"# suggestions seed='{args.seed}'  geo={args.geo or 'US'}  ({len(items)})")
    print(f"{'keyword':<34}{'volume':>10}{'comp':>8}")
    for it in items:
        ki = it.get("keyword_info", {})
        print(f"{str(it.get('keyword'))[:33]:<34}{n(ki.get('search_volume')):>10}{str(ki.get('competition') or '-'):>8}")

def cmd_difficulty(args):
    loc, lang = geo(args)
    res = call("/dataforseo_labs/google/bulk_keyword_difficulty/live",
               [{"keywords": args.keywords, "location_code": loc, "language_code": lang}])
    items = (res[0].get("items") if res else None) or []
    if args.json: print(json.dumps(items, ensure_ascii=False, indent=2)); return
    print(f"# keyword difficulty  geo={args.geo or 'US'}")
    for it in items:
        print(f"  {str(it.get('keyword'))[:40]:<42}{n(it.get('keyword_difficulty'))}")

def cmd_app_competitors(args):
    loc, lang = geo(args)
    res = call("/dataforseo_labs/google_play/app_competitors/live",
               [{"app_id": args.app_id, "location_code": loc, "language_code": lang, "limit": args.limit}])
    items = (res[0].get("items") if res else None) or []
    if args.json: print(json.dumps(items, ensure_ascii=False, indent=2)); return
    print(f"# app competitors app={args.app_id}  ({len(items)})")
    for it in items:
        m = it.get("metrics", {}) or {}
        print(f"  {str(it.get('app_id'))[:40]:<42} intersections={n(it.get('intersections'))}")

def main():
    global AUTH
    p = argparse.ArgumentParser(description="DataForSEO ASO client")
    sub = p.add_subparsers(dest="cmd", required=True)
    def add_geo(sp):
        sp.add_argument("--geo"); sp.add_argument("--lang"); sp.add_argument("--json", action="store_true")
    sub.add_parser("balance")
    sp = sub.add_parser("volume"); sp.add_argument("keywords", nargs="+"); add_geo(sp)
    sp = sub.add_parser("app-keywords"); sp.add_argument("app_id"); sp.add_argument("--limit", type=int, default=50); add_geo(sp)
    sp = sub.add_parser("suggest"); sp.add_argument("seed"); sp.add_argument("--limit", type=int, default=50); add_geo(sp)
    sp = sub.add_parser("difficulty"); sp.add_argument("keywords", nargs="+"); add_geo(sp)
    sp = sub.add_parser("app-competitors"); sp.add_argument("app_id"); sp.add_argument("--limit", type=int, default=20); add_geo(sp)
    args = p.parse_args()
    AUTH = load_creds()
    {"balance": cmd_balance, "volume": cmd_volume, "app-keywords": cmd_app_keywords,
     "suggest": cmd_suggest, "difficulty": cmd_difficulty, "app-competitors": cmd_app_competitors}[args.cmd](args)

if __name__ == "__main__":
    main()
