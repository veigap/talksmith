# Visual guidance — the generic visualization floor (all modes)

The **medium-agnostic foundation of good information design**: the universal principles a
well-made slide obeys, and the **hard defects that must never ship** in any generated deck.
Referenced by **every** render mode (`strict`, `free-form`, `preview`) at GENERATE (the
renderer honors it) and at FEEDBACK (the critique enforces it).

This is the **most generic layer** — it sits *beneath* the more specific shared docs and
they must never contradict it:

- [`slide-templates.md`](slide-templates.md) — *which shape* a slide takes (the templates).
- [`slide-design.md`](slide-design.md) — the *operational, per-slide critique catalog*
  (category-tagged, checkable practices). It **implements** the principles below as concrete
  checks; where it is silent, this page still governs. slide-design must never conflict with
  a rule here.
- [`render-modes.md`](render-modes.md) — per-mode config (which audits/critique run when).

Think of it as the constitution: broad, stable, rarely edited. The other docs are the
statutes that apply it.

## Part A — Hard invariants (must never ship, any mode, any template)

Absolute prohibitions. A slide that violates one is broken regardless of style, taste, or
template. Where a defect is deterministically detectable it is a CONTROL audit (build fails);
otherwise the FEEDBACK critique flags it as **blocking**, not editorial.

1. **No unreadable text–image overlap.** Text never sits directly on busy imagery such that
   either becomes hard to read. Text over an image requires a scrim/overlay or a clear zone.
2. **Nothing bleeds off the slide.** No shape, text, or image crosses the canvas edge; no
   content is clipped by the slide boundary.
3. **No truncation / ellipsis.** Text is never cut off or `…`-truncated to fit. If it doesn't
   fit, the content is reduced or the slide is split — never shrunk past legibility or clipped.
4. **No occluding overlap.** Shapes/images/text boxes don't accidentally cover one another's
   content; z-order never hides information.
5. **No image distortion.** Images scale uniformly — the rendered aspect ratio equals the
   source's. No stretching, squishing, or anamorphic "fit to box". (Deterministic:
   `audits/aspect_ratios.py`.)
6. **Legible contrast, always.** Sufficient figure-ground contrast; no low-contrast text
   (light-on-light, dark-on-dark, or text lost in an image).
7. **Above the legibility floor.** Body text is readable from the back of the room — treat
   ~30 pt as the floor (Kawasaki's 10/20/30). Nothing critical rendered too small to read.
8. **Inside the safe area.** Content respects safe margins; nothing hugs or crosses the edges.
9. **No silently dropped content.** Every source block becomes a visible element and every
   `### Notes` block reaches the notes pane. (Deterministic: `audits/block_coverage.py`,
   `audits/notes_coverage.py`.)
10. **No wall of text; no bullet dump for parallel concepts.** A slide is not a document page:
    prose belongs in the notes; a set of parallel labeled concepts is cards/panels, never a
    plain bullet list (the [`slide-templates.md`](slide-templates.md) universal invariant).

## Part B — Generic good-visualization practices (the *why* the checks exist)

The universal principles [`slide-design.md`](slide-design.md) operationalizes into specific,
category-tagged checks. Stated here once, generically, so every mode's renderer designs *from*
them rather than rediscovering them.

- **Figure/ground.** The eye must instantly separate content from background. Contrast,
  spacing, and scrims serve this.
- **One visual hierarchy.** Each slide has a single clear focal point and an obvious reading
  order (size, weight, position, colour encode importance). Not two things shouting equally.
- **Alignment to an invisible grid.** Elements share edges and gridlines; nothing sits at an
  arbitrary offset. Alignment is the cheapest signal of care.
- **Whitespace is structural.** Negative space groups, separates, and rests the eye — it is
  designed, not leftover. Crowding and dead corners are both failures.
- **Signal over noise.** Every element earns its place; remove what doesn't carry meaning
  (Tufte's data-ink). Decorative clutter, redundant chrome, and gratuitous effects are noise.
- **Proximity & grouping (Gestalt).** Related items sit together; labels attach to the figure
  they describe; unrelated things are separated.
- **Consistency & repetition.** Recurring chrome, spacing rhythm, type scale, and layouts stay
  consistent across the deck — consistency is what reads as professional.
- **Legibility at distance.** Design for the back row: large type, high contrast, few words.
- **Structure over prose.** Cards, panels, columns, and diagrams beat paragraphs and bullet
  lists for scannability — show the structure of the idea, don't narrate it.
- **Colour with restraint & meaning.** A small palette used consistently; accent colour marks
  the one thing that matters, not everything.

## How the modes use this

- **GENERATE (all modes).** The renderer designs *from* Part B and must not emit any Part-A
  violation. Strict/free-form realize it in native `pptx`; preview/html realize it
  deterministically in styled HTML.
- **CONTROL (pptx modes).** The deterministic subset of Part A is audited (aspect, block,
  notes); a violation fails the build.
- **FEEDBACK (modes with a critique).** The critique walks [`slide-design.md`](slide-design.md)
  and treats any surviving **Part-A** violation as blocking (fix, don't defer), and any
  **Part-B** shortfall per that catalog's severity.
