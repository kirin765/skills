---
name: sonar
description: >
  App-store keyword & revenue intelligence from the Sonar API (trysonar.app) — for
  Google Play AND the App Store: a real per-keyword DIFFICULTY score (0–100, how hard
  to rank) + POPULARITY/search-demand score (0–100) + how many apps rank, keyword
  autocomplete/suggestions, and a monthly REVENUE $ estimate for ANY app (stateless).
  Use whenever the user asks "이 키워드 랭크하기 어려워?", "키워드 난이도/인기도",
  "이 앱 월매출 얼마", "경쟁 앱 매출 추정", "how hard is this keyword to rank",
  "keyword difficulty for the app store", "how much revenue does <app> make",
  "app store keyword research". Android-first (default store=android). Bearer key in
  this skill's .env; each call spends credits (search ~10, metrics ~1/kw; 50 free on signup).
  Pick sonar (not dataforseo) when you need an app-store keyword DIFFICULTY score or a
  revenue $ figure — DataForSEO's difficulty is web-SERP based, and it has no revenue estimate.
---

# Sonar — ASO keyword difficulty/popularity + revenue estimates

The two signals your other tools structurally lack:
1. a **Play/App-Store keyword difficulty + popularity score** (DataForSEO's
   `keyword_difficulty` is web-SERP/backlink based — wrong signal for app-store ranking), and
2. a **monthly revenue $ estimate for any app** (nothing else in the stack estimates revenue).

Every command here is **stateless** — works on any keyword/app, no account setup.
Bearer key in `.env` (`SONAR_API_KEY`, prefix `aso_`) — gitignored. Base API + CLI + MCP
ship on every plan.

## ⚠️ Metering
Each call spends credits: `keywords` (search) ~10, `metrics` ~1 per keyword, `suggest`/
`revenue`/`reviews` light. 50 free on signup, prepaid packs from $10, or Full plan
1,000 req/day. Prefer `metrics` (1/kw) over `keywords` (10) once you know the terms.

## Usage
```bash
cd ~/.claude/skills/sonar
python3 scripts/sonar.py keywords "sleep tracker"                    # research: fan out + score (~10cr)
python3 scripts/sonar.py metrics "sleep tracker" "habit tracker"     # score known kws (1cr each)
python3 scripts/sonar.py suggest "recipe"                            # raw autocomplete (cheap, no score)
python3 scripts/sonar.py revenue com.northcube.sleepcycle            # monthly $ for any app
python3 scripts/sonar.py reviews com.northcube.sleepcycle --stars low
```
Defaults: `--store android` (or `ios`), `--country us`. Add `--json` for raw output.
For KR: `--country kr`. For iOS, the `id`/`store_id` is the numeric App Store id.

## Commands → endpoints (base `https://trysonar.app/api/v1`)
| command | endpoint | returns |
|---|---|---|
| `keywords <q>` | `/keywords/search` | related keywords, each with `difficulty` (0–100), `popularity` (0–100), `results_count` — ~10 credits, fans out to ideas |
| `metrics <kw...>` | `/keywords/metrics` | same three scores for the exact keywords you name (up to 25) — ~1 credit/kw |
| `suggest <seed>` | `/keywords/suggestions` | raw store autocomplete terms + priority (no difficulty) — cheap |
| `revenue <id...>` | `/apps/revenue` | monthly revenue estimate + monetization `model` for any app (up to 25) |
| `reviews <id>` | `/apps/reviews` | store reviews; `--stars low` (bug signals) / `high` (positive copy) |

## Reading the scores
- **difficulty** 0–100, higher = harder to rank. **popularity** 0–100, higher = more search
  demand. The sweet spot is **high popularity + low difficulty**.
- Scores are **modelled**, not clickstream (iOS pulls Apple Search Ads; Play is inferred) —
  trust *relative* comparisons between candidate keywords for go/no-go, not absolute counts.
- `revenue` is an estimate with the usual MAPE — directional, but it's a real $ figure your
  other tools don't produce; check the `model` (subscription / iap / ads / paid).

## Where this fits with the other skills
- **sonar** (this) — app-store keyword difficulty/popularity + revenue $, any app/keyword.
- **appbrain** — Android install estimates + the SDK/library stack a competitor ships.
- **dataforseo** — keyword search *volume* (web), a Play app's ranked keywords, keyword competitors.
- **google-play-scraper** / **google-keyword-planner** / **naver-api** — free scrape / KP volume / KR demand.

Pre-build flow: sonar `keywords`/`metrics` (winnable keyword?) → appbrain `search`+`getapp`
(who's there, how big, how they monetize) → sonar `revenue` (what the leaders earn).
