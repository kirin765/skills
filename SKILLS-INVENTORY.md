# Claude Code Skills Inventory

생성: 2026-06-10 · 머신: kiwankim · 스킬 루트: `~/.claude/skills`

분류 기준: **A. 사용자 제작**(워크플로우 특화·한국어 설명·전용 scripts 보유) / **B. 설치 스킬팩**(마켓/번들, 영문·범용) / **C. 플러그인 네임스페이스 스킬**(`plugin:skill` 형태, 이 레포 밖 — 플러그인 시스템으로 설치) / **D. 빌트인 명령**.
(A/B 경계는 휴리스틱 — 일부는 추정.)

---

## A. 사용자 제작 스킬 (personal)

### Play / Android 출시 + 게임 개발 (단일 스킬)
| 스킬 | 용도 |
|---|---|
| `android-app-builder` | 아이디어 → 앱 → Play Console 검토 제출까지 단일 스킬. 게임은 Phaser4+Vite+Capacitor, 그 외는 네이티브 Kotlin으로 분기 개발. AdMob 수익화·에셋 합성·Play 등록/업데이트/검토제출·읽기전용 조회(리뷰·트랙·versionCode) 전부 포함. 구 `play-store-submit`·`play-api-read`·`phaser-arcade-game`을 흡수(2026-06-14 통합). dev 계정 happylife2080100 + GCP claude-for-android. |

### 브라우저 자동화 / 스크랩 (인증세션 CDP · Claude in Chrome)
| 스킬 | 용도 |
|---|---|
| `cdp-anywhere` | 범용 인증세션 브라우저 자동화 (전용 스킬 없는 임의 사이트) |
| `x-cdp-search` | X(트위터) 검색결과 SearchTimeline GraphQL 직접 수집 |
| `x-account-coach` | X 계정 운영 코칭 |
| `reddit-cdp-coach` | Reddit 댓글 후보 발굴·초안 코칭 (read-only) |
| `careful-factcheck` | 내장 WebSearch로 주장·수치 다각도 교차검증 (반증 탐색·다중 출처, read-only) |
| `naver-cafe-scrape` | 네이버 카페 게시판 일괄 스크랩 (내부 JSON API) |
| `naver-blog-brunch-scrape` | 네이버 블로그·브런치 스크랩 |

### 한국 리서치 / 데이터 / 검증
| 스킬 | 용도 |
|---|---|
| `kr-sales-safari` | 한국 커뮤니티 Sales Safari → SaaS 아이디어 발굴 (Mom Test) |
| `dcinside-sales-safari` | 디시인사이드 기반 Sales Safari (전용 scripts) |
| `saas-viability-kr` | 한국 1인 SaaS 아이디어 ABC 등급 평가 |
| `stress-test-idea` | 아이디어 적대적 프리모템(5점 비판) |
| `kosis-api` | KOSIS 국가통계 API 조회 |
| `naver-api` | 네이버 오픈 API |
| `naver-seo` | 네이버 SEO |

### 발행 / 배포 / 알림
| 스킬 | 용도 |
|---|---|
| `tistory-naver-crosspost` | 소스 글 → 티스토리·네이버 블로그 크로스포스트 |
| `postiz-publish` | Postiz API로 32개 SNS 즉시 발행·스케줄링 |
| `app-launch-promo` | 신규 앱 멀티채널 홍보 오케스트레이터 — IG·Threads·X·TikTok(Claude in Chrome)+YouTube(youtube-upload API) 게재, inpock 링크 추가, disquiet 프로젝트+로그. 카피는 플랫폼별 생성, 영상은 입력. 즉시 자동발행. |
| `telegram-bot` | 텔레그램 메시지·알림 발송 |

### 기타 유틸
| 스킬 | 용도 |
|---|---|
| `conclave` | 멀티 LLM 카운슬(익명 토론·합의) |
| `openai-assist` | OpenAI 보조 호출 |
| `find-skills` | 스킬 탐색 헬퍼 |
| `contribute-catalog` | 스킬 카탈로그 기여 |
| `obsidian-vault` | Obsidian 볼트 작업 |

> ⚠️ `aso-audit`(App Store/Play ASO 감사)는 `~/.agents/skills/aso-audit` **심링크** — 설치팩 쪽 실체. play 워크플로우에서 함께 호출하지만 소스는 이 레포가 아님.

---

## B. 설치 스킬팩 (마켓/번들 — 이 레포에 함께 스냅샷)

- **GSD 프레임워크** (`gsd-*`, 60+): 프로젝트 라이프사이클 — `gsd-new-project`, `gsd-plan-phase`, `gsd-execute-phase`, `gsd-code-review`, `gsd-debug`, `gsd-ship`, `gsd-workspace`, `gsd-ns-*`(NoteSpace) 등.
- **SEO**: `seo`, `seo-audit`, `seo-content`, `seo-cluster`, `seo-backlinks`, `seo-local`, `seo-maps`, `seo-geo`, `seo-google`, `seo-technical`, `seo-schema`, `seo-sitemap`, `seo-hreflang`, `seo-image*`, `seo-page`, `seo-plan`, `seo-programmatic`, `seo-sxo`, `seo-drift`, `seo-dataforseo`, `seo-ecommerce`, `seo-competitor-pages`, `ai-seo`, `programmatic-seo`, `schema-markup`, `site-architecture`, `discover`.
- **Firecrawl**: `firecrawl`, `firecrawl-agent`, `firecrawl-scrape`, `firecrawl-crawl`, `firecrawl-map`, `firecrawl-search`, `firecrawl-download`, `firecrawl-interact`, `firecrawl-build-*`.
- **마케팅/그로스**: `ad-creative`, `cold-email`, `copywriting`, `copy-editing`, `email-sequence`, `marketing-ideas`, `marketing-psychology`, `content-strategy`, `social-content`, `lead-magnets`, `lead-research-assistant`, `paid-ads`, `launch-strategy`, `referral-program`, `pricing-strategy`, `product-marketing-context`, `sales-enablement`, `competitor-alternatives`, `customer-research`, `churn-prevention`, `revops`, `free-tool-strategy`, `ab-test-setup`, `analytics-tracking`.
- **CRO**: `form-cro`, `onboarding-cro`, `page-cro`, `paywall-upgrade-cro`, `popup-cro`, `signup-flow-cro`.
- **프론트엔드/애니메이션**: `animejs`, `gsap`, `lottie`, `three`, `typegpu`, `waapi`, `css-animations`, `tailwind`, `shadcn`, `theme-factory`, `canvas-design`, `web-artifacts-builder`, `agentation`.
- **영상/모션**: `hyperframes`, `hyperframes-cli`, `hyperframes-media`, `hyperframes-registry`, `remotion-best-practices`, `remotion-to-hyperframes`, `website-to-hyperframes`, `navigate`.
- **Vercel/개발**: `vercel-composition-patterns`, `vercel-react-best-practices`, `playwright-dev`.
- **기타**: `ai-image-generator`, `design-review`, `agent-room`, `claude-api`, `review-chain`, `task-breakdown`.

---

## C. 플러그인 네임스페이스 스킬 (`plugin:skill` — 플러그인 시스템 설치, 이 레포 밖)

- **superpowers**: `brainstorming`, `test-driven-development`, `systematic-debugging`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `using-git-worktrees`, `requesting/receiving-code-review`, `verification-before-completion`, `writing-skills`, `finishing-a-development-branch`, `using-superpowers`.
- **vercel**: `bootstrap`, `deploy`, `nextjs`, `ai-sdk`, `ai-gateway`, `chat-sdk`, `auth`, `env-vars`, `marketplace`, `vercel-cli`, `vercel-functions`, `vercel-storage`, `turbopack`, `shadcn`, `workflow` 외 다수.
- **context-mode**: `context-mode`, `ctx-stats`, `ctx-doctor`, `ctx-insight`, `ctx-purge`, `ctx-upgrade`, `diagnose`, `grill-me`, `tdd`, `improve-codebase-architecture`.
- **claude-mem**: `mem-search`, `timeline-report`, `learn-codebase`, `make-plan`, `pathfinder`, `smart-explore`, `babysit`, `knowledge-agent`, `version-bump`.
- **anthropic-skills**: `docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `schedule`, `consolidate-memory`, `setup-cowork`.
- **cowork 직무팩**: `marketing:*`, `engineering:*`, `design:*`, `operations:*`, `product-management:*`.
- **searchfit-seo**: `seo-audit`, `content-strategy`, `keyword-clustering`, `internal-linking`, `schema-markup`, `technical-seo`, `ai-visibility`, `broken-links`, `content-brief`, `create-content/topic` 외.
- **기타 플러그인**: `frontend-design:frontend-design`, `code-review:code-review`, `postiz:postiz`, `cowork-plugin-management:*`.

---

## D. 빌트인 슬래시 명령 (스킬형)

`deep-research`, `code-review`, `simplify`, `verify`, `run`, `init`, `review`, `security-review`, `loop`, `schedule`, `update-config`, `keybindings-help`, `fewer-permission-prompts`.

---

## 레포 메모

- 원격: `github.com/kirin765/claude-skills`
- 제외(.gitignore): `*-workspace/` 생성물, `dcinside-sales-safari/scripts/{raw,signals}/` 스크랩 코퍼스(재생성 가능, ~10MB).
- 시크릿은 추적 안 함 — 스킬 코드는 `~/.config/*` / 환경변수 경로만 참조(키 값 미포함).
