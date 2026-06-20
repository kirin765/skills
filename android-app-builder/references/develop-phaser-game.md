# 개발 — Phaser 게임 (탭/아케이드) → Capacitor

게임 앱의 "개발" 경로. 핵심은 **이미 동작이 검증된 파일을 복사해 적응**시키는 것 — 매번 절차적 오디오 엔진·텍스처 팩토리·상태머신 씬을 백지에서 다시 짜지 않는다(토큰 낭비의 주범). `assets/phaser/`의 파일을 프로젝트 `src/`로 복사하고, 게임 고유 부분(아트·메커니즘·튜닝)만 바꾼다.

## 무엇이 들어있나

`assets/phaser/` (프로젝트 `src/`로 복사):
- **`audio.ts`** — 절차적 Web Audio 효과음 엔진. **게임 무관, 그대로 복사.** 점프/점수(콤보 음정↑)/마일스톤/충돌/스워시/버튼 + 음소거(localStorage). 에셋 파일 0개.
- **`config.ts`** — `GAME_WIDTH/HEIGHT` 등 공유 상수. **반드시 별도 파일로.** 순환 import TDZ 부팅 실패를 막는다(`references/phaser-vite-gotchas.md` §1).
- **`textures.ts`** — 런타임 벡터 아트 팩토리(플래피 예시). 바이너리 에셋 없이 `Graphics`로 새·파이프·언덕·구름·바닥·파티클·메달·아이콘을 찍어낸다. `tex()`/`softCircle()`/`starPoints()`/`toPoints()` 헬퍼는 범용 — 재사용하고 그릴 대상만 교체.
- **`GameScene.ts`** — `ready | playing | dead` 상태머신 씬 템플릿. 패럴랙스·물리·기울기·스폰·점수·난이도곡선·파티클·게임오버 패널·메달·음소거 전부 배선됨. `showGameOver()`에 광고/애널리틱스 통합 지점 주석(§1.5 AdMob 훅 위치).
- **`main.ts`** — `Phaser.Game` 부트스트랩(antialias·FIT 스케일·arcade 중력).
- **`style.css`** — 모바일 풀스크린 캔버스 CSS(`100svh`, `touch-action:none`).

`references/`:
- **`phaser-vite-gotchas.md`** — 실제로 시간을 태운 버그들. **새 게임 시작 전·문제 발생 시 먼저 읽어라.** 순환 import TDZ, Sprite vs Image, `Geom.Point` 부재, 백그라운드 탭 검증 한계 등.
- **`juice-checklist.md`** — "퀄리티 최상"을 만드는 항목 목록 + 구현 위치.

## 표준 흐름

### 1. 스캐폴드
Vite + TS 프로젝트가 없으면 만든다. `package.json` 의존성: `phaser@^4`, devDeps `vite`, `typescript`. 안드로이드까지면 `@capacitor/core`·`@capacitor/cli`·`@capacitor/android`.

`assets/phaser/`의 6개 파일을 복사:
- `audio.ts` `config.ts` `textures.ts` `main.ts` `style.css` → `src/`
- `GameScene.ts` → `src/scenes/`

`index.html`은 viewport에 `viewport-fit=cover, user-scalable=no, maximum-scale=1`, `#game` div, manifest/theme-color(게임 톤).

### 2. 게임 정체성 정의
사용자에게 한 줄로: **무슨 메커니즘**(탭으로 점프? 좌우 회피? 타이밍?), **테마/팔레트**, **목표/점수 방식**. 모호하면 플래피류로 가정하되 확인.

### 3. 적응 (백지 생성 금지 — 교체만)
- **`config.ts`**: 캔버스 크기만 조정(보통 360×640 세로).
- **`textures.ts`**: `tex()`/`softCircle()`/`starPoints()` 헬퍼는 두고, 그리는 대상(`drawBird`, 파이프, 언덕…)을 새 테마로 교체. 팔레트 상수만 바꿔도 분위기가 크게 변한다.
- **`GameScene.ts`**: 메커니즘이 플래피와 다르면 `flap()`·`spawnPipes()`·충돌·`update()`를 교체. 같은 계열이면 튜닝 상수(`FLAP`, `get gap()/pipeSpeed()/spawnDelay()`)만 조정. 상태머신·점수·게임오버·메달·음소거 배선은 **재사용**.
- **`audio.ts`**: 거의 그대로. 필요하면 새 사운드 함수 추가.

### 4. 품질 패스
`references/juice-checklist.md`를 훑고 빠진 연출을 채운다. 단색 배경·평면 도형·무음·즉시 재시작은 미완성 신호.

### 5. 검증 (글로벌 goal-driven 원칙)
`npx tsc --noEmit` → `npm run build` 통과 확인. dev 서버를 띄워 **브라우저에서 실제로** 렌더·물리·점수·게임오버를 확인한다. 프리뷰 탭이 백그라운드면 게임 루프가 멈추니 **`references/phaser-vite-gotchas.md` §4의 검증 기법**(씬 메서드 직접 호출 + `game.step()` 수동 스텝, 트윈은 최종 상태 스냅)을 쓴다. "됐다"고 하기 전에 스크린샷으로 증명.

## Capacitor → 서명 release AAB

게임의 최종 빌드는 Capacitor로 묶는다(네이티브 Kotlin 아님):

```bash
npm run build                    # dist/ 생성
npx cap add android              # 최초 1회
npx cap sync android             # dist → android/app/src/main/assets/public
```

서명·`bundleRelease`는 네이티브와 동일 — 키스토어 생성/서명/AAB 산출 명령은 `references/develop-native-kotlin.md`의 "키스토어·서명 AAB" 절을 그대로 쓴다(Capacitor가 만든 `android/` Gradle 프로젝트에 동일 적용). 산출물 경로 `android/app/build/outputs/bundle/release/app-release.aab`를 기록 — 제출(§3)에서 업로드.

> 에뮬레이터 스크린샷 캡처도 네이티브와 동일(`references/develop-native-kotlin.md`의 "에뮬레이터 스크린샷"). 단, 게임 루프가 백그라운드 탭에서 멈추는 특성 때문에 에뮬레이터 캡처가 웹 캡처보다 신뢰성 높다.
