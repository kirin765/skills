---
name: telegram-bot
description: Send Telegram messages and notifications using the bot configured in the project's .env file. Use this skill whenever the user asks to send a Telegram message, notification, alert, or wants to notify someone via Telegram — even if they just say "send a message" or "let me know on Telegram" without explicitly mentioning the skill. Also trigger when the user says things like "텔레그램으로 보내줘", "텔레그램 알림", "메시지 보내줘" in Korean.
---

# Telegram Bot Messenger

Send messages and notifications via the Telegram Bot API using credentials from the project's `.env` file.

## How it works

The project already has a `TelegramService` class that handles message sending, chunking, and error handling. This skill wraps that service for quick ad-hoc messaging from Claude.

## Required environment variables

These live in the project's `.env` file:

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API token from @BotFather |
| `TELEGRAM_CHAT_ID` | Target chat/group ID |
| `TELEGRAM_BASE_URL` | API endpoint (default: `https://api.telegram.org`) |

## Sending a message

Write and run an inline Python script. The project's `TelegramService` handles everything — long message splitting (3500 char chunks), error handling, and timeouts.

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.telegram_service import TelegramService

svc = TelegramService()
if not svc.is_configured():
    print("Telegram is not configured. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    sys.exit(1)

message = """Your message here"""
sent = svc.send_message(message)
print(f"Sent {sent} message(s)")
```

## Guidelines

- Always confirm the message content with the user before sending, unless they gave you the exact text.
- If sending a report or structured data, format it readably — Telegram supports basic markdown but keep it simple (bold with `*`, code with backticks).
- The service auto-splits messages over 3500 characters, so long messages are fine.
- Run the script from the project root directory so `src/` is importable.
- If `.env` is missing Telegram credentials, tell the user what they need to set up.
