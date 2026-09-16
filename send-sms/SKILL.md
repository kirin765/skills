---
name: send-sms
description: Send SMS and iMessage from the Mac through the Messages app, relayed by the user's own iPhone (Text Message Forwarding) — no API, no extra cost, messages go out from the user's real number. Use whenever the user asks to send a 문자/SMS/문자메시지 to a phone number: "문자 보내줘", "SMS 보내줘", "iMessage 보내줘", "이 내용 010...로 문자로 보내줘", "send a text to ...", "send SMS to ...". Distinct from telegram-bot (Telegram chat) and gmail-mail (email).
---

# Send SMS / iMessage (macOS Messages + AppleScript)

Send text messages from the Mac through the Messages app. The Mac sends iMessage directly; SMS goes out via the paired iPhone (Text Message Forwarding), so the recipient sees the user's own number. No carrier API, no phone in hand, no cost beyond the normal SMS plan. iMessage recipients cost nothing. RCS is supported too when the carrier/recipient supports it.

One script, Python stdlib only: `scripts/send_sms.py`.

Modern macOS (15+) reworked the Messages scripting dictionary: `service`/`buddy` are now
`account`/`participant`, and `every account` is no longer enumerable (accounts are discovered
through existing chats). The script targets this model and auto-detects the machine's accounts.

## Setup (one-time)

1. **Text Message Forwarding** — iPhone: 설정 → 메시지 → 문자 메시지 전달 → check this Mac. Both devices: same Apple ID, iPhone on and on the same Wi-Fi (or Handoff). Without this, iMessage works but SMS fails.
2. **Automation permission** — the first `osascript` run pops a "… wants to control Messages" prompt; grant it. If missed: System Settings → Privacy & Security → Automation → allow the terminal/agent process to control Messages. If the agent runs from SSH (no GUI session), Messages control fails — it must run in the user's Mac session.
3. **Contacts** — brand-new numbers generally work without a saved contact (participant lookup auto-creates), but if a send is rejected, save the number in Contacts first. Contact *names* are not supported — pass a number.

Verify everything once with `python scripts/send_sms.py --doctor` before the first real send.

## Usage

```bash
python scripts/send_sms.py --to 010-1234-5678 --message "안녕하세요"
python scripts/send_sms.py --to 010-1234-5678 --body-file draft.txt   # long/multiline Korean text
python scripts/send_sms.py --to +821012345678 --service sms
python scripts/send_sms.py --to 010-1234-5678 --dry-run               # preview, nothing sent
python scripts/send_sms.py --doctor                                   # diagnostics
```

- Number formats accepted: `010-1234-5678`, `01012345678`, `+821012345678`, `821012345678` — normalized automatically.
- `--service auto` (default): let Messages route — iMessage when the recipient has it, otherwise RCS/SMS via the iPhone.
- `--service sms`: force the SMS account. `--service imessage`: force iMessage. `--service rcs`: force RCS. Forcing needs the account to exist (auto-detected from existing chats); if it can't be found the script falls back to auto routing.
- `--dry-run`: prints the exact AppleScript + recipient + message without executing. Use it for the confirmation step below.
- Send flow: `participant "<E.164>"` (auto-creates for new numbers) → on failure, chat-based send for numbers with an existing chat.
- "Sent" means handed to Messages — **delivery is asynchronous**. A green SMS needs the iPhone on and reachable; a failed delivery surfaces later in the Messages chat, not in the script exit code.

## The confirmation gate (mandatory)

A text message is outward-facing and cannot be taken back. Before sending:

1. Draft the message, then **show the user the recipient and the full text** and get explicit confirmation.
2. For anything non-trivial, run `--dry-run` first and show its output.
3. Never batch-send to a list or auto-reply to strangers without the user's explicit approval for each message.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `-1743` / "not authorized" | Automation permission missing — Setup 2 |
| `-10000` / "AppleEvent handler failed" | Known macOS 15+ Messages scripting regression. Retry once; if it persists, quit and relaunch Messages (must be signed in), then retry |
| iMessage works, SMS fails | Text Message Forwarding off — Setup 1 |
| Sent OK but nothing arrives | iPhone off / off Wi-Fi; SMS relays through it — retry with iPhone on |
| No SMS account in `--doctor` | Forwarding not enabled on this Mac (iPhone: 설정 → 메시지 → 문자 메시지 전달) |
