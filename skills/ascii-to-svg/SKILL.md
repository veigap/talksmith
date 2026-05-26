---
name: talksmith:ascii-to-svg
description: Render **one** ASCII diagram block into **one** SVG file. Invoked by the `illustrator` role during Step 6 (Polish) — once per fenced ASCII block in `final.md`. The skill applies the standing visual rules in [`${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md`](${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md) plus optional per-render directives from the caller. The caller passes the pre-extracted slide context (title, content, speaker notes, section goal, language) so the SVG can be labelled and themed semantically. No template catalog; no closed style spec. CLI-safe.
---

# talksmith:ascii-to-svg — Render one ASCII block to one SVG

This skill renders **a single** ASCII diagram to **a single** SVG file. It is invoked once per fenced ASCII block by the [`illustrator`](${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md) role during Step 6 (Polish). Its scope is intentionally narrow:

| | Caller (`illustrator` role) does | This skill does |
|---|---|---|
| 1 | Invoke [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `scan` once; the scan output enumerates every fenced ASCII block **and** carries each block's pre-extracted slide context (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, optional `presentation_language`) | — |
| 2 | Pick the output filename `<slide-id>-<n>-<short-description>.svg` (kebab-case slug — see [`${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md`](${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md) → *Output filename convention*) | — |
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
| `style_directives` | optional | freeform string with per-render visual instructions from the presenter (e.g. *"use orange for the model panel"*, *"don't use arrows, use plain lines"*). Applied **on top of** the standing rules in `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md`; if it conflicts with a standing rule, the directive wins for this render only — note the deviation in the report. |
| `repo_root` | yes | absolute path to the presenter's **working directory** (the folder where `/talksmith:init` ran — contains `CLAUDE.md`, `config/profile.md`, `talks/`). The skill uses this to anchor Talk-relative paths the caller passes. Plugin-bundled assets like `diagram-style.md` are loaded via `${CLAUDE_PLUGIN_ROOT}/` directly and do **not** depend on `repo_root`. The illustrator role passes it from its own dispatch context. |

## Process

0. **Resolve input mode.** If `ascii_file` is provided, read it, split on the first line starting with `<!-- ascii-note:`. The ASCII payload is everything before that line (rstrip a trailing blank line); the `ascii_note` is everything from the sentinel through the line containing `-->` (inclusive). If no sentinel is present, the whole file is the ASCII payload and `ascii_note` is empty. If `ascii_block` was passed instead, use it directly and treat any caller-supplied `ascii_note` as authoritative.

1. **Detect diagram vs code.** If the resolved ASCII payload is a real programming language (Python, bash, JSON, YAML, etc.) or contains no diagram glyphs (`+-|`, `─│┌┐└┘├┤┬┴┼`, `→ ← ↑ ↓ ⇒ -->`, `=>`, `~~~`, `/\`, `<>v^`), stop and return `skipped: not a diagram`.

2. **Load standing visual rules.** Read `<repo_root>/config/diagram-style.md`. The bullets in that file are the standing rules every render must obey (e.g. "flat style only", "light mode only"). Treat them as hard constraints. If `repo_root` is missing from the invocation, stop and return `failed: repo_root input missing`. If `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md` doesn't exist, render with sensible defaults (light background, flat 2D, plain typography) and note `deviations: no diagram-style.md`.

3. **Merge with per-render directives.** Apply `style_directives` (if any) on top of the standing rules. A per-render directive that contradicts a standing rule wins for this render only — note the deviation in the report. A directive that adds to the standing rules (e.g. a specific color for a panel) is taken verbatim.

4. **Generate text from context, not from the ASCII.** The ASCII gives layout. The labels come from:
   - SVG `<title>`: `slide_title`
   - SVG `<desc>`: the first sentence of `speaker_notes` (one line); fall back to a `slide_title`-derived sentence if `speaker_notes` is empty
   - Per-panel heading: pull from `slide_content_prose` — the words the audience will hear
   - Per-panel subhead: the secondary phrase from `slide_content_prose`
   - In-panel callouts (axis labels, peak markers, equation captions): drawn from `speaker_notes` when it flags something to emphasize
   - **All text in `presentation_language`** — never mix languages. If unclear, fall back to the dominant language of `slide_content_prose`.

5. **Render the SVG.** Use a `viewBox` proportional to the diagram's aspect ratio (commonly `0 0 680 H` for landscape diagrams). Include `<title>` and `<desc>` as the first two children of the root `<svg>` for accessibility. Choose colors and shapes that satisfy *every* standing rule + any non-conflicting per-render directive. When the diagram has semantic structure (input/output, before/after, baseline/improved), use distinct hues to make the structure visible; default palette is the presenter's choice or a tasteful neutral if no directive is provided.

   **Aspect-ratio contract — the SVG's intrinsic aspect is load-bearing downstream.** The Step 8 PPTX renderer sizes each picture's slot from this SVG's `viewBox` ratio (per [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §12) and an audit (`audit_aspect_ratios.py`) fails the build at 1% tolerance if the rendered `cx:cy` diverges from `viewBox_w:viewBox_h`. So:
   - The root `<svg>` **must** declare `viewBox="0 0 W H"` with `W` and `H` chosen to match the diagram's true visual aspect — the eye's reading of the rendered art, **not** the ASCII block's character grid. A 60-char × 14-line ASCII block is *not* 60:14 because monospace cells are roughly half as wide as tall — sanity-check by multiplying char count by ~0.5: 60×0.5 : 14 = 30:14 ≈ 2.14:1, landscape. Pick `viewBox` units that round to that ratio (e.g. `0 0 680 318` for 2.14:1, `0 0 680 510` for 4:3, `0 0 680 383` for 16:9). Round to whole units.
   - Do **not** set `width="…"` / `height="…"` attributes on the root `<svg>` at values that disagree with the viewBox ratio. Either omit them entirely (consumers honor viewBox alone — preferred) or set them to the same numbers as the viewBox so there is one source of truth.
   - Do **not** set `preserveAspectRatio="none"` anywhere. The default `xMidYMid meet` is correct; `none` signals to consumers that anamorphic scaling is OK and defeats every downstream guarantee.
   - When the same diagram could plausibly fit two ratios (e.g. a flow that reads either as a wide row or a tall column), pick the ratio the *content* actually demands and commit — never split the difference. A near-square viewBox to "hedge" against the eventual slot is the bug — the slot adapts to the SVG, not the other way around.
   - Self-check before writing: open the SVG mentally, ask "if I rasterized this at 600px wide, how many pixels tall would it be?" That number divided by 600 must equal `H/W` from the viewBox. If it doesn't, the viewBox is wrong — fix it before step 6.

6. **Write the SVG** to `output_path`. Create the parent directory if it doesn't exist (`mkdir -p`). Overwrite if the file already exists — idempotency is the caller's concern, not this skill's.

   **Then validate it against the aspect-ratio contract** by running [`validate_svg.py`](validate_svg.py) on the file you just wrote:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/validate_svg.py <output_path>
   ```

   The validator checks the same contract spelled out in step 5 and rewrites the file in place when it can auto-repair:
   - **viewBox present + parseable** with positive W, H → unfixable; exit 2 if missing or malformed.
   - **No `preserveAspectRatio="none"`** on the root `<svg>` or any nested `<svg>`/`<image>` → auto-fixed by dropping the attribute (default `xMidYMid meet` restored).
   - **Root `width`/`height` either absent or agree with the viewBox W:H ratio within 1%** → auto-fixed by dropping both attributes (viewBox is authoritative).

   A non-zero exit means the SVG is broken in a way this skill can't mechanically repair (no viewBox, malformed XML, root element isn't `<svg>`). When that happens, **do not return success** — return `failed: svg_validation: <error>` per step 8. A broken SVG must not reach disk: the downstream PPTX renderer trusts the viewBox to size its placement slot, and a faulty viewBox poisons the [`audit_aspect_ratios.py`](../md-to-pptx/audit_aspect_ratios.py) gate at PPTX-build time (one full render cycle wasted). Catching it here is cheap; catching it there is expensive. If repair happened, note the fix count in the step-8 report under `svg_validation:`.

7. **Rasterize a deliverable PNG companion** at `<output_path with .png extension>` (same directory as the SVG, same basename, `.png` extension). This is the **build deliverable** that the Step-8 PPTX renderer consumes — the native `pptx` skill and any python-pptx fallback load via PIL, which cannot decode SVG, so the .pptx references the PNG bytes. Per [`${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md`](${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md) → *Output contract — SVG + PNG companion*, every illustrator run produces both files; the [`md-to-pptx`](../md-to-pptx/SKILL.md) skill's *PNG companion for every SVG* prereq stops the build if the PNG is missing.

   Preferred tool: `cairosvg` (`pip install cairosvg --break-system-packages` in Cowork sandboxes; pure-Python, fast):

   ```bash
   python3 -c "import cairosvg; cairosvg.svg2png(url='<output_path>', write_to='<output_path with .png>', output_width=<viewBox_w * 2>)"
   ```

   Width = SVG `viewBox` width × 2 (e.g. `viewBox="0 0 680 318"` → `output_width=1360`); height auto-derived to preserve aspect ratio per §12. If `cairosvg` isn't available, fall back to `qlmanage -t -s <viewBox_w*2> -o <parent>/ <output_path>` on macOS (then `mv <parent>/<basename>.svg.png <parent>/<basename>.png` to normalize the basename — `qlmanage` appends `.png` rather than replacing). If both fail, return `failed: png_companion: <reason>` per step 8 — the SVG alone is not a successful render.

8. **Rasterize a critique-companion PNG.** Render the SVG to a PNG sibling at `<output_path parent>/.critique/<basename>.png` (create `.critique/` if missing). This PNG is **not** referenced from `final.md`, **not** consumed by the Step-8 PPTX renderer, and **distinct from the deliverable PNG written in step 7** — it exists solely so the illustrator role can perform visual analysis on rasterized pixels in step 5b of its loop (XML inspection of an SVG is not a substitute for visual critique).

   Use `qlmanage` (built into macOS, zero install):

   ```bash
   qlmanage -t -s 1600 -o <parent>/.critique/ <output_path>
   mv <parent>/.critique/<basename>.svg.png <parent>/.critique/<basename>.png
   ```

   `qlmanage` writes the thumbnail as `<input-filename>.png` (it appends `.png` rather than replacing `.svg`), so the `mv` normalizes the basename. If `qlmanage` exits non-zero or the resulting PNG is missing / 0-byte, still report the SVG as `rendered` but add `png_companion: failed` to the report — a missing PNG degrades critique fidelity but doesn't invalidate the render. Never delete the SVG because the PNG step failed.

9. **Return** a one-line report:
   - On success: `rendered: <output_path> · svg_validation: <ok|N fix(es)> · png_deliverable: <path> · png_critique: <path|failed> · directives_applied: <count> · deviations: <none|description>`
   - On skip: `skipped: <reason>`
   - On failure: `failed: <reason>` — and do **not** write a broken SVG. Validation failures from step 6 (unfixable viewBox) surface here as `failed: svg_validation: <error>` and must delete (or never have written) the broken file. Deliverable-PNG failures from step 7 surface as `failed: png_companion: <reason>` — without the PNG the Step-8 PPTX renderer cannot consume the asset, so the render is incomplete; the SVG bytes may stay on disk but the report must not declare success.

## You cannot ask questions

This skill cannot ask follow-ups. If the standing rules + slide context + `style_directives` together don't disambiguate a critical choice, return `failed: ambiguous · <what's unresolved>`. The illustrator role surfaces the ambiguity to the orchestrator, which asks the presenter and re-invokes this skill with the disambiguation baked in.

**Sparse-context is not ambiguous.** When `slide_content_prose` and/or `speaker_notes` are empty, render with whatever context is present (`slide_title`, `section_title`, `section_goal`, `talk_thesis`) and pick neutral colors derived from box order rather than slide-prose keywords. Add `deviations: sparse-context (no <field>)` to the success report. Do **not** return `failed: ambiguous` just because prose is empty — an empty SVG is worse than a sparsely-labelled one.

## What this skill is NOT

- **Not** a coordinator. It renders one block. The illustrator role walks `final.md` and invokes this skill per block.
- **Not** allowed to write outside `output_path`. No edits to `final.md`, no creating sibling files.
- **Not** a `.pptx` renderer. That's [`talksmith:md-to-pptx`](../md-to-pptx/SKILL.md).
- **Not** allowed to read network resources. Pure local file work.
- **Not** dependent on any template catalog. There is no closed style spec or per-shape template library — the standing rules in `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md` plus per-render directives are the full styling input. Start simple; rules accumulate in `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md` over time as patterns crystallize.

## Why a skill, not just the agent

The illustrator role does per-Talk coordination (which slides have ASCII, what's the per-slide context, what should the output filename be) and judgement (the slug, the alt, optionally collecting per-render directives from the presenter). The actual rendering of one block from one context bundle is repetitive enough to factor out — making it a skill keeps each agent invocation small, surfaces a stable per-block contract, and lets the agent focus on judgement over SVG bookkeeping.
