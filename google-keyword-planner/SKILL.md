---
name: google-keyword-planner
description: >
  Query Google Ads Keyword Planner via the user's authenticated Chrome (CDP port
  9222) — no official API, no Ads spend. Drives the "새 키워드 찾기 / Discover new
  keywords" flow, submits seed keywords, and scrapes the results table (keyword,
  monthly search-volume range, competition, top-of-page bid). Use when the user
  wants Google Keyword Planner data for ASO/keyword research — "키워드 플래너로
  검색량", "KP로 키워드 뽑아줘", "keyword planner volume". Free but CDP-fragile.
  For reliable per-country volume prefer the dataforseo skill (`volume --geo`).
---

# Google Keyword Planner (CDP)

Borrows the user's logged-in Chrome (port 9222) to drive Keyword Planner. No
official API and no ad spend required. Read-only: submits seeds and scrapes
results; never creates or saves a plan.

## Preconditions
- Chrome running with `--remote-debugging-port=9222`.
- Logged into a **Google Ads account with Keyword Planner access** (verified
  account: `830-864-6170` / gksrkdls1982). The account's default location is
  대한민국 and UI language is Korean — selectors are written for the Korean UI.
- **Volume shows as ranges** (e.g. `100~1천`) unless the account actively spends —
  exact numbers require active campaigns. This is a Google limitation, not a bug.

## Usage
```bash
cd ~/.claude/skills/google-keyword-planner
node scripts/kp.mjs gunpla "gundam model kit"          # account default location (대한민국)
node scripts/kp.mjs 건프라 프라모델 도색               # Korean seeds
node scripts/kp.mjs gunpla --geo US --json             # (best-effort location targeting — see below)
```
Flags: `--geo US|KR|JP|GB|DE|FR|CA|AU|IN|ID|TW|BR` · `--lang ko|en|ja` ·
`--limit N` · `--json`.

## ⚠️ Location targeting is best-effort
`--geo` / `--lang` drive Keyword Planner's location/language pickers, but Google's
obfuscated Material dialog is fragile and the change **often fails and silently
falls back to the account default location** (a warning is printed; data is still
returned, just at the default geo). Do **not** rely on `--geo` for accurate
per-country volume.

**For reliable per-country search volume, use the `dataforseo` skill instead:**
`python3 ~/.claude/skills/dataforseo/scripts/dfs.py volume "gunpla" --geo US` —
that hits Google Ads data via API (per-country, exact numbers) with no CDP fragility.

## What it returns
`keyword | monthly volume (range) | competition (낮음/중간/높음) | bid low | bid high`,
plus the keyword ideas Keyword Planner expands from your seeds.

## Notes
- Volume here is web search volume — a proxy for in-store intent (same caveat as
  any KP data). For in-Play intent use google-play-scraper `suggest`; post-launch
  use Play Console Search Analytics.
- If the results table doesn't appear it's usually a transient rate-limit — retry.
- Selectors target the Korean Ads UI; if Google changes the UI, re-run a DOM probe
  to update the seed input (`aria-label="검색어 입력"`), the `결과 보기` trigger, and
  the `[role="row"]` results rows.
