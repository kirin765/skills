# Tistory + Naver Blog Crosspost — Portable Implementation Guide

Consolidated from three skill versions (`tistory-naver-crosspost`, `-v2`, `-v3`) and verified
against their actual `scripts/crosspost.mjs` sources on 2026-07-30. Written so an LLM with no
prior context can pick a version, run it, or re-implement it elsewhere.

Everything here drives **an already-logged-in Chrome over CDP port 9222** with Playwright
(`chromium.connectOverCDP`). No credentials are stored or typed anywhere.

---

## 1. Decide which version to run

| | v1 (`tistory-naver-crosspost`) | v2 (`-v2`) | v3 (`-v3`) — current default |
|---|---|---|---|
| Naver | full publish (공개) | fills + leaves publish panel open | full publish (공개) |
| Tistory | CDP: login → TinyMCE → tags → 임시저장 (user clicks 완료/발행) | same as v1 + Kakao DKAPTCHA auto-solver | **no CDP at all** — writes a queue JSON, fires a detached scheduler |
| Naver category | `--naver-category`, falls back to `낙서장` | not supported | `--naver-category` + `--naver-topic` (no fallback) |
| Rich body formatting | yes (bold QnA, sentence breaking) | yes | **no** (plain `htmlToPlain` only) |
| Daily automation | none | none | launchd: 08:20 writer + 09:00 publisher, two independent queues |

**Pick v3** for the daily pipeline and for anything where Tistory should publish itself.
**Pick v1** when you need the richer body formatting (QnA bold, sentence breaks) or a Tistory
draft you inspect before publishing. **v2 only** matters if you hit a Kakao DKAPTCHA and want
its auto-solver; it is otherwise a v1 with the Naver auto-publish removed.

Script paths: `~/.claude/skills/tistory-naver-crosspost{,-v2,-v3}/scripts/crosspost.mjs`

---

## 2. Preconditions

1. **Node + Playwright** available (`import { chromium } from "playwright"`).
2. **CDP Chrome on port 9222 with at least one open tab.**
   - Probe: `curl -s http://localhost:9222/json/version`
   - All three scripts auto-launch a *dedicated* profile if it's down (macOS only):
     `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"` — then poll `:9222` for 15s.
   - The user's everyday Chrome uses a different `--user-data-dir` and is never touched.
     Never judge CDP state by `pgrep Chrome`; only by the `:9222` response.
   - **Zero page targets is a real failure mode.** `connectOverCDP` throws
     `Browser context management is not supported` while `/json/version` still returns healthy
     JSON. Guard with `ensureCdpTab()`: if `/json/list` has no `type === "page"`, do
     `curl -X PUT http://localhost:9222/json/new?about:blank` and wait ~800ms.
3. **Naver Blog already logged in** in that Chrome profile. There is **no Naver login
   automation** and none should be written.
4. **Tistory login** — v1/v2 click through Kakao's saved-profile picker (see §6); v3 delegates
   the whole login surface to the background scheduler.
5. **Hero PNG on disk**, absolute path, real `.png` (v3 rejects other extensions — the Tistory
   clipboard path needs `«class PNGf»`). Convert SVG first with `sharp`/`rsvg-convert`.
6. **Source reachable** — a live URL, or a local HTML file whose body is wrapped in `<article>`.
   If the source is a site you just deployed, wait for the build to go green; do **not** try to
   parse TSX/MDX locally (multiline `<a>`, `{" "}`, entities, relative hrefs make it brittle).

---

## 3. Inputs (identical flag/env contract in all three)

| input | flag | env | notes |
|---|---|---|---|
| source | `--source` | `SOURCE_URL` | live URL **or** absolute local HTML path |
| hero image | `--hero` | `HERO_PNG` | absolute `.png` |
| title | `--title` | `TITLE` | the only title source; in-article `<h1>` is stripped |
| tags | `--tags` | `TAGS` | comma-separated |
| mode | first positional arg | — | see §4 |
| Kakao account (v1/v2) | — | `TISTORY_KAKAO_EMAIL` | default `kwan765@kakao.com` |
| Naver 게시판 | `--naver-category` | `NAVER_CATEGORY` | v1 falls back to `낙서장`; v3 does not |
| Naver 주제 분류 | `--naver-topic` (v3) | `NAVER_TOPIC` | undocumented in v3's SKILL.md, present in code |
| Tistory category | `--category` (v3) | `TISTORY_CATEGORY` | goes into the queue JSON |
| reserved publish | `--scheduled-at` (v3) | `SCHEDULED_AT` | ISO 8601 with `+09:00` |
| queue filename slug | `--slug` (v3) | — | default derived from source |
| skip scheduler hook | `--no-hook` (v3) | — | batch-queue several, hook once |
| skip Naver publish | `--no-publish-naver` (v1) | — | leaves the panel open |
| blog URLs | `--tistory-url`, `--naver-url` | `TISTORY_URL`, `NAVER_URL` | defaults `kirin765.tistory.com/manage/newpost/`, `blog.naver.com/GoBlogWrite.naver` |

Debug artifacts always written: `/tmp/crosspost-body.txt` (Naver plain text), `/tmp/crosspost-body.html`
(v1/v2 Tistory HTML), plus screenshots under `/tmp/{tistory,naver}-*.png`.

---

## 4. Modes

| mode | v1 / v2 | v3 |
|---|---|---|
| `both` (default) | Tistory draft, then Naver | Naver full publish **now**, then Tistory queue + hook |
| `naver` | Naver only | Naver only, through 발행 |
| `tistory` | Tistory CDP only | alias of `tistory-queue` (JSON + hook, no browser) |
| `tistory-queue` | — | queue JSON + hook |
| `queue` | — | enqueue **both** `~/.naver-queue` and `~/.tistory-queue`, no hook, no browser |
| `tags` | refill Tistory tags on the open tab | — |
| `naver-tags` | clear + refill Naver tags on the open publish panel | same |

Example (v3):

```bash
node ~/.claude/skills/tistory-naver-crosspost-v3/scripts/crosspost.mjs both \
  --source "https://sajangbu.com/blog/<slug>" \
  --hero   "/abs/path/public/blog-images/png/<slug>.png" \
  --title  "쿠팡 빠른정산, '진짜 무료'인가?" \
  --tags   "쿠팡빠른정산,셀러월렛,정산수수료" \
  --naver-category "생활 정보" \
  --category "쿠팡·스마트스토어"
```

**Order inside `both` is deliberate: Naver first, Tistory hook last.** The hook spawns a
detached daemon that drives the *same* CDP Chrome — firing it earlier means two Playwright
drivers fighting over one browser. v3 still validates the Tistory inputs (hero exists, is
`.png`, source has `<article>`) **before** the irreversible Naver publish.

---

## 5. The three non-negotiable Naver text rules

These are the bugs that kept recurring. Reverting any of them reintroduces a known failure.

**(a) Type the body — never paste.** Naver SmartEditor's `paste` handler mis-decodes clipboard
UTF-8 as MacRoman, so Korean text lands as mojibake (`Ïø†Îå°…`). The clipboard itself is fine
(`pbpaste` confirms), the corruption is inside the editor. Typing bypasses the handler.

**(b) `keyboard.type`, not a single bulk `insertText` per line.** A bulk insert of a string
containing paired punctuation (`'…'`, `—`, a `label: 설명` colon segment) can land the caret
mid-string: SmartEditor's autoformat mutates the DOM while `insertText` is still writing.
`keyboard.type(line, { delay: 4 })` fires real per-character key events, so the mutation lands
between characters. Same fix applies to the **title** field.

**(c) Decode HTML entities after tag-stripping.** React SSR escapes text nodes, so every
apostrophe in a live page's HTML is `&#x27;`. Tag-stripping by regex leaves those literals, and
they get typed out verbatim — this was the *actual* cause of
`&#x27;문의&#x27;, &#x27;답변 없음&#x27;이 자주 보이면: …`, not a caret jump. Tistory never
showed it because `tinymce.setContent(html)` parses real HTML and decodes as it goes.

```js
function decodeEntities(s) {
  return s
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g,           (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&nbsp;/g, " ").replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}
```

When a garbling report comes in, grep `/tmp/crosspost-body.txt` for stray `&#x27;` / `&amp;` /
`&quot;` **before** blaming the editor.

---

## 6. Selector reference (live-verified; class hashes rotate)

### Body extraction pipeline (`fetchArticleHtml`)

Match `<article[^>]*>([\s\S]*?)</article>`, then in order: drop the first `<h1>…</h1>`, strip
`<script>` / `<noscript>` / `<!-- -->`, strip `class|className|style|data-*` attributes,
absolutize `href="/…"` against the source origin. Both outputs derive from this one trimmed HTML.

- **Tistory HTML** — v1/v2 `formatTistoryHtml`: `<dt>` → `<p data-ke-size="size16"><b>Q…</b></p>`,
  `<dd>` → answer `<p>` + a `&nbsp;` spacer `<p>`, and inline-tag-free `<p>`s longer than 90
  chars get split at sentence boundaries with `<br>`.
- **Naver plain text** — `htmlToPlain`: `<h2>` → `\n\n■ $1\n\n`, `</p>` → `\n\n`, `<li>` →
  `• …`, `<a href>` → `text (url)`, strip remaining tags, `decodeEntities`, collapse 3+ newlines.
  v1/v2 additionally wrap QnA questions as `**…**` (typed with `Cmd+B` toggles) and break
  body lines over 60 chars at sentence boundaries. **v3 has none of that** — its `htmlToPlain`
  is the plain version.

### Tistory `/manage/newpost/` (v1/v2 only)

| what | selector / method |
|---|---|
| Kakao login link | `a.link_kakao_id`, `a.btn_login.link_kakao_id` |
| saved account cards | `a.wrap_profile:has(.tit_profile)` — filter by `TISTORY_KAKAO_EMAIL`; the "새 계정으로 로그인" row shares the class but has no `.tit_profile` |
| consent screen | `button:has-text('계속하기' \| '동의하고 계속하기' \| '전체 동의')`, `button.btn_agree`, `button[name=user_oauth_approval]` |
| **password field** | `input[type=password]` → **hard-stop**: screenshot `/tmp/tistory-login-HARDSTOP.png` and throw. Never type a credential. |
| title | `#post-title-inp` (`.fill()`) |
| editor iframe | `#editor-tistory_ifr` (TinyMCE) |
| body injection | `window.tinymce.activeEditor.setContent(html)` |
| hero image | focus iframe body, collapse a Range at offset 0, put PNG on the clipboard via `osascript … as «class PNGf»`, `Meta+V`, wait ~8s for the Kakao CDN URL |
| tags | `#tagText` — accepts multi-word tags, commit each with Enter |
| draft save | `span.btn-draft a.action` (an `<a>`, not a `<button>`; the adjacent number opens the draft list) |
| native confirm on existing draft | register `page.on("dialog", d => d.dismiss())` **before** navigating, or an unhandled ProtocolError kills the run |
| DKAPTCHA (v2) | `iframe[src*='dkaptcha']` → `input[type=text], input[placeholder*='정답']`, fill, dispatch synthetic `input`/`change`/`keyup` to enable submit, then `#btn_dkaptcha_submit`, `button.btn_submit_dkaptcha`, `button:has-text('답변 제출')` |

Never click **[완료]** from a script in v1/v2 — it opens a publish modal the user finishes.

### Naver `GoBlogWrite.naver`

The editor lives in an iframe whose URL contains `PostWriteForm`. **Always re-find it by URL
substring** — it is recreated on navigation.

| what | selector / method |
|---|---|
| draft-recovery popup | `button.se-popup-button-cancel` (also `button:has-text('취소')`); poll ~6× 700ms across all frames |
| title | `.se-title-text` → click, then `keyboard.type` |
| 사진 button | `button.se-image-toolbar-button` — opens a **native OS filechooser**, no resting `input[type=file]`. Arm `page.waitForEvent("filechooser")` *before* clicking, click with `noWaitAfter: true`, then `chooser.setFiles(hero)` |
| committed image | `.se-canvas .se-components-wrap .se-component.se-image` — poll up to 25 × 800ms; skip the whole step if count > 0 (idempotent re-run) |
| body paragraph | `.se-component.se-text .se-text-paragraph` **`.last()`** — `.first()` can be the title or an image caption; the last is the empty paragraph Naver puts after the image |
| publish panel open | `button.publish_btn__m9KHH` → `button[class*='publish_btn']` → `button[class*='publish']`; detect "already open" via `/태그 편집/.test(document.body.innerText)` |
| tag input | `#tag-input` (`tag_input__rvUB5`) — **commits on SPACE**, so `raw.replace(/\s+/g, "")` before typing or one tag becomes three chips |
| existing chips | `.tag__zPnmI` — clear by focusing the input and pressing Backspace `chipCount + 1` times |
| 게시판 dropdown | trigger `button[class*='selectbox_button']` (aria-label 카테고리 목록 버튼); items `label[class*='radio_label']` (v3) or `span[data-testid^='categoryItemText_']` (v1). Sub-categories prepend a blind `하위 카테고리` span — strip before exact-matching |
| 주제 분류 (v3) | row `div[class*='option_theme']` → its `a`/`button` opens a layer; pick `label[class*='radio_label']`, confirm with `button[class*='ok_btn']`, else close with `button[class*='cancel_btn']` so it can't block 발행 |
| visibility | the `label` matching `/^전체\s*공개/`, else exact `공개`; check the linked radio's `checked` first |
| final 발행 | `[data-testid='seOnePublishBtn']` → `button[class*='confirm_btn']` → the **last** button whose exact text is `발행` and whose class does not match `publish_btn` |
| success test | URL leaves `GoBlogWrite`/`PostWriteForm` (v3) or gains a 9+ digit post id / `logNo=` (v1); dismiss any `button.se-popup-button-confirm` / `button:has-text('확인')` while polling, 25s deadline |

**Category gotcha (cost a wrong-category publish):** a JS `el.click()` on the category item does
**not** register with React — the post goes out under the previous category while the click
"succeeds". Use a real Playwright click, then verify the trigger button's text changed to the
target before publishing. v3 clicks the label inside `evaluate` and *verifies the trigger text
afterwards*; if you see the wrong category on a published post, this is the first suspect.

**Strikethrough:** on a fresh editor no toolbar format is active. On a non-fresh one, typed text
can inherit 취소선. Both v1 and v3 detect it via `getComputedStyle(...).textDecorationLine`
containing `line-through`, then `Meta+A` and click the button matching `/취소선|strikethrough/i`.

---

## 7. v3's Tistory queue architecture (no browser)

Spec of record: `~/.gemini/config/skills/tistory-post/references/agent-queue-guide.md`.

1. Build the job JSON — `title`, `source` (live URL or **absolute** local HTML path containing
   `<article>`), `hero` (**absolute real `.png`**), optional `tags[]`, `category`,
   `naverCategory`, `naverTopic`, `scheduledAt`, `tistoryUrl`.
2. Write it to `~/.tistory-queue/pending/post-YYYYMMDD-<slug>.json`, then re-`JSON.parse` it
   from disk as a validity self-check.
3. Fire `node ~/.gemini/config/skills/tistory-post/scripts/tistory-scheduler.mjs hook` — **with
   no path argument.** `hook <path>` runs `addJob`, which *copies* the file into `pending/`; the
   file is already there, so passing the path enqueues it twice → **double publish**. Only pass
   a path for a JSON written *outside* `pending/`.
4. Return immediately (<0.1s). A detached daemon does the login/publish. Do not wait, poll, or
   monitor — progress lives in `~/.tistory-queue/logs/`. Fire-and-forget is the contract.

Failed items land in `~/.tistory-queue/failed/` with an `error` field; fix the JSON, move it
back to `pending/`, hook again.

### Two independent queues — do not merge them

`~/.naver-queue/` and `~/.tistory-queue/` are separate on purpose. Any tistory hook/run moves
pending JSONs into *its* `done/`; sharing one queue would silently starve the Naver publish. The
tistory scheduler does not know `~/.naver-queue/` exists, and the daily Naver job never reads
`~/.tistory-queue/`.

### Daily launchd pipeline

| job | time | what |
|---|---|---|
| `com.brain.daily-blog-writer` | 08:20 | headless `claude -p` with `scripts/daily-writer-prompt.md`: RSS-first dedupe against `rss.blog.naver.com/<id>.xml` (a duplicate-post incident on 2026-07-27 is why RSS comes before any API), free-stack keyword research, 4-gate verdict, AEO draft + hero PNG, then `queue` mode. Skips entirely if `~/.naver-queue/pending/` is non-empty (one-post buffer). Uses `--allowedTools`, not a permission-bypass flag. |
| `com.brain.daily-crosspost` | 09:00 | `scripts/daily-crosspost.mjs`: picks the oldest due JSON from `~/.naver-queue/pending/` (name sort, future `scheduledAt` skipped, one per day), runs v3 `naver` mode, parses `[naver-publish] ✅ PUBLISHED → <url>` from stdout. Success → stamp `naverPublishedAt`/`naverUrl`, move to `done/`. Failure → JSON stays in `pending/` for tomorrow, exit 1. Telegram ✅/⚠ either way (credentials from `~/niche-finder/.env`). Logs: `~/.naver-queue/logs/`. |

Manual test: `launchctl kickstart gui/$UID/com.brain.daily-crosspost`.

---

## 8. The source article must already be AEO-shaped

These skills copy the source **verbatim** — they never restructure content. Full spec:
`references/aeo-template.md` in any of the three skill dirs.

1. **Answer-first** — the first paragraph is a 40–80자 direct answer to the title's question,
   in `<b>`. The hook comes *after*.
2. **Question-form H2s** — "쿠팡 구매확정은 언제 되나요?", not "구매확정". Each header = a query.
3. **자주 묻는 질문 section** near the end — 3–6 self-contained Q&A as
   `<h2 data-ke-size="size26">자주 묻는 질문</h2>` + `<dl><dt><b>Q. …</b></dt><dd>…</dd></dl>`.
4. **Tables** for comparisons/rates/dates, `<ol>` for procedures.
5. Entity defined on first mention; alt text on images.
6. Naver ranking (C-Rank/D.I.A.): repeat the target keyword in title + first paragraph + tags.

Platform facts:

- **JSON-LD `<script>` is stripped on save by both TinyMCE and Naver SmartEditor.** Per-post
  FAQPage/HowTo schema via the body is impossible — and Google deprecated FAQ/HowTo rich
  results in 2023, so skip it. The AEO value is in the visible structure.
- Tistory renders `<table>` fine. **Naver body is plain text**, so HTML tables do not transfer —
  insert them with the 표 toolbar manually, or make the source use a labeled list.

**Editing an existing Tistory post** (not the create flow): use `window.tinymce.activeEditor`
and call `ed.save()` after `setContent`/append, or the publish serializes the OLD body. To append
without re-triggering image upload (the "0개의 파일을 업로드 중" hang), use
`ed.getBody().insertAdjacentHTML('beforeend', html)` rather than a full `setContent`. Space rapid
successive publishes ~25s apart or Kakao trips a DKAPTCHA.

---

## 9. Failure modes

| symptom | cause | fix |
|---|---|---|
| `connectOverCDP timeout` | Chrome not on 9222, or a stale browser-level WS | check `/json/version`; if healthy, just retry |
| `Browser context management is not supported` | CDP Chrome has zero page targets (`/json/version` still looks fine) | `curl -X PUT http://localhost:9222/json/new?about:blank`, retry |
| body duplicates the title | source wraps its title in an in-article `<h1>` | `fetchArticleHtml` strips the first `<h1>`; title comes only from `--title` |
| Naver body mojibake (`Ïø†Îå°…`) | someone reverted to clipboard paste | restore `keyboard.type`; re-run `naver` |
| literal `&#x27;` in the Naver body | `decodeEntities` missing or moved before tag-stripping | restore it as the last step of `htmlToPlain`; check `/tmp/crosspost-body.txt` |
| Naver line order scrambled | bulk `insertText` on a line with `—` or paired quotes | `keyboard.type` per line, char-by-char |
| Naver body struck through | 취소선 was active on a non-fresh editor | `Meta+A` → toggle 취소선 off (the scripts auto-detect) |
| Naver tags split into extra chips | spaces not stripped | re-run `naver-tags` (it clears chips first) |
| published under the wrong category | JS `el.click()` didn't register with React | real Playwright click + verify the trigger button's text before 발행 |
| `공개 radio not found` | publish-panel DOM changed | it publishes with the panel's sticky visibility — verify the post, update the label matcher |
| `final 발행 button not found` | `confirm_btn` hash rotated and text lookup missed | post is a draft with the panel open; click 발행 manually, probe `document.querySelectorAll("button[class*='confirm']")` |
| `no navigation within 25s` | slow publish or an unhandled popup | check `/tmp/naver-publish-TIMEOUT.png` — it may actually be live; check the blog before re-running |
| hero image not inserted (Naver) | 사진 button missing or no filechooser fired | script logs `[naver-img] … skip image` and continues; drag it in manually |
| hero image not uploaded (Tistory) | clipboard PNG format wrong | absolute path, real `.png`, check the `osascript «class PNGf»` call |
| stuck on Kakao profile picker | logged-out session, or a password field appeared | if `input[type=password]` shows, the saved Kakao session is dead — log in manually once in that profile |
| `N saved Kakao accounts, none matching …` | `TISTORY_KAKAO_EMAIL` matches no profile card | set the right address, or log into the right account first |
| Tistory published twice | someone passed the pending JSON's path to `hook` | bare `hook`, never `hook <path>` for a file already in `pending/` |
| queue item in `failed/` with `Missing required fields` | JSON lacks title/source/hero | fix, move back to `pending/`, hook again |
| hook printed nothing | `tistory-scheduler.mjs` moved | fix the `SCHEDULER` const path |

---

## 10. Don't do this

- **Don't paste or bulk-insert Naver title/body text.** `keyboard.type` only. See §5.
- **Don't remove `decodeEntities`** from `htmlToPlain`.
- **Don't apply HTML to the Naver body** — SmartEditor mangles it; plain text is the proven path.
- **Don't store cookies, tokens, or credentials.** Reuse the existing CDP session.
- **Don't type a Kakao password.** The login click-through hard-stops on `input[type=password]`.
- **Don't touch Tistory via CDP in v3** — no `/manage/newpost/`, no TinyMCE, no DKAPTCHA. That
  whole surface belongs to the background scheduler.
- **Don't pass the pending JSON's path to `hook`** (double publish).
- **Don't wait for the Tistory publish to finish** in v3.
- **Don't parse TSX/MDX source directly** — fetch the rendered HTML.
- **Don't fire the Tistory hook before/while the Naver CDP pass runs** — two drivers, one browser.
- **Don't auto-click Naver's final 발행 in v2.** v1 and v3 do it by explicit user decision
  (2026-07-26); v2 deliberately stops at the open panel.

---

## 11. Porting to another blog identity

Currently scoped to `kirin765.tistory.com` + `blog.naver.com/kwan765`.

- Override with `--tistory-url` / `--naver-url` (already parameterized) and
  `TISTORY_KAKAO_EMAIL`.
- Naver class hashes (`publish_btn__m9KHH`, `tag__zPnmI`, `tag_input__rvUB5`) are CDN-cached and
  rotate. On a selector miss, probe from DevTools —
  `document.querySelectorAll('button[class*="publish"]')` — and update the constant. Keep an
  attribute-substring fallback next to every hashed class.
- Both blogs share a 4-category scheme since 2026-07-27: 생활 정보 (the renamed 낙서장, and the
  default) · 쿠팡·스마트스토어 · 앱·개발 · 지난 글.

**Two doc/code discrepancies worth knowing** (found while writing this guide, not fixed):
v3's `SKILL.md` claims `--naver-category` falls back to `낙서장` — that is v1 behavior; v3 just
logs `not-found` and publishes with the panel's current category. And v3's `--naver-topic` flag
exists in the code but is absent from its flag list.

---

## 12. Related skills

- `cdp-anywhere` — general CDP work on arbitrary authenticated sites.
- `naver-blog-brunch-scrape` — the inverse (reading Naver Blog content).
- `youtube-upload` / `tiktok-upload` — these crosspost skills are **image + text only**; there is
  no video-embed path. Post a video separately, or drag the mp4 into the draft before 발행.
