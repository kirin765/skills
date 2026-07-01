---
name: naver-seo
description: >-
  Optimize a website for Naver search (네이버 검색 노출) following the official Naver
  Search Advisor / 웹마스터 가이드 (searchadvisor.naver.com/guide). Use this whenever
  the user mentions 네이버 SEO, 네이버 검색 최적화, 네이버 검색 노출, 서치어드바이저, Search Advisor,
  웹마스터도구, Yeti(네이버 검색로봇), naver-site-verification, RSS 피드 제출, 네이버 사이트맵,
  네이버 파비콘, or wants their site/store/blog to rank or appear in Naver search —
  even if they only say "SEO" but the audience is Korean / the site targets Naver.
  Naver differs from Google in important ways (Yeti robot, RSS feed with full body,
  Open Graph used directly for search, favicon must be absolute URL, schema.org
  Product is NOT a Naver-supported rich type). Apply this skill before hand-rolling
  generic SEO for a Korean-market site. For Google/AI-engine (AEO/GEO) SEO use the
  generic seo / seo-geo skills instead or in addition.
---

# Naver SEO (네이버 검색 최적화)

Make a site eligible for — and well-presented in — Naver search, per the official
웹마스터 가이드. Naver's crawler, feeds, and ranking signals differ from Google's, so a
site that's fully Google-optimized can still be invisible or poorly presented on Naver.

## What's genuinely Naver-specific (don't assume Google rules transfer)

These are the points people miss when they apply generic SEO to a Korean-market site:

1. **The crawler is `Yeti`.** Firewalls/robots rules that allow `Googlebot` but not
   `Yeti` block Naver entirely. Never block crawlers by IP — Yeti's IP ranges change.
2. **Open Graph is a primary search signal, not just social.** Naver reads `og:title`,
   `og:description`, `og:image`, `og:url` to build search snippets and decide exposure.
   On many Naver-optimized sites OG is more impactful than on Google. Always include it.
3. **RSS feed is submitted separately from the sitemap**, and Naver wants the **full
   article body** inside the RSS — not just an excerpt. This is how Naver discovers and
   ingests fresh content fast. (Sitemap = URL list; RSS = fresh full content.)
4. **Favicon must use an absolute URL** in the markup and be crawlable, or it won't show
   beside your result. Naver renders favicons in the SERP.
5. **schema.org `Product` is NOT one of Naver's documented rich-result types.** Naver
   documents: Article, BreadcrumbList, FAQ, Review/Rating(AggregateRating), Recipe,
   HowTo, Video, Movie/TVSeries, Restaurant/Address, Software, Job, Channel, Carousel.
   Product JSON-LD is still fine to ship (Google + general schema.org), just don't
   expect a Naver rich result from it — for a shop, lean on BreadcrumbList + FAQ + Review.
6. **Verification + submission happen in 웹마스터도구 (Search Advisor),** a separate
   console from Google Search Console, with its own `naver-site-verification` meta tag.
7. **`nosourceinfo` robots directive** opts a page out of Naver's AI-generated source
   description. Most sites should NOT set it; know it exists.

## Workflow

When asked to do Naver SEO on a project, work in this order. Read the project first —
don't add tags that already exist or contradict the framework's conventions (e.g.
Next.js App Router generates viewport and reads `metadata`/`sitemap`/`robots` files).

1. **Audit current state.** Grep for existing `robots`, `sitemap`, OG tags, favicon,
   `naver-site-verification`, JSON-LD, canonical. Use `references/checklist.md` as the
   audit list. Report what's present vs missing before changing anything.
2. **Crawlability** — robots allows `Yeti` (an `allow: /` for `*` covers it; add an
   explicit `Yeti` rule only if other bots are restricted). sitemap.xml exists and is
   referenced from robots. See `references/markup.md` → robots/sitemap.
3. **Per-page markup** — unique `<title>`, unique meta `description` (1–2 sentences, no
   keyword stuffing), Open Graph (incl. `og:url`, `og:image`), Twitter card, canonical,
   `viewport`. Details + exact tags in `references/markup.md`.
4. **Favicon** — absolute-URL favicon + apple-touch-icon, crawlable. `references/markup.md`.
5. **Structured data** — add the Naver-supported JSON-LD types that fit the site.
   `references/structured-data.md` has copy-paste examples and the support matrix.
6. **Content hygiene** — original text (not text-baked-into-images), real `<a href>`
   links (not `onclick`), no duplicate/stuffed titles. `references/checklist.md`.
7. **Submission (manual, by the user)** — register in Search Advisor, verify ownership,
   submit sitemap + RSS, then verify with `site:` query. Steps in
   `references/submission.md`. These need the user's Naver login — produce the exact
   tag/feed for them and hand off with clear instructions; don't claim it's "submitted."

After code changes, verify the rendered HTML actually contains the tags (build/curl the
page or check the framework's generated `<head>`), then tell the user which submission
steps remain on their side.

## Reference files

- `references/markup.md` — every `<head>` tag Naver cares about, with exact syntax and
  the Naver-specific note for each (title, description, OG, Twitter, favicon, canonical,
  robots meta, viewport, mobile URL pairing).
- `references/structured-data.md` — Naver-supported schema.org types, JSON-LD examples,
  and what to use for e-commerce vs blog vs local business.
- `references/submission.md` — Search Advisor registration, ownership verification,
  sitemap/RSS submission, and how to confirm indexing.

Read the reference file relevant to the step you're on; don't load all three up front.
