# Google Cloud / Play / AdMob 셋업 — claude-for-android (1회, 앱 무관)

업로드·읽기·AdMob API의 인증 기반을 만든다. **dev 계정·GCP 프로젝트 단일화:** 전부 `happylife2080100@gmail.com` 로그인 + GCP 프로젝트 **`claude-for-android`**.

> **authuser 인덱스 주의:** URL의 `authuser=N`(Cloud) / `/u/N/`(Play)의 N은 **Chrome 프로필마다 다르다** — 계정을 못 찾으면 헌팅 금지. "사용자가 사용하는 chrome"에서 happylife2080100 = **authuser=5**(2026-06 실증). authuser=1은 다른 계정(heungmiloungwahagsangsig)이었음. 먼저 아무 Cloud Console 페이지를 열어 아바타/계정 선택기로 happylife2080100을 고르면 올바른 N이 URL에 박힌다.

> dev *계정*(Play/AdMob 로그인 신원)과 GCP *프로젝트*(API 호출 로봇=서비스 계정)는 별개다. 이 셋업은 로봇을 `claude-for-android`에 만들고 Play Console에 연결한다. 한 번 끝나면 모든 앱이 공유. (2026-06-14 happylife2080100/authuser=5에서 SA `play-publisher@claude-for-android` 생성·키 발급·Play 권한 부여 완료.)

## 엔진: Claude in Chrome (read-tier 콘솔)

사용자의 로그인된 Chrome 세션에서 `mcp__claude-in-chrome__*`(`navigate`/`find`/`computer`/`read_page`)로 조작. `list_connected_browsers` → 확인 → `select_browser`. 좌표 대신 ref 클릭, 스크린샷은 검증 지점만.

## 단계

### 1. API 2개 활성화 (Cloud Console)
`navigate` → `console.cloud.google.com/apis/library?authuser=1&project=claude-for-android`. 검색·진입·**사용 설정**:
- **Google Play Android Developer API** (`androidpublisher.googleapis.com`)
- **AdMob API** (`admob.googleapis.com`)
각 API 페이지에서 "사용 설정(Enable)" 버튼 ref 클릭. 이미 켜져 있으면 "관리"로 표시됨(스킵).

### 2. 서비스 계정 + JSON 키 (Cloud Console)
`navigate` → `console.cloud.google.com/iam-admin/serviceaccounts?authuser=1&project=claude-for-android`.
1. "서비스 계정 만들기" → 이름 `play-publisher` → 생성(역할 부여 단계는 건너뛰어도 됨 — 권한은 Play Console에서 줌) → 완료. 결과 이메일: **`play-publisher@claude-for-android.iam.gserviceaccount.com`**.
2. 그 서비스 계정 → "키" 탭 → "키 추가" → "새 키 만들기" → **JSON** → 만들기. 브라우저가 JSON 키를 `~/Downloads`로 다운로드(이 다운로드 1건이 유일한 바이너리 동작 — Chrome이 트리거, 아래에서 Bash로 이동).

### 3. 키를 자리에 배치 (Bash — 기존 것 백업)
```bash
mkdir -p ~/.config/play-publisher
# 기존 키 백업 (있으면)
[ -f ~/.config/play-publisher/sa.json ] && cp ~/.config/play-publisher/sa.json ~/.config/play-publisher/sa-claude-android-upload.json.bak
# 방금 받은 키를 자리로 (파일명은 실제 다운로드명으로)
mv ~/Downloads/claude-for-android-*.json ~/.config/play-publisher/sa.json
chmod 600 ~/.config/play-publisher/sa.json
```
경로를 그대로 유지하므로 `play_upload.py`/`play_read.py`의 `SA_KEY`는 수정 불필요(이메일 문구만 갱신됨).

### 4. Play Console 권한 부여 (Play Console — 사용자 및 권한으로 SA 초대)
`navigate` → `play.google.com/console/u/5/developers/8303647010319569479/users-and-permissions`(happylife2080100).

> **`/api-access`(GCP 프로젝트 링크) 페이지는 이 콘솔 버전에서 deprecated** — 열면 홈으로 리디렉션된다. 프로젝트를 따로 "링크"할 필요 없이, SA 이메일을 **사용자로 초대**하면 권한이 붙는다(기존 claude-android-upload SA도 이 모델로 동작 중).

1. **신규 사용자 초대** → 이메일 `play-publisher@claude-for-android.iam.gserviceaccount.com` 입력.
2. **⚠️ 반드시 앱 권한(app-level)으로 부여 — 계정 권한(account-level)은 SA의 API에 안 먹힘(2026-06 실증).** 계정 권한만 주면 콘솔엔 권한이 보여도 `edits.insert`가 403. **앱 권한** 탭 → **애플리케이션 추가 → "모두 선택"**(현재 모든 앱) → 적용. 그러면 각 앱에 "프로덕션 출시 + 앱 정보 관리" 등 6개 권한이 붙는다(릴리스·등록정보·이미지 커버).
3. **변경사항 저장 → 예**. 서비스 계정은 이메일 확인 없이 즉시 활성. (계정 권한은 안 먹히므로 굳이 줄 필요 없음. 관리자 전체권한도 과도 — 앱 권한이 정답.)
4. **신규 앱을 만들면 그 앱에도 SA 앱 권한을 추가**해야 API가 동작(account-level이 자동 커버 안 함). 앱 생성 직후 사용자 및 권한 → SA → 앱 권한 → 애플리케이션 추가로 새 앱 체크.
5. 권한 전파에 수 분 걸릴 수 있음(직후 `play_read.py`가 403이면 잠시 후 재시도). 검증: `play_read.py summary`가 200, `play_upload.py`(--commit 없이)가 "validate OK".

### 5. AdMob 계정 (AdMob 콘솔 — §1.5에서 앱별로)
`apps.admob.com`(happylife2080100). **유일한 수동 단계 = 계정 가입(약관·결제국가·계정생성) — 대행 금지.** 가입만 끝나면 앱/광고단위 생성·ID 읽기·코드 반영은 §1.5대로 Claude in Chrome 무인(write API 없어 콘솔 클릭, ID는 콘솔에서 직접 read). AdMob API(2단계에서 켬)는 `scripts/admob_api.py`의 **읽기**(앱·광고단위·리포트)용 — 첫 사용 시 OAuth 1회 동의(`~/.config/play-publisher/admob_oauth_client.json` + 발급 토큰).

## 검증
```bash
~/.config/play-publisher/venv/bin/python ~/.claude/skills/android-app-builder/scripts/play_read.py summary
```
200으로 details/tracks가 나오면 연결·권한 OK. 403이면 4번(권한 전파 — 보통 수 분) 재확인. 업로드 측은 `play_upload.py --config <기존앱>.json`(--commit 없이)이 `validate OK / DRY RUN ok`면 정상.

## 롤백
새 연결이 전파 안 되면: `cp ~/.config/play-publisher/sa-claude-android-upload.json.bak ~/.config/play-publisher/sa.json`로 복원하고 `play-publishing-api.md`/`play_upload.py`의 SA 이메일을 옛값으로 되돌린다.
