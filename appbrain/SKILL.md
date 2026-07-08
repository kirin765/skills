---
name: appbrain
description: >
  Google Play competitor & market intelligence from the AppBrain API — for ANY
  Android app: estimated install counts (exact number + bracket + recent installs),
  the SDKs/libraries an app ships (ad networks, analytics, IAP, engines — the
  monetization/tech stack), ratings + star histogram + review counts, permissions,
  developer/category metadata, plus app search & discovery by keyword. Use whenever
  the user wants to size or scout a COMPETITOR Android app before building — "이 앱
  다운로드 얼마나 돼", "경쟁 앱 설치수", "이 앱 무슨 SDK/광고 붙였어", "이 앱 어떤
  라이브러리 써", "이 니치에 어떤 앱들 있어", "how many installs does <app> have",
  "what ads/SDK does <app> use", "find Android apps for <keyword>". Google-Play-only.
  Reads the key from this skill's .env; competitor lookups spend credits (500/mo free).
  Distinct from: sonar (keyword difficulty/popularity + revenue $), dataforseo
  (keyword volume/ranked-keywords), google-play-scraper (raw listing scrape, no SDK/install-estimate).
---

# AppBrain — Google Play app intelligence

Google-Play-only market data: **install estimates, used SDKs/libraries, ratings,
and app search**. This is the "how big is this competitor and how do they monetize"
layer your other tools can't give — google-play-scraper only exposes Google's coarse
`10M+` bracket and no SDK list; Play Console only covers *your own* apps.

Key in `.env` (`APPBRAIN_API_KEY`, format `<clientid>.<secret>`) — gitignored.

## ⚠️ Metering
Your **own** apps are free; **competitor / other apps consume credits** (500/mo on
the free tier, top up with AppBrain Intelligence from ~$57.50/mo). Each `getapp` /
`search` call spends credits — plan the set of lookups, don't loop blindly.

## Usage
```bash
cd ~/.claude/skills/appbrain
python3 scripts/appbrain.py getapp com.whatsapp --libs        # one app: installs + SDKs
python3 scripts/appbrain.py getapp com.despdev.quitzilla       # (raw library IDs, cheaper)
python3 scripts/appbrain.py search "habit tracker" --limit 10  # niche discovery
python3 scripts/appbrain.py libraries                          # SDK/library catalog (id→name)
python3 scripts/appbrain.py countries
```
Add `--json` for raw output. `--country US` (default). `getapp --summary` for a
lighter payload; `getapp --libs` resolves library IDs to human names (one extra call).

## Commands → endpoints (base `https://api.appbrain.com/v2`)
| command | endpoint | returns |
|---|---|---|
| `getapp <pkg>` | `/info/getapp` | `estimatedDownloads`, `downloadsCategory` (bracket), `estimatedRecentDownloads`, `rating` + `rating{1..5}StarCount`, `ratingCount`, `libraries` (SDK IDs), `permissions`, category, developer, apkSize, update time |
| `search <query>` | `/info/search` | list of matching apps, each with the full `getapp` field set |
| `libraries` | `/info/getlibraries` | dictionary of known libraries (id, name, tags) — resolves the SDK IDs from `getapp` |
| `countries` | `/info/getcountries` | supported country codes |

## How to use it well
- **Size a competitor:** `getapp <pkg>` → read `estimatedDownloads` + `estimatedRecentDownloads`
  (momentum) + the star histogram. The bracket (`downloadsCategory`) is Google's own; the
  estimate is AppBrain's finer number.
- **Reverse the monetization stack:** `getapp <pkg> --libs` lists the SDKs — spot the
  ad networks (AdMob, AppLovin, ironSource…), analytics (Firebase, Adjust…), engines
  (Unity, Flutter, ExoPlayer…) an incumbent ships. Tells you how they make money before you build.
- **Scout a niche:** `search "<keyword>"` → rank the field by installs to see how crowded/
  winnable it is and who the leaders are; then `getapp` the top few for depth.

## Where this fits with the other skills
- **appbrain** (this) — Android install estimates + SDK/library stack + app discovery, any app.
- **sonar** — Play/App-Store keyword **difficulty + popularity** and monthly **revenue $** estimates.
- **dataforseo** — keyword search volume + a Play app's ranked keywords + keyword competitors.
- **google-play-scraper** — free raw listing scrape (title, description, reviews) — no install estimate, no SDK list.

A natural pre-build flow: sonar (which keyword is winnable) → appbrain `search` (who's in the
niche + how big) → appbrain `getapp --libs` (how the leaders monetize) → sonar `revenue` (what they earn).
