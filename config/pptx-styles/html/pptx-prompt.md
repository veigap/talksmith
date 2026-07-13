# PPTX style: html (static-site deliverable)

`html` is a **first-class render style** whose deliverable is a **styled static HTML site**,
not a `.pptx`. It is the presentable sibling of `preview`: both are the same code-generated
renderer ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/build_html.py), shared
tokens/components in `html_style.py`) — `preview` renders a pre-Polish `draft.md` for a fast
throwaway look, `html` renders `final.md` as a shareable deliverable.

For the native-`pptx` styles see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md) and
[`../free-form/pptx-prompt.md`](../free-form/pptx-prompt.md); for style selection see
[`../README.md`](../README.md).

> **Deterministic, and that's the point.** Unlike the native `.pptx` render (which follows
> prose and can silently drop the styled layer — icons, callouts, code surfaces), the HTML
> render emits that layer **every time**, because the same components produce it in code. No
> Cowork, no native skill, no base-template.

## 1. Substrate — the committed code renderer

`build_html.py --talk talks/<Talk>` → a self-contained `output/html/index.html`. Pipeline:
`convert.py` → per-slide units → classify each against the shared catalog
([`../slide-templates.md`](../slide-templates.md), `_classify`) → render the matched
template's real styling in the strict tokens (palette, Helvetica/Courier, §7/§8/§9 geometry):
cards, **per-concept Material Symbols icons** (fetched by name via
[`icon_fetch.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/icon_fetch.py), recoloured to
`#DA1B2E`, inlined), callout boxes, code surfaces, numbered strips. A §4 **cover slide** is
prepended from the frontmatter. SVG images embed inline; PNG/JPG as data-URIs.

## 2. Template-aware + the same shared bar

Every slide honours the shared catalog (**cards, never bullets**), the generic
[`../visual-guidance.md`](../visual-guidance.md) floor, and the
[`../slide-design.md`](../slide-design.md) practices — the HTML substrate simply *guarantees*
them. An optional `<!-- template: X -->` comment under a slide heading **forces** that template
over auto-classification. Writes the shared template-decision log to
`output/html/template-log.md`.

## 3. Presentation & fit

The page is a **presentable deck**: a fixed header (section pill + title, anchored — it does
not move with content) over a content region that **scales to fit 16:9** (nothing clipped),
and a **present mode** — ▶ full screen, → / ← or click to advance, `F` toggles browser full
screen, `Esc` exits. Slides are white by design.

## 4. Render flow

`html` is **GENERATE → FEEDBACK (≤2, `walk-design`) → surface**, per the `html` column of
[`../render-modes.md`](../render-modes.md) — the single source of truth; this spec does not
restate it. **No CONTROL phase** (it produces no `.pptx`, so the deck-parsing audits don't
apply; block-coverage holds by construction — every unit is rendered). REGENERATE **surfaces**
findings (the code renderer takes no per-slide fix instructions; the presenter resolves them
by editing `final.md` and re-rendering). The canonical `test` fixture that exercises every
template lives at `tests/skills/md-to-pptx/`.
