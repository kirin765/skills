# Search Advisor registration, verification & feed submission

Naver indexing starts with 웹마스터도구 (Search Advisor), a console separate from Google
Search Console. These steps need the user's Naver login — you can produce the exact
verification tag and feed URLs, but the user clicks through the console. Never report
these as "done" from code alone.

## 1. Register & verify ownership

1. Go to https://searchadvisor.naver.com → 웹마스터도구 → 사이트 등록 → enter the site URL.
2. Verify ownership by one of:
   - **HTML 메타태그** — add `<meta name="naver-site-verification" content="…">` to the
     site `<head>` (in Next.js: `metadata.verification.other["naver-site-verification"]`).
   - **HTML 파일 업로드** — upload the given file to the site root.
3. If verification fails, check: the meta tag is on the **root/main** page, the page
   returns HTTP 200, robots.txt doesn't block `Yeti`, and no firewall blocks Naver IPs.

## 2. Allow the crawler

- Confirm `robots.txt` at the host root allows `Yeti` (`User-agent: *` + `Allow: /`
  suffices) and lists the sitemap.
- Don't block by IP — Yeti's IP ranges change. Control access via robots.txt only.

## 3. Submit sitemap

- 웹마스터도구 → 요청 → 사이트맵 제출 → enter the **absolute** sitemap URL
  (`https://www.example.com/sitemap.xml`).
- All URLs in the sitemap must be absolute and on the **same host** as the registered
  site, or they're skipped.

## 4. Submit RSS (content sites — important & Naver-specific)

- 웹마스터도구 → 요청 → RSS 제출.
- The RSS feed should contain the **full body** of recent posts, not just titles/excerpts
  — this is how Naver ingests fresh content quickly. (Sitemap = URL inventory; RSS =
  fresh full content.) For a pure product catalog with no blog, RSS is optional; add a
  feed once there's article/blog content.

## 5. Confirm indexing

- After Yeti visits, content typically appears within ~1 week.
- Check with a `site:` query: `site:www.example.com` in Naver search.
- Use 웹마스터도구 → 검증 → 웹페이지 검사 (URL inspection) for a single URL, and the
  콘텐츠 노출/클릭 report for exposure/CTR over time.

## 6. Optional but recommended

- 사이트 연관 채널 — link your Naver Blog / SmartStore / 소셜 channels in 웹마스터도구 so
  Naver associates them with the site.
- Register both desktop and mobile sites if you run a separate `m.` host (responsive
  single-URL sites don't need this).
