#!/usr/bin/env node
// tistory-naver-crosspost — drive existing Chrome CDP session to publish a blog post
// to Tistory (full auto draft, incl. Kakao login click-through) + Naver Blog
// (title + hero image + body via keyboard.type + tags, all auto).
//
// Usage:
//   node crosspost.mjs [mode] \
//     --source  <url>            # live article URL whose <article> is the source of truth
//     --hero    <abs-png-path>   # hero PNG to paste at top
//     --title   "..."
//     --tags    "tag1,tag2,..."
//     [--tistory-url <newpost url>]   # default: https://kirin765.tistory.com/manage/newpost/
//     [--naver-url   <write url>]     # default: https://blog.naver.com/GoBlogWrite.naver
//
// modes:
//   both         (default)  tistory + naver
//   tistory      tistory only (title + body + hero image + tags + auto-save)
//   naver        naver only (title + hero image + body via insertText + tags via publish panel)
//   tags         re-fill Tistory tags on existing open tab
//   naver-tags   clear + re-fill Naver tags on existing publish panel
//
// All inputs can also come from env: SOURCE_URL, HERO_PNG, TITLE, TAGS, TISTORY_URL, NAVER_URL,
// TISTORY_KAKAO_EMAIL.

import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { writeFileSync, readFileSync, existsSync } from "node:fs";

// ---------- arg parsing ----------
const args = process.argv.slice(2);
const mode = args[0] && !args[0].startsWith("--") ? args[0] : "both";
function flag(name) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : undefined;
}
const SOURCE_URL  = flag("source")      || process.env.SOURCE_URL;
const HERO_PNG    = flag("hero")        || process.env.HERO_PNG;
const TITLE       = flag("title")       || process.env.TITLE;
const TAGS_RAW    = flag("tags")        || process.env.TAGS         || "";
const TISTORY_URL = flag("tistory-url") || process.env.TISTORY_URL || "https://kirin765.tistory.com/manage/newpost/";
const NAVER_URL   = flag("naver-url")   || process.env.NAVER_URL   || "https://blog.naver.com/GoBlogWrite.naver";
// Kakao account to pick on Tistory's "카카오계정으로 로그인" simple-login screen when the
// session is logged out. Override per-account via TISTORY_KAKAO_EMAIL.
const TISTORY_KAKAO_EMAIL = process.env.TISTORY_KAKAO_EMAIL || "kwan765@kakao.com";

const TAGS = TAGS_RAW.split(",").map(s => s.trim()).filter(Boolean);
// 2026-07-26 사용자 요청: 네이버는 발행 버튼까지 눌러 실제 발행까지 간다. 이전(패널만 열어두는)
// 동작이 필요하면 --no-publish-naver.
const NAVER_PUBLISH = !args.includes("--no-publish-naver");
// 2026-07-26 사용자 요청: 발행 시 글 주제에 맞는 카테고리를 --naver-category 로 넘기고,
// 블로그에 그 카테고리가 없으면 '낙서장'으로 발행한다.
const NAVER_CATEGORY = flag("naver-category") || process.env.NAVER_CATEGORY || "낙서장";

const needsContent = mode === "both" || mode === "tistory" || mode === "naver";
const needsTags    = mode !== "naver"; // skip if naver-only-body (but our default both includes tags)
if (needsContent && !SOURCE_URL) die("missing --source URL");
if ((mode === "tistory" || mode === "both") && !HERO_PNG) die("missing --hero PNG path");
if ((mode === "tistory" || mode === "both" || mode === "naver") && !TITLE) die("missing --title");
function die(msg) { console.error("crosspost: " + msg); process.exit(2); }

// ---------- CDP connect ----------
// CDP 전용 Chrome(chrome-cdp-profile, 9222) 이 안 떠 있을 때 backup 으로 자동 기동한다.
// 사용자의 평소 Chrome(Default 프로파일)은 별도 --user-data-dir 라 손대지 않는다.
async function launchCdpChromeMacos() {
  const os = await import("node:os");
  const { spawn } = await import("node:child_process");
  const path = await import("node:path");
  const chromeBin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  const profileDir = path.join(os.homedir(), "chrome-cdp-profile");
  try {
    const child = spawn(chromeBin, [`--remote-debugging-port=9222`, `--user-data-dir=${profileDir}`], {
      stdio: "ignore", detached: true,
    });
    child.unref();
  } catch (e) {
    return { ok: false, msg: `CDP Chrome launch failed: ${e.message}` };
  }
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try { await (await fetch("http://localhost:9222/json/version")).json(); return { ok: true, msg: "CDP Chrome auto-launched" }; }
    catch {}
  }
  return { ok: false, msg: "launched CDP Chrome but 9222 still not responding after 15s" };
}

async function connect() {
  let v;
  try {
    v = await (await fetch("http://localhost:9222/json/version")).json();
  } catch {
    if (process.platform === "darwin") {
      console.error("⏳ CDP 9222 not reachable — attempting to auto-launch CDP Chrome (chrome-cdp-profile)...");
      const { ok, msg } = await launchCdpChromeMacos();
      console.error((ok ? "✅ " : "❌ ") + msg);
      if (ok) {
        try {
          v = await (await fetch("http://localhost:9222/json/version")).json();
        } catch (e2) {
          die(`Chrome CDP still not reachable after auto-launch: ${e2.message}`);
        }
      } else {
        die("Auto-launch failed — start Chrome manually with --remote-debugging-port=9222 --user-data-dir=\"$HOME/chrome-cdp-profile\"");
      }
    } else {
      die("Chrome CDP not reachable on http://localhost:9222 — start Chrome with --remote-debugging-port=9222");
    }
  }
  await ensureCdpTab();
  return chromium.connectOverCDP(v.webSocketDebuggerUrl);
}

// connectOverCDP throws "Browser context management is not supported" if the CDP Chrome has
// ZERO page targets — e.g. all windows were closed but the process lingers, or a fresh
// --user-data-dir was launched with no window. /json/version still returns a healthy JSON in
// that state, so the version probe in connect() can't detect it. Verified live 2026-07-19:
// chrome-cdp-profile with 0 tabs → connectOverCDP failed; opening one blank tab fixed it.
// Ensure at least one page target exists before attaching.
async function ensureCdpTab() {
  try {
    const list = await (await fetch("http://localhost:9222/json/list")).json();
    if (Array.isArray(list) && list.some(t => t.type === "page")) return;
  } catch {}
  console.error("⏳ CDP browser has no page target — opening a blank tab so connectOverCDP can attach…");
  try { await fetch("http://localhost:9222/json/new?about:blank", { method: "PUT" }); } catch {}
  await new Promise(r => setTimeout(r, 800));
}

// ---------- clipboard helpers ----------
function setClipboardPng(absPath) {
  if (!existsSync(absPath)) die("hero PNG not found: " + absPath);
  execSync(`osascript -e ${JSON.stringify(`set the clipboard to (read (POSIX file ${JSON.stringify(absPath)}) as «class PNGf»)`)}`);
}

// ---------- HTML fetch + transforms ----------
async function fetchArticleHtml(src) {
  // Source can be a live http(s) URL (sajangbu.com / reviewboost) OR a local HTML file on
  // disk (e.g. an app's own promo-output/blog/*.html) — the latter needs no live deploy.
  let html;
  if (/^https?:\/\//.test(src)) {
    const res = await fetch(src);
    if (!res.ok) die(`source URL returned HTTP ${res.status}: ${src}`);
    html = await res.text();
  } else {
    const path = src.replace(/^file:\/\//, "");
    if (!existsSync(path)) die(`source file not found: ${path}`);
    html = readFileSync(path, "utf8");
  }
  const m = html.match(/<article[^>]*>([\s\S]*?)<\/article>/);
  if (!m) die("no <article> tag in source HTML — is the post live / does the file wrap its body in <article>?");
  let body = m[1];
  // Drop the article's own <h1> title — the title is supplied separately via --title, so an
  // in-article H1 would duplicate it in both the Tistory body and the Naver plain text.
  body = body.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, "");
  body = body.replace(/<script[\s\S]*?<\/script>/g, "");
  body = body.replace(/<noscript[\s\S]*?<\/noscript>/g, "");
  body = body.replace(/<!--[\s\S]*?-->/g, "");
  body = body.replace(/\s(class|className|style|data-[a-z-]+)="[^"]*"/g, "");
  // absolutize internal relative hrefs (http source only — local files have no origin)
  if (/^https?:\/\//.test(src)) {
    const origin = new URL(src).origin;
    body = body.replace(/href="\/([^"]*)"/g, `href="${origin}/$1"`);
    body = body.replace(/href="\/"/g, `href="${origin}/"`);
  }
  return body.trim();
}
// React's SSR HTML-escapes text nodes (including apostrophes → &#x27;), so any live page
// rendered by React/Next.js will have quotes/ampersands/etc as entities in the raw HTML.
// Tistory is unaffected (TinyMCE.setContent parses real HTML, entities decode naturally),
// but Naver's plain-text path just types out the literal "&#x27;문의&#x27;, ..." string if
// this isn't decoded — this was the actual cause of "이상하게 입력된다" reports, not a
// caret-jump bug. Must run AFTER tag-stripping so it also covers decoded href/text content.
function decodeEntities(s) {
  return s
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(parseInt(dec, 10)))
    .replace(/&nbsp;/g, " ")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}
// 2026-07-26 사용자 요청 — 긴 문단은 문장 경계에서 끊어 가독성을 높인다. 문장을 탐욕적으로
// 묶어 한 줄이 max자를 넘지 않게 나눈다.
function breakSentences(text, max) {
  const sentences = text.split(/(?<=[.!?])\s+/);
  const lines = [];
  let cur = "";
  for (const s of sentences) {
    if (cur && (cur + " " + s).length > max) { lines.push(cur); cur = s; }
    else cur = cur ? cur + " " + s : s;
  }
  if (cur) lines.push(cur);
  return lines;
}

function htmlToPlain(html) {
  let s = html;
  s = s.replace(/<h2[^>]*>(.*?)<\/h2>/g, "\n\n■ $1\n\n");
  // QnA(<dl><dt><b>Q…</b></dt><dd>…</dd></dl>) → Q는 자기 줄 + 볼드 마커(**…**, injectNaverBody
  // 가 Cmd+B 토글로 해석), A는 다음 줄, 쌍 사이 빈 줄 (2026-07-26 사용자 요청).
  s = s.replace(/<dt[^>]*>([\s\S]*?)<\/dt>/g, (_, q) => `\n\n**${q.replace(/<[^>]+>/g, "").trim()}**\n`);
  s = s.replace(/<dd[^>]*>([\s\S]*?)<\/dd>/g, (_, a) => `${a.trim()}\n\n`);
  s = s.replace(/<\/?dl[^>]*>/g, "\n");
  s = s.replace(/<\/p>/g, "\n\n");
  s = s.replace(/<li>(.*?)<\/li>/g, "• $1\n");
  s = s.replace(/<\/?ul>/g, "");
  s = s.replace(/<strong>(.*?)<\/strong>/g, "$1");
  s = s.replace(/<a\s+href="([^"]+)"[^>]*>(.*?)<\/a>/g, "$2 ($1)");
  s = s.replace(/<[^>]+>/g, "");
  s = decodeEntities(s);
  s = s.replace(/\n{3,}/g, "\n\n").trim();
  // Q 줄 바로 아래에 A가 붙도록 — 빈 줄은 QnA 쌍 '사이'에만 남긴다
  s = s.replace(/(^\*\*.+\*\*)\n\n+/gm, "$1\n");
  // 긴 본문 줄만 문장 단위로 끊는다 — 헤더(■)·불릿(•)·볼드 Q 줄은 그대로.
  s = s.split("\n").map(line => {
    const t = line.trim();
    if (!t || t.length <= 60 || /^(\*\*|•|■)/.test(t)) return line;
    return breakSentences(t, 60).join("\n");
  }).join("\n");
  return s;
}

// Tistory 본문용 변형 (2026-07-26 사용자 요청): QnA <dl>을 문단 쌍으로 풀고(볼드 Q 줄 / A 줄 /
// 쌍 사이 빈 문단), 인라인 태그 없는 긴 <p>는 문장 경계에서 <br>로 끊는다.
function formatTistoryHtml(html) {
  let s = html;
  s = s.replace(/<dt[^>]*>([\s\S]*?)<\/dt>/g, (_, q) => {
    const inner = /<b>|<strong>/.test(q) ? q.trim() : `<b>${q.trim()}</b>`;
    return `<p data-ke-size="size16">${inner}</p>`;
  });
  s = s.replace(/<dd[^>]*>([\s\S]*?)<\/dd>/g, `<p data-ke-size="size16">$1</p><p data-ke-size="size16">&nbsp;</p>`);
  s = s.replace(/<\/?dl[^>]*>/g, "");
  s = s.replace(/<p([^>]*)>([\s\S]*?)<\/p>/g, (m, attrs, inner) => {
    if (/<[^>]+>/.test(inner) || inner.length <= 90) return m;
    return `<p${attrs}>` + breakSentences(inner, 90).join("<br>") + `</p>`;
  });
  return s;
}

// ---------- Tistory Kakao simple-login (no-op if already logged in) ----------
// When the CDP profile is logged out, newpost redirects to /auth/login. This drives the
// Kakao click-through: "카카오계정으로 로그인" → pick the saved TISTORY_KAKAO_EMAIL profile →
// back to the editor. CLICK-THROUGH ONLY: it never types into any field. The instant an
// input[type=password] appears (dead Kakao session), it screenshots + throws so the routine
// reports "manual login needed" instead of attempting a credential login. Live-verified.
const ON_TISTORY_LOGIN = (u) => /\/auth\/login/.test(u) || /accounts\.kakao\.com/.test(u) || /kauth\.kakao\.com/.test(u);
const ON_TISTORY_EDITOR = (u) => /\/manage\/newpost/.test(u);

async function assertNoTistoryPassword(page, where) {
  const hasPw = await page.evaluate(() => !!document.querySelector("input[type=password]")).catch(() => false);
  if (hasPw) {
    await page.screenshot({ path: "/tmp/tistory-login-HARDSTOP.png" }).catch(() => {});
    throw new Error(`[tistory] Kakao needs manual password login (pw field at ${where}) — /tmp/tistory-login-HARDSTOP.png`);
  }
}

async function ensureTistoryLogin(page) {
  if (ON_TISTORY_EDITOR(page.url()) && await page.$("#post-title-inp")) return; // already logged in
  const kakaoBtn = page.locator("a.link_kakao_id, a.btn_login.link_kakao_id").first();
  const hasBtn = await kakaoBtn.isVisible({ timeout: 1500 }).catch(() => false);
  if (!ON_TISTORY_LOGIN(page.url()) && !hasBtn) return; // not a login screen — let caller proceed

  console.log("[tistory] logged out — driving Kakao login click-through");
  await assertNoTistoryPassword(page, "tistory-auth-page");
  if (hasBtn) {
    await Promise.all([
      page.waitForURL(/accounts\.kakao\.com|kauth\.kakao\.com|\/manage\/newpost/, { timeout: 12000 }).catch(() => {}),
      kakaoBtn.click({ timeout: 5000 }).catch(() => {}),
    ]);
    await page.waitForTimeout(1500);
  }

  const deadline = Date.now() + 40000;
  while (Date.now() < deadline) {
    if (ON_TISTORY_EDITOR(page.url()) && await page.$("#post-title-inp")) { console.log("[tistory] Kakao login OK — editor ready"); return; }
    await assertNoTistoryPassword(page, "kakao-loop");

    if (/accounts\.kakao\.com/.test(page.url())) {
      // Real saved accounts have a .tit_profile email; the "새 계정으로 로그인" row shares
      // class wrap_profile but has no .tit_profile — exclude it. Prefer the expected email.
      const saved = page.locator("a.wrap_profile:has(.tit_profile)");
      const nSaved = await saved.count().catch(() => 0);
      const expected = saved.filter({ hasText: TISTORY_KAKAO_EMAIL });
      if ((await expected.count().catch(() => 0)) >= 1) {
        console.log(`[tistory] selecting Kakao account ${TISTORY_KAKAO_EMAIL}`);
        await expected.first().click({ timeout: 4000 }).catch(() => {});
        await page.waitForTimeout(1800); continue;
      }
      if (nSaved > 1) {
        await page.screenshot({ path: "/tmp/tistory-login-MULTIACCOUNT.png" }).catch(() => {});
        throw new Error(`[tistory] ${nSaved} saved Kakao accounts, none matching ${TISTORY_KAKAO_EMAIL} — refusing to guess. /tmp/tistory-login-MULTIACCOUNT.png`);
      }
      if (nSaved === 1) {
        console.log("[tistory] selecting single saved Kakao account");
        await saved.first().click({ timeout: 4000 }).catch(() => {});
        await page.waitForTimeout(1800); continue;
      }
      // consent/continue screen (no saved-profile card)
      const cont = page.locator("button:has-text('계속하기'), button:has-text('동의하고 계속하기'), button.btn_agree, button[name=user_oauth_approval], button:has-text('전체 동의')").first();
      if (await cont.isVisible({ timeout: 1500 }).catch(() => false)) {
        await cont.click({ timeout: 4000 }).catch(() => {});
        await page.waitForTimeout(1800); continue;
      }
    }
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: "/tmp/tistory-login-TIMEOUT.png" }).catch(() => {});
  throw new Error(`[tistory] login click-through did not reach editor in 40s (url=${page.url()}) — /tmp/tistory-login-TIMEOUT.png`);
}

// ---------- Tistory ----------
async function doTistory(ctx, htmlBody) {
  const page = await ctx.newPage();
  // Tistory fires a native confirm ("…저장된 글이 있습니다. 이어서 작성하시겠습니까?") when a
  // draft exists. Without a handler Playwright auto-dismisses and the race throws an
  // unhandled ProtocolError that kills the run — dismiss explicitly and swallow the race.
  page.on("dialog", d => d.dismiss().catch(() => {}));
  console.log("[tistory] opening newpost…");
  await page.goto(TISTORY_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3500);

  // if the session is logged out, click through Kakao login (never types credentials)
  await ensureTistoryLogin(page);

  // dismiss possible continue-from-draft modal
  try {
    const cancel = page.locator("button:has-text('취소'), button:has-text('새로 작성')").first();
    if (await cancel.isVisible({ timeout: 2000 })) await cancel.click();
  } catch {}
  await page.waitForTimeout(1000);

  // title
  try {
    const title = await page.waitForSelector("#post-title-inp", { timeout: 8000 });
    await title.fill(TITLE);
    console.log("[tistory] title filled");
  } catch (e) {
    console.log("[tistory] title selector miss:", e.message);
  }

  // body via TinyMCE
  await page.waitForSelector("#editor-tistory_ifr", { timeout: 15000 });
  await page.waitForTimeout(1500);
  const setOk = await page.evaluate(html => {
    const tm = window.tinymce;
    if (!tm || !tm.activeEditor) return "no-tinymce";
    tm.activeEditor.setContent(html);
    return "ok";
  }, htmlBody);
  console.log("[tistory] body setContent:", setOk);
  await page.waitForTimeout(1500);

  // hero image at top
  const iframeHandle = await page.$("#editor-tistory_ifr");
  const frame = await iframeHandle.contentFrame();
  await frame.evaluate(() => {
    const b = document.body; b.focus();
    const r = document.createRange(); r.setStart(b, 0); r.setEnd(b, 0);
    const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
  });
  setClipboardPng(HERO_PNG);
  await page.waitForTimeout(400);
  await page.keyboard.press("Meta+V");
  console.log("[tistory] hero image pasted, waiting for upload…");
  await page.waitForTimeout(8000);

  await doTistoryTags(page);

  // 임시저장을 한 번 눌러 자동저장 주기를 기다리지 않고 바로 저장한다 (2026-07-26 사용자 요청)
  try {
    const save = page.locator("button:has-text('임시저장')").first();
    await save.click({ timeout: 4000 });
    await page.waitForTimeout(2500);
    console.log("[tistory] 임시저장 clicked");
  } catch (e) { console.log("[tistory] 임시저장 button not found:", e.message); }

  await page.screenshot({ path: "/tmp/tistory-crosspost-done.png" });
  console.log("[tistory] screenshot: /tmp/tistory-crosspost-done.png");
  console.log("[tistory] DRAFT — user clicks [완료] → [발행]");
}

async function doTistoryTags(page) {
  if (!TAGS.length) { console.log("[tistory-tags] no tags supplied, skipping"); return; }
  try {
    const tag = await page.waitForSelector("#tagText", { timeout: 5000 });
    for (const t of TAGS) {
      await tag.click();
      await page.keyboard.type(t, { delay: 8 });
      await page.keyboard.press("Enter");
      await page.waitForTimeout(250);
    }
    console.log(`[tistory-tags] entered ${TAGS.length} tags`);
  } catch (e) {
    console.log("[tistory-tags] failed:", e.message);
  }
}

// ---------- Naver ----------
async function doNaver(ctx, plainText) {
  const page = await ctx.newPage();
  page.on("dialog", d => d.dismiss().catch(() => {}));
  console.log("[naver] opening write…");
  await page.goto(NAVER_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(5000);

  // dismiss "작성 중인 글이 있습니다" recovery popup → discard (취소) so we inject clean.
  // The recovery popup renders inside the PostWriteForm iframe a beat after load, so poll a few times.
  for (let attempt = 0; attempt < 6; attempt++) {
    let done = false;
    for (const frame of page.frames()) {
      try {
        const cancel = frame.locator("button.se-popup-button-cancel").first();
        if (await cancel.isVisible({ timeout: 500 })) {
          await cancel.click();
          console.log("[naver] dismissed continue popup");
          done = true;
          break;
        }
      } catch {}
    }
    if (done) break;
    await page.waitForTimeout(700);
  }
  await page.waitForTimeout(1500);

  // title
  let titleOk = false;
  for (const frame of page.frames()) {
    try {
      const t = frame.locator(".se-title-text").first();
      if (await t.isVisible({ timeout: 1500 })) {
        await t.click();
        await page.keyboard.type(TITLE, { delay: 6 });
        titleOk = true;
        console.log("[naver] title typed");
        break;
      }
    } catch {}
  }
  if (!titleOk) console.log("[naver] title field not found — type manually");

  // hero image at TOP — insert BEFORE body text so it becomes the first body component.
  // Live-verified order: [title, IMAGE, body-text]. The 사진 button fires a native file
  // picker (no input[type=file] at rest); body text then goes into the empty paragraph
  // Naver places AFTER the image (see injectNaverBody → .se-text-paragraph.last()).
  if (HERO_PNG) await insertNaverHeroImage(page, HERO_PNG);

  // body via keyboard.type, line-by-line (typing path) — NEVER clipboard/paste: Naver
  // SmartEditor mis-decodes pasted UTF-8 as MacRoman → 외계어/mojibake. Real key events also
  // avoid the per-line bulk-insertText caret-jump bug on punctuation-heavy lines (see below).
  await injectNaverBody(page, plainText);

  // tags via publish panel
  await doNaverTags(page);

  await page.screenshot({ path: "/tmp/naver-crosspost-ready.png" });
  console.log("[naver] screenshot: /tmp/naver-crosspost-ready.png");

  if (NAVER_PUBLISH) await doNaverPublish(page);
  else console.log("[naver] --no-publish-naver — publish panel left open for manual 발행");
}

// 발행 패널의 카테고리 셀렉트박스에서 NAVER_CATEGORY 를 고른다. 그 이름이 목록에 없으면
// '낙서장'으로 fallback (2026-07-26 사용자 요청). 클래스가 해시라 텍스트 기반으로 찾는다.
async function selectNaverCategory(editor, page) {
  try {
    const opened = await editor.evaluate(() => {
      const btn = document.querySelector("button[class*='selectbox_button'], button[class*='selectbox']")
        || [...document.querySelectorAll("button")].find(b => /카테고리/.test(b.getAttribute("aria-label") || ""));
      if (!btn) return false;
      btn.click();
      return true;
    });
    if (!opened) { console.log("[naver-cat] category dropdown not found — panel default 유지"); return; }
    await page.waitForTimeout(800);
    // 목록 항목은 label/li 로만 찾는다 — 셀렉트박스 버튼 자신의 텍스트(span)에 오매칭 방지
    const picked = await editor.evaluate((want) => {
      const items = [...document.querySelectorAll("label, li")]
        .filter(e => e.offsetParent !== null && !e.closest("button"));
      const norm = e => (e.textContent || "").trim();
      let hit = items.find(e => norm(e) === want);
      if (!hit) hit = items.find(e => norm(e) === "낙서장");
      if (!hit) return null;
      hit.click();
      return norm(hit);
    }, NAVER_CATEGORY);
    await page.waitForTimeout(600);
    console.log(picked
      ? `[naver-cat] category selected: ${picked}` + (picked !== NAVER_CATEGORY ? ` (요청 '${NAVER_CATEGORY}' 없음 → fallback)` : "")
      : `[naver-cat] '${NAVER_CATEGORY}'도 '낙서장'도 목록에 없음 — panel default 유지`);
  } catch (e) { console.log("[naver-cat] skipped:", e.message); }
}

// 발행 패널 안의 최종 [발행] 버튼을 눌러 실제 발행까지 마친다 (2026-07-26 사용자 요청, e2e).
// 카테고리·공개범위는 네이버가 기억하는 패널 기본값 그대로 나간다. 발행 성공 판정: URL이
// 글번호가 붙은 게시글 주소로 바뀌는 것.
async function doNaverPublish(page) {
  const editor = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!editor) { console.log("[naver-publish] editor frame missing — NOT published"); return false; }

  // doNaverTags 가 이미 패널을 열어뒀지만, 재실행 등으로 닫혀 있으면 다시 연다
  const panelOpen = await editor.evaluate(() => /태그 편집/.test(document.body.innerText || "")).catch(() => false);
  if (!panelOpen) {
    try {
      await editor.locator("button.publish_btn__m9KHH, button[class*='publish']").first().click({ timeout: 3000 });
      await page.waitForTimeout(1500);
    } catch (e) { console.log("[naver-publish] could not open publish panel:", e.message); return false; }
  }

  // 카테고리 선택: 요청 이름 → 없으면 '낙서장' (2026-07-26 사용자 요청)
  await selectNaverCategory(editor, page);

  // 최종 확인 버튼: data-testid 우선, 해시 클래스 fallback, 마지막으로 패널 내 텍스트가
  // 정확히 "발행"인 버튼(패널을 연 버튼과 텍스트가 같아서 마지막 매치를 쓴다)
  let clicked = false;
  const btn = editor.locator("[data-testid='seOnePublishBtn'], button[class*='confirm_btn']").first();
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click({ timeout: 4000 }).catch(() => {});
    clicked = true;
  } else {
    clicked = await editor.evaluate(() => {
      const cands = [...document.querySelectorAll("button")].filter(b => (b.textContent || "").trim() === "발행");
      if (!cands.length) return false;
      cands[cands.length - 1].click();
      return true;
    }).catch(() => false);
  }
  if (!clicked) {
    await page.screenshot({ path: "/tmp/naver-publish-FAIL.png" }).catch(() => {});
    console.log("[naver-publish] 발행 button not found — /tmp/naver-publish-FAIL.png");
    return false;
  }
  console.log("[naver-publish] 발행 clicked — waiting for post URL…");

  try {
    await page.waitForURL(u => /blog\.naver\.com/.test(u.href) && /\/\d{9,}/.test(u.pathname + u.search), { timeout: 25000 });
  } catch {}
  await page.waitForTimeout(2000);
  const url = page.url();
  const published = /\/\d{9,}|logNo=\d+/.test(url);
  await page.screenshot({ path: "/tmp/naver-crosspost-published.png" }).catch(() => {});
  console.log(published
    ? `[naver-publish] ✅ PUBLISHED: ${url}`
    : `[naver-publish] ⚠ URL did not change to a post URL (${url}) — verify /tmp/naver-crosspost-published.png`);
  return published;
}

// Insert the hero PNG as the FIRST body component (above the text). Live-verified against
// blog.naver.com PostWriteForm: the 사진 button (button.se-image-toolbar-button) opens a native
// OS file picker — there is NO input[type=file] at rest — intercepted via filechooser. The
// committed image is a .se-component.se-image inside .se-canvas .se-components-wrap (NOT the
// nonexistent .se-main-container; the 라이브러리 side-panel thumbnail is not a .se-component).
// No-op-safe: logs + returns if the button/frame is missing, never throws.
async function insertNaverHeroImage(page, heroPng) {
  const ef = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!ef) { console.log("[naver-img] editor frame missing — skip image"); return false; }

  const countImages = () => ef.evaluate(() => {
    const w = document.querySelector(".se-canvas .se-components-wrap") || document.querySelector(".se-components-wrap");
    return w ? w.querySelectorAll(".se-component.se-image").length : 0;
  });
  // idempotency: don't re-upload if the editor already holds an image (re-run case)
  if ((await countImages()) > 0) { console.log("[naver-img] image already present — skip"); return true; }

  const photoBtn = ef.locator("button.se-image-toolbar-button").first();
  if (!(await photoBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
    console.log("[naver-img] 사진 button not found — skip image (drag manually): " + heroPng);
    return false;
  }
  // arm filechooser BEFORE click; noWaitAfter so the click doesn't block on the modal picker
  const chooserP = page.waitForEvent("filechooser", { timeout: 8000 }).catch(() => null);
  try { await photoBtn.click({ noWaitAfter: true, timeout: 5000 }); }
  catch (e) { console.log("[naver-img] 사진 click failed — skip image:", e.message); return false; }
  const chooser = await chooserP;
  if (!chooser) { console.log("[naver-img] no file picker appeared — skip image (drag manually): " + heroPng); return false; }
  try { await chooser.setFiles(heroPng); }
  catch (e) { console.log("[naver-img] setFiles failed — skip image:", e.message); return false; }

  let ok = false;
  for (let i = 0; i < 25; i++) {
    await page.waitForTimeout(800);
    if ((await countImages()) > 0) { ok = true; break; }
  }
  console.log("[naver-img] hero image inserted at top:", ok);
  await page.waitForTimeout(800);
  return ok;
}

async function injectNaverBody(page, plainText) {
  const lines = plainText.replace(/\n{3,}/g, "\n\n").trim().split("\n");
  let clicked = false;
  for (const frame of page.frames()) {
    try {
      // Target the LAST text-component paragraph (the empty body paragraph Naver places
      // after the hero image), NOT .se-text-paragraph.first() — which can be the title /
      // an image-caption paragraph. .se-component.se-text scopes to body text only.
      const body = frame.locator(".se-component.se-text .se-text-paragraph").last();
      if (await body.isVisible({ timeout: 1500 })) { await body.click(); clicked = true; break; }
    } catch {}
  }
  if (!clicked) { console.log("[naver] body paragraph not found — body NOT injected"); return; }
  await page.waitForTimeout(400);
  // Per-line bulk insertText (single call for the whole line) has the same caret-jump bug
  // documented for the title: a line containing paired punctuation (quotes '…', em-dash —,
  // "label:" colon segments) can land the caret mid-string and scramble character order,
  // because SmartEditor's autoformat (quote pairing / auto-list-on-colon) mutates the DOM
  // mid-insert while insertText is still writing the rest of the chunk. keyboard.type()
  // fires real per-character key events instead, so SmartEditor's mutation happens between
  // characters rather than mid-chunk — same fix already proven for the title field.
  for (let i = 0; i < lines.length; i++) {
    // **…** 로 감싸인 줄(QnA의 Q 줄)은 Cmd+B 토글로 볼드 타이핑 (2026-07-26 사용자 요청)
    const boldM = lines[i].match(/^\*\*(.+)\*\*$/);
    if (boldM) {
      await page.keyboard.press("Meta+b");
      await page.keyboard.type(boldM[1], { delay: 4 });
      await page.keyboard.press("Meta+b");
    } else if (lines[i].length) {
      await page.keyboard.type(lines[i], { delay: 4 });
    }
    if (i < lines.length - 1) await page.keyboard.press("Enter");
    await page.waitForTimeout(25);
  }
  console.log(`[naver] body typed via keyboard.type (${lines.length} lines)`);

  // Strip inherited 취소선: if the editor's active format applied line-through to the
  // typed text (non-fresh editor), select all body and toggle the strikethrough button off.
  try {
    const ef = page.frames().find(f => f.url().includes("PostWriteForm"));
    const struck = await ef.evaluate(() => {
      const nodes = document.querySelectorAll(".se-text-paragraph, .se-text-paragraph *");
      for (const n of nodes) {
        if ((getComputedStyle(n).textDecorationLine || "").includes("line-through")) return true;
      }
      return false;
    });
    if (struck) {
      await page.keyboard.press("Meta+a");
      await page.waitForTimeout(250);
      await ef.evaluate(() => {
        const b = [...document.querySelectorAll("button")].find(x =>
          /취소선|strikethrough/i.test((x.getAttribute("aria-label") || "") + " " + x.className + " " + (x.title || "")));
        if (b) b.click();
      });
      await page.waitForTimeout(300);
      await page.keyboard.press("End");
      console.log("[naver] removed inherited 취소선");
    }
  } catch (e) { console.log("[naver] strike-check skipped:", e.message); }
}

async function doNaverTags(page) {
  if (!TAGS.length) { console.log("[naver-tags] no tags supplied, skipping"); return; }
  const editor = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!editor) { console.log("[naver-tags] editor frame missing"); return; }

  // open publish panel if not already
  const panelOpen = await editor.evaluate(() => /태그 편집/.test(document.body.innerText || ""));
  if (!panelOpen) {
    try {
      const btn = editor.locator("button.publish_btn__m9KHH, button[class*='publish']").first();
      await btn.click({ timeout: 3000 });
      await page.waitForTimeout(1500);
      console.log("[naver-tags] publish panel opened");
    } catch (e) {
      console.log("[naver-tags] could not open panel:", e.message);
      return;
    }
  }

  try {
    const tagInput = editor.locator("#tag-input").first();
    await tagInput.click({ timeout: 5000 });

    // clear existing chips (handles re-run case)
    const chipCount = await editor.evaluate(() => document.querySelectorAll(".tag__zPnmI").length);
    if (chipCount > 0) {
      console.log(`[naver-tags] clearing ${chipCount} existing chips`);
      for (let i = 0; i < chipCount + 1; i++) {
        await page.keyboard.press("Backspace");
        await page.waitForTimeout(120);
      }
    }

    // Naver commits on space — strip
    await tagInput.click();
    for (const raw of TAGS) {
      const t = raw.replace(/\s+/g, "");
      await page.keyboard.type(t, { delay: 8 });
      await page.keyboard.press("Enter");
      await page.waitForTimeout(250);
    }
    const finalCount = await editor.evaluate(() => document.querySelectorAll(".tag__zPnmI").length);
    console.log(`[naver-tags] entered ${TAGS.length} tags, chips now: ${finalCount}`);
  } catch (e) {
    console.log("[naver-tags] failed:", e.message);
  }
}

// ---------- main ----------
(async () => {
  let html = "", plain = "";
  if (needsContent) {
    console.log("fetching live article HTML…");
    const raw = await fetchArticleHtml(SOURCE_URL);
    html = formatTistoryHtml(raw);
    plain = htmlToPlain(raw);
    writeFileSync("/tmp/crosspost-body.html", html);
    writeFileSync("/tmp/crosspost-body.txt", plain);
    console.log(`html ${html.length}B → /tmp/crosspost-body.html`);
    console.log(`plain ${plain.length}B → /tmp/crosspost-body.txt\n`);
  }

  const browser = await connect();
  const ctx = browser.contexts()[0];
  try {
    if (mode === "tistory" || mode === "both") await doTistory(ctx, html);
    if (mode === "naver"   || mode === "both") await doNaver(ctx, plain);
    if (mode === "tags") {
      const t = ctx.pages().find(p => p.url().includes("tistory.com/manage/newpost"));
      if (!t) die("no open Tistory newpost tab — run `tistory` mode first");
      await t.bringToFront(); await t.waitForTimeout(500);
      await doTistoryTags(t);
    }
    if (mode === "naver-tags") {
      const n = ctx.pages().find(p => p.url().includes("blog.naver.com") && p.url().includes("Write"));
      if (!n) die("no open Naver write tab — run `naver` mode first");
      await n.bringToFront(); await n.waitForTimeout(500);
      await doNaverTags(n);
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error("FATAL:", e); process.exit(1); });
