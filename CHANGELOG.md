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
