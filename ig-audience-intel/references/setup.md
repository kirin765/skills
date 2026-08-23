# Setup — Osintgraph for IG audience intelligence (zero-state, macOS)

One-time. After this, the skill just runs `scripts/run_intel.py`. Verified against Osintgraph 0.1.1.

## 0. Burner Instagram account (do this first, it takes the longest)
Osintgraph scrapes by importing your **Firefox** Instagram session — it acts AS whatever account is logged in. Scraping violates IG ToS and can get the account suspended.
- Use a **burner account, never your main promo account.**
- Per Osintgraph's own anti-suspension guide: enable **2FA**, log in via Firefox, and **warm it up** (post/like/scroll like a human) for several days before scraping. No VPN. Don't use the account for anything else while a scrape runs. Don't scrape >6h straight; keep `--rate-limit` on.

## 1. Neo4j database
Osintgraph needs a Bolt-reachable Neo4j. Two options — pick one:

**A. Neo4j Aura (free cloud, what the README assumes)**
1. Sign up at https://neo4j.com → create a **free instance (AuraDB)**.
2. Download the admin credentials file — you get **Connection URI** (`neo4j+s://xxxx.databases.neo4j.io`), **username** (`neo4j`), **password**. Keep these.
3. ⚠ Aura Free caps at ~200k nodes / 400k relationships. A few seeds × 1000 followers each fits; large/`explore` runs can exceed it → use option B.

**B. Local Neo4j via Docker (no node cap, free)**
```bash
docker run -d --name osintgraph-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/changeme-strong-pass \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5.28
```
Then your creds are: URI `bolt://localhost:7687`, user `neo4j`, password `changeme-strong-pass`. (APOC is enabled because Osintgraph reads the schema via `apoc.meta.schema()`.) Browser at http://localhost:7474.

## 2. Firefox + Instagram login
- Install Firefox if needed, open it, and **log in to Instagram with the burner account**. Leave it logged in. Osintgraph reads `~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite` directly.
- (Optional) Grab your Firefox User-Agent: Google "my user agent" in that Firefox and copy the string — you'll paste it in setup so the scrape looks consistent with your login.

## 3. Install Osintgraph
Python ≥ 3.9 required. Recommended via pipx (isolated):
```bash
brew install pipx 2>/dev/null; pipx ensurepath
pipx install osintgraph
# add the neo4j driver into the SAME env so run_intel.py can query directly:
pipx inject osintgraph neo4j
```
Alternative (venv + pip):
```bash
python3 -m venv ~/.venvs/osintgraph && source ~/.venvs/osintgraph/bin/activate
pip install osintgraph neo4j
```

## 4. Configure Osintgraph
Interactive — there is **no .env**; values are saved to `credentials.json` inside the package dir.
```bash
osintgraph setup instagram     # choose "login via Firefox session"
osintgraph setup neo4j         # paste URI / username / password from step 1
osintgraph setup user-agent    # paste your real Firefox UA (optional but recommended)
# Gemini is NOT needed — this skill skips all AI analysis. Leave `osintgraph setup gemini` unset.
```
Verify login worked: `osintgraph discover <some_public_account> --limit follower=20 followee=20 post=1` should start writing nodes. Ctrl-C after it confirms it's collecting.

## 5. Hand Neo4j creds to run_intel.py
`run_intel.py` finds Neo4j creds in this order: CLI flags → env vars → Osintgraph's `credentials.json`.
- If you ran `pipx inject osintgraph neo4j`, the auto-locate of `credentials.json` usually just works — try it with no extra flags.
- Otherwise export them (same values as step 1):
```bash
export NEO4J_URI='neo4j+s://xxxx.databases.neo4j.io'   # or bolt://localhost:7687
export NEO4J_USERNAME='neo4j'
export NEO4J_PASSWORD='...'
```
- Or pass `--neo4j-uri/--neo4j-user/--neo4j-password` directly.

## ⚠ Known limitation — instaloader ↔ live Instagram (verified 2026-06)
osintgraph pins **instaloader==4.14.2**. Against current Instagram:
- **Profile fetch works** (`discover <user> --skip follower followee post post-analysis account-analysis` reliably writes the seed Person node → username, fullname, followers/followees count, bio, category, verified/business).
- **Post collection crashes** on comment-fetch: `post.get_comments()` → `doc_id_graphql_query` returns None / `400 Bad Request "invalid request"`. So top_hashtags / top_posts / posting_times / seed_content_profile can't be collected as-is.
- Upgrading to **instaloader 4.15.1 is worse** (profile metadata itself 400s). Don't bump blindly.
- A **brand-new / low-trust account** compounds this (deep GraphQL queries get throttled). An **aged, warmed account** is much more likely to get valid post/follower responses.

→ Practical path today: run **profile-only** on seeds first (audience size + bio + category landscape). For posts/followers/overlap, warm the account several days, then retry; if still blocked, an instaloader version that currently matches IG's doc_ids is required (moving target).

## Ready check
- [ ] Burner IG logged in to Firefox, warmed up, 2FA on
- [ ] Neo4j running (Aura or Docker), creds saved
- [ ] `osintgraph` installed, `neo4j` driver importable in that env
- [ ] `osintgraph setup instagram/neo4j` done; a tiny test discover wrote nodes
