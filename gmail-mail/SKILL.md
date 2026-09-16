---
name: gmail-mail
description: Send and read Gmail with Python stdlib SMTP/IMAP using a Google app password (no browser, no pip installs).
---

# Gmail (SMTP send + IMAP read)

Send and read `@gmail.com` email using Python stdlib only (`smtplib`/`imaplib`) — no pip installs, no browser. Two scripts:

- `scripts/send_mail.py` — send via `smtp.gmail.com:465` (SSL)
- `scripts/read_mail.py` — read/search via `imap.gmail.com:993` (SSL)

SMTP is send-only; anything about **reading** an inbox goes through IMAP.

## Setup (one-time)

1. **Create an app password:** go to https://myaccount.google.com/apppasswords (requires 2-Step Verification enabled on the account). Name it something like "opencode", copy the 16-char password. Gmail **rejects the regular account password** for SMTP/IMAP — the app password is mandatory.
2. **Credentials in `~/niche-finder/.env`:**
   ```
   GMAIL_MAIL_ADDRESS=you@gmail.com
   GMAIL_MAIL_PASSWORD=<16-char app password>
   ```
   Unlike Naver, the SMTP/IMAP login username is the **full email address**. Override with `GMAIL_MAIL_USER` only if login differs.

If creds are missing or wrong, the scripts exit with a message saying exactly what to fix — relay it to the user rather than guessing.

## Sending

```bash
python scripts/send_mail.py --to a@b.com --subject "제목" --body "본문"
```

Useful flags:
- `--to a@b.com,c@d.com` — multiple recipients (comma-separated); same for `--cc` / `--bcc`
- `--body-file draft.txt` — read the body from a file (better for long/multiline Korean text than a huge `--body` string)
- `--html "<h1>..</h1>"` — send an HTML alternative
- `--attach report.pdf` — attach a file (repeat the flag for several)
- `--from-name "홍길동"` — set a display name

When the user dictates a message, draft the subject/body, **show it to them, and only send after they confirm** — sending is outward-facing and hard to take back. For long bodies write the text to a temp file and use `--body-file` to avoid shell-escaping issues with quotes and newlines.

## Reading

List mode is the default (newest first); pass `--uid` to open one message.

```bash
python scripts/read_mail.py                     # newest 10 in INBOX
python scripts/read_mail.py --unseen --limit 20 # unread only
python scripts/read_mail.py --from github.com   # sender contains "github.com"
python scripts/read_mail.py --subject 결제       # subject contains 결제 (UTF-8 search works)
python scripts/read_mail.py --since 2026-07-01  # on/after a date
python scripts/read_mail.py --uid 12345         # print full decoded body
python scripts/read_mail.py --uid 12345 --mark-read
```

Listing uses `BODY.PEEK` and opens the mailbox read-only, so it never marks anything read. A message is only marked read when you pass `--mark-read` on a `--uid` fetch. Filters combine (e.g. `--unseen --from boss@x.com`).

ASCII `--from`/`--subject` terms search the whole mailbox server-side. **Korean (non-ASCII) `--subject`/`--from` terms are matched client-side over the newest ~500 messages** — imaplib's UTF-8 literal handling is unreliable against Gmail too, and client-side matching always works. So a Korean subject search only reaches recent mail; for older Korean mail, narrow with `--since` or raise `CLIENT_SCAN_CAP` in the script.

Typical read flow: run a list to get UIDs, then `--uid <n>` to read the one the user cares about.

## Notes

- Gmail's free tier caps sending (~500 recipients/day) to fight spam; a burst of sends can hit a temporary limit. Send deliberately, not in loops.
- Bodies are decoded with the part's declared charset (Gmail mail is almost always UTF-8) — both are handled.
- Only INBOX is searched by default. Other Gmail folders use non-ASCII IMAP names; add folder handling only if the user asks for it.
- Gmail app passwords are account-wide: the same password works for any device/app on that account. Revoke it at the same app-password page if it leaks.
