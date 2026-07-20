import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = await b.contexts()[0].newPage();
await page.setViewportSize({width:1440,height:1000});
await page.goto('https://kmong.com/gig/781350',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(4000);
await page.screenshot({path:'/tmp/km-gig-top.png', clip:{x:0,y:0,width:1440,height:1000}});
const btns = await page.evaluate(()=>[...document.querySelectorAll('button,a')]
  .map(e=>({t:(e.textContent||'').trim().slice(0,25), h:e.getAttribute('href')||''}))
  .filter(o=>o.t && /수정|편집|관리|내 서비스|판매자|전문가|대시/.test(o.t)));
console.log('버튼:', JSON.stringify(btns,null,0));
console.log('제목:', await page.title());
await page.close(); await b.close();
