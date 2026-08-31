---
name: english-scan
description: >-
  Passively logs the user's OWN messages (their Korean/English answers and
  requests — never the agent's) verbatim into an English-usage corpus at
  ~/.dsh/english-log/corpus.md, in EVERY session. On "what's the problem with
  my english?", "내 영어 어때?", "영어 스캔", "영어 피드백" or any request to
  review/check the user's English, analyzes the recorded corpus: corrects
  errors (grammar, vocabulary, naturalness, before → after) and profiles
  English proficiency (strengths, repeated weak patterns, estimated level,
  trend vs. the last analysis), then appends the analysis to
  ~/.dsh/english-log/analysis.md.
---

# english-scan — 세션 영어 로그 + 분석

사용자가 쓴 메시지를 매 세션 로그로 쌓아 두고, 사용자가 물을 때 그 로그로 영어 실력을 진단하는 스킬이다. 캡처는 항상, 분석은 요청이 있을 때만 한다.

## 캡처 — 매 세션, 항상

**사용자가 직접 쓴 메시지만** 로그에 쌓는다. 에이전트(자기 자신)의 답변은 절대 기록하지 않는다.

- 대상 파일: `~/.dsh/english-log/corpus.md`. 없으면 `.dsh/english-log/` 디렉토리와 함께 생성한다.
- 매 사용자 턴이 끝나면, 그 턴의 사용자 메시지를 아래 형식으로 파일 **끝에 추가**한다. 기존 내용은 고치지 않는다.

  ```md
  ## 2026-08-31
  - 14:02 [EN] I want to make a skill that scans my english.
  ```

- 언어 태그: 한글 위주 `[KO]`, 영어 위주 `[EN]`, 섞였으면 `[MIX]`. 판단이 애매하면 본문 첫 언어를 따른다.
- 코드 블록·긴 경로·URL은 `[code]` / `[path]` / `[url]` 한 줄로 줄여 기록한다. 코퍼스는 영어 연습 기록이지 코드 저장소가 아니다.
- 중복 방지: 파일 끝의 마지막 기록이 방금 추가할 메시지와 같으면 추가하지 않는다. 세션 중간에 이 스킬을 다시 읽어도 같은 메시지를 두 번 쌓지 않는다.
- 사용자 메시지가 로그에 없으면 즉시 추가하고, 결과를 한 줄로만 알린다. "로그에 저장했습니다" 이상 설명하지 않는다.

## 분석 — 사용자가 명시적으로 물을 때만

"what's the problem with my english?", "내 영어 어때?", "영어 스캔", "영어 피드백" 같은 요청이 오면 다음을 한다.

1. **범위를 정한다.** `corpus.md`를 읽는다. 기본은 최근 30일이고, 다른 기간을 원하면 물어본다.
2. **사용자가 직접 쓴 영어 문장만 고른다.** 이번 요청·지난 요청 모두 포함한다. 코드, 경로, URL, 따옴표로 인용한 남의 문장은 제외한다. 한글만 있으면 "영어 기록이 아직 없다"고 말하고 수집부터 하라고 안내한다.
3. **오류 교정** — 문장별로 셋을 묶어 보여준다:
   - 원문
   - 문제: 문법 / 어휘 / 자연스러움(원어민 표현) 중 무엇이 어때서인지, 한 줄로
   - 고친 문장
   같은 오류가 여러 번 나오면 문장마다 반복하지 말고 **패턴으로 묶어 한 번** 지적하고, 해당 문장들을 나열한다. 심각도 순으로 정렬한다.
4. **실력 프로파일** — 다음을 짧게:
   - 강점 (문장 1~2개의 예와 함께)
   - 반복되는 약점 패턴 (위 3에서 나온 것의 요약)
   - 현재 수준 추정: 어휘·문법·문장 구조 근거로 "~ 수준으로 보인다"라고 **가설로** 표시한다. 단정하지 않는다.
   - 직전 분석(`analysis.md`의 마지막 항목)과 비교한 변화: 나아진 것, 그대로인 것
   - 다음에 집중할 것 하나
5. **기록과 답변** — 분석 전문을 `~/.dsh/english-log/analysis.md`에 날짜 헤더와 함께 추가하고, 채팅에는 핵심만 요약해서 답한다. 코퍼스 원문을 통째로 다시 붙여넣지 않는다.

`analysis.md` 형식:

```md
## 2026-08-31 — 분석 (기간: 2026-08-01~30, 메시지 N개)

### 오류 교정
- 원문: ...
  고친 문장: ...
  문제: ...

### 프로파일
- 강점 / 약점 패턴 / 수준 추정 / 이전 대비 / 다음 집중
```

## 하지 말 것

- 에이전트 답변·프롬프트·시스템 지시를 로그에 넣지 않는다.
- 쌓은 로그 항목을 임의로 수정하거나 삭제하지 않는다. 오타 수정도 사용자 확인 후에만.
- 분석 요청 없이 교정·점수·조언을 먼저 주지 않는다. 캡처만 하고 조용히 있는다.
- 인격·기분·노력을 평가하는 말을 붙이지 않는다. 로그에 나온 사실만 말한다.
- 로그 파일 위치를 바꾸겠다고 임의로 정하지 않는다. 바꿔야 하면 사용자에게 묻는다.