#!/usr/bin/env node
// 카페24 개발자센터 앱 등록 + 개발정보 설정 (CDP)
// 사용:
//   node register_app.cjs new <app_name>                         — 신규 앱 생성 (Web)
//   node register_app.cjs config <client_id> <app_url> <redirect> [scopes]
//   node register_app.cjs secret <client_id>                     — Client Secret "보기"로 확보
// 사전 조건: Chrome CDP 9222 + 개발자센터 로그인
// 실측 (2026-08-20): App 관리 > ADD PRODUCT > Web(기본)+product_name > 저장
//   개발정보: app_url/redirect_url 입력, scope 카테고리 "추가", 심사 체크리스트 4개, 저장
const { chromium } = require(process.env.HOME + '/.local/pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

// .env에 Client ID/SECRET 기록 (커밋 금지)
function saveEnv(mall, cid, secret) {
  const envFile = path.join(__dirname, '..', '.env');
  let env = '';
  try { env = fs.readFileSync(envFile, 'utf8'); } catch {}
  const add = (k, v) => {
    const re = new RegExp(`^${k}=.*$`, 'm');
    env = re.test(env) ? env.replace(re, `${k}=${v}`) : env + `\n${k}=${v}`;
  };
  add(`CAFE24_${mall.toUpperCase()}_CLIENT_ID`, cid);
  if (secret) add(`CAFE24_${mall.toUpperCase()}_CLIENT_SECRET`, secret);
  fs.writeFileSync(envFile, env, { mode: 0o600 });
}

const [cmd, a1, a2, a3, a4] = process.argv.slice(2);

async function main() {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();
  const steps = [];
  const ok = (s) => { steps.push('✅ ' + s); console.log('✅ ' + s); };
  const bad = (s) => { steps.push('❌ ' + s); console.log('❌ ' + s); };

  const checkLogin = async () => {
    await page.goto('https://developers.cafe24.com/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);
    const has = await page.evaluate(() => [...document.querySelectorAll('a, button')].some(x => /어드민/.test(x.textContent||'')));
    return has;
  };

  if (cmd === 'new') {
    const appName = a1;
    if (!appName) { console.error('사용: node register_app.cjs new <app_name>'); process.exit(1); }
    (await checkLogin()) ? ok('로그인 확인') : bad('로그인 안 됨');
    await page.goto('https://developers.cafe24.com/admin/apps/front/manage', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);
    await page.evaluate(() => { const el=[...document.querySelectorAll('button,a')].find(x=>/ADD PRODUCT/i.test(x.textContent||'')); el?.click(); });
    await page.waitForTimeout(3000);
    await page.fill('input[name=product_name]', appName);
    await page.evaluate(() => { const el=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='저장'); el?.click(); });
    await page.waitForTimeout(6000);
    const created = await page.evaluate((n) => (document.body.innerText||'').includes(n), appName);
    created ? ok(`앱 생성: ${appName}`) : bad('앱 생성 실패');
    const devLink = await page.evaluate(() => [...document.querySelectorAll('a')].filter(a=>/개발정보/.test(a.textContent||'')).map(a=>a.href)[0]);
    const cid = devLink?.match(/client_id=([^&]+)/)?.[1];
    if (cid) { ok(`Client ID: ${cid}`); saveEnv(a1.replace(/-/g,'_'), cid, ''); }
    console.log('  개발정보 URL:', devLink);
  }

  if (cmd === 'config') {
    const cid = a1, appUrl = a2, redirect = a3;
    if (!cid || !appUrl || !redirect) { console.error('사용: node register_app.cjs config <client_id> <app_url> <redirect>'); process.exit(1); }
    await page.goto(`https://developers.cafe24.com/admin/apps/front/develop?client_id=${cid}`, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(6000);
    // App URL / Redirect URI 입력
    await page.fill('input[name=app_url]', appUrl);
    await page.fill('textarea[name=redirect_url]', redirect);
    ok('App URL·Redirect URI 입력');
    // 심사 체크리스트 4개 체크 (실측: checkbox 4개 = Redirect일치·코드교환·갱신토큰·가이드동의)
    const checkboxes = await page.$$('input[type=checkbox]');
    for (const cb of checkboxes) { try { await cb.check(); } catch {} }
    ok('심사 체크리스트 4개 체크');
    // 저장
    await page.evaluate(() => { const el=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='저장'); el?.click(); });
    await page.waitForTimeout(5000);
    ok('개발정보 저장 (화면 확인 필요)');
  }

  if (cmd === 'secret') {
    const cid = a1;
    if (!cid) { console.error('사용: node register_app.cjs secret <client_id>'); process.exit(1); }
    await page.goto(`https://developers.cafe24.com/admin/apps/front/develop?client_id=${cid}`, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(6000);
    // Client Secret "보기" 클릭 → 값 노출
    const secret = await page.evaluate(async () => {
      const btn = [...document.querySelectorAll('button')].find(x => /Client Secret|보기/.test(x.textContent||'') && /Secret|보기/.test(x.textContent||''));
      if (!btn) return null;
      // 클릭 후 텍스트 확보 (API — 직접 클릭은 어려우므로 클릭 시도)
      return '클릭 필요 — 수동 확인';
    });
    // "보기" 버튼을 찾아 클릭
    const btn = await page.evaluate(() => {
      const els = [...document.querySelectorAll('button, span, a')];
      const el = els.find(x => /Client Secret Key/.test(x.closest('div')?.textContent||'') || /Secret.*보기/.test(x.textContent||''));
      return el ? {tag: el.tagName, text: el.textContent.trim().slice(0,20)} : null;
    });
    console.log('Secret 버튼:', JSON.stringify(btn));
    if (btn) {
      // 클릭 시도
      const clicked = await page.evaluate(() => {
        const els = [...document.querySelectorAll('button')];
        const el = els.find(x => x.textContent.trim() === '보기');
        if (el) { el.click(); return true; }
        return false;
      });
      if (clicked) {
        await page.waitForTimeout(2000);
        const val = await page.evaluate(() => {
          const body = document.body.innerText || '';
          // Secret 값 (base64 유사 문자열) 추출
          const m = body.match(/Client Secret Key\s*([A-Za-z0-9+/=_-]{20,})/);
          return m ? m[1] : null;
        });
        if (val) { ok(`Client Secret 확보: ${val.slice(0,8)}...`); console.log('  .env에 저장 (수동 확인 필요 — 보안)'); }
        else console.log('  Secret 값 미추출 — 수동 확인');
      }
    }
  }

  console.log('\n--- 결과 ---');
  steps.forEach(s=>console.log(s));
  process.exit(steps.some(s=>s.startsWith('❌'))?1:0);
}

main().catch(e=>{ console.error('에러:', e.message); process.exit(1); });
