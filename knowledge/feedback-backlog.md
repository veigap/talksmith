# Feedback backlog

Cross-presentation log of every `Presenter feedback` bullet captured during Step 5 (Review). The Editor appends to this file whenever a feedback bullet is closed in a Talk's `master.md`. The orchestrator scans this file at presentation completion to detect repeated patterns; for each pattern the presenter approves, the orchestrator dispatches the Editor to append a new entry to [`learnings.md`](learnings.md) and move the contributing rows from here into [`feedback-processed.md`](feedback-processed.md). The orchestrator never writes either file directly.

> **Do not edit by hand during a Review round.** Add feedback to the Talk's `master.md` `Presenter feedback` fields; the Editor mirrors closed bullets here.

## Format

One entry per closed feedback bullet, newest at the bottom:

```
- talk: <talk-folder>
  date: YYYY-MM-DD
  location: <Thesis | Agenda | Section "<name>" | Slide "<title>">
  feedback: "<verbatim presenter wording>"
  resolution: <one-line summary of what changed in master.md>
  tags: [<short kebab-case tags — see Tagging below>]
```

## Tagging

Tags are how patterns surface. Reuse existing tags from prior entries before inventing new ones. Common axes:

- **Surface**: `thesis`, `agenda`, `section-goal`, `slide-content`, `speaker-notes`, `sources`, `cut-material`.
- **Concern**: `too-dense`, `too-academic`, `too-vague`, `off-thesis`, `wrong-audience`, `missing-evidence`, `bad-order`, `redundant`, `tone`, `visual`, `length`.
- **Action**: `rewrite`, `reorder`, `cut`, `merge`, `split`, `add-source`, `add-visual`.

## Pattern detection

At presentation completion (when the presenter declares `master.md` final, before Step 8), the orchestrator:

1. Scans the entries added during this Talk and combines them with prior backlog history.
2. Groups by tag and by recurring resolution shape.
3. For any pattern that has appeared **3+ times across all Talks**, prompts the presenter via `AskUserQuestion` whether to promote it to [`learnings.md`](learnings.md) as a durable rule.
4. For each promoted pattern, **dispatches the Editor** to (a) append a new entry to [`learnings.md`](learnings.md) and (b) move the contributing entries from this file to [`feedback-processed.md`](feedback-processed.md) — adding `promoted_to` and `promoted_at` fields — so this backlog stays lean and only holds patterns that haven't yet crossed the promotion threshold. The Editor is the sole writer of both files; the orchestrator never edits them by hand.

## Entries

<!-- Editor appends entries below this line. -->