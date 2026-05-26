# Presenter Profile

> Schema, loading semantics, and filling rules live in [`${CLAUDE_PLUGIN_ROOT}/schemas/profile.md`](${CLAUDE_PLUGIN_ROOT}/schemas/profile.md).

---

## Subject

<!-- Required. The overarching subject this working directory is dedicated to — a course title, workshop series, or research area (e.g. "AI in Biomedicine — undergraduate course", "Intro to GANs for engineers"). One working directory per subject. Copied into every Talk's draft.md frontmatter as the `presentation` field. The Step-1 briefing captures only what's specific to *this class*; the subject is subject-level and never re-prompted per-Talk. -->

## Presenter

<!-- Required. One line — name, role, organization (e.g. "Paulo Veiga, Lecturer, Universidad Austral"). Copied into every Talk's draft.md frontmatter as the default `presenter`. Per-Talk override: edit draft.md frontmatter directly in Step 5 Review. -->

## How my presentations are consumed

<!-- Required. Live talks? Recorded? Async read-through of the deck? Classroom lecture? Conference keynote? Internal status update? Mix — and which is the most common default? Set once in Step 0.5 and never re-prompted per-Talk. Drives slide density and speaker-note weight across every Talk in this working directory. -->

## Audience defaults

<!-- Required. Who is typically in the room (or watching async)? Technical level, role, what they already know, what they care about. The Editor uses this as the default `audience` for every Talk's frontmatter. Per-Talk calibration happens in Step 5 Review by editing draft.md directly — never re-prompted in Step 4. -->

## Default duration

<!-- Required. Typical total talk length including Q&A — e.g. "60 min + 10 min Q&A", "45 min", "90 min lecture". Copied into every Talk's draft.md frontmatter as the default `duration`. Per-Talk override: edit draft.md frontmatter directly in Step 5 Review. -->

## Presentation language

<!-- Required. The language used for slide text, panel labels, subtitles, captions, SVG <title>/<desc>, and the conversation with the agent. Single value (e.g. "English", "Spanish", "Portuguese") or a default + exception ("Spanish by default, English for international audiences"). The Illustrator uses this for all in-SVG text; the Editor uses it for the conversation and draft.md prose. -->
