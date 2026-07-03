#!/usr/bin/env node
// Standalone Google Trends analysis via the user's authenticated Chrome (CDP 9222).
//
// Google Trends has NO public API. Its internal endpoints (trends.google.com/trends/api/*)
// reject anonymous datacenter calls with HTTP 429. The reliable path is to borrow the
// user's logged-in Chrome session over CDP — real cookies + residential IP.
//
// Precondition: Chrome running with --remote-debugging-port=9222, logged into Google.
//
// Examples
//   node google_trends.mjs bitcoin                       # worldwide, last 12 months
//   node google_trends.mjs 아이폰 갤럭시 --geo KR          # compare two, Korea
//   node google_trends.mjs "chatgpt" --time "today 5-y" --related --region
//   node google_trends.mjs diet --geo US --out gt.json --json

import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pwPath = process.env.PLAYWRIGHT_PATH || `${process.env.HOME}/node_modules/playwright`;
let chromium;
try {
  ({ chromium } = require(pwPath));
} catch {
  console.error(`Could not load Playwright from ${pwPath}. Set PLAYWRIGHT_PATH or install it (npm i -g playwright).`);
  process.exit(1);
}

// ---- args ----
const argv = process.argv.slice(2);
const opt = { keywords: [], geo: '', time: 'today 12-m', cat: 0, tz: -540, related: false, region: false, json: false, out: null };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--geo') opt.geo = argv[++i];
  else if (a === '--time' || a === '--timeframe') opt.time = argv[++i];
  else if (a === '--cat' || a === '--category') opt.cat = Number(argv[++i]);
  else if (a === '--tz') opt.tz = Number(argv[++i]);
  else if (a === '--related') opt.related = true;
  else if (a === '--region') opt.region = true;
  else if (a === '--json') opt.json = true;
  else if (a === '--out') opt.out = argv[++i];
  else if (a.startsWith('--')) { console.error('unknown flag', a); process.exit(2); }
  else opt.keywords.push(a);
}
if (opt.keywords.length === 0) { console.error('provide at least one keyword'); process.exit(2); }
opt.keywords = opt.keywords.slice(0, 5); // Trends compares max 5

const strip = t => t.replace(/^\)\]\}'[,\n]*/, '');
const H = { 'accept-language': 'en-US,en', referer: 'https://trends.google.com/trends/explore' };

async function ensureTab() {
  const list = await (await fetch('http://localhost:9222/json')).json();
  if (!list.some(t => t.type === 'page')) {
    await fetch('http://localhost:9222/json/new?about:blank', { method: 'PUT' });
  }
}

async function getJSON(ctx, url) {
  const r = await ctx.request.get(url, { headers: H });
  if (r.status() !== 200) {
    const body = (await r.text()).slice(0, 160);
    throw new Error(`HTTP ${r.status()} from ${url.split('?')[0]} :: ${body}`);
  }
  return JSON.parse(strip(await r.text()));
}

function exploreUrl() {
  const req = {
    comparisonItem: opt.keywords.map(k => ({ keyword: k, geo: opt.geo, time: opt.time })),
    category: opt.cat, property: '',
  };
  return 'https://trends.google.com/trends/api/explore?hl=en-US&tz=' + opt.tz + '&req=' + encodeURIComponent(JSON.stringify(req));
}
function widgetUrl(path, w) {
  return 'https://trends.google.com/trends/api/widgetdata/' + path + '?hl=en-US&tz=' + opt.tz +
    '&req=' + encodeURIComponent(JSON.stringify(w.request)) + '&token=' + w.token;
}

function bar(v, peak) { return peak ? '█'.repeat(Math.round(v / 5)) : ''; }

(async () => {
  let cdpOk = true;
  try { await fetch('http://localhost:9222/json/version'); } catch { cdpOk = false; }
  if (!cdpOk) {
    console.error('CDP 9222 not responding. Launch Chrome with:\n  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile"');
    process.exit(1);
  }
  await ensureTab();
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];

  let widgets;
  try {
    widgets = (await getJSON(ctx, exploreUrl())).widgets;
  } catch (e) {
    // warm up consent/session cookies once, then retry
    const page = await ctx.newPage();
    await page.goto('https://trends.google.com/trends/explore', { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2000);
    await page.close();
    try { widgets = (await getJSON(ctx, exploreUrl())).widgets; }
    catch (e2) {
      console.error('Google Trends rejected the request even via your session.\n' + e2.message +
        '\nIf this is 429, you are temporarily rate-limited — wait a few minutes. If 401/redirect, log into Google in the CDP Chrome profile.');
      await browser.close();
      process.exit(1);
    }
  }

  const out = { query: opt, interestOverTime: null, related: {}, region: {} };

  // Interest over time (TIMESERIES) — always
  const ts = widgets.find(w => w.id === 'TIMESERIES');
  const tl = (await getJSON(ctx, widgetUrl('multiline', ts))).default.timelineData;
  out.interestOverTime = tl;

  const blocks = [];
  blocks.push(`# Google Trends  geo=${opt.geo || 'WORLDWIDE'}  time="${opt.time}"  (interest 0-100, relative)`);
  opt.keywords.forEach((kw, idx) => {
    const series = tl.map(p => ({ period: p.formattedAxisTime, v: p.value[idx], partial: !!p.isPartial }));
    const peak = Math.max(...series.map(s => s.v), 0);
    const avg = series.reduce((a, s) => a + s.v, 0) / (series.length || 1);
    blocks.push(`\n== ${kw} ==  (avg ${avg.toFixed(1)}, peak ${peak})`);
    for (const s of series) blocks.push(`  ${s.period}${s.partial ? '*' : ' '}  ${String(s.v).padStart(3)}  ${bar(s.v, peak)}`);
  });

  // Related queries
  if (opt.related) {
    const rqs = widgets.filter(w => w.id.startsWith('RELATED_QUERIES'));
    for (let i = 0; i < rqs.length; i++) {
      const kw = opt.keywords[i] ?? `kw${i}`;
      try {
        const lists = (await getJSON(ctx, widgetUrl('relatedsearches', rqs[i]))).default.rankedList || [];
        const top = (lists[0]?.rankedKeyword || []).slice(0, 8).map(k => `${k.query} (${k.value})`);
        const rising = (lists[1]?.rankedKeyword || []).slice(0, 8).map(k => `${k.query} (${k.formattedValue})`);
        out.related[kw] = { top, rising };
        blocks.push(`\n-- related queries: ${kw} --`);
        blocks.push(`  TOP:    ${top.join(', ') || '(none)'}`);
        blocks.push(`  RISING: ${rising.join(', ') || '(none)'}`);
      } catch (e) { blocks.push(`\n-- related queries: ${kw} -- (unavailable: ${e.message.split('::')[0].trim()})`); }
    }
  }

  // Interest by region
  if (opt.region) {
    const gms = widgets.filter(w => w.id.startsWith('GEO_MAP'));
    for (let i = 0; i < gms.length; i++) {
      const kw = opt.keywords[i] ?? `kw${i}`;
      try {
        const geo = (await getJSON(ctx, widgetUrl('comparedgeo', gms[i]))).default.geoMapData || [];
        const ranked = geo.filter(g => g.hasData?.[0]).sort((a, b) => b.value[0] - a.value[0]).slice(0, 10)
          .map(g => `${g.geoName} (${g.value[0]})`);
        out.region[kw] = ranked;
        blocks.push(`\n-- top regions: ${kw} --`);
        blocks.push(`  ${ranked.join(', ') || '(none)'}`);
      } catch (e) { blocks.push(`\n-- top regions: ${kw} -- (unavailable)`); }
    }
  }

  await browser.close();

  if (opt.out) {
    const { writeFileSync } = require('fs');
    writeFileSync(opt.out, JSON.stringify(out, null, 2));
    console.error('saved JSON -> ' + opt.out);
  }
  console.log(opt.json ? JSON.stringify(out, null, 2) : blocks.join('\n'));
})();
