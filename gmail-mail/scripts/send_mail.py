#!/usr/bin/env python3
"""Send an email through Gmail SMTP (smtp.gmail.com:465, SSL). Python stdlib only.

Examples:
  python send_mail.py --to a@b.com --subject "제목" --body "본문"
  python send_mail.py --to a@b.com,c@d.com --subject Hi --body-file draft.txt --attach report.pdf
  python send_mail.py --to a@b.com --subject Hi --html "<h1>hi</h1>" --cc boss@x.com
"""
import argparse
import mimetypes
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _creds import get_creds  # noqa: E402

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def split_addrs(value):
    if not value:
        return []
    return [a.strip() for a in value.replace(";", ",").split(",") if a.strip()]


def build_message(address, args):
    msg = EmailMessage()
    from_addr = args.from_addr or address
    msg["From"] = formataddr((args.from_name, from_addr)) if args.from_name else from_addr
    msg["To"] = ", ".join(args.to)
    if args.cc:
        msg["Cc"] = ", ".join(args.cc)
    msg["Subject"] = args.subject

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text()

    if args.html:
        msg.set_content(body or "This message requires an HTML-capable client.")
        msg.add_alternative(args.html, subtype="html")
    else:
        msg.set_content(body or "")

    for path in args.attach or []:
        p = Path(path)
        if not p.exists():
            sys.exit(f"Attachment not found: {path}")
        ctype, _ = mimetypes.guess_type(p.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(
            p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name
        )
    return msg


def main():
    ap = argparse.ArgumentParser(description="Send email via Gmail SMTP")
    ap.add_argument("--to", required=True, help="recipient(s), comma-separated")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", default="", help="plain-text body")
    ap.add_argument("--body-file", help="read plain-text body from a file")
    ap.add_argument("--html", help="HTML body (sent as an alternative part)")
    ap.add_argument("--attach", action="append", help="file to attach (repeatable)")
    ap.add_argument("--cc", help="cc recipient(s), comma-separated")
    ap.add_argument("--bcc", help="bcc recipient(s), comma-separated")
    ap.add_argument("--from-addr", help="override From address (defaults to your account)")
    ap.add_argument("--from-name", help="display name for the From header")
    args = ap.parse_args()

    args.to = split_addrs(args.to)
    args.cc = split_addrs(args.cc)
    bcc = split_addrs(args.bcc)
    if not args.to:
        sys.exit("No valid --to recipients.")

    address, login_user, password = get_creds()
    msg = build_message(address, args)
    recipients = args.to + args.cc + bcc

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=30) as smtp:
            smtp.login(login_user, password)
            smtp.send_message(msg, from_addr=args.from_addr or address, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError:
        sys.exit(
            "SMTP auth failed. Check GMAIL_MAIL_PASSWORD. Gmail requires an app\n"
            "password (myaccount.google.com/apppasswords), not your regular password."
        )
    print(f"Sent to {', '.join(recipients)} (subject: {args.subject})")


if __name__ == "__main__":
    main()
