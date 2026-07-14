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

## [0.53.0] — 2026-07-14

### Added

- **HTML deck: PDF export button.** New button in the top-right chrome (below the animations
  toggle) that opens the deck's Reveal `?print-pdf` view in a new tab — carrying the active
  theme and style — and auto-opens the browser's print dialog once Reveal signals the print
  layout is ready ("Save as PDF" from there). Falls back to same-tab navigation when pop-ups
  are blocked.
- **HTML deck: fullscreen button.** Below the PDF button; toggles the Fullscreen API on the
  whole document (Reveal's `F` shortcut still works), with a pure-CSS enter/exit icon swap.
- **HTML deck: six selectable styles.** `editorial` (serif, warm paper), `terminal`
  (monospace, green), `ocean` (Avenir, blue), `forest` (Gill Sans, green on warm paper),
  `sunset` (Futura, orange), and `business` — a corporate business-school look (inspired by
  iae.edu.ar): royal blue #1724A9 on clean white surfaces and **Montserrat**, vendored as an
  OFL variable woff2 so the deck stays self-contained — token-only overrides of fonts,
  colors, and backgrounds; layout
  is untouched. Each composes with the light/dark toggle. **Each style is its own CSS file**
  under `templates/html/styles/<name>.css`, discovered and inlined at build — add a style by
  adding a file. Selected from a small **picker popover** on the palette button (one entry per
  style, "default" resets) — a deliberate choice that sticks; no accidental cycling. **Selecting
  a style or theme also writes it into the URL** (`?deck-style=…&deck-theme=…`), so copying the
  address bar shares the exact look; defaults clear their param. Opening such a link applies it
  on load.

- **Viewer-actions documentation.** New README section "Presenting the HTML deck" — a compact
  table of everything a presenter can do (Reveal built-ins: navigation, overview, speaker view,
  fullscreen, `?print-pdf`; plus the Talksmith button cluster and its `?deck-theme=` /
  `?deck-style=` URL params). The `talksmith-intro` example talk gained two matching slides
  ("Presenting the HTML deck: shortcuts / the buttons") in its workflow section.

### Changed

- **Intro talk: presenter notes are now documentation.** All 29 slide notes in `talksmith-intro`
  were rewritten to go deep on the concept each slide presents — the mechanism behind the claim,
  what each number/artifact/command actually is, the trade-offs and the why — so the notes read
  as the full explanation the slide is a projection of, not stage directions.
- **Icons now follow the active accent.** Material icons are inlined as `currentColor` and
  tinted by CSS tokens, so the selectable styles (and any future palette change) recolor every
  icon; chip icons stay white on the accent disc.
- **Example talk: "Review is a loop" now renders as numbered steps.** Converted to the `process`
  template — real numbered chips (1/2/3) for the three feedback rounds — alongside the loop
  diagram, using process's new optional image slot. (The style reference still exercises both
  process variants; nothing was dropped.)

## [0.52.2] — 2026-07-14

### Changed

- **License is now MIT (permissive), consistent everywhere.** The `LICENSE` file was Unlicense
  while the plugin manifest declared MIT — reconciled to **MIT** across the `LICENSE` file,
  `README.md`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`. Use, modify, and
  distribute freely, including commercially.

## [0.52.1] — 2026-07-14

### Changed

- **Example talk (`talksmith-intro`).** Added a "One source, three outputs" slide after "What you
  end up with" — HTML deck / PowerPoint / PDF from the same `final.md` — with a note that the deck
  you're viewing is itself one of those outputs, rendered from its `draft.md`. Added a note to the
  "It's Markdown all the way down" slide clarifying the reverse pipeline is optional (only when you
  edit the deck outside the cycle). Re-rendered the sample.

## [0.52.0] — 2026-07-14

### Added

- **Animations on/off toggle in the HTML deck.** A discreet icon button below the light/dark toggle
  (top-right) turns the reveal animations off — every fragment shows at once and slide transitions
  are disabled — for viewers who prefer a static deck. Enabled by default; the choice persists in
  `localStorage`. Sequential reveal is also applied to `concept-breakdown` (the example's slide 5).

### Fixed

- **Renderer chrome labels are now language-aware.** The cover's author / last-modified lines, the
  `pros-cons` column headers, and the `quiz` answer label were hardcoded Spanish, so an English deck
  showed "Autor" / "Última modificación" / "Ventajas" / "Riesgos" / "Respuesta". They now localize
  from a new `deck.lang` field (default `en`; sourced from the profile's *Presentation language*).
  Spanish decks set `lang: "es"` and keep the Spanish chrome.

## [0.51.0] — 2026-07-14

### Added

- **Sequential reveal for enumeration slides.** A `stat`, `card-row`, `concept-breakdown`, or
  `icon-list` slide can carry `reveal: sequential` so its items appear **one at a time** in the HTML
  deck (Reveal fragments; the `.pptx` render is static and shows all at once). Fragments keep their
  layout space, so the content-fit still measures correctly.
- **Optional author hints in `draft.md`.** The Editor may — when it has a specific intent for a
  slide — write `<!-- template: <type> -->` (pin the slide type) or `<!-- reveal: sequential -->`
  under a slide's heading. Optional, never required. Polish copies them through to `final.md`
  verbatim, and the `md-to-deck` FILL honours them when mapping to `slide-model.json` (they are the
  only HTML comments read rather than dropped).

### Changed

- **Slide-template catalog reorganized into a two-level taxonomy.** `slide-templates.md` now groups
  the templates into **7 concept families** (labeled-set, two-groups, ordered-sequence, metrics,
  one-claim, visual, verbatim, + frame) with a top-of-catalog overview showing, per family, the one
  signal that picks the sub-category. **No template ids, Match rules, or disambiguators changed** —
  pure clarity; classification is byte-identical.
- **The Editor drafts with the slide taxonomy in mind.** [`editor.md`](agents/editor.md) Step 4 now
  tells the Editor to shape each slide's content to a concept family (a parallel set → cards, metrics
  → numbers, one claim → a line, …), reinforcing the cards-not-bullets invariant from the first draft.

## [0.50.1] — 2026-07-14

### Fixed

- **Per-skill consistency audit — SKILL.md docs reconciled with their scripts.**
  - **polish-ascii:** implemented the documented **exit-3 stale-plan guard** (it was documented but
    missing) — `cleanup`/`apply` now abort, writing nothing, if `final.md` changed since `scan` so a
    block's line numbers no longer bracket an ASCII fence; and out-of-range line numbers now exit `2`
    as documented (was exiting `1`). Closes a silent-corruption path.
  - **pptx-extract:** removed a self-contradiction in the description (claimed both "stdlib, no
    python-pptx" **and** "requires python-pptx" — it uses python-pptx); corrected "four-tier" →
    "five-tier" template-detection ladder; and dropped the stale "`--stage-new`" condition on
    `staging/` (staging is always on).
  - **ascii-to-svg:** fixed three step cross-references (the Return step is 9, not 8) and a report
    field name (`png_companion` → `png_critique`).
  - **md-to-deck:** the html-strict progress checklist no longer shows a review/fix cycle (it's a
    single-pass, no-critique render).
  - **feedback-cycle:** documented the `--allow-empty-tags` flag.
  - **orchestrator/schemas:** removed the phantom `convert.py` references and the stale html-strict
    "critique loop" prose; the live-view dispatch now correctly describes FILL → mechanical render.
  - ingest, pptx-diff, pptx-merge, pptx-learn audited clean.

## [0.50.0] — 2026-07-14

### Changed

- **Render now runs right after Polish, and is renamed from "Render PPTX" to just "Render."** The
  workflow order is now Polish (6) → **Render (7, optional)** → **Learnings (8, mandatory)**: the
  presenter gets their deck immediately after polishing, and the cross-Talk learnings/promotion
  wrap-up happens last. The step is called "Render" because it produces a PowerPoint *or* a
  shareable HTML/Reveal.js deck — not only `.pptx`. Renumbered and renamed consistently across the
  orchestrator spec, the schemas, agent/skill docs, `config/`, the README, the plugin description,
  and the workflow diagram (`docs/workflow.svg`/`.png`). No session-start contract change — existing
  working directories pick this up on their next session reload (no re-init needed).

### Removed

- **Dead code in the HTML renderer.** Retired the orphaned `agenda` template (`agenda.j2` +
  its `.agenda/.agrow/.agn` CSS — superseded by `section-agenda`), the never-emitted `.fig` and
  `.stitle.ag` CSS rules, and the unused code-syntax classes (`.codebox .kw/.st/.cm` + their
  `--kw/--st/--cm` tokens — the code template emits escaped raw lines, so they never applied). No
  visual change; the style reference still renders every live template with zero fallback.

## [0.50.0] — 2026-07-14

### Added

- **Quiz reveal upgrade.** The `quiz` slide can now name the `correct` choice (by option text,
  1-based index, or letter) — on next-nav that choice highlights (accent fill + check) *in sync*
  with the answer, via a Reveal *custom* fragment. It also takes an optional `image` (shown at the
  right, sized to its own aspect — never cropped) and an `answer_label` (defaults to "Respuesta").
  Choices now render as cards. Documented in `schemas/slide-model.md` and the catalog.

- **Example talk fixture — Talksmith, built with Talksmith.** Added
  [`tests/examples/talksmith-intro/`](tests/examples/talksmith-intro/): a complete, realistic
  `draft.md` for a ~40-min intro talk *about* Talksmith (problem framing → what it is → the workflow
  → behind the scenes → getting started). It follows the full schema (including a `[open]`/`[closed]`
  feedback audit trail), exercises nearly every slide type, and carries three render-driving ASCII
  diagrams plus a real in-Claude screenshot (also shown at the top of the README). Its **rendered
  HTML deck is committed** (`output/html/index.html`, produced by the `md-to-deck` FILL +
  `build_html.py` render from `output/slide-model.json`) and linked from the README as the on-ramp
  for new users.

### Changed

- **Style reference rebuilt as a self-documenting English deck.** Every slide's copy now explains
  the template it demonstrates; the deck is divided into template *families* by `section-agenda`
  separators, opens with an explainer slide stating its purpose, and demos the upgraded quiz
  (correct-highlight + right-side image). Still one example per template plus the layout edge cases
  (2/3/4/6 cards, long title/body, 2/3-col comparison, the six highlight kinds).

- **Docs overhaul — README is now usage-first.** Rewrote the README lean (~300 → ~120 lines):
  a copy-paste **Quickstart** up top, a single rendered **workflow diagram**
  ([`docs/workflow.png`](docs/workflow.png), authored as [`docs/workflow.svg`](docs/workflow.svg))
  as the one process explanation — the duplicate four-phase mini-diagram is gone — and a
  **reference-artifacts table** linking a real example or canonical shape for every artifact
  (including the committed rendered deck and example `final.md` / `slide-model.json`). Moved the
  deep material out of the README into `docs/`: the four-phase method + "LLM wiki" philosophy →
  [`docs/methodology.md`](docs/methodology.md), the five roles + render pipeline →
  [`docs/roles.md`](docs/roles.md), the reverse pipeline → [`docs/reverse-pipeline.md`](docs/reverse-pipeline.md).

- **Workflow steps 7 and 8 reordered.** **Render** is now the optional **Step 7** (a `.pptx` *or* a
  shareable HTML deck), and **Learnings** promotion is the mandatory final **Step 8** — you deliver
  the talk, then promote what recurred. Propagated across the orchestrator, agents, schemas, and
  docs, and the workflow diagram was regenerated to match.

- **Institution logo is now repo-configured.** Drop a `config/logo.*` into your subject repo at
  setup and every rendered deck (HTML + PPTX) uses it; with none configured, decks fall back to a
  neutral placeholder. The HTML renderer's resolution order is now frontmatter `logo:` → the Talk's
  `images/logo.*` → the repo's `config/logo.*` → bundled placeholder → institution text. The
  strict/free-form PPTX specs now treat the logo *slot* as fixed and the *image* as repo-supplied.

### Fixed

- **Full-bleed HTML slides no longer overflow.** `quote`, `statement`, and `closing-hero` emit their
  own full-bleed `.stage cover` and were skipping the content fit pass (which only ran on
  `stage()`-macro slides), so long text overflowed. Added a `fitCover()` shrink-to-fit pass for them
  (`html_style.py`), and right-sized the oversized closing-hero title (`.qa` 16cqw → 9cqw, with more
  margin) so it reads proportionate to the rest of the deck.

### Removed

- **Institution branding removed from the plugin.** The Universidad Austral logo no longer ships:
  deleted the bundled `cover-logo.png` and replaced the baked-in `image-1-1.png` in all three
  `.pptx` templates (strict `template.pptx` + `base-template.pptx`, free-form `base-template.pptx`)
  with a neutral unbranded placeholder (`config/pptx-styles/placeholder-logo.png`). Genericized the
  remaining Austral/IAE example text in the schemas and profile placeholders. *(The strict
  `template-previews/base-template/slide-01.png` still shows the old logo visually — regenerating it
  needs a PPTX→PNG renderer and is a follow-up.)*

## [0.48.0] — 2026-07-14

### Added

- **`quiz` slide type (HTML).** A "question → answer" slide for check-for-understanding decks:
  the question and its optional lettered choices (A/B/C/D) show immediately, and the answer panel
  is revealed on the *next* navigation using Reveal.js's own `fade-up` fragment animation — so the
  audience can think before the reveal. The answer sits in a red-accented light-pink panel with a
  "RESPUESTA" label and an optional one-line explanation; space for it is reserved up front so the
  question never jumps. Fields: `question`, `answer` (required), `title`/`options`/`explanation`
  (optional). In `.pptx` (static, no reveal) the answer renders visible in place.

### Changed

- **Deck navigation cluster.** The nav arrows are smaller and centered along the bottom with the
  page number between them (`‹ 12 / 74 ›`) instead of the corner cross. The whole cluster
  auto-hides: it only appears while the pointer is moving and fades out after a short idle.
- **README.** Added *"A knowledge base in the Karpathy sense"* — frames Talksmith's corpus / memory /
  learnings / knowledge-library as an instance of Karpathy's compilation-over-retrieval **LLM wiki**
  (raw sources → synthesized wiki → schema; ingest / query / lint), and notes where it diverges.

## [0.47.0] — 2026-07-14

### Added

- **Highlight kinds.** A `highlights` entry can carry a `kind` — `takeaway` (default), `important`,
  `definition`, `example`, `quote`, or `note` — each with its own accent colour + icon (quote renders
  italic). The **fill picks the kind** (a semantic choice, like a callout's tone); documented in
  `schemas/slide-model.md`. The style reference demos all six.
- **`quiz` template.** A question with optional lettered choices shown up front and the answer
  revealed on next-nav (a Reveal fragment) — for the vote-first "rompemitos" dynamic.

## [0.46.3] — 2026-07-14

### Added

- **Auto-hiding nav.** The nav arrows and slide number now sit centered along the bottom and fade
  out when idle, reappearing on pointer activity (a small idle-UI script toggles `html.deck-ui`).

## [0.46.2] — 2026-07-14

### Fixed

- **Colon lead-in labels render bold.** The reset neutralizes the default `<b>`, so a fact's label
  (`.cifacts b`, e.g. **PII**: …) showed unbolded while elements with an explicit weight didn't. Fact
  labels now carry an explicit weight + dark ink, so the `Label:` lead-in reads as emphasized.

### Changed

- **The image-top caption uses the same soft red-accent box as a `highlight`** — consistent emphasis
  styling for the text under an `image-top` `content+image` slide.

## [0.46.1] — 2026-07-14

### Fixed

- **icon-list label-only rows now align the icon with the text.** A row with no `body` (a bare
  label, e.g. "Sin NDA" / "No hubo hackers") kept the icon top-aligned and a dangling label margin,
  so the icon sat higher than its single line of text. Such rows now center the icon vertically.

## [0.46.0] — 2026-07-14

### Added

- **Highlights band.** Any content slide may carry an optional `highlights` list (one or more
  emphasized takeaways / comments), rendered in a soft red-accent band under the body. Each entry
  is a string or `{label,body}`. It's the home for a key line — e.g. the takeaway a diagram builds
  to — so content is never dropped for being "redundant."
- **Explicit labeled lines.** `content-image` `facts` (and `highlights`) accept `{label,body}`; the
  label renders bold before a colon. **The fill detects the label** (splits `Label: rest`) — the
  renderer no longer parses the colon.

### Changed

- **`schemas/slide-model.md` documents the "never drop content" rule** (every source line is
  translated — as a field, card, fact, or highlight) and the labeled-line / highlights contracts.
- **Renderer stays mechanical:** removed the `emphlabel` colon-parsing heuristic from `html_style`
  (that detection is the fill's job); the render is pure field-mapping.
- The style reference now exercises highlights, labeled facts, and a **tall image** (to catch the
  content-image crop regression).

## [0.45.5] — 2026-07-14

### Removed

- **The html-strict render has no critique/FEEDBACK cycle.** `html-strict` is now a single-pass
  GENERATE — the deck is produced and the presenter reviews it (resolving anything by editing the
  source, which re-fills the model, then re-rendering). Updated the render-modes matrix, the
  html-strict spec, and SKILL.md.

## [0.45.4] — 2026-07-14

### Fixed

- **Content images are no longer cropped.** A real image was forced to `height:100%` inside a fixed
  16:9 container, which defeated `object-fit:contain` and clipped the bottom (e.g. the diagram
  captions on "PII vs. Personal Data" and "Las dos caras"). Real images now size to their own
  aspect ratio (`height:auto`, capped by `max-height`) and always show in full.

## [0.45.3] — 2026-07-14

### Changed

- **The section pill on content slides is 30% smaller and sits closer to the title** (`1.8cqw` →
  `1.26cqw`; title top margin `2.4cqw` → `1.1cqw`) — a quieter section tag tight above the title.

## [0.45.2] — 2026-07-13

### Fixed

- **`content+image` `image-top` no longer clips the caption.** The image band used `cqh`, which is
  unreliable under an inline-size container, so a two-line caption overflowed the slide. The band is
  now width-relative (`cqw`, like every other component), keeping image and caption in view.

## [0.45.1] — 2026-07-13

### Fixed

- **No-repeat icons now holds for unmatched labels too.** A label that content-matched nothing fell
  to the same default icon (`bolt`) without deduping, so e.g. two negative sentences on one slide
  shared an icon. Unmatched items now draw from a distinct neutral fallback pool.

## [0.45.0] — 2026-07-13

### Added

- **Icons never repeat within a slide.** The renderer content-matches a distinct icon to each item
  of an icon-bearing template and won't reuse one already placed on that slide. The **fill may also
  suggest** a per-item `icon` (a Material Symbols name); suggestions are honoured and reserved first.

### Changed

- **Emoji removal is a FILL rule, not a render transform** (documented in `schemas/slide-model.md`
  alongside the rest of the FILL decomposition contract): when a slide gets an icon-bearing
  template, the fill strips leading/inline emoji from its labels/bodies — the matched icon stands
  in for the emoji.

### Fixed

- **`comparison` no longer leaves an empty 3rd column** — it used a hard-coded 3-column grid; now it
  uses the actual number of columns, so a 2-column comparison fills the width.
- **`content+image` `image-top`** — the caption under the image now sits in a soft (non-shouty)
  highlight box.

## [0.44.0] — 2026-07-13

### Changed

- **PPTX now authors from the shared `slide-model.json`**, the same structured model the HTML
  render uses — the FILL step (LLM decomposition of `final.md`) replaces the `convert.py` prose
  intermediate, so a slide looks the same in HTML and PPTX. The template per slide is decided in
  FILL; there is no separate per-render template log.
- **The CONTROL audits validate against `slide-model.json`** instead of re-parsing `final.md`:
  `block_coverage`, `notes_coverage`, `icon_coverage`, and `layout_fit` now read the model's given
  `template` + fields (each takes `slide-model.json` as its first argument). This removes the
  brittle markdown re-parsing they carried.
- **Agenda / roadmap items are clickable** — each section row deep-links to that section's slide
  (Reveal anchor navigation).

### Fixed

- **`content+image` `image-top` layout** — the image now fills a prominent top band with the text
  beneath, instead of a tiny centered graphic.

### Removed

- **`convert.py`** — the markdown→prose pre-processor for the PPTX path; superseded by the FILL
  step producing `slide-model.json`.

## [0.43.0] — 2026-07-13

### Changed

- **The HTML render is now model-driven, not parser-driven.** `build_html.py` renders from
  `slide-model.json` (the LLM-filled structured model — [`schemas/slide-model.md`](schemas/slide-model.md)):
  `html_style.render_model_slide` maps each slide's fields onto its Jinja template. **All
  classification and information-breakdown moved out of regex and into the LLM fill step** in the
  `md-to-deck` skill, which decomposes `final.md` into per-slide `{template, …fields…, notes}`. The
  same model is the shared IR for the PPTX renderer. The `md-to-deck` skill and the html-strict spec
  now document the two-step **FILL → RENDER** flow.
- **New `content+image` `image-top` layout** — image on top, short text below (a model `layout` field).

### Removed

- **The regex classifier/parser is gone** — `slide_model.py` (`_classify`, `_parse_unit`, the metric/
  anaphora/marker heuristics) and `curate.py` (marker recovery) were deleted; the renderer no longer
  parses markdown. The brittle per-edge-case heuristics they accreted are superseded by the LLM fill
  step against a fixed field contract.

## [0.42.0] — 2026-07-13

### Added

- **`schemas/slide-model.md` — the structured slide-model contract.** Defines `slide-model.json`,
  the intermediate representation between `final.md` and the renderers: a deck object plus one
  object per slide carrying its `template` and the **fields that template requires** (e.g. `stat`
  → `stats:[{value,caption}]`; `concept-breakdown` → `cards:[{label,body}]`). Groundwork for
  moving classification + information-breakdown out of brittle regex (`slide_model.py`) and into an
  LLM decomposition step in the `md-to-deck` skill, with the HTML and PPTX renderers reading fields
  mechanically. Schema only in this release; the fill step and renderer rewiring follow.

## [0.41.0] — 2026-07-13

### Added

- **Stat slides are auto-detected.** A slide whose payload is standalone metrics — number
  bullets (`$4.44M`, `$670K`) or metric-labeled items (`**97%** …`) — now renders as a `stat`
  slide (big numbers + captions) instead of being hijacked into `content+image` by a stray graphic
  or flattened into a card grid. A bare integer (a year, a count) is deliberately *not* treated as
  a metric.

## [0.40.0] — 2026-07-13

### Added

- **Short anaphora / unlabeled enumerations now render as an `icon-list`** instead of falling to
  `fallback`. A slide that is 2–5 short parallel lines under a title (no labels, images or code —
  e.g. "No hubo hackers. No hubo malware. No hubo intrusión.") becomes one icon row per line. A
  line that merely repeats the slide title is dropped, so a title echoed by its first line no
  longer shows twice.
- **The style-reference exercises the section separator** (roadmap) and a plain sub-opener divider,
  so both are covered by the committed visual test.

### Fixed

- **`content+image` no longer drops content.** It rendered only the first two body lines; a slide
  with several stat lines beside an image silently lost the rest. Now the first line leads and
  every remaining fact renders beneath it.

### Changed

- **Per-template rationale lives once in `slide-templates.md`.** The duplicated `_WHY` table in
  code is gone; the html-strict decision log records the chosen template, raw signals, and review
  flags, and points to the catalog for the "why."

## [0.39.0] — 2026-07-13

### Added

- **`curate.py` — deterministic source normalization for `draft.md` / `final.md`.** Repairs
  authoring defects that make a slide render oddly, without changing wording. Today it recovers
  **ordered lists whose `2.`/`3.` markers were dropped** (`1. first` + bare continuation lines →
  a uniform numbered list). Run it on the *source* so `draft.md` stays the single source of truth
  (`python3 curate.py talks/<Talk>/draft.md`; `--check` to preview); idempotent.
- **Dedicated section-separator layout** (`section-agenda.j2`): the numbered section roadmap on
  the left, the current section as a big number + title on the right — replacing the plain
  re-shown agenda. Shown at each section start with the active section accented.

### Changed

- **Theme toggle is now a single discreet icon** (moon in Light, sun in Dark) in place of the
  Light / Dark button pair — same behaviour (persisted, `?deck-theme=`), quieter chrome.
- **Cover splits the `presentation:` frontmatter line** into a large title + an institution
  subtitle (on the em/en-dash), instead of cramming both into one heading.

### Removed

- **The standalone `# Agenda` slide is dropped** — the roadmap re-shows at every section start
  (the dedicated separator above), so a separate agenda slide added nothing. Supersedes the
  0.37.0 fix that re-populated it.

### Fixed

- **Authored duplicate title-page slides are dropped** (`## Portada` / `Cover` / `Título…`): the
  cover is synthesized from frontmatter, so a second one authored inside a section is redundant.
- **A numbered step now ends on a blank line** — a trailing pull-quote or paragraph after a list
  stays its own block instead of gluing onto the last item.

## [0.38.0] — 2026-07-13

### Added

- **Runtime Light / Dark theme toggle** in the HTML deck — a switcher (top-right, persisted in
  `localStorage`, also `?deck-theme=dark`). Themes are token overrides on our own component CSS
  (Reveal's stock themes don't restyle our cards/callouts), so a new theme is a
  `:root[data-deck-theme="<name>"]` block in `theme.css` + a button. Made pill/callout/code/card
  colors theme-aware so the dark theme reads correctly.

## [0.37.0] — 2026-07-13

### Fixed

- **HTML cover shows a real institution logo**, not a 3-letter text stand-in. Resolution order:
  frontmatter `logo:` → the Talk's `images/logo|cover-logo.*` → the bundled institution logo →
  text initials only if no image is found (embedded self-contained).
- **The `# Agenda` slide renders the actual agenda list again** (numbered sections), not an empty
  "Agenda" title — the `nt == "agenda"` case had been dropped in the section-enrichment refactor.

## [0.36.1] — 2026-07-13

### Fixed

- **Debug audit of the html-strict path (spec vs code):** the `html-strict` spec + the
  `render-modes` `html-render` action def said the HTML deck renders in Helvetica/Courier and
  omitted Reveal/Jinja/notes/PDF — corrected to IBM Plex Sans/Mono, the Reveal.js shell, per-type
  Jinja templates, catalog-matched icons, and softened the overstated "§7/§8/§9 EMU geometry"
  claim (HTML approximates the shapes in CSS). Small cover fix: the class line no longer hugs a
  long multi-line title.

## [0.36.0] — 2026-07-13

### Changed

- **`md-to-deck/SKILL.md` fully rewritten** so the three render modes are peers: **Path A —
  native `.pptx`** (`pptx-strict`/`pptx-free-form`, via the official pptx skill, Cowork-only) and
  **Path B — `html-strict`** (code-rendered HTML/Reveal.js, Cowork-independent). Consolidated the
  audit suite into one CONTROL list (marking floor vs strict-only), fixed all remaining stale IDs,
  removed the preview/incremental-cache leftovers and the pptx-only framing at the top; 431 → 220
  lines. Orchestrator section references realigned.

## [0.35.1] — 2026-07-13

### Fixed

- **Debug pass on `md-to-deck/SKILL.md`**: removed a duplicate `html/` output-tree entry; fixed
  stale `final.strict.`/`final.free-form.` and `.critique/strict|free-form/` names to the
  `pptx-strict`/`pptx-free-form` IDs; corrected the `html-strict` output row (it writes
  `output/html/`, not a separate `draft-preview/`); dropped the false "N changed slides (M reused)"
  incremental-cache claim (build_html renders the whole deck); retitled the skill and the Step-8
  entry away from "PowerPoint" since it also renders HTML; fixed a mislinked `build_html.py` ref.

## [0.35.0] — 2026-07-13

### Added

- **Two more slide types: `big-number` and `pros-cons`.** `big-number` is a single hero metric
  (vs the `stat` grid); `pros-cons` is two colour-coded columns (blue check = pro, pink ×= con).
  Author-directed, documented in `slide-templates.md`, and added to the reference deck.

## [0.34.0] — 2026-07-13

### Added

- **Two new slide types (Gamma-inspired): `quote` and `timeline`.** `quote` is a full-bleed
  pull-quote with attribution (distinct from `statement`, which is a claim in the presenter's
  voice); `timeline` is a vertical dated-milestone rail (distinct from `process` steps). Both are
  author-directed via `<!-- template: X -->`, documented in `slide-templates.md`, and added to
  the reference deck.

## [0.33.0] — 2026-07-13

### Changed

- **The HTML deck uses IBM Plex Sans + IBM Plex Mono** (vendored woff2, inlined as @font-face
  data-URIs so the deck stays offline) — a distinctive, editorial superfamily in place of
  Helvetica/Courier. The native `.pptx` styles are unchanged (Helvetica/Courier).

## [0.32.0] — 2026-07-13

### Changed

- **Three render modes, renamed and consolidated: `pptx-strict`, `pptx-free-form`, `html-strict`.**
  The style folders (`config/pptx-styles/strict|free-form|html`) and every path/ID reference were
  renamed accordingly (prose adjectives like "strict styling" unchanged). Step 8 offers these three.
- **`preview` is removed as a separate concept.** The code-rendered **`html-strict`** deck now
  serves both roles: the orchestrator auto-renders it from the in-progress `draft.md` after the
  first complete draft and keeps it in sync on every review (the **live view**, `--draft`), and it
  renders `final.md` as the Step-8 deliverable — one renderer, one output (`output/html/index.html`).
  Step 5.5 is now "Live HTML view"; the `preview/` style folder is deleted.

### Fixed

- Repaired references that pointed at the pre-rename `config/pptx-styles/strict/…` path and the
  pre-move `audit_*.py` names across agents, ascii-to-svg, pptx-learn, and the audits themselves.

## [0.31.0] — 2026-07-13

### Changed

- **Section dividers are redesigned** — a red monospace section number (`01`) with an accent
  rule over the large section title, instead of a bare centred title.

## [0.30.1] — 2026-07-13

### Changed

- Section label (pill) is smaller and less rounded — a subtle tag, not a big pill.

## [0.30.0] — 2026-07-13

### Added

- **Every slide is enriched with the section it belongs to, and shows it** — a pill on content
  slides, a red eyebrow on full-bleed statement/hero slides. The section is tracked per slide in
  `build_html` (from the agenda when present, else each divider title). Statement slides read as
  more editorial for it.
- **Numbered steps can carry an intro lead** (the `process` template renders `body[0]` above the
  steps); added a "Steps · con intro" fixture.

### Changed

- **Spacing + positioning polish (HTML):** the content region is a flex column with a gap, so a
  lead line no longer crowds the cards/steps below it; numbered-step chips are smaller and
  outlined (not filled); content sits in the upper third rather than dead-centre so sparse slides
  hug the title.

## [0.29.2] — 2026-07-13

### Added

- **Test fixture now exercises the plain numbered-steps and styled-fallback render paths** — two
  slides added to `tests/skills/md-to-deck/final.md` (a plain `1.`…`4.` numbered list → vertical
  steps, and a lead + point-panels fallback), so `style-reference.html` covers every slide type.

## [0.29.1] — 2026-07-13

### Changed

- **The seven CONTROL audits moved into `skills/md-to-deck/audits/` with simplified names**
  (`audit_layout_fit.py` → `audits/layout_fit.py`, etc.); the shared pptx machinery is imported
  as a sibling. All spec references updated. No behaviour change.

## [0.29.0] — 2026-07-13

### Changed

- **HTML slide markup moved into Jinja templates — one `.j2` per slide type.** `html_style.py`
  now computes each slide's structured context and renders `templates/html/<type>.j2`; the markup
  no longer lives in Python f-strings. Adds a **jinja2** dependency (`pip install jinja2`) for the
  HTML/preview render. Same visual output (verified against the test deck).

### Removed

- Deleted the dead `freeform_deck.py` (free-form cover/agenda groundwork that was never wired).

## [0.28.0] — 2026-07-13

### Added

- **Numbered lists render as steps.** A numbered list (≥2 `1. …` lines) is now recognised as an
  ordered step sequence: **labeled** steps (`1. **Label** — body`) render as the numbered card
  strip, **plain** steps (`1. Sentence`) as a clean vertical numbered list (red number chips).
  Previously these landed on `fallback`. A lone numbered line is left as prose (so it doesn't
  swallow the lines after it).

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
