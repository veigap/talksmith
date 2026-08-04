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
> Releases older than the last few are compacted into milestone bands below.

## [0.77.0] — 2026-08-04

### Added

- **`design` — a slide is a design filled with a style, chosen in that order.** Where the picture
  goes used to be answered in three different places: a `layout` field that existed on five
  templates and only when the slide carried an `image`, a parallel `aside` column with its own
  vocabulary for the same decision, and composition hard-coded inside those five templates. A
  template on neither list simply could not be composed — a card set could not have a diagram
  beside it. Now one `design` field divides the canvas and one `media` field says what goes in it,
  and **every content template accepts every design**, because the renderer's stage places the
  media and the template only emits content. Seven designs: `full` (default), `split-right` /
  `split-left` (half the canvas, media **contained** — a diagram or screenshot the audience
  reads), `banded` (media over a caption band), `column-right` / `column-left` (a narrow
  full-bleed strip, **cropped to fill** — atmosphere only), and `bleed` (media fills the slide,
  content over it). Contained vs cropped is the whole split/column distinction: a chart in a
  column gets cut. Mirroring stays CSS-only, so the reading order for PDF export and screen
  readers never depends on which side the picture landed on. **Existing models are unaffected**:
  `image` reads as `media`, `layout: text-left/image-left/image-top` as
  `split-right`/`split-left`/`banded`, and `aside: {image, side}` as `column-right`/`column-left`,
  all silently.

- **Inline font styling, in every field of every template.** An author emphasizing a phrase
  *inside* a sentence — a figure in a body, a term in a lead, a cited title in a source line — got
  literal asterisks on the slide. `**bold**`, `*italic*`, `` `code` `` and `[text](url)` are now
  resolved in the slide's text fields, once, before the template sees them, so this is not a
  per-template feature: any field of any type accepts them. Escaping still runs first (authored
  HTML stays inert text), links are limited to `http:`/`https:`/`mailto:`, and the fields whose
  bytes *are* the content — code blocks, speaker notes, image paths, the enum-ish fields the
  renderer branches on — are excluded. The grammar deliberately stops at inline marks: block
  markdown inside a field would let content route around the schema.
- **A plain unlabeled list is now a numbered list, not bullets.** A slide whose items carry no
  label (course logistics, the rules of an assignment, a set of conditions) had nothing to build a
  card around, so it fell to `fallback` and drew as bare bullets. It now matches `process`, whose
  unlabeled branch already renders a numbered list — an outlined number chip and the line — and
  rows tighten from 6 items on so 8 still fit. The numbering is the point: it makes a loose list
  countable and gives the presenter something to point at, without implying a sequence. The one
  unlabeled list that stays out is a 2–5 line **anaphora**, whose force is the rhythm; those go to
  `concept-breakdown` as label-only cards, since numbering would turn rhetoric into a checklist.

### Changed

- **Metadata descriptions corrected.** The plugin and marketplace manifests carried two copies of
  the same paragraph that had already drifted (the marketplace one was missing `pptx-learn`), and
  both described the deliverable as "optionally a `.pptx`" — never mentioning the HTML/Reveal.js
  deck, which is a first-class output. They are now one identical, shorter description that says
  what you get. The two anti-slop skills are namespaced `talksmith:` like the other eleven, so the
  bundled copy coexists with a user's own same-named skill instead of colliding with it (which is
  what the Editor's load order always assumed), and `stop-slop`'s trigger — "use when drafting,
  editing, or reviewing text" — is narrowed to explicit invocation, matching its Spanish sibling:
  as written it would have fired on ordinary authoring, which is exactly what an anti-slop pass
  must not do.
- **A labeled set is always a grid — the `list` format is retired.** `concept-breakdown`'s fourth
  format stacked N concepts in a single column, spending the whole slide width on one item at a
  time and making a set of peers read as a sequence. It is gone: the template keeps `grid`
  (cards), `editorial` (flat) and `row`, all of which read side by side. The `grid` format now
  also carries the `lead` and renders a bodyless item as a label-only card, so nothing the retired
  format held is dropped. A model still carrying `format: "list"` — or the legacy `icon-list`
  template id — renders as `grid` and the build warns, naming the slide. A set whose per-item
  prose genuinely needs a full-width column is not a labeled set: it is `content-text`, or two
  slides. On the strict `.pptx` path the §7.5 icon-bullet geometry stays documented (reference
  slide 15 demonstrates it) but no model selects it.
- **The `lead` reads as the title's sub-line.** It was set at body size and weight, so a framing
  sentence under the title read as the first paragraph of the body. It is now a step larger and
  bold.

- **New highlight kind `source` — a citation, rendered plain.** Attribution lines ("Fuente: OWASP
  Top 10 for LLM Applications, 2025") had no home: as a `note` they got a card, an accent bar and
  an icon, so a credit line drew as much attention as the content it credits. `kind: "source"` is
  the one highlight with no card, no accent bar and no icon — just a small muted line under the
  body. Use it for provenance only (paper, standard, dataset, report, URL); a line that *says
  something* about the source is still a `note`. Honored on both render paths: the HTML band drops
  its box, and the strict `.pptx` emits it as a plain card-body-size line instead of a §8 panel.

## [0.76.0] — 2026-08-03

### Added

- **`concept-breakdown` gains a flat `editorial` format — the same concepts without the cards.**
  The card grid reads as a product/dashboard surface: every concept in its own panel with a fill,
  a radius, wide padding and a large icon. That is right when the panels are part of the design and
  wrong when the deck wants an editorial page, where the weight of eight boxes crowds the slide and
  the panels mean nothing. `format: "editorial"` keeps the icon, label and body and drops the box:
  a small icon on the label's line, the body indented under it, a hairline and white space instead
  of a panel.
  It also fixes the count arithmetic. The card grid rounds 3 concepts to "two on top, one spanning
  the width", 7 to 3+3+1 and 8 to 3+3+2 — layouts that leave holes and change the visual hierarchy.
  The editorial grid maps counts to a regular grid (2·4 → 2 columns, 3·5·6 → 3, 7·8 → 4) and a
  short last row keeps the item width of the row above and **centers** (5 → 3+2, 7 → 4+3), so no
  concept is ever stranded alone across a row, and up to 8 fit without crowding.
  A conclusion stays a full-width band below the grid, never another cell in it.
  **Opt-in and non-breaking:** `grid` remains the default, so every deck that renders today renders
  byte-identically. The `.pptx` renderers have no flat recipe and fall back to the card grid.
- **The build now says when a slide won't fit instead of shrinking it.** An `editorial` grid whose
  bodies outgrow the column width (~140 chars at 2–4 concepts, ~100 at 5–6, ~70 at 7–8) or that
  carries more than 8 concepts warns and names the two real fixes — `format: "list"`, or split the
  slide — rather than letting the fit pass compress the type until it's unreadable. An
  unrecognized `format` also warns instead of silently rendering as cards, like `layout` already did.

## [0.75.0] — 2026-08-01

### Changed

- **`comparison` is now `value-columns` — a rename with no alias.** The shape it renders is 2–3
  aligned columns of parallel values read row by row; "comparison" described only its most common
  use, and the narrow name kept pushing slides that merely *list* parallel values across columns
  (three options judged on the same factors) toward the wrong template. The catalog entry now
  matches on **the columns being parallel and comparable**, not on the slide being adversarial.
  **This is breaking, deliberately:** the old id is gone rather than aliased, so a hand-pinned
  `<!-- template: comparison -->` or a stale `slide-model.json` renders as `fallback` and the build
  warns naming the slide — visible, not silent. Migration is a find-and-replace of the id in
  `draft.md` hints; models are refilled on every render anyway.

### Added

- **A table and a supporting diagram no longer compete for the same slide.** A slide
  that compares A vs B in a table *and* carries a diagram the prose walks through had no template:
  `value-columns` renders the aligned grid but had no image slot, and `content+cards+image` has the
  image but only one enumerable slot, so a `factor | A | B` table filled into it collapsed each row
  into a single card body (`"A: … B: …"`) — the parallelism between columns, which is what the
  slide teaches, survived as punctuation inside a sentence. Authors were pinning one template to
  save the diagram and paying with the table. `value-columns` now takes three optional fields with
  the meaning they already have everywhere else: **`image`** (a supporting diagram beside the grid),
  **`layout`** (`text-left` default, `image-left` mirrored), and **`lead`** (a framing line above
  the grid, with or without an image). It is the fifth body-plus-image composition, not a new
  template — the mirror is CSS-only, so reading order for PDF export and screen readers is
  unchanged, and the compare-strip keeps the wider track in both layouts.
  **Nothing existing renders differently:** a `value-columns` slide without `image` or `lead` emits
  byte-identical markup to the old `comparison` and still anchors to the bottom edge. Beside an image the grid stays a grid (columns keep
  their alignment; it never degrades to one row per cell), so it wants **≤3 columns × ≤5 rows** —
  past that the build warns instead of letting the slide squeeze silently. `image-top` is
  deliberately not accepted here: a grid under a full-width image is a different slide.
  On the `.pptx` path this is the existing table-to-card-grid conversion placed in the existing
  supporting-image slot — no new geometry — and, like every other image-bearing template there,
  it emits grid-left regardless of `layout`.

### Fixed

- **A resolved feedback entry could leave its `Resolution:` text on the finished slide.** The
  Step-6 strip swept a `**Presenter feedback:**` block by consuming bullets, and stopped at the
  first line that was neither a bullet nor blank. A resolution long enough to wrap onto an indented
  continuation line is neither — so the sweep cut there and the tail survived into `final.md` and
  into the rendered deck. The sweep now follows **indentation** rather than requiring a bullet:
  everything indented past the block's opener belongs to it, and a heading or `---` still ends it.
  The same wrap in the legacy inline-bullet form is fixed with it.
- **The strict layout audit crashed on every run.** Its `RenderEvidence` record — the half that
  reads what the rendered deck actually emitted — was dropped by accident in 0.44.0, so the audit
  raised `NameError` the moment it opened a `.pptx` instead of reporting layout mismatches. Restored.

## [0.74.1] — 2026-07-31

### Fixed

- **The rendered deck was not a well-formed HTML document, and previews choked on it.** `page()`
  emitted a bare fragment — `<meta>`, `<style>`, then the slides — with no `<!doctype html>` and no
  `<html>`/`<head>`/`<body>`. A browser opening the file directly recovers, but it recovers into
  **quirks mode** (`document.compatMode` was `BackCompat`), and anything that *embeds* the file
  instead of opening it — a preview pane, an iframe, a sanitizer — is entitled to drop `<meta>` and
  `<style>` found outside a `<head>`, which is how a deck that looked right in a browser came out
  broken in a preview. The document now carries a doctype, `<html lang>` taken from `deck.lang`,
  and explicit `<head>`/`<body>`. Rendering is **pixel-identical** across the reference deck (the
  explicit `box-sizing` reset was already absorbing the quirks-mode box model), so this is a
  correctness fix with no visual change.

## [0.74.0] — 2026-07-31

### Changed

- **The labeled set is one template again, not three.** `concept-breakdown`, `card-row` and
  `icon-list` were never three *shapes* — they are all "N parallel labeled concepts", and the
  catalog already told the fill to choose between them by item count and body length. Three Match
  rules for one shape is what made this the family the fill got wrong most often, and getting it
  wrong is expensive: a set routed to the wrong one loses its per-concept icons or its prose room.
  Now the **shape is the classification** and the arrangement is a **`format` field** — `grid`
  (default), `row`, `list` — exactly the pattern `layout` follows for images. The catalog drops from
  three entries to one, the renderer from three templates to one.
  **Nothing renders differently and nothing needs migrating:** `card-row` and `icon-list` remain
  valid `template` values that simply select their own format, `rows:` is still read as the item
  list, and the three formats emit byte-for-byte the markup their templates emitted before — the
  committed style reference is unchanged to the byte, which is the proof. New models should emit
  `concept-breakdown` and set `format` when the default isn't right.

## [0.73.0] — 2026-07-31

### Added

- **`image-full` — a new slide type for the slide that *is* one image.** A screenshot or diagram
  the presenter narrates, with the detail in the speaker notes, had no home in the catalog: it was
  either a `content-image` with an empty text column, or `image-grid` abused down to a single
  image. Now it is its own type — the **normal header** (section pill + title, plus an optional
  one-line `lead`), and the image takes **everything below it, bleeding to the left, right and
  bottom edges**: no padding, no frame, no caption. It is **contained, never cropped**, the
  invariant every image-owning template holds — a screenshot cut at the edges stops being
  evidence — so an image narrower than the space it is given centres rather than filling it. If
  you want cropping-to-fill, that is what `aside` is for.
  The `image_only` signal now classifies to this type across the catalog's walk, its
  disambiguation table and the fill guide, so the choice is no longer left to each fill to invent.
  `content-image` correspondingly requires its prose again; the renderer keeps dropping an empty
  text column defensively for models written before this.

### Fixed

- A stray line of prose after a comment's closing `*/` in `theme.css` made the CSS parser swallow
  the rule that followed it, so a full-bleed image escaped its box and was clipped at the slide
  edge. Fixed, and the two nested sizing traps behind it are now commented where they bite: a
  percentage height inside a `place-items:center` grid is cyclic and silently falls back to the
  image's intrinsic aspect, so both the frame and the picture are pinned with `inset:0` instead.

## [0.72.0] — 2026-07-31

Three composition fields that used to belong to one template each now mean the same thing on
every slide that can carry them — plus an audit of the metadata the fill step uses to pick a
template at all.

### Added

- **`layout` works on every slide that carries its own image**, not just `content-image`. Where a
  supporting image sits is a *composition* choice, so `content+cards+image`, `process` and `quiz`
  now read the same field with the same meaning: `text-left` (default) or `image-left` (mirrored,
  so the image is read first). `image-top` stays `content-image`-only — a card set or a step list
  under a full-width image is a different slide, not a layout of this one. This closes the trap
  that forced authors to choose between per-concept icons and an image-first reading order: a
  labeled set with a diagram stays `content+cards+image` and pins `layout: image-left` instead of
  being demoted to `content-image` facts. The mirror is CSS-only — markup stays body-then-image, so
  PDF and screen-reader order never change, the enumeration keeps its order/icons/alignment, and
  each side keeps its own column width (grid tracks flip along with the content, since grid
  auto-placement follows `order`). A `layout` a template doesn't define, or one on a slide with no
  image, renders as the default **and warns on stderr**.
- **`highlights` entries choose their band with `position`.** The accent band used to be hardwired
  below the body, which only fits a *remark* — a line that comments on what the audience just read.
  A line that *frames* what follows (a voiced line that sets the theme, a definition the items
  depend on, a warning that has to land first) now sets `position: "top"` and renders in a band
  between the title and the body. It is **per entry, not per slide**, so one slide can open with a
  frame and still close with a takeaway; both bands are the same component (same classes, colours,
  icons). Reveal follows the same logic it always did: the closing band arrives on the last click,
  and the framing band is on screen from the moment the slide opens, because a frame that arrives
  last frames nothing.

### Fixed

- **An image-only slide no longer projects an empty text column.** `content-image` emitted its text
  wrapper unconditionally, so a slide with just an image (a screenshot the presenter narrates, its
  detail in the notes) produced a blank half-slide — or, under `image-top`, a bordered accent box
  with nothing in it. The column is now emitted only when there is a `lead` or `facts`, and when it
  is absent the image takes the **full width** instead of staying in its half. This shape is now
  documented as first-class: `content-image` with no text *is* the image-only slide, so there is no
  longer a reason to abuse `image-grid` (≥4 images) to get chrome-free art.
- **A diagram rendered to `.pptx` came back as a blurry raster in the HTML deck.** `final.md`
  carries `.svg` refs, but the `.pptx` prerequisite check rewrites them to the `.png` companion
  (Keynote drops SVG on import) and never rewrites them back — so a talk rendered to `.pptx` and
  then to HTML shipped rasterized diagrams, unreadable at the small type a diagram uses, with the
  vector original sitting right beside them. The HTML render now inlines the `.svg` twin when one
  exists **and is provably generated** (an `.ascii` sidecar or the `talksmith-ascii-sha256` stamp —
  the same provenance test `polish-ascii gc` uses), so a presenter's own `chart.png` is never
  swapped for an unrelated `chart.svg`. No re-run of the pipeline needed.
- **An image on a busy slide shrank into a letterbox.** Images were sized `width:100%` with a
  height cap in `cqw`. The content-fit pass lays a slide out wider and scales it down, so on a
  crowded slide the image's column inflated while its cap — a share of the *slide* — did not: the
  picture was clamped short, and `object-fit` centred it inside a column-wide box, leaving a small
  diagram marooned in a big empty bordered frame (worse the busier the slide). Images now size to
  hug the picture, so the frame wraps the image exactly at any scale, and the cap was raised to the
  largest value that keeps every reference slide overflow-free. Measured on a real deck, diagrams on
  crowded slides went from 51–89% of their column width to 67–96%. The cap is deliberately still
  unscaled — a comment in
  `theme.css` and one in `fitContent` explain why scaling it makes the fit unsolvable, since that
  is the tempting "fix".
- **The same guard applied across every other template** in one pass: `code-example` no longer
  emits an empty dark code panel (and a missing panel collapses the split to full width),
  `callout`/`single-point` no longer emits a coloured box with no point, `quiz` no longer emits an
  empty answer panel, and `content-text`/`pros-cons` no longer emit empty prose containers.
- **Template selection was defaulting to a handful of types.** The catalog's discriminator walk —
  the prescriptive part the fill step actually executes — named only ~14 of 25 templates, so the
  rest were reachable in practice only through an explicit author hint. `timeline`, `quote`,
  `quiz`, `pros-cons`, `big-number`, `callout` and `closing-cta` now have their own signals
  (`date_labels`, `is_voiced`, `is_question`, `polarity`, `one_metric`, `is_cta`, `image_only`) and
  their own branch in the walk, and the four entries that described themselves as "author-directed"
  now state the signal they fire on by themselves. Two ordering bugs are fixed with them:
  `is_ordered` was tested before dates (so every timeline was swallowed by `process`), and the
  disambiguation table sent *any* labeled set with an image to `content-image`/`figures`, which is
  what dissolved card sets into fact lists. The FILL guide also gains the `lead`-vs-`highlights`
  rule — a line that introduces the body is the `lead`, only a line that comments on it is a
  highlight.

### Changed

- The `.pptx` path states what it does with the new fields instead of diverging in silence: strict
  **honors** `highlights[].position` (a band above the body costs no new geometry) and an
  image-only slide (no empty text frame), but **ignores** `layout` by decision — its EMU geometry
  is bound to a base template with no mirrored exemplar. Free-form honors all three as design calls.
- `audits/field_coverage.py` knows `layout` is consumed by `content+cards+image`, `process` and
  `quiz`, so it no longer reports the field as ignored on the very slides that render it. It stays
  listed per-template rather than universal — on a template with no image of its own, `layout`
  really is dead weight and should still be flagged.
- The style-reference fixture gains an example of **every new permutation** — `image-left` on all
  four image-bearing templates, the image-only slide in both layouts and with a highlights band,
  a framing band alone and both bands together, and a one-panel `code-example` — so any of them
  regressing shows up in the committed `style-reference.html` diff.

## [0.71.0] — 2026-07-31

### Fixed

- **Two catalog template names didn't match the renderer, so decks using them silently rendered
  as `fallback`.** The catalog published `content+image` and `agenda`; the renderer's registry
  keys are `content-image` and `section-agenda`. An LLM classifying against the catalog and
  copying the name it read there produced a model the renderer couldn't dispatch — and because an
  unknown `template` falls through to `fallback.j2` without a word, the result looked like a bad
  classification rather than a typo. The bundled test fixture had the bug too (`<!-- template:
  agenda -->`). Catalog headings and every cross-reference now use the real values, each with a
  note on why the near-miss exists (`content+image` remains the *strict PPTX recipe* name — a
  separate namespace from `template` values). **`build_html.py` now warns on stderr** when a slide
  names a template it doesn't know, naming the slide, so this class of drift can't be silent again.
- **A timeline's per-milestone `marker` was documented but never rendered.** The schema has listed
  it as an optional field all along; `timeline.j2` never read it, so a fill step that emitted one
  had it silently dropped. It now rides inside the milestone dot, which grows to hold it; a
  milestone with no marker keeps the plain dot exactly as before.
- **`divider` had no catalog entry** — it exists in the schema, the renderer and the fixture, but
  the catalog documented no Match criteria, leaving the fill step no rule for choosing it. Added,
  with the discriminator against `section-agenda` stated explicitly: title names a `deck.sections`
  entry → `section-agenda`, otherwise → `divider`.

### Added

- **`content+image` can put the image on the left.** Until now the only side-by-side arrangement
  was text-left / image-right, and the sole alternative was `image-top` (stacked). The one layout
  that did accept a left image — the `aside` column — crops to fill and is explicitly off-limits
  for a diagram the audience has to read, so there was no way to lead with a readable image. The
  new `"layout": "image-left"` on `content-image` mirrors the two columns: image left, text right,
  **aspect still preserved, never cropped**. Reach for it when the image should be read first (a
  diagram the prose then walks through) or to break up a run of text-left slides. The enumeration
  is deliberately untouched — `facts` keep their order, their left-edge dot markers and their left
  alignment in all three layouts; only the column positions swap, and the markup order stays
  text-then-image so reading order (PDF export, screen readers) is unchanged. Default is still
  `text-left` when `layout` is omitted, so existing decks render identically.
- **`<!-- layout: <value> -->` author directive** — forces the arrangement *within* a template
  when the type is right but the default placement isn't, the sibling of `<!-- template: … -->`
  (which pins the type). Currently read by `content-image` (`text-left` | `image-left` |
  `image-top`); an unrecognized value falls back to the template's default rather than erroring,
  matching how `reveal:` already behaves. Declared in the four places a directive has to be
  declared to work: the author-facing list in `editor.md`, the preserved-verbatim row in
  `schemas/draft.md`, the honour-directives rule in the `slide-model.json` fill step, and the
  catalog's `content-image` entry.
- **The style reference now covers every render path, not just every template.** It had one slide
  per template but left whole branches unexercised, so a regression in them would ship unseen:
  `fallback` had no slide at all, `process` with a supporting image (a distinct two-column layout,
  not the numbered cards), the blue `callout` tone, `stat` at its 2- and 4-number edges (the grid
  is count-driven), explicit per-card `icon` suggestions (vs. content-matched), timeline markers,
  and `reveal: together`. Added, taking the deck from 43 to 49 slides; both the default and the
  variant path is now present for each, so a diff shows which one moved.

## [0.69.1] — 2026-07-31

### Changed

- **Concept cards lead with the icon on the left instead of stacking it on top.** The icon used to
  occupy a full-width row of its own above the label, leaving a wide band of dead space beside it
  and pushing the text down. It now sits in its own column, spanning the label and the body, so a
  card reads icon → label → body left-to-right and reclaims the vertical space. Applies everywhere
  concept cards appear — `concept-breakdown` at every card count (2/3/4/6) and the narrower cards
  in `content+cards+image`. Layout-only, in `theme.css`; no template or renderer change, and the
  slide model is untouched. Note this now differs from the PPTX recipe for the same template
  (§7.2.1 still places the icon above the label).

### Fixed

- **`source` and `question_answer` rendered as a generic info glyph.** Neither name is in the
  bundled icon set, so a deck built without network lost the concept the icon was carrying. Both
  now alias to a bundled equivalent — `description` and `forum`.
- **The committed tutorial deck was stale.** `tests/examples/talksmith-intro` had been rendered by
  an older build and never regenerated, so it was missing fragment reveals and the SVG id
  namespacing that keeps two inlined diagrams from sharing arrow-marker ids — and three of its
  icons drew nothing at all. Rebuilt from its `slide-model.json`; all 46 icons now draw.

## [0.69.0] — 2026-07-30

### Added

- **A bundled icon set, so HTML decks build offline.** 75 Material Symbols (outlined, Apache-2.0,
  `skills/md-to-deck/icons/`) covering the offline concept map, the neutral fallback chain and the
  concepts most decks reach for. Resolution order is unchanged — cache, then CDN, then these — so
  an online render still picks from the full catalog; the bundle only catches the case that used
  to fail. Icons still ship inlined, so the deck remains a single self-contained file.

### Fixed

- **Icons degraded to a meaningless bullet with no network.** `icon_for()` chose a semantic icon
  name, but the glyph itself came from the CDN — so with no connection and a cold cache every icon
  on every slide rendered as a plain disc. Silently: no warning, and a slide about metacognition
  looked identical to one about payments. There is no longer any shape fallback; an icon that
  can't be resolved renders a real generic glyph and warns, naming what was asked for and what was
  substituted. Offline concept matching also learned cognition, creativity, adaptation, judgment
  and human capital (→ `psychology` and neighbours) instead of dropping them on the default.
- **Icon names that 404 even when online.** `insights`, `message`, `business`, `emoji_emotions`
  and others are listed in the Google Fonts catalog but absent from the CDN package the renderer
  pulls from — and `insights` was in the offline seed map, so metrics slides were rendering a
  placeholder whether or not there was a connection. Known cases now map to an equivalent that
  exists; anything left over hits the warning path rather than failing silently.
- `circle` and `adjust` are gone from the neutral fallback chain: both draw a plain disc, which is
  the exact bullet the chain exists to avoid.

## [0.68.4] — 2026-07-30

### Fixed

- **Label separators stranded in the model.** A source line like `- **Problemas bien definidos**:
  cuando el objetivo está claro` was split at the `**` rather than at the separator, so the model
  carried `body: ": cuando el objetivo…"` and the slide showed a dangling `:` under its heading.
  (The mirror-image slip left it on the label instead.) The fill contract now names both wrong
  outputs explicitly and states the rule: the separator is consumed, the body's first letter is
  capitalized once it's gone, a colon *inside* either side is content and stays, and the rule
  covers every `{label, body}` field rather than the one template where it was first noticed.

## [0.68.3] — 2026-07-30

### Fixed

- **Generated diagrams rendered as raster instead of vector in HTML decks.** `final.md` correctly
  referenced `images/<name>.svg`, but the FILL step rewrote the extension to the `.png` companion
  while building `slide-model.json` — so the HTML deck embedded a flat raster and never inlined the
  SVG. The cause was the `.svg`-forbidden prerequisite, which exists for the Keynote import path
  and was being applied to the HTML fill as well. That rule is now explicitly scoped to the `.pptx`
  path, and both the fill step and the model schema state that an image `src` is copied verbatim,
  extension included. Re-render an affected talk to pick up the vector version.
- **Colliding `id`s between inlined SVGs.** Every diagram in an HTML deck lands in one document, but
  the generator names its `defs` for their role rather than for uniqueness (`a` = grey arrowhead,
  `r` = red one), so a deck with three diagrams carried three `id="a"` and every `url(#a)` resolved
  to the first one in document order — diagrams 2..N silently painted with diagram 1's marker. It
  stayed invisible only because those definitions happened to be identical; one differently
  coloured arrowhead would have made it a wrong-colour bug with no error. Each inlined SVG now gets
  its `id`s namespaced as it goes in, references rewritten to match.

## [0.68.2] — 2026-07-30

### Fixed

- **Dangling colons on card and row labels.** The fill splits a `Label: rest` source line into
  `{label, body}` and is told to drop the separator, but it often carried it into `label` — so a
  card heading read `Leave feedback:` with nothing after it, and the inline sites that emit their
  own separator (`highlights`, `content-image` facts, `process` steps) read `Leave feedback::`.
  The HTML render now strips a label's trailing colon at the eleven sites where the layout already
  separates label from body. The `single-point`/`callout` panels are deliberately untouched: they
  render `**label** body` inline with no separator of their own, so a colon there is doing work.

## [0.68.1] — 2026-07-30

### Changed

- **Animated slides now start empty.** An enumeration slide (`stat`, `card-row`,
  `concept-breakdown`, `icon-list`, `content+cards+image`) used to show its first card
  immediately and animate in only items 2..N. Every item is a fragment now, so the slide opens
  on its heading alone and the presenter clicks each item in — including the first. Unchanged:
  `reveal: together` still shows the whole slide at once, the runtime animations toggle still
  flattens every fragment, and `.pptx` is static as before.

## [0.68.0] — 2026-07-17

Bug-triage batch from the `claude-cowork` production run — correctness fixes and new guardrails across Polish and Render.

### Added
- **Two render preflights that catch content before it silently vanishes** ([`md-to-deck`](skills/md-to-deck/audits/)). `field_coverage.py` flags model fields the chosen template will ignore (an image on a `divider`, a second image on `content-image`) — a misclassification tell. `image_coverage.py` compares every `![](…)` in `final.md` against the model and lists any dropped image ref (a slide would render with no image), ignoring `ascii-source` echoes, `# Cut material` / `# Open questions`, and refs waived with `<!-- deck-omit: <path> -->`. Both are advisory (exit 0 + a stderr list; `--strict` to fail) and run in the CHECK step.
- **`gc` subcommand on both Polish skills** — `polish-ascii gc` and `polish-images gc` prune orphaned generated triplets left after a re-architecture/renumber (`.svg`/`.png`/`.ascii` + `.critique` png; `.png`/`.imgprompt`/`.imgstamp`). Non-destructive by default (`--apply` to delete), and a stem is a candidate **only when proven generated** (a stamped `.svg` / `.ascii` sidecar, or an `.imgprompt` / `.imgstamp`), so presenter-owned images are never deletion targets.
- **Deterministic `Presenter feedback` stripper** ([`feedback-cycle/strip_feedback.py`](skills/feedback-cycle/strip_feedback.py)) replaces the hand-strip at Step 6 (d). It removes all three authored forms and **guarantees a blank line before every `---` slide boundary**, so a strip can never leave `text\n---` for Markdown to misread as a setext-H2 heading (which had silently fused slides). Covered by a test.
- **Explicit ASCII render-override hints** — `<!-- ascii-render: force -->` renders a block to SVG even on a slide that also has an image (the "banner + screenshot" case), and `<!-- ascii-render: documentation-only -->` suppresses one that would otherwise render. With no hint, the image-ref default is unchanged; the scan surfaces the hint for auditing.
- **Mount-portable render args** — `prepare-render-args` (both Polish skills) now emits Talk-relative path twins (`images/<name>`) plus `talk_rel` (the Talk dir relative to `repo_root`) alongside the absolute paths, and warns loudly when the Talk isn't under `repo_root`. `ascii-to-svg` / `generate-image` prefer the twins, re-anchoring on the `repo_root` they were dispatched with, so a render worker in a different mount (VM vs host) resolves paths correctly. The absolute paths stay as a same-session fast path.
- **Diagram-style rules promoted** ([`config/diagram-style.md`](config/diagram-style.md)) from recurring visual defects: `markerUnits="userSpaceOnUse"` for arrowheads, arrow-shaft termination on the destination edge, no inline `<tspan>` under centered text (cairosvg overprint), `xml:space="preserve"` for leading whitespace, a broadened no-Unicode-symbol-glyphs rule (checks/crosses/bullets, not just arrows), and no decorative XML comments (`--` is illegal inside a comment and rejected as malformed). A regression test asserts `validate_svg` rejects `--` comments.

### Fixed
- **`content+cards+image` silently dropped its `lead`** — the schema declared `lead` optional but the template never rendered it. It now renders above the cards (regression-guarded in the style fixture).
- **Invalid suggested icons fell to a generic placeholder circle** instead of a real icon. A per-item `icon` suggestion is now validated against the live Material Symbols catalog; an unknown name is dropped, content-matched via `icon_for`, and logged as `invalid_icon`.

## [0.67.1] — 2026-07-17

### Changed
- **Compacted the intro workflow chart.** The Step-0 workflow overview now shows the eight steps as a single one-line flow (`[1] Frame → … → [8] Learnings`) plus a tight aligned list of what the agent says at each step, dropping the tall vertical `v`-arrow ladder that consumed most of the screen.

## [0.67.0] — 2026-07-17

### Added
- **Render freshness guard — a deck is never built from a stale `slide-model.json`.** `slide-model.json` (and `slide-model.draft.json`) is a **generated artifact**, re-produced by the FILL step from the current source before every render. The FILL step now **stamps** the model with the SHA-256 of the exact `final.md` / `draft.md` bytes it was filled from (new `model_freshness.py stamp`), and every generator **verifies that stamp before rendering** and refuses on a mismatch or a missing stamp — it never silently falls back to an existing model. `html-strict` (including the `--draft` live view) enforces this inside `build_html.py` (refuses with exit 2); `pptx-strict` and `pptx-free-form` run `model_freshness.py check` as an explicit pre-render gate. If FILL fails, the render stops and reports rather than reusing an old model. The committed HTML style test (`--model` direct mode) is exempt — it has no resolvable source — and `--allow-stale` is an explicit override for deliberate ad-hoc renders. Documented across the md-to-deck SKILL.md and the `slide-model.json` schema so future generators treat the model as generated, not maintained.

## [0.66.0] — 2026-07-17

### Changed
- **Generated asides are now editorial, symbolic illustrations — not generic atmospheric backdrops.** The image-illustrator's guidance was rewritten around a house visual language: a **flat, poster-like editorial vector illustration** that reads as a **visual metaphor** for the slide's idea (abstract enough to avoid a literal stock-photo scene, connected enough that the viewer infers why the image belongs with the slide). The enriched prompt must now name five things — the slide's **emotional role**, the **conceptual metaphor**, the **visual language** (editorial vector / poster-like / flat graphic), the **deck palette + contrast discipline** (light ground, `#3B3535` mass, single `#DA1B2E` accent, strong white negative space, thin contour linework), and an explicit **negative list** (no photorealism, no literal scenes/people/places, no generic decorative geometry, no UI/screenshots, no readable text/logos). The Editor's one-line brief now describes the *emotion + concept* to evoke rather than a literal scene (e.g. *"the vertigo of scale"*, not *"a lone figure at dawn"*), and the light post-generation review now also catches drift into photorealism/literal/decorative-geometry.
- **Anti-slop is now enforced once, at draft authoring — no longer a presenter-gated Step-6 pass.** The Editor's *Anti-slop authoring standard* (always-on, at `draft.md` creation) is now the sole enforcement point; it runs unconditionally and never asks permission. The optional opt-in anti-slop offer in Step 6 (Polish) and the corresponding one-time prompt were removed — Polish now runs fully unattended and assumes the prose is already clean.

## [0.65.0] — 2026-07-17

### Changed
- **The Editor now *actively* proposes generated atmospheric asides, and never leaves an image need `[open]` just because no file exists.** The 0.64.0 capability existed but the Editor treated it as optional, so in practice it stayed conservative — when a presenter asked for an image and no corpus asset fit, it documented the gap as an open question instead of proposing generation. The spec is now explicit: proposing `generate-image` directives is a **standing pass on every draft and review round**, with two triggers — (1) a sparse slide that would read better with imagery, and (2) **a presenter image request with no available asset**, which now becomes an authored `generate-image` proposal, not an `[open]`. A missing file is a reason to propose generation, not a dead end. (The only thing still left open is a request for something that must be *read* — a specific chart/screenshot — which generation can't supply.)

## [0.64.0] — 2026-07-17

### Added
- **Generated atmospheric aside images** — a new visual path for sparse-text slides, mirroring the diagram pipeline end to end. On a slide with little text where a full-bleed image down one edge would help, the **Editor** now suggests a generated aside by authoring a short, high-level, presenter-editable directive in `draft.md`:
  ```
  <!-- generate-image: right | a cold, minimal sense of vast scale — a lone figure at dawn -->
  ```
  At Polish, the new **`image-illustrator`** agent enriches that one-line idea into a full generation prompt — **folding in the deck's own palette** (`config/diagram-style.md`: light ground, `#3B3535`, single `#DA1B2E` accent) so a generated aside and a rendered diagram read as one system — and produces the image via the new **`talksmith:generate-image`** skill. The directive is then rewritten into a normal `<!-- aside: … -->` ref the existing left/right column already renders.
  - **Tool-agnostic and graceful.** Generation uses whatever image capability the session exposes (an MCP image tool, the host's native generation). Where none is present, the directive is left unfulfilled, the slide keeps its text, and the count is reported — it never blocks Polish (the same way `.pptx` modes are Cowork-only).
  - **Atmosphere, not information.** Generated imagery is mood only; anything the audience must *read* stays a diagram (ASCII → SVG) or a corpus image. The image-illustrator refuses text-bearing directives.
  - Extraction is the new **`talksmith:polish-images`** skill — the sibling of `polish-ascii`, with the same staged `scan` / `annotate` / `extract` / `prepare-render-args` / `stamp-renders` / `cleanup` shape and idempotency (keyed on the presenter's original description, stamped in a companion `.imgstamp` since a raster can't carry an inline comment).

### Changed
- **Shared slide-context scanner** factored into `skills/_shared/_context.py` (headings, prose stripping, thesis, the per-block context bundle) and imported by both `polish-ascii` and `polish-images` — one implementation, no duplication. The `polish-ascii` refactor was verified to produce byte-identical scan output.

## [0.63.0] — 2026-07-17

### Changed
- **The `illustrator` agent is renamed to `diagram-illustrator`**, everywhere — frontmatter `name:`, filename, every spec/skill/schema/doc reference, the presenter-facing role list, and the demo talk. The new name pairs with its sibling `diagram-critic` (draws / reviews) and states plainly that this role handles **diagrams** (ASCII → SVG), not imagery — leaving the name "illustrator" free for a possible future generative-image role. No re-init required: agents and the orchestrator refresh on `/plugin update` and the next session.

## [0.62.0] — 2026-07-17

### Added
- **`/talksmith:init` now also writes `AGENTS.md`**, so a Talksmith working directory boots the same workflow under **Codex** (and any agent that reads `AGENTS.md`), not only Claude Code. To avoid duplication, `CLAUDE.md` stays the single source of the boot instructions and `AGENTS.md` is a thin **pointer** to it — it only re-states the two Claude-Code-specific fallbacks a non-Claude agent needs (the `@`-import is inert; `${CLAUDE_PLUGIN_ROOT}` is unset, so locate `orchestrator.md` under the plugins directory and read it). The two files can't drift because only one carries content.

> **Re-run `/talksmith:init`** in each working directory to drop the new `AGENTS.md`. Existing `CLAUDE.md` behavior is unchanged.

## [0.61.0] — 2026-07-16

### Added
- **`timeline` now takes an optional `lead`** — one intro line above the dated rail. Previously a timeline slide that needed a framing sentence had no place to put it, so such slides were forced over to `process` (numbered cards) purely to gain a lead, losing the time-rail visual. The lead is optional; without it the rail still starts at the top. Slides that only drifted to `process` for this reason can move back to `timeline`.

## [0.60.0] — 2026-07-15

**Never leave the presenter staring at silence.** Polish and Render already showed a live checklist while they worked; the other long unattended stretches didn't, so the deck would go quiet for minutes with no sign of life. This release extends the pattern to every step that makes the presenter wait, and adds a workflow-wide "you are here".

> **Re-run `/talksmith:init`** in each working directory to pick this up — the stub's session-start contract changed. Everything else here rides along on `/plugin update` with no re-init.

### Added
- **Two one-line rails, shown together.** A **step rail** on every step transition, so the presenter can see how much is left, and a **stage rail** under it during a long step, so they can see it's alive:
  ```
  ✓ Frame → ✓ Collect → ▶ CORPUS → Draft → Review → Polish → Render → Learnings
  ✓ Read 12 sources → ▶ Pulling out the images (34) → Building the knowledge base
  ```
  Deliberately one line each: the step rail is not a reprint of the Step-0 chart, and two lines is the ceiling — a rail needing a third is too granular. Long stages carry counts and tick **per item**, not at the end; a failed stage marks `✗` and the step keeps going.
- **Stage rails on Steps 3 and 4**, which previously ran silent. Step 3 (reading every source) hid 3–5 minutes behind a single up-front ETA. Step 4 Modes B and C draft the entire deck before the presenter sees a word of it. Mode A shows none — it's Q&A, so there's no silence to cover.

### Changed
- **Steps 6 and 7 progress: multi-row checklists → the one-line stage rail**, so every step reports progress the same way. The glyph vocabulary and flip/heartbeat/failure rules now live **once** in `orchestrator.md` → *Interaction defaults*; each step (and `md-to-deck`'s SKILL.md, for the three render modes) contributes only its own stage names.

### Fixed
- **A diagram-free Talk skipped a stage that actually runs.** Step 6 told a Talk with no diagrams to skip "the middle three rows" — but that range includes *Adding them to the deck*, which also converts every photo. An image-heavy deck with no ASCII diagrams went silent for minutes on a stage marked skipped. Only *Drawing* and *Checking* are skipped now, and the heartbeat rule explicitly covers the last two stages, which aren't instant just because they come last.
- **The live view narrated itself over the review it must not interrupt.** Step 5.5 is designed to be invisible — background, non-blocking, refreshing silently — but also instructed to show the render checklist. It now shows neither rail; a failure surfaces when the view is offered, not as a `✗` mid-review.
- **Cowork sessions opened with plumbing instead of a greeting.** The stub tells the agent to Read the spec itself when the `@`-import doesn't expand, and it did — but announced it first (*"I need to load the Talksmith spec first…"*). The load is now silent; the first thing a presenter sees is the introduction.

## [0.59.1] — 2026-07-15

Post-restructure audit sweep: three parallel audits (cross-reference integrity, stale claims, Python bug hunt with fixture repros) over the whole plugin; every confirmed finding fixed.

### Fixed
- **`polish_ascii.py` — seven verified bugs:** a fence opener with a non-word tag or info string (```` ```c++ ````, ```` ```python title=x ````) flipped fence parity and could mint a phantom block spanning the next slide's headings (structural corruption on `cleanup`); a mid-line `-->` in an `ascii-note` (e.g. `emphasize: the input --> model arrow`) truncated the note; an in-place payload edit passed the stale-plan guard and was silently reverted (guard now compares payload byte-for-byte → exit 3); slide-boundary detection read `#`-prefixed lines *inside* fences as headings, breaking `documentation_only` and context extraction; a stale `apply` wrote sidecars before aborting (now validates first — exit 3 writes nothing); the `⇒` arrow glyph documented in the legacy heuristic wasn't detected; scan plans stored a cwd-relative `final_path` that `prepare-render-args` mis-anchored from another cwd (now resolved absolute).
- **`merge_draft.py`:** `apply-auto` landed a slide's retitle first, orphaning that slide's remaining edits on unnumbered slides (anchored by the pre-change title); retitles now apply last.
- **`pptx_inventory.py`:** the SVG-only picture fallback was dead code — link-only / SVG-only pictures were silently dropped from the inventory; the fallback is now reachable.
- **Stale docs:** `editor.md`/`schemas/draft.md` documented the no-op legacy `<!-- reveal: sequential -->` instead of the real opt-out `<!-- reveal: together -->`; `principles.md` justified the title budget with the retired Roboto Mono face; the strict spec still attributed the icon picture-shape format to Marp, overstated `template-previews/` coverage, and carried two malformed relative links; one pointer targeted `config/feedback-backlog.md` for a section that lives in `schemas/feedback-backlog.md`; three pointers named a README heading that doesn't exist (*One shared repo per subject* → *One repo per subject*); `polish-ascii` SKILL.md's "all subcommands are idempotent" and exit-code contract corrected to match actual behavior.
- **Dev-data leak:** `config/learnings.md` in the plugin repo carried a real learning entry from a development talk (already promoted into the strict spec's §15 meta-rule); reset to the canonical empty form.

## [0.59.0] — 2026-07-15

A plugin-wide **prose diet + single-source restructure**. Every spec file is LLM context, and an audit found the same facts stated in 2–9 places, plus large rationale/history blocks in high-frequency files. This release establishes an **ownership map** (now in the dev `CLAUDE.md`): every fact lives in exactly one owning file — the catalog owns template Match/Format, `schemas/slide-model.md` owns field contracts, the strict prompt owns EMU recipes, `diagram-critic.md` owns the blind-critique rationale, each skill owns its own mechanics — and every other file points there. ~17k words (~22k tokens) of restatement removed; **no rule, CLI contract, or schema form was dropped**, and the regenerated `tests/.../style-reference.html` is byte-identical.

### Changed
- **Skill descriptions** (always in session context) cut from ~1,120 to ~350 words — now concise triggers; interface detail lives in each SKILL.md body.
- **`orchestrator.md`** (loaded every session) slimmed ~12%: Step 5.5 detail now points at `md-to-deck` → *Path B*; the Step-7 suppression vocabulary + don't/do examples moved to `md-to-deck` SKILL.md → *Progress reporting*; the memory-writer contract defers to `schemas/memory.md`; repeated "Speak human" / "style is render-time" statements reduced to one each.
- **`diagram-critic.md`** (dispatched per block per critique iteration) trimmed ~16% — one tight statement of the blind-critique rule; checklist and report format intact. **`illustrator.md`** (−14%) and **`editor.md`** (−12%) now point at `diagram-critic.md` and the `polish-ascii`/`ascii-to-svg` contracts instead of restating them.
- **`pptx-strict/pptx-prompt.md`** (−1,760 words): dropped §16 "Recipes summary" and the §19.7 navigation recap; §15.5's discriminator column compacted to defer to the catalog's *Match* rules; pill/agenda-capacity/cover/icon rules now stated once at their home section.
- **`ascii-to-svg` SKILL.md** (−15%): benchmark evidence and spec-history removed; every rule kept; step 9 renamed *Aspect audit* (the anchor other files reference).
- **`polish-ascii` SKILL.md**: the plan-JSON shape is printed once; detection tiers defer to `illustrator.md`.

### Fixed
- Literal duplicated/empty table header in the strict spec's §11.
- Two stale claims: the `md-to-deck` Path-A prerequisite and the strict spec's §19.1 asset row still said icons ship inside `base-template.pptx` (§17.6 documents they never did — icons are fetched by name via `icon_fetch.py`).

### Removed
- The two duplicate copies of `_pptxlib.py`: the canonical module now lives once at `skills/_shared/_pptxlib.py`, `sys.path`-imported by the three reverse-pipeline scripts (all CLIs verified).
- ~1,240 lines of superseded changelog history, compacted into milestone bands per this file's own maintenance note.

## [0.58.2] — 2026-07-15

The SVG authoring step is the pipeline's only real cost — measured at ~36 s against 0.34 s
for every script around it, and it is bound by *output* tokens, so bytes not emitted are
seconds not spent. This release stops emitting about a fifth of them.

### Changed

- **Inheritable attributes are hoisted to the root** (`SKILL.md` step 5). `font-family`
  belongs once on the `<svg>`, not on all fifteen `<text>` children; same for `font-size`
  and `fill` where one value dominates. SVG inherits down the tree, so the render is
  unchanged — measured across the fixtures: **0 differing pixels out of 3.9M**, files
  **24.6% smaller** (~1450 tokens over seven diagrams; 19.9% of bytes across all nine once
  `fill` and `font-size` are counted).

  The rule carries the trap that makes it non-obvious: **inheritance is by tree, not by
  document order**. A `<tspan font-family="…mono">` inside a `<text font-family="Helvetica">`
  must keep its declaration even when mono is the root's value — it inherits from its
  parent. Dropping it there silently reverts an inline code span to the wrong face,
  invisible in the XML and visible only in pixels. That case exists in this repo's fixtures
  and a naive implementation of this very optimisation broke it.

  This is deliberately an authoring rule and not a cleanup pass: by the time any script
  runs, the seconds were already spent emitting the bytes, so shrinking the file afterwards
  saves nothing.

### Added

- **A hoisting lint** in `validate_svg.py` — advisory, never repaired (repairing would save
  no time, per above). It reports how many declarations a root declaration would make
  unnecessary. It measures *hoistability* by resolving the tree, not repetition: the common
  waste pattern has no root declaration at all and fifteen children restating the same
  value — nothing is redundant in the strict sense, yet all fifteen are avoidable — while
  the nested-override case above is a legitimate repeat that must not be flagged. Tests in
  `tests/skills/ascii-to-svg/test_redundant_attrs.py`.

### Investigated, no change

- **Whether `talk_thesis` / `section_goal` earn their place in the context bundle** —
  hypothesis was that ~67% of the bundle leaves no trace in the render. **No evidence
  either way, and the pixel-diff A/B cannot produce any**: a control arm (two renders from
  byte-identical input) differs from itself in **12%, 32% and 46% of pixels** depending on
  the block. That noise floor swamps the effect. Moot regardless: the bundle is **input**,
  and this step is output-bound — removing 2.1 KB of input saves ~0 s, so even a
  proven-dead field would not be worth the risk. The bundle stays as it is.

## [0.58.1] — 2026-07-15

Hardening of the blind critic, from what a nine-diagram test run actually surfaced.

### Fixed

- **A defect naming something that isn't there had no legal outcome.** A critic reported a
  gradient on a panel that was flat `#FFFFFF`. The illustrator is told to treat the verdict
  as authoritative and never check it against the XML — so obeying meant fabricating an edit
  for a non-existent element, and not obeying meant the arithmetic self-review the split
  exists to kill. There is now an `unreproducible` verdict, scoped tightly: it applies only
  when a defect's *subject* is verifiably absent from the source, never when its *judgement*
  is merely one you'd rather overrule.
- **A critic that couldn't load the standing rules failed silently.** Its output would carry
  no rule violations, which reads exactly like a diagram that has none. It now returns
  `missing_rules:` and the block is recorded `unresolved: critique_unavailable` rather than
  passing.

### Changed

- **The critic's checklist learned the two glyph traps** that were the only real defects in
  the whole test run: arrow characters rasterizing as tofu, and hyphens drawing as long
  dashes. Both make the XML look perfect and the picture lie, so the blind critic is the only
  thing that can catch them.
- **The standing-rule item no longer invites confabulated gradients** — the one false defect
  of the run. Paired with a general rule: report only what you could point at with a finger.
  The renderer cannot catch a wrong defect, by design — it acts on it.

## [0.58.0] — 2026-07-15

Step 6 (Polish) reviewed diagrams it could not actually see, and re-rendered diagrams
that hadn't changed. This release fixes both, and removes a rasterizer that was quietly
corrupting every image the pipeline produced.

### Added

- **A fixture Talk for the whole Step-6 pipeline** at `tests/skills/ascii-to-svg/` — nine
  slides lifted verbatim from production Talks, spanning 1.4:1 to 7.9:1 plus a
  no-`ascii-note` block and a legacy-tagged fence. Its `test_audit_aspect.py` holds the
  audit's real regression tests: synthetic, deliberately broken, required to *fail*.
- **Standing font rules in `config/diagram-style.md`**: arrow glyphs (`←` `→` `↑`,
  U+2190-21FF) rasterize as **tofu** — absent from the fonts cairosvg resolves — so arrows
  must be drawn as paths. And `Menlo` is a trap: it resolves, so nothing errors, but its
  hyphen draws at near-full-em width, turning `a-b` into `a–b` and fusing YAML `---` into
  one rule. Both produce a correct-looking XML and a lying picture.
- **A blind diagram critic.** Visual review of a rendered diagram now happens in its own
  `diagram-critic` subagent that receives the PNG and nothing else — no SVG path, and
  `tools: Read` so pixels are all it can reach. Previously the agent that *wrote* the SVG
  also critiqued it, which cannot work: with every coordinate already in context it
  reviewed by arithmetic rather than by eye, "confirming" text was centred by re-deriving
  the formula it had just used to place it. The critic now describes what it sees in visual
  language and the renderer, which has the coordinates, translates that into the edit.
- **A mechanical aspect audit** (`audit_aspect.py`), because one defect class is invisible
  to *any* visual review: the critique PNG is rasterized **from** the viewBox, so a viewBox
  that doesn't fit its art renders a correct-looking picture whose dead canvas reads as
  deliberate whitespace. It now surfaces at render time as an ordinary defect, with a
  suggested corrected viewBox that is a pure crop. It measures margins in viewBox units
  (ratio drift flags healthy diagrams), samples the background from the image corners
  (not hard-coded white), and claims only that the frame *fits the art* — `ok` never means
  "this was the right shape".

### Fixed

- **The viewBox contract taught the wrong method, and its self-check was a tautology.**
  Step 5 said to derive the aspect from the character grid; measured across the nine
  fixtures that diverged from the honest layout in six, by up to 2×. And the offered
  self-check (rasterize and compare) is true by construction, since the raster derives from
  the viewBox. Step 5 now says: lay out the art, measure the ink, add an even margin, and
  the viewBox is that rectangle.
- **Render idempotency was built but never armed.** `stamp-renders` — the step that writes
  the ASCII digest deciding what re-renders next pass — existed as a working subcommand but
  appeared in no sequence, so SVGs went unstamped, no digest ever matched, and every pass
  re-rendered a Talk whose ASCII hadn't changed — minutes instead of sub-second. It is now
  step 9 of the illustrator's loop.
- **`qlmanage` removed as a rasterizer.** It was the documented macOS fallback and was
  silently mangling output: `-s N` fits the art into an N×N square padded with *opaque
  white*, and its geometry disagrees with cairosvg's, placing ink 100px off at identical
  dimensions. **`cairosvg` is now required, with no fallback** — if it's missing the render
  fails and says how to install it.
- **`pip install cairosvg` was never sufficient on macOS**, which is why the fallback kept
  firing: the stock python3 can't see Homebrew's libcairo (dyld default paths exclude
  `/opt/homebrew/lib`, and SIP strips `DYLD_*`). All rasterization now goes through
  `rasterize.py`, which preloads the dylib by absolute path and re-measures every PNG
  against the viewBox before letting it reach disk.
- **`ascii-to-svg` looked for `diagram-style.md` in the wrong place** — `<repo_root>/config/`
  instead of `${CLAUDE_PLUGIN_ROOT}/config/`. The render didn't fail; it silently dropped
  the palette and reported `deviations: no diagram-style.md`.

### Changed

- **Critique cap lowered from 3 iterations to 2** (initial + 1 revision). Historically half
  the blocks land clean on the first pass and nearly all the rest on the second.
- **Diagram dispatch is a sliding window of 5, not fixed batches of 5** — a barrier parked
  up to four slots waiting on the slowest straggler.

## [0.57.0] — 2026-07-15

### Changed

- **Slides now animate by default.** Enumeration slides (`stat`, `card-row`,
  `concept-breakdown`, `icon-list`, `content+cards+image`) reveal their items one at a time
  in the HTML deck, and a slide's `highlights` arrive as one final step — so the takeaway
  lands after what it comments on. Animation used to be opt-in via `<!-- reveal: sequential -->`,
  which in practice meant decks never had any. The hint is now an opt-*out* —
  `<!-- reveal: together -->` shows a slide all at once. Old `sequential` hints keep working.
  Unchanged for `.pptx`, which is static; viewers can still switch every animation off from
  the deck's animations button.
- **The deck fills the window.** The 4% inset margin is gone, so a slide — and an `aside`
  column in particular — runs to the window's edge. Side bands in a non-16:9 window are
  letterboxing, not margin.

### Fixed

- **A slide's `aside` image column is full-bleed again.** The rules that make an inline
  figure look like a figure tied the aside's own rules on CSS specificity and quietly won.
  Note for authors: a **photo** aside crops to fill on its own, but an **SVG** aside must
  carry `preserveAspectRatio="… slice"` itself or it will letterbox.
- **Polish no longer attributes a discarded diagram to a real slide.** ASCII under
  `# Cut material`, `# Open questions`, or `# Thesis` was inherited by the preceding section —
  the scan only recognized `# N.`, `# Agenda` and `# Conclusiones` as boundaries. Any
  heading now ends a section, and ASCII under one that carries no slides is skipped and
  reported.
- **Polish no longer reuses a stale diagram, or one from another topic.** Re-render was
  decided from a filename prefix minted from position in `final.md`, which renames itself
  as soon as slides move. Each rendered SVG is now stamped with a digest of the ASCII it
  was drawn from (diagram + `ascii-note` intent), and that digest is the only thing
  consulted; an unstamped SVG re-renders rather than being trusted.

## [0.45.0 – 0.56.0] — 2026-07-13 → 2026-07-15

The HTML deck matured from a working renderer into the polished deliverable: viewer
chrome, richer slide semantics, the example talk, and the docs/workflow reorganization.

### Added

- **Aside image column.** `<!-- aside: ![alt](…) -->` under a slide heading devotes ~a third
  of the slide's width to a full-bleed edge image (right by default, `left` supported) on
  every content slide type — atmosphere, not information; readable figures stay in the body.
- **Highlights band.** Any content slide may carry `highlights` — emphasized takeaways in a
  soft accent band under the body, each with a `kind` (`takeaway`, `important`,
  `definition`, `example`, `quote`, `note`) carrying its own accent + icon; facts and
  highlights accept `{label,body}` labeled lines. The schema documents the "never drop
  content" rule: every source line is translated as a field, card, fact, or highlight.
- **`quiz` slide type.** Question + optional lettered choices shown up front; the answer
  reveals on next-nav, the named `correct` choice highlights in sync, with optional image
  and explanation. Static (visible) in `.pptx`.
- **Icons never repeat within a slide** — a distinct content-matched icon per item, with
  fill-suggested `icon` names honoured and a neutral fallback pool for unmatched labels;
  emoji stripping is a FILL rule (the matched icon stands in for the emoji).
- **Deck viewer chrome:** animations on/off toggle, PDF export and fullscreen buttons, an
  auto-hiding bottom nav cluster, and **six selectable styles** (`editorial`, `terminal`,
  `ocean`, `forest`, `sunset`, `business`) — one CSS file per style, composing with
  light/dark, persisted and shareable via `?deck-style=` / `?deck-theme=` URL params.
  Documented in the README's "Presenting the HTML deck" section.
- **Optional author hints in `draft.md`:** `<!-- template: <type> -->` and `<!-- reveal: … -->`
  under a slide heading — Polish copies them through and the FILL honours them (the only
  HTML comments read rather than dropped).
- **Example talk fixture** [`tests/examples/talksmith-intro/`](tests/examples/talksmith-intro/):
  a complete ~40-min talk *about* Talksmith exercising nearly every slide type, with its
  rendered HTML deck committed and linked from the README; its slide notes are written as
  documentation, not stage directions.
- **Institution logo setup.** Setup asks for your logo; drop it at `config/logo.*` and
  every rendered deck (HTML + PPTX) uses it, with a documented resolution order down to a
  neutral placeholder.
- **`/talksmith:init` also writes a `.gitignore`** — a marked, idempotent block ignoring
  regenerable `output/`, caches, and local settings; talk source stays tracked.
- Renderer chrome labels localize from `deck.lang` (was hardcoded Spanish).

### Changed

- **Workflow order: Polish (6) → Render (7, optional) → Learnings (8, mandatory)**, and the
  step is named just "Render" (it produces a `.pptx` *or* a shareable HTML/Reveal.js deck).
  The suffixed-output guarantee (`output/final.<style>.…`, canonical copy last) is stated in
  the orchestrator, not only the skill.
- **Docs overhaul — README is usage-first** (~300 → ~120 lines): Quickstart up top, one
  rendered workflow diagram, a reference-artifacts table; deep material moved to
  `docs/methodology.md`, `docs/roles.md`, `docs/reverse-pipeline.md`. Added the Karpathy
  "LLM wiki" framing for the corpus/memory/learnings knowledge base.
- **Slide-template catalog reorganized into 7 concept families** with a per-family
  selection signal — pure clarity, classification byte-identical. The Editor drafts with
  the taxonomy in mind (shape each slide's content to a family).
- **Layout polish:** three-card concept slides lay out 2-on-top + 1 full-width; stat slides
  pick column count from stat count; icons follow the active accent (`currentColor`);
  quieter section pill; soft highlight box on the image-top caption.
- **Style reference rebuilt as a self-documenting English deck** — every slide's copy
  explains the template it demonstrates.
- **License is MIT, consistent everywhere** (`LICENSE`, README, plugin + marketplace
  manifests).

### Fixed

- **Slide templates are self-contained** — each `.j2` reads its own `slide-model.json`
  fields directly; the Python field-renaming layer is gone, so a markup change is a
  one-file edit (see CLAUDE.md → *Adding a new slide type*).
- **Full-bleed HTML slides no longer overflow** — `quote`/`statement`/`closing-hero` gained
  a `fitCover()` shrink-to-fit pass; the closing-hero title was right-sized.
- **Content images always show in full** (size to their own aspect, never force-cropped);
  `image-top` captions stay in view; `comparison` uses the actual column count; icon-list
  label-only rows center their icon; colon lead-in labels render bold.
- **Polish provenance echo escapes `-->`** so ASCII arrows can't close the
  `<!-- ascii-source -->` comment early and leak onto the slide; `prepare-render-args`
  fails loud on a stale plan or missing `.ascii` sidecars instead of emitting invalid
  render args.
- **Per-skill consistency audit** reconciled every SKILL.md with its scripts.

### Removed

- **The html-strict critique/FEEDBACK cycle** — html-strict is a single-pass GENERATE; the
  presenter reviews the deck and resolves issues by editing the source.
- **Institution branding from the plugin** — the bundled Universidad Austral logo is gone;
  templates ship a neutral placeholder and the logo is repo-supplied (above).
- Dead renderer code: the orphaned `agenda` template (superseded by `section-agenda`) and
  never-applied CSS.

## [0.23.1 – 0.44.0] — 2026-07-13

The HTML renderer, built from scratch and then rebuilt model-driven: a code-rendered
Reveal.js deck that always emits the full styled layer, fed by an LLM-filled
`slide-model.json` shared with the PPTX path.

### Added

- **The code-rendered HTML deck** (`build_html.py` + `html_style.py`): a self-contained
  styled deck that always emits cards (never bullets), per-concept Material Symbols icons,
  callouts, and code surfaces — fixing the native-`.pptx` failure where the styled layer
  was silently dropped. Icons are content-matched against the **live Material Symbols
  catalog** (~4200 icons, cached), with a Spanish→English bridge and an offline seed
  fallback; a strict icon-coverage audit backs it.
- **Built on vendored, inlined Reveal.js**: Reveal owns navigation, deck-to-window scaling,
  the overview, transitions, **speaker notes** (`### Speaker notes` → `<aside class="notes">`),
  and **PDF export** (`?print-pdf`). The only custom presentation code is the per-slide
  content-fit, reworked so busy slides neither clip nor shrink into a centred block.
- **`slide-model.json`, the structured IR** ([`schemas/slide-model.md`](schemas/slide-model.md)):
  the `md-to-deck` FILL step has an **LLM decompose `final.md`** into per-slide
  `{template, …fields…, notes}`, and the renderer maps fields mechanically onto one Jinja
  template per slide type. The same model is the shared IR for the PPTX render and the
  live view, and the CONTROL audits validate against it instead of re-parsing markdown.
- **Slide-type growth:** `quote`, `timeline`, `big-number`, `pros-cons`, numbered steps,
  auto-detected `stat` slides, anaphora/enumerations as `icon-list`, and the
  `section-agenda` separator — the numbered roadmap re-shown at every section start with
  the active section accented, each row deep-linking to its section.
- **Deck identity:** vendored IBM Plex Sans/Mono; a persisted Light/Dark theme toggle
  (`?deck-theme=`); every slide shows its section (pill or eyebrow); redesigned section
  dividers; the cover splits title and institution subtitle.
- **Canonical visual fixture** at `tests/skills/md-to-deck/` — one directive-forced slide
  per template plus edge cases, rendered to the committed `style-reference.html` so a diff
  shows any visual regression.

### Changed

- **Render modes consolidated and renamed: `pptx-strict`, `pptx-free-form`, `html-strict`**
  — three peers, with `md-to-deck/SKILL.md` rewritten around them and the audit suite
  consolidated into one CONTROL list. The html-strict renderer serves both the **live
  view** (`--draft`, auto-refreshed during review) and the **deliverable**
  (`output/html/index.html`).
- **Skill renamed `md-to-pptx` → `md-to-deck`** (it renders HTML too); the `pptx-*`
  reverse-pipeline skills keep their names.
- End-to-end render of a real 74-slide deck drove a fix wave: speaker-notes/`### Sources`
  blocks captured instead of leaking onto slides, literal markdown markers stripped, cover
  title band reserved, mojibake fixed.

### Removed

- **The separate `preview` render style and the Pillow wireframe renderer**
  (`build_preview.py` and friends) — the html-strict deck took over both the live-view and
  deliverable roles; the `preview/` style folder is deleted.
- **The regex classifier/parser** (`slide_model.py` heuristics, `curate.py` marker
  recovery) — superseded by the LLM FILL against a fixed field contract.
- **`convert.py`**, the markdown→prose pre-processor for the PPTX path — superseded by the
  shared `slide-model.json`.
- **The standalone `# Agenda` slide** — the roadmap re-shows at every section start, so a
  separate agenda slide added nothing. Authored duplicate cover slides are dropped too (the
  cover is synthesized from frontmatter).

## [0.10.0 – 0.19.1] — 2026-07-09 → 2026-07-12

The shared design system and a session start that actually boots.

### Added

- **The shared slide-template catalog**
  ([`config/pptx-styles/slide-templates.md`](config/pptx-styles/slide-templates.md)) — the
  single home for which template a slide is, when it applies, and its prescriptive Format,
  distilled from three real hand-built decks (131 slides, 0 bullet lists). Every render
  mode classifies each slide against it at GENERATE; the universal invariant — **labeled
  enumerations render as cards, never plain bullets** — holds in every mode. A signal
  glossary, discriminator order, and worked examples make classification deterministic;
  dry-running a real 74-slide deck closed the gaps so **every slide classifies** into a
  real template.
- **The layered design bar:** `visual-guidance.md` (the medium-agnostic floor: principles +
  hard must-never-happen defects), `slide-design.md` (the per-slide visual-transformation
  mandate the critique enforces), and `render-modes.md` (the phase × format → action matrix
  centralizing per-format render config that had drifted across ~6 files).
- **Every render writes a template-decision log** beside its output — per slide: the
  template chosen, why, the raw signals, and flags.
- **`concept-breakdown` carries a per-concept icon by default**, with balanced card
  content; any source image disqualifies the template. **Speaker-notes coverage is
  audited**, so a forgotten notes stage can't ship silently.

### Changed

- **The session start is reliable.** The stub (`talksmith-orch.md`) now *forces* the spec
  to load and the workflow to start: verify `orchestrator.md` is in context and Read it
  explicitly if the `@`-import didn't resolve (Cowork doesn't expand it), then execute
  Step 0 — the self-introduction + new-vs-resume ask — as the first response no matter what
  the user typed, folding their message into Step 1. All evolving behavior lives in
  `orchestrator.md`, which reloads fresh every session; the stub stays stable.
- **Free-form honors the shared design bar at GENERATE**, staying single-pass — its freedom
  is scoped to visual execution. The strict spec's duplicated layout guidance was
  consolidated into the catalog; strict keeps only its EMU realizations.

### Fixed

- **The shipped base-template covers were re-authored in Helvetica** so the
  system-fonts-only palette audit and the cover-fidelity audit stop contradicting each
  other on the shipped asset (they made every strict render fail one or the other).
- **HTML-comment stripping is line-based**, so `-->` arrows inside preserved ASCII can
  never close an `ascii-source` block early and spill onto the slide.

## [0.2.0 – 0.9.2] — 2026-07-09

The reverse pipeline, the learning loop, and the render-QA foundations.

### Added

- **The reverse pipeline** — reconcile an externally-edited `.pptx` back into `draft.md`,
  all artifacts under `talks/<Talk>/reconcile/`: **`pptx-extract`** (python-pptx; rebuilds
  the deck as `draft.md`-shaped Markdown + inventory), **`pptx-diff`** (stdlib; explains
  every title/content/note/image change vs `final.md`), **`pptx-merge`** (auto-applies the
  simple high-confidence changes to `draft.md`, routes complex ones to the Editor).
- **`pptx-learn`** (strict-only) — mines a presenter's hand-corrections into candidate
  conformance patterns: `learn_patterns.py` diffs the edited deck's per-shape geometry
  against the as-generated baseline (`output/final.generated.geometry.json`), the LLM
  judges which deltas are generalizable template rules vs content one-offs, survivors land
  in `config/strict-learnings.md` for human promotion into the declarative
  `conformance-patterns.md`. Runs auto after `pptx-merge` and on-demand.
- **The categorized critique rubric** — CONTENT / AESTHETIC / DISTRIBUTION /
  LAYOUT-CONFORMANCE (strict-only), each concern checked in exactly one place, enriched
  with established design guidance.
- **Per-mode output isolation** (`output/final.<style>.pptx`, latest copied to the
  canonical `final.pptx`) and **live per-phase render progress** in every mode — no more
  opaque multi-minute dispatches; any phase silent >60s surfaces as a stall.

### Fixed

- **Working-meta never leaks onto slides** (section goals, narrative arc, presenter
  feedback) — stripped in every render mode, with the hard rule that the render authors
  from the intermediate and never re-parses `final.md` raw.
- **Deep contradiction sweeps** left the render instructions internally consistent across
  all modes: the base-template delete range corrected to 3–15 (a real render bug), audit
  membership reconciled per mode, the "no python-pptx" wording fixed (driving the native
  skill's python-pptx-from-base-template workflow is required; *bypassing* it is
  forbidden), and every dangling cross-reference repaired.
- **Section dividers stopped vanishing** — a trailing stripped field could swallow the
  following `# N.` divider; field bodies now terminate at the next rule or heading.

*(A Step-5.5 "draft preview" was also built in this band — first a throwaway `.pptx`, then a
code-only Pillow wireframe — later superseded by the live HTML view; see the band above.)*

## [0.1.0]

Initial plugin release: the Presenter Agent orchestrator, five subagents
(Librarian, Composer, Editor, Illustrator, Global-Librarian), the `/talksmith:init`
command, and the forward-pipeline skills (`ingest`, `ascii-to-svg`, `polish-ascii`,
`feedback-cycle`, `md-to-deck`) driving the 8-step workflow from raw sources to
`draft.md`, `final.md`, and an optional `.pptx`.
