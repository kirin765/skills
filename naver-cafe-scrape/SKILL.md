---
name: naver-cafe-scrape
description: 네이버 카페 (cafe.naver.com) 의 특정 게시판들을 기간 또는 글 수 단위로 일괄 스크랩하는 워크플로우. 사용자가 "네이버 카페 X 카페 게시판 Y, Z 스크랩", "cafe.naver.com 글 모아줘", "naver cafe Y개월치 수집", "카페 코퍼스 만들어줘" 비슷한 요청을 할 때 발동. 카페 SPA 의 내부 JSON API 를 호출해 본문·메타데이터를 마크다운+frontmatter 로 저장. Chrome CDP (포트 9222) 를 통해 사용자의 인증된 세션을 그대로 사용하므로 네이버 로그인·카페 가입·등업이 사전 조건. 게시판 ID 만 알면 카페 종류 무관하게 작동. 사용자가 카페·게시판·기간만 알려주면 스크랩 시작 전 자동으로 사전 조건을 검증하고, background 실행 + 30분 단위 wakeup 으로 진척 보고.
---

# 네이버 카페 스크랩 워크플로우

## 무엇을 하는 skill 인가

사용자가 네이버 카페 URL (또는 카페 이름) 과 게시판 menuid 들 + 기간(또는 글 수)을 지정하면, Chrome CDP 로 카페 SPA 의 내부 JSON 응용 프로그래밍 인터페이스 (API) 를 호출해 게시판별 글을 일괄 수집하고 마크다운+frontmatter 형식으로 저장한다. 카페 종류 (자영업·교육·취미 등) 와 무관하게 같은 흐름으로 작동한다.

## 왜 이 흐름인가 — 설계 배경

네이버 카페는 SPA 라서 DOM 스크래핑은 비용이 크고 깨지기 쉽다. 그러나 SPA 자체가 호출하는 내부 JSON API (`apis.naver.com/cafe-web/...`) 가 안정적으로 노출되어 있고, 사용자의 로그인·가입·등업 상태가 쿠키에 담겨 있다. Chrome CDP 로 사용자가 띄운 브라우저 세션에 붙으면 그 쿠키를 그대로 재사용하므로 별도 로그인 자동화·캡차 우회가 불필요하다. 이 skill 은 그 패턴을 정형화한 것이다.

## 사전 조건 (skill 시작 전 반드시 확인)

스크랩 시작 전에 다음 4가지를 자동 probe 한다. 하나라도 실패하면 사용자에게 명확히 안내하고 스크랩을 시작하지 않는다.

1. **Chrome CDP 가 9222 포트에서 응답** — `curl -s http://localhost:9222/json/version`
2. **네이버 로그인 상태** — 카페 페이지에 접근해 로그인 사용자 정보가 노출되는지 확인
3. **카페 가입 여부** — 가입 안 한 카페는 게시판 API 가 권한 오류 반환
4. **게시판별 등업 여부** — 게시판마다 등업 등급이 다름. 각 게시판 1페이지를 미리 fetch 해 HTTP 401 / `restrictMenu` 응답 검출

스크립트가 이를 자동으로 검사하니, Claude 는 결과를 받고 막히는 게시판이 있으면 사용자에게 그 게시판만 빼고 진행할지, 등업 후 다시 시작할지 물어보면 된다.

## CDP 띄우는 명령어 (사용자가 미리 실행해야 함)

스크랩 시작 전에 사용자가 다음 명령으로 Chrome 을 CDP 모드로 띄우고 네이버에 로그인·해당 카페 가입·등업까지 마쳐야 한다. 이미 띄워져 있으면 새로 띄울 필요 없다.

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-cdp-profile"
```

CDP 가 응답 안 하거나 (포트 9222 미응답) 로그인이 풀려 있을 때는 사용자에게 위 명령으로 다시 띄워 달라고 요청하라.

## 사용자 인풋에서 추출할 정보

사용자 메시지에서 아래 항목들을 뽑아낸다. 빠진 게 있으면 묻는다.

| 항목 | 예시 | 필수 여부 |
|---|---|---|
| 카페 URL 또는 이름 | `cafe.naver.com/tazza4` 또는 `tazza4` | 필수 |
| 게시판 menuid 목록 | `59, 135, 94` | 필수 |
| 기간 (일 수) 또는 글 수 | `180일`, `6개월`, `1000글` | 필수 (둘 중 하나) |
| 출력 디렉토리 | `./raw/tazza4` (기본값) | 선택 |

게시판 menuid 는 카페 메뉴 좌측 사이드바 링크의 `menuid=` 파라미터에서 보인다. 사용자가 menuid 를 모르면, 카페 페이지에 접근해 좌측 메뉴 링크들을 추출해 후보를 보여주고 선택하게 한다.

## 핵심 스크립트

이 skill 의 모든 로직은 `scripts/scrape_naver_cafe.py` 한 파일에 들어 있다. 기능별로 분기되어 있으니, Claude 는 상황에 맞는 인자만 골라 호출하면 된다.

### 1. 사전 조건 probe 만 하기 (스크랩 안 함)

```bash
python ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe.py \
  --cafe tazza4 --boards 59,135,94 --probe
```

출력 예시:
- ✅ CDP 9222 응답
- ✅ 네이버 로그인됨 (kiwankim)
- ✅ 카페 가입됨 (tazza4, club_id 15776665)
- ✅ board 59 (자유게시판) 접근 가능
- ❌ board 140 (학원평판게시판) 401 — 등업 부족

### 2. 본 스크랩 (기간 단위)

```bash
python ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe.py \
  --cafe tazza4 --boards 59,135,94 --days 180
```

### 3. 본 스크랩 (글 수 단위)

```bash
python ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe.py \
  --cafe tazza4 --boards 59 --limit 500
```

### 4. 진행 인덱스 초기화 (재시작)

```bash
python ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe.py \
  --cafe tazza4 --boards 59 --days 180 --reset
```

### 5. 단일 글 본문 응답 구조 확인 (디버깅용)

```bash
python ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe.py \
  --cafe tazza4 --probe-article 334844
```

## node raw-CDP 폴백 + 키워드 검색 (Playwright 안 될 때)

일부 Chrome(예: chrome-cdp-profile)은 **Playwright `connectOverCDP` 와 Network 도메인·
Page.navigate 가 비활성**이라 위 Python 스크립트(Playwright 의존)가 행/실패한다. 이때는
node raw-CDP 스크립트를 쓴다. 안정적으로 동작하는 것만 사용: `Network.getAllCookies` +
`Runtime.evaluate`(navigation 없이) + 추출 쿠키로 **node 서버사이드 fetch(CORS 없음)**.

```bash
# 사전 확인 (CDP 응답 + 쿠키 + club_id + list API 동작)
node ~/.claude/skills/naver-cafe-scrape/scripts/scrape_naver_cafe_cdp.mjs --cafe soho --probe

# 키워드 검색 — archive 검색 REST 가 폐기되어, ArticleListV2(전체글 최신피드)를
# --pages 만큼 페이지네이션하며 제목 grep. 키워드는 공백 분리 OR 매치.
node .../scrape_naver_cafe_cdp.mjs --cafe soho --search "쿠팡 정산" --pages 40
node .../scrape_naver_cafe_cdp.mjs --cafe soho --search "정산 수수료" --pages 40 --body   # 매치글 본문 스니펫 포함
node .../scrape_naver_cafe_cdp.mjs --cafe soho --search 정산 --pages 20 --deep            # 본문까지 grep(느림)

# 단일 글 본문
node .../scrape_naver_cafe_cdp.mjs --cafe soho --article 4064913
# club_id 알면 resolve 생략
node .../scrape_naver_cafe_cdp.mjs --club 10094408 --search 정산
```

검색 결과는 `cafe_{cafe}_search.json` 에 저장(`--out` 로 변경). 매치 = {id, subject, writer,
date, read, cmt, (bodySnippet)}.

**한계:** 카페 키워드 검색 REST 는 전부 폐기/변경됨(`cafe2/ArticleSearchList*`=API없음,
`cafe-search-api/v3·v1`=404). 그래서 검색은 "최신글 N페이지 스캔 + grep" 우회라 **과거
archive 전체 검색은 불가**. 오래된 특정 글은 글 URL/articleId 를 받아 `--article` 로 직접 fetch.

## 권장 실행 흐름

1. **확인 단계** — `--probe` 만으로 사전 조건 4가지 검증. 막히는 게시판이 있으면 사용자에게 보고하고 결정 받음.
2. **소량 테스트** — `--boards <첫 게시판> --limit 3` 로 3건만 받아 파일 형식 검증.
3. **본 스크랩 (background)** — `--days N` 으로 background 실행. 사용자가 다른 작업 가능하도록.
4. **30분 단위 wakeup** — `ScheduleWakeup` 으로 진척 점검 설정 (게시판별 page 진행 / 파일 수). cutoff 도달까지 반복.
5. **완료 보고 + 세션 요약 저장** — 사용자 mcptest 워크스페이스인 경우 `sessions/YYYY-MM-DD-{cafe}-scrape.md` 에 세션 요약 저장 (CLAUDE.md §3 규칙).

## 출력 형식

각 글은 다음 경로 구조와 형식으로 저장된다.

```
{out_dir}/{cafe_name}/{board_label_slug}/{YYYY-MM}/{article_id}.md
```

파일 내용 (frontmatter + 본문):

```markdown
---
source: cafe.naver.com/{cafe_name}
board_key: free
board_label: 자유게시판
article_id: 334844
url: https://cafe.naver.com/f-e/cafes/{club_id}/articles/334844
posted_at: 2026-05-06T14:38:20
scraped_at: 2026-05-06T16:17:13
writer_nick: ...
writer_level: Lv.2
views: 84
likes: ...
comment_count: 3
---

# 글 제목

본문 텍스트 (HTML → 평문 변환됨)
```

진행 인덱스는 `{out_dir}/INDEX_{cafe_name}.json` 에 저장되어 중단 후 재시작이 가능하다.

## 트러블슈팅 — 자주 겪는 문제

### CDP 9222 미응답
- Chrome 종료된 상태. 사용자에게 위 CDP 명령어 다시 실행 요청.

### 게시판 fetch 중 HTTP 401 발생
- 세션이 풀렸거나 (네이버 로그인 만료) 등업 부족.
- 사용자에게 카페에 직접 접속해 로그인 + 등업 상태 확인 요청.
- 등업 가능 게시판만 추려서 진행 옵션 제시.

### CDP 연결되어 있는데 로그인 안 됨
- 다른 도메인 (예: `cafe.daum.net`) 으로 들어가 있을 수 있음. CDP 명령어의 `--user-data-dir` 가 매번 동일한 경로 (`$HOME/chrome-cdp-profile`) 인지 확인.

### 글 수가 예상보다 적음
- 광고·블라인드·sticky·marketArticle 자동 필터 적용. 일반적인 운영 정책상 합리적이지만, 광고도 전부 받고 싶으면 스크립트의 `is_filtered` 함수 수정.

### 댓글이 빠져 있음
- 현재 v1 은 댓글 본문은 가져오지 않음 (commentCount 메타만 보존). 댓글이 필요하면 별도 수집 작업 필요 (네이버 댓글 API 는 별 endpoint).

## 사용자 워크스페이스가 mcptest 인 경우의 추가 규약

`/Users/kiwankim/mcptest/CLAUDE.md` 의 작업 규칙이 적용되는 경우:
- 출력 디렉토리는 `sales-safari/raw/{cafe_name}/` 로 저장
- 세션 종료 시 `sessions/YYYY-MM-DD-{cafe}-scrape.md` 에 요약 저장
- lens (분석) 는 사용자가 별도 요청할 때만 진행. 스크랩 자체는 수집까지만.

## 다른 워크스페이스인 경우

- 출력 디렉토리는 사용자가 명시한 곳, 또는 현재 작업 디렉토리의 `./raw/{cafe_name}/`
- 세션 요약 저장은 사용자가 요청할 때만
