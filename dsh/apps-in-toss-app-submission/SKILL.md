---
name: apps-in-toss-app-submission
description: >-
  Submit an existing web app to Toss's Apps in Toss (앱인토스) platform as a
  mini-app: SDK 3 .ait build, console registration form data, console asset
  specs, game rating/GRAC code lookup behind a mandatory step, and the
  sandbox/QR test + publish flow. Use when the user mentions "App in Toss",
  "apps in toss", "앱인토스", ".ait", "ait build", "앱인토스 제출/등록", or
  submitting/publishing a game app to Toss. NOTE: App In Toss is a PUBLISHING
  PLATFORM (Toss mini-app marketplace) — it is NOT a UI design style. Never
  restyle the app to a "Toss fintech" look. Target users are Korean: the app UI
  must stay Korean.
---

# Apps in Toss (앱인토스) App Submission Skill

## Critical first rule

"App In Toss" = a **platform** — you publish your EXISTING app inside the Toss
app as a mini-app. It is **NOT** a UI design style. Never restyle the app into a
"Toss fintech" look (white/#3182F6) unless the user explicitly asks for both.
The deliverables are a packaged build (`.ait`) and console submission
preparation.

**Target users are Korean: keep the app UI Korean.** (`lang="ko"`, Korean menu,
buttons and user-facing text, PWA manifest `lang: "ko"`.)

## 1. Understand the request

- "앱인토스 버전", "App In Toss build", "submit this app to App in Toss",
  ".ait" → package the existing web app for the Apps in Toss platform.
- Confirm with the user: app name, `appName` (unique ID), build tooling (Vite
  etc.), and game / non-game type.

## 2. Build the `.ait` artifact (SDK 3)

```sh
npm i -D @apps-in-toss/web-framework @apps-in-toss/cli
```

Create `apps-in-toss.config.ts` at the project root:

```ts
import { defineConfig, type AppsInTossConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: '<unique-ascii-id>', // 고유 ID: immutable after console registration; must match console exactly
  brand: { primaryColor: '#...' },
  permissions: [],              // clipboard/geolocation/contacts/photos/camera/microphone
  webView: {
    bounces: false,
    pullToRefreshEnabled: false,
    overScrollMode: 'never',
    allowsBackForwardNavigationGestures: false,
    allowsInlineMediaPlayback: true,
  },
  webBundleDir: 'dist',         // built web bundle (must contain index.html)
});
```

Scripts: `"ait:build": "ait build"`, `"build:ait": "vite build && ait build"`.
Output: `<appName>.ait` (AITBUNDL container: `sources/*`, `bundle.json`,
`project-package.json`). Verify: `unzip -p <appName>.ait bundle.json` →
`config.appName` must match. Add `*.ait` to `.gitignore`. SDK 3 release is
irreversible (no rollback to SDK 2).

## 3. Console registration form — required fields

| field | rules |
|---|---|
| App intro (어떤 앱을 만들고 싶나요?) | wizard's one-sentence app description (e.g., "매일 돌을 쌓으며 소원을 비는 게임"); used to check publishability — keep the same tone as subtitle/detailed description. 오목 대결: `AI와 두뇌 대결을 즐기는 클래식 오목 게임` |
| Korean app name | ≤10 chars; editable later |
| English app name | ≤15 chars; easy-to-pronounce noun; no commands/verb phrases |
| appName | unique ID · immutable · exact match with config · decides deep link `intoss://{appName}` |
| Subtitle (부제) | ≤20 chars; concrete user value; no slang/exclamation marks |
| Detailed description | what the user SEES → presses → experiences; for games include "게임머니·베팅·결제 없는 AI 1:1" (no game money/betting/payments, AI 1:1) |
| App type | game (게임) / non-game (비게임) |
| Category (카테고리) | '게임 앱' 선택 → 오목 장르에 맞는 게임 카테고리 선택 (보드/전략 계열). 실제 서비스와 다르면 검토 과정에서 조정됨 |
| Web board game flag | 온라인 보드·전략 게임(체스·장기·오목 등)이면 **웹보드 여부 체크** — **보드게임은 '스토어 링크' 경로 불허** (GRAC 증명서 경로 필수) |
| Usage age | 전체이용가 etc. — must match the GRAC 이용등급 later |

## 4. Console assets — exact specs

| asset | spec |
|---|---|
| App logo | 600×600 PNG · square · **no rounded corners** · opaque background required |
| Dark-mode logo | 600×600 PNG · same rules · dark background (outline dark elements) |
| Thumbnail | 1932×828 image |
| Screenshots (vertical) | at least 3 · 636×1048 · PNG |
| Screenshots (horizontal) | at least 1 · 1504×741 · PNG |
| Search keywords | Korean + English terms (name, genre, romanization) |

## 5. Game rating — the GRAC code is a blocker. FIND IT.

- All games require GRAC (게임물관리위원회) rating classification. Google
  Play/App Store IARC ratings are NOT valid in Korea on their own.
- **Board games (webboard)**: the console's '스토어 링크' route is **rejected** →
  the only valid path is GRAC formal rating review → **게임물 등급분류증명서 PDF**.
- **Always look up the GRAC code (등급분류번호) — mandatory agent step:**
  1. Self-rate lookup: <https://www.grac.or.kr/Statistics/SelfRateGameStatistics.aspx>
     ASP.NET WebForms — GET, extract `__VIEWSTATE`, keep cookies + Referer,
     POST with `__EVENTTARGET=ctl00$ContentHolder$lbtnSearch`
     (fields: `ctl00$ContentHolder$tbGameTitle` 게임물명 / `tbRatingNbr` / `ddlGrade`).
  2. Rated-games lookup: <https://www.grac.or.kr/Statistics/GameStatistics.aspx>
     (fields: `ctl00$ContentHolder$txtGameTitle` / `txtRatingNbr` / `txtEntName`).
  3. Code formats: `GC-CC-NP-YYMMDD-###`, `SC-OM-YYMMDD-###`, `CC-NP-YYMMDD-###`.
  4. 0 results = not registered → guide GRAC rating application (review takes
     ~10–15 days; 청소년이용가-games can use the '간소화 신청' simplified path).
     Fee = base price × usage-type coefficient × genre coefficient × localization
     coefficient (mobile (open-market excluded) 60,000 KRW base, board genre 3군
     ×1.5, NON-network ×1.0, Korean ×1.0 → 90,000 KRW; **individual-made games
     get 50% off → 45,000 KRW**).
- Console game-rating step: attach the certificate PDF + fill the
  자체등록분류 게임물 정보 EXACTLY as on the certificate (등록자명 /
  등급분류일자 / 등급분류번호 / 이용등급 / 내용정보). Mismatch of
  registered-name vs business-name → rejected (individual: write explanation /
  business: submit registry document).

## 6. Test & publish

- Sandbox: `intoss://<appName>` · Release QR: `intoss-private://<appName>`
  (scan inside the Toss app)
- If there is a backend, allow CORS: `https://<appName>.web.tossmini.com` +
  `https://<appName>.private-web.tossmini.com`
- Order: `ait build` → upload to console → full-flow QR test → publish.

## 7. Reference implementation (this repo: 오목 대결)

- Console form values: Korean name `오목 대결` · English name `Omok Duel` ·
  appName `omok-daegyeol` · subtitle `AI와 두뇌 대결을 즐기는 오목` ·
  usage age `전체이용가` · type `게임`
- Docs: `docs/apps-in-toss-submission.md`, `docs/grac/README.md`,
  `docs/grac/query-grac.py` (GRAC re-check script),
  `docs/grac/console-rating-checklist.md`, `docs/grac/grac-rating-application.md`,
  `docs/apps-in-toss-caution-compliance.md`
- Assets: `promo/ait-assets/` (app-icon-600.png, app-icon-dark-600.png,
  thumbnail-1932x828.png, screenshot-1..4)
- Scripts: `tmp/capture-ait-assets.mjs`, `tmp/smoke-ait.mjs`

## Ready-to-paste prompt (give this to any AI agent)

> 기존 웹 앱을 **앱인토스(App in Toss)**에 제출하려고 해. App In Toss는 UI
> 디자인 스타일이 아니라 **토스 미니앱 게시 플랫폼**이야. 앱 디자인을 바꾸지 말고
> 아래를 진행해줘: ① `apps-in-toss.config.ts` 작성·확인 후 `npm run build:ait`로
> `{appName}.ait` 생성 ② 콘솔 등록 폼 데이터(한국어/영어 앱 이름, appName, 부제,
> 상세 설명, 사용 연령, 앱 유형, 웹보드 여부) ③ 규격 자산(아이콘 600×600 불투명
> 정사각형, 다크 로고 600×600, 썸네일 1932×828, 스크린샷 세로 636×1048×3 +
> 가로 1504×741) ④ **GRAC 등급분류번호(등급분류번호)를 반드시 조회** — GRAC
> 자체등급분류·등급분류결정 조회 페이지에서 게임물명으로 검색, 없으면 GRAC 심의
> 신청 절차 안내 ⑤ 출시 전 샌드박스/QR 테스트 절차 안내.

## Do NOT

- Never restyle the app UI into a "Toss fintech" design.
- Never skip the GRAC code / certificate step (store IARC does not replace it).
- Never change `appName` after console registration.
- Never use the '스토어 링크' route for board games.
- Never anglicize the app UI — target users are Korean, UI stays Korean.