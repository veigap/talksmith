# Slide templates — the shared layout catalog (single source of truth)

This file is the **one authoritative home for slide-template guidance**: what templates
exist, the **prescriptive rule for matching each** to a slide's content, and the
**prescriptive format each must take**. It is a **dual-consumer** file:

- **GENERATE** (every mode) — classify each slide against this catalog, then render the
  matched template following its *Format*.
- **FEEDBACK** (the critique) — the critique receives each slide's classified template id
  and reviews the slide **against that template's *Format* here**, not against a generic
  notion of "looks good."

All three render formats — `pptx-strict`, `pptx-free-form`, `html-strict` — use it. When nothing
matches, they fall back (`fallback` below).

> **This is the single home — do not duplicate.** The design-level template guidance that
> used to live in strict §7/§8/§13/§15.5, free-form's prose, and `slide-design.md`
> (when-to-pick rules, capacity thresholds, format-at-the-design-level, the
> card-not-bullet invariant) lives **here now**. Each spec keeps only what is genuinely
> substrate-specific: **strict** keeps its exact EMU measurements (base-template
> pixel-equivalence) and the `audits/layout_fit.py` gate, *realizing* the *Format* below;
> the **html-strict** render uses its Jinja templates (`templates/html/*.j2`). Everything else references this file.

Evidence base: three real hand-built decks — the 53-slide `pptx-strict/template.pptx`
reference (`ref`), a 21-slide presenter-corrected deck (`final`), and a 57-slide
governance deck (`gov`). **0 plain bullet lists across all 131 slides.**

## Speaker notes are template-independent

Template choice governs only the **slide body**. **Every `### Notes` block in the source
is emitted verbatim into its slide's notes pane, for every template and every mode** —
no truncation, no dropping, never spilled onto the slide face (per
[`principles.md`](${CLAUDE_PLUGIN_ROOT}/config/principles.md) → *Speaker notes are the
talk*). Classification never moves prose from notes onto the slide, and `content-text`'s
"prose belongs in notes" flag is about *body* prose, not the notes pane. This is enforced
deterministically by `audits/notes_coverage.py` (CONTROL floor) in every mode that emits a
`.pptx`.

## The universal invariant — cards, not bullets

> **A set of parallel *labeled* concepts renders as cards / panels / figures, NEVER as a
> plain bullet list.** Plain unlabeled bullets are a rare last resort — a ≤3-item caveat
> aside under another template, nothing more. If a slide reads as "a title and some
> bullets," it is a mis-classified `concept-breakdown`, `process`, or `figures`.
> This holds in every mode, at GENERATE and in FEEDBACK.

## Classification procedure (all modes)

Decide the template **from the content**, as a discriminator walk — not first-match:

1. **Collect surface signals.** Detect each of these on the slide unit (an H2 block and its
   body). Detection must be identical across modes — the definitions below are the contract:

   | Signal | How to detect it (precise) |
   |---|---|
   | `is_cover` | The unit is slide 1 / has frontmatter and no H2. |
   | `is_divider` | The heading is an **H1** (`# …`), not an H2 — the canonical signal. **Also** a slide whose title carries an explicit section-break marker (`〔divisor〕`, `〔Backup〕`, or equivalent) even at H2: some authoring conventions mark dividers/backups by marker rather than heading level, and the pipeline must treat these as dividers, not content slides. |
   | `is_terminal` | The unit is the last slide of the deck or of a section. |
   | `n_images` | Count of `![alt](path)` refs in the body. |
   | `has_code` | A fenced ```` ``` ```` block is present as body content. |
   | `has_table` | A Markdown pipe-table (`\| … \| … \|` with a `---` separator row) is present. |
   | `labeled_items` | Count of **labeled** units: a bullet whose lead is bold (`- **Label** body` / `- <emoji> **Label:** body`), an `#### Label` / `### Subhead` immediately followed by a short paragraph, **or** a **numbered-list line** (`1. …`) when there are ≥2 of them (each line is an ordered step item, label optional). A *labeled* item ≠ a plain `- text` bullet. |
   | `is_ordered` | Any labeled item's label matches an ordinal: `1.`/`2.`, `Paso N`, `Step N`, `Fase N`/`Fase I`, `Etapa …`, `Case A`/`Caso A`, `Phase N`, or the items form a numbered list / a stepwise/decision flow. |
   | `body_len` | Per-item body length in characters, post-Markdown-strip. "Short" ≤ ~80 chars; "prose" > ~80. Judge by the **longest** item. |
   | `two_groups` | The body splits into **two symmetric groups** compared against each other (A-vs-B, before/after, myth/reality), or a pipe-table of `factor \| A \| B` rows. |
   | `big_metrics` | 2–4 standalone numbers/metrics with labels (`~750K tokens`, `$2.50/1M`, `Dice 0.95`, `50–90%`). |
   | `one_claim` | A single dominant assertion (≤ ~16 words) with no ≥2-item enumeration, no code, no image set — optionally followed by a **short reveal / one counter-point** (e.g. a `Mito → Realidad` myth-buster, a claim + its one-line answer). The claim, not a list, is the slide. |
   | `one_two_words` | The whole slide is 1–2 words (`Q&A`, `Gracias`). |
   | `is_voiced` | The dominant line is **someone else's words**: a `>` blockquote, a line wrapped in quotation marks, and/or an attribution line opening `—`/`–` or naming a source (`Anthropic:`, `— Ana Pérez, CISO`). A claim in the presenter's own voice is not voiced. |
   | `is_question` | The title or the body's dominant line **asks** something the slide then answers — a `¿…?`/`…?` line followed by its resolution, a `Pregunta … Respuesta …` split, or multiple-choice options (A/B/C/D). A rhetorical question with no answer on the slide does **not** count. |
   | `date_labels` | ≥2 labeled items whose **labels are dates or periods** (`2023`, `Marzo 2023`, `Q1`, `20 días después`, `Semana 3`). *When* is what the labels carry. |
   | `polarity` | The two groups are explicitly **upside vs downside**, not just A vs B — `Ventajas`/`Riesgos`, `Pros`/`Contras`, `Beneficios`/`Limitaciones`, `Qué gana`/`Qué cuesta`. |
   | `one_metric` | **One** dominant figure is the whole slide (`$2.50`, `18%`, `1M`) with a one-line caption and nothing else competing. (2–4 figures is `big_metrics`.) |
   | `is_cta` | A terminal (or section-terminal) slide whose items are **next steps / resources / links / where-to-go** — names + URLs + one-line descriptors, not concepts. |
   | `image_only` | `n_images ≥ 1` and the body carries **no prose and no enumeration** beyond the title — a screenshot or diagram the presenter narrates, its detail in `### Notes`. An explicit "just the image" author instruction produces exactly this. |

2. **Enumerate every catalog entry whose _Match_ fires** given those signals.
3. **Apply the disambiguators** (each entry's *Match* names what it is **not**) to pick
   **exactly one**. The decisive discriminators, in order (first match wins **only** after
   the richer-template rule — never fall to a plainer template when a richer one fits):
   - `is_divider` → `section-agenda` if the title names a `deck.sections` entry (the
     roadmap has a position to highlight), else `divider`.
   - `has_code` → `code-example` (before anything else — code dominates).
   - `is_question` (the slide asks and then answers) → `quiz`. Before the enumeration rules:
     multiple-choice options are *choices*, not a labeled set.
   - `is_voiced` (someone else's words carry the slide) → `quote`, **not** `statement`.
   - `one_metric` → `big-number`; `big_metrics` (2–4 standalone numbers are the payload) → `stat`.
   - `has_table`: **2–3 comparable value-columns** (A-vs-B, before/after, or three options over
     shared factors) → `value-columns`; a **label/value or N-level/N-column** table →
     `concept-breakdown` (card-per-row grid), **not** `value-columns`. (A pipe-table is never a
     native `<a:tbl>`.) A table that also has **one shared supporting image** is still
     `value-columns`, with `image` + `layout` — the mirror of the `content+cards+image` rule one
     step down. The image is not a reason to reclassify, and the table is not a reason to drop the
     image: sending the slide to `content+cards+image` to keep the picture collapses each row into
     a single card body (`"A: … B: …"`) and loses the column alignment that is the whole point.
   - `two_groups` → `pros-cons` when `polarity` (the two groups are upside vs downside, and the
     colour-coding is the point), else `value-columns` (a neutral compare).
   - `labeled_items ≥ 2` and `date_labels` → `timeline` (the rail; *when* is the axis), else
     `is_ordered` → `process`. Check `date_labels` **first**: dated milestones are also ordered,
     so testing `is_ordered` first is what silently swallows every timeline into `process`.
   - `labeled_items ≥ 2`, each item has its own image → `figures`.
   - **`labeled_items ≥ 2` and exactly one shared supporting image → `content+cards+image`.**
     The labeled set stays a card set; the image sits beside it. Do **not** dissolve the labels
     into `content-image` `facts` (they lose their per-concept icon) and do **not** drop the
     image to keep `concept-breakdown` — this hybrid exists precisely for this shape, and
     wanting the image on the left is a `layout` choice, never a reason to reclassify.
   - `labeled_items ≥ 2`, unordered, **and `images == 0`** → `concept-breakdown` (**including a
     2-item set** → two cards). It requires `images == 0` — any source image disqualifies it (its
     per-card icons are renderer-added, not source pictures). Then pick its `format` by count and
     body length: `row` for a lead + 3–5 short items, `list` for a lead + 3–5 prose items or an
     anaphora, `grid` otherwise. That is a **formatting** choice made after the template, not a
     second classification.
   - `labeled_items == 1` (a lead + one point) → `single-point`, or `callout` when that point is
     a **tone-carrying aside** (a tip, a warning, an analogy — the pink/blue panel *is* the
     message) rather than the slide's substance. If an image supports it → `content-image`.
     **Never a lone bullet under a title.**
   - `image_only` → **`image-full`** — the normal header, then the image edge to edge. Not
     `image-grid` (which wants ≥4 images and treats variety as the message), and never an
     invented paragraph to justify a text column.
   - `n_images ≥ 4`, variety is the message → `image-grid`; `n_images` 1–3 supporting prose →
     `content-image`.
   - `one_claim` (a single dominant ≤ ~16-word assertion, optionally with a short reveal /
     one counter-point — e.g. a myth→reality slide) → `statement`.
   - `is_cta` (resources / next steps / links) → `closing-cta`; `one_two_words` + `is_terminal`
     → `closing-hero`.
   - only prose, none of the above → `content-text` (flag as restructure candidate).
   **Never fall to a plainer template** (plain bullets, raw table, `content-text`) when a
   richer one matches. The same rule applies *within* a walk step: when two entries both fire,
   take the one that keeps more structure — a card set over a fact list, a timeline over a
   step list, a quote over a statement.
4. **No entry matches → `fallback`** (log it).

See **Matching examples** below for worked classifications, including the tricky ties.

Strict additionally runs a **deterministic post-emit gate**
([`audits/layout_fit.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/layout_fit.py)):
emitted layout must equal the predicted template or the build fails. Free-form and
html-strict uses the same classification judgment **without** the hard gate (free-form logs
its pick to `.layout-log.md`; html-strict selects the matching template).

---

## Catalog

Each entry gives **Match** (precise fire conditions + disambiguators), **Format** (the
prescriptive layout — regions, counts, sizing, spacing, and what is forbidden), the
**Strict recipe** it binds to, and **Provenance**. Sizes are the shared design ladder
(strict encodes them as `sz="pt*100"`; html-strict scales them to its 1280×720 canvas).
Content-area width ≈ 8.9 in; canvas 10×5.63 in (16:9).

### Concept families — the two-level view

The catalog is **two levels**. Every slide first belongs to a **family** — *what it is
doing* — and within that family the specific template is a **sub-category** chosen by **one
signal** (count, body length, dates, colour, image-pairing). Classify by picking the family
first, then reading that single discriminator; the detailed *Match*/*Format* for each
sub-category follows, grouped by family.

| Family — what the slide does | Sub-categories | Picks the sub-category by |
|---|---|---|
| **Frame** — structure, not content | `cover` · `section-agenda` · `divider` · `closing-cta` · `closing-hero` | position in the deck (slide 1 / section header / final slide) |
| **One claim / emphasis** — a single message | `statement` · `quote` · `quiz` · `callout` | attributed/voiced → `quote`; question→answer → `quiz`; an aside *inside* another slide → `callout`; else `statement` |
| **Labeled set** — parallel labeled concepts (cards, never bullets) | `single-point` · `concept-breakdown` | **count**: exactly 1 item → `single-point`; any set of 2+ → `concept-breakdown`, whose `format` (grid / row / list) is then picked by count + body length |
| **Ordered sequence** — order carries meaning | `process` · `timeline` | date/period labels → `timeline`; else `process` |
| **Metrics** — standalone numbers | `big-number` · `stat` | 1 hero figure → `big-number`; 2–4 figures → `stat` |
| **Aligned columns** — parallel values, read across | `value-columns` · `pros-cons` | a decision framed upside/downside (colour-coded) → `pros-cons`; 2–3 parallel value columns → `value-columns` (which may carry one supporting image) |
| **Visual** — images carry the content | `image-full` · `content-image` · `content+cards+image` · `figures` · `image-grid` | **one image and no prose → `image-full`**; 1–3 supporting prose → `content-image`; cards + 1 image → `content+cards+image`; each item imaged → `figures`; ≥4 where variety is the point → `image-grid` |
| **Verbatim / last-resort** | `code-example` · `content-text` · `fallback` | code meant to be read → `code-example`; only prose → `content-text`; nothing matches → `fallback` |

The signal *definitions* are in *Classification procedure* above; the row-level tie-breaks
are in *Disambiguation quick-reference* below. This overview is the map; those two are the
precise rules.

> **Reveal, on by default.** With no author action, the HTML deck steps through a slide on click
> (Reveal fragments): every enumeration slide (`stat`, `concept-breakdown`,
> `content+cards+image`) reveals its items **one at a time**, and a slide's
> **closing** `highlights` band then lands as **one final step** — so the takeaway below the body
> arrives after what it comments on, instead of being readable before the presenter gets there. To
> show a whole slide at once instead, carry `reveal: together` — set from an author
> `<!-- reveal: together -->` hint. The `.pptx` render is static and shows everything at once
> regardless. Viewers can also toggle every fragment off at runtime from the deck's animations
> button, so `together` is for slides whose parts must be read as one, not for viewer preference.
>
> **Optional highlights — two bands, one piece.** Any content slide may carry `highlights`: one or
> more emphasized lines in an accented band, each with its own `kind` (colour + icon at the left).
> Each entry also chooses its `position`. A **remark** — it comments on, concludes or qualifies the
> body — sits in the band **below** it (`bottom`, the default) and reveals last. A **frame** — a
> voiced line that sets the theme, a definition the items depend on, a warning that has to land
> first — sits in the band **above** the body (`top`) and is **visible from the moment the slide
> opens**, because a frame that arrives last frames nothing. Both bands are the same component in a
> different place: same classes, same per-`kind` colour and icon. A slide may carry both.
>
> **Optional layout.** A slide that pairs a body with **its own** supporting image
> (`content-image`, `content+cards+image`, `process`/`quiz` with an image) may carry `layout` to
> place that image: `text-left` (default), `image-left` (mirrored, so the image is read first), and
> on `content-image` also `image-top` (stacked). It is a *composition* choice made **after** the
> template — never a reason to pick a different template (full contract:
> [`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)).
>
> **Optional aside.** Any slide type in this catalog *except* the full-bleed ones (`cover`,
> `divider`, `statement`, `quote`, `closing-hero`) and the image-owning ones (`content-image`,
> `figures`, `image-grid`, `image-full`, `content+cards+image`, `process` with an image) may carry
> `aside: {image, side}` — set from an author `<!-- aside: [left|right] ![alt](path) -->` hint. It
> renders the image as a **full-bleed column down that edge** (default `right`, ~37% of the width),
> with the title and body in the remaining width. It is **visual reinforcement** — an evocative
> image that sets the tone — and it crops to fill, so it must never carry information the audience
> has to read. Content that must be read goes to an image-owning template instead.

### Frame — structure, not a content choice

#### `cover`
- **Match:** slide 1 only; frontmatter present, no H2. Not a content choice.
- **Format:** Title (bold, 40–44 pt, top-left) + class/course line + author + date;
  optional hero image or logo at right. White background. No section pill.
- **Strict recipe:** §4. **Provenance:** ref S1, final S1, gov S1.

#### `section-agenda`
- **Match:** an H1-only slide (numbered section header). Re-shown before each section's
  first content slide. Not a content choice.
- **Name:** the `template` value is **`section-agenda`** — spell it exactly. (`agenda`
  alone is the *source* block in `draft.md`/`final.md` that feeds `deck.sections`; it is
  not a template value and renders as `fallback`.)
- **Format:** the heading "Agenda" + the full numbered section list; the **active
  section is accent-highlighted** (`#DA1B2E`), the rest muted `#3B3535`. **No body
  prose, no images.** All instances identical except which item is active. Warn if
  sections > 8 (tight) or > 10 (out of room).
- **Strict recipe:** §5. **Provenance:** ref S2/12/17…, final S4/7/14/18, gov S2/20/26….

#### `divider`
- **Match:** a section break that is **not** one of the deck's `deck.sections` entries —
  an H1 (or a `〔divisor〕`/`〔Backup〕`-marked heading) that opens a sub-part *within* a
  section, so there is no roadmap position to highlight. The discriminator against
  `section-agenda` is exactly that: title names a `deck.sections` entry → `section-agenda`;
  it doesn't → `divider`. Not a content choice.
- **Format:** the title alone, full-bleed, no roadmap, no body prose, no images. A beat of
  visual silence between sub-parts — if it wants a claim, it is a `statement`; if it wants
  the section list, it is a `section-agenda`.
- **Strict recipe:** §5 (section break, roadmap omitted).

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

### One claim / emphasis

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

#### `quote` (pull-quote, full-bleed)
- **Match:** the slide **is a quotation** in someone's voice — a dominant quoted line
  (optionally with an attribution line starting `—`/`–`). A claim in the *presenter's* voice
  is a `statement`; a quote is attributed / voiced. **Fires on `is_voiced` on its own** — a
  blockquote, quotation marks or a named source is enough, no hint required; `<!-- template:
  quote -->` only pins it. *(A voiced line that **frames** another slide's body is not this
  template at all: it is a `highlights` entry with `kind: quote`, `position: top`.)*
- **Format:** full-bleed, vertically centred: a large accent quotation mark, the quote in
  large bold (≤~35 words), then a muted `— attribution` line. No cards, no header pill body.
- **Provenance:** gov deck testimonial slides; common in Gamma-style decks.

#### `quiz` (question → revealed answer)
- **Match:** the slide **poses a question and then answers it** — a quiz/check-for-understanding
  or a myth-as-question. Signals: a `### Content` (or title) that is a question, an explicit
  `<!-- template: quiz -->` hint, or a body split into a prompt + its resolution (often
  "Pregunta … Respuesta …", multiple-choice options A/B/C/D, or "¿…? → …"). **Not:** a bare
  assertion with no question (→ `statement`); a quoted line (→ `quote`); a list of parallel
  facts (→ enumeration templates).
- **Format:** section pill + optional topic title; the **question set large** (Bold, ~24–28 pt),
  optional **carded choices** (A/B/C/D) beneath, then a distinct **answer panel** — light-pink
  `#F9D2D6`, red left-accent, an uppercase red "RESPUESTA" label — carrying the answer (Bold) and
  an optional one-line explanation. An optional **image sits at the right** (contained, sized to
  its own aspect — never cropped), splitting the slide into text-left / image-right. **In the HTML
  deck the reveal is a Reveal fragment:** the question (and choices) render immediately, and on the
  *next* navigation the answer fades up (`fade-up`) **while the `correct` choice highlights in sync**
  (accent fill + check, via a Reveal *custom* fragment) — so the audience votes first, then sees
  both the right choice and the why. Space for the answer is reserved up front so the question
  never jumps.
- **Strict recipe:** none yet. `.pptx` is static (no reveal), so render the answer panel visible
  in place — same layout, just always shown. **Provenance:** the *seguridad-governance-ai* deck
  (a quiz per page).

### Labeled set — parallel labeled concepts (cards, never bullets)

> **One shape, one entry.** A set of parallel labeled items is a *single* classification decision;
> how it is arranged is a `format` field, not a different template. This used to be three catalog
> entries (`concept-breakdown`, `card-row`, `icon-list`) whose Match rules differed only by item
> count and body length — three rules for one shape, and the family the fill misclassified most.
> The only count that still changes the *template* is **exactly 1**, which is `single-point`
> (emphasis, not enumeration). All forbid plain bullets.

#### `concept-breakdown` — the labeled set
- **Match:** **2–N** parallel **labeled** concepts (`- **Label** body`, or `### Subhead` /
  `#### Label` + short-para groups), **unordered**, **no per-item image**. The default home for any
  labeled set of 2+ items that isn't ordered (→ `process`/`timeline`) or per-item-imaged
  (→ `figures`). A **2-item** set is valid (two cards) — do **not** drop it to bullets or prose.
  **Hard rule — no source image.** Its per-card icons are renderer-added §17 glyphs, never source
  pictures. **If the slide has any `![]()` image, it is NOT this** → `figures` (a per-item image),
  `content-image` (1–3 supporting prose), or `content+cards+image` (a card set + one shared image).
  **Not:** ordered/numbered (→ `process`); exactly one item (→ `single-point`).
- **Accepted ids.** `card-row` and `icon-list` remain valid `template` values and simply select
  their own `format` below, so decks and models written against them keep rendering unchanged.
  New models should emit `concept-breakdown` and set `format` when the default isn't right.
- **Format** — the arrangement is the `format` field; **pick it by count and body length**, the
  same rule that used to pick between the three templates:

  | `format` | When | Layout |
  |---|---|---|
  | `grid` *(default)* | short bodies, any count 2–6 | a grid of **equal cards**, each = a content-matched icon **above** a label (13.5 pt Bold) + a one-line body (11 pt). 2 → side by side; 3 → a row; 4 → 2×2; 5–6 → 3×N. Beyond ~6 → split the slide. |
  | `row` | a lead + **3–5** items, **every body ≤ ~80 chars** | a **single horizontal row** of N equal-width cards, each headed by a filled accent **chip** icon. Parallel concept *summaries* ("three innovations", "four pillars"). At N=5 bodies must be ≤ 60 chars; if they don't fit, use `list` — never shrink the font. |
  | `list` | a lead + **3–5** items, **at least one body > ~80 chars** | a **vertical stack** of N rows, each = a line-art icon at the left + heading + a 2–4-sentence body to the right. Judge by the **longest** item; never split one group across `row` and `list`. Also the home for a short **anaphora** (2–5 short parallel lines with no bodies — "No hubo hackers. No hubo malware.") so those don't fall to `fallback`. |

  The **per-concept icon is standard, not optional** — a concept is *anchored by its icon*, and it
  is **different per item**. A plain, iconless grid is a fallback only for a dense 5–6-item set or
  when no sensible glyph fits. Uniform card + icon size, consistent gutters (~0.2 in), shared
  gridlines, aligned rows. **Never bullets.**
- **Strict recipe:** §7.2 card + §7.2.1 per-card icon (ref S8 geometry) / §7.6 — `row` is §7.4 and
  `list` is §7.5 (+ §7.3 chooser); icon chosen per §17.5. **Provenance:** ref S8/S27/S49 (icon'd),
  S5/S25/S53 (dense/plain fallback), final S11/12/13, gov S22/24.

#### `single-point` — exactly one labeled item (lead + one point)
- **Match:** a slide whose body is a lead/prose paragraph plus **exactly one** labeled item
  or emphasized point (a single `- **Label** …`, a lone bold takeaway, or a one-line
  reveal). Very common (a claim + its one supporting beat). **Not:** 2+ labeled items
  (→ `concept-breakdown`); a bare emphasized aside with no host content (→ `callout`); a
  single ≤16-word claim with no supporting prose (→ `statement`).
- **Format:** the lead as the slide's body (a short statement or 1–2 sentences) + the single
  point rendered as **one card/panel or a callout**, never a lone bullet floating under a
  title. If an image supports it → `content-image` with the point as a caption card. The
  rule: one labeled point is *emphasis*, so give it a shape (card/callout), not a bullet.
- **Strict recipe:** §7.2 single card or §8 callout. **Provenance:** gov S36/38/42–47
  (many "one claim + one beat" slides).

### Metrics — standalone numbers

> Numbers are the payload. One hero figure → `big-number`; a set of 2–4 → `stat`.

#### `stat`
- **Match:** the payload is **2–4 standalone metrics/figures** — big numbers with labels
  (`~750K tokens`, `$2.50/1M`, `Dice 0.95`, `50–90%`).
- **Format:** a row of **stat cards**, each = the **number set large (24–40 pt Bold, often
  `#DA1B2E`)** + a short label/unit beneath (11 pt). Equal size, aligned baselines. May
  appear as the lower band of a `content-image` slide (a stat pair).
- **Strict recipe:** §7.2 card variant with an enlarged number run. **Provenance:** ref
  S6 (📚~750K / 🏥~800K pair).

#### `big-number` (one hero metric)
- **Match:** a **single** dominant figure is the whole slide (`$2.50`, `18%`, `1M`) with a
  one-line caption. Distinct from `stat` (2–4 metrics in a grid). **Fires on `one_metric` on its
  own** — a lone headline figure does not need a hint to earn the hero treatment, and letting it
  fall to prose wastes the deck's loudest slide; `<!-- template: big-number -->` only pins it.
  `body[0]` is the number, the rest is the caption.
- **Format:** the number set **very large** in `#DA1B2E`, a bold caption beneath, optional
  supporting line. Left-aligned, vertically centred.
- **Provenance:** impact / headline-stat slides; common in Gamma-style decks.

### Ordered sequence

#### `process`
- **Match:** a **named/ordered sequence** — `1./2./3.`, `Paso N`, `Step N`, `Fase N`,
  `Etapa`, `Case A/B/C`, a decision flow, or a branching tree. Order carries meaning. A
  **plain numbered list of ≥2 `1. …` lines** also matches (the numbered lines are the steps),
  with or without bold labels; a *single* numbered line stays prose. **Not:** an unordered
  concept set (→ `concept-breakdown`).
- **Format:** **numbered/step cards or a numbered list**, by whether the steps are labeled:
  - **Labeled steps** (`1. **Label** — body`, `Paso N …`) → §7.1 numbered card strip: outer
    card + left strip (`#F2EEEE`) + number (Bold) + heading + body.
  - **Plain steps** (`1. Sentence` with no label) → a **vertical numbered list**: a small
    outlined number chip + the sentence per row.
  - An optional **intro lead** (a plain line before the numbered list) renders above the steps.
  - An optional supporting image/diagram/example may sit beside the numbered steps in a split
    layout; the ordered steps remain the primary structure.
  The ordinal is the rendered number; **strip it from extracted labels/bodies** (`1 · Leave
  feedback` → `label:"Leave feedback"`, not `label:"1 · Leave feedback"`). After stripping the
  ordinal, apply the colon lead-in rule: `1 · Leave feedback: drop bullets in draft.md` →
  `label:"Leave feedback"`, `body:"drop bullets in draft.md"`. The description is the body. The
  label **must not** render as an inline paragraph prefix — the sequence must be visually
  scannable as steps.
- **Strict recipe:** §7.1 / §7.6. **Provenance:** ref S13 (6 components), S30 (ToT tree),
  S44 (cascade), S47 (5 stages).

#### `timeline` (dated / milestone sequence)
- **Match:** an ordered sequence whose labels are **dates / periods / milestones** (`2023`,
  `Marzo 2023`, `20 días después`, `Q1`), where *when* matters — a history or roadmap. Distinct
  from `process` (abstract steps, order-not-date). **Fires on `date_labels` on its own** — no
  hint required, and it is tested **before** `is_ordered`, since dated milestones are ordered too
  and testing order first is what used to swallow every timeline into `process`.
  `<!-- template: timeline -->` only pins it.
- **Format:** a **vertical rail** with a connecting line and a dot per entry; each row = the
  date/milestone (mono accent) + a one-line detail. Time flows top→bottom. An optional **`lead`**
  (one intro line) may sit above the rail — use it when the sequence needs framing before the
  dates; without it the rail starts at the top. (Its presence is what let this template absorb
  slides that would otherwise fall to `process` only to get a lead.)
- **Provenance:** roadmap / history slides; common in Gamma-style decks.

### Aligned columns — parallel values, read across

#### `value-columns`
- **Match:** **2–3 aligned columns of parallel values**, read row by row against a shared
  left-hand factor or against each other. Two symmetric groups set against each other is the
  common case — A-vs-B, before/after, single-model vs cascade, myth vs reality — but it is not
  the only one: three options judged on the same factors, or a pipe-table of factor→X→Y→Z rows,
  belong here too. What selects this template is **the columns being parallel and comparable**,
  not the slide being adversarial. **Not** a label/value table (that is `concept-breakdown`,
  card-per-row); **not** a valenced upside/downside pair (that is `pros-cons`, colour-coded).
  *This template was called `comparison` until 0.75.0 — the old name described only the common
  case and kept pushing three-column parallel listings to the wrong template. The old id is gone;
  a model still carrying it renders as `fallback` and the build warns, naming the slide.*
- **Format:** either **two equal columns** (left = A, right = B; parallel headings, equal
  weight/height) or a **compare-strip**: header row (Factor · A · B) + N aligned rows,
  rendered as a **card-per-row grid, never a native table**. Uniform column widths,
  shared gridlines. **Not** bullets.
- **A supporting image is allowed** (optional `image` + `layout`, `text-left` default /
  `image-left` mirrored): the grid takes the wider column, the diagram sits beside it.
  This is the fifth body-plus-image composition, not a separate template — a table and a diagram
  on the same slide never have to trade against each other. An optional `lead` frames the grid,
  with or without an image. At half width the grid still reads as a grid (columns stay aligned;
  it never degrades to one row per cell), so keep it to **≤3 columns × ≤5 rows** — past that the
  build warns and the slide wants splitting. There is no `image-top`: a grid under a
  full-width image is a different slide, not a layout of this one.
- **Strict recipe:** §11 (pipe-table → card-grid) / two §7.2 columns; with an image, §11 composed
  with §13 (body beside a picture) — no new geometry. **Provenance:** ref
  S44 (compare-strip), S6 (pair).

#### `pros-cons` (two colour-coded columns)
- **Match:** a **decision framed as upside vs downside** — two labelled groups (Ventajas /
  Riesgos, Pros / Cons, Consumo / Enterprise). **Fires on `two_groups` + `polarity` on its own**
  — when the two groups are valenced, the colour-coding *is* the information, so this beats the
  neutral `value-columns`; `<!-- template: pros-cons -->` only pins it. Content is two `### Group`
  items (first = the "pro", second = the "con").
- **Format:** two panels — the pro in the **blue** callout tint with a `verified` check, the
  con in the **pink** tint with an `error`/`dangerous` mark; each = label + a short body.
- **Provenance:** trade-off / decision slides; common in Gamma-style decks.

### Visual — images carry the content

#### `content-image`
- **Match:** one main claim supported by **1–3** `![]()` images; the prose leads, the
  images are evidence — **the prose is required**. An image with *no* `lead` and no `facts` is
  not this template: it is `image-full`, which drops the text column and bleeds the image to the
  edges. (The renderer still guards the empty case — a legacy model that carries a bare image here
  renders the image full width rather than an empty bordered column — but new models should
  classify it as `image-full`.) **Not:** a labeled set of ≥2 concepts that happens to have one
  image — that is `content+cards+image`, and demoting its cards to `facts` costs them their icons.
- **Name:** the `template` value is **`content-image`** (hyphen), even though the strict
  PPTX recipe for it is named "§13 content+image". Recipe names and `template` values are
  different namespaces; `"content+image"` in the model renders as `fallback`.
- **Format:** text column (lead + a few short facts / a callout) on one half; **1–3
  images aligned to the text columns** on the other, **aspect preserved**, no full-bleed.
  Not a grid. **Three layouts** (`layout` field): `text-left` (default — text left, image
  right), `image-left` (mirrored — image left, text right: the image leads the eye and the
  text follows, for a diagram the prose walks through or to break a run of `text-left`
  slides), and
  `image-top` (stacked, image over a short caption — for text too short to hold a column).
  The image is **never cropped** in any of them, so all three are safe for a diagram the
  audience must read — unlike the `aside` column (see above), which crops to fill. Pick the
  layout from the content (short text → `image-top`; image to be read first → `image-left`);
  an author `<!-- layout: <value> -->` hint pins it and overrides that judgement.
- **Strict recipe:** §13 content+image. **Provenance:** ref S6/19/20, final
  S3/9/15/16/17/20, gov case-study slides.

#### `content+cards+image`
- **Match:** labeled **cards/steps on one side AND a supporting image/example/code on the
  other** — the hybrid (strict's own 4th type). Both a card set *and* a single evidence
  visual. **This is the default for `labeled_items ≥ 2` + one shared image** — it is not a rare
  hybrid to reach for only when nothing else fits.
- **Format:** ~50/50 split: cards or a numbered list on one half + one supporting
  image/worked-example/code panel on the other, aligned to a shared baseline. **Two layouts**
  (`layout` field): `text-left` (default — cards left, image right) and `image-left` (mirrored —
  image left, cards right). Pick the layout from the content the same way `content-image` does
  (image to be read first → `image-left`); an author `<!-- layout: <value> -->` hint pins it and
  overrides that judgement. Only the two columns swap: the cards keep their order, their icons
  and their left alignment, and the cards' column stays the wider of the two. There is **no
  `image-top`** here — a stack of cards under a full-width image is a different slide, not a
  variant of this one; the value is rejected with a warning rather than half-honored.
- **Strict recipe:** §13 content+cards+image (§7 cards + §12 image). **Provenance:** ref
  S7, S30, S42.

#### `image-full` (one image, edge to edge under the header)
- **Match:** the slide **is one image** — a screenshot, UI capture, or diagram the presenter
  narrates while the audience looks at it, with the detail in `### Notes` rather than on the
  slide face. Fires on `image_only` (`n_images == 1`, no prose and no enumeration in the body).
  An author writing "just the image, no text" produces exactly this. **Not:** a caption or a
  couple of supporting facts alongside it (→ `content-image`, whose prose leads); not ≥4 images
  where variety is the message (→ `image-grid`); not atmosphere behind text (→ an `aside`, which
  crops).
- **Format:** the **normal header** — section pill + title, plus an optional one-line `lead` —
  kept compact at the top; the image then takes **all remaining space, bleeding to the left,
  right and bottom edges** with no padding, no frame, no rounded corners. It is **contained,
  never cropped** (the invariant every image-owning template holds — a screenshot loses its
  meaning when its edges are cut), so an image whose aspect is taller than the area it is given
  centres with space at the sides. Nothing else is on the slide: no facts, no cards, no band.
- **Strict recipe:** §13 image-full — a single full-width `<p:pic>` below the title block, sized
  to its own aspect against the remaining canvas. **Provenance:** screenshot walkthrough slides
  (`claude-cowork` 1.4).

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
  per-image text. **Not** for a list of items that merely each have an icon (→ `concept-breakdown`, `format: list`).
- **Strict recipe:** §13 image-grid. **Provenance:** ref S10/31/33–38/44, gov S40/43.

### Verbatim / last-resort

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
  candidate** in FEEDBACK: most "wall of prose" slides are `concept-breakdown`/
  `content-image` in disguise.
- **`panels` is a set — never one.** The panel strip is a `repeat(3,1fr)` grid, so a
  **single** panel renders as a lonely third-width card at the bottom, and an emphatic
  closing line dropped there reads as demoted afterthought, not punchline. If the slide is
  *a lead + one restatement/aphorism* (exactly the `labeled_items == 1` case above), it is
  **`single-point`**, not `content-text`: promote that line to `point.label` and the
  explanation to `point.body`. Only reach for `content-text` when there are genuinely **2–4**
  supporting statements of comparable weight. A one-panel `content-text` is always a
  misclassification — the deterministic `audits/degenerate_enum.py` floor fails it.
- **Strict recipe:** §13 content-text. **Provenance:** ref S41, final S10/19.

#### `fallback`
- **Match:** content matching no entry above.
- **Format:** the mode's default flow (lead + supporting), **still card/panel over
  bullets**; log that fallback was used so the gap can be added to the catalog later.

---

## Matching examples — worked classifications

Each shows a slide's Markdown, the template it classifies to, and **why** (which signals
fired, which near-miss was ruled out). These are the ground truth for consistent matching.

**`concept-breakdown`** — labeled set, unordered, short bodies, no images:
```
## Limitaciones de los modelos
- **Alucinaciones** Predicen texto plausible, no verifican hechos.
- **No-determinismo** El mismo prompt produce respuestas diferentes.
- **Sesgo de recencia** Presta más atención al inicio y al final.
```
→ `concept-breakdown`. `labeled_items=3`, `is_ordered=false`, `n_images=0`, bodies short →
3 equal cards. **Ruled out:** plain bullets (labels make it a card set — the invariant);
the `row` format would also fit but with no lead paragraph the default grid is chosen; `process`
(no ordinal labels).

**`process`** — same shape but ordered:
```
## Cómo funciona el pipeline
- **Paso 1** El usuario envía un prompt.
- **Paso 2** El modelo tokeniza la entrada.
- **Paso 3** Genera la salida token a token.
```
→ `process`. Identical to the above **except** `is_ordered=true` (`Paso N`) → numbered
cards. This single signal is the whole difference; never render an ordered set as an
unordered grid.

**`format: row` vs `format: list`** — lead + 3–5 labeled items, split by body length:
```
## Tres innovaciones de StyleGAN
StyleGAN cambió la síntesis de imágenes en tres frentes.
- **Mapping network** Desenreda el espacio latente.
- **AdaIN** Inyecta estilo por capa.
- **Mixing regularization** Combina estilos de dos latentes.
```
→ `concept-breakdown`, `format: row`. Lead paragraph + `labeled_items=3`, longest body ≤ 80 chars → one horizontal
row of 3 cards. Had any body run 2–4 sentences (> 80 chars), it would be `format: list`
(vertical, prose room). Pick by the **longest** item; never split the group across both.

**`figures` vs `concept-breakdown`** — the per-item image decides:
```
## Alucinaciones en profundidad
![why](images/hall-1.svg) **¿Por qué ocurren?** No acceden a hechos verificados.
![bias](images/hall-2.svg) **Entrenamiento sesgado** Datos incompletos o desactualizados.
![conf](images/hall-3.svg) **Confianza sin verificación** No distingue saber de inventar.
```
→ `figures`. `labeled_items=3` **and each carries its own image** (`n_images=3`, one per
item) → image+label+body cards. Without the per-item images this is `concept-breakdown`.

**`content-image` vs `image-grid`** — image count + intent:
```
## ¿Cuánto es 1 millón de tokens?
Un millón de tokens es más contexto del que parece.
![scale](images/tokens-scale.png)
📚 ~750K tokens — toda la obra de Tolkien.  🏥 ~800K tokens — historial clínico completo.
```
→ `content-image`. Prose leads, `n_images=1` supports it. (The 📚/🏥 pair is a `stat`
sub-band, not its own slide.) With `n_images ≥ 4` where the *variety* is the point, it would
be `image-grid`.

**`value-columns`** — parallel value columns / a compare-table:
```
## Modelo único vs. Cascading
| Factor | Modelo único | Cascading |
| --- | --- | --- |
| Precisión | Estable | Depende del routing |
| Costo | Mayor por llamada | Menor en promedio |
```
→ `value-columns`. `has_table` with `factor | A | B` → card-per-row compare-strip, **never a
native `<a:tbl>`**. A two-column "Pros vs Cons" of labeled cards classifies here too
(`two_groups`), and so does a third parallel column (`factor | A | B | C`) — the columns being
comparable is the signal, not the slide being adversarial.

**`code-example`** — code dominates:
```
## Prompt caching
```python
client.messages.create(model=…, system=[{"type":"text","cache_control":{…}}])
```
Marca las partes reutilizables para cachear.
```
→ `code-example`. `has_code=true` wins before any other signal → mono code surface + a short
explanation column.

**`statement`** — one bold claim:
```
## La IA no piensa como un humano
```
→ `statement`. `one_claim=true` (≤ 16 words, no items/images/code) → one large assertion.
**Ruled out:** `content-text` (that carries *several* supporting facts; this is a single
line). A recurring myth/reality series is a run of `statement` slides.

**`stat`** — standalone metrics:
```
## Costes en la práctica
- **~$2.50 / 1M** tokens de entrada (GPT-4o)
- **~$10 / 1M** tokens de salida
- **50–90%** de ahorro con prompt caching
```
→ `stat`. `big_metrics` (2–4 numbers with labels) → big-number cards. (If the numbers were
prose points rather than the payload, this would be `concept-breakdown`.)

**`fallback`** — nothing fires:
```
## Una definición
La ingeniería de prompts es el arte de estructurar instrucciones para un modelo.
```
→ `content-text` (a `fallback`-adjacent last resort). No labeled items, no images, no code,
> 16 words. Emit as a lead statement + light panels; **flag as a restructure candidate**
(most such slides are a hidden `concept-breakdown`/`content-image`).

## Disambiguation quick-reference

| If the slide is… | and… | → |
|---|---|---|
| a labeled set (**≥2**) | labels are **dates/periods** | `timeline` (check before `process`) |
| a labeled set (**≥2**) | ordered (steps/1./Paso), labels not dates | `process` |
| a labeled set (**≥2**) | **each item** has an image | `figures` |
| a labeled set (**≥2**) | **one shared** supporting image | `content+cards+image` — keep the cards; **never** dissolve them into `content-image` facts |
| a labeled set (**≥2**) | **no image** (incl. a **2-item** set) | `concept-breakdown` (renderer adds per-card icons) — then `format`: `row` = lead + 3–5 short, `list` = lead + 3–5 prose or an anaphora, `grid` otherwise |
| **exactly 1 labeled item** | lead + one point/reveal | `single-point` (card/callout, never a bullet) |
| **exactly 1 labeled item** | it's a tip/warning/analogy — tone *is* the message | `callout` |
| numbers/metrics | **1** hero figure + caption | `big-number` |
| numbers/metrics | 2–4 big figures + labels | `stat` |
| a table | **2–3 comparable value-columns** (A vs B, or options over shared factors) | `value-columns` |
| a table | 2–3 comparable value-columns **+ one shared image** | `value-columns` with `image` + `layout` — **never** flatten the rows into `content+cards+image` cards to keep the picture |
| a table | label/value or **N-level/N-column** | `concept-breakdown` (card-per-row) |
| two groups | upside vs downside (`polarity`) | `pros-cons` |
| two groups | a neutral A vs B / before-after | `value-columns` |
| images | ≥4, variety is the message | `image-grid` |
| images | 1–3 supporting prose | `content-image` |
| images | **image only** — no prose, no enumeration | `image-full` (header, then the image edge to edge); **not** `image-grid` |
| one big claim | ≤16 words, opt. reveal/counter-point | `statement` |
| one big claim | it is **someone else's words** (quoted/attributed) | `quote` |
| a question | the slide answers it (opt. A/B/C/D choices) | `quiz` |
| section break | H1 **or** `〔divisor〕`/`〔Backup〕` marker | `section-agenda`/`divider` |
| terminal slide | next steps / resources / links | `closing-cta` |
| terminal slide | 1–2 words (`Q&A`, `Gracias`) | `closing-hero` |
| only prose | no visual, no enumeration | `content-text` (flag) |
| code | meant to be read | `code-example` |
