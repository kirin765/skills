# Naver Search Ads API — endpoint reference

Official docs: https://naver.github.io/searchad-apidoc/ · Base: `https://api.searchad.naver.com`

Use `scripts/searchad.py raw <METHOD> <path> [--param k=v ...] [--body '<json>']` for anything below that the wrapped commands don't cover. The `raw` command signs and sends; you supply method, path, query params, and JSON body. Writes spend real money — confirm with the user first.

## Contents
- [Object hierarchy](#object-hierarchy)
- [Campaigns](#campaigns)
- [Ad groups](#ad-groups)
- [Keywords & bids](#keywords--bids)
- [Ads](#ads)
- [Stats & reports](#stats--reports)
- [Keyword tool](#keyword-tool)
- [Other resources](#other-resources)
- [Common errors](#common-errors)

## Object hierarchy

```
Customer (account, X-Customer)
└── Campaign        cmp-…   campaignTp: WEB_SITE | SHOPPING | POWER_CONTENTS | BRAND_SEARCH | PLACE
    └── Adgroup     grp-…   has default bidAmt, dailyBudget, pcChannelId/mobileChannelId
        ├── Keyword nkw-…   has bidAmt, useGroupBidAmt, qualityKeyword (1–10)
        └── Ad      nad-…   creative; type depends on campaign
```

`status` values: `ELIGIBLE` (running), `PAUSED`, `DELETED`, plus review states. Writes that pause/enable flip the `userLock` boolean (`true` = paused by user).

## Campaigns

| Op | Method · path | Notes |
|----|---------------|-------|
| List | `GET /ncc/campaigns` | all campaigns (wrapped: `campaigns`) |
| Get | `GET /ncc/campaigns/{id}` | |
| Create | `POST /ncc/campaigns` | body needs `name`, `campaignTp`, `customerId` |
| Update | `PUT /ncc/campaigns/{id}?fields=budget` | `fields` selects what changes: `budget`, `period`, `useDailyBudget`, `userLock` |
| Delete | `DELETE /ncc/campaigns/{id}` | |

Daily budget example:
```
raw PUT /ncc/campaigns/<id> --param fields=budget --body '{"nccCampaignId":"<id>","dailyBudget":50000,"useDailyBudget":true}'
```

## Ad groups

| Op | Method · path | Notes |
|----|---------------|-------|
| List | `GET /ncc/adgroups?nccCampaignId={id}` | wrapped: `adgroups <campaignId>`. Also `?nccCampaignId=` optional → all |
| Get | `GET /ncc/adgroups/{id}` | |
| Create | `POST /ncc/adgroups` | needs `nccCampaignId`, `name`, `pcChannelId`, `mobileChannelId` |
| Update bid | `PUT /ncc/adgroups/{id}?fields=bidAmt` | wrapped: `groupbid` |
| Update budget | `PUT /ncc/adgroups/{id}?fields=budget` | `dailyBudget`, `useDailyBudget` |
| Pause/enable | `PUT /ncc/adgroups/{id}?fields=userLock` | wrapped: `on/off adgroup` |
| Delete | `DELETE /ncc/adgroups/{id}` | |

## Keywords & bids

| Op | Method · path | Notes |
|----|---------------|-------|
| List | `GET /ncc/keywords?nccAdgroupId={id}` | wrapped: `keywords <adgroupId>` |
| Add | `POST /ncc/keywords?nccAdgroupId={id}` | body is an **array** of `{keyword, bidAmt, useGroupBidAmt}` |
| Update bid | `PUT /ncc/keywords/{id}?fields=bidAmt` | wrapped: `bid`. Set `useGroupBidAmt:false` to use a custom bid |
| Bulk bid | `PUT /ncc/keywords?fields=bidAmt` | body = array of `{nccKeywordId, bidAmt, useGroupBidAmt}` |
| Pause/enable | `PUT /ncc/keywords/{id}?fields=userLock` | wrapped: `on/off keyword` |
| Delete | `DELETE /ncc/keywords/{id}` | |

`useGroupBidAmt:true` means the keyword inherits the adgroup default bid; the `bid` command sets it `false` so your amount sticks.

## Ads

| Op | Method · path |
|----|---------------|
| List | `GET /ncc/ads?nccAdgroupId={id}` |
| Get / Create / Update / Delete | `GET|POST|PUT|DELETE /ncc/ads[/{id}]` |
| Pause/enable | `PUT /ncc/ads/{id}?fields=userLock` |

## Stats & reports

Two systems — pick by size:

**1. Live stats — `GET /stats`** (wrapped: `stats`). Good for one or a few ids, on demand.
- `id` (one) or `ids` (JSON array, ≤ a few hundred)
- `fields` — JSON array, e.g. `["impCnt","clkCnt","salesAmt","ctr","cpc","ccnt"]`
- `timeRange` — JSON `{"since":"YYYY-MM-DD","until":"YYYY-MM-DD"}`, or `datePreset` = `today|yesterday|last7days|last30days|thisMonth|lastMonth`
- `timeIncrement=1` → daily rows (the `--daily` flag); `breakdown` → split by `pcMobile`, `hh24`, `region`, `gender`, `age`, `week`, `weekday`

Stat field dictionary (most-used):

| field | meaning | field | meaning |
|-------|---------|-------|---------|
| `impCnt` | impressions 노출수 | `clkCnt` | clicks 클릭수 |
| `ctr` | click-through rate % | `cpc` | avg cost per click 원 |
| `salesAmt` | **ad spend (cost) 광고비**, won | `ccnt` | conversions 전환수 |
| `avgRnk` | avg rank/position 평균순위 | `viewCnt` | viewable imps |
| `crto` | conversion rate | `convAmt` | conversion value (if tracked) |

`salesAmt` is the spend Naver charges you, **not** sales revenue — a common trap.

**2. Bulk StatReport / MasterReport** — async files for big pulls or whole-account history:
- `POST /stat-reports` body `{"reportTp":"AD","statDt":"YYYYMMDD"}` → returns a report job; poll `GET /stat-reports/{id}` until `BUILT`, then download `downloadUrl` (TSV). `reportTp`: `AD`, `AD_DETAIL`, `AD_CONVERSION`, `EXPKEYWORD`, etc.
- `GET /master-reports` / `POST /master-reports` — full entity dumps (`Campaign`, `Adgroup`, `Keyword`, `Ad`, `BusinessChannel`…). Use for reconstructing account structure in bulk instead of walking the tree.

## Keyword tool

`GET /keywordstool` (wrapped: `keywordtool`). Query params:
- `hintKeywords` — comma-joined, **spaces removed** (the wrapper strips them)
- `showDetail=1` — include competition + ad-depth detail
- optional `siteId`, `biztpId`, `month`, `event`

Response `keywordList[]` fields: `relKeyword`, `monthlyPcQcCnt`, `monthlyMobileQcCnt` (monthly searches; small counts come back as the string `"< 10"`), `monthlyAvePcClkCnt`/`monthlyAveMobileClkCnt`, `monthlyAvePcCtr`/`…Mobile…`, `plAvgDepth` (avg # of ads shown), `compIdx` (`낮음|중간|높음` competition).

## Other resources

| Resource | Path | Use |
|----------|------|-----|
| Business channels | `GET /ncc/channels?campaignTp=...` | site/place channels (needed as `pcChannelId`/`mobileChannelId` when creating adgroups) |
| Ad extensions | `/ncc/ad-extensions` | phone, location, calculation, etc. |
| Labels | `/ncc/labels`, `/ncc/label-refs` | tagging campaigns/adgroups/keywords |
| Target/restricted | `/ncc/restricted-keywords`, `/ncc/targets` | negative keywords, schedule/region targeting |
| Estimate (입찰가 추정) | `POST /estimate/average-position-bid/keyword` | bid needed for a target position; `POST /estimate/performance/...` for forecast |
| Bizmoney (잔액) | `GET /billing/bizmoney` | account balance |
| Managed customers | `GET /ncc/managedCustomerLinks` | agency: list sub-accounts (set `X-Customer` to operate on one) |

## Common errors

- **401 / signature mismatch** — clock skew (timestamp must be ~now) or the signed path included a query string. The client signs the path only; if you hand-build a request, sign `"{ts}.{METHOD}.{path-without-query}"`.
- **403 / not permitted** — the API license lacks scope for that resource, or `X-Customer` isn't an account this license manages.
- **400 with `fields`** — `PUT` updates require the `fields` query param naming what you change, and the body must include the entity's own id (`nccCampaignId` etc.) plus those fields.
- **Rate limits** — the API throttles per second/day; back off on `429` rather than retrying hard.
