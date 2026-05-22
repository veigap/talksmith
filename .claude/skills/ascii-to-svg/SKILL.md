---
name: talksmith:ascii-to-svg
description: Render **one** ASCII diagram block into **one** SVG file. Invoked by the `illustrator` role during Step 6 (Polish) — once per fenced ASCII block in `final.md`. The skill applies the standing visual rules in [`config/diagram-style.md`](../../../config/diagram-style.md) plus optional per-render directives from the caller. The caller passes the pre-extracted slide context (title, content, speaker notes, section goal, language) so the SVG can be labelled and themed semantically. No template catalog; no closed style spec. CLI-safe.
---

# talksmith:ascii-to-svg — Render one ASCII block to one SVG

This skill renders **a single** ASCII diagram to **a single** SVG file. It is invoked once per fenced ASCII block by the [`illustrator`](../../roles/illustrator.md) role during Step 6 (Polish). Its scope is intentionally narrow:

| | Caller (`illustrator` role) does | This skill does |
|---|---|---|
| 1 | Invoke [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `scan` once; the scan output enumerates every fenced ASCII block **and** carries each block's pre-extracted slide context (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, optional `presentation_language`) | — |
| 2 | Pick the output filename `<slide-id>-<n>-<short-description>.svg` (kebab-case slug — see [`.claude/roles/illustrator.md`](../../roles/illustrator.md) → *Output filename convention*) | — |
| 3 | Pass through the scan's `context` bundle + sidecar path + (optional) `style_directives` | — |
| 4 | — | **Render the SVG for that one block** |
| 5 | Aggregate results, report rendered/unchanged/failed counts | — |

The agent is the coordinator; this skill is the worker. One invocation = one SVG file. The caller never re-parses `final.md` — every context field comes from the scan bundle. This makes the dispatch trivially parallelizable across subagents.

## Caller contract

The agent must pass the following in the skill invocation prompt. **Two input modes** for the ASCII payload — exactly one must be provided:

- **Mode A — inline (legacy / one-off renders):** pass `ascii_block` as a verbatim string. Used when no `.ascii` sidecar exists yet.
- **Mode B — from file (Step 6 standard):** pass `ascii_file` = absolute path to a `.ascii` sidecar produced by [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `extract`. The skill reads the file and **splits it on the `<!-- ascii-note:` sentinel**: everything before the sentinel (minus the separating blank line) is the ASCII payload; the comment from sentinel through `-->` populates the `ascii_note` context input. This is the canonical input mode during a normal Step 6 pass — the sidecar already carries both the source and the illustrator's render-time intent.

| Input | Required? | Example |
|---|---|---|
| `ascii_block` | Mode A | the fenced block's payload, verbatim |
| `ascii_file` | Mode B | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.ascii` |
| `ascii_note` | optional (Mode A only) | the captured `<!-- ascii-note: ... -->` if available. In Mode B the skill parses it from the sidecar; in Mode A you can pass it explicitly. The `intent:` / `emphasize:` / `labels:` lines drive per-diagram emphasis. |
| `output_path` | yes | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.svg`. In Mode B, if omitted, the skill defaults to the sibling SVG path (same basename as `ascii_file`, `.svg` extension). |
| `slide_title` | yes | from the slide's H2 heading (prefix-stripped) |
| `slide_content_prose` | recommended | the `### Content` body — used for subtitles, panel headings, in-panel callouts. Pass an empty string for sparse-context slides; the skill falls back to minimal labelling. |
| `speaker_notes` | recommended | the `### Speaker notes` body — used for `<desc>` and pedagogical-intent cues. Pass an empty string when the field is empty. |
| `section_title` | recommended | from the H1 the slide lives under |
| `section_goal` | recommended | from the section's `**Goal of this section:**` line |
| `talk_thesis` | recommended | top of `final.md` |
| `presentation_language` | recommended | from `config/profile.md` — determines language of all text in the SVG |
| `style_directives` | optional | freeform string with per-render visual instructions from the presenter (e.g. *"use orange for the model panel"*, *"don't use arrows, use plain lines"*). Applied **on top of** the standing rules in `config/diagram-style.md`; if it conflicts with a standing rule, the directive wins for this render only — note the deviation in the report. |
| `repo_root` | yes | absolute path to the Talksmith repo root (the folder containing `CLAUDE.md`, `config/`, `talks/`). The skill resolves `config/diagram-style.md` relative to this — **not** relative to the current working directory. The illustrator role passes it from its own dispatch context. |

## Process

0. **Resolve input mode.** If `ascii_file` is provided, read it, split on the first line starting with `<!-- ascii-note:`. The ASCII payload is everything before that line (rstrip a trailing blank line); the `ascii_note` is everything from the sentinel through the line containing `-->` (inclusive). If no sentinel is present, the whole file is the ASCII payload and `ascii_note` is empty. If `ascii_block` was passed instead, use it directly and treat any caller-supplied `ascii_note` as authoritative.

1. **Detect diagram vs code.** If the resolved ASCII payload is a real programming language (Python, bash, JSON, YAML, etc.) or contains no diagram glyphs (`+-|`, `─│┌┐└┘├┤┬┴┼`, `→ ← ↑ ↓ ⇒ -->`, `=>`, `~~~`, `/\`, `<>v^`), stop and return `skipped: not a diagram`.

2. **Load standing visual rules.** Read `<repo_root>/config/diagram-style.md`. The bullets in that file are the standing rules every render must obey (e.g. "flat style only", "light mode only"). Treat them as hard constraints. If `repo_root` is missing from the invocation, stop and return `failed: repo_root input missing`. If `config/diagram-style.md` doesn't exist, render with sensible defaults (light background, flat 2D, plain typography) and note `deviations: no diagram-style.md`.

3. **Merge with per-render directives.** Apply `style_directives` (if any) on top of the standing rules. A per-render directive that contradicts a standing rule wins for this render only — note the deviation in the report. A directive that adds to the standing rules (e.g. a specific color for a panel) is taken verbatim.

4. **Generate text from context, not from the ASCII.** The ASCII gives layout. The labels come from:
   - SVG `<title>`: `slide_title`
   - SVG `<desc>`: the first sentence of `speaker_notes` (one line); fall back to a `slide_title`-derived sentence if `speaker_notes` is empty
   - Per-panel heading: pull from `slide_content_prose` — the words the audience will hear
   - Per-panel subhead: the secondary phrase from `slide_content_prose`
   - In-panel callouts (axis labels, peak markers, equation captions): drawn from `speaker_notes` when it flags something to emphasize
   - **All text in `presentation_language`** — never mix languages. If unclear, fall back to the dominant language of `slide_content_prose`.

5. **Render the SVG.** Use a `viewBox` proportional to the diagram's aspect ratio (commonly `0 0 680 H` for landscape diagrams). Include `<title>` and `<desc>` as the first two children of the root `<svg>` for accessibility. Choose colors and shapes that satisfy *every* standing rule + any non-conflicting per-render directive. When the diagram has semantic structure (input/output, before/after, baseline/improved), use distinct hues to make the structure visible; default palette is the presenter's choice or a tasteful neutral if no directive is provided.

6. **Write the SVG** to `output_path`. Create the parent directory if it doesn't exist (`mkdir -p`). Overwrite if the file already exists — idempotency is the caller's concern, not this skill's.

7. **Rasterize a critique-companion PNG.** Render the SVG to a PNG sibling at `<output_path parent>/.critique/<basename>.png` (create `.critique/` if missing). This PNG is **not** referenced from `final.md` and is **not** consumed by Step 8 — it exists solely so the illustrator role can perform visual analysis on rasterized pixels in step 5b of its loop (XML inspection of an SVG is not a substitute for visual critique).

   Use `qlmanage` (built into macOS, zero install):

   ```bash
   qlmanage -t -s 1600 -o <parent>/.critique/ <output_path>
   mv <parent>/.critique/<basename>.svg.png <parent>/.critique/<basename>.png
   ```

   `qlmanage` writes the thumbnail as `<input-filename>.png` (it appends `.png` rather than replacing `.svg`), so the `mv` normalizes the basename. If `qlmanage` exits non-zero or the resulting PNG is missing / 0-byte, still report the SVG as `rendered` but add `png_companion: failed` to the report — a missing PNG degrades critique fidelity but doesn't invalidate the render. Never delete the SVG because the PNG step failed.

8. **Return** a one-line report:
   - On success: `rendered: <output_path> · png_companion: <path|failed> · directives_applied: <count> · deviations: <none|description>`
   - On skip: `skipped: <reason>`
   - On failure: `failed: <reason>` — and do **not** write a broken SVG.

## You cannot ask questions

This skill cannot ask follow-ups. If the standing rules + slide context + `style_directives` together don't disambiguate a critical choice, return `failed: ambiguous · <what's unresolved>`. The illustrator role surfaces the ambiguity to the orchestrator, which asks the presenter and re-invokes this skill with the disambiguation baked in.

**Sparse-context is not ambiguous.** When `slide_content_prose` and/or `speaker_notes` are empty, render with whatever context is present (`slide_title`, `section_title`, `section_goal`, `talk_thesis`) and pick neutral colors derived from box order rather than slide-prose keywords. Add `deviations: sparse-context (no <field>)` to the success report. Do **not** return `failed: ambiguous` just because prose is empty — an empty SVG is worse than a sparsely-labelled one.

## What this skill is NOT

- **Not** a coordinator. It renders one block. The illustrator role walks `final.md` and invokes this skill per block.
- **Not** allowed to write outside `output_path`. No edits to `final.md`, no creating sibling files.
- **Not** a `.pptx` renderer. That's [`talksmith:md-to-pptx`](../md-to-pptx/SKILL.md).
- **Not** allowed to read network resources. Pure local file work.
- **Not** dependent on any template catalog. There is no closed style spec or per-shape template library — the standing rules in `config/diagram-style.md` plus per-render directives are the full styling input. Start simple; rules accumulate in `config/diagram-style.md` over time as patterns crystallize.

## Why a skill, not just the agent

The illustrator role does per-Talk coordination (which slides have ASCII, what's the per-slide context, what should the output filename be) and judgement (the slug, the alt, optionally collecting per-render directives from the presenter). The actual rendering of one block from one context bundle is repetitive enough to factor out — making it a skill keeps each agent invocation small, surfaces a stable per-block contract, and lets the agent focus on judgement over SVG bookkeeping.
