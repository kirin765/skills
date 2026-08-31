# Chrome CDP 셋업 (cdp-anywhere 공용)

다른 cdp-* 스킬 (x-cdp-search, reddit-cdp-coach, naver-cafe-scrape) 과 동일 프로파일 공유. 이미 띄워져 있으면 새로 띄울 필요 없음.

## 이 머신의 Chrome 은 두 개 — 이름 붙여서 구분

| | 메인 Chrome | CDP Chrome |
|---|---|---|
| 프로파일 | Default (평소 쓰는 창) | `$HOME/chrome-cdp-profile` (전용) |
| 용도 | Engine A (Claude in Chrome 확장) | Engine B (CDP + Playwright) |
| 포트 | 없음 | `--remote-debugging-port=9222` |
| 판별 방법 | `list_connected_browsers` (확장 API) | `curl :9222/json/version` |

**절대 프로세스 이름(`ps aux | grep "Google Chrome"`, `pgrep Chrome`)만으로 두 인스턴스를 구분하려 하지 말 것** — 둘 다 같은 `Google Chrome` 바이너리라 목록에 같이 뜬다. 메인 Chrome 이 실행 중이어도 CDP Chrome 은 안 떠 있을 수 있고, 반대도 마찬가지. Engine B 작업 전엔 항상 `:9222` 응답으로만 CDP Chrome 의 존재를 판단한다.

## 자동 기동 (권장 — 먼저 시도)

`scripts/probe.py` 는 CDP 가 미응답이면 **CDP Chrome 을 스스로 백그라운드로 띄우고** 최대 15초 재확인한다. 메인 Chrome 은 별도 `--user-data-dir` 라 손대지 않고 그대로 공존한다.

```bash
python3 <스킬 설치 경로>/cdp-anywhere/scripts/probe.py
# 예: ~/.dsh/skills/cdp-anywhere (DSH), ~/.claude/skills/cdp-anywhere (Claude Code)
```

> probe.py 자동 기동: macOS 는 Google Chrome, Linux(Omarchy/Hyprland) 는
> chromium + `--class=cdpchrome` 으로 띄운다 (Linux 지원은 2026-08-23 추가).

이게 실패했을 때만(브라우저 설치 경로가 다르거나 권한 문제) 아래 수동 명령으로 사용자에게 직접 띄워달라고 요청한다.

## CDP 모드로 Chrome 수동 띄우기

### macOS (Intel + Apple Silicon 공통)
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

### Linux (Omarchy/Hyprland, 실측 2026-08-23)
반드시 `--class=cdpchrome` 을 붙인다. 이 머신의 주력 브라우저도 같은
`chromium` 바이너리라, 클래스가 같으면 Hyprland 가 둘을 구분할 수 없어
CDP 창이 열릴 때마다 포커스를 뺏는다. `--class` 는 Wayland app_id 까지
바꾼다(실측 확인). `~/.config/hypr/hyprland.lua` 에 아래 규칙이 있어야
한다(적용 완료):

```lua
-- CDP 전용 chromium: 열릴 때 포커스 안 뺏음, 작업공간 98로 격리
o.window("cdpchrome", { no_initial_focus = true, float = true, workspace = "98 silent" })
```

```bash
chromium \
  --class=cdpchrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile" &
```

클래스 확인(규칙이 걸려 있는지):
```bash
hyprctl clients | grep "class: cdpchrome"
```
응답이 없으면 규칙 미적용 상태 — `--class=cdpchrome` 누락을 의심한다.

- 효과: 창은 떠 있지만 포커스·작업공간을 안 뺏는다. 직접 보고 싶을 땐
  워크스페이스 98로 가서 클릭하면 된다. `no_initial_focus`는 열릴 때만
  막는다(수동 클릭 가능).
- `--class=cdpchrome` 을 빠뜨리면 규칙이 안 걸린다. 기존 사용 명령에
  이 플래그만 추가하면 된다.
- 창 자체도 안 보고 싶으면 `--headless=new` 로 띄우면 창이 생기지 않는다.
  단 사이트 봇 감지가 다를 수 있고 직접 로그인·확인 창이 없다.

### Windows (Git Bash / WSL)
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

처음 띄우면 빈 프로파일이 만들어지고, 그 안에서 대상 사이트 로그인을 진행한다. 두 번째부터는 쿠키 · 로그인 상태가 유지됨.

## 동작 검증

```bash
curl -s http://localhost:9222/json/version | python3 -m json.tool
```

`"Browser": "Chrome/..."` 가 보이면 OK.

열린 탭 목록 확인:
```bash
curl -s http://localhost:9222/json | python3 -m json.tool | head -40
```

## 자주 겪는 문제

### `bind() returned an error: address already in use`
이미 9222 로 다른 Chrome 인스턴스가 떠 있음. `lsof -i :9222` 로 PID 확인 후 결정:
- 같은 cdp 프로파일이라면 그걸 그대로 사용 (새로 띄우지 말 것).
- 다른 프로파일이라면 그쪽을 종료하거나, 이 스킬은 그쪽 창에서 진행할지 결정 필요.

### `curl :9222` 응답 없음
- Chrome 이 안 떠 있음 → 위 명령으로 다시 띄움.
- 방화벽이 localhost 차단 — 거의 없지만 가능. 사용자에게 확인 요청.

### 평소 쓰는 Chrome 과 분리하고 싶음
`--user-data-dir` 가 격리 키. `$HOME/chrome-cdp-profile` 디렉토리가 별도 프로파일이라, 평소 Chrome (Default 프로파일) 의 북마크 · 비번 등과 완전 분리됨. 같은 머신에 두 Chrome 창 동시 띄워도 안전.

### macOS — Chrome 이 이미 떠 있어서 CDP 안 붙음
같은 user-data-dir 로 두 번 띄우는 건 불가. 평소 Chrome 을 닫기 싫으면 위 명령처럼 별도 `--user-data-dir` 를 쓰는 게 정석. 이미 평소 Chrome (Default) 이 떠 있어도 별도 dir 이라 공존 가능.

### `--remote-debugging-port` 가 무시되는 듯
보통 user-data-dir 충돌. `~/chrome-cdp-profile` 디렉토리 안에 `SingletonLock` / `SingletonSocket` 파일이 남아있으면 지운 뒤 재시도:
```bash
rm -f ~/chrome-cdp-profile/SingletonLock ~/chrome-cdp-profile/SingletonSocket ~/chrome-cdp-profile/SingletonCookie
```

## 백그라운드로 띄우기 (선택)

터미널 닫혀도 살아있게:
```bash
nohup /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile" \
  > /tmp/chrome-cdp.log 2>&1 &
disown
```

종료는 `pkill -f chrome-cdp-profile` 또는 Cmd+Q (창에서).

## 보안 메모

- `--remote-debugging-port` 가 열려 있는 동안에는 같은 머신의 다른 프로세스가 그 Chrome 을 제어할 수 있다. 신뢰할 수 없는 코드를 그 머신에서 동시에 돌리지 말 것.
- 작업이 끝났는데도 CDP 모드 Chrome 을 계속 띄워둘 필요는 없음. 일상용으로는 평소 Chrome (별도 프로파일) 쓰고, CDP 작업할 때만 띄우는 게 깔끔.
- 이 스킬은 `browser.close()` 를 절대 호출하지 않음. 사용자가 직접 닫을 때까지 살려둔다.
