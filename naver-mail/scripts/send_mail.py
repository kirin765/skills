#!/usr/bin/env python3
"""Send an email through Naver SMTP (smtp.naver.com:465, SSL). Python stdlib only.

Examples:
  python send_mail.py --to a@b.com --subject "안녕" --body "본문입니다"
  python send_mail.py --to a@b.com,c@d.com --subject Hi --body-file draft.txt --attach report.pdf
  python send_mail.py --to a@b.com --subject Hi --html "<h1>hi</h1>" --cc boss@x.com
  python send_mail.py --to a@b.com --subject "RE: ..." --body-file reply.txt --reply-to-uid 48556
"""
import argparse
import email
import mimetypes
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _creds import get_creds  # noqa: E402
from read_mail import connect, decode_hdr, extract_body  # noqa: E402

QUOTE_CAP = 30000  # max chars of quoted thread appended under a reply

SMTP_HOST = "smtp.naver.com"
SMTP_PORT = 465


def split_addrs(value):
    if not value:
        return []
    return [a.strip() for a in value.replace(";", ",").split(",") if a.strip()]


def fetch_message_raw(uid):
    """Fetch the full RFC822 message by INBOX UID, read-only (never marks read)."""
    imap = connect()
    try:
        imap.select("INBOX", readonly=True)
        typ, resp = imap.uid("FETCH", str(uid), "(RFC822)")
        if typ != "OK" or not resp or resp[0] is None:
            sys.exit(f"Message UID {uid} not found.")
        return email.message_from_bytes(resp[0][1])
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def scrub_quote(text):
    """Strip Naver mail CSS noise and collapse blank runs for a clean inline quote."""
    text = re.sub(r"#dext_body[^{}]*\{[^}]*\}", "", text)
    text = re.sub(r"<img[^>]*/?>", "", text)
    text = re.sub(r"(?m)^\s*[.#]?\w[\w:.-]*\s*\{[^}]*\}\s*$", "", text)
    text = re.sub(r"(?m)^제목없음\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_quote(msg):
    """Naver-style '-----Original Message-----' block with headers + body."""
    cc = decode_hdr(msg.get("Cc", ""))
    body = extract_body(msg).strip()
    if len(body) > QUOTE_CAP:
        body = body[:QUOTE_CAP] + "\n[... 이전 내용 생략]"
    quote = (
        "\n\n\n-----Original Message-----\n"
        f"From: {decode_hdr(msg.get('From', ''))}\n"
        f"To: {decode_hdr(msg.get('To', ''))}\n"
        + (f"Cc: {cc}\n" if cc else "")
        + f"Date: {decode_hdr(msg.get('Date', ''))}\n"
        f"Subject: {decode_hdr(msg.get('Subject', '(제목 없음)'))}\n"
        "\n"
        f"{body}"
    )
    return scrub_quote(quote)


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

    if args.reply_to_uid:
        orig = fetch_message_raw(args.reply_to_uid)
        body = (body.rstrip() + build_quote(orig)) if body else build_quote(orig)
        msgid = orig.get("Message-ID")
        if msgid:
            msg["In-Reply-To"] = msgid
            # 전달이 깊은 메일은 References 헤더에 개행이 섞여 있어 그대로 쓰면 전송이 깨진다.
            # 헤더 값은 한 줄이어야 하므로 공백·개행을 정리해 다시 조립한다.
            refs = " ".join((((orig.get("References", "") or "") + " " + msgid).split()))
            if refs:
                msg["References"] = refs

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
    ap = argparse.ArgumentParser(description="Send email via Naver SMTP")
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
    ap.add_argument("--reply-to-uid", help="quote this INBOX message UID below the reply "
                                           "(Naver-style original-message block)")
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
            "SMTP auth failed. Check NAVER_MAIL_PASSWORD, confirm SMTP is enabled in\n"
            "네이버 메일 > 환경설정 > POP3/IMAP 설정, and if 2FA is on use an 애플리케이션 비밀번호."
        )
    print(f"Sent to {', '.join(recipients)} (subject: {args.subject})")


if __name__ == "__main__":
    main()
