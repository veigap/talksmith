# PPTX style: free-form

Visual specification for Talksmith's **free-form** PPTX style. The renderer judges per-slide layout from content, constrained only by the floor in §1–§4 below. For the alternative spec-driven style see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md); for the style-selection mechanism see [`../README.md`](../README.md). This file is self-contained — it duplicates the floor sections from `strict/pptx-prompt.md` by design so each style can evolve independently without coupling.

> **Starting a new deck?** Open [`base-template.pptx`](base-template.pptx) — a 1-slide cover-only foundation. Substitute the four §4.3 placeholders on slide 1; build every other slide fresh per §5 layout dispatch.

> **EMU primer.** 1 inch = 914400 EMU; 1 point = 12700 EMU; font `sz` is in hundredths of a point (`sz="1450"` = 14.5pt). Slide size is `9144000 × 5143500` EMU = `10.00 × 5.625` inches.

---

## 1. Canvas

| Property | Value |
|---|---|
| Aspect ratio | **16:9** |
| Slide size | `9144000 × 5143500` EMU (`10.00 × 5.625` inches; `720 × 405` pt) |
| Slide background | **Pure white `#FFFFFF`** on every slide. No tints, no off-whites, no warm greys. Emit as a single `<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>` on every layout. Non-negotiable floor — audited at CONTROL. |
| Master chrome | **None** — `slideMaster1.xml` has an empty `<p:spTree>`. Every visible mark lives on individual slides or layouts. |
| Speaker-notes pane | **Load-bearing, not decorative.** Per [`principles.md`](../../principles.md) → *Content* → *Speaker notes are the talk; the slide is the punctuation*, the notes pane carries the prose the slide replaces. The renderer emits every `### Notes` block from `final.md` into the corresponding slide's notes pane verbatim — no truncation, no dropping. |

---

## 2. Color system — the palette floor

Free-form does not relax the palette. Every `<a:srgbClr val="…"/>` in the rendered deck resolves to a hex below. Off-palette colors are a render failure, audited at CONTROL by [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py).

### 2.1 Text inks

| Hex | Role |
|---|---|
| `#3B3535` | Primary body text (warm near-black) |
| `#1F1E1E` | Titles, emphasis, dark labels |
| `#000000` | Code-block default ink + callout body |
| `#FFFFFF` | Inverted text (on dark surfaces) |
| `#6A737D` | Code comments (GitHub-light grey) |
| `#D73A49` | Code keywords (GitHub-light red) |
| `#DA1B2E` | Brand accent red, active state |
| `#F33447` | Bright accent red |
| `#005CC5` | Code strings / identifiers (GitHub-light blue) |

### 2.2 Fills (shapes, cards, pills, callouts)

| Hex | Role |
|---|---|
| `#FFFFFF` | Card body fill |
| `#F2F2F2` | Code-block surface fill (slide bg is `#FFFFFF` per §1) |
| `#F2EEEE` | Soft accent — left-strips, inactive markers |
| `#F9D2D6` | Pink chip — section labels, soft attention |
| `#F7BBC1` | Peach-pink callout — analogy / tip / warning |
| `#B8E6F5` | Light cyan callout — declarative claim / key takeaway |
| `#D8D4D4` | Mid-grey separator / connector |
| `#DA1B2E` | Active accent fill |
| `#F33447` | Active progress / connector |

**Semantic conventions** (recommended, not enforced beyond the palette membership): red = current/active/important · pink (`#F9D2D6`) = section identity · peach-pink (`#F7BBC1`) = analogy/tip/warning · cyan (`#B8E6F5`) = declarative claim · grey = inactive/secondary. Free-form may break these conventions when content demands (e.g. inverting red and pink for a slide about urgency) — the audit cares only about palette membership.

### 2.3 Corner radius (recommended)

Roundrect shapes use a **~5760 EMU (≈4.6 pt) constant corner radius** for visual consistency with the brand. This is a recommendation in free-form, not an enforced rule — a slide whose content reads better with sharper or softer corners may deviate, but the deviation must be intentional and applied consistently across that slide's siblings.

---

## 3. Typography — the font floor

Free-form does not relax the font palette. Every `<a:latin typeface="…"/>` resolves to one of the three faces below. No theme fonts (`+mj-lt`, `+mn-lt`); no system fallbacks. Audited at CONTROL by [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py).

| Role | Typeface | Used for |
|---|---|---|
| Display / titles / labels | **Roboto Mono Medium** | Slide titles, headings, labels, ALL-CAPS marks |
| Body prose | **Roboto** | Descriptive paragraphs, bullet text, captions |
| Code | **Consolas** | All code blocks (Roboto Mono is **not** used in code) |

The renderer overrides typeface at the run level on every text shape — never inherits from `+mj-lt` / `+mn-lt`. Type sizes are picked per slide from a reasonable scale (5pt – 40.5pt observed in the source reference deck); free-form does not pin specific sizes per slide-role beyond the cover.

**Default alignment is left.** Centering is reserved for in-shape labels, very short headings, and intentional design choices the critic can defend. Right-alignment is rare; use only for tabular numbers or page-foot-style metadata.

---

## 4. Cover slide — contractually fixed recipe (floor)

The cover is the deck's **identity slide and must be reproduced byte-for-byte structurally**, identical to the strict-style cover. Only the *content* of the four shapes changes per Talk; positions, sizes, fonts, colors, and z-order are fixed. The institution logo is part of the brand and never moves. Audited at CONTROL by the cover-fidelity check.

### 4.1 Background

Pure white `#FFFFFF` per §1.

### 4.2 Shapes (z-order: as listed)

| # | Role | EMU off (x,y) | EMU ext (w,h) | Inches off | Inches ext | Style |
|---|---|---|---|---|---|---|
| 1 | **Cover title** (`p:sp`, `rect`, no fill, no border) | `(496119, 536823)` | `(8151763, 1948458)` | `(0.542, 0.587)` | `(8.914, 2.131)` | Body insets `0,0,0,0`. `normAutofit`. One `<a:p>` with `algn="l"`, `lnSpc=104%`. Single run: `sz="4050"` (40.5pt), Roboto Mono Medium, `#1F1E1E`. |
| 2 | **Subtitle** (`p:sp`, `rect`, no fill) | `(496119, 2677269)` | `(6216923, 235297)` | `(0.542, 2.928)` | `(6.800, 0.257)` | `wrap="none"`. Body insets `0`. `algn="l"`. Single run: `sz="1450"` (14.5pt), Roboto Mono Medium, `#1F1E1E`. |
| 3 | **Author + date block** (`p:sp`, `rect`, no fill) | `(496119, 3219748)` | `(3295799, 560933)` | `(0.542, 3.521)` | `(3.603, 0.613)` | Two paragraphs. `algn="l"`, `lnSpc=123%`, `spcAft=900` (9pt). Each run: `sz="1150"` (11.5pt), **Roboto**, `#3B3535`. |
| 4 | **Institution logo** (`p:pic`) | `(7183562, 3248546)` | `(1469008, 1214065)` | `(7.856, 3.553)` | `(1.606, 1.328)` | PNG, `ppt/media/image-1-1.png`. `noChangeAspect="1"`. `<a:stretch><a:fillRect/></a:stretch>`. |

### 4.3 Content substitution

| Slot | Source in `final.md` frontmatter | Example |
|---|---|---|
| Shape #1 text | `presentation:` (the Subject from `profile.md`) | `Inteligencia Artificial Generativa Aplicada en Biomedicina` |
| Shape #2 text | `subtitle:` (Talk-specific, **required** — collected at Step 1 / Step 4) | `Clase 3: Ingeniería de Prompts y Técnicas Avanzadas` |
| Shape #3 paragraph 1 | `Autor: <presenter>` from `profile.md` Presenter section | `Autor: Paulo Veiga` |
| Shape #3 paragraph 2 | `Última Modificación: <Month, YYYY>` from frontmatter `date:` | `Última Modificación: Marzo, 2026` |
| Shape #4 image | `ppt/media/image-1-1.png` — preserved verbatim |  |

**Localization.** "Autor:" and "Última Modificación:" follow `Presentation language` from `profile.md`.

---

## 5. Layout dispatch — slide-by-slide judgment

After the cover, free-form has **no fixed layout taxonomy and no emit-rules table**. The renderer judges per slide from content, then logs its choice for traceability.

### 5.1 The dispatch loop

For each `## <H2>` in `final.md` (after the cover):

1. **Read the slide's content** — H2 title, body prose, images, code, tables, bullets, callouts, speaker notes. Read the section it belongs to (`# <H1>`) and the preceding/following slides for cycle-rhythm context.
2. **Choose a layout** that serves the content. Anything is fair game: full-bleed hero image, asymmetric two-column, three-band horizontal strip, centered manifesto, dense data table, single quote on white, image stack with caption rail, anything the slide actually wants. Strict's taxonomy (§13 in `../strict/pptx-prompt.md` — cards, image-grid, code-example, content+image, callout) is a useful **inspiration library** but not a constraint; cite it when applicable, deviate when content benefits.
3. **Emit the slide** honoring the floor: white bg (§1), §2 palette only, §3 fonts only. Use the cover (§4) byte-for-byte for slide 1.
4. **Log the choice** to a per-render sidecar at `talks/<Talk>/output/.layout-log.md` — one entry per slide:

   ```
   slide 7 · H2: "Why the diagnostic gap persists"
     chose: asymmetric 60/40 two-column, left=prose, right=hero-image with caption rail underneath
     why: the slide is one main claim supported by one evidentiary image; the claim deserves more horizontal room than a centered headline would give
     siblings: slide 6 was a centered manifesto; slide 8 is a three-band grid. Rhythm reads varied without feeling chaotic.
   ```

   The log is the audit trail an LLM or human reviewer reads to verify the renderer wasn't randomly picking layouts. It's also what the FEEDBACK phase critic uses when judging *composition rhythm* (practice 1 below) — without the log there's no way to see whether consecutive slides were chosen as a sequence or as isolated objects.

### 5.2 What the renderer must NOT do

- **Drop content to make a layout fit.** Every block in `final.md` appears on the rendered slide. Audited at CONTROL by [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py) — same rule, same audit, same exit code as strict.
- **Pick a layout for a single slide that breaks deck-wide coherence.** If slides 3–12 establish a generous-margins convention, slide 13 doesn't suddenly hug the edges. Coherence is rubric practice 8 below.
- **Treat the floor as a recommendation.** §1 (white bg) + §2 (palette) + §3 (fonts) + §4 (cover) are non-negotiable. A render that violates them fails CONTROL regardless of how good the slide looks.

### 5.3 Branded icons (§17 of strict) are optional in free-form

Strict mandates the 15-icon line-art catalog at `#DA1B2E` and forbids system emojis. Free-form **may** use the same icon set (it ships in `base-template.pptx`), but is not required to — photographs, hand-drawn marks, abstract glyphs, or no icons at all are all valid choices when the slide's content benefits. The only constraint: whatever icon idiom the deck picks must be applied consistently across the deck (mixing photographic icons on slide 5 with line-art icons on slide 12 is a coherence fail per practice 8).

System emojis are still discouraged — they render unpredictably across viewers — but not banned. When emojis appear, the renderer must either swap them to a chosen icon idiom or render them as text *consistently*. Inconsistent treatment (one slide swaps, the next strips) is a coherence fail.

### 5.4 Tables (§11 of strict) are allowed in free-form

Strict converts pipe-tables to card-grid because the source 53-slide reference deck contains zero native `<a:tbl>` elements. Free-form **may** emit native `<a:tbl>` when the content is genuinely tabular (a real data table reads better as a table than as cards). The choice is per-slide: if the table is 3-rows-by-2-columns of label/value pairs, emit it as cards anyway (cards read better at low N); if it's 12-rows-by-5-columns of comparison data, emit it as a table. Critic flags inconsistent treatment under practice 8.

---

## 6. FEEDBACK rubric — 8 practices

When the [CLAUDE.md](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) *Render cycle* enters its FEEDBACK phase, the orchestrator walks **this** rubric on every slide PNG. Same per-defect line format as strict (`slide N · practice K · <description> → <fix in this iteration | defer because <reason> | surface to presenter>`), same minor-as-defer discipline, same 3-cycle cap.

Practice #0 is the block-coverage precondition (same as strict practice #0 — every source block must appear as a shape on the rendered slide; enforced by [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py) in CONTROL before FEEDBACK runs). The remaining 8 practices are free-form-specific.

| # | Practice | What to look for |
|---|---|---|
| 0 | **Block-coverage precondition** | Same as strict — see [CLAUDE.md](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) Step 8 → *Post-render visual review*. Enforced by audit in CONTROL; if `[block-drop]`, do not enter FEEDBACK. |
| 1 | **Composition rhythm** | Across the deck, layout variety reads as *paced*, not random and not monotonous. Three consecutive identical card grids bore. Eight consecutive radically-different layouts read as chaos. The rhythm carries the audience between ideas; consecutive slides should feel like *steps in a sequence*, not *unrelated objects*. Read the per-slide `.layout-log.md` entries alongside the PNGs to judge whether sibling choices were made deliberately. |
| 2 | **Focal hierarchy** | One element on each slide draws the eye first; supporting content recedes. The first element ≠ the most decorative; it should be the most *load-bearing* (the claim, the chart, the diagram). Ambiguity is a fail; intentional rejection of a single focal point (e.g. a tiled gallery where variety *is* the message) is allowed but the critic must call it out as deliberate. |
| 3 | **Color use within palette** | §2 palette membership is enforced by `audit_palette_fonts.py` in CONTROL — every color is in-palette by the time FEEDBACK starts. This practice judges whether the chosen color is **emotionally apt** to the slide's content. A `#DA1B2E` bright-red callout on a slide about a privacy breach reads wrong even though red is in-palette. In-palette is a floor, not a pass. |
| 4 | **Type intent** | Each typographic choice (size, weight, case, family) has a job. Sizes drawn from a clear scale (no 17.3pt body next to 17pt body across slides); ALL-CAPS reserved for labels/section names; bold reserved for emphasis within prose, not decoration; italics reserved for citations / titles of works / non-English terms. Decorative variation ("make this line bigger because it looks empty") is a fail. |
| 5 | **Image scale + placement** | Aspect ratio preserved (enforced by [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_aspect_ratios.py) in CONTROL). Hero images dominate; supporting images supplement. No load-bearing detail cropped to fit a slot. Image-text gutters consistent; images don't crash into adjacent text. Photographs and diagrams may coexist, but their treatment (size relative to slide, framing, padding) is internally consistent. |
| 6 | **Typography quality (micro)** | No widows (single word on the last line of a paragraph). No orphans (heading at the bottom of a column, body on the next). Numbers in a column use tabular figures (aligned decimals). Headings don't break awkwardly across the right-margin gutter. Em-dashes are em-dashes (`—`), not double-hyphens (`--`). The marks that distinguish a designed deck from a wireframed one. |
| 7 | **Density — slide breathes** | Generous safe margins; no wall of text; no claustrophobic packed grid. The audience should absorb the slide's primary content in 3–5 seconds, then turn attention to the speaker. A slide that takes 30 seconds to *read* is the speaker's competitor, not their support. Test: *can the eye land and rest within a beat*. |
| 8 | **Coherence across slides** | Type sizes don't drift (what reads as "title" on slide 5 reads as "title" on slide 25); palette use stays internally consistent (an accent that meant "warning" on slide 4 doesn't mean "highlight" on slide 12); image and icon treatment stays internally consistent (if photographs are 4:3 inset with 0.3-in padding on slide 8, they are 4:3 inset with 0.3-in padding on slide 18; if icons are line-art on slide 3, they are line-art on slide 14). Free-form is not "different every slide"; it is "the right layout for each slide, with consistent treatment of recurring elements." Read with `.layout-log.md` to verify the renderer's choices form a system, not a sequence of one-offs. |

**Plus the aesthetic note.** After walking practices 0–8, the critic adds a one-sentence free-form aesthetic note per slide naming whatever the eye catches that the rubric does not — same discipline as strict. The rubric is the floor; the aesthetic note is where the critic's judgment shows. `aesthetic: clean` is a valid note when nothing catches the eye.

**Critique discipline carries forward.** Same as strict: every flagged cell of the slide × practice matrix gets *fix in this iteration* / *defer because <reason>* / *surface to presenter*. Silent `[minor] → ignore` is the same prohibited pattern. Free-form does not lower the bar on per-defect resolution; if anything it raises it, because there is no spec-side recipe to fall back on.

---

## 7. Render cycle integration

The render cycle (GENERATE → CONTROL → FEEDBACK → REGENERATE, 3-cycle cap) is style-agnostic and lives in [CLAUDE.md](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) → *Render cycle*. This section names the free-form-specific content of each phase.

| Phase | What runs in free-form |
|---|---|
| **GENERATE** | Cover (§4) byte-equivalent from `base-template.pptx`; every other slide built fresh per §5 layout dispatch. The renderer writes `.layout-log.md` alongside `final.pptx` as a sibling artifact (one entry per emitted slide; format in §5.1). |
| **CONTROL** | 5 audits — OOXML invariants per `../strict/pptx-prompt.md` §19.4 (style-agnostic structural rules), [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_aspect_ratios.py), [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py), [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py), and the cover-fidelity check (slide 1 of `final.pptx` byte-equivalent to slide 1 of `base-template.pptx` modulo the 4 placeholder substitutions). The layout-fit audit is **skipped** — free-form has no spec-predicted layout to compare against, and the per-slide `.layout-log.md` is what the FEEDBACK critic reads instead. |
| **FEEDBACK** | Walk §6's 8-practice rubric per slide; emit one `slide N · practice K · …` line per defect with resolution disposition. |
| **REGENERATE** | Re-render only the touched slides; cycle counter increments; flow returns to GENERATE for cycle N+1. The `.layout-log.md` is updated in place — re-emitted slides overwrite their previous entries, untouched slides retain theirs. |

---

## 8. Operating guide for the renderer

| Stage | What you do |
|---|---|
| 1 | Read this file end-to-end. Particularly: §1 (canvas), §2 (palette), §3 (fonts), §4 (cover recipe), §5 (dispatch + log), §6 (rubric the FEEDBACK phase will use to judge you). |
| 2 | Read `final.md` end-to-end. Cache the H1 sections, the H2 slides, the per-slide block inventories. |
| 3 | Open [`base-template.pptx`](base-template.pptx) as a working copy. **Slide 1 only** — copy verbatim, substitute the 4 cover placeholders per §4.3. |
| 4 | For each H2 in `final.md` after the cover, run the §5.1 dispatch loop: read content, choose layout, emit slide, log to `.layout-log.md`. |
| 5 | Emit speaker notes (`### Notes` blocks) verbatim into each slide's notes pane. |
| 6 | Write `final.pptx` to `talks/<Talk>/output/final.pptx` and `.layout-log.md` alongside it. |
| 7 | Hand back to the orchestrator for CONTROL (the 5 audits in §7) and FEEDBACK (the rubric in §6). |

When in doubt at dispatch time, read `strict/pptx-prompt.md` §13 (layout taxonomy) and §15 (emit-rules) for inspiration — strict's recipes are well-tested layouts that often serve free-form content too. The difference is that free-form picks them by *judgment* rather than by mechanical signal-match, and is free to invent layouts strict's taxonomy doesn't cover.
