Visual specification distilled from [`config/template.pptx`](template.pptx) (53 slides). All measurements are concrete and reproducible: a downstream generator should be able to emit `final.pptx` shapes matching the template by reading the EMU coordinates and color hexes verbatim from this file. For diagram-internal style see [`config/diagram-style.md`](diagram-style.md). Visual references for the two contractually-fixed slides are in [`template-previews/`](template-previews/) — they are the source of truth alongside this prose.

> **Starting a new deck?** Open [`config/base-template.pptx`](base-template.pptx) — it's the working foundation derived from this spec: cover + agenda with `{{placeholders}}` to substitute, a red separator banner, and 10 example slides demonstrating every recurring layout pattern. Each example slide carries a `TEMPLATE — <LAYOUT>` pill so it's unambiguous during generation. See **§17** for the branded icon library, **§18** for a slide-by-slide reference of `base-template.pptx`, and **§19** for the operating guide an agent/skill follows when rendering `final.md` into `.pptx` (reading order, workflow stages, output contract, anti-patterns).

> **EMU primer.** 1 inch = 914400 EMU; 1 point = 12700 EMU; font `sz` is in hundredths of a point (`sz="1450"` = 14.5pt). Slide size is `9144000 × 5143500` EMU = `10.00 × 5.625` inches. All shape coordinates below are quoted in **both** EMU (XML-faithful) and inches (human-readable).

---

## 0. Style modes — strict vs. free-form

Talksmith renders PPTX in one of two modes, declared per-Talk via `draft.md` frontmatter `style: strict | free-form` (default `strict` when absent; Editor asks at Step 1 (Frame) per [CLAUDE.md](../CLAUDE.md) → *Step 1*).

| | **Option 1 — strict** | **Option 2 — free-form** |
|---|---|---|
| Source of truth for layout | §15.5 emit-rules table + §15.6.1 discriminator | Renderer's judgment per slide content |
| Layout vocabulary | §4 (cover), §5 (agenda + dividers), §6 (section pill), §7 (cards), §8 (callouts), §9 (code), §13 (taxonomy) | Free-form within the **floor** below |
| Starting deck | [`base-template.pptx`](base-template.pptx) as working copy (§18) | [`base-template.pptx`](base-template.pptx) for **slide 1 cover only**; rest is built fresh |
| Pre-emit decision audit | §15.6 (mandatory) | N/A — renderer logs layout choice per slide for traceability, no discriminator to walk |
| Post-emit layout-fit audit | §19.5 [`audit_layout_fit.py`](../.claude/skills/md-to-pptx/audit_layout_fit.py) | N/A — no spec-predicted layout to compare against |
| FEEDBACK rubric (CLAUDE.md Step 8 cycle) | 12-practice rubric ([CLAUDE.md](../CLAUDE.md) → *Post-render visual review*) | Free-form design rubric — see §15.7 below |
| Branded icons (§17) required | Yes — emojis swap to catalog icons per §17.7 | No — free-form renders may use icons from §17.1 *or* any visually consistent source (photographs, hand-drawn marks, abstract glyphs); the §17.2 line-art style is recommended but not enforced |
| Native `<a:tbl>` tables (§11) | Forbidden — converted to card-grid | Allowed when content warrants — a real data table reads better as a table than as cards |
| Section pill (§6) on content slides | Required | Free — emit if it aids navigation; omit if the deck's section structure is implicit |

### 0.1 The Option 2 floor (non-negotiable in both modes)

Free-form does not mean "anything goes." Four rules hold for **both** modes; an Option 2 render that violates any of these is a render failure exactly as in Option 1:

1. **Cover slide (§4)** — slide 1 is byte-equivalent to the cover-recipe with substituted placeholders. The cover is the deck's identity slide; both modes ship the same one. Audited at §19.5 *cover-fidelity check* — slide 1 must come from `base-template.pptx` with only the four §4.3 placeholder substitutions applied.
2. **Color palette (§2)** — every `<a:srgbClr val="…"/>` in the rendered deck resolves to a hex in the §2 palette (text inks, fills, accents). Off-palette colors are forbidden in both modes. Audited at §19.5 by [`audit_palette_fonts.py`](../.claude/skills/md-to-pptx/audit_palette_fonts.py).
3. **Font palette (§3.1)** — every `<a:latin typeface="…"/>` resolves to Roboto Mono Medium (titles/labels/headings), Roboto (body), or Consolas (code). No theme fonts (`+mj-lt`, `+mn-lt`); no system fallback fonts. Audited by the same script.
4. **White background (§1)** — every slide carries a pure-white `<p:bg>` solid fill. No tints, no overlays, no legacy black+overlay recipe. Same rule in both modes.

Other Option-1 rules — section pill, agenda as slide 2, no native tables, line-art icons, §15.5 emit-rules, §15.6 discriminator audit — are **Option-1-only**. The renderer for an Option-2 Talk treats them as recommendations, not requirements; the §19.5 layout-fit audit does not run.

### 0.2 When to pick which

| Pick **strict** when | Pick **free-form** when |
|---|---|
| The Talk is a class in a course series and visual consistency across classes matters | The Talk is a one-off, a keynote, a hand-crafted pitch |
| The deck will be skimmed asynchronously (recorded video, PDF distribution) — predictable layout helps scanning | The deck will be presented live and the speaker drives every transition |
| The presenter wants the workflow to do the visual decisions | The presenter has design instincts they want the renderer to follow |
| Most of the content fits cleanly into §13's taxonomy (cards, image-grid, code-example, content+image) | A meaningful fraction of slides have content that doesn't fit the taxonomy — manifestos, hero quotes, dense data visualizations, full-bleed imagery |

The two modes are not better/worse — they trade *predictability* for *expressive range*. The same fork can carry Talks in both modes; the `style:` field on each Talk's `draft.md` is the switch.

### 0.3 The cycle applies to both modes

The CLAUDE.md *Render cycle* (GENERATE → CONTROL → FEEDBACK → REGENERATE, 3-cycle cap) runs identically in both modes. What differs is the **content** of CONTROL (which audits fire) and the **content** of FEEDBACK (which rubric the orchestrator walks):

| Phase | Strict | Free-form |
|---|---|---|
| GENERATE | per §19.3 7-stage workflow + §15.5 emit-rules | per §15.7 free-form layout dispatch (no fixed stages beyond cover + slide-by-slide judgment) |
| CONTROL | aspect-ratio + layout-fit + block-coverage + palette/fonts + OOXML | aspect-ratio + block-coverage + palette/fonts + cover-fidelity + OOXML (layout-fit skipped) |
| FEEDBACK | 12-practice rubric ([CLAUDE.md](../CLAUDE.md)) | 8-practice free-form design rubric (§15.7) |
| REGENERATE | re-render touched slides | same |

The generate-control-feedback-improve loop is **the constant**; the rules it loops against are what the `style:` mode switches.

---

## 1. Canvas

| Property | Value |
|---|---|
| Aspect ratio | **16:9** |
| Slide size | `9144000 × 5143500` EMU (`10.00 × 5.625` inches; `720 × 405` pt) |
| Slide background | **Pure white `#FFFFFF`** on every slide. No tints, no off-whites, no warm greys. Emit as a single `<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:bgPr></p:bg>` on every layout. (Historical note: the source 53-slide reference deck used a black `<p:bg>` + 95%-alpha white overlay producing apparent `#F2F2F2`; this fork has standardized on pure white. Generators must emit `#FFFFFF` solid — do not reproduce the legacy two-layer recipe.) |
| Master chrome | **None** — `slideMaster1.xml` has an empty `<p:spTree>`. No footer, page number, or logo on master. Every visible mark lives on individual slides or layouts. |
| Theme | `theme1.xml` declares Calibri Light / Calibri and the standard Office accent palette. **Zero slides use them** — every run overrides theme defaults at the `<a:rPr>` level. Treat the theme as residual scaffolding; never inherit from it. |
| Speaker-notes pane | **Load-bearing, not decorative.** The reference 53-slide template happened to leave the pane sparse (mean ~2 chars/slide); that is a property of *that one* source deck, **not** the contract for generated decks. Per [`principles.md`](principles.md) → *Content* → *Speaker notes are the talk; the slide is the punctuation*, the notes pane carries the prose the slide replaces. A generated deck with empty notes panes signals an over-authored deck where the slide is doing the speaker's job. The renderer emits every `### Notes` block from `final.md` into the corresponding slide's notes pane verbatim — no truncation, no dropping. |

---

## 2. Color system

The deck uses a tight palette. Office theme colors (`#4472C4`, `#ED7D31`, etc.) appear **zero times** in slide content. Use only the colors below.

### 2.1 Text inks

| Hex | Role | Run count |
|---|---|---|
| `#3B3535` | Primary body text (warm near-black) — Roboto/Roboto Mono | 837 |
| `#1F1E1E` | Titles, emphasis, dark labels | 121 |
| `#000000` | Code-block default ink + callout body | 92 |
| `#FFFFFF` | Inverted text (on red active dot, dark surfaces) | 76 |
| `#6A737D` | Code comments (GitHub-light grey) | 43 |
| `#D73A49` | Code keywords (GitHub-light red) | 23 |
| `#DA1B2E` | Brand accent red, active state, agenda active-dot fill | 20 |
| `#F33447` | Bright accent red — active progress-bar segment | (paired with `#DA1B2E`) |
| `#005CC5` | Code strings / identifiers (GitHub-light blue) | 12 |

### 2.2 Fills (shapes, cards, pills)

| Hex | Role |
|---|---|
| `#FFFFFF` | Card body fill (the rounded-rect card itself) |
| `#F2F2F2` | Code-block surface fill (slide background is pure white `#FFFFFF` per §1 — do not reuse `#F2F2F2` as a slide bg in generated decks) |
| `#F2EEEE` | Card left-strip accent, **inactive agenda dot** |
| `#F9D2D6` | Section-label pill (top-left of every content slide) |
| `#F7BBC1` | Callout / "analogy" / "tip" rounded rectangle |
| `#D8D4D4` | Agenda spine and **inactive** horizontal connector |
| `#DA1B2E` | Active agenda dot fill |
| `#F33447` | Active agenda horizontal connector |

**Semantic conventions.** **Red = current / active / important** · **pink (`#F9D2D6`) = section identity (top-left pill)** · **peach-pink (`#F7BBC1`) = call-attention block (analogy / tip / warning)** · **white card with `#F2EEEE` left-strip = grouped enumerated item** · **grey (`#D8D4D4`, `#F2EEEE`) = inactive / secondary**. Do not introduce new accent hues; reuse from this palette.

### 2.3 Corner radius (every `roundRect` in the deck)

Every `roundRect` shape — pills, cards, callouts, agenda dots, code surfaces — resolves to a **constant ~5760 EMU (≈0.0063 in ≈ 4.6 pt) corner radius**, regardless of overall shape size. The `<a:avLst><a:gd name="adj">` values vary (`835`–`10000`) because the value is encoded as a fraction of the shape's shorter side, but the resulting visual radius is always ~4.6 pt. A generator that draws roundRects should hard-code a **5760 EMU corner radius** and back-compute `adj` per shape.

---

## 3. Typography

### 3.1 Faces

Four typefaces are embedded in `presentation.xml`. Slide bodies use only these — no system fallbacks observed.

| Role | Typeface | Frequency in slides | Used for |
|---|---|---|---|
| Display / titles / labels | **Roboto Mono Medium** | 443 runs | Cover title, slide titles, section pill, agenda numbers, card headings, sub-headings, callouts |
| Body prose | **Roboto** | 597 runs | Descriptive paragraphs, bullet text, captions |
| Code | **Consolas** | 176 runs | All code blocks (Roboto Mono is **not** used in code) |
| Rare accent | Roboto Mono Light | 8 runs | Negligible — treat as Roboto Mono Medium |

The deck overrides typeface at the run level on every text shape. New slides must do the same — never inherit from `+mj-lt` / `+mn-lt`.

### 3.2 Type scale (point sizes encoded as `sz="<pt*100>"`)

Sizes range 5pt – 40.5pt in 0.5pt increments. Bucketed by role:

| Role | Range | Typical | Notes |
|---|---|---|---|
| Cover title (slide 1 only) | 40.5pt | 40.5pt | Roboto Mono Medium, `#1F1E1E`, line-spacing `lnSpc=104%` |
| Agenda / divider title (`Agenda`) | 20pt – 21.5pt | **21.5pt** | Roboto Mono Medium, `#1F1E1E` |
| Slide title (H2 — `## Foo`) | 17pt – 31pt | adaptive, mean ~26pt | Roboto Mono Medium, `#1F1E1E` (see §3.3) |
| Subsection / card heading | 13pt – 15.5pt | 13.5pt | Roboto Mono Medium, `#3B3535` |
| Body paragraph | 10.5pt – 12.5pt | 11pt | Roboto, `#3B3535` |
| Card body / dense text | 8.5pt – 10pt | 9pt | Roboto |
| Code (Consolas) | 6.5pt – 10pt | 8.5pt | `#000000` with syntax-color spans |
| Captions, fine print | 5pt – 7pt | 6.5pt | Last resort; used when card density is extreme |

### 3.3 Title sizing is adaptive

There is **no single H2 point size**. Titles fit to one line across the available width. Examples:

| Slide | Title | Length | sz |
|---|---|---|---|
| 13 | Los 6 Componentes de un Prompt | long | 17pt |
| 8 | Limitaciones de los Foundational Models | longest | 31pt |
| 47 | Recorrido del Paciente | medium | ~26pt |

A renderer should measure the title text width in Roboto Mono Medium and pick the largest `sz` in `[17, 18, 19, 20, 21, 22.5, 24, 26, 28, 30, 31]` that fits the content area (~9 inches wide, less the section-pill offset of ~0.54 in).

### 3.4 Text alignment

| Alignment | Run count | Used for |
|---|---|---|
| Left (`algn="l"`) | 1049 | Default for everything |
| Center (`algn="ctr"`) | 78 | Numbers inside agenda dots, very short labels |
| Right (`algn="r"`) | 8 | Edge cases only |

**Default to left.** Centering is for in-shape numbers, not body text.

### 3.5 Title metadata

| Property | Value |
|---|---|
| Position | Top-left, `~(0.42 – 0.54, 0.67 – 1.14)` inches (directly below the section pill) |
| Word count | min 1, max 6, **mean 3.6** |
| Capitalization | Sentence case in the presentation language (`¿Qué es un Prompt?`, `Limitaciones de los Foundational Models`). The section pill above is **ALL CAPS**; the slide title beneath is **sentence case**. |
| Punctuation | Question marks allowed (`¿…?`), colons for subtitle pattern (`Tree of Thought (ToT): Ejemplo`) |
| Subtitle | No separate subtitle placeholder. When a sub-line is needed, use the colon convention inside the same title |
| Color | `#1F1E1E` |
| Font | Roboto Mono Medium |

**`body_y_start` depends on the title's actual wrap state, not on a defensive margin.** Renderers commonly compute `body_y_start = title_y + max_title_height` using the *maximum* height the title could occupy under any wrap (a defensive constant baked into the chars-per-line picker). That's wrong: a 14-char title that fits one line at 31pt has a *measured* `title_height` of roughly one line-height (~0.50 in), and `body_y_start` should land just below that — not below the 2- or 3-line maximum the worst-case title would have produced. When the defensive margin wins, every short-title slide ships with a visible title-to-body gap. The contract: after sizing the title via the §3.3 ladder, **measure the resulting wrapped text height** (number of wrap lines × `line_height_for(sz)`) and set `body_y_start = title_y + actual_title_height + body_gap` where `body_gap ≈ 0.20 in`. The picker's job is to choose `sz`; the layout's job is to read the resulting height — not to reserve room the title turned out not to need.

---

## 4. Slide 1 (Cover) — contractually fixed recipe

> **Visual reference:** [`template-previews/slide-01-cover.png`](template-previews/slide-01-cover.png).
>
> **The cover is the deck's identity slide and must be reproduced byte-for-byte structurally.** Only the *content* of the four text/image shapes changes per Talk; positions, sizes, fonts, colors, and z-order are fixed. The institution logo (Universidad Austral) is part of the brand and never moves.

### 4.1 Background

Pure white `#FFFFFF` per §1. Same on every slide in the deck.

### 4.2 Shapes (z-order: as listed; later items paint on top)

| # | Role | EMU off (x,y) | EMU ext (w,h) | Inches off | Inches ext | Style |
|---|---|---|---|---|---|---|
| 1 | **Cover title** (`p:sp`, `rect`, no fill, no border) | `(496119, 536823)` | `(8151763, 1948458)` | `(0.542, 0.587)` | `(8.914, 2.131)` | Body insets `0,0,0,0`. `normAutofit`. One `<a:p>` with `algn="l"`, `lnSpc=104%`. Single run: `sz="4050"` (40.5pt), Roboto Mono Medium, `#1F1E1E`. Wraps to multiple lines as needed. |
| 2 | **Subtitle** (`p:sp`, `rect`, no fill) | `(496119, 2677269)` | `(6216923, 235297)` | `(0.542, 2.928)` | `(6.800, 0.257)` | `wrap="none"` (single line). Body insets `0`. `algn="l"`, `lnSpc=104%`. Single run: `sz="1450"` (14.5pt), Roboto Mono Medium, `#1F1E1E`. |
| 3 | **Author + date block** (`p:sp`, `rect`, no fill) | `(496119, 3219748)` | `(3295799, 560933)` | `(0.542, 3.521)` | `(3.603, 0.613)` | Two paragraphs. `algn="l"`, `lnSpc=123%`, `spcAft=900` (9pt) between paragraphs. Each run: `sz="1150"` (11.5pt), **Roboto** (not Mono), `#3B3535`. |
| 4 | **Institution logo** (`p:pic`) | `(7183562, 3248546)` | `(1469008, 1214065)` | `(7.856, 3.553)` | `(1.606, 1.328)` | PNG, `ppt/media/image-1-1.png` (Universidad Austral, 616×510 px, RGBA). `noChangeAspect="1"`. `<a:stretch><a:fillRect/></a:stretch>`. |

### 4.3 Content substitution slots

When generating a new cover, substitute **content only**; preserve geometry exactly.

| Slot | Source in `final.md` frontmatter | Example |
|---|---|---|
| Shape #1 text | `presentation:` (the Subject from `profile.md`) | `Inteligencia Artificial Generativa Aplicada en Biomedicina` |
| Shape #2 text | `subtitle:` (Talk-specific, **required** — collected in Step 4 per CLAUDE.md). The Subject in shape #1 is fork-level and identical across every Talk; this subtitle is what distinguishes *this* class. Do not leave the placeholder text; do not omit the shape. | `Clase 3: Ingeniería de Prompts y Técnicas Avanzadas` |
| Shape #3 paragraph 1 | `Autor: <presenter>` — `<presenter>` from `profile.md` Presenter section | `Autor: Paulo Veiga/Marcos Sanchez Sorondo` |
| Shape #3 paragraph 2 | `Última Modificación: <Month, YYYY>` from `final.md` frontmatter `date:` | `Última Modificación: Marzo, 2026` |
| Shape #4 image | `ppt/media/image-1-1.png` (institution logo, never replaced unless presenter explicitly swaps brands) | (binary preserved verbatim) |

**Cover title line breaks.** The shape uses `normAutofit` so PowerPoint will reflow long titles automatically; lengths up to ~80 chars at 40.5pt have been observed to wrap to 3 lines comfortably within the 2.131-in shape height. Do not hand-insert line breaks.

**Localization.** "Autor:" and "Última Modificación:" follow the `Presentation language` from `profile.md`. English equivalents: "Author:" / "Last Modified:". Generators must localize these labels, not the content.

---

## 5. Slide 2 (Agenda) — contractually fixed recipe

> **Visual reference:** [`template-previews/slide-02-agenda.png`](template-previews/slide-02-agenda.png).
>
> **The Agenda follows directly after the Cover and is the only navigation chrome in the deck.** It re-appears as a section divider at positions 12, 17, 21, 40, 45, 52 — each instance is identical except for **which numbered item is highlighted as active**. There are no other "section divider" layouts.

### 5.1 Background

Pure white `#FFFFFF` per §1.

### 5.2 The fixed chrome (title + spine)

| # | Role | EMU off | EMU ext | Inches off | Inches ext | Style |
|---|---|---|---|---|---|---|
| 1 | Title `Agenda` | `(480640, 504974)` | `(3246834, 348704)` | `(0.526, 0.552)` | `(3.551, 0.381)` | `algn="l"`, body insets `0`. `sz="2150"` (21.5pt), Roboto Mono Medium, `#1F1E1E`. |
| 2 | Vertical spine | `(606103, 994172)` | `(14288, 3644354)` | `(0.663, 1.087)` | `(0.016, 3.986)` | `roundRect`, fill `#D8D4D4`. Spans dot row 1 top (`y=1.087`) to dot row 7 bottom + extra (`y≈5.073`). Width 14288 EMU = 1.15 pt. |

### 5.3 Per-item geometry (one row per agenda entry)

Items are stacked vertically with a **constant stride of `540693 EMU (0.591 in)`** between row tops. The agenda emits **one row per section** — there is no fixed row count. Row 1's top is fixed at `994172 EMU (1.087 in)`; row k's top = `994172 + (k - 1) × 540693` EMU.

The source template happened to have 7 sections, so its measured rows landed at:

| Item | y EMU | y inches |
|---|---|---|
| 1 | 994172 | 1.087 |
| 2 | 1534864 | 1.679 |
| 3 | 2075557 | 2.270 |
| 4 | 2616250 | 2.861 |
| 5 | 3156942 | 3.452 |
| 6 | 3697635 | 4.044 |
| 7 | 4238327 | 4.635 |

For N ≠ 7, recompute via the formula. **Capacity check:** the slide canvas is `5143500 EMU (5.625 in)` tall; row N's bottom shape (subtitle) extends ~`400198 EMU` below `y_dot`. The last fully-contained row N satisfies `994172 + (N − 1) × 540693 + 400198 ≤ 5143500`, i.e. **N ≤ 8 fits cleanly**. For 9 ≤ N ≤ 10, the renderer should still emit rows (with a warning that the bottom row crowds the slide edge); for N > 10, surface to the presenter — the agenda layout's vertical room is genuinely exhausted and a different chrome is needed.

Each row consists of 5 shapes (positions relative to `y_dot = row top`):

| Shape | EMU off | EMU ext | Inches | Active fill | Inactive fill | Notes |
|---|---|---|---|---|---|---|
| **Dot** (`roundRect`) | `(480603, y_dot)` | `(250999, 250999)` | `0.274 × 0.274` square | `#DA1B2E` | `#F2EEEE` | Corner radius ~25100 EMU = 0.027 in (softly rounded square, not a circle). |
| **Number text** (`rect`, inside dot) | `(522387, y_dot + 20873)` | `(167357, 209178)` | `0.183 × 0.229` | text `#FFFFFF` | text `#3B3535` | `sz="1300"` (13pt), Roboto Mono Medium. The number "N" is centered inside the dot via shape padding (x-padding ≈ 41784 EMU each side; y-padding ≈ 20873 EMU top/bottom). |
| **Horizontal connector** (`roundRect`) | `(717314, y_dot + 118319)` | `(334714, 14288)` | `0.366 × 0.016` | `#F33447` | `#D8D4D4` | A thin horizontal bar joining the dot to the item title. Y-offset 118319 EMU places it ~vertically centered on the dot. |
| **Item title** (`rect`, no fill) | `(1164059, y_dot + 38323)` | `(varies, 174278)` | `varies × 0.191` | `#3B3535` | `#3B3535` | `sz="1050"` (10.5pt), Roboto Mono Medium. Width = `min(measured-text-width + 50000, 2843808)` EMU; tight content boxes are observed in the template. |
| **Item subtitle** (`rect`, no fill) | `(1164059, y_dot + 254719)` | `(7499300, 145479)` | `8.201 × 0.159` | `#3B3535` | `#3B3535` | `sz="850"` (8.5pt), Roboto (not Mono). Single line at full width. |

### 5.4 Active-state rules

- **Exactly one** item is "active" per agenda instance — the section the presenter is about to enter.
- On the active row: dot fill = `#DA1B2E`, number text = `#FFFFFF`, horizontal connector = `#F33447`.
- On every other row: dot fill = `#F2EEEE`, number text = `#3B3535`, horizontal connector = `#D8D4D4`.
- Item title and subtitle text colors **do not change** with active state — always `#3B3535`. The signal is the dot + connector, not the text.

### 5.5 Content substitution

| Slot | Source |
|---|---|
| Item title (1..N) | The H1 of section k in `final.md` (the numbered section header, e.g. `# 3. In-Context Learning`). Strip the leading `k. `. |
| Item subtitle (1..N) | Section k's `Subtitle:` field if present; else a single-line summary of the section's Goal. |
| Active item index | The agenda instance's position in the deck — the first agenda (after the cover) highlights item 1; the agenda before section k highlights item k. The mapping is **invariant**: agenda instance k highlights item k. |

**The agenda emits exactly N rows, where N = number of H1 sections in `final.md`.** N is not fixed — the source template happened to have 7, but `base-template.pptx` contains 7 placeholder rows and the renderer is expected to clone or delete rows to match N. Capacity per §5.3: N ≤ 8 fits cleanly; 9–10 emits with a tightness warning; N > 10 surfaces to the presenter (the agenda chrome is out of vertical room and an alternate layout is needed).

### 5.6 Agenda instance positions

The agenda appears at slide 2 (active = 1, doubles as section 1's divider) and is re-emitted before each subsequent section's first content slide (active = 2, 3, …, N). With N sections the deck contains **N agenda instances total: 1 after the cover + (N − 1) re-emits between sections.** There is no separate "section title" layout.

For reference, the source template (53 slides, 7 sections) placed its agenda re-emits at slide positions 2, 12, 17, 21, 40, 45, 52 — those positions are descriptive of that one deck, not prescriptive. Generators key off section transitions in `final.md`, not absolute slide numbers.

### 5.7 Agenda title-length guidance

Section H1s authored in `final.md` become both the agenda row text (§5.5) **and** the section pill text (§6) on every subsequent content slide in that section. Two consumers, two different visual envelopes — short titles serve both well; long titles strain both. Authoring guidance, not a render gate:

- **Target ≤ 25 characters** per [`principles.md`](principles.md) line 34 → *Title-length budget*. At this length the agenda row renders at full type-scale and the §6 pill renders as a clean single-line chip at `sz="800"` without entering the downsize/wrap ladder.
- **Acceptable up to ~50 characters.** The agenda still fits its row; the §6 pill renders single-line at `sz="800"` (up to ~3.1 in width). No quality loss.
- **Long but renderable, ~50–80 characters.** The pill enters the downsize ladder (`sz="800" → "700" → "650"`) to stay single-line, or wraps to 2 lines at the smallest size. Renders cleanly — the renderer's §6 sizing algorithm is designed to never break — but the pill becomes visually heavier than ideal, and the agenda row may need a smaller subtitle to balance.
- **Beyond ~80 characters.** Still renders without breaking, but the pill occupies enough horizontal space that the slide title below loses its visual primacy. Strong signal to abbreviate the H1 at authoring time. Common reshape: drop the descriptive subordinate clause and move it to the section subtitle (which renders in the agenda row but not in the per-slide pill).

The renderer never fails on length — see §6 *Sizing algorithm* steps 4–6, which always produce a non-broken pill regardless of how long the label is. This subsection exists so the Editor / Composer can author with both consumers in mind during Step 4, not so the renderer has a reason to reject a long H1.

---

## 6. Section-label pill (universal chrome)

Every content slide (49 of 53 — excluding cover, the 53 closing-CTA, and 3 unusual ones) carries a small pill in the **top-left corner** identifying the parent section.

| Property | Value |
|---|---|
| Geometry | `roundRect`, `prstGeom prst="roundRect"` |
| Position | `(0.53, 0.55)` inches median; range `(0.39 – 0.54, 0.41 – 0.84)` |
| Size | **Computed per-slide from the pill text** — never hardcoded. See *Sizing algorithm* below. Source-deck observed range `1.11 – 3.06` × `0.14 – 0.33` in. |
| Fill | `#F9D2D6` |
| Corner radius | ~5760 EMU (4.6 pt), constant — see §2.3 |
| Stroke | None |
| Text shape | A separate `rect` overlay inside the pill, body insets `0`. The pill itself contains no text. |
| Text | ALL CAPS, `sz="550" – "900"` (5.5pt – 9pt) typical, Roboto Mono Medium, `#3B3535` |
| Alignment | Left |

**Sizing algorithm — pill geometry is a function of pill text, not a fixed default.** The single most common §6 failure mode is a renderer emitting a hardcoded pill width (e.g., inherited from a base-template reference slide whose label happened to be shorter), so a real section name overflows the pill background and wraps below it with no fill — the pink chip covers line 1, line 2 hangs unstyled below the chip. Avoid by computing geometry from the text every time:

1. **Measure the pill text** in Roboto Mono Medium at the chosen `sz` (default `sz="800"` = 8pt). Use `monospace_glyph_w ≈ 0.0535 in × (sz/800)` and `line_h ≈ 0.115 in × (sz/800)` as the renderer's measurement constants for Roboto Mono Medium — they match the source deck's observed pill widths to within ~3% (e.g. 24-char label at 8pt → `24 × 0.0535 = 1.28 in` text width, matches the 1.11–3.06 in observed range).
2. **Padding:** `horizontal_padding = 0.15 in` per side, `vertical_padding = 0.04 in` per side. Constant; do not scale with text length.
3. **Single-line preferred — pill stays one line whenever possible.** `pill_cx = text_w + 2 × horizontal_padding`, `pill_cy = line_h + 2 × vertical_padding`.
4. **Single-line cap:** if `pill_cx > 4.00 in`, try downsizing the text to `sz="700"` (7pt) then `sz="650"` (6.5pt) and recomputing; if any single-line width fits the 4.00-in cap, ship that single-line pill at that smaller `sz`.
5. **Multi-line fallback** (when single-line at `sz="650"` still exceeds the cap): the pill grows downward, never rightward, wrapping at the nearest whitespace before `pill_cx_max = 4.00 in`. `pill_cy = N_lines × line_h + 2 × vertical_padding` where `N_lines` is whatever the text requires (typically 2; rarely 3). The slide title's `y` offset (§3.5) shifts down by `(pill_cy − single_line_cy)` to preserve the gap between pill and title. The pill fill always covers the full text — no line ever hangs unstyled below the chip.
6. **Floor — `sz="550"` (5.5pt).** Do not shrink below this; if a label at 5.5pt still requires multi-line wrap, accept the wrap. The renderer's contract is *always produce a non-broken pill*, regardless of label length — there is no length at which the renderer is permitted to fail, truncate, ellipsize, or let text overflow the background.

**Authoring-side budget (cross-reference).** [`principles.md`](principles.md) line 34 recommends section H1s ≤ 25 characters as a deck-quality guideline — short pills read cleaner and leave more room for the slide title below. The renderer does **not** enforce this — long H1s render correctly via the downsize-then-wrap ladder above. The 25-char target is editorial guidance for the Editor / Composer in Step 4; the renderer's job is to make any length look clean. See §5.7 for the same guidance applied at agenda-authoring time.

**Anti-patterns.** Do not: emit a fixed-width pill independent of text (e.g. always 1.88 in because that was the median in the source deck); shrink the text below `sz="550"` to fit; silently truncate the label with an ellipsis (changes meaning; an audience reading "ECG — EL ELECTRO…" cannot recover the rest); let text overflow the pill background visually (the chip covers part of the text, the rest hangs in white).

The pill text mirrors the active **agenda section name verbatim, uppercased**. Examples (all of these render cleanly via the sizing ladder above — the renderer never fails on length):
- Agenda item 1 "ECG" → pill text `ECG` (3 chars — single-line at default `sz="800"`)
- Agenda item 2 "ECG — el electrocardiograma" → pill text `ECG — EL ELECTROCARDIOGRAMA` (27 chars — single-line at `sz="800"`, width ~1.74 in well under cap)
- Agenda item 3 "Fundamentos de Foundational Models" → pill text `FUNDAMENTOS DE FOUNDATIONAL MODELS` (34 chars — single-line at `sz="800"`, width ~2.12 in, still under cap)
- Agenda item 4 (extreme) "Ingeniería de prompts estructurada y técnicas avanzadas" → 55 chars — single-line at 8pt would be ~3.24 in (under cap), so still single-line; only at 70+ chars does the ladder enter downsize/wrap territory.

Every content slide under a section must carry this pill — it is the only thing tying a content slide back to its parent agenda entry.

---

## 7. Card pattern (recurring grouped-item shape)

Used for grouped items: slide 13's "6 components", slide 47/48 patient-journey rows, slide 53's "4 modules". Two variants are in use.

### 7.1 Numbered card with left-strip (slide 13)

Each card is a stack of **5 shapes**. Slide-13 measurements (one row):

| Shape | EMU off | EMU ext | Inches | Style |
|---|---|---|---|---|
| Outer card | `(384476, 1005842)` | `(4085167, 588086)` | `(0.42, 1.10)` × `(4.47, 0.64)` | `roundRect`, fill `#FFFFFF`, no stroke |
| Left strip | `(393189, 1015045)` | `(357027, 567039)` | `(0.43, 1.11)` × `(0.39, 0.62)` | `rect` (sharp), fill `#F2EEEE` |
| Number text | `(494833, 1218812)` | `(127635, 167357)` | `(0.54, 1.33)` × `(0.14, 0.18)` | `sz="1000"` (10pt), Roboto Mono Medium, `#3B3535`, centered |
| Card heading | `(789055, 1107603)` | `(1107305, 137389)` | `(0.86, 1.21)` × `(1.21, 0.15)` | `sz="850"` (8.5pt), Roboto Mono Medium, `#3B3535` |
| Card body | `(789055, 1284058)` | `(3589248, 210418)` | `(0.86, 1.40)` × `(3.92, 0.23)` | `sz="650"` (6.5pt), Roboto, `#3B3535` |

Vertical stride between rows in slide 13: **0.69 in** (rows at y=1.10, 1.79, 2.48, 3.17, …). Six cards stacked in a 4.47-in-wide column on the left, paired with a worked example or code on the right.

### 7.2 Plain title-only card (slide 7)

Smaller, no left strip, no number. Used for sibling cards in a flat grid.

| Shape | Inches off | Inches ext | Style |
|---|---|---|---|
| Card | `(5.19, 2.03)` | `(2.07, 1.63)` | `roundRect`, fill `#FFFFFF`, no stroke |
| Heading | `(5.37, 2.21)` | `(1.72, 0.24)` | `sz="1350"` (13.5pt), Roboto Mono Medium, `#3B3535` |
| Body | `(5.37, 2.57)` | `(1.72, 0.67)` | `sz="1100"` (11pt), Roboto, `#3B3535` |

The card's inner padding is **~0.18 in** on the left (`5.37 − 5.19 = 0.18`) and **~0.18 in** on the top (`2.21 − 2.03 = 0.18`).

### 7.3 Lead + N items — choose card-row (§7.4) or icon-bullet list (§7.5)

A very common slide shape is: **section pill, large title, lead paragraph, then 3–5 parallel items each with a heading + body**. The deck has two distinct renderings for this shape; pick by the per-item body length, not by author preference.

| Per-item body length | Layout | Why |
|---|---|---|
| ≤ ~80 chars (1–2 short sentences, parallel concept summaries) | **§7.4 card-row** (horizontal) | Visual parallelism reads at a glance; equal-width cards make the items feel like siblings. |
| > ~80 chars (2–4 sentences each, prose explanations) | **§7.5 icon-bullet list** (vertical) | Each item gets real horizontal room for prose; the stack scans top-to-bottom like a reading order. |

The shape signal in Markdown is the same for both — a lead paragraph followed by 3–5 H4 / bolded-label items, or 3–5 `- **Label** body…` bullets. The renderer counts per-item body chars (post-Markdown-stripping) and picks. When item lengths are mixed (one short, two long), pick by the **longest** item — the row layout would underuse cards for the long item, the list layout handles both gracefully. Never split a single lead+N group across both layouts.

### 7.4 Card-row (lead + 3–5 short cards) — horizontal

Section pill + title + lead paragraph (full width) + a row of N equal-width cards (N ∈ {3, 4, 5}) + optional source/citation line at the bottom. Each card carries an **icon chip** (filled `#DA1B2E` circle with the catalog line-art glyph in `#FFFFFF` — see §17.2 *chip variant*) above a short heading and a 1–2-sentence body. Used for parallel concept summaries: "three innovations of StyleGAN", "four pillars of X", "five steps".

| Element | Spec (approximate — tighten against the base-template reference slide when emitted) |
|---|---|
| Section pill | §6 geometry, unchanged |
| Title | §3.3 adaptive sizing; same anchor as other content slides (~`(0.54, 0.85)`) |
| Lead paragraph | full content width, anchor ~`(0.54, 2.05)`, ext ~`(8.91, 0.85)`, `sz="1200"` (12pt) Roboto, `#3B3535`, body insets `0` |
| Card row baseline | y ≈ 3.20 in; gutter between cards ≈ 0.22 in; row height ≈ 1.85 in |
| Per-card width | `(8.91 − (N−1) × 0.22) / N` — at N=3: ~2.82 in; N=4: ~2.06 in; N=5: ~1.60 in |
| Card outer | `roundRect`, fill `#F2EEEE`, no stroke, corner radius 5760 EMU |
| Icon chip | `ellipse` (perfect circle), fill `#DA1B2E`, no stroke, diameter ~0.42 in, anchored ~`(card_x + 0.20, 3.40)`. The line-art glyph (from §17.1) is overlaid on the chip in `#FFFFFF` stroke at ~70% of the chip's diameter. **This is the only place the chip variant is permitted — see §17.2.** Each card's glyph is **picked per §17.5 from the heading/body of *that card*** — never reuse the same glyph across cards in the same row, never default to a single house glyph for the whole layout. Three cards = three different §17.1 entries chosen to match each card's concept. The base-template slide 14 ships a hollow-ellipse stand-in inside the chip purely as a structural marker for the slot; the real render swaps it for the content-matched §17.1 glyph. |
| Card heading | anchor ~`(card_x + 0.20, 3.95)`, `sz="1350"` (13.5pt) Roboto Mono Medium, `#1F1E1E`, single line preferred |
| Card body | anchor ~`(card_x + 0.20, 4.30)`, width = card_width − 0.40, `sz="1100"` (11pt) Roboto, `#3B3535`, 2–3 lines max |
| Source line (optional) | anchor `(0.54, 5.30)`, ext `(8.91, 0.20)`, `sz="900"` (9pt) Roboto Italic, `#6A737D`. Emit when the slide cites a single source; omit when content is synthesized across the corpus. Format: `Fuente: <source title>` (localize "Fuente:" per `Presentation language`; English: `Source:`). |

**Capacity:** N=3 is the visual sweet spot; N=4 still reads cleanly; N=5 is the floor — at N=5 the per-card width drops to 1.60 in and bodies must be ≤ 60 chars (~1 short sentence). If 5 cards don't comfortably fit short bodies, fall back to §7.5 icon-bullet list instead of shrinking the body font.

### 7.5 Icon-bullet list (lead + 3–5 prose items) — vertical

Section pill + title + lead paragraph (full width) + a vertical stack of N rows (N ∈ {3, 4, 5}), each with a line-art icon at the left and a heading + multi-sentence body to the right. Used for prose explanations: "three strengths of GANs", "four limitations of X", "five reasons Y matters".

| Element | Spec (approximate — tighten against the base-template reference slide when emitted) |
|---|---|
| Section pill | §6 geometry, unchanged |
| Title | §3.3 adaptive sizing; may wrap to 2 lines (the lead paragraph + row stack accommodate a taller title than §7.4) |
| Lead paragraph | full content width, anchor ~`(0.54, 2.05)`, ext ~`(8.91, 0.90)`, `sz="1200"` (12pt) Roboto, `#3B3535` — inline bold (`**…**`) preserved with `b="1"` |
| Row stack baseline | y ≈ 3.10 in; vertical stride per row = `(slide_h − 3.10 − 0.30 bottom margin) / N` (at N=3 → ~0.74 in; N=4 → ~0.56 in; N=5 → ~0.44 in) |
| Per-row icon | anchor `(0.54, row_y + 0.04)`, ext `(0.42, 0.42)`, line-art `#DA1B2E` per §17.2 (**no chip background** — §17.2 default treatment). Each row's icon is **picked per §17.5 from the heading/body of *that row*** — never reuse the same icon across rows in the same stack. Three rows = three different §17.1 entries chosen to match each row's concept. The base-template slide 15 ships a hollow-ellipse stand-in purely as a structural marker; the real render swaps it for a content-matched `<p:pic>` of the chosen §17.1 icon per §17.4. |
| Per-row heading | anchor `(1.16, row_y + 0.05)`, ext `(7.75, 0.30)`, `sz="1350"` (13.5pt) Roboto Mono Medium, `#1F1E1E`, single line |
| Per-row body | anchor `(1.16, row_y + 0.40)`, ext `(7.75, stride − 0.45)`, `sz="1100"` (11pt) Roboto, `#3B3535`, 2–3 sentences. Inline bold preserved. |
| Source line (optional) | same as §7.4 |

**Capacity:** N=3 with 3-sentence bodies fits comfortably. N=4 with 2-sentence bodies is the upper bound; N=5 only with 1–2-sentence bodies. Beyond that the slide is overstuffed — split into two slides rather than shrink body font below 11pt.

**Lead paragraph carries no icon slot.** The §7.5 layout reserves icons for per-row slots only. When the source markdown places an emoji in the lead paragraph (e.g. `🤔 The question we're answering is…`), drop the emoji from the lead and emit the lead as plain prose — do **not** try to promote the lead-paragraph emoji to a fourth icon. The §17.7 *Strip is not swap* rule flags this as `[late-catch]` (the source put an emoji where the layout has no slot) so the editor knows to clean up the source for next time, but the render itself proceeds with the emoji dropped from the lead.

### 7.6 Labeled enumerations render as cards, never as paragraph leads

When a slide body contains a named sequence — `Paso 1` / `Paso 2` / `Paso 3`, `Step 1` / `Step 2`, `Etapa A` / `Etapa B`, `Phase 1` / `Phase 2`, `Case A` / `Case B`, `Fase I` / `Fase II`, and equivalents in any presentation language — **each named unit is a structural element**: a §7.1 numbered card (when the label carries an integer), a §7.2 plain card heading, or a `sz="1350"` Roboto Mono Medium subheading on its own line. The label **must not** render as an inline paragraph prefix (e.g. `**Paso 1.** Lorem ipsum…` followed by an indented sub-bullet list), because the resulting layout reads as a single flat paragraph block — the named hierarchy collapses visually and the reader cannot scan the steps. The numeric or ordinal portion of the label becomes the card's number / heading; the descriptive portion becomes the card body. Integer-labeled sequences map cleanly to §7.1; non-numeric labels (`Case A`, `Phase X`) use §7.2 with the label as `Card heading`. Cross-reference: §15 layout-selection table — any H2 whose body matches the labeled-enumeration shape selects **card-grid** or **content+cards+image**, never **content-text**.

---

## 8. Callout patterns — two variants

The deck uses two distinct callout styles for two distinct semantic roles. Pick the variant by intent — they are not interchangeable.

### 8.1 Pink callout (`#F7BBC1`) — analogy / tip / warning

For lateral, evocative content: an analogy, a tip, a warning, a mnemonic. The pink reads as "soft attention" and pairs with iconography like 💡, ⚠, 📚.

| Element | Spec |
|---|---|
| Outer | `roundRect`, fill `#F7BBC1` (peach-pink), corner radius ~5760 EMU |
| Inner (optional) | Nested `roundRect`, fill `#F2F2F2`, ~0.1 in inset — used when the callout contains code |
| Marker icon | A small `<p:pic>` image at the left of the body (~0.19 × 0.16 in), positioned ~0.17 in inside the outer's left edge. Use the branded icon library (§17) — `lightbulb` for analogy, `warning` for caution, `book` for reference, etc. |
| Body text | `rect` overlay, body insets `0`, fill `#000000`, `sz="1100" – "1150"` (11 – 11.5pt), Roboto |

Two examples:
- **Slide 3, full-width analogy:** outer at `(0.54, 4.18)` × `(8.91, 0.88)`; icon at `(0.71, 4.41)`; text at `(1.08, 4.36)` × `(8.21, 0.49)`.
- **Slide 7, half-width callout:** outer at `(0.54, 3.05)` × `(4.27, 0.80)`; icon at `(0.70, 3.27)`; text at `(1.05, 3.21)` × `(3.61, 0.45)`.

### 8.2 Blue insight callout (`#B8E6F5`-ish) — "what this enables" / key takeaway

For a load-bearing claim about what becomes possible, a quantified result, or the key takeaway of a section. The cool blue reads as "factual / important / proven" — distinct from the warm pink which reads as "lateral / evocative".

| Element | Spec |
|---|---|
| Outer | `roundRect`, fill `#B8E6F5` (light cyan), corner radius ~5760 EMU |
| Marker icon | A small `(i)` `info` icon (§17 library — `icon-info.svg`) in `#DA1B2E` at the left of the body, ~0.20 × 0.20 in |
| Body text | `rect` overlay, body insets `0`, fill `#1F1E1E`, `sz="1100" – "1300"` (11 – 13pt), Roboto. Bold lead-in (e.g. **"Lo que la IA Generativa hace posible:"**) followed by the explanatory body. Quantified figures (Dice scores, dollar amounts, percentages) get inlined in `#DA1B2E` bold — they're the "punch" of the statement. |
| Typical placement | Below the main content as the closing claim — visually heaviest element on the slide |
| Width | Full content-area width (~9 in) |

**When to use which:**

| Intent | Variant | Marker icon |
|---|---|---|
| "Like a recipe for a chef…" (analogy) | Pink (§8.1) | `lightbulb` |
| "Be careful: model can hallucinate" (warning) | Pink (§8.1) | `warning` |
| "Cachear prompts repetidos reduce costes" (tip) | Pink (§8.1) | `lightbulb` |
| "U-Net trained on combined real+synthetic achieved Dice 0.9524 vs 0.9459 (real-only)" (proven result) | Blue (§8.2) | `info` |
| "Generative AI enables synthetic data, modality translation, anonymization with clinical realism" (capability statement) | Blue (§8.2) | `info` |
| "Section 4 covers Chain of Thought, Self-Consistency, and Extended Thinking" (forward reference) | Blue (§8.2) | `info` |

The pink callout is **conversational**; the blue callout is **declarative**. Choose accordingly.

### 8.3 Callout line-count estimate — load-bearing for body fit

Renderers must reserve vertical space for the callout **before** placing the preceding body content, not after — otherwise the callout's height is computed against a body region that has already consumed the slot, and the callout's bottom edge slides past the slide's `effective_bottom`. When that happens, the renderer either clips the callout or — worse — silently drops the trailing block from emission. Typical trigger: a slide whose primary body is a table or dense paragraph; the table sizes as if the trailing callout weren't there, and the callout falls off.

Estimate callout line count by character count at the callout's render width:

```
callout_lines = max(1, ceil(text_len / chars_per_line))
chars_per_line ≈ 110     # 11pt Roboto at BODY_W − 0.7 in (icon column + insets)
callout_height = callout_lines × line_h_11pt + 2 × callout_v_padding
                 line_h_11pt ≈ 0.20 in
                 callout_v_padding ≈ 0.08 in
```

Reserve `callout_height` at the bottom of the body region first; lay out the preceding blocks against `effective_bottom = slide_bottom − callout_height − callout_top_margin`. This is the inverse of the naive "lay out top-to-bottom, callout last" pattern that ships the drop. For 12pt callouts use `chars_per_line ≈ 100`; for 11.5pt use `≈ 105`. Long callouts (≥3 estimated lines) are a content-authoring signal — surface as `[over-budget]` and flag for re-authoring before render, do not silently shrink-fit.

---

## 9. Code-block pattern (the dominant slide type — 17 of 53)

| Element | Spec |
|---|---|
| Background surface | `roundRect`, fill `#F2F2F2`, corner radius ~5760 EMU |
| Optional accent border | A `roundRect` `#F7BBC1` 1–2 px larger as outer frame (used to mark "before/after" pairs) |
| Font | **Consolas** (not Roboto Mono), `sz="650" – "1000"` (6.5 – 10pt), default ink `#000000` |
| Body insets | `0` on all four sides (text is positioned via the parent rect, not via the txBody padding) |
| Syntax highlighting | keyword `#D73A49`, string/identifier `#005CC5`, comment `#6A737D` (GitHub-light theme) |
| Layout | Code surface typically occupies the right ~45% of the slide; left ~45% is a `card` or `text` column explaining the code |

Code uses **Consolas**, not Roboto Mono. Roboto Mono Medium is reserved for titles, labels, and card headings.

---

## 10. Bullets

Bullets are **rare** — only 40 bullet-character runs across all 53 slides. The deck strongly prefers **cards over bullet lists** for grouped content. Most list-shaped content (e.g. slide 22's six techniques) is rendered as a 2×3 grid of titled paragraphs without bullets.

When bullets appear (slides 19, 20, 26, 29, 32, 34, 49), they stay shallow — single level, no nesting observed.

**Bullet glyph — render via paragraph-property markup, never as a literal Unicode character.** Bullets are emitted as the OOXML paragraph property `<a:buChar char="•"/>` (or equivalent `<a:buAutoNum>` for numbered lists) inside the paragraph's `<a:pPr>`, so PowerPoint draws the bullet glyph automatically per the paragraph's bullet style. **Never** start a text run with a literal `• ` character — that path looks correct in isolation but produces a deck-wide inconsistency: paragraphs styled via `<a:buChar>` render the bullet at the paragraph indent with the bullet color taking the run's color; paragraphs whose text run begins with `• ` render the dot at the run's exact baseline x-position, with the dot's color tied to whatever character font is active. The two land at different x offsets, often with different glyph metrics, and adjacent slides emit visibly different bullet shapes. The contract is uniform per-deck: pick one renderer path (`<a:buChar>` is the OOXML-native choice) and use it for **every** bullet paragraph in the deck — the renderer's bullet path must not have a `style="dot" | "char"` parameter that different code paths can set differently.

---

## 11. Tables

**The template contains ZERO `<a:tbl>` elements.** `ppt/tableStyles.xml` is empty (just `<a:tblStyleLst def="…"/>`).

When the Markdown source contains a pipe-table, the renderer must **convert it to a card grid**, not emit a native PPTX table. Two acceptable strategies:

| Markdown shape | Render as |
|---|---|
| ≤3 columns, ≤6 rows, where col 1 is a label and col 2 is a value | A vertical stack of left-strip cards (§7.1), with col 1 → card heading, col 2 → card body |
| 2×N or 3×N comparison grid (e.g. "Pros vs Cons", "Approach A vs Approach B") | A horizontal flex of plain title-only cards (§7.2), one column per table column header, rows aligned by row index |
| ≥4 columns | Split into multiple slides or rotate to a 1-column form — the template does not support wide tables |

The visual cue "this is tabular data" is carried by **alignment and identical card sizes**, not by gridlines. There are no borders, no header banding, no zebra striping.

If a future deck genuinely needs a table, introduce it as a new shape pattern — but document the recipe here first.

---

## 12. Image conventions

- 240 image assets total: **147 PNG** + **93 SVG**.
- Naming: `image-<slide>-<n>.{png,svg}` — one-to-one mapped to the slide they appear on.
- **Most icons ship as PNG + SVG pairs** (PNG is the rasterized fallback). When generating, prefer SVG; emit PNG alongside as a Marp-compatibility fallback.
- **No image is used full-bleed** (zero slides with an image ≥ 90% canvas). All images are inset, sized to a content column, and aligned to adjacent text.
- Image counts per slide: most 1–4; max 11 (slide 44).
- No captions exist as separate text — image meaning is carried by the adjacent title or card.
- The cover logo (`image-1-1.png`, 616×510 px) is the only **branded** image and is preserved verbatim across decks unless the presenter explicitly swaps institutions.
- **Aspect ratio is fixed at the source and must not be changed.** When sizing an image into a slot, scale **uniformly** — the rendered `cx:cy` ratio of every `<p:pic>` must equal the source asset's intrinsic `width:height`. Stretching, squishing, anamorphic crops, or "fit to box" non-uniform scaling are forbidden; they distort diagrams, logos, and rasterized SVGs. If a slot's box doesn't match the image's aspect, leave the unfilled gap (whitespace) rather than distort. The cover logo's `noChangeAspect="1"` flag (§4.2 shape #4) makes this explicit in XML; **every other `<p:pic>` should carry the same flag** so downstream editors can't accidentally re-fit the image. The SVG `<a:stretch><a:fillRect/></a:stretch>` pattern in §17.4 is uniform scaling — never use `<a:srcRect>` cropping or `<a:stretch>` with non-zero `fillRect` insets to "stretch to fit".

  **Enforcement (three layers, defense in depth):**
  1. **Upstream — SVG generation.** Every SVG produced by [`ascii-to-svg`](../.claude/skills/ascii-to-svg/SKILL.md) declares a `viewBox` whose `W:H` matches the diagram's true visual aspect, with no conflicting `width`/`height` attrs and no `preserveAspectRatio="none"`. See that skill's step 5 *Aspect-ratio contract* for the rule. A wrong viewBox at this stage poisons every downstream check.
  2. **Baseline — base template.** [`config/base-template.pptx`](base-template.pptx) is shipped pre-audited: every `<p:pic>` in cover + agenda + every retained layout slide already passes the aspect audit at 1% tolerance and carries `noChangeAspect="1"`. A working copy of the base template is compliant by construction.
  3. **Downstream — post-render audit.** After the native renderer emits `final.pptx`, the [`md-to-pptx`](../.claude/skills/md-to-pptx/SKILL.md) skill runs [`audit_aspect_ratios.py`](../.claude/skills/md-to-pptx/audit_aspect_ratios.py) (Process step 6, progress stage 5) which walks every `<p:pic>`, resolves its source asset, and **fails the render on any mismatch ≥ 1%**. Repair = shrink the larger placement dimension to match the source ratio per the rule above. Never resolve by widening the tolerance, never by emitting `<a:srcRect>` / non-zero `<a:stretch fillRect>` insets.

---

## 13. Layout taxonomy (53 slides)

| Type | Count | Slide # | Recipe |
|---|---|---|---|
| **cover** | 1 | 1 | §4 |
| **agenda / section divider** | 7 | 2, 12, 17, 21, 40, 45, 52 | §5 — all 7 instances identical except active dot |
| **content + cards + image** | 4 | 7, 47, 48, 51 | Title + section pill + 2–4 cards (mix of §7.1 and §7.2) + one supporting image |
| **content + image** | 7 | 6, 8, 9, 18, 23, 29, 39 | Title + section pill + 1–3 inline images aligned to text columns |
| **content-text** | 1 | 5 | Pure text, no images — rare |
| **card-grid** | 1 | 25 | 2×N or 3×N grid of plain cards (§7.2), no images |
| **code-example** | 17 | 11, 13–16, 19, 20, 22, 24, 26–28, 30, 32, 41–43 | §9 — code block + explanation column |
| **image-grid** | 14 | 3, 4, 10, 31, 33–38, 44, 46, 49, 50 | 3+ images arranged in row or grid; each typically a PNG+SVG pair |
| **closing-cta** | 1 | 53 | Title + 4-card grid of next-step resources |

### 13.1 Layout files — Marp-style, one per slide

The .pptx contains **55 `slideLayout*.xml` files** (54 in use + 1 `DEFAULT`) named `Slide 1 master` … `Slide N master` — i.e. **one bespoke layout per slide**. Layouts are *not* reusable templates with placeholders; they are slide-specific carriers. Downstream `md-to-pptx` should **generate shape geometry directly** rather than expect named placeholders.

---

## 14. Slide-by-slide inventory

`txt` = text-run count; `pic` = total `<p:pic>` count (PNG + SVG combined).

| # | Type | Pics | Txt | H2 title |
|---|---|---|---|---|
| 1 | cover | 1 | 4 | Inteligencia Artificial Generativa Aplicada en Biomedicina |
| 2 | agenda/divider (active: 1) | 0 | 22 | Agenda |
| 3 | image-grid | 4 | 11 | ¿Qué es un Prompt? |
| 4 | image-grid | 4 | 18 | ¿Qué es lo que se guarda en un prompt? |
| 5 | content-text | 0 | 18 | Ventana de Contexto |
| 6 | content+image | 1 | 13 | ¿Cuánto es 1 millón de tokens? |
| 7 | content+cards+image | 1 | 18 | Economía de Tokens |
| 8 | content+image | 3 | 8 | Limitaciones de los Foundational Models |
| 9 | content+image | 3 | 19 | Alucinaciones: En Profundidad |
| 10 | image-grid | 6 | 22 | Mitigación de Alucinaciones |
| 11 | code-example | 3 | 23 | Modelo Mental: Motores de Completado |
| 12 | agenda/divider (active: 2) | 0 | 22 | Agenda |
| 13 | code-example | 1 | 46 | Los 6 Componentes de un Prompt |
| 14 | code-example | 2 | 27 | Salidas Estructuradas: JSON Schema |
| 15 | code-example | 2 | 36 | XML Tags: Estructura Semántica |
| 16 | code-example | 4 | 13 | Optimización por Modelo |
| 17 | agenda/divider (active: 3) | 0 | 22 | Agenda |
| 18 | content+image | 3 | 9 | In-Context Learning (ICL) |
| 19 | code-example | 1 | 25 | Few-Shot Learning |
| 20 | code-example | 1 | 23 | Many-Shot Learning |
| 21 | agenda/divider (active: 4) | 0 | 22 | Agenda |
| 22 | code-example | 5 | 14 | Técnicas Avanzadas de Prompting: Resumen |
| 23 | content+image | 3 | 17 | Chain of Thought (CoT) |
| 24 | code-example | 1 | 17 | CoT en Acción: Ejemplo |
| 25 | card-grid | 0 | 17 | Self-Consistency: Votación por Mayoría |
| 26 | code-example | 1 | 25 | Self-Consistency: Ejemplo |
| 27 | code-example | 3 | 13 | Extended Thinking (Anthropic) |
| 28 | code-example | 5 | 23 | Extended Thinking: Ejemplo |
| 29 | content+image | 2 | 19 | Tree of Thought (ToT) |
| 30 | code-example | 4 | 24 | Tree of Thought (ToT): Ejemplo |
| 31 | image-grid | 6 | 27 | Prompt Chaining |
| 32 | code-example | 1 | 27 | Prompt Chaining: Ejemplo |
| 33 | image-grid | 10 | 24 | Técnicas Avanzadas: Pros y Contras |
| 34 | image-grid | 4 | 14 | ¿Por qué funcionan estas técnicas? |
| 35 | image-grid | 7 | 19 | ¿Por qué tardan más en responder? |
| 36 | image-grid | 8 | 19 | El Problema: Prompts sin Verificación |
| 37 | image-grid | 5 | 29 | DSPy: Optimización Automática de Prompts |
| 38 | image-grid | 4 | 19 | Versionado de Prompts |
| 39 | content+image | 1 | 27 | Datos y Testing Sistemático |
| 40 | agenda/divider (active: 5) | 0 | 22 | Agenda |
| 41 | code-example | 1 | 50 | El Paisaje de Modelos |
| 42 | code-example | 8 | 28 | Prompt Caching: Reducción de Costos 50-90% |
| 43 | code-example | 2 | 36 | Prompt Caching: Ejemplo de Implementación |
| 44 | image-grid | 11 | 43 | Model Cascading: Modelos Baratos Primero |
| 45 | agenda/divider (active: 6) | 0 | 22 | Agenda |
| 46 | image-grid | 4 | 20 | Prompting y Medicina |
| 47 | content+cards+image | 1 | 40 | Recorrido del Paciente |
| 48 | content+cards+image | 1 | 44 | Research Biomédica |
| 49 | image-grid | 4 | 27 | Casos de Éxito: Donde se Aplican Hoy |
| 50 | image-grid | 4 | 23 | Oportunidades vs. Riesgos |
| 51 | content+cards+image | 1 | 33 | Mitigaciones Clave y Para Pensar |
| 52 | agenda/divider (active: 7) | 0 | 22 | Agenda |
| 53 | closing-cta | 0 | 19 | ¡A Practicar! |

---

## 15. Generator emit-rules (for `md-to-pptx` and equivalents)

**Meta-rule — the renderer applies the layout the spec selects, not the layout that ships without violations.** Every layout rule in §6–§17 pairs an anti-pattern (what must not appear) with a positive obligation (what must appear in its place). Satisfying the anti-pattern by *deletion* — stripping an emoji, dropping a label, picking a plainer layout — is a render failure when the positive obligation calls for *substitution* or for a richer layout. A §19.6-clean deck that bypassed §15.5's discriminator or §17.7's substitution table is still a render failure; §19.6 is necessary but not sufficient. The pre-emit audit in §15.6 enforces the positive obligation per slide; the post-emit audit in §19.5 verifies it landed.

When rendering `final.md` to `.pptx`, follow these rules in order:

1. **Slide 1 = Cover.** No matter what the Markdown contains for slide 1, emit the §4 recipe. Pull text from frontmatter (`presentation`, `subtitle`, `presenter`, `date`, `Presentation language`). Preserve `ppt/media/image-1-1.png` verbatim. Do **not** apply the section pill (§6).
2. **Slide 2 = Agenda with active item 1.** Emit the §5 recipe. Pull the N item titles from the N H1s in `final.md` (N = section count, not fixed); pull subtitles from per-section `Subtitle:` fields. Clone or delete placeholder rows in `base-template.pptx` to match N. Surface a warning to the presenter when N > 8 (tight) or N > 10 (out of room — see §5.3 capacity).
3. **Section dividers.** Before every new section k (k ∈ {2..N}), re-emit the §5 agenda with active item set to k. Place each divider immediately before its section's first content slide — there are no absolute slide-number positions to honor.
4. **Every content slide carries a §6 section pill** at top-left, with text = the active section's H1 verbatim, uppercased.
5. **Layout selection per content slide** — pick from §13 based on Markdown signal:

   The **Markdown signal** column is mechanical (regex-shaped); the **Content-intent fit** column is the discriminator for an LLM choosing a layout when two signals could plausibly match — read it before defaulting to the first row that fits.

   | Markdown signal in the H2-led slide | Layout type (§13) | Content-intent fit (when this layout is right; when it is not) |
   |---|---|---|
   | First slide of deck, no H2, frontmatter present | **cover** (§4) | Not a content choice — first slide is always cover regardless of Markdown. |
   | H1-only slide (numbered section header) | **agenda/divider** (§5) — render full 7-item agenda with matching number active | Not a content choice — section transitions always emit an agenda re-emit with the active dot incremented. |
   | H2 + 1–3 `![]()` images interleaved with paragraphs | **content+image** | **Use when:** one main claim is supported by 1–3 illustrative images (a hero diagram + 1–2 close-ups; a worked example with its result; a concept + its real-world instance). The slide is *about* the prose; the images are evidence. **NOT for:** parallel concepts of equal weight (→ §7.4 card-row or §7.5 list); a visual catalog where variety is the point (→ image-grid); a single full-bleed hero (template never goes full-bleed per §12). |
   | H2 + ≥4 `![]()` images | **image-grid** | **Use when:** the *visual variety itself* is the message — model output samples, phenotype spreads, before/after pairs across N cases, a portfolio. The reader scans the grid as one composite. **NOT for:** a list of items that each happen to have an icon (→ §7.5 icon-bullet list, which keeps text dominant); one main idea with supporting illustrations (→ content+image, where the prose leads). |
   | H2 + fenced ``` ``` code block as primary content | **code-example** (§9) | **Use when:** the audience must read code line-by-line — a worked snippet, an API call shape, a config example, a before/after diff. Pairs the code surface (right) with a 2–3-sentence explanation column (left). **NOT for:** code as a cited artifact you don't expect the audience to read (drop into speaker notes or screenshot it as an image); pseudocode for an algorithm whose structure matters more than its syntax (→ §7.5 with the steps as items, or a diagram). |
   | H2 + sequence of `### Subhead` + paragraph repeats (4+ groups) | **card-grid** (no image) or **content+cards+image** (image present) | **Use when:** 4 or more named, structurally-parallel concepts each fit in a short heading + 1–2-line body — a catalog of techniques, a feature comparison, a 2×N or 3×N matrix. The grid reads as a navigable index. **NOT for:** 3 items (→ §7.4 card-row, the row layout reads more cleanly at low N); items with multi-sentence prose bodies (→ §7.5 icon-bullet list); label/value pairs that read like a small table (→ card-grid via §11, which uses a tighter visual). |
   | H2 + lead paragraph + 3–5 `- **Label** body…` bullets (or 3–5 `- <emoji> **Label:** body…` or `#### Label` + paragraph groups) | **§7.4 card-row** when every per-item body ≤ ~80 chars; **§7.5 icon-bullet list** otherwise — **NEVER §10 plain bullets** | **§7.4 card-row use when:** 3–5 symmetric, equal-weight, parallel concept *summaries* — "three innovations of StyleGAN", "four pillars of X", "five steps". Each item headline-able in ≤ ~80 chars; the audience reads horizontally and sees the parallelism. **§7.5 icon-bullet list use when:** 3–5 parallel items each needing 2–3 sentences of prose — "three strengths of GANs", "four limitations of X", "five reasons Y matters". The audience reads top-to-bottom; each item gets real horizontal room. **Decision rule:** measure post-Markdown chars per item body, pick by the *longest* item, never split a group across both. See §7.3. **Common renderer mistake:** falling through to §10 plain bullets when the emoji-bullet-with-bold-label pattern is detected. The lead + 3-5 *labeled* bullets shape is **never** a §10 bullet list — even when bodies are short (→ §7.4) or long (→ §7.5), the *labeled* structure makes it a card/row layout. §10 is for plain unlabeled bullets only (rare; e.g. a 3-item caveat list under a content+image slide). **NOT for:** label/value pairs (→ §11 card-grid); enumerations with > 5 items (split into two slides); a single concept with sub-points (→ content+image or content-text). |
   | H2 + pipe-table | **card-grid** via §11 conversion | **Use when:** the content is structurally label/value pairs — model specs, parameter comparisons, "before vs after" rows, dosage tables. The template never emits native `<a:tbl>`; pipe-tables convert to a card-per-row visual. **NOT for:** 3–5 parallel concepts where the "table" is just a layout convenience (→ §7.4 or §7.5, more visually appropriate); narrative rows that read as prose (→ content-text or split into multiple slides). |
   | Final slide with H2 + list of links | **closing-cta** | **Use when:** the talk's last slide — a call to action, a "where to next" list, contact + repo links, references the audience will photograph. **NOT for:** any non-terminal slide; an inline references section (those belong in speaker notes or an appendix slide, not in a CTA layout). |
   | H2 + paragraphs only, no images, no code | **content-text** | **Last-resort use when:** a slide genuinely carries only prose — a definition, a quote, an opening framing. Template avoids this; appears 1× in 53 source slides. **NOT for:** anything that could be restructured — most "wall of paragraphs" slides are draft defects where parallel structure (→ §7.4 / §7.5) or a diagram (→ content+image) would serve better. Flag in review as a candidate to restructure before accepting. |
   | H2 + single-bullet `- <emoji> **<bold lead>** …` (one item, emoji-prefixed, bold lead-in) | **callout** (§8) — pink (§8.1) for analogy/tip/warning, blue (§8.2) for declarative claim/key takeaway | **Use when:** a slide's content includes a single emphasized claim or aside that markdown-authored as a one-item bullet with emoji + bold lead. The shape is **not a bullet list** — a 1-bullet "list" never reads as enumeration; it reads as emphasis. Promote to the §8 callout layout, picking pink vs. blue per the §8 decision table by the bullet's intent (`🎯`, `💡`, `📚`, `⚠` → pink; `📊`, `ℹ️`, declarative claim → blue). Per [`audit_block_coverage.py`](../.claude/skills/md-to-pptx/audit_block_coverage.py), the renderer is audited for this — emitting the bullet as a plain `<a:buChar>` paragraph instead of a callout shape registers as a `[block-drop]` because the audit looks for the matching `#F7BBC1`/`#B8E6F5` roundRect. **NOT for:** multi-bullet emoji-prefixed lists (those are §10 bullet lists with the emoji-to-icon swap per §17.7); inline bold within a paragraph (not a callout signal — just emphasis). |

6. **Title sizing per content slide.** Apply §3.3 — pick the largest size from the discrete ladder `[17, 18, 19, 20, 21, 22.5, 24, 26, 28, 30, 31]` pt that fits the title on one line.
7. **All `roundRect` shapes use 5760 EMU corner radius** (§2.3). Encode the per-shape `adj` accordingly.
8. **Background.** Pure white `#FFFFFF` `<p:bg>` solid fill on every layout (§1). No overlays, no tints.
9. **Fonts are always set at run level.** Never inherit from theme. Roboto Mono Medium for titles/labels/headings; Roboto for body; Consolas for code. No fallbacks.
10. **Emit speaker notes verbatim into the notes pane.** Every `### Notes` block in `final.md` becomes the notes content of the corresponding slide — no truncation, no dropping. The pane is load-bearing per §1 and [`principles.md`](principles.md) → *Content* → *Speaker notes are the talk*; do not treat it as decorative.
11. **The renderer never fixes content defects.** If the post-render visual review surfaces a slide whose title overflows because the title is too long, whose body crowds because it carries two ideas, whose section pill is missing because the H1 has no number, or whose notes pane is empty — those are **Step-4 / Step-5 / Step-6 authoring defects** surfacing late. The renderer's job is to apply the spec faithfully, not to shrink-fit a 60-character title into the H2 ladder's 17pt floor, drop a card to fit a budget, or invent a section pill text. When a content defect is detected at render time, stop the iteration budget, surface to the presenter with the exact rule violated (e.g. "Slide 14 H2 = 62 chars, exceeds the 40-char budget in `principles.md` → *Title-length budget*"), and offer either: (a) accept the defect for this ship and log to `feedback-backlog.md` with the `late-catch` tag, or (b) re-open the authoring stage that owns the defect. **Never silently compensate.** Renderer compensation is what causes the next Talk to re-introduce the same defect — the authoring stage never learned.

### 15.6 Pre-emit decision audit

Before emitting any content slide, the renderer must walk this audit in order. Each step is **fail-loud**: a missing input or unresolved decision is surfaced to the presenter per §15.6.4, never silently absorbed. The audit is the operational expression of the §15 meta-rule above — it forces the renderer to *show its work* on layout selection, emoji handling, and bullet emission rather than landing whichever rendering happens not to violate §19.6.

#### 15.6.1 Layout selection — the discriminator, not the first match

The §15.5 emit-rules table is a **decision tree**, not a "first match wins" lookup. Two markdown signals can be surface-compatible (e.g. "H2 + paragraph + bullets" matches §10 plain bullets, §7.4 card-row, and §7.5 icon-bullet list simultaneously). The **Content-intent fit** column is the discriminator. The renderer must:

1. Collect *every* surface signal in the slide's markdown body (`![]` count, fenced code presence, pipe-table presence, `- ` bullet count, `- **Label**` bullet count, `### Subhead` group count, per-item body length, presence of emoji prefixes on bullets).
2. Enumerate every §15.5 row whose Markdown-signal column matches.
3. Apply the **Content-intent fit** discriminator to pick exactly one. The discriminator is mechanical when the spec gives a threshold (e.g. §7.4-vs-§7.5: "pick by the longest item body, > 80 chars → §7.5"); when ambiguous, surface to the presenter per §15.6.4.
4. **Never default to the plainer layout** (§10 plain bullets, §11 raw table, content-text) when a richer one matches. The plainer layouts exist as *last-resort* fallbacks, explicitly flagged "rare" / "last-resort" in their own sections. Picking them is a positive choice that must be justified by the discriminator's output, not a fallback the renderer takes when uncertain.

**Symptoms of a §15.6.1 violation in the rendered deck:**

- A slide whose source has 3+ `- **Label**: body` bullets (longest body > 80 chars) renders as §10 plain bullets — no per-row heading typography, no per-row icon.
- A slide whose source has ≥4 `![]` images renders as content+image (1–3 image positions) — the image-grid signal was missed.
- A slide whose source has a fenced code block renders as content-text — code-example was skipped.
- A slide whose source has `### Subhead` groups of 4+ renders as plain prose — card-grid / content+cards+image was skipped.

#### 15.6.2 Emoji handling — substitute, never strip

This sub-section is the operational form of §17.7. The audit obligation: for every emoji codepoint in the slide body, the renderer either emits a `<p:pic>` of the matching catalog icon **at a slot the chosen layout actually has**, or surfaces the case per §15.6.4. The substantive contract — codepoint detection ranges, the §17.7 swap table, the *Strip is not swap* anti-pattern, the *Lead paragraph carries no icon slot* edge case (§7.5) — lives in §17.7 and §7.5 and is not duplicated here. The audit's job is to **prove** the obligation was met per slide, not to restate it.

#### 15.6.3 Bullet emission — single canonical implementation

This sub-section is the operational form of §10's bullet-glyph contract. The audit obligation: the renderer's bullet path is centralized to one helper that emits the OOXML-native `<a:buChar>` paragraph property; no code path emits a literal `•` (U+2022) glyph as text; bullet shape and gutter offset are uniform across every slide in the deck. The substantive contract lives in §10 and is not duplicated here. The audit's job is to **prove** the bullet path is single-source per render, typically by walking every slide's `<a:p>` paragraphs and confirming each list item carries `<a:buChar>` rather than a leading `• ` in its `<a:t>`.

#### 15.6.4 Surfacing protocol — what to do when the audit can't resolve

When §15.6.1 produces an ambiguous layout selection (two §15.5 rows match and the discriminator is borderline), §15.6.2 hits an emoji outside the §17.7 table at a slot the chosen layout doesn't have, or §15.6.3 detects existing bullet-style drift in the renderer, the renderer **stops the iteration budget** (per the CLAUDE.md *Render cycle* 3-cycle cap) and surfaces a single structured prompt to the presenter:

```
[pptx pre-emit audit] Slide N — <H2 title>
  defect: <one of layout-ambiguous | emoji-unmapped | bullet-style-drift>
  evidence: <markdown signals collected from the slide body>
  proposed resolution: <the renderer's best guess>
  alternatives: <2-3 named alternatives the presenter can pick from>
  effect: <what changes downstream if the presenter accepts the default>
```

The presenter picks one. The renderer records the resolution in [`config/feedback-backlog.md`](feedback-backlog.md) with the tag `pre-emit-audit` so the next Talk in the fork can carry the rule forward via the Step-7 learnings promotion.

**Never silently compensate.** A renderer that absorbs an ambiguity by picking the plainer layout, dropping the emoji, or shrinking the font is exactly the renderer that ships the regression this audit exists to prevent.

### 15.7 Free-form design rubric (Option 2 FEEDBACK phase)

When the Talk's `style: free-form` and the CLAUDE.md *Render cycle* enters its FEEDBACK phase, the orchestrator walks **this** rubric on every slide PNG instead of the 12-practice strict rubric. Same per-defect line format (`slide N · practice K · <description> → <fix | defer because <reason> | surface to presenter>`), same minor-as-defer discipline, same 3-cycle cap.

Eight practices, plus precondition #0 (block-coverage, identical to strict practice #0 — every source block must appear as a shape on the rendered slide; the only Option-1 practice that survives because it catches structural drops in both modes).

| # | Practice | What to look for |
|---|---|---|
| 0 | **Block-coverage precondition** | Same as strict practice #0 — see [CLAUDE.md](../CLAUDE.md) Step 8. Enforced by [`audit_block_coverage.py`](../.claude/skills/md-to-pptx/audit_block_coverage.py) in the CONTROL phase before FEEDBACK runs. |
| 1 | **Composition rhythm** | Across the deck, layout variety reads as *paced*, not random and not monotonous. Three consecutive identical card grids bore. Eight consecutive radically-different layouts read as chaos. The rhythm is what carries the audience between ideas; check that consecutive slides feel like *steps in a sequence*, not *unrelated objects*. |
| 2 | **Focal hierarchy** | One element on each slide draws the eye first; supporting content recedes. The first element ≠ the most decorative; it should be the most *load-bearing* (the claim, the chart, the diagram). Ambiguity ("which thing am I supposed to look at?") is a fail; intentional rejection of a single focal point (e.g. a tiled gallery slide where variety *is* the message) is allowed but the critic must call it out as deliberate. |
| 3 | **Color use within palette** | Every color is in the §2 palette (enforced by [`audit_palette_fonts.py`](../.claude/skills/md-to-pptx/audit_palette_fonts.py) in CONTROL), AND the chosen color is emotionally apt to the slide's content. A `#DA1B2E` bright-red callout on a slide about a privacy breach reads wrong even though red is in-palette. Color is a semantic choice; in-palette is a floor, not a pass. |
| 4 | **Type intent** | Each typographic choice (size, weight, case, family) has a job. Sizes drawn from a clear scale (no 17.3pt body next to 17pt body across slides); ALL-CAPS reserved for labels/section names; bold reserved for emphasis within prose, not decoration; italics reserved for citations / titles of works / non-English terms. Decorative variation ("make this line bigger because it looks empty") is a fail. |
| 5 | **Image scale + placement** | Aspect ratio preserved (enforced by [`audit_aspect_ratios.py`](../.claude/skills/md-to-pptx/audit_aspect_ratios.py) in CONTROL). Hero images dominate; supporting images supplement. No load-bearing detail cropped to fit a slot. Image-text gutters consistent; images don't crash into adjacent text. Photographs and diagrams may coexist in free-form, but their treatment (size relative to slide, framing, padding) is internally consistent. |
| 6 | **Typography quality (micro)** | No widows (single word on the last line of a paragraph). No orphans (heading at the bottom of a column, body on the next). Numbers in a column use tabular figures (aligned decimals). Headings don't break awkwardly across the right-margin gutter. Em-dashes are em-dashes (`—`), not double-hyphens (`--`). These are the marks that distinguish a designed deck from a wireframed one. |
| 7 | **Density — slide breathes** | Generous safe margins; no wall of text; no claustrophobic packed grid. The audience should be able to absorb the slide's primary content in 3–5 seconds, then turn attention to the speaker. A slide that takes 30 seconds to *read* is the speaker's competitor, not their support. Density limits are softer than strict's "≤5–7 bullets" rule — the test is *can the eye land and rest within a beat*, not a bullet count. |
| 8 | **Coherence across slides** | Type sizes don't drift (what reads as "title" on slide 5 reads as "title" on slide 25); color palette use stays internally consistent (an accent that meant "warning" on slide 4 doesn't mean "highlight" on slide 12); image treatment stays internally consistent (if photographs are 4:3 inset with 0.3-in padding on slide 8, they are 4:3 inset with 0.3-in padding on slide 18). Free-form is not "different every slide"; it is "the right layout for each slide, with consistent treatment of recurring elements." |

**Plus the aesthetic note.** After walking practices 0–8, the critic adds a one-sentence free-form aesthetic note per slide naming whatever the eye catches that the rubric does not — same discipline as strict. The rubric is the floor; the aesthetic note is where the critic's judgment shows. `aesthetic: clean` is a valid note when nothing catches the eye.

**Critique discipline carries forward.** Same as strict: every flagged cell of the slide × practice matrix gets *fix in this iteration* / *defer because <reason>* / *surface to presenter*. Silent `[minor] → ignore` is the same prohibited pattern. Free-form does not lower the bar on per-defect resolution; if anything it raises it, because there is no spec-side recipe to fall back on.

---

## 16. Recipes summary

When you only need a one-line cheat-sheet:

| Concern | Answer |
|---|---|
| Background | Pure white `#FFFFFF` `<p:bg>` solid fill on every slide |
| Title font | Roboto Mono Medium, `#1F1E1E`, adaptive 17–31pt (40.5pt for cover) |
| Body font | Roboto, `#3B3535`, 10.5–12.5pt |
| Code font | Consolas, `#000000` with GitHub-light syntax colors |
| Section pill | `roundRect` `#F9D2D6` top-left, ALL CAPS Roboto Mono Medium `#3B3535` text overlay |
| Card (numbered) | `roundRect` `#FFFFFF` + `rect` `#F2EEEE` left strip + Roboto Mono Medium number + heading + Roboto body |
| Card (plain) | `roundRect` `#FFFFFF` + Roboto Mono Medium heading + Roboto body, 0.18 in inner padding |
| Callout | `roundRect` `#F7BBC1` + emoji image + Roboto `#000000` text |
| Code surface | `roundRect` `#F2F2F2` + Consolas + syntax-color spans |
| Agenda dot (active) | `roundRect` `#DA1B2E` + `#FFFFFF` "N" text + `#F33447` connector |
| Agenda dot (inactive) | `roundRect` `#F2EEEE` + `#3B3535` "N" text + `#D8D4D4` connector |
| Corner radius | Constant ~5760 EMU (4.6 pt) on every roundRect |
| Tables | None — convert pipe-tables to card grids |
| Cover logo | `image-1-1.png` at `(7183562, 3248546)` EMU, `(1469008, 1214065)` EMU size — preserved verbatim |

---

## 17. Icon library — branded line-art set

The deck uses a **single, consistent icon style**: clean line-art strokes in brand red `#DA1B2E` on transparent background. **No two icon styles in one deck.** No filled silhouettes, no two-tone illustrations, no system emojis (💡 📚 🏥 do not render reliably in LibreOffice and visually clash with the typographic restraint of the template).

The library ships with `base-template.pptx` as both SVG (`ppt/media/icon-<name>.svg`) and rasterized PNG previews. Visual reference: [`template-previews/icons/`](template-previews/icons/).

### 17.1 Catalog — 15 icons, semantic mapping

The icon **must be visually related to its content**. This table maps each icon to the topics it pairs with. Pick from the catalog; do not invent new icons unless the topic is unambiguously outside it.

| Icon | Preview | Use for content about | Example pairings |
|---|---|---|---|
| `warning` | ![warning](template-previews/icons/icon-preview-warning.png) | Scarcity, limitation, risk, caveat, alert | "Datos escasos" · "Riesgo de alucinación" · "Cuidado con…" |
| `shield` | ![shield](template-previews/icons/icon-preview-shield.png) | Privacy, security, compliance, protection | "Privacidad de pacientes" · "HIPAA / GDPR" · "Anonimización" |
| `coins` | ![coins](template-previews/icons/icon-preview-coins.png) | Cost, price, economics, finance | "Coste por token" · "Presupuesto" · "ROI" |
| `lightbulb` | ![lightbulb](template-previews/icons/icon-preview-lightbulb.png) | Idea, tip, insight, analogy, intuition | "Analogía: como una receta…" · "💡 Tip: cachear prompts" |
| `book` | ![book](template-previews/icons/icon-preview-book.png) | Knowledge, documentation, reference, learning | "Bibliografía" · "Para aprender más" · "Documentación oficial" |
| `medical` | ![medical](template-previews/icons/icon-preview-medical.png) | Health, medicine, patient, clinical | "Caso clínico" · "Historia del paciente" · "Diagnóstico" |
| `star` | ![star](template-previews/icons/icon-preview-star.png) | Highlight, featured, key point, recommended | "Mejor práctica" · "Recomendado" · "Punto clave" |
| `check` | ![check](template-previews/icons/icon-preview-check.png) | Success, validated, approved, completed | "Validado" · "Cumple criterio" · "Done" |
| `gear` | ![gear](template-previews/icons/icon-preview-gear.png) | Configuration, settings, system, mechanism | "Cómo funciona" · "Configuración del modelo" · "Engine internals" |
| `chart` | ![chart](template-previews/icons/icon-preview-chart.png) | Data, metrics, analytics, results, benchmarks | "Métricas" · "Resultados" · "Comparativa" |
| `clock` | ![clock](template-previews/icons/icon-preview-clock.png) | Time, deadline, history, sequence, latency | "Latencia" · "Tiempo de respuesta" · "Antes / después" |
| `people` | ![people](template-previews/icons/icon-preview-people.png) | Users, audience, team, stakeholders, patients | "Para clínicos" · "Audiencia objetivo" · "Equipo" |
| `code` | ![code](template-previews/icons/icon-preview-code.png) | Technical, implementation, developer, API | "Ejemplo de código" · "Para devs" · "API call" |
| `search` | ![search](template-previews/icons/icon-preview-search.png) | Research, exploration, discovery, investigation | "Estudio" · "Investigación" · "Análisis de literatura" |
| `info` | ![info](template-previews/icons/icon-preview-info.png) | **Reserved** for the blue insight callout (§8.2) | "Lo que esto hace posible…" · key takeaway |

### 17.2 Style spec — line-art

| Property | Value |
|---|---|
| Stroke color | `#DA1B2E` (brand red, no exceptions) |
| Stroke width | 4 px at 64×64 viewBox (scales proportionally) |
| Fill | `none` for outline icons; `#DA1B2E` solid for small accents only (e.g. the bars in `chart`, the `+` arms in `medical`, the dot under the `warning` exclamation mark) |
| Line cap | `round` |
| Line join | `round` |
| Canvas | 64×64 SVG viewBox; rasterized to 200×200 PNG for fallback |
| Background | transparent — never a coloured backdrop |

**Chip variant (one permitted exception).** The §7.4 card-row layout renders its per-card icon as a **chip**: a filled `#DA1B2E` perfect circle (`ellipse`) acting as the background, with the same catalog line-art glyph overlaid in `#FFFFFF` stroke (color inverted; everything else — viewBox, stroke-width ratio, line caps, line joins — unchanged). The glyph fills ~70% of the chip's diameter and is centered. This treatment is **only** permitted as the card-head decoration in §7.4 — never in §7.5 icon-bullet lists (which use the default line-art-on-white), never in §8 callout markers, never as a standalone icon elsewhere. The chip is a layout-specific decoration, not a permitted theme variant.

**Anti-patterns** (do not):
- Stroke any color other than `#DA1B2E`. No grey icons, no off-red, no dark navy.
- Mix line-art and filled-silhouette styles in the same deck — pick one (this deck = line-art).
- Use system emojis (💡 📚 🏥 ⚠️) as text glyphs. They render unpredictably across PowerPoint/LibreOffice and visually clash with the typographic restraint. Always emit as `<p:pic>` images using the icons in this library.
- Introduce a new icon for a concept that's already covered by the catalog (e.g. don't add a "hospital building" if `medical` already covers it).

### 17.3 Sizing

| Slot | Size on slide | Notes |
|---|---|---|
| **Card-row icon** (above card heading) | `0.41 × 0.41 in` (376535 × 376535 EMU) | The default size used in the source deck for slides 3, 8, 9, 10, 11 |
| **Callout marker** (left of body text) | `0.19 × 0.16 in` to `0.21 × 0.16 in` | Used inside pink and blue callouts |
| **Section-hero icon** (paired with a heading at column top) | `0.40 × 0.40 in` | Same as card-row; the icon sits above the heading, not beside it |
| **Inline marker** (inside body prose, e.g. "✓ done") | `0.12 × 0.12 in` | Rarely used; prefer a Unicode bullet for very small inline marks |

### 17.4 How to render an icon shape in XML

The picture shape format Marp emits has both a PNG fallback and an SVG primary via `<asvg:svgBlip>`. **A generator must emit both** so the icon renders in PowerPoint *and* in LibreOffice/Keynote/Google Slides:

```xml
<p:pic>
  <p:nvPicPr>...</p:nvPicPr>
  <p:blipFill>
    <a:blip r:embed="rIdN">                              <!-- PNG fallback -->
      <a:extLst>
        <a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">
          <asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main"
                        r:embed="rIdN+1"/>               <!-- SVG primary -->
        </a:ext>
      </a:extLst>
    </a:blip>
    <a:stretch><a:fillRect/></a:stretch>
  </p:blipFill>
  <p:spPr>
    <a:xfrm>
      <a:off x="EMU_X" y="EMU_Y"/>
      <a:ext cx="376535" cy="376535"/>                   <!-- 0.41 × 0.41 in -->
    </a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
  </p:spPr>
</p:pic>
```

Then in `slideN.xml.rels` register both:

```xml
<Relationship Id="rIdN"   Type=".../image" Target="../media/image-N-1.png"/>
<Relationship Id="rIdN+1" Type=".../image" Target="../media/image-N-2.svg"/>
```

### 17.5 Selecting the icon at generation time

When a content slide is being assembled and an icon slot needs to be filled:

1. **Read the heading or first body sentence** of the cell the icon will sit above.
2. **Match the dominant noun/concept** to the catalog in §17.1. Most clinical/AI presentations resolve cleanly to 1 of the 15 catalog icons.
3. **If two icons fit, prefer the more specific** (`medical` over `people` for a patient context; `coins` over `chart` for cost data).
4. **If nothing fits**, fall back to `star` (neutral "this matters") rather than inventing a new icon.
5. **In a multi-item layout (e.g. §7.4 card-row, §7.5 icon-bullet list, slide 9's content+image 3-section list, slide 11's 5-row mitigation list), pick a *different* §17.1 icon per item.** Repeating one icon across cards/rows in the same group destroys the visual differentiation the icons exist to provide — the reader scans by glyph shape, not by reading every heading. If two items genuinely share the same dominant concept (rare — usually a sign the items should be merged), fall through to the next-most-specific catalog entry for one of them rather than duplicating. `star` may appear once per group as a neutral fallback; it should never fill more than one slot in the same multi-item layout.

### 17.6 Where to find the assets

| Asset | Location in `base-template.pptx` | Standalone preview |
|---|---|---|
| SVG (preferred — vector) | `ppt/media/icon-<name>.svg` | [`template-previews/icons/icon-preview-<name>.png`](template-previews/icons/) |
| PNG (fallback — 200×200 raster) | Already substituted into the slide media as `image-*.png` | (same preview) |

The 23 slide-attached image slots in `base-template.pptx` are already pre-populated with branded icons (rotating through the catalog) so every preview renders cleanly. When you generate a real deck, replace the rotating selection with the **content-matched** icon per §17.5.

### 17.7 Emoji → catalog-icon swap table

When the source `final.md` contains a system emoji (in body prose, callout lead-ins, headings, anywhere) the renderer **must** swap each emoji to the matching catalog icon (§17.1) emitted as a `<p:pic>` per §17.4. Emojis must never reach the rendered deck — they render unpredictably across PowerPoint / LibreOffice / Keynote / Google Slides and clash with the typographic restraint of the template (see §17 intro + §17.2 anti-patterns).

| Emoji | Catalog icon | Concept |
|---|---|---|
| 💡 ✨ 🧠 | `lightbulb` | Idea, tip, insight, analogy |
| 📚 📖 📝 | `book` | Knowledge, reference, documentation |
| 🏥 ⚕️ 💊 🩺 | `medical` | Health, clinical, patient |
| ⚠️ ❗ 🚨 ⛔ | `warning` | Caveat, alert, scarcity, risk |
| ✅ ✔️ ☑️ 👍 | `check` | Success, validated, approved |
| ⚙️ 🔧 🛠️ | `gear` | Configuration, mechanism, how-it-works |
| 🔍 🔎 🧐 | `search` | Research, exploration, investigation |
| ⏰ ⏱️ ⌛ 🕐 | `clock` | Time, deadline, latency, history |
| 💰 💵 💸 🪙 | `coins` | Cost, price, economics |
| 👥 👤 🧑‍⚕️ 🧑‍💻 | `people` | Users, audience, team, stakeholders |
| 🛡️ 🔒 🔐 | `shield` | Privacy, security, compliance |
| ⭐ 🌟 🏆 | `star` | Highlight, featured, recommended |
| 📊 📈 📉 | `chart` | Data, metrics, results, benchmarks |
| 💻 🖥️ ⌨️ | `code` | Technical, implementation, developer |
| ℹ️ 💬 | `info` | Reserved for blue insight callouts (§8.2) |

Codepoint detection ranges to scan: `U+1F300`–`U+1FAFF`, `U+2600`–`U+27BF`, `U+2300`–`U+23FF`, plus any variation-selector-16 (`U+FE0F`) sequences. Emojis outside this table are **surfaced to the presenter** with a proposed catalog icon (or `star` as the neutral fallback per §17.5) — never silently dropped, never silently rendered as text.

**Strip is not swap.** A renderer that satisfies the no-emoji rule by *deleting* the emoji glyph without substituting a `<p:pic>` of the matching catalog icon has **failed §17.7**, even though the rendered deck looks emoji-free. The emoji carries semantic content (a `💡` flags an idea, a `⚠` flags a caveat); dropping it loses that signal and turns the source bullet into bare text. The contract is: for every detected emoji codepoint, emit a `<p:pic>` per §17.4 at the position the emoji occupied. If the emoji's host context has no icon slot (e.g. it sits in the lead paragraph of a §7.5 layout, which carries no per-paragraph icon), drop the emoji **and** flag it as `[late-catch]`: the source markdown placed an emoji where the layout has nowhere to render it, which is an authoring defect the editor should clean up — not a license to strip silently.

---

## 18. Base-template walkthrough ([`base-template.pptx`](base-template.pptx))

`base-template.pptx` is a 15-slide foundation derived from this spec. It splits into three zones:

| Zone | Slides | Treatment when generating a new deck |
|---|---|---|
| **A. Emit-as-is with substitution** | 1 – 2 | Copy verbatim; substitute the `{{...}}` placeholders. |
| **B. Separator banner** | 3 | **Discard** — never appears in a generated deck. Its only job is to mark the boundary in the template. |
| **C. Layout reference (do not copy content)** | 4 – 15 | **Discard the slides themselves.** Use them only as visual recipes; build your own slides from the matching `§` recipe and your real content. |

Rendered previews live in [`template-previews/base-template/slide-NN.png`](template-previews/base-template/) — one per slide.

### 18.1 Slide-by-slide

| # | Zone | Demonstrates | Spec § | What's on the slide | When generating |
|---|---|---|---|---|---|
| 1 | A | **Cover** | §4 | 4 text shapes (`{{PRESENTATION_TITLE}}`, `{{TALK_SUBTITLE}}`, `Autor: {{PRESENTER}}`, `Última Modificación: {{DATE}}`) + the Universidad Austral logo at (7.86, 3.55) in. | Substitute the four placeholders from `profile.md` (`Subject`, `Presenter`, `Presentation language`) and the Talk's frontmatter (`subtitle`, `date`). Logo stays. |
| 2 | A | **Agenda (item 1 active)** | §5 | Title "Agenda" + 7 placeholder item rows with `{{SECTION_k_TITLE}}` / `{{SECTION_k_SUBTITLE}}` slots. Dot 1 is `#DA1B2E` (active), dots 2–7 are `#F2EEEE` (inactive). | Replace `2 × N` placeholders with the N H1s and `Subtitle:` fields from `final.md` (N = section count). Clone or delete rows so the agenda has exactly N rows. Keep active dot at 1. Always emit immediately after the cover. |
| 3 | B | **Separator banner** | — | Red `#DA1B2E` band across the middle with the text "TEMPLATE — LAYOUT EXAMPLES BELOW", flanked by guidance above/below. | **Drop this slide entirely.** It's a marker for the human/agent reading the template. |
| 4 | C | **image-grid + callout** (was source slide 3) | §7.1 (cards) + §8 (callout) | Section pill `TEMPLATE — IMAGE-GRID + CALLOUT`, large H2, lead paragraph, 3-column image-headed cards, full-width `#F7BBC1` callout at bottom with 💡 emoji. | Use when a slide has 3 supporting concepts each with a small icon, plus a tip/analogy at the bottom. |
| 5 | C | **image-grid** (dense, 2-column components) | §13 image-grid | Section pill `TEMPLATE — IMAGE-GRID`, H2, then a 2×4 grid of icon-headed cards followed by a "what to know" bullet list. | Use for catalog-style listings — N parallel concepts that each fit in a single line of body text. |
| 6 | C | **card-grid** (mixed text + comparison) | §11 (tables-as-cards) + §7.2 | Section pill `TEMPLATE — CARD-GRID`, H2 over a dark "definition" panel on the left, four comparison cards on the right (model name + spec). | Use when content is structurally a small table (label + value rows). Convert pipe-tables to this shape per §11. |
| 7 | C | **content + image** (single hero image) | §13 content+image | Section pill `TEMPLATE — CONTENT + IMAGE`, oversized H2, single paragraph, two image+caption pairs at the bottom. | Use when the slide has one main idea supported by 1–3 illustrative images. |
| 8 | C | **content + cards + image** | §7.2 plain cards + image | Section pill `TEMPLATE — CONTENT + CARDS + IMAGE`, H2, left column: heading + paragraph + `#F7BBC1` callout + link; right column: 3 white `#FFFFFF` cards arranged 2-up + 1-below. | Use when concepts have both narrative and structured supporting data. The richest content layout — appears 4× in the source deck. |
| 9 | C | **content + image** (3-section list) | §13 content+image | Section pill `TEMPLATE — CONTENT + IMAGE`, H2, three `Heading + paragraph` blocks stacked vertically with thumbnail icons. | Use for sequential or hierarchical content (e.g. "Three limitations of X"). |
| 10 | C | **content + image (dense)** | §13 content+image | Section pill `TEMPLATE — CONTENT + IMAGE (DENSE)`, H2, left column: dark `#3B3535` panel with 4 sub-cards; right column: 4 case-study cards. | Use for deep-dive slides — accept higher density than other layouts. |
| 11 | C | **image-grid + card-grid** (mitigation pattern) | §13 image-grid + §7.1 cards | Section pill `TEMPLATE — IMAGE-GRID + CARD-GRID`, H2, left: 5-row icon+heading+body list; right: dark panel with 4 sub-cards + footer "rule of thumb". | Use for "strategies + implementation" slides — paired action list with concrete tactics. |
| 12 | C | **card-grid compare** | §7.1 numbered cards | Section pill `TEMPLATE — CARD-GRID (COMPARE)`, H2, four side-by-side card stacks comparing "before/after" or "weak/strong" approaches. | Use when content is essentially a comparison table. The "vs." pattern of the deck. |
| 13 | C | **Agenda re-emit (section divider, item 2 active)** | §5 + §5.6 | Identical to slide 2 but with the **active dot at position 2** instead of 1, and the previously-active dot 1 now inactive. | Template for section dividers between content sections. Generate one per section transition, incrementing the active index (positions 2, 12, 17, 21, 40, 45, 52 in the source deck). |
| 14 | C | **card-row (lead + 3 short cards)** | §7.3 + §7.4 + §17.2 chip variant | Section pill `TEMPLATE — CARD-ROW (LEAD + 3 CARDS)`, H2, lead paragraph, 3-column row of `#F2EEEE` cards. Each card carries a `#DA1B2E` filled-circle **icon chip** (with a white inner glyph stand-in — the real layout uses a `#FFFFFF` line-art glyph from §17.1), heading, body, and an optional source line at the bottom. | Use when the slide has 3–5 parallel concept summaries each ≤ ~80 chars of body. Pick by the §7.3 decision rule — for longer prose, use slide 15's pattern instead. |
| 15 | C | **icon-bullet list (lead + 3 prose items)** | §7.3 + §7.5 + §17.2 default | Section pill `TEMPLATE — ICON-BULLET LIST (LEAD + 3 ITEMS)`, H2, lead paragraph, vertical stack of 3 rows. Each row carries a line-art `#DA1B2E` icon stand-in (the real layout uses a §17.1 catalog icon — no chip background), heading, and a 2–3-sentence body. Optional source line at the bottom. | Use when the slide has 3–5 parallel items each needing 2–3 sentences of prose. Pick by the §7.3 decision rule — for short labels, use slide 14's pattern instead. |

### 18.2 Generator workflow using base-template

1. **Open** `base-template.pptx` as a working copy.
2. **Slide 1:** find/replace the four cover placeholders with values from `profile.md` + `final.md` frontmatter. Localize `Autor:` / `Última Modificación:` per `Presentation language`.
3. **Slide 2:** find/replace agenda placeholders with the N H1s and subtitles from `final.md` (N = section count). Clone or delete placeholder rows so the agenda has exactly N rows. Keep item 1 active.
4. **Delete slides 3–15** from the working copy — that's the entire layout-reference zone.
5. **Insert content slides** built from your `final.md`, choosing layouts per the emit-rules in §15. The recipes in §6 (section pill), §7 (cards), §8 (callouts), §9 (code), and §13 (taxonomy) are the source of truth — use the slide-3-to-13 PNGs in `template-previews/base-template/` as the visual cross-check.
6. **Insert agenda re-emits** before each new section by duplicating slide 2's structure with the active dot moved to the matching item index.

### 18.3 Marker conventions inside the template

To make it unambiguous during inspection / generation that this is a template (not real content), every layout-reference slide carries **two** markers:

| Marker | Where | What it says |
|---|---|---|
| Section pill | Top-left of every example slide (§6 geometry, `#F9D2D6` fill) | `TEMPLATE — <LAYOUT TYPE>` |
| Placeholder text | Every text shape body | `{{Slide title (h2) N}}`, `{{Card heading N}}`, `{{Body paragraph N}}`, `{{Card body N}}`, `{{Caption / fine print N}}` — role name derived from the original font size bucket |

Plus the single red separator banner on slide 3. Combined, anyone — human or agent — opening `base-template.pptx` can tell at a glance which slides to emit, which to discard, and what each text region represents.

---

## 19. Operating guide for generators

This section is the procedural layer on top of the spec — what an agent does, in what order, to render a `final.md` into `talks/<Talk>/output/final.pptx`. **Decision rules are not duplicated here** — every step points to the earlier §-section that owns the rule. Read the cross-references; don't reinvent them.

The whole guide is small enough to serve as the body of an `md-to-pptx` skill, a system message for a dedicated rendering agent, or a `/render-deck` slash command. If you carry it elsewhere, carry the §-pointers with it — the spec is the contract.

### 19.1 Asset inventory

| File / folder | What it is | When to consult |
|---|---|---|
| [`config/template.pptx`](template.pptx) | The original 53-slide brand reference deck. Read-only. | Only when verifying a measurement not in the spec, or copying a binary asset (cover logo). |
| [`config/pptx-prompt.md`](pptx-prompt.md) | This file — canonical visual specification. | **Always.** Read end-to-end on entry. |
| [`config/base-template.pptx`](base-template.pptx) | Working foundation: cover + agenda with `{{placeholders}}`, red separator (slide 3), 10 layout-example slides, section-divider example (slide 13). | **Always.** Open as the starting deck; substitute placeholders; discard slides 3–13. |
| [`config/template-previews/`](template-previews/) | Rendered PNGs of every template.pptx and base-template.pptx slide + icon catalog. | Visual cross-check when a recipe is ambiguous in prose. |
| [`config/template-previews/icons/`](template-previews/icons/) | 15 branded line-art icon PNG previews. SVG+PNG pairs live in `base-template.pptx` at `ppt/media/icon-<name>.{svg,png}`. | When picking an icon per §17.5. |
| [`config/profile.md`](profile.md) | Presenter's fork-level defaults — Subject, Presenter, Audience, Default duration, Presentation language. | At cover/agenda substitution time (§19.3 stages 1–2). |
| `talks/<Talk>/final.md` | The deliverable Markdown. Frontmatter + structured sections. | The content source. |

### 19.2 Required reading order on entry

Skipping any of these produces a deck that drifts from the spec.

1. Read **this file** (`pptx-prompt.md`) end-to-end. Particularly: §1 (canvas), §3 (typography), §4 (cover), §5 (agenda), §6 (pill), §7 (cards), §8 (callouts), §9 (code), §13 (taxonomy), §15 (emit-rules), §17 (icons), §18 (base-template walkthrough).
2. Read `config/profile.md`. Cache: `Subject`, `Presenter`, `Presentation language`, `Default duration`.
3. Read `talks/<Talk>/final.md`. Cache frontmatter + all N H1 sections (N is variable).
4. Open `config/base-template.pptx` as a working copy. **Never edit the source file.**

### 19.3 Workflow — 7 stages

Each stage points to the §-section that owns the substantive rules. The stage description is the *sequencing*, not the rules themselves.

| Stage | What you do | Rules in |
|---|---|---|
| **1. Cover** | Substitute the 4 placeholders on slide 1: `{{PRESENTATION_TITLE}}` (← `profile.md.Subject`), `{{TALK_SUBTITLE}}` (← `final.md.subtitle` — **required**, never delete the shape; if the field is missing in frontmatter, stop and surface as a render-blocking error so the editor can fill it), `Autor: {{PRESENTER}}` (localize "Autor:" per `Presentation language`), `Última Modificación: {{DATE}}` (localize prefix; format date as "Month, YYYY"). Preserve logo verbatim. | §4 + §4.3 |
| **2. Agenda** | Substitute the placeholders on slide 2: `{{SECTION_k_TITLE}}` and `{{SECTION_k_SUBTITLE}}` for k = 1..N (N = section count). Clone/delete placeholder rows to match N. Active dot stays at 1. Warn the presenter if N > 8 (tight) or N > 10 (out of vertical room — §5.3). | §5 + §5.3 + §5.5 |
| **3. Discard zones B and C** | Delete slides 3 through 15 from your working copy. They are template guidance. After deletion the working deck has only the cover + agenda. | §18 (zone classification) |
| **4. Build content slides** | For each `## <Title>` in `final.md`, pick a layout per the Markdown-signal table (§15), then emit: section pill (§6) at top-left with text = `<UPPERCASE SECTION H1>`, slide title sized adaptively (§3.3), body per the layout recipe, icons per §17.5, callouts per §8 decision table. | §15 + §6 + §7 + §8 + §9 + §13 + §17 |
| **5. Section dividers** | Between section k-1's last slide and section k's first slide (k = 2..N), emit an agenda re-emit with active dot at k. Total dividers = N − 1. | §5 + §5.6 |
| **6. Backgrounds** | Pure white `#FFFFFF` `<p:bg>` solid fill on every layout. No overlays, no tints, no grey. | §1 |
| **7. Speaker notes** | Emit every `### Notes` block from `final.md` into the corresponding slide's notes pane verbatim. The notes pane is **load-bearing**, not decorative — it carries the prose the slide replaces (per [`principles.md`](principles.md) → *Content* → *Speaker notes are the talk*). No truncation, no dropping; never spill notes content into the slide body. | §1 (Speaker-notes pane row) + [`principles.md`](principles.md) |

### 19.4 Output contract

- **File path:** `talks/<Talk>/output/final.pptx`.
- **Slide count:** `2 (cover + agenda active=1) + Σ(content slides per section) + (N − 1) (section-divider agenda re-emits between sections 1→2, 2→3, …, (N−1)→N)`, where N = section count in `final.md`. The deck alternates content blocks and dividers after slide 2.
- **Zip structure:**
  - `[Content_Types].xml` is the **first entry**, stored uncompressed.
  - All other entries deflated.
- **Integrity invariants:**
  - Every `Override PartName` in `[Content_Types].xml` resolves to a real file in the zip.
  - Every XML file in the zip (other than `[Content_Types].xml` itself) is registered with an `Override`.
  - Every `Target` in every `.rels` file resolves to a real file in the zip.
  - `presentation.xml`'s `sldIdLst` entries each have a matching Relationship in `presentation.xml.rels`.
  - `slideMaster1.xml`'s `sldLayoutIdLst` entries each have a matching Relationship in `slideMaster1.xml.rels`.

A clean rebuild of `base-template.pptx` (see its commit history) passes all five invariants. Use that as your sanity baseline.

### 19.5 Verification

After emit, the renderer runs four checks in order before declaring the build a success:

1. **OOXML invariants** per §19.4 — `[Content_Types].xml` first in zip, no dangling overrides / rels, `sldIdLst` resolves.
2. **Aspect-ratio audit** — [`audit_aspect_ratios.py`](../.claude/skills/md-to-pptx/audit_aspect_ratios.py): every `<p:pic>` cx:cy matches the source asset intrinsic ratio within 1%.
3. **Block-coverage audit** — [`audit_block_coverage.py`](../.claude/skills/md-to-pptx/audit_block_coverage.py): every callout and content image in `final.md` appears as the corresponding shape on the rendered slide.
4. **Layout-fit audit** — [`audit_layout_fit.py`](../.claude/skills/md-to-pptx/audit_layout_fit.py): for every content slide, the layout *predicted* from the §15.5 emit-rules table (recomputed from the source markdown's surface signals + §15.6.1 discriminator) equals the layout *emitted* in the rendered slide (inferred from shape composition — `<p:pic>` count and geometry, native `<a:tbl>` presence, bullet shape inventory, code-block presence, per-row icon presence). When predicted ≠ emitted, the audit fails with a structured report naming the source evidence, the emitted evidence, and the likely root cause (typically a §15.6.1 discriminator skip — §10 plain bullets shipped when §7.5 was selected, or content+image shipped when image-grid was selected). This catches the class of regression where the §19.6 anti-pattern check passes (no emojis, no native tables, no theme drift) but the substantive spec was bypassed.

Only after all four pass: render the deck to PNG via `soffice --headless --convert-to pdf` + `pdftoppm` (or the native skill's slide-to-image endpoint), then walk the **12-practice visual review** in [`CLAUDE.md` Step 8](CLAUDE.md) (Post-render visual review) as the cycle's FEEDBACK phase.

Edit + re-render up to **3 cycles total** per the CLAUDE.md *Render cycle* cap. After the cap, surface unresolved defects to the presenter rather than looping.

### 19.6 Consolidated anti-patterns

Things that look reasonable but break the template. The §-section in each row is where the corresponding rule lives.

| Don't | Why | Rule in |
|---|---|---|
| Emit theme fonts (`+mj-lt`, `+mn-lt`) | Template overrides at run level on every shape | §3.1 |
| Emit Office accent colors (`#4472C4`, `#ED7D31`, etc.) | Zero occurrences in template — use only the §2 palette | §2 |
| Use system emojis as text runs (💡 📚 🏥 ⚠) | Render unpredictably across viewers; clash with typography | §17 + §17.2 anti-patterns |
| Mix icon styles in one deck | Library is line-art only — no filled silhouettes | §17.2 |
| Stroke an icon in any color other than `#DA1B2E` | Brand red is the only icon ink | §17.2 |
| Emit native `<a:tbl>` tables | Template has zero — convert pipe-tables to card grids | §11 |
| Emit any background other than pure white `#FFFFFF` (grey tints, the legacy black+overlay recipe, off-whites) | All slides are pure white solid fill | §1 |
| Resize an image without preserving aspect ratio (stretch/squish/anamorphic crop) | Aspect ratio is fixed at the source; scale uniformly only | §12 |
| Use a non-5760 EMU corner radius on roundRects | Constant across all pills/cards/callouts/code/dots | §2.3 |
| Fudge agenda row count to match the placeholder's 7 (pad with blanks, or truncate sections) | Agenda row count = N (section count); clone/delete rows to match. Warn only when N > 8 (tight) or > 10 (out of room). | §5.3 + §5.5 |
| Include base-template slides 3–13 (separator + examples) in output | They are reference, not content | §18 zone C |
| Reuse the pink callout for declarative claims, or the blue for analogies | Variants are not interchangeable | §8 decision table |
| Invent a new icon when the §17.1 catalog has one that fits | Defeats the visual consistency of the library | §17.5 |
| Plain-bullet layout (§10) shipped when source has ≥4 `### Subhead` groups (§15.5 → card-grid / content+cards+image) | Card layouts exist because the deck "strongly prefers cards over bullet lists for grouped content" (§10); falling through to plain bullets defeats the visual hierarchy | §15.6.1 |
| Layout chosen because "it was easier" rather than because §15.5's discriminator selected it | §15.5 is a contract, not a negotiation. Each render must justify its layout choice from the discriminator's output, logged at the cycle's CONTROL phase | §15.6.1 |

### 19.7 When in doubt — navigation

| Question | Where to look |
|---|---|
| "What's the exact EMU position of the cover title?" | §4 |
| "What size is a card-row icon?" | §17.3 |
| "Pink or blue callout for this content?" | §8 decision table |
| "What icon for 'patient privacy'?" | §17.1 → `shield` |
| "How do I emit a section divider?" | §5 + §5.6 |
| "Can I use a native PPTX table?" | §11 — no, convert to cards |
| "What's the slide background color?" | §1 — pure white `#FFFFFF` solid fill on every slide |
| "Can I resize an image to fit a slot exactly?" | §12 — scale uniformly only; aspect ratio is fixed |
| "What font for code blocks?" | §3.1 — Consolas (not Roboto Mono) |
| "How many lines can a slide title span?" | §3.3 — adaptive sz to fit one line |
| "Where is the brand logo?" | `ppt/media/image-1-1.png` in template.pptx / base-template.pptx |
| "How do I render a dual-format icon (PNG fallback + SVG primary)?" | §17.4 |
| "What goes in `[Content_Types].xml`?" | §19.4 integrity invariants |
| "How many iterations of edit + re-render are allowed?" | §19.5 — 2 beyond initial |

### 19.8 Deployment — where this guide can live

The whole spec (§§1–19) is self-contained. Three places it usefully gets installed:

1. **`.claude/skills/md-to-pptx/SKILL.md` body** — the skill loads the full spec on invocation; downstream actually emits the XML.
2. **System message of a dedicated rendering agent** — agent stays oriented across multi-turn editing; pass `talks/<Talk>/final.md` and `config/profile.md` as user-turn inputs.
3. **`/render-deck` slash command body** — one-shot CLI invocation.

In all three cases pointing the agent at `config/pptx-prompt.md` is sufficient — this file is the contract. Trust the spec; defer to `base-template.pptx` for geometry; defer to the §17 catalog for visual marks; defer to the §8 decision table for callouts. When the spec and intuition disagree, the spec wins — file an issue if you think the spec is wrong, but do not silently drift.
