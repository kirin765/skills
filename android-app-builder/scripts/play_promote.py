#!/usr/bin/env python3
"""Promote an EXISTING track release status (e.g. draft -> completed) WITHOUT
re-uploading the AAB. Use when a release was committed as `draft` and now needs
to be sent to review.

  ~/.config/play-publisher/venv/bin/python play_promote.py \
      --package com.x.y --track production --version-code 1 --status completed [--commit]

Without --commit: opens edit, stages the track update, prints the resulting
release, then ABANDONS (nothing persisted). With --commit: commits -> sends to
review (irreversible-ish).
"""
import argparse, json, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SA_KEY = "/Users/kiwankim/.config/play-publisher/sa.json"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]


def svc():
    creds = service_account.Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def run(a):
    s = svc()
    edit_id = s.edits().insert(packageName=a.package, body={}).execute()["id"]
    print(f"edit {edit_id} opened for {a.package}")
    try:
        cur = s.edits().tracks().get(packageName=a.package, editId=edit_id, track=a.track).execute()
        rel = None
        for r in cur.get("releases", []):
            if a.version_code in (r.get("versionCodes") or []):
                rel = r
                break
        if rel is None:
            rel = {"versionCodes": [a.version_code]}
        rel["status"] = a.status
        body = {"track": a.track, "releases": [rel]}
        res = s.edits().tracks().update(packageName=a.package, editId=edit_id, track=a.track, body=body).execute()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if a.commit:
            s.edits().commit(packageName=a.package, editId=edit_id).execute()
            print("COMMITTED -> release sent for review.")
        else:
            s.edits().delete(packageName=a.package, editId=edit_id).execute()
            print("DRY RUN ok -> edit abandoned (nothing persisted). Re-run with --commit to ship.")
    except Exception:
        try:
            s.edits().delete(packageName=a.package, editId=edit_id).execute()
        except Exception:
            pass
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--track", default="production")
    ap.add_argument("--version-code", required=True)
    ap.add_argument("--status", default="completed",
                    choices=["completed", "draft", "inProgress", "halted"])
    ap.add_argument("--commit", action="store_true", help="commit + send for review (irreversible)")
    a = ap.parse_args()
    try:
        run(a)
    except HttpError as e:
        print(f"\nAPI error {e.resp.status}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
