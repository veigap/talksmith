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

| Phase / effort | `strict` | `free-form` | `preview` | `html` |
|---|---|---|---|---|
| **GENERATE** (render) | `native-render` | `native-render` | `html-render` | `html-render` |
| **CONTROL** (deterministic audits) | `audit-full` | `audit-floor` | `audit-none` | `audit-none` |
| **FEEDBACK** (multimodal critique) | `walk-all` | `no-critique` | `walk-design` | `walk-design` |
| **REGENERATE** (on findings) | `auto-regenerate` | — (n/a) | `surface` | `surface` |
| **Cycle cap** | 3 | — (single pass) | 2 | 2 |
| **Scope** | whole deck | whole deck | whole deck (from `draft.md`) | whole deck (from `final.md`) |
| **Deliverable** | `output/final.strict.pptx` (+ canonical) | `output/final.free-form.pptx` (+ canonical) | `output/draft-preview/preview.html` | `output/html/index.html` (+ `.icons/`) |
| **Needs Cowork?** | yes (native `pptx` skill) | yes (native `pptx` skill) | no (HTML by code) | no (HTML by code) |

**`preview` and `html` are the same renderer** ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)) — a code-generated **styled HTML** deck (real cards, per-concept Material icons, callout boxes, code surfaces; icons via `icon_fetch.py`, inlined). `preview` renders `draft.md` for a fast throwaway look; `html` renders `final.md` as a shareable, presentable **deliverable** (cover slide, arrow-key / full-screen present mode). Both are deterministic — the styled layer *always* renders, unlike the native `.pptx` render which follows prose and can drop it. (The earlier Pillow wireframe substrate is superseded; `build_preview.py` remains only as the shared `_parse_unit`/`_classify` helpers `build_html` imports.)

## Action definitions — *how* each action is performed

Each action is defined once and reused across formats via the matrix above.

Every GENERATE action first **classifies each slide against the shared catalog**
[`slide-templates.md`](slide-templates.md) (its *Classification procedure*) and renders
the matched template's *Format*, falling back to the mode default when nothing matches.
The universal invariant — labeled enumerations are cards/panels, never plain bullets —
holds in all three. Every GENERATE also writes a **template-decision log** beside its
output — `output/final.<style>.template-log.md` for the native styles (side by side with
`final.<style>.pptx`), `output/draft-preview/template-log.md` for preview — recording the
template chosen per slide and why (schema: [`slide-templates.md`](slide-templates.md) →
*Template decision log*).
- `native-render` — author the deck with the official `skill://antropic-skills:/pptx`, starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`), per that style's `pptx-prompt.md`. Classifies each slide against `slide-templates.md` and emits the matched template via the style's §-recipes (strict additionally runs the `audit_layout_fit.py` gate; free-form logs its pick to `.layout-log.md`). Consumes the `convert.py` intermediate (never re-parses `final.md`). Cowork-only. Full contract: [`SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md) → *Render flow*.
- `html-render` — [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py) renders a **styled static HTML** deck (shared tokens/components in `html_style.py`): classifies each slide (`_classify`), emits the matched template's real styling — cards, per-concept Material Symbols icons (fetched by name via `icon_fetch.py`, recoloured, inlined), callout boxes, code surfaces, card strips — and prepends a §4 cover slide from the frontmatter. A fixed header (pill + title) sits over a content region that scales to fit 16:9; the page has a full-screen present mode (arrow keys). SVG images embed inline, PNG/JPG as data-URIs. An optional `<!-- template: X -->` comment forces a template. Deterministic (the styled layer always renders); no `.pptx`, no native skill, Cowork-independent. `preview` renders `draft.md` → `output/draft-preview/preview.html`; `html` renders `final.md` → `output/html/index.html`.

**CONTROL** (all deterministic Python audits; a non-zero exit ends the phase)
- `audit-full` — OOXML invariants + `audit_block_coverage.py` + `audit_aspect_ratios.py` + `audit_cover_fidelity.py` + **`audit_notes_coverage.py`** + **`audit_palette_fonts.py`** + **`audit_layout_fit.py`** + **`audit_icon_coverage.py`**. The last three enforce the strict template (layout-conformance) and are strict-only; the rest are the shared floor. **`audit_icon_coverage.py`** fails the build when a concept-breakdown or callout slide rendered **zero** icons — closing the gap where a render silently skips the §17 icon-fetch step and ships naked cards (no other audit looked at icons, so it passed clean).
- `audit-floor` — OOXML invariants + `audit_block_coverage.py` + `audit_aspect_ratios.py` + `audit_cover_fidelity.py` + `audit_notes_coverage.py`. The shared floor; no palette/fonts, no layout-fit. `audit_notes_coverage.py` fails the build if any `### Notes` block lands in an empty notes pane (notes are load-bearing and template-independent).
- `audit-none` — no audits run: the format produces no `.pptx`, and every deterministic audit parses a rendered deck. `block-coverage`'s guarantee (every source block becomes a slide element) instead holds **by construction** (`build_html.py` renders every slide unit).

**FEEDBACK** (multimodal walk of slide pixels against the practices in [`slide-design.md`](slide-design.md))
- `walk-all` — walk **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE**, applying the strict elaborations in `strict/pptx-prompt.md` §20. TEMPLATE reviews each slide against its classified template's *Format* in [`slide-templates.md`](slide-templates.md).
- `walk-design` — walk **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION** (never layout-conformance — the HTML render has no strict base-template, but it *does* realize catalog templates, so TEMPLATE is walked).
- `no-critique` — no automated critique. The renderer designs freely and the **presenter reviews after delivery** (the `slide-design.md` practices are a handy self-review checklist for that human pass).

**REGENERATE** (disposition of FEEDBACK findings)
- `auto-regenerate` — the skill composes per-slide edit instructions and re-renders the touched slides, up to the cycle cap; objective defects are fixed, editorial-judgement calls get `defer because <reason>` and surface in the closing report.
- `surface` — findings are **surfaced** to the presenter, not auto-fixed: the deterministic HTML renderer takes no fix instructions, so the presenter resolves them by editing `draft.md` (which re-fires the preview on the changed slides). Objective content/structure findings are what the presenter acts on during Review anyway; aesthetic/distribution findings are informational and are truly fixed on the Step-8 render.

The **walk discipline**, **aesthetic note**, and **closing-report / declare-clean** contract that any FEEDBACK action follows live in [`slide-design.md`](slide-design.md).

**To change a format:** edit its cell in the matrix above. **To change the quality bar** (add/refine a practice): edit [`slide-design.md`](slide-design.md) — every format that walks that category picks it up.
