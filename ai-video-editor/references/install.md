# 설치 레시피 (idempotent)

선택한 도구만 설치한다. 이미 깔려 있으면 건너뛴다. clone 위치는 업스트림 관례 `~/Developer/`.

## 공통 사전 점검

```bash
command -v ffmpeg  >/dev/null || echo "NEED: brew install ffmpeg"
command -v git     >/dev/null || echo "NEED: git"
```

ffmpeg는 두 도구 다 필수다. 없으면 `brew install ffmpeg`.

---

## video-use

설치 여부 검사:

```bash
test -d ~/Developer/video-use && echo "video-use: installed" || echo "video-use: missing"
```

없으면:

```bash
# 1. clone + 에이전트 스킬 디렉토리에 심볼릭
git clone https://github.com/browser-use/video-use ~/Developer/video-use
ln -sfn ~/Developer/video-use ~/.claude/skills/video-use

# 2. 의존성
cd ~/Developer/video-use
uv sync                 # uv 없으면: pip install -e .
brew install ffmpeg     # 이미 있으면 자동 skip
brew install yt-dlp     # 선택 (URL에서 소스 받을 때만)
```

**ElevenLabs 키** — *나레이션 음성을 생성할 때만* 필요. 고양이 영상은 음악+자막이면 충분하니 기본은 건너뛴다. 실제로 TTS가 필요한 워크플로우에 들어갈 때만:

```bash
cd ~/Developer/video-use
cp .env.example .env     # 그 후 ELEVENLABS_API_KEY=... 를 사용자에게 받아 채움
```

설치 후 video-use의 `SKILL.md`(일상 사용)와 `helpers/`(편집 스크립트 위치)를 읽고 따른다. 설치 직후엔 아무것도 transcribe하지 말고 "준비됨"만 알린 뒤 소스 폴더를 기다린다.

---

## OpenMontage

설치 여부 검사:

```bash
test -d ~/Developer/OpenMontage && echo "OpenMontage: installed" || echo "OpenMontage: missing"
```

사전 조건: **Python 3.10+, FFmpeg, Node.js 18+**.

```bash
python3 --version    # 3.10+ 확인
node --version       # 18+ 확인
```

없으면:

```bash
git clone https://github.com/calesthio/OpenMontage.git ~/Developer/OpenMontage
cd ~/Developer/OpenMontage
make setup
```

구동은 repo 안에서 한다 — `cd ~/Developer/OpenMontage` 후 `AGENT_GUIDE.md`(필요 시 `PROJECT_CONTEXT.md`)를 읽고 **Rule Zero**(모든 제작은 `pipeline_defs/`의 파이프라인 경유)를 지킨다. OpenMontage는 자신을 `~/.claude/skills`에 등록하지 않으므로, 항상 repo로 들어가 그 안의 가이드를 따른다.

**프로바이더 키** — 본인 푸티지 편집/무료 스톡 경로엔 불필요. 유료 생성(Veo/Kling/FLUX 등)을 쓰는 워크플로우에 들어갈 때만, 비용을 사용자에게 먼저 알리고 해당 키를 받는다(`docs/PROVIDERS.md` 참조). 라이선스는 **AGPLv3**.
