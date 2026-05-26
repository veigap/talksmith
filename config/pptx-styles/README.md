# PPTX styles

Talksmith renders PPTX in one of several **styles**. Each style is a self-contained spec + asset set under its own subdirectory here, designed to evolve independently without introducing regressions in sibling styles.

## Available styles

| Style | Subdirectory | Spec | Starting deck | When to pick |
|---|---|---|---|---|
| **strict** | [`strict/`](strict/) | [`strict/pptx-prompt.md`](strict/pptx-prompt.md) | [`strict/base-template.pptx`](strict/base-template.pptx) — 15-slide foundation (cover + agenda + 12 layout-reference + agenda-divider example) | Course series where visual consistency across classes matters; deck will be skimmed asynchronously; presenter wants the workflow to make the visual decisions; most content fits §13's taxonomy. |
| **free-form** | [`free-form/`](free-form/) | [`free-form/pptx-prompt.md`](free-form/pptx-prompt.md) | [`free-form/base-template.pptx`](free-form/base-template.pptx) — 1-slide cover-only foundation | One-off keynote or pitch; live-presented with the speaker driving every transition; presenter has design instincts they want the renderer to follow; meaningful fraction of slides have content that doesn't fit a fixed taxonomy. |

The two styles are not better/worse — they trade *predictability* for *expressive range*. The same working directory can carry Talks in both styles.

## Per-Talk style selection

Each Talk declares its style via the `style:` field in `draft.md` frontmatter:

```yaml
---
presentation: …
subtitle: …
style: strict        # or: free-form
…
---
```

Default when absent: `strict` (the safer, more constrained mode). The Editor asks the presenter at Step 1 (Frame) per [CLAUDE.md](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) → *Step 1*, proposing 2 candidates derived from the Step-1 briefing's signals (deck-purpose, audience, delivery context).

## What the styles share

Four rules hold in **every** style — the floor. A render that violates any of these is a render failure regardless of which spec is active. The per-style `pptx-prompt.md` files duplicate the floor sections (canvas / palette / fonts / cover recipe) by design — each spec is self-contained so it can evolve without coupling to siblings — but the floor *content* is identical and audited identically:

1. **Cover slide (§4 in each spec)** — slide 1 is byte-equivalent to the style's `base-template.pptx` slide 1 with only the four placeholder substitutions applied. Audited at CONTROL via cover-fidelity check.
2. **Color palette (§2 in each spec)** — every `<a:srgbClr val="…"/>` in the rendered deck is in the §2 palette. Audited at CONTROL by [`audit_palette_fonts.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/audit_palette_fonts.py).
3. **Font palette (§3 in each spec)** — every `<a:latin typeface="…"/>` is Roboto / Roboto Mono Medium / Consolas. Audited by the same script.
4. **White background (§1 in each spec)** — every slide carries a pure-white `<p:bg>` solid fill.

The **render cycle itself** (GENERATE → CONTROL → FEEDBACK → REGENERATE, 3-cycle cap) is style-agnostic and lives in [`CLAUDE.md`](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) → *Render cycle*. What differs per style is the **content** of CONTROL (which audits fire) and the **content** of FEEDBACK (which rubric the orchestrator walks):

| Phase | strict | free-form |
|---|---|---|
| GENERATE | per `strict/pptx-prompt.md` §19.3 7-stage workflow + §15.5 emit-rules | per `free-form/pptx-prompt.md` §5 layout dispatch (slide-by-slide judgment) |
| CONTROL | aspect-ratio + layout-fit + block-coverage + palette/fonts + cover-fidelity + OOXML | aspect-ratio + block-coverage + palette/fonts + cover-fidelity + OOXML (layout-fit skipped — no spec-predicted layout to compare) |
| FEEDBACK | 12-practice rubric ([`CLAUDE.md`](${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md) → *Post-render visual review*) | 8-practice free-form design rubric (`free-form/pptx-prompt.md` §6) |
| REGENERATE | re-render touched slides | same |

The generate-control-feedback-improve loop is **the constant**; the rules it loops against are what the `style:` field switches.

## Adding a new style

To add a third style (e.g. `minimal`, `editorial`, `dark-mode`):

1. `mkdir config/pptx-styles/<name>/`
2. Author `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/pptx-prompt.md` — self-contained spec including the four floor sections (canvas, palette, fonts, cover recipe). Copy from `strict/` or `free-form/` and modify.
3. Ship the starting deck `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<name>/base-template.pptx` honoring the floor (cover slide + palette + fonts + white bg).
4. Add a row to the *Available styles* table above.
5. Extend the `style:` enum in [`${CLAUDE_PLUGIN_ROOT}/schemas/draft.md`](${CLAUDE_PLUGIN_ROOT}/schemas/draft.md) to include `<name>`.
6. Update [`${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-pptx/SKILL.md) to branch on the new value (load the right spec, point at the right base-template, run the right rubric).

No other style's files need to change. That's the point of the split.

## Cross-refs from style-agnostic prose

Documents outside `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/` (CLAUDE.md, SKILL.md, the audit scripts, the schemas) reference style-specific spec sections by writing `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md §X` where `<style>` is resolved per the active Talk's `style:` field. The style-agnostic audit scripts (aspect-ratio, block-coverage, palette-fonts) take the active style's `pptx-prompt.md` path as an input where needed; the layout-fit audit is `strict`-only and lives unchanged in the skill.
