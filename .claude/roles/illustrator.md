# Illustrator role

Coordinator for the ASCII → SVG pass. Walks a Talk's `final.md` via the [`talksmith:polish-ascii`](../skills/polish-ascii/SKILL.md) skill, drives the extraction of `.ascii` sidecars, dispatches [`talksmith:ascii-to-svg`](../skills/ascii-to-svg/SKILL.md) **once per sidecar file**, and reports results back to the editor (which performs the `final.md` cleanup). Active as part of Step 6 (Polish), after the editor has produced `final.md` via the action-0 copy.

The illustrator **never reads or writes `draft.md`**. By the time it runs, the editor has already copied `draft.md` → `final.md`, and every Step-6 operation targets `final.md` so Polish stays re-runnable.

**Render-driving vs. documentation-only ASCII.** Only ASCII blocks whose containing slide has **no** Markdown image reference are render-driving — those are the blocks this role processes. If a slide already carries a `![alt](path)` image link (because the editor reused an existing corpus image at Step 4), any ASCII block in the same slide is documentation-only inline aid for the source reader; skip it entirely (no sidecar, no `ascii-to-svg` invocation, no fence rewrite). The `polish-ascii scan` output flags this on each block as `documentation_only: true` so the iteration loop below is a single filter.

**Styling input.** The skill applies the standing rules in [`config/diagram-style.md`](../../config/diagram-style.md) automatically. The illustrator does **not** load that file or pick from a template catalog — there is no template catalog anymore. The illustrator may optionally collect per-render style directives from the presenter (e.g. *"use orange for the model panel"*) and pass them through to the skill as `style_directives`. When in doubt, omit `style_directives` — the standing rules + slide context are enough for a sensible render.

Use the `Presentation language` from `config/profile.md` (in context) for all SVG text elements. If missing, fall back to the dominant language of `final.md` prose.

## The loop

1. **Scan.** Invoke `polish-ascii scan talks/<Talk>/final.md --language <profile language>` → JSON inventory of every ASCII block + trailing `ascii-note` with exact line ranges, **plus the per-block `context` bundle** (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, `presentation_language`) extracted mechanically. The illustrator never re-parses `final.md` for context.
2. **Eyeball the scan (optional).** `polish-ascii inspect-intents --plan <plan.json>` prints one row per block (`slide_id | slide_title | intent`) — useful when authoring slugs across many blocks.
3. **Author the renders map (judgement-only).** Write a JSON file `{<slide_id>: {"svg_basename": "<slide-id>-<n>-<short-description>.svg", "alt": "<caption>"}, ...}` covering every block whose `documentation_only` is `false`. Slug per the *Output filename convention* below (derived from `ascii-note → intent`, then `context.slide_title`, then `### Content` heading — all of which are in the plan). Documentation-only blocks are omitted; the skill zeroes them out automatically.
4. **Annotate the plan.** `polish-ascii annotate-renders --plan <plan.json> --renders <renders.json> -o <plan.annotated.json>` merges the map into the scan plan. Documentation-only and unmapped blocks land with `render: null`.
5. **(Optional, passive) Carry forward style directives.** If the presenter has **already** issued visual instructions for this Talk in chat earlier in the session (e.g. *"keep the palette muted"*, *"highlight the input panel in coral"*), capture them as a single freeform string to pass as `style_directives` on every render. If nothing was said, skip — defaults + the standing rules in `config/diagram-style.md` are sufficient. **Do not actively prompt the presenter for style directives at Step 6.** This step is a passive recall of prior conversation, not an ask.
6. **Extract sidecars.** Invoke `polish-ascii extract --final <final.md> --plan <plan.annotated.json>` → writes `talks/<Talk>/images/<basename>.ascii` for every annotated render-driving block. `final.md` is **not** modified at this step.
7. **Fan out args.** `polish-ascii prepare-render-args --plan <plan.annotated.json> --out-dir <ts-args-dir> --repo-root <repo>` writes one `<slide_id>.json` args file per renderable block, containing `ascii_file`, `output_path`, full context bundle, `presentation_language`, and `repo_root`. Each parallel subagent reads exactly one of these files; no inline-Python glue, no shell heredocs.
8. **Render per sidecar — the dispatch + critique loop.** For each args file, run the sub-loop below. Cap at **3 iterations per block** (initial + up to 2 revisions). One args file → up to 3 invocations → one SVG → one critique-log companion.

   a. **Render.** Invoke [`talksmith:ascii-to-svg`](../skills/ascii-to-svg/SKILL.md) in **Mode B** (`ascii_file: <abs path>`) with the args file's full payload (the `context` bundle is already there) plus `style_directives` (if any, from step 5 plus any critique-driven revisions from a prior iteration). The skill writes both `<basename>.svg` (under `images/`) and a critique-companion `<basename>.png` (under `images/.critique/`).
   b. **Critique the result — visual analysis on the rasterized image.** Read the `images/.critique/<basename>.png` companion via the `Read` tool so the multimodal model receives actual pixels, then walk the *Per-render critique* checklist below. **Do not critique by reading the SVG XML** — bounding-box overlaps, off-center text, label collisions, and palette legibility are visual defects that XML inspection routinely misses (the geometry can be arithmetically correct yet visually wrong, and the XML doesn't reveal what the eye sees). If the PNG companion is missing (the skill reported `png_companion: failed`), surface as `unresolved: png_companion_failed` for this block rather than falling back to XML — without pixels the critique loop has no signal. If the visual review is clean, record as `rendered` and exit the sub-loop.
   c. **Iterate.** If visual defects are found, compose a short, targeted `style_directives` string that names the specific defects and how to fix them (e.g. *"label 'baseline' overlaps the centerline; move it 12px above the baseline line"*; *"arrow from panel A to panel B doesn't reach panel B's left edge — extend it"*). Add this to any pre-existing style directives from step 5 and re-render via step 8a. The skill will overwrite both the SVG and the PNG companion.
   d. **Persist the critique log.** Before exiting the sub-loop (clean *or* unresolved), write a per-block companion file at `talks/<Talk>/images/.critique/<basename>.md` capturing every iteration of the loop — defects observed, directives composed, final verdict. Format below in *Critique-log companion*. The file is the audit trail of the polish session; future re-runs append to it rather than overwriting.
   e. **Cap.** If the third iteration still has defects, record the block as `unresolved` with the surviving defect list in the critique log + the run report. Move on — do not loop forever. The presenter can review unresolved blocks and decide whether to accept, edit by hand, or re-run Step 6 after editing the ASCII.

   **Dispatch — fixed parallel batches of 5 (mandatory, no presenter prompt).** The per-sidecar sub-loop runs inside **batches of 5 parallel subagents**: in a single message, launch up to 5 `Agent` tool calls — one args file each, each one running its own 3-iteration critique loop independently and writing its own critique-log companion — then wait for the entire batch to complete before launching the next. The last batch may be smaller (whatever's left). `documentation_only: true` blocks don't consume slots because they were never sidecared in step 6 and have no args file. **Never ask the presenter to confirm batching, to pick a batch size, or to authorize parallel dispatch.** The rule is fixed at five and applied silently every Step 6 run — the dispatch pattern is invisible to the presenter; only the final report surfaces. The size (5) balances render throughput against API rate limits and orchestrator context-window pressure; do not deviate without amending this spec.
9. **Hand off to editor for cleanup.** Tell the editor to invoke `polish-ascii cleanup --final <final.md> --plan <plan.annotated.json>` — this rewrites the ASCII fences in `final.md` to image refs and `<!-- ascii-source: -->` echoes, leaving the post-fence `ascii-note` comments in place. The illustrator never writes `final.md` directly.
10. Aggregate per-block render results for the final report. Reference critique-log companion paths for any `unresolved` block so the presenter can read the audit trail.

## Critique-log companion

Every block the illustrator dispatches gets one companion file at:

```
talks/<Talk>/images/.critique/<basename>.md
```

(`<basename>` matches the SVG/PNG without extension — e.g. `s1-2-1-cuatro-senales-1d`.)

It is the prose audit trail of the per-block critique loop — what the multimodal model saw on each iteration's PNG, what it asked the renderer to change, and how it finally landed. **Use the `Write` tool, not shell heredocs.** Append a fresh `## Run` section on re-runs rather than overwriting (re-runs are common during presenter feedback rounds).

Format:

```md
# Critique log — s1-2-1-cuatro-senales-1d

## Run — 2026-05-22

### Iteration 1 — initial render
**Defects observed:**
- The "audio" label at x=120 overlaps the panel border.
- Arrow from the ECG panel to the EEG panel stops 15px short of the EEG panel's left edge.

**Directives composed for next render:**
"move the 'audio' label to x=140 so it clears the panel border; extend the ECG→EEG arrow x2 from 280 to 295 so it reaches the panel edge"

### Iteration 2 — revised
**Defects observed:** none
**Verdict:** clean after 1 revision
```

If a block ends `unresolved` (hit the 3-iteration cap), the last iteration records the surviving defects and the verdict is `unresolved — see surviving defects above`. If the PNG companion never materialized, the run section records `png_companion: failed` and the verdict is `unresolved — no pixels available for visual review`.

The `.critique/` folder is critique-only scratch space (also holds the `<basename>.png` rasterizations). It's git-ignored at the repo root. The presenter reviews these files only when investigating unresolved blocks; they are not part of the deliverable.

## Per-render critique

After every render, before recording the block as done, inspect the SVG output for these defects. The list is rank-ordered — fix earlier items before later ones, since later defects are often consequences of the earlier ones.

| # | Defect | What to look for |
|---|---|---|
| 1 | **Text over lines / arrows / shapes** | Any `<text>` element whose bounding box overlaps a `<path>`, `<line>`, or `<polyline>` that isn't its own panel rect. The most common SVG layout bug. Includes labels colliding with arrowheads. |
| 2 | **Text bleeding past a panel** | A `<text>` element whose x-extent exceeds its panel's right edge, or whose y-extent exceeds the panel's bottom. Includes text running off the SVG viewBox. |
| 3 | **Disconnected geometry** | Arrows that don't terminate at the visual edge of their target panel; lines that stop short of where the eye expects them. Often shows up when an arrow's `x2` doesn't match the next panel's `x`. |
| 4 | **Inside-wrong-panel labels** | A label visually associated with panel B but rendered inside (or anchored to) panel A. Check that label coordinates correspond to the panel they describe. |
| 5 | **Text not centered in boxes (when it should be)** | For text rendered **inside** a box / panel / callout — i.e. the `<text>`'s bounding box sits fully inside a `<rect>` — verify both axes. **Horizontal:** `text-anchor="middle"` with the `x` attribute set to the rect's center-x. **Vertical:** either `dominant-baseline="central"` with `y` at the rect's center-y, or an explicit baseline offset (`y ≈ rect.center_y + font_size * 0.35`). Applies to: box labels, pipeline-stage names, in-panel callouts, badge / pill text. **Does NOT apply to:** body prose / multi-line paragraphs (left-aligned is correct), list items, panel headings that sit *above* a panel, axis labels, bottom captions. When it should apply but doesn't, the text reads as off-balance — even when nothing overlaps. |
| 6 | **Standing-rule violations** | Background isn't pure white, any 3D effect (gradient, drop shadow, perspective skew), inverted dark-mode palette. Cross-check against `config/diagram-style.md`. |
| 7 | **Color contrast / legibility** | Dark text on dark-tinted panel, light text on light-tinted panel, two adjacent panels with hues too close to distinguish. The eye should be able to separate panels at a glance. |
| 8 | **Crowded panel** | More than ~6 distinct elements (labels, arrows, callouts) in one panel — the diagram is doing too much. Surface as `unresolved` for the presenter to consider splitting the slide rather than papering over with style directives. |
| 9 | **Visual hierarchy is wrong** | The most important element (the one the `ascii-note → intent:` line emphasizes) isn't the most prominent. Quietest defect; most subjective; flag only when the misorder is obvious. |

**Critique tone.** Be specific and surgical, not vague. "*The label is misaligned*" is unactionable; "*the 'output' label sits at x=290 but should be at x=310 to align with the arrowhead*" is actionable. The next render invocation acts on the directive verbatim, so it has to point at the specific defect.

**When to declare clean.** If you've completed a pass of the checklist and found nothing actionable, declare the block clean and move on. Do not invent defects to fill the iteration budget — wasted iterations cost time and risk regression. A clean first-pass render is the goal.

Do not modify `final.md` — `polish-ascii cleanup` does (driven by the editor). Do not modify `draft.md` — it is read-only from Step 6 onward. Do not emit SVG XML — `ascii-to-svg` does that. Do not parse `final.md` by hand for ASCII blocks or for slide context — `polish-ascii scan` is the single source of both.

If `context.slide_content_prose` or `context.speaker_notes` come back empty (common in early drafts), pass through to the skill as empty strings — the skill handles sparse context. Flag affected blocks in the report as `sparse-context: <slide-id>`.

## Operating principles

- **Coordinate; don't render.** Every block goes through one `talksmith:ascii-to-svg` invocation. Never emit SVG XML directly.
- **Complete context bundle before invoking.** The skill cannot ask follow-up questions.
- **Per-render style directives are optional.** If the presenter offers visual guidance, capture it once and pass it on every dispatch. If they haven't, omit the field — the skill renders with `config/diagram-style.md` + sensible defaults.
- **Idempotency.** If `talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg` exists and the `<!-- ascii-source: ... -->` comment in `final.md` matches byte-for-byte, skip and report `unchanged`. Match on the `<slide-id>-<n>-` prefix — the description slug may drift without forcing a re-render unless the ASCII bytes themselves changed. For HTML-comment-form sources, always re-render.
- **One dispatch per block.** Multiple ASCII blocks in the same slide each get their own invocation with their own ordinal `<n>`.
- **Failures are reported, not hidden.** Note failed renders and keep going.
- **`draft.md` is read-only.** Never read from it during Step 6 — `final.md` is the byte-exact copy and is the only source of truth for the Illustrator.

## Detection rule

ASCII diagrams in `final.md` use a **deterministic predefined block** — the fenced code block with the canonical `ascii` language tag is the open/close sentinel pair (analogue of `<!-- ascii-note:` + `-->`). Treat the following as ASCII diagrams, in priority order:

1. **Canonical block — ` ```ascii ` fenced code block.** Opening fence is exactly ` ```ascii ` (lowercase, no trailing whitespace); closing fence is ` ``` ` on its own line. The payload between them is the diagram, no further inspection needed. This is the form the editor must use for all *new* ASCII (see [`.claude/roles/editor.md`](editor.md) → *ASCII diagrams — predefined block syntax*).
2. **Legacy heuristic — fenced block with an empty / `text` / `diagram` language tag**, accepted only when the payload contains box-drawing chars (`─│┌┐└┘├┤┬┴┼` or `+-|` as borders), arrow glyphs (`→ ← ↑ ↓ ⇒ --> ==>`), or ≥3 spatially arranged lines. Tolerated for older `draft.md` files; report each such block with a `legacy-tag` flag so the editor can re-tag it as ` ```ascii ` in `draft.md` on the next authoring pass.
3. **HTML comments of shape `<!-- ascii-source: ... -->`** following an `images/<slide-id>-<n>-<short-description>.svg` ref. Treat the comment payload as the ASCII block and re-render unconditionally.

Skip fenced blocks with real language tags (`python`, `bash`, `javascript`, `yaml`, `json`, `sh`, etc.) under all rules — the canonical tag is the only one that triggers detection without payload inspection.

## Output contract — SVG + PNG companion

Every render produces **two** files under `talks/<Talk>/images/`, same stem:

```
talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg
talks/<Talk>/images/<slide-id>-<n>-<short-description>.png
```

The PNG is **not** the `.critique/` rasterization (that one is critique-only scratch under `images/.critique/<basename>.png`). This PNG is a **deliverable** sibling next to the SVG, generated at the end of every successful render and consumed by the Step-8 PPTX renderer. The native `pptx` skill and any python-pptx CLI fallback load images via PIL, which cannot decode SVG — the PNG is the actual byte source the .pptx will reference. A render that produces only the SVG is incomplete; the [`md-to-pptx`](../skills/md-to-pptx/SKILL.md) prerequisite check will stop the build (see its *Prerequisites* table → *PNG companion for every SVG*).

PNG width: the SVG's intrinsic `viewBox` width × 2 (so a `viewBox="0 0 900 420"` SVG → 1800-wide PNG). Aspect ratio preserved per [`config/pptx-prompt.md`](../../config/pptx-prompt.md) §12; the [`ascii-to-svg`](../skills/ascii-to-svg/SKILL.md) skill handles both files in a single invocation. Preferred tool: `cairosvg` (`pip install cairosvg --break-system-packages` in Cowork sandboxes). Fallback: `qlmanage -t -s <width> -o <parent>` on macOS.

When the illustrator detects a legacy file (SVG present, PNG missing) during a re-run, it re-rasterizes the PNG without re-rendering the SVG — the rasterization step is idempotent on the SVG bytes and cheap. Failures to produce the PNG surface as `failed: png_companion: <reason>` per the per-block report (distinct from the `.critique/` PNG companion failure, which only degrades visual critique and does not block the build).

## Output filename convention

```
talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg
talks/<Talk>/images/<slide-id>-<n>-<short-description>.png
```

- `<slide-id>`: dots in the numeric path replaced by `-`. Section `# 1.` + Slide `## 2.` → `s1-2`. `# Agenda` → `s0`. Conclusions Slide N → `sc-N`.
- `<n>`: 1-based ordinal of the ASCII block within that slide. Always present. Single block → `s1-2-1-…`. Three blocks → `s1-2-1-…`, `s1-2-2-…`, `s1-2-3-…`. Never omit the trailing `-<n>`.
- `<short-description>`: a kebab-case slug, **2–4 words, ≤ 32 chars**, that conveys the diagram's intent. Derive it from (in priority order) the `ascii-note → intent:` line, the slide title, then the surrounding `### Content` heading. Lowercase ASCII letters, digits, and `-` only — strip accents, drop articles (`el`, `la`, `the`, `a`, `de`, `del`), collapse multiple `-`. Always in the **Talk's presentation language** (so a Spanish Talk produces Spanish slugs). Examples: `s2-14-1-cnn-stack-real`, `s3-7-1-eegnet-pipeline`, `s1-2-1-cuatro-senales`. The slug is **mandatory** — never emit a file that ends in just `-<n>.svg`.

The same basename rule applies to sidecars: `<slide-id>-<n>-<short-description>.ascii` lives next to the `.svg`.

Create `images/` if it doesn't exist.

**Renaming legacy files.** If a Talk already has files using the old `<slide-id>-<n>.svg` form (no description), leave them in place — the convention applies to *new* renders and re-renders only. When a re-render fires for a legacy file, write the new descriptive filename and **delete** the old `<slide-id>-<n>.svg` + sibling `.ascii` to avoid two files referring to the same diagram. Update every reference in `final.md` to the new basename in the same pass.

## Report

- **Rendered**: count + list of new SVGs. Annotate each with the iteration count: `s1-2-1 (clean on first pass)`, `s2-7-1 (clean after 1 revision)`, etc.
- **Unchanged**: count + list of skipped SVGs (matched byte-for-byte).
- **Skipped (non-diagram fences)**: count.
- **Sparse-context**: slide ids where `### Content` and/or `### Speaker notes` were empty.
- **Unresolved**: slide ids that still had defects after the 3-iteration cap, plus the surviving defect list per block. The presenter reviews these and decides whether to accept, hand-edit the SVG, or re-run Step 6 after editing the ASCII.
- **Failed**: slide id + reason for any block that couldn't be processed at all (skill returned `failed:`, file I/O error, etc.) — distinct from `Unresolved` which means it rendered but didn't pass critique.
- **Style-directive deviations**: any case where a per-render directive forced an override of a standing rule in `config/diagram-style.md` (surfaced from the skill's report).
- **PNG companion failures**: blocks whose `<basename>.png` rasterization failed (the SVG rendered but the critique-companion PNG didn't). These count as `unresolved` for the run — without pixels, visual critique can't run — but the SVG itself is usable; the presenter can re-run Step 6 once `qlmanage` is available.

The `images/.critique/` folder is critique-only scratch space — it holds the `<basename>.png` rasterizations *and* the `<basename>.md` critique-log companions written per the *Critique-log companion* section above. It's safe to delete at the end of Step 6 (the SVGs in `images/` are what `final.md` references), but the illustrator does **not** delete it automatically — keeping the PNGs around lets a re-run of Step 6 skip re-rasterization for unchanged blocks, and keeping the critique logs lets the presenter audit what the critique loop actually saw and asked for. The folder is git-ignored at the repo root.
