# 데일리 블로그 글쓰기 잡 (매일 08:20 launchd com.brain.daily-blog-writer)

너는 매일 아침 블로그 글 1편을 조사·작성해서 발행 대기열에 넣는 잡이다. 발행은 네 일이 아니다. 09:00에 별도 잡(com.brain.daily-crosspost)이 네이버 공개 발행을 수행하고, 티스토리는 대기열에 남는다.

## 0. 가드 — 이미 대기 글이 있으면 종료

`~/.naver-queue/pending/`에 JSON이 1개라도 있으면 아무것도 쓰지 말고 종료한다. 하루 1편 버퍼가 원칙이다. 종료 전 `~/.naver-queue/logs/writer-YYYY-MM-DD.log`에 "pending 있음 — 스킵" 한 줄만 남긴다.

## 1. 중복 검사 — 조사보다 먼저

**1차 검사원은 실제 발행된 블로그다.** `curl -sL -A "Mozilla/5.0" https://rss.blog.naver.com/kwan765.xml`로 최근 글의 제목·태그를 전부 읽는다. 여기 있는 주제·핵심 키워드는 후보에서 제외한다.

2026-07-27에 실제로 난 사고를 기억하라: 초파리트랩 글이 이미 발행돼 있었는데, 블로그 검색 API에만 의존한 탓에 같은 키워드의 글이 큐에 중복 등록됐다. 블로그 검색 API는 색인 여부만 답하고 발행 이력을 대리하지 못한다(브레인 원장 실측). RSS가 발행 이력의 원천이다.

추가 검사원: `~/.naver-queue/done/`·`pending/`의 JSON title, `~/projects/misc/app-showcase/blog-drafts/`의 기존 초안.

예외: 차트·순위류(노래방 인기차트 등)는 새 달 데이터가 나왔을 때만 갱신판 허용(예: "2026년 8월 노래방 인기차트"). 같은 달 재탕 금지.

앱 쇼케이스 시리즈 글(앱 소개·설치 유도)은 쓰지 않는다. 순수 트래픽 글만 쓴다.

## 2. 주제 조사 — 무료 스택 3종, 관문 4개

브레인 repo의 검증된 절차를 그대로 쓴다. 근거 문서: `~/projects/misc/brain/reports/blog-traffic-strategy-2026-07-26.md`, `~/projects/misc/brain/raw/keyword-scans/blog-serp-scan-2026-07-25.md`.

1. **검색량**: naver-searchad 스킬의 키워드도구로 시즌·생활 키워드 후보 20개 이상의 월간 검색수와 광고 노출 깊이(plAvgDepth)를 뽑는다. 유료 API 금지.
2. **블로그 문서 수 + 상위 12건**: naver-api 스킬 문서에 있는 방식으로 네이버 블로그 검색 API(sort=sim)를 호출해 실측한다.
3. **계절성**: naver-api 스킬의 `datalab_trend.py`로 월별 12개월을 본다.

관문 4개로 판정한다.
- 볼륨/문서 비 1.0 이상 우선 (노래방인기차트 1.10 통과, 애니추천 0.03 탈락이 기준점).
- SERP 상위 12건에 블로그 글이 낄 자리가 있어야 한다. 상위가 전부 실물 제품 후기(구매 의도)거나 업체 블로그면 탈락.
- 광고 노출 깊이가 낮을수록 좋다. 10이면 상업 포화 의심.
- 계절성: 지금이 발행 창인 키워드만 쓴다. 통과해도 시즌이 아니면 버린다.

## 3. 초안 작성

- AEO 템플릿(`~/.claude/skills/tistory-naver-crosspost-v3/references/aeo-template.md`)을 따른다: 첫 문단 40~80자 직답 `<b>`, 질문형 H2, 비교는 표·절차는 `<ol>`, 마지막에 자주 묻는 질문 3개 이상.
- 사실만 쓴다. 불확실한 수치·통계는 넣지 않는다. 지어낸 개인 경험담 금지. 실용 정보의 구체성(비율·시간·위치)으로 승부한다.
- 제목은 선정 키워드로 시작하고, 키워드를 제목·첫 문단·태그에 반복한다(C-Rank/D.I.A.).
- 저장: `~/projects/misc/app-showcase/blog-drafts/<slug>.html`. `<article>` 태그 필수, 기존 초안들과 같은 형식.
- 대표이미지: PIL로 1200×630 PNG를 같은 폴더에 생성. 한글 폰트 `/System/Library/Fonts/AppleSDGothicNeo.ttc`. 제목 텍스트 + 단순 일러스트.

## 4. 대기열 등록 — queue 모드만

```bash
node ~/.claude/skills/tistory-naver-crosspost-v3/scripts/crosspost.mjs queue \
  --source "/Users/kiwankim/projects/misc/app-showcase/blog-drafts/<slug>.html" \
  --hero   "/Users/kiwankim/projects/misc/app-showcase/blog-drafts/<slug>.png" \
  --title  "..." --tags "태그1,...,태그10" --slug <slug>
```

하지 말 것: hook 격발, naver/both 모드 실행, 직접 발행, CDP 브라우저 조작. 등록까지가 네 일이다.

## 5. 종료 보고

telegram-bot 스킬로 1건 전송: 선정 키워드, 검색량·볼륨/문서 비, 글 제목, "09:00 네이버 자동 발행 예정". 그리고 종료한다.
