#!/usr/bin/env python3
"""Collect IG audience data via Osintgraph (raw, no Gemini) and extract promotion metrics.

Two phases:
  collect  — run `osintgraph discover` (and optional `explore`) on each seed, AI analysis skipped.
  extract  — run the Cypher metrics in references/queries.cypher and dump JSON + CSV.

Neo4j creds resolve in order: CLI flags > env (NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD) >
Osintgraph's credentials.json. Run this in the same Python env where `osintgraph` is installed
(so `neo4j` and the `osintgraph` package are importable), or `pip install neo4j` first.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

QUERIES_FILE = Path(__file__).resolve().parent.parent / "references" / "queries.cypher"
EXPLORE_ONLY = {"hub_centrality"}  # degenerate vs shared_interests in discover-only mode


def parse_queries(path):
    blocks, name, buf = {}, None, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^//\s*name:\s*(\S+)", line)
        if m:
            if name:
                blocks[name] = "\n".join(buf).strip().rstrip(";")
            name, buf = m.group(1), []
        elif name is not None:
            buf.append(line)
    if name:
        blocks[name] = "\n".join(buf).strip().rstrip(";")
    return blocks


def load_osintgraph_credentials(explicit):
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    try:
        import osintgraph  # noqa: only to locate the package dir
        candidates.append(Path(osintgraph.__file__).resolve().parent / "credentials.json")
    except Exception:
        pass
    home = Path.home()
    for pat in (
        ".local/pipx/venvs/osintgraph/lib/python*/site-packages/osintgraph/credentials.json",
        ".local/share/pipx/venvs/osintgraph/lib/python*/site-packages/osintgraph/credentials.json",
        ".local/pipx/venvs/osintgraph/lib/python*/site-packages/osintgraph-*/osintgraph/credentials.json",
    ):
        candidates.extend(home.glob(pat))
    for c in candidates:
        try:
            if c and c.exists():
                return json.loads(c.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def resolve_neo4j(args):
    creds = load_osintgraph_credentials(args.osintgraph_credentials) or {}
    uri = args.neo4j_uri or os.environ.get("NEO4J_URI") or creds.get("NEO4J_URI")
    user = args.neo4j_user or os.environ.get("NEO4J_USERNAME") or creds.get("NEO4J_USERNAME")
    pwd = args.neo4j_password or os.environ.get("NEO4J_PASSWORD") or creds.get("NEO4J_PASSWORD")
    if not (uri and user and pwd):
        sys.exit(
            "Neo4j credentials not found. Provide them one of three ways:\n"
            "  --neo4j-uri ... --neo4j-user ... --neo4j-password ...\n"
            "  export NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD\n"
            "  --osintgraph-credentials /path/to/credentials.json"
        )
    return uri, user, pwd


def discover_cmd(seed, args):
    return [
        "osintgraph", "discover", seed,
        "--skip", "post-analysis", "account-analysis",
        "--limit", f"follower={args.limit_follower}", f"followee={args.limit_followee}", f"post={args.limit_post}",
        "--rate-limit", str(args.rate_limit),
    ]


def explore_cmd(seed, args):
    return [
        "osintgraph", "explore", seed, "--max", str(args.explore),
        "--skip", "post-analysis", "account-analysis",
        "--limit", f"follower={args.limit_follower}", f"followee={args.limit_followee}", f"post={args.limit_post}",
        "--rate-limit", str(args.rate_limit),
    ]


def run_collect(seeds, args):
    creds = load_osintgraph_credentials(args.osintgraph_credentials) or {}
    ig = creds.get("INSTAGRAM_USERNAME", "<unknown — run `osintgraph setup instagram`>")
    if not args.yes:
        sys.exit(
            f"\nCollection scrapes Instagram as account: {ig}\n"
            "This MUST be a burner account, never your main promo account (IG ToS / ban risk).\n"
            "Re-run with --yes once you've confirmed the account above is a burner."
        )
    print(f"[collect] scraping as IG account: {ig}", flush=True)
    for seed in seeds:
        cmd = discover_cmd(seed, args)
        print(f"\n>>> {' '.join(cmd)}", flush=True)
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"!! discover {seed} exited {rc} (osintgraph is resumable — rerun to continue)", flush=True)
        if args.explore:
            ecmd = explore_cmd(seed, args)
            print(f"\n>>> {' '.join(ecmd)}", flush=True)
            subprocess.call(ecmd)


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(["|".join(map(str, v)) if isinstance(v, list) else ("" if v is None else v) for v in (r.get(c) for c in cols)])


def run_extract(seeds, args, outdir):
    try:
        from neo4j import GraphDatabase
    except Exception:
        sys.exit("The `neo4j` driver is not importable. Run this in osintgraph's env, or `pip install neo4j`.")
    uri, user, pwd = resolve_neo4j(args)
    queries = parse_queries(QUERIES_FILE)
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    summary = {"seeds": seeds, "min_seeds": args.min_seeds, "top": args.top, "counts": {}, "skipped": []}
    try:
        with driver.session() as session:
            for name, cypher in queries.items():
                if name in EXPLORE_ONLY and not args.explore:
                    summary["skipped"].append(name)
                    continue
                rows = session.run(cypher, seeds=seeds, min_seeds=args.min_seeds, top=args.top).data()
                (outdir / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
                write_csv(outdir / f"{name}.csv", rows)
                summary["counts"][name] = len(rows)
    finally:
        driver.close()
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description="Collect + extract IG audience/content intelligence via Osintgraph.")
    ap.add_argument("seeds", nargs="+", help="Seed Instagram usernames (competitor/representative accounts in your niche).")
    ap.add_argument("--niche", default="run", help="Label used in the output directory name.")
    ap.add_argument("--out", default=None, help="Output directory (default: ./ig-audience-<niche>-<date>).")
    ap.add_argument("--extract-only", action="store_true", help="Skip collection; only run the Cypher metrics.")
    ap.add_argument("--yes", action="store_true", help="Confirm the configured IG account is a burner; required to collect.")
    ap.add_argument("--explore", type=int, default=0, metavar="N", help="Also run `osintgraph explore <seed> --max N` (default 0 = off).")
    ap.add_argument("--limit-follower", type=int, default=1000)
    ap.add_argument("--limit-followee", type=int, default=1000)
    ap.add_argument("--limit-post", type=int, default=10)
    ap.add_argument("--rate-limit", type=int, default=200, help="osintgraph: pause 8-10 min after every N requests.")
    ap.add_argument("--min-seeds", type=int, default=2, help="Overlap threshold for the 'shared' metrics.")
    ap.add_argument("--top", type=int, default=100, help="Rows per ranked metric.")
    ap.add_argument("--neo4j-uri", default=None)
    ap.add_argument("--neo4j-user", default=None)
    ap.add_argument("--neo4j-password", default=None)
    ap.add_argument("--osintgraph-credentials", default=None, help="Path to osintgraph credentials.json.")
    args = ap.parse_args()

    seeds = [s.strip().lstrip("@") for s in args.seeds if s.strip()]
    outdir = Path(args.out) if args.out else Path.cwd() / f"ig-audience-{args.niche}-{date.today().isoformat()}"
    outdir.mkdir(parents=True, exist_ok=True)

    if not args.extract_only:
        run_collect(seeds, args)

    summary = run_extract(seeds, args, outdir)

    print("\n=== extraction summary ===")
    print(f"seeds: {', '.join(seeds)}  | min_seeds={args.min_seeds} top={args.top}")
    for name, n in summary["counts"].items():
        print(f"  {name:24s} {n} rows")
    if summary["skipped"]:
        print(f"  skipped (need --explore): {', '.join(summary['skipped'])}")
    print(f"output: {outdir}")
    print("Check seed_profile.json: followers_scraped/followees_scraped/posts_scraped should be true for each seed.")


if __name__ == "__main__":
    main()
