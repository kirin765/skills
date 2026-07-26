---
name: tistory-naver-crosspost-v3
description: |
  v3: Cross-post a blog article to Naver Blog and Tistory with a split strategy — Naver is
  driven via Chrome CDP (port 9222) all the way through 공개 발행 (no manual step left),
  while Tistory involves NO CDP work at all: the post is saved as a queue JSON per
  ~/.gemini/config/skills/tistory-post/references/agent-queue-guide.md and the standalone
  tistory-scheduler is triggered once via its hook command. Trigger on "티스토리/네이버 v3",
  "tistory-naver-crosspost-v3", "크로스포스트 v3", "네이버 발행까지 + 티스토리 큐".
---

# Tistory + Naver Blog Crosspost v3 (Naver full publish + Tistory queue)

## What changed vs v2

| | v2 | v3 |
|---|---|---|
| Naver | fills everything, leaves publish panel open, **user clicks 발행** | sets 공개(전체공개) and **clicks 발행 itself** — fully finished |
| Tistory | CDP drives the editor (login, TinyMCE, DKAPTCHA…) | **no CDP** — writes a job JSON to `~/.tistory-queue/pending/` and fires the scheduler hook; a detached daemon publishes without the agent |

**v3 auto-publishes Naver deliberately** (user decision 2026-07-26) — v2's "don't auto-click 발행" rule does not apply here. Category stays whatever the editor defaults to (usually 낙서장); if a specific category matters, use v2 or fix it after publish.

> **Image + text only — no video.** Exactly one static hero PNG per platform; no video-embed path.

## The two paths

### 1. Naver Blog (CDP, full publish)

Same proven v2 flow — open `GoBlogWrite.naver`, dismiss continue-popup, type title, insert hero PNG via 사진 toolbar + native filechooser, type body line-by-line with `keyboard.type` (never paste — MacRoman mojibake; never bulk insertText — autoformat caret-jump; entities decoded via `decodeEntities`), fill tags in the publish panel (spaces stripped — Naver commits on space) — **then v3 continues**: select the 공개/전체공개 radio, click the final 발행 button (`button[class*='confirm_btn']`, fallback: exact-text 발행 that isn't the panel-open `publish_btn`), wait for navigation to the published post, and log the post URL. Screenshot: `/tmp/naver-crosspost-published.png`.

### 2. Tistory (queue JSON + hook, NO browser)

Follows `~/.gemini/config/skills/tistory-post/references/agent-queue-guide.md` exactly:

1. Build the job JSON — `title`, `source` (live URL or **absolute** local HTML path with an `<article>` tag), `hero` (**absolute path to a real `.png`** — SVG/JPG/WebP rejected), optional `tags` array, optional `scheduledAt` (ISO 8601 `+09:00`; omitted unless `--scheduled-at` given), optional `tistoryUrl` (only when explicitly passed).
2. Save it as `~/.tistory-queue/pending/post-YYYYMMDD-<slug>.json` (folder auto-created, JSON re-parsed from disk as a validity self-check).
3. **Fire the hook** — `node ~/.gemini/config/skills/tistory-post/scripts/tistory-scheduler.mjs hook` with **no path argument**. The command returns in <0.1s; a detached background daemon does the actual Tistory login/publish with zero agent involvement. Do NOT wait for or monitor the publish — progress lives in `~/.tistory-queue/logs/`.

**Why hook gets NO path argument:** `hook <path>` runs `addJob`, which *copies* the file into `pending/`. Our JSON is already saved there, so passing its path would enqueue the same post twice → double publish. Bare `hook` only triggers the run. If you ever hand-write a JSON *outside* `pending/`, then (and only then) pass its path.

## Usage

```bash
node scripts/crosspost.mjs both \
  --source "https://sajangbu.com/blog/<slug>"   # or /abs/path/to/post.html \
  --hero  "/abs/path/to/public/blog-images/png/<slug>.png" \
  --title "..." \
  --tags  "tag1,tag2,tag3,tag4,tag5"
```

| mode | does |
|---|---|
| `both` (default) | Naver full publish **first**, then Tistory queue + hook |
| `naver` | Naver only, through 발행 |
| `tistory-queue` (alias `tistory`) | queue JSON + hook only — no browser at all |
| `naver-tags` | clear + refill Naver tags on an existing open publish panel (no publish) |

Optional flags: `--slug` (queue filename; default derived from source), `--scheduled-at "2026-07-27T09:00:00+09:00"` (Tistory reserved publish), `--no-hook` (queue without triggering — e.g. batch-queue several posts, hook once at the end), `--tistory-url`, `--naver-url`.

**Order is deliberate: Naver first, Tistory hook last.** The hook's detached daemon drives the same CDP Chrome (port 9222) as the Naver automation — firing it before/while the Naver pass runs would have two Playwright drivers fighting over one browser. Queue validation (hero exists, `.png`, `<article>` present) still runs **up front** so a bad Tistory input fails before the irreversible Naver publish.

## Preconditions

1. **Naver Blog logged in** on the CDP Chrome (port 9222). No Naver login automation exists. The script auto-launches `chrome-cdp-profile` Chrome if 9222 is down and auto-opens a blank tab if the browser has zero page targets (`Browser context management is not supported` guard).
2. **Hero PNG exists on disk** — required even for Tistory-only runs (queue spec mandates it).
3. **Source reachable** — live URL responding, or local file wrapping its body in `<article>`.
4. **Tistory login is NOT this skill's problem** — the background scheduler's own crosspost script handles Kakao login/DKAPTCHA. If a queue item lands in `~/.tistory-queue/failed/`, inspect its JSON (`error` field) and the logs, fix, and move it back to `pending/` (or re-run this skill).

## After running — what to tell the user

1. Naver: published post URL (from `[naver-publish] ✅ PUBLISHED → …`) or the failure screenshot path.
2. Tistory: the queued JSON path + "발행 Hook을 전송해 백그라운드에서 에이전트 없이 자동 진행 중" + logs at `~/.tistory-queue/logs/`.
3. Do **not** keep the session open waiting for the Tistory publish — fire and forget is the contract.

## Failure modes

| symptom | cause | fix |
|---|---|---|
| `[naver-publish] 공개 radio not found` | publish-panel DOM changed | it publishes with the panel's current (sticky) visibility — verify the post; update the label matcher |
| `[naver-publish] final 발행 button not found` | `confirm_btn` hash rotated AND text lookup missed | post is still a draft with panel open — click 발행 manually; probe `document.querySelectorAll("button[class*='confirm']")` and update |
| `[naver-publish] no navigation within 25s` | slow publish or an unhandled popup | check `/tmp/naver-publish-TIMEOUT.png`; the post may actually be live — check the blog before re-running |
| queue JSON in `failed/` with `Missing required fields` | title/source/hero absent in JSON | shouldn't happen via this script (validated up front); fix JSON, move back to `pending/`, `node …/tistory-scheduler.mjs hook` |
| Tistory published twice | someone passed the pending-file path to `hook` | never `hook <path>` for a file already in `pending/` — see the no-path rule above |
| hook printed nothing / scheduler missing | `~/.gemini/config/skills/tistory-post/scripts/tistory-scheduler.mjs` moved | script dies with the expected path — fix `SCHEDULER` const |
| Naver body mojibake / literal `&#x27;` / scrambled lines | someone reverted typing→paste or type→bulk insertText, or dropped `decodeEntities` | keep `keyboard.type` + `decodeEntities` — full history in v2 SKILL.md |

## Don't do this

- **Don't touch Tistory via CDP in this skill.** No opening `/manage/newpost/`, no TinyMCE, no DKAPTCHA. That whole surface belongs to the background scheduler.
- **Don't pass the pending JSON's path to `hook`** (double-enqueue — see above).
- **Don't wait for the Tistory publish to finish.** Hook is fire-and-forget by contract.
- **Don't paste or bulk-insert Naver body/title text.** `keyboard.type` only (v2 gotchas all still apply).
- **Don't store credentials.** Naver uses the existing CDP session; Tistory login lives in the scheduler's own flow.

## Resources

- `scripts/crosspost.mjs` — main entry
- `references/aeo-template.md` — the AEO structure the SOURCE article must already follow (this skill copies verbatim)
- Queue spec: `~/.gemini/config/skills/tistory-post/references/agent-queue-guide.md`
- Naver editor selector deep-dive + history: `tistory-naver-crosspost-v2/SKILL.md`
