---
name: ntfy-notify
description: Send ntfy.sh push notifications to the user's phone — task done ✅, waiting-on-user/question ❓, error ❌. Credentials ALWAYS from ~/.config/ntfy.env (NTFY_TOPIC), never the current project's env. Trigger whenever the user asks to send an ntfy/push/phone notification — "ntfy", "알림 보내줘", "폰으로 알림", "핸드폰 알림" — or when a workflow rule requires a work-complete / blocked-on-user / error phone notification.
---

# ntfy Notifier

Send push notifications via [ntfy.sh](https://ntfy.sh). Works from ANY project — no project code needed. Shares the same topic as the deepseek-harness (dsh) `ntfy-notify` plugin, so dsh and opencode land in one feed on the phone.

## Credentials

Always from `~/.config/ntfy.env`, never the current project's `.env*`:

```bash
NTFY_TOPIC=...   # publish/private topic — already set, matches dsh's topic
# optional overrides:
# NTFY_BASE=https://ntfy.sh
# NTFY_CLICK=http://...   # URL opened when tapping the notification (e.g. LAN dashboard)
```

Do NOT invent or print the topic value; it is read from the file.

## HTTP header rule (critical, learned from dsh)

ntfy HTTP headers are Latin-1. Unicode in the `Title` header is NOT decoded — even percent-encoded `%E2%9C%85` is stored literally. So:

- **`Title` header: ASCII only** — e.g. `opencode: task done`.
- **Unicode/emoji go in the message body** (UTF-8) — e.g. `✅ done`.
- The notification icon is chosen with the **`Tags` header ASCII shortcode**: `white_check_mark`→✅, `grey_question`→❓, `x`→❌, `warning`→⚠️, `information_source`→ℹ️.

## Sending

```bash
TOPIC=$(grep '^NTFY_TOPIC=' ~/.config/ntfy.env | sed 's/^NTFY_TOPIC=//;s/^"//;s/"$//')
NTFY_BASE=$(grep '^NTFY_BASE=' ~/.config/ntfy.env | sed 's/^NTFY_BASE=//;s/^"//;s/"$//')
NTFY_BASE=${NTFY_BASE:-https://ntfy.sh}
# write the message to a file, then curl -d @file — avoids shell-quoting issues with unicode
cat > /tmp/ntfy-msg.txt <<'EOF'
✅ opencode: task done
short status — what changed, what's next.
EOF
curl -s -H "Title: opencode: task done" -H "Tags: white_check_mark" \
  -H "Click: ${NTFY_CLICK:-https://ntfy.sh}" \
  -d @/tmp/ntfy-msg.txt "${NTFY_BASE}/${TOPIC}"
```

Response `{"id":...}` means OK. `{"error":...}` (e.g. 400, 403) means the topic/base is wrong or the topic requires auth — report it.

### Type → Tags/Template

| Type | `Tags` | Title (ASCII) | Body prefix |
|---|---|---|---|
| Task done | `white_check_mark` | `opencode: task done` | ✅ |
| Waiting on user / question | `grey_question` | `opencode: question` | ❓ |
| Error | `x` | `opencode: error` | ❌ |
| Warning | `warning` | `opencode: warning` | ⚠️ |
| Plain note | `information_source` | `opencode: note` | ℹ️ |

## Guidelines

- Confirm message content with the user before sending, unless they gave the exact text or a standing rule (work-complete / blocked / error notification) applies.
- Style: ASCII title + status shortcode icon, body 2–4 lines, skimmable on mobile.
- Long messages over ~3500 chars: split, or truncate — phones show a short preview anyway.
- For unattended/agent-loop runs, only notify on meaningful events (done after a long run, blocked-on-user, error) — not every turn.
