# Render style: html-strict (static HTML / Reveal.js deliverable)

`html-strict` is a **first-class render style** whose deliverable is a **styled static HTML /
Reveal.js site**, not a `.pptx`. It is the code-generated renderer
([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py), shared
tokens/components in `html_style.py`, per-slide-type markup in `templates/html/*.j2`). One
renderer, **two sources**: it renders the in-progress `draft.md` as a **live view** (auto-fired
after the first complete draft and kept in sync each review, `--draft`) and `final.md` as the
shareable **deliverable** — both to `output/html/index.html`. There is no separate "preview" mode.

For the native-`pptx` styles see [`../pptx-strict/pptx-prompt.md`](../pptx-strict/pptx-prompt.md) and
[`../pptx-free-form/pptx-prompt.md`](../pptx-free-form/pptx-prompt.md); for style selection see
[`../README.md`](../README.md).

> **Deterministic, and that's the point.** Unlike the native `.pptx` render (which follows
> prose and can silently drop the styled layer — icons, callouts, code surfaces), the HTML
> render emits that layer **every time**, because the same components produce it in code. No
> Cowork, no native skill, no base-template.

## 1. Substrate — the committed code renderer

`build_html.py --talk talks/<Talk>` → a self-contained `output/html/index.html`. Pipeline:
`convert.py` → per-slide units (`slide_model._parse_unit`) → classify each against the shared
catalog ([`../slide-templates.md`](../slide-templates.md), `slide_model._classify`) → render the
matched template's markup (one Jinja template per type, `templates/html/*.j2`) in the strict
**palette** (`#DA1B2E` accent, pill/callout tints) with **IBM Plex Sans/Mono** (vendored, inlined
as `@font-face` data-URIs): cards, **per-concept Material Symbols icons** (matched to each concept
against the live catalog, then fetched by name via
[`icon_fetch.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/icon_fetch.py), recoloured to
`#DA1B2E`, inlined), callout boxes, code surfaces, numbered strips. A §4 **cover slide** is
prepended from the frontmatter. SVG images embed inline; PNG/JPG as data-URIs. It approximates the
strict templates' *shapes* in CSS (container-query `cqw` units on a fixed 16:9), not the native
`.pptx` §7/§8/§9 EMU geometry.

The presentation shell is **[Reveal.js](https://revealjs.com/)** (vendored under
`skills/md-to-deck/vendor/reveal/`, inlined so the deck stays offline + self-contained). Each
slide is a Reveal `<section>`; our catalog templates render *inside* them as a custom Reveal
theme aligned with the strict tokens. Reveal owns navigation, deck-to-window scaling,
transitions, overview, speaker notes, and PDF export; the only custom code is a per-slide
content-fit (scale-to-fill-width + fit-height — the one thing Reveal/CSS can't do).

## 2. Template-aware + the same shared bar

Every slide honours the shared catalog (**cards, never bullets**), the generic
[`../visual-guidance.md`](../visual-guidance.md) floor, and the
[`../slide-design.md`](../slide-design.md) practices — the HTML substrate simply *guarantees*
them. An optional `<!-- template: X -->` comment under a slide heading **forces** that template
over auto-classification. Writes the shared template-decision log to
`output/html/template-log.md`.

## 3. Presentation, notes & export (Reveal.js)

A **presentable Reveal.js deck**: a fixed header (section pill + title, anchored) over a
content region that fits 16:9 (nothing clipped). Reveal provides the presentation affordances
out of the box:

- **Navigate** — → / ← / Space / click to advance, `Esc` for the slide overview, `F` full
  screen. The whole deck scales to any window.
- **Speaker notes** — presenter comments (source `### Speaker notes`) are captured into
  `<aside class="notes">` and shown in Reveal's **speaker view** (press `s`), never on the
  slide face — the native-`.pptx` notes-pane behaviour, in HTML.
- **PDF export** — open the deck with `?print-pdf` appended to the URL, then Print → Save as
  PDF (one slide per page). Good for handouts.
- **Transitions** — a subtle slide transition between steps.

Slides are white by design.

## 4. Render flow

`html-strict` is **GENERATE → FEEDBACK (≤2, `walk-design`) → surface**, per the `html-strict` column of
[`../render-modes.md`](../render-modes.md) — the single source of truth; this spec does not
restate it. **No CONTROL phase** (it produces no `.pptx`, so the deck-parsing audits don't
apply; block-coverage holds by construction — every unit is rendered). REGENERATE **surfaces**
findings (the code renderer takes no per-slide fix instructions; the presenter resolves them
by editing `final.md` and re-rendering). The canonical `test` fixture that exercises every
template lives at `tests/skills/md-to-deck/`.
