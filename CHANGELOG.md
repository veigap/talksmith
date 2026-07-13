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

## [0.27.0] — 2026-07-13

### Added

- **The agenda is re-shown at every section start, with the active section highlighted.** The
  HTML deck parses the canonical section list from the Agenda slide and, at each section-start
  divider, renders the full numbered agenda with that section accent-highlighted (per
  `slide-templates.md`). Mid-section `〔divisor〕` sub-openers stay as plain title slides.

## [0.26.0] — 2026-07-13

### Changed

- **Per-concept icons are matched against the live Material Symbols catalog, not a hardcoded
  keyword→icon table.** `build_html` fetches the full catalog metadata (icon names + English
  search tags + popularity, cached, never committed) and scores each concept's **label** (body
  only breaks ties) against it — so any of the ~4200 icons can be chosen, and the choice is
  grounded in Material's own tags. A thin Spanish→English bridge lets Spanish concept words match
  the English tags; a small regex seed is the offline fallback. Fixes e.g. "Seguridad" → `shield`
  (was a brittle 25-row map, and body text could hijack the icon).

## [0.25.1] — 2026-07-13

### Fixed

- **Under-structured slides no longer render as a wall of plain text.** The `fallback` template
  (≈⅓ of a real narrative deck) now renders a **styled lead + accented point panels** (red
  left-rule cards) instead of bare paragraphs — the "lead + facts" catalog shape — so even
  prose slides look designed, not like bullets.
- **`〔divisor〕` / `〔Backup〕` section markers are honoured.** A title carrying one of these
  markers is now treated as a section divider (even at H2, per `slide-templates.md`) and the
  marker is stripped from the shown title — previously the literal `〔divisor〕` text leaked onto
  the slide.

## [0.25.0] — 2026-07-13

### Changed

- **The HTML deck (`html` + `preview`) is now built on [Reveal.js](https://revealjs.com/)**
  (vendored + inlined under `skills/md-to-deck/vendor/reveal/`, so the deck stays offline and
  self-contained). Our catalog templates render *inside* Reveal `<section>`s as a **custom theme
  aligned with the strict tokens** (Helvetica/Courier, `#DA1B2E`, pill/callout palette). Reveal
  now owns navigation, deck-to-window scaling, the slide overview, transitions, **speaker notes**,
  and **PDF export** — replacing the hand-rolled present/navigation/fit chrome. The only custom
  presentation code left is a per-slide content-fit (scale-to-fill-width + fit-height), which
  Reveal and CSS genuinely can't do.
- **New Reveal-native features:** **PDF export** (open the deck with `?print-pdf`, then Print →
  Save as PDF), slide **overview** (`Esc`), subtle **transitions**, and full-screen present mode
  (`F`) — all standard Reveal affordances.
- **Presenter comments are preserved, not dropped.** `### Speaker notes` blocks are captured into
  `<aside class="notes">` and shown in Reveal's **speaker view** (`s`) — the native-`.pptx`
  notes-pane behaviour, in HTML. (Previously these leaked onto the slide as a callout, then were
  dropped; now they're kept off the slide face but available to the presenter.)
- **Renderer cleanup.** The parse + template-classification logic moved to a clearly-named
  `slide_model.py`; the retired Pillow wireframe renderer (`build_preview.py`, `preview_plan.py`,
  `render_ascii.py`) is deleted. `html_style.py` now holds only template markup + the Reveal
  theme CSS.

### Fixed

- Rendered the real `seguridad-governance-ai` deck (74 slides) as an end-to-end test, fixing:
  speaker-notes / `### Sources` blocks leaking onto slides (now captured/dropped correctly),
  literal `>` blockquote and `~~strikethrough~~` markers, an empty-bullet line producing a stray
  " -", and a long cover title overrunning the class/author block (now a pure-CSS reserved title
  band). Parsing lives in `slide_model.py`.

## [0.24.1] — 2026-07-13

### Fixed

- **HTML fit-to-slide reworked — content no longer overflows, clips, or shrinks into a tiny
  centred block.** The old scaler capped shrink at 0.5 (so busy slides clipped), scaled the
  region from a top origin (leaving a dead void), and measured `clientHeight` including padding
  (so tall slides lost their last line). The content region now solves for a scale that fits the
  height *and* widens the content so it always spans the full width — big cards filling the page
  instead of a small centred cluster — then centres vertically. Verified across all 29 templates
  in the test deck (concept 2/4/6, process, stat, comparison, code, content+image,
  content+cards+image, icon-list): every slide fits with nothing clipped or overlapping the title.

### Changed

- **Docs: the orchestrator's Step 5.5 and the config specs now describe `preview` as the styled
  HTML render it is** (`build_html.py --draft` → `preview.html`), not the retired Pillow PNG
  wireframe. Step 8's prerequisite clarifies that `html` renders without Cowork, so it's offered
  even when the native `.pptx` styles are unavailable. `md-to-deck`'s `style:` list now includes
  `html` (same renderer as `preview`, reading `final.md`).

## [0.24.0] — 2026-07-13

### Changed

- **Skill renamed `md-to-pptx` → `md-to-deck`.** The skill now renders `.pptx` (strict /
  free-form) *and* styled HTML (`html` / `preview`), so the `pptx`-specific name undersold it.
  Renames the skill folder, its `SKILL.md` `name:` (`talksmith:md-to-deck`), the test fixture
  folder (`tests/skills/md-to-deck/`), and every `${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/…`
  reference repo-wide. The orchestrator dispatches it by the new name automatically; no re-init
  needed. (The `config/pptx-styles/` folder and the reverse-pipeline `pptx-*` skills keep their
  names — they are genuinely pptx-scoped.)

## [0.23.1] — 2026-07-13

### Added

- **HTML render — a deterministic, styled deck rendered by code.** New `build_html.py`
  (shared tokens/components in `html_style.py`) turns a talk's markdown into a
  self-contained styled HTML deck that **always** emits the full styled layer — cards
  (never bullets), per-concept Material Symbols icons (fetched by name via `icon_fetch.py`,
  recoloured, inlined), callout boxes, code surfaces — because the same components produce
  it in code. This fixes the native-`.pptx` failure where the styled layer was silently
  dropped and no audit caught it. Two styles share the renderer: **`html`** renders
  `final.md` as a shareable deliverable (`output/html/index.html`); **`preview`** replaces
  the old Pillow wireframe — it now renders a pre-Polish `draft.md` to a styled
  `output/draft-preview/preview.html`. Both classify every slide against the shared catalog,
  honour an optional `<!-- template: X -->` override, and write a template-decision log.
- **Presentable deck + present mode.** A fixed header (section pill + title, anchored — it
  does not move with content) over a content region that **scales to fit 16:9** (nothing
  clipped), plus present mode: ▶ full screen, → / ← or click to advance, `F` browser full
  screen, `Esc` exits. The cover follows the free-form §2 recipe (title top-left,
  class/author lower-left, institution logo bottom-right).
- **Strict icon-coverage audit** (`audit_icon_coverage.py`) — fails a strict render that
  ships concept cards / callouts with zero small icon pictures.
- **Canonical HTML test fixture** at `tests/skills/md-to-deck/` — one slide per template
  plus edge cases (2/3/4/6 concept cards, 3/5-step process, 2/3-column comparison, long
  titles/bodies), each forced with a `<!-- template: X -->` directive, rendered to the
  committed `style-reference.html`. Regenerate it after any style change.

### Fixed

- Concept-breakdown of 4 cards renders 2×2 (not 3+1); stat strips use adaptive columns.
- Slides 4/5: cards no longer overwrite the title (content region flows from the top and
  clips, so overflow never pushes up into the fixed header).
- Slide 22 (content + cards + image): added the missing `.cci`/`.ccicards` grid CSS.
- `<meta charset="utf-8">` on the HTML doc fixes mojibake.

## [0.19.1] — 2026-07-12

### Changed

- **Dev docs: added a "refreshing the plugin so Cowork picks up changes" section** to the
  plugin-repo `CLAUDE.md` — the short loop (commit + push → bump version → `/plugin update
  talksmith` → new session / `/plugin reload`) that avoids the full reinstall + re-init,
  since everything under `${CLAUDE_PLUGIN_ROOT}/` is read fresh each session and only the stub
  needs re-init. Contributor-facing only; no runtime behavior change.

## [0.19.0] — 2026-07-12

### Changed

- **Free-form now honors the shared design bar *at GENERATE*, not just template choice.**
  Free-form classified against the catalog but otherwise designed "freely," treating the
  design practices as a mere human checklist — so decks under-honored the guidance, and a
  dangling ref pointed at a non-existent free-form FEEDBACK step. Free-form's §1/§3 now
  require the renderer to design *from* the shared bar as it builds: the generic
  `visual-guidance.md` floor (hard invariants + principles), the matched template's *Format*
  (incl. the concept-breakdown per-concept icon and balanced cards), and the
  `slide-design.md` CONTENT/TEMPLATE/AESTHETIC/DISTRIBUTION practices. Its freedom is now
  scoped to the *visual execution* (palette, type, spacing, icon idiom); the only bar it
  still skips is the strict-only LAYOUT-CONFORMANCE. Stays single-pass (no critique loop) —
  the guidance is applied while building and the presenter reviews after.

## [0.18.0] — 2026-07-12

### Added

- **Every render writes a template-decision log** beside its output —
  `output/final.<style>.template-log.md` (same `final.<style>` convention as the deck, side
  by side) for strict/free-form, `output/draft-preview/template-log.md` for preview. Records
  per slide the template chosen, why, what was ruled out, the raw signals, and flags, plus a
  header tally + fallback count — for review and to improve the catalog / feed `pptx-learn`.
  Schema in `slide-templates.md`; the preview writes it in code (implemented + tested).
  Supersedes free-form's ad-hoc `.layout-log.md`.

### Changed

- **`concept-breakdown` carries a per-concept icon by default.** A concept card is anchored
  by a content-matched §17 line-art glyph (≈0.44 in, different per card, renderer-chosen —
  the source has no per-item image), above its label + body — the plain iconless card grid is
  now the *fallback* (dense 5–6-item sets). Fixes real strict slides that rendered as flat
  iconless cards. Added the strict recipe (§7.2.1, ref-S8 geometry) and drew the icon in the
  preview.
- **Hard rule: any source `![]()` image disqualifies `concept-breakdown`** (→ `figures` /
  `content+image` / `content+cards+image`) — its icons are renderer-added, never source
  pictures. Encoded in the Match, discriminator walk, and disambiguation table.
- **Card content is balanced within the card (`DISTRIBUTION-09`).** Uniform equal cards in a
  grid are correct (a concept grid *should* be a regular grid), but content must sit balanced
  (vertically centred / icon-top with even padding), never crammed at the top with a dead
  void below — the "items spread out in oversized boxes" defect. The preview now fills the
  region with uniform cards and centres their content.
- **Preview classifier aligned to the catalog** — enumeration threshold lowered to ≥2,
  `single-point` handled (one labeled item → card, not a bullet), and the no-image rule for
  concept-breakdown applied.

## [0.17.1] — 2026-07-10

### Fixed

- **The render's style-suffixed output guarantee is now stated in the orchestrator's Step 8,
  not only in the skill.** Renders are meant to write `output/final.<style>.pptx`
  (`final.strict.pptx`, `final.free-form.pptx`) so strict and free-form decks of the same Talk
  coexist, with the latest copied to a canonical `final.pptx` — but that rule lived only in
  `md-to-deck`'s spec, and real Cowork renders were writing `final.pptx` directly (styles
  overwriting each other). Step 8 (the render driver) now names the guarantee explicitly:
  never render straight to `final.pptx`, always the suffixed name; a render that produced only
  `final.pptx` bypassed the rule and is a defect.

## [0.17.0] — 2026-07-10

### Changed

- **The stub now opens with an imperative that *forces* the spec to load and the workflow to
  start — fixing the "spec never loads" failure at its root.** The `@`-import is lazy: the
  stub being auto-loaded doesn't make the agent *act* on it, so descriptive load instructions
  could just sit there while the agent answered the user's prompt with no spec. The stub's
  first content is now a three-step instruction to **execute now**: (1) ensure
  `orchestrator.md` is loaded — Read it directly if the `@`-import didn't resolve (Cowork),
  with a locate-the-install fallback; (2) **execute the spec's Step 0** (introduce Talksmith,
  show the workflow, ask new-vs-resume) as the first response; (3) only then handle the user's
  message, folding it into Step 1. The stub holds *only* this bootstrap trigger — all evolving
  behavior lives in `orchestrator.md`, which reloads fresh every session, so the stub stays
  stable and re-init stays a once-ever action.
- **`/talksmith:init` is a clean one-time stub drop again.** It writes `CLAUDE.md` (with a
  locate-the-install fallback if `${CLAUDE_PLUGIN_ROOT}` is unset) and finishes by telling the
  user to close the session and reopen — the freshly-loaded stub then forces the load + Step 0.
  Init no longer loads the spec or runs the workflow itself (that was replicating what the
  reopen already does). **Re-run `/talksmith:init`** to pick up the new forcing stub.

## [0.15.0] — 2026-07-10

### Fixed

- **The orchestrator spec now loads reliably in Cowork, not just the CLI.** The stub relied
  on the `@${CLAUDE_PLUGIN_ROOT}/orchestrator.md` import to pull the full spec into context —
  but that `@`-import is a Claude Code **CLI** convention that **Cowork does not expand**, so
  the stub loaded while the actual operating spec silently did not, and Talksmith ran with no
  workflow knowledge. Worse, the old stub misread this as a broken install and told the user
  to reinstall. The load directive now: keeps the import for the CLI, **tells the agent not
  to assume it resolved**, has it **verify the spec is in context and Read
  `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` explicitly if not** (with a locate-the-install
  fallback), and only surfaces a reinstall message if the file is genuinely unfindable.
  - **Action required: re-run `/talksmith:init`** in each working directory to pick up the
    robust load directive (Cowork users especially).

## [0.14.2] — 2026-07-10

### Changed

- **Stub's presenter section is now a link, not an inline how-to.** Replaced the five-step
  "How to use Talksmith" in `talksmith-orch.md` with a short *"Learn more"* pointer to the
  project repo (`https://github.com/veigap/talksmith`) — one place to keep current instead
  of a copy that drifts. Re-running `/talksmith:init` is optional (no contract change).

## [0.14.1] — 2026-07-10

### Changed

- **Talksmith now introduces itself and takes the lead on turn one, no matter what the
  user types first.** A hard, non-negotiable session-start directive: whatever the opening
  message is (a topic, a direct "build me a deck" request, a pasted file, an unrelated
  question, or a bare greeting), the agent's first response is the Step 0 self-introduction
  + the new-vs-resume ask, then it drives the conversation into the workflow — never
  answering the opening message on its own terms and skipping the intro, never sitting idle
  waiting to be told to begin. Any signal in the opening message is folded into Step 1, not
  dropped. Enforced in **both** the working-directory stub (`talksmith-orch.md`) and the
  orchestrator's Step 0. The stub was also restructured to lead with its directives (load
  the spec; introduce-first), then context, then a short **"How to use Talksmith"** for a
  first-time presenter.
  - **Action required: re-run `/talksmith:init`** in each Talksmith working directory to
    pick up the stricter stub (the command always overwrites). The orchestrator half
    propagates automatically on next session reload.

## [0.13.0] — 2026-07-10

### Added

- **`slide-templates.md` now has a precise signal glossary, discriminator order, and worked
  matching examples** so classification is deterministic across modes — each signal
  (`labeled_items`, `is_ordered`, `has_table`, `one_claim`, …) has an exact detection rule,
  and ~10 Markdown→template examples show the decision (including the tricky ties:
  concept-breakdown vs process, card-row vs icon-list, figures vs concept-breakdown,
  table→comparison vs card-grid).
- **New `single-point` template** for the very common "lead + exactly one labeled point"
  shape — rendered as a card or callout, never a lone bullet.

### Fixed

- **Closed five real classification gaps found by dry-running the full security deck
  (74 slides) through the catalog** (a debugging pass, no live render): (1) the `≥3
  labeled-items` threshold left 1–2-item slides undefined — 40/74 fell to `fallback`;
  lowered to `≥2` and added `single-point` for 1 item, so **all 74 now classify** into a
  real template; (2) `concept-breakdown` Match said "3–N" while Format said "2–4 cards" —
  reconciled to `2–N`; (3) section dividers marked `〔divisor〕`/`〔Backup〕` at H2 (not H1)
  were misread as content — the divider signal now recognizes the marker; (4) `pipe-table →
  comparison` was too eager — a table is `comparison` only for two comparable value-columns,
  else `concept-breakdown`; (5) `statement` was too narrow — now allows a short reveal /
  counter-point (myth→reality slides).

## [0.12.0] — 2026-07-10

### Added

- **`visual-guidance.md` — the generic visualization floor.** A new shared doc holding the
  *medium-agnostic* good-design principles (figure/ground, one hierarchy, alignment,
  whitespace, signal-over-noise, structure-over-bullets) **and** the hard
  "must-never-happen" defects (text/image overlap, off-slide bleed, truncation, occlusion,
  image distortion, illegible contrast, sub-legibility type, dropped content). Referenced by
  every mode at GENERATE (honor it) and FEEDBACK (hard violations are blocking). It is the
  most generic layer; `slide-design.md` *implements* it as per-slide checks and must not
  contradict it.
- **`preview` is now a first-class render style.** Added `config/pptx-styles/preview/pptx-prompt.md`
  and a row in the styles table; `preview` is selected like any style (`style: preview`, with
  the legacy `preview: true` accepted as an alias) and differs only in *substrate* — a code
  wireframe (Pillow), no base-template, no native `pptx`, its own critique loop. No longer a
  special-case exception branch.

### Changed

- **Renamed `slide-quality.md` → `slide-design.md`** and reframed it as *the mandate for the
  visual transformation of a slide* that the critique loop exists to enforce (not just a
  "quality bar"). All references updated.
- **Resolved the remaining strict-spec duplication.** The design-level layout guidance that
  was inline in strict §7.3/§7.6/§8/§10/§11 (card-row-vs-list chooser, labeled-enumeration
  invariant, callout pink-vs-blue intent, cards-over-bullets, pipe-table→card mapping) now
  lives once in `slide-templates.md`; strict keeps only its EMU realizations and references
  the catalog. Global rendering principles were centralized too — the no-dead-title-gap rule
  became `DISTRIBUTION-08`; one-line-title/aspect reference the shared floor.

## [0.11.0] — 2026-07-10

### Added

- **Shared slide-template catalog — all three render modes now build to the same layout
  vocabulary.** New [`config/pptx-styles/slide-templates.md`](config/pptx-styles/slide-templates.md)
  is the single home for *which template a slide is, when it applies, and the prescriptive
  format it must take* — cover, agenda, statement, concept-breakdown, card-row, icon-list,
  process, comparison, stat, figures, image-grid, content+image, content+cards+image,
  code-example, callout, closing-cta/hero, and a fallback. Distilled from three real
  hand-built decks (131 slides, **0 bullet lists** — every enumeration is cards/panels).
  Each mode now **classifies every slide against the catalog at GENERATE and renders the
  matched template**, falling back to its default only when nothing fits. Previously this
  vocabulary lived only in strict's prose; free-form ("renderer decides") and the preview
  (which flattened everything to bullets) had no notion of it — so concept sets shipped as
  bullet lists. The universal invariant — **labeled enumerations render as cards, never
  plain bullets** — is now enforced at GENERATE in every mode and walked in FEEDBACK.
- **The preview wireframe is template-aware.** `build_preview.py` classifies each slide
  (`_classify`) and draws its template shape — cards, figures, content/image split, code
  block, statement, image-grid — instead of a single bullet-flattened layout.
- **The critique is template-aware.** New `TEMPLATE` category in
  [`slide-design.md`](config/pptx-styles/slide-design.md): FEEDBACK reviews each slide
  against its classified template's *Format*, not a generic look. Walked in every mode.
- **Speaker-notes coverage is now enforced, not just specified.** New
  `audit_notes_coverage.py` (shared CONTROL floor, all `.pptx` modes) fails the build if any
  `### Notes` block lands in an empty notes pane. Notes were load-bearing but nothing checked
  them, so a forgotten notes stage shipped silently.
- **Committed free-form cover/agenda builder (groundwork).** `skills/md-to-deck/freeform_deck.py`
  builds the free-form deck's fixed cover + agenda from `final.md` metadata into a from-scratch
  `python-pptx` `Presentation()` (which ships a default theme + slideMaster, so it imports into
  Keynote), plus the bundled `config/pptx-styles/free-form/cover-logo.png`. Standalone-tested;
  not yet wired into the free-form render flow (that spec rewrite is a separate change).

### Fixed

- **Title extraction no longer assumes Roboto Mono.** The shared `_extract_title` in
  `audit_block_coverage.py` (reused by the new notes audit) hardcoded `"Roboto Mono"`, stale
  since the Helvetica migration — it under-matched titles on every current deck, weakening the
  block- and notes-coverage audits. Now accepts Helvetica/Arial titles too.

### Changed

- **Layout guidance consolidated into the catalog, not duplicated.** Strict §13/§15.5 now
  reference `slide-templates.md` as authoritative for *when* a template applies (strict keeps
  only its exact EMU realizations + the `audit_layout_fit.py` gate); free-form §3 changed from
  "renderer decides freely" to "classify against the catalog first, design freely only on
  fallback" (logging the chosen template id to `.layout-log.md`).

## [0.10.3] — 2026-07-09

### Fixed

- **Strict/free-form base-template cover no longer fails its own audits.** The shipped
  `base-template.pptx` covers (and the strict agenda) were authored in **Roboto / Roboto
  Mono Medium** — which `audit_palette_fonts.py` forbids (system-fonts-only, because Roboto
  crashes Keynote import) while `audit_cover_fidelity.py` requires the render to *match* that
  cover. The two hard audits contradicted each other on the shipped asset, so no strict
  render could pass both. Rewrote the cover + agenda font runs to the fonts the §4.3 recipe
  already specifies — **Helvetica Bold** (title/subtitle) and **Helvetica** (author/date) —
  so template = spec recipe = allowed palette, and both audits now agree. (Strict template
  slides 3–15 are the deleted layout-reference zone and don't reach the render.)

## [0.10.2] — 2026-07-09

### Fixed

- **`convert.py` no longer leaks `<!-- ascii-source -->` blocks into slide bodies.** The
  HTML-comment stripper used a non-greedy `<!--.*?-->` regex that terminated at the first
  `-->` — but ASCII diagrams preserved inside `ascii-source` / `ascii-note` comments
  routinely contain `-->` / `===>` arrows, so the block closed early and its tail spilled
  onto the slide. Rewrote it line-based: inline comments are stripped per line, and a
  multi-line block runs until a line that is *only* the close marker `-->`, so arrows inside
  the ASCII can never close it early.

## [0.10.1] — 2026-07-09

### Changed

- **Separated two concerns that had been in one file.** `render-modes.md` was doing double
  duty — the per-format *pipeline config* (matrix + action definitions) *and* the *design
  quality bar* (the CONTENT / AESTHETIC / DISTRIBUTION / LAYOUT-CONFORMANCE practices). Split
  them: `render-modes.md` keeps the matrix + actions (how each format runs); the practice
  catalog + walk discipline + closing-report moved to a new **`slide-design.md`** (what a
  good slide looks like). The FEEDBACK action references the catalog. You can now tune the
  aesthetic bar without touching mode config, and vice versa.

## [0.10.0] — 2026-07-09

### Changed

- **Per-format render config centralized into one matrix — the source of all the drift is
  gone.** The per-format behavior (render substrate, CONTROL audits, FEEDBACK categories,
  cycle cap, deliverable) was duplicated across ~6 files (the rubric, SKILL's phase tables,
  README's phase table, each style spec, the orchestrator) and kept diverging. It now lives
  once in a **phase × format → action** matrix, with each *action* defined once (how it's
  performed). Renamed `config/pptx-styles/critique-rubric.md` → **`render-modes.md`** to
  reflect its role; every other doc now *references* the matrix instead of restating it.
  Changing a format is a one-cell edit.
- **Free-form is single-pass again — no automated critique.** The renderer designs freely
  and the presenter reviews after delivery (GENERATE → CONTROL, floor audits, done). The
  automated critique loop now lives only in `strict` (all four categories, ≤3 cycles); the
  throwaway `preview` keeps its own light ≤2-cycle content/aesthetic/distribution loop whose
  findings surface.

## [0.9.2] — 2026-07-09

### Fixed

- **Section goals (and narrative arc) no longer leak onto slides.** `**Goal of this
  section:**` is the author's note about a section's purpose — it belongs in the editable
  source + audit trail, never on the divider slide. `final.md` keeps it (by design), but
  `convert.py` was only stripping the working-meta bold labels (`Goal of this section` /
  `Narrative arc` / `Presenter feedback`) in draft/preview mode, so a real strict/free-form
  render spilled the goal text into the divider body. Now stripped in **every** mode.
- **Hard rule: the render authors from the `convert.py` intermediate, never re-parses
  `final.md`.** The root cause of both this and the "Sources + speaker notes in the slide
  body" bug was a renderer parsing `final.md` raw and looking for `### Notes` — which only
  exists after `convert.py` (which also drops `### Sources`, unwraps `### Content`, and
  removes working-meta). SKILL.md now states loudly that `final.md` is untouchable source
  and the intermediate is the only thing the renderer parses.

## [0.9.1] — 2026-07-09

### Fixed

- **Clarified the "no python-pptx" contradiction that made a correct free-form/strict render
  look forbidden.** The official `pptx` skill authors decks *by writing python-pptx from a
  working copy of `base-template.pptx`* — that is the mechanism, and free-form §1 / the
  "base template is mandatory" rule already require `Presentation(<base_template_path>)`. But
  SKILL.md's intro said, absolutely, "no python-pptx," contradicting that. Reworded so the
  rule reads correctly: driving the native skill's python-pptx-from-base-template workflow is
  required; what's forbidden is *bypassing* it (a blank `Presentation()` from scratch,
  reimplementing the theme, or another tool). A generator that starts from the base template
  and builds each slide per the visual spec is the correct render, not the anti-pattern.

## [0.9.0] — 2026-07-09

Milestone release consolidating this cycle's PPTX work (details in 0.4.0–0.8.2 below):
the optional **Step-5.5 draft preview** (committed code-only renderer `build_preview.py`
— numbered per-slide wireframes, no `.pptx`/`.pdf`, Cowork-independent); the shared,
**categorized critique rubric** (CONTENT / AESTHETIC / DISTRIBUTION / LAYOUT-CONFORMANCE)
selectable per mode, with free-form and preview gaining a real critique loop; the
strict-only **`pptx-learn`** skill that mines styling/positioning patterns from
hand-corrected decks into declarative conformance rules; live per-phase render progress
in every mode; per-mode output isolation; and two deep contradiction sweeps leaving the
render instructions internally consistent and runnable across all three modes.

## [0.8.2] — 2026-07-09

### Fixed

- **Second, deeper contradiction sweep of the PPTX docs.** Reconciled the last preview-audit
  contradiction (the rubric's "shared floor runs in every mode" + SKILL's "cover-fidelity runs
  in all modes" still implied preview ran deck-parsing audits — it produces no deck, so none
  run); gave the heavily-referenced **§15.5 layout-selection table an addressable anchor** (it
  was cited 20+ times but existed only as an unlabelled list item); and fixed a cluster of
  dangling cross-references — orchestrator's "Step 8 reverse pipeline" (repointed to
  pptx-merge/pptx-learn), free-form "§2.2"→"§2" cover placeholders, SKILL "strict §4–§20"→"§1–§20",
  the strict-centric §4.3 cover-slot label (now notes free-form §2 too), and the phantom
  "PNG companion for every SVG" prereq-row reference in illustrator.md + ascii-to-svg. Commands
  in every spec were re-verified against the scripts' actual CLIs — all correct.

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

- **Shared, categorized critique rubric** ([`config/pptx-styles/render-modes.md`](config/pptx-styles/render-modes.md)).
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
  ([`render_ascii.py`](skills/md-to-deck/render_ascii.py)), and re-renders only the
  slides that changed between review rounds via a content-addressed cache
  ([`preview_plan.py`](skills/md-to-deck/preview_plan.py)). It walks the same
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

- **md-to-deck section dividers.** The `final.md` → intermediate converter was letting a
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
`feedback-cycle`, `md-to-deck`) driving the 8-step workflow from raw sources to
`draft.md`, `final.md`, and an optional `.pptx`.
