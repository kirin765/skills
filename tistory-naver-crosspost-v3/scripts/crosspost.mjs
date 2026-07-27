#!/usr/bin/env node
// tistory-naver-crosspost v3 — Naver Blog full publish (공개) via Chrome CDP +
// Tistory via queue JSON handed to the standalone tistory-scheduler (NO CDP work here).
//
// Naver: title + hero image + body via keyboard.type + tags + 공개 발행 클릭까지 완주.
// Tistory: writes a job JSON into ~/.tistory-queue/pending/ per
//   ~/.gemini/config/skills/tistory-post/references/agent-queue-guide.md
// then fires `tistory-scheduler.mjs hook` (no path arg — the JSON is already in
// pending/; passing the path would make hook COPY it there a second time → double publish).
//
// Usage:
//   node crosspost.mjs [mode] \
//     --source  <url-or-abs-html-path>  # live URL or local file whose <article> is the body
//     --hero    <abs-png-path>          # hero PNG (Tistory queue REQUIRES a real .png)
//     --title   "..."
//     --tags    "tag1,tag2,..."
//     [--slug   <slug>]                 # queue filename slug (default: derived from source)
//     [--scheduled-at "2026-07-27T09:00:00+09:00"]  # Tistory reserved publish (omit = ASAP)
//     [--no-hook]                       # queue only, don't trigger the scheduler
//     [--tistory-url <newpost url>]     # only written into the JSON when explicitly given
//     [--naver-url   <write url>]       # default: https://blog.naver.com/GoBlogWrite.naver
//
// modes:
//   both           (default)  naver full publish now, then tistory queue + hook
//   naver          naver only (title + hero + body + tags + 공개 발행)
//   tistory-queue  tistory queue JSON + hook only (alias: tistory)
//   queue          enqueue BOTH (naver-queue + tistory-queue), NO hook, no browser —
//                  naver는 다음 09:00 launchd 잡이 발행, tistory는 초안 대기열에만 등록
//   naver-tags     clear + re-fill Naver tags on existing publish panel (no publish)
//
// Env equivalents: SOURCE_URL, HERO_PNG, TITLE, TAGS, NAVER_URL, TISTORY_URL, SCHEDULED_AT.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { writeFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const SCHEDULER = path.join(os.homedir(), ".gemini/config/skills/tistory-post/scripts/tistory-scheduler.mjs");
const PENDING_DIR = path.join(os.homedir(), ".tistory-queue/pending");
// Naver 전용 대기열 — 매일 09:00 daily-crosspost.mjs(launchd)가 소비한다. 티스토리 큐와
// 절대 공유하지 않는다: 공유하면 티스토리 hook이 JSON을 done으로 옮겨 Naver 발행이 누락된다.
const NAVER_PENDING_DIR = path.join(os.homedir(), ".naver-queue/pending");

// ---------- arg parsing ----------
const args = process.argv.slice(2);
const mode = args[0] && !args[0].startsWith("--") ? args[0] : "both";
function flag(name) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : undefined;
}
const SOURCE_URL   = flag("source")       || process.env.SOURCE_URL;
const HERO_PNG     = flag("hero")         || process.env.HERO_PNG;
const TITLE        = flag("title")        || process.env.TITLE;
const TAGS_RAW     = flag("tags")         || process.env.TAGS         || "";
const SLUG         = flag("slug");
// Tistory category name — scheduler maps it to a category id after publish (default: 생활 정보).
const CATEGORY     = flag("category")     || process.env.TISTORY_CATEGORY;
const SCHEDULED_AT = flag("scheduled-at") || process.env.SCHEDULED_AT;
const NO_HOOK      = args.includes("--no-hook");
const NAVER_URL    = flag("naver-url")    || process.env.NAVER_URL    || "https://blog.naver.com/GoBlogWrite.naver";
// Only forwarded into the queue JSON when explicitly given — the scheduler has its own default.
const TISTORY_URL_EXPLICIT = flag("tistory-url") || process.env.TISTORY_URL;

const TAGS = TAGS_RAW.split(",").map(s => s.trim()).filter(Boolean);

const wantsNaver   = mode === "both" || mode === "naver";
const wantsTistory = mode === "both" || mode === "tistory" || mode === "tistory-queue" || mode === "queue";
if ((wantsNaver || wantsTistory) && !SOURCE_URL) die("missing --source URL/path");
if ((wantsNaver || wantsTistory) && !TITLE) die("missing --title");
if (wantsTistory && !HERO_PNG) die("missing --hero PNG path (Tistory queue requires it)");
function die(msg) { console.error("crosspost: " + msg); process.exit(2); }

// ---------- queue writers (no CDP) ----------
// Spec: agent-queue-guide.md — absolute paths only, real .png hero,
// post-YYYYMMDD-slug.json into the target pending dir.
function writeQueueJson(pendingDir, label) {
  let src = SOURCE_URL;
  if (!/^https?:\/\//.test(src)) {
    src = path.resolve(src.replace(/^file:\/\//, ""));
    if (!existsSync(src)) die("source file not found: " + src);
    if (!/<article[\s>]/.test(readFileSync(src, "utf8"))) die("source file has no <article> tag: " + src);
  }
  const hero = path.resolve(HERO_PNG);
  if (!existsSync(hero)) die("hero PNG not found: " + hero);
  if (!hero.toLowerCase().endsWith(".png")) die("hero must be a .png (clipboard «class PNGf» path): " + hero);
  if (/\.$/.test(TITLE.trim())) console.log(`[${label}] warning: title ends with '.' — guide says drop the trailing period`);

  const job = { title: TITLE, source: src, hero };
  if (CATEGORY) job.category = CATEGORY;
  if (TAGS.length) job.tags = TAGS;
  if (SCHEDULED_AT) job.scheduledAt = SCHEDULED_AT;
  if (TISTORY_URL_EXPLICIT) job.tistoryUrl = TISTORY_URL_EXPLICIT;

  const slug = (SLUG || deriveSlug(src)).replace(/[^a-zA-Z0-9가-힣_-]+/g, "-").replace(/^-+|-+$/g, "") || String(Date.now());
  const ymd = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  mkdirSync(pendingDir, { recursive: true });
  const jsonPath = path.join(pendingDir, `post-${ymd}-${slug}.json`);
  writeFileSync(jsonPath, JSON.stringify(job, null, 2) + "\n");
  JSON.parse(readFileSync(jsonPath, "utf8")); // self-check: valid JSON on disk
  console.log(`[${label}] queued:`, jsonPath);
  return jsonPath;
}

function queueNaver() {
  writeQueueJson(NAVER_PENDING_DIR, "naver-queue");
  console.log("[naver-queue] 매일 09:00 com.brain.daily-crosspost 잡이 공개 발행합니다");
}

function queueTistory() {
  writeQueueJson(PENDING_DIR, "tistory-queue");

  if (NO_HOOK || mode === "queue") { console.log("[tistory-queue] no hook — scheduler NOT triggered (초안 대기열에만 등록)"); return; }
  if (!existsSync(SCHEDULER)) die("tistory-scheduler.mjs not found at " + SCHEDULER);
  // No path arg on purpose: hook <path> COPIES the file into pending/ (addJob) — the job is
  // already there, so a path arg would enqueue it twice. Bare hook only triggers the run.
  const out = execFileSync(process.execPath, [SCHEDULER, "hook"], { encoding: "utf8" });
  process.stdout.write(out);
  console.log("[tistory-queue] hook fired — background scheduler publishes without the agent; logs: ~/.tistory-queue/logs/");
}

function deriveSlug(src) {
  const base = /^https?:\/\//.test(src)
    ? (new URL(src).pathname.split("/").filter(Boolean).pop() || "")
    : path.basename(src, path.extname(src));
  return base;
}

// ---------- CDP connect ----------
// CDP 전용 Chrome(chrome-cdp-profile, 9222) 이 안 떠 있을 때 backup 으로 자동 기동한다.
// 사용자의 평소 Chrome(Default 프로파일)은 별도 --user-data-dir 라 손대지 않는다.
async function launchCdpChromeMacos() {
  const { spawn } = await import("node:child_process");
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
// ZERO page targets — /json/version still looks healthy in that state (verified 2026-07-19).
async function ensureCdpTab() {
  try {
    const list = await (await fetch("http://localhost:9222/json/list")).json();
    if (Array.isArray(list) && list.some(t => t.type === "page")) return;
  } catch {}
  console.error("⏳ CDP browser has no page target — opening a blank tab so connectOverCDP can attach…");
  try { await fetch("http://localhost:9222/json/new?about:blank", { method: "PUT" }); } catch {}
  await new Promise(r => setTimeout(r, 800));
}

// ---------- HTML fetch + transforms ----------
async function fetchArticleHtml(src) {
  let html;
  if (/^https?:\/\//.test(src)) {
    const res = await fetch(src);
    if (!res.ok) die(`source URL returned HTTP ${res.status}: ${src}`);
    html = await res.text();
  } else {
    const p = src.replace(/^file:\/\//, "");
    if (!existsSync(p)) die(`source file not found: ${p}`);
    html = readFileSync(p, "utf8");
  }
  const m = html.match(/<article[^>]*>([\s\S]*?)<\/article>/);
  if (!m) die("no <article> tag in source HTML — is the post live / does the file wrap its body in <article>?");
  let body = m[1];
  // Drop the article's own <h1> — the title comes from --title, an in-article H1 would duplicate it.
  body = body.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, "");
  body = body.replace(/<script[\s\S]*?<\/script>/g, "");
  body = body.replace(/<noscript[\s\S]*?<\/noscript>/g, "");
  body = body.replace(/<!--[\s\S]*?-->/g, "");
  body = body.replace(/\s(class|className|style|data-[a-z-]+)="[^"]*"/g, "");
  if (/^https?:\/\//.test(src)) {
    const origin = new URL(src).origin;
    body = body.replace(/href="\/([^"]*)"/g, `href="${origin}/$1"`);
    body = body.replace(/href="\/"/g, `href="${origin}/"`);
  }
  return body.trim();
}
// React SSR escapes text nodes (apostrophes → &#x27; etc.) — must decode AFTER tag-stripping
// or the literal entity string gets typed into Naver verbatim (the historical 외계어 bug #2).
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
function htmlToPlain(html) {
  let s = html;
  s = s.replace(/<h2>(.*?)<\/h2>/g, "\n\n■ $1\n\n");
  s = s.replace(/<\/p>/g, "\n\n");
  s = s.replace(/<li>(.*?)<\/li>/g, "• $1\n");
  s = s.replace(/<\/?ul>/g, "");
  s = s.replace(/<strong>(.*?)<\/strong>/g, "$1");
  s = s.replace(/<a\s+href="([^"]+)"[^>]*>(.*?)<\/a>/g, "$2 ($1)");
  s = s.replace(/<[^>]+>/g, "");
  s = decodeEntities(s);
  s = s.replace(/\n{3,}/g, "\n\n").trim();
  return s;
}

// ---------- Naver ----------
async function doNaver(ctx, plainText) {
  const page = await ctx.newPage();
  console.log("[naver] opening write…");
  await page.goto(NAVER_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(5000);

  // dismiss "작성 중인 글이 있습니다" recovery popup → discard (취소) so we inject clean.
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

  // title — keyboard.type (real key events), never bulk insertText (em-dash caret-jump bug)
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

  // hero image at TOP — BEFORE body text so the order lands [title, IMAGE, body-text]
  if (HERO_PNG) await insertNaverHeroImage(page, path.resolve(HERO_PNG));

  // body via keyboard.type line-by-line — NEVER clipboard paste (MacRoman mojibake),
  // never bulk insertText (SmartEditor autoformat scrambles punctuation-heavy lines)
  await injectNaverBody(page, plainText);

  await doNaverTags(page);

  const url = await publishNaver(page);
  await page.screenshot({ path: "/tmp/naver-crosspost-published.png" }).catch(() => {});
  console.log("[naver] screenshot: /tmp/naver-crosspost-published.png");
  return url;
}

// Insert the hero PNG as the FIRST body component. The 사진 button opens a NATIVE file
// picker (no resting input[type=file]) — arm waitForEvent('filechooser') BEFORE clicking.
// Idempotent: skips if an image already exists (re-run case). Never throws.
async function insertNaverHeroImage(page, heroPng) {
  const ef = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!ef) { console.log("[naver-img] editor frame missing — skip image"); return false; }

  const countImages = () => ef.evaluate(() => {
    const w = document.querySelector(".se-canvas .se-components-wrap") || document.querySelector(".se-components-wrap");
    return w ? w.querySelectorAll(".se-component.se-image").length : 0;
  });
  if ((await countImages()) > 0) { console.log("[naver-img] image already present — skip"); return true; }

  const photoBtn = ef.locator("button.se-image-toolbar-button").first();
  if (!(await photoBtn.isVisible({ timeout: 3000 }).catch(() => false))) {
    console.log("[naver-img] 사진 button not found — skip image (drag manually): " + heroPng);
    return false;
  }
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
      // LAST text-component paragraph = the empty body paragraph Naver places after the
      // hero image; .first() can be the title or an image caption.
      const body = frame.locator(".se-component.se-text .se-text-paragraph").last();
      if (await body.isVisible({ timeout: 1500 })) { await body.click(); clicked = true; break; }
    } catch {}
  }
  if (!clicked) { console.log("[naver] body paragraph not found — body NOT injected"); return; }
  await page.waitForTimeout(400);
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length) await page.keyboard.type(lines[i], { delay: 4 });
    if (i < lines.length - 1) await page.keyboard.press("Enter");
    await page.waitForTimeout(25);
  }
  console.log(`[naver] body typed via keyboard.type (${lines.length} lines)`);

  // Strip inherited 취소선 (only possible on a non-fresh editor)
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

async function openNaverPublishPanel(editor, page) {
  const panelOpen = await editor.evaluate(() => /태그 편집/.test(document.body.innerText || ""));
  if (panelOpen) return true;
  try {
    const btn = editor.locator("button.publish_btn__m9KHH, button[class*='publish_btn'], button[class*='publish']").first();
    await btn.click({ timeout: 3000 });
    await page.waitForTimeout(1500);
    console.log("[naver] publish panel opened");
    return true;
  } catch (e) {
    console.log("[naver] could not open publish panel:", e.message);
    return false;
  }
}

async function doNaverTags(page) {
  if (!TAGS.length) { console.log("[naver-tags] no tags supplied, skipping"); return; }
  const editor = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!editor) { console.log("[naver-tags] editor frame missing"); return; }
  if (!(await openNaverPublishPanel(editor, page))) return;

  try {
    const tagInput = editor.locator("#tag-input").first();
    await tagInput.click({ timeout: 5000 });

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

// v3: finish the publish — set visibility to 공개(전체공개) and click the final 발행 button,
// then wait for navigation to the published post. Returns the post URL or null.
async function publishNaver(page) {
  const editor = page.frames().find(f => f.url().includes("PostWriteForm"));
  if (!editor) { console.log("[naver-publish] editor frame missing — NOT published"); return null; }
  if (!(await openNaverPublishPanel(editor, page))) { console.log("[naver-publish] NOT published"); return null; }

  // visibility: pick the 전체공개/공개 radio (labels: 전체공개·이웃공개·서로이웃공개·비공개)
  try {
    const picked = await editor.evaluate(() => {
      const labels = [...document.querySelectorAll("label")];
      const norm = el => (el.textContent || "").replace(/\s+/g, " ").trim();
      const lab = labels.find(l => /^전체\s*공개/.test(norm(l))) || labels.find(l => norm(l) === "공개");
      if (!lab) return "label-not-found";
      const input = lab.htmlFor ? document.getElementById(lab.htmlFor) : lab.querySelector("input[type=radio]");
      if (input && input.checked) return "already-공개";
      lab.click();
      return "clicked-공개";
    });
    console.log("[naver-publish] visibility:", picked);
    if (picked === "label-not-found") console.log("[naver-publish] 공개 radio not found — publishing with the panel's current setting");
    await page.waitForTimeout(500);
  } catch (e) { console.log("[naver-publish] visibility set skipped:", e.message); }

  // final 발행 button: confirm_btn (class hash rotates) — fall back to a button whose exact
  // text is 발행 but is NOT the panel-open publish_btn.
  const clicked = await editor.evaluate(() => {
    const byClass = [...document.querySelectorAll("button[class*='confirm_btn']")].pop();
    if (byClass) { byClass.click(); return "confirm_btn"; }
    const byText = [...document.querySelectorAll("button")].filter(b =>
      (b.textContent || "").trim() === "발행" && !/publish_btn/.test(b.className));
    if (byText.length) { byText[byText.length - 1].click(); return "text-발행"; }
    return null;
  }).catch(e => { console.log("[naver-publish] confirm click failed:", e.message); return null; });
  if (!clicked) {
    await page.screenshot({ path: "/tmp/naver-publish-FAILED.png" }).catch(() => {});
    console.log("[naver-publish] final 발행 button not found — NOT published, /tmp/naver-publish-FAILED.png");
    return null;
  }
  console.log("[naver-publish] final 발행 clicked via", clicked);

  // wait until the editor navigates to the published post; dismiss any 확인 popup on the way
  const deadline = Date.now() + 25000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(1000);
    for (const frame of page.frames()) {
      try {
        const ok = frame.locator("button.se-popup-button-confirm, button:has-text('확인')").first();
        if (await ok.isVisible({ timeout: 300 })) { await ok.click(); console.log("[naver-publish] dismissed 확인 popup"); }
      } catch {}
    }
    const u = page.url();
    if (!/GoBlogWrite|PostWriteForm/.test(u) && /blog\.naver\.com/.test(u)) {
      console.log("[naver-publish] ✅ PUBLISHED →", u);
      return u;
    }
  }
  await page.screenshot({ path: "/tmp/naver-publish-TIMEOUT.png" }).catch(() => {});
  console.log("[naver-publish] no navigation within 25s — verify manually, /tmp/naver-publish-TIMEOUT.png (url=" + page.url() + ")");
  return null;
}

// ---------- main ----------
(async () => {
  // Tistory queue inputs are validated up front so a bad hero/source fails BEFORE the
  // irreversible Naver publish runs.
  if (wantsTistory) {
    const hero = path.resolve(HERO_PNG);
    if (!existsSync(hero)) die("hero PNG not found: " + hero);
  }

  let plain = "";
  if (wantsNaver) {
    console.log("fetching article HTML…");
    const html = await fetchArticleHtml(SOURCE_URL);
    plain = htmlToPlain(html);
    writeFileSync("/tmp/crosspost-body.txt", plain);
    console.log(`plain ${plain.length}B → /tmp/crosspost-body.txt\n`);
  }

  if (wantsNaver || mode === "naver-tags") {
    const browser = await connect();
    const ctx = browser.contexts()[0];
    try {
      if (wantsNaver) await doNaver(ctx, plain);
      if (mode === "naver-tags") {
        const n = ctx.pages().find(p => p.url().includes("blog.naver.com") && p.url().includes("Write"));
        if (!n) die("no open Naver write tab — run `naver` mode first");
        await n.bringToFront(); await n.waitForTimeout(500);
        await doNaverTags(n);
      }
    } finally {
      await browser.close();
    }
  }

  // Tistory LAST: the hook spawns a detached scheduler that drives the same CDP Chrome —
  // queueing after the Naver work is done keeps the two from fighting over the browser.
  if (wantsTistory) queueTistory();
  if (mode === "queue") queueNaver();
})().catch(e => { console.error("FATAL:", e); process.exit(1); });
