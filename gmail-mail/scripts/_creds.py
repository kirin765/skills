"""Shared credential loading for the gmail-mail scripts.

Gmail uses an app password for both SMTP and IMAP when 2FA is on (always required
for IMAP now). Unlike Naver, the SMTP/IMAP login username is the FULL email address.
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
    address = os.environ.get("GMAIL_MAIL_ADDRESS")
    password = os.environ.get("GMAIL_MAIL_PASSWORD")
    if not address or not password:
        sys.exit(
            "Gmail mail not configured. Add to ~/niche-finder/.env:\n"
            "  GMAIL_MAIL_ADDRESS=you@gmail.com\n"
            "  GMAIL_MAIL_PASSWORD=<app password>\n"
            "Generate an app password at myaccount.google.com/apppasswords (requires\n"
            "2-Step Verification). Use it as GMAIL_MAIL_PASSWORD. The regular password\n"
            "will be rejected."
        )
    login_user = os.environ.get("GMAIL_MAIL_USER") or address
    return address, login_user, password
