# The 5 building blocks → concrete Claude Code primitives

The roadmap is tool-agnostic (Codex and Claude Code both work). This maps each block to what the user can actually create **in Claude Code today**, so Stage D proposes real commands. Confirm what's available in the user's environment before recommending — not every install has cloud Routines or the scheduled-tasks MCP.

## Automations (the heartbeat)
Three primitives that compose into the same shape:
- **`/loop <interval> <prompt-or-slash-command>`** — session-scoped cadence. Reruns on an interval; omit the interval to let the model self-pace. Best for a check you want to run regardless of state while a session is alive. *This built-in is only the scheduler — this skill is what decides whether the loop should exist and what its four parts are.*
- **`/goal <condition>`** *(where available)* — keep going until a stated condition holds, checked by a separate small model so the maker isn't the grader. Use when "done" is objectively checkable ("all tests in test/auth pass and lint is clean").
- **Scheduled tasks / Routines / `CronCreate`** — for restart-survival (Desktop scheduled tasks) or laptop-off cloud runs (Routines). Use the `schedule` skill or `CronCreate` to register a cron-scheduled cloud agent. The `create_scheduled_task` MCP (if connected) is another route.
- **Hooks** — for lifecycle events (on Stop, on tool use, post-commit). Wire deterministic side-effects (run the gate, push a notification) the agent shouldn't have to remember.

Example shape from the source:
```
/loop 30m /goal All tests in test/auth pass and lint is clean.
  Scan src/auth for new failures, propose fixes in claude/auth-fixes,
  open draft PR when goal condition holds.
```
Always bake in a **hard stop** (iteration count / token budget / time limit).

## Worktrees (parallel without chaos)
- `git worktree add ../wt-<branch> <branch>` — a separate checkout on its own branch, same repo history.
- The `--worktree` flag opens a Claude Code session in its own checkout.
- `isolation: worktree` on a subagent gives each helper a fresh checkout that auto-cleans when unchanged.
Reminder: worktrees remove file collisions, but **review bandwidth is the real ceiling** on how many agents run at once.

## Skills (project knowledge, written once)
- A folder with `SKILL.md` (name + description frontmatter + instructions), optional `scripts/`, `references/`, `assets/`.
- Lives in `.claude/skills/<name>/` (or this repo). The loop reads it every run instead of re-deriving context.
- For the loop's own task, scaffold from `assets/loop-skill.template.md`: classification rules, fix patterns, a "Never do" list, and a rule to update the state file each run.

## Connectors (MCP)
- Claude Code speaks MCP; a connector written for one tool usually works in the other.
- Priority for loop work: **GitHub** (`gh` CLI or the GitHub MCP — branches, PRs, issues, webhook reactions), then **Linear/Jira**, **Slack**, **Sentry**.
- Connect via `claude mcp` or `/mcp` (interactive). In a headless/cron run, interactively-authenticated servers may be absent — prefer CLIs like `gh` for cloud loops.

## Sub-agents (maker ≠ checker)
- Define agents in `.claude/agents/*.md` (name, description, instructions, optional model + reasoning effort), or spawn ad-hoc with the `Agent` tool.
- The verifier should have **different instructions and ideally a different/stronger model**, and no exposure to the maker's reasoning.
- Typical split: one explores, one implements, one verifies against the spec. Sub-agents cost extra tokens (own model + tool work) — spend them where a second opinion pays.

## Putting it together — the MVL wiring
1. **Skill** in `.claude/skills/<task>/SKILL.md` holds the context.
2. **State** in `STATE.md` (or Linear) records done/next.
3. **Gate** is a shell command that exits non-zero on failure, run by the agent (and, ideally, in CI + a hook).
4. **Automation** (`/loop` + `/goal`, or a Routine/`CronCreate`) fires the cadence with a hard stop; optional **verifier subagent** for the maker/checker split.
