# Schema — `config/profile.md`

Specification for [`config/profile.md`](config/profile.md): the presenter's global profile that applies across every Talk in this working directory.

## Purpose

Captures per-presenter defaults that apply across every Talk in this working directory: the **subject** the working directory is dedicated to (one working directory per subject — see [`README.md`](${CLAUDE_PLUGIN_ROOT}/README.md) → *One working directory per subject*), who is delivering, how presentations are typically consumed, who the typical audience is, default total duration, presentation language, and whether the subject has an institution logo for rendered deck covers. Read once at session start and kept in context across all role work. Step 4 (Draft) reads these silently to populate `draft.md` frontmatter — it does **not** re-prompt for any field listed here.

## Loading semantics

| Reader | Read when | What for |
|---|---|---|
| Orchestrator | **Session start, eagerly** | Loaded into session context. If filled, treat sections as global defaults for presenter identity, audience, tone, duration, and language. If absent or any required section is missing/empty, Step 0.5 walks through the missing required sections (no skip). |
| All five roles (Librarian, Composer, Editor, Illustrator, Global-Librarian) | When performing any role | Profile is in session context — roles read it directly. If the profile is empty, each role falls back to defaults and notes the omission — never stops. |

The orchestrator writes the file whenever Step 0.5 collects a value for a previously-missing required section. Step 4 (Draft) also writes here as a **safety-net backstop** if it discovers a required section is still empty (i.e. Step 0.5 was bypassed for some reason) — but the canonical collection point is Step 0.5.

**One-time, session-load settings.** Three sections in particular — `How my presentations are consumed`, `Audience defaults`, and `Presentation language` — are **initialized once** during Step 0.5 and **never re-prompted per-Talk**. They are subject-level defaults read silently at session start; per-Talk calibration (e.g. a one-off audience tweak for a specific class) happens by editing `draft.md` frontmatter directly in Step 5 Review.

## Canonical sections (exactly seven)

| Section | Required? | Purpose |
|---|---|---|
| `Subject` | **Required** | The overarching subject this working directory is dedicated to — a course title, workshop series, or research area (e.g. "AI in Biomedicine — undergraduate course", "Intro to GANs for engineers", "Quantum computing seminar"). One working directory per subject. Copied into every Talk's `draft.md` frontmatter as the `presentation` field — every Talk in this working directory shares it. The Step-1 briefing captures only what's specific to *this class*; the subject is subject-level and never re-prompted per-Talk. |
| `Presenter` | **Required** | Identity record — name, role, organization (e.g. "Jane Doe, Lecturer, Example University"). **For shared-repo setups** (multiple presenters teaching the same subject — see `README.md` → *One shared repo per subject*), list every team presenter on its own line. The Editor copies the field into every Talk's `draft.md` frontmatter as the default `presenter`; whichever presenter is giving a given class overrides per-Talk in `draft.md` frontmatter at Step 4 or Step 5 Review. |
| `How my presentations are consumed` | **Required** | Live vs. recorded vs. async, default consumption mode. Drives slide density and speaker-note weight. Set once in Step 0.5 and never re-prompted per-Talk. |
| `Audience defaults` | **Required** | Typical audience profile across Talks (technical level, role, what they already know, what they care about). Copied into every Talk's `draft.md` frontmatter as the default `audience`. Per-Talk calibration ("alumnos de IA en Biomedicina") happens in Step 5 Review by editing `draft.md` directly — never re-prompted in Step 4. |
| `Default duration` | **Required** | Typical total talk length including Q&A — e.g. "60 min + 10 min Q&A", "45 min", "90 min lecture". Copied into every Talk's `draft.md` frontmatter as the default `duration`. Per-Talk override: edit the `draft.md` frontmatter directly in Step 5 Review. |
| `Presentation language` | **Required** | Language for slide text, panel labels, captions, SVG `<title>`/`<desc>`, prose in `draft.md`, and the conversation with the agent. Single value (e.g. "English", "Spanish", "Portuguese") or a default + exception ("Spanish by default, English for international audiences"). The Illustrator uses this for all in-SVG text; the Editor uses it for the conversation and `draft.md` prose. |
| `Institution logo` | *Optional* | Records the logo decision, not the image — the image is the file `config/logo.svg\|.png\|.jpg\|.jpeg`, reused on every rendered deck cover. Holds either the filename supplied (e.g. "`config/logo.png`") or a decline ("None — use the neutral placeholder"), so Step 0.5 asks once and never again. Renderers ignore this text and resolve the logo by file presence, so a stale value can't break a render. |

**Do not invent additional sections** (no "Who I am", "Tone and style", "Class structure", "Constraints" — these were intentionally removed). **Do not remove any of the seven canonical sections** — even if empty, keep the heading + an HTML-comment placeholder so the partial-fill detection works.

## Empty vs. filled state

Step 0.5's behavior depends on the state of `config/profile.md`. The driving rule: **required sections must be filled before the orchestrator advances past Step 0.5**. Optional sections may be skipped.

| State of `config/profile.md` | Orchestrator action (Step 0.5) |
|---|---|
| All seven sections filled (`Institution logo` counts as filled once it records a choice, decline included) | Load as global defaults. Acknowledge picked-up defaults. Skip to Step 1. |
| Partially filled — one or more sections missing, empty, or HTML-comment-only | Load the filled sections as global defaults. Walk through every missing section, prompting with 2–4 concrete candidates per section — **no skip option** for the six required ones. Write the result back. |
| Exists but every section is empty (only headings + HTML comments) | Walk through every section with the presenter. Never free-text except where the section semantics demand it (Subject and Presenter are free-text by definition). Write the result back. |
| Exists but missing one or more canonical section headings (e.g. legacy / hand-edited file that dropped `## Audience defaults`) | Treat the file as needing rebuild: re-bootstrap from the *Canonical empty form* below, **preserving any content under the canonical headings that did exist** (copy it into the rebuilt file under the same heading). Never silently drop presenter content. Then proceed as the "exists but every section is empty" case for whatever required sections came up empty after the rebuild. |
| Does not exist | Bootstrap from the *Canonical empty form* below → `config/profile.md`, then proceed as the "exists but every section is empty" case above. |

## Filling rules

- Per-section content is free-form prose (not a structured key/value).
- For required sections, the orchestrator must walk them in Step 0.5 by asking the presenter. Concrete candidates the orchestrator should offer:
  - `Subject`: free-text prompt (no candidates make sense — it's the unique overarching subject of this working directory).
  - `Presenter`: free-text prompt (no candidates make sense — it's a personal identity record).
  - `How my presentations are consumed`: 2–4 candidates such as "Live in-person talks", "Recorded video (async viewers)", "Hybrid — live with recording", "Async deck read-through (no narration)".
  - `Audience defaults`: 2–4 candidates such as "Technical peers / engineers", "Mixed technical + business", "University students (undergraduate)", "Domain practitioners (non-engineering)".
  - `Default duration`: 2–4 candidates such as "30 min", "45 min", "60 min + Q&A", "90 min lecture".
  - `Presentation language`: 2–3 candidates such as "Spanish", "English", "Portuguese".
  - `Institution logo`: asked last, and skippable. If `config/logo.*` already exists, record its filename without asking. Otherwise offer to take a path (copy it to `config/logo.<ext>`), wait for a drop-in, or skip. On skip write "None — use the neutral placeholder" — an empty section means *not yet asked* and re-prompts next session.
- The six sections above `Institution logo` are required — every one must be filled before the orchestrator advances past Step 0.5.

## Step 4 (Draft) contract

Step 4 reads `Subject`, `Presenter`, `Audience defaults`, `Default duration`, and `Presentation language` **silently** from this file and uses them to populate `draft.md` frontmatter (`presentation` ← `Subject`; `presenter` ← `Presenter`; `audience` ← `Audience defaults`; `duration` ← `Default duration`) plus the language of all prose the editor writes. It does not re-prompt for any of them. If a required section is unexpectedly empty when Step 4 begins (Step 0.5 bypassed, file edited out-of-band, etc.), Step 4 stops, redirects to Step 0.5 to collect the missing field, then resumes. No inline backstop prompts.

The only frontmatter field Step 4 actively prompts for is `date` (always per-Talk, no profile default). The pass-through keys (`research:`, `description:`) are populated by the editor from the schema's canonical empty form.

## Missing-profile fallback (shared rule)

This rule applies when performing any of the five roles (Librarian, Composer, Editor, Illustrator, Global-Librarian). It exists once, here, to keep the role specs consistent.

**When `config/profile.md` is genuinely empty or missing**, each role:

1. Proceeds without stopping — a missing profile is never a fatal error.
2. Derives `presentation`, `presenter`, `audience`, `duration` from `draft.md` frontmatter where present. If absent, falls back to neutral defaults and surfaces the gap in the final report.
3. Derives `Presentation language` from the dominant language of `draft.md` prose. If `draft.md` itself is empty (early Mode A pre-bootstrap), falls back to English and surfaces the gap.
4. **Notes the omission in the final report** so the orchestrator can prompt the presenter to fill the profile.

**When a specific profile section is missing, empty, or contains only an HTML-comment placeholder**, the same fallback applies for that section alone. Roles do not refuse to run; they degrade gracefully and report.

## Canonical empty form

Bootstrap `config/profile.md` from this form on first creation. The one-line schema pointer at the top stays; the section headings and HTML-comment placeholders below stay until the presenter fills them in.

```markdown
# Presenter Profile

> Schema, loading semantics, and filling rules live in [`${CLAUDE_PLUGIN_ROOT}/schemas/profile.md`](${CLAUDE_PLUGIN_ROOT}/schemas/profile.md).

---

## Subject

<!-- Required. The overarching subject this working directory is dedicated to — a course title, workshop series, or research area (e.g. "AI in Biomedicine — undergraduate course", "Intro to GANs for engineers"). One working directory per subject. Copied into every Talk's draft.md frontmatter as the `presentation` field. The Step-1 briefing captures only what's specific to *this class*; the subject is subject-level and never re-prompted per-Talk. -->

## Presenter

<!-- Required. One line — name, role, organization (e.g. "Jane Doe, Lecturer, Example University"). Copied into every Talk's draft.md frontmatter as the default `presenter`. Per-Talk override: edit draft.md frontmatter directly in Step 5 Review. -->

## How my presentations are consumed

<!-- Required. Live talks? Recorded? Async read-through of the deck? Classroom lecture? Conference keynote? Internal status update? Mix — and which is the most common default? Set once in Step 0.5 and never re-prompted per-Talk. Drives slide density and speaker-note weight across every Talk in this working directory. -->

## Audience defaults

<!-- Required. Who is typically in the room (or watching async)? Technical level, role, what they already know, what they care about. The Editor uses this as the default `audience` for every Talk's frontmatter. Per-Talk calibration happens in Step 5 Review by editing draft.md directly — never re-prompted in Step 4. -->

## Default duration

<!-- Required. Typical total talk length including Q&A — e.g. "60 min + 10 min Q&A", "45 min", "90 min lecture". Copied into every Talk's draft.md frontmatter as the default `duration`. Per-Talk override: edit draft.md frontmatter directly in Step 5 Review. -->

## Presentation language

<!-- Required. The language used for slide text, panel labels, subtitles, captions, SVG <title>/<desc>, and the conversation with the agent. Single value (e.g. "English", "Spanish", "Portuguese") or a default + exception ("Spanish by default, English for international audiences"). The Illustrator uses this for all in-SVG text; the Editor uses it for the conversation and draft.md prose. -->

## Institution logo

<!-- Optional. Drop your institution logo at config/logo.svg|.png|.jpg|.jpeg — it appears on the cover of every rendered deck in this working directory. This section just records the choice so you're asked once: the filename supplied, or "None — use the neutral placeholder". -->
```
