# Learnings

Durable, cross-presentation rules promoted from the [`feedback-backlog.md`](feedback-backlog.md) when a pattern repeats 3+ times. **Lazy-loaded**: read from disk only at the step that needs it. The orchestrator reads it on entry to Step 7 (Learnings) to append new promotions and avoid duplicates; the `scribe` reads it on dispatch in Step 4 Modes B (Agent Draft) and C (Presenter Outline) to apply each entry as a soft rule while drafting. No other step or agent loads it.

> **How entries get here.** At presentation completion, the orchestrator scans the feedback backlog for recurring patterns. When a pattern hits 3+ occurrences across Talks, it asks the presenter via `AskUserQuestion` whether to promote it. Promoted entries land below.

## Format

```
### <Short rule title>

**Rule:** <one-sentence directive — what the agent should now do by default>

**Why:** <what the recurring feedback was, in the presenter's own words where possible>

**Where it applies:** <surface — Thesis, Agenda, Slide content, Speaker notes, Sources, etc.>

**Evidence:** <talk-folder>:<date>, <talk-folder>:<date>, <talk-folder>:<date> (links to backlog entries)

**Added:** YYYY-MM-DD
```

## Entries

<!-- Promoted learnings live below this line. -->
