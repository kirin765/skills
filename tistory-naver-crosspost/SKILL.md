---
name: tistory-naver-crosspost
description: |
  Cross-post a blog article from a source URL (e.g. sajangbu.com/blog/<slug> or reviewboost's blog) to **Tistory** and **Naver Blog** using the user's existing authenticated Chrome session via CDP (port 9222). Tistory is fully automated (Kakao login click-through if logged out + title + body HTML via TinyMCE setContent + hero image paste + multi-word tags). Naver is fully automated (title + hero image + body + tags): the hero image is inserted via the 사진 toolbar button + native filechooser (no manual drag needed), and the body is typed line-by-line via `page.keyboard.type` (real key events), NOT via clipboard paste and NOT via a single bulk `insertText` per line — paste mis-decodes UTF-8 as MacRoman into 외계어/mojibake, and bulk insertText can scramble a line containing paired punctuation (quotes, em-dash, a colon segment). Use this skill whenever the user says "티스토리/네이버에 글 올려줘", "tistory naver 크로스포스트", "blog 같이 발행", "사장부/리뷰부스트 블로그를 티스토리·네이버에도 올려줘", or any variant of cross-posting one source blog post to those two Korean blog platforms. Also trigger when the user just finished publishing a post on their own site and asks to mirror it to Tistory/Naver. Do NOT use for scraping (see `naver-blog-brunch-scrape`) or for arbitrary CDP work (see `cdp-anywhere`).
---

# Tistory + Naver Blog Crosspost (CDP)

## What this does

Given a source article URL, hero image, title, and tag list, this skill drives the user's existing Chrome session (CDP port 9222) to:

1. **Tistory** — open `/manage/newpost/`; if the CDP profile is logged out, click through Kakao's "카카오계정으로 로그인" screen and pick the saved `TISTORY_KAKAO_EMAIL` profile card automatically (never types a password — hard-stops with a screenshot if a password field appears); then fill title, inject body HTML into TinyMCE, paste hero PNG at top, fill multi-word tags. Leaves the draft auto-saved. User clicks **[완료] → [발행]** themselves.
2. **Naver Blog** — open `GoBlogWrite.naver`, dismiss continue-popup, type title, insert the hero PNG via the 사진 toolbar button (native OS filechooser, no manual drag), then type the body as plain text via `keyboard.type` line-by-line into the paragraph Naver places after the image, then open the publish panel and fill tags (with spaces stripped — Naver commits on space).

**Why typing (keyboard.type), not paste:** Naver's SmartEditor paste handler mis-decodes clipboard UTF-8 as MacRoman, turning Korean body text into 외계어/mojibake (e.g. `Ïø†Îå°…`). The clipboard itself is valid UTF-8 (`pbpaste` confirms) — the corruption happens inside SmartEditor's `paste` event. The typing path bypasses the paste handler and lands clean. This was the recurring bug; do NOT revert the body to a clipboard/Cmd+V approach.

**Why keyboard.type, not bulk insertText:** the body used to be typed via a single `page.keyboard.insertText(line)` call per line. Per the title's own documented gotcha, a single bulk insert of a string containing paired punctuation (em-dash, quotes) can land the caret mid-string on some editors, so the body was switched to `keyboard.type()` (real per-character key events) as a defensive match to the title's fix. This is a real risk in general, but it turned out NOT to be the cause of the `'문의', '답변 없음'이 자주 보이면: ...` garbling reports — see the entity-decoding gotcha below, which was the actual root cause. Keep `keyboard.type` for the body regardless; do NOT revert to a single bulk `insertText` call per line.

**Why decodeEntities:** the actual cause of `'문의', '답변 없음'이 자주 보이면: ...` (and any other quote-containing line) rendering garbled on Naver was HTML-entity leakage, not a caret-jump. React SSR escapes text nodes — every apostrophe in the live page's rendered HTML is `&#x27;`, not `'`. `htmlToPlain()` strips HTML tags via regex but never decoded entities, so the literal string `&#x27;문의&#x27;, &#x27;답변 없음&#x27;이 자주 보이면...` got typed character-by-character into Naver. Tistory never showed this bug because TinyMCE's `setContent(html)` parses real HTML and decodes entities as part of normal HTML parsing. Fix: `htmlToPlain()` now calls `decodeEntities()` as its last step (after tag-stripping, so it also cleans up decoded `<a href>`/text content). Do NOT remove this call — check `/tmp/crosspost-body.txt` for stray `&#x27;`/`&amp;`/`&quot;` if a similar garbling report comes back.

**Still plain text, not HTML:** only plain text is injected (HTML formatting is lost — that is acceptable). Section markers (`■`) and bullets (`•`) come from `htmlToPlain`. Links render as `text (url)`.

**Strikethrough caveat:** on a *fresh* editor (the script starts one and dismisses the draft-restore popup) no toolbar format is active, so text is clean. If you ever inject into a non-fresh editor where 취소선 is highlighted, typed text inherits it — Cmd+A → toggle 취소선 off.

## Preconditions

Before invoking the script:

1. **Chrome with CDP on port 9222** is running. Naver Blog (`blog.naver.com/<id>` or their own) must already be logged in — there is no login automation for Naver. Tistory does NOT need to be pre-logged-in: if the session is logged out, the script drives the Kakao login click-through itself (see `ensureTistoryLogin`), as long as the target Kakao account has a saved profile card in this Chrome profile (i.e. the user has completed the password step at least once before).
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
| Kakao account (Tistory login) | env `TISTORY_KAKAO_EMAIL` | `kwan765@kakao.com` (default) |

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
   - Naver tab → hero image + body are already injected → set 카테고리 (defaults to 낙서장) → click **[발행]** in the already-open side panel
4. **Re-run partial modes** if anything goes wrong:
   - `tags` — refills Tistory tags on the existing open `/manage/newpost/` tab
   - `naver-tags` — clears + refills Naver publish-panel tags
   - `tistory` or `naver` alone — redoes just that platform

## Selectors and quirks (proven)

These are observed values as of 2026-05; bake them into the script with sensible fallbacks but check them when something breaks.

### Tistory `kirin765.tistory.com/manage/newpost/`

- Kakao login click-through (only when logged out — `ensureTistoryLogin`): "카카오계정으로 로그인" link is `a.link_kakao_id` / `a.btn_login.link_kakao_id`. On `accounts.kakao.com`, saved account cards are `a.wrap_profile:has(.tit_profile)` — match against `TISTORY_KAKAO_EMAIL`; a bare consent/continue screen has a `button:has-text('계속하기')`-style button instead. If `input[type=password]` ever appears, the script hard-stops (screenshot + throw) rather than typing a credential — that means the saved Kakao session is dead and needs a manual password login once.
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
- Hero image (`insertNaverHeroImage`, runs before body injection): 사진 toolbar button is `button.se-image-toolbar-button` — it opens a native OS filechooser (no resting `input[type=file]`), so arm `page.waitForEvent('filechooser')` *before* clicking, then `chooser.setFiles(heroPng)`. Committed images land as `.se-component.se-image` inside `.se-canvas .se-components-wrap`. Idempotent: skips if an image already exists (re-run safe). Inserting the image first pushes Naver's inserted order to `[title, IMAGE, body-text]`.
- Body paragraphs: target `.se-component.se-text .se-text-paragraph` **`.last()`**, not `.first()` — after the hero image is inserted, the first paragraph can be an image caption; the last one is the empty body paragraph Naver places after the image. (the editable lives in a nested iframe; `activeElement` reads as `IFRAME` from the outer frame — keyboard still reaches it after a click/Enter)
- **Body: type via `keyboard.type` per line, never paste, never bulk `insertText`.** Naver's paste handler mis-decodes clipboard UTF-8 as MacRoman → mojibake, so no clipboard/Cmd+V. A single bulk `insertText(line)` call per line can also scramble a line mid-string when it contains paired punctuation (quotes `'…'`, em-dash `—`, a `label: 설명` colon segment) — SmartEditor's autoformat (quote-pairing / auto-list-on-colon) mutates the DOM while `insertText` is still writing the rest of the chunk. `keyboard.type(line, {delay: 4})` fires real per-character key events so the mutation lands between characters instead of mid-chunk. The script types the title, inserts the hero image, clicks the last body paragraph, then types each line this way. Do NOT switch body lines back to clipboard/Cmd+V or a single bulk `insertText` call.
- Title em-dash gotcha: type the title with `keyboard.type` (real key events, char-by-char), not a single bulk `insertText` — a bulk insert of a string containing `—` can land the caret mid-string and scramble order. Body lines hit the same class of bug and are fixed the same way (see above).
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
| Naver body is 외계어/mojibake (`Ïø†Îå°…`) | someone reverted to clipboard paste — SmartEditor mis-decodes pasted UTF-8 | body must use `keyboard.type` (current script does). Re-run `naver` mode; do NOT paste |
| Naver body shows literal `&#x27;문의&#x27;, &#x27;답변 없음&#x27;이 자주 보이면: ...` instead of `'문의', '답변 없음'이 자주 보이면: ...` | React SSR HTML-escapes text nodes (apostrophes → `&#x27;`, etc.) in the live page; `htmlToPlain()` stripped tags but never decoded entities, so the literal `&#x27;` string got typed into Naver verbatim. Tistory is unaffected because TinyMCE's `setContent` parses real HTML and decodes entities naturally. | confirm `htmlToPlain()` calls `decodeEntities(s)` after tag-stripping (current script does); re-run `naver` mode. Check `/tmp/crosspost-body.txt` for stray `&#x27;`/`&amp;`/`&quot;` before blaming the editor. |
| Naver body/title scrambled order | bulk `insertText` of a string with `—` jumped the caret | type the title and each body line with `keyboard.type` char-by-char, never a single bulk `insertText` call |
| Naver body has strikethrough | 취소선 toolbar button was active (non-fresh editor) | Cmd+A on body → click 취소선 to toggle off. Fresh editor (script default) avoids this |
| Hero image doesn't upload (Tistory) | macOS clipboard PNG format incorrect | check `osascript` command; PNG path must be absolute and exist |
| Hero image doesn't insert (Naver) | 사진 toolbar button not found, or no filechooser fired | script logs `[naver-img] ... skip image` and continues — drag the PNG in manually; re-run `naver` mode after checking `button.se-image-toolbar-button` still exists |
| Tistory stuck on Kakao "카카오계정으로 로그인" / profile picker | CDP session was logged out and the script's `ensureTistoryLogin` click-through wasn't present or a password field appeared | confirm you're on the current `crosspost.mjs` (has `ensureTistoryLogin`); if a `input[type=password]` prompt appears the saved Kakao session is dead — log in manually once in that Chrome profile, then re-run |
| `[tistory] N saved Kakao accounts, none matching ...` | `TISTORY_KAKAO_EMAIL` env doesn't match any saved profile card text | set `TISTORY_KAKAO_EMAIL` to the right address, or log into the right account in that Chrome profile first |

## When to expand the skill

Currently scoped to **kirin765.tistory.com** + **blog.naver.com/kwan765**. If the user runs another blog identity:

- Override URLs via `--tistory-url` and `--naver-url` flags (already parameterized in the script).
- Class hashes (`publish_btn__m9KHH`, `tag__zPnmI`, etc.) are Naver-CDN-cached and can rotate. When a selector miss appears, probe via `document.querySelectorAll('button[class*="publish"]')` from DevTools and update the constant.

## Don't do this

- **Don't auto-click Naver's final 발행 button.** The skill leaves the publish panel open so the user verifies category, visibility, comment settings, then clicks 발행 themselves. Auto-publishing risks publishing with wrong category or wrong privacy.
- **Don't store cookies or login state.** The skill reuses the user's existing CDP session — no credential handling.
- **Don't try to parse the TSX/MDX source directly.** Fetching the live rendered HTML is dramatically more reliable.
- **Don't apply HTML to Naver body, and don't paste it.** SmartEditor mangles HTML, and pasting plain text mis-decodes UTF-8 → mojibake. Plain text via `keyboard.insertText` (typing path) is the proven path.
- **Don't type a Kakao password.** `ensureTistoryLogin` only click-throughs the saved-profile picker; if it ever sees `input[type=password]` it hard-stops with a screenshot instead of typing credentials.

## Resources

- `scripts/crosspost.mjs` — main entry, parameterized via flags + env vars
- See also: `cdp-anywhere` skill for general CDP work; `naver-blog-brunch-scrape` for the inverse (reading Naver Blog content)
