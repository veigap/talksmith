---
name: talksmith:ascii-to-svg
description: Render **one** ASCII diagram block into **one** styled SVG file following `knowledge/image-styles/style.md`. Invoked by the `illustrator` agent during Step 6 (Polish) — once per fenced ASCII block in `master.md`. The skill is the per-block renderer; the illustrator agent is the per-Talk coordinator. The caller passes the pre-extracted slide context (title, content, speaker notes, section goal, language) so the SVG can be labelled and colored semantically. CLI-safe.
---

# talksmith:ascii-to-svg — Render one ASCII block to one SVG

This skill renders **a single** ASCII diagram to **a single** SVG file. It is invoked once per fenced ASCII block by the [`illustrator`](../../agents/illustrator.md) agent during Step 6 (Polish). Its scope is intentionally narrow:

| | Caller (`illustrator` agent) does | This skill does |
|---|---|---|
| 1 | Walk `master.md`, find fenced ASCII blocks | — |
| 2 | Per block, extract slide context (title, content prose, notes, section goal, language) | — |
| 3 | Decide the output filename `<slide-id>-<n>.svg` | — |
| 4 | — | **Render the SVG for that one block** |
| 5 | Aggregate results, report rendered/unchanged/failed counts | — |

The agent is the coordinator; this skill is the worker. One invocation = one SVG file.

## Caller contract

The agent must pass the following in the skill invocation prompt:

| Input | Required? | Example |
|---|---|---|
| `ascii_block` | yes | the fenced block's payload, verbatim |
| `output_path` | yes | absolute path, e.g. `talks/<Talk>/images/s1-2-1.svg` |
| `slide_title` | yes | from the slide's H2 heading (prefix-stripped) |
| `slide_content_prose` | yes | the `### Content` body — used for subtitles, in-panel callouts, axis labels |
| `speaker_notes` | yes | the `### Notes` body — used for `<desc>` and pedagogical-intent cues |
| `section_title` | recommended | from the H1 the slide lives under |
| `section_goal` | recommended | from the section's `**Goal of this section:**` line |
| `talk_thesis` | recommended | top of `master.md` |
| `presentation_language` | recommended | from `knowledge/profile.md` — determines language of all text in the SVG |
| `template_name` | recommended | bare name (no extension, no path) of the [`knowledge/image-styles/*.txt`](../../../knowledge/image-styles/) template the illustrator picked for this block — e.g. `pipeline-3-stage`. Pass `null` if no template fits (skill renders a custom shape against `style.md` only). |

The skill resolves both style files itself, hardcoded relative to repo root:

- `knowledge/image-styles/style.md` — always read.
- `knowledge/image-styles/<template_name>.txt` — read iff `template_name` is non-null.

This is deliberate: the locations are stable, the contract stays small, and there's no risk of the caller passing a broken path. The illustrator agent does the template **match** (one per block) by walking the `*.txt` catalog itself; the skill receives only the chosen name.

**Do not read the canonical `knowledge/image-styles/*.svg` files.** They are human reference only — they sit beside the `*.txt` templates as *examples* of finished output. The rendering contract is **style.md + matched `*.txt` template + slide context** alone. If something is unclear from those three inputs, it belongs in `style.md` (file an issue, do not reach for the SVGs). Reading the SVG corpus during a render bloats the skill's context, encourages cargo-culting one historical layout, and bypasses `style.md` as the single source of truth.

## Process

1. **Detect diagram vs code.** If `ascii_block` is a real programming language (Python, bash, JSON, YAML, etc.) or contains no diagram glyphs (`+-|`, `─│┌┐└┘├┤┬┴┼`, `→ ← ↑ ↓ ⇒ -->`, `=>`, `~~~`, `/\`, `<>v^`), stop and return `skipped: not a diagram`.

2. **Load style files.** Read `knowledge/image-styles/style.md` (always). If `template_name` is non-null, also read `knowledge/image-styles/<template_name>.txt`. Both paths are hardcoded relative to repo root. Do **not** walk the full `image-styles/` catalog — the illustrator owns the match decision. If `template_name` is `null`, fall back to a custom shape — `style.md`'s palette, typography, idioms, and layout rules still apply.

3. **Pick semantic colors** from the slide context, **not** from box order. Use the *Semantic color → panel class* table in `style.md`:
   - `slide_content_prose` words like "before / dirty / noisy / raw" → `.c-coral` or `.c-gray`
   - "intermediate / improved / processing" → `.c-amber` or `.c-purple`
   - "clean / final / synthetic / generated" → `.c-teal`
   - "input / reference / ground-truth / neutral" → `.c-blue`
   - "model / system / black-box" → `.c-purple` (full panel) or `.c-gray` (inset)
   - When the slide is histological/biological tissue and `style.md`'s histology accent applies, use the pink ramp and document the deviation in `<desc>`.

4. **Generate text from context, not from the ASCII.** The ASCII gives layout. The labels come from:
   - SVG `<title>`: `slide_title`
   - SVG `<desc>`: the first sentence of `speaker_notes` (one line)
   - Per-panel heading: pull from `slide_content_prose` — the words the audience will hear
   - Per-panel subhead: the secondary phrase from `slide_content_prose`
   - In-panel callouts (axis labels, peak markers, equation captions): drawn from `speaker_notes` when it flags something to emphasize
   - **All text in `presentation_language`** — never mix languages. If unclear, fall back to the dominant language of `slide_content_prose`.

5. **Render the SVG** following `style.md` end to end:
   - Hard constraints: `viewBox="0 0 680 H"`, `role="img"`, `<title>` + `<desc>`, shared `<marker id="arrow">` def.
   - Panel layout from `style.md`'s *Panel layout grid* table (2-up = 290+290 @ x=40,350; 3-up = 200×3; pipeline = 160×3 with arrows; etc.).
   - Heading-position rule by layout type (above for stacked, inside for narrow pipeline boxes).
   - Color tonal scale: pastel rect fill, mid rect stroke, **darkest** for primary polyline stroke, light for centerlines.
   - Dash patterns: `2 2` for drop-lines, `3 3` for reference/orbit/zoom-connector.
   - Bottom caption (when applicable): `x="340"`, `y=viewBox.H - 22`, `fill="#888780"`.
   - Idioms section verbatim for the elements you use.

6. **Write the SVG** to `output_path`. Create the parent directory if it doesn't exist (`mkdir -p`). Overwrite if the file already exists — idempotency is the caller's concern, not this skill's.

7. **Return** a one-line report:
   - On success: `rendered: <output_path> · template: <category-or-custom> · colors: <c1,c2,...> · deviations: <none|description>`
   - On skip: `skipped: <reason>`
   - On failure: `failed: <reason>` — and do **not** write a broken SVG.

## You cannot ask questions

This skill has no `AskUserQuestion`. If `style_md` + `slide_content_prose` + `speaker_notes` together don't disambiguate a critical choice (language, semantic color when slide context is silent, template when none fits), return `failed: ambiguous · <what's unresolved>`. The illustrator agent will surface the ambiguity to the orchestrator, which will ask the presenter and re-invoke this skill with the disambiguation baked in.

## What this skill is NOT

- **Not** a coordinator. It renders one block. The illustrator agent walks `master.md` and invokes this skill per block.
- **Not** allowed to write outside `output_path`. No edits to `master.md`, no creating sibling files.
- **Not** a `.pptx` renderer. That's [`talksmith:md-to-pptx`](../md-to-pptx/SKILL.md).
- **Not** allowed to read network resources. Pure local file work.

## Why a skill, not just the agent

The illustrator agent does context extraction and per-Talk coordination (which slides have ASCII, what's the per-slide context, what should the output filename be). The actual rendering of one block from one structured-context bundle is repetitive and well-defined enough to factor out — making it a skill keeps each agent invocation small (one block of work per skill call), surfaces a stable per-block contract for testing, and lets the agent focus on judgement over context rather than mixing context-judgement with SVG-syntax bookkeeping.
