---
name: brain-capture
description: >-
  Capture the CURRENT session's durable findings into the personal "brain"
  knowledge wiki at ~/projects/misc/brain, following that repo's AGENTS.md
  workflow (raw → wiki/sources → wiki/topics → reports, state files,
  ingest:/query:/lint: commits). Trigger on "brain에 정리해줘/등록/기록",
  "save this to brain", "brain 업데이트", "brain capture", or any
  end-of-session request to persist knowledge. Runs from ANY project, always
  targets brain by absolute path. Flow — propose what/where, get approval,
  then write and commit locally. Not for ordinary code edits, the lightweight
  ~/.claude file memory, or throwaway answers.
---

# Brain Capture

Turn the work of the current session into durable, interlinked knowledge in the
user's personal wiki — the **brain** repo — so it compounds instead of vanishing
into chat history.

You are almost always invoked from *another* project (an app build, a research
run, a strategy chat). Your job is to read what just happened here, decide what
deserves to live in brain, and file it there correctly. You never write to the
current project; everything goes into the brain repo by absolute path.

**Brain repo:** `~/projects/misc/brain` (expand `~` to the real home dir, e.g.
`/Users/kiwankim/projects/misc/brain`). If that path doesn't exist, stop and ask
the user where brain lives rather than guessing.

## Why defer to brain's own rules

Brain is a maintained system with its own operating notes that evolve over time.
Hardcoding its structure here would rot. So the first thing you do is **read
brain's current rules and state**, then follow them. This skill only adds the
session-capture layer on top.

## Step 1 — Orient yourself in brain

Read these from the brain repo before doing anything else:

- `AGENTS.md` — the authoritative ingest / query / lint workflow. Follow it.
- `wiki/index.md` — the catalog of existing pages, so you update instead of duplicate.
- `wiki/memory.md` — stable working context and current priorities.
- `wiki/action-tracker.md`, `wiki/decision-log.md` — open tasks and past decisions.
- `wiki/log.md` (tail) — recent entries, to match the log format exactly.

Get today's date from the brain repo: `git -C ~/projects/misc/brain log -1 --format=%cd`
is fine for context, but use the real current date (`date +%F`) for new entries.

If anything in the conversation references files the session *produced* (a report,
a dataset, a scraped corpus), treat those as candidate sources too — not just the
chat text.

## Step 2 — Extract only what's durable

Most of a session is scaffolding. Save the parts that a future you would want to
retrieve and that aren't already recoverable elsewhere. Good candidates:

- **Findings / discoveries** — a verified fact, an API quirk, a market signal, a
  number that took work to get.
- **Decisions** — a choice made and *why*, especially anything that changes
  priorities or kills/starts a direction.
- **Answers worth reusing** — a question you researched and resolved (a report).
- **New sources** — an article, repo, dataset, transcript that fed the thinking.
- **Changed context** — priorities, active projects, or open tasks that shifted.

Skip, unless the user asks otherwise:

- Things derivable from a repo, git history, or code you can just read later.
- Step-by-step mechanics of how a task was done (the outcome matters, not the keystrokes).
- Ephemeral chatter, half-baked ideas the user didn't commit to, secrets/credentials.

If, after this filter, there's genuinely nothing durable, say so plainly and
propose either a one-line log entry or no change at all. Not polluting brain is a
feature — empty is a valid result.

## Step 3 — Classify and map to brain's structure

For each durable item, decide what it is and where it lands. Follow AGENTS.md;
the usual mapping:

| Kind | Lands in | Log type |
|---|---|---|
| New source material (immutable) | `raw/<name>` + a note in `wiki/sources/` | `ingest` |
| A session's work summary | `wiki/sources/session-<topic>-<date>.md` | `ingest` |
| Synthesized, canonical knowledge | new/updated page in `wiki/topics/` | `ingest` |
| A reusable answer to a question | `reports/<slug>.md` | `query` |
| A durable decision + rationale | row in `wiki/decision-log.md` | (note in log) |
| New/changed open task | row in `wiki/action-tracker.md` | (note in log) |
| Shifted stable context/priorities | edit `wiki/memory.md` | (note in log) |

Always, in addition:

- **Prefer updating an existing page over creating a new one.** Search first
  (`wiki/index.md`, then grep brain for the entity/topic). Compounding > duplication.
- **Add `[[wikilinks]]`** to connect new content to existing topics/sources.
- **Add a line to `wiki/index.md`** whenever you create a new page.
- **Append one entry to `wiki/log.md`** — never edit past entries.
- **Preserve provenance** — note which session/project and date the knowledge came
  from, so a claim can be traced.

### Log entry format

Match the existing style in `wiki/log.md`:

```md
## [YYYY-MM-DD] ingest | <short title>

- 소스/source: <where it came from — session in <project>, an artifact, etc.>
- 추출/what: <what durable knowledge was captured and synthesized>
- 신규/갱신: <new pages created> / <existing pages updated>
- (skipped): <notable things scanned but intentionally not captured, if useful>
```

Use `query |` for reusable-answer captures and `lint |` for cleanup passes. A
capture that is purely a decision (a `decision-log.md` row, no new source or
report) still needs one log line — default it to `ingest |`, since you're
recording new durable knowledge. Mirror the user's language — these logs are mostly Korean; write the entry in the
language the session's content is in.

## Step 4 — Propose before writing

This is the default and the user expects it. Before touching any brain file,
present a compact plan:

1. **What you'll capture** — a short bullet list of the durable items.
2. **Where each goes** — the exact files to create or update, marked new vs update.
3. **A preview** — for new pages, a short outline or the first lines; for state
   files (memory / decision-log / action-tracker), the exact row/line you'll add;
   the log entry verbatim.
4. **What you're deliberately skipping** and why, so the user can pull something
   back in.

Then wait for approval. If the user adjusts scope, revise the plan. Don't write
until they're good with it.

## Step 5 — Write it

On approval, make the edits with absolute paths into the brain repo. Honor
AGENTS.md writing rules: short sections, explicit headings, factual over flowery,
mark uncertainty, don't silently reconcile conflicting claims (record the
conflict). Keep `wiki/memory.md` small — move history into topic/source pages
rather than letting memory grow.

Touch the smallest set of files that keeps the wiki coherent. Every changed line
should trace to something the user agreed to capture.

## Step 6 — Commit locally

Commit in the brain repo only (the current project's git is untouched):

```bash
git -C ~/projects/misc/brain add -A
git -C ~/projects/misc/brain commit -m "ingest: <short description>"
```

Use the prefix matching the dominant action: `ingest:`, `query:`, or `lint:`
(brain's convention). Do **not** push — the user pushes themselves. Report the
commit and a one-line summary of what changed.

## Quality bar

Before you call it done, sanity-check:

- Did I update existing pages instead of creating near-duplicates?
- Is every new page linked from `wiki/index.md` and cross-linked with `[[...]]`?
- Did I append (not edit) the log, with the right type and a traceable source?
- Did `memory.md` / `decision-log.md` / `action-tracker.md` get touched only if
  the stable context, a decision, or an open task actually changed?
- Did I avoid dumping raw chat — is what I wrote synthesized and retrievable?
- Did I commit in the brain repo with the right prefix and not push?
