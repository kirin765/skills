---
name: ig-android
description: Android 실기기(iMUZ IM-H031 태블릿)의 Instagram 앱을 adb+uiautomator2로 직접 조작하는 워크플로우 — Reels 업로드(영상 푸시→계정 검증→트렌딩 오디오→캡션→AI라벨→게시), 계정 워밍(warm.py 위임), 기기 연결/식별. 사용자가 "태블릿으로 IG 게시", "릴스 올려줘", "보석십자수/photofix 릴 게시", "IG 워밍 돌려줘", "IM-H031로 진행", "인스타 업로드 자동화" 같은 표현을 쓰면 반드시 발동 — 계정명이나 기기명을 안 말해도 IG 앱 조작·릴스 게시·계정 워밍이면 이 스킬이다. IG 웹/CDP 자동화(cdp-anywhere)나 스크래핑(x-cdp-search)이 아니라 **실기기 앱 조작**이 핵심 구분점. 게시는 되돌릴 수 없으므로 계정 검증·단계별 스크린샷 검수 규율이 스킬의 존재 이유다.
---

# ig-android — Android 실기기 IG 조작 (Reels 업로드 + 워밍)

adb + uiautomator2 로 IM-H031 태블릿의 Instagram 앱을 조작한다. 브라우저/API가 아니라 **실기기 앱**이므로: 트렌딩 오디오를 입힐 수 있고(도달에 유리), 계정 신뢰도가 유지되고, 대신 **오발송이 물리적으로 되돌릴 수 없다**. 이 스킬의 절반은 "어떻게 하는가", 나머지 절반은 "무엇을 반드시 확인하고 하는가"다.

기존 인프라 위치: `~/projects/misc/brain/bin/ig-prime/` (warm.py + igw/ 모듈 — device·session·human·safety). 이 스킬의 셀렉터·안전장치는 igw 모듈을 재사용한다.

## 0. 기기 연결 — 반드시 모델 확인부터

- 대상: **iMUZ IM-H031** (Android 15, 2000×1200 가로, USB 시리얼 `H03125M1F09706`), 무선 adb `<DHCP IP>:5555`.
- ⚠️ **같은 네트워크에 Box Q(Homatics TV박스)가 5555를 열고 있다.** IP만 보고 연결하면 엉뚱한 기기다(실제 사고 사례: 2026-07-04, 영상을 Box Q에 푸시). 연결 후 **반드시** `adb -s <serial> shell getprop ro.product.model` == `IM-H031` 확인 후 진행.
- IP를 모르면 서브넷 스캔: `for i in $(seq 2 254); do (nc -z -G 1 192.168.0.$i 5555 2>/dev/null && echo OPEN $i) & done; wait` → 각 OPEN IP에 connect + 모델 확인.
- **기기 연결 실패 시 (Wi-Fi 저전력 모드 대응)**: 태블릿의 Wi-Fi 카드가 저전력 모드로 진입하면 패킷 지연시간(RTT)이 1초 이상으로 늘어나 포트 스캔이나 연결이 실패할 수 있다. 대상 IP로 핑을 보내고(`ping -c 2 -W 2000 <IP>`) 연결하면 정상 복구된다 (`upload_reel.py` 가동 시 자동 수행).
- 둘 다 실패하면 USB 연결 후 `adb tcpip 5555` 재활성화가 필요하다 — 이건 사용자에게 요청.
- 화면잠금은 '없음'이어야 무인 조작 가능 (igw.device.wake 가 swipe 키가드만 해제).
- 작업 종료 시 화면은 `igw.device.sleep(d)` 로 끈다 — warm.py 는 finally 에서 항상, upload_reel.py 는 게시 성공 시 자동 수행. 수동/애드혹 조작 후에도 마지막에 호출할 것.

## 1. 안전 계약 (모든 작업 공통)

1. **계정 검증 없이는 아무것도 탭하지 않는다.** IG 앱에 여러 계정이 로그인돼 있다(happylife2080100, photofix.kr 등). 프로필 탭 → `igw.session.active_handle(d)` 가 기대 handle 과 일치할 때만 진행. 불일치면 계정 전환(`SWITCHER` 셀렉터) 후 재검증.
2. **단계마다 스크린샷 검수.** `d.screenshot(path)` 찍고 Read 로 눈으로 확인 → 다음 탭. UI 는 수시로 바뀌므로 좌표 blind-tap 연쇄는 금지. 셀렉터는 `.exists` 확인 후 클릭, 없으면 SKIP하고 화면을 다시 본다.
3. **체크포인트 감지 시 즉시 중단.** `igw.device.checkpoint(d, phrases)` — "확인이 필요", "Suspicious", "차단" 류 문구가 뜨면 어떤 액션도 하지 말고 사용자에게 보고.
4. **게시(Share) 클릭은 사용자가 명시 요청했을 때만.** 테스트·리허설은 `--stop-before-share` 로 공유 직전까지만 간다.
5. 콜드 스타트 원칙: `igw.device.open_ig(d, PKG)` (stop=True) — 홈 피드라는 결정적 상태에서 시작. `app_current()` 는 이 태블릿에서 오보고하므로 IG 여부는 `dump_hierarchy()` 로 판정.

## 2. Reels 업로드 — 검증된 플로우 (2026-07-04 실증)

빠른 경로: 번들 스크립트 사용.

```bash
cd ~/.claude/skills/ig-android
python3 scripts/upload_reel.py \
  --serial 192.168.0.147:5555 \
  --account happylife2080100 \
  --video ~/Downloads/boseok-reel1/reel1.mp4 \
  --caption-file /tmp/caption.txt \
  --audio-trending-rank 1 \
  --ai-label \
  --screenshot-dir /tmp/igshots
```

**Exit 코드 — 호출자는 반드시 구분할 것 (2026-07-15 추가).**

| 코드 | 뜻 | 재시도 |
|---|---|---|
| 0 | 게시 완료 + 포스트 수 증가까지 실측 | — |
| 1 | UI 건드리기 전 거부(기기 오인·영상 없음·**푸시한 영상이 갤러리 최신 아님**) | ❌ |
| 2 | **Share 누르기 전** 정지 — 게시 안 됨 | ✅ 콜드 스타트로 재시도 안전 |
| 3 | **Share 누른 뒤** 정지 — 게시 여부 불명 | ❌ **절대 금지** — 여기서 재시도가 곧 중복 게시. 사람에게 에스컬레이션 |

`bin/ig-autopost/autopost.py`가 이 규칙대로 exit 2만 3회까지 재시도한다. 대부분의 UI 정지는 일시적 모달이라 재시도로 그날을 살린다.

스크립트는 각 단계에서 스크린샷을 남기고, 셀렉터가 안 잡히면 그 지점에서 멈추고 경로를 출력한다. **멈추면 스크린샷을 Read 로 보고 수동으로 그 단계만 이어간 뒤 재개하는 게 정석** — UI 드리프트는 정상이다.

단계별 흐름 (스크립트가 하는 일 = 수동 폴백 시 그대로 따라가는 순서):

1. **푸시**: `adb push <video> /sdcard/DCIM/Camera/<name>.mp4` + `MEDIA_SCANNER_SCAN_FILE` 브로드캐스트 (안 하면 IG 갤러리에 안 보임).
   - ⚠️ **푸시 후 그 파일이 미디어스토어 최신인지 반드시 검증**(2026-07-15 추가, `wait_media_newest`). 갤러리 타일은 좌표로 찍으므로 **첫 타일에 있는 게 곧 게시되는 것**이다. 스캔이 늦으면 어제 릴이나 **다른 계정 릴**이 올라간다. 최신이 될 때까지 재스캔하고, 안 되면 exit 1로 거부한다.
   - **파일명은 계정·날짜별로 고유하게.** 자동화가 양쪽 계정 모두 `reel.mp4`로 푸시하던 시절엔 두 번째 실행이 첫 번째를 덮어썼다 → `bin/ig-autopost/autopost.py`는 이제 `{account}-{YYYYMMDD}.mp4`를 쓴다.
   - 조회는 `content query --projection _display_name:date_added` 후 **파이썬에서 정렬**한다. `--sort 'date_added DESC'`는 adb가 argv를 공백으로 이어붙이고 기기 셸이 다시 쪼개서 `Invalid token LIMIT`/토큰 깨짐으로 실패한다(2026-07-15 실측).
2. **계정 검증**: IG 콜드 스타트 → interstitial dismiss → 프로필 탭(`tab_avatar`) → `active_handle` 일치 확인.
3. **만들기**: `d(description="Create")` 클릭 → "New reel" 갤러리 (하단 모드가 REEL 인지 확인) → 방금 푸시한 영상 = Recents 최신 비디오 썸네일 클릭.
   - ⚠️ **미게시 드래프트가 있으면 "Keep editing your draft?" 모달이 피커를 가린다**(2026-07-15 실측). 모달이 계층을 덮어 REEL 마커 탐지가 실패하므로 `reel_mode` 에서 멈춘 것처럼 보이지만 실제로는 모드가 정상이다. **"Start new video"** = 드래프트 저장 후 새로 시작(정답). "Keep editing" 은 남의 드래프트를 물고 가므로 절대 금지. 스크립트가 자동 처리한다.
4. **에디터 진입 방해물**: "Level up your videos with Edits" 홍보 모달이 뜨면 `back` 으로 닫는다 (Get App 누르지 말 것).
5. **오디오**: 하단 툴바 첫 아이콘(음표) → 피커에서 **Trending 탭** → 곡 선택 기준: 상승세(초록 화살표) + reels 수 + 영상 톤 매칭. 행 클릭 → 하단 미리듣기 바의 **→ 버튼**으로 적용 → "Choose the part you want" 클립 화면은 기본 구간으로 **Done** (text 셀렉터가 종종 늦게 잡히므로 우상단 좌표 폴백).
   - 원본 영상에 오디오가 없으면 볼륨 밸런스 조정 불필요 — 우리 렌더는 의도적으로 무음.
6. **Next** → 공유 설정 화면. "Others can now download..." 모달은 **Continue**.
   - ⚠️ **위치태그 "Map preview" 모달 — 무인 실행 최대 위험**(07-06 D3·07-09 D5 2회 실측, 코드 반영은 2026-07-15). IG가 공유화면에서 **실제 물리적 위치**(실측: "IKEA 광명점")를 자동 제안·적용하고, 동시에 **AI 라벨을 OFF로 리셋**한다. 사람이 붙어 있을 땐 매번 Cancel로 막았지만 무인이면 사장님 실제 위치가 공개 계정에 박힌 채 게시된다. `dismiss_location()`이 Cancel → 사라졌는지 검증 → 안 사라지면 게시 거부(exit 2). **순서 고정: 위치 모달 해제 → AI 라벨 재확인 → Share.** 반대로 하면 라벨이 다시 OFF가 된다.
7. **캡션**: "Write a caption" 필드 클릭 → `d.send_keys(캡션)` — 한국어+이모지+해시태그 정상 입력됨(2026-07-04 실증). 해시태그 자동완성 드롭다운이 떠도 무시하고 우상단 **OK**.
8. **AI 라벨**: 소재에 AI 생성 실사가 들어갔다면 "Add AI label" 토글 ON — IG 정책 준수이자 평판 계정 보호. 우리 파이프라인(생성 이미지 기반 리빌)은 기본 ON.
   - 상태 판독은 **계층의 `checked` 속성**으로 한다(2026-07-15 수정). IG 는 이 토글을 `Switch` 가 아니라 제네릭 `android.view.View` + `checkable="true" checked="true/false"` 로 렌더하므로 class 기반 조회는 못 찾는다. `_ai_toggle()` 은 "Add AI label" 행과 같은 y(±60px)에 있는 checkable 노드를 찾아 `(켜짐여부, cx, cy)` 를 돌려준다.
   - ⚠️ **AI 라벨은 최다 재발 실패 모드다(3회: 07-06 위치모달 리셋 · 07-09 화면회전 리셋 · 07-14 상태 오판).** 세 번 다 원인이 같다 — **상태를 모르면서 안다고 가정하고 행동한 것.** 그래서 규칙은 하나다: **판정 불가는 OFF 가 아니다.**
     - 픽셀 밝기 추정(구버전)은 이미 ON 인 토글을 OFF 로 오판해 3번 헛돌렸다.
     - 그 대체 구현도 노드를 못 찾으면 `False` 를 반환해, 호출부가 하드코딩 x(`AI_TOGGLE_CX=1445`)를 맹목적으로 눌렀다 — 켜져 있던 라벨을 우리 손으로 끄는 경로였다. 2026-07-15 제거.
     - 지금은 노드를 못 찾으면 `None` → **게시 거부(exit 2)**. 클릭도 하드코딩 좌표가 아니라 **찾은 노드의 실제 중심**을 누른다. 추측해서 게시하느니 그날을 거르는 게 낫다 — 잘못 추측하면 AI 실사가 라벨 없이 공개된다.
9. **Next** → 최종 확인. "Update on your original audio" (Meta AI 사용 동의) 모달은 **"Turn off and share"** — 프라이버시 보수 기본값.
10. **검증**: **Share 탭 = 게시 아니다**(2026-07-15). 스크립트는 계정 검증 단계에서 프로필 포스트 수를 기준선으로 읽어두고, Share 후 최대 2분간 폴링해 **포스트 수가 실제로 늘었는지 확인**한 뒤에만 성공(exit 0)으로 보고한다. 안 늘면 exit 3 — 게시 여부 불명이므로 재시도 금지, 사람이 계정을 눈으로 확인해야 한다. 이 검증이 없던 시절엔 Share가 조용히 실패해도 "PUBLISHED"를 출력했고, 호출자는 그날을 게시한 걸로 기록했다.

게시 완료 후: kill-test 트랙이면 **brain 트래커에 게시일 기록 + 판정일(게시일+14) 갱신**을 잊지 말 것 (`~/projects/misc/brain/wiki/action-tracker.md`, `query:` 커밋).

## 3. 워밍 (릴스 시청·좋아요·팔로우 프라이밍)

직접 구현하지 말고 기존 실행기에 위임한다:

```bash
cd ~/projects/misc/brain/bin/ig-prime
python3 warm.py --serial <ip>:5555 --account <handle>   # 실행
python3 warm.py --probe                                  # 기기+IG+체크포인트 점검만
python3 warm.py --dry-run                                # 계획만
python3 warm.py --dump                                   # 셀렉터 보정용 UI 덤프
```

일일 캡·휴식일·최소 간격 등은 `warm.config.json` 이 관리한다. 워밍과 업로드를 같은 시간대에 겹치지 않게 — 세션 패턴이 기계적으로 보이는 걸 피한다.

**무인 스케줄 (2026-07-04~)**: launchd `com.brain.ig-warm` 이 매일 12:40·21:35 에 `warm-routine.sh` 를 실행한다 — 태블릿 IP 자동 탐색(모델 검증 포함) → `warm.py --account happylife2080100`. 프라이밍 대상은 happylife 만 (기준: brain `wiki/topics/ig-topic-priming.md` — photofix 는 신규 계정이라 게시가 곧 프라이밍). 니치 패스: `explore/tags/` 딥링크 그리드에서 시청 — `GRID_CELL`(`image_button`) 셀렉터는 미캘리브레이션이므로 첫 실기기 런에서 `--dump` 로 확인·보정할 것.

## 3.5 실측 검증 기록 (2026-07-15, happylife2080100 게시→삭제 1회전)

리허설(`--stop-before-share`) → 실게시 → 즉시 삭제로 전 경로를 실기기에 대고 확인했다. 포스트 수 12 → 13 → 12 로 원복.

| 경로 | 상태 |
|---|---|
| 미디어스토어 가드 — 푸시 파일이 최신인지 | ✅ 고유 파일명으로 통과 |
| 포스트 수 기준선 (`posts before: 12`) | ✅ |
| **드래프트 모달** ("Keep editing your draft?") | ✅ **실제로 떴고 자동 처리됨** — 07-14 boseok 을 죽인 그 모달. 리허설이 남긴 컴포저 상태가 조건을 재현했다 |
| 트렌딩 오디오 (rank 2) | ✅ |
| 한국어 캡션 | ✅ |
| **AI 라벨 tri-state** | ✅ **공유화면에 토글이 4개**(AI label·Threads·Facebook·Your story)인데 행 매칭이 AI label 만 정확히 선택. 8단계·9단계 2회 다 ON 확인 |
| **게시 검증** (`posts after: 13 (was 12)`) | ✅ Share 탭 후 폴링해 실제 증가 확인 |
| **위치태그 모달 및 유출 방지** | ✅ **실측 검증 완료 (07-15 18:55)** — `pm revoke`를 통해 `ACCESS_FINE_LOCATION` 및 `ACCESS_COARSE_LOCATION`이 모두 성공적으로 회수(`granted=false`)되었으며, 화면 레이아웃에서 `"Add location"` 문자열 유무를 검증하여 위치 유출을 차단하는 3중 방어막의 유효성을 실기기 리허설로 확인했다. |

**삭제 다이얼로그는 "Delete reel?" 이다** — 게시물의 "Delete Post?" 와 문구가 다르다. 선택지는 `Delete` / `Move to drafts` / `Cancel`. **`Move to drafts` 는 금지** — 드래프트가 남아 다음 업로드에서 위 모달을 부른다. 30일간 Your activity → Recently deleted 에서 복구 가능.

## 4. UI 드리프트 대응

IG 앱 업데이트로 셀렉터가 깨지는 건 예정된 일이다. 그때:
- `warm.py --dump` 또는 `d.dump_hierarchy()` 로 현재 계층 확인 → `igw/session.py` 상수(캘리브레이션 블록)와 이 스킬의 스크립트를 함께 갱신.
- 이 태블릿의 IG 는 **좌측 세로 네비레일** 레이아웃(가로 태블릿 UI), 탭들은 `tab_icon` resourceId 를 index 로 공유. 앱 언어는 영어(EN) — text 셀렉터는 영문 기준.
- 고칠 때마다 SKILL.md 의 해당 단계도 갱신해 둘 것 (다음 세션의 나를 위해).

## 5. 이 스킬이 아닌 것

- IG **웹** 자동화 / 데이터 수집 → `cdp-anywhere`
- IG 오디언스 분석 → `ig-audience-intel`
- CDP 큐 생성 `bin/ig-prime/ig_prime.py` — **폐지됨(2026-07-04)**: cron 해제, 프라이밍은 위 warm-routine(launchd) 이 대체. 파일은 참고용으로만 남아 있다
- 여러 SNS 동시 홍보 오케스트레이션 → `app-launch-promo`
