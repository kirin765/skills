import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = await b.contexts()[0].newPage();
await page.setViewportSize({width:1440,height:1000});
await page.goto('https://kmong.com/my-gigs/edit/781350?rootCategoryId=6&subCategoryId=667',{waitUntil:'domcontentloaded',timeout:45000});
await page.waitForTimeout(6000);
const steps = await page.evaluate(()=>[...document.querySelectorAll('button,a,li,div')]
  .map(e=>(e.textContent||'').trim()).filter(t=>t && t.length<12 && /가격|패키지|기본정보|서비스 설명|이미지|요청사항|FAQ/.test(t)));
console.log('스텝:', JSON.stringify([...new Set(steps)].slice(0,15)));
const inputs = await page.evaluate(()=>[...document.querySelectorAll('input')]
  .map(i=>({name:i.name||i.id||'', ph:i.placeholder||'', val:i.value||'', type:i.type})).filter(o=>o.val||o.ph));
console.log('입력필드:', JSON.stringify(inputs.slice(0,25),null,0));
await page.screenshot({path:'/tmp/km-edit2.png', clip:{x:0,y:0,width:1440,height:1000}});
await page.close(); await b.close();
