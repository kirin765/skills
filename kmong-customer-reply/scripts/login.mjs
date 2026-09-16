// login.mjs — 크몽 CDP 세션 확보 (네이버 간편로그인 우선)
//
// 이메일/PW 로그인은 캡차를 유발할 수 있어, CDP 프로필에 유지되는 **네이버 세션**을
// 이용한 SNS 간편로그인을 기본 경로로 쓴다. 네이버 세션까지 만료됐고 네이버 로그인
// 화면에 캡차가 뜨면 자동으로 풀지 않는다 — cdp-anywhere 스킬의 캡차 릴레이로 넘긴다.
//
// 실행:  node "<skill>/scripts/login.mjs"
// 출력:  {"ok":true,"logged_in":true,"method":"already|naver", ...}
//        {"ok":false,"logged_in":false,"error":"captcha", "url":..., "screenshot":...}
//        {"ok":false,"logged_in":false,"error":"naver-credentials-required", ...}
//
// 전제: Chrome :9222(chrome-cdp-profile). Linux 는 --class=cdpchrome 로 기동.

import os from 'node:os';
import path from 'node:path';
import { connectCdp } from './cdp.mjs';

const SHOT = path.join(process.env.KMONG_SHOT_DIR || os.tmpdir(), 'kmong-login.png');
const CAPTCHA_SEL = 'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"], [data-sitekey], .g-recaptcha, [id*="captcha" i], [name*="captcha" i], img[src*="captcha" i]';
const CAPTCHA_HINTS = ['로봇이 아닙니다', '보안 문자', '자동 입력 방지', 'captcha', 'verify you are human', 'enter the characters'];

function out(obj) { console.log(JSON.stringify(obj, null, 1)); }

async function isLoggedIn(ctx) {
  try {
    const res = await ctx.request.get('https://kmong.com/api/v5/inbox-groups?page=1');
    if (!res.ok()) return false;
    const j = await res.json();
    return Array.isArray(j.inbox_groups);
  } catch { return false; }
}

async function detectCaptcha(page) {
  try {
    const els = await page.$$eval(CAPTCHA_SEL, a => a.map(e => ({
      tag: e.tagName, src: (e.getAttribute('src') || '').slice(0, 120), id: e.id,
    })));
    if (els.length) return els;
    const text = (await page.locator('body').innerText({ timeout: 3000 })).toLowerCase();
    if (CAPTCHA_HINTS.some(h => text.includes(h.toLowerCase()))) return [{ tag: 'text-hint' }];
  } catch { /* navigating */ }
  return [];
}

let browser;
try {
  browser = await connectCdp({ log: m => console.error(m) });
} catch (e) {
  out({ ok: false, logged_in: false, error: 'no-cdp', hint: e.message });
  process.exit(1);
}

const ctx = browser.contexts()[0];
if (!ctx) { out({ ok: false, logged_in: false, error: 'no-context' }); process.exit(1); }

// --logout : 크몽 쿠키만 삭제해 세션을 끊고 네이버 간편로그인을 다시 태운다 (계정 전환/테스트용)
if (process.argv.includes('--logout')) {
  const page0 = ctx.pages()[0] || await ctx.newPage();
  const cdp = await ctx.newCDPSession(page0);
  for (const c of await ctx.cookies('https://kmong.com')) {
    await cdp.send('Network.deleteCookies', { name: c.name, domain: c.domain, path: c.path }).catch(() => {});
  }
}

if (await isLoggedIn(ctx)) {
  out({ ok: true, logged_in: true, method: 'already' });
  await browser.close();
  process.exit(0);
}

const newPages = [];
ctx.on('page', p => newPages.push(p));

let page = ctx.pages().find(p => p.url().includes('kmong.com')) || ctx.pages()[0] || await ctx.newPage();
await page.goto('https://kmong.com/?open=login_modal&next_page=%2Finboxes', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3000);

const naverBtn = page.locator('button:has(img[src*="naver-logo"])').first();
try {
  await naverBtn.waitFor({ state: 'attached', timeout: 10000 });
} catch {
  await page.screenshot({ path: SHOT });
  out({ ok: false, logged_in: false, error: 'naver-button-not-found', url: page.url(), screenshot: SHOT });
  await browser.close();
  process.exit(1);
}
await naverBtn.scrollIntoViewIfNeeded();
await naverBtn.click();

const deadline = Date.now() + 30000;
while (Date.now() < deadline) {
  await page.waitForTimeout(1500);
  const cur = newPages.length ? newPages[newPages.length - 1] : page;
  const url = cur.url();

  const cap = await detectCaptcha(cur);
  if (cap.length) {
    await cur.screenshot({ path: SHOT }).catch(() => {});
    out({ ok: false, logged_in: false, error: 'captcha', url, elements: cap, screenshot: SHOT });
    await browser.close();
    process.exit(1);
  }

  // 네이버 동의 화면이 뜨면 통과
  try {
    const agree = cur.locator('a, button').filter({ hasText: /동의하고 계속하기|동의하기/ }).first();
    if (url.includes('naver.com') && await agree.count() && await agree.isVisible()) {
      await agree.click();
      continue;
    }
  } catch { /* ignore */ }

  // 네이버 로그인 폼(ID/PW)이 뜨면 자격증명 필요 — 자동 입력하지 않음
  if (url.includes('nid.naver.com') && (await cur.locator('#id, input#pw, input[name="id"]').count())) {
    await cur.screenshot({ path: SHOT }).catch(() => {});
    out({ ok: false, logged_in: false, error: 'naver-credentials-required', url, screenshot: SHOT });
    await browser.close();
    process.exit(1);
  }

  if (await isLoggedIn(ctx)) {
    out({ ok: true, logged_in: true, method: 'naver' });
    await browser.close();
    process.exit(0);
  }
}

await (newPages.length ? newPages[newPages.length - 1] : page).screenshot({ path: SHOT }).catch(() => {});
out({ ok: false, logged_in: false, error: 'login-timeout', url: (newPages.length ? newPages[newPages.length - 1] : page).url(), screenshot: SHOT });
await browser.close();
process.exit(1);
