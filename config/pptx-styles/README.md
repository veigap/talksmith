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

A second Step-8 run on the same Talk can pick a different style with no migration; the previous render in `output/final.pptx` is simply overwritten.

## What the styles share

Four rules hold in **every** style — the floor. A render that violates any of these is a render failure regardless of which spec is active. The per-style `pptx-prompt.md` files duplicate the floor sections (canvas / palette / fonts / cover recipe) by design — each spec is self-contained so it can evolve without coupling to siblings — but the floor *content* is identical and audited identically:

1. **Cover slide (§4 in each spec)** — slide 1 is byte-equivalent to the style's `base-template.pptx` slide 1 with only the four placeholder substitutions applied. Audited at CONTROL via cover-fidelity check.
2. **Color palette (§2 in each spec)** — every `<a:srgbClr val="…"/>` in the rendered deck is in the §2 palette. Audited at CONTROL by [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py).
3. **Font palette (§3 in each spec)** — every `<a:latin typeface="…"/>` is Roboto / Roboto Mono Medium / Consolas. Audited by the same script.
4. **White background (§1 in each spec)** — every slide carries a pure-white `<p:bg>` solid fill.

The render **flow** is owned by [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Render flow* and **branches by style** (strict iterates, free-form is single-pass). What differs per style:

| Phase | strict | free-form |
|---|---|---|
| GENERATE | per `strict/pptx-prompt.md` §19.3 7-stage workflow + §15.5 emit-rules | per `free-form/pptx-prompt.md` §5 layout dispatch (slide-by-slide judgment) |
| CONTROL | aspect-ratio + layout-fit + block-coverage + palette/fonts + cover-fidelity + OOXML | aspect-ratio + block-coverage + palette/fonts + cover-fidelity + OOXML (layout-fit skipped — no spec-predicted layout to compare) |
| FEEDBACK | 12-practice rubric ([`strict/pptx-prompt.md` §20](strict/pptx-prompt.md)) | *(no FEEDBACK — single-pass; the 8-practice list in `free-form/pptx-prompt.md` §6 is a self-review checklist the presenter uses, not a critique loop)* |
| REGENERATE | re-render touched slides, up to 3 cycles total | *(no REGENERATE)* |

## Adding a new style

To add a third style (e.g. `minimal`, `editorial`, `dark-mode`):

1. `mkdir config/pptx-styles/<name>/`
2. Author `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/pptx-prompt.md` — self-contained spec including the four floor sections (canvas, palette, fonts, cover recipe). Copy from `strict/` or `free-form/` and modify.
3. Ship the starting deck `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/base-template.pptx` honoring the floor (cover slide + palette + fonts + white bg).
4. Add a row to the *Available styles* table above.
5. Extend the Step-8 ask in [`${CLAUDE_PLUGIN_ROOT}/orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 8 step 1* to offer `<name>` as a candidate, and the allowed-values list in [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) → *Style resolution*.
6. Update [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) to branch on the new value (load the right spec, point at the right base-template, run the right rubric).

No other style's files need to change. That's the point of the split.

## Cross-refs from style-agnostic prose

Documents outside `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/` (`orchestrator.md`, SKILL.md, the audit scripts) reference style-specific spec sections by writing `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md §X` where `<style>` is resolved per the current render's `style:` invocation parameter. The style-agnostic audit scripts (aspect-ratio, block-coverage, palette-fonts) take the active style's `pptx-prompt.md` path as an input where needed; the layout-fit audit is `strict`-only and lives unchanged in the skill.
