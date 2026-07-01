# The 14-step roadmap — prompter → loop designer

Source: Lev Deviatkin's thread summarizing Addy Osmani's loop-engineering essay, Anthropic's engineering docs, and AlphaSignal's economics analysis. This is the deep reference; `SKILL.md` is the runnable wizard. Read the section you need when a stage wants depth.

## PART 1 · The Why & The Test

### 01. Loop engineering is replacing yourself as the prompter
The old mode: write prompt → share context → read result → write next prompt. You are the tool-holder the entire time. A loop is a small system that **finds the work, hands it to the agent, checks the result, records what happened, and decides the next move — on its own.** You design it once; it prompts from then on. Osmani's six parts: automation, worktrees, skills, connectors, sub-agents, state. Anthropic engineers report merging ~8× more code/day than 2024 — a number Anthropic itself calls "almost certainly an overstatement." The number is debated; the mechanism isn't: **leverage moved from typing prompts to designing the loop that prompts.**

### 02. The 4-condition test (run before building anything)
A loop earns its cost only if **all four** hold. Miss one → the loop costs more than it returns.
1. **The task repeats** (≥ weekly). Amortizes setup across runs. One-time job → a good prompt is faster and cheaper.
2. **Verification is automated.** A test/type-check/lint/build can fail the work with no human present. No gate → back in the chair reading every diff.
3. **Token budget can absorb the waste.** Loops re-read, retry, explore — burning tokens regardless of whether a run ships. Scales with budget; reckless when metered.
4. **The agent has a senior engineer's tools.** Logs, a repro environment, the ability to run its own code. Without them the loop iterates blind.

### 03. Who wins, who loses (economics are not universal)
Loops favor whoever can spend. "Obvious" to people with unmetered tokens; "reckless" for someone on a $20 plan running heavy verification into a surprise invoice.
- **Wins:** teams with repetitive, machine-checkable work *and* budget (CI triage, dep bumps, lint-and-fix, issue-to-PR on strong tests); codebases with strong existing suites ("a junior could do it from a checklist and the suite catches mistakes"); async-first teams already using multi-agent patterns.
- **Skip, today:** solo builders on consumer plans (the bill arrives before the gain); any code with no automated verification (the loop is the agent agreeing with itself on repeat); teams whose real bottleneck is **review capacity** not typing speed (a loop just lengthens the review queue).
- For one-off / exploratory / judgment-call "done," **a single well-aimed prompt still wins.** Honest version: loop engineering is real, and most developers don't need it yet.

### 04. The 30-second loop check (tactical, per-task)
Miss one box → keep it a manual prompt.
1. Happens at least weekly (else setup never amortizes).
2. A test/type-check/build/linter can reject bad output (else the agent grades its own homework).
3. The agent can run the code it changes (else iteration is blind).
4. The loop has a **hard stop** — budget, iteration count, or time limit (else it runs until someone notices the bill).
5. A **human reviews** before merge/deploy/dependency change (anything irreversible needs an approval gate).

**Good first loops:** CI failure triage (nightly), dependency-bump PRs (weekly), lint-and-fix passes (on PR open), flaky-test reproduction (loop until a theory survives), issue-to-PR drafts (on strong tests).
**Bad first loops — human in the chair:** architecture rewrites, auth/payments code, production deploys, vague product work, anything where "done" is a judgment call.

## PART 2 · The 5 Building Blocks

### 05. Automations — the heartbeat
What makes it a loop and not one run you did once. Fire on schedule/event/trigger; everything else hangs off them. `/loop` reruns on a cadence regardless of state; `/goal` keeps going until a written condition is actually true, with **a separate small model checking completion** so the maker isn't the grader. This is the maker-vs-checker split applied to the *stop condition itself.*

### 06. Worktrees — parallel without chaos
The moment two agents write the same file you have two engineers committing to the same lines without talking. A **git worktree** is a separate working directory on its own branch sharing repo history, so one agent's edits can't touch another's checkout. Worktrees remove the mechanical collision, but **your review bandwidth is the ceiling** on parallelism, not the tool.

### 07. Skills — write project knowledge once, read every run
A `SKILL.md` folder (instructions + metadata + optional scripts/refs/assets) stops you re-explaining project context every session. A loop without skills re-derives everything from zero each cycle; **with skills, intent compounds** — conventions, build steps, the "we don't do it like this because of that one incident," written once outside, read by every run.

### 08. Connectors (MCP) — the loop touches your real tools
A filesystem-only loop is a tiny loop. MCP connectors let the agent read the issue tracker, query a DB, hit a staging API, drop a Slack message. Fastest payback, in order: **GitHub** (repos/branches/PRs/issues/webhooks — biggest day-one win), **Linear/Jira** (update tickets, link PRs, auto-close on verification), **Slack** (post triage, ping on escalation, morning summaries), **Sentry/error tracker** (investigate live alerts, draft fixes for frequent ones). The difference between "here is the fix" and a loop that opens the PR, links the ticket, and pings the channel once CI is green.

### 09. Sub-agents — keep the maker away from the checker
The single most useful structural move: split the agent that *writes* from the one that *checks*. The model that wrote the code is "way too nice grading its own homework." A second agent with different instructions (and sometimes a different model) catches what the first talked itself into. This is the **evaluator-optimizer pattern** (Anthropic, Dec 2024) under a new name. Why it matters *inside* a loop: the loop runs while you're not watching, so a verifier you actually trust is the only reason you can walk away. Sub-agents cost more tokens — spend them where a second opinion is worth paying for.

## PART 3 · Build It Right or Don't Build It

### 10. The state file — the agent forgets, the file does not
The spine of every working loop, and it sounds too dumb to matter. A markdown file / Linear board / JSON that lives outside the single conversation and holds what's done and what's next. Agents have short memory by default; what they learn this session is gone tomorrow unless written down. **Osmani's rule: the agent forgets, the repo does not.** No state → restart every run; state → resume. Homes: **`STATE.md` in-repo** (version-controlled, diff-readable, solo/small-team) or **external system** (queryable, cross-repo, team-visible, production). For drift-prone long-runners, pair with a standing **VISION.md/AGENTS.md** reread each run: state says where it is, the spec says where to go.

### 11. The minimum viable loop — four parts, no swarm
Smallest loop that works before anything fancy: **one automation** (scheduled, fires on cadence, stops on a clear condition — `/loop`, pair with `/goal`), **one skill** (the project context otherwise re-derived every run), **one state file** (tomorrow resumes instead of restarting), **one gate** (the test/type-check/build that fails bad work automatically — *the part that decides whether the loop helps or just spends*). **Order:** get one manual run reliable → turn it into a skill → wrap in a loop → then schedule. The metric that matters is **cost per accepted change** — below ~50% acceptance you're doing the review work the loop was supposed to save.

### 12. The Ralph Wiggum loop — loops that fail quietly
(Geoffrey Huntley.) An agent meant to emit a completion token only when finished emits it early; the loop exits on a half-done job and keeps spending. Happens when: **no real verifier** (just a second agent asked to "review" — two optimists agreeing), **soft completion conditions** ("done" by the agent's judgment, not a test/build/type-check), **no hard stops** (runs until something external kills it). Fix = the gate from step 11: *something objective that can fail the work*, not a verifier with an opinion. Other measured failure modes: **goal drift** over long sessions (lossy summarization; "don't do X" vanishes by turn 47 → reread a standing spec), **self-preferential bias** (→ separate verifier subagent), **agentic laziness** ("done enough" → `/goal` with an objective stop checked by a fresh model).

### 13. Comprehension debt & cognitive surrender
Sharpens as the loop gets *better*, not worse. **Comprehension debt:** the faster the loop ships code you didn't write, the wider the gap between what the repo contains and what you understand — the bill that hurts is the day you must debug a system no one has read. **Cognitive surrender:** the pull to stop forming an opinion and accept whatever the loop returns. Designing the loop is the cure when done with judgment, the accelerant when done to avoid thinking — same action, opposite result. Mitigations are not technical: **read the diffs**; **spot-check the gate** (pick a few loop PRs, verify the test actually catches the failure you care about — gates rot); **block the loop from architecture work**; **pair-design loops with a teammate**.

### 14. The security tax — an unattended loop is an unattended attack surface
- **Generated code shipping unreviewed** → the gate must include security checks (SAST, dependency audit, secret scanning).
- **Skills as injection vectors** → a loop that auto-installs skills inherits every prompt injection in their descriptions; audit sources before installing (of 17,022 audited skills, 520 leaked credentials).
- **Credentials in logs** → verbose debug logging scatters secrets across unmonitored logs; disable in production, sanitize what's logged.
- **Permission scope creep** → a read-only loop gains "just one" write permission and never gets re-audited; re-audit every 30 days.

## The mistakes that turn loops into money pits
Building without the 4-condition test · no objective gate · one agent writing *and* verifying · no state file · vague stop conditions · no token-budget cap · heavy verification on a consumer plan · auto-installing community skills · loops on judgment-call work · **not reading the diffs.**
