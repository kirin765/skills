# Google Search Console + ASO

## GSC console map

`https://search.google.com/search-console` (pick the property for the domain).
`navigate` usually works here; if blocked, use user-opens (see `access.md`).

- **Pages / Indexing** — indexed vs not-indexed counts with reasons. The ones to
  act on: "Crawled - currently not indexed", "Discovered - not indexed"
  (thin/duplicate/low-value → improve content or internal links), "Page with
  redirect", "Duplicate without user-selected canonical" (fix canonical),
  "Excluded by 'noindex'" (intentional?), "Soft 404".
- **Sitemaps** — submitted sitemaps + discovered URL counts + errors.
- **URL Inspection** (top bar) — per-URL: indexed? last crawl, canonical Google
  chose vs declared, mobile usability, rich-result detection. Has a **Request
  Indexing** button (side-effecting).
- **Experience / Core Web Vitals** — LCP/INP/CLS field data (mobile + desktop),
  grouped by URL pattern. INP replaced FID — watch it.
- **Enhancements** (Breadcrumbs, FAQ, etc.) — structured-data validity per type;
  errors here mean a rich result won't show.

Read tables with `get_page_text`; GSC also exposes data via its internal API
that `javascript_tool` `fetch` can read when a table is paginated/awkward.

## What to fix (Google side)

- Map each "not indexed" reason to a concrete code/content fix; don't just
  Request-Indexing your way around a content problem.
- Ensure declared canonical == the URL you want indexed; resolve duplicate
  clusters.
- Valid sitemap, referenced from robots, only canonical indexable URLs.
- Structured data: Google supports `Product`, `Article`, `BreadcrumbList`,
  `FAQPage`, `Review`, etc. Keep JSON-LD valid (Rich Results Test) so
  Enhancements stays green.
- CWV: act on the worst URL group; INP is the common Korean-site weak point
  (heavy hydration, third-party scripts).

## Submission / verification (side-effecting — confirm first)

- Submit sitemap under Sitemaps.
- URL-Inspect → Request Indexing for changed/important URLs (rate-limited; spend
  it on the pages that matter).
- Confirm with `site:<domain>` on Google after a crawl window and re-read
  Indexing to confirm the reason cleared.

## ASO (Google Play / App Store) — when the domain ships an app

Store search is its own ranking system; optimize the listing, not the website.
Hand the deep audit to the **`aso-audit` skill** and keep messaging consistent
with the site. The listing levers:

- **Title** — primary keyword + brand, within the char limit (Play 30, App
  Store 30).
- **Short description** (Play 80 chars) / **Subtitle** (App Store 30) — the
  highest-weight keyword line after the title.
- **Long description** (Play) — natural keyword coverage, not stuffing; Play
  indexes it. App Store's long description is NOT indexed — keywords go in the
  dedicated **keyword field** (100 chars, comma-separated, no spaces, no
  repeats, singular forms).
- **Screenshots + feature graphic** — first 2 screenshots drive conversion;
  caption the value prop.
- **Localization** — a Korean (ko-KR) listing for Korean-market apps; localize
  title/description/screenshots, don't just translate.
- Conversion (install rate) and retention feed back into store ranking — ASO is
  listing + quality, not just keywords.

Use `aso-audit` for competitor comparison, keyword scoring, and the full
listing teardown; bring its recommendations back so the app's site and store
pages tell the same story.
