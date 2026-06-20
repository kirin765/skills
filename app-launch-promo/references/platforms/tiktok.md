# TikTok 발행 (social-video-upload 스킬에 위임)

계정: **aigroove99**. 세로(9:16) 영상 + 후킹 설명 + 발견용 해시태그.

DOM을 직접 다루지 않는다. `social-video-upload` 스킬의 업로더에 위임한다(SKILL.md 3-1 참고):

```bash
SVU=~/.claude/skills/social-video-upload/scripts/upload.mjs
NP=/opt/homebrew/lib/node_modules

NODE_PATH=$NP node $SVU tiktok whoami --account aigroove99
NODE_PATH=$NP node $SVU tiktok post "$VIDEO" "$(cat /tmp/cap_tiktok.txt)" \
  --account aigroove99 --auto
```

- TikTok은 저작권/콘텐츠 검사가 끝날 때까지 기다린 뒤 게시하므로 **한 호출이 수 분** 걸릴 수 있다
  (검사 중 발행하면 "검토중/나만 보기"로 고정될 수 있어 업로더가 의도적으로 대기한다).
- 마지막 줄 `RESULT {json}`에서 `posted`·`url`을 읽어 리포트에 기록. `posted:false`에 `note`가
  "POST UNCONFIRMED"면 `~/.social-upload/shots/tiktok_5_after.png`로 실제 게시 여부 확인.
- `error`가 "not logged in"이면 건너뛰고 `login` 필요로 표시:
  `NODE_PATH=$NP node $SVU tiktok login --account aigroove99`
- 캡션은 TikTok용 카피 + 해시태그(#fyp 류 + 앱/카테고리 5~8개; `copy-guidelines.md`)를
  `/tmp/cap_tiktok.txt`에 써서 넘긴다. 캡션 링크는 클릭 불가일 수 있으니 "프로필 링크 참고" 문구를 곁들인다.
