import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = await b.contexts()[0].newPage();
await page.setViewportSize({width:1440,height:1000});
await page.goto('https://kmong.com/my-gigs',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(4500);
const ok = await page.evaluate(()=>{
  const n=[...document.querySelectorAll('*')].find(e=>e.children.length===0 && /서비스 상태 안내/.test(e.textContent||''));
  if(!n) return false; (n.closest('button')||n).click(); return true;
});
console.log('툴팁 클릭:', ok);
await page.waitForTimeout(2500);
const t = await page.evaluate(()=>document.body.innerText);
const i = t.indexOf('서비스 상태');
console.log(t.slice(i, i+900).replace(/\n{2,}/g,'\n'));
await page.screenshot({path:'/tmp/km-status.png'});
await page.close(); await b.close();
