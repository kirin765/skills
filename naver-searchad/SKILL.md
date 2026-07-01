---
name: naver-searchad
description: Manage a Naver Search Ads account (네이버 검색광고) and pull its performance data via the official Search Ads API (api.searchad.naver.com). Use this skill whenever the user wants to list/inspect their 검색광고 campaigns (캠페인), ad groups (광고그룹), keywords (키워드) and their bids (입찰가/입찰), change a bid, pause or enable a campaign/adgroup/keyword, pull impression/click/cost/conversion stats (노출·클릭·비용·전환 리포트), or run the keyword tool for search volume and related keywords (키워드도구, 월간 검색수, 연관키워드, 경쟁정도) — even if they don't name the API. Trigger on phrases like "내 검색광고", "캠페인 목록", "광고그룹/키워드 봐줘", "입찰가 바꿔줘", "광고 성과/리포트 뽑아줘", "키워드 검색량", "naver searchad", "네이버 광고 API". This is the full ad-management API (campaigns/adgroups/keywords/bids/stats) — distinct from the `naver-api` skill, which only does read-only search-demand/trend lookups. For the keyword tool alone either skill works; for anything touching the account's own ads, use this one.
---

# Naver Search Ads API

Manage and report on the user's Naver Search Ads account through the official REST API at `https://api.searchad.naver.com`. Everything goes through one signed-request client: `scripts/searchad.py`.

## Credentials

Read automatically from `~/niche-finder/.env` (`NAVER_ADS_CUSTOMER_ID`, `NAVER_ADS_API_KEY`, `NAVER_ADS_SECRET_KEY`); same-named environment variables override the file. Nothing is hardcoded — never paste keys into files. If creds are missing the script exits with a clear message.

## How auth works (so you can trust / debug it)

Every request carries four headers. The signature is the load-bearing one:

```
X-Timestamp : current epoch milliseconds
X-API-KEY   : the access license
X-Customer  : numeric customer (account) id
X-Signature : base64( HMAC-SHA256( secret, "{timestamp}.{METHOD}.{uri}" ) )
```

The signed `uri` is the **path only** — no query string, no host. `scripts/searchad.py` handles this; you only need to know it when debugging a `401`/`signature` error (usually a stale timestamp or a query string that leaked into the signed path).

## The client

Run read commands freely. **Write commands change a live account that spends real money** — confirm the exact change with the user before running `bid`, `groupbid`, `on`, `off`, or any `raw` PUT/POST/DELETE.

```bash
cd ~/.claude/skills/naver-searchad

# --- read (safe) ---
python3 scripts/searchad.py campaigns                      # list campaigns + status + daily budget
python3 scripts/searchad.py adgroups   <campaignId>        # adgroups in a campaign (with default bid)
python3 scripts/searchad.py keywords   <adgroupId>         # keywords + per-keyword bids
python3 scripts/searchad.py keywordtool 치과 임플란트 --limit 30   # search volume + related keywords
python3 scripts/searchad.py stats <id> --since 2026-06-01 --until 2026-06-23
python3 scripts/searchad.py stats <id> --preset last30days --daily

# --- write (confirm with user first) ---
python3 scripts/searchad.py bid      <keywordId> 250       # set one keyword's bid to 250 won
python3 scripts/searchad.py groupbid <adgroupId> 300       # set an adgroup's default bid
python3 scripts/searchad.py off      keyword <keywordId>   # pause (on = enable) campaign|adgroup|keyword

# --- escape hatch for any endpoint not wrapped above ---
python3 scripts/searchad.py raw GET /ncc/ads --param nccAdgroupId=<adgroupId>
python3 scripts/searchad.py raw PUT /ncc/campaigns/<id> --param fields=budget --body '{"nccCampaignId":"<id>","dailyBudget":50000}'
```

Add `--json` to read commands for raw JSON instead of a table. `stats` is always raw JSON (its shape varies by entity and date options).

## The id hierarchy (how to navigate)

The account is a tree; you almost always walk down it: **campaign → adgroup → keyword → ad**. Ids are prefixed so you can tell them apart at a glance: `cmp-…` campaign, `grp-…` adgroup, `nkw-…` keyword, `ad-…` ad. To answer "what are my best keywords this month," list campaigns → pick one → list its adgroups → list each adgroup's keywords → run `stats` on the keyword ids.

## Stats

`stats <id>` works for any campaign / adgroup / keyword / ad id. Default fields are `impCnt, clkCnt, ctr, cpc, salesAmt, ccnt, avgRnk` (impressions, clicks, CTR, cost-per-click, **cost** in won — `salesAmt` is ad spend, not revenue — conversions, avg position). Override with `--fields impCnt,clkCnt,salesAmt`. Use `--since/--until` for an explicit range or `--preset last7days|last30days|lastMonth`; add `--daily` to break the range down by day. For deeper reporting (large bulk reports, breakdowns by region/device/hour), see the StatReport endpoints in the reference.

## Going beyond the wrapped commands

The wrapped commands cover the common 90%. The API is much larger — ads, business channels, ad extensions, labels, target/restricted keywords, bulk stat reports, agency-managed customers. When you need one of those, read the catalog and use `raw`:

→ **`references/endpoints.md`** — endpoint map, key request/response fields, the stat field dictionary, and `raw` recipes for create/update/delete flows.

## Safety habits

- Default to read. Treat `bid`, `groupbid`, `on`, `off`, create, and delete as actions the user must explicitly approve — state what will change (which id, from what to what) and get a yes before running.
- One account, real budget. A wrong bid or an un-paused campaign spends money immediately.
- When a write returns, echo the relevant fields back (e.g. the new `bidAmt`) so the user can confirm it took.
