---
name: dcinside-sales-safari
description: dcinside 마이너 갤러리에서 사용자가 지정한 페르소나·타겟·시장에 맞는 verbatim 고통 신호를 수집해 SaaS 클러스터 후보를 산출한다. "디시인사이드 갤러리 스크랩", "dcinside 페인포인트 발굴", "디시 갤러리 찾아줘", "자영업/셀러/학원/개발자 페르소나 페인 조사", "dcinside Sales Safari", "마이너 갤러리 verbatim 수집", "한국 micro-niche SaaS 후보 발굴" 등의 요청 시 반드시 사용한다. 한국어 직군명·타겟 키워드를 받아 활성 갤 발굴 → 페르소나 검증 → 12개월 메타 스캔 → 필터 → 본문+댓글 정밀 수집 → vocab 스코어링 → Tier 1 클러스터링까지의 7단계 파이프라인을 실행한다. 결과는 saas-viability-kr 스킬로 이어져 시장성 ABC 평가 가능. kr-sales-safari (Velog/Disquiet 등) 와 보완 관계 — 익명 갤 페르소나가 더 솔직하고 깊은 페인을 표출하는 점에서 차별.
---

# dcinside Sales Safari

dcinside 마이너 갤러리(mgallery)는 한국 익명 커뮤니티 중 직군별 페르소나 신호가 가장 두꺼운 채널이다. 익명성 덕분에 사장·강사·셀러·개발자가 본인의 진짜 페인을 verbatim으로 토로한다. 이 스킬은 그 신호를 SaaS 후보로 변환하는 검증된 파이프라인이다.

## Mom Test 절대 원칙

모든 인용은 **원문 + URL + 작성자(닉/IP 두옥텟 또는 UID)** 세 필드 동시 보유. 하나라도 빠지면 그 인용은 존재하지 않는 것으로 처리.

- Verbatim only — LLM이 페인을 생성하거나 패러프레이즈 금지
- 동일 작성자 dedup 후 카운트 (Phase 7 진입 전 필수)
- 3명 미만 고유 인원 = 클러스터 자격 없음 → 단일 신호 노트

## 입력

- **페르소나/타겟**: 한국어 직군명 (예: "1인 카페 사장", "초보 셀러", "학원강사", "백엔드 개발자") — 필수
- **갤 ID 직접 지정** (선택): `instructors`, `ptutor` 같은 알려진 갤 ID가 있으면 Phase 1 일부 생략

알려진 갤 카탈로그는 `references/known-galleries.md` 참조. 새 페르소나면 무조건 Phase 1부터 시작.

## 출력 위치

기본 작업 디렉토리: `dcinside/` (현재 디렉토리 기준 또는 사용자 지정)

```
dcinside/
├── raw/
│   ├── {gall}_meta.jsonl         # Phase 2 결과
│   └── {gall}_full.jsonl         # Phase 4 결과
├── signals/
│   ├── all-scored.jsonl          # Phase 5 결과
│   ├── top-{N}.md                # Phase 5 verbatim 검토용
│   └── tier1_bundle.txt          # Phase 6 클러스터링 입력
├── clusters/
│   ├── INDEX.md                  # 클러스터 요약
│   └── cluster-N-{name}.md       # Phase 7 결과
└── pain-vocab.yml                # 작업 시점 vocab (페르소나별 튜닝)
```

작업 시작 시 빈 디렉토리이면 그대로 시작하고, 기존 결과가 있으면 갤별 분리(`signals_v1_xxx/`로 백업) 후 진행.

---

## Phase 1 — 갤러리 발굴 + 페르소나 검증 ★ 가장 중요

페르소나 의도 → 한국어 직군 키워드 → DC 검색 → 후보 갤 ID → page1 샘플 제목 직접 검증.

### 1.1 검색어 설계

페르소나에서 직군명·도메인 단어 3~6개 추출.

| 페르소나 | 검색어 예시 |
|---|---|
| 1인 카페 사장 | "카페 사장", "자영업", "음식점", "소상공인" |
| 초보 셀러 | "스마트스토어", "쿠팡 셀러", "위탁판매", "사입" |
| 학원강사 | "학원강사", "원장", "과외", "사교육" |
| 백엔드 개발자 | "백엔드", "스프링", "취준 개발자", "신입 개발자" |

### 1.2 Probe 실행

```bash
python3 scripts/probe_galleries.py 학원강사 과외 원장
```

출력에서 row 30+ 활성 갤 + 갤 제목 + page1 샘플 제목 5개를 제시. **사람이 직접 페르소나 일치 여부 판정** (또는 사용자에게 확인 받기).

### 1.3 페르소나 검증 체크리스트 (4점 모두 통과해야 진행)

1. 샘플 제목 화자가 우리가 찾는 페르소나(사장/강사/셀러)인가?
2. 갤 `<title>` 메타가 의도한 도메인과 맞는가? (예: `coffee` = 커피 마니아 갤 ≠ 카페 사장)
3. 정치/혐오/잡담 비중이 절반 이하인가?
4. 페이지1 row 30+ 인가? (10 미만이면 죽은 갤)

**불일치 시 즉시 다른 갤 후보로 이동.** `references/persona-mismatch-cases.md`에 함정 사례 다수.

---

## Phase 2 — 메타 스캔 (12개월)

각 검증된 갤마다:

```bash
python3 scripts/fetch_meta.py --gall {GALL_ID} --months 12
```

결과: `raw/{GALL_ID}_meta.jsonl` (post_num, title, writer_nick, writer_ip, writer_uid, date_full, view, recommend, comment_count, url 등)

### 거대 갤 / 죽은 갤 처리

- 12개월 메타 5,000건 미만 → 정상 진행
- **5,000건 ~ 50,000건**: filter 통과율 확인 후 detail 임계값 강화 결정
- **50,000건+ (예: coffee 167k)**: 페르소나 불일치 의심 — 샘플 다시 확인
- **빈 페이지 무한 루프** (selfemployed 사례): page count 10,000+ 발견 시 즉시 `pkill`

병렬 실행: 갤 여러 개 동시 스캔 가능 (`run_in_background=true`로 분리).

---

## Phase 3 — 필터 (engagement 기반)

기본 임계값: `comment_count >= 6 OR recommend >= 2`

```python
import json
total = pf = 0
with open(f"raw/{gall}_meta.jsonl") as f:
    for line in f:
        d = json.loads(line)
        total += 1
        if d["comment_count"] >= 6 or d["recommend"] >= 2:
            pf += 1
print(f"{gall}: {total} total, {pf} pass ({100*pf/total:.1f}%)")
```

| 통과 건수 | 처리 |
|---|---|
| < 30 | 갤이 너무 작음 — 클러스터링 가능성 낮음, 단일 신호로 |
| 30 ~ 2,000 | 정상 — 그대로 detail fetch |
| 2,000 ~ 5,000 | 임계값 강화 검토 (`comment≥10 OR recommend≥3`) |
| 5,000+ | 강화 필수 (`comment≥15 OR recommend≥5`) |

`references/workflow-examples.md`의 backend(32k → 1,959) 사례 참조.

---

## Phase 4 — Detail Fetch (본문 + 댓글 inline)

```bash
python3 scripts/fetch_detail.py --gall {GALL_ID}                            # 기본 임계값
python3 scripts/fetch_detail.py --gall {GALL_ID} --min-comments 15 --min-recommend 5  # 강화
```

### 모바일 엔드포인트 사용 이유

데스크탑 view 페이지는 댓글이 AJAX (e_s_n_o CSRF 토큰 필요) → 복잡. 모바일 `m.dcinside.com/board/{gall}/{post_num}`은 단일 GET으로 본문(`div.thum-txtin`) + 댓글(`.all-comment-lst li[class*=comment]`) inline 반환 → 단순.

결과: `raw/{GALL_ID}_full.jsonl` (메타 + body + comments[])

속도: 약 1.5초/건. 1,000건 = 25분, 2,000건 = 50분. 백그라운드 실행 권장.

---

## Phase 5 — Vocab 스코어링

`pain-vocab.yml`에 5개 카테고리 키워드 정의. 각 카테고리별 가중치:

| 카테고리 | 가중치 | 의미 |
|---|---|---|
| explicit_gap | 3 | 직접 솔루션 갈망 ("왜 없", "있으면 좋겠") — 가장 강한 신호 |
| time_money_waste | 2 | 시간/돈 낭비 (이미 비싼 우회책 사용 중 = 결제 의향 증명) |
| workaround_share | 1 | 우회책 공유 (현재 솔루션 부족함 노출) |
| emotion_high | 1 | 감정 강도 (단독으로는 약한 신호) |
| peer_validation | 0 (별도 카운트) | 동의·공감 ("ㄹㅇ", "나도 그래") |

```bash
python3 scripts/extract_signals.py --galls {GALL_A} {GALL_B} --top 300
```

`combined_score = body_score + 0.5 × comment_pain_score + validators_count`

결과:
- `signals/all-scored.jsonl` — 전체 점수
- `signals/top-{N}.md` — 상위 N건 verbatim 검토용

### 페르소나별 vocab 튜닝 (필수 사항)

기본 `pain-vocab.yml`은 음식점 + 셀러 + 학원 어휘 mixed. **새 페르소나 진입 시 vocab에 도메인 어휘 5~10개 추가하지 않으면 신호 1/5로 줄어듦** (V2 instructors 사례: 추가 전 Tier 1 4건 → 추가 후 24건).

페르소나별 추천 어휘 표는 `references/workflow-examples.md` "Vocab 튜닝 가이드" 참조.

vocab 수정 후 재스코어 → 점수 분포 재확인.

---

## Phase 6 — Tier 1 Bundle 생성

스코어 ≥ 6 (Tier 1) 글을 LLM 클러스터링용 압축 텍스트로 묶기.

```bash
python3 scripts/build_tier1_bundle.py
```

결과: `signals/tier1_bundle.txt`

- 본문 350자, 댓글 200자, 댓글 5개/글 cap
- 한 글당 헤더 (#N | gall | s=score | author=key | val=N) + TITLE/URL/BODY/COMMENTS

Tier 1 100건 미만이면 단일 bundle, 이상이면 갤별 분리.

---

## Phase 7 — 클러스터링 + 4-체크박스 검증

`tier1_bundle.txt`를 읽고 같은 페인 표현을 묶어 후보 3~6개 작성.

### 클러스터 4-체크박스 (모두 통과해야 자격)

- [ ] 3명 이상 고유 인원 (uid 또는 ip+nick dedup 후)
- [ ] 기존 부분 해결책 존재 (완전 미해결 = 시장이 너무 이름)
- [ ] 갭이 구체적·빌드 가능 (모호한 "더 좋아야" 아님)
- [ ] 반복적·지속적 (일회성 이벤트 아님)

### 클러스터 파일 템플릿

`clusters/cluster-{N}-{name}.md`:

```markdown
# 클러스터 #N — {이름}

**갤**: {gall}
**고유 작성자**: M명 / **인용 수**: K개

## 대표 인용 (서로 다른 작성자 3명+)

- "verbatim 원문" — @nick(ip) ([URL](...), 날짜)
- ...

## 현재 사용 중인 대안

- 갤 직접 묻기, 외주, 강의팔이 등 (관찰된 우회책)

## 남은 갭

- 부분 해결책이 못 채우는 구체적 부분

## SaaS 아이디어 한 줄

**{제품명}** — {핵심 기능}

## 4-체크박스

- [x] 3명 이상 고유 인원 (M명 ✓)
- [x] 기존 부분 해결책 존재
- [x] 갭이 구체적·빌드 가능
- [x] 반복적·지속적

**판정: 4/4 — 빌드 추진 후보**
```

3명 미만은 INDEX.md "단일 신호 노트" 섹션에 보존.

### Sub-segment 분류 (선택)

페르소나 내부 sub-segment(업종·판매형태 등) 분포 보려면:

```bash
python3 scripts/classify_subsegments.py --gall {GALL} --score-min 3
# 또는 --config classify.yml 로 페르소나별 사전 주입
```

업종 × 페인 cross-tab으로 MVP 우선 sub-페르소나 도출 (`workflow-examples.md` V1 자영업 5개 sub-segment 분석 참고).

---

## 최종 출력 (INDEX.md)

```markdown
# dcinside Sales Safari 결과

**조사 페르소나**: {페르소나}
**사용 갤**: {gall1}, {gall2} ...
**실패/제외 갤**: {gall} — {사유}
**총 인용 수 (Tier 1)**: N개 / **고유 작성자**: M명 / **조사 범위**: 12개월

## 클러스터 (4/4 통과)

| # | 이름 | 갤 | 고유 인원 | 빌드 난이도 |
|---|---|---|---|---|
| 1 | ... | ... | N | 하/중 |

## 단일 신호 노트 (3명 미만)
- ...

## 다음 단계
- 빌드 추진 후보 → `saas-viability-kr` 스킬로 ABC 평가
- 추가 페르소나 → 본 스킬 재실행
```

---

## 결정 게이트 요약

| 통과 클러스터 | 다음 액션 |
|---|---|
| 4/4 통과 1+ | `saas-viability-kr` 스킬 실행 권장 |
| 3/4 이하만 | 미흡 항목 명시 + 추가 조사 또는 페르소나 피벗 제안 |
| 클러스터 0개 | 페르소나 재정의 또는 다른 채널(kr-sales-safari) 시도 |

---

## 작업 중 자주 빠지는 함정

1. **페르소나 검증 생략** → 17만건 짜리 마니아 갤(coffee) 헛스캔
2. **vocab 튜닝 생략** → 신호 1/5로 줄어들고 잘못된 결론
3. **거대 갤 기본 임계값** → 4시간 detail fetch 후 후회
4. **죽은 갤 무한 루프** → 16,000+ page 도는 동안 데이터 없음
5. **dedup 누락** → 같은 작성자 3개 글로 Tier 1 가짜 4-체크박스 통과
6. **댓글 무시** → comment_pain_score 빠짐, 신호 두께 절반

자세한 함정 사례는 `references/persona-mismatch-cases.md`.

---

## 보조 자료

- `scripts/probe_galleries.py` — 갤 발굴 + 페르소나 검증 헬퍼
- `scripts/fetch_meta.py` — list 페이지 메타 스캔
- `scripts/fetch_detail.py` — 모바일 본문+댓글 정밀 수집
- `scripts/extract_signals.py` — vocab 스코어링·랭킹
- `scripts/build_tier1_bundle.py` — 클러스터링 입력 압축
- `scripts/classify_subsegments.py` — sub-segment 분류 cross-tab
- `references/pain-vocab.yml` — 5개 카테고리 어휘 (페르소나별 튜닝 시작점)
- `references/known-galleries.md` — 검증된 갤 카탈로그
- `references/persona-mismatch-cases.md` — 페르소나 불일치 함정 카탈로그
- `references/workflow-examples.md` — 4개 페르소나 분석 사례 + vocab 튜닝 가이드 + 4-체크박스 기준

---

## 사용 예시

```
사용자: "1인 카페 사장 페르소나로 dcinside Sales Safari 돌려줘"

1. Phase 1: probe_galleries.py 실행 ("카페 사장", "자영업", "소상공인", "음식점")
   → coffee 마갤은 마니아 갤이라 제외 (페르소나 불일치)
   → sajang 마갤 + smallbusiness 마갤이 활성 + 페르소나 일치
   → 사용자에게 확인 후 진행
2. Phase 2: 두 갤 12개월 메타 병렬 스캔 (백그라운드)
3. Phase 3: 필터 통과 건수 확인 → 둘 다 정상 범위 → detail 진행
4. Phase 4: detail fetch (병렬 백그라운드)
5. Phase 5: vocab에 카페 도메인 어휘 추가 (원두·머신·홀딩·1인운영) → 스코어
6. Phase 6: Tier 1 bundle 생성
7. Phase 7: bundle 읽고 4~6개 클러스터 작성, 4/4 통과만 채택
8. INDEX.md + 다음 단계 (saas-viability-kr) 안내
```
