---
name: <loop-name>
description: <What the loop does + when it fires. E.g. "Classify CI failures by root
  cause (env, flake, real bug, dependency, infra), draft fixes for the easy ones,
  escalate the rest. Trigger whenever a workflow run fails or on the morning triage loop.">
---

# <loop-name> skill

<!--
This is the project knowledge the loop reads EVERY run so it doesn't re-derive
context from zero. Written once outside, read by every cycle → intent compounds.
Fill each section with the loop's actual task; delete what doesn't apply.
-->

## Classification / decision rules
<!-- How the loop decides what kind of work each item is, and what to do with it. -->
- <category>: <how to recognize it>  # <action: fix / retry / escalate / human>
- <category>: <how to recognize it>  # <action>

## Fix patterns
<!-- Where to look first for each recurring shape of work. -->
- <symptom> → <where to look / what to try first>

## Never do
<!-- Guardrails. The blast-radius rules that keep this a safe first loop. -->
- <e.g. Disable failing tests — always file as an escalation instead.>
- <e.g. Modify CI config without human approval.>
- <e.g. Touch src/payments/ or src/billing/.>

## Gate
The objective check that must pass before anything ships:
```
<literal command that exits non-zero on failure, e.g. npm test && npm run lint>
```

## State
Update `STATE.md` at the end of every run: items checked, classifications, PRs opened,
items escalated, and any lesson learned (write lessons in the file, not in chat).
