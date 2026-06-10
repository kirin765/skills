---
name: tistory-naver-crosspost
description: |
  Cross-post a blog article from a source URL (e.g. sajangbu.com/blog/<slug>) to **Tistory** and **Naver Blog** using the user's existing authenticated Chrome session via CDP (port 9222). Tistory is fully automated (title + body HTML via TinyMCE setContent + hero image paste + multi-word tags). Naver is automated (title + body + tags): the body is injected as plain text via the typing path (`page.keyboard.insertText`), NOT via clipboard paste — Naver's SmartEditor mis-decodes pasted UTF-8 as MacRoman and produces 외계어/mojibake, so paste is avoided entirely. Hero image is still dragged in manually. Use this skill whenever the user says "티스토리/네이버에 글 올려줘", "tistory naver 크로스포스트", "blog 같이 발행", "사장부 블로그를 티스토리·네이버에도 올려줘", or any variant of cross-posting one source blog post to those two Korean blog platforms. Also trigger when the user just finished publishing a post on their own site and asks to mirror it to Tistory/Naver. Do NOT use for scraping (see `naver-blog-brunch-scrape`) or for arbitrary CDP work (see `cdp-anywhere`).
---

# Tistory + Naver Blog Crosspost (CDP)

## What this does

Given a source article URL, hero image, title, and tag list, this skill drives the user's existing Chrome session (CDP port 9222) to:

1. **Tistory** — open `/manage/newpost/`, fill title, inject body HTML into TinyMCE, paste hero PNG at top, fill multi-word tags. Leaves the draft auto-saved. User clicks **[완료] → [발행]** themselves.
2. **Naver Blog** — open `GoBlogWrite.naver`, dismiss continue-popup, type title, press Enter to drop into the body, inject the body as plain text via `keyboard.insertText` line-by-line, then open the publish panel and fill tags (with spaces stripped — Naver commits on space). Hero image is still dragged in manually.

**Why insertText, not paste:** Naver's SmartEditor paste handler mis-decodes clipboard UTF-8 as MacRoman, turning Korean body text into 외계어/mojibake (e.g. `Ïø†Îå°…`). The clipboard itself is valid UTF-8 (`pbpaste` confirms) — the corruption happens inside SmartEditor's `paste` event. The typing path (`insertText`) bypasses the paste handler and lands clean, exactly like the title field. This was the recurring bug; do NOT revert the body to a clipboard/Cmd+V approach.

**Still plain text, not HTML:** only plain text is injected (HTML formatting is lost — that is acceptable). Section markers (`■`) and bullets (`•`) come from `htmlToPlain`. Links render as `text (url)`.

**Strikethrough caveat:** on a *fresh* editor (the script starts one and dismisses the draft-restore popup) no toolbar format is active, so text is clean. If you ever inject into a non-fresh editor where 취소선 is highlighted, typed text inherits it — Cmd+A → toggle 취소선 off.

## Preconditions

Before invoking the script:

1. **Chrome with CDP on port 9222** is running and the user is logged into both Tistory (`kirin765.tistory.com` or their own) and Naver Blog (`blog.naver.com/<id>` or their own).
   Probe: `curl -s http://localhost:9222/json/version` returns a JSON.
   If it fails, ask the user to launch:
   ```
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir="$HOME/chrome-cdp-profile"
   ```
2. **Hero image PNG** exists on disk (use the project's existing `public/blog-images/png/<slug>.png` or generate from SVG via `sharp`/`rsvg-convert` first).
3. **Source URL is live** — the article HTML must be reachable so the `<article>` body can be fetched. For sajangbu.com, this means the Vercel build is green for the new post.

## Inputs

The script accepts inputs via env vars or args. Defaults are tuned for `kirin765.tistory.com` + `blog.naver.com/kwan765`.

| input | source | example |
|-------|--------|---------|
| source URL | `--source` or env `SOURCE_URL` | `https://sajangbu.com/blog/coupang-fast-settlement-fee-truth` |
| hero PNG path | `--hero` or env `HERO_PNG` | `/Users/.../public/blog-images/png/<slug>.png` |
| title | `--title` or env `TITLE` | `쿠팡 빠른정산, '진짜 무료'인가?` |
| tags (comma-sep) | `--tags` or env `TAGS` | `쿠팡 빠른정산 수수료,셀러월렛 무료,...` |
| mode | first positional arg | `both` (default), `tistory`, `naver`, `tags`, `naver-tags` |

## Workflow

Run `scripts/crosspost.mjs` from the project root. The script supports incremental modes so you can re-run only the failed piece.

### Recommended order

1. **First pass** (full publish flow):
   ```bash
   node scripts/crosspost.mjs both \
     --source "https://sajangbu.com/blog/<slug>" \
     --hero  "/abs/path/to/public/blog-images/png/<slug>.png" \
     --title "..." \
     --tags  "tag1,tag2,tag3,tag4,tag5"
   ```
2. **Verify** via screenshots saved to `/tmp/tistory-crosspost-*.png` and `/tmp/naver-crosspost-*.png`.
3. **User actions** that remain:
   - Tistory tab → click **[완료]** → choose 공개 → **[발행]**
   - Naver tab → body is already injected (clean text) → set 카테고리 (defaults to 낙서장) → drag hero PNG to top of body → click **[발행]** in the already-open side panel
4. **Re-run partial modes** if anything goes wrong:
   - `tags` — refills Tistory tags on the existing open `/manage/newpost/` tab
   - `naver-tags` — clears + refills Naver publish-panel tags
   - `tistory` or `naver` alone — redoes just that platform

## Selectors and quirks (proven)

These are observed values as of 2026-05; bake them into the script with sensible fallbacks but check them when something breaks.

### Tistory `kirin765.tistory.com/manage/newpost/`

- Title input: `#post-title-inp`
- Body editor iframe: `#editor-tistory_ifr` (TinyMCE)
- Body injection: `window.tinymce.activeEditor.setContent(html)` — reliable, accepts full HTML
- Hero image: place caret at top of iframe body → write PNG to macOS clipboard via `osascript` `«class PNGf»` → `Cmd+V` → wait ~7s for upload (Kakao CDN URL appears in `<img src>`)
- Tag input: `#tagText` — accepts multi-word tags (e.g. `쿠팡 빠른정산 수수료`); commit each with Enter
- Save: auto-save fires every ~30s; the draft becomes the "임시저장 N" entry. Do NOT click **[완료]** in the script — that opens a publish modal the user must complete themselves.

### Naver `blog.naver.com/GoBlogWrite.naver`

- The editor lives in `iframe` whose `src` contains `PostWriteForm.naver`. Always re-find by URL substring; the iframe is recreated on navigation.
- Continue-from-draft popup: dismiss with `button:has-text('취소')` or `.se-popup-button-cancel` — search across all frames
- Title: `.se-title-text` (contenteditable, inside the editor frame)
- Body paragraphs: `.se-text-paragraph` (the editable lives in a nested iframe; `activeElement` reads as `IFRAME` from the outer frame — keyboard still reaches it after a click/Enter)
- **Body: inject via `keyboard.insertText`, never paste.** Naver's paste handler mis-decodes clipboard UTF-8 as MacRoman → mojibake. The script types the title, presses **Enter** (title → body caret), then `insertText`s each line. This lands clean. Do NOT switch back to clipboard/Cmd+V.
- Title em-dash gotcha: type the title with `keyboard.type` (real key events, char-by-char), not a single bulk `insertText` — a bulk insert of a string containing `—` can land the caret mid-string and scramble order.
- Publish-panel button: `button.publish_btn__m9KHH` (class hash changes occasionally; fall back to `button[class*='publish']`)
- Tag input (inside publish panel only): `#tag-input` with class `tag_input__rvUB5`
- **Naver tag input commits on SPACE**, not just Enter. So `"쿠팡 빠른정산 수수료"` becomes 3 chips. Strip spaces before typing → single token tag.
- Existing tag chips: `.tag__zPnmI`. Clear by focusing `#tag-input` and pressing Backspace once per existing chip + 1 extra.

## Generating the body HTML

For sajangbu.com posts the easiest source of clean, rendered HTML is the live page itself — fetching the TSX file and converting JSX is brittle (multiline `<a>` tags, `{" "}` separators, `&ldquo;` entities, relative `href="/"`).

The script fetches the live URL and extracts the `<article>...</article>` content, then:

- Strips `<script>`, `<noscript>`, `<!-- -->` comments
- Removes `class` / `style` / `data-*` attributes
- Absolutizes relative `href="/..."` → `https://sajangbu.com/...`

Both Tistory HTML and Naver plain text are derived from this same trimmed HTML.

If the source URL is NOT yet live (Vercel build still building), wait and re-run — don't try to parse the TSX locally.

## Failure modes and how to recover

| symptom | cause | fix |
|---------|-------|-----|
| `connectOverCDP timeout` | Chrome not on port 9222, or stale browser-level WS | check `curl http://localhost:9222/json/version`; if fine, retry — sometimes one connect attempt fails |
| Tistory body is empty | `tinymce.activeEditor` not ready | wait longer (sleep 3s after iframe appears), retry the `evaluate` |
| Tistory tags missing | clicked too early before page settled | re-run with `tags` mode |
| Naver editor frame not found | URL redirected through interstitial; popup not dismissed | dismiss popup loop already in script — if it still fails, manually close popup and re-run |
| Naver tags split on spaces | forgot to strip — should already be stripped by `raw.replace(/\s+/g, "")` | re-run `naver-tags` mode (it auto-clears existing chips first) |
| Naver body is 외계어/mojibake (`Ïø†Îå°…`) | someone reverted to clipboard paste — SmartEditor mis-decodes pasted UTF-8 | body must use `keyboard.insertText` (current script does). Re-run `naver` mode; do NOT paste |
| Naver body/title scrambled order | bulk `insertText` of a string with `—` jumped the caret | type the title with `keyboard.type` char-by-char; insert body line-by-line |
| Naver body has strikethrough | 취소선 toolbar button was active (non-fresh editor) | Cmd+A on body → click 취소선 to toggle off. Fresh editor (script default) avoids this |
| Hero image doesn't upload | macOS clipboard PNG format incorrect | check `osascript` command; PNG path must be absolute and exist |

## When to expand the skill

Currently scoped to **kirin765.tistory.com** + **blog.naver.com/kwan765**. If the user runs another blog identity:

- Override URLs via `--tistory-url` and `--naver-url` flags (already parameterized in the script).
- Class hashes (`publish_btn__m9KHH`, `tag__zPnmI`, etc.) are Naver-CDN-cached and can rotate. When a selector miss appears, probe via `document.querySelectorAll('button[class*="publish"]')` from DevTools and update the constant.

## Don't do this

- **Don't auto-click Naver's final 발행 button.** The skill leaves the publish panel open so the user verifies category, visibility, comment settings, then clicks 발행 themselves. Auto-publishing risks publishing with wrong category or wrong privacy.
- **Don't store cookies or login state.** The skill reuses the user's existing CDP session — no credential handling.
- **Don't try to parse the TSX/MDX source directly.** Fetching the live rendered HTML is dramatically more reliable.
- **Don't apply HTML to Naver body, and don't paste it.** SmartEditor mangles HTML, and pasting plain text mis-decodes UTF-8 → mojibake. Plain text via `keyboard.insertText` (typing path) is the proven path.

## Resources

- `scripts/crosspost.mjs` — main entry, parameterized via flags + env vars
- See also: `cdp-anywhere` skill for general CDP work; `naver-blog-brunch-scrape` for the inverse (reading Naver Blog content)
