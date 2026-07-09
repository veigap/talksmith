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
