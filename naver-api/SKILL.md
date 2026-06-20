---
name: naver-api
description: Get real search-demand data from Naver APIs (DataLab 검색어트렌드, Web Search, Ads Keyword Tool, Shopping Insight) AND Google Trends. Use this skill whenever the user asks about keyword research, search trends, 검색량, 네이버 트렌드, 구글 트렌드, Google Trends, 검색어 트렌드, 키워드 분석, 쇼핑 인사이트, interest over time, related/rising queries, interest by region/country, or wants to compare keyword popularity — for the Korean market (Naver) or globally/cross-country (Google Trends), even if they don't name a specific API. Also trigger when building reports or analyses that would benefit from search-demand data, or when comparing how a term trends in Korea vs other countries.
---

# Naver API Tools

Query four Naver APIs for Korean market data.

Two ways to call them, pick by where you are:
- **Inside the `micro_niche_finder` project** (you can import `src/...`): use the ready-made service classes below — they read keys from `.env` and return typed objects.
- **Anywhere else** (this `brain` repo, a one-off question, no project on the path): use the **standalone search-trend script** — see [Standalone search trend](#standalone-search-trend-no-project-needed). It has no dependencies and works on its own.

For Korean **search trend / 검색어트렌드** questions when you're not in the project, reach for the standalone script first — it's the shortest path to real numbers.

**Naver vs Google Trends — pick by audience:** Naver DataLab reflects the **Korean** market (where most search happens on Naver). Google Trends reflects **global / non-Korea** demand and lets you compare across countries. For "is X trending in Korea?" use DataLab; for "how does X trend worldwide / in the US / Korea vs Japan?" use Google Trends; for a full picture, run both and compare. See [Google Trends](#google-trends-global--cross-country).

## Available APIs

| API | Service class | What it returns |
|-----|---------------|-----------------|
| **DataLab** | `NaverDataLabService` | Relative search trend over time (0-100 ratio per week/month) |
| **Web Search** | `NaverSearchService` | Web search results (title, link, description, total count) |
| **Ads Keyword Tool** | `NaverAdsKeywordService` | Monthly search volume (PC/mobile), competition index |
| **Shopping Insight** | `NaverShoppingInsightService` | Shopping category click trend over time |

## Credentials

All stored in `.env`. No need to handle keys manually — the service classes read them via `get_settings()`.

| API | Env vars |
|-----|----------|
| DataLab | `NAVER_DATALAB_CLIENT_ID`, `NAVER_DATALAB_CLIENT_SECRET` |
| Web Search | `NAVER_SEARCH_CLIENT_ID/SECRET` (falls back to DataLab keys) |
| Ads Keyword | `NAVER_ADS_CUSTOMER_ID`, `NAVER_ADS_API_KEY`, `NAVER_ADS_SECRET_KEY` |
| Shopping Insight | Uses DataLab keys + `NAVER_SHOPPING_CATEGORY_OPTIONS_JSON` |

## Standalone search trend (no project needed)

When you're not inside `micro_niche_finder`, call the bundled script. It hits the
DataLab endpoint directly (Python stdlib only — no pip install, no `src/` import):

```bash
python scripts/datalab_trend.py <keywords...>            # one group, last 12 months
python scripts/datalab_trend.py --group "name:kw1,kw2" --group "..." --unit week --weeks 26
```

Common flags: `--unit date|week|month`, `--start/--end YYYY-MM-DD`, `--device pc|mo`,
`--gender m|f`, `--ages 3,4,5`, `--out trend.json` (save raw JSON), `--json` (raw instead of a table).
Up to 5 keyword groups, 20 keywords each. Ratios are **relative** (0–100, peak = 100), not absolute volume —
for absolute monthly counts use the Ads Keyword Tool below.

**Credentials:** the script defaults to a working app (DATALAB scope enabled). To use different keys,
export `NAVER_DATALAB_CLIENT_ID` / `NAVER_DATALAB_CLIENT_SECRET` and they take precedence. A `401` means
the keys are rejected — the app on developers.naver.com must have the `데이터랩(검색어트렌드)` API added under
its API settings; a Client ID that exists in a different account or lacks the DATALAB scope will fail auth.

Example output:

```
== 한글  [한글, 훈민정음] ==
  2025-10-01  100.00  ████████████████████
  2025-11-01   70.75  ██████████████
```

## Google Trends (global / cross-country)

Google Trends has **no public API**, and its internal endpoints reject anonymous calls with
`429`. So unlike DataLab, this path **borrows the user's logged-in Chrome over CDP** (real cookies +
residential IP) — the same mechanism the project uses for other Naver/Google automation.

**Precondition:** Chrome running with `--remote-debugging-port=9222` and logged into Google. If port
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
hammer it (see rate-limit hygiene in the `cdp-anywhere` skill).

## Usage patterns

Run scripts from the project root so `src/` is importable. All services are synchronous (httpx with 20s timeout, tenacity retries).

### 1. Search trend (DataLab)

Get relative search popularity over time for a keyword group.

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.datalab_service import NaverDataLabService

svc = NaverDataLabService()
req = svc.build_request(
    group_name="학원 관리",
    queries=["학원 관리 프로그램", "학원 출결 관리", "학원 운영"],
    weeks=12,           # lookback window
    time_unit="week",   # "week", "month", or "date"
)
resp = svc.fetch(req)

for result in resp.results:
    print(f"== {result.title} ==")
    for point in result.data:
        print(f"  {point.period}: {point.ratio}")
```

**Optional filters:** `device="pc"` or `"mo"`, `ages=["1","2"]`, `gender="f"` or `"m"`.

### 2. Keyword volume (Ads Keyword Tool)

Get absolute monthly search counts and competition level.

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.naver_ads_keyword_service import NaverAdsKeywordService

svc = NaverAdsKeywordService()
if not svc.is_configured():
    print("Naver Ads API not configured — check .env")
else:
    req = svc.build_request(["학원 관리 프로그램", "출결 관리"], limit=5)
    metrics = svc.fetch(req)
    for m in metrics:
        print(f"{m.keyword}: PC {m.monthly_pc_searches}, Mobile {m.monthly_mobile_searches}, Total {m.monthly_total_searches}, Competition: {m.competition_index}")
```

The API returns related keywords too — `metrics` may include more keywords than you requested.

### 3. Web search results (Naver Search)

Get actual search results for a query.

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.domain.schemas import NaverSearchRequest

svc = NaverSearchService()
req = NaverSearchRequest(query="학원 출결 관리 프로그램", display=5, start=1, sort="sim")
resp = svc.fetch(req)

print(f"Total results: {resp.total}")
for item in resp.items:
    print(f"  {item.title} — {item.link}")
```

**Sort options:** `"sim"` (relevance) or `"date"` (recency).

### 4. Shopping category trend (Shopping Insight)

Get click-trend data for a shopping category. Requires category selection first.

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService
from micro_niche_finder.domain.schemas import NaverShoppingCategorySelection

svc = NaverShoppingInsightService()

# List available categories
options = svc.category_options()
for opt in options:
    print(f"  {opt.code}: {opt.label}")

# Fetch trend for a specific category
selection = NaverShoppingCategorySelection(code="50000000", label="패션의류", rationale="test")
req = svc.build_request(selection, weeks=12)
resp = svc.fetch(req)

for result in resp.results:
    for point in result.data:
        print(f"  {point.period}: {point.ratio}")
```

## Combining APIs for richer analysis

A common pattern is to combine multiple APIs for a complete picture:

1. **DataLab** — Is the keyword trending up or down?
2. **Ads Keyword Tool** — How many people actually search for it monthly?
3. **Web Search** — What are the top-ranking pages? (competition landscape)
4. **Shopping Insight** — If commerce-related, what's the shopping click trend?

Use `build_search_evidence()`, `build_context()`, and `build_shopping_evidence()` methods to get pre-formatted summary objects for structured reports.

## Error handling

Each service has `is_configured()` — check it before calling `fetch()` so you can give the user a clear message about missing credentials rather than a cryptic error. If credentials are missing, the services fall back to mock data (useful for development but not for real analysis — mention this to the user).
