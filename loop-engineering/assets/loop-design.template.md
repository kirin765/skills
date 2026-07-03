# Loop Design Doc · <loop-name>

_Produced by the loop-engineering coach. This is the spec for the loop — build it in the rollout order at the bottom, not all at once._

## Qualification verdict
- **Verdict:** ✅ qualifies / ❌ not yet
- **4-condition test:** repeats weekly [ ] · automated verification [ ] · budget absorbs waste [ ] · agent has senior tools [ ]
- **30-second check:** ≥weekly [ ] · gate can reject [ ] · agent can run the code [ ] · hard stop [ ] · human reviews irreversible [ ]
- **Not an off-limits task** (architecture / auth / payments / prod deploy / judgment call): confirmed [ ]

## The task
<one concrete, recurring, machine-checkable task>

## The four parts (Minimum Viable Loop)

### 1. Gate (the objective check — decides whether the loop helps or just spends)
```
<literal command that exits non-zero on failure>
```

### 2. State file
- Home: `STATE.md` in repo / external (<Linear / Issues / DB>)
- Standing spec reread each run (optional): `<VISION.md / AGENTS.md>`

### 3. Skill
- Path: `.claude/skills/<loop-name>/SKILL.md`
- Holds: <the conventions / fix patterns / never-touch paths written once>

### 4. Automation
- Primitive: `/loop <interval>` (+ `/goal <condition>`) / Routine / CronCreate / scheduled task
- Cadence: <e.g. nightly 03:00 / on PR open / weekly Mon>
- **Hard stop:** <iteration count / token budget / time limit>
- Stop condition (`/goal`): <objective, checked by a fresh model>

### Maker/checker split (optional)
- Verifier subagent: <yes/no> — <different instructions + model, no exposure to maker's reasoning>

## Failure-mode mitigations (standing practice)
- **Ralph Wiggum:** objective gate + hard stop + `/goal` checked by fresh model.
- **Goal drift:** reread `<standing spec>` each run.
- **Comprehension debt / cognitive surrender:** read the diffs; spot-check the gate; keep off architecture; pair-design.
- **Security tax:** security checks in the gate (SAST / dep audit / secret scan); audit skills before install; no verbose logging in prod; re-audit permissions every 30 days.

## Rollout order (do not skip ahead)
1. Get **one manual run** reliable.
2. Turn it into the **skill**.
3. Wrap it in the **loop** (automation + gate + state).
4. Then **schedule** it.

## Success metric
**Cost per accepted change.** If the accepted-change rate drops below ~50%, tighten the gate or narrow the task before scaling — you're doing the review work the loop was supposed to save.
