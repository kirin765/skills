# Chrome CDP Setup (x-cdp-search)

이 skill 은 `naver-cafe-scrape` 와 동일한 Chrome 프로파일 (`$HOME/chrome-cdp-profile`) 을 사용한다. 한 번 띄워 두면 두 skill 이 동시에 쓸 수 있다.

## CDP 모드로 Chrome 띄우기

기존 Chrome 이 켜져 있어도 무관 — `--user-data-dir` 가 다르므로 별개 프로세스로 뜬다.

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

처음 띄우면 빈 Chrome 창이 열린다. **한 번** 다음 사이트들에 로그인하면 쿠키가 `$HOME/chrome-cdp-profile` 에 저장되어 다음부터는 자동 로그인된다.

- `https://x.com` — X (Twitter) 로그인
- `https://cafe.naver.com` — 네이버 로그인 (naver-cafe-scrape 도 쓸 거라면)

## 동작 검증

CDP 가 9222 포트에서 응답하는지:

```bash
curl -s http://localhost:9222/json/version | head -1
# {"Browser": "Chrome/..."} 형태가 나오면 OK
```

X 로그인 상태 확인:

```bash
python ~/.claude/skills/x-cdp-search/scripts/x_search.py --probe
# ✅ X 로그인: X 로그인 쿠키 (ct0+auth_token) 확인됨
```

## 자주 겪는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `connection refused` 9222 | CDP Chrome 안 떠있음 | 위 명령으로 다시 띄우기 |
| Chrome 창은 떴는데 `curl localhost:9222` 실패 | 다른 Chrome 프로세스가 포트 점유 | `lsof -i :9222` 로 점유 확인, 죽이고 재시도 |
| probe 가 "ct0 없음" 반환 | 그 Chrome 창에서 X 로그인 안 됨 | 그 창에서 x.com 열고 로그인 |
| probe 통과인데 검색 결과 0 | 쿼리 너무 좁음, 또는 X soft rate-limit | 쿼리 넓혀서 재시도, 또는 10~30분 대기 |
| 매번 다시 로그인하라고 나옴 | `--user-data-dir` 경로가 매번 다름 | 항상 `$HOME/chrome-cdp-profile` 로 통일 |

## 백그라운드로 띄우기 (선택)

작업 중 Chrome 창이 거슬리면 백그라운드 실행:

```bash
nohup /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile" \
  > /dev/null 2>&1 &
```

종료 시:

```bash
pkill -f "remote-debugging-port=9222"
```

## 보안 메모

- `--remote-debugging-port=9222` 는 localhost 에만 바인딩되지만, 같은 머신의 다른 프로세스는 모두 이 Chrome 을 완전히 제어할 수 있다.
- 공유 머신에서 쓰지 말 것. 외부에 9222 노출하지 말 것.
- 작업 끝나면 위 `pkill` 로 정리하는 게 안전.
