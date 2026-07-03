---
name: loop-engineering
description: Interactive coach that walks the user through designing an agentic "loop" — a small self-prompting system that finds work, hands it to a coding agent, checks the result with an objective gate, records state, and decides the next move on its own. Runs the 14-step "prompter → loop designer" roadmap as a gated, one-question-at-a-time wizard — it first QUALIFIES the task (the 4-condition test + 30-second checklist) and will honestly tell the user to keep prompting by hand if the task doesn't earn a loop, then — only if it passes — helps them assemble the Minimum Viable Loop (one automation, one skill, one state file, one gate) as concrete Claude Code artifacts, and hardens it against the known failure modes (Ralph Wiggum quiet-failure, comprehension debt, the security tax). Use this whenever the user wants to automate a repetitive coding-agent task, build a self-prompting or "set it and forget it" agent, design a CI-triage / dependency-bump / lint-and-fix / issue-to-PR loop, asks "should I turn this into a loop / automate this", "루프 만들어줘", "이 작업 자동화 루프 짜줘", "에이전트가 알아서 반복하게", "loop engineering", "build me an agent loop", "loop designer", or is about to schedule a recurring agent and hasn't checked whether a loop is even worth it. This is the DESIGN + qualification coach — distinct from the built-in /loop, which merely reruns a command on a cadence; this decides whether a loop should exist and architects its four parts. Do NOT use it to design loops for architecture rewrites, auth/payments code, production deploys, or judgment-call work — steer those back to a human in the chair.
---

# loop-engineering

## What this skill is for

For two years the way you got work out of a coding agent was: write a prompt, share context, read the diff, write the next prompt. You held the tool the whole time. **That is the part that's ending.** A *loop* is a small system that finds the work, hands it to the agent, checks the result against an objective gate, records what happened, and decides the next move — on its own. You design it once; it prompts the agent from then on.

The leverage moved one floor up: from typing prompts to designing the system that prompts. Your job in this skill is to take the user from *prompter* to *loop designer* — but **honestly**, because the single most valuable thing this skill does is tell most users *"not yet."* A loop that doesn't earn its cost is a money pit that grades its own homework. Qualifying the task is the product; the design is the reward for passing.

Source: the 14-step roadmap (Addy Osmani's loop-engineering essay + Anthropic's engineering docs + AlphaSignal's economics analysis). Deep detail lives in `references/roadmap.md`; the concrete Claude Code tool mapping in `references/claude-code-primitives.md`; the failure catalog in `references/failure-modes.md`.

## How to run this — the one rule that matters

**Go one stage at a time and actually wait.** The user asked to be walked through this step by step. Do not front-run: don't invent their gate command, don't assume their cadence, don't dump the whole design in one message. Ask the questions for the current stage, stop, read their answer, then move on. Use `AskUserQuestion` for the discrete either/or gates (it's faster for the user than free text); use plain prose questions when you need their specifics (the literal task, the literal test command).

Converse in the user's language (they may be writing Korean). Keep each stage short — this is a clinic, not a lecture. When a stage's reasoning gets deep, pull from the reference files rather than pasting theory inline.

Track progress with a short todo list of the stages below so neither of you loses the thread.

---

## Stage A — Frame and capture the task

Open by naming what a loop is in one or two sentences (above), then ask **what specific, recurring task** they're picturing automating. You need a concrete answer, not "my workflow" — e.g. "triage nightly CI failures," "open dependency-bump PRs weekly," "run a lint-and-fix pass on every PR." Pull it from the conversation if it's already there; don't re-ask.

If they don't have a specific task yet, offer the canonical *good first loops* to react to (full list + why in `references/roadmap.md`):

- **CI failure triage** — nightly: scan failures, classify cause, draft fix PRs for the easy ones.
- **Dependency bump PRs** — weekly: scan for updates, test compatibility, open PRs.
- **Lint-and-fix passes** — on every PR-open: apply style fixes automatically.
- **Flaky-test reproduction** — loop until a theory survives the test.
- **Issue-to-PR drafts** — on a codebase with strong tests that reject bad output.

Once you have the task, go to the gate. Don't design anything yet.

---

## Stage B — The qualification gate (do NOT skip; you may stop here)

This is the honest part most threads skip. A loop earns its cost only under four conditions; miss one and it costs more than it returns. Walk them as real questions — `AskUserQuestion` works well here with one question per condition, or bundle them. **Be willing to end the session at a fail.** Recommending "keep this as a manual prompt" (or "go build the test suite *first*, then come back") is a successful outcome of this skill, not a failure.

**The 4-condition test** — all four must hold:

1. **The task repeats — at least weekly.** A loop amortizes setup across many runs. Less than weekly and the setup cost never pays back — you have a script you ran once, not a loop.
2. **Verification is automated.** There is a test suite / type checker / linter / build that can *fail the work without you in the room*. No automated gate → you're back in the chair reading every diff, which is the exact job the loop was supposed to remove.
3. **The token budget can absorb the waste.** Loops re-read context, retry, and explore — that burns tokens whether or not a run ships anything. On a metered/consumer plan running heavy verification, the bill arrives before the productivity gain. (Economics detail in `references/roadmap.md` §03.)
4. **The agent has a senior engineer's tools.** Logs, a reproduction environment, the ability to run the code it writes and see what breaks. Without that, the loop iterates blind.

Then the tactical **30-second check** — the box-ticking on *this specific* task. Miss one box → keep it a manual prompt:

- [ ] Happens at least weekly.
- [ ] A test / type check / build / linter can *reject* bad output.
- [ ] The agent can *run* the code it changes.
- [ ] The loop has a **hard stop** — token budget, iteration count, or time limit.
- [ ] A **human reviews** before merge / deploy / dependency change (anything irreversible).

**Hard refusal — these need a human in the chair, do not design a loop for them** even if the 4 conditions technically pass: architecture rewrites, auth or payments code, production deploys, vague product work, anything where "done" is a judgment call. If their task is one of these, say so plainly and stop. Comprehension debt and blast radius make these the wrong first loop (and often the wrong loop ever).

**Verdict:** state clearly — ✅ *qualifies*, or ❌ *not yet* with the specific failing condition and what would have to change. Only continue to Stage C on a ✅.

---

## Stage C — Choose the loop shape

They passed. Before building, pin down the shape so the pieces have something to hang on. Confirm (or pick) which pattern their task is closest to from the good-first-loop list, because the pattern implies the gate and the state fields. Keep the ambition low: **the smallest loop that works, no swarm.** Talk them out of a multi-agent fleet on run one — parallelism is a Stage-D refinement, and *their review bandwidth*, not the tooling, is the real ceiling on how many agents they can run.

---

## Stage D — Design the Minimum Viable Loop (four parts)

Build the four parts in this order, **asking per part**. Order matters because the gate constrains everything and the automation should be wired last. For each part, capture the user's concrete answer and draft the actual artifact (templates in `assets/`). Tool-by-tool Claude Code mapping is in `references/claude-code-primitives.md` — read it before proposing a specific command so you recommend something that exists in their environment.

### D1 — The gate (most important; decide this first)
Ask for the **literal command** that fails bad work by exiting non-zero: `npm test`, `pytest -q`, `tsc --noEmit`, `ruff check`, `cargo build`, a CI job. This is the part that decides whether the loop helps or just spends. It must be *objective* — a test that passes or fails, a build that compiles or doesn't — **not** a second agent "reviewing" and having an opinion (that's the Ralph Wiggum trap, Stage E). If they can't name one command, they actually failed condition 2 — go back to Stage B.

### D2 — The state file (the agent forgets; the file does not)
A loop without persistent state restarts every run; with state it *resumes*. Ask where it should live:
- **`STATE.md` in the repo** — version-controlled, diff-readable, simple. Best for solo / small-team.
- **External** (Linear / GitHub Issues / a DB) — queryable, survives across repos, team-visible. Best for production loops.

Scaffold it from `assets/STATE.template.md` with their real context: last run, in-progress, completed, escalated-to-humans, and a **lessons-learned** section (write learnings here, not in chat). For long-runners that risk drifting off-goal, pair it with a standing `VISION.md`/`AGENTS.md` the agent rereads each run — *state says where it is, the spec says where to go*.

### D3 — The skill (write project knowledge once, read every run)
Without a skill the loop re-derives your whole project context from zero every cycle; with one, intent compounds. Ask for the conventions, build steps, the "we don't do it like this because of that one incident," and the never-touch paths. Scaffold a `SKILL.md` for *their loop's task* from `assets/loop-skill.template.md` (classification rules, fix patterns, a "Never do" list, and a pointer to update the state file each run).

### D4 — The automation (the heartbeat; wire it last)
Ask for **cadence** and, critically, the **hard stop**. Then pick the primitive (details in `references/claude-code-primitives.md`):
- **`/loop <interval>`** — reruns on a cadence regardless of state. Use for regular checks.
- **`/goal <condition>`** — keeps going until a stated condition is *actually true*, verified by a separate small model, so the agent that wrote the code isn't the one grading it. Use when "done" has a checkable definition.
- **Scheduled tasks / Routines / `CronCreate`** — for restart-survival or laptop-off cloud runs.

Every automation needs a hard stop baked in — iteration count, token budget, or time limit — *"or the loop runs until someone notices the bill."*

### D5 — Maker/checker split (optional but high-value)
The model that wrote the code is "way too nice grading its own homework" (the evaluator-optimizer pattern). If the task warrants a second opinion beyond the objective gate, add a **verifier subagent** with different instructions — and ideally a different/stronger model — that never saw the maker's reasoning. Spend the extra tokens where a second opinion is worth paying for; the gate (D1) is still the objective backstop, the verifier is judgment on top.

---

## Stage E — Harden against the failure modes

Before emitting, walk the three named failure modes and bake the mitigation into the artifacts. Detail + measured examples in `references/failure-modes.md`.

- **The Ralph Wiggum loop (quiet failure).** The agent emits its "done" token early and the loop exits on a half-done job, spending forever. Root causes: no real verifier, soft completion conditions, no hard stop. Mitigation is Stage D done right — an *objective* gate + a hard stop + a `/goal` condition checked by a fresh model. Also watch: **goal drift** (constraints vanish by turn 47 of a long session → reread a standing spec), **self-preferential bias** (→ separate verifier), **agentic laziness** ("done enough" → objective stop condition).
- **Comprehension debt & cognitive surrender.** The faster the loop ships code you didn't write, the wider the gap between what the repo contains and what anyone understands — and the pull to stop forming an opinion. The mitigations are not technical: **read the diffs**, spot-check that the gate actually catches the failure you care about (gates rot), keep the loop off architecture/judgment work, and pair-design loops with a teammate. Put these in the design doc as standing practice, not a one-time step.
- **The security tax (an unattended loop is an unattended attack surface).** Bake in: security checks in the gate (SAST / dependency audit / secret scanning), **audit any skill before the loop auto-installs it** (prompt-injection lives in skill descriptions), disable verbose logging in production loops (credentials leak into logs no one watches), and **re-audit permissions every 30 days** (scope creep: a read-only loop quietly gains a write permission "just once").

---

## Stage F — Emit the Loop Design Doc and the rollout order

Assemble everything into one **Loop Design Doc** from `assets/loop-design.template.md`: the qualification verdict, the task, and the four concrete artifacts (gate command, state file, skill, automation command) plus the failure-mode mitigations. Then give them the **rollout order — and insist on it**, because skipping ahead is how loops fail in production:

> **Get one manual run reliable → turn it into the skill → wrap it in the loop → then schedule it.** Order matters.

Close with the metric that actually decides success: **cost per accepted change** — not tokens spent, not tasks attempted, not loops scheduled. If the accepted-change rate is below ~50%, they're doing the review work the loop was supposed to save, and the loop is losing — tighten the gate or narrow the task before scaling.

Leave them with the one-line thesis: **the leverage moved; build the loop, stay the engineer.** Reading the diffs is the whole job now.

---

## Reference files

- `references/roadmap.md` — the full 14 steps with the *why* for each, the who-wins/who-loses economics (§03), and the good/bad first-loop lists. Read when a stage needs depth.
- `references/claude-code-primitives.md` — the 5 building blocks (automations, worktrees, skills, connectors, sub-agents) mapped to concrete Claude Code tools. Read before proposing a specific command in Stage D.
- `references/failure-modes.md` — Ralph Wiggum, goal drift, self-preferential bias, agentic laziness, comprehension debt, cognitive surrender, the security tax — each with its mitigation. Read for Stage E.

## Asset templates

- `assets/STATE.template.md` — the state file (Stage D2).
- `assets/loop-skill.template.md` — a `SKILL.md` scaffold for the loop's own task (Stage D3).
- `assets/loop-design.template.md` — the final Loop Design Doc (Stage F).
