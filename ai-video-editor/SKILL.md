---
name: ai-video-editor
description: 찍어둔 영상(특히 고양이 클립)이나 무자본 소스로 유튜브용 숏폼·롱폼을 편집·제작하는 라우터 스킬. 작업 성격을 보고 video-use(기존 푸티지를 한 편으로 깔끔히 컷·자막·색보정)와 OpenMontage(롱→숏 다수 추출, 음악·B-roll·타이틀·애니 넣은 풀 제작, 플랫폼 프로파일)를 자동 선택해 각 도구의 자체 가이드로 핸드오프한다. 사용자가 "고양이 영상 편집해줘", "이 클립들 한 편으로 편집", "유튜브 숏/롱폼 만들어줘", "쇼츠로 잘라줘", "롱폼 영상 만들어줘", "영상 편집 도와줘", "이 영상 자막 넣고 색보정", "video-use로 ~", "OpenMontage로 ~", "edit these clips into a video", "make shorts/longform from this footage" 같이 *영상 편집·유튜브 숏/롱폼 제작·푸티지를 한 편으로 만들기*를 원할 때 반드시 발동한다. 도구가 안 깔려 있으면 첫 사용 때 설치하고, 기본 출력은 YouTube Shorts(9:16) + Long-form(16:9)이며 편집이 끝나면 youtube-upload 스킬로 게시까지 연결한다. 단순 단일 클립 트림 한 줄(ffmpeg)·순수 이미지 생성(ai-image-generator)·이미 만든 영상 업로드만(youtube-upload)·순수 HyperFrames 애니 저작(hyperframes)은 이 스킬이 아니다.
---

# AI Video Editor — video-use / OpenMontage 라우터

## 무엇을 하는 스킬인가

찍어둔 영상(주 용례: 집고양이 클립)이나 무자본 소스를 받아 **유튜브용 숏폼·롱폼**으로 편집·제작한다. 직접 편집하지 않고, 두 오픈소스 에이전트 도구 중 **작업에 맞는 쪽을 골라 그 도구의 자체 워크플로우로 넘긴다.**

- **video-use** (github.com/browser-use/video-use) — 이미 찍은 푸티지를 한 편의 깔끔한 영상으로. 군더더기·무음 컷, 색보정, 컷마다 30ms 오디오 페이드, 자막 번인, 애니 오버레이, 렌더 자기검수.
- **OpenMontage** (github.com/calesthio/OpenMontage) — 풀 제작 스튜디오. 롱 영상에서 숏 여러 개 추출(Clip Factory), 무료 스톡/생성 에셋 합성, 음악·타이틀·애니, **빌트인 플랫폼 출력 프로파일(Shorts 9:16, Landscape 16:9 등)**.

## 왜 이 구조인가 — 설계 배경

두 도구 모두 *자기 자신을 구동하는 가이드를 repo에 내장*한다. video-use는 설치 시 스스로를 `~/.claude/skills/video-use`로 심볼릭하고 `SKILL.md`·`helpers/`로 동작한다. OpenMontage는 repo 안의 `AGENT_GUIDE.md`/`CLAUDE.md`와 `pipeline_defs/`로 단계별 구동된다.

그래서 이 스킬은 **편집 로직을 재구현하지 않는다.** 가치는 네 가지뿐이다: (1) 한국어 한 마디로 진입, (2) 작업 성격→도구 라우팅, (3) 첫 사용 시 idempotent 설치, (4) 고양이/유튜브 기본값 + youtube-upload 연결. 실제 편집·렌더는 항상 선택된 도구의 자체 가이드가 한다. 도구가 새 버전을 내면 그 가이드를 따르면 되므로, 이 스킬은 얇게 유지한다.

## 도구 선택 (라우팅)

핵심 결정만 아래 표로. 더 자세한 케이스·OpenMontage 파이프라인 치트시트는 **[references/routing.md](references/routing.md)** 를 읽고 고른다.

| 사용자가 원하는 것 | 도구 |
|---|---|
| 찍어둔 클립들을 **한 편의 깔끔한 영상**으로 (컷·자막·색보정) | **video-use** |
| **롱 영상 → 숏폼 여러 개** 자동 추출·랭킹 | **OpenMontage · Clip Factory** |
| 음악·B-roll·타이틀·애니 넣은 **롱폼 제작**, 또는 엄격한 9:16/16:9 프로파일 필수 | **OpenMontage** (Documentary / Talking Head / Hybrid / Cinematic) |
| 무료 스톡/생성 영상으로 **소스 없이 새로 제작** | **OpenMontage** |

판단이 애매하면 사용자에게 한 번 물어 확정한다 — 잘못된 도구로 수 분짜리 설치·렌더를 돌리는 비용이 질문 비용보다 크다.

**기본 시나리오 ("고양이 영상 → 숏 + 롱폼 둘 다")**: 롱폼은 video-use로 클린 편집, 숏은 OpenMontage Clip Factory로 배치 추출하는 2-트랙을 *제안*하되, 사용자가 "둘 다 OpenMontage로"를 원하면 따른다. 항상 실행 전에 계획을 한 줄로 보여주고 OK를 받는다.

## 워크플로우

1. **작업 성격 파악 → 도구 선택.** 위 표 + routing.md. 숏/롱폼/둘 다인지, 소스가 있는지(폴더 경로) 없는지 확인.
2. **설치 확인.** 선택한 도구가 깔려 있는지 검사하고, 없으면 그 도구만 설치한다 → **[references/install.md](references/install.md)** 의 레시피를 그대로 따른다. 둘 다 필요하면 둘 다. API 키는 *그 워크플로우가 실제로 요구할 때만* 사용자에게 요청한다(미리 받지 않는다).
3. **소스 폴더 확정.** 고양이 푸티지가 든 폴더 절대경로를 사용자에게 확인. (소스 없이 OpenMontage로 새로 제작이면 생략.)
4. **출력 기본값 제안.** 별말 없으면 **Shorts 1080×1920(9:16) + Long-form 1920×1080(16:9)** 둘 다 산출을 기본으로 깔고 한 줄로 확인받는다. 사용자가 한쪽만 원하면 그쪽만.
5. **도구 자체 가이드로 핸드오프.** 여기서부터는 선택된 도구가 운전한다:
   - **video-use**: 소스 폴더로 이동해 그 폴더에서 작업하고, video-use의 `SKILL.md`·`helpers/`를 읽어 따른다. "이 클립들 \<숏/롱폼\>으로 편집해줘"로 시작 → 도구가 인벤토리·전략 제안 후 `<폴더>/edit/`에 산출.
   - **OpenMontage**: repo로 `cd` 후 `AGENT_GUIDE.md`(필요 시 `PROJECT_CONTEXT.md`)를 읽고 **Rule Zero**(모든 제작은 pipeline 경유)를 지킨다. 적합 파이프라인 선택 → 단계별 director 스킬을 읽으며 실행. 출력 프로파일을 YouTube Shorts/Landscape로 지정.
6. **산출물 수집 → 게시 제안.** 렌더 결과 경로를 사용자에게 보여주고, **youtube-upload 스킬**로 게시할지 묻는다(그 스킬 기본 공개범위 unlisted). 자동 발행하지 말고 사용자가 OK한 것만 올린다.

## 기본값 / 사용자 컨텍스트

- **주 소재**: 집고양이 영상. 톤은 보통 음악 + 자막(나레이션 TTS는 대개 불필요 — 5번에서 키 요청을 부르지 않게 주의).
- **타깃 플랫폼**: 유튜브. Shorts(9:16) + Long-form(16:9) 동시 산출이 기본.
- **게시**: 기존 `youtube-upload` 스킬과 연결. 본 스킬은 게시를 *제안*만 하고 실행은 그 스킬에 위임.
- **clone 위치**: 업스트림 관례대로 `~/Developer/video-use`, `~/Developer/OpenMontage`.

## 주의점 (사용자에게 미리 알릴 것)

- **OpenMontage = AGPLv3** (카피레프트). 개인 유튜브 업로드엔 무방. 코드 자체를 재배포·서비스화할 때만 의미.
- **video-use의 ElevenLabs 키**는 *나레이션 음성을 생성할 때만* 필요. 고양이 영상은 음악+자막이면 충분하니 키 없이 진행 가능 — 불필요하게 키를 요구하지 말 것.
- **OpenMontage 생성 프로바이더(Veo/Kling/FLUX 등)는 유료.** 하지만 **본인 고양이 푸티지를 편집**하는 데는 필요 없다(무료 스톡 Pexels/Pixabay/Wikimedia + 로컬 경로가 기본). 유료 생성이 비용을 부르면 사용자에게 먼저 확인.
- **첫 설치는 수 분** 소요(clone + deps + ffmpeg). 설치 중임을 사용자에게 알린다.
- 설치가 끝나면 video-use는 자체 스킬(`~/.claude/skills/video-use`)도 등록한다 — 정상이다. 본 스킬은 그 위에서 라우팅·기본값·게시 연결을 담당한다.

## 이 스킬이 하지 않는 것

- **단일 클립 한 줄 트림/변환** (자르기·해상도 변경 한 방) — 그건 ffmpeg 한 줄이면 된다. 도구 설치·파이프라인 오버킬.
- **순수 이미지 생성** — `ai-image-generator`.
- **이미 만든 영상 업로드만** — `youtube-upload` 직접.
- **순수 HyperFrames 애니 저작/렌더** — `hyperframes`. (단, video-use/OpenMontage가 내부적으로 HyperFrames를 오버레이로 쓰는 건 그 도구가 알아서 한다.)
- **쓰기형 위험 동작 자동화** — 게시·삭제는 항상 사용자 확인 후.
