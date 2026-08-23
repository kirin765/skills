# Phaser 4 + Vite + Capacitor — 함정 모음

실제로 디버깅에 시간을 태운 것들. 처음부터 피하면 토큰을 크게 아낀다.

## 1. 순환 import → TDZ로 부팅 실패 (가장 비쌌던 버그)

**증상:** 캔버스가 아예 안 생김. `#game` div가 0×0. 콘솔 에러도 안 잡히는데 `window.game`이 Phaser 객체가 아니라 `<div id="game">` 엘리먼트임(브라우저가 id로 전역을 만듦 → 할당이 안 됐다는 신호).

**원인:** `GAME_WIDTH/HEIGHT`를 `main.ts`에서 export하고, `GameScene`/`textures`가 `main`에서 import하면 순환 참조가 된다. 모듈 **최상위**에서 그 상수를 쓰면(`const PLAY_BOTTOM = GAME_HEIGHT - GROUND_H`) `main`이 아직 초기화 전이라 `Cannot access 'GAME_HEIGHT' before initialization`로 죽는다. (메서드 안에서만 쓰면 런타임이라 안 터져서 놓치기 쉽다.)

**해결:** 공유 상수는 **의존성 없는 `config.ts`**에 둔다. `main`·`GameScene`·`textures` 모두 `config`에서 import. 이게 `assets/config.ts`가 따로 있는 이유다. 절대 상수를 `main.ts`에 두지 말 것.

## 2. 애니메이션 = Sprite, Image 아님

`this.anims.play('flap')`를 쓰려면 `this.physics.add.sprite(...)`로 만들어야 한다. `physics.add.image`는 `play`/`stop`이 없어서 `Property 'play' does not exist` 컴파일 에러. 타입은 `SpriteWithDynamicBody`.

## 3. `Phaser.Geom.Point`는 Phaser 4에서 생성자가 아님

`new Phaser.Geom.Point(x,y)` → 타입 에러(`POINT` 상수와 혼동). `graphics.fillPoints(...)`에 넘길 점 배열은 `new Phaser.Math.Vector2(x, y)`로 만든다.

## 4. 백그라운드 탭 프리뷰의 검증 한계 (중요)

프리뷰 탭이 포커스를 안 받으면 `requestAnimationFrame`이 멈춰서 게임 루프가 안 돈다. 따라서:

- **합성 PointerEvent(`dispatchEvent`)는 Phaser 입력에 안 들어간다.** 입력 검증은 씬 메서드를 직접 호출(`scene['onTap'].call(scene)`)로.
- **`game.step(time, delta)`를 수동 호출**하면 Arcade 물리와 `scene.update()`는 전진한다(새 위치·각도·파이프 이동·충돌·점수 확인 가능). **하지만 TweenManager는 전진하지 않는다**(실제 rAF 시계에 묶여 있음). 그래서 트윈 기반 연출(타이틀 페이드, 사망 낙하 트윈→`showGameOver`, 점수 팝, 패널 등장)은 수동 스텝으로 안 보인다 — 게임 버그가 아니라 하네스 한계다.
- **트윈 연출 스크린샷이 필요하면**: 해당 메서드를 직접 호출하고(`scene['showGameOver'].call(scene)`), 등장 트윈의 최종 상태로 스냅(`container.setScale(1)`)한 뒤 캡처.
- 점수 검증: 오토파일럿으로 갭 중앙을 노려도 FLAP 임펄스가 세서 잘 못 통과한다. 점수 로직 자체는 `pair.top.x < bird.x` 한 줄이라, 1점이라도 올라가면 동작 확인으로 충분.

이 절차를 알면 "왜 화면이 안 변하지"로 왕복하지 않는다.

## 5. 충돌 박스 정렬

원형 히트박스는 `sprite.setCircle(r, offsetX, offsetY)`. offset은 프레임 좌상단 기준 원의 좌상단 = `(몸통중심 - r)`. 텍스처 48×40에 몸통중심 (20,20), r=15면 `setCircle(15, 5, 5)`.

## 6. 파이프는 풀하이트 바디 + 별도 캡

바디 텍스처를 화면 전체 높이로 만들고 origin을 갭 모서리에 두고(상단 `(0.5,1)`, 하단 `(0.5,0)`) 세로로 늘린다. 그라데이션을 **가로 방향**으로 그리면 세로 stretch에도 안 깨진다. 캡은 약간 넓은 별도 스프라이트로 갭 입구에 얹고 같은 속도를 준다. 둘 다 overlap 그룹에 넣어 충돌.

## 7. 월드 바운드로 바닥만 사망 처리

`physics.world.setBounds(0, 0, W, H - GROUND_H)` + `bird.setCollideWorldBounds(true)` + `onWorldBounds`. 핸들러에서 `down`일 때만 `die()` — 천장은 막되 즉사 안 함(클래식 플래피 느낌).

## 8. Capacitor/모바일 셋업

- `index.html` viewport: `width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover`
- CSS: `#game { height: 100svh }`, `#game canvas { touch-action: none }`, `body { overscroll-behavior: none }`
- Phaser scale: `mode: FIT, autoCenter: CENTER_BOTH` — 어떤 비율에서도 레터박스로 중앙 정렬
- `manifest.json`/`theme-color`는 하늘색 등 게임 톤과 맞춤

## 9. 번들 경고는 정상

`vite build`가 "chunks larger than 500 kB"를 경고하지만 Phaser가 원래 ~357kB(gzip)다. 코드 스플리팅 불필요 — 무시해도 됨.
