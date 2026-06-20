# Instagram 발행 (social-video-upload 스킬에 위임)

계정: **happylife2080100**. 세로(9:16) 영상을 Reels로 올린다.

DOM을 직접 다루지 않는다. `social-video-upload` 스킬의 업로더에 위임한다(SKILL.md 3-1 참고):

```bash
SVU=~/.claude/skills/social-video-upload/scripts/upload.mjs
NP=/opt/homebrew/lib/node_modules

# 1) 계정 확인
NODE_PATH=$NP node $SVU instagram whoami --account happylife2080100
#   → RESULT {"ok":true,...,"handle":"happylife2080100"} 인지 확인

# 2) 발행 (--expect로 오발행 차단, --auto로 실제 공유)
NODE_PATH=$NP node $SVU instagram post "$VIDEO" "$(cat /tmp/cap_ig.txt)" \
  --account happylife2080100 --expect happylife2080100 --auto
```

- 마지막 줄 `RESULT {json}`에서 `posted`·`url`을 읽어 리포트에 기록.
- `error`가 "not logged in"이면 건너뛰고 `login` 필요로 표시(자동 로그인 안 함):
  `NODE_PATH=$NP node $SVU instagram login --account happylife2080100`
- 셀렉터 깨짐·진단(`/tmp/ig-fail-*`)은 `social-video-upload`의 troubleshooting.md.
- 캡션은 IG용 카피(`copy-guidelines.md`)를 `/tmp/cap_ig.txt`에 써서 넘긴다(셸 이스케이프 사고 방지).
