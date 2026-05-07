#!/usr/bin/env python3
"""
스코어링된 글에 sub-segment 분류 (업종/판매형태/규모/페인) 적용.

extract_signals.py 결과(signals/all-scored.jsonl)와 raw/{gall}_full.jsonl을 읽어
사용자가 정의한 분류 사전으로 글마다 라벨을 붙이고 cross-tab을 출력한다.

분류 사전은 `--config classify.yml` 로 외부 주입 (스킬 사용자가 페르소나에 맞춰 작성).
설정 미지정 시 음식점 기본 사전 사용.

Usage:
  python classify_subsegments.py --gall sajang --score-min 3
  python classify_subsegments.py --config seller-classify.yml --gall smartstore
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

# 음식점 기본 사전 (자영업 V1 분석에서 검증됨)
DEFAULT_CONFIG = {
    "industries": {
        "치킨/배달": ["치킨", "닭팔이", "닭집", "교촌", "굽네", "BBQ", "배달전문"],
        "고깃집": ["고깃집", "고기집", "삼겹살", "갈비", "곱창", "한우"],
        "분식": ["분식", "떡볶이", "김밥", "라볶이"],
        "중식": ["중식당", "중국집", "짜장면", "짬뽕", "마라탕"],
        "일식": ["일식", "초밥", "라멘", "돈까스", "이자카야"],
        "한식": ["한식", "백반", "국밥", "찌개", "밥집", "식당"],
        "카페/디저트": ["카페", "커피숍", "베이커리", "빵집"],
        "술집": ["술집", "포차", "와인바", "맥주집", "호프"],
        "편의점/슈퍼": ["편의점", "GS25", "CU", "세븐일레븐", "슈퍼"],
        "미용": ["미용실", "헤어", "네일", "왁싱"],
        "PC방": ["PC방", "피시방", "피씨방"],
    },
    "scale": {
        "1인": ["1인", "혼자", "혼자서"],
        "부부/가족": ["부부", "여친", "남친", "와이프", "남편"],
        "알바있음": ["알바 ", "알바생"],
        "직원있음": ["직원 "],
    },
    "pains": {
        "인건비": ["인건비", "알바비", "시급", "알바", "직원"],
        "월세": ["월세", "임대료"],
        "권리금": ["권리금", "보증금"],
        "원가": ["식자재", "원가", "물대"],
        "세금": ["부가세", "종소세", "4대보험", "세금"],
        "광고비": ["광고비", "광고", "마케팅"],
        "배달앱": ["배민", "쿠팡이츠", "요기요", "배달수수료"],
    },
}


def classify(text: str, mapping: dict) -> set[str]:
    found = set()
    for cat, kws in mapping.items():
        for kw in kws:
            if kw in text:
                found.add(cat)
                break
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gall", required=True, help="갤러리 ID")
    ap.add_argument("--score-min", type=float, default=3.0, help="포함할 최소 점수")
    ap.add_argument("--config", help="분류 사전 YAML (없으면 음식점 기본)")
    ap.add_argument("--scored", default="signals/all-scored.jsonl")
    ap.add_argument("--raw-dir", default="raw")
    args = ap.parse_args()

    if args.config:
        config = yaml.safe_load(Path(args.config).read_text())
    else:
        config = DEFAULT_CONFIG

    posts = []
    with open(args.scored) as f:
        for line in f:
            d = json.loads(line)
            if d.get("gall") == args.gall and d["combined_score"] >= args.score_min:
                posts.append(d)

    raw_by_no: dict[str, dict] = {}
    raw_path = Path(args.raw_dir) / f"{args.gall}_full.jsonl"
    with raw_path.open() as f:
        for line in f:
            r = json.loads(line)
            raw_by_no[r.get("post_num", "")] = r

    # 카운트
    ind_total: Counter = Counter()
    pain_total: Counter = Counter()
    scale_total: Counter = Counter()
    ind_pain: dict[str, Counter] = defaultdict(Counter)

    for p in posts:
        pn = p.get("post_num") or p.get("url", "").split("no=")[-1]
        raw = raw_by_no.get(pn, {})
        text = (
            p.get("title", "")
            + " "
            + raw.get("body", "")
            + " "
            + " ".join(c.get("text", "") for c in raw.get("comments", []))
        )[:5000]
        inds = classify(text, config.get("industries", {})) or {"미분류"}
        scales = classify(text, config.get("scale", {})) or {"미언급"}
        pains = classify(text, config.get("pains", {}))

        for i in inds:
            ind_total[i] += 1
            for pa in pains:
                ind_pain[i][pa] += 1
        for s in scales:
            scale_total[s] += 1
        for pa in pains:
            pain_total[pa] += 1

    print(f"=== {args.gall} sub-segment 분류 (score≥{args.score_min}, n={len(posts)}) ===\n")
    print("[Industry]")
    for k, v in ind_total.most_common():
        print(f"  {k:18s}: {v:4d}")
    print("\n[Scale]")
    for k, v in scale_total.most_common():
        print(f"  {k:18s}: {v:4d}")
    print("\n[Pain]")
    for k, v in pain_total.most_common():
        print(f"  {k:18s}: {v:4d}")

    # cross-tab
    top_inds = [i for i, _ in ind_total.most_common() if i != "미분류"][:8]
    if top_inds and pain_total:
        all_pains = [p for p, _ in pain_total.most_common()][:8]
        print("\n[Industry × Pain crosstab — % of posts in each industry]")
        header = f"{'industry':18s} {'n':>4s}  " + "  ".join(f"{p[:8]:>9s}" for p in all_pains)
        print(header)
        for ind in top_inds:
            n = ind_total[ind]
            row = f"{ind:18s} {n:>4d}  "
            for pa in all_pains:
                c = ind_pain[ind].get(pa, 0)
                pct = 100 * c / n if n else 0
                row += f"{c:3d}({pct:>3.0f}%) "
            print(row)


if __name__ == "__main__":
    main()
