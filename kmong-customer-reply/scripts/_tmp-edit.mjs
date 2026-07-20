import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = await b.contexts()[0].newPage();
await page.setViewportSize({width:1440,height:1000});
await page.goto('https://kmong.com/my-gigs/edit/781350?rootCategoryId=6&subCategoryId=667',{waitUntil:'domcontentloaded',timeout:45000});
await page.waitForTimeout(6000);
const f = page.locator('input[type="text"]').filter({hasNot:page.locator('[placeholder]')}).first();
const target = page.locator('input').nth(1);           // 200,000 필드
await target.scrollIntoViewIfNeeded();
await target.click({clickCount:3});
await page.keyboard.press('Meta+A');
await page.keyboard.type('9900', {delay:60});
await page.waitForTimeout(2500);
const after = await page.evaluate(()=>[...document.querySelectorAll('input')].slice(0,4).map(i=>i.value));
console.log('입력 후 가격 필드:', JSON.stringify(after));
const err = await page.evaluate(()=>document.body.innerText.split('\n').filter(l=>/최소|이상|오류|입력해|원 이상|불가/.test(l)).slice(0,8));
console.log('검증 메시지:', JSON.stringify(err,null,0));
const save = await page.evaluate(()=>[...document.querySelectorAll('button')].map(e=>(e.textContent||'').trim()).filter(t=>/저장|등록|수정 완료|제출|심사/.test(t)));
console.log('저장 버튼:', JSON.stringify(save));
await page.screenshot({path:'/tmp/km-price.png', clip:{x:400,y:100,width:1040,height:800}});
await page.close(); await b.close();   // 저장 안 함
