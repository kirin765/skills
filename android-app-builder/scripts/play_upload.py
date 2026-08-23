#!/usr/bin/env python3
"""Play Developer API uploader — AAB · store images · listings, in one edit.

Bypasses the blocked Chrome file-picker path. Run with the skill's venv:
  ~/.config/play-publisher/venv/bin/python play_upload.py --config app.json [--commit]

Without --commit it validates and abandons the edit (dry run, nothing persists).
With --commit it commits → sends changes for review (IRREVERSIBLE-ish: goes to
review/publish). Only pass --commit when the user said "출시까지".

Prereq: the service account (SA_KEY) must be granted "release" permission on the
app in Play Console, and the app + its FIRST AAB must already exist (created
manually once). See references/play-publishing-api.md.
"""
import argparse, json, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SA_KEY = "/Users/kiwankim/.config/play-publisher/sa.json"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]
IMAGE_TYPES = {"icon", "featureGraphic", "phoneScreenshots",
               "sevenInchScreenshots", "tenInchScreenshots", "tvBanner", "wearScreenshots"}


def client():
    creds = service_account.Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def run(cfg, commit, changes_not_sent=False):
    pkg = cfg["packageName"]
    svc = client()
    edits = svc.edits()
    edit_id = edits.insert(packageName=pkg, body={}).execute()["id"]
    print(f"edit {edit_id} opened for {pkg}")
    version_codes = []

    try:
        # 1) AAB (only if a new version is being shipped)
        if cfg.get("aab"):
            res = edits.bundles().upload(
                packageName=pkg, editId=edit_id,
                media_body=MediaFileUpload(cfg["aab"], mimetype="application/octet-stream",
                                           resumable=True)).execute()
            vc = res["versionCode"]
            version_codes.append(vc)
            print(f"  AAB uploaded → versionCode {vc}")

        # 2) Store images — replace each type wholesale
        for itype, val in (cfg.get("images") or {}).items():
            if itype not in IMAGE_TYPES:
                sys.exit(f"unknown imageType: {itype}")
            files = [val] if isinstance(val, str) else list(val)
            lang = cfg.get("graphicsLanguage", "ko-KR")
            edits.images().deleteall(packageName=pkg, editId=edit_id,
                                     language=lang, imageType=itype).execute()
            for f in files:
                edits.images().upload(
                    packageName=pkg, editId=edit_id, language=lang, imageType=itype,
                    media_body=MediaFileUpload(f, mimetype="image/png")).execute()
            print(f"  images[{itype}] ← {len(files)} file(s) @ {lang}")

        # 3) Listings per language (video = YouTube 프로모션 동영상 URL, 선택)
        for lang, l in (cfg.get("listings") or {}).items():
            edits.listings().update(packageName=pkg, editId=edit_id, language=lang, body={
                "language": lang,
                "title": l["title"],
                "shortDescription": l.get("shortDescription", ""),
                "fullDescription": l.get("fullDescription", ""),
                "video": l.get("video", ""),
            }).execute()
            print(f"  listing[{lang}] updated"
                  + (f" (+video {l['video']})" if l.get("video") else ""))

        # 4) Track assignment (only if we shipped an AAB)
        if version_codes:
            track = cfg.get("track", "production")
            release = {"status": cfg.get("releaseStatus", "completed"),
                       "versionCodes": [str(v) for v in version_codes]}
            if cfg.get("releaseNotes"):
                release["releaseNotes"] = [{"language": lang, "text": text}
                                           for lang, text in cfg["releaseNotes"].items()]
            edits.tracks().update(packageName=pkg, editId=edit_id, track=track, body={
                "track": track,
                "releases": [release],
            }).execute()
            print(f"  track[{track}] ← versionCodes {version_codes}"
                  + (" (+releaseNotes)" if cfg.get("releaseNotes") else ""))

        # 일부 앱은 API 자동 검토전송이 막혀 validate/commit에 changesNotSentForReview=true가 필수다.
        # 이 경우 validate조차 400을 내므로, 그 모드에선 validate를 건너뛰고 commit에서 검증한다.
        if not changes_not_sent:
            edits.validate(packageName=pkg, editId=edit_id).execute()
            print("  validate OK")

        if commit:
            if changes_not_sent:
                edits.commit(packageName=pkg, editId=edit_id,
                             changesNotSentForReview=True).execute()
                print("COMMITTED (changesNotSentForReview=true) → 트랙에 반영됨. "
                      "이 앱은 API 자동 검토전송이 막혀 있으니, Play Console에서 "
                      "'변경사항 검토를 위해 전송'을 1회 클릭해 재심사 제출을 완료하세요.")
            else:
                edits.commit(packageName=pkg, editId=edit_id).execute()
                print("COMMITTED → changes sent for review.")
        else:
            edits.delete(packageName=pkg, editId=edit_id).execute()
            print("DRY RUN ok → edit abandoned (nothing persisted). Re-run with --commit to ship.")
    except Exception:
        try:
            edits.delete(packageName=pkg, editId=edit_id).execute()
            print("edit abandoned due to error.")
        except Exception:
            pass
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="path to app config JSON")
    ap.add_argument("--commit", action="store_true", help="commit + send for review (irreversible)")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    try:
        run(cfg, a.commit)
    except HttpError as e:
        if e.resp.status == 400 and "changesNotSentForReview" in str(e):
            print("↻ 이 앱은 API 자동 검토전송 불가 → changesNotSentForReview=true로 재시도.",
                  file=sys.stderr)
            try:
                run(cfg, a.commit, changes_not_sent=True)
                return
            except HttpError as e2:
                e = e2
        print(f"\nAPI error {e.resp.status}: {e}", file=sys.stderr)
        if e.resp.status in (401, 403):
            print("→ The service account likely lacks Play Console permission for this app, "
                  "or the app/package doesn't exist yet. Grant 'release' access to "
                  "play-publisher@claude-for-android.iam.gserviceaccount.com in "
                  "Play Console → Users and permissions, and ensure the app + first AAB exist.",
                  file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
