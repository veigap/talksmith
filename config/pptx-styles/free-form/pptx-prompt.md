# PPTX style: free-form

Free-form is **almost-no spec**: the cover slide is contractually fixed (§2), the core practices below are non-negotiable, and everything else — style, fonts, layout, colors, type scale, icon idiom, table treatment — is the renderer's call, based on its own design judgment of what serves the content.

For the alternative spec-driven style see [`../strict/pptx-prompt.md`](../strict/pptx-prompt.md); for the style-selection mechanism see [`../README.md`](../README.md).

> **Starting a new deck?** Open [`base-template.pptx`](base-template.pptx) — a 1-slide cover-only foundation. Substitute the four §2 cover placeholders on slide 1. From slide 2 onward you design.

> **EMU primer.** 1 inch = 914400 EMU; 1 point = 12700 EMU; font `sz` is in hundredths of a point. Slide size is `9144000 × 5143500` EMU (`10.00 × 5.625` inches; 16:9).

---

## 1. Core practices (non-negotiable)

These are not style rules — they are correctness rules. They hold regardless of design choices.

- **Open `base-template.pptx` as the working file.** In python-pptx terms: `Presentation(<base_template_path>)`, never `Presentation()` from scratch. Scratch-built decks fail Keynote import even with valid OOXML.
- **Every block in `final.md` becomes a shape on the rendered slide.** No content dropping to fit a design. Audited at CONTROL by [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_block_coverage.py).
- **Every `### Notes` block lands verbatim in the corresponding slide's notes pane.** Never on the slide body.
- **Aspect ratio preserved on every image** (no non-uniform scaling). Audited at CONTROL by [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_aspect_ratios.py).
- **OOXML invariants hold** per `../strict/pptx-prompt.md` §19.4 (style-agnostic structural rules — dangling rels, `[Content_Types].xml` ordering, etc.).
- **Honor the shared design bar *at GENERATE*.** Free-form designs *from* the guidance, not around it — its freedom is the *visual execution*, not permission to skip the design bar. As the deck is built, apply:
  - the **generic visualization floor** [`../visual-guidance.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/visual-guidance.md) — its **hard invariants** (no text/image overlap, no off-slide bleed, no truncation, no image distortion, legible contrast, above the ~30 pt floor, inside the safe area) *and* its generic **principles** (one clear hierarchy, alignment to a grid, structural whitespace, signal-over-noise, structure over bullets);
  - the matched **template's *Format*** from [`../slide-templates.md`](../slide-templates.md) (§3) — including the `concept-breakdown` per-concept icon and balanced card content (`DISTRIBUTION-09`);
  - the **CONTENT / TEMPLATE / AESTHETIC / DISTRIBUTION** practices in [`../slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md).
  The **only** design bar free-form does *not* honor is the strict-only **LAYOUT-CONFORMANCE** (fixed palette/fonts, section pill, base-template pixel-equivalence) — free-form picks its own palette, type, and layout idiom to realize the above.
- **Single pass, no critique loop.** Free-form is GENERATE → CONTROL → done: it *applies* the design bar above while building, but there is **no** automated FEEDBACK/REGENERATE pass that re-checks it — the **presenter reviews the deck after delivery** (the `../slide-design.md` practices double as that human checklist). Automated critique lives in `strict`; the throwaway `preview` runs its own light loop.

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

## 3. From slide 2 onward — classify against the catalog, then design

After the cover, the renderer is the designer — but not from a blank slate. **Read each
`## <H2>` slide's content and classify it against the shared template catalog**
[`../slide-templates.md`](../slide-templates.md) (its *Classification procedure* + each
template's *Match*). When a template matches, **render that template following its
*Format*** — the same templates strict and preview use. When nothing matches, **design
freely** (the catalog's `fallback`).

Free-form's freedom is in the **execution**, not the taxonomy: the catalog fixes *what
shape* the content takes (a labeled set is cards, not bullets; an ordered sequence is a
process; a big claim is a `statement`) and free-form chooses the fonts, colours, palette,
spacing, and icon idiom that realize it. The one hard rule the catalog carries into every
mode — **the universal invariant: labeled enumerations are cards/panels, never plain
bullets** — holds here too. Render each slide to its matched template's *Format* and to the
shared design bar (§1: the `visual-guidance.md` floor + the `slide-design.md` practices) —
free-form has **no** automated critique that re-checks this afterward (single pass, §4), so
honoring it *while building* is what makes the deck good; the presenter reviews after.

### 3.1 Template-decision log

Write the standard **template-decision log** to `talks/<Talk>/output/final.free-form.template-log.md`
(same `final.<style>` convention as the deck, side by side with it) — one entry per slide
naming the **catalog template id** it realized (or `fallback`), the signals that drove the
choice, what was ruled out, and any flags. Schema:
[`../slide-templates.md`](../slide-templates.md) → *Template decision log*. It is the render's
audit trail and what the critique reads to know each slide's intended template. (This replaces
the older `.layout-log.md`.)

### 3.2 Icons — optional

Free-form has no branded icon catalog and no icon requirement. Use icons or not, as the design warrants. If you do use them, keep **one consistent icon style** across the deck — that is an `AESTHETIC-11` (image/icon treatment consistency) concern the critique walks, not a conformance rule.

---

## 4. Render flow — single pass

Free-form is **GENERATE → CONTROL, one pass, no critique iterations.** Full contract: [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md) → *Render flow — branches by style*.

| Phase | What runs |
|---|---|
| **GENERATE** | Cover (§2) byte-equivalent from `base-template.pptx`; slides 2+ built fresh per §3 — **applying the shared design bar as it builds** (§1: the `visual-guidance.md` floor, the matched template's *Format*, the `slide-design.md` practices). Writes `output/final.free-form.template-log.md` (§3.1) + slide previews to `output/.critique/slide-NN.png`. |
| **CONTROL** | Shared-floor audits only: OOXML invariants, [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_block_coverage.py), [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_aspect_ratios.py), cover-fidelity. **No palette/font audit, no layout-fit audit** — those enforce the strict template (layout-conformance) and don't apply here. All audits 0 → done. Any non-zero → surface `unresolved: <audit_name>` and stop; **no auto-fix** — the presenter decides whether to re-trigger. |

**No FEEDBACK phase, no REGENERATE phase. The presenter is the reviewer.** The CONTENT + AESTHETIC + DISTRIBUTION practices in [`../slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) make a handy self-review checklist for that human pass, but the skill does not walk them automatically for free-form. (The automated per-slide critique loop lives in `strict`; the throwaway `preview` runs its own light version.)
