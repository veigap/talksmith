# Critique rubric — shared, categorized, per-mode-selectable

This is the **single source of truth** for what the render critique walks. Every
render mode (`strict`, `free-form`, `preview`) selects a subset of the categories
below; it does not carry its own rubric. The FEEDBACK sub-agent walks the selected
`FEEDBACK` practices on the rasterized slide PNGs; the `CONTROL` practices are the
deterministic Python audits run before FEEDBACK.

> **Why this file exists.** The per-style `pptx-prompt.md` specs are deliberately
> self-contained and duplicate the visual *floor* (canvas / palette / fonts / cover).
> The critique rubric is a **documented exception** to that convention — it is
> centralized here, exactly like the deterministic `audit_*.py` scripts are shared
> rather than copied per style. Its consumer is the critique sub-agent and
> [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md)
> → *Render flow*, not the per-slide renderer. Centralizing it is what makes the
> aesthetic/distribution bar improvable in one place instead of drifting across three
> specs (which is how the phantom free-form "§6 8-practice list" arose).

## Categories

- **CONTENT** — is the substance right and digestible: every source block present, no
  wall-of-text, sane bullet budget, no raw emoji.
- **AESTHETIC** — visual polish: overflow, margins, balance, focal point, image scale,
  contrast, type scale, alignment, emphasis, colour, image treatment, widows/orphans.
- **DISTRIBUTION** — spatial arrangement: grid alignment, gutters, negative-space
  balance, column/section balance, proximity grouping, uniform sizing, reading flow.
- **LAYOUT-CONFORMANCE** — adherence to the strict template: layout selection, section
  pill, master type-hierarchy, theme/pixel-equivalence, palette/font set, branded
  icons. **strict-only** — free-form and preview render their own layouts and are
  never judged against a fixed template.

## Selection matrix

| Mode | Categories walked (FEEDBACK) | Deterministic audits (CONTROL) | Cycle cap | Scope | On finding |
|---|---|---|:--:|---|---|
| **strict** | CONTENT + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE | block-coverage, aspect-ratio, cover-fidelity, **palette/fonts**, **layout-fit** | 3 | whole deck | auto-regenerate; editorial → defer |
| **free-form** | CONTENT + AESTHETIC + DISTRIBUTION | block-coverage, aspect-ratio, cover-fidelity | 2 | whole deck | auto-regenerate; editorial → defer |
| **preview** | CONTENT + AESTHETIC + DISTRIBUTION | block-coverage, aspect-ratio, cover-fidelity | 2 | **per-slide, changed-only** | auto-regenerate |

`palette/fonts` and `layout-fit` are **strict-only** (they enforce the strict
template — a layout-conformance concern). `block-coverage`, `aspect-ratio`, and
`cover-fidelity` are the **shared floor**, run in every mode. In `preview`, audit
failures are surfaced but non-blocking (the preview still ships — it is a sanity
check, not a deliverable).

**To extend:** add one entry below under its category — every mode that selects that
category picks it up. **To refine a mode:** edit its row above (categories, cycle cap)
and the mirror row in `SKILL.md` → *Render flow*.

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
  modes: [strict, free-form, preview]
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
  check: "Image scale appropriate to role; aspect ratio preserved (no stretching). Dual-enforced by design: audit_aspect_ratios.py (CONTROL) catches sub-perceptual stretch, this practice catches gross squashing. (strict adds a per-slide measurement protocol — see strict/pptx-prompt.md §20 @AESTHETIC-04.)"

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
