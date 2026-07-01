# Failure modes and their mitigations

The gap between a loop that compounds value and one that quietly burns money is entirely in how it fails. Walk these in Stage E and bake each mitigation into the artifacts — don't just warn.

## The Ralph Wiggum loop (quiet failure)
Named by Geoffrey Huntley. An agent meant to emit its completion token only when finished emits it **early**; the loop exits on a half-done job — or, worse, never converges and keeps spending. It happens when:
- **No real verifier** — just a second agent asked to "review," no objective signal. Two optimists agreeing.
- **Soft completion conditions** — "done" defined by the agent's judgment, not a test/build/type-check.
- **No hard stops** — the loop runs until something external kills it (rate limit, you noticing the bill).

**Mitigation:** the objective gate from the MVL — *something that can fail the work*: a test that passes/fails, a build that compiles or not, a linter returning zero/non-zero. **Not** a verifier that has an opinion. Add a hard stop (iteration/budget/time) and, where "done" is checkable, a `/goal` condition verified by a fresh model.

## Goal drift over long sessions
Each summarization step is lossy; "don't do X" constraints disappear around turn 47. **Mitigation:** a standing `VISION.md` / `AGENTS.md` the agent rereads each run. State tells the agent *where it is*; the spec tells it *where to go*.

## Self-preferential bias
The agent that wrote the code is too nice grading its own homework — it's always "A+." **Mitigation:** a separate verifier subagent with different instructions, ideally a different/stronger model, and no exposure to the maker's reasoning (evaluator-optimizer).

## Agentic laziness
The loop declares "done enough" at partial completion. **Mitigation:** `/goal` with an *objective* stop condition checked by a fresh model — not the agent's self-assessment.

## Comprehension debt
The faster the loop ships code you didn't write, the larger the distance between what the repo contains and what you understand. The bill that hurts isn't tokens — it's the day you must debug a system no one on the team has read. **Mitigation (not technical):** read the diffs; keep the loop on small, machine-checkable changes; block it from architecture.

## Cognitive surrender
The pull to stop forming an opinion and accept whatever the loop returns. Designing the loop is the *cure* when done with judgment and the *accelerant* when done to avoid thinking — same action, opposite result. **Mitigation:** spot-check the gate (verify it actually catches the failure you care about — gates rot); pair-design loops with a teammate to catch blind spots the loop would otherwise exploit forever.

## The security tax (an unattended loop is an unattended attack surface)
- **Unreviewed generated code merges** → put security checks in the gate: SAST, dependency audit, secret scanning.
- **Skills as injection vectors** → audit any skill's source before the loop auto-installs it; prompt injection hides in descriptions. (Of 17,022 audited skills, 520 leaked credentials.)
- **Credentials in logs** → disable verbose logging in production loops; sanitize what gets logged.
- **Permission scope creep** → a loop tested read-only gains "just one" write permission for convenience and never gets re-audited. Re-audit permissions every 30 days.
