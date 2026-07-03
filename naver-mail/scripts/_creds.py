"""Shared credential loading for the naver-mail scripts.

Naver Mail uses one account password (or an app password when 2FA is on) for both
SMTP and IMAP. Login username is the local part of the address (Naver's rule:
for hong@naver.com the SMTP/IMAP user is `hong`), which is why we split on '@'.
"""
import os
import sys
from pathlib import Path

ENV_FILE = Path.home() / "niche-finder" / ".env"


def _load_env_file():
    """Populate os.environ from ~/niche-finder/.env for any keys not already set."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def get_creds():
    """Return (address, login_user, password) or exit with a clear setup message."""
    _load_env_file()
    address = os.environ.get("NAVER_MAIL_ADDRESS")
    password = os.environ.get("NAVER_MAIL_PASSWORD")
    if not address or not password:
        sys.exit(
            "Naver mail not configured. Add to ~/niche-finder/.env:\n"
            "  NAVER_MAIL_ADDRESS=you@naver.com\n"
            "  NAVER_MAIL_PASSWORD=<account or app password>\n"
            "Also enable IMAP/SMTP in 네이버 메일 > 환경설정 > POP3/IMAP 설정, and if 2FA is\n"
            "on, generate an 애플리케이션 비밀번호 and use it as NAVER_MAIL_PASSWORD."
        )
    login_user = os.environ.get("NAVER_MAIL_USER") or address.split("@", 1)[0]
    return address, login_user, password
