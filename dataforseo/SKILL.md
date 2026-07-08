---
name: dataforseo
description: >
  Query DataForSEO's pay-as-you-go API for ASO/keyword data — keyword search
  volume + competition + CPC (Google Ads data), keyword ideas/suggestions,
  keyword difficulty scores, and the keywords a Google Play app ranks for +
  its app competitors. Use whenever the user wants programmatic keyword volume,
  keyword difficulty, competitor keyword analysis, or Play-app ranked-keyword
  data — e.g. "DataForSEO로 검색량 뽑아줘", "키워드 난이도", "이 앱이 랭크된
  키워드", "keyword volume via API", "app competitors". Paid per call (reads
  creds from this skill's .env). Distinct from the free stacks: google-play-scraper
  (Play scrape), naver-api (KR web volume), google-keyword-planner (CDP).
---

# DataForSEO ASO client

Pay-as-you-go REST API for keyword/ASO data. Synchronous `/live` endpoints.
Creds in `.env` (`DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`) — gitignored.

## ⚠️ Preconditions
- **Account must be verified** at https://app.dataforseo.com/ (unverified accounts
  get `40104: Please verify your account` on every data endpoint; only
  `balance` works before verification).
- **Balance must be funded.** Each call costs money (see cost table). Check with
  `dfs.py balance`.
- **No separate "App Data" setup.** DataForSEO Labs (incl. the Play `app-keywords` /
  `app-competitors` endpoints) is not a separate product, subscription, or dashboard
  toggle — it's the same account + login/password, just different endpoint paths, and
  the commands below already call them. There is nothing extra to enable.

## Usage

```bash
cd ~/.claude/skills/dataforseo
python3 scripts/dfs.py balance
python3 scripts/dfs.py volume "gunpla" "gundam model kit" --geo US
python3 scripts/dfs.py volume "건프라" "프라모델" --geo KR
python3 scripts/dfs.py app-keywords com.kiwan.pralog --geo US --limit 50
python3 scripts/dfs.py suggest "gunpla" --geo US --limit 50
python3 scripts/dfs.py difficulty "gunpla tracker" "gundam model kit" --geo US
python3 scripts/dfs.py app-competitors com.kiwan.pralog --geo US
```

Add `--json` for raw output, `--lang` to override the geo's default language.
`--geo` accepts `US KR JP GB DE FR CA AU IN BR ID TW` (mapped to location_code)
or a raw numeric location_code.

## Commands → endpoints
| command | endpoint | returns |
|---|---|---|
| `volume` | `keywords_data/google_ads/search_volume/live` | monthly volume, competition, competition_index, CPC (KP-equivalent, per-country) |
| `app-keywords` | `dataforseo_labs/google/keywords_for_app/live` | keywords a Play app ranks for + volume/difficulty |
| `suggest` | `dataforseo_labs/google/keyword_suggestions/live` | keyword ideas + volume |
| `difficulty` | `dataforseo_labs/google/bulk_keyword_difficulty/live` | keyword difficulty score (0–100) |
| `app-competitors` | `dataforseo_labs/google/app_competitors/live` | competing Play apps by keyword overlap |

## Cost (approx, per DataForSEO pricing)
Google Play Labs endpoints: ~$0.01/task + $0.0001/returned item. Google Ads
search volume: cheap per call (up to 1000 keywords/call). Verify current pricing
at dataforseo.com/pricing. Skill only spends on data endpoints, never on `balance`.

## Notes
- `volume` (Google Ads data) is **web search volume** — a proxy for in-store
  intent, same caveat as Google Keyword Planner. For true in-Play intent use
  google-play-scraper `suggest`, and post-launch use Play Console Search Analytics.
- Keyword difficulty (`difficulty`) is the signal the free ASO web tools
  (Checkaso etc.) gate behind their dashboards — here it's a direct API call.
