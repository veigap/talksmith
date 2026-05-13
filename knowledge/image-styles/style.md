# Image Style Spec (LLM-optimized)

Visual contract for SVG diagrams in Talksmith. Sibling `*.svg`/`*.txt` files in this directory are recurring shape templates. **Shape catalog is open** (custom ASCII shapes are fine). **Style spec below is closed** — every rendered SVG must conform.

## Hard constraints (apply to every SVG)

- `viewBox="0 0 680 H"`, H ∈ [260, 580]. Width fixed at 680. `width="100%"`.
- Root attrs: `role="img"`. Children include `<title>` + `<desc>` (one-line, Spanish — match corpus language).
- `<defs>` block with `<marker id="arrow">` declared verbatim (see Idioms).
- Outer left margin = 40 px. First panel starts y ≥ 60.
- Heading + subhead pair sits **above** the panel rect, never inside.
- Panel `<rect>` uses `rx="8"` (or `rx="6"` if height < 120) and `stroke-width="0.5"`. Stroke width never exceeds 0.5.

## `<style>` block (paste verbatim)

```css
text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
.t  { font-size: 14px; fill: #1c1c1c; }
.ts { font-size: 12px; fill: #5f5e5a; }
.th { font-size: 14px; font-weight: 500; fill: #1c1c1c; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.c-coral  > rect { fill: #FAECE7; stroke: #993C1D; stroke-width: 0.5; }
.c-purple > rect { fill: #EEEDFE; stroke: #534AB7; stroke-width: 0.5; }
.c-teal   > rect { fill: #E1F5EE; stroke: #1D9E75; stroke-width: 0.5; }
.c-blue   > rect { fill: #E6F1FB; stroke: #185FA5; stroke-width: 0.5; }
.c-gray   > rect { fill: #F1EFE8; stroke: #888780; stroke-width: 0.5; }
.c-amber  > rect { fill: #FAEEDA; stroke: #BA7517; stroke-width: 0.5; }
.c-red    > rect { fill: #FCEBEB; stroke: #E24B4A; stroke-width: 0.5; }
```

## Text class reference

| class | use | size | weight | fill |
|---|---|---|---|---|
| `.t` | body | 14 | 400 | `#1c1c1c` |
| `.ts` | subhead, caption, axis label | 12 | 400 | `#5f5e5a` |
| `.th` | panel heading | 14 | 500 | `#1c1c1c` |
| `.mono` | code / sequence text | inherits | inherits | inherits |

Center text with `text-anchor="middle"`. Override fill inline to tint heading/subhead in the panel hue (use the *darkest* / *mid* values below).

## Per-hue tonal scale

Four tints per hue. Pick by role.

| Role | Coral | Purple | Teal | Blue | Gray | Amber | Red |
|---|---|---|---|---|---|---|---|
| pastel (rect fill) | `#FAECE7` | `#EEEDFE` | `#E1F5EE` | `#E6F1FB` | `#F1EFE8` | `#FAEEDA` | `#FCEBEB` |
| mid (rect stroke, polyline stroke) | `#993C1D` | `#534AB7` | `#0F6E56`/`#1D9E75` | `#185FA5` | `#888780` | `#BA7517` | `#E24B4A` |
| darkest (heading text, emphasis polyline) | `#712B13` | `#3C3489` | `#085041` | `#042C53`/`#0C447C` | `#2C2C2A` | `#854F0B` | `#791F1F` |
| light (centerline, dashed guide) | `#F0997B` | `#7F77DD`/`#AFA9EC` | `#5DCAA5` | `#85B7EB`/`#B5D4F4` | `#B4B2A9` | — | — |

Accents outside the 7-color panel system (foreground markers only, never panel fills):

| Color | Use |
|---|---|
| `#D85A30` | "moving / important" (vivid coral). |
| `#A32D2D` | "wrong / aliased / degraded" (dark red). |
| `#FBEAF0` fill + `#D4537E` stroke | Histology / tissue domain only. Document deviation in `<desc>`. |

## Semantic color → panel class

| Panel meaning | Use |
|---|---|
| anomaly, error, dirty, before-state, baseline noise | `.c-coral` or `.c-red` |
| intermediate processing, improvement-in-progress | `.c-amber` |
| model, system, prediction, computation | `.c-purple` (full panel) or `.c-gray` (black-box inset) |
| final clean state, success, synthetic/generated, after-state | `.c-teal` |
| neutral data, input, reference, ground truth | `.c-blue` |
| raw input, generic placeholder, neutral side-panel | `.c-gray` |

Pick by semantics, not by order. Two-panel diagrams typically use coral/teal (before/after) or blue/teal (real/synthetic).

## Idioms (verbatim, substitute `<placeholder>`)

### Arrow marker — declare once per SVG

```svg
<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>
```

Apply with `marker-end="url(#arrow)"`. Arrow stroke `#5f5e5a` by default; use the panel hue when the arrow belongs visually to one panel.

### Labeled panel

```svg
<text class="th" x="40" y="30" fill="#1c1c1c"><title></text>
<text class="ts" x="40" y="48" fill="#5f5e5a"><subhead></text>
<g class="c-<color>"><rect x="40" y="60" width="600" height="<h>" rx="8"/></g>
```

### Time-series polyline

```svg
<polyline fill="none" stroke="<darkest-hue>" stroke-width="<w>" points="x1,y1 x2,y2 …"/>
```

Stroke width: 1.0 for dense/noisy traces · 1.2–1.6 for headline traces · 1.8 for emphasis. `fill="none"` always.

### Centerline / baseline

Tinted horizontal at the zero level of a polyline panel:

```svg
<line x1=… y1=<zero> x2=… y2=<zero> stroke="<light-hue>" stroke-width="0.5"/>
```

### Annotation drop-line

```svg
<line x1=<x> y1=<peak-y> x2=<x> y2=<label-y+5> stroke="<mid-hue>" stroke-width="0.5" stroke-dasharray="2 2"/>
<text class="ts" x=<x> y=<label-y> fill="<darkest-hue>" text-anchor="middle"><label></text>
```

### Bottom caption

```svg
<text class="ts" x="340" y=<bottom> text-anchor="middle" fill="#888780"><sentence></text>
```

One sentence max. Centered on the 680-px canvas mid-point.

### Color-stepped grid (heatmap / pixel art)

Row or column of equal-size `<rect>`s, fills stepping through the same hue family. ≥7 steps for a smooth gradient feel.

## ASCII → SVG mapping

| ASCII element | SVG output |
|---|---|
| Box `+----+ \| ... \|` | `<g class="c-<color>"><rect rx="8" stroke-width="0.5"/></g>` |
| Title at box top-left | `<text class="th">` above the rect (y≈30) |
| Subtitle under title | `<text class="ts">` above the rect (y≈48) |
| Arrow `-->` / `==>` | `<line marker-end="url(#arrow)" stroke="#5f5e5a"/>` |
| Waveform `/\/\` / `___/\__` / `~~~~` | `<polyline fill="none" stroke="<darkest>">` |
| Color hint `[coral]` / `[teal]` | sets `class="c-<color>"` on the panel `<g>` |
| `mono:` prefix | apply `.mono` class to the `<text>` |
| Bottom sentence | `<text class="ts" text-anchor="middle" fill="#888780">` |
| `<title>` of slide | becomes SVG `<title>` |
| First sentence of slide speaker notes | becomes SVG `<desc>` |

Color selection is **semantic, never positional** — consult the *Semantic color → panel class* table above.

## Catalog of recurring shapes

Each row points to two sibling files in this directory: the canonical rendered `.svg` and the parameterized ASCII template `.txt` (with `<placeholder>` slots). Catalog is **open**: when no row fits, draft a custom ASCII shape — the style spec above still applies.

| Category | Trigger | Variants |
|---|---|---|
| [`grid-2x2`](grid-2x2.txt) · [svg](grid-2x2.svg) | 3–4 sibling concepts that differ in *kind*. Each cell its own color. | — |
| [`stack-signals`](stack-signals.txt) · [svg](stack-signals.svg) | 2–4 similar 1-D traces stacked, full-page width. | — |
| [`pipeline-3-stage`](pipeline-3-stage.txt) · [svg](pipeline-3-stage.svg) | input → process → output, three boxes with arrows. | **model-blackbox**: middle stage rendered as smaller `.c-gray` panel inset between larger end panels. |
| [`dual-view-side-by-side`](dual-view-side-by-side.txt) · [svg](dual-view-side-by-side.svg) | Same data in two equivalent representations. Equivalence asserted by bottom caption. | — |
| [`progression-sequence`](progression-sequence.txt) · [svg](progression-sequence.svg) | Convergence/refinement over 3 discrete steps. "More X →" caption below. | — |
| [`frame-grid-2-rows`](frame-grid-2-rows.txt) · [svg](frame-grid-2-rows.svg) | Compare two scenarios across the same time axis. Top = reference; bottom = contrast/failure. | — |
| [`pipeline-stages-vertical`](pipeline-stages-vertical.txt) · [svg](pipeline-stages-vertical.svg) | Same signal evolving through 3–4 stacked full-width transformations. Color carries progression. | **degradation**: invert color story to teal → amber → red. |
| [`paired-explainer`](paired-explainer.txt) · [svg](paired-explainer.svg) | Mechanism + its output, with cross-labels mapping cause → effect. Differs from `dual-view-side-by-side`: here one panel *produces* the other. | — |
| [`multi-representation-3`](multi-representation-3.txt) · [svg](multi-representation-3.svg) | Same object in 3 encodings (visual + text/code + spatial). Middle panel `.mono`. | — |
| [`zoom-detail-pair`](zoom-detail-pair.txt) · [svg](zoom-detail-pair.svg) | Wide context + zoomed crop. Wide panel must include a highlight rect marking the crop region. | Domain pink (`#FBEAF0`/`#D4537E`) acceptable for histology; document in `<desc>`. |
| [`mosaic-pair`](mosaic-pair.txt) · [svg](mosaic-pair.svg) | Compare two collections of same-kind mini-charts; row-vs-row contrast (blue ref vs teal contrast). Differs from `grid-2x2`: cells share the panel color; contrast is between rows, not cells. | — |
