#!/usr/bin/env python3
"""AppBrain API client — Google Play app intelligence: install estimates, used
SDKs/libraries, ratings, and app search/discovery.

Reads APPBRAIN_API_KEY from ../.env or env. Key format: <clientid>.<secret>.
Own apps are free; competitor/other apps consume account credits (500/mo free tier).

Usage:
  appbrain.py getapp <package> [--country US] [--summary] [--libs] [--json]
  appbrain.py search <query>   [--country US] [--limit 20] [--json]
  appbrain.py libraries [--json]
  appbrain.py countries
"""
import sys, os, json, argparse, urllib.request, urllib.parse, urllib.error

BASE = "https://api.appbrain.com/v2"

def load_key():
    k = os.environ.get("APPBRAIN_API_KEY")
    if not k:
        envp = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(envp):
            for line in open(envp):
                line = line.strip()
                if line.startswith("APPBRAIN_API_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("Missing APPBRAIN_API_KEY (.env or env var).")
    return k

KEY = None
def call(path, params):
    q = urllib.parse.urlencode({**params, "apikey": KEY})
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"User-Agent": "appbrain-skill"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")

def n(v):
    return "-" if v is None else (f"{v:,}" if isinstance(v, (int, float)) else str(v))

def rating_str(r):
    return f"{r:.2f}" if isinstance(r, (int, float)) else "-"

def libcatalog():
    try:
        return {l["id"]: l.get("name", l["id"]) for l in call("/info/getlibraries", {}).get("libraries", [])}
    except Exception:
        return {}

def cmd_getapp(a):
    r = call("/info/getapp", {"package": a.package, "country": a.country,
                              "schema": "summary" if a.summary else "full"})
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2)); return
    libs = r.get("libraries") or []
    if a.libs and libs:
        cat = libcatalog(); libs = [cat.get(x, x) for x in libs]
    print(f"{r.get('name')}  ({r.get('package')})")
    print(f"  developer:   {r.get('developerName')}   category: {r.get('marketCategory')}")
    print(f"  rating:      {rating_str(r.get('rating'))}  ({n(r.get('ratingCount'))} ratings, {n(r.get('commentCount'))} comments)")
    print(f"  installs:    {n(r.get('estimatedDownloads'))} est  |  bracket {r.get('downloadsCategory')}  |  recent {n(r.get('estimatedRecentDownloads'))}")
    print(f"  updated:     {r.get('lastAppUpdateTime')}   apkSize {n(r.get('apkSize'))}   price {n(r.get('price'))}")
    print(f"  permissions: {len(r.get('permissions') or [])}")
    print(f"  libraries ({len(libs)}): " + ", ".join(map(str, libs)))

def cmd_search(a):
    r = call("/info/search", {"query": a.query, "country": a.country, "schema": "full"})
    apps = (r.get("apps") or [])[:a.limit]
    if a.json:
        print(json.dumps(apps, ensure_ascii=False, indent=2)); return
    print(f"# search '{a.query}'  country={a.country}  ({len(apps)})")
    print(f"{'name':<34}{'installs':>13}{'bracket':>12}{'rating':>7}  package")
    for it in apps:
        print(f"{str(it.get('name'))[:33]:<34}{n(it.get('estimatedDownloads')):>13}"
              f"{str(it.get('downloadsCategory') or '-'):>12}{rating_str(it.get('rating')):>7}  {it.get('package')}")

def cmd_libraries(a):
    r = call("/info/getlibraries", {})
    libs = r.get("libraries") or []
    if a.json:
        print(json.dumps(libs, ensure_ascii=False, indent=2)); return
    print(f"# known libraries ({len(libs)})")
    for l in libs:
        print(f"  {l.get('id'):<32} {l.get('name')}  [{','.join(l.get('tags') or [])}]")

def cmd_countries(a):
    print(json.dumps(call("/info/getcountries", {}), ensure_ascii=False, indent=2))

def main():
    global KEY
    p = argparse.ArgumentParser(description="AppBrain Google Play intelligence client")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("getapp"); sp.add_argument("package")
    sp.add_argument("--country", default="US"); sp.add_argument("--summary", action="store_true")
    sp.add_argument("--libs", action="store_true", help="resolve library IDs to names")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("search"); sp.add_argument("query")
    sp.add_argument("--country", default="US"); sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("libraries"); sp.add_argument("--json", action="store_true")
    sub.add_parser("countries")
    a = p.parse_args()
    KEY = load_key()
    {"getapp": cmd_getapp, "search": cmd_search, "libraries": cmd_libraries,
     "countries": cmd_countries}[a.cmd](a)

if __name__ == "__main__":
    main()
