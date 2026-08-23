---
name: ppomppu-clien-scrape
description: 뽐뿌(ppomppu.co.kr)·클리앙(clien.net) 공개 게시판 글을 일괄 수집하는 워크플로우. 사용자가 "뽐뿌 글 수집", "클리앙 스크랩", "클리앙 모두의공원 모아줘", "뽐뿌 자유게시판 크롤링", "클리앙에서 ~~ 검색해서 수집", "커뮤니티 pain 신호 수집 (뽐뿌/클리앙)" 비슷한 요청을 할 때 발동. 로그인·CDP 불필요 (둘 다 공개 HTML). 본문·메타데이터를 마크다운+frontmatter 로 저장. 클리앙은 서버사이드 검색 지원, 뽐뿌는 검색이 봇 차단이라 목록 페이지네이션+로컬 키워드 필터로 대체. 네이버 카페는 naver-cafe-scrape, DC인사이드는 dcinside-sales-safari 가 담당.
---

# 뽐뿌·클리앙 스크랩 워크플로우

## 무엇을 하는 skill 인가

뽐뿌와 클리앙의 공개 게시판을 페이지네이션하며 글 본문+메타데이터를 마크다운+frontmatter 로 저장한다. pain 신호 수집(complaint-miner 류)이 주 용도. 두 사이트 모두 로그인이 필요 없어 CDP·Playwright 없이 requests 만으로 동작한다.

## 사이트별 특성 (설계 배경)

| | 클리앙 | 뽐뿌 |
|---|---|---|
| 목록 | `/service/board/{board}?po={p}` 서버 렌더링 | `zboard.php?id={board}&page={p}` (euc-kr) |
| 검색 | ✅ `/service/search` 서버사이드 지원 | ❌ 검색 endpoint 봇 차단(403) → 목록 수집 + `--keyword` 로컬 필터 |
| 본문 | `div.post_article` | `td.han` 중 최장 텍스트 (구형 zboard) |
| 댓글 | ✅ 본문 HTML 에 포함, 수집됨 | ❌ AJAX 로딩 — v1 미수집 (`comment_count` 메타만) |
| RSS | 없음 (폐지됨) | ✅ `rss.php?id={board}` — 최신글 폴링용 |
| 차단 | 관대함 | 세션 쿠키 없거나 burst 요청 시 간헐 403 → 스크립트가 자동 처리 (홈 방문 쿠키 + delay 1.5s + 재시도) |

## 게시판 ID 확인법

게시판 URL 에서 그대로 읽는다.
- 클리앙: `clien.net/service/board/park` → `park` (모두의공원). `jirum`(알뜰구매), `kin`(질문답변), `cm_stock`(주식), `sold`(중고장터) 등.
- 뽐뿌: `zboard.php?id=freeboard` → `freeboard` (자유게시판). 핫딜은 `ppomppu`.

## 핵심 스크립트

모든 로직은 `scripts/scrape.py` 한 파일. 상황에 맞는 인자만 골라 호출한다.

### 1. 접근성 probe (수집 안 함)

```bash
python3 ~/.claude/skills/ppomppu-clien-scrape/scripts/scrape.py --site clien --board park --probe
python3 ~/.claude/skills/ppomppu-clien-scrape/scripts/scrape.py --site ppomppu --board freeboard --probe
```

### 2. 게시판 수집 (페이지 단위)

```bash
python3 .../scrape.py --site clien --board park --pages 10 --out ./raw
python3 .../scrape.py --site ppomppu --board freeboard --pages 10 --out ./raw
```

### 3. 클리앙 키워드 검색 수집 (서버사이드, 과거 글 포함)

```bash
python3 .../scrape.py --site clien --query "정산 힘들다" --pages 5
python3 .../scrape.py --site clien --query "정산" --board cm_stock --pages 3   # 특정 게시판 한정
```

### 4. 뽐뿌 키워드 수집 (목록 스캔 + 로컬 필터)

```bash
python3 .../scrape.py --site ppomppu --board freeboard --pages 30 --keyword "정산,수수료,일일이"
```

키워드는 쉼표 구분 OR 매치, 제목+본문 대상. 서버 검색이 아니라서 **스캔한 페이지 범위 안에서만** 찾는다. 과거 archive 전체 검색은 불가.

### 5. 뽐뿌 최신글 폴링 (RSS, 가장 가벼움)

```bash
python3 .../scrape.py --site ppomppu --board freeboard --rss --no-body
```

### 기타 옵션

- `--days N` — N일 이내 글만, cutoff 도달 시 중단
- `--limit N` — 최대 저장 글 수
- `--no-body` — 목록 메타만 (본문 fetch 생략, 빠름)
- `--delay S` — 요청 간격 (기본 clien 0.8 / ppomppu 1.5초). **뽐뿌에서 1.0 미만으로 내리지 말 것** — 403 유발
- `--out DIR` — 기본 `./raw`

## 출력 형식

```
{out}/{site}/{board 또는 query}/{YYYY-MM}/{article_id}.md
```

frontmatter: source/board/article_id/url/title/posted_at/scraped_at/writer_nick/views/comment_count. 본문 뒤에 클리앙은 `## 댓글` 섹션 포함.

중복 방지 인덱스: `{out}/INDEX_{site}_{label}.json` — 재실행 시 수집한 id 는 스킵하므로 같은 명령을 cron 처럼 반복 실행해도 안전하다.

## 권장 실행 흐름

1. `--probe` 로 두 사이트 접근성 확인.
2. `--limit 3` 소량 테스트로 파일 형식 확인.
3. 본 수집은 background 실행 (`--pages` 크면 오래 걸림 — 뽐뿌는 글당 ~1.5초).
4. 대량 수집(수백 페이지)은 30분 단위 wakeup 으로 진척 점검.

## 트러블슈팅

- **뽐뿌 403 반복**: delay 를 3.0 으로 올려 재시도. 그래도 막히면 IP 차단 가능성 — 잠시 쉬었다 재개.
- **뽐뿌 본문이 비어 있음**: 이미지-only 글이면 정상. 텍스트 글인데 비면 `td.han` 구조 변경 의심 — 해당 글 HTML 을 받아 셀렉터 확인.
- **클리앙 목록 0건**: `data-role="list-row"` 구조 변경 의심. 게시판 ID 오타도 확인.
- **뽐뿌 RSS 글자 깨짐**: RSS 는 UTF-8, zboard 는 euc-kr — 스크립트가 Content-Type 으로 자동 분기하니 스크립트 밖에서 curl 로 받을 때만 주의.

## 다른 skill 과의 경계

- 네이버 카페 → `naver-cafe-scrape` (CDP 필요)
- DC인사이드 → `dcinside-sales-safari`
- X → `x-cdp-search`
- 에펨코리아 → 전용 skill 없음. 안티봇이 공격적이라 수집하려면 cdp-anywhere 로 사용자 세션 사용.
