# Naver `<head>` markup reference

Every tag Naver's 웹마스터 가이드 calls out, with exact syntax and the Naver-specific
reason it matters. Framework note: in Next.js App Router, most of these come from the
`metadata` export (and `metadataBase` makes OG/canonical URLs absolute) — prefer that
over hand-written `<head>` tags. Hand-written tags are shown here because the guide
specifies them and because non-Next sites need them verbatim.

## Title — unique per page

```html
<head><title>페이지 제목</title></head>
```

- Main page title = **brand/상호/서비스명** (proper noun). It's how brand-name search
  finds you.
- Every page gets a **unique** title describing that page's content. Never reuse one
  title sitewide — duplicate titles hurt discoverability.
- No fixed length limit, but keep it short enough to render in the SERP. Repeating a
  keyword 2+ times, spam keywords, or unrelated promo text = ranking penalty.
- Naver may still auto-pick the displayed title from title + OG + anchors; your tag is
  an input, not a guarantee.

## Meta description — unique, 1–2 sentences

```html
<head><meta name="description" content="페이지 설명"></head>
```

- One short paragraph (1–2 sentences) specific to the page. Don't paste the full body,
  don't duplicate the title, don't reuse the same description across pages, don't list
  bare keywords — each of those is a documented penalty trigger.
- The actual snippet shown is auto-extracted by Naver from this tag + body relative to
  the query, so write for humans.

## Open Graph — used by Naver search, not only social

```html
<head>
<meta property="og:type" content="website">
<meta property="og:title" content="페이지 제목">
<meta property="og:description" content="페이지 설명">
<meta property="og:image" content="https://www.example.com/og.jpg">
<meta property="og:url" content="https://www.example.com/page">
</head>
```

- Naver explicitly states its crawler also uses OG for page analysis and exposure.
  Treat OG as required on every page, not optional social polish.
- `og:image` should be an absolute URL. Provide one default site image + per-page images
  where meaningful (product photo, article hero).

## Twitter / social card

```html
<head>
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="페이지 제목">
<meta name="twitter:description" content="페이지 설명">
<meta name="twitter:image" content="https://www.example.com/og.jpg">
<meta name="twitter:domain" content="example.com">
</head>
```

- Naver's 소셜 미디어 section recommends these so you control how shared links render.
  Low cost; include `summary` (or `summary_large_image` if you have a big image).

## Favicon — absolute URL, crawlable

```html
<head><link rel="shortcut icon" href="https://www.example.com/favicon.ico"></head>
```

- `href` **must be an absolute path**, not relative — this is called out explicitly.
- Valid `rel` values: `shortcut icon`, `icon`, `apple-touch-icon`,
  `apple-touch-icon-precomposed`.
- Naver renders the favicon next to your SERP result, so a missing/blocked favicon is a
  visible quality gap. Ensure robots.txt does not Disallow the favicon path.
- Provide a standard `favicon.ico` plus a larger PNG (e.g. 152×152 apple-touch-icon).

## Canonical / 선호 URL — collapse duplicates

```html
<head><link rel="canonical" href="https://www.example.com/article/1"></head>
```

- Point duplicate or parameterized URLs at the single 대표(canonical) URL so Naver
  doesn't split signals across copies.
- **Separate mobile host (`m.example.com`):** each mobile page should canonical to its
  1:1 desktop URL, and both desktop + mobile sites should be registered in 웹마스터도구.
  (Responsive single-URL sites don't need this — Naver prefers responsive.)

## robots meta — page-level control

```html
<head><meta name="robots" content="index,follow"></head>
```

- Default/desired for public pages is `index,follow` (or just omit the tag).
- `noindex` → excluded from results; `nofollow` → links on the page not crawled (this
  also reduces how many of your pages Naver discovers — don't set it site-wide).
- `nosourceinfo` → opt this page out of Naver's **AI-generated source description**.
  Only set deliberately.
- Redirect-only pages may not honor the meta — set the same directive on the redirect
  target instead.

## Viewport — responsive (Naver-preferred)

```html
<head><meta name="viewport" content="width=device-width"></head>
```

- Naver recommends responsive (single URL, adapts to screen) over a separate mobile
  host. Next.js injects a viewport tag by default; confirm it's present on non-Next sites.

## robots.txt + sitemap

```
User-agent: *
Allow: /
Sitemap: https://www.example.com/sitemap.xml
```

- `Yeti` is Naver's crawler. `User-agent: *` + `Allow: /` covers it. Add an explicit
  `User-agent: Yeti / Allow: /` block **only** if you otherwise restrict bots:

  ```
  User-agent: *
  Disallow: /
  User-agent: Yeti
  Allow: /
  ```
- robots.txt must sit at the host root (`/robots.txt`) and is scoped per host+protocol+
  port (the `http://` file does not apply to `https://`).
- Disallow only the patterns you truly want hidden (admin, private, checkout) — never
  `Disallow: /` for a site you want indexed.
- Use **real `<a href="…">` links**, not `onclick="javascript:…"`, or Yeti can't resolve
  the destination URL and won't crawl deeper. Sitemap/RSS links must be **absolute** and
  on the **same host** as the registered site, or they're skipped.
