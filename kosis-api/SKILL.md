---
name: kosis-api
description: Query KOSIS (Korean Statistical Information Service / 통계청) API for industry statistics — business counts, employee counts, revenue, value added, CAGR, regional concentration. Use this skill whenever the user asks about Korean industry statistics, 통계청 데이터, 사업체 수, 종사자 수, 산업 통계, market size estimation for Korean industries, or needs public data to assess a market. Also trigger when building reports that would benefit from official Korean economic statistics.
---

# KOSIS API (통계청)

Query Korea's official statistics service for industry-level data: business counts, employee counts, revenue, value added, growth rates (CAGR), and regional concentration.

## What the service provides

The project's `KosisEmployeeService` wraps the KOSIS OpenAPI and supports multiple "profile" configurations — each profile points at a different statistics table and extracts different metrics.

| Metric | Description |
|--------|-------------|
| `business_count` | Number of businesses in the industry |
| `employee_count` | Number of employees |
| `revenue` | Total revenue |
| `value_added` | Value added (부가가치) |
| CAGR | Compound annual growth rate (auto-computed from time series) |
| Regional concentration | Max region / average ratio |

## Credentials

Stored in `.env` — the service reads them via `get_settings()`.

| Env var | Purpose |
|---------|---------|
| `KOSIS_API_KEY` | API authentication key |
| `KOSIS_INDUSTRY_OPTIONS_JSON` | Industry code mapping (KSIC → KOSIS codes) |
| `KOSIS_PROFILE_OPTIONS_JSON` | Statistics table configurations |

## Pre-configured industries

The `.env` has a KSIC-10 중분류 mapping. Check current options:

```python
import sys, json
sys.path.insert(0, "src")
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService

svc = KosisEmployeeService()
for opt in svc.industry_options():
    print(f"  {opt.code}: {opt.label} — {opt.description}")
```

## Usage patterns

Run all scripts from the project root.

### 1. Quick lookup — single industry employee count

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.domain.schemas import KosisIndustrySelection

svc = KosisEmployeeService()
if not svc.is_configured():
    print("KOSIS not configured — check KOSIS_API_KEY in .env")
else:
    selection = KosisIndustrySelection(code="G47912", label="스마트스토어", rationale="온라인 소매업")
    req = svc.build_request(selection)
    resp = svc.fetch(req)
    print(f"{resp.industry_label}: 종사자 {resp.employee_count:,}명 ({resp.reference_year}년)")
```

### 2. Full profile — all metrics for an industry

This fetches every configured profile (structure, economics) and produces a comprehensive `MarketSizeContext`:

```python
import sys
sys.path.insert(0, "src")
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.domain.schemas import KosisIndustrySelection

svc = KosisEmployeeService()
selection = KosisIndustrySelection(code="G47912", label="스마트스토어", rationale="온라인 소매업 시장 규모 확인")

# Build all profile requests for this industry
requests = svc.build_requests(selection)
print(f"Fetching {len(requests)} profiles...")

# Fetch each profile
responses = []
for req in requests:
    resp = svc.fetch_profile(req)
    responses.append(resp)
    print(f"  {resp.profile_label} / {resp.metric_key}: {resp.latest_value:,.0f}" if resp.latest_value else f"  {resp.profile_label} / {resp.metric_key}: N/A")

# Build comprehensive market context
ctx = svc.build_market_context(selection=selection, responses=responses, rationale="시장 규모 평가")
print(f"\n{ctx.summary}")
```

The `MarketSizeContext` includes:
- `employee_count`, `business_count`, `revenue`, `value_added`
- `employee_cagr`, `business_cagr` — growth rates
- `revenue_per_employee` — productivity metric
- `regional_concentration` — geographic concentration
- `summary` — Korean-language narrative summary
- `profile_summaries` — per-profile one-line summaries

### 3. Profile types

The service auto-selects which profiles apply based on industry code prefixes:

| Profile | Tables | Applies to |
|---------|--------|-----------|
| Business structure | `DT_1F2A01` | All industries |
| Service economics | `DT_1SB1501` | Non-manufacturing (excludes `C*`) |
| Manufacturing economics | `DT_1MC1503` | Manufacturing only (`C*` prefixes) |

### 4. Time series data

Each profile response includes a `series` field with year-by-year data points:

```python
for resp in responses:
    if resp.series:
        print(f"\n{resp.profile_label} / {resp.metric_key}:")
        for point in resp.series:
            print(f"  {point.period}: {point.value:,.0f}")
        if resp.cagr is not None:
            print(f"  CAGR: {resp.cagr * 100:.1f}%")
```

## Selecting an industry code

If the user gives you a Korean industry name but not a KOSIS code:
1. First check `svc.industry_options()` for a pre-configured match
2. If no match, ask the user — the KOSIS code mapping depends on their `.env` configuration
3. The project's `OpenAIResearchService.select_kosis_industry()` can also map niche names to KOSIS codes using LLM reasoning

## Error handling

- `svc.is_configured()` checks for API key and at least one profile — call it before `fetch_profile()`
- The KOSIS API returns error objects in the JSON response — the service extracts and raises them as `RuntimeError`
- If the API key is missing, tell the user to set `KOSIS_API_KEY` in `.env`
