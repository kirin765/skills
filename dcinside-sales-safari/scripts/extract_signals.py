#!/usr/bin/env python3
"""
dcinside 본문+댓글에서 pain 신호 추출, 스코어링, 상위 후보 마크다운 출력.

입력: raw/{gall}_full.jsonl (메타 + body + comments[])
출력:
  signals/all-scored.jsonl — 각 글의 점수와 hits
  signals/top-{N}.md — 상위 N건 verbatim 검토용

Usage:
  python extract_signals.py
  python extract_signals.py --top 300
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "raw"
SIG_DIR = ROOT / "signals"
VOCAB_FILE = ROOT / "pain-vocab.yml"

WEIGHTS = {
    "explicit_gap": 3,
    "time_money_waste": 2,
    "workaround_share": 1,
    "emotion_high": 1,
    "peer_validation": 0,   # 점수에 직접 반영 X — 별도 카운트로 활용
}
MAX_HITS_PER_CAT = 5


def compile_vocab(vocab: dict) -> dict:
    out = {}
    for cat, terms in vocab.items():
        compiled = []
        for t in terms or []:
            if isinstance(t, str) and t.startswith("re:"):
                compiled.append(("regex", re.compile(t[3:])))
            else:
                compiled.append(("lit", t))
        out[cat] = compiled
    return out


def score_text(text: str, compiled: dict) -> tuple[int, dict]:
    if not text:
        return 0, {}
    hits: dict[str, list[str]] = {}
    score = 0
    for cat, patterns in compiled.items():
        cat_hits: list[str] = []
        for kind, p in patterns:
            if kind == "lit":
                if p in text:
                    cat_hits.append(p)
            else:
                m = p.search(text)
                if m:
                    cat_hits.append(m.group(0))
            if len(cat_hits) >= MAX_HITS_PER_CAT:
                break
        if cat_hits:
            hits[cat] = cat_hits
            score += WEIGHTS.get(cat, 0) * len(cat_hits)
    return score, hits


def author_key(rec: dict) -> str:
    """글 작성자 dedup 키 — uid 우선, 없으면 ip+nick."""
    uid = rec.get("writer_uid", "") or ""
    if uid:
        return f"uid:{uid}"
    return f"ip:{rec.get('writer_ip','')}/{rec.get('writer_nick','')}"


def comment_author_key(c: dict) -> str:
    ip = c.get("ip", "") or ""
    nick = c.get("nick", "") or ""
    if ip:
        return f"ip:{ip}/{nick}"
    return f"nick:{nick}"


def process_record(rec: dict, compiled: dict) -> dict:
    body_score, body_hits = score_text(rec.get("body", ""), compiled)
    body_validation = body_hits.pop("peer_validation", []) if "peer_validation" in body_hits else []

    comment_pain_score = 0
    comment_pain_hits: dict[str, list[str]] = defaultdict(list)
    validators: set[str] = set()
    pain_commenters: set[str] = set()
    scored_comments = []
    for c in rec.get("comments", []):
        cs, ch = score_text(c.get("text", ""), compiled)
        validation_hits = ch.pop("peer_validation", []) if "peer_validation" in ch else []
        if validation_hits:
            validators.add(comment_author_key(c))
        if ch:
            pain_commenters.add(comment_author_key(c))
            for cat, terms in ch.items():
                comment_pain_hits[cat].extend(terms[:2])
            comment_pain_score += cs
        scored_comments.append({**c, "score": cs, "hits": ch, "validation": validation_hits})

    combined = body_score + 0.5 * comment_pain_score + 1.0 * len(validators)
    top_comments = sorted(scored_comments, key=lambda x: x["score"], reverse=True)[:5]

    return {
        "post_num": rec["post_num"],
        "title": rec["title"],
        "url": rec["url"],
        "date_full": rec["date_full"],
        "recommend": rec["recommend"],
        "comment_count": rec["comment_count"],
        "writer_nick": rec["writer_nick"],
        "writer_ip": rec["writer_ip"],
        "writer_uid": rec["writer_uid"],
        "author_key": author_key(rec),
        "body": rec.get("body", ""),
        "body_score": body_score,
        "body_hits": body_hits,
        "comment_pain_score": comment_pain_score,
        "comment_pain_hits": dict(comment_pain_hits),
        "validators_count": len(validators),
        "pain_commenters_count": len(pain_commenters),
        "combined_score": round(combined, 2),
        "top_comments": top_comments,
        "all_comments_count": len(rec.get("comments", [])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=300)
    ap.add_argument("--galls", nargs="+", default=["sajang", "smartstore"])
    args = ap.parse_args()

    SIG_DIR.mkdir(parents=True, exist_ok=True)
    vocab = yaml.safe_load(VOCAB_FILE.read_text())
    compiled = compile_vocab(vocab)

    all_results: list[dict] = []
    by_gall: Counter = Counter()
    for gall in args.galls:
        path = RAW_DIR / f"{gall}_full.jsonl"
        if not path.exists():
            print(f"skip (없음): {path}")
            continue
        for line in path.open():
            rec = json.loads(line)
            r = process_record(rec, compiled)
            r["gall"] = gall
            all_results.append(r)
            by_gall[gall] += 1

    all_results.sort(key=lambda x: x["combined_score"], reverse=True)

    out_path = SIG_DIR / "all-scored.jsonl"
    with out_path.open("w") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 분포 요약
    print(f"전체 {len(all_results)}건  ({dict(by_gall)})")
    score_counter = Counter()
    for r in all_results:
        s = r["combined_score"]
        if s == 0:
            score_counter["0"] += 1
        elif s < 3:
            score_counter["1-2"] += 1
        elif s < 6:
            score_counter["3-5"] += 1
        elif s < 12:
            score_counter["6-11"] += 1
        else:
            score_counter["12+"] += 1
    print(f"점수 분포: {dict(score_counter)}")

    # top-N 마크다운
    md_path = SIG_DIR / f"top-{args.top}.md"
    with md_path.open("w") as f:
        f.write(f"# dcinside 상위 {args.top} pain 신호\n\n")
        f.write(f"전체 {len(all_results)}건 / 갤별 {dict(by_gall)}\n\n")
        for i, r in enumerate(all_results[: args.top], 1):
            f.write(f"## #{i} [{r['gall']}] score={r['combined_score']} (body={r['body_score']}, cmt_pain={r['comment_pain_score']}, validators={r['validators_count']})\n\n")
            f.write(f"**{r['title']}** — {r['date_full'][:10]} · 추천 {r['recommend']} · 댓글 {r['comment_count']}\n\n")
            f.write(f"<{r['url']}>\n\n")
            if r["body_hits"]:
                f.write(f"본문 hits: {r['body_hits']}\n\n")
            if r["body"]:
                body_preview = r["body"][:600] + ("..." if len(r["body"]) > 600 else "")
                f.write(f"```\n{body_preview}\n```\n\n")
            if r["top_comments"]:
                f.write("**top 댓글**:\n")
                for c in r["top_comments"][:3]:
                    if c["score"] == 0 and not c["validation"]:
                        continue
                    f.write(f"- ({c['nick']} {c['ip']}) [{c['score']}] {c['text'][:300]}\n")
                f.write("\n")
            f.write("---\n\n")
    print(f"마크다운: {md_path}")


if __name__ == "__main__":
    main()
