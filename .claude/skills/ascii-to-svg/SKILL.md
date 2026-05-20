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
| 3 | Decide the output filename `<slide-id>-<n>-<short-description>.svg` (illustrator computes the kebab-case description slug — see `.claude/roles/illustrator.md` → *Output filename convention*) | — |
| 4 | — | **Render the SVG for that one block** |
| 5 | Aggregate results, report rendered/unchanged/failed counts | — |

The agent is the coordinator; this skill is the worker. One invocation = one SVG file.

## Caller contract

The agent must pass the following in the skill invocation prompt. **Two input modes** for the ASCII payload — exactly one must be provided:

- **Mode A — inline (legacy / one-off renders):** pass `ascii_block` as a verbatim string. Used when no `.ascii` sidecar exists yet.
- **Mode B — from file (Step 6 standard):** pass `ascii_file` = absolute path to a `.ascii` sidecar produced by [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `extract`. The skill reads the file and **splits it on the `<!-- ascii-note:` sentinel**: everything before the sentinel (minus the separating blank line) is the ASCII payload; the comment from sentinel through `-->` populates the `ascii_note` context input. This is the canonical input mode during a normal Step 6 pass, because the sidecar already carries both the source and the illustrator's render-time intent.

| Input | Required? | Example |
|---|---|---|
| `ascii_block` | Mode A | the fenced block's payload, verbatim |
| `ascii_file` | Mode B | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.ascii` |
| `ascii_note` | optional (Mode A only) | the captured `<!-- ascii-note: ... -->` if available. In Mode B the skill parses it from the sidecar; in Mode A you can pass it explicitly when you've extracted it elsewhere. The `intent:` / `emphasize:` / `labels:` / `template-hint:` lines are used to drive labelling and color emphasis. |
| `output_path` | yes | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.svg`. In Mode B, if omitted, the skill defaults to the sibling SVG path (same basename as `ascii_file`, `.svg` extension). |
| `slide_title` | yes | from the slide's H2 heading (prefix-stripped) |
| `slide_content_prose` | recommended | the `### Content` body — used for subtitles, in-panel callouts, axis labels. Pass an empty string when the slide field is empty (early-draft slides during Mode A); the skill will fall back to a minimal labelling and note `deviations: sparse-context` in its report. |
| `speaker_notes` | recommended | the `### Speaker notes` body — used for `<desc>` and pedagogical-intent cues. Pass an empty string when the field is empty; the skill omits the `<desc>` emphasis cues and uses a default `<desc>` derived from `slide_title`. |
| `section_title` | recommended | from the H1 the slide lives under |
| `section_goal` | recommended | from the section's `**Goal of this section:**` line |
| `talk_thesis` | recommended | top of `master.md` |
| `presentation_language` | recommended | from `knowledge/profile.md` — determines language of all text in the SVG |
| `template_name` | recommended | bare name (no extension, no path) of the [`knowledge/image-styles/*.txt`](../../../knowledge/image-styles/) template the illustrator picked for this block — e.g. `pipeline-3-stage`. Pass `null` if no template fits (skill renders a custom shape against `style.md` only). |
| `repo_root` | yes | absolute path to the Talksmith repo root (the folder containing `CLAUDE.md`, `knowledge/`, `talks/`). The skill resolves `style.md` and template files relative to this — **not** relative to the current working directory. The illustrator agent passes it from its own dispatch context. |

The skill resolves both style files relative to `repo_root`:

- `<repo_root>/knowledge/image-styles/style.md` — always read.
- `<repo_root>/knowledge/image-styles/<template_name>.txt` — read iff `template_name` is non-null.

This avoids any reliance on the session's current working directory (which is undefined when the skill is invoked from a subdir, a Cowork workspace, or any other harness). The illustrator agent does the template **match** (one per block) by walking the `*.txt` catalog itself; the skill receives only the chosen name.

**Do not read the canonical `knowledge/image-styles/*.svg` files.** They are human reference only — they sit beside the `*.txt` templates as *examples* of finished output. The rendering contract is **style.md + matched `*.txt` template + slide context** alone. If something is unclear from those three inputs, it belongs in `style.md` (file an issue, do not reach for the SVGs). Reading the SVG corpus during a render bloats the skill's context, encourages cargo-culting one historical layout, and bypasses `style.md` as the single source of truth.

## Process

0. **Resolve input mode.** If `ascii_file` is provided, read it, split on the first line starting with `<!-- ascii-note:`. The ASCII payload is everything before that line (rstrip a trailing blank line); the `ascii_note` is everything from the sentinel through the line containing `-->` (inclusive). If no sentinel is present, the whole file is the ASCII payload and `ascii_note` is empty. If `ascii_block` was passed instead, use it directly and treat any caller-supplied `ascii_note` as authoritative.

1. **Detect diagram vs code.** If the resolved ASCII payload is a real programming language (Python, bash, JSON, YAML, etc.) or contains no diagram glyphs (`+-|`, `─│┌┐└┘├┤┬┴┼`, `→ ← ↑ ↓ ⇒ -->`, `=>`, `~~~`, `/\`, `<>v^`), stop and return `skipped: not a diagram`.

2. **Load style files.** Read `<repo_root>/knowledge/image-styles/style.md` (always). If `template_name` is non-null, also read `<repo_root>/knowledge/image-styles/<template_name>.txt`. Resolve both via the `repo_root` input — never via the current working directory. Do **not** walk the full `image-styles/` catalog — the illustrator owns the match decision. If `template_name` is `null`, fall back to a custom shape — `style.md`'s palette, typography, idioms, and layout rules still apply. If `repo_root` is missing from the invocation, stop and return `failed: repo_root input missing`.

3. **Pick semantic colors** from the slide context, **not** from box order. Apply the *Semantic color → panel class* table in `style.md` to keywords found in `slide_content_prose`. `style.md` is the authority — do not restate its mappings here. If the slide is histological/biological tissue and `style.md`'s histology accent applies, use the pink ramp and document the deviation in `<desc>`.

4. **Generate text from context, not from the ASCII.** The ASCII gives layout. The labels come from:
   - SVG `<title>`: `slide_title`
   - SVG `<desc>`: the first sentence of `speaker_notes` (one line)
   - Per-panel heading: pull from `slide_content_prose` — the words the audience will hear
   - Per-panel subhead: the secondary phrase from `slide_content_prose`
   - In-panel callouts (axis labels, peak markers, equation captions): drawn from `speaker_notes` when it flags something to emphasize
   - **All text in `presentation_language`** — never mix languages. If unclear, fall back to the dominant language of `slide_content_prose`.

5. **Render the SVG** following `style.md` end to end. `style.md` is the single source of truth for hard constraints (viewBox, `role`, `<title>`/`<desc>`, shared `<marker>`), the *Panel layout grid*, heading-position rules, the tonal scale, dash patterns, bottom-caption placement, and idioms. If a matched template (`<template_name>.txt`) is loaded, it overrides layout where applicable but does not loosen `style.md`'s constraints. Do not restate any of these here — read them from `style.md` per render.

6. **Write the SVG** to `output_path`. Create the parent directory if it doesn't exist (`mkdir -p`). Overwrite if the file already exists — idempotency is the caller's concern, not this skill's.

7. **Return** a one-line report:
   - On success: `rendered: <output_path> · template: <category-or-custom> · colors: <c1,c2,...> · deviations: <none|description>`
   - On skip: `skipped: <reason>`
   - On failure: `failed: <reason>` — and do **not** write a broken SVG.

## You cannot ask questions

This skill cannot ask questions. If `style.md` + `slide_content_prose` + `speaker_notes` together don't disambiguate a critical choice (language, semantic color when slide context is silent, template when none fits), return `failed: ambiguous · <what's unresolved>`. The illustrator agent will surface the ambiguity to the orchestrator, which will ask the presenter and re-invoke this skill with the disambiguation baked in.

**Sparse-context is not ambiguous.** When `slide_content_prose` and/or `speaker_notes` are empty (early-draft Mode A slides where the diagram exists before the prose), render with whatever context is present (`slide_title`, `section_title`, `section_goal`, `talk_thesis`) and pick neutral semantic colors derived from box order rather than slide-prose keywords. Add `deviations: sparse-context (no <field>)` to the success report. Do **not** return `failed: ambiguous` just because prose is empty — the illustrator coordinator and presenter both expect the ASCII to render even early; an empty SVG is worse than a sparsely-labelled one.

## What this skill is NOT

- **Not** a coordinator. It renders one block. The illustrator agent walks `master.md` and invokes this skill per block.
- **Not** allowed to write outside `output_path`. No edits to `master.md`, no creating sibling files.
- **Not** a `.pptx` renderer. That's [`talksmith:md-to-pptx`](../md-to-pptx/SKILL.md).
- **Not** allowed to read network resources. Pure local file work.
- **Not** willing to guess paths. If `repo_root` is missing from the invocation, the skill fails fast (`failed: repo_root input missing`) rather than defaulting to the current working directory — CWD is undefined when the skill runs from a subdir, a Cowork workspace, or any other harness.

## Why a skill, not just the agent

The illustrator agent does context extraction and per-Talk coordination (which slides have ASCII, what's the per-slide context, what should the output filename be). The actual rendering of one block from one structured-context bundle is repetitive and well-defined enough to factor out — making it a skill keeps each agent invocation small (one block of work per skill call), surfaces a stable per-block contract for testing, and lets the agent focus on judgement over context rather than mixing context-judgement with SVG-syntax bookkeeping.
