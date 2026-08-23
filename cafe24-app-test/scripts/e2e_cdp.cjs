#!/usr/bin/env node
// 카페24 앱 E2E 테스트 — CDP로 개발자센터/몰 접속 확인 (S1 보조)
// 사용: node e2e_cdp.cjs <mall_id> [--debug]
// 사전 조건: Chrome CDP 9222, 카페24 개발자센터 로그인, 테스트 설치 한도 잔여
const fs = require('fs');
const path = require('path');

function loadEnv() {
  const envFile = path.join(__dirname, '..', '.env');
  if (!fs.existsSync(envFile)) return {};
  const env = {};
  for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (m) env[m[1]] = m[2].replace(/^"|"$/g, '');
  }
  return env;
}

const mall = process.argv[2];
const debug = process.argv.includes('--debug');
if (!mall) { console.error('사용: node e2e_cdp.cjs <mall_id> [--debug]'); process.exit(1); }
const env = loadEnv();

async function main() {
  // Playwright — 전역 설치 위치 (naver-cafe-scrape 스킬과 동일)
  const pwPath = process.env.HOME + '/.local/pw/node_modules/playwright';
  const { chromium } = require(pwPath);
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();
  const steps = [];
  const ok = (s) => { steps.push('✅ ' + s); console.log('✅ ' + s); };
  const bad = (s) => { steps.push('❌ ' + s); console.log('❌ ' + s); };

  // 1. 개발자센터 로그인 확인 — "어드민" 버튼 존재가 로그인 지표 (사용자 실측 2026-08-20)
  try {
    await page.goto('https://developers.cafe24.com/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(5000);
    const adminBtn = await page.evaluate(() => {
      const el = [...document.querySelectorAll('a, button')].find(x => /어드민/.test(x.textContent || ''));
      return el ? { text: el.textContent.trim().slice(0, 20), href: el.href || null } : null;
    });
    if (adminBtn) {
      ok('개발자센터 로그인 확인 (어드민 버튼 존재)');
      // 어드민 클릭 → 콘솔 진입 확인
      await page.goto(adminBtn.href, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(() => {});
      await page.waitForTimeout(4000);
      const loggedInAs = await page.evaluate(() => {
        const body = document.body.innerText || '';
        const m = body.match(/([^\n|]{2,20})\s*님|로그아웃/);
        return m ? m[1] || '로그인됨' : null;
      });
      loggedInAs ? ok(`콘솔 로그인: ${loggedInAs}`) : bad('콘솔 진입 후 로그인 식별 실패');
    } else {
      bad('로그인 안 됨 — 개발자센터 우상단 "어드민" 버튼 없음. CDP Chrome에 개발자센터 로그인 필요');
    }
  } catch (e) { bad('개발자센터 접속 실패: ' + e.message); }

  // 2. 몰 관리자 접속 확인
  try {
    await page.goto(`https://${mall}.cafe24.com/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(4000);
    const mallTitle = await page.title();
    ok(`몰 ${mall} 접속 (${mallTitle})`);
  } catch (e) { bad(`몰 ${mall} 접속 실패: ${e.message}`); }

  if (debug) await page.screenshot({ path: path.join(__dirname, '..', 'debug-e2e.png') });

  console.log('\n--- E2E 결과 ---');
  steps.forEach(s => console.log(s));
  const fails = steps.filter(s => s.startsWith('❌')).length;
  console.log(`\nPASS=${steps.length - fails} FAIL=${fails}`);
  process.exit(fails > 0 ? 1 : 0);
}

main().catch(e => { console.error('E2E 에러:', e); process.exit(1); });
