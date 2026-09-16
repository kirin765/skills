#!/usr/bin/env python3
"""Send SMS / iMessage / RCS from macOS Messages via AppleScript (iPhone Text Message Forwarding).

Python stdlib only. Targets the modern (macOS 15+) Messages scripting model: accounts instead of
services, participants instead of buddies. `send` is the only reliable primitive — account
enumeration happens via existing chats, and participant lookup auto-resolves any E.164 handle.

Run `--doctor` once after setup, `--dry-run` to preview. Sending is outward-facing: never send
without the user's explicit confirmation.
"""
import argparse
import re
import subprocess
import sys

ACCOUNT_RE = re.compile(r"account id ([0-9A-Fa-f-]+)")


def normalize_number(raw: str) -> str:
    """Accept 010-1234-5678 / 01012345678 / +821012345678 / 821012345678 → +821012345678."""
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if digits.startswith("+82"):
        return digits
    if digits.startswith("82") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("01") and len(digits) == 11:  # 010... → +8210...
        return "+82" + digits[1:]
    if digits.startswith("0") and len(digits) >= 9:    # 070, 02, 031... → +82...
        return "+82" + digits[1:]
    if digits.startswith("+"):
        return digits
    return "+" + digits


def apple_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def run_osascript(script: str) -> tuple[int, str, str]:
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def discover_accounts() -> dict[str, str]:
    """Map service type → account id, discovered from existing chats."""
    rc, out, _ = run_osascript('tell application "Messages" to get account of every chat')
    accounts: dict[str, str] = {}
    if rc != 0:
        return accounts
    for aid in dict.fromkeys(ACCOUNT_RE.findall(out)):  # dedupe, keep order
        r2, st, _ = run_osascript(
            f'tell application "Messages" to get service type of account id "{aid}"'
        )
        if r2 == 0 and st:
            accounts.setdefault(st, aid)
    return accounts


def account_for(accounts: dict[str, str], service: str) -> str | None:
    """Pick the account id for a forced service; None means let Messages route (auto)."""
    if service == "auto":
        return None
    if service in accounts:
        return accounts[service]
    for st, aid in accounts.items():  # tolerate "iMessage" vs "imessage" drift
        if service in st.lower():
            return aid
    return None


def build_script(number: str, message: str, account_id: str | None = None) -> str:
    if account_id:
        target = f'participant "{number}" of account id "{account_id}"'
    else:
        target = f'participant "{number}"'
    return (
        'tell application "Messages"\n'
        f'    send "{apple_escape(message)}" to {target}\n'
        "end tell"
    )


def build_chat_script(number: str, message: str) -> str:
    """Fallback for existing chats (chat ids resolve only for chats that already exist)."""
    return (
        'tell application "Messages"\n'
        f'    send "{apple_escape(message)}" to chat id "any;-;{number}"\n'
        "end tell"
    )


def hint_for(err: str) -> str:
    lowered = err.lower()
    if "-1743" in err or "not authorized" in lowered:
        return ("Automation permission missing. Grant it: System Settings → Privacy & Security → "
                "Automation → allow your terminal/agent process to control Messages, then retry.")
    if "-10000" in err or "handler failed" in lowered:
        return ("Messages' scripting backend failed (a known macOS 15+ regression). Retry once; if it "
                "persists, quit and relaunch Messages (it must be signed in), then retry.")
    if "sms" in lowered and ("forward" in lowered or "deliver" in lowered):
        return ("SMS send failed — likely Text Message Forwarding is off. On iPhone: 설정 → 메시지 → "
                "문자 메시지 전달 → enable this Mac. iPhone must be on, same Apple ID, same Wi-Fi.")
    return ""


def attempt(number: str, message: str, account_id: str | None) -> tuple[bool, str]:
    rc, _, err = run_osascript(build_script(number, message, account_id))
    return rc == 0, err.strip()


def doctor() -> None:
    print("=== send-sms diagnostics ===")
    proc = subprocess.run(["pgrep", "-x", "Messages"], capture_output=True)
    print("Messages app running:", "yes" if proc.returncode == 0 else "no (auto-launches on send)")
    rc, out, err = run_osascript('tell application "Messages" to get count of chats')
    if rc == 0:
        print("Automation permission: OK")
        print("Chats accessible:", out)
        accounts = discover_accounts()
        print("Accounts found:", ", ".join(f"{st}={aid}" for st, aid in accounts.items()) or "(none)")
        for svc in ("iMessage", "RCS", "SMS"):
            print(f"  {svc}:", "yes" if svc in accounts else "no")
        if "SMS" not in accounts:
            print("  → no SMS account: enable Text Message Forwarding on the iPhone for this Mac.")
    else:
        print("Automation permission: FAILED —", err)
        print(hint_for(err))
    print("Note: brand-new recipients generally work without Contacts, but saving the number in "
          "Contacts is the safe path if a send is rejected.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send SMS/iMessage/RCS via macOS Messages (iPhone Text Message Forwarding)."
    )
    parser.add_argument("--to", help="phone number: 010-1234-5678 / 01012345678 / +821012345678")
    parser.add_argument("--message", help="message body")
    parser.add_argument("--body-file", help="read message body from a file (multiline/Korean safe)")
    parser.add_argument("--service", choices=["auto", "sms", "imessage", "rcs"], default="auto",
                        help="auto: let Messages route (iMessage→RCS→SMS) — default")
    parser.add_argument("--dry-run", action="store_true", help="print what would be sent, send nothing")
    parser.add_argument("--doctor", action="store_true", help="run diagnostics, send nothing")
    args = parser.parse_args()

    if args.doctor:
        doctor()
        return 0

    if not args.to:
        parser.error("--to is required")
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            message = f.read()
    elif args.message:
        message = args.message
    else:
        parser.error("need --message or --body-file")

    number = normalize_number(args.to)
    if not re.match(r"^\+\d{8,15}$", number):
        print(f"Invalid number after normalization: {number!r} — pass digits or +8210...", file=sys.stderr)
        return 1

    accounts = discover_accounts() if args.service != "auto" else {}
    account_id = account_for(accounts, args.service)

    if args.dry_run:
        print(f"Recipient: {number}")
        if account_id:
            print(f"Account: {args.service} ({account_id})")
        print(f"Message ({len(message)} chars): {message!r}")
        print("--- AppleScript ---")
        print(build_script(number, message, account_id))
        return 0

    ok, err = attempt(number, message, account_id)
    if not ok:
        # fallback: chat-based send (only works when a chat with this number already exists)
        rc2, _, err2 = run_osascript(build_chat_script(number, message))
        if rc2 == 0:
            print(f"Sent via chat to {number}")
            return 0
        print(f"{args.service} error: {err}", file=sys.stderr)
        print("chat fallback error:", err2, file=sys.stderr)
        print(hint_for(err), file=sys.stderr)
        return 1
    route = f" via {args.service}" if args.service != "auto" else ""
    print(f"Sent{route} to {number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
