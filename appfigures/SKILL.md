---
name: appfigures
description: Pull real App Store & Google Play analytics for the user's OWN apps from the Appfigures API — sales, revenue, downloads/uninstalls, user reviews, star-rating breakdowns, store chart ranks, ASO keyword ranks, and featured placements. Use this skill whenever the user asks about their app's downloads or sales numbers, how many installs/uninstalls they got, their reviews or ratings over time, which keywords their app ranks for and at what position, where their app sits on a store chart, featured placements, or any quantitative metric about an app they publish (iOS, Android, Amazon, or Mac) — even if they don't say "Appfigures". This is for the actual ASO keyword-rank and chart-rank *numbers* — distinct from rewriting store-listing copy (that's the aso-audit skill). Also trigger when building a performance or ASO-ranking report for their apps, or when they reference their Appfigures account. Note: this token is single-account, so it covers the user's own linked apps, not arbitrary competitor apps (that needs Partner API access).
---

# Appfigures API

[Appfigures](https://appfigures.com) aggregates App Store / Google Play / Amazon data: rankings,
ASO keywords, reviews, ratings, featured placements, and (for linked accounts) sales & revenue.
This skill calls the v2 API through one authenticated helper so you never hand-roll auth.

## How to call it

Use the bundled client for **every** request — it handles Bearer auth, the base URL, and JSON:

```bash
python scripts/appfigures.py <PATH>
```

`<PATH>` is any endpoint path (with its query string). The script prepends `https://api.appfigures.com/v2`.
Pretty-prints JSON by default; `--compact` for one-line, `--out file.json` to save, `--method POST --data '{...}'`
for writes.

```bash
python scripts/appfigures.py /products/search/habit+tracker
python scripts/appfigures.py "/reviews?products=29521&stars=1,2&count=20"
```

**Auth:** the script reads a Personal Access Token from `APPFIGURES_PAT` (env), else a baked-in default.
A `401` means the token is missing/invalid — create one at appfigures.com → API client → "Create Personal
Access Token". Don't switch to raw `curl`; the helper already encodes auth correctly.

**Access scope (important).** This token is **single-account** — it returns data only for the user's own
linked apps. `GET /products/mine` lists them; resolve ids from there. Calls that touch apps the user
doesn't own (e.g. `/products/search`, or another app's id) return **403 "requires Partner API Access"**.
So treat this as *the user's own-app analytics*, not a competitor-research tool. If the user asks about a
competitor app, say plainly that this token can't reach it — competitor/market data needs the **Public Data
Access add-on** (enabled in the Appfigures account; billed via pre-paid credits, ~2 credits/request, with
daily rate limits). Once that add-on is on, `/products/search`, any app's `/ranks`, `/reviews`, `/reports/ratings`,
and `/featured` start working for apps the user doesn't own — the same helper and paths, no code change.

## Dates & common params

- **Relative dates**: `start_date=-30` = 30 days ago, `0` = today. Great for "last N days" without computing dates.
- **Absolute dates**: `start_date=2024-01-01&end_date=2024-12-31`.
- **products**: comma-separated Appfigures product ids (`products=29521,1015630`). Get ids via `/products/search` or `/products/{store}/{store_id}`.
- **countries**: ISO codes, comma-separated (`countries=US,KR,JP`). Omit = all.
- **group_by**: shapes the response, e.g. `group_by=product,date` or `group_by=country`.

## Endpoint reference (pick the path, then call the helper)

### Products — your apps & metadata  →  app info
- `GET /products/mine` — **start here.** Lists the user's own apps with their Appfigures ids (reuse those ids everywhere else). `?store=apple` to filter.
- `GET /products/{appfigures_id}` — details for one of your apps.
- `GET /products/search/{term}` and `GET /products/{store}/{id_in_store}` exist but need **Partner API access** — on this single-account token they 403 for apps you don't own. Don't lead with them.

### ASO & keywords  →  ASO / keyword ranks
- `GET /aso?products={id}&country={CC}` — per-keyword ranks/visibility. **Both `products` and `country` are required** (e.g. `/aso?products=338137897450&country=US`) or you get a 400.
- `GET /aso/stats?products={id}&country={CC}` — aggregate ASO stats (ranked keywords, top-5/25/100 counts, avg position).
ASO only returns keywords the product actually tracks in Appfigures; a new/untracked app returns empty — that's expected, not an error. Try a couple of relevant countries.

### Ranks — store chart positions  →  app rankings
- `GET /ranks/{product_ids}/{granularity}/{start_date}/{end_date}?countries=US,KR` — rank history. `granularity` = `hourly|daily|weekly`. e.g. `/ranks/29521/daily/-14/0?countries=US`.
- `GET /ranks/snapshots/{time}/{country}/{category}/{subcategory}` — chart snapshot (who's ranking now). e.g. `/ranks/snapshots/current/us/71/free?count=1000` (category ids via `/data/categories`).

### Reviews & ratings  →  reviews / star ratings
- `GET /reviews?products={ids}&count=25&page=1&lang=en&countries=US&stars=1,2&sort=date` — individual reviews (filterable by star, language, country, date).
- `GET /reviews/count?products={ids}` — review counts.
- `GET /reports/ratings?products={ids}&start_date=-30&group_by=product,date` — star-rating breakdown & averages over time (1–5★ counts, positive/negative, new vs total).

### Sales, revenue, downloads  →  sales reports (needs linked store accounts)
- `GET /reports/sales?group_by=products,dates&start_date=-30` — downloads, revenue, IAP, returns.
- `GET /reports/revenue?group_by=product,date&start_date=-30` — revenue detail.
- `GET /reports/subscriptions`, `/reports/ads`, `/reports/adspend`, `/reports/usage`, `/reports/estimates` — related reports.
These only return data if the user has connected their App Store Connect / Play Console to Appfigures. If a sales/revenue call comes back empty, that's almost always why — tell the user rather than assuming the API failed.

### Featured & events  →  featured placements
- `GET /featured/summary/{start_date}/{end_date}` — featured-placement summary.
- `GET /featured/full/{product_id}/{start_date}/{end_date}` — full featured history. **Date span must be ≤ 31 days** (e.g. `/featured/full/{id}/-30/0`) or it 400s.
- `GET /featured/counts?granularity=daily&end={date}&count=30` — counts over time.
- `GET /events` — your annotated events/timeline (also POST/PUT/DELETE to manage).

### Reference data  →  ids & lookups
- `GET /data/categories`, `/data/countries` (`/data/countries/apple`), `/data/languages`, `/data/currencies`, `/data/stores`.
Use these to resolve the category ids, country codes, and store names other endpoints expect.

## Workflow tips

- **Start from `/products/mine`.** It gives the Appfigures `product` ids for the user's apps; reuse those ids across sales/reviews/ratings/ranks/aso/featured calls.
- **Explore an endpoint by calling it with just `products` (and `country` for `/aso`)** and reading the JSON shape before adding more filters — cheaper than guessing param names. Several endpoints have required params and return a clear 400 telling you what's missing.
- **Empty ≠ broken.** A new or low-traffic app legitimately returns zeros/empty for reviews, ratings, ranks, ASO, and featured. Sales/downloads usually has data if the store account is linked. Say "no data yet for this app" rather than implying the call failed.
- For reports, gather the raw JSON via the helper, then summarize/tabulate — don't paste giant JSON blobs back at the user.

## Rate limits

The API is rate-limited; a `429` means slow down. Batch what you can into single calls (comma-separated `products`,
`group_by`) instead of many tiny requests, and back off on `429` instead of retrying immediately.
