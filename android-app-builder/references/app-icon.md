# 앱 아이콘 — 런처 아이콘 = 스토어 512 (단일 소스 규칙)

**왜 이 문서가 있나 (반려 재발 방지):** 앱에 설치되는 **런처 아이콘**(AAB 안 `mipmap/ic_launcher*`)이 스토어 등록정보의 **512 아이콘**과 다르면 Google이 **"혼동을 야기하는 주장 — 앱 스토어 등록정보 불일치"**로 반려한다("설치된 아이콘 또는 이름이 스토어 등록정보와 다릅니다"). 스캐폴드가 남긴 **기본 템플릿 아이콘**(Capacitor/Android 템플릿의 X·별 모양)을 안 바꾸고 스토어엔 예쁜 512만 올리면 정확히 이 반려가 난다. 실제로 컬러 메모리가 이걸로 두 번 반려됐다.

**철칙: 런처 아이콘과 스토어 512는 반드시 하나의 소스에서 파생한다. 별도로 만들지 않는다.**

## 소스 1장 (유일한 진실)

`assets/icon.png` — **1024×1024, 정사각형, 불투명 배경**(투명 금지). 스토어 512도 런처도 전부 여기서 파생한다. 앱 정체성이 담긴 최종 아이콘 아트를 여기에 둔다.

> adaptive 아이콘은 바깥 ~25%가 마스킹되니, 핵심 그래픽은 가운데 안전영역 안에 둔다.

## 런처 아이콘 생성 — 경로별

### Capacitor(게임) — `@capacitor/assets`
```bash
npm i -D @capacitor/assets
# assets/icon.png (1024, 불투명) 준비 후:
npx @capacitor/assets generate --android
npx cap sync android
```
→ `android/app/src/main/res/mipmap-*/`의 모든 밀도 + adaptive(`ic_launcher_foreground`/배경 + `mipmap-anydpi-v26/ic_launcher.xml`)를 소스에서 덮어쓴다. 기본 템플릿 아이콘이 이 시점에 사라진다.

### 네이티브 Kotlin — 밀도 PNG
```bash
SRC=assets/icon.png
for d in mdpi:48 hdpi:72 xhdpi:96 xxhdpi:144 xxxhdpi:192; do
  n=${d%%:*}; s=${d##*:}
  mkdir -p app/src/main/res/mipmap-$n
  sips -z $s $s "$SRC" --out app/src/main/res/mipmap-$n/ic_launcher.png >/dev/null
  sips -z $s $s "$SRC" --out app/src/main/res/mipmap-$n/ic_launcher_round.png >/dev/null
done
```
> **함정 — adaptive 아이콘 우선순위:** `app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`이 있으면 API 26+에서 위 PNG 대신 그 XML(foreground 드로어블 + 배경)이 뜬다. 이 파일이 있으면 XML이 참조하는 `ic_launcher_foreground` 드로어블도 소스로 교체하거나, adaptive를 안 쓸 거면 `mipmap-anydpi-v26/`를 지워 PNG를 진실로 만든다. **둘 중 하나를 반드시 처리** — 안 하면 PNG만 바꾸고 실기기엔 옛 템플릿이 뜨는 이번 반려가 그대로 재발한다.

## 스토어 512 (같은 소스에서)
```bash
sips -z 512 512 assets/icon.png --out ~/Downloads/<app>-store-assets/icon-512.png
```
(§2 asset-scripts.md의 "아이콘 512" 대체 — PWA 아이콘 재사용 금지, 반드시 이 소스에서.)

## 검증 게이트 — 제출 전 필수 (backstop)

단일 소스로 만들었어도, **release AAB에 실제로 들어간 런처 아이콘을 꺼내 스토어 512와 같은 그림인지 눈으로 대조**한 뒤에만 제출한다.

```bash
AAB=android/app/build/outputs/bundle/release/app-release.aab   # 네이티브면 app/build/...
rm -rf /tmp/icocheck && unzip -o "$AAB" -d /tmp/icocheck 'base/res/mipmap*/*' >/dev/null
ls -l /tmp/icocheck/base/res/mipmap*/
```
그다음 **가장 큰 `ic_launcher*.png`(보통 xxxhdpi)를 `Read`로 열고, `~/Downloads/<app>-store-assets/icon-512.png`도 `Read`로 열어 같은 아트인지 확인**한다.
- 같은 그림 → 통과, 제출 진행.
- 다르거나 AAB에 X·별 같은 템플릿 아이콘이 보이면 → **제출 금지.** 위 생성 단계를 다시 하고 AAB를 재빌드한다.

기존 앱 업데이트 때도 아이콘 512를 새로 올리면 이 게이트를 똑같이 통과해야 한다.
