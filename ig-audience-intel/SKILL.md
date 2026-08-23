---
name: ig-audience-intel
description: >-
  Osintgraph(IG 소셜그래프 OSINT 도구)로 경쟁/대표 Instagram 계정의 팔로워·팔로잉·게시물을 Neo4j에 raw 수집한 뒤
  (Gemini 불필요), 고정 Cypher로 ①코어 오디언스 오버랩 ②공통 관심사·커뮤니티 ③허브 인플루언서 ④해시태그·콘텐츠
  시그널을 뽑아 **IG 홍보용 오디언스·콘텐츠 인텔리전스 리포트**를 만들어 brain(~/projects/misc/brain)에 저장하는 워크플로우.
  사용자가 "인스타 홍보 자료 수집", "IG 오디언스 분석", "경쟁 인스타 계정 팔로워 분석해줘", "내 니치 인스타에 뭘 올려야 할지",
  "osintgraph로 인스타 ~~", "IG 콘텐츠/해시태그 전략용 데이터", "instagram audience/competitor intelligence",
  "IG 인플루언서·콜라보 후보 찾아줘" 같은 요청을 할 때 발동. **집계형 마케팅 인텔리전스 전용** — 개인 타겟 대량
  DM/팔로우 리스트는 만들지 않는다. 부계정 IG + Neo4j 필요(제로부터면 references/setup.md). 단순 한 플랫폼 게시·앱
  출시 멀티채널 홍보는 app-launch-promo, X 검색 수집은 x-cdp-search, 키워드 수요는 naver-api를 쓴다.
---

# IG Audience & Content Intelligence (via Osintgraph)

시드 IG 계정(내 니치의 경쟁/대표 계정 2~6개)을 받아 → Osintgraph로 그래프를 raw 수집 → 4지표 Cypher → 홍보 리포트.
산출물은 brain의 `reports/`(리포트) + `raw/`(추출 데이터)로 들어간다.

## ⛔ 가드레일 (먼저 읽고, 어기지 말 것)
1. **부계정으로만.** Osintgraph는 Firefox에 로그인된 계정으로 스크랩한다 = IG ToS 위반 + 정지 위험. **메인 홍보 계정 금지.** `run_intel.py`는 수집 전 설정된 IG 계정명을 출력하고 `--yes` 없이는 수집을 거부한다 — 사용자에게 "이거 부계정 맞아?" 확인받고 진행.
2. **집계 전용.** 산출은 오버랩 카운트·상위 N 계정(그 자체가 공개·대형)·해시태그 같은 **집계 인사이트**다. 개인을 골라 대량 DM/대량 팔로우하는 타겟 리스트는 만들지 않는다. 사용자가 그걸 요구하면 거절하고 집계 방향으로 되돌린다.
3. **숫자는 방향성.** 팔로워/팔로잉은 스크랩 상한 내 표본, likes·comments는 IG 제약상 부분값. 리포트에서 절대수치 단정 금지.
4. **레이트리밋 유지.** `--rate-limit` 항상 켜고, 6시간 이상 연속 스크랩 금지(정지 회피).

## 전제 확인 (제로부터면 setup)
실행 전 빠르게 점검 — 안 돼 있으면 [references/setup.md](references/setup.md)로 안내(부계정 워밍업 → Neo4j(Aura/Docker) → `pipx install osintgraph` + `pipx inject osintgraph neo4j` → `osintgraph setup instagram/neo4j`).
- [ ] 부계정 IG가 Firefox에 로그인 + 워밍업됨
- [ ] Neo4j 구동 + 접속정보 확보
- [ ] `osintgraph` 설치됨, 같은 env에 `neo4j` 드라이버 importable
- [ ] `osintgraph setup instagram/neo4j` 완료

## 워크플로우

### 1) 입력 확정
- 사용자에게 **시드 계정 2~6개**(경쟁/대표 IG 핸들)와 **니치 라벨**을 받는다. (시드가 곧 분석 모집단 — 같은 니치로 일관되게.)
- 노브: `--explore N`(허브/관심사 보강, 무겁다, 기본 off) · `--limit-follower/-followee/-post` · `--min-seeds`(공통 임계, 기본 2) · `--rate-limit`.
- **콘텐츠 전략(§3)이 주 산출물이면 `--limit-post 30~50`** 으로 올려라(기본 10은 패턴 역설계엔 표본 부족). rate-limit 시간 트레이드오프 있음.

### 2) 수집 + 추출 (한 번에)
부계정 확인을 받은 뒤:
```bash
python3 ~/.claude/skills/ig-audience-intel/scripts/run_intel.py \
  SEED_A SEED_B SEED_C \
  --niche "<niche-label>" \
  --out "/Users/kiwankim/projects/misc/brain/raw/ig-audience/<niche>-<YYYY-MM-DD>" \
  --rate-limit 200 --yes
```
- `osintgraph`/`neo4j`가 설치된 env에서 실행(pipx면 `pipx run --spec osintgraph python ...`가 아니라, neo4j를 inject했으면 그냥 시스템 python에서 creds 자동탐색이 되는지 먼저 시도; 안 되면 venv 활성화 후 실행).
- 수집은 길고 resumable하다(중단되면 같은 명령 재실행 = 이어받음). 대형 계정은 `--limit-follower`를 낮춰 1차 표본부터.
- 이미 수집돼 있으면 `--extract-only`로 Cypher만 재실행.
- 산출: `--out` 디렉터리에 `seed_profile / core_audience / audience_overlap_matrix / shared_interests / hub_centrality / top_hashtags / top_posts / seed_content_profile`의 `.json`+`.csv`, 그리고 `summary.json`.

### 3) 커버리지 검증
`seed_profile.json`을 먼저 보고 각 시드의 `followers_scraped/followees_scraped/posts_scraped`가 모두 true인지 확인. false면 그 시드는 데이터 불완전 → 재수집(`run_intel.py ... --extract-only` 말고 수집 재실행)하거나 리포트에서 명시.

### 4) 합성
지표 JSON + `top_posts`의 캡션 샘플을 읽고 [references/report_template.md](references/report_template.md)를 채운다:
- **1. 코어 오디언스(사이징)** — `core_audience`(시드 ≥min_seeds 동시 팔로우 = 타겟 규모·도달 노드) + `audience_overlap_matrix`(시드 간 경쟁/인접도). *콘텐츠가 아니라 타겟 사이징.*
- **2. 관심사·커뮤니티 + 콜라보** — `shared_interests`(공통 팔로우, `category`로 묶어 커뮤니티/브랜드 맵) + `top_mentions`(캡션 @멘션 = 콜라보 1순위) + (explore 시) `hub_centrality`.
- **3. 콘텐츠 전략** — `top_hashtags`(태그 세트) + `seed_content_profile`(포맷·**오가닉** 벤치마크) + `posting_times`(언제 올릴까, UTC→KST) + `top_posts`(먹히는 패턴, *표본 적으면 가설*).
- **4. 30일 액션** — 콘텐츠 캘린더 시드 · 해시태그 A/B · 아웃리치 후보 Top N(`top_mentions` 기반) · 다음 수집 계획(explore/limit 상향).

### 5) brain에 저장 (AGENTS.md 워크플로우)
1. 추출 디렉터리는 이미 `brain/raw/ig-audience/<niche>-<date>/`에 있게 `--out`을 줬다(불변 소스).
2. 리포트를 `brain/reports/ig-audience-<niche>-<YYYY-MM-DD>.md`로 저장 — `report_template.md`의 frontmatter(`type: report`, `status: stable`, `created/updated`, `tags`) 채워서.
3. `brain/wiki/index.md`의 `## 📤 Reports` 섹션에 `- [[ig-audience-<niche>-<date>|IG 오디언스 인텔 — <niche>]]` 한 줄 추가.
4. `brain/wiki/log.md`에 append: `query: IG 오디언스 인텔 — <niche> (시드 N개, Osintgraph)`.
5. `cd brain && python3 bin/lint.py`로 점검 후 `git commit`(brain은 post-commit 훅으로 자동 push) — 메시지 `query: IG 오디언스·콘텐츠 인텔 — <niche>`.
- (의심되면 brain의 컨벤션은 `brain/AGENTS.md` + `obsidian-vault-dialect` 스킬을 따른다.)

## 지표가 그래프 어디서 나오나 (참고)
- FOLLOW 방향(검증됨): `(follower)-[:FOLLOWS]->(followee)`.
- 코어 오디언스 = 시드들의 **팔로워** 교집합. 관심사 맵 = 시드들의 **팔로잉** 교집합. 콜라보(`top_mentions`)·해시태그·포스팅타임 = 시드 **게시물**. 전부 시드 discover만으로 계산됨.
- 허브 중심성은 discover만으론 관심사 맵에 수렴 → `run_intel.py`가 `--explore` 없으면 **자동 생략**하고, explore로 이웃 팔로우 엣지를 채울 때만 실행.
- `category`/`bio`는 풀 discover된 계정에만 채워짐(스텁은 null) → explore가 보강.
- 전체 쿼리: [references/queries.cypher](references/queries.cypher) (Neo4j Browser에서 `:param`으로 직접 돌려도 됨).

## 파일
- `scripts/run_intel.py` — 수집(`osintgraph discover/explore`, AI 스킵) + 추출(Cypher→JSON/CSV) 래퍼.
- `references/queries.cypher` — 4지표 Cypher (단일 소스; run_intel.py가 `// name:`로 분할 실행).
- `references/report_template.md` — 리포트 스켈레톤.
- `references/setup.md` — 제로부터 셋업 가이드.
