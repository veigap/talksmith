# PPTX style: preview (draft wireframe)

Preview is a **first-class render style**, selected like `strict` or `free-form` — not a
special-case branch. Its distinguishing property is its **substrate**: instead of authoring
a native `.pptx` via the Cowork `pptx` skill, it draws each slide **by code** (Pillow) to a
numbered PNG. That makes it fast, throwaway, and **Cowork-independent** — the right tool for
a Step-5.5 look at a pre-Polish `draft.md` before committing to a full render.

For the spec-driven and free-design styles see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md)
and [`../free-form/pptx-prompt.md`](../free-form/pptx-prompt.md); for style selection see
[`../README.md`](../README.md).

> **No base-template, no native skill.** Preview never opens `base-template.pptx` and never
> calls `skill://antropic-skills:/pptx`. It has no `.pptx`, `.pdf`, palette, or font contract —
> the real look comes from a later `strict` / `free-form` render.

## 1. Substrate — the committed code renderer

The entire render is [`build_preview.py --talk talks/<Talk>`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/build_preview.py)
(Pillow only). It is the committed renderer so the preview is reproducible and lives in the
skill — never hand-rolled per run. Pipeline: `convert.py --draft --split-dir` → per-slide
units → `preview_plan.py` content-addressed cache (only changed slides re-render) →
`render_ascii.py` (ASCII fences → PNG) → per-slide PNG. Output: numbered
`talks/<Talk>/output/draft-preview/slide-NN.png`.

## 2. Template-aware, like every style

Preview classifies each slide against the shared catalog
[`../slide-templates.md`](../slide-templates.md) (`build_preview._classify`) and draws that
template's shape — concept-breakdown / process / figures as **cards** (never bullets, per the
catalog's universal invariant), content+image split, code block, statement, image-grid —
falling back to a plain title+body flow. It honors the generic
[`../visual-guidance.md`](../visual-guidance.md) floor to the fidelity a wireframe allows
(legible text, no overlap, structure over bullets); exact palette/fonts are deliberately not
its job.

## 3. Its own critique loop

Preview runs a light **FEEDBACK → REGENERATE** loop, ≤ 2 cycles, walking **CONTENT +
TEMPLATE + AESTHETIC + DISTRIBUTION** (the [`../slide-design.md`](../slide-design.md)
practices) on the numbered PNGs, scoped to the changed slides. Two properties distinguish it
from the pptx styles:

- **No CONTROL phase.** Preview produces no `.pptx`, so the deck-parsing audits can't run;
  `block-coverage`'s guarantee holds by construction (`build_preview` renders every unit).
- **REGENERATE surfaces, it doesn't auto-restyle.** The deterministic code renderer takes no
  fix instructions — FEEDBACK findings **surface** to the presenter, who resolves them by
  editing `draft.md`, which re-fires the preview on the changed slides.

Its per-phase config is the `preview` column of [`../render-modes.md`](../render-modes.md) —
the single source of truth; this spec does not restate it.
