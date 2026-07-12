# Slide design — the visual-transformation mandate + critique catalog

This is the **mandate for the visual transformation** of a slide: the operational,
per-slide practices a rendered slide must honour, and that the **critique loop exists to
enforce**. Organized into categories; each practice is one entry with a category-prefixed
id. This is *what a good slide looks like* — the pipeline config that decides *when* each
is walked lives in [`render-modes.md`](render-modes.md), not here.

It sits between two shared docs and must stay consistent with both:

- [`visual-guidance.md`](visual-guidance.md) — the **generic** visualization floor
  (universal principles + hard "must-never-happen" defects). This catalog **implements**
  those principles as concrete, checkable practices and must never contradict them; its
  hard-invariant checks are the operational form of that floor's Part A.
- [`slide-templates.md`](slide-templates.md) — *which template* a slide is; the `TEMPLATE`
  category below reviews each slide against its classified template's *Format*.

## Categories

- **CONTENT** — is the substance right and digestible: every source block present, no
  wall-of-text, sane bullet budget, no raw emoji, speaker notes preserved.
- **TEMPLATE** — does the slide take the right *shape*: it realizes its classified
  catalog template ([`slide-templates.md`](slide-templates.md)) and honours the universal
  cards-not-bullets invariant. Walked in every mode.
- **AESTHETIC** — visual polish: overflow, margins, balance, focal point, image scale,
  contrast, type scale, alignment, emphasis, colour, image treatment, widows/orphans.
- **DISTRIBUTION** — spatial arrangement: grid alignment, gutters, negative-space
  balance, column/section balance, proximity grouping, uniform sizing, reading flow.
- **LAYOUT-CONFORMANCE** — adherence to the strict template: layout selection, section
  pill, master type-hierarchy, theme/pixel-equivalence, palette/font set, branded
  icons. **strict-only** — free-form and preview render their own layouts and are
  never judged against a fixed template.

## Entry schema

```
- id:          AESTHETIC-06                      # category-prefixed, stable, order-independent
  category:     AESTHETIC
  enforcement:  FEEDBACK                         # FEEDBACK (visual walk) | CONTROL (deterministic audit)
  audit:        audit_aspect_ratios.py           # present only when a Python floor backs it
  modes:        [strict, free-form, preview]     # default = every mode selecting this category
  check:        "one-line judgement the critic applies"
```

Mode-specific depth (e.g. strict's practice-7 measurement protocol, the §17 icon
binding, base-template pixel-equivalence) lives in that mode's `pptx-prompt.md` as an
**annotation keyed by id**, not here — the catalog stays terse and shared.

---

## CONTENT

```
- id: CONTENT-00
  category: CONTENT
  enforcement: CONTROL
  audit: audit_block_coverage.py
  modes: [strict, free-form]   # preview produces no .pptx to audit — the guarantee holds by construction (build_preview renders every unit)
  check: "Every block in the source appears as a shape on the rendered slide. Deterministic gate — not walked; any [block-drop] → REGENERATE before FEEDBACK runs."

- id: CONTENT-01
  category: CONTENT
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "No raw system-emoji glyphs (💡 📚 🏥 ⚠️ ✅ ⚙️ 🔍 …) in any slide body."

- id: CONTENT-02
  category: CONTENT
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "≤ 5–7 bullets per slide; 8+ → flag for split, never shrink-fit."

- id: CONTENT-03
  category: CONTENT
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Body isn't a wall of paragraphs; long prose belongs in the notes pane, not the slide body. The slide should be glance-able."

- id: CONTENT-04
  category: CONTENT
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "One core message per slide — the slide makes a single point. If it argues two unrelated things, split it. (Gamma: 'make one single point per slide.')"

- id: CONTENT-05
  category: CONTENT
  enforcement: CONTROL
  audit: audit_notes_coverage.py
  modes: [strict, free-form]   # preview produces no .pptx; notes are not part of the wireframe deliverable
  check: "Every `### Notes` block reaches a non-empty notes pane on its slide. Deterministic gate — any [notes-drop] → REGENERATE before FEEDBACK runs. Notes are load-bearing and template-independent."
```

## TEMPLATE

The critique is **template-aware**: it receives each slide's classified template id (from
GENERATE — strict's pre-emit audit line, free-form's `.layout-log.md`, or the preview
classifier) and reviews the slide against **that template's *Format* in
[`slide-templates.md`](slide-templates.md)**, not a generic notion of "looks good." Walked
in every mode.

```
- id: TEMPLATE-01
  category: TEMPLATE
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "The slide realizes its classified catalog template (or a justified `fallback`): the right regions, item counts, arrangement (row/grid/columns/split), and uniform sizing per that template's Format in slide-templates.md. A slide that classified as concept-breakdown but rendered as prose, or as figures but dropped its images, fails."

- id: TEMPLATE-02
  category: TEMPLATE
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "The universal invariant: a set of parallel labeled concepts renders as cards/panels/figures, NEVER as a plain bullet list. Plain unlabeled bullets only as a ≤3-item caveat aside. A 'title + bullets' slide is a mis-rendered concept-breakdown / card-row / icon-list / process / figures."
```

## AESTHETIC

```
# AESTHETIC = how the slide LOOKS (style/polish). Spatial concerns — margins,
# visual balance, focal point — live in DISTRIBUTION (they used to sit here as
# AESTHETIC-02/03/05; those ids are retired to keep each concern in one place).

- id: AESTHETIC-01
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "No text overflow or truncation — titles fit on 1–2 lines, body stays inside placeholders, nothing bleeds off-slide or ellipsizes. Can't fit → split (defer with reason)."

- id: AESTHETIC-04
  category: AESTHETIC
  enforcement: FEEDBACK
  audit: audit_aspect_ratios.py
  modes: [strict, free-form, preview]
  check: "Image scale appropriate to role; aspect ratio preserved (no stretching). Dual-enforced in strict/free-form: audit_aspect_ratios.py (CONTROL) catches sub-perceptual stretch, this practice catches gross squashing. In preview (no deck, no CONTROL) only the FEEDBACK half runs. (strict adds a per-slide measurement protocol — see strict/pptx-prompt.md §20 @AESTHETIC-04.)"

- id: AESTHETIC-06
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Contrast & legibility — dark-on-light by default, strong text-to-background contrast; body text large enough to read from the back of the room (≈ 30pt floor per the 10/20/30 rule); text over an image sits on a scrim/overlay."

- id: AESTHETIC-07
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Type discipline — at most ~2 type families (one display/heading, one body) and a few consistent size steps with a clear title→body ratio; not a jumble of families, sizes, or weights."

- id: AESTHETIC-08
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Text-alignment consistency — text runs/blocks use one alignment scheme (e.g. all left), not a mix of centre/left/ragged; the scheme doesn't change slide to slide. (Element-to-grid edge alignment is DISTRIBUTION-01, not this.)"

- id: AESTHETIC-09
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Emphasis restraint — one clear emphasis guiding the eye; bold/accent used sparingly, not on everything."

- id: AESTHETIC-10
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Colour restraint & harmony — a small palette (≈ 4 colours including neutrals) used consistently deck-wide; accent colour used purposefully, not decoratively everywhere; no clashing hues."

- id: AESTHETIC-11
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Image treatment consistency — uniform crop/corner-radius/border across images; no low-res image among sharp ones."

- id: AESTHETIC-12
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "No widows/orphans; parallel bullet grammar — no stranded last word, bullets grammatically parallel."

- id: AESTHETIC-13
  category: AESTHETIC
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Deck-wide consistency — recurring chrome (headers, footers, page numbers, section markers), the spacing rhythm, and repeated layouts stay consistent slide to slide. Consistency is what separates amateur decks from professional ones. (Distinct from the per-attribute checks: this is the across-slide meta-view.)"
```

**AESTHETIC note (category directive, all modes that walk AESTHETIC).** After the
per-practice matrix, add one free-text aesthetic sentence per slide for what the eye
catches but the checklist doesn't — wonky alignment, wrong focal point, dead or
claustrophobic composition, emotionally-mismatched palette, rhythm fatigue, or
image-text gestalt. If nothing catches the eye, write `aesthetic: clean`. Not
optional padding — the part only the critic can do.

## DISTRIBUTION

```
# DISTRIBUTION = WHERE things sit (spatial arrangement). It absorbs the spatial
# concerns that used to be miscategorized under AESTHETIC — safe margins (→ -03),
# visual balance (→ -04), and focal point (→ -07) — each merged into its natural
# home so a concern is checked in exactly one place.

- id: DISTRIBUTION-01
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Grid alignment — element edges (shapes, images, columns) share gridlines; nothing sits at an arbitrary offset. (This is element-to-grid alignment; text-run alignment is AESTHETIC-08.)"

- id: DISTRIBUTION-02
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Consistent gutters/spacing — equal gaps between repeated elements (cards, columns) and between stacked blocks."

- id: DISTRIBUTION-03
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Whitespace & margins — content respects safe margins (nothing hugs the slide edges) AND negative space is balanced: no dead corners, no crammed region; the frame fills evenly unless emptiness is deliberate."

- id: DISTRIBUTION-04
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Weight & column balance — slide weight (text + images) is distributed, not stacked left/right/top; in multi-column layouts columns are roughly equal weight/height (one isn't overflowing while another is half-empty)."

- id: DISTRIBUTION-05
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Proximity grouping — related items grouped, unrelated separated; every label sits next to the figure it describes (Gestalt proximity)."

- id: DISTRIBUTION-06
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Uniform element sizing — repeated cards/icons rendered at the same size; no one arbitrarily larger."

- id: DISTRIBUTION-07
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Focal point & reading flow — one dominant element the eye lands on first (not two equally-prominent images/headings), placed for impact (rule-of-thirds / off-centre rather than dead-centre by default), with the layout following a natural Z/F eye path: entry top-left, resolution/CTA bottom-right."

- id: DISTRIBUTION-08
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "No dead title→body gap — body content begins just below the title's *actual* wrapped height, not below a worst-case reserve. A short one-line title must not leave a large empty band above the body (the classic symptom of a renderer that reserved room for a 2–3-line title the text didn't need). (strict realizes this via the measured-height rule in strict/pptx-prompt.md §3.5.)"

- id: DISTRIBUTION-09
  category: DISTRIBUTION
  enforcement: FEEDBACK
  modes: [strict, free-form, preview]
  check: "Card content is balanced within the card — uniform equal cards in a grid are correct (a concept grid *should* be a regular grid of equal cards, even filling the region), but the content must sit balanced inside each card (vertically centred, or icon-top with even padding), never crammed at the top with a large dead void below. The failure mode is not uniformity — it is a big box whose content hugs the top edge, so items read as far apart. Balance the content; keep the grid uniform."
```

## LAYOUT-CONFORMANCE  *(strict-only)*

The specifics of these live in `strict/pptx-prompt.md`; the entries here carry the
one-line intent and point at the strict machinery. In Phase 2 the measurable rules
move into `strict/conformance-patterns.md` (declarative, learnable).

```
- id: CONFORMANCE-01
  category: LAYOUT-CONFORMANCE
  enforcement: FEEDBACK
  modes: [strict]
  check: "Consistent type hierarchy — sizes inherit the template master deck-wide; no local overrides."

- id: CONFORMANCE-02
  category: LAYOUT-CONFORMANCE
  enforcement: FEEDBACK
  modes: [strict]
  check: "Section dividers distinct — each numbered H1 → a divider slide (large title, no body)."

- id: CONFORMANCE-03
  category: LAYOUT-CONFORMANCE
  enforcement: FEEDBACK
  audit: audit_cover_fidelity.py, audit_palette_fonts.py
  modes: [strict]
  check: "Theme consistency — template fonts/colours/master layouts honoured; slides 1–2 pixel-equivalent to base-template modulo placeholder text."

- id: CONFORMANCE-04
  category: LAYOUT-CONFORMANCE
  enforcement: FEEDBACK
  modes: [strict]
  check: "Section pill on every content slide — #F9D2D6 rounded-rect at top-left naming the active section in ALL CAPS."

- id: CONFORMANCE-05
  category: LAYOUT-CONFORMANCE
  enforcement: FEEDBACK
  modes: [strict]
  check: "Branded icons only — every iconographic mark is a #DA1B2E §17 catalog line-art icon; one consistent icon style (no mixed styles)."

- id: CONFORMANCE-06
  category: LAYOUT-CONFORMANCE
  enforcement: CONTROL
  audit: audit_layout_fit.py
  modes: [strict]
  check: "Emitted layout == the layout predicted from the source by strict §15.5/§15.6.1. Deterministic."
```

---

## Walk discipline (all modes)

1. **Every slide, not a sample.** Read every slide PNG — one Read per slide. A smoke
   test (cover + a few) is not a review; report it as such if that's all that was done.
2. **Every cell of slide × selected-practice.** For each slide name each applicable
   practice and assign *pass / concern / fail*. "Clean" = every cell passes. A visible
   violation is a fail even if the slide looks "mostly OK." Skipping a cell on vibes is
   a critic failure.
3. **Be surgical.** *"Slide 7 title wraps to a third line — shorten X → Y"*, not "title
   too long."
4. **Minor ≠ defer.** Every flagged cell gets *fix this iteration* / *defer because
   <reason>*. `[minor]` is not a synonym for defer.

**Disposition — auto-regenerate vs defer (all auto-regenerating modes).** Objective,
unambiguous defects (overflow, off-slide bleed, raw emoji, distorted image, misaligned
columns) get *fix this iteration* → REGENERATE. Editorial-judgement calls (which of two
balanced compositions reads better, tone of palette) get *defer because <reason>* and
surface in the closing report for the presenter. This holds for strict, free-form, and
preview alike — they differ only in category selection, cycle cap, and (preview) scope.

## When to declare clean

A first-cycle pass on all selected practices + a clean aesthetic note is the goal.
Don't manufacture issues to fill the cycle budget — an unneeded REGENERATE risks
regressing adjacent slides.

**Closing report:** `clean on cycle 1` | `clean after N cycle(s)` |
`unresolved: <slide N — defect>` | `deferred (presenter to review): <slide N — defect — reason>`.
N counts top-level cycles only, not build-time recoveries.

## Provenance

The AESTHETIC + DISTRIBUTION practices distill established slide-design guidance —
Gamma's design principles (visual hierarchy, one point per slide, restrained type/colour,
purposeful whitespace), Kawasaki's 10/20/30 rule (≈30pt floor), and standard composition
guidance (alignment/grid, contrast, rule-of-thirds, cross-slide consistency). Sources:
[Gamma — visual hierarchy](https://gamma.app/explore/content/guides/how-gamma-builds-clean-modern-presentations-with-visual-hierarchy),
[Gamma — 10/20/30 method](https://gamma.app/insights/the-10-20-30-method),
[BrightCarbon — whitespace](https://www.brightcarbon.com/blog/presentation-whitespace/),
[Flashdocs — 10 design principles](https://www.flashdocs.com/post/10-design-principles-every-slide-creator-should-know).
