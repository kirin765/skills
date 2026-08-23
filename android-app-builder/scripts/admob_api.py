#!/usr/bin/env python3
"""AdMob API (read-only) helper — parallel to play_upload.py.

AdMob API does NOT support service accounts; it needs OAuth user creds.
This stores a refresh token once, then runs headless like the Play API.

Credentials (under ~/.config/play-publisher/):
  admob_oauth_client.json  OAuth *Desktop* client secret (you provide once)
  admob_token.json         refresh token (created by `auth`, reused after)

Commands:
  admob_api.py auth                          one-time browser consent -> save token
  admob_api.py accounts                      list publisher accounts (-> publisher id)
  admob_api.py apps    [--account pub-XXXX]  list apps
  admob_api.py adunits [--account pub-XXXX]  list ad units
  admob_api.py report  [--account pub-XXXX] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
                                             network report (default: last 7 days)

--account is optional; if omitted the first account is used.
Output is JSON on stdout.
"""
import argparse, json, os, sys, datetime

CFG = os.path.expanduser("~/.config/play-publisher")
CLIENT = os.path.join(CFG, "admob_oauth_client.json")
TOKEN = os.path.join(CFG, "admob_token.json")
SCOPES = ["https://www.googleapis.com/auth/admob.readonly"]


def _creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    if not os.path.exists(TOKEN):
        sys.exit("No token. Run: admob_api.py auth")
    c = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not c.valid:
        if c.expired and c.refresh_token:
            c.refresh(Request())
            open(TOKEN, "w").write(c.to_json())
        else:
            sys.exit("Token invalid/expired. Re-run: admob_api.py auth")
    return c


def _svc():
    from googleapiclient.discovery import build
    return build("admob", "v1", credentials=_creds(), cache_discovery=False)


def cmd_auth(_):
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not os.path.exists(CLIENT):
        sys.exit(f"Missing {CLIENT}\nCreate an OAuth *Desktop* client in the GCP project, "
                 "download it, and save the JSON to that path.")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
    creds = flow.run_local_server(port=8765, open_browser=False, prompt="consent",
                                  authorization_prompt_message="AUTH_URL:{url}")
    open(TOKEN, "w").write(creds.to_json())
    print(json.dumps({"saved": TOKEN, "has_refresh_token": bool(creds.refresh_token)}, indent=2))


def _account(svc, arg):
    if arg:
        return arg if arg.startswith("accounts/") else f"accounts/{arg}"
    accs = svc.accounts().list().execute().get("account", [])
    if not accs:
        sys.exit("No AdMob accounts visible for this user.")
    return accs[0]["name"]


def cmd_accounts(_):
    print(json.dumps(_svc().accounts().list().execute(), indent=2, ensure_ascii=False))


def cmd_apps(a):
    svc = _svc(); acc = _account(svc, a.account)
    print(json.dumps(svc.accounts().apps().list(parent=acc).execute(), indent=2, ensure_ascii=False))


def cmd_adunits(a):
    svc = _svc(); acc = _account(svc, a.account)
    print(json.dumps(svc.accounts().adUnits().list(parent=acc).execute(), indent=2, ensure_ascii=False))


def _d(s):
    y, m, d = map(int, s.split("-"))
    return {"year": y, "month": m, "day": d}


def cmd_report(a):
    svc = _svc(); acc = _account(svc, a.account)
    end = a.end or datetime.date.today().isoformat()
    start = a.start or (datetime.date.fromisoformat(end) - datetime.timedelta(days=7)).isoformat()
    body = {"reportSpec": {
        "dateRange": {"startDate": _d(start), "endDate": _d(end)},
        "metrics": ["ESTIMATED_EARNINGS", "IMPRESSIONS", "CLICKS", "AD_REQUESTS", "MATCH_RATE"],
        "dimensions": ["DATE"],
    }}
    rows = svc.accounts().networkReport().generate(parent=acc, body=body).execute()
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(fn=cmd_auth)
    sub.add_parser("accounts").set_defaults(fn=cmd_accounts)
    for name, fn in [("apps", cmd_apps), ("adunits", cmd_adunits), ("report", cmd_report)]:
        sp = sub.add_parser(name); sp.add_argument("--account")
        if name == "report":
            sp.add_argument("--start"); sp.add_argument("--end")
        sp.set_defaults(fn=fn)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
