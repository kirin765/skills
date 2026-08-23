#!/usr/bin/env python3
"""Play Developer API — READ-ONLY operator.

Run with the shared venv:
  ~/.config/play-publisher/venv/bin/python play_read.py <cmd> [--package PKG] [opts]

Commands:
  summary    one-shot: details + tracks + bundles + listing languages
  reviews    user reviews + star ratings (--max N, --lang xx, --token CURSOR)
  details    default language, contact email/website
  tracks     tracks + releases (versionCodes, status, staged rollout fraction)
  bundles    uploaded AAB versionCodes (+ apks)
  listings   per-language store listing (title + short/full description)

Read-only by design: opens an edit, reads, abandons it. Never commits. No writes.
Caveat: aggregate rating / install / crash STATS are NOT in this API — that's the
Play Console Reporting API / BigQuery export, a different surface. This returns
individual reviews and the current edit state only.
"""
import argparse, json, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SA_KEY = "/Users/kiwankim/.config/play-publisher/sa.json"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
DEFAULT_PKG = "com.kiwan.quicktodo"


def svc():
    creds = service_account.Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def with_edit(s, pkg, fn):
    eid = s.edits().insert(packageName=pkg, body={}).execute()["id"]
    try:
        return fn(eid)
    finally:
        try:
            s.edits().delete(packageName=pkg, editId=eid).execute()
        except Exception:
            pass


def cmd_reviews(s, pkg, a):
    kw = {"packageName": pkg, "maxResults": a.max}
    if a.lang:
        kw["translationLanguage"] = a.lang
    if a.token:
        kw["token"] = a.token
    r = s.reviews().list(**kw).execute()
    out = []
    for rv in r.get("reviews", []):
        c = (rv.get("comments") or [{}])[0].get("userComment", {})
        out.append({
            "author": rv.get("authorName"),
            "reviewId": rv.get("reviewId"),
            "starRating": c.get("starRating"),
            "text": c.get("text"),
            "device": c.get("deviceMetadata", {}).get("productName"),
            "androidOsVersion": c.get("androidOsVersion"),
            "appVersionName": c.get("appVersionName"),
            "lastModified": c.get("lastModified", {}).get("seconds"),
            "replied": len(rv.get("comments") or []) > 1,
        })
    return {"count": len(out), "reviews": out,
            "nextToken": r.get("tokenPagination", {}).get("nextPageToken")}


def cmd_details(s, pkg, a):
    return with_edit(s, pkg, lambda e: s.edits().details().get(packageName=pkg, editId=e).execute())


def cmd_tracks(s, pkg, a):
    def f(e):
        r = s.edits().tracks().list(packageName=pkg, editId=e).execute()
        res = []
        for t in r.get("tracks", []):
            for rel in t.get("releases", []):
                res.append({
                    "track": t["track"], "name": rel.get("name"),
                    "status": rel.get("status"),
                    "versionCodes": rel.get("versionCodes"),
                    "userFraction": rel.get("userFraction"),
                })
        return {"releases": res}
    return with_edit(s, pkg, f)


def cmd_bundles(s, pkg, a):
    def f(e):
        b = s.edits().bundles().list(packageName=pkg, editId=e).execute().get("bundles", [])
        k = s.edits().apks().list(packageName=pkg, editId=e).execute().get("apks", [])
        return {"bundles": [{"versionCode": x["versionCode"], "sha256": x.get("sha256")} for x in b],
                "apks": [{"versionCode": x["versionCode"]} for x in k]}
    return with_edit(s, pkg, f)


def cmd_listings(s, pkg, a):
    def f(e):
        ls = s.edits().listings().list(packageName=pkg, editId=e).execute().get("listings", [])
        return {"listings": [{"language": l["language"], "title": l.get("title"),
                              "shortDescription": l.get("shortDescription"),
                              "fullDescription": (l.get("fullDescription") or "")[:300]} for l in ls]}
    return with_edit(s, pkg, f)


def cmd_images(s, pkg, a):
    lang = a.lang or "ko-KR"
    types = ["icon", "featureGraphic", "phoneScreenshots",
             "sevenInchScreenshots", "tenInchScreenshots", "tvBanner", "wearScreenshots"]
    def f(e):
        out = {}
        for it in types:
            imgs = s.edits().images().list(packageName=pkg, editId=e,
                                           language=lang, imageType=it).execute().get("images", [])
            if imgs:
                out[it] = [{"id": im.get("id"), "url": im.get("url"), "sha256": im.get("sha256")} for im in imgs]
        return {"language": lang, "images": out,
                "counts": {k: len(v) for k, v in out.items()}}
    return with_edit(s, pkg, f)


def cmd_summary(s, pkg, a):
    return {
        "package": pkg,
        "details": cmd_details(s, pkg, a),
        "tracks": cmd_tracks(s, pkg, a)["releases"],
        "bundles": cmd_bundles(s, pkg, a),
        "listingLanguages": [l["language"] for l in cmd_listings(s, pkg, a)["listings"]],
        "imageCounts": cmd_images(s, pkg, a)["counts"],
    }


CMDS = {"summary": cmd_summary, "reviews": cmd_reviews, "details": cmd_details,
        "tracks": cmd_tracks, "bundles": cmd_bundles, "listings": cmd_listings,
        "images": cmd_images}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=list(CMDS))
    ap.add_argument("--package", default=DEFAULT_PKG)
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--lang", default=None, help="translate reviews to this language e.g. en")
    ap.add_argument("--token", default=None, help="reviews pagination cursor")
    a = ap.parse_args()
    try:
        print(json.dumps(CMDS[a.cmd](svc(), a.package, a), ensure_ascii=False, indent=2))
    except HttpError as e:
        msg = f"API error {e.resp.status}: {e}"
        if e.resp.status in (401, 403):
            msg += ("\n→ service account lacks read access to this app, or package wrong. "
                    "Grant play-publisher@claude-for-android.iam.gserviceaccount.com "
                    "in Play Console → Users and permissions.")
        print(msg, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
