#!/usr/bin/env python3
"""One-time OAuth flow for YouTube uploads — issues a refresh token.

Run with the skill's venv:
  ~/.config/youtube-upload/venv/bin/python yt_auth.py --client-secret <client_secret.json>

Opens the browser for consent (the Google account that OWNS the YouTube
channel must approve), then saves credentials to
~/.config/youtube-upload/token.json. Re-run only if the token is revoked.

Prereq: a *Desktop app* type OAuth client in the GCP project, and the
account added as a test user (or the consent screen published to
production — testing-mode refresh tokens expire after 7 days).
"""
import argparse, json, os, sys
from google_auth_oauthlib.flow import InstalledAppFlow

TOKEN_PATH = os.path.expanduser("~/.config/youtube-upload/token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-secret", required=True)
    args = ap.parse_args()

    with open(args.client_secret) as f:
        kind = next(iter(json.load(f)))
    if kind != "installed":
        sys.exit(f"client_secret is '{kind}' type — need a 'Desktop app' (installed) "
                 "OAuth client. Create one in GCP Console > Credentials.")

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        sys.exit("No refresh token returned — re-run; consent prompt must be approved fresh.")

    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)
    print(f"OK: refresh token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    main()
