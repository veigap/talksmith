# PPTX style: free-form

Free-form is **almost-no spec**: the cover slide is contractually fixed (§2), the core practices below are non-negotiable, and everything else — style, fonts, layout, colors, type scale, icon idiom, table treatment — is the renderer's call, based on its own design judgment of what serves the content.

For the alternative spec-driven style see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md); for the style-selection mechanism see [`../README.md`](../README.md).

> **Starting a new deck?** Open [`base-template.pptx`](base-template.pptx) — a 1-slide cover-only foundation. Substitute the four §2 cover placeholders on slide 1. From slide 2 onward you design.

> **EMU primer.** 1 inch = 914400 EMU; 1 point = 12700 EMU; font `sz` is in hundredths of a point. Slide size is `9144000 × 5143500` EMU (`10.00 × 5.625` inches; 16:9).

---

## 1. Core practices (non-negotiable)

These are not style rules — they are correctness rules. They hold regardless of design choices.

- **Open `base-template.pptx` as the working file.** In python-pptx terms: `Presentation(<base_template_path>)`, never `Presentation()` from scratch. Scratch-built decks fail Keynote import even with valid OOXML.
- **Every block in `final.md` becomes a shape on the rendered slide.** No content dropping to fit a design. Audited at CONTROL by [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py).
- **Every `### Notes` block lands verbatim in the corresponding slide's notes pane.** Never on the slide body.
- **Aspect ratio preserved on every image** (no non-uniform scaling). Audited at CONTROL by [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_aspect_ratios.py).
- **OOXML invariants hold** per `../strict/pptx-prompt.md` §19.4 (style-agnostic structural rules — dangling rels, `[Content_Types].xml` ordering, etc.).
- **Critique loop for content, look & arrangement.** Free-form runs GENERATE → CONTROL → FEEDBACK → REGENERATE (≤ 2 cycles), critiquing **CONTENT + AESTHETIC + DISTRIBUTION** from the shared [`../critique-rubric.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/critique-rubric.md). It does **not** walk LAYOUT-CONFORMANCE — the renderer designs freely; the critique judges whether the design *works* (is it legible, balanced, well-distributed?), never whether it matches a template. See §4 (flow) + §5 (selection). This is not a single-pass render.

---

## 2. Cover slide — contractually fixed *(the only mandatory layout)*

The cover is the deck's identity slide and is reproduced **byte-for-byte structurally**, identical to the strict-style cover. Only the *content* of the four shapes changes per Talk; positions, sizes, fonts, colors, z-order, and the institution logo are fixed. Audited at CONTROL by the cover-fidelity check.

Four shapes, in z-order:

| # | Role | EMU off (x,y) | EMU ext (w,h) | Style | Content source |
|---|---|---|---|---|---|
| 1 | **Cover title** (`p:sp`, `rect`, no fill, no border) | `(496119, 536823)` | `(8151763, 1948458)` | `algn="l"`, `lnSpc=104%`. Single run: `sz="4050"` (40.5pt), Helvetica Bold, `#1F1E1E`. | `presentation:` from `final.md` frontmatter (Subject from `profile.md`) |
| 2 | **Class name** (`p:sp`, `rect`, no fill) | `(496119, 2677269)` | `(6216923, 235297)` | `wrap="none"`, `algn="l"`. Single run: `sz="1450"` (14.5pt), Helvetica Bold, `#1F1E1E`. | `class:` from `final.md` frontmatter (per-Talk, **required** — collected at Step 4) |
| 3 | **Author + date block** (`p:sp`, `rect`, no fill) | `(496119, 3219748)` | `(3295799, 560933)` | Two paragraphs, `algn="l"`, `lnSpc=123%`, `spcAft=900`. Each run: `sz="1150"` (11.5pt), **Helvetica**, `#3B3535`. | Paragraph 1: `Autor: <presenter>` (localize "Autor:" per `Presentation language`). Paragraph 2: `Última Modificación: <Month, YYYY>` from `date:` (localize prefix). |
| 4 | **Institution logo** (`p:pic`) | `(7183562, 3248546)` | `(1469008, 1214065)` | PNG, `ppt/media/image-1-1.png`. `noChangeAspect="1"`. | `ppt/media/image-1-1.png` preserved verbatim. |

The cover's specific font choices (Helvetica Bold / Helvetica) are part of the fixed recipe — they exist because the cover is contractually identical across both styles, not because free-form prescribes a typography palette. Slides 2 onward have no font / size / color rules.

---

## 3. From slide 2 onward — renderer decides

After the cover, the renderer is the designer. Read each `## <H2>` slide's content, decide what serves it best, emit. The spec does not prescribe layout, fonts, sizes, colors, palette, icon idiom, or table treatment — the renderer judges by its own criteria. What the renderer builds is then judged by the FEEDBACK critique (§5) on **whether it works**, not on template conformance.

### 3.1 Layout log

Log each choice to `talks/<Talk>/output/.layout-log.md` (one entry per slide, naming what you built + one-line rationale). The log is the render's audit trail.

### 3.2 Icons — optional

Free-form has no branded icon catalog and no icon requirement. Use icons or not, as the design warrants. If you do use them, keep **one consistent icon style** across the deck — that is an `AESTHETIC-11` (image/icon treatment consistency) concern the critique walks, not a conformance rule.

---

## 4. Render flow — critique loop (≤ 2 cycles)

Free-form is **GENERATE → CONTROL → FEEDBACK → REGENERATE**, up to **2 cycles**. Full contract: [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Render flow — branches by style*.

| Phase | What runs |
|---|---|
| **GENERATE** | Cover (§2) byte-equivalent from `base-template.pptx`; slides 2+ built fresh per §3. Writes `.layout-log.md` + slide previews to `output/.critique/slide-NN.png`. |
| **CONTROL** | Shared-floor audits only: OOXML invariants, [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py), [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_aspect_ratios.py), cover-fidelity. **No palette/font audit, no layout-fit audit** — those enforce the strict template (layout-conformance) and don't apply here. Any non-zero → REGENERATE (no visual review on a broken render). |
| **FEEDBACK** | Walk **CONTENT + AESTHETIC + DISTRIBUTION** from [`../critique-rubric.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/critique-rubric.md) on every slide PNG. See §5. |
| **REGENERATE** | Re-render the touched slides from the FEEDBACK handoff; cycle counter increments. |

## 5. Post-render review — category selection

Free-form walks **CONTENT + AESTHETIC + DISTRIBUTION** from the shared catalog; it does **not** walk **LAYOUT-CONFORMANCE** (there is no fixed template to conform to). Walk discipline, the aesthetic note, and the declare-clean/closing-report contract are the shared sections of [`../critique-rubric.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/critique-rubric.md).

### 5.1 Disposition — what auto-fixes vs what defers

Free-form auto-regenerates like strict, but biases toward the presenter for taste (free-form's ethos is that the presenter is the final judge of *style*):
- **Fix this iteration (REGENERATE):** objective, unambiguous defects — text overflow/off-slide (`AESTHETIC-01`), raw emoji (`CONTENT-01`), distorted image (`AESTHETIC-04`), misaligned columns / uneven gutters (`DISTRIBUTION-01/02`).
- **Defer because \<reason\> (surface in the closing report):** editorial-judgement calls — which of two balanced compositions reads better, palette tone, rhythm. The presenter decides.

Cap 2 cycles. After the cap, surviving items surface as `unresolved:` / `deferred:` per the catalog's closing-report format.
