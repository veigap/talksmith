# Schema — `knowledge/profile.md`

Specification for [`knowledge/profile.md`](../../knowledge/profile.md): the presenter's global profile that applies across every Talk in this repository.

## Purpose

Captures per-presenter defaults that apply across every Talk: how presentations are typically consumed, who the typical audience is, and what language slides are delivered in. Read once at session start, then passed into every subagent dispatch as context.

## Loading semantics

| Reader | Read when | What for |
|---|---|---|
| Orchestrator | **Session start, eagerly** | Loaded into session context. If filled, treat sections as global defaults for audience, tone, agenda, and language. If absent or empty, Step 0.5 offers to fill it. |
| All four subagents (`librarian`, `composer`, `editor`, `illustrator`) | On every dispatch | The orchestrator passes the profile's content **in the dispatch prompt**. Subagents do **not** read this file from disk. If a dispatch prompt omits profile content entirely (orchestrator bug or empty profile), every subagent falls back to defaults and notes the omission in its final report — never stops. |

The orchestrator writes the file when it persists newly-collected fields — e.g. when the presenter resolves `Presentation language` in Step 4 Pre-mode for the first time, the answer is written back so future Talks inherit it.

## Canonical sections (exactly three)

| Section | Purpose |
|---|---|
| `How my presentations are consumed` | Live vs. recorded vs. async, default consumption mode. Drives slide density and speaker-note weight. |
| `Audience defaults` | Typical audience profile across Talks (technical level, role, what they already know). Used as default `audience` for every Talk's frontmatter. |
| `Presentation language` | Language for slide text, panel labels, captions, SVG `<title>`/`<desc>`, prose in `master.md`, and the conversation with the agent. Single value or default + exception. |

**Do not invent additional sections** (no "Who I am", "Tone and style", "Class structure", "Constraints"). **Do not remove any of the three canonical sections** — even if empty, keep the heading + an HTML-comment placeholder so the partial-fill detection works.

## Empty vs. filled state

| State of `knowledge/profile.md` | Orchestrator action (Step 0.5) |
|---|---|
| All sections filled | Load as global defaults. Acknowledge picked-up defaults. Skip to Step 1. |
| Partially filled (some sections have content, others are blank or HTML-comment-only) | Load filled sections as global defaults. `AskUserQuestion`: fill the missing sections now or skip. Skipping is allowed — missing fields are re-prompted just-in-time (e.g. `Presentation language` is re-prompted in Step 4 Pre-mode). |
| Exists but empty (only headings + HTML comments) | `AskUserQuestion`: fill now or skip. If fill: walk through every present section via `AskUserQuestion` with 2–4 concrete candidates per section. Never free-text. Write result back. |
| Does not exist | `AskUserQuestion`: create + fill, or skip. If create: bootstrap from the *Canonical empty form* below → `knowledge/profile.md`, then proceed as the empty case above. |

## Filling rules

- Per-section content is free-form prose (not a structured key/value).
- Leave a section blank (or its placeholder HTML comment intact) if it genuinely does not apply — Talksmith treats blank sections as "ask me each time".

## No `presenter` field by design

The profile is a *global preferences* file, not an *identity* record. The `presenter` frontmatter field in each Talk's `master.md` captures the per-Talk presenter identity (collected in Step 4 Pre-mode on the first session of a new Talk).

## Canonical empty form

Bootstrap `knowledge/profile.md` from this form on first creation. The one-line schema pointer at the top stays; the section headings and HTML-comment placeholders below stay until the presenter fills them in.

```markdown
# Presenter Profile

> Schema, loading semantics, and filling rules live in [`.claude/schemas/profile.md`](../.claude/schemas/profile.md).

---

## How my presentations are consumed

<!-- Live talks? Recorded? Async read-through of the deck? Classroom lecture? Conference keynote? Internal status update? Mix — and which is the most common default? -->

## Audience defaults

<!-- Who is typically in the room (or watching async)? Technical level, role, what they already know, what they care about. The Agent will use this as the default audience unless overridden per-presentation. -->

## Presentation language

<!-- The language used for slide text, panel labels, subtitles, captions, SVG <title>/<desc>, and the conversation with the agent. Single value (e.g. "English", "Spanish", "Portuguese") or a default + exception ("Spanish by default, English for international audiences"). The Illustrator uses this for all in-SVG text; the Editor uses it for the conversation and master.md prose. -->
```
