---
name: talksmith:md-to-deck
description: Convert a Talk's cleaned `final.md` into a PowerPoint (.pptx) deck by delegating all .pptx authoring to Anthropic's official `pptx` skill at `skill://antropic-skills:/pptx`. **Cowork-only** — requires that skill in the session registry. Optional Step 8 of the Presenter Agent workflow, invoked after Step 6 (Polish) has rendered SVGs and produced `final.md`. Consumes images already on disk under `talks/<Talk>/images/`; does not author the deck itself. **Branches by the `style:` invocation parameter** (`strict` | `free-form` | `preview`, **mandatory — no default**) — the orchestrator asks the presenter at every Step 8 entry and passes the answer in; `final.md` itself is style-agnostic. The skill fails render-blocking if `style:` is absent. Each style resolves to a self-contained spec under [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/) per [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md); `strict`/`free-form` add a `base-template.pptx`. Output: `talks/<Talk>/output/final.pptx`. **The `preview` and `html` styles** render a **styled HTML deck by code** (no native skill, Cowork-independent) via the committed [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py): `html` renders `final.md` as a shareable deliverable at `output/html/index.html`; `preview` (Step-5.5, `style: preview` — the legacy `preview: true` is an accepted alias) renders a fast, throwaway look at a pre-Polish `draft.md` at `output/draft-preview/preview.html`, then runs **its own light critique loop** (CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION, ≤2 cycles, findings surface). Because they render in HTML, the styled layer (cards, per-concept icons, callouts, code surfaces) is **always present**.
---

# md-to-deck — Render `final.md` to PowerPoint

**This skill is a thin orchestrator. All `.pptx` authoring must go through Anthropic's official `pptx` skill at [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx)** — which authors the deck **programmatically with `python-pptx`**, starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`; see §1 of the free-form spec and the *base template is mandatory* rule below). So "delegate to the pptx skill" means: **drive that skill's `python-pptx` workflow from the base template + visual spec.** Writing `python-pptx` this way is not just allowed, it is the mechanism.

What is **forbidden** is *bypassing* that path: authoring from a blank `Presentation()` from scratch, reimplementing the theme yourself, or using another tool (`pandoc`, Marp, hand-written XML) — all abandoned because they fail Keynote import (see *Why Cowork-only*). A python generator that starts from `base-template.pptx`, substitutes the cover, and builds each slide per the visual spec is the **correct** free-form/strict render, not the anti-pattern.

Pre-process `final.md`, then invoke `skill://antropic-skills:/pptx` with the intermediate file, the image paths, **the base template, and the visual spec**. If that skill is not in the current session's registry (i.e. the session is not running inside Claude Cowork), stop and tell the presenter to run this step inside Cowork. No CLI fallback — see *Why Cowork-only* at the bottom.

**Style resolution — `style:` invocation parameter (mandatory, no default).** Every render begins by reading the `style:` parameter the orchestrator passed in at invocation. Allowed values are `strict` and `free-form` per [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md). The orchestrator asks the presenter at every Step 8 entry (see [`${CLAUDE_PLUGIN_ROOT}/orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → Step 8 step 1) and must get an explicit answer before dispatching this skill. `final.md` and `draft.md` carry no `style:` field — the same Talk content can be rendered in either style at any time. If the invocation arrives with no `style:` parameter, the skill **fails render-blocking** with the error message at Process step 0 below; it does not guess or default. The resolved style determines two paths the rest of this skill uses:

```
<spec_path>          = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md
<base_template_path> = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx
```

Both paths are **mandatory inputs** to the render. References below that say "the spec" or "the base template" without qualification mean **the style-resolved path** — not strict's by default.

**The base template is mandatory and non-negotiable.** Every render starts from a working copy of `<base_template_path>`, not from a blank deck. For `strict`: this is a 15-slide foundation (cover + agenda + 12 layout-reference slides + 1 section-divider example) and the renderer substitutes placeholders, deletes the layout-reference zone (slides 3–15), and inserts generated content per the recipes in `<spec_path>`. For `free-form`: this is a 1-slide cover-only foundation; the renderer substitutes the cover's four §2 placeholders, then builds every other slide fresh per the style's §3 (renderer decides). Decks rendered from scratch — even if they "look similar" — are a render failure in either style.

**Single responsibility.** This skill **only** prepares the inputs and invokes `skill://antropic-skills:/pptx`. ASCII → SVG conversion is the Illustrator role's job, performed in Step 6 (Polish) before this skill ever runs. `final.md` arrives already cleaned (image refs inlined, `Presenter feedback` stripped) and every referenced image already lives under `talks/<Talk>/images/`.

**Reads `final.md`, never `draft.md` — except in `preview: true` mode.** In a normal render the working file (`draft.md`) still carries `Presenter feedback` blocks and raw ASCII fences and is not a valid PPTX input; the skill's CLI takes the path to `final.md` as a positional argument, and passing `draft.md` produces malformed output (Presenter feedback bullets leaking into slide bodies, ASCII fences rendered as code blocks). The **one exception** is the Step-5.5 draft preview (`preview: true`), which reads `draft.md` *by design* and pre-processes it with `convert.py --draft` — see *`preview: true` — Step-5.5 draft preview* below. Preview output is isolated under `output/draft-preview/` and is never the deliverable.

## When to use

After Step 6 (Polish) completes and the presenter picks **Render to PowerPoint** from the terminal branch. Optional — many presenters stop at the outline.

## Prerequisites

| Prereq | What to check | If missing |
|---|---|---|
| [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) in session registry | Skill list includes the `pptx` entry | Stop. Tell presenter to run this step inside Cowork. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `final.md` | Exists; no `Presenter feedback` fields; ASCII blocks replaced by `![...](images/...)` refs | Stop. Polish hasn't run — return to Step 6. |
| Pre-rendered local images | `talks/<Talk>/images/<file>` exists on disk for every **local** image ref in `final.md` (i.e. every `![...](images/...)` reference). Remote URLs (`http://`, `https://`) are checked separately — see below. | Stop. Dispatch `illustrator` to render missing SVGs, or stop and ask the presenter to drop a missing non-SVG asset into `images/`. |
| Keynote-safe image extensions in `final.md` | Every `![alt](path)` reference in `final.md` uses `.png` or `.jpg`/`.jpeg`. **Forbidden: `.svg`, `.webp`, `.avif`, `.heic`** — Keynote refuses to embed WebP/AVIF/HEIC and refuses to render SVG as embedded media; the .pptx ships but every offending slide loses its image on Keynote import (and behavior is inconsistent across other consumers). This is the Step 6 (b) image-consolidation contract — see [`${CLAUDE_PLUGIN_ROOT}/agents/editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md) → *(b) Consolidate image refs*. | Stop. Surface as a render-blocking error and list every offending ref (path + slide). Tell the orchestrator to re-dispatch the appropriate Step-6 role: any `.svg` ref (whether illustrator-produced or external corpus SVG) is **the Illustrator's** responsibility — re-dispatch Illustrator to produce the missing `.png` companion, then re-dispatch the Editor's Step-6 (b) ref-rewrite pass. `.webp`/`.avif`/`.heic` refs are **the Editor's** responsibility — re-dispatch Editor only (it rasterizes those formats inline). Never proceed — Keynote-incompatible refs ship a broken deck. |
| Remote image refs handled | `final.md` contains no `![...](http(s)://...)` references — they survived Step 6 Polish unchanged, but `skill://antropic-skills:/pptx`'s behavior on remote URLs is implementation-defined and not guaranteed. | Stop and ask the presenter to either (a) download the asset into `images/` and rewrite the ref to `images/<file>`, or (b) explicitly accept the risk that the slide may ship without that image. Never silently ship a deck where a remote image was dropped. |
| Base template | `<base_template_path>` = `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx` exists (style resolved at Process step 0 from the `style:` invocation parameter; presenter override optional). Mandatory starting deck. | Stop and ask. |
| Visual spec | `<spec_path>` = `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md` exists. Section catalog varies by style — strict §1–§20, free-form §1–§4. Per-format render config is the matrix in [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md); the design-quality practices its FEEDBACK action walks are in [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) (strict + preview walk it; free-form is single-pass). | Stop and ask — the spec is the rendering contract. |
| Icon library *(strict only)* | [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/base-template.pptx`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/base-template.pptx) `ppt/media/icon-*.svg` (15 branded line-art icons in `#DA1B2E`) — see [`strict/pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §17. Free-form makes icons optional (per `free-form/pptx-prompt.md` §3.2). | Stop and ask — without the icons the strict no-emoji rule cannot be enforced. |

## Inputs

- **Active `Talk` path** — absolute.
- **`config/profile.md` content** — pass the global presenter profile (the cover placeholders `{{PRESENTATION_TITLE}}` and `{{PRESENTER}}` substitute from `Subject` and `Presenter`; agenda placeholder language follows `Presentation language`).
- **Base template** — resolved as `<base_template_path>` from the `style:` invocation parameter (`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx`). Override only if the presenter explicitly passes a different path. The legacy [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/template.pptx`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/template.pptx) (53-slide reference deck) is **not** a valid override — it is the source the strict spec was distilled from, not a rendering input.
- **Visual spec** — resolved as `<spec_path>` from the `style:` invocation parameter (`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md`). The renderer treats it as the rendering contract for any slide that isn't a direct copy of a base-template slide.
- **Operating guide for the renderer** — [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §19. Self-contained: required reading order (§19.2), 7-stage workflow (§19.3), output contract + OOXML invariants (§19.4), verification (§19.5), consolidated anti-patterns (§19.6), and a navigation index (§19.7). SKILL.md is a thin orchestrator; **§19 is the operating manual**. Pass `pptx-prompt.md` verbatim to the native skill (or rendering subagent) as instructions context.

## Output

```
talks/<Talk>/
├── draft.md                 # working file (Steps 1–5) — read-only here
├── final.md                 # source for this skill (cleaned by Polish)
├── images/                  # populated by illustrator + editor (Step 6)
│   ├── s1-1.svg
│   └── ...
└── output/
    ├── final.pptx                    # canonical deliverable — a copy of the most recent render
    ├── final.strict.pptx             # per-mode render, persists for comparison
    ├── final.strict.template-log.md  # per-mode template-decision log (side by side w/ its .pptx)
    ├── final.free-form.pptx          # per-mode render, persists for comparison
    ├── final.free-form.template-log.md
    ├── final.<style>.intermediate.md # per-mode transient pre-processed file (convert.py)
    ├── .critique/                    # critique-only slide previews (git-ignored)
    │   ├── strict/slide-NN.png
    │   └── free-form/slide-NN.png
    ├── html/                         # html deliverable style — index.html + template-log.md (build_html.py)
    └── draft-preview/                # preview mode — preview.html, fully isolated (see preview subsection)
```

**Per-mode output isolation (so renders don't overwrite each other).** Each render writes a **suffixed** deck `output/final.<style>.pptx` (its intermediate `output/final.<style>.intermediate.md`, its critique PNGs under `output/.critique/<style>/`, and its **template-decision log `output/final.<style>.template-log.md`** — same `final.<style>` convention, side by side with the deck), so a strict and a free-form render of the same Talk coexist and can be compared side by side. After a successful render the skill also **copies** the suffixed deck to the canonical `output/final.pptx` — the single deliverable that the reverse pipeline and the Phase-2 as-generated baseline read. Last render wins the canonical slot; the suffixed files persist. The **template-decision log** records, per slide, which catalog template was chosen and why (schema: [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) → *Template decision log*) — the strict render fills it from the §15.6 pre-emit audit (chosen template, emitted §-recipe, `audit_layout_fit` pass/mismatch); free-form from its per-slide layout choices. Preview is separate — it never touches any of these, writing its own `template-log.md` under `output/draft-preview/`.

## Process

0. **Preview is a style, not an exception.** `preview` is one of the render styles
   ([`preview/pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/preview/pptx-prompt.md)); it differs only in **substrate** — a styled HTML deck rendered by code, not a native `.pptx`. When the resolved style is **`preview`** (the orchestrator's Step-5.5 passes `style: preview`; the legacy `preview: true` invocation is accepted as an alias for it), the render is [`build_html.py --talk talks/<Talk> --draft`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py) (no native `pptx` skill, no base-template, no CONTROL audits) followed by its **own light critique loop** (CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION, ≤2 cycles, per-slide, findings surface) — see *preview — Step-5.5 draft preview* in *Render flow*. All other steps below (the native-`pptx` pipeline) apply to the `strict` / `free-form` styles.

0. **Resolve style.** Read the `style:` value from the invocation parameters (the orchestrator's Step 8 step 1 asked the presenter and passed it in). **The parameter is mandatory — no default.** If the value is **absent or empty**, fail render-blocking with `[pptx 0/8] FAILED: style: invocation parameter missing — the orchestrator must ask the presenter and pass the answer (see ${CLAUDE_PLUGIN_ROOT}/orchestrator.md Step 8 step 1).` Do not proceed; the orchestrator's job is to re-ask the presenter, not the skill's job to guess. If the value is present but not a directory under `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/`, fail render-blocking per *Style resolution failed* in *Failure modes*. Cache `<spec_path> = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md` and (for the native-`pptx` styles only) `<base_template_path> = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx`. Verify `<spec_path>` exists for every style; verify `<base_template_path>` exists for `strict` / `free-form` (the **`preview`** style has a code substrate and **no base-template** — skip that check). If a required file is missing, the style enum has drifted from disk — surface as a render-blocking error naming the missing file. Emit `[pptx 0/8] Style resolved: <style> (spec=<spec_path>).`
1. Verify all prerequisites (table above). Stop on any failure.
2. **Pre-process `final.md` with [`convert.py`](convert.py)** — a CLI-safe, dependency-free Python script that emits the Markdown shape `skill://antropic-skills:/pptx` consumes:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/convert.py \
     talks/<Talk>/final.md \
     -o talks/<Talk>/output/final.<style>.intermediate.md
   ```

   **Per-mode paths.** Everywhere below, `output/final.pptx`, `output/final.intermediate.md`, and `output/.critique/` resolve to the **per-style** forms `output/final.<style>.pptx`, `output/final.<style>.intermediate.md`, and `output/.critique/<style>/` (see *Output* → per-mode isolation). The final render step also copies the per-style deck to the canonical `output/final.pptx`.

   The script performs these transformations (specified in its docstring; see [`convert.py`](convert.py) for the canonical contract):
   - Drops YAML frontmatter, HTML comments (including `<!-- ascii-source: ... -->` blocks), and the sections `# Thesis`, `# Open questions`, `# Cut material`.
   - Strips the numeric / legacy prefix from H1 / H2 headings: `# 1. Foundations` → `# Foundations`, `## 2. Why X` → `## Why X`. Legacy forms `# Section N:` / `## Slide N:` / `# N —` / `## N —` accepted.
   - For each H2 slide, processes its H3 fields: drops the `### Content` label (keeps body), drops `### Sources` entirely (presenter-internal), renames `### Speaker notes` → `### Notes` (keeps body), defensively drops any lingering `### Presenter feedback`.
   - Preserves `![alt](images/...)` image refs verbatim. Preserves `---` rules.
   - Collapses runs of 3+ blank lines to 1.

   Output Markdown shape — one H1 per section divider, one H2 per content slide, `### Notes` for speaker notes, inline image refs. This is what `skill://antropic-skills:/pptx` receives.

   > **Hard rule — the renderer authors from this intermediate ONLY; never re-parse `final.md`.** `convert.py` has already resolved every field: `### Content` → body (label dropped), `### Sources` → **dropped**, `### Speaker notes` → `### Notes` (notes pane), and the working-meta bold labels `**Goal of this section:**` / `**Narrative arc:**` / `**Presenter feedback:**` → **dropped**. `final.md` still *contains* all of those raw (it is the editable source + audit trail). A renderer that parses `final.md` directly will look for `### Notes` (only in the intermediate) and miss it, and will spill `### Sources`, speaker notes, and the section **goal** into the slide body — the exact class of bug this pre-processing exists to prevent. **Parse the intermediate; treat `final.md` as untouchable source.**

2.5. **Classify each slide against the template catalog (all modes).** Walk each H2 in the intermediate file and classify it against the shared catalog [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) → *Classification procedure* + each template's *Match* — pick the single best-fit template (or `fallback`), honoring the universal invariant (labeled enumerations → cards, never plain bullets). Every mode classifies; how the pick is recorded and checked differs:
   - **strict** — additionally applies the §15.6 pre-emit decision audit per `<spec_path>` §15.6 and emits one `[pptx audit N/M]` line per slide showing the chosen template and the inputs that led there (strict's §15.5 table binds each catalog id to its §-recipe). Stop and surface per §15.6.4 on an unresolved ambiguity, an unmapped emoji at a slot the chosen layout has, or bullet-shape drift. The pick is re-checked deterministically at CONTROL by `audit_layout_fit.py`.
   - **free-form** — records the chosen template id (or `fallback`) in the per-slide layout-log sidecar (`<spec_path>` §3.1 → `.layout-log.md`); no deterministic gate.
   - **preview / html** — classification runs inside `build_html.py` (`_classify`), which selects the render template; nothing to emit here.

3. **Render** by invoking [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx). The invocation follows the **base-template 7-stage workflow** described in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §19.3 — the native skill is the executor, this skill is the recipe-bearer. Pass:
   - the intermediate file at `output/final.intermediate.md`,
   - the image paths under `talks/<Talk>/images/` (the intermediate already references them — resolved relative to the intermediate's parent),
   - the **base template** at [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/base-template.pptx`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/base-template.pptx) (or explicit override) — opened as a **working copy**, not as a theme reference,
   - the **icon library** rooted at the base template's `ppt/media/icon-*.svg` (15 branded line-art SVGs, see [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §17),
   - the **visual spec** [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) (the layout recipes the skill emits against).

   The invocation follows the **7-stage workflow in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §19.3** verbatim — open base-template as working copy → cover substitution (§4) → agenda substitution (§5) → discard slides 3–15 → build content slides (§15 + §6–§9 + §13) → section dividers (§5.6) → backgrounds (§1) → speaker notes. All substantive rules (placeholder edge cases, slide-count formula, OOXML invariants, callout pink-vs-blue, no native tables, emoji→icon swap, palette, fonts, corner radius) live in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) and are **not duplicated here**. The skill's sole §19 obligation is to **pass the spec to the native renderer** and verify the output against §19.4 + §19.5. When this skill and the spec disagree, the spec wins.

   Acceptance bar: open the rendered `final.pptx` next to `base-template.pptx` — slides 1–2 must be pixel-equivalent modulo placeholder text. Author-from-scratch with the native skill's default theme = render failure.
4. Verify `talks/<Talk>/output/final.<style>.pptx` exists and is non-empty, then **copy it to the canonical `talks/<Talk>/output/final.pptx`** (the deliverable the reverse pipeline reads). The suffixed per-style deck persists for comparison.

   **When `style == strict`, snapshot the as-generated geometry baseline** for the learning loop — the deck before any human touches it:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/learn_patterns.py inventory \
     talks/<Talk>/output/final.strict.pptx \
     -o talks/<Talk>/output/final.generated.geometry.json
   ```

   This per-shape geometry snapshot survives in-place editing of the deck and is the baseline [`talksmith:pptx-learn`](${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/SKILL.md) diffs the human-edited deck against. Skip for free-form/preview (nothing to learn against).
5. **Verify visual fidelity.** Spot-check that the rendered deck matches the reference template's look (theme, fonts, layouts). If it doesn't, treat as a failure — see *Failure modes*.
6. **Audit `<p:pic>` aspect ratios.** Run [`audit_aspect_ratios.py`](audit_aspect_ratios.py) against the rendered deck:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_aspect_ratios.py \
     talks/<Talk>/output/final.pptx
   ```

   The script walks every `<p:pic>` in every slide, resolves the source asset via the slide's rels file, reads its intrinsic aspect ratio (SVG `viewBox`, PNG/JPG header), and compares to the rendered `cx:cy`. Default tolerance: 1%. Non-zero exit = render failure — surface the FAIL lines verbatim and re-render. This catches the class of bug where a placeholder's slot is wider/taller than the asset and the renderer fills it by non-uniform scaling (the §12 rule in prose; this is its enforcement). The audit also surfaces missing `<a:picLocks noChangeAspect="1"/>` as warnings; warnings do not fail the render. Audit failures are not a §19.6 visual-spec violation per se — they are a structural picture-sizing bug — but they are surfaced and treated identically (stop, repair, re-verify).

   **Then run [`audit_palette_fonts.py`](audit_palette_fonts.py) — only when `style == strict`.** This enforces the strict template's §2 palette + §3.1 font set (a LAYOUT-CONFORMANCE concern — see [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md)). **Skip for `free-form` and `preview`** — their slides 2+ deliberately have no fixed palette/font, so this audit does not apply (for free-form the fixed cover is still checked by `audit_cover_fidelity.py`; preview produces no deck, so no deck-parsing audit runs there at all). For strict:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_palette_fonts.py \
     talks/<Talk>/output/final.pptx
   ```

   Walks every `<a:srgbClr>` and `<a:latin>` in every slide. Off-palette colors and off-fonts surface as `[off-palette]` / `[off-font]` lines naming the slide and the offending value. Non-zero exit = render failure. Catches the class of bug where an Office theme accent leaks in from a copy-paste, a text run forgets its `<a:latin>` and falls back to a system font, or a renderer emits a near-relative of a palette color (e.g. `#FFB3B4` instead of `#F7BBC1`).

   Then run [`audit_cover_fidelity.py`](audit_cover_fidelity.py) to confirm slide 1 of `final.pptx` is byte-equivalent to slide 1 of the style's `<base_template_path>` (modulo only the four cover substitution slots — title, subtitle, author+date, logo image basename; defined in strict §4.3 and free-form §2):

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_cover_fidelity.py \
     talks/<Talk>/output/final.pptx \
     <base_template_path>
   ```

   Extracts a structural fingerprint of every shape on slide 1 (geometry, prstGeom, fill, stroke, primary-run font + color + alignment, picture rels target) and compares against the base-template's. Diffs in any non-text-content field fail the audit. Catches subtle cover drift — title sized 38pt instead of 40.5pt, logo shifted 0.1 in, author block using Roboto Mono instead of Roboto, etc.

   **Then run [`audit_layout_fit.py`](audit_layout_fit.py) — only when `style == strict`.** When `style == free-form`, skip this audit entirely (free-form has no §15.5 emit-rules table to predict against). For strict:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_layout_fit.py \
     talks/<Talk>/final.md \
     talks/<Talk>/output/final.pptx
   ```

   The script reparses `final.md` per H2 (image count, code blocks, pipe-tables, labeled-bullet count, per-item body length, H3 group count, emoji prefixes) and applies the §15.5 + §15.6.1 decision tree to compute the **predicted** layout. It then parses `final.pptx` per slide and infers the **emitted** layout from shape composition. When predicted ≠ emitted, the audit fails with the source evidence, the emitted evidence, and a likely root cause (typically a §15.6.1 discriminator skip). Catches the class of regression where the §19.6 anti-pattern check passes but the substantive spec was bypassed by picking the plainer layout. Non-zero exit = render failure.

   **Then run [`audit_icon_coverage.py`](audit_icon_coverage.py) — only when `style == strict`.** For strict:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_icon_coverage.py \
     talks/<Talk>/final.md \
     talks/<Talk>/output/final.pptx
   ```

   Concept-breakdown cards (§7.2.1) and callouts (§8) each carry a small branded icon (Material Symbols, fetched by name via `icon_fetch.py` per §17). The render fetches + embeds those by following prose and can **silently skip it** — shipping naked cards while the layout log claims icons were used. This audit counts the icons a slide *should* have (one per concept card, one per callout) from `final.md`, counts the small (≤0.6 in) `<p:pic>` shapes actually emitted, and fails with `[icon-drop] slide N …` when a slide that calls for icons rendered **zero**. It closes the exact gap where a no-icon deck passed clean because the other six audits never look at icons. Non-zero exit = render failure — fetch the icons (§17.6) and re-render.

   Then run [`audit_block_coverage.py`](audit_block_coverage.py) to confirm every load-bearing block from `final.md` survived into the rendered deck:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_block_coverage.py \
     talks/<Talk>/final.md \
     talks/<Talk>/output/final.pptx
   ```

   The script parses `final.md` per H2 into block inventories (callouts, content images), parses `final.pptx` per slide into shape inventories (pink `#F7BBC1` + blue `#B8E6F5` callout roundRects, content `<p:pic>` excluding cover logo + section-pill icons), matches by H2 title text (ordinal matching breaks because section dividers shift counts), and reports any slide where source count > render count as `[block-drop] slide N "<H2>" — source has X, render has Y`. Non-zero exit = render failure. Catches the class of bug where the renderer's top-to-bottom layout runs out of room on a busy slide and silently skips the trailing block from emission — the visual rubric never asks "is every source block present," so a silent drop sails through. The audit runs **before** the orchestrator's visual review begins; any `[block-drop]` stops the cycle and routes to REGENERATE. Unmatched H2s (`[unmatched] line N "<H2>" — no rendered slide with matching title`) are also surfaced; they usually mean a title was rewritten between Polish and render, not a true drop, but the orchestrator confirms before proceeding.

   Then run [`audit_notes_coverage.py`](audit_notes_coverage.py) (shared floor — **strict and free-form**) to confirm speaker notes were not dropped:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audit_notes_coverage.py \
     talks/<Talk>/final.md \
     talks/<Talk>/output/final.pptx
   ```

   The script records which `final.md` H2 slides carry a non-empty `### Notes` block, reads each rendered slide's linked `notesSlide` part (excluding the slide-number placeholder), matches by H2 title, and reports any slide with source notes but an empty notes pane as `[notes-drop] slide N "<H2>" — source has notes, render notes pane empty`. Non-zero exit = render failure. Speaker notes are load-bearing (the prose the slide replaces) and **template-independent** — every template emits them — so a forgotten notes stage or a dropped slide's notes is a silent content loss the visual rubric can't see. Slides with no `### Notes` block are never flagged (no false positives).
7. **Render per-slide critique PNGs.** Rasterize every slide to `talks/<Talk>/output/.critique/slide-NN.png` (zero-padded 2-digit slide number, `01` … `NN`). These PNGs are critique-only — not referenced from `final.pptx`, not part of the deliverable — and exist so the FEEDBACK sub-agent can walk the shared critique rubric on actual pixels rather than slide-XML inspection (see [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) and *Render flow* above).

   Path priority (use the first that works):

   1. If [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) exposes a slide-to-image render endpoint, call it. The native skill is the most faithful source — it knows the deck's true layout post-render.
   2. Fallback: `libreoffice --headless --convert-to pdf <output_dir> talks/<Talk>/output/final.pptx`, then `pdftoppm -r 150 -png talks/<Talk>/output/final.pdf talks/<Talk>/output/.critique/slide` to produce one PNG per slide. Rename / pad to `slide-NN.png`. Requires `libreoffice` (`brew install --cask libreoffice`) and `poppler` (`brew install poppler`); document the dependency.

   If both paths fail, the deck is still valid — report `slide_previews: failed: <reason>` and continue. The orchestrator will surface this as `unresolved: slide_previews_failed` for the post-render review (visual critique can't run without pixels), but the `.pptx` itself is unaffected.

8. Report: `style: <strict|free-form|preview>`, slide count, image references resolved, `aspect_audit: <ok|N fail>`, `palette_fonts: <ok|N fail|skipped:non-strict>`, `cover_fidelity: <ok|N diff>`, `layout_fit: <ok|N mismatch|skipped:non-strict>`, `block_coverage: <ok|N drop>`, `slide_previews: <count|failed>`, any warnings surfaced by `skill://antropic-skills:/pptx`.

### Render flow — branches by style

The skill is invoked with a mandatory `style:` parameter (the orchestrator asks the presenter every Step 8 entry — never persisted to `final.md`). **The skill owns the entire render loop end-to-end** — including the visual critique iterations for `strict`. The orchestrator hands off, displays the progress checklist as stage events arrive, and reads the closing report. It does not know whether strict iterates internally or not.

> **Stream the phases — mandatory in every mode (preview, free-form, strict).** The render must surface its **processing phases as they happen** — the presenter sees the phase progress advance, never a multi-minute *"Multitasking…"* with no output. Two hard rules:
> 1. **Never run the whole render as one opaque, long-lived dispatch.** Structure it so a phase event reaches the presenter's chat at **every phase boundary** — after pre-process, after the deck is built, after CONTROL, after each FEEDBACK pass, after each REGENERATE — and the checklist item flips `[⟳]`→`[✓]` at that moment.
> 2. **Chunk the slow phases and report between chunks.** The FEEDBACK multimodal walk is the long pole (it reads every slide PNG). Do it in **batches** (e.g. 8–10 slides) and emit a progress line after each batch — *"Reviewing slides 10 of 29…"* — so the item visibly advances. Same for building many slides: emit *"Built 12 of 29…"*. **Any phase quiet for > 30 s must emit a heartbeat.** A silent stretch longer than that is a defect, not normal.
>
> This applies to preview (`build_html.py --draft` render → ≤2 critique cycles) and strict (build → CONTROL → ≤3 critique cycles) — the modes with a critique loop, which is the slowest phase and the one most prone to going silent, so batch-level progress matters most there. Free-form is single-pass (build → CONTROL), so it just streams its build + audit phases.

The skill is a Python pipeline + native `pptx` author + (for strict only) an internally-dispatched multimodal sub-agent that reads slide PNGs and walks the rubric. That sub-agent's invocation is an implementation detail of this skill; do not surface it to the orchestrator.

#### `style: strict` — multi-cycle critique loop *(skill-internal)*

Four named phases, up to **3 cycles total** (cycle 1 = initial build; 2–3 = review-and-edit budget). Every phase is owned by the skill; the orchestrator sees only stage events for the progress checklist.

| Phase | Tag | What runs | Exit |
|---|---|---|---|
| **GENERATE** | `[cycle N/3] GENERATE` | Cycle 1: full pipeline (preprocess → native `pptx` skill → write → rasterize previews). Cycles 2–3: re-render only the touched slides from the prior REGENERATE handoff. | `final.pptx` written, slide previews in `output/.critique/`. |
| **CONTROL** | `[cycle N/3] CONTROL` | Build-time audits: aspect ratios, block coverage, notes coverage, palette/fonts, cover fidelity, layout fit, OOXML invariants (§19.4 of `strict/pptx-prompt.md`). | All audits exit 0 → FEEDBACK. Any non-zero → straight to REGENERATE for this cycle (no visual review on a broken render). |
| **FEEDBACK** | `[cycle N/3] FEEDBACK` | Skill dispatches a multimodal sub-agent (via `Agent` tool) to walk the shared critique rubric [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) on every slide PNG (multimodal `Read` of rasterized pixels — XML inspection forbidden). **Strict selects all five categories — CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE** — applying the strict elaborations in `strict/pptx-prompt.md` §20. Each finding: `slide N · <catalog-id> · <description> → fix this iteration \| defer because <reason>`. **Strict runs autonomously** — no presenter prompts at any point. Editorial-judgement findings get `defer` and surface in the closing report. | List empty OR all entries `defer` → cycle done, exit loop. Any `fix this iteration` → REGENERATE. |
| **REGENERATE** | `[cycle N/3] REGENERATE` | Skill composes per-slide edit instructions from the FEEDBACK list and re-runs GENERATE on the touched-slide subset. Cycle counter increments. | Cycle N+1 starts. |

**Cycle cap counts only top-level rotations.** Build-time recoveries inside a single GENERATE (broken regex, leaked marker, undersized callout) don't consume cycle budget. After cycle 3, surviving defects surface as `unresolved: …` in the closing report.

#### `style: free-form` — single pass *(skill-internal)*

Two phases, one pass. **No FEEDBACK, no REGENERATE** — the renderer designs freely and the presenter reviews the deck after delivery.

| Phase | What runs | Exit |
|---|---|---|
| **GENERATE** | Full pipeline against [`pptx-styles/free-form/`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/free-form/) → `final.pptx` + `.layout-log.md` + slide previews. | Output written. |
| **CONTROL** | Shared-floor audits: OOXML invariants, block-coverage, aspect-ratio, cover-fidelity, notes-coverage. **No palette/fonts, no layout-fit** (strict-only). | All 0 → done. Any non-zero → closing report carries `unresolved: <audit_name>`. No auto-fix; presenter decides whether to re-trigger. |

The CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION practices in [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) are a self-review checklist for the presenter's human pass — the skill does **not** walk them for free-form. (Automated critique lives in strict; the throwaway preview runs its own.)

#### `preview: true` — Step-5.5 draft preview *(one committed script, code-rendered)*

An optional **fast, throwaway** **styled HTML deck** of a **pre-Polish `draft.md`** so the presenter can eyeball slide order, layout, and rough content *before* committing to Step 6 (Polish) + a real render. The orchestrator auto-fires it in the background when `draft.md` first completes and again when the Step-5 review changes it (see [`${CLAUDE_PLUGIN_ROOT}/orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 5.5 — Draft preview*).

**Run the committed renderer — never hand-roll one.** Preview is the same code renderer as the `html` deliverable style, [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py), invoked with `--draft`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py --talk talks/<Talk> --draft
```

It orchestrates the whole thing deterministically and reuses the sibling substrate: `convert.py --draft` (per-slide units, `**Presenter feedback:**`/`**Narrative arc:**` scaffolding stripped) → per-unit classification against the shared catalog (`_classify`, with `<!-- template: X -->` overrides) → **the matched template's real styling** via the shared `html_style` components (cards, per-concept Material Symbols icons, callout boxes, code surfaces), a fit-to-16:9 pass, and present mode → a **single self-contained styled HTML deck**, `output/draft-preview/preview.html`. **Do not write an ad-hoc render script** — that is the exact anti-pattern this file exists to prevent (mirrors the *Why Cowork-only* rule for the real deck).

Key properties:

| Aspect | Preview behavior |
|---|---|
| **No `.pptx`, no `.pdf`, no native skill** | The deck is rendered **directly to styled HTML by code**. Nothing authors a `.pptx`, nothing rasterizes a PDF. Because it renders in HTML, the **styled layer (cards, icons, callouts, code surfaces) is fully present** — the only thing deferred to a later `strict`/`free-form` render is the native `.pptx` itself. |
| **Cowork-independent** | Unlike Step 8, the preview needs no native `pptx` skill and no LibreOffice. It runs in any session, which is why it can auto-fire in the background. |
| **Input** | `talks/<Talk>/draft.md` (read-only). Raw ASCII fences and `Presenter feedback` are expected and handled — do **not** dispatch the Illustrator, do **not** stop on missing SVGs. |
| **Template-aware** | Every slide is classified against the shared catalog ([`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)) and rendered as its template (cards, never bullets), honouring [`visual-guidance.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/visual-guidance.md) and [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md). Writes the template-decision log to `output/draft-preview/template-log.md`. |
| **Critique — its own light loop** | After `build_html.py --draft` renders (GENERATE), preview runs its **own** FEEDBACK → REGENERATE loop, ≤ 2 cycles, walking **CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION** (the [`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md) practices) on the rendered `preview.html`. (Its config is the preview column of the [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md) matrix; independent of free-form, which is single-pass.) Two properties: **no CONTROL phase** (preview has no `.pptx`, so the deck-parsing audits can't run — block-coverage instead holds by construction, `build_html` renders every unit); and the deterministic code renderer takes no fix instructions, so REGENERATE does **not** autonomously restyle — FEEDBACK findings **surface** for the presenter, who resolves them via a `draft.md` edit → re-fire. |
| **Output (isolated)** | `talks/<Talk>/output/draft-preview/` — `preview.html` (the styled deck) and `template-log.md`. **Never** touches `output/final.pptx`, `output/html/`, or `output/.critique/`. |

Preview phase table (GENERATE = `build_html.py --draft`, then its own FEEDBACK/REGENERATE):

| Phase | Tag | What runs |
|---|---|---|
| **GENERATE** | `[preview]` / `[cycle N/2] GENERATE` | `build_html.py --draft` renders `draft.md` to the styled `preview.html`. |
| **CONTROL** | — | *None.* Preview produces no `.pptx`, so the deck-parsing audits can't run; block-coverage holds by construction (`build_html` renders every unit). |
| **FEEDBACK** | `[cycle N/2] FEEDBACK` | Multimodal walk of CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION on the rendered `preview.html`, per the shared rubric. Findings surface (see REGENERATE). |
| **REGENERATE** | `[cycle N/2] REGENERATE` | Re-render after the presenter edits `draft.md`; **surface** the FEEDBACK findings (the deterministic renderer takes no fix instructions, so no autonomous restyle). |

Degrades gracefully: a render error → the script says so and the orchestrator reports the preview is unavailable (never fatal — it's a convenience).

### Presenter-facing progress checklist

**A live checklist is mandatory in every render mode (strict, free-form, preview).** Rendering runs 30 s – 3 min; silence reads as a hang. The orchestrator **must** show a live, todo-list-style checklist on render entry and **update it in place** — flipping each item to `[⟳]` when its phase starts and `[✓]` the moment it completes — so the presenter always sees what is happening now and what is done. Never run a render with no visible progress. State markers: `[ ]` pending, `[⟳]` in progress, `[✓]` done, `[—]` skipped / not-applicable, `[✗]` failed.

The skill drives the checklist by emitting one bracketed stage line per phase (see *Progress reporting* below); the orchestrator consumes those lines and edits the checklist message in place (it never relays the raw tags — see the suppression rule). For any stage that runs > 30 s without advancing, the skill emits a heartbeat and the orchestrator surfaces a plain-language *"still working — N of M slides…"* line so the checklist item visibly breathes. The orchestrator owns the rendering; the skill owns *which items appear and when each ticks*.

**`style: strict` checklist** (5 items; *Reviewing slides* and *Applying fixes* update their cycle counter on each rotation):

```
Building your deck:
  [ ] Formatting source
  [ ] Building draft slides
  [ ] Reviewing slides (cycle N of 3)
  [ ] Applying fixes
  [ ] Final check
```

Item ↔ phase mapping (strict):

| Item | Ticks when |
|---|---|
| Formatting source | Skill emits `[pptx 2/8] Pre-processing done`. |
| Building draft slides | Skill emits `[pptx 4/8] final.pptx written` for cycle 1. |
| Reviewing slides (cycle N) | Orchestrator finishes walking the rubric on every slide PNG (FEEDBACK phase). |
| Applying fixes | Skill returns from REGENERATE-driven re-render, OR `[—] no fixes needed` if the cycle was clean. |
| Final check | Final cycle exits clean OR cycle 3 ends with surviving `unresolved: …` (marker `[✗]` if any). |

**`style: free-form` checklist** (3 items; single pass):

```
Building your deck:
  [ ] Formatting source
  [ ] Building slides
  [ ] Sanity check
```

Item ↔ phase mapping (free-form):

| Item | Ticks when |
|---|---|
| Formatting source | `[pptx 2/8] Pre-processing done`. |
| Building slides | `[pptx 4/8] final.pptx written`. |
| Sanity check | All CONTROL audits exit 0 (or `[✗]` on any non-zero with the audit name in the closing report). |

**`preview: true` checklist** (5 items; counts personalize — *"Rendering 3 changed slides (71 reused)"*):

```
Putting together a quick preview:
  [ ] Formatting draft
  [ ] Rendering N changed slides (M reused)
  [ ] Reviewing slides (cycle N of 2)
  [ ] Applying fixes
  [ ] Ready to view
```

Item ↔ phase mapping (preview):

| Item | Ticks when |
|---|---|
| Formatting draft | `[preview]` — `convert.py --draft` done (N slides from `draft.md`). |
| Rendering styled deck | `build_html.py --draft` finished rendering `draft.md` to `preview.html`. |
| Reviewing slides (cycle N) | FEEDBACK finishes walking CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION on the rendered `preview.html`. |
| Applying fixes | REGENERATE re-renders after a `draft.md` edit / surfaces findings, OR `[—] no fixes needed`. |
| Ready to view | `preview.html` on disk under `output/draft-preview/`; the presenter opens it (present mode: → / ← to advance, `F` full screen). |

### Progress reporting — internal log-only

PPTX render is a long-running multi-stage operation (30s–3 min). The skill emits **one bracketed log-line per stage** so the orchestrator can drive its presenter-facing progress checklist and so `memory.md` has a complete audit trail of the run. **These lines are log-only — the orchestrator never relays them to chat verbatim** (per [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) Step 8 → *Tag-suppression rule*). They drive checklist state and land in the closing report; the presenter sees the checklist + plain-language summaries, never the raw tags.

Every line below is **structured event output** for the orchestrator to consume, not chat content. Tag namespaces the skill owns: `[pptx`, `[cycle`, `[late-catch`, `[block-drop`, `[off-palette`, `[off-font]`, `[unmatched]`, `[skipped]`. If any of these strings reach chat verbatim it's a leak — see *Tag-suppression rule* in the orchestrator.

Step 8's render flow (single-pass for free-form, ≤ 3-cycle for strict; both defined above in *Render flow*). Cycle 1's 8 stages are tabled below; strict cycles 2+ collapse to one log-line per phase prefixed `[cycle N/3] GENERATE/CONTROL/FEEDBACK/REGENERATE`.

| Moment | Example line |
|---|---|
| Skill entry | `[pptx] Starting render for talks/<Talk>/final.md → output/final.pptx` |
| Prereqs verified | `[pptx 1/8] Prereqs OK — base-template loaded, N H1 sections found, K local image refs to resolve.` |
| Pre-processing start | `[pptx 2/8] Pre-processing final.md → final.intermediate.md via convert.py…` |
| Pre-processing done | `[pptx 2/8] Pre-processing done — M slides, P speaker-notes blocks, Q image refs.` |
| Native skill invocation (per stage of §19.3) | `[pptx 3/8] Stage 1 Cover — substituting 4 placeholders…` `[pptx 3/8] Stage 2 Agenda — substituting 2×N placeholders, N rows…` `[pptx 3/8] Stage 3 — deleting template slides 3–15…` `[pptx 3/8] Stage 4 — building M content slides…` `[pptx 3/8] Stage 5 — emitting (N−1) section dividers…` `[pptx 3/8] Stage 6 — white backgrounds, run-level fonts…` `[pptx 3/8] Stage 7 — emitting speaker notes…` (one line each; collapse Stages 6 and 7 into a single line if the native skill does not separate them) |
| Output file written | `[pptx 4/8] final.pptx written, S slides, U bytes.` |
| OOXML integrity check | `[pptx 5/8] OOXML invariants verified (per §19.4).` |
| Aspect-ratio audit | `[pptx 5/8] Aspect-ratio audit: <p:pic> N shapes, all within 1% tolerance — or — FAILED: M distorted (slide K: <src> rendered A:B vs intrinsic C:D).` |
| Palette/fonts audit | `[pptx 5/8] Palette/fonts audit: K slides, every color in §2 palette, every font in §3.1 set — or — FAILED: slide N has color #XXXXXX (off-palette) / font "Y" (off-font).` |
| Cover-fidelity audit | `[pptx 5/8] Cover-fidelity audit: slide 1 byte-equivalent to <style>/base-template.pptx (modulo text content) — or — FAILED: shape #N "X" differs in <field>: base=… rendered=….` |
| Layout-fit audit (strict only) | `[pptx 5/8] Layout-fit audit: K content slides, all predicted layouts match emitted layouts — or — FAILED: slide N "<H2>" predicted <layout> vs. emitted <layout> (likely cause: …). [skipped — style=free-form]` |
| Block-coverage audit | `[pptx 5/8] Block-coverage audit: K slides, M blocks total, 0 dropped — or — FAILED: slide N "<H2>" drops {block_type} (source line L).` |
| Visual fidelity spot-check | `[pptx 6/8] Visual spot-check vs base-template slides 1–2: OK.` |
| Slide-preview rasterization start | `[pptx 7/8] Rasterizing S slides to output/.critique/slide-NN.png…` |
| Slide-preview rasterization done | `[pptx 7/8] Slide previews ready (S PNGs) — or — slide_previews: failed: <reason>.` |
| Final report | `[pptx 8/8] Done. S slides, K images, slide_previews: <count|failed>, warnings: <count>.` |

**Pacing.** Emit each log-line *at the moment that stage begins or ends* — the orchestrator's checklist depends on this for live updates. If any single stage runs >30s without emitting, emit a `[pptx 3/8] Stage 4 — still building (Nth of M slides)…` heartbeat carrying a count (also log-only; the orchestrator translates to a plain-language *"Built N of M…"* chat line). **The FEEDBACK visual walk must emit per batch** — `[cycle N/M] FEEDBACK — reviewed 10/29 slides` after each 8–10-slide batch — never one silent multi-minute read of the whole deck. **>60s with no emission from any phase is a defect** (a *"Multitasking…"* stall the presenter reads as a hang) — emit `[pptx N/8] Stage X may be stalled` and surface it.

**Failure surfacing.** Stage failures emit `[pptx N/8] Stage X FAILED: <one-line reason>` (log-only). The orchestrator translates to plain language (*"Hit a snag on slide 9 — retrying."*) for chat.

**Iteration passes.** Cycle 2 and 3 (strict) / cycle 2 (preview) prefix every emission with `[cycle N/M] <PHASE>` and emit **per phase and per batch within FEEDBACK**, so a multi-cycle render shows continuous forward motion (build → review 10/29 → review 20/29 → 4 fixes → re-build → …) rather than one opaque spinner. Free-form is single-pass (no cycles). Same suppression rule — these are stage events for the checklist, not chat content.

**No-default policy on missing `style:`.** The `style:` invocation parameter is mandatory. If it is absent or empty on skill entry, the skill emits `[pptx 0/8] FAILED: style: invocation parameter missing` and stops — it does **not** fall back to `strict` or any other value. The orchestrator's job is to ask the presenter (Step 8 step 1) and pass an explicit answer; if the skill is reached without one, the orchestrator must re-ask. There is no defense-in-depth default — silent fallback was the bug, the loud failure is the fix.

## Rules

This skill is an orchestrator. Visual rules (palette, fonts, icons, emoji swap, callouts, tables, corner radius, agenda count, layout selection) live in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) — the consolidated anti-pattern list is §19.6 and the renderer must enforce it. The rules below are skill-local — they govern IO and orchestration, not visual style.

- **The base template is mandatory, not advisory** *(Keynote-compatibility rule)*. Every render **starts from a working copy of `<base_template_path>`** (resolved from the `style:` invocation parameter; presenter override optional). In python-pptx terms: `Presentation(<base_template_path>)`, **never** `Presentation()` from scratch. Scratch-built decks fail Keynote import even when OOXML audits pass, because they lack the master/layout/theme chain Keynote validates on load — the import error fires before any content is parsed. This is enforced at CONTROL via the cover-fidelity audit (drift from base-template slide 1 → render failure) and via the strict-spec §19.3 7-stage workflow.
- **System fonts only** *(Keynote-compatibility rule)*. Every text run's `<a:latin typeface="…"/>` must resolve to a font preinstalled on the import target — for the macOS/Keynote happy path that means **Arial / Helvetica / Courier New** (and their bold variants). Custom fonts that aren't on disk at import time — Roboto, Roboto Mono, Roboto Mono Medium, Consolas — trigger Keynote import failures before any content is parsed, even if the OOXML is well-formed. The per-style palette is the contract (`<style>/pptx-prompt.md` §3); `audit_palette_fonts.py` enforces it; any `[off-font]` finding stops the render. Embedding custom fonts inside the .pptx is a future option but not currently supported by this skill — until then, every spec-allowed font must be a system font.
- **The spec is the contract.** Pass [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) verbatim to the native renderer as instructions context. If the native skill ignores it, that's a render failure — surface and rerun, do not paper over with post-hoc edits.
- **Never modify `final.md` during render.** All transformation happens in memory or in `output/final.intermediate.md`. The cleaned `final.md` from Polish stays the source of truth for the render.
- **Never read or modify `draft.md`** — except read-only in `preview: true` mode. The Step-5.5 draft preview reads `draft.md` (never writes it) to render a throwaway preview before Polish. In every other invocation `draft.md` is untouched. No mode ever *modifies* `draft.md`.
- **Never re-render SVGs.** If an image ref points at a missing SVG, stop and tell the orchestrator to perform the Illustrator role rather than improvising.
- **Speaker notes go into the notes pane**, never on the slide body.
- **Progress visible at every stage.** The render is long enough that silence is a defect — emit one prefixed line per stage (see *Progress reporting* above), heartbeat every 30s inside long stages, and surface failures with the same prefix + `FAILED:` suffix. The presenter must never have to ask "is it still running?"

## Failure modes to surface

Operational / IO failures only. **Visual-spec violations** (emoji survived, non-template color/font, native `<a:tbl>` emitted, wrong callout variant, missing section pill, mixed icon style, flat `#F2F2F2` background, non-5760 corner radius, base-template slides 3–15 leaking through) are catalogued in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §19.6; surface any §19.6 violation as a render failure and rerun.

- Native `pptx` skill not available → stop, instruct presenter to run inside Cowork.
- Base template missing or unreadable → stop and ask.
- Base template was loaded but not honored — slides 1–2 in the rendered deck are not pixel-equivalent to base-template slides 1–2 (placeholders aside), or slides 3–15 leaked into the output, or theme/fonts/layouts don't match → surface loudly; offer to rerun.
- **Agenda capacity exceeded.** `final.md` has N H1 sections; the agenda emits one row per section per §5.3 / §5.5 (no fixed count). N ≤ 8 fits cleanly; for 9 ≤ N ≤ 10 emit with a tightness warning; for N > 10 stop and ask the presenter — the agenda chrome is out of vertical room and an alternate layout is needed. Never pad the agenda to 7 rows with blanks, and never truncate sections to fit.
- **OOXML integrity broken** per §19.4 invariants (dangling overrides / rels, `[Content_Types].xml` not first in zip, `sldIdLst` / `sldLayoutIdLst` without matching rels). Most often after Stage-3 deletion. Stop, repair, re-verify before declaring success.
- **Style invocation parameter missing.** `style:` was not passed at invocation. Fail render-blocking with `[pptx 0/8] FAILED: style: invocation parameter missing — the orchestrator must ask the presenter and pass the answer (see ${CLAUDE_PLUGIN_ROOT}/orchestrator.md Step 8 step 1).` Do not default. The orchestrator's job is to re-ask the presenter.
- **Style resolution failed** — the `style:` invocation value is not a directory under `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/`, or the resolved `<spec_path>` / `<base_template_path>` is missing. Surface verbatim with the offending value and the resolved paths. Cannot proceed — every render is style-rooted from step 0.
- **Palette/fonts audit failed** ([`audit_palette_fonts.py`](audit_palette_fonts.py) exit 1). One or more slides contain a color outside the §2 palette or a font outside the §3.1 set. Typical causes: Office theme accent leaked from a copy-paste, text run forgot its `<a:latin>` and fell back to a system font, renderer emitted a near-relative of a palette color. Surface the `[off-palette]` / `[off-font]` lines verbatim. The fix is renderer-side (correct the run's color/font emission); never compensate by widening the allowed set. Re-render and re-audit.
- **Cover-fidelity audit failed** ([`audit_cover_fidelity.py`](audit_cover_fidelity.py) exit 1). Slide 1 of `final.pptx` structurally differs from slide 1 of `<base_template_path>` in a field other than text content (geometry, fonts, fills, alignment, picture target). Per §4 of every style spec, the cover is contractually fixed. The fix is renderer-side (substitute *content only*, preserve all other shape attributes verbatim from the base template); never compensate by accepting drift. Re-render and re-audit.
- **Layout-fit audit failed** ([`audit_layout_fit.py`](audit_layout_fit.py) exit 1). One or more content slides emitted a layout that does not match the layout predicted from the source markdown's §15.5 surface signals + §15.6.1 discriminator. Typical pattern: the renderer fell through to §10 plain bullets when source has 3–5 labeled bullets (the spec mandates §7.4 card-row when bodies ≤ 80c, §7.5 icon-bullet list otherwise); or it picked content+image when source has ≥4 images (image-grid was selected); or content-text where a fenced code block mandates code-example. **Stop.** Re-route the offending slide through the discriminator-correct layout per §15.6.1; do not absorb the ambiguity by shipping the plainer layout. The audit's *likely cause* line names the discriminator that was skipped and the correct layout to emit. Re-render and re-audit.
- **Block-coverage audit failed** ([`audit_block_coverage.py`](audit_block_coverage.py) exit 1). One or more H2 slides in `final.md` carry a callout or image block that did not survive into `final.pptx`. Typical pattern: a trailing block on a slide whose preceding content (table, dense paragraphs) consumed the body area; the renderer's `effective_bottom` overflowed and the trailing block was silently skipped. **Stop. Do not start the orchestrator visual review** — the visual rubric does not catch silent drops (no shape on the slide → no rubric hit). Surface the offending `[block-drop]` lines verbatim. The fix is renderer-side (correct the body-fit calculation per §3.5 and the §8.3 line-count estimate) or content-side (split the slide if it's genuinely overstuffed) — never compensate by deleting the dropped block from `final.md`. Re-render and re-audit.
- **Cover `class:` missing from `final.md` frontmatter.** Per [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/strict/pptx-prompt.md) §4.3 + §19.3 stage 1, the class name is required — the cover's shape #2 must carry this class's name in smaller font below the Subject. Stop and tell the orchestrator to dispatch the Editor to add it (the Editor should propose 2–4 candidates from the Step-1 briefing per `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` Step 4); do not render with a blank or placeholder shape.
- **Aspect-ratio audit failed** ([`audit_aspect_ratios.py`](audit_aspect_ratios.py) exit 1). One or more `<p:pic>` shapes are rendered at a `cx:cy` ratio that diverges from the source asset's intrinsic ratio by more than the tolerance (default 1%). The renderer picked a slot rectangle and wrote it as `<a:ext cx=… cy=…/>` without uniform-scaling the asset to fit, so the asset is stretched or squished. Stop. Per §12: shrink the larger dimension to match the source ratio (leaving whitespace) rather than distort. Never resolve by widening the tolerance or by emitting `<a:srcRect>` / non-zero `<a:stretch fillRect>` insets to "fit". Re-render and re-audit.
- `final.md` not yet produced (Step 6 Polish hasn't run) or still contains `Presenter feedback` fields or unrendered ASCII fenced blocks → stop; return to Step 6.
- The path passed in points at `draft.md` instead of `final.md` → stop and ask. `draft.md` is never a valid input to this skill.
- An image ref points at a missing SVG → stop; orchestrator performs Illustrator role to render it.
- A Section has zero Slides.
- Native skill exits non-zero → surface its error message verbatim in the final report.
- **H1-as-content-slide regression.** `convert.py` only strips the numeric prefix and passes H1 through — the H1→divider semantic is the native skill's job. Spot-check after render: every numbered section in `final.md` must produce exactly one divider slide (per §5.6). H1 rendered as a content slide = contract violation, do not ship.

## Why Cowork-only

Earlier iterations tried three *CLI-only, from-scratch* rendering paths (note: this is about building a deck **without** the native `pptx` skill — the native skill's own `python-pptx`-from-base-template workflow is the sanctioned path, see the top of this file):

| Attempt | Outcome |
|---|---|
| Hand-rolled `python-pptx` script **from a blank `Presentation()`** (reimplementing the theme, no base template, no native skill) | Brittle `final.md` parsing, layout-by-layout theme reimplementation, fails Keynote import. Abandoned. *(This is NOT the native pptx skill's base-template workflow, which is required.)* |
| Marp CLI | Required migrating `final.md` to Marp syntax — a structural change to the source of truth. Reverted. |
| `pandoc --reference-doc=…` | Template-layout name mismatch (pandoc expects `Title Slide`, `Section Header`, etc. — our template doesn't have them), so theme fell back to pandoc's defaults. Section dividers also split into two slides because of body content between H1 and the first H2. Tables sometimes dropped silently. Removed. |

Each path produced a deck with subtle correctness or fidelity issues. The native `pptx` skill is the only tested-good rendering path. `final.md` is plain Markdown, so a presenter who really needs CLI rendering for a one-off can pipe it through their own toolchain — Talksmith just won't maintain that path.

