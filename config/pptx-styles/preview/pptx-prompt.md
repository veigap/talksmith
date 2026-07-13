# PPTX style: preview (fast styled HTML of the draft)

Preview is a **first-class render style**, selected like `strict` or `free-form` — not a
special-case branch. Its distinguishing property is its **substrate**: instead of authoring a
native `.pptx` via the Cowork `pptx` skill, it renders a **styled HTML deck by code** from a
pre-Polish `draft.md`. That makes it fast, throwaway, and **Cowork-independent** — the right
tool for a Step-5.5 look before committing to a full render. It is the same renderer as the
`html` deliverable style ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/build_html.py));
`preview` reads `draft.md`, `html` reads `final.md`.

For the native-`pptx` styles see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md) and
[`../free-form/pptx-prompt.md`](../free-form/pptx-prompt.md); for the `html` deliverable see
[`../html/pptx-prompt.md`](../html/pptx-prompt.md); for style selection see
[`../README.md`](../README.md).

> **No base-template, no native skill.** Preview never opens `base-template.pptx` and never
> calls `skill://antropic-skills:/pptx`. Because it renders in HTML, the styled layer (cards,
> icons, callouts, code surfaces) is *fully present* — the only thing deferred to a later
> `strict` / `free-form` render is the native `.pptx` itself.

## 1. Substrate — the committed code renderer

`build_html.py --talk talks/<Talk> --draft` → `talks/<Talk>/output/draft-preview/preview.html`,
a self-contained styled HTML deck. It is the committed renderer so the preview is reproducible
and lives in the skill — never hand-rolled per run. Pipeline: `convert.py --draft` → per-slide
units → classify each (`_classify`) → render the matched template's real styling via the shared
`html_style` components (cards, per-concept Material Symbols icons via `icon_fetch.py`, callout
boxes, code surfaces), with a fit-to-16:9 pass and present mode.

## 2. Template-aware + the shared bar

Preview classifies each slide against the shared catalog
[`../slide-templates.md`](../slide-templates.md) and renders the matched template — cards
(never bullets, per the universal invariant), content+image, code, statement, image-grid,
callout, … — honouring the generic [`../visual-guidance.md`](../visual-guidance.md) floor and
the [`../slide-design.md`](../slide-design.md) practices. An optional `<!-- template: X -->`
comment forces a template. It writes the shared template-decision log to
`output/draft-preview/template-log.md`.

## 3. Its own light critique loop

Preview runs a light **FEEDBACK → REGENERATE** loop, ≤ 2 cycles, walking **CONTENT + TEMPLATE +
AESTHETIC + DISTRIBUTION** ([`../slide-design.md`](../slide-design.md)) on the rendered
`preview.html`. Two properties distinguish it from the pptx styles:

- **No CONTROL phase.** Preview produces no `.pptx`, so the deck-parsing audits can't run;
  `block-coverage`'s guarantee holds by construction (`build_html` renders every unit).
- **REGENERATE surfaces, it doesn't auto-restyle.** The deterministic code renderer takes no
  fix instructions — FEEDBACK findings **surface** to the presenter, who resolves them by
  editing `draft.md` and re-rendering.

Its per-phase config is the `preview` column of [`../render-modes.md`](../render-modes.md) —
the single source of truth; this spec does not restate it.
