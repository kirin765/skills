# Chrome CDP 셋업 (cdp-anywhere 공용)

다른 cdp-* 스킬 (x-cdp-search, reddit-cdp-coach, naver-cafe-scrape) 과 동일 프로파일 공유. 이미 띄워져 있으면 새로 띄울 필요 없음.

## CDP 모드로 Chrome 띄우기

### macOS (Intel + Apple Silicon 공통)
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

### Linux
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile" &
```

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
