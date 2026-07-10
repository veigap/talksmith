# Render modes — the per-format effort matrix (single source of truth)

This file is the **one authoritative definition of how each render format behaves** —
`strict`, `free-form`, and `preview`: which render substrate, which audits, which
critique action, cycle cap, and deliverable, per phase.

- **The config** (which action each format runs per phase) is the **matrix** below.
- **The design/quality bar** the FEEDBACK action walks — the CONTENT / AESTHETIC /
  DISTRIBUTION / LAYOUT-CONFORMANCE practices — lives in its own file,
  [`slide-design.md`](slide-design.md). This file only names the *categories*; the
  practices themselves are there.
- **The slide-template catalog** every mode classifies against at GENERATE (and the
  critique checks against at FEEDBACK) is [`slide-templates.md`](slide-templates.md) —
  the shared home for *which template a slide is, when it applies, and the format it must
  take* (cards, not bullets). GENERATE picks + renders the template; FEEDBACK reviews the
  slide against that template's format.
- **The generic visualization floor** — universal good-design principles + the hard
  "must-never-happen" defects (text/image overlap, off-slide bleed, illegible contrast,
  distorted images) — is [`visual-guidance.md`](visual-guidance.md). Every GENERATE honors
  it; every FEEDBACK treats a hard-invariant violation as blocking. `slide-design.md`
  implements it as per-slide checks and must not contradict it.

> **Do not duplicate this config.** Every other doc (SKILL.md, README.md, the per-style
> `pptx-prompt.md` specs, orchestrator.md) **references** this matrix; none restates it.
> Restating per-format config across files is exactly what produced the drift this repo
> kept fixing (preview-CONTROL, the 3–13 range, the phantom free-form "§6"). To change a
> format, edit its cell here — one place.

## Per-format effort matrix — THE single source of truth

**This matrix is the one authoritative definition of what each render format does per
phase. Every other doc (SKILL.md, README.md, the per-style specs, orchestrator.md) must
*reference* it, never restate it — restating it is what caused the drift this file
exists to end.** Rows are the render phases; columns are the formats; each cell names an
**action** defined in *Action definitions* below (which say *how* the action is
performed). To change a format's behavior, edit its cell here — one place.

| Phase / effort | `strict` | `free-form` | `preview` |
|---|---|---|---|
| **GENERATE** (render) | `native-render` | `native-render` | `wireframe-render` |
| **CONTROL** (deterministic audits) | `audit-full` | `audit-floor` | `audit-none` |
| **FEEDBACK** (multimodal critique) | `walk-all` | `no-critique` | `walk-design` |
| **REGENERATE** (on findings) | `auto-regenerate` | — (n/a) | `surface` |
| **Cycle cap** | 3 | — (single pass, no critique) | 2 |
| **Scope** | whole deck | whole deck | per-slide, changed-only |
| **Deliverable** | `output/final.strict.pptx` (+ canonical copy) | `output/final.free-form.pptx` (+ canonical copy) | numbered `output/draft-preview/slide-NN.png` |
| **Needs Cowork?** | yes (native `pptx` skill) | yes (native `pptx` skill) | no (Pillow only) |

## Action definitions — *how* each action is performed

Each action is defined once and reused across formats via the matrix above.

Every GENERATE action first **classifies each slide against the shared catalog**
[`slide-templates.md`](slide-templates.md) (its *Classification procedure*) and renders
the matched template's *Format*, falling back to the mode default when nothing matches.
The universal invariant — labeled enumerations are cards/panels, never plain bullets —
holds in all three.
- `native-render` — author the deck with the official `skill://antropic-skills:/pptx`, starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`), per that style's `pptx-prompt.md`. Classifies each slide against `slide-templates.md` and emits the matched template via the style's §-recipes (strict additionally runs the `audit_layout_fit.py` gate; free-form logs its pick to `.layout-log.md`). Consumes the `convert.py` intermediate (never re-parses `final.md`). Cowork-only. Full contract: [`SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Render flow*.
- `wireframe-render` — [`build_preview.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/build_preview.py) is **template-aware**: it classifies each slide (`_classify`, same catalog signals) and draws that template's shape — concept-breakdown/process/figures as cards (never bullets), content+image split, code block, statement, image-grid — falling back to a plain title+body flow. Draws each changed slide directly to a numbered PNG (Pillow); no `.pptx`, no `.pdf`, no native skill. ASCII → PNG by code (`render_ascii.py`); only changed slides re-render (content-addressed cache; bump `preview_plan.RENDER_VERSION` on recipe changes). Cowork-independent.

**CONTROL** (all deterministic Python audits; a non-zero exit ends the phase)
- `audit-full` — OOXML invariants + `audit_block_coverage.py` + `audit_aspect_ratios.py` + `audit_cover_fidelity.py` + **`audit_notes_coverage.py`** + **`audit_palette_fonts.py`** + **`audit_layout_fit.py`**. The last two enforce the strict template (layout-conformance) and are strict-only; the rest are the shared floor.
- `audit-floor` — OOXML invariants + `audit_block_coverage.py` + `audit_aspect_ratios.py` + `audit_cover_fidelity.py` + `audit_notes_coverage.py`. The shared floor; no palette/fonts, no layout-fit. `audit_notes_coverage.py` fails the build if any `### Notes` block lands in an empty notes pane (notes are load-bearing and template-independent).
- `audit-none` — no audits run: the format produces no `.pptx`, and every deterministic audit parses a rendered deck. `block-coverage`'s guarantee (every source block becomes a slide element) instead holds **by construction** (`build_preview.py` renders every slide unit).

**FEEDBACK** (multimodal walk of slide pixels against the practices in [`slide-design.md`](slide-design.md))
- `walk-all` — walk **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE**, applying the strict elaborations in `strict/pptx-prompt.md` §20. TEMPLATE reviews each slide against its classified template's *Format* in [`slide-templates.md`](slide-templates.md).
- `walk-design` — walk **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION** (never layout-conformance — the code wireframe has no strict base-template, but it *does* realize catalog templates, so TEMPLATE is walked).
- `no-critique` — no automated critique. The renderer designs freely and the **presenter reviews after delivery** (the `slide-design.md` practices are a handy self-review checklist for that human pass).

**REGENERATE** (disposition of FEEDBACK findings)
- `auto-regenerate` — the skill composes per-slide edit instructions and re-renders the touched slides, up to the cycle cap; objective defects are fixed, editorial-judgement calls get `defer because <reason>` and surface in the closing report.
- `surface` — findings are **surfaced** to the presenter, not auto-fixed: the deterministic wireframe takes no fix instructions, so the presenter resolves them by editing `draft.md` (which re-fires the preview on the changed slides). Objective content/structure findings are what the presenter acts on during Review anyway; aesthetic/distribution findings are informational and are truly fixed on the Step-8 render.

The **walk discipline**, **aesthetic note**, and **closing-report / declare-clean** contract that any FEEDBACK action follows live in [`slide-design.md`](slide-design.md).

**To change a format:** edit its cell in the matrix above. **To change the quality bar** (add/refine a practice): edit [`slide-design.md`](slide-design.md) — every format that walks that category picks it up.
