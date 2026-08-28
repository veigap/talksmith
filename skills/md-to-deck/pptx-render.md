# md-to-deck — Path A: native `.pptx` render

> **Load this file only when the resolved `style:` is `pptx-strict` or `pptx-free-form`.**
> It is the `.pptx` half of [`SKILL.md`](SKILL.md), split out precisely so an `html-strict` render —
> including the Step-5.5 live view, which fires automatically on every first complete draft — never
> pays for it. `SKILL.md` resolves the style first and points here only on a `pptx-*` value; if you
> arrived here any other way, go back and resolve the style.

Everything in [`SKILL.md`](SKILL.md) still applies: style resolution, the shared FILL step and its
model audits, the output layout, progress reporting and the stage rails. This file adds only what is
specific to authoring a `.pptx`.

## Path A — native `.pptx` (`pptx-strict`, `pptx-free-form`)

**This path is a thin orchestrator over the official `pptx` skill.** All `.pptx` authoring goes through the official `pptx` skill in the session registry, which authors the deck **programmatically with `python-pptx`** starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`). "Delegate to the pptx skill" means **drive that skill's `python-pptx` workflow from the base template + visual spec** — writing `python-pptx` that way is the mechanism, not a workaround.

**Forbidden** is *bypassing* that path: authoring from a blank `Presentation()`, reimplementing the theme, or using another tool (`pandoc`, Marp, hand-written XML) — all abandoned because they fail Keynote import (see *Why Cowork-only*). A generator that starts from `base-template.pptx`, substitutes the cover, and builds each slide per the visual spec is the **correct** render.

**The base template is mandatory and non-negotiable.** `pptx-strict`'s is a 15-slide foundation (cover + agenda + 12 layout-reference slides + 1 divider example); the renderer substitutes placeholders, deletes the layout-reference zone (slides 3–15), and inserts content per `<spec_path>`. `pptx-free-form`'s is a 1-slide cover-only foundation; it substitutes the cover's four §2 placeholders, then designs every other slide fresh per its §3. Decks built from scratch are a render failure in either style.

**Single responsibility.** This skill prepares the inputs and invokes the pptx skill. ASCII → SVG is the Diagram-Illustrator's job (Step 6, before this runs); `final.md` arrives cleaned with every referenced image already under `talks/<Talk>/images/`.

### Prerequisites (Path A)

| Prereq | What to check | If missing |
|---|---|---|
| The `pptx` skill in the session registry | Skill list includes `pptx` | Stop. Tell the presenter to run inside Cowork. No CLI fallback. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `final.md` | Exists; no `Presenter feedback`; ASCII replaced by `![...](images/...)` | Stop — Polish hasn't run; return to Step 6. |
| Pre-rendered local images | `talks/<Talk>/images/<file>` exists for every `![...](images/...)` ref | Stop. Dispatch `diagram-illustrator` for missing SVGs, or ask the presenter to drop the asset in. |
| Keynote-safe image extensions *(this path only — `html-strict` inlines `.svg` and must keep it)* | Every `![alt](path)` uses `.png`/`.jpg`/`.jpeg`. **Forbidden: `.svg`, `.webp`, `.avif`, `.heic`** — Keynote drops them on import. | Stop, list every offending ref. `.svg` → re-dispatch Diagram-Illustrator for a `.png` companion + Editor's Step-6(b) rewrite; `.webp/.avif/.heic` → re-dispatch Editor (rasterizes inline). |
| No remote image refs | No `![...](http(s)://...)` refs (pptx skill behavior on URLs is undefined) | Stop and ask the presenter to download into `images/` or explicitly accept the risk. |
| No video refs *(this path only)* | No `![...](*.webm/.mp4/.m4v/.mov/.ogv)` and no YouTube link in a media ref. **Video is an HTML-deck feature** — it autoplays on slide entry there; this path has no equivalent. | Don't stop the render: tell the presenter those slides carry a clip that only the HTML deck plays, and ask for a still (a poster frame in `images/`) for the `.pptx`, or accept the slide without it. |
| Base template | `<base_template_path>` exists (style-resolved) | Stop and ask. |
| Visual spec | `<spec_path>` exists (strict §1–§15 + §17–§20, free-form §1–§4) | Stop and ask — the spec is the contract. |
| Icon capability *(pptx-strict only)* | Icons are fetched by name at render time via `icon_fetch.py` (network on first fetch, cached under `output/.icons/`) — see `pptx-strict/pptx-prompt.md` §17.6. Free-form makes icons optional (§3.2). | Stop and ask — the no-emoji rule needs them. |

### Inputs (Path A)

- **Active `Talk` path** (absolute) and **`config/profile.md`** (cover placeholders `{{PRESENTATION_TITLE}}`/`{{PRESENTER}}` substitute from `Subject`/`Presenter`; agenda language from `Presentation language`).
- **Base template** = `<base_template_path>` (opened as a working copy, not a theme reference; presenter override optional — the `pptx-strict/template.pptx` 53-slide reference deck is **not** a valid override).
- **Visual spec** = `<spec_path>` — the rendering contract for any slide that isn't a verbatim base-template slide. The operating manual for the renderer is `pptx-strict/pptx-prompt.md` §19 (reading order §19.2, 7-stage workflow §19.3, output contract + OOXML invariants §19.4, verification §19.5, anti-patterns §19.6). Pass it verbatim to the native skill as instructions context. When this skill and the spec disagree, **the spec wins**.

### Process (Path A)

0. **Resolve style** (see *Style resolution*). Cache `<spec_path>` (verify it exists for the style) and `<base_template_path>` (verify for the two `.pptx` styles). Emit `[pptx 0/8] Style resolved: <style> (spec=<spec_path>).`
1. **Verify prerequisites** (table above). Stop on any failure.
2. **FILL `slide-model.json`** — the shared semantic step, **identical to Path B's Step 1** (classify per the catalog, decompose into the template's required fields, lift notes verbatim, drop scaffolding — see Path B above + [`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)). HTML and PPTX author from this same structured model, so a slide looks the same in both. **Always re-FILL from the current `final.md` on every render — the model is a generated artifact, never reused stale.** Then stamp it, exactly as Path B does, and gate the render on the stamp:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py stamp --talk talks/<Talk>   # after FILL
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py check --talk talks/<Talk>   # before RENDER — exit 3 ⇒ STOP
   ```

   `build_html.py` runs this guard internally, but the `.pptx` render is driven by the native skill, so **run `check` explicitly here and stop the render on a non-zero exit** (surface the message; re-run FILL). If FILL itself fails, stop and report — never render from a pre-existing model.

   > **Author from the model ONLY; never re-parse `final.md`.** The model has already resolved every field — `template`, structured content, `notes`, `section`.

   **Per-mode paths.** Everywhere below, `output/final.pptx`, `output/.critique/` resolve to the per-style forms `output/final.<style>.pptx`, `output/.critique/<style>/`. The `slide-model.json` is shared (one per Talk). After a successful render the per-style deck is also copied to the canonical `output/final.pptx`.

2.5. **Template is decided in FILL.** Each slide's `template` is set in `slide-model.json`, per the catalog. **pptx-strict** re-checks it deterministically at CONTROL (`audits/layout_fit.py`, model vs emitted).

2.6. **CHECK + CLASSIFY-REVIEW the model** — Path B's **Steps 1.5 and 1.6**, run verbatim here. They read the model alone, so they are mode-independent and this path gets them for the same reason it gets the FILL: it is the same artifact. `layout_fit.py` at CONTROL checks that the *emitted* deck matches the template the model names — it takes the model's choice as given and never asks whether that choice was the right one. Run `degenerate_enum` + `template_diversity` + the two coverage preflights, then dispatch the `slide-classifier-critic` per content slide and apply its verdicts, **before** the render at step 3. Re-classifying after the deck is authored means re-authoring the slide.
3. **Render** by invoking the pptx skill against the **7-stage workflow** in `<spec_path>` §19.3 (for strict: open base-template as working copy → cover §4 → agenda §5 → discard slides 3–15 → content slides §15/§6–§9/§13 → dividers §5.6 → backgrounds §1 → speaker notes). Pass: **`slide-model.json`**, the image paths, the base template, the icon library, and the visual spec — each slide is authored from its model fields. All substantive rules live in `<spec_path>` and are not duplicated here.

   **Acceptance bar:** open the rendered deck next to `<base_template_path>` — slides 1–2 must be pixel-equivalent modulo placeholder text. Author-from-scratch = failure.
4. **Verify `output/final.<style>.pptx` exists and is non-empty, then copy it to the canonical `output/final.pptx`** (what the reverse pipeline reads). The suffixed deck persists for comparison. **When `style == pptx-strict`,** snapshot the as-generated geometry baseline for the learning loop:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/learn_patterns.py inventory \
     talks/<Talk>/output/final.pptx-strict.pptx -o talks/<Talk>/output/final.generated.geometry.json
   ```

   (`talksmith:pptx-learn` diffs the human-edited deck against this baseline. Skip for `pptx-free-form`.)
5. **CONTROL — deterministic audits** (a non-zero exit is a render failure: surface the FAIL lines verbatim, repair, re-render). Run against `output/final.pptx`:
   - `audits/aspect_ratios.py` *(floor)* — every `<p:pic>`'s rendered `cx:cy` matches its source's intrinsic ratio (1% tolerance). Catches non-uniform scaling.
   - `audits/cover_fidelity.py` *(floor)* — slide 1 is byte-equivalent to `<base_template_path>` slide 1 modulo the four cover slots.
   - `audits/block_coverage.py` *(floor)* — every model slide's structured blocks (cards/rows/stats/figures/image) survived into the deck (no silent drops on busy slides). Its `--source` stage ran already at Step 1.5.
   - `audits/notes_coverage.py` *(floor)* — every model slide that carries `notes` reached a non-empty notes pane (notes are load-bearing, template-independent). Same: the `--source` half ran at Step 1.5.
   - `audits/palette_fonts.py` *(**pptx-strict only**)* — every color/font is in the strict §2/§3.1 set.
   - `audits/layout_fit.py` *(**pptx-strict only**)* — the emitted layout equals the layout expected for the slide's model `template`; catches emitting a plainer layout than the model calls for.
   - `audits/icon_coverage.py` *(**pptx-strict only**)* — a concept-breakdown/callout slide whose model carries icon-bearing fields rendered at least one icon (catches a silently skipped §17 icon-fetch).

   Free-form runs the four floor audits only. Each is a standalone CLI, comparing the deck against the model: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/<name>.py talks/<Talk>/output/final.pptx [talks/<Talk>/output/slide-model.json]`. `block_coverage` and `notes_coverage` take the model first and the deck as an **optional** second argument — omit it and they run their `--source` stage against `final.md` instead, which is what makes them usable on a deck that renders only to HTML.
6. **Render per-slide critique PNGs** to `output/.critique/<style>/slide-NN.png` so the FEEDBACK sub-agent walks actual pixels. Priority: (1) the pptx skill's slide-to-image endpoint if it has one; (2) `libreoffice --headless --convert-to pdf` then `pdftoppm -r 150 -png`. If both fail the deck is still valid — report `slide_previews: failed: <reason>` and continue (visual critique can't run, but the `.pptx` is unaffected).
7. **FEEDBACK / REGENERATE** per mode (see *Render flow*). **pptx-strict** runs the multi-cycle critique loop; **pptx-free-form** is single-pass (presenter reviews afterward).
8. **Report:** `style: <mode>`, slide count, images resolved, and each audit's result (`aspect_audit`, `cover_fidelity`, `block_coverage`, `notes_coverage`, and — strict — `palette_fonts`, `layout_fit`, `icon_coverage` — each `ok | N fail | skipped:non-strict`), `slide_previews: <count|failed>`, plus any warnings from the pptx skill.

### Render flow (Path A)

The skill owns the entire render loop end-to-end (including strict's internal critique via a multimodal sub-agent that reads slide PNGs — an implementation detail, not surfaced to the orchestrator). Per-mode config is the [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md) matrix.

**`pptx-strict` — multi-cycle critique, up to 3 cycles.** Per cycle: **GENERATE** (cycle 1: full pipeline; 2–3: re-render only touched slides) → **CONTROL** (the audit suite; any non-zero → straight to REGENERATE) → **FEEDBACK** (a multimodal sub-agent walks all five `slide-design.md` categories — CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE — on the slide PNGs, autonomously; each finding is `fix this iteration` or `defer because …`) → **REGENERATE** (compose per-slide edits, re-render the subset). Empty/all-defer FEEDBACK → done. Only top-level rotations count against the cap; build-time recoveries inside one GENERATE do not. After cycle 3, survivors surface as `unresolved: …`.

**`pptx-free-form` — single pass.** GENERATE → CONTROL (floor audits). No FEEDBACK/REGENERATE — the renderer designs freely and the presenter reviews after delivery. Any non-zero audit → `unresolved: <audit>` in the report (no auto-fix). The `slide-design.md` practices are the presenter's self-review checklist here.


## Rules (Path A)

- **Base template is mandatory** (Keynote-compat): `Presentation(<base_template_path>)`, never blank. Scratch decks fail Keynote import (no master/layout/theme chain). Enforced by `audits/cover_fidelity.py`.
- **System fonts only** (Keynote-compat): every `<a:latin>` must resolve to a font on the import target (Arial / Helvetica / Courier New on the macOS/Keynote path). Custom fonts (Roboto, Consolas, …) fail import even with valid OOXML. Enforced by `audits/palette_fonts.py`. (Path B embeds its own IBM Plex fonts as data-URIs — HTML, not Keynote, so this does not apply there.)
- **The spec is the contract:** pass `<spec_path>` verbatim to the native renderer; if it's ignored, that's a render failure — rerun, don't patch post-hoc.
- **Speaker notes go into the notes pane**, never on the slide body.

## Failure modes to surface (Path A)

Operational/IO failures (visual-spec violations are catalogued in `<spec_path>` §19.6 — surface any as a render failure and rerun). The style-resolution and model-freshness failures in [`SKILL.md`](SKILL.md) → *Failure modes* apply here too.

- **pptx skill unavailable** → stop, tell the presenter to run inside Cowork.
- **Base template missing / not honored** — slides 1–2 not pixel-equivalent, or slides 3–15 leaked → surface loudly; offer rerun.
- **Any CONTROL audit failed** (`aspect_ratios`, `cover_fidelity`, `block_coverage`, `notes_coverage`, and — strict — `palette_fonts`, `layout_fit`, `icon_coverage`) → surface the `[…]` lines verbatim; the fix is renderer-side (never widen tolerances, drop blocks, or accept drift); re-render and re-audit.
- **Agenda capacity exceeded** — N ≤ 8 fits; 9–10 emit with a tightness warning; > 10 stop and ask. Never pad to a fixed count or truncate sections.
- **OOXML integrity broken** (§19.4) — usually after the Stage-3 deletion. Stop, repair, re-verify.
- **Cover `class:` missing** from `final.md` frontmatter (§4.3) → stop; orchestrator dispatches the Editor to add it.
- **A section has zero slides**, or **H1 rendered as a content slide** (must be exactly one divider per numbered section, §5.6) → contract violation, do not ship.
- **pptx skill exits non-zero** → surface its error verbatim.

## Why Cowork-only (Path A)

Every CLI-only, from-scratch path (blank `Presentation()`, Marp, `pandoc --reference-doc`) was tried and abandoned — each fails Keynote import or mangles the source of truth. The native `pptx` skill's `python-pptx`-from-base-template workflow is the only sanctioned path; there is no CLI fallback.

The native `pptx` skill is the only tested-good `.pptx` path. `html-strict` (Path B) needs no Cowork at all — it's deterministic code. `final.md` is plain Markdown, so a presenter who needs one-off CLI rendering can use their own toolchain; Talksmith just won't maintain that path.
