# 스토어 에셋 생성 스크립트 (재사용)

`playwright`가 프로젝트에 설치돼 있어야 함(`npm i -D playwright` + `npx playwright install chromium`). `tmp/`에 저장(gitignore).

## 스크린샷 (9:16, 1080×1920)

게임 캔버스 좌표는 앱마다 다름. 아래는 Phaser RESIZE 모드(CSS px == game px) 예시. 메뉴 버튼/보드 교차점 좌표는 해당 게임 소스에서 계산.

```js
// tmp/shots.mjs
import { chromium } from 'playwright'
const URL = 'https://<app>.vercel.app/'
const W = 1080, H = 1920
const sleep = (ms) => new Promise(r => setTimeout(r, ms))
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
await page.goto(URL, { waitUntil: 'networkidle' })
await sleep(2500)
await page.screenshot({ path: 'tmp/shot-menu.png' })
// 시작 버튼/게임 진행 클릭 후 추가 캡처 …
await page.mouse.click(W/2, H/2 + 115); await sleep(1500)
// 보드 교차점: origin=(W-min(W*.93,H*.82))/2, spacing=boardPx/14 …
await page.screenshot({ path: 'tmp/shot-game.png' })
await browser.close()
```

요건: PNG/JPEG, 변당 ≤8MB, 비율 16:9 또는 9:16(2:1 초과 금지), 최소변 ≥320, 최대변 ≤3840. 1080×1920 = 정확히 9:16, 안전.

## 폰 프레임 + 카피 스크린샷 (항상 이 형식으로 마감)

위 raw 캡처는 **중간 입력물**(`shots/`)일 뿐. 스토어엔 **스마트폰 목업 프레임 + 헤드라인 카피**를 얹은 마케팅 컷(`framed/`)을 올린다. raw PNG를 base64로 HTML `<img>`에 박고, 그라데이션 배경·헤드라인·서브카피·폰 목업(노치 포함)을 `page.setContent`로 렌더해 `1242×2208`로 캡처. 헤드라인은 `aso-audit` 결과(한국어 기본; 영어판은 텍스트만 교체해 동일 레이아웃 재렌더).

```js
// tmp/render-screens.mjs  — raw shots/ → framed/
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
const SHOTS = 'tmp/shots', OUT = 'tmp/framed', W = 1242, H = 2208
const b64 = f => 'data:image/png;base64,' + readFileSync(`${SHOTS}/${f}`).toString('base64')
const SCREENS = [
  { file: 'home.png',  title: ['위젯에서 1초 만에', '할 일 추가'], sub: '앱을 열 필요 없이 바로' },
  { file: 'list.png',  title: ['핵심 기능', '한눈에'],            sub: '서브 카피 한 줄' },
  // … 2~8장, title/sub는 aso-audit 카피에서
]
const html = (s) => `<!doctype html><meta charset=utf-8><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:${W}px;height:${H}px;font-family:'Apple SD Gothic Neo','Pretendard',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{width:${W}px;height:${H}px;position:relative;overflow:hidden;
 background:radial-gradient(120% 80% at 50% -10%, #6B7BFF 0%, #4C5DF2 42%, #3A45C4 100%)}
.copy{position:absolute;left:0;right:0;top:120px;text-align:center;padding:0 70px}
.title{color:#fff;font-weight:900;font-size:96px;line-height:1.14;letter-spacing:-3px}
.sub{color:#DBE0FF;font-weight:600;font-size:42px;margin-top:28px}
.phone{position:absolute;left:50%;bottom:-150px;transform:translateX(-50%);
 width:780px;background:#0B1020;border-radius:60px;padding:16px;
 box-shadow:0 50px 90px rgba(10,14,40,.45)}
.screen{border-radius:46px;overflow:hidden;background:#fff}
.screen img{width:100%;display:block}
.notch{position:absolute;top:30px;left:50%;transform:translateX(-50%);width:150px;height:30px;background:#0B1020;border-radius:0 0 18px 18px;z-index:2}
</style><div class=wrap>
 <div class=copy><div class=title>${s.title.join('<br>')}</div><div class=sub>${s.sub}</div></div>
 <div class=phone><div class=notch></div><div class=screen><img src="${b64(s.file)}"></div></div>
</div>`
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
for (let i = 0; i < SCREENS.length; i++) {
  await page.setContent(html(SCREENS[i]), { waitUntil: 'load' }); await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/${String(i+1).padStart(2,'0')}.png`, clip: { x:0, y:0, width:W, height:H } })
}
await browser.close()
```

1242×2208 = 9:16, 안전. 색상·폰트는 앱 브랜드에 맞춰 조정. 위젯 중심 앱이면 위젯 배치 화면도 한 컷 포함.

## 피처그래픽 1024×500

```js
// tmp/feature.mjs
import { chromium } from 'playwright'
const html = `<!doctype html><html><head><meta charset=utf-8><style>
*{margin:0;box-sizing:border-box} body{width:1024px;height:500px;overflow:hidden;
font-family:'Apple SD Gothic Neo',sans-serif;
background:linear-gradient(135deg,#d9b074,#b3823f);position:relative}
.t{position:absolute;left:70px;top:50%;transform:translateY(-50%)}
.title{font-size:96px;font-weight:bold;color:#2e1f13}
.sub{font-size:30px;color:#43301b}
</style></head><body><div class=t>
<div class=title>앱 이름</div><div class=sub>한 줄 소개</div>
</div></body></html>`
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1024, height: 500 }, deviceScaleFactor: 1 })
await p.setContent(html, { waitUntil: 'networkidle' })
await p.screenshot({ path: 'tmp/feature-graphic.png' })
await b.close()
```

## 개인정보처리방침 (public/privacy.html → 배포)

핵심 문구(데이터 수집 없는 오프라인 앱):
- 수집하는 개인정보: 없음. 기기 내 단독 작동.
- 로컬 저장소: 게임상태/설정만 기기에 저장, 외부 전송 없음.
- 제3자 제공·광고·분석: 없음.
- 아동: 만 13세 이상 대상.
- 문의: <이메일>.
- 영문 단락 1개 병기 권장.

Vite면 `public/`에 두면 `/<파일>.html`로 서빙. 배포 후 `curl -s -o /dev/null -w "%{http_code}"`로 200 확인.

## 아이콘 512px

**런처 아이콘과 반드시 같은 소스에서 뽑는다** — `references/app-icon.md`의 단일 소스 규칙. PWA 아이콘이나 별도 제작 아이콘을 스토어에만 쓰면 앱에 설치된 런처 아이콘과 갈려 "스토어 등록정보 불일치"로 반려된다.
```bash
sips -z 512 512 assets/icon.png --out ~/Downloads/<app>-store-assets/icon-512.png
```
