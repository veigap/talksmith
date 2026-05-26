# Schema — `config/learnings.md`

Specification for [`config/learnings.md`](config/learnings.md): the durable, cross-presentation rule store. Entries are promoted from [`config/feedback-backlog.md`](config/feedback-backlog.md) when a pattern repeats 3+ times across Talks.

## Purpose

Holds the rules that future Talks should inherit as soft defaults — earned through repeated correction. Treat entries as **stronger defaults than `${CLAUDE_PLUGIN_ROOT}/config/principles.md`**: principles are seeded; learnings are evidence-backed by recurring presenter feedback.

## Loading semantics

**Lazy-loaded** — never in session context at start.

| Reader | Read when | What for |
|---|---|---|
| Orchestrator | Entering Step 7 (Learnings) | Scan existing entries to (a) avoid proposing duplicate promotions and (b) look up the entry id assigned to a freshly promoted pattern (used in the Move pass). **Read-only** — never writes the file directly. |
| Composer role | Every drafting milestone in Step 4 (after thesis, after agenda, after each section in Mode A; after the full draft in Modes B/C) | Apply each entry as a soft rule when critiquing the draft. Cite by entry title in punch-list items: `(learnings.md: <entry-title>)`. |
| Editor role | Step 7 only — when performing a Promote pass for a pattern to record | **Sole writer** of this file. Append-only — never edit or delete prior entries. |

No other agent and no other orchestrator step loads this file.

## Entry format

```
### <Short rule title>

**Rule:** <one-sentence directive — what the agent should now do by default>

**Why:** <what the recurring feedback was, in the presenter's own words where possible>

**Where it applies:** <surface — Thesis, Agenda, Slide content, Speaker notes, Sources, etc.>

**Evidence:** <talk-folder>:<date>, <talk-folder>:<date>, <talk-folder>:<date> (links to backlog entries that triggered the promotion)

**Added:** YYYY-MM-DD
```

The Editor role generates a stable `entry id` per promotion (incrementing integer or next available slug — match the file's existing convention) and returns it in the Promote-pass final report. The orchestrator uses that id in the subsequent Move pass so each moved row in `feedback-processed.md` can stamp `promoted_to: <entry id>`.

## How entries get here

1. Orchestrator scans `feedback-backlog.md` at presentation completion.
2. Groups entries by tag and resolution shape.
3. For any pattern recurring 3+ times across Talks, asks the presenter whether to promote (options: *Promote* / *Skip* / *Promote with edits*).
4. For each approved pattern, performs the Editor role twice:
   - **Promote** — append a new entry here.
   - **Move** — relocate the contributing backlog rows from `feedback-backlog.md` to [`config/feedback-processed.md`](config/feedback-processed.md), stamping each with `promoted_to:` and `promoted_at:`.

The orchestrator never writes this file directly. See *Step 7* in [CLAUDE.md](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) for the full protocol.

## Canonical empty form

```markdown
# Learnings

> Format spec, loading semantics, and promotion rules live in [`${CLAUDE_PLUGIN_ROOT}/schemas/learnings.md`](${CLAUDE_PLUGIN_ROOT}/schemas/learnings.md).

## Entries

<!-- Editor role appends promoted learnings below this line during the Step 7 Promote pass. -->
```

