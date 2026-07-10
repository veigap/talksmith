# PPTX styles

Talksmith renders PPTX in one of several **styles**. Each style is a self-contained spec + asset set under its own subdirectory here, designed to evolve independently without introducing regressions in sibling styles.

## Available styles

| Style | Subdirectory | Spec | Starting deck | When to pick |
|---|---|---|---|---|
| **strict** | [`strict/`](strict/) | [`strict/pptx-prompt.md`](strict/pptx-prompt.md) | [`strict/base-template.pptx`](strict/base-template.pptx) — 15-slide foundation (cover + agenda + 12 layout-reference + agenda-divider example) | Course series where visual consistency across classes matters; deck will be skimmed asynchronously; presenter wants the workflow to make the visual decisions; most content fits §13's taxonomy. |
| **free-form** | [`free-form/`](free-form/) | [`free-form/pptx-prompt.md`](free-form/pptx-prompt.md) | [`free-form/base-template.pptx`](free-form/base-template.pptx) — 1-slide cover-only foundation | One-off keynote or pitch; live-presented with the speaker driving every transition; presenter has design instincts they want the renderer to follow; meaningful fraction of slides have content that doesn't fit a fixed taxonomy. |

The two styles are not better/worse — they trade *predictability* for *expressive range*. The same subject repo can carry Talks in both styles.

## Per-render style selection

Style is **not** a Talk attribute — it's a **render-time parameter** chosen fresh on every PPTX generation. `draft.md` and `final.md` carry no `style:` field; the same content can be rendered in either style at any time.

The orchestrator asks the presenter at **every Step 8 entry** per [`${CLAUDE_PLUGIN_ROOT}/orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 8 step 1* and passes the answer to `md-to-pptx` as an invocation parameter. The ask is mandatory and there is **no default** — if the presenter is unsure, the orchestrator re-asks with framing of what each style implies for *this* Talk. The skill refuses to run without an explicit `style:` value (see [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Style resolution*).

A second Step-8 run on the same Talk can pick a different style with no migration. Renders are **isolated by filename suffix** — `output/final.strict.pptx` and `output/final.free-form.pptx` coexist so the two styles can be compared side by side — and the most recent render is also copied to the canonical `output/final.pptx` (what the reverse pipeline reads).

## What the styles share

**The shared floor — holds in every style** (strict, free-form, preview). A render that violates any of these fails regardless of spec:

1. **Cover slide** — slide 1 is byte-equivalent to the style's `base-template.pptx` slide 1 with only the four placeholder substitutions applied. Audited by [`audit_cover_fidelity.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_cover_fidelity.py).
2. **Block coverage** — every source block becomes a shape; no silent drops. Audited by [`audit_block_coverage.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_block_coverage.py).
3. **Image aspect ratio** — no non-uniform scaling. Audited by [`audit_aspect_ratios.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_aspect_ratios.py).
4. **OOXML invariants** hold (`strict/pptx-prompt.md` §19.4).
5. **Keynote-safe system fonts** — every `<a:latin>` resolves to a font on the import target (correctness rule; see SKILL.md → *System fonts only*).

**Strict-only (LAYOUT-CONFORMANCE, not floor):** the strict §2 colour palette + §3 font-set (audited by [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py)), white background, section pill, branded icons, and the §15.5 emit-rules layout (audited by [`audit_layout_fit.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_layout_fit.py)). Free-form and preview render their own layouts from slide 2 on and are **not** judged against these — their slides 2+ have no fixed palette/font/background. (This resolves the earlier three-way inconsistency where palette/fonts was called both a universal floor and strict-only.)

**Two things are centralized, not duplicated per spec** — a deliberate exception to the "each spec is self-contained" convention: the deterministic `audit_*.py` scripts, and the **per-format render matrix** [`render-modes.md`](render-modes.md). That matrix is the single source of truth for *how each format behaves per phase* (render substrate, CONTROL audits, FEEDBACK categories, cycle cap, deliverable). (Duplicating this config per spec is exactly what produced the phantom free-form "§6 8-practice list" and the other drifts.)

The render **flow** is owned by [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Render flow* (the *mechanics* of each phase). **What each format does per phase — the config — is the matrix in [`render-modes.md`](render-modes.md) → *Per-format effort matrix*; do not restate it here.** In brief: strict authors a native-`pptx` deck and runs the full audit suite + a 3-cycle critique across all four categories; free-form authors a native-`pptx` deck in a single pass (floor audits, no automated critique — the presenter reviews); preview draws a code wireframe (no deck, no audits) and runs its own ≤2-cycle content/aesthetic/distribution critique whose findings surface.

## Adding a new style

To add a third style (e.g. `minimal`, `editorial`, `dark-mode`):

1. `mkdir config/pptx-styles/<name>/`
2. Author `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/pptx-prompt.md` — self-contained spec including the four floor sections (canvas, palette, fonts, cover recipe). Copy from `strict/` or `free-form/` and modify.
3. Ship the starting deck `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/base-template.pptx` honoring the floor (cover slide + palette + fonts + white bg).
4. Add a row to the *Available styles* table above.
5. Extend the Step-8 ask in [`${CLAUDE_PLUGIN_ROOT}/orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 8 step 1* to offer `<name>` as a candidate, and the allowed-values list in [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Style resolution*.
6. Update [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) to branch on the new value (load the right spec, point at the right base-template).
7. Add a row for the new mode to the **selection matrix** in [`render-modes.md`](render-modes.md) — its category selection (which of CONTENT / AESTHETIC / DISTRIBUTION / LAYOUT-CONFORMANCE it walks) and cycle cap. Do **not** copy a rubric into the new spec; the mode inherits the shared catalog.

No other style's files need to change. That's the point of the split.

## Cross-refs from style-agnostic prose

Documents outside `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/` (`orchestrator.md`, SKILL.md, the audit scripts) reference style-specific spec sections by writing `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md §X` where `<style>` is resolved per the current render's `style:` invocation parameter. The shared-floor audit scripts (aspect-ratio, block-coverage, cover-fidelity) run in every mode; **palette-fonts and layout-fit are `strict`-only** (they enforce the strict template). The critique rubric is the shared [`render-modes.md`](render-modes.md), referenced by every mode.
