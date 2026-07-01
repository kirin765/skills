# 라우팅 — 어떤 도구로 보낼까

목표: 잘못된 도구로 수 분짜리 설치·렌더를 돌리지 않기. 아래로 빠르게 분기하고, 애매하면 사용자에게 한 번 묻는다.

## 한눈 결정

```
소스(찍어둔 클립) 있음?
├─ 있음
│   ├─ 한 편의 깔끔한 영상으로 (컷·무음 제거·자막·색보정)        → video-use
│   ├─ 롱 영상에서 숏폼 여러 개 뽑기                              → OpenMontage · Clip Factory
│   ├─ 음악·B-roll·타이틀·애니까지 얹은 본격 롱폼                 → OpenMontage · Talking Head / Hybrid / Cinematic
│   └─ 9:16·16:9 플랫폼 프로파일을 엄격히 맞춰야 함               → OpenMontage (출력 프로파일 지정)
└─ 없음 (무자본으로 새로 제작)
    ├─ 무료 스톡 실사 몽타주                                      → OpenMontage · Documentary Montage
    ├─ 트레일러/티저/무드 영상                                    → OpenMontage · Cinematic
    └─ 모션그래픽/키네틱 타이포/애니                              → OpenMontage · Animation
```

핵심 직관 한 줄: **"하나의 소스 → 하나의 클린 편집본"이면 video-use. "롱→숏 배치, 생성/스톡 에셋, 엄격한 플랫폼 프로파일"이면 OpenMontage.**

## video-use 능력 요약

기존 푸티지 편집에 특화. 폴더에 클립을 두고 대화하면 `<폴더>/edit/final.mp4` 산출.

- 필러워드(`음`, `어`, false start)·무음 컷
- 세그먼트별 자동 색보정(warm cinematic / neutral punch / 커스텀 ffmpeg 체인)
- 컷마다 30ms 오디오 페이드(팝 방지)
- 자막 번인(기본 2단어 대문자 청크, 커스터마이즈 가능)
- 애니 오버레이 생성(HyperFrames / Remotion / Manim / PIL, 서브에이전트 병렬)
- 렌더 결과 컷 경계 자기검수 후에만 프리뷰 제시
- `project.md`에 세션 메모리 지속 → 다음 세션 이어가기

아스펙트는 소스/요청대로. 숏(9:16)·롱폼(16:9)을 둘 다 원하면, 각각 한 번씩 편집 패스를 돌리거나 롱폼은 video-use, 숏은 Clip Factory로 나누는 2-트랙을 제안.

## OpenMontage 파이프라인 치트시트

모든 파이프라인 공통 흐름: `research → proposal → script → scene_plan → assets → edit → compose`. 각 단계마다 director 스킬(`skills/pipelines/<pipeline>/<stage>-director.md`)을 *먼저 읽고* 실행.

| 파이프라인 | 쓰임 |
|---|---|
| **Clip Factory** | 롱 소스 1개 → 랭킹된 숏폼 여러 개 (소셜 리퍼포징) ← **숏폼 배치의 정답** |
| **Talking Head** | 화자/푸티지 중심 영상 (발표·브이로그·인터뷰) |
| **Documentary Montage** | 무료 스톡·아카이브(Pexels/Archive.org/NASA/Wikimedia/Unsplash) 코퍼스에서 테마 몽타주 ← 유료 생성 없이 실사 |
| **Hybrid** | 소스 푸티지 + AI 생성 보조 비주얼 |
| **Cinematic** | 트레일러·티저·무드 편집 |
| **Animation** | 모션그래픽·키네틱 타이포·애니 시퀀스 |
| **Podcast Repurpose** | 팟캐스트 하이라이트/오디오그램 |
| **Screen Demo** | 소프트웨어 화면 녹화·워크스루 |
| **Avatar Spokesperson** | 아바타 발표자 영상 |

### 플랫폼 출력 프로파일 (빌트인)

| 프로파일 | 해상도 | 비율 |
|---|---|---|
| YouTube Landscape | 1920×1080 | 16:9 |
| YouTube 4K | 3840×2160 | 16:9 |
| **YouTube Shorts** | 1080×1920 | 9:16 |
| Instagram Reels | 1080×1920 | 9:16 |
| Instagram Feed | 1080×1080 | 1:1 |
| TikTok | 1080×1920 | 9:16 |
| LinkedIn | 1920×1080 | 16:9 |
| Cinematic | 2560×1080 | 21:9 |

고양이 → 유튜브 기본: **YouTube Shorts(9:16)** + **YouTube Landscape(16:9)** 둘 다.

## 기본 시나리오: "고양이 영상 → 숏 + 롱폼 둘 다"

권장 2-트랙(제안 후 확인):

1. **롱폼(16:9)** — video-use로 찍어둔 클립을 한 편의 클린 영상으로(컷·자막·색보정). 또는 OpenMontage Talking Head/Hybrid.
2. **숏폼(9:16)** — 그 롱폼(또는 원본 롱 클립)을 OpenMontage **Clip Factory**에 넣어 랭킹된 숏 여러 개 추출, YouTube Shorts 프로파일로 렌더.

사용자가 "둘 다 OpenMontage로", "숏만", "롱폼만"을 원하면 그대로 따른다. 실행 전 항상 한 줄 계획으로 확인.
