#!/usr/bin/env python3
"""YouTube Data API v3 uploader — video + metadata + optional thumbnail.

Run with the skill's venv:
  ~/.config/youtube-upload/venv/bin/python yt_upload.py \
    --video promo.mp4 --title "..." --description-file desc.txt \
    --tags "tag1,tag2" [--privacy unlisted] [--thumbnail thumb.png]

Prints the video ID and watch URL on success. Quota: each upload costs
1,600 units of the 10,000/day default — about 6 uploads per day.

Prereq: ~/.config/youtube-upload/token.json from yt_auth.py.
"""
import argparse, os, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

TOKEN_PATH = os.path.expanduser("~/.config/youtube-upload/token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def client():
    if not os.path.exists(TOKEN_PATH):
        sys.exit(f"Missing {TOKEN_PATH} — run yt_auth.py first (one-time setup).")
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--title", required=True)
    desc = ap.add_mutually_exclusive_group()
    desc.add_argument("--description", default="")
    desc.add_argument("--description-file", help="UTF-8 text file; survives multi-line Korean text")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--privacy", default="unlisted", choices=["public", "unlisted", "private"])
    ap.add_argument("--category", default="22", help="categoryId (22=People & Blogs, 28=Sci/Tech)")
    ap.add_argument("--thumbnail", help="PNG/JPEG under 2MB")
    ap.add_argument("--made-for-kids", action="store_true")
    ap.add_argument("--language", default="ko", help="defaultLanguage / defaultAudioLanguage")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"Video not found: {args.video}")
    if len(args.title.encode()) > 100 * 4:  # API limit is 100 chars
        sys.exit("Title too long (max 100 chars)")
    description = args.description
    if args.description_file:
        with open(args.description_file, encoding="utf-8") as f:
            description = f.read()
    if args.thumbnail and os.path.getsize(args.thumbnail) > 2 * 1024 * 1024:
        sys.exit("Thumbnail over 2MB — YouTube rejects it. Compress first.")

    body = {
        "snippet": {
            "title": args.title,
            "description": description,
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "categoryId": args.category,
            "defaultLanguage": args.language,
            "defaultAudioLanguage": args.language,
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": args.made_for_kids,
        },
    }

    yt = client()
    media = MediaFileUpload(args.video, chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    try:
        response = None
        while response is None:
            status, response = req.next_chunk()
            if status:
                print(f"  upload {int(status.progress() * 100)}%", flush=True)
        vid = response["id"]
        print(f"OK: video id={vid}")
        print(f"URL: https://youtu.be/{vid}")

        if args.thumbnail:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(args.thumbnail)).execute()
            print("OK: thumbnail set")
    except HttpError as e:
        if e.resp.status == 403 and b"quotaExceeded" in e.content:
            sys.exit("FAIL: daily quota exceeded (uploads cost 1,600 of 10,000 units). Retry after midnight PT.")
        sys.exit(f"FAIL: {e.resp.status} {e.content.decode()[:500]}")


if __name__ == "__main__":
    main()
