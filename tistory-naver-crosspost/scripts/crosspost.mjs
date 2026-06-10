#!/usr/bin/env node
// tistory-naver-crosspost — drive existing Chrome CDP session to publish a blog post
// to Tistory (full auto draft) + Naver Blog (title + body + tags auto; body via insertText, not paste).
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
//   naver        naver only (title + body via insertText + tags via publish panel)
//   tags         re-fill Tistory tags on existing open tab
//   naver-tags   clear + re-fill Naver tags on existing publish panel
//
// All inputs can also come from env: SOURCE_URL, HERO_PNG, TITLE, TAGS, TISTORY_URL, NAVER_URL.

import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { writeFileSync, existsSync } from "node:fs";

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

const TAGS = TAGS_RAW.split(",").map(s => s.trim()).filter(Boolean);

const needsContent = mode === "both" || mode === "tistory" || mode === "naver";
const needsTags    = mode !== "naver"; // skip if naver-only-body (but our default both includes tags)
if (needsContent && !SOURCE_URL) die("missing --source URL");
if ((mode === "tistory" || mode === "both") && !HERO_PNG) die("missing --hero PNG path");
if ((mode === "tistory" || mode === "both" || mode === "naver") && !TITLE) die("missing --title");
function die(msg) { console.error("crosspost: " + msg); process.exit(2); }

// ---------- CDP connect ----------
async function connect() {
  let v;
  try {
    v = await (await fetch("http://localhost:9222/json/version")).json();
  } catch {
    die("Chrome CDP not reachable on http://localhost:9222 — start Chrome with --remote-debugging-port=9222");
  }
  return chromium.connectOverCDP(v.webSocketDebuggerUrl);
}

// ---------- clipboard helpers ----------
function setClipboardPng(absPath) {
  if (!existsSync(absPath)) die("hero PNG not found: " + absPath);
  execSync(`osascript -e ${JSON.stringify(`set the clipboard to (read (POSIX file ${JSON.stringify(absPath)}) as «class PNGf»)`)}`);
}

// ---------- HTML fetch + transforms ----------
async function fetchArticleHtml(url) {
  const res = await fetch(url);
  if (!res.ok) die(`source URL returned HTTP ${res.status}: ${url}`);
  const html = await res.text();
  const m = html.match(/<article[^>]*>([\s\S]*?)<\/article>/);
  if (!m) die("no <article> tag in source HTML — is the post live?");
  let body = m[1];
  body = body.replace(/<script[\s\S]*?<\/script>/g, "");
  body = body.replace(/<noscript[\s\S]*?<\/noscript>/g, "");
  body = body.replace(/<!--[\s\S]*?-->/g, "");
  body = body.replace(/\s(class|className|style|data-[a-z-]+)="[^"]*"/g, "");
  // absolutize internal relative hrefs
  const origin = new URL(url).origin;
  body = body.replace(/href="\/([^"]*)"/g, `href="${origin}/$1"`);
  body = body.replace(/href="\/"/g, `href="${origin}/"`);
  return body.trim();
}
function htmlToPlain(html) {
  let s = html;
  s = s.replace(/<h2>(.*?)<\/h2>/g, "\n\n■ $1\n\n");
  s = s.replace(/<\/p>/g, "\n\n");
  s = s.replace(/<li>(.*?)<\/li>/g, "• $1\n");
  s = s.replace(/<\/?ul>/g, "");
  s = s.replace(/<strong>(.*?)<\/strong>/g, "$1");
  s = s.replace(/<a\s+href="([^"]+)"[^>]*>(.*?)<\/a>/g, "$2 ($1)");
  s = s.replace(/<[^>]+>/g, "");
  s = s.replace(/\n{3,}/g, "\n\n").trim();
  return s;
}

// ---------- Tistory ----------
async function doTistory(ctx, htmlBody) {
  const page = await ctx.newPage();
  console.log("[tistory] opening newpost…");
  await page.goto(TISTORY_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3500);

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
  console.log("[naver] opening write…");
  await page.goto(NAVER_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(5000);

  // dismiss continue popup
  for (const frame of page.frames()) {
    try {
      const cancel = frame.locator("button:has-text('취소'), .se-popup-button-cancel").first();
      if (await cancel.isVisible({ timeout: 1000 })) {
        await cancel.click();
        console.log("[naver] dismissed continue popup");
        break;
      }
    } catch {}
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

  // body — inject via insertText, NOT clipboard paste.
  // Naver SmartEditor mis-decodes pasted UTF-8 as MacRoman → 외계어/mojibake.
  // The typing path (insertText) lands clean, same as the title above.
  if (titleOk) {
    await page.keyboard.press("Enter"); // title → first body paragraph
    await page.waitForTimeout(500);
  } else {
    // fallback: focus first body paragraph directly
    for (const frame of page.frames()) {
      try {
        const p = frame.locator(".se-text-paragraph").first();
        if (await p.isVisible({ timeout: 1500 })) { await p.click({ force: true }); break; }
      } catch {}
    }
    await page.waitForTimeout(400);
  }
  const lines = plainText.replace(/\r/g, "").split("\n");
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length) await page.keyboard.insertText(lines[i]);
    if (i < lines.length - 1) await page.keyboard.press("Enter");
  }
  console.log(`[naver] body injected via insertText (${lines.length} lines) — no clipboard, no mojibake`);
  console.log("[naver] hero PNG (drag manually to top of body): " + HERO_PNG);

  // tags via publish panel
  await doNaverTags(page);

  await page.screenshot({ path: "/tmp/naver-crosspost-ready.png" });
  console.log("[naver] screenshot: /tmp/naver-crosspost-ready.png");
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
    html = await fetchArticleHtml(SOURCE_URL);
    plain = htmlToPlain(html);
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
