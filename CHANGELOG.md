# Changelog

All notable changes to the Talksmith plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses [semantic
versioning](https://semver.org/): patch for fixes and docs, minor for new
agents/skills/commands or workflow changes, major for breaking schema or
session-start contract changes. The authoritative version is the `"version"`
field in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

> **Maintenance note (for contributors):** keep this file *useful*, not exhaustive.
> Every commit adds a functional description of what changed and why, but old
> entries get compacted as they age — collapse superseded fixes, fold noise into
> the release summary, drop detail that no longer helps a reader. Less is more.

## [0.8.1] — 2026-07-09

### Fixed

- **Contradiction sweep across the PPTX docs** (from role-playing a real render and an
  independent audit). Corrected the base-template delete range **3–13 → 3–15** everywhere
  (the template is verified 15 slides; deleting only 3–13 would have leaked the card-row
  and icon-bullet example slides 14–15 into every strict deck — a real render bug); removed
  the last places that implied preview runs a CONTROL/block-coverage audit (it has no deck —
  block-coverage holds by construction); added OOXML back to the rubric CONTROL matrix rows;
  repointed the strict spec's dangling `orchestrator.md *Render cycle*` cap references to
  `SKILL.md` → *Render flow*; fixed a stale `§18.2` workflow ref to `§19.3`; and dropped the
  strict spec's undercounted "10 example slides" wording. No behavioral change — the render
  instructions are now internally consistent for all three modes.

## [0.8.0] — 2026-07-09

### Changed

- **Preview outputs numbered individual images, not a grid.** `build_preview.py` now writes
  `slide-01.png … slide-NN.png` at the top of `output/draft-preview/` (the presenter flips
  through them in order); the content-addressed cache stays hidden in `.previews/`. No
  contact-sheet grid.
- **Preview runs the same critique categories and cycle as free-form** — CONTENT +
  AESTHETIC + DISTRIBUTION, ≤2 cycles, per-slide — walked on the numbered images. One
  honest limitation, documented throughout: the preview's renderer is a *deterministic
  code wireframe that takes no fix instructions*, so its REGENERATE cannot autonomously
  restyle a slide the way free-form's native renderer can — FEEDBACK findings **surface**
  for the presenter, who resolves them with a `draft.md` edit (which re-fires the preview).
  This fits the workflow (preview runs during Review, where content edits happen anyway);
  aesthetic/distribution issues are truly fixed on the Step-8 render.

### Fixed

- **Consistency pass across the pptx docs.** Corrected preview's CONTROL to block-coverage
  only (it has no deck, so aspect/cover-fidelity/OOXML can't run), removed stale "grid" and
  "no-critique" references left over from the intermediate iterations, and aligned the
  free-form/preview cycle wording. No contradictory statements remain about caps, category
  selection, audit membership, or the ASCII→SVG (strict/free-form) vs ASCII→PNG (preview)
  split.

## [0.7.0] — 2026-07-09

### Changed

- **Draft preview is now one committed, code-only renderer — `build_preview.py`.** Instead
  of the agent hand-rolling a throwaway build script each run, the whole Step-5.5 preview
  is a single committed command: `python3 build_preview.py --talk talks/<Talk>`. It draws
  each slide **directly to a PNG with Pillow** (title, bullets, diagram/image thumbnails)
  and assembles a contact-sheet `grid.png` — **no `.pptx`, no `.pdf`, no native `pptx`
  skill, no LibreOffice**, so it now runs in **any** session (Cowork no longer required)
  and can truly auto-fire in the background. Only changed slides re-render (content-addressed
  cache). The preview is a deliberately provisional *wireframe* for eyeballing structure
  (slide order, missing/thin sections); it runs **no automated critique** — the real
  content/aesthetic/distribution critique stays on the Step-8 strict/free-form renders,
  whose layouts are actually designed.

### Fixed

- **Preview no longer leaks working-notes onto slides.** `convert.py --draft` now strips
  `**Narrative arc:**` (and still `**Presenter feedback:**`) blocks, and matches those
  labels whether they stand alone or have inline prose on the same line — so a preview
  Agenda shows only its section list, not the author's narrative-arc scaffolding. Inline
  markdown emphasis (`**`, `*`, `` ` ``) is also stripped from wireframe text.

## [0.6.1] — 2026-07-09

### Fixed

- **Preview ASCII PNGs can't collide with Polish images.** Pinned `render_ascii.py`'s
  output to `output/draft-preview/ascii/` so the preview's `ascii-<hash>.png` files never
  land in `talks/<Talk>/images/` (Polish's SVG→PNG `s<sec>-<slide>-….png` territory). The
  two already used different name prefixes and directories; this makes the separation
  explicit in the spec so a preview run can't pollute the real image folder.

## [0.6.0] — 2026-07-09

### Changed

- **Live phase progress in every render mode (no more silent "Multitasking…").** PPTX
  generation must now stream its processing phases as they happen — for preview,
  free-form, and strict alike. The render may no longer run as one opaque multi-minute
  dispatch: a phase event must reach the presenter after pre-process, after the build,
  after CONTROL, and after each critique/fix pass, ticking the checklist in place. The
  slow visual-review walk is chunked into slide batches with per-batch progress
  ("reviewed 10 of 29…"), and any phase silent for >60s is treated as a stall to
  surface. Tightens the earlier checklist contract, which a real multi-cycle strict
  render showed was too easy to satisfy with a single silent sub-agent call.

## [0.5.0] — 2026-07-09

### Added

- **`pptx-learn` — learn strict patterns from real edits (new skill).** When a presenter
  hand-corrects a rendered strict deck (positions, sizes, fonts, fills) and reconciles it,
  this skill mines those corrections into candidate template rules. `learn_patterns.py`
  (python-pptx) is the *evidence* layer — it diffs the human-edited deck's per-shape
  geometry against an as-generated baseline snapshotted at strict render
  (`output/final.generated.geometry.json`) and surfaces the recurring deltas. The **LLM is
  the analyst**: it examines the before/after slides (multimodal where renders are
  available), reasons about *why* each change was made, and — crucially — judges whether a
  delta is a **generalizable template rule** or a **content-specific one-off**, discarding
  the latter even when it recurred. Survivors, each carrying a design rationale, land in
  the project file `config/strict-learnings.md`; a human promotes chosen ones at Step 7
  into the plugin's declarative `config/pptx-styles/strict/conformance-patterns.md`, which
  future strict renders apply. Runs auto after `pptx-merge` and on-demand. strict-only.
- **Declarative strict conformance.** `config/pptx-styles/strict/conformance-patterns.md`
  holds the strict template's layout rules as data (with a `why` on each), so learned
  patterns can be merged in cleanly rather than the rules living only as prose.
- **Richer good-practice bar from established design guidance.** Folded in Gamma / 10-20-30
  / composition principles: one core message per slide, ≤2 type families, ≤~4 colours, a
  ~30pt readable-from-the-back floor, rule-of-thirds focal placement, and a deck-wide
  cross-slide-consistency check.

### Changed

- **Cleaner critique taxonomy.** Audited the rubric for repeats/misclassification: the
  spatial practices that were mis-filed under AESTHETIC (margins, visual balance, focal
  point) moved into DISTRIBUTION and merged with their overlaps, so every concern is
  checked in exactly one place. AESTHETIC is now purely visual style; DISTRIBUTION is
  purely spatial. Text-alignment (AESTHETIC) vs element-grid-alignment (DISTRIBUTION) are
  disambiguated.

## [0.4.0] — 2026-07-09

### Added

- **Shared, categorized critique rubric** ([`config/pptx-styles/critique-rubric.md`](config/pptx-styles/critique-rubric.md)).
  One source of truth for what each render mode's visual review walks, organized into
  four categories — **CONTENT**, **AESTHETIC**, **DISTRIBUTION** (new), and
  **LAYOUT-CONFORMANCE** (strict-only). Each mode selects which categories it walks;
  adding a practice or refining a mode is a one-line edit. Replaces the rubric that was
  buried inside the strict spec.
- **Materially richer aesthetic + distribution bar.** Beyond the original checks
  (overflow, margins, balance, focal point, image scale) the rubric now covers
  contrast, type-scale, alignment, emphasis restraint, colour harmony, image-treatment
  consistency, widows/orphans — and a whole **distribution** category (grid alignment,
  gutters, negative-space balance, column balance, proximity grouping, uniform sizing,
  reading flow). This is what makes slides stop looking "off."
- **Free-form now critiques and self-corrects.** Free-form gained a GENERATE → CONTROL
  → FEEDBACK → REGENERATE loop (≤ 2 cycles) over CONTENT + AESTHETIC + DISTRIBUTION —
  it no longer ships its first pass unreviewed. It still never imposes the strict
  template's layout; it judges whether its own design *works*.
- **Preview upgraded to a per-slide, incremental critique loop.** The Step-5.5 draft
  preview now renders per slide, rasterizes ASCII diagrams to PNG **by code**
  ([`render_ascii.py`](skills/md-to-pptx/render_ascii.py)), and re-renders only the
  slides that changed between review rounds via a content-addressed cache
  ([`preview_plan.py`](skills/md-to-pptx/preview_plan.py)). It walks the same
  CONTENT + AESTHETIC + DISTRIBUTION bar as free-form.
- **Live progress visibility in every render mode.** All modes now drive a live,
  todo-list-style checklist that ticks each step as it completes, with heartbeats on
  long stages — no more long silent renders.
- **Per-mode output isolation.** Each render writes `output/final.<style>.pptx` (and
  per-style intermediate + critique PNGs) so strict and free-form renders coexist for
  side-by-side comparison; the most recent render is copied to the canonical
  `output/final.pptx` the reverse pipeline reads.

### Changed

- Free-form is no longer single-pass. Cycle caps: strict 3, free-form 2, preview 2.

### Fixed

- **Palette/fonts audit membership.** Now consistently **strict-only** (a
  layout-conformance concern); free-form and preview slides past the cover have no
  fixed palette/font and are not audited against one. Resolves a three-way
  contradiction across the specs.
- Removed dangling references to free-form spec sections (§5–§8) and the phantom
  "8-practice list" that were never written on disk, and stale cross-refs that named
  `orchestrator.md` as the home of the visual rubric.

## [0.3.0] — 2026-07-09

### Added

- **Draft preview — optional Step 5.5.** A fast, throwaway PowerPoint rendered straight
  from `draft.md` so the presenter can eyeball the deck's shape before committing to
  Polish + the final render. Auto-fires in the background (non-blocking) when the draft
  first completes and refreshes on change; offered at the review-end checkpoint. Reads
  `draft.md` read-only via `convert.py --draft`, writes only under
  `output/draft-preview/`. Cowork-only.

### Fixed

- **md-to-pptx section dividers.** The `final.md` → intermediate converter was letting a
  trailing stripped field (e.g. `### Sources`) swallow the following `# N.` section
  divider; every section divider after the first could vanish. Field bodies now
  terminate at the next `---` rule or heading.

## [0.2.0] — 2026-07-09

### Added

- **Reverse pipeline — reconcile an externally-edited `.pptx` back into `draft.md`.**
  Three CLI-safe skills, run in order, that pull edits a presenter made in
  Keynote/PowerPoint back into the editable source of truth so the next Polish
  re-derives `final.md`:
  - **`pptx-extract`** — reads the deck (`python-pptx`), classifies slides
    (cover / agenda / section-divider / content), stages every content image, and
    rebuilds it as `draft.md`-shaped Markdown (`reconcile/finalpptx.md` + inventory
    sidecar). Requires `--style {strict|free-form}`.
  - **`pptx-diff`** — aligns the reconstruction against `final.md` and reports every
    title / content / speaker-note / image change (bullet-granular, low-confidence
    matches flagged); writes `reconcile/finalpptx.diff.json`. Stdlib-only, read-only.
  - **`pptx-merge`** — re-anchors each change structurally and auto-applies the
    simple, high-confidence ones to `draft.md`; routes complex/confusing ones to the
    Editor. Atomic, anchor-guarded. Writes only `draft.md` and `images/`.

  All artifacts live under `talks/<Talk>/reconcile/`. README documents the full
  workflow.

### Fixed

- `pptx-extract`: stable shape ids and a wider active-dot palette for divider
  detection.
- `pptx-diff`: pipe-table rows are filtered out of the prose diff units so table
  edits don't surface as spurious content changes.

## [0.1.0]

Initial plugin release: the Presenter Agent orchestrator, five subagents
(Librarian, Composer, Editor, Illustrator, Global-Librarian), the `/talksmith:init`
command, and the forward-pipeline skills (`ingest`, `ascii-to-svg`, `polish-ascii`,
`feedback-cycle`, `md-to-pptx`) driving the 8-step workflow from raw sources to
`draft.md`, `final.md`, and an optional `.pptx`.
