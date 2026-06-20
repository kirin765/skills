# Access: driving the consoles via Claude in Chrome

The engine is the **Claude in Chrome extension** (`mcp__Claude_in_Chrome__*`)
against the user's authenticated sessions. Naver and Google are both logged-in
surfaces, so never try to log in or enter credentials — operate the session
that's already there.

## The hard constraint

`searchadvisor.naver.com` is **blocked from `navigate`**:

```
navigate(url:"https://searchadvisor.naver.com/console/board")
→ "This site is not allowed due to safety restrictions."
```

This is an extension policy, not a transient error. Don't retry the same
`navigate`. Instead use **user-opens, extension-operates**.

## User-opens, extension-operates (default pattern)

1. List browsers once to confirm a local Chrome is connected:
   `list_connected_browsers`.
2. Ask the user to open the exact console URL in their Chrome (paste it). For
   Search Advisor, the site list is `https://searchadvisor.naver.com/console/board`.
3. `tabs_context_mcp{createIfEmpty:false}` → find the tab whose URL matches.
4. Read it: `get_page_text(tabId)` for text, `read_page(tabId, filter:"interactive")`
   for actionable elements, `find` to locate a specific control.
5. Operate it: `computer`/`find`-driven clicks, `form_input` for fields,
   `javascript_tool` to read in-page JSON/DOM state or call the console's own
   internal endpoints (many console panels hydrate from a JSON API you can read
   with `fetch` inside `javascript_tool`).

Google Search Console (`search.google.com/search-console`) generally allows
`navigate` directly — try it first; fall back to user-opens if blocked.

## CDP fallback (only if the extension can't operate the open tab)

If even reading/clicking an already-open `searchadvisor` tab is blocked, fall
back to the `cdp-anywhere` skill's pattern: raw CDP on port 9222 against the
user's authenticated Chrome (the same engine `x-cdp-search` / `naver-cafe-scrape`
use). CDP is more fragile (extension targets can hang `connect_over_cdp`; use a
single page target) — prefer the extension and only reach for CDP when forced.
Pre-condition: the user's Chrome is running with `--remote-debugging-port=9222`.

## Side effects need explicit confirmation

Reading consoles is free. But submitting a sitemap/RSS, requesting indexing,
editing settings, or publishing edited content are outward-facing actions.
State exactly what you're about to click and get a clear "yes" in chat first.
Permission for one submit does not extend to the next.
