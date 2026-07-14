# Render modes — the per-format effort matrix (single source of truth)

This file is the **one authoritative definition of how each render format behaves** —
`pptx-strict`, `pptx-free-form`, and `html-strict`: which render substrate, which audits, which
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

| Phase / effort | `pptx-strict` | `pptx-free-form` | `html-strict` |
|---|---|---|---|
| **GENERATE** (render) | `native-render` | `native-render` | `html-render` |
| **CONTROL** (deterministic audits) | `audit-full` | `audit-floor` | `audit-none` |
| **FEEDBACK** (multimodal critique) | `walk-all` | `no-critique` | `no-critique` |
| **REGENERATE** (on findings) | `auto-regenerate` | — (n/a) | — (n/a) |
| **Cycle cap** | 3 | — (single pass) | — (single pass) |
| **Scope** | whole deck | whole deck | whole deck |
| **Deliverable** | `output/final.pptx-strict.pptx` (+ canonical) | `output/final.pptx-free-form.pptx` (+ canonical) | `output/html/index.html` (+ `.icons/`) |
| **Needs Cowork?** | yes (native `pptx` skill) | yes (native `pptx` skill) | no (HTML by code) |

**`html-strict` is the code-rendered deck** ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)) — a styled **HTML / [Reveal.js](https://revealjs.com/)** deck (real cards, per-concept Material icons, callout boxes, code surfaces; icons via `icon_fetch.py`, inlined; cover slide, present mode, slide overview, speaker notes with `s`, transitions, PDF export via `?print-pdf`). It has **two sources, one renderer and one output** (`output/html/index.html`): while the talk is being built it renders the **in-progress `draft.md`** — auto-fired after the first complete draft and kept in sync on every review (`--draft`), giving the presenter a live styled view; at Step 8 it renders **`final.md`** as the shareable deliverable. Deterministic render — the styled layer *always* renders, unlike the native `.pptx` render which follows prose and can drop it. Classification + information-breakdown are done by an **LLM that fills `slide-model.json`** ([`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)); `build_html` renders that model mechanically via the per-type Jinja templates (`templates/html/*.j2`), mapping fields to markup. (The in-progress view *is* `html-strict` on the draft model.)

## Action definitions — *how* each action is performed

Each action is defined once and reused across formats via the matrix above.

Every GENERATE action first **classifies each slide against the shared catalog**
[`slide-templates.md`](slide-templates.md) (its *Classification procedure*) and renders
the matched template's *Format*, falling back to the mode default when nothing matches.
The universal invariant — labeled enumerations are cards/panels, never plain bullets —
holds in all three. Each slide's chosen `template` (and its decomposed fields) lives in the shared
`slide-model.json` ([`../../schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)),
the FILL-step output that every mode renders from.
- `native-render` — author the deck with the official `skill://antropic-skills:/pptx`, starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`), per that style's `pptx-prompt.md`. Authors each slide from its `slide-model.json` fields — the `template` is already chosen (strict additionally runs the `audits/layout_fit.py` gate). Never re-parses `final.md`. Cowork-only. Full contract: [`SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md) → *Render flow*.
- `html-render` — [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py) renders a **styled HTML / Reveal.js** deck from `slide-model.json`: `html_style.render_model_slide` maps each slide's fields onto its per-type Jinja template (`templates/html/*.j2`) in the strict palette + **IBM Plex** fonts — cards, per-concept Material Symbols icons (catalog-matched, fetched by `icon_fetch.py`, recoloured, inlined), callout boxes, code surfaces, numbered strips — with the cover synthesized from the `deck` object. Slides render inside a vendored+inlined **Reveal.js** shell: navigation, deck-to-window scaling, overview (`Esc`), transitions, full screen (`F`), **speaker notes** (`s`), **PDF export** (`?print-pdf`); the only custom code is a per-slide content-fit. SVG images inline, PNG/JPG as data-URIs. Deterministic (the styled layer always renders); no `.pptx`, no native skill, Cowork-independent (needs `jinja2`). Renders the draft model (`--draft`) or final model → `output/html/index.html`.

**CONTROL** (all deterministic Python audits; a non-zero exit ends the phase)
- `audit-full` — OOXML invariants + `audits/block_coverage.py` + `audits/aspect_ratios.py` + `audits/cover_fidelity.py` + **`audits/notes_coverage.py`** + **`audits/palette_fonts.py`** + **`audits/layout_fit.py`** + **`audits/icon_coverage.py`**. The last three enforce the strict template (layout-conformance) and are strict-only; the rest are the shared floor. **`audits/icon_coverage.py`** fails the build when a concept-breakdown or callout slide rendered **zero** icons — closing the gap where a render silently skips the §17 icon-fetch step and ships naked cards (no other audit looked at icons, so it passed clean).
- `audit-floor` — OOXML invariants + `audits/block_coverage.py` + `audits/aspect_ratios.py` + `audits/cover_fidelity.py` + `audits/notes_coverage.py`. The shared floor; no palette/fonts, no layout-fit. `audits/notes_coverage.py` fails the build if any `### Notes` block lands in an empty notes pane (notes are load-bearing and template-independent).
- `audit-none` — no audits run: the format produces no `.pptx`, and every deterministic audit parses a rendered deck. `block-coverage`'s guarantee (every source block becomes a slide element) instead holds **by construction** (`build_html.py` renders every slide unit).

**FEEDBACK** (multimodal walk of slide pixels against the practices in [`slide-design.md`](slide-design.md))
- `walk-all` — walk **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE**, applying the strict elaborations in `pptx-strict/pptx-prompt.md` §20. TEMPLATE reviews each slide against its classified template's *Format* in [`slide-templates.md`](slide-templates.md).
- `no-critique` — no automated critique. The renderer produces the deck and the **presenter reviews after delivery** (the `slide-design.md` practices are a handy self-review checklist for that human pass). Both `pptx-free-form` and `html-strict` use this — html-strict is a single-pass GENERATE with no feedback loop.

**REGENERATE** (disposition of FEEDBACK findings)
- `auto-regenerate` — the skill composes per-slide edit instructions and re-renders the touched slides, up to the cycle cap; objective defects are fixed, editorial-judgement calls get `defer because <reason>` and surface in the closing report.
- `surface` — findings are **surfaced** to the presenter, not auto-fixed: the deterministic HTML renderer takes no fix instructions, so the presenter resolves them by editing `draft.md` (which re-fires the html-strict render on the changed slides). Objective content/structure findings are what the presenter acts on during Review anyway; aesthetic/distribution findings are informational and are truly fixed on the Step-8 render.

The **walk discipline**, **aesthetic note**, and **closing-report / declare-clean** contract that any FEEDBACK action follows live in [`slide-design.md`](slide-design.md).

**To change a format:** edit its cell in the matrix above. **To change the quality bar** (add/refine a practice): edit [`slide-design.md`](slide-design.md) — every format that walks that category picks it up.
