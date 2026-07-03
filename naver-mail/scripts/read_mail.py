#!/usr/bin/env python3
"""Read email from Naver IMAP (imap.naver.com:993, SSL). Python stdlib only.

List mode (default) prints newest-first: UID, date, from, subject, [UNREAD].
Fetch mode (--uid N) prints the full decoded text body of one message.

Examples:
  python read_mail.py                        # newest 10 in INBOX
  python read_mail.py --unseen --limit 20    # unread only
  python read_mail.py --from naver.com       # from anyone @naver.com
  python read_mail.py --subject 결제          # subject contains 결제 (UTF-8 search)
  python read_mail.py --since 2026-07-01
  python read_mail.py --uid 12345            # full body of that message
  python read_mail.py --uid 12345 --mark-read
"""
import argparse
import email
import imaplib
import sys
from datetime import datetime
from email.header import decode_header, make_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _creds import get_creds  # noqa: E402

IMAP_HOST = "imap.naver.com"
IMAP_PORT = 993


def decode_hdr(raw):
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw


def connect():
    address, login_user, password = get_creds()
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        imap.login(login_user, password)
    except imaplib.IMAP4.error:
        sys.exit(
            "IMAP auth failed. Confirm IMAP is enabled in 네이버 메일 > 환경설정 >\n"
            "POP3/IMAP 설정, check NAVER_MAIL_PASSWORD, and if 2FA is on use an 애플리케이션 비밀번호."
        )
    return imap


def build_search(args):
    """Return (charset, criteria_list). charset is 'UTF-8' when a term is non-ASCII."""
    criteria = []
    if args.unseen:
        criteria.append("UNSEEN")
    if args.since:
        d = datetime.strptime(args.since, "%Y-%m-%d")
        criteria += ["SINCE", d.strftime("%d-%b-%Y")]
    if args.from_addr:
        criteria += ["FROM", args.from_addr]
    if args.subject:
        criteria += ["SUBJECT", args.subject]
    if args.search:
        criteria += args.search.split()
    if not criteria:
        criteria = ["ALL"]
    non_ascii = any(not str(c).isascii() for c in criteria)
    return ("UTF-8" if non_ascii else None), criteria


def list_messages(imap, args):
    imap.select("INBOX", readonly=True)
    charset, criteria = build_search(args)
    if charset:
        enc = [c.encode("utf-8") if not str(c).isascii() else c for c in criteria]
        typ, data = imap.uid("SEARCH", charset, *enc)
    else:
        typ, data = imap.uid("SEARCH", None, *criteria)
    if typ != "OK":
        sys.exit(f"IMAP search failed: {data}")
    uids = data[0].split()
    if not uids:
        print("No matching messages.")
        return
    uids = uids[::-1][: args.limit]

    fetch_set = b",".join(uids)
    typ, resp = imap.uid("FETCH", fetch_set, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
    if typ != "OK":
        sys.exit(f"IMAP fetch failed: {resp}")

    rows = {}
    for part in resp:
        if not isinstance(part, tuple):
            continue
        meta, raw_hdr = part[0], part[1]
        meta = meta.decode(errors="replace")
        uid = meta.split("UID", 1)[1].split()[0].strip("()") if "UID" in meta else "?"
        unread = "\\Seen" not in meta
        hdr = email.message_from_bytes(raw_hdr)
        rows[uid] = (
            decode_hdr(hdr.get("Date", "")),
            decode_hdr(hdr.get("From", "")),
            decode_hdr(hdr.get("Subject", "(제목 없음)")),
            unread,
        )

    for uid in [u.decode() for u in uids]:
        if uid not in rows:
            continue
        date, frm, subj, unread = rows[uid]
        flag = " [UNREAD]" if unread else ""
        print(f"UID {uid}{flag}\n  {date}\n  From: {frm}\n  Subj: {subj}\n")


def extract_body(msg):
    if msg.is_multipart():
        plain, html = None, None
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition", "").startswith("attachment"):
                continue
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
        return plain or html or ""
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def fetch_message(imap, uid, mark_read):
    imap.select("INBOX", readonly=not mark_read)
    typ, resp = imap.uid("FETCH", str(uid), "(RFC822)")
    if typ != "OK" or not resp or resp[0] is None:
        sys.exit(f"Message UID {uid} not found.")
    msg = email.message_from_bytes(resp[0][1])
    print(f"From:    {decode_hdr(msg.get('From',''))}")
    print(f"To:      {decode_hdr(msg.get('To',''))}")
    print(f"Date:    {decode_hdr(msg.get('Date',''))}")
    print(f"Subject: {decode_hdr(msg.get('Subject',''))}")
    print("-" * 60)
    print(extract_body(msg).strip())
    if mark_read:
        imap.uid("STORE", str(uid), "+FLAGS", "(\\Seen)")
        print("\n[marked as read]")


def main():
    ap = argparse.ArgumentParser(description="Read email via Naver IMAP")
    ap.add_argument("--uid", help="fetch full body of this message UID")
    ap.add_argument("--mark-read", action="store_true", help="mark fetched message as read")
    ap.add_argument("--limit", type=int, default=10, help="max messages to list (default 10)")
    ap.add_argument("--unseen", action="store_true", help="only unread messages")
    ap.add_argument("--from-addr", help="filter by sender (substring)")
    ap.add_argument("--subject", help="filter by subject (substring)")
    ap.add_argument("--since", help="on/after date, YYYY-MM-DD")
    ap.add_argument("--search", help="raw IMAP SEARCH terms, e.g. 'FLAGGED'")
    args = ap.parse_args()

    imap = connect()
    try:
        if args.uid:
            fetch_message(imap, args.uid, args.mark_read)
        else:
            list_messages(imap, args)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
