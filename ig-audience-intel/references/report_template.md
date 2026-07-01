---
type: report
status: stable
created: {DATE}
updated: {DATE}
tags: [ig, audience-intel, osintgraph, {niche}, marketing]
---
# IG 오디언스·콘텐츠 인텔리전스 — {niche} ({DATE})

> 방법: Osintgraph로 시드 {N}개 계정의 팔로워·팔로잉·게시물을 Neo4j에 raw 수집(AI 분석 미사용) → 고정 Cypher 4지표 → 합성.
> 시드: {seed_list}  ·  수집 범위: follower/followee 각 {limit}, post {post_limit}, explore={explore}
> 데이터 한계: 팔로워/팔로잉은 스크랩 상한 내 표본, likes·comments는 Instagram 제약상 부분값 — **방향성**으로 읽을 것. 집계 분석 전용.
> ⚠ 콘텐츠 시그널(해시태그·평균 인게이지먼트·먹히는 패턴)은 **시드당 약 {post_limit}개(기본 10) 게시물 표본** — 패턴은 가설 수준, 본인 계정 A/B로 검증할 것. §3을 산출물로 쓸 땐 수집 시 `--limit-post 30~50` 권장.
> 관련: [[app-portfolio]] · [[solo-dev-korea-marketing-2026-06-24]]

## TL;DR
- (3~5줄: 코어 오디언스는 누구이고, 어떤 관심사/커뮤니티로 묶이며, 콘텐츠·해시태그 전략의 핵심 한 줄.)

## 1. 코어 오디언스 — 사이징·도달 (콘텐츠 아님)
- 시드 {min_seeds}곳 이상을 동시 팔로우하는 계정 = 최고 의도 타겟층의 **규모 추정**과 대표 검증계정 리스트. (무엇을 올릴지가 아니라 타겟이 얼마나 크고 누가 도달 노드인지)
- 시드 간 오디언스 오버랩 매트릭스 → 누가 진짜 경쟁이고 누가 인접 니치인지.
- (출처: `core_audience.json`, `audience_overlap_matrix.json`)

## 2. 관심사·커뮤니티 맵 + 콜라보 (뭘 좋아하나 / 누구와 손잡나)
- **관심사·커뮤니티**: 여러 시드가 공통 팔로우하는 계정 = 니치를 정의하는 인플루언서·브랜드·커뮤니티·콘텐츠 소스. `category`(비즈니스 카테고리)로 묶어 커뮤니티/브랜드 맵을 만든다 → 콘텐츠 주제 클러스터·노출 채널.
- **콜라보 숏리스트**: 시드들이 캡션에서 실제 @멘션하는 계정 = 가장 직접적인 협업·언급·리포스트 후보(팔로우 추론보다 신뢰도 높음). 아웃리치 1순위.
- (explore 켠 경우) **허브 게이트키퍼**: 보강된 중심성 상위. *discover-only면 생략됨*(관심사 맵과 동일해짐).
- (출처: `shared_interests.json`, `top_mentions.json`, explore 시 `hub_centrality.json`)

## 3. 콘텐츠 전략 (뭘, 언제, 어떻게 올릴까)
- **해시태그 세트**: 시드들이 실제로 쓰는 태그 상위 — 빈도·평균 좋아요 기준 추천 묶음.
- **포맷·벤치마크**: 영상 비중, 게시 빈도, **오가닉 평균 인게이지먼트**(`avg_likes_organic` — 스폰서 제외한 현실적 기준선; 블렌드 평균은 유료도달로 부풀려짐).
- **포스팅 윈도우**: 시드 게시물의 시간대(UTC, KST=+9)별 평균 인게이지먼트 상위 = "언제 올릴까".
- **먹히는 콘텐츠 패턴**: 인게이지먼트 상위 게시물 캡션에서 역설계한 주제/후크/포맷 — **표본 {post_limit}개 기준, 가설로 취급**.
- (출처: `top_hashtags.json`, `seed_content_profile.json`, `posting_times.json`, `top_posts.json`)

## 4. 30일 액션
- [ ] 콘텐츠 캘린더 시드: (주제 클러스터 → 주차별 포스트 아이디어)
- [ ] 해시태그 세트 A/B: (코어 N개 + 롱테일 M개)
- [ ] 아웃리치/콜라보 후보 Top N: (관심사 맵에서 — 팔로우·언급·협업 제안)
- [ ] 다음 수집: explore 켜서 허브 보강 / 시드 추가 / follower 상한 상향

## 부록 — 데이터
- 추출물: `raw/ig-audience/{niche}-{DATE}/*.json|csv`
- 시드 커버리지: `seed_profile.json` (각 시드 followers/followees/posts 스크랩 완료 여부)
