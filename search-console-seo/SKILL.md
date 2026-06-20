---
name: search-console-seo
description: >-
  Console-driven SEO/ASO optimization. Drives the user's authenticated Naver
  Search Advisor (웹마스터도구) AND Google Search Console through the Claude in
  Chrome extension to read real index/crawl/coverage data, then optimizes a
  target domain — both local codebases (Next.js etc.) and external content
  (Tistory/blog promo posts) — against the official Naver 웹마스터 가이드
  (https://searchadvisor.naver.com/guide) and Google Search Essentials. Also
  covers ASO (Google Play / App Store listing) for the domain's app when one
  exists. This is an explicitly user-invoked skill: run it whenever the user
  asks to "optimize SEO for <domain>", "check Search Advisor / Search Console",
  "네이버 SEO 최적화", "구글 서치콘솔 최적화", "ASO 최적화", or to tune a
  Tistory/blog post for Naver/Google search. Does not need a special keyword to
  trigger — assume relevance when the user mentions Search Advisor, Search
  Console, Naver/Google SEO, indexing, sitemaps, or ASO for their own sites.
---

# Search Console SEO/ASO

Optimize a target for **both** Korean (Naver) and global (Google) search by
reading the real state from the two webmaster consoles and acting on it. The
value over a blind on-page audit is that you work from ground truth: what Naver
and Google actually crawled, indexed, and flagged.

Two console surfaces, one workflow:

- **Naver Search Advisor** (`searchadvisor.naver.com`, 웹마스터도구) — Yeti
  crawl status, 웹페이지 수집/색인, sitemap & RSS submission, 사이트 최적화 진단.
- **Google Search Console** (`search.google.com/search-console`) — coverage /
  indexing, sitemaps, URL inspection, enhancements, Core Web Vitals.

A target is either a **local codebase** (you edit code) or **external content**
you can only reach in the browser (a Tistory post, a hosted page). The audit
criteria are the same; only the fix mechanism differs.

## Access model (read this first — there is a hard constraint)

Engine: the **Claude in Chrome extension** (`mcp__Claude_in_Chrome__*`), using
the user's already-authenticated sessions. But:

> **`searchadvisor.naver.com` is blocked from `navigate`** by the extension's
> safety restrictions ("This site is not allowed…"). You cannot open it
> yourself.

So the working pattern is **user-opens, extension-operates**:

1. Ask the user to open the specific console page in their Chrome (give the
   exact URL).
2. Call `tabs_context_mcp` to find the open tab, then `read_page` /
   `get_page_text` / `find` / `javascript_tool` to read and operate **within
   the already-open tab**.
3. For Google Search Console, `navigate` usually works directly — try it; fall
   back to user-opens if blocked.
4. **CDP fallback** (`cdp-anywhere` pattern, port 9222) only if the extension
   can't operate on an open console tab at all. CDP is more fragile; prefer the
   extension. See `references/access.md`.

Side-effecting console actions (submitting a sitemap/RSS, requesting indexing,
changing settings) require an explicit user confirmation in chat before you
click the final button — these are outward-facing and not always reversible.

## Workflow

Work in this order. Don't submit anything to a console until the on-page/content
fixes are actually live, or you'll just re-submit broken pages.

### 0. Identify targets and map them

Pin down exactly what to optimize and where its source lives:

- Each domain → its local repo (grep `next.config.*`, `CNAME`, `vercel.json`,
  `package.json` for the domain). A domain with no local repo is external
  content (edit in-browser).
- If the user names a blog (e.g. `kirin765.tistory.com`) and a subset ("only
  the sajangbu.com promo posts"), enumerate just those posts — don't touch the
  rest.
- Note whether the domain ships an app (Play/App Store) → ASO is in scope.

### 1. Pull console ground truth

Have the user open each relevant console page; read it via the extension.
Capture, per target:

- **Naver**: is the site registered? sitemap & RSS submitted and "정상"?
  웹페이지 수집 count, 수집 errors, 사이트 최적화 진단 warnings, which
  verification method is active. See `references/naver-searchadvisor.md`.
- **Google**: indexed vs not-indexed pages and reasons, sitemap status, URL
  Inspection on key URLs, enhancement/CWV reports. See
  `references/google-search-console.md`.

Report what's actually wrong (e.g. "Naver collected 3 of 14 blog URLs",
"GSC: 8 pages 'Crawled - not indexed'") before changing anything.

### 2. Audit against the guides

For each target, check the items below. For **local codebases**, the on-page
markup is editable — audit the full list. For **external content** (Tistory),
audit what the platform exposes: title, meta description, representative/OG
image, tags, headings, body text, internal/outbound links.

The Naver-specific points that generic (Google-only) SEO misses — these are the
highest-leverage and most-often-wrong:

1. **Crawler is `Yeti`.** A blanket `allow: /` for `*` covers it. Never block
   by IP. Only add an explicit `Yeti` rule if other bots are restricted.
2. **Open Graph is a primary Naver search signal**, not just social. Naver
   builds snippets from `og:title`/`og:description`/`og:image`/`og:url` and
   uses them for exposure. Always present, per page.
3. **RSS is submitted separately from the sitemap, and Naver wants the FULL
   article body** in the feed (`<content:encoded>` with `xmlns:content`), not an
   excerpt. This is how Naver ingests fresh content fast. (Sitemap = URL list;
   RSS = fresh full content.) See `references/naver-searchadvisor.md` for the
   verified Next.js full-body RSS pattern (render the post body with
   `react-dom/server.edge`'s `renderToStaticMarkup`).
4. **Favicon must be an absolute, crawlable URL** or it won't show in the SERP.
5. **`schema.org Product` is NOT a Naver-documented rich type.** Naver
   documents Article, BreadcrumbList, FAQ, Review/AggregateRating, Recipe,
   HowTo, Video, Movie/TVSeries, Restaurant/Address, Software, Job, Channel,
   Carousel. Ship Product JSON-LD for Google, but for Naver lean on
   BreadcrumbList + FAQ + Article + Review.
6. **Verification + submission live in Search Advisor**, separate from GSC, with
   its own `naver-site-verification` tag. Two stale verification codes are
   harmless but confusing — reconcile to the one Search Advisor actually shows.
7. **`nosourceinfo`** opts a page out of Naver's AI source description; most
   sites should not set it.

Standard cross-engine on-page items also apply (unique `<title>` + meta
description per page, canonical, viewport, Twitter card, real `<a href>` links,
text not baked into images, sitemap referenced from robots). The standalone
`naver-seo` skill has an exhaustive per-tag markup reference if you need it.

### 3. Apply fixes

- **Local codebase**: edit in the repo, matching the framework's conventions
  (Next.js App Router reads `metadata`/`sitemap`/`robots` files — don't hand-add
  tags it generates). Then **verify the rendered output** — start the dev server
  and fetch the actual route (RSS/sitemap/page `<head>`), confirming the tags or
  feed content are really present. Don't claim a fix from the source alone.
- **External content (Tistory etc.)**: edit in-browser via the extension. For
  Tistory specifically, see `references/tistory.md` for which fields map to
  Naver/Google signals (title, 설명/대표이미지 = OG, tags, headings) and how to
  edit them without corrupting the body.

### 4. ASO (only if the domain has an app)

If the target ships a Google Play / App Store app, optimize the store listing —
title, short/long description, keyword field (App Store), screenshots, feature
graphic — for store search. The dedicated `aso-audit` skill does the deep
listing audit; invoke it for the heavy lifting and feed its output back here so
on-site and on-store messaging stay consistent. See
`references/google-search-console.md` → ASO section.

### 5. Submit and verify (confirm before each side-effecting click)

Only after fixes are live:

- **Naver**: submit/re-submit sitemap and RSS in Search Advisor; use 웹페이지
  수집 to request collection of key URLs; re-run 사이트 최적화 진단.
- **Google**: submit sitemap; URL-Inspect → Request Indexing on changed URLs.
- Confirm with a `site:` query on each engine after a crawl window, and re-read
  the console to confirm errors cleared.

Hand the user a short list of any steps that genuinely need them (a login
re-auth, a CAPTCHA, a final submit they want to click themselves).

## Reference files

Read the one relevant to the step you're on; don't load all up front.

- `references/access.md` — Claude-in-Chrome operating pattern, the
  `searchadvisor` navigate block + user-opens workaround, CDP fallback.
- `references/naver-searchadvisor.md` — Search Advisor console map, the
  웹마스터 가이드 essentials, verified full-body RSS pattern, sitemap/RSS
  submission, verification.
- `references/google-search-console.md` — GSC console map (coverage, sitemaps,
  URL inspection, enhancements, CWV) and the ASO listing checklist.
- `references/tistory.md` — editing a Tistory post for Naver/Google search
  without breaking the body.
