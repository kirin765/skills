#!/usr/bin/env python3
"""
Tier 1 (combined_score >= 6) 글을 클러스터링용 압축 텍스트 번들로 생성.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
SCORED = ROOT / "signals" / "all-scored.jsonl"
OUT = ROOT / "signals" / "tier1_bundle.txt"
THRESHOLD = 6.0
MAX_BODY = 350
MAX_COMMENT = 200
MAX_COMMENTS_PER_POST = 5


def main():
    rows = [json.loads(l) for l in SCORED.open()]
    rows = [r for r in rows if r["combined_score"] >= THRESHOLD]
    rows.sort(key=lambda x: x["combined_score"], reverse=True)

    lines = []
    lines.append(f"# Tier 1 dcinside (score >= {THRESHOLD}) — {len(rows)}건\n")
    for i, r in enumerate(rows, 1):
        body = (r.get("body") or "").replace("\n", " ").strip()
        if len(body) > MAX_BODY:
            body = body[:MAX_BODY] + "..."
        akey = r["author_key"].replace("ip:", "").replace("uid:", "")
        lines.append(f"\n=== #{i} | {r['gall']} | s={r['combined_score']} | author={akey} | val={r['validators_count']} ===")
        lines.append(f"TITLE: {r['title']}")
        lines.append(f"URL: {r['url']}  ({r['date_full'][:10]} · 추천{r['recommend']} · 댓글{r['comment_count']})")
        if body:
            lines.append(f"BODY: {body}")
        # 점수 0보다 큰 또는 validation 있는 댓글만 — 노이즈 줄임
        keep = [c for c in r.get("top_comments", []) if c.get("score", 0) > 0 or c.get("validation")]
        if keep:
            lines.append("COMMENTS:")
            for c in keep[:MAX_COMMENTS_PER_POST]:
                t = (c.get("text") or "").replace("\n", " ").strip()
                if len(t) > MAX_COMMENT:
                    t = t[:MAX_COMMENT] + "..."
                marker = "[VAL]" if c.get("validation") else f"[s={c.get('score',0)}]"
                ip = c.get("ip", "")
                nick = c.get("nick", "")
                lines.append(f"  - {marker} ({nick} {ip}) {t}")

    OUT.write_text("\n".join(lines))
    chars = OUT.stat().st_size
    print(f"저장: {OUT}  ({chars:,} chars, {len(rows)}건)")


if __name__ == "__main__":
    main()
