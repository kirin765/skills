---
name: naver-mail
description: Send and read email from a personal Naver mailbox (@naver.com) over SMTP and IMAP. Use this skill whenever the user wants to send an email, reply, or check/read/search their Naver inbox — e.g. "네이버 메일 보내줘", "네이버로 이메일 발송", "이 파일 메일로 보내줘", "받은편지함 확인해줘", "안 읽은 메일 있어?", "네이버 메일에서 결제 관련 메일 찾아줘", "send an email from my Naver account", "read my Naver inbox", "check unread mail". Trigger even when the user doesn't say "Naver" but clearly means their own @naver.com mailbox for personal email send/read. This is the personal mailbox skill (SMTP send + IMAP read) — NOT naver-api (search trends), naver-searchad (ads), or naver-commerce-api (store). For Gmail, use the GMAIL_* SMTP path instead, not this skill.
---

# Naver Mail (SMTP send + IMAP read)

Send and read `@naver.com` email using Python stdlib only (`smtplib`/`imaplib`) — no pip installs, no browser. Two scripts:

- `scripts/send_mail.py` — send via `smtp.naver.com:465` (SSL)
- `scripts/read_mail.py` — read/search via `imap.naver.com:993` (SSL)

SMTP is send-only; anything about **reading** an inbox goes through IMAP.

## Setup (one-time)

1. **Enable access in Naver Mail:** 네이버 메일 → 환경설정 → POP3/IMAP 설정 → set **IMAP/SMTP 사용 = 사용함**. Without this, auth fails even with the right password.
2. **Credentials in `~/niche-finder/.env`:**
   ```
   NAVER_MAIL_ADDRESS=you@naver.com
   NAVER_MAIL_PASSWORD=<account password, or app password if 2FA is on>
   ```
   Login username is derived as the part before `@` (Naver's rule). Override with `NAVER_MAIL_USER` only if login differs from the address prefix.
3. **If 2단계 인증 (2FA) is on:** a normal password will be rejected. Generate an 애플리케이션 비밀번호 at naver.com 보안 설정 and use it as `NAVER_MAIL_PASSWORD`.

If creds are missing or access isn't enabled, the scripts exit with a message saying exactly what to fix — relay it to the user rather than guessing.

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
python scripts/read_mail.py --from naver.com    # sender contains "naver.com"
python scripts/read_mail.py --subject 결제       # subject contains 결제 (UTF-8 search works)
python scripts/read_mail.py --since 2026-07-01  # on/after a date
python scripts/read_mail.py --uid 12345         # print full decoded body
python scripts/read_mail.py --uid 12345 --mark-read
```

Listing uses `BODY.PEEK` and opens the mailbox read-only, so it never marks anything read. A message is only marked read when you pass `--mark-read` on a `--uid` fetch. Filters combine (e.g. `--unseen --from boss@x.com`). Korean subject/sender search is sent as UTF-8 automatically.

Typical read flow: run a list to get UIDs, then `--uid <n>` to read the one the user cares about.

## Notes

- Naver caps outbound volume (roughly a few hundred recipients/day) to fight spam; a burst of sends can hit a temporary limit. Send deliberately, not in loops.
- Bodies are decoded with the part's declared charset (Naver mail is often UTF-8, sometimes EUC-KR) — both are handled.
- Only INBOX is searched by default. Other Naver folders use non-ASCII IMAP names; add folder handling only if the user asks for it.
