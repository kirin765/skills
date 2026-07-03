#!/usr/bin/env python3
"""Steam library + SteamSpy helper for the steam-recommend skill.

One client for every call so the workflow never hand-rolls auth, rate limits, or
the SteamSpy tag math. Steam Web API needs a key; SteamSpy and the store
appdetails endpoint are keyless.

Usage:
    python steam.py profile                 # verify creds + profile visibility
    python steam.py owned [--json]          # owned games, sorted by playtime
    python steam.py recent                  # last-2-weeks games
    python steam.py spy <appid>             # SteamSpy tags/genre for one app
    python steam.py tag "Roguelike"         # games carrying a SteamSpy tag
    python steam.py taste [--top N]         # weighted tag/genre taste profile
    python steam.py candidates [--limit M]  # unowned games ranked by taste fit
    python steam.py backlog [--limit M]     # owned-but-unplayed ranked by taste fit

Credentials: STEAM_API_KEY and STEAM_ID env vars (or fill in the DEFAULT_*
placeholders below). STEAM_ID is the 17-digit SteamID64. A 401/empty owned list
usually means the key is wrong or the profile's "Game details" is not public.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Fill these in (or export STEAM_API_KEY / STEAM_ID) so the skill works without env.
DEFAULT_API_KEY = "PUT_YOUR_STEAM_API_KEY"
DEFAULT_STEAM_ID = "PUT_YOUR_STEAMID64"

API_KEY = os.environ.get("STEAM_API_KEY", DEFAULT_API_KEY)
STEAM_ID = os.environ.get("STEAM_ID", DEFAULT_STEAM_ID)

WEB_API = "https://api.steampowered.com"
SPY_API = "https://steamspy.com/api.php"
ITAD_API = "https://api.isthereanydeal.com"
ITAD_KEY = os.environ.get("ITAD_API_KEY", "")
CACHE = Path(__file__).resolve().parent / ".spy_cache.json"
ITAD_CACHE = Path(__file__).resolve().parent / ".itad_cache.json"


def _get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "steam-recommend/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                klen = len(API_KEY)
                hint = " (your key is %d chars; a valid Steam Web API key is 32 hex chars)" % klen if klen != 32 else ""
                sys.exit("Steam API rejected the request (HTTP %d). The API key is wrong or expired%s.\n"
                         "  Re-copy it from https://steamcommunity.com/dev/apikey" % (e.code, hint))
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def _check_creds():
    if "PUT_YOUR" in API_KEY or "PUT_YOUR" in STEAM_ID:
        sys.exit(
            "Missing credentials. Set STEAM_API_KEY and STEAM_ID env vars, or edit the "
            "DEFAULT_* values at the top of steam.py.\n"
            "  Key:     https://steamcommunity.com/dev/apikey\n"
            "  SteamID64: 17-digit number (https://steamid.io)\n"
            "  Also set profile -> Privacy -> Game details = Public."
        )


# ---------- Steam Web API ----------

def profile():
    _check_creds()
    url = f"{WEB_API}/ISteamUser/GetPlayerSummaries/v2/?key={API_KEY}&steamids={STEAM_ID}"
    players = _get(url).get("response", {}).get("players", [])
    if not players:
        sys.exit("No profile returned — check STEAM_ID and key.")
    p = players[0]
    vis = {1: "private", 2: "friends-only", 3: "public"}.get(p.get("communityvisibilitystate"), "?")
    return {
        "personaname": p.get("personaname"),
        "steamid": p.get("steamid"),
        "profile_visibility": vis,
        "profileurl": p.get("profileurl"),
    }


def owned():
    _check_creds()
    url = (
        f"{WEB_API}/IPlayerService/GetOwnedGames/v1/?key={API_KEY}&steamid={STEAM_ID}"
        "&include_appinfo=1&include_played_free_games=1&format=json"
    )
    games = _get(url).get("response", {}).get("games", [])
    if not games:
        sys.exit(
            "Owned game list is empty. Either the account owns nothing, or "
            "profile -> Privacy -> Game details is not Public."
        )
    out = [
        {
            "appid": g["appid"],
            "name": g.get("name", str(g["appid"])),
            "playtime_min": g.get("playtime_forever", 0),
            "playtime_2weeks": g.get("playtime_2weeks", 0),
            "last_played": g.get("rtime_last_played", 0),
        }
        for g in games
    ]
    out.sort(key=lambda x: x["playtime_min"], reverse=True)
    return out


def recent():
    _check_creds()
    url = f"{WEB_API}/IPlayerService/GetRecentlyPlayedGames/v1/?key={API_KEY}&steamid={STEAM_ID}&format=json"
    games = _get(url).get("response", {}).get("games", [])
    return [
        {
            "appid": g["appid"],
            "name": g.get("name", str(g["appid"])),
            "playtime_2weeks": g.get("playtime_2weeks", 0),
            "playtime_min": g.get("playtime_forever", 0),
        }
        for g in games
    ]


# ---------- SteamSpy ----------

def _load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(c):
    try:
        CACHE.write_text(json.dumps(c))
    except Exception:
        pass


def spy(appid, cache=None):
    """SteamSpy appdetails — tags (dict tag->votes), genre, owners. Cached."""
    key = str(appid)
    cache = _load_cache() if cache is None else cache
    if key in cache:
        return cache[key]
    data = _get(f"{SPY_API}?request=appdetails&appid={appid}") or {}
    rec = {
        "appid": appid,
        "name": data.get("name"),
        "genre": data.get("genre", ""),
        "tags": data.get("tags", {}) if isinstance(data.get("tags"), dict) else {},
        "positive": data.get("positive", 0),
        "negative": data.get("negative", 0),
    }
    cache[key] = rec
    _save_cache(cache)
    time.sleep(1)  # SteamSpy appdetails: ~1 req/sec
    return rec


def tag_games(tag):
    """Games carrying a SteamSpy tag (1 req / 60s server-side — call sparingly)."""
    t = urllib.parse.quote(tag)
    data = _get(f"{SPY_API}?request=tag&tag={t}") or {}
    return data  # dict: appid -> {name, positive, negative, ...}


# ---------- Composites ----------

def taste(top=12):
    """Weighted taste profile from the most-played owned games.

    Playtime is sqrt-weighted so a single 800h game doesn't drown everything
    else — taste is about breadth of what you enjoy, not one obsession.
    """
    games = owned()
    played = [g for g in games if g["playtime_min"] > 0][:top]
    cache = _load_cache()
    tag_scores, genre_scores = {}, {}
    profiled = []
    for g in played:
        info = spy(g["appid"], cache)
        w = (g["playtime_min"] / 60.0) ** 0.5  # hours, sqrt-damped
        tags = sorted(info["tags"].items(), key=lambda kv: kv[1], reverse=True)[:6]
        total = sum(v for _, v in tags) or 1
        for name, votes in tags:
            tag_scores[name] = tag_scores.get(name, 0) + w * (votes / total)
        for gen in [x.strip() for x in info["genre"].split(",") if x.strip()]:
            genre_scores[gen] = genre_scores.get(gen, 0) + w
        profiled.append({"name": g["name"], "hours": round(g["playtime_min"] / 60, 1),
                         "top_tags": [t for t, _ in tags]})
    return {
        "based_on": profiled,
        "tag_scores": dict(sorted(tag_scores.items(), key=lambda kv: kv[1], reverse=True)),
        "genre_scores": dict(sorted(genre_scores.items(), key=lambda kv: kv[1], reverse=True)),
        "library_size": len(games),
    }


def candidates(limit=20, top_tags=5, min_reviews=500):
    """Unowned games ranked by taste-tag overlap, gated and weighted by quality.

    SteamSpy's tag lists are crowd-tagged and full of shovelware that spams many
    tags (a jigsaw game tagged Strategy+RPG+City-Builder). Ranking on raw tag-match
    count surfaces exactly that junk, so the real signal is: taste overlap × how
    well-liked × is-it-actually-played. We gate out games below `min_reviews` total
    reviews (kills shovelware) and rank by tag-fit × positive-ratio.
    """
    t = taste()
    owned_ids = {g["appid"] for g in owned()}
    top = list(t["tag_scores"].items())[:top_tags]
    pool = {}
    for tag, weight in top:
        for appid, info in tag_games(tag).items():
            aid = int(appid)
            if aid in owned_ids:
                continue
            rec = pool.setdefault(aid, {
                "appid": aid, "name": info.get("name"), "fit": 0.0,
                "matched_tags": [], "positive": info.get("positive", 0),
                "negative": info.get("negative", 0),
            })
            rec["fit"] += weight
            rec["matched_tags"].append(tag)
    ranked = []
    for r in pool.values():
        total = r["positive"] + r["negative"]
        if total < min_reviews:
            continue
        r["total_reviews"] = total
        r["positive_ratio"] = round(r["positive"] / total, 3)
        r["score"] = round(r["fit"] * r["positive_ratio"], 3)
        r["store_url"] = f"https://store.steampowered.com/app/{r['appid']}"
        ranked.append(r)
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return {"taste_tags": [t for t, _ in top], "candidates": ranked[:limit]}


def backlog(limit=15, max_played_min=30):
    """Owned-but-barely-played games ranked by fit with the taste profile."""
    t = taste()
    tag_scores = t["tag_scores"]
    unplayed = [g for g in owned() if g["playtime_min"] <= max_played_min]
    cache = _load_cache()
    scored = []
    for g in unplayed[:60]:  # cap SteamSpy calls
        info = spy(g["appid"], cache)
        tags = list(info["tags"].keys())
        match = [tg for tg in tags if tg in tag_scores]
        score = sum(tag_scores[tg] for tg in match)
        scored.append({
            "appid": g["appid"], "name": g["name"],
            "playtime_min": g["playtime_min"],
            "matched_tags": match[:6], "score": round(score, 3),
            "store_url": f"https://store.steampowered.com/app/{g['appid']}",
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    return {"taste_tags": list(tag_scores)[:8], "backlog": scored[:limit]}


STORE_API = "https://store.steampowered.com/api/appdetails"
DECK_API = "https://store.steampowered.com/saleaction/ajaxgetdeckappcompatibilityreport"
DECK_LABEL = {0: "unknown", 1: "unsupported", 2: "playable", 3: "verified"}


def store_price(appid, cc="kr"):
    """Steam store price_overview for a region. None if free/unavailable."""
    data = _get(f"{STORE_API}?appids={appid}&cc={cc}&filters=price_overview") or {}
    rec = data.get(str(appid), {})
    if not rec.get("success"):
        return None
    return (rec.get("data") or {}).get("price_overview")


def deck_compat(appid):
    """Steam Deck compatibility category: 0 unknown, 1 unsupported, 2 playable, 3 verified."""
    data = _get(f"{DECK_API}?nAppID={appid}&l=english") or {}
    return (data.get("results") or {}).get("resolved_category")


def _fmt_money(amount, currency):
    if amount is None:
        return None
    if currency == "KRW":
        return f"₩{amount:,.0f}"
    return f"{amount:g} {currency}"


def _itad_id(appid, cache):
    key = str(appid)
    if key in cache:
        return cache[key]
    lk = _get(f"{ITAD_API}/games/lookup/v1?key={ITAD_KEY}&appid={appid}") or {}
    gid = lk.get("game", {}).get("id") if lk.get("found") else None
    cache[key] = gid
    try:
        ITAD_CACHE.write_text(json.dumps(cache))
    except Exception:
        pass
    return gid


def itad_lows(appids, country="KR"):
    """Price history per Steam appid: current vs all-time low (IsThereAnyDeal).

    Returns {appid: {historic_low, historic_low_date, current_price, current_cut,
    is_historic_low, pct_above_low}} — None for games ITAD can't resolve.
    """
    if not ITAD_KEY:
        sys.exit("Price history needs an IsThereAnyDeal key. Set ITAD_API_KEY "
                 "(free at https://isthereanydeal.com/apps/my/).")
    country = country.upper()
    cache = json.loads(ITAD_CACHE.read_text()) if ITAD_CACHE.exists() else {}
    ids = {aid: _itad_id(aid, cache) for aid in appids}
    gids = [g for g in ids.values() if g]
    by_gid = {}
    if gids:
        body = json.dumps(gids).encode()
        req = urllib.request.Request(
            f"{ITAD_API}/games/overview/v2?key={ITAD_KEY}&country={country}",
            data=body, headers={"User-Agent": "steam-recommend/1.0", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            ov = json.loads(r.read().decode("utf-8"))
        by_gid = {p["id"]: p for p in ov.get("prices", [])}
    out = {}
    for aid, gid in ids.items():
        p = by_gid.get(gid)
        if not p:
            out[aid] = None
            continue
        cur, low = p.get("current") or {}, p.get("lowest") or {}
        cur_amt = (cur.get("price") or {}).get("amount")
        low_amt = (low.get("price") or {}).get("amount")
        cur_curr = (cur.get("price") or {}).get("currency", country)
        low_curr = (low.get("price") or {}).get("currency", country)
        pct = None
        is_low = False
        if cur_amt is not None and low_amt:
            pct = round((cur_amt - low_amt) / low_amt * 100, 1)
            is_low = cur_amt <= low_amt + 1e-6
        out[aid] = {
            "current_price": _fmt_money(cur_amt, cur_curr), "current_cut": cur.get("cut"),
            "historic_low": _fmt_money(low_amt, low_curr), "historic_low_cut": low.get("cut"),
            "historic_low_date": (low.get("timestamp") or "")[:10],
            "is_historic_low": is_low, "pct_above_low": pct,
        }
    return out


def _enrich_itad(records, country="KR"):
    """Attach ITAD price-history fields to records that carry an 'appid'."""
    if not records or not ITAD_KEY:
        return records
    lows = itad_lows([r["appid"] for r in records], country)
    for r in records:
        r["price_history"] = lows.get(r["appid"])
    return records


def _deal_record(appid, info, cc, deck_min, scan_state):
    """Return a deal dict if appid is on sale AND Deck-playable+, else None."""
    po = store_price(appid, cc)
    time.sleep(0.25)
    if not po or po.get("discount_percent", 0) <= 0:
        return None
    cat = deck_compat(appid)
    time.sleep(0.25)
    if cat is None or cat < deck_min:
        return None
    p, n = info.get("positive", 0), info.get("negative", 0)
    tot = p + n
    return {
        "appid": appid, "name": info.get("name"),
        "discount_percent": po["discount_percent"],
        "price": po.get("final_formatted"), "was": po.get("initial_formatted"),
        "deck": DECK_LABEL.get(cat, str(cat)),
        "positive_ratio": round(p / tot, 3) if tot else None, "total_reviews": tot,
        "store_url": f"https://store.steampowered.com/app/{appid}",
    }


def diverse_deals(tags, cc="kr", deck_min=2, per_tag=1, min_reviews=500, scan_per_tag=25):
    """One genre per tag: for each tag, the most-popular on-sale + Deck-playable unowned game.

    Ranks each tag's games by positive-review COUNT (popularity × liked), so you get the
    recognizable standout of each genre rather than the global tag-overlap winner — which is
    what collapses everything into one genre.
    """
    owned_ids = {g["appid"] for g in owned()}
    chosen = set()
    out = []
    for tag in tags:
        games = tag_games(tag)
        ranked = sorted(
            ((int(a), i) for a, i in games.items()
             if int(a) not in owned_ids and (i.get("positive", 0) + i.get("negative", 0)) >= min_reviews),
            key=lambda x: x[1].get("positive", 0), reverse=True,
        )
        picks, scanned = [], 0
        for aid, info in ranked:
            if aid in chosen or scanned >= scan_per_tag:
                if scanned >= scan_per_tag:
                    break
                continue
            scanned += 1
            rec = _deal_record(aid, info, cc, deck_min, None)
            if rec:
                rec["genre"] = tag
                picks.append(rec)
                chosen.add(aid)
                if len(picks) >= per_tag:
                    break
        out.append({"tag": tag, "picks": picks})
    _enrich_itad([p for blk in out for p in blk["picks"]], cc)
    return {"diverse": out}


def deals(limit=12, top_tags=6, min_reviews=300, cc="kr", deck_min=2, scan=120):
    """Unowned, taste-matched games that are BOTH on sale and Deck-playable+.

    Pulls a wide candidate pool (ranked by taste fit), then for each — in fit order —
    checks the live store price first (cheap, most games aren't discounted) and only
    when discounted checks the Deck compatibility report. Stops once `limit` games
    clear both gates, so it rarely scans the whole pool.
    """
    pool = candidates(limit=scan, top_tags=top_tags, min_reviews=min_reviews)["candidates"]
    out = []
    for r in pool:
        po = store_price(r["appid"], cc)
        time.sleep(0.25)
        if not po or po.get("discount_percent", 0) <= 0:
            continue
        cat = deck_compat(r["appid"])
        time.sleep(0.25)
        if cat is None or cat < deck_min:
            continue
        out.append({
            "appid": r["appid"], "name": r["name"],
            "discount_percent": po["discount_percent"],
            "price": po.get("final_formatted"),
            "was": po.get("initial_formatted"),
            "deck": DECK_LABEL.get(cat, str(cat)),
            "positive_ratio": r["positive_ratio"], "total_reviews": r["total_reviews"],
            "matched_tags": r["matched_tags"], "score": r["score"],
            "store_url": r["store_url"],
        })
        if len(out) >= limit:
            break
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"deals": _enrich_itad(out, cc)}


def check(appids, cc="kr"):
    """Validate specific games before recommending: owned?, on sale?, Deck?, rating.

    Use this whenever you hand-pick titles instead of going through `candidates`/`deals`
    — the composites filter owned games for you, but a manual list does not, so checking
    here prevents recommending something the user already owns.
    """
    owned_map = {g["appid"]: g for g in owned()}
    out = []
    for aid in appids:
        g = owned_map.get(aid)
        po = store_price(aid, cc) or {}
        time.sleep(0.25)
        cat = deck_compat(aid)
        time.sleep(0.25)
        sp = spy(aid)
        p, n = sp.get("positive", 0), sp.get("negative", 0)
        out.append({
            "appid": aid, "name": sp.get("name"),
            "owned": bool(g), "playtime_min": g["playtime_min"] if g else 0,
            "discount_percent": po.get("discount_percent", 0),
            "price": po.get("final_formatted"),
            "deck": DECK_LABEL.get(cat, str(cat)),
            "positive_ratio": round(p / (p + n), 3) if (p + n) else None,
            "total_reviews": p + n,
            "store_url": f"https://store.steampowered.com/app/{aid}",
        })
    return _enrich_itad(out, cc)


def histlow(appids, country="KR"):
    """Price-history lookup for specific games (current vs all-time low)."""
    lows = itad_lows(appids, country)
    owned_map = {g["appid"]: g for g in owned()}
    out = []
    for aid in appids:
        sp = spy(aid)
        rec = {"appid": aid, "name": sp.get("name"), "owned": aid in owned_map,
               "store_url": f"https://store.steampowered.com/app/{aid}"}
        rec.update(lows.get(aid) or {"price_history": None})
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser(description="Steam library + SteamSpy helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profile")
    sub.add_parser("owned")
    sub.add_parser("recent")
    sp = sub.add_parser("spy"); sp.add_argument("appid", type=int)
    tg = sub.add_parser("tag"); tg.add_argument("name")
    ts = sub.add_parser("taste"); ts.add_argument("--top", type=int, default=12)
    cd = sub.add_parser("candidates")
    cd.add_argument("--limit", type=int, default=20); cd.add_argument("--top-tags", type=int, default=5)
    cd.add_argument("--min-reviews", type=int, default=500)
    bl = sub.add_parser("backlog"); bl.add_argument("--limit", type=int, default=15)
    dl = sub.add_parser("deals")
    dl.add_argument("--limit", type=int, default=12); dl.add_argument("--cc", default="kr")
    dl.add_argument("--deck-min", type=int, default=2); dl.add_argument("--scan", type=int, default=120)
    dl.add_argument("--tags", default=None, help="comma-separated tags -> one genre per tag (diverse mode)")
    dl.add_argument("--per-tag", type=int, default=1)
    ck = sub.add_parser("check"); ck.add_argument("appids", type=int, nargs="+"); ck.add_argument("--cc", default="kr")
    hl = sub.add_parser("histlow"); hl.add_argument("appids", type=int, nargs="+"); hl.add_argument("--country", default="KR")
    args = ap.parse_args()

    if args.cmd == "profile":
        out = profile()
    elif args.cmd == "owned":
        out = owned()
    elif args.cmd == "recent":
        out = recent()
    elif args.cmd == "spy":
        out = spy(args.appid)
    elif args.cmd == "tag":
        out = tag_games(args.name)
    elif args.cmd == "taste":
        out = taste(args.top)
    elif args.cmd == "candidates":
        out = candidates(args.limit, args.top_tags, args.min_reviews)
    elif args.cmd == "backlog":
        out = backlog(args.limit)
    elif args.cmd == "deals":
        if args.tags:
            out = diverse_deals([t.strip() for t in args.tags.split(",") if t.strip()],
                                cc=args.cc, deck_min=args.deck_min, per_tag=args.per_tag)
        else:
            out = deals(limit=args.limit, cc=args.cc, deck_min=args.deck_min, scan=args.scan)
    elif args.cmd == "check":
        out = check(args.appids, args.cc)
    elif args.cmd == "histlow":
        out = histlow(args.appids, args.country)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
