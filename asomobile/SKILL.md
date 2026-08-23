---
name: asomobile
description: Get ASO keyword & market intelligence from the ASOMobile API — search volume/traffic, keyword difficulty/competition (CI, KEI, ASA), keyword suggestions, an app's ranked keywords, keyword rank history, competitor apps, app metadata, category rankings, and organic-download estimates for ANY iOS or Google Play app (3M+ apps, 60+ countries). Use this whenever the user wants keyword research, search volume for an app-store term, how hard a keyword is to rank for, which keywords an app (theirs OR a competitor's) ranks for, who an app's competitors are, app-store keyword suggestions, or to find high-traffic low-competition keywords to target. This is the competitor/market ASO layer — pick it (not appfigures, which is the user's own-app analytics only; not aso-audit, which rewrites listing copy) whenever the question needs keyword volume, difficulty, or competitor keyword data. Trigger on "검색량", "키워드 난이도", "키워드 추천", "경쟁 앱 키워드", "이 키워드 트래픽", "ASO 키워드 리서치", "what keywords does <app> rank for", "keyword difficulty", "search volume for <term>".
---

# ASOMobile API

ASO keyword & market data: search volume, keyword difficulty, suggestions, ranked
keywords, competitors, rankings, and organic-download estimates across the App Store
and Google Play. Use the bundled client — it handles auth and ASOMobile's async flow.

## How the API works — async ticket flow (important)

Every data endpoint is **two steps**: a Request returns a `ticket_id`, then you poll a
Result endpoint with that id until the computation finishes. The helper does both for you:

```bash
python scripts/asomobile.py "<request_path_with_query>"
```

It fires the request, reads `ticket_id`, then polls `{path}/result?ticket_id=N` until the
data is ready, and prints the result JSON. Flags: `--method POST --data '{...}'` for POST
endpoints, `--timeout`/`--interval` for slow results, `--out file.json`, `--compact`.

**Auth & quota:** token from `ASOMOBILE_TOKEN` env, else a baked-in default. Usage is
**metered** — each request spends account tokens. `403 "Request limit reached"` means the
quota is used up (check/top up at app.asomobile.net/api-dashboard). Because calls cost
quota, be deliberate: don't loop over many keywords/apps without the user's okay.

## Conventions (every endpoint)

- **platform**: `ANDROID` (then `app_id` = package name, e.g. `com.kiwankim.tapgame`) or
  `IOS` (then `app_id` = `id` + store number, e.g. `id284882215`, plus `ios_device=IPHONE|IPAD`).
- **country**: ISO code — `US`, `KR`, `JP`, …
- **keyword**: the search phrase (URL-encode spaces).
- **dates** (keyword-rank): millisecond epoch (`from_date`, `to_date`).

## Endpoints — keyword & market research

The richest, most-used call is **keyword-check** — it's the core "is this keyword worth
targeting?" lookup.

| Endpoint | Request path | Returns |
|---|---|---|
| **keyword-check** | `/keyword-check/?platform=&country=&keyword=` | `traffic` (search volume), `ci` (competition index), `kei` (keyword efficiency), `asa`, `apps_count`, `suggestions`, `top_apps`. The go-to for keyword volume + difficulty. |
| **keyword-suggest** | `/keyword-suggest` (POST body) | autocomplete/related keyword ideas |
| **keyword-rank** | `/keyword-rank/?app_id=&platform=&country=&keyword=&from_date=&to_date=` | an app's position history for one keyword |
| **keyword-monitor** | `/keyword-monitor/?app_id=&platform=&country=` | tracked-keyword positions for an app |
| **app-keywords** | `/app-keywords/?app_id=&platform=&country=` | the keywords an app ranks for (works for competitors too) |
| **app-keywords (multi-country)** | `/app-keywords/multiple-countries` (POST) | the above across several countries |
| **world-wide-check** | `/world-wide-check` (POST) | one keyword's metrics across many countries |

## Endpoints — app & competitor intelligence

| Endpoint | Request path | Returns |
|---|---|---|
| **app-profile** | `/apps/app/profile?app_id=&platform=&country=` | app metadata: title, description, visual assets |
| **app-competitors** | `/apps/competitors/?app_id=&platform=&country=` | competitor apps for a given app |
| **app-ranking** | `/app-ranking/?app_id=&platform=&ios_device=` | the app's category / chart rankings |
| **organic-downloads** | `/organic-downloads?app_id=&platform=&country=` | estimated organic download volume |

## How to use it well

- **Find keywords worth targeting:** run `keyword-check` on candidate terms; favor high
  `traffic` with low `ci`/`apps_count`. `kei` already blends volume vs competition — a high
  `kei` is the sweet spot. Surface these as a ranked shortlist, not raw JSON.
- **Mine a competitor's keywords:** `app-competitors` to find rivals, then `app-keywords`
  on each to see what they rank for — those are keyword gaps to consider.
- **Expand a seed:** `keyword-suggest` (or the `suggestions` field from `keyword-check`)
  to widen the candidate list, then `keyword-check` the promising ones.
- **Track movement:** `keyword-rank` / `keyword-monitor` for how a term's position changes over time.
- Each call costs quota, so plan the set of lookups, run them, then synthesize — rather than
  firing one-offs. For multi-keyword research, confirm the list with the user first.

## Where this fits with the other skills

- **asomobile** (this) — keyword volume/difficulty, suggestions, competitor keywords, market data for *any* app.
- **appfigures** — the user's *own* apps' performance (downloads, revenue, ratings). Own-account only.
- **aso-audit** — rewrites a listing's title/description/screenshots. Use asomobile's keyword data to *feed* an aso-audit.

A natural pipeline: asomobile (find the keywords) → aso-audit (put them in the listing) →
appfigures (watch downloads/ranks move).
