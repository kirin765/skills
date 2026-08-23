# SDK 연동 노트 — @apps-in-toss/web-framework

검증된 실구현 패턴(운영 중 미니앱 코드 기준) + 공식 API 문서 요약. SDK 버전은 패키지로 관리(`@apps-in-toss/web-framework`, `ait` CLI 포함).

## 설치 · 빌드

```bash
npm i @apps-in-toss/web-framework
```

- `apps-in-toss.config.ts` (프로젝트 루트):

```ts
import { defineConfig } from '@apps-in-toss/web-framework/config'

export default defineConfig({
  appName: 'my-app',            // 필수. intoss:// 스킴 ID (콘솔과 일치해야 함)
  brand: { primaryColor: '#08d9d6' },
  permissions: [],              // clipboard/geolocation/contacts/photos/camera/microphone
  webView: {
    allowsInlineMediaPlayback: true,
    overScrollMode: 'never',
    mediaPlaybackRequiresUserAction: true,
  },
  webBundleDir: 'dist',         // 웹빌드 결과 디렉터리
})
```

- 빌드(웹뷰 프로젝트): vite 빌드 후 `ait.js`가 패키징.

```jsonc
// package.json
"scripts": {
  "build:ait": "npm run build && node node_modules/@apps-in-toss/web-framework/bin/ait.js build"
}
```

- 산출물: `<서비스명>.ait` = zip(`sources/**` + `bundle.json` + `project-package.json`). `bundle.json`에 deploymentId·config·SDK 버전이 들어간다. 압축 해제 기준 100MB 이하.
- **vite는 `base: './'` 권장**(서브패스 서빙 대응). iframe·SSR 금지.

## 실행 환경 감지 — 토스 밖에서 전부 no-op 처리

```ts
import { getOperationalEnvironment } from '@apps-in-toss/web-framework'
// 'toss' | 'sandbox' | 그 외(브라우저 등)
export function isInToss() {
  try { const e = getOperationalEnvironment(); return e === 'toss' || e === 'sandbox' } catch { return false }
}
```

모든 브릿지 API는 `isSupported()` 존재 여부·호출 가능 여부를 먼저 확인하고, 미지원/비토스 환경에선 조용히 실패(false) 반환하도록 감싼다. 하트 등 로컬 상태는 `localStorage`(키: `neonswitch.hearts` 식), 지급 멱등성은 `neonswitch.granted.<orderId>` 키로.

## 인앱 결제 (IAP)

```ts
import { IAP } from '@apps-in-toss/web-framework'

IAP.createOneTimePurchaseOrder({
  options: {
    sku: 'heart_5',                       // 콘솔에 등록한 SKU
    processProductGrant: ({ orderId }) => {
      // orderId 키로 멱등 지급 (재호출·중복 결제 방지)
      if (!localStorage.getItem('granted.' + orderId)) {
        localStorage.setItem('granted.' + orderId, '1')
        grantHearts(50)
      }
      return true
    },
  },
  onEvent: (event) => { if (event.type === 'success') /* 완료 처리 */ },
  onError: (error) => { /* code: 'USER_CANCELED' 등 */ },
})
```

- 결제 시트가 열린 상태에서 호스트가 조용히 실패하는 경우를 대비해 타임아웃(예: 30초)으로 해제.
- 결제 진행 중 앱 음악·영상 일시정지(출시 가이드 의무).
- 서버 검증(토큰·승인)이 필요하면 서버 API(mTLS + 결제 상태 조회) 사용 — SDK만으로는 부족할 수 있다.

## 인앱 광고 (전면/리워드 — v3 우선, v2 폴백)

광고 타입은 **adGroupId로 자동 결정**. `load → show → (다음 load)` 순서, 프리로드 후 show.

```ts
import { loadFullScreenAd, showFullScreenAd, GoogleAdMob } from '@apps-in-toss/web-framework'

// v3 (권장): 광고 2.0 ver2, 토스 앱 5.247.0+
if (loadFullScreenAd.isSupported?.() && showFullScreenAd.isSupported?.()) {
  loadFullScreenAd({ options: { adGroupId: GROUP }, onEvent(e) { if (e.type === 'loaded') /* show 준비 */ }, onError })
  showFullScreenAd({ options: { adGroupId: GROUP }, onEvent(e) { /* 'userEarnedReward'(리워드) / 'dismissed' / 'failedToShow' */ }, onError })
}
// v2 폴백: GoogleAdMob.loadAppsInTossAdMob / showAppsInTossAdMob (같은 파라미터 형태)
```

- 같은 adGroupId 기준 프리로드는 한 번에 1개. 여러 그룹이면 그룹별로 1개씩.
- 리워드 보상은 `userEarnedReward` 이벤트에서만 지급. 전면은 dismissed/failedToShow에서 종료.
- 미리 로드해 두고, show 후 다음 로드(load → show → load → show).
- iOS 광고 미로드 시 App Tracking Transparency(앱 추적 권한) 확인.
- 샌드박스에서는 인앱 광고 불가 → 콘솔 QR 테스트 + 테스트용 ID만.

## 배너 (WebView)

```ts
import { TossAds } from '@apps-in-toss/web-framework'

await new Promise((res, rej) => TossAds.initialize({ callbacks: { onInitialized: res, onInitializationFailed: rej } }))
const handle = TossAds.attachBanner(BANNER_AD_GROUP_ID, container, {
  theme: 'dark', variant: 'expanded',
  callbacks: { onAdFailedToRender: () => {}, onNoFill: () => {} },
})
// container: 하단 고정 div (position:fixed; bottom:0; height:96px)
handle.destroy() // 해제
```

- 배너는 상단 또는 하단 고정만 허용. 배너 ID는 테스트 시 `ait-ad-test-banner-id`(리스트형).

## 혜택탭 프로모션 (토스 포인트 지급 — 유입·리텐션 도구)

```ts
import { Promotion } from '@apps-in-toss/web-framework'
await Promotion.grantReward({ promotionCode: code, amount: 500 }) // code는 env에서(VITE_PROMOTION_CODE)
```

- 프로모션 코드: 운영 코드(콘솔 발급) vs 테스트 코드(TEST_... = 샌드박스 전용) 구분. 실제 지급하려면 운영 코드로 교체·재배포.
- 콘솔: 혜택탭 프로모션 등록(예산·기간) → '혜택' 탭 노출(미니앱 최대 유입 지면). 세그먼트(성별·연령·지역·통신사·OS·거래·활동 조건 조합)로 푸시/광고 타게팅.
- 푸시 문구는 creative-review API로 사전 검증(문구 심사 — 명령형·임의 축약 거부되는 경우가 많아 '명사형~하기' 형태 권장).

## 공유 (바이럴)

```ts
import { Share } from '@apps-in-toss/web-framework'
const link = await Share.createLink({ path: 'intoss://my-app', ogImageUrl: 'https://공개-https-절대주소/og.png' })
await Share.sendMessage({ message: link })
```

- OG 이미지는 **공개 https 절대 URL**이어야 외부 플랫폼(카카오 등)이 가져갈 수 있음(GitHub raw 등).
- `intoss://` 딥링크는 정식 출시 후에만 접근 가능 — 출시 전 테스트는 테스트 스킴(`intoss-private://` + `_deploymentId`).

## .ait 배포 (CI/CD)

```bash
npx ait token add                 # 콘솔 '키' 메뉴에서 발급한 API 키 1회 등록(로컬 토큰 저장)
npx ait deploy -m "출시 메모"      # 번들 업로드 → 테스트 스킴 반환
```

- 콘솔 업로드 시: 버전 탭 → .ait 파일 업로드 → '테스트하기' QR. **검토 요청은 테스트 1회 완료 후 활성화**.

## 실측 게이트 규칙 (베팅 원장 기준 — 이 스킬을 게이트에 쓸 때)

- 결제 게이트(예: 2주 내 IAP·토스페이 결제 <1만원 = KILL)라면: 분모(혜택탭 프로모션 1회 + 세그먼트 푸시)를 **집행 전에** 기록하고, 판정은 결제 발생액으로만. 가입·설치·관심은 착시.
- IAA(인앱광고)는 익월 말 정산이라 단기 게이트에 실측 불가 — 게이트 숫자로 쓰지 말 것.
- 유입 0 = 채널 사망(오퍼 손대지 말고 채널 바꾸기), 유입 있고 결제 0 = 오퍼 사망(채널 바꾸지 말고 오퍼 바꾸기). 둘을 동시에 바꾸지 않는다.
- 광고 그룹별 노출·eCPM·수익은 콘솔 분석에서 각각 집계되므로 광고 성과와 IAP 결제를 한 숫자로 섞지 않는다.