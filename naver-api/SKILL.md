---
name: naver-api
description: Query Naver APIs (DataLab trends, Web Search, Ads Keyword Tool, Shopping Insight) to get Korean search data, keyword volumes, trend analysis, and shopping category insights. Use this skill whenever the user asks about Korean keyword research, search trends, 검색량, 네이버 트렌드, 키워드 분석, 쇼핑 인사이트, or needs real Naver data to inform a decision — even if they don't name a specific API. Also trigger when building reports or analyses that would benefit from Korean search demand data.
---

# Naver API Tools

Query four Naver APIs for Korean market data. The project has ready-made service classes — use them directly instead of building raw HTTP requests.

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
