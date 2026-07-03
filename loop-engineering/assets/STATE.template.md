# Loop state · <loop-name>

<!--
The agent forgets; this file does not. It lives OUTSIDE the single conversation so
tomorrow's run RESUMES instead of restarting. Keep it diff-readable. The agent must
update it at the end of every run — that instruction belongs in the loop's SKILL.md.
-->

## Last run
<YYYY-MM-DD HH:MM UTC> · <one-line summary: e.g. 7 failures classified, 3 fixes drafted, 4 escalated>

## In progress
- <branch / task> — <status, e.g. tests passing locally, awaiting CI>

## Completed today
- <branch / task> → <outcome, e.g. merged (CI green)>

## Escalated to humans
- <path / issue> — <why it needs a human: root cause unclear, infra, judgment call>

## Lessons learned (write here, not in chat)
- <YYYY-MM-DD>: <durable fact the next run needs, e.g. "tests/e2e/checkout needs the Stripe webhook secret in env; skip if missing.">

## Stop conditions met since last review
- <goal condition> achieved on commit <sha> at <HH:MM UTC>
