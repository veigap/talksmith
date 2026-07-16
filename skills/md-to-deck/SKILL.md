---
name: talksmith:md-to-deck
description: Render a Talk's `final.md` to a presentation — a native `.pptx` (styles `pptx-strict` / `pptx-free-form`, Cowork-only) or a code-rendered HTML/Reveal.js deck (`html-strict`, Cowork-independent; also the Step-5.5 live view from `draft.md` via `--draft`). Optional Step 7 of the workflow. The `style:` invocation parameter is mandatory — the skill fails render-blocking without it.
---

# md-to-deck — render `final.md` to a presentation (`.pptx` or HTML)

This skill turns a Talk's cleaned `final.md` into a presentation. It has **two render paths**, chosen by the mandatory `style:` invocation parameter:

- **Path A — native `.pptx`** (`pptx-strict`, `pptx-free-form`). Authored through Anthropic's official `pptx` skill at [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx). **Cowork-only** (that skill must be in the session registry). Starts from a style `base-template.pptx`, runs a build → audit → (strict) critique loop.
- **Path B — `html-strict`.** A styled **HTML / Reveal.js** deck rendered by code ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)). **Cowork-independent** — needs only Python + `jinja2`. No base template, no native skill, no deck-parsing audits. Also the **live in-progress view** (from `draft.md`, `--draft`) the orchestrator auto-fires at Step 5.5.

All three modes classify each slide against the shared catalog [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) and render the matched template; the universal invariant (labeled enumerations → cards, never plain bullets) holds in every mode. Per-mode phase config is the matrix in [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md) — the single source of truth; this file describes the *mechanics*, not that config.

## Style resolution — mandatory, no default

Every render begins by reading the `style:` parameter the orchestrator passed in (it asks the presenter at every Step 7 entry — see [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 7 step 1*). Allowed values: `pptx-strict`, `pptx-free-form`, `html-strict`. `final.md`/`draft.md` carry no `style:` field — the same content can be rendered in any mode at any time.

The resolved style names a self-contained spec (and, for Path A, a base template):

```
<spec_path>          = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md   # all modes
<base_template_path> = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx # Path A only
```

**If `style:` is absent or empty, fail render-blocking** — do not guess or default:

```
[pptx 0/8] FAILED: style: invocation parameter missing — the orchestrator must ask the presenter and pass the answer (see ${CLAUDE_PLUGIN_ROOT}/orchestrator.md Step 7 step 1).
```

If the value is present but is not a directory under `config/pptx-styles/`, or a required path is missing, fail render-blocking naming the offending value/path (the enum drifted from disk). Silent fallback to a default was the bug; the loud failure is the fix.

**Reads `final.md`, never `draft.md` — one exception.** `final.md` is the cleaned source (image refs inlined, `Presenter feedback` stripped by Polish). The **only** file-source exception is `html-strict --draft` (the Step-5.5 live view), which reads the in-progress `draft.md` *by design*. No mode ever modifies `draft.md` or `final.md`; all transformation happens in memory or in `output/…` artifacts.

## When to use

After Step 6 (Polish) completes and the presenter picks **Render** from the terminal branch, then chooses a mode. Optional — many presenters stop at the outline. (`html-strict` also auto-runs earlier, from `draft.md`, as the Step-5.5 live view.)

---

## Path B — `html-strict` (code render)

`html-strict` runs in **two steps: FILL, then RENDER.** The semantics live in the fill step (an
LLM decomposition); the render is a mechanical, committed script. **Never hand-roll a renderer, and
keep the renderer mechanical** — it maps model fields to templates and must not classify or parse
markdown.

**Step 1 — FILL `slide-model.json` (the semantic step, LLM).** Read `final.md` (or `draft.md` for
the live view) and produce `output/slide-model.json` conforming to
[`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md): a `deck` object (cover +
the ordered section list) and one object per slide. For **each** slide you:
- **classify** it against the catalog [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)
  (its *Match* rules) — set `template`;
- **decompose** the body into exactly that template's **required fields** (e.g. `stat` →
  `stats:[{value,caption}]`; `concept-breakdown` → `cards:[{label,body}]`; `comparison` →
  `columns:[{header,cells}]`) — splitting a metric from its caption, grouping symmetric blocks into
  columns, honouring the universal invariant (labeled sets → cards, never bullets);
- lift every `### Speaker notes` block **verbatim** into `notes` (never onto the slide face), and
  set `section` to the section the slide belongs to.
The judgment is the LLM's, against a fixed field contract. Write to
`talks/<Talk>/output/slide-model.json` (or `slide-model.draft.json` for `--draft`).

**Step 2 — RENDER (mechanical, deterministic).** [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)
loads the model and maps each slide's fields onto its Jinja template — no parsing, no classification:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py --talk talks/<Talk>          # output/slide-model.json → deliverable
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py --talk talks/<Talk> --draft  # output/slide-model.draft.json → live view
```

The **same `slide-model.json` is the shared IR for PPTX** — both renderers read fields, so a slide
looks the same across HTML and PPTX. (PPTX consumes it via its style spec; see Path A.)

- **Render mechanics.** Each template's markup is `templates/html/<type>.j2`, rendered by
  `html_style.render_model_slide` (cards, per-concept Material Symbols icons matched against the
  live catalog and inlined by `icon_fetch.py`, callout boxes, code surfaces), wrapped in a
  vendored, inlined **[Reveal.js](https://revealjs.com/)** shell → one self-contained
  `output/html/index.html`. Icons cache under `.icons/` (gitignored).
- **Presentation.** Reveal owns navigation (→ / ← / click), deck-to-window scaling, slide overview
  (`Esc`), transitions, full screen (`F`), **speaker notes** (`notes` → `<aside class="notes">`,
  shown with `s`), and **PDF export** (`?print-pdf` → Print → Save as PDF). The only custom code is
  a per-slide content-fit. A discreet Light/Dark toggle (moon/sun) is top-right. Fonts are IBM Plex
  Sans/Mono (vendored, inlined).
- **Prerequisites.** Python 3 + `jinja2`; network on the first run (Material Symbols catalog + icon
  fetch, then cached). **No Cowork, no native skill, no base template.** Degrades gracefully: on a
  render error, report the live view is unavailable — never fatal.
- **No critique loop.** `html-strict` is a single-pass GENERATE — no automated FEEDBACK/critique
  cycles. The presenter reviews the deck and resolves anything by editing the source (which re-fills
  the model) and re-rendering.

The rest of this file (Path A) does not apply to `html-strict`.

---

## Path A — native `.pptx` (`pptx-strict`, `pptx-free-form`)

**This path is a thin orchestrator over the official `pptx` skill.** All `.pptx` authoring goes through [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx), which authors the deck **programmatically with `python-pptx`** starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`). "Delegate to the pptx skill" means **drive that skill's `python-pptx` workflow from the base template + visual spec** — writing `python-pptx` that way is the mechanism, not a workaround.

**Forbidden** is *bypassing* that path: authoring from a blank `Presentation()`, reimplementing the theme, or using another tool (`pandoc`, Marp, hand-written XML) — all abandoned because they fail Keynote import (see *Why Cowork-only*). A generator that starts from `base-template.pptx`, substitutes the cover, and builds each slide per the visual spec is the **correct** render.

**The base template is mandatory and non-negotiable.** `pptx-strict`'s is a 15-slide foundation (cover + agenda + 12 layout-reference slides + 1 divider example); the renderer substitutes placeholders, deletes the layout-reference zone (slides 3–15), and inserts content per `<spec_path>`. `pptx-free-form`'s is a 1-slide cover-only foundation; it substitutes the cover's four §2 placeholders, then designs every other slide fresh per its §3. Decks built from scratch are a render failure in either style.

**Single responsibility.** This skill prepares the inputs and invokes the pptx skill. ASCII → SVG is the Illustrator's job (Step 6, before this runs); `final.md` arrives cleaned with every referenced image already under `talks/<Talk>/images/`.

### Prerequisites (Path A)

| Prereq | What to check | If missing |
|---|---|---|
| [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) in registry | Skill list includes `pptx` | Stop. Tell the presenter to run inside Cowork. No CLI fallback. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `final.md` | Exists; no `Presenter feedback`; ASCII replaced by `![...](images/...)` | Stop — Polish hasn't run; return to Step 6. |
| Pre-rendered local images | `talks/<Talk>/images/<file>` exists for every `![...](images/...)` ref | Stop. Dispatch `illustrator` for missing SVGs, or ask the presenter to drop the asset in. |
| Keynote-safe image extensions | Every `![alt](path)` uses `.png`/`.jpg`/`.jpeg`. **Forbidden: `.svg`, `.webp`, `.avif`, `.heic`** — Keynote drops them on import. | Stop, list every offending ref. `.svg` → re-dispatch Illustrator for a `.png` companion + Editor's Step-6(b) rewrite; `.webp/.avif/.heic` → re-dispatch Editor (rasterizes inline). |
| No remote image refs | No `![...](http(s)://...)` refs (pptx skill behavior on URLs is undefined) | Stop and ask the presenter to download into `images/` or explicitly accept the risk. |
| Base template | `<base_template_path>` exists (style-resolved) | Stop and ask. |
| Visual spec | `<spec_path>` exists (strict §1–§15 + §17–§20, free-form §1–§4) | Stop and ask — the spec is the contract. |
| Icon capability *(pptx-strict only)* | Icons are fetched by name at render time via `icon_fetch.py` (network on first fetch, cached under `output/.icons/`) — see `pptx-strict/pptx-prompt.md` §17.6. Free-form makes icons optional (§3.2). | Stop and ask — the no-emoji rule needs them. |

### Inputs (Path A)

- **Active `Talk` path** (absolute) and **`config/profile.md`** (cover placeholders `{{PRESENTATION_TITLE}}`/`{{PRESENTER}}` substitute from `Subject`/`Presenter`; agenda language from `Presentation language`).
- **Base template** = `<base_template_path>` (opened as a working copy, not a theme reference; presenter override optional — the legacy `pptx-strict/template.pptx` 53-slide reference is **not** a valid override).
- **Visual spec** = `<spec_path>` — the rendering contract for any slide that isn't a verbatim base-template slide. The operating manual for the renderer is `pptx-strict/pptx-prompt.md` §19 (reading order §19.2, 7-stage workflow §19.3, output contract + OOXML invariants §19.4, verification §19.5, anti-patterns §19.6). Pass it verbatim to the native skill as instructions context. When this skill and the spec disagree, **the spec wins**.

### Process (Path A)

0. **Resolve style** (see *Style resolution*). Cache `<spec_path>` (verify it exists for the style) and `<base_template_path>` (verify for the two `.pptx` styles). Emit `[pptx 0/8] Style resolved: <style> (spec=<spec_path>).`
1. **Verify prerequisites** (table above). Stop on any failure.
2. **FILL `slide-model.json`** — the shared semantic step, **identical to Path B's Step 1** (classify per the catalog, decompose into the template's required fields, lift notes verbatim, drop scaffolding — see Path B above + [`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)). HTML and PPTX author from this same structured model, so a slide looks the same in both.

   > **Author from the model ONLY; never re-parse `final.md`.** The model has already resolved every field — `template`, structured content, `notes`, `section`.

   **Per-mode paths.** Everywhere below, `output/final.pptx`, `output/.critique/` resolve to the per-style forms `output/final.<style>.pptx`, `output/.critique/<style>/`. The `slide-model.json` is shared (one per Talk). After a successful render the per-style deck is also copied to the canonical `output/final.pptx`.

2.5. **Template is decided in FILL.** Each slide's `template` is set in `slide-model.json`, per the catalog. **pptx-strict** re-checks it deterministically at CONTROL (`audits/layout_fit.py`, model vs emitted).
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
   - `audits/block_coverage.py` *(floor)* — every model slide's structured blocks (cards/rows/stats/figures/image) survived into the deck (no silent drops on busy slides).
   - `audits/notes_coverage.py` *(floor)* — every model slide that carries `notes` reached a non-empty notes pane (notes are load-bearing, template-independent).
   - `audits/palette_fonts.py` *(**pptx-strict only**)* — every color/font is in the strict §2/§3.1 set.
   - `audits/layout_fit.py` *(**pptx-strict only**)* — the emitted layout equals the layout expected for the slide's model `template`; catches emitting a plainer layout than the model calls for.
   - `audits/icon_coverage.py` *(**pptx-strict only**)* — a concept-breakdown/callout slide whose model carries icon-bearing fields rendered at least one icon (catches a silently skipped §17 icon-fetch).

   Free-form runs the four floor audits only. Each is a standalone CLI, comparing the deck against the model: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/<name>.py talks/<Talk>/output/final.pptx [talks/<Talk>/output/slide-model.json]`.
6. **Render per-slide critique PNGs** to `output/.critique/<style>/slide-NN.png` so the FEEDBACK sub-agent walks actual pixels. Priority: (1) the pptx skill's slide-to-image endpoint if it has one; (2) `libreoffice --headless --convert-to pdf` then `pdftoppm -r 150 -png`. If both fail the deck is still valid — report `slide_previews: failed: <reason>` and continue (visual critique can't run, but the `.pptx` is unaffected).
7. **FEEDBACK / REGENERATE** per mode (see *Render flow*). **pptx-strict** runs the multi-cycle critique loop; **pptx-free-form** is single-pass (presenter reviews afterward).
8. **Report:** `style: <mode>`, slide count, images resolved, and each audit's result (`aspect_audit`, `cover_fidelity`, `block_coverage`, `notes_coverage`, and — strict — `palette_fonts`, `layout_fit`, `icon_coverage` — each `ok | N fail | skipped:non-strict`), `slide_previews: <count|failed>`, plus any warnings from the pptx skill.

### Render flow (Path A)

The skill owns the entire render loop end-to-end (including strict's internal critique via a multimodal sub-agent that reads slide PNGs — an implementation detail, not surfaced to the orchestrator). Per-mode config is the [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md) matrix.

**`pptx-strict` — multi-cycle critique, up to 3 cycles.** Per cycle: **GENERATE** (cycle 1: full pipeline; 2–3: re-render only touched slides) → **CONTROL** (the audit suite; any non-zero → straight to REGENERATE) → **FEEDBACK** (a multimodal sub-agent walks all five `slide-design.md` categories — CONTENT + TEMPLATE + AESTHETIC + DISTRIBUTION + LAYOUT-CONFORMANCE — on the slide PNGs, autonomously; each finding is `fix this iteration` or `defer because …`) → **REGENERATE** (compose per-slide edits, re-render the subset). Empty/all-defer FEEDBACK → done. Only top-level rotations count against the cap; build-time recoveries inside one GENERATE do not. After cycle 3, survivors surface as `unresolved: …`.

**`pptx-free-form` — single pass.** GENERATE → CONTROL (floor audits). No FEEDBACK/REGENERATE — the renderer designs freely and the presenter reviews after delivery. Any non-zero audit → `unresolved: <audit>` in the report (no auto-fix). The `slide-design.md` practices are the presenter's self-review checklist here.

## Output layout

```
talks/<Talk>/
├── draft.md                              # working file (Steps 1–5) — read-only here (except html-strict --draft)
├── final.md                              # source for this skill (cleaned by Polish)
├── images/                               # populated by illustrator + editor (Step 6)
└── output/
    ├── slide-model.json                 # the structured model (FILL step) — HTML + PPTX both render from it
    ├── slide-model.draft.json            # in-progress model (html-strict --draft live view)
    ├── final.pptx                        # canonical deliverable — a copy of the most recent .pptx render
    ├── final.pptx-strict.pptx            # per-mode .pptx render, persists for comparison
    ├── final.pptx-free-form.pptx
    ├── .critique/                        # critique-only slide previews for the .pptx modes (git-ignored)
    │   ├── pptx-strict/slide-NN.png
    │   └── pptx-free-form/slide-NN.png
    └── html/                             # html-strict deck — index.html + .icons/ (build_html.py; final or draft model)
```

**Per-mode isolation.** Each `.pptx` render writes a suffixed deck `output/final.<style>.pptx` (with its `.critique/<style>/` PNGs), so strict and free-form renders coexist; the latest is copied to the canonical `output/final.pptx`. Each slide's chosen `template` lives in the shared `slide-model.json`. `html-strict` writes only under `output/html/`.

## Progress reporting (log-only)

Rendering runs 30 s – 3 min; silence reads as a hang. The skill emits **one bracketed stage line per phase**; the orchestrator drives a live stage rail from them and **never relays the raw tags to chat** (per [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Suppression rule*). Tag namespaces the skill owns: `[pptx`, `[cycle`, `[html`, `[block-drop`, `[off-palette`, `[off-font]`, `[unmatched]`, `[skipped]`. Any of these reaching chat verbatim is a leak.

**Rules:** emit a line at every phase boundary (after pre-process, deck built, CONTROL, each FEEDBACK batch, each REGENERATE); chunk slow phases and report between chunks (*"Reviewing slides 10 of 29…"*, *"Built 12 of 29…"*); **any phase quiet > 30 s emits a heartbeat**, and > 60 s of total silence is a defect. Strict cycles 2+ prefix every line `[cycle N/3] <PHASE>`; `html-strict` uses `[html]` (single pass, no cycles).

**Suppression vocabulary — what must never reach chat verbatim.** Beyond the bracketed tags: phase names (CONTROL / FEEDBACK / REGENERATE / GENERATE), audit/script names (`audits/palette_fonts.py`, `audits/block_coverage.py`, `audits/aspect_ratios.py`, `audits/cover_fidelity.py`, `audits/layout_fit.py`), library/tool names (`python-pptx`, `cairosvg`, `qlmanage`, `pandoc`, Marp, libreoffice, pdftoppm), XML internals (`<p:style>`, `<p:bg>`, `<a:srgbClr>`, `<p:pic>`, OOXML, `ppt/media/…`, `[Content_Types].xml`), slide-XML coordinates (EMU values), rubric-row format (`slide N · <catalog-id> · …`), and the phrases *"final.md frontmatter"* / *"draft.md frontmatter"*. Translation pattern: name the *outcome* (what got fixed, how many, which slides — slide numbers are presenter-actionable and stay); strip the *mechanism* (which audit, XML element, library, phase tag). **Don't:** *"Three issues were caught and fixed during CONTROL: a palette false-positive from python-pptx's `<p:style>` boilerplate (stripped), the cover logo relationship (corrected to embed image-1-1.png directly), and 4 slides with missing callout shapes (slides 9, 12, 24, 27 — callouts added)."* **Do:** *"Checked the deck and applied 3 small automatic fixes (a palette check, the cover image, and 4 slides where a block needed re-adding — 9, 12, 24, 27). Done."*

**Stage rails** — the orchestrator renders these as a one-line rail and edits it in place; glyphs and rules are its own (`orchestrator.md` → *Interaction defaults* → *stage rail*). This skill owns only the stage names per mode:

```
pptx-strict:      Formatting source → Building draft slides → Reviewing slides (N/3) → Applying fixes → Final check
pptx-free-form:   Formatting source → Building slides → Sanity check
html-strict:      Formatting source → Rendering the deck → Ready to view
```

`html-strict` "Ready to view" = `index.html` on disk under `output/html/`; open it (Reveal deck: → / ← advance, `Esc` overview, `F` full screen, `s` speaker notes, `?print-pdf` to export PDF).

## Rules

- **Base template is mandatory** (Path A, Keynote-compat): `Presentation(<base_template_path>)`, never blank. Scratch decks fail Keynote import (no master/layout/theme chain). Enforced by `audits/cover_fidelity.py`.
- **System fonts only** (Path A, Keynote-compat): every `<a:latin>` must resolve to a font on the import target (Arial / Helvetica / Courier New on the macOS/Keynote path). Custom fonts (Roboto, Consolas, …) fail import even with valid OOXML. Enforced by `audits/palette_fonts.py`. (Path B embeds its own IBM Plex fonts as data-URIs — HTML, not Keynote, so this does not apply.)
- **The spec is the contract** (Path A): pass `<spec_path>` verbatim to the native renderer; if it's ignored, that's a render failure — rerun, don't patch post-hoc.
- **Never modify `final.md`/`draft.md`.** All work is in memory or `output/…`. `html-strict --draft` reads `draft.md` read-only.
- **Never re-render SVGs.** A missing SVG ref → stop, the orchestrator dispatches the Illustrator.
- **Speaker notes go into the notes pane** (Path A) / the Reveal `<aside class="notes">` (Path B), never on the slide body.

## Failure modes to surface

Operational/IO failures (visual-spec violations are catalogued in `<spec_path>` §19.6 — surface any as a render failure and rerun):

- **`style:` missing** → `[pptx 0/8] FAILED: style: invocation parameter missing …`; do not default.
- **Style resolution failed** — value not a directory under `config/pptx-styles/`, or a resolved path missing → surface verbatim.
- **pptx skill unavailable** (Path A) → stop, tell the presenter to run inside Cowork.
- **Base template missing / not honored** — slides 1–2 not pixel-equivalent, or slides 3–15 leaked → surface loudly; offer rerun.
- **Any CONTROL audit failed** (`aspect_ratios`, `cover_fidelity`, `block_coverage`, `notes_coverage`, and — strict — `palette_fonts`, `layout_fit`, `icon_coverage`) → surface the `[…]` lines verbatim; the fix is renderer-side (never widen tolerances, drop blocks, or accept drift); re-render and re-audit.
- **Agenda capacity exceeded** — N ≤ 8 fits; 9–10 emit with a tightness warning; > 10 stop and ask. Never pad to a fixed count or truncate sections.
- **OOXML integrity broken** (§19.4) — usually after the Stage-3 deletion. Stop, repair, re-verify.
- **Cover `class:` missing** from `final.md` frontmatter (§4.3) → stop; orchestrator dispatches the Editor to add it.
- **`final.md` not produced / still has `Presenter feedback` or raw ASCII fences**, or the path points at `draft.md` → stop; return to Step 6 / ask.
- **A section has zero slides**, or **H1 rendered as a content slide** (must be exactly one divider per numbered section, §5.6) → contract violation, do not ship.
- **pptx skill exits non-zero** → surface its error verbatim.
- **html-strict render error** (Path B) → report the deck/live view is unavailable (never fatal).

## Why Cowork-only (Path A)

Every CLI-only, from-scratch path (blank `Presentation()`, Marp, `pandoc --reference-doc`) was tried and abandoned — each fails Keynote import or mangles the source of truth. The native `pptx` skill's `python-pptx`-from-base-template workflow is the only sanctioned path; there is no CLI fallback.

The native `pptx` skill is the only tested-good `.pptx` path. `html-strict` (Path B) needs no Cowork at all — it's deterministic code. `final.md` is plain Markdown, so a presenter who needs one-off CLI rendering can use their own toolchain; Talksmith just won't maintain that path.
