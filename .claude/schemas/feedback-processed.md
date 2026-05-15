# Schema — `knowledge/feedback-processed.md`

Specification for [`knowledge/feedback-processed.md`](../../knowledge/feedback-processed.md): the archive of feedback-backlog entries that have been promoted to learnings.

## Purpose

Moves promoted entries out of [`knowledge/feedback-backlog.md`](../../knowledge/feedback-backlog.md) so the backlog stays lean and only holds patterns that haven't yet crossed the 3-occurrence promotion threshold. Preserves the full audit trail behind each `learnings.md` entry — the chain from a learning back to the originating feedback bullets is recoverable by scanning this file for the matching `promoted_to:` value.

## Loading semantics

**Lazy-loaded** — never in session context at start.

| Reader | Read when | What for |
|---|---|---|
| `editor` subagent | Step 7 (Learnings), Move dispatch | Read existing entries to avoid duplicate appends when moving promoted backlog rows here. **Sole writer.** Append-only — never edit prior entries. |

No other reader. The orchestrator never reads or writes this file directly.

## Entry format

Same per-entry shape as `feedback-backlog.md`, with two added fields linking to the resulting learning:

```
- talk: <talk-folder>
  date: YYYY-MM-DD
  location: <Thesis | Agenda | Section "<name>" | Slide "<title>">
  feedback: "<verbatim presenter wording>"
  resolution: <one-line summary of what changed in master.md>
  tags: [<tags>]
  promoted_to: <learning title in learnings.md>
  promoted_at: YYYY-MM-DD
```

## Audit-trail invariant

Every row in this file corresponds to a `learnings.md` entry referenced by `promoted_to:`. **Read-only audit trail** — do not edit by hand. The editor moves entries here from `feedback-backlog.md` when the orchestrator dispatches a Step 7 Move. The original verbatim wording, location, and tags are preserved so the evidence chain in `learnings.md` remains traceable.

## Canonical empty form

```markdown
# Feedback — processed

> Format spec and audit-trail invariant live in [`.claude/schemas/feedback-processed.md`](../.claude/schemas/feedback-processed.md).

## Entries

<!-- Editor appends entries below this line when the orchestrator dispatches a Step 7 Move. -->
```

