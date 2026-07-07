#!/usr/bin/env node
// Google Keyword Planner via the user's authenticated Chrome (CDP 9222).
// Drives the "새 키워드 찾기 / Discover new keywords" flow, sets location+language,
// submits seed keywords, scrapes the results table.
//
// Precondition: Chrome on --remote-debugging-port=9222, logged into a Google Ads
// account with Keyword Planner access. Volume shows as RANGES unless the account
// actively spends. No spend / read-only (does not create or save a plan).
//
//   node kp.mjs gunpla "gundam model kit" --geo US
//   node kp.mjs 건프라 프라모델 --geo KR --json

import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pwPath = process.env.PLAYWRIGHT_PATH || `${process.env.HOME}/node_modules/playwright`;
let chromium;
try { ({ chromium } = require(pwPath)); }
catch { console.error(`Could not load Playwright from ${pwPath}. Set PLAYWRIGHT_PATH or install it.`); process.exit(1); }

// --- args ---
const argv = process.argv.slice(2);
const opt = { seeds: [], geo: '', lang: '', limit: 60, json: false };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--geo') opt.geo = argv[++i];
  else if (a === '--lang') opt.lang = argv[++i];
  else if (a === '--limit') opt.limit = Number(argv[++i]);
  else if (a === '--json') opt.json = true;
  else if (a.startsWith('--')) { console.error('unknown flag', a); process.exit(2); }
  else opt.seeds.push(a);
}
if (!opt.seeds.length) { console.error('provide at least one seed keyword'); process.exit(2); }

// geo code -> Korean country name (KP UI is Korean for this account)
const GEO_KO = { US:'미국', KR:'대한민국', JP:'일본', GB:'영국', DE:'독일', FR:'프랑스',
  CA:'캐나다', AU:'호주', IN:'인도', ID:'인도네시아', TW:'대만', BR:'브라질', CN:'중국', ES:'스페인' };
const LANG_KO = { ko:'한국어', en:'영어', ja:'일본어', zh:'중국어', es:'스페인어', de:'독일어', fr:'프랑스어' };

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickText(page, texts, timeout = 5000) {
  for (const t of [].concat(texts)) {
    try { await page.locator(`text=${t}`).first().click({ timeout }); return true; } catch {}
  }
  return false;
}

(async () => {
  try { await fetch('http://localhost:9222/json/version'); }
  catch { console.error('CDP 9222 not responding. Launch Chrome with:\n  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"'); process.exit(1); }

  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  const fail = async (msg) => { console.error(msg); await page.close().catch(()=>{}); await browser.close().catch(()=>{}); process.exit(1); };

  await page.goto('https://ads.google.com/aw/keywordplanner/home', { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(()=>{});
  await sleep(3500);
  const title = await page.title().catch(()=> '');
  if (!/키워드 플래너|Keyword Planner/i.test(title)) {
    if (/로그인|Sign in|accounts\.google/i.test(title + page.url()))
      return fail('Not logged into Google Ads in the CDP Chrome profile. Log in, then retry.');
    return fail(`Keyword Planner did not load (title="${title}"). Is a Google Ads account selected?`);
  }

  if (!await clickText(page, ['새 키워드 찾기', 'Discover new keywords'], 8000))
    return fail('Could not open "새 키워드 찾기".');
  await sleep(3500);

  // --- location targeting (best-effort; falls back to account default on failure) ---
  if (opt.geo) {
    const country = GEO_KO[opt.geo.toUpperCase()] || opt.geo;
    try {
      // open the location dialog (retry; button label = icon "location_on" + "대한민국")
      let dlg = null;
      for (let a = 0; a < 2 && !dlg; a++) {
        await page.getByRole('button', { name: /대한민국/ }).first().click({ timeout: 4000 }).catch(() => {});
        await sleep(1800);
        if (await page.locator('[role="dialog"]').count()) dlg = page.locator('[role="dialog"]').first();
      }
      if (dlg) {
        const search = dlg.locator('input').first();   // placeholder is a floating label, so scope to dialog
        await search.click({ timeout: 4000 });
        await search.type(country, { delay: 35 });
        await sleep(2200);
        await page.locator('[role="option"]').filter({ hasText: country }).first().click({ timeout: 4000 })
          .catch(async () => { await clickText(page, [`${country} 국가`, country], 3000); });
        await sleep(1200);
        if (country !== '대한민국') {   // drop the default so volume is target-country only
          const koRow = dlg.locator('[role="row"], li, div').filter({ hasText: '대한민국 국가' }).first();
          await koRow.getByRole('button').last().click({ timeout: 2500 }).catch(() => {});
          await sleep(700);
        }
        await dlg.getByText(/^저장$|^Save$/).first().click({ timeout: 4000 })
          .catch(async () => { if (!await clickText(page, ['저장', 'Save'], 2500)) await page.keyboard.press('Escape').catch(()=>{}); });
        await sleep(2000);
      }
    } catch (e) {
      console.error('  (location targeting failed → using account default; ' + String(e).split('\n')[0].slice(0, 70) + ')');
      await page.keyboard.press('Escape').catch(()=>{}); await sleep(800);
    }
  }

  // --- language (best-effort) ---
  if (opt.lang) {
    const langName = LANG_KO[opt.lang.toLowerCase()] || opt.lang;
    try {
      if (await clickText(page, [`translate ${langName}`, 'translate'], 3000)) {
        await sleep(1500);
        const box = page.getByPlaceholder(/언어|language/i).first();
        await box.click({ timeout: 2500 }); await box.type(langName, { delay: 30 }); await sleep(1200);
        await clickText(page, [langName], 3000);
        if (!await clickText(page, ['저장', 'Save'], 3000)) await page.keyboard.press('Escape').catch(()=>{});
        await sleep(1500);
      }
    } catch { await page.keyboard.press('Escape').catch(()=>{}); await sleep(600); }
  }

  // --- seeds (retry once with Escape in case a dialog is still open) ---
  let seedOk = false;
  for (let attempt = 0; attempt < 2 && !seedOk; attempt++) {
    try {
      const seed = page.locator('[aria-label="검색어 입력"], [aria-label="Enter search terms"]').first();
      await seed.click({ timeout: 6000 });
      for (const s of opt.seeds) { await seed.type(s, { delay: 25 }); await page.keyboard.press('Enter'); await sleep(400); }
      seedOk = true;
    } catch { await page.keyboard.press('Escape').catch(()=>{}); await sleep(1200); }
  }
  if (!seedOk) return fail('Could not find the seed input (a dialog may be blocking it).');

  if (!await clickText(page, ['결과 보기', 'Get results'], 6000)) return fail('Could not click "결과 보기".');

  // wait for results table
  let ok = false;
  for (let i = 0; i < 20; i++) {
    await sleep(1500);
    const n = await page.locator('[role="row"]').count().catch(()=>0);
    if (n > 4 && await page.locator('text=월간 평균 검색량').count().catch(()=>0)) { ok = true; break; }
  }
  if (!ok) return fail('Results table did not appear (timeout / possible rate-limit). Try again.');

  // --- scrape --- (cells are newline-separated within each [role="row"])
  const rows = await page.evaluate((limit) => {
    const out = [];
    const ICON = /^(add|help_outline|check_box|check_box_outline_blank|star|star_border|arrow_upward|arrow_downward|more_vert|info|open_in_new|expand_more)$/i;
    for (const r of document.querySelectorAll('[role="row"]')) {
      const cells = (r.innerText || '').split('\n').map(s => s.trim()).filter(s => s && !ICON.test(s));
      if (cells.length < 3) continue;
      const kw = cells[0];
      const vol = cells[1] || '';
      if (!kw || /월간 평균 검색량|키워드\s*\(|성인용/.test(kw)) continue;   // skip header / chip bar
      if (!/~|\d/.test(vol)) continue;                                       // volume-like only
      const comp = cells.find(c => /^(낮음|중간|높음|Low|Medium|High)$/.test(c)) || '';
      const bids = cells.filter(c => /[₩$]/.test(c));
      out.push({ keyword: kw, volume: vol, competition: comp, bid_low: bids[0] || '', bid_high: bids[bids.length - 1] || '' });
      if (out.length >= limit) break;
    }
    return out;
  }, opt.limit).catch(()=>[]);

  await page.close().catch(()=>{});
  await browser.close().catch(()=>{});

  if (!rows.length) { console.error('No rows scraped (DOM may have changed).'); process.exit(1); }
  if (opt.json) { console.log(JSON.stringify({ geo: opt.geo || 'account-default', lang: opt.lang || 'default', rows }, null, 2)); return; }
  console.log(`# Keyword Planner  geo=${opt.geo || 'account-default(대한민국)'}  lang=${opt.lang || 'default'}  (volume = monthly range; exact numbers need active ad spend)`);
  console.log(`${'keyword'.padEnd(30)}${'volume'.padStart(14)}${'comp'.padStart(8)}${'bid_low'.padStart(9)}${'bid_high'.padStart(9)}`);
  for (const r of rows) console.log(`${r.keyword.slice(0,29).padEnd(30)}${r.volume.padStart(14)}${(r.competition||'-').padStart(8)}${(r.bid_low||'-').padStart(9)}${(r.bid_high||'-').padStart(9)}`);
})();
