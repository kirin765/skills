---
name: kr-sales-safari
description: 한국 커뮤니티(Velog, Disquiet, Brunch, 네이버 블로그 등)에서 SaaS 아이디어 발굴을 위한 Sales Safari를 수행한다. Mom Test 원칙에 따라 실제 고통 신호를 수집하고 SaaS 후보 아이디어를 산출한다. "한국 커뮤니티에서 SaaS 아이디어 찾아줘", "세일즈 사파리", "Velog/Disquiet 페인포인트 수집", "vibe coding 고통 신호", "한국 SaaS 기회 발굴", "어떤 불편함 있는지 조사", "한국 개발자 커뮤니티 조사" 등을 언급하면 반드시 사용한다. 주제가 있어도 없어도 실행 가능하며, 결과는 saas-viability-kr 스킬로 이어진다.
---

# 한국 커뮤니티 SaaS Sales Safari

한국 개발자·스타트업 커뮤니티에서 실제 고통 신호를 verbatim으로 수집해 SaaS 아이디어 후보를 산출한다.

## Mom Test 절대 원칙 (어기면 결과 무효)

모든 인용은 **원문 + URL + 작성자** 세 필드가 동시에 있어야 한다. 하나라도 빠지면 그 인용은 존재하지 않는 것으로 처리한다.

- Verbatim only — LLM이 고통을 생성하거나 패러프레이즈 금지
- 동일 username의 복수 게시 = 1명으로 카운트 (Phase 4 진입 전 dedup 필수)
- 3명 미만 고유 인원 = 클러스터 자격 없음 (단일 신호 노트로 분리)

## 입력

- **주제** (선택): 도메인 (예: "배포", "콘텐츠 자동화", "팀 협업")
- **주제 없음**: 한국 개발자/vibe-coder 커뮤니티 광범위 탐색

---

## Phase 1 — 검색어 생성

주제 있으면 한국어 고통 패턴 6개:
`[주제] 불편한 점`, `[주제] 문제`, `[주제] 아쉬운`, `[주제] 자동화`, `[주제] 대안 없을까`, `[주제] 툴 추천` (마지막은 기존 툴 파악 → 갭 분석용)

주제 없으면 광범위 키워드:
`vibe coding 불편`, `claude code 문제`, `1인 개발 힘든 점`, `SaaS 개발 귀찮은`, `팀 협업 툴 불편`, `자동화 안 되는`

신호어(필터): `불편`, `문제`, `아쉬운`, `안 된다`, `힘들다`, `막막하다`, `귀찮다`, `자동화`, `대안`, `없나요`

---

## Phase 2 — 소스별 수집 (병렬 실행)

가능한 소스 호출은 **한 메시지 안에 병렬 tool call로** 묶는다. 실패 소스는 건너뛰고 최종 출력의 "실패/차단 소스"에 명시.

### A. Velog — GraphQL (검증됨)

엔드포인트: `POST https://api.velog.io/graphql`, `Content-Type: application/json`

검증된 쿼리 (각 검색어마다 1회 호출):
```json
{
  "query": "query($keyword: String!) { searchPosts(keyword: $keyword) { count posts { id title body url_slug user { username } comments_count likes released_at } } }",
  "variables": { "keyword": "[검색어]" }
}
```

- 포스트 URL: `https://velog.io/@[username]/[url_slug]`
- `body` 필드에 본문 전체가 포함되므로 신호어 매칭 후 verbatim 추출 가능
- 댓글 GraphQL 쿼리는 현재 스키마에 없음 → 댓글이 필요하면 포스트 URL을 WebFetch로 가져온다
- 주의: introspection은 서버에서 차단됨 — 위 쿼리만 사용

### B. Disquiet — Playwright 전용 (API 없음)

Disquiet는 React SPA고 공개 API(`api.disquiet.io/*`)는 모두 404다. Playwright MCP로 직접 렌더링.

```
mcp__plugin_playwright_playwright__browser_navigate → https://disquiet.io/products
mcp__plugin_playwright_playwright__browser_snapshot
```

추출 대상:
- 메이커 노트의 "이런 점이 불편해요", "이런 게 아쉬워요", "이런 기능이 있었으면" 섹션
- 댓글의 unmet need 표현 ("없나요?", "됐으면 하는데", "아쉽게도")

상세가 필요한 제품은 카드 링크 따라가서 다시 navigate → snapshot.

### C. Brunch — Playwright

검색: `https://brunch.co.kr/search?q=[검색어]`
navigate → snapshot으로 결과 목록 추출. 신호어 포함된 글은 URL navigate 후 본문 전체 수집.

### D. 네이버 블로그 — Playwright

검색: `https://search.naver.com/search.naver?where=blog&query=[검색어]`
JS 렌더링 필요(WebFetch 불가). navigate → snapshot → 신호어 포함 글 본문 추출.

### E. X (Twitter) — Playwright + 쿠키

`~/.config/kr-sales-safari/.env` 에서 `X_AUTH_TOKEN`, `X_CT0` 읽는다. 파일 없거나 읽기 실패 → X 건너뛰고 실패 소스로 명시.

`mcp__plugin_playwright_playwright__browser_run_code`:
```javascript
async (page) => {
  await page.context().addCookies([
    { name: 'auth_token', value: X_AUTH_TOKEN, domain: '.x.com', path: '/', secure: true, httpOnly: true },
    { name: 'ct0', value: X_CT0, domain: '.x.com', path: '/', secure: true, httpOnly: false }
  ]);
  await page.goto('https://x.com/search?q=[검색어]&src=typed_query&f=top');
  await page.waitForSelector('article', { timeout: 8000 }).catch(() => null);
  return await page.$$eval('article', els =>
    els.slice(0, 20).map(el => ({
      text: el.innerText.slice(0, 500),
      url: el.querySelector('a[href*="/status/"]')?.href || ''
    }))
  );
}
```

검색 전략: `[검색어] lang:ko min_faves:5`, `[검색어] 불편 OR 문제 OR 아쉬운 lang:ko`

### F. WebSearch — 보완

위 소스에서 누락된 신호은 `WebSearch`로 보강:
`[검색어] "개선되었으면" OR "아쉬운 점" OR "불편해서" 한국어`

---

## Phase 3 — 인용 카드 형식

수집된 모든 인용은 이 5필드로 정리. 하나라도 빠지면 폐기.

```
- "[정확한 한국어 원문 — 수정 없음]"
  URL: [전체 URL]
  작성자: @[username] (또는 익명+플랫폼ID)
  날짜: [YYYY-MM-DD]
  플랫폼: Velog | Disquiet | Brunch | Naver | X | Web
```

90일 이상 된 인용은 끝에 `[오래됨]` 태그.

---

## Phase 4 — Dedup → 클러스터링

1. **Dedup**: 같은 username/플랫폼ID는 가장 강한 인용 1개만 남기고 나머지는 "추가 게시" 카운트로만 처리
2. **클러스터링**: 같은 고통 표현을 묶어 후보 3–5개 작성. 고유 인원 < 3명이면 클러스터 자격 미달 → 단일 신호 노트로 이동

각 후보 템플릿:
```
## 고통 후보 #N: [후보명]

**고유 인원**: N명 / **인용 수**: M개 / **추가 게시(중복저자)**: K건

**대표 인용** (서로 다른 작성자 3명 이상):
- "[원문]" — @username1 ([URL], 날짜, 플랫폼)
- "[원문]" — @username2 ([URL], 날짜, 플랫폼)
- "[원문]" — @username3 ([URL], 날짜, 플랫폼)

**현재 사용 중인 대안**: [어떤 툴/방식으로 버티는지]
**남은 갭**: [대안이 해결 못 하는 구체적 부분]
**SaaS 아이디어 한 줄**: [이 갭을 채우는 제품]

**4-체크박스**:
- [ ] 3명 이상 고유 인원이 동일 고통 표현
- [ ] 기존 부분 해결책 존재 (완전 미해결 = 시장이 너무 이름)
- [ ] 갭이 구체적·빌드 가능 (모호한 "더 좋아야" 아님)
- [ ] 반복적·지속적 고통 (일회성 이벤트 아님)
```

---

## Phase 5 — 결정 게이트

- 4/4 체크 → **빌드 추진** + `saas-viability-kr` 스킬 실행 권장
- 3/4 이하 → 미흡 항목 명시 + 추가 조사 방향 또는 도메인 피벗 제안

---

## 최종 출력 형식

```markdown
# 한국 커뮤니티 SaaS Sales Safari 결과

**조사 주제**: [주제 또는 "광범위 탐색"]
**사용 소스**: [성공한 소스 목록]
**실패/차단 소스**: [소스 — 사유]
**총 인용 수**: N개 / **고유 인원**: M명 / **조사 범위**: 최근 [N]일

## 고통 후보
[Phase 4 템플릿 반복]

## 단일 신호 노트 (고유 인원 < 3명)
- [주제]: "[원문]" — @user (URL, 날짜)

## 결정 게이트 요약
| 후보 | 고유 인원 | ✅ | 판정 |
|------|----------|----|------|
| #1 [이름] | N | 4/4 | 빌드 추진 |
| #2 [이름] | N | 2/4 | 추가 조사 |

## 다음 단계
- **빌드 추진 후보**: `saas-viability-kr` 스킬 실행 권장
- **추가 조사 필요**: [어떤 소스/키워드를 더 봐야 하는지]
- **소스 공백**: [접근 못 한 소스와 사유]
```
