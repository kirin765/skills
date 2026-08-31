# skills

[![skills.sh](https://skills.sh/b/kirin765/skills)](https://skills.sh/kirin765/skills)

Agent skills by [@kirin765](https://github.com/kirin765) — research workflows, Korean-market tooling, app/game publishing, distribution, and Steam recommendations. Built for Claude Code; works with any agent that supports the [skills](https://github.com/vercel-labs/skills) format.

병합됨: `kirin765/claude-skills` → `kirin765/skills` (2026-08-24). 전체 224개 스킬(루트 89 + `agents/` 134 + `dsh/` 1) 통합.

## Install

```bash
npx skills add kirin765/skills
```

Or install a single skill by pointing at its directory.

## Structure

- **루트** — 사용자 본인 운영 스킬 89개 (한국 시장·발행·앱 출시·CDP 자동화 등).
- **`agents/`** — 플러그인/번들 스킬 실체 백업 134개 (`~/.agents/skills` 스냅샷). 이름 충돌 시 루트가 우선 — 이 둘은 기능 중복이 아니라 소스 위치가 다름.
- **`dsh/`** — DSH 하네스용 스킬 (`apps-in-toss-app-submission`).

## Skills (루트 대표)

| Skill | What it does |
|---|---|
| [careful-factcheck](careful-factcheck/) | Cross-verify claims, numbers, and facts with multi-angle web searches — ✅/⚠️/❌/❓ verdicts, actively hunts counter-evidence. Built-in WebSearch/WebFetch only, no external APIs. |
| [storm-research](storm-research/) | Stanford STORM-style multi-perspective research briefing: 5 expert lenses, contradiction map, synthesis, self peer-review scoring. |
| [loop-engineering](loop-engineering/) | Interactive coach for designing agentic loops — self-prompting systems that find work, hand it to a coding agent, and check results. With failure-mode catalog and templates. |
| [steam-recommend](steam-recommend/) | Pulls your Steam library + playtime, builds a taste profile from your most-played games, and recommends what to play next (backlog, discovery, deals). |
| [naver-api](naver-api/) | Search-demand data: Naver DataLab 검색어트렌드 (Korean market) + Google Trends (global, via your logged-in Chrome over CDP). |
| [naver-searchad](naver-searchad/) | Naver Search Ads (네이버 검색광고) API client — campaigns, ad groups, keywords, bids, performance stats, and the keyword tool (monthly search volume). |
| [saas-viability-kr](saas-viability-kr/) | Grades solo-developer SaaS ideas for the Korean market (A/B/C) using Mom Test and Start Small Stay Small criteria. |
| [android-app-builder](android-app-builder/) | Idea → app → Play Console review submission in a single skill. Phaser4+Vite+Capacitor for games, native Kotlin otherwise. AdMob, asset synthesis, Play submit/update/review, read-only queries. |
| [app-in-toss](app-in-toss/) | Apps in Toss (앱인토스) mini-apps end-to-end: .ait build+validate, console register/앱정보/등급분류/review/launch, challenge submission form, monetization (IAP products + 전면/리워드/배너 ad groups & placement), secret audit before upload. |
| [cdp-anywhere](cdp-anywhere/) | Generic authenticated-session browser automation via Chrome DevTools Protocol (for sites without a dedicated skill). Explicitly refuses bot-detection evasion. |
| [x-cdp-search](x-cdp-search/) | X search-result collection via SearchTimeline GraphQL (queryId capture + cursor replay, zero browser render). |
| [ig-audience-intel](ig-audience-intel/) | IG audience/competitor intelligence via Osintgraph → Neo4j (4-metric Cypher → promo report). Alt-account only, ToS-flagged. |
| [tistory-naver-crosspost](/tistory-naver-crosspost/) · v2 · v3 | Blog article → Tistory + Naver Blog cross-post via authenticated Chrome CDP session. |
| [youtube-upload](youtube-upload/) | Unattended YouTube upload via Data API v3 (OAuth refresh token + REST, default unlisted). |
| [conclave](conclave/) | Multi-LLM council with anonymized debate — quick/standard/deep depth levels. |
| [kr-sales-safari](kr-sales-safari/) | Korean community Sales Safari → SaaS idea discovery (Mom Test). |
| [gmail-mail](gmail-mail/) | Gmail send via authenticated session. |
| [telegram-bot](telegram-bot/) | Telegram message/notification send (creds from `~/niche-finder/.env`). |
| [send-sms](send-sms/) | SMS/iMessage send from macOS Messages via AppleScript — routed through the user's own iPhone, no API or cost. |
| [kiwoom-trade-api](kiwoom-trade-api/) | Kiwoom (키움증권) REST API — quotes/charts/balance/orders + auto-trading (paper/demo/live). Live orders gated (2026-09-12) until demo validation passes. |
| [google-tasks](google-tasks/) | Google Tasks create/list via official REST API (OAuth desktop flow, token cache reuse). |
| [tuya-light](tuya-light/) | Tuya smart-light control — mood/situation → lighting mapping. |
| [brag](brag/) | Highlight/project brag-doc generator. |
| [english-scan](english-scan/) | Always-on session logger of the user's own messages → `~/.dsh/english-log/corpus.md`; on "what's the problem with my english?" corrects errors (grammar/vocabulary/naturalness, before→after) and profiles proficiency (strengths, repeated weak patterns, level estimate, trend), appending analyses to `analysis.md`. |
| + 65 more under 루트 (naver-cafe-scrape, ppomppu-clien-scrape, reddit-cdp-coach, careful-factcheck, cafe24-app-dev/test, coupon/naver-commerce/toss APIs, media/hyperframes video pipeline, ubuntu-server, ASO/SEO tooling…) | |

전체 목록: `SKILLS-INVENTORY.md` (분류 기준 A 사용자 제작 / B 설치 스킬팩 / C 플러그인 네임스페이스 / D 빌트인 명령).

## Setup notes

- **careful-factcheck / storm-research / saas-viability-kr / loop-engineering** — prompt-only, zero setup.
- **steam-recommend** — needs `STEAM_API_KEY` ([free](https://steamcommunity.com/dev/apikey)) and `STEAM_ID` (SteamID64); optional `ITAD_API_KEY` for price history.
- **naver-api** — needs `NAVER_DATALAB_CLIENT_ID/SECRET` (free app at [developers.naver.com](https://developers.naver.com/apps/)); Google Trends needs Chrome with `--remote-debugging-port=9222`.
- **naver-searchad** — needs Naver Search Ads API keys in `~/.naver-searchad.env` (issued in 검색광고 관리시스템 → 도구 → API 사용 관리).
- **cdp-based skills** (x-cdp-search, tistory-naver-crosspost 등) — need Chrome with `--remote-debugging-port=9222` and a logged-in profile.

All scripts are Python/Node stdlib-only — no pip/npm installs (except Playwright for Google Trends).

## Security

- `.env` 파일은 커밋 대상 아님(`.gitignore`). 시크릿은 환경변수/`~/.config` 경로 참조만 — 키 값은 repo에 없음(2026-08-24 공개 전 purge + 재스캔 완료).
- `cdp-anywhere`·`seo-drift` 계열은 봇 탐지 회피·SSRF 우회를 명시 거부.

## License

MIT