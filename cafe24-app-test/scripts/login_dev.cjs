// 개발자센터 로그인 + 개발정보 화면 실측
const { chromium } = require(process.env.HOME + '/.local/pw/node_modules/playwright');
const fs = require('fs');

const env = {};
fs.readFileSync(process.env.HOME + '/.claude/skills/cafe24-app-test/.env', 'utf8').split('\n').forEach(l => {
  const m = l.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^"|"$/g, '');
});

async function main() {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  await page.goto('https://developers.cafe24.com/developer/front/login', { waitUntil: 'networkidle', timeout: 60000 }).catch(()=>{});
  await page.waitForTimeout(4000);
  // 로그인 폼 입력
  const inputs = await page.evaluate(() => [...document.querySelectorAll('input')].map(i=>({type:i.type, name:i.name, id:i.id, ph:i.placeholder})));
  console.log('로그인 폼 inputs:', JSON.stringify(inputs));
  await page.fill('#idLoginId', env.CAFE24_CONSOLE_ID).catch(e=>console.log('id fill err', e.message));
  await page.fill('#idLoginPasswd', env.CAFE24_CONSOLE_PW).catch(e=>console.log('pw fill err', e.message));
  await page.waitForTimeout(500);
  await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/로그인/.test(x.textContent||'')); b?.click(); });
  await page.waitForTimeout(7000);
  const after = await page.evaluate(() => ({ url: location.href, body: (document.body.innerText||'').slice(0,250).replace(/\n/g,' | ') }));
  console.log('로그인 후 URL:', after.url);
  console.log('BODY:', after.body);
  await page.screenshot({ path: '/tmp/c24login-after.png' });
  process.exit(0);
}
main().catch(e=>{console.error('err', e.message); process.exit(1);});
