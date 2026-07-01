# Naver SEO audit checklist

Run top to bottom against a project. Mark each ✅ present / ❌ missing / ⚠ partial before
changing anything, and report the audit to the user first.

## Crawlability
- [ ] `robots.txt` at host root, returns 200, allows `Yeti` (or `*` `Allow: /`)
- [ ] robots.txt lists absolute `Sitemap:` URL
- [ ] No `Disallow: /` on a site meant to be indexed; only private paths disallowed
- [ ] Favicon path and JS/CSS paths are **not** disallowed (Naver needs them)
- [ ] `sitemap.xml` exists, URLs absolute + same host
- [ ] Internal links are real `<a href>` (not `onclick`/JS-only)

## Per-page `<head>`
- [ ] Unique `<title>` per page; main page = brand name
- [ ] Unique meta `description`, 1–2 sentences, no keyword stuffing
- [ ] Open Graph: `og:type`, `og:title`, `og:description`, `og:image` (absolute), `og:url`
- [ ] Twitter card: `twitter:card/title/description/image/domain`
- [ ] `<link rel="canonical">` (absolute) — or framework `metadataBase` makes it absolute
- [ ] `<meta name="viewport" content="width=device-width">` (responsive)
- [ ] robots meta is `index,follow` (or absent) on public pages

## Identity & verification
- [ ] `naver-site-verification` meta present on root
- [ ] Favicon: absolute-URL `<link rel="shortcut icon"/icon/apple-touch-icon">`, crawlable
- [ ] `favicon.ico` and an apple-touch-icon PNG actually exist in the project

## Structured data (JSON-LD)
- [ ] Sitewide `Organization`/`Store` block (name, url, logo, address, tel)
- [ ] `BreadcrumbList` on nested pages
- [ ] `FAQPage` on policy/help pages (also strong for AEO)
- [ ] `AggregateRating`/`Review` where real ratings exist
- [ ] (Shop) `Product` JSON-LD for Google — note Naver has no Product rich type
- [ ] All structured data reflects content visible on the page

## Content hygiene
- [ ] Text content is real text, not baked into images
- [ ] No duplicate titles/descriptions across pages
- [ ] No keyword stuffing, hidden text, cloaking, or doorway pages
- [ ] Original content (not copied from elsewhere)

## Submission (user, in Search Advisor — see submission.md)
- [ ] Site registered + ownership verified in 웹마스터도구
- [ ] Sitemap submitted
- [ ] RSS submitted (content sites)
- [ ] Indexing confirmed via `site:` query
