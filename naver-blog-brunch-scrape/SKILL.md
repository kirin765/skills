---
name: naver-blog-brunch-scrape
description: 네이버 블로그 (blog.naver.com) 와 브런치 (brunch.co.kr) 에서 검색어 목록을 받아 최근 N개월 내의 글을 일괄 스크랩하는 워크플로우. 사용자가 "네이버 블로그 X 키워드 스크랩", "브런치 Y 검색어 글 모아줘", "blog.naver.com 자료 수집", "검색어 batch 로 블로그 글 수집" 같은 요청을 할 때 사용한다. 출력은 frontmatter + 본문 형식의 md 파일 (`raw/{소스}/YYYY-MM/{id}.md`). 결제 의향·페인 분석·자료 조사 등 후속 분석 단계와 무관하게 단순 자료 수집 자체에 초점을 둔 범용 도구.
---

# naver-blog-brunch-scrape

네이버 블로그 + 브런치 두 채널에서 사용자가 지정한 **검색어 목록** 으로 최근 N 개월치 글을 받아 md 파일로 저장한다.

## When to use

- 사용자가 검색어 (또는 검색어 batch) 로 네이버 블로그 또는 브런치 글을 수집하라고 요청할 때
- 두 채널 중 하나만, 또는 둘 다 수집해야 할 때
- 출력 형태가 `raw/{소스}/YYYY-MM/{id}.md` (frontmatter + 본문) 가 적절할 때
- 빠른 자료 수집·코퍼스 구축이 목적인 경우 (분석 자체는 별도 단계)

## When NOT to use

- 단일 글 본문 추출만 필요한 경우 → `firecrawl-scrape` 등 단일 페이지 도구
- 카페 (cafe.naver.com) 게시판 스크랩 → `naver-cafe-scrape` skill
- 여러 사이트에 걸친 일반 웹 검색 → `firecrawl-search` 등

## Inputs

- **검색어 목록** (필수) — 쉼표로 분리된 문자열 또는 텍스트 파일
  - 예: `"엑셀 자동화,CSV,VBA 한계"` 또는 `--queries-file queries.txt` (한 줄당 하나)
- **기간** (선택, default 180일) — `--days N`
- **소스** (선택, default 둘 다) — `--source naver_blog` | `brunch` | `both`
- **출력 디렉토리** (선택, default `./raw`) — `--output-dir <경로>`
- **검색어당 최대 글 수** (선택, default 200) — `--max-per-query N`

## Workflow

### 1단계 — 환경 점검

네이버 블로그를 Open API 로 받으려면 `NAVER_OPEN_API_CLIENT_ID` + `NAVER_OPEN_API_CLIENT_SECRET` 환경변수 또는 `~/.naver_api_credentials` 파일이 필요하다. 자세한 발급·설정 방법은 `references/naver-open-api-setup.md` 참조. 키가 없으면 자동으로 HTML 검색 결과 파싱으로 fallback 한다.

브런치는 인증 불필요 (공식 검색 응용프로그램 인터페이스 `api.brunch.co.kr/v1/search/article` 사용).

### 2단계 — 검색어·기간 확정

사용자가 검색어와 기간을 명시했으면 그대로 사용. 모호한 경우 (예: "엑셀 관련 글 모아줘") 다음을 명확화:
- 정확한 검색어 list (페인 키워드·솔루션 키워드 분리 제안)
- 기간 (3개월 / 6개월 / 12개월 중 default 6개월)
- 두 채널 모두인지 한 쪽인지

### 3단계 — 스크립트 실행

#### 양쪽 다
```bash
python scripts/scrape_both.py \
  --queries "엑셀 자동화,CSV,VBA 한계" \
  --days 180 \
  --output-dir raw
```

#### 네이버 블로그만
```bash
python scripts/scrape_naver_blog.py \
  --queries "엑셀 자동화,CSV" \
  --days 180 \
  --output-dir raw/naver_blog
```

#### 브런치만
```bash
python scripts/scrape_brunch.py \
  --queries "엑셀 자동화,CSV" \
  --days 180 \
  --output-dir raw/brunch
```

긴 수집 (검색어 10+ 개 또는 기간 12개월) 은 백그라운드 launch 권장:
```bash
nohup python scripts/scrape_both.py --queries "..." --days 180 > scrape.log 2>&1 &
```

### 4단계 — 결과 점검

```bash
# 보드별·소스별 글 수 통계
find raw -type f -name "*.md" | sed 's|/[^/]*$||' | sort | uniq -c

# 최근 글 제목 확인
find raw -type f -name "*.md" -exec head -10 {} \; | grep "^title:"
```

## Output format

각 글은 `raw/{source}/{YYYY-MM}/{id}.md` 형식. `source` 는 `naver_blog` 또는 `brunch`. `id` 는 네이버 블로그의 경우 `{bloggerid}_{logno}`, 브런치의 경우 `{userid}_{articleno}`.

```markdown
---
source: naver_blog
search_q: 엑셀 자동화
url: https://blog.naver.com/userid/12345
title: 엑셀 자동화 첫 발걸음
author: userid
posted_at: 2026-01-15
scraped_at: 2026-05-07T12:34:56
---

# 엑셀 자동화 첫 발걸음

본문 첫 단락...

본문 둘째 단락...
```

브런치 글은 `posted_at` 이 timestamp 변환 후 ISO 형식, `description` 필드 (검색 응용프로그램 인터페이스 contentSummary 220자) 가 본문으로 들어간다. 풀 본문은 카카오 로그인 필요해서 기본 미수집 — 필요 시 CDP 활용 가능 (별도 옵션).

## Edge cases

- **네이버 블로그 OG description / 본문 추출 실패** — iframe 구조 또는 권한 제한. 이 경우 search.naver.com 결과의 description (snippet 200자 정도) 만 frontmatter `description` 필드로 저장하고 본문은 빈 상태로 남김
- **브런치 본문 0byte** — 카카오 자동 로그인 redirect. 검색 응용프로그램 인터페이스 `contentSummary` (220자 발췌) 가 대신 들어감
- **검색어당 결과 1000건 초과** — 네이버 Open API 는 start ≤ 1000 제한. 6개월 cutoff 으로 보통 충분하지만 인기 키워드는 cutoff 없이 1000건까지만
- **rate limit** — 네이버 Open API 는 일 25,000건 제한. 검색어 10개 + 기간 12개월 = 약 5,000건. 통상 안전. 페이지 간 0.3초 sleep 적용
- **중복 글** — 같은 글이 검색어 두 개에 걸리면 `id` 기준 dedup. 첫 매칭된 검색어만 frontmatter 에 기록

## Files

- `scripts/scrape_naver_blog.py` — 네이버 블로그 단독 (Open API → HTML fallback 자동)
- `scripts/scrape_brunch.py` — 브런치 단독
- `scripts/scrape_both.py` — 두 스크립트 순차 호출 wrapper
- `references/naver-open-api-setup.md` — Open API 키 발급·환경변수 설정 가이드

## Why this skill exists separately

`firecrawl-search` 같은 일반 웹 검색 도구로도 비슷한 일이 가능하지만, 네이버 블로그·브런치는 한국어 검색·본문 파싱 관행이 국지적이라 전용 진입점이 더 빠르고 정확하다 (네이버 PostView iframe 구조, 브런치 검색 응용프로그램 인터페이스, 카카오 자동 로그인 redirect 등). `naver-cafe-scrape` 와는 채널 (블로그·매거진 vs 카페 게시판) 이 다른 sibling.
