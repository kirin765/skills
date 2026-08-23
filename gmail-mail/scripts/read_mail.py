#!/usr/bin/env python3
"""Read email from Gmail IMAP (imap.gmail.com:993, SSL). Python stdlib only.

List mode (default) prints newest-first: UID, date, from, subject, [UNREAD].
Fetch mode (--uid N) prints the full decoded text body of one message.

Examples:
  python read_mail.py                        # newest 10 in INBOX
  python read_mail.py --unseen --limit 20    # unread only
  python read_mail.py --from github.com      # from anyone @github.com
  python read_mail.py --subject 결제          # subject contains 결제 (UTF-8 search)
  python read_mail.py --since 2026-07-01
  python read_mail.py --uid 12345            # full body of that message
  python read_mail.py --uid 12345 --mark-read
"""
import argparse
import email
import imaplib
import re
import sys
from datetime import datetime
from email.header import decode_header, make_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _creds import get_creds  # noqa: E402

IMAP_HOST = "imap.gmail.com"
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
            "IMAP auth failed. Confirm GMAIL_MAIL_PASSWORD is an app password\n"
            "(myaccount.google.com/apppasswords), not your regular password."
        )
    return imap


CLIENT_SCAN_CAP = 500  # newest N headers scanned for non-ASCII (Korean) filters


def fetch_headers(imap, uids):
    """uids: list[bytes]. Return {uid_str: (date, from, subject, unread)}."""
    if not uids:
        return {}
    typ, resp = imap.uid(
        "FETCH", b",".join(uids), "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
    )
    if typ != "OK":
        sys.exit(f"IMAP fetch failed: {resp}")
    rows = {}
    i = 0
    while i < len(resp):
        part = resp[i]
        if isinstance(part, tuple):
            descriptor = part[0].decode(errors="replace")
            if i + 1 < len(resp) and isinstance(resp[i + 1], (bytes, bytearray)):
                descriptor += " " + resp[i + 1].decode(errors="replace")
                i += 1
            m_uid = re.search(r"UID (\d+)", descriptor)
            m_flags = re.search(r"FLAGS \(([^)]*)\)", descriptor)
            if m_uid:
                hdr = email.message_from_bytes(part[1])
                rows[m_uid.group(1)] = (
                    decode_hdr(hdr.get("Date", "")),
                    decode_hdr(hdr.get("From", "")),
                    decode_hdr(hdr.get("Subject", "(제목 없음)")),
                    "\\Seen" not in (m_flags.group(1) if m_flags else ""),
                )
        i += 1
    return rows


def list_messages(imap, args):
    imap.select("INBOX", readonly=True)

    server, client = [], []
    if args.unseen:
        server.append("UNSEEN")
    if args.since:
        server += ["SINCE", datetime.strptime(args.since, "%Y-%m-%d").strftime("%d-%b-%Y")]
    if args.search:
        server += args.search.split()
    for field, val in (("FROM", args.from_addr), ("SUBJECT", args.subject)):
        if not val:
            continue
        if val.isascii():
            server += [field, val]
        else:
            client.append((field, val.lower()))
    if not server:
        server = ["ALL"]

    typ, data = imap.uid("SEARCH", None, *server)
    if typ != "OK":
        sys.exit(f"IMAP search failed: {data}")
    uids = data[0].split()[::-1]  # newest first
    if not uids:
        print("No matching messages.")
        return

    scan = uids[:CLIENT_SCAN_CAP] if client else uids[: args.limit]
    rows = fetch_headers(imap, scan)

    shown = 0
    for uid in (u.decode() for u in scan):
        row = rows.get(uid)
        if not row:
            continue
        date, frm, subj, unread = row
        if client:
            hay = {"FROM": frm.lower(), "SUBJECT": subj.lower()}
            if not all(term in hay[field] for field, term in client):
                continue
        flag = " [UNREAD]" if unread else ""
        print(f"UID {uid}{flag}\n  {date}\n  From: {frm}\n  Subj: {subj}\n")
        shown += 1
        if shown >= args.limit:
            break
    if shown == 0:
        print("No matching messages.")


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
    ap = argparse.ArgumentParser(description="Read email via Gmail IMAP")
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
