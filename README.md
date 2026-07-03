# skills

[![skills.sh](https://skills.sh/b/kirin765/skills)](https://skills.sh/kirin765/skills)

Agent skills by [@kirin765](https://github.com/kirin765) — research workflows, Korean-market tooling, and Steam recommendations. Built for Claude Code; works with any agent that supports the [skills](https://github.com/vercel-labs/skills) format.

## Install

```bash
npx skills add kirin765/skills
```

Or install a single skill by pointing at its directory.

## Skills

| Skill | What it does |
|---|---|
| [careful-factcheck](careful-factcheck/) | Cross-verify claims, numbers, and facts with multi-angle web searches — ✅/⚠️/❌/❓ verdicts, actively hunts counter-evidence. Built-in WebSearch/WebFetch only, no external APIs. |
| [storm-research](storm-research/) | Stanford STORM-style multi-perspective research briefing: 5 expert lenses, contradiction map, synthesis, self peer-review scoring. |
| [loop-engineering](loop-engineering/) | Interactive coach for designing agentic loops — self-prompting systems that find work, hand it to a coding agent, and check results. With failure-mode catalog and templates. |
| [steam-recommend](steam-recommend/) | Pulls your Steam library + playtime, builds a taste profile from your most-played games, and recommends what to play next (backlog, discovery, deals). |
| [naver-api](naver-api/) | Search-demand data: Naver DataLab 검색어트렌드 (Korean market) + Google Trends (global, via your logged-in Chrome over CDP). |
| [naver-searchad](naver-searchad/) | Naver Search Ads (네이버 검색광고) API client — campaigns, ad groups, keywords, bids, performance stats, and the keyword tool (monthly search volume). |
| [saas-viability-kr](saas-viability-kr/) | Grades solo-developer SaaS ideas for the Korean market (A/B/C) using Mom Test and Start Small Stay Small criteria. |

## Setup notes

- **careful-factcheck / storm-research / saas-viability-kr / loop-engineering** — prompt-only, zero setup.
- **steam-recommend** — needs `STEAM_API_KEY` ([free](https://steamcommunity.com/dev/apikey)) and `STEAM_ID` (SteamID64); optional `ITAD_API_KEY` for price history.
- **naver-api** — needs `NAVER_DATALAB_CLIENT_ID/SECRET` (free app at [developers.naver.com](https://developers.naver.com/apps/)); Google Trends needs Chrome with `--remote-debugging-port=9222`.
- **naver-searchad** — needs Naver Search Ads API keys in `~/.naver-searchad.env` (issued in 검색광고 관리시스템 → 도구 → API 사용 관리).

All scripts are Python/Node stdlib-only — no pip/npm installs (except Playwright for Google Trends).

## License

MIT
