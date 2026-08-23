---
name: steam-recommend
description: Pull the user's own Steam library and playtime from the Steam Web API and recommend games for them. Use this skill whenever the user wants game recommendations based on their Steam history, asks "what should I play next", wants to dig something out of their backlog (games they own but barely played), wants new/unowned games to buy or wishlist that match their taste, or asks anything like "스팀 게임 추천", "내 스팀 기록으로 추천해줘", "다음에 뭐 할까", "안 한 게임 중에 추천", "내 취향 게임 찾아줘", "recommend Steam games", "what to play from my library". It builds a taste profile from the genres/tags of the user's most-played games (SteamSpy data) and ranks recommendations against it. Trigger even if the user doesn't say "Steam" but clearly means their Steam library. Not for live multiplayer matchmaking, game prices/deals tracking, or other people's libraries — this is the user's own account.
---

# Steam Game Recommender

Recommends games from the user's Steam history. Everything runs through one helper —
`scripts/steam.py` — which handles Steam Web API auth, SteamSpy tag data, rate limits,
and the taste-matching math, so you never hand-roll API calls.

## Credentials (one-time)

The helper reads `STEAM_API_KEY` and `STEAM_ID` from env, falling back to baked-in
defaults at the top of `scripts/steam.py`. Both must be set for anything to work:

- **API key** — free at https://steamcommunity.com/dev/apikey
- **STEAM_ID** — the 17-digit SteamID64 (https://steamid.io if unknown)
- The profile's **Privacy → Game details must be Public**, or the owned-games list comes back empty.
- **`ITAD_API_KEY`** (optional) — IsThereAnyDeal key for price history / all-time-low. A working
  key is baked into `steam.py`; only needed if that one stops working (free at
  https://isthereanydeal.com/apps/my/). Powers the "buy now vs wait" verdict on deals.

Always start a session by running `python scripts/steam.py profile`. It confirms the key
works and prints `profile_visibility` — if that isn't `public`, stop and tell the user to
flip the privacy setting; recommendations are impossible without the library.

## Picking the mode

Match what the user asked for. If they just say "추천해줘" with no qualifier, do **backlog
first** (free, no spending) and then offer the other two.

| User intent | Mode | Command |
|---|---|---|
| "이거부터 해라" / own-but-unplayed / clear my backlog | **Backlog** | `python scripts/steam.py backlog` |
| New games to buy/wishlist / "살만한 거" / 신작·미보유 | **Discovery** | `python scripts/steam.py candidates` |
| "다음에 뭐 할까" / based on what I've been playing lately | **Next up** | `python scripts/steam.py recent` + `taste` |

All three share a taste profile: `python scripts/steam.py taste` weights the user's
most-played games (sqrt-damped by hours, so one 800h obsession doesn't dominate) and
aggregates SteamSpy tags + genres into a ranked profile. Run it first when you want to
explain *why* something is recommended.

## Workflow

1. `profile` — verify creds + public visibility.
2. `taste` — see what the user actually enjoys (top tags/genres + the games it's based on).
3. Run the mode command (`backlog` / `candidates` / `recent`).
4. Write a short markdown report (template below). Pick the strongest 5–8, not the raw list.
   Each pick needs a **one-line reason tied to the user's taste** ("you put 120h into
   Hades and this shares Roguelike + Action") — generic blurbs are useless.
5. Offer the other modes as a follow-up.

`backlog` and `candidates` are composites that already exclude owned games (for discovery),
score by tag overlap, and attach store URLs + positive review ratios — so usually you just
run one command and write it up. Reach for the raw commands (`spy <appid>`, `tag "<name>"`,
`owned`, `recent`) only when you need to dig deeper or sanity-check a pick.

## On-sale + Steam Deck + price history

When the user wants discounted and/or Deck-compatible games, or asks "is now a good time to
buy", use these — they add live Steam store price, Deck compatibility, and IsThereAnyDeal
all-time-low history on top of taste matching:

| Need | Command |
|---|---|
| Taste-matched, on sale now, Deck-playable | `deals` (`--cc kr`, `--deck-min 2\|3`) |
| **Spread across genres** (avoid one-genre pileup) | `deals --tags "Automation,Souls-like,JRPG,4X,Metroidvania,City Builder"` — one pick per tag, ranked by popularity |
| Vet specific hand-picked titles | `check <appid> <appid> ...` |
| Price history only | `histlow <appid> ...` |

**`deck`** field: `verified` > `playable` > `unsupported`. **`price_history`** (from ITAD) gives
`historic_low` + `historic_low_date` + `is_historic_low` (current price ties the all-time low →
buy now) + `pct_above_low` (how much over the floor it is → how much waiting could save).

**Hand-picking discipline.** The composites filter owned games; a manual list does NOT. When you
suggest titles from your own knowledge (e.g. "games unlike anything in your library" — useful when
taste-overlap picks feel stale to the user), ALWAYS run them through `check` first. It catches
games the user already owns AND wrong appids (a mistyped appid resolves to a different game). Skipping
this is how you end up recommending something they've already finished.

## Report structure

```markdown
## 🎮 추천 ([mode])

**네 취향:** [top 3-4 tags/genres] — [most-played 게임 2-3개]에서 뽑음

1. **[게임명]** ([positive_ratio]% 긍정) — [한 줄 이유: 어떤 보유게임/태그와 연결되는지]
   <store_url>
2. ...
```

Keep it skimmable. Lead with the single best pick. If `positive_ratio` is missing or low,
say so honestly rather than overselling.

## Notes & limits

- **SteamSpy `appdetails` is rate-limited (~1 req/sec).** The helper sleeps 1s between calls
  and caches results in `scripts/.spy_cache.json`, so the first `taste`/`backlog` on a big
  library takes ~10–30s but reruns are instant. `tag` (used by `candidates`) is fast.
- **Discovery quality gate.** `candidates` filters out games below `--min-reviews` (default 500)
  and ranks by tag-fit × positive-ratio. This is deliberate: SteamSpy tag lists are full of
  shovelware that spams tags, and without the gate that junk floats to the top. If results
  feel too mainstream, lower `--min-reviews`; if too obscure, raise it.
- **Tags ≠ ground truth.** SteamSpy tags are crowd-sourced; treat overlap as a signal, then
  apply judgment (e.g. don't recommend a hardcore PvP shooter to someone whose taste is all
  cozy single-player even if a tag matches).
- **Filtering.** Default is taste-only with no category exclusions. If the user asks to
  exclude something ("성인물 빼고", "멀티 말고 싱글", "한국어 지원만"), filter the candidate
  list before writing the report — check `matched_tags`/genre, or call `spy <appid>` for detail.
- Recommendations cover the user's **own** account only. Competitor/other-user libraries and
  price/deal tracking are out of scope.
