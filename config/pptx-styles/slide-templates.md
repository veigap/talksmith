# Slide templates — the shared layout catalog (single source of truth)

This file is the **one authoritative home for slide-template guidance**: what templates
exist, the **prescriptive rule for matching each** to a slide's content, and the
**prescriptive format each must take**. It is a **dual-consumer** file:

- **GENERATE** (every mode) — classify each slide against this catalog, then render the
  matched template following its *Format*.
- **FEEDBACK** (the critique) — the critique receives each slide's classified template id
  and reviews the slide **against that template's *Format* here**, not against a generic
  notion of "looks good."

All three render formats — `strict`, `free-form`, `preview` — use it. When nothing
matches, they fall back (`fallback` below).

> **This is the single home — do not duplicate.** The design-level template guidance that
> used to live in strict §7/§8/§13/§15.5, free-form's prose, and `slide-design.md`
> (when-to-pick rules, capacity thresholds, format-at-the-design-level, the
> card-not-bullet invariant) lives **here now**. Each spec keeps only what is genuinely
> substrate-specific: **strict** keeps its exact EMU measurements (base-template
> pixel-equivalence) and the `audit_layout_fit.py` gate, *realizing* the *Format* below;
> the **preview** keeps its Pillow render functions. Everything else references this file.

Evidence base: three real hand-built decks — the 53-slide `strict/template.pptx`
reference (`ref`), a 21-slide presenter-corrected deck (`final`), and a 57-slide
governance deck (`gov`). **0 plain bullet lists across all 131 slides.**

## Speaker notes are template-independent

Template choice governs only the **slide body**. **Every `### Notes` block in the source
is emitted verbatim into its slide's notes pane, for every template and every mode** —
no truncation, no dropping, never spilled onto the slide face (per
[`principles.md`](${CLAUDE_PLUGIN_ROOT}/config/principles.md) → *Speaker notes are the
talk*). Classification never moves prose from notes onto the slide, and `content-text`'s
"prose belongs in notes" flag is about *body* prose, not the notes pane. This is enforced
deterministically by `audit_notes_coverage.py` (CONTROL floor) in every mode that emits a
`.pptx`.

## The universal invariant — cards, not bullets

> **A set of parallel *labeled* concepts renders as cards / panels / figures, NEVER as a
> plain bullet list.** Plain unlabeled bullets are a rare last resort — a ≤3-item caveat
> aside under another template, nothing more. If a slide reads as "a title and some
> bullets," it is a mis-classified `concept-breakdown`, `card-row`, `icon-list`,
> `process`, or `figures`. This holds in every mode, at GENERATE and in FEEDBACK.

## Classification procedure (all modes)

Decide the template **from the content**, as a discriminator walk — not first-match:

1. **Collect surface signals** — is it slide 1 / the final slide? heading level (H1 vs
   H2); `![]()` image count; fenced ```` ``` ```` code block present?; count of *labeled*
   items (`- **Label** …`, `#### Label`/`### Subhead` + paragraph groups); is the label
   set **ordered** (`1.`/`Paso N`/`Step N`/`Fase N`/`A,B,C`)?; pipe-table present?;
   two symmetric groups (A-vs-B)?; a single dominant short line (≤ ~14 words) with no
   enumeration?; per-item body length; large standalone number/metric.
2. **Enumerate every catalog entry whose _Match_ fires.**
3. **Apply the disambiguators** (each entry's *Match* names what it is **not**) to pick
   **exactly one**. **Never fall to a plainer template** (plain bullets, raw table,
   `content-text`) when a richer one matches.
4. **No entry matches → `fallback`** (log it).

Strict additionally runs a **deterministic post-emit gate**
([`audit_layout_fit.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_layout_fit.py)):
emitted layout must equal the predicted template or the build fails. Free-form and
preview use the same classification judgment **without** the hard gate (free-form logs
its pick to `.layout-log.md`; the preview classifier selects the render function).

---

## Catalog

Each entry gives **Match** (precise fire conditions + disambiguators), **Format** (the
prescriptive layout — regions, counts, sizing, spacing, and what is forbidden), the
**Strict recipe** it binds to, and **Provenance**. Sizes are the shared design ladder
(strict encodes them as `sz="pt*100"`; the preview scales them to its 1280×720 canvas).
Content-area width ≈ 8.9 in; canvas 10×5.63 in (16:9).

### Frame templates

#### `cover`
- **Match:** slide 1 only; frontmatter present, no H2. Not a content choice.
- **Format:** Title (bold, 40–44 pt, top-left) + class/course line + author + date;
  optional hero image or logo at right. White background. No section pill.
- **Strict recipe:** §4. **Provenance:** ref S1, final S1, gov S1.

#### `agenda`
- **Match:** an H1-only slide (numbered section header). Re-shown before each section's
  first content slide. Not a content choice.
- **Format:** the heading "Agenda" + the full numbered section list; the **active
  section is accent-highlighted** (`#DA1B2E`), the rest muted `#3B3535`. **No body
  prose, no images.** All instances identical except which item is active. Warn if
  sections > 8 (tight) or > 10 (out of room).
- **Strict recipe:** §5. **Provenance:** ref S2/12/17…, final S4/7/14/18, gov S2/20/26….

#### `closing-cta`
- **Match:** the **final** slide (or a section's last), content = call-to-action /
  next-steps / resource links / modules.
- **Format:** title + a **2×2 (or 1×N) grid of resource cards**, each = name + URL +
  one-line descriptor. Not prose.
- **Strict recipe:** §13 closing-cta / §7.2 cards. **Provenance:** ref S53, final S21.

#### `closing-hero`
- **Match:** a terminal slide carrying **one or two words only** — "Q&A", "Gracias",
  "Thank you", "¿Preguntas?".
- **Format:** the single phrase set **very large (60–112 pt)**, centered or lower-left;
  optional small contact line. Nothing else.
- **Strict recipe:** none yet (new); emit as an oversized §3 title on a blank body.
  **Provenance:** gov S57 (111.5 pt "Q&A").

### Statement / emphasis templates

#### `statement`
- **Match:** the slide's message is **one bold claim, myth/reality, or short quote** —
  a single dominant line ≤ ~16 words, no enumeration, no code. Recurs as a series
  (e.g. myth-buster sequence).
- **Format:** the claim set **large (40–52 pt) Helvetica Bold**, occupying the upper-left
  ≈ 60% of the canvas; an optional supporting image at the right/bottom, or an optional
  one-line sub-statement (`#3B3535`, 18–22 pt) beneath. **No bullets, no cards.** The
  point is a single visual assertion. Distinct from `content-text` (which carries
  several supporting facts) and `callout` (which sits *inside* another slide).
- **Strict recipe:** none yet (new); emit as an oversized §3 title + optional §3 subtitle
  + optional §12-aligned image. **Provenance:** gov S11–S19 (48–51 pt "ROMPEMITOS").

#### `callout` (inline, not standalone)
- **Match:** a **single** emphasized aside inside another slide — one `- <emoji>
  **bold lead** …` item, or a lone tip/warning/takeaway. A 1-item "list" is emphasis,
  never enumeration.
- **Format:** a rounded panel used **within** the host template:
  - **Pink `#F7BBC1`** — analogy / tip / warning / mnemonic (warm, "lateral"). Marker
    icon (lightbulb/warning/book) at left; body 11–11.5 pt.
  - **Blue `#B8E6F5`** — proven result / capability / key takeaway / forward-reference
    (cool, "declarative"). `info` marker; body 11–13 pt; bold lead-in; quantified figures
    inlined in `#DA1B2E` bold.
  Reserve the callout's height **before** laying out the body above it (§8.3), so its
  bottom never slides past the slide edge and silently drops. ≥3 estimated lines →
  surface as over-budget, do not shrink-fit.
- **Strict recipe:** §8.1 / §8.2 / §8.3. **Provenance:** ref S3/S7; pink `F9D2D6` recurs
  across all three decks.

### Enumeration templates — unordered labeled sets (cards, never bullets)

> The three below share the signal "lead + 3–5 labeled parallel items." Pick by **body
> length** and **count**; all forbid plain bullets.

#### `card-row`
- **Match:** lead paragraph + **3–5** labeled items (`- **Label** body`, `#### Label`+para,
  or `- <emoji> **Label:** body`), **each body ≤ ~80 chars** (1–2 short sentences).
  Parallel concept *summaries* ("three innovations", "four pillars", "five steps").
  **Not:** items needing prose (→ `icon-list`); items each with an image (→ `figures`);
  >5 items (split slides); ordered steps (→ `process`).
- **Format:** section pill + title + full-width lead (12 pt) + a **single horizontal row
  of N equal-width cards** (N∈{3,4,5}). Per-card width = `(8.9 − (N−1)×0.22)/N`
  (N=3→2.82, N=4→2.06, N=5→1.60 in); gutter 0.22 in; row height ≈ 1.85 in. Each card =
  `#DA1B2E` icon chip (content-matched glyph, **different per card**) + heading
  (13.5 pt Bold) + 2–3-line body (11 pt). Optional italic source line at 5.30 in. At N=5
  bodies must be ≤ 60 chars; if they don't fit, use `icon-list` — never shrink the font.
- **Strict recipe:** §7.4 (+ §7.3 chooser). **Provenance:** ref (§7.4), final S13.

#### `icon-list`
- **Match:** lead + **3–5** labeled items, **at least one body > ~80 chars** (2–4
  sentences each). Parallel prose explanations ("three strengths", "four limitations").
  Pick by the **longest** item; never split one group across `card-row` and `icon-list`.
- **Format:** section pill + title (may wrap 2 lines) + full-width lead + a **vertical
  stack of N rows**. Stride = `(canvas_h − 3.10 − 0.30)/N` (N=3→0.74, 4→0.56, 5→0.44 in).
  Each row = line-art `#DA1B2E` icon (no chip, content-matched, **different per row**) at
  left + heading (13.5 pt Bold) + 2–3-sentence body (11 pt) to the right. Lead carries
  **no** icon slot. N=3/3-sentence comfortable; N=5 only with 1–2-sentence bodies; beyond
  → split slides.
- **Strict recipe:** §7.5 (+ §7.3 chooser). **Provenance:** ref (§7.5), final S11/12.

#### `concept-breakdown`
- **Match:** **3–N** parallel **labeled** concepts (`### Subhead`+short-para groups,
  4+ groups; or a labeled set that is neither a clean 3–5 row nor prose-heavy), **short
  bodies, no per-item image, unordered.** The general labeled-grid case.
  **Not:** ordered/numbered (→ `process`); each item has a figure (→ `figures`);
  exactly 3–5 with the lead+item shape (→ `card-row`/`icon-list`).
- **Format:** title + a **2×N or 3×N grid of equal cards**, each = label (13.5 pt Bold) +
  one-line body (11 pt), optional small icon. **Uniform card size**, consistent gutters
  (~0.2 in), shared gridlines, aligned rows. **Never bullets.** Up to ~6 cards; beyond →
  split.
- **Strict recipe:** §7.2 (plain cards) / §7.6. **Provenance:** ref S5/8/25/53, final
  S11/12/13, gov S22/24.

#### `stat`
- **Match:** the payload is **2–4 standalone metrics/figures** — big numbers with labels
  (`~750K tokens`, `$2.50/1M`, `Dice 0.95`, `50–90%`).
- **Format:** a row of **stat cards**, each = the **number set large (24–40 pt Bold, often
  `#DA1B2E`)** + a short label/unit beneath (11 pt). Equal size, aligned baselines. May
  appear as the lower band of a `content+image` slide (a stat pair).
- **Strict recipe:** §7.2 card variant with an enlarged number run. **Provenance:** ref
  S6 (📚~750K / 🏥~800K pair).

### Ordered templates

#### `process`
- **Match:** a **named/ordered sequence** — `1./2./3.`, `Paso N`, `Step N`, `Fase N`,
  `Etapa`, `Case A/B/C`, a decision flow, or a branching tree. Order carries meaning.
  **Not:** an unordered concept set (→ `concept-breakdown`).
- **Format:** **numbered/step cards**. Linear: §7.1 numbered card = outer card + left
  strip (`#F2EEEE`) + number (Bold) + heading + body, stacked with fixed stride
  (~0.69 in). Flow/tree: progressively **indented** step rows with small step markers and
  an optional worked example/panel on the opposite half (as in a decision cascade). The
  ordinal is the card's number/heading; the description is the body. The label **must not**
  render as an inline paragraph prefix — the sequence must be visually scannable as steps.
- **Strict recipe:** §7.1 / §7.6. **Provenance:** ref S13 (6 components), S30 (ToT tree),
  S44 (cascade), S47 (5 stages).

### Comparison

#### `comparison`
- **Match:** **two symmetric groups** set against each other — A-vs-B, before/after,
  single-model vs cascade, myth vs reality-pair, or a pipe-table of factor→A→B rows.
- **Format:** either **two equal columns** (left = A, right = B; parallel headings, equal
  weight/height) or a **compare-strip**: header row (Factor · A · B) + N aligned rows,
  rendered as a **card-per-row grid, never a native table**. Uniform column widths,
  shared gridlines. **Not** bullets.
- **Strict recipe:** §11 (pipe-table → card-grid) / two §7.2 columns. **Provenance:** ref
  S44 (compare-strip), S6 (pair).

### Visual templates

#### `content+image`
- **Match:** one main claim supported by **1–3** `![]()` images; the prose leads, the
  images are evidence.
- **Format:** text column (lead + a few short facts / a callout) on one half; **1–3
  images aligned to the text columns** on the other, **aspect preserved**, no full-bleed.
  Not a grid.
- **Strict recipe:** §13 content+image. **Provenance:** ref S6/19/20, final
  S3/9/15/16/17/20, gov case-study slides.

#### `content+cards+image`
- **Match:** labeled **cards/steps on one side AND a supporting image/example/code on the
  other** — the hybrid (strict's own 4th type). Both a card set *and* a single evidence
  visual.
- **Format:** ~50/50 split: cards or a numbered list on one half + one supporting
  image/worked-example/code panel on the other, aligned to a shared baseline.
- **Strict recipe:** §13 content+cards+image (§7 cards + §12 image). **Provenance:** ref
  S7, S30, S42.

#### `figures`
- **Match:** a **visual set** where **each item carries its own image/diagram** — ≥3
  `![]()` interleaved with per-item labels.
- **Format:** optional lead line + N **figure cards** = image + label + short body, in a
  row or grid; **uniform crop, uniform size, aligned**. Distinct from `concept-breakdown`
  only by the per-item image.
- **Strict recipe:** §13 image-grid / content+cards. **Provenance:** ref S9/22, final
  S2/5/6/8/21.

#### `image-grid`
- **Match:** **≥4** `![]()` images where the **visual variety itself is the message** —
  output samples, before/after across cases, a portfolio. The reader scans the grid as one
  composite.
- **Format:** a **dense 2×N or 3×N image grid**, uniform cell size and gutters, minimal
  per-image text. **Not** for a list of items that merely each have an icon (→ `icon-list`).
- **Strict recipe:** §13 image-grid. **Provenance:** ref S10/31/33–38/44, gov S40/43.

### Special / last-resort

#### `code-example`
- **Match:** a fenced code block is the **primary** content (worked snippet, API shape,
  config, before/after diff) meant to be read.
- **Format:** a **monospace (Courier New) code surface** on ~45% (fill `#F2F2F2`, syntax
  colors keyword `#D73A49` / string `#005CC5` / comment `#6A737D`) + a 2–3-sentence
  explanation column on the other ~45%. Optional pink outer frame marks before/after.
  Code as an un-read cited artifact → screenshot or notes, not this template.
- **Strict recipe:** §9. **Provenance:** ref S13/14/24/43, final code slides.

#### `content-text`
- **Match:** **last resort** — a slide that genuinely carries only prose (a definition, a
  framing) with no visual, no enumeration, no code. Appears ~1× in 53 source slides.
- **Format:** one lead statement (larger) + 2–4 short supporting statements as **light
  panels or a stat strip — not a paragraph, not bullets.** **Flag as a restructure
  candidate** in FEEDBACK: most "wall of prose" slides are `card-row`/`icon-list`/
  `content+image` in disguise.
- **Strict recipe:** §13 content-text. **Provenance:** ref S41, final S10/19.

#### `fallback`
- **Match:** content matching no entry above.
- **Format:** the mode's default flow (lead + supporting), **still card/panel over
  bullets**; log that fallback was used so the gap can be added to the catalog later.

---

## Disambiguation quick-reference

| If the slide is… | and… | → |
|---|---|---|
| a labeled set | ordered (steps/1./Paso) | `process` |
| a labeled set | each item has an image | `figures` |
| a labeled set | 3–5 items, bodies ≤ 80 chars | `card-row` |
| a labeled set | 3–5 items, prose bodies | `icon-list` |
| a labeled set | otherwise (grid of short concepts) | `concept-breakdown` |
| numbers/metrics | 2–4 big figures + labels | `stat` |
| two groups | A vs B / before-after / factor table | `comparison` |
| images | ≥4, variety is the message | `image-grid` |
| images | 1–3 supporting prose | `content+image` |
| cards **and** an image | hybrid | `content+cards+image` |
| one big claim | ≤16 words, no enumeration | `statement` |
| one emphasized aside | inside another slide | `callout` |
| only prose | no visual, no enumeration | `content-text` (flag) |
| code | meant to be read | `code-example` |
