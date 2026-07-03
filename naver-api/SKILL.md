---
name: naver-api
description: Get real search-demand data from Naver DataLab (검색어트렌드) and Google Trends. Use this skill whenever the user asks about keyword research, search trends, 검색량, 네이버 트렌드, 구글 트렌드, Google Trends, 검색어 트렌드, 키워드 분석, interest over time, related/rising queries, interest by region/country, or wants to compare keyword popularity — for the Korean market (Naver) or globally/cross-country (Google Trends), even if they don't name a specific API. Also trigger when building reports or analyses that would benefit from search-demand data, or when comparing how a term trends in Korea vs other countries.
---

# Naver DataLab + Google Trends

Two standalone scripts for search-demand data. No pip installs, no project setup.

**Naver vs Google Trends — pick by audience:** Naver DataLab reflects the **Korean** market (where most search happens on Naver). Google Trends reflects **global / non-Korea** demand and lets you compare across countries. For "is X trending in Korea?" use DataLab; for "how does X trend worldwide / in the US / Korea vs Japan?" use Google Trends; for a full picture, run both and compare.

## Naver search trend (DataLab)

Hits the DataLab 검색어트렌드 endpoint directly (Python stdlib only):

```bash
python scripts/datalab_trend.py <keywords...>            # one group, last 12 months
python scripts/datalab_trend.py --group "name:kw1,kw2" --group "..." --unit week --weeks 26
```

Common flags: `--unit date|week|month`, `--start/--end YYYY-MM-DD`, `--device pc|mo`,
`--gender m|f`, `--ages 3,4,5`, `--out trend.json` (save raw JSON), `--json` (raw instead of a table).
Up to 5 keyword groups, 20 keywords each. Ratios are **relative** (0–100, peak = 100), not absolute volume —
for absolute monthly search counts use the Naver Ads keyword tool (see the `naver-searchad` skill).

**Credentials (one-time):** export `NAVER_DATALAB_CLIENT_ID` / `NAVER_DATALAB_CLIENT_SECRET`.
Register a free app at https://developers.naver.com/apps/ and add the `데이터랩(검색어트렌드)` API
under its API settings. A `401` means the keys are rejected — usually the app lacks the DATALAB scope.

Example output:

```
== 한글  [한글, 훈민정음] ==
  2025-10-01  100.00  ████████████████████
  2025-11-01   70.75  ██████████████
```

## Google Trends (global / cross-country)

Google Trends has **no public API**, and its internal endpoints reject anonymous calls with
`429`. So unlike DataLab, this path **borrows the user's logged-in Chrome over CDP** (real cookies +
residential IP).

**Preconditions:** Chrome running with `--remote-debugging-port=9222` and logged into Google, plus
Playwright available (`PLAYWRIGHT_PATH` env var if it isn't at `~/node_modules/playwright`). If port
9222 isn't up, the script prints the launch command and exits — relay it to the user; don't try to
work around it.

```bash
node scripts/google_trends.mjs <keywords...>                 # worldwide, last 12 months
node scripts/google_trends.mjs 아이폰 갤럭시 --geo KR          # compare up to 5, Korea
node scripts/google_trends.mjs chatgpt --time "today 5-y" --related --region
```

Flags: `--geo KR|US|JP|…` (omit = worldwide), `--time` (Google syntax: `"today 12-m"`, `"today 5-y"`,
`"now 7-d"`, `"all"`, or `"2024-01-01 2024-12-31"`), `--related` (TOP + RISING related queries),
`--region` (top regions/countries), `--cat N` (category id), `--out file.json`, `--json`.
Up to 5 keywords are compared on one 0–100 scale (peak across all = 100). A `*` on a period marks
Google's partial/incomplete latest bucket.

If it still `429`s through the session, the user is briefly rate-limited — wait a few minutes; don't
hammer it.

## Combining for richer analysis

1. **DataLab** — Is the keyword trending up or down in Korea?
2. **Google Trends** — How does it trend globally / in other countries?
3. **Ads Keyword Tool** (`naver-searchad` skill) — How many people actually search it monthly, in absolute numbers?
