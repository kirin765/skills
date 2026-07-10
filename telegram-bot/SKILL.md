---
name: telegram-bot
description: Send Telegram messages and notifications via the user's bot. Credentials ALWAYS come from ~/niche-finder/.env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID), regardless of the current project. Trigger whenever the user asks to send a Telegram message, alert, or notification — "텔레그램으로 보내줘", "텔레그램 알림", "메시지 보내줘" — or when a workflow rule requires a work-complete / blocked-on-user notification.
---

# Telegram Bot Messenger

Send messages via the Telegram Bot API. Works from ANY project — no project code needed.

## Credentials

Always from `~/niche-finder/.env`, never the current project's `.env*`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## Sending

```bash
BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' ~/niche-finder/.env | sed 's/^TELEGRAM_BOT_TOKEN=//;s/^"//;s/"$//')
CHAT_ID=$(grep '^TELEGRAM_CHAT_ID=' ~/niche-finder/.env | sed 's/^TELEGRAM_CHAT_ID=//;s/^"//;s/"$//')
# write response to a file (-o), then read it — avoids stdout-blocking hooks
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
msg = '''*Title* ✅
short status — what changed, what's next.
'''
print(json.dumps({'chat_id': '$CHAT_ID', 'text': msg, 'parse_mode': 'Markdown'}))
")" -o /tmp/tg-result.json
python3 -c "import json; r=json.load(open('/tmp/tg-result.json')); print('OK' if r.get('ok') else r)"
```

## Guidelines

- Confirm message content with the user before sending, unless they gave the exact text or a standing rule (work-complete / blocked notification) applies.
- Style: `*bold*` title + status emoji (✅ done, ⏸ waiting, ⚠ issue), 2–4 lines, skimmable on mobile.
- Telegram Markdown is picky — keep formatting simple (bold `*`, backticks).
- Messages over ~3500 chars: split into multiple sendMessage calls.
