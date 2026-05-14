# Image Style Spec (LLM-optimized)

Visual contract for SVG diagrams in Talksmith. Sibling `*.svg`/`*.txt` files in this directory are recurring shape templates. **Shape catalog is open** (custom ASCII shapes are fine). **Style spec below is closed** — every rendered SVG must conform.

## Hard constraints (apply to every SVG)

- `viewBox="0 0 680 H"`, H ∈ [260, 580]. Width fixed at 680. `width="100%"`.
- Root attrs: `role="img"`. Children include `<title>` + `<desc>` (one-line each). **All in-SVG text** (`<title>`, `<desc>`, panel headings, subheads, captions, axis labels) uses the **`Presentation language`** declared in [`knowledge/profile.md`](../profile.md). If the profile is missing or that field is empty, fall back to the language of `master.md`'s prose; if still ambiguous, ask the presenter before rendering.
- `<defs>` block with `<marker id="arrow">` declared verbatim (see Idioms).
- Outer left margin = 40 px. First panel starts y ≥ 60.
- Heading + subhead pair sits **above** the panel rect by default. **Exception:** pipeline-style small-square panels (e.g. `pipeline-3-stage` boxes ≤ 200 wide) center heading + subhead **inside** the panel using `text-anchor="middle"` at panel center, heading at `panel.y + 35`, subhead at `panel.y + 55`.
- Panel `<rect>` uses `rx="8"` by default; use `rx="6"` when panels are part of a stacked sequence (rhythm consistency) regardless of height. `stroke-width="0.5"` always; never exceed.

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
| mid (rect stroke only; also dashed reference polylines at 0.6 width) | `#993C1D` | `#534AB7` | `#0F6E56`/`#1D9E75` | `#185FA5` | `#888780` | `#BA7517` | `#E24B4A` |
| darkest (heading text inside colored panel; **primary polyline stroke**) | `#712B13` | `#3C3489` | `#085041` | `#042C53`/`#0C447C` | `#2C2C2A` | `#854F0B` | `#791F1F` |
| light (centerline / baseline; reference grid lines) | `#F0997B` | `#7F77DD`/`#AFA9EC` | `#5DCAA5` | `#85B7EB`/`#B5D4F4` | `#B4B2A9` | — | — |

**Gray panel exception:** primary traces inside a `.c-gray` panel use stroke `#444441` (one shade darker than the listed `darkest` `#2C2C2A`) for readable contrast on the pastel-gray fill.

**Polyline stroke quick rule:** primary trace = **darkest**, width 1.0–1.8; dashed reference/target overlay = **mid**, width 0.6, `stroke-dasharray="3 3"`. Width 1.8 specifically when the trace is paired with a dashed reference in the same panel (convergence/approximation slides).

Accents outside the 7-color panel system (foreground markers only, never panel fills):

| Color | Use |
|---|---|
| `#D85A30` | "moving / important" (vivid coral). |
| `#A32D2D` | "wrong / aliased / degraded" (dark red). |
| Histology ramp: pastel `#FBEAF0`, light fill `#F4C0D1`, mid fill `#ED93B1`, stroke `#D4537E`, darkest `#993556` | Histology / tissue domain only. Document deviation in `<desc>`. |

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

## Panel layout grid

Canonical column geometries on the 680-px canvas with the 40-px outer margin:

| Layout | Panel widths | Panel x positions | Notes |
|---|---|---|---|
| **Full-width** (stacked rows) | 600 | x=40 | One panel per row. Heights vary per content. |
| **2-up** (side-by-side) | 290 each | x=40, x=350 | 20-px gutter at x∈[330, 350]. |
| **3-up** (side-by-side) | 200 each | x=40, x=240, x=440 | Abutting, no gutter. |
| **3-up pipeline** (small boxes + arrow connectors) | 160 each | x=40, x=260, x=480 | 60-px arrow gap between boxes (arrow line uses x1=panel.right+2, x2=next-panel.left−2). |
| **2-up asymmetric** (paired-explainer style) | 280 + 280 | x=40, x=360 | 40-px gutter for caption breathing room. |

Per-panel content inset = **15 px** from panel left/right edges (inner-text x = panel.x + 15; centerline/baseline endpoints inset 15 from each end).

## Panel heights — pick by content

| Content type | Height |
|---|---|
| Slim trace (single waveform, no annotations) | 80 |
| Standard trace (multi-channel, annotated peaks, headline polyline) | 110–170 |
| Tall diagram (orbit + labels, 3D illustration, pixel grid, mosaic) | 200–280 |
| Pipeline box (small, label + tiny viz) | 100–140 |

Stacked sequences (`pipeline-stages-vertical`, `stack-signals`) use **uniform** heights for rhythm. Pipelines (`pipeline-3-stage`) may vary the middle panel by ±40 to emphasize the centerpiece.

## Heading + subhead — position rules

| Layout | Heading position | Subhead position |
|---|---|---|
| Full-width stacked panel | x=40 (canvas margin), y = panel.y − 30; fill `#1c1c1c` | x=40 *or* inline to the right of heading at the same y (when vertical space is tight: x = 40 + heading-text-width + 12); fill `#5f5e5a` |
| Side-by-side panels (2-up / 3-up) | x = panel.x + 15 (panel inner-left), y = panel.y − 30; fill = panel's darkest hue | x = panel.x + 15, y = panel.y − 12; fill = panel's mid hue |
| Narrow pipeline box (≤ 200 wide) | text-anchor="middle" at panel center; y = panel.y + 35; fill = panel's darkest hue | text-anchor="middle" at panel center; y = panel.y + 55; fill = panel's mid hue |

**Fill rule recap:** heading/subhead use neutral fills (`#1c1c1c` / `#5f5e5a`) when the heading sits outside / above a single colored panel context, but switch to the panel's darkest/mid hues when the heading is tied tightly to one colored panel (inside the panel, or directly above a single side-by-side panel).

## Idioms (verbatim, substitute `<placeholder>`)

### Arrow marker — declare once per SVG

```svg
<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>
```

Apply with `marker-end="url(#arrow)"`. Arrow stroke `#5f5e5a` by default; use the panel hue when the arrow belongs visually to one panel.

### Pipeline connector arrow (between adjacent boxes)

Straight neutral arrow joining two pipeline panels:

```svg
<line x1=<left.right + 2> y1=<panel-mid-y> x2=<right.left - 2> y2=<panel-mid-y>
      stroke="#5f5e5a" stroke-width="1.5" marker-end="url(#arrow)"/>
```

Vertical position = midpoint of the connected rects; 2 px gap on each side.

### Curved transition arrow (between frames, time evolution)

Quadratic Bezier with marker-end. Used in `frame-grid-2-rows` between successive time frames:

```svg
<path d="M <x1> <y1> Q <xmid> <ymid> <x2> <y2>" fill="none"
      stroke="<accent-or-panel-hue>" stroke-width="1.2" marker-end="url(#arrow)"/>
```

Color is semantic: success/forward = `#1D9E75` (teal mid); failure/aliased = `#A32D2D` (dark red accent).

### Labeled panel (default — heading above)

```svg
<text class="th" x="40" y="30" fill="#1c1c1c"><title></text>
<text class="ts" x="40" y="48" fill="#5f5e5a"><subhead></text>
<g class="c-<color>"><rect x="40" y="60" width="600" height="<h>" rx="8"/></g>
```

### Labeled panel — heading inside (pipeline box variant)

For pipeline boxes ≤ 200 wide:

```svg
<g class="c-<color>"><rect x=<panel.x> y=<panel.y> width=<w> height=<h> rx="8"/></g>
<text class="th" x=<panel.cx> y=<panel.y + 35> text-anchor="middle" fill="<darkest-hue>"><title></text>
<text class="ts" x=<panel.cx> y=<panel.y + 55> text-anchor="middle" fill="<mid-hue>"><subhead></text>
```

### Time-series polyline

```svg
<polyline fill="none" stroke="<darkest-hue>" stroke-width="<w>" points="x1,y1 x2,y2 …"/>
```

Stroke width: 1.0 for dense/noisy traces · 1.2–1.6 for headline traces · 1.8 for emphasis (paired with a dashed reference). `fill="none"` always. Sample density: every 2 px on x for dense traces, every 5–7 px for coarse. Amplitude window ≈ ±25 px around centerline.

### Dashed reference polyline (target / ideal overlay)

For approximation slides — the ideal curve drawn behind the actual:

```svg
<polyline fill="none" stroke="<mid-hue>" stroke-width="0.6" stroke-dasharray="3 3" points="…"/>
```

### Centerline / baseline

Tinted horizontal at the zero level of a polyline panel. Endpoints inset 15 px from panel edges:

```svg
<line x1=<panel.x + 15> y1=<zero> x2=<panel.x + panel.width - 15> y2=<zero>
      stroke="<light-hue>" stroke-width="0.5"/>
```

### Annotation drop-line

Dashed vertical from a polyline peak to a label, dash pattern `2 2`:

```svg
<line x1=<x> y1=<peak-y> x2=<x> y2=<label-y+5> stroke="<mid-hue>" stroke-width="0.5" stroke-dasharray="2 2"/>
<text class="ts" x=<x> y=<label-y> fill="<darkest-hue>" text-anchor="middle"><label></text>
```

Dash convention: `2 2` for annotations/drop-lines; `3 3` for reference/target overlays, orbit/guide circles, and zoom connector lines.

### Bottom caption

```svg
<text class="ts" x="340" y="<viewBox.height − 22>" text-anchor="middle" fill="#888780"><sentence></text>
```

Always `x="340"` (canvas mid-point). When a formal expression (equation, identity) precedes the plain-language caption, it sits at y = caption.y − 20 with fill = `#5f5e5a` (or the panel-darkest hue if tied to one stage).

### Color-stepped grid (heatmap / pixel art)

Row or column of equal-size `<rect>`s, fills stepping through the same hue family. Default cell = **24×24 with 2 px gap**. Use the full 7-step ramp; for blue: `#042C53 → #0C447C → #185FA5 → #378ADD → #85B7EB → #B5D4F4 → #E6F1FB`.

### Highlight rect (zoom-detail wide panel)

The small empty rect inside the wide-view panel marking the magnified region:

```svg
<rect x=<x> y=<y> width=<w> height=<h> fill="none"
      stroke="<panel-mid-hue>" stroke-width="1.5"/>
```

No `rx`. Stroke uses the panel's mid hue (or `#993556` for histology).

### Zoom connector lines (zoom-detail pair)

Three dashed lines fanning from the highlight rect to the detail panel's left edge:

```svg
<line x1=<hl.right> y1=<hl.top> x2=<detail.left> y2=<detail.top>
      stroke="#5f5e5a" stroke-width="0.6" stroke-dasharray="3 3"/>
<line x1=<hl.right> y1=<hl.cy>  x2=<detail.left> y2=<detail.cy>
      stroke="#5f5e5a" stroke-width="1.2" stroke-dasharray="3 3"/>
<line x1=<hl.right> y1=<hl.bottom> x2=<detail.left> y2=<detail.bottom>
      stroke="#5f5e5a" stroke-width="0.6" stroke-dasharray="3 3"/>
```

The middle (mid-y) line is heavier (1.2) to anchor the eye; top/bottom are 0.6.

## ASCII → SVG mapping

| ASCII element | SVG output |
|---|---|
| Box `+----+ \| ... \|` | `<g class="c-<color>"><rect rx="8" stroke-width="0.5"/></g>` |
| Title at box top-left | `<text class="th">` above the rect (y = panel.y − 30) — *or* inside the rect (y = panel.y + 35, `text-anchor="middle"`) for narrow pipeline boxes (≤ 200 wide) |
| Subtitle under title | `<text class="ts">` 18 px below the heading; fill = neutral `#5f5e5a` for full-width panels, panel-mid hue for side-by-side or inside-pipeline panels |
| Arrow `-->` / `==>` | `<line marker-end="url(#arrow)" stroke="#5f5e5a"/>` |
| Waveform `/\/\` / `___/\__` / `~~~~` | `<polyline fill="none" stroke="<darkest>">` |
| Color hint `[coral]` / `[teal]` | sets `class="c-<color>"` on the panel `<g>` |
| `mono:` prefix | apply `.mono` class to the `<text>`; combine with `.th` for emphasized code/sequence content (`class="th mono"`) |
| Bottom sentence | `<text class="ts" text-anchor="middle" fill="#888780">` |
| `<title>` of slide | becomes SVG `<title>` |
| First sentence of slide speaker notes | becomes SVG `<desc>` |

Color selection is **semantic, never positional** — consult the *Semantic color → panel class* table above.

## Catalog of recurring shapes

Each row points to the parameterized ASCII template `.txt` (with `<placeholder>` slots) — that is the **input the renderer reads**. The `[svg]` link in each row points to a canonical rendered example **for human reference only**; renderers (the `talksmith:ascii-to-svg` skill, the `illustrator` agent) must **not** read those `.svg` files. The rendering contract is `style.md` (this file) + the matched `.txt` template + slide context. Catalog is **open**: when no row fits, draft a custom ASCII shape — the style spec above still applies.

| Category | Trigger | Variants |
|---|---|---|
| [`grid-2x2`](grid-2x2.txt) · [svg](grid-2x2.svg) | 3–4 sibling concepts that differ in *kind*. Each cell its own color. | — |
| [`stack-signals`](stack-signals.txt) · [svg](stack-signals.svg) | 2–4 similar 1-D traces stacked, full-page width. | — |
| [`pipeline-3-stage`](pipeline-3-stage.txt) · [svg](pipeline-3-stage.svg) | input → process → output, three boxes with arrows. | **model-blackbox**: middle stage rendered as smaller `.c-gray` panel inset between larger end panels. |
| [`dual-view-side-by-side`](dual-view-side-by-side.txt) · [svg](dual-view-side-by-side.svg) | Same data in two equivalent representations. Equivalence asserted by bottom caption. | — |
| [`progression-sequence`](progression-sequence.txt) · [svg](progression-sequence.svg) | Convergence/refinement over 3 discrete steps. "More X →" caption below. | — |
| [`frame-grid-2-rows`](frame-grid-2-rows.txt) · [svg](frame-grid-2-rows.svg) | Compare two scenarios across the same time axis. Top = reference; bottom = contrast/failure. Cells are **circles** (`r=45`) for rotational/orbital content; spacing **5 frames at 115 px stride** starting x=80; row centers y≈130 (top) and y≈330 (bottom). Curved arrows between frames carry semantic color. | — |
| [`pipeline-stages-vertical`](pipeline-stages-vertical.txt) · [svg](pipeline-stages-vertical.svg) | Same signal evolving through 3–4 stacked full-width transformations. Color carries progression. | **degradation**: invert color story to teal → amber → red. |
| [`paired-explainer`](paired-explainer.txt) · [svg](paired-explainer.svg) | Mechanism + its output, with cross-labels mapping cause → effect. Cross-labels use `.th` for sparse spatial markers (≤ 6 points), `.ts` for dense waveform annotations; label fill = panel's darkest hue. Differs from `dual-view-side-by-side`: here one panel *produces* the other. | — |
| [`multi-representation-3`](multi-representation-3.txt) · [svg](multi-representation-3.svg) | Same object in 3 encodings (visual + text/code + spatial). Middle panel `.mono`. | — |
| [`zoom-detail-pair`](zoom-detail-pair.txt) · [svg](zoom-detail-pair.svg) | Wide context + zoomed crop. Wide panel must include a highlight rect marking the crop region. | Domain pink (`#FBEAF0`/`#D4537E`) acceptable for histology; document in `<desc>`. |
| [`mosaic-pair`](mosaic-pair.txt) · [svg](mosaic-pair.svg) | Compare two collections of same-kind mini-charts; row-vs-row contrast (blue ref vs teal contrast). Inner cell frames: `stroke = panel's light hue`, `stroke-width="0.5"`, `fill="none"`, no `rx`. Cells are content-sized (free-packed, not gridded); all cells share the panel's color. Differs from `grid-2x2`: cells share the panel color; contrast is between rows, not cells. | — |
