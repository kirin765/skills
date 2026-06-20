# Threads 발행 (social-video-upload 스킬에 위임)

계정: **happylife2080100** (IG 연동). 짧은 대화체 + 세로 영상 첨부.

DOM을 직접 다루지 않는다. `social-video-upload` 스킬의 업로더에 위임한다(SKILL.md 3-1 참고):

```bash
SVU=~/.claude/skills/social-video-upload/scripts/upload.mjs
NP=/opt/homebrew/lib/node_modules

NODE_PATH=$NP node $SVU threads whoami --account happylife2080100
NODE_PATH=$NP node $SVU threads post "$VIDEO" "$(cat /tmp/cap_threads.txt)" \
  --account happylife2080100 --auto
```

- 마지막 줄 `RESULT {json}`에서 `posted`·`url`을 읽어 리포트에 기록.
- `error`가 "not logged in"이면 건너뛰고 `login` 필요로 표시:
  `NODE_PATH=$NP node $SVU threads login --account happylife2080100`
- 캡션은 Threads용 카피(≤500자, 해시태그 1~3개; `copy-guidelines.md`)를 `/tmp/cap_threads.txt`에
  써서 넘긴다. 500자를 넘으면 Threads가 분할/차단하니 짧게 유지.
