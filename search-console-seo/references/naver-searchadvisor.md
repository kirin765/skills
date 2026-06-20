# Naver Search Advisor (웹마스터도구) + 웹마스터 가이드

Official guide: https://searchadvisor.naver.com/guide (JS-rendered SPA — to read
it programmatically, open it in the user's Chrome and `get_page_text`, or read
the sub-pages; a plain fetch only returns the nav shell).

## Console map (what to read, and where)

Open `https://searchadvisor.naver.com/console/board` (the site list), then per
site:

- **요약 / 사이트 현황** — registration status, last crawl.
- **수집/색인 → 웹페이지 수집** — how many URLs Naver collected vs submitted;
  per-URL collection status; a box to request collection of a specific URL.
- **요청 → 사이트맵 제출** — submitted sitemaps and their status (정상/오류).
- **요청 → RSS 제출** — submitted RSS feeds (separate from sitemap).
- **검증 → 사이트 최적화** — Naver's own diagnostic: flags missing title/meta,
  robots issues, missing OG, etc. This is the closest thing to a Naver Lighthouse.
- **검증 → 로봇스 / 수집 진단** — robots.txt as Naver sees it; fetch-as-Yeti.
- **사이트 소유확인** — which verification method/code is currently active.

Read these with `get_page_text`. Many panels hydrate from an internal JSON
endpoint — `javascript_tool` with `fetch` against the same origin can pull the
structured data directly when the rendered table is awkward to parse.

## 웹마스터 가이드 — the points that matter and that generic SEO misses

1. **Crawler = `Yeti`.** Allow it (blanket `allow: /` for `*` is enough). Never
   block crawlers by IP — Yeti's ranges change. Reference the sitemap from robots.
2. **Open Graph is a primary search signal.** Naver reads `og:title`,
   `og:description`, `og:image`, `og:url` to build the SERP snippet and decide
   exposure — weight it more than you would for Google. Every page needs OG.
3. **RSS = full body, submitted separately.** Naver discovers and ingests fresh
   content through RSS faster than through the sitemap, and it wants the **whole
   article**, not an excerpt. Emit `<content:encoded>` with the
   `xmlns:content="http://purl.org/rss/1.0/modules/content/"` namespace.
4. **Favicon: absolute URL, crawlable.** Naver renders it beside the result.
5. **Supported rich types**: Article, BreadcrumbList, FAQ,
   Review/AggregateRating, Recipe, HowTo, Video, Movie/TVSeries,
   Restaurant/Address, Software, Job, Channel, Carousel. `Product` is NOT a
   Naver-documented type — fine to ship for Google, but for Naver lean on
   BreadcrumbList + FAQ + Article + Review.
6. **`nosourceinfo`** robots directive opts a page out of Naver's AI-generated
   source description. Most pages should not set it.
7. Original text (not baked into images), real `<a href>` links (not `onclick`),
   unique non-stuffed titles.

## Verified full-body RSS pattern (Next.js App Router, React 19)

App Router blocks a bare `import ... from "react-dom/server"` in a route handler
("You're importing a component that imports react-dom/server"). Import the
`.edge` entry instead — it exposes `renderToStaticMarkup` and is not intercepted:

```ts
// app/rss.xml/route.ts
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server.edge"; // NOT "react-dom/server"

export const dynamic = "force-static";
// ...for each post, render its body component to an HTML string:
const html = renderToStaticMarkup(createElement(post.body) as ReactElement);
// emit inside the item:
//   <content:encoded><![CDATA[${html}]]></content:encoded>
// and add xmlns:content to the <rss> root.
```

If post bodies are structured data (block arrays) rather than components, render
the blocks to an HTML string directly — no react-dom needed. CDATA-wrap the body
and HTML-escape block text (`& < >`) so raw text can't inject tags. Make image
`src` and item `link`/`guid` absolute (prefix the site base URL).

Verify after editing: run the dev server and fetch `/rss.xml`; confirm the items
contain `content:encoded` and the body HTML, not just `<description>`.

## Submission (side-effecting — confirm first)

1. 사이트맵 제출: submit `https://<domain>/sitemap.xml`.
2. RSS 제출: submit `https://<domain>/rss.xml` (the full-body feed).
3. 웹페이지 수집: request collection for the most important / newly-changed URLs.
4. Re-run 사이트 최적화 to confirm warnings cleared.
5. After a crawl window, confirm with `site:<domain>` on Naver.
