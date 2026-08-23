#!/usr/bin/env python3
"""Play install stats (downloads/uninstalls) from the GCS reporting bucket.

The Play Developer API exposes NO install numbers — they live only in the
private stats bucket gs://pubsite_prod_<devId>/stats/installs/*_overview.csv.
The publishing service account can already read that bucket (devstorage scope).

Run with the shared venv:
  ~/.config/play-publisher/venv/bin/python play_installs.py [--package PKG] [--json]

Default: lifetime per-app summary across every package in the bucket.
"""
import argparse, csv, io, json, sys, urllib.parse, urllib.request
from collections import defaultdict
from google.oauth2 import service_account
import google.auth.transport.requests as gtr

SA = "/Users/kiwankim/.config/play-publisher/sa.json"
DEV_ID = "8303647010319569479"
BUCKET = f"pubsite_prod_{DEV_ID}"
SCOPE = "https://www.googleapis.com/auth/devstorage.read_only"


def token():
    c = service_account.Credentials.from_service_account_file(SA, scopes=[SCOPE])
    c.refresh(gtr.Request())
    return c.token


def get(url, tok):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    return urllib.request.urlopen(req).read()


def list_overviews(tok):
    base = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o"
    names, page = [], None
    while True:
        u = base + "?prefix=stats/installs/&fields=items(name),nextPageToken"
        if page:
            u += f"&pageToken={page}"
        r = json.loads(get(u, tok))
        names += [i["name"] for i in r.get("items", []) if i["name"].endswith("_overview.csv")]
        page = r.get("nextPageToken")
        if not page:
            return names


def pkg_of(name):
    stem = name.split("/")[-1][len("installs_"):-len("_overview.csv")]
    return stem.rsplit("_", 1)[0]  # drop trailing _YYYYMM


def fetch_csv(name, tok):
    o = urllib.parse.quote(name, safe="")
    return get(f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{o}?alt=media", tok).decode("utf-16")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", help="filter to one package (case-insensitive)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tok = token()
    files = list_overviews(tok)
    if args.package:
        files = [f for f in files if pkg_of(f).lower() == args.package.lower()]
        if not files:
            sys.exit(f"no install reports for package {args.package}")

    agg = defaultdict(lambda: {"downloads": 0, "uninstalls": 0, "device_installs": 0,
                               "active": 0, "last_date": ""})
    for name in files:
        pkg = pkg_of(name)
        a = agg[pkg]
        for row in csv.DictReader(io.StringIO(fetch_csv(name, tok))):
            a["downloads"] += int(row["Daily User Installs"] or 0)
            a["uninstalls"] += int(row["Daily User Uninstalls"] or 0)
            a["device_installs"] += int(row["Daily Device Installs"] or 0)
            if row["Date"] > a["last_date"]:
                a["last_date"] = row["Date"]
                a["active"] = int(row["Active Device Installs"] or 0)

    rows = sorted(agg.items(), key=lambda kv: -kv[1]["downloads"])
    if args.json:
        print(json.dumps({p: v for p, v in rows}, indent=2, ensure_ascii=False))
        return

    print(f"{'PACKAGE':<42}{'DL(user)':>9}{'UNINST':>8}{'ACTIVE':>8}")
    print("-" * 67)
    td = tu = ta = 0
    for pkg, v in rows:
        print(f"{pkg:<42}{v['downloads']:>9}{v['uninstalls']:>8}{v['active']:>8}")
        td += v["downloads"]; tu += v["uninstalls"]; ta += v["active"]
    print("-" * 67)
    print(f"{'TOTAL ('+str(len(rows))+' apps)':<42}{td:>9}{tu:>8}{ta:>8}")


if __name__ == "__main__":
    main()
