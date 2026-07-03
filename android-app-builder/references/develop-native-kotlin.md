# 네이티브 Kotlin — 빌드·서명·에뮬레이터 캡처

이 문서는 네이티브 안드로이드 빌드 공백만 담는다. 스토어 등록·검토 제출은 `references/play-submit.md`, 스크린샷 합성은 `references/asset-scripts.md`를 쓴다.

## 전제 도구

- Android Studio + Android SDK (`$ANDROID_HOME` 또는 `~/Library/Android/sdk`)
- `adb`, `emulator`, `sdkmanager`, `avdmanager`가 PATH 또는 `$ANDROID_HOME/platform-tools`·`/emulator`에 있음
- JDK 17+ (AGP 8.x 요구)

도구가 없으면 추측해서 헤매지 말고 사용자에게 Android Studio 설치/SDK 경로를 확인한다.

## 프로젝트 스캐폴드

기본은 **Jetpack Compose + 단일 모듈**. MVP에 멀티모듈·과한 아키텍처는 넣지 않는다(범위 최소).

- 빌드 시스템: Gradle (Kotlin DSL, `build.gradle.kts`)
- 최소 SDK: `minSdk 24` 정도(현실적 커버리지), `targetSdk`는 최신 안정
- UI: Compose, `MaterialTheme`
- 상태: `ViewModel` + `StateFlow`. 로컬 저장이 필요하면 DataStore(설정) 또는 Room(구조적 데이터)

새 프로젝트가 비었으면 Android Studio 템플릿 대신 Gradle로 직접 스캐폴드해도 된다. 핵심은 `./gradlew assembleDebug`가 통과하는 최소 골격에서 시작해 기능을 goal 단위로 붙이는 것.

## 테스트 (goal 검증용)

- **JVM 단위 테스트** (`src/test/`): ViewModel·repository·유스케이스 등 순수 로직. 빠르고 결정적 — goal 루프의 주력. `./gradlew test`.
- **계측 테스트** (`src/androidTest/`, Espresso/Compose UI test): 에뮬레이터 필요, 느림. MVP에선 핵심 사용자 플로우 1~2개만. `./gradlew connectedAndroidTest`.

"기능 X 추가" → 먼저 실패하는 단위 테스트 → 통과시키기 → 에뮬레이터에서 손으로 확인.

## 에뮬레이터 띄우기

```bash
# AVD 목록
$ANDROID_HOME/emulator/emulator -list-avds
# 없으면 생성 (예: Pixel 7, API 34)
$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd -n pixel7_api34 \
  -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_7
# 부팅 (백그라운드)
$ANDROID_HOME/emulator/emulator -avd pixel7_api34 -no-snapshot -netdelay none -netspeed full &
# 부팅 완료 대기
adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done'
# 디버그 빌드 설치·실행
./gradlew installDebug
adb shell monkey -p <packageName> -c android.intent.category.LAUNCHER 1
```

## 서명된 release AAB

업로드 키스토어가 필요하다. **키스토어 비밀번호·별칭은 사용자 자산** — 새로 만들면 사용자에게 값을 받거나 사용자가 만들게 하고, **키스토어 파일·비밀번호를 git에 커밋하지 않는다**(`.gitignore`, `local.properties` 또는 환경변수).

키스토어 생성(사용자 동의 후):
```bash
keytool -genkeypair -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 9125 \
  -alias upload
# 비밀번호·별칭은 사용자 입력
```

**런처 아이콘(필수 — 안 하면 스토어 불일치 반려):** `bundleRelease` 전에 스캐폴드 기본 `ic_launcher`를 `assets/icon.png`(1024)에서 생성한 실제 아이콘으로 덮어쓴다. `references/app-icon.md`의 "네이티브 Kotlin" 절(밀도 PNG + adaptive `mipmap-anydpi-v26` 처리)을 따른다. 스토어 512도 같은 소스에서 뽑는다.

`app/build.gradle.kts`에 `signingConfigs.release`를 `local.properties`/환경변수에서 읽게 연결한 뒤:
```bash
./gradlew bundleRelease
# 산출물: app/build/outputs/bundle/release/app-release.aab
```
이 AAB 경로를 3단계(`references/play-submit.md`) 업로드에 넘긴다.

> Play의 **앱 서명(Play App Signing)**을 쓰면 업로드 키만 있으면 된다(권장). 업로드 키 분실 대비해 사용자에게 안전 보관을 안내한다.

## 에뮬레이터 스크린샷 (2단계 raw 캡처)

각 핵심 화면을 띄운 상태에서 픽셀 직접 추출(상태바 포함이 싫으면 앱을 immersive로 캡처):

```bash
mkdir -p tmp/shots
# 원하는 화면으로 네비게이션(adb로 탭/입력하거나 손으로 이동) 후:
adb exec-out screencap -p > tmp/shots/home.png
# 다음 화면으로 이동 후 반복
adb exec-out screencap -p > tmp/shots/list.png
```

해상도가 1080×1920(9:16)이 아니면, 9:16 비율의 에뮬레이터(예: Pixel 7은 1080×2400)를 쓰거나 캡처를 1080×1920으로 크롭/리사이즈한다. Play 요건: PNG/JPEG, 비율 9:16 또는 16:9(2:1 초과 금지), 최소변 ≥320, 최대변 ≤3840.

이렇게 모은 `tmp/shots/*.png`를 `references/asset-scripts.md`의 "폰 프레임 + 카피" 합성 스크립트에 그대로 입력하면 최종 `framed/` 마케팅 컷이 나온다. 합성 스크립트는 raw PNG를 base64로 박을 뿐 소스가 웹인지 네이티브인지 가리지 않으므로 그대로 재사용된다.
