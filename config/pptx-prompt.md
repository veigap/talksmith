Visual specification distilled from [`config/template.pptx`](template.pptx) (53 slides). All measurements are concrete and reproducible: a downstream generator should be able to emit `final.pptx` shapes matching the template by reading the EMU coordinates and color hexes verbatim from this file. For diagram-internal style see [`config/diagram-style.md`](diagram-style.md). Visual references for the two contractually-fixed slides are in [`template-previews/`](template-previews/) — they are the source of truth alongside this prose.

> **Starting a new deck?** Open [`config/base-template.pptx`](base-template.pptx) — it's the working foundation derived from this spec: cover + agenda with `{{placeholders}}` to substitute, a red separator banner, and 10 example slides demonstrating every recurring layout pattern. Each example slide carries a `TEMPLATE — <LAYOUT>` pill so it's unambiguous during generation. See **§17** for the branded icon library, **§18** for a slide-by-slide reference of `base-template.pptx`, and **§19** for the operating guide an agent/skill follows when rendering `final.md` into `.pptx` (reading order, workflow stages, output contract, anti-patterns).

> **EMU primer.** 1 inch = 914400 EMU; 1 point = 12700 EMU; font `sz` is in hundredths of a point (`sz="1450"` = 14.5pt). Slide size is `9144000 × 5143500` EMU = `10.00 × 5.625` inches. All shape coordinates below are quoted in **both** EMU (XML-faithful) and inches (human-readable).

---

## 1. Canvas

| Property | Value |
|---|---|
| Aspect ratio | **16:9** |
| Slide size | `9144000 × 5143500` EMU (`10.00 × 5.625` inches; `720 × 405` pt) |
| Apparent background | `#F2F2F2` (light warm grey, **not** pure white) |
| Background recipe | Every slide layout (53 of them — all except the unused `slideLayout1.xml`) sets `<p:bg><p:bgPr><a:solidFill><a:srgbClr val="000000"/></...></p:bg>` (black) **plus** a layer-0 full-canvas `<p:sp>` of size 9144000×5143500 filled `#FFFFFF` with `<a:alpha val="95000"/>` (95%). Black × 5% + White × 95% = `#F2F2F2`. **A generator must emit both elements** — a plain `#F2F2F2` solid fill on the slide looks the same to the eye but will fail an XML-level template comparison. |
| Master chrome | **None** — `slideMaster1.xml` has an empty `<p:spTree>`. No footer, page number, or logo on master. Every visible mark lives on individual slides or layouts. |
| Theme | `theme1.xml` declares Calibri Light / Calibri and the standard Office accent palette. **Zero slides use them** — every run overrides theme defaults at the `<a:rPr>` level. Treat the theme as residual scaffolding; never inherit from it. |
| Speaker-notes pane | Effectively unused (mean ~2 chars/slide). The notes pane is decorative; downstream agents should not rely on it. |

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
| `#F2F2F2` | Code-block surface (and the apparent slide background — see §1) |
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

---

## 4. Slide 1 (Cover) — contractually fixed recipe

> **Visual reference:** [`template-previews/slide-01-cover.png`](template-previews/slide-01-cover.png).
>
> **The cover is the deck's identity slide and must be reproduced byte-for-byte structurally.** Only the *content* of the four text/image shapes changes per Talk; positions, sizes, fonts, colors, and z-order are fixed. The institution logo (Universidad Austral) is part of the brand and never moves.

### 4.1 Background

Layout `slideLayout2.xml` ("Slide 1 master") provides:
- `<p:bg>` black `#000000`
- A full-canvas `<p:sp>` rect at `(0,0)` size `(9144000, 5143500)` filled `#FFFFFF` with `<a:alpha val="95000"/>`

Apparent background: `#F2F2F2`. Same recipe as every other slide.

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
| Shape #2 text | `subtitle:` (Talk-specific; if absent, omit shape #2 entirely — do **not** leave the placeholder text) | `Clase 3: Ingeniería de Prompts y Técnicas Avanzadas` |
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

Same recipe as §1 (layout `slideLayout3.xml`: black `<p:bg>` + 95% white full-canvas rect).

### 5.2 The fixed chrome (title + spine)

| # | Role | EMU off | EMU ext | Inches off | Inches ext | Style |
|---|---|---|---|---|---|---|
| 1 | Title `Agenda` | `(480640, 504974)` | `(3246834, 348704)` | `(0.526, 0.552)` | `(3.551, 0.381)` | `algn="l"`, body insets `0`. `sz="2150"` (21.5pt), Roboto Mono Medium, `#1F1E1E`. |
| 2 | Vertical spine | `(606103, 994172)` | `(14288, 3644354)` | `(0.663, 1.087)` | `(0.016, 3.986)` | `roundRect`, fill `#D8D4D4`. Spans dot row 1 top (`y=1.087`) to dot row 7 bottom + extra (`y≈5.073`). Width 14288 EMU = 1.15 pt. |

### 5.3 Per-item geometry (one row per agenda entry)

Items are stacked vertically with a **constant stride of `540693 EMU (0.591 in)`** between row tops.

Row top y-coordinates (EMU and inches):

| Item | y EMU | y inches |
|---|---|---|
| 1 | 994172 | 1.087 |
| 2 | 1534864 | 1.679 |
| 3 | 2075557 | 2.270 |
| 4 | 2616250 | 2.861 |
| 5 | 3156942 | 3.452 |
| 6 | 3697635 | 4.044 |
| 7 | 4238327 | 4.635 |

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
| Item title (1..7) | The H1 of section N in `final.md` (the numbered section header, e.g. `# 3. In-Context Learning`). Strip the leading `N. `. |
| Item subtitle (1..7) | Section N's `Subtitle:` field if present; else a single-line summary of the section's Goal. |
| Active item index | The agenda instance's position in the deck — slide 2 = active 1; slide 12 = active 2; etc. The mapping is **invariant**: agenda instance N highlights item N. |

**The deck always has exactly 7 sections.** If a Talk's `final.md` has fewer, the agenda recipe still emits 7 rows — empty rows must not collapse, since the geometry depends on a 7-row stride. A generator should warn rather than silently truncate.

### 5.6 Agenda instance positions

| Slide # | Active item |
|---|---|
| 2 | 1 |
| 12 | 2 |
| 17 | 3 |
| 21 | 4 |
| 40 | 5 |
| 45 | 6 |
| 52 | 7 |

The agenda appears between Cover and content (slide 2), then again as a divider before each new section (12, 17, 21, 40, 45, 52). There is no separate "section title" layout.

---

## 6. Section-label pill (universal chrome)

Every content slide (49 of 53 — excluding cover, the 53 closing-CTA, and 3 unusual ones) carries a small pill in the **top-left corner** identifying the parent section.

| Property | Value |
|---|---|
| Geometry | `roundRect`, `prstGeom prst="roundRect"` |
| Position | `(0.53, 0.55)` inches median; range `(0.39 – 0.54, 0.41 – 0.84)` |
| Size | `(1.88, 0.21)` inches median; width adapts to label text (range `1.11 – 3.06` × `0.14 – 0.33`) |
| Fill | `#F9D2D6` |
| Corner radius | ~5760 EMU (4.6 pt), constant — see §2.3 |
| Stroke | None |
| Text shape | A separate `rect` overlay inside the pill, body insets `0`. The pill itself contains no text. |
| Text | ALL CAPS, `sz="550" – "900"` (5.5pt – 9pt) typical, Roboto Mono Medium, `#3B3535` |
| Alignment | Left |

The pill text mirrors the active **agenda section name verbatim, uppercased**. Examples:
- Agenda item 1 "Fundamentos de Foundational Models" → pill text `FUNDAMENTOS DE FOUNDATIONAL MODELS`
- Agenda item 2 "Ingeniería de Prompts Estructurada" → pill text `INGENIERÍA DE PROMPTS ESTRUCTURADA`

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

Bullets are **rare** — only 40 bullet-character runs across all 53 slides. The bullet char, when used, is `•`. The deck strongly prefers **cards over bullet lists** for grouped content. Most list-shaped content (e.g. slide 22's six techniques) is rendered as a 2×3 grid of titled paragraphs without bullets.

When bullets appear (slides 19, 20, 26, 29, 32, 34, 49), they stay shallow — single level, no nesting observed.

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

When rendering `final.md` to `.pptx`, follow these rules in order:

1. **Slide 1 = Cover.** No matter what the Markdown contains for slide 1, emit the §4 recipe. Pull text from frontmatter (`presentation`, `subtitle`, `presenter`, `date`, `Presentation language`). Preserve `ppt/media/image-1-1.png` verbatim. Do **not** apply the section pill (§6).
2. **Slide 2 = Agenda with active item 1.** Emit the §5 recipe. Pull the 7 item titles from the 7 H1s in `final.md`; pull subtitles from per-section `Subtitle:` fields. If `final.md` has ≠7 sections, **warn the presenter** rather than truncating or padding silently.
3. **Section dividers.** Before every new section N (N ∈ {2..7}), re-emit the §5 agenda with active item set to N. Place these at the deck positions listed in §5.6 (12, 17, 21, 40, 45, 52) only when the section's content slide count matches the template's; otherwise place each divider immediately before its section's first content slide.
4. **Every content slide carries a §6 section pill** at top-left, with text = the active section's H1 verbatim, uppercased.
5. **Layout selection per content slide** — pick from §13 based on Markdown signal:

   | Markdown signal in the H2-led slide | Layout type (§13) |
   |---|---|
   | First slide of deck, no H2, frontmatter present | **cover** (§4) |
   | H1-only slide (numbered section header) | **agenda/divider** (§5) — render full 7-item agenda with matching number active |
   | H2 + 1–3 `![]()` images interleaved with paragraphs | **content+image** |
   | H2 + ≥4 `![]()` images | **image-grid** |
   | H2 + fenced ``` ``` code block as primary content | **code-example** (§9) |
   | H2 + sequence of `### Subhead` + paragraph repeats | **card-grid** (no image) or **content+cards+image** (image present) |
   | H2 + pipe-table | **card-grid** via §11 conversion |
   | Final slide with H2 + list of links | **closing-cta** |
   | H2 + paragraphs only, no images, no code | **content-text** (use sparingly — template avoids this) |

6. **Title sizing per content slide.** Apply §3.3 — pick the largest size from the discrete ladder `[17, 18, 19, 20, 21, 22.5, 24, 26, 28, 30, 31]` pt that fits the title on one line.
7. **All `roundRect` shapes use 5760 EMU corner radius** (§2.3). Encode the per-shape `adj` accordingly.
8. **Background.** Emit on every layout the §1 recipe (`<p:bg>` black + 95%-alpha white full-canvas rect). Do not substitute a flat `#F2F2F2` solid fill.
9. **Fonts are always set at run level.** Never inherit from theme. Roboto Mono Medium for titles/labels/headings; Roboto for body; Consolas for code. No fallbacks.
10. **Speaker notes pane is ignored** by default. If the Markdown has speaker notes (`> Notes:` blocks or similar), emit them into the notes pane but do not rely on them visually.

---

## 16. Recipes summary

When you only need a one-line cheat-sheet:

| Concern | Answer |
|---|---|
| Background | Black `<p:bg>` + 95%-alpha-white full-canvas rect → apparent `#F2F2F2` |
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

---

## 18. Base-template walkthrough ([`base-template.pptx`](base-template.pptx))

`base-template.pptx` is a 13-slide foundation derived from this spec. It splits into three zones:

| Zone | Slides | Treatment when generating a new deck |
|---|---|---|
| **A. Emit-as-is with substitution** | 1 – 2 | Copy verbatim; substitute the `{{...}}` placeholders. |
| **B. Separator banner** | 3 | **Discard** — never appears in a generated deck. Its only job is to mark the boundary in the template. |
| **C. Layout reference (do not copy content)** | 4 – 13 | **Discard the slides themselves.** Use them only as visual recipes; build your own slides from the matching `§` recipe and your real content. |

Rendered previews live in [`template-previews/base-template/slide-NN.png`](template-previews/base-template/) — one per slide.

### 18.1 Slide-by-slide

| # | Zone | Demonstrates | Spec § | What's on the slide | When generating |
|---|---|---|---|---|---|
| 1 | A | **Cover** | §4 | 4 text shapes (`{{PRESENTATION_TITLE}}`, `{{TALK_SUBTITLE}}`, `Autor: {{PRESENTER}}`, `Última Modificación: {{DATE}}`) + the Universidad Austral logo at (7.86, 3.55) in. | Substitute the four placeholders from `profile.md` (`Subject`, `Presenter`, `Presentation language`) and the Talk's frontmatter (`subtitle`, `date`). Logo stays. |
| 2 | A | **Agenda (item 1 active)** | §5 | Title "Agenda" + 7 item rows with `{{SECTION_N_TITLE}}` / `{{SECTION_N_SUBTITLE}}` placeholders. Dot 1 is `#DA1B2E` (active), dots 2–7 are `#F2EEEE` (inactive). | Replace 14 placeholders with the seven H1s and `Subtitle:` fields from `final.md`. Keep active dot at 1. Always emit immediately after the cover. |
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

### 18.2 Generator workflow using base-template

1. **Open** `base-template.pptx` as a working copy.
2. **Slide 1:** find/replace the four cover placeholders with values from `profile.md` + `final.md` frontmatter. Localize `Autor:` / `Última Modificación:` per `Presentation language`.
3. **Slide 2:** find/replace 14 agenda placeholders with the seven H1s and subtitles from `final.md`. Keep item 1 active.
4. **Delete slides 3–13** from the working copy — that's the entire layout-reference zone.
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
3. Read `talks/<Talk>/final.md`. Cache frontmatter + the 7 sections.
4. Open `config/base-template.pptx` as a working copy. **Never edit the source file.**

### 19.3 Workflow — 7 stages

Each stage points to the §-section that owns the substantive rules. The stage description is the *sequencing*, not the rules themselves.

| Stage | What you do | Rules in |
|---|---|---|
| **1. Cover** | Substitute the 4 placeholders on slide 1: `{{PRESENTATION_TITLE}}` (← `profile.md.Subject`), `{{TALK_SUBTITLE}}` (← `final.md.subtitle`, delete shape if absent), `Autor: {{PRESENTER}}` (localize "Autor:" per `Presentation language`), `Última Modificación: {{DATE}}` (localize prefix; format date as "Month, YYYY"). Preserve logo verbatim. | §4 + §4.3 |
| **2. Agenda** | Substitute the 14 placeholders on slide 2: `{{SECTION_N_TITLE}}` and `{{SECTION_N_SUBTITLE}}` for N=1..7. Active dot stays at 1. **Hard fail** if `final.md` has ≠7 sections — do not pad or truncate. | §5 + §5.5 |
| **3. Discard zones B and C** | Delete slides 3 through 13 from your working copy. They are template guidance. After deletion the working deck has only the cover + agenda. | §18 (zone classification) |
| **4. Build content slides** | For each `## <Title>` in `final.md`, pick a layout per the Markdown-signal table (§15), then emit: section pill (§6) at top-left with text = `<UPPERCASE SECTION H1>`, slide title sized adaptively (§3.3), body per the layout recipe, icons per §17.5, callouts per §8 decision table. | §15 + §6 + §7 + §8 + §9 + §13 + §17 |
| **5. Section dividers** | Between section N-1's last slide and section N's first slide (N=2..7), emit an agenda re-emit with active dot at N. | §5 + §5.6 |
| **6. Backgrounds** | Every layout you emit must carry the §1 recipe — black `<p:bg>` plus a full-canvas `#FFFFFF` rect with `<a:alpha val="95000"/>`. Apparent `#F2F2F2`. **Never** emit a flat `#F2F2F2` solid fill. | §1 |
| **7. Speaker notes** | If `final.md` has `Speaker notes:` blocks per slide, emit them into the notes pane. The template barely uses it; do not rely on it for content. | (none — decorative) |

### 19.4 Output contract

- **File path:** `talks/<Talk>/output/final.pptx`.
- **Slide count:** `2 (cover + agenda) + Σ(content slides per section) + 6 (section dividers between sections 1→2, 2→3, …, 6→7)`. The deck alternates content blocks and dividers after slide 2.
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

After emit, render the deck to PNG via `soffice --headless --convert-to pdf` + `pdftoppm`, then walk the **10-practice visual review** in [`CLAUDE.md` Step 8](CLAUDE.md) (Post-render visual review): type hierarchy consistency, no text overflow, ≤5–7 bullets per slide, no wall-of-paragraph body, generous margins, visual balance, appropriate image scale, distinct section dividers, single focal point, theme consistency.

Edit + re-render up to **2 iterations** beyond the initial render (CLAUDE.md cap). After the cap, surface unresolved defects to the presenter rather than looping.

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
| Emit a flat `#F2F2F2` background | Use the black + 95%-white-overlay recipe | §1 |
| Use a non-5760 EMU corner radius on roundRects | Constant across all pills/cards/callouts/code/dots | §2.3 |
| Pad fewer or more than 7 agenda items | Geometry depends on the 7-row stride; warn instead | §5.5 |
| Include base-template slides 3–13 (separator + examples) in output | They are reference, not content | §18 zone C |
| Reuse the pink callout for declarative claims, or the blue for analogies | Variants are not interchangeable | §8 decision table |
| Invent a new icon when the §17.1 catalog has one that fits | Defeats the visual consistency of the library | §17.5 |

### 19.7 When in doubt — navigation

| Question | Where to look |
|---|---|
| "What's the exact EMU position of the cover title?" | §4 |
| "What size is a card-row icon?" | §17.3 |
| "Pink or blue callout for this content?" | §8 decision table |
| "What icon for 'patient privacy'?" | §17.1 → `shield` |
| "How do I emit a section divider?" | §5 + §5.6 |
| "Can I use a native PPTX table?" | §11 — no, convert to cards |
| "Why does the background look grey if it's `#FFFFFF`?" | §1 — 95% alpha over black master |
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
