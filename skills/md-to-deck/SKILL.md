---
name: talksmith:md-to-deck
description: Render a Talk's cleaned `final.md` to a presentation. **Branches by the mandatory `style:` invocation parameter** — three modes, no default: **`pptx-strict`** and **`pptx-free-form`** author a native PowerPoint (`.pptx`) via Anthropic's official `pptx` skill (`skill://antropic-skills:/pptx`, **Cowork-only**, each with a `base-template.pptx`); **`html-strict`** renders a styled **HTML / Reveal.js** deck by code via [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py) (**Cowork-independent**, needs `jinja2`) — from `final.md` as the shareable deliverable (`output/html/index.html`), and, auto-fired by the orchestrator with `--draft`, from the in-progress `draft.md` as a **live view kept in sync during drafting** (same renderer, same output). Optional Step 8 of the Presenter Agent workflow, invoked after Step 6 (Polish); the live view auto-fires earlier (Step 5.5). Consumes images already on disk under `talks/<Talk>/images/`. The orchestrator asks the presenter the style at every Step 8 entry and passes it in; `final.md`/`draft.md` are style-agnostic. The skill fails render-blocking if `style:` is absent. Each style resolves to a self-contained spec under [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/) per [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/README.md). Output: the `.pptx` styles → `talks/<Talk>/output/final.<style>.pptx` (+ canonical `final.pptx`); `html-strict` → `output/html/index.html`. Because `html-strict` renders in HTML, its styled layer (cards, per-concept icons, callouts, code surfaces) is **always present**, unlike the native `.pptx` render which can drop it.
---

# md-to-deck — render `final.md` to a presentation (`.pptx` or HTML)

This skill turns a Talk's cleaned `final.md` into a presentation. It has **two render paths**, chosen by the mandatory `style:` invocation parameter:

- **Path A — native `.pptx`** (`pptx-strict`, `pptx-free-form`). Authored through Anthropic's official `pptx` skill at [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx). **Cowork-only** (that skill must be in the session registry). Starts from a style `base-template.pptx`, runs a build → audit → (strict) critique loop.
- **Path B — `html-strict`.** A styled **HTML / Reveal.js** deck rendered by code ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)). **Cowork-independent** — needs only Python + `jinja2`. No base template, no native skill, no deck-parsing audits. Also the **live in-progress view** (from `draft.md`, `--draft`) the orchestrator auto-fires at Step 5.5.

All three modes classify each slide against the shared catalog [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) and render the matched template; the universal invariant (labeled enumerations → cards, never plain bullets) holds in every mode. Per-mode phase config is the matrix in [`render-modes.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/render-modes.md) — the single source of truth; this file describes the *mechanics*, not that config.

## Style resolution — mandatory, no default

Every render begins by reading the `style:` parameter the orchestrator passed in (it asks the presenter at every Step 8 entry — see [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 8 step 1*). Allowed values: `pptx-strict`, `pptx-free-form`, `html-strict`. `final.md`/`draft.md` carry no `style:` field — the same content can be rendered in any mode at any time.

The resolved style names a self-contained spec (and, for Path A, a base template):

```
<spec_path>          = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/pptx-prompt.md   # all modes
<base_template_path> = ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/<style>/base-template.pptx # Path A only
```

**If `style:` is absent or empty, fail render-blocking** — do not guess or default:

```
[pptx 0/8] FAILED: style: invocation parameter missing — the orchestrator must ask the presenter and pass the answer (see ${CLAUDE_PLUGIN_ROOT}/orchestrator.md Step 8 step 1).
```

If the value is present but is not a directory under `config/pptx-styles/`, or a required path is missing, fail render-blocking naming the offending value/path (the enum drifted from disk). Silent fallback to a default was the bug; the loud failure is the fix.

**Reads `final.md`, never `draft.md` — one exception.** `final.md` is the cleaned source (image refs inlined, `Presenter feedback` stripped by Polish). The **only** file-source exception is `html-strict --draft` (the Step-5.5 live view), which reads the in-progress `draft.md` *by design*. No mode ever modifies `draft.md` or `final.md`; all transformation happens in memory or in `output/…` artifacts.

## When to use

After Step 6 (Polish) completes and the presenter picks **Render** from the terminal branch, then chooses a mode. Optional — many presenters stop at the outline. (`html-strict` also auto-runs earlier, from `draft.md`, as the Step-5.5 live view.)

---

## Path B — `html-strict` (code render)

`html-strict` runs in **two steps: FILL, then RENDER.** The semantics live in the fill step (an
LLM decomposition); the render is a mechanical, committed script. **Never hand-roll a renderer, and
never re-add markdown parsing/classification to the renderer** — that regex path was removed on
purpose.

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
This replaces the old brittle regex classifier — the judgment is the LLM's, against a fixed field
contract. Write to `talks/<Talk>/output/slide-model.json` (or `slide-model.draft.json` for `--draft`).

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
- **Critique.** A light **FEEDBACK → surface** loop, ≤ 2 cycles, walking CONTENT + TEMPLATE +
  AESTHETIC + DISTRIBUTION ([`slide-design.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-design.md))
  on the rendered `index.html`. A finding is fixed by **re-filling the model** (adjust a slide's
  template or fields), then re-rendering — the render itself takes no fix instructions.

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
| Visual spec | `<spec_path>` exists (strict §1–§20, free-form §1–§4) | Stop and ask — the spec is the contract. |
| Icon library *(pptx-strict only)* | `pptx-strict/base-template.pptx` `ppt/media/icon-*.svg` — see `pptx-strict/pptx-prompt.md` §17. Free-form makes icons optional (§3.2). | Stop and ask — the no-emoji rule needs them. |

### Inputs (Path A)

- **Active `Talk` path** (absolute) and **`config/profile.md`** (cover placeholders `{{PRESENTATION_TITLE}}`/`{{PRESENTER}}` substitute from `Subject`/`Presenter`; agenda language from `Presentation language`).
- **Base template** = `<base_template_path>` (opened as a working copy, not a theme reference; presenter override optional — the legacy `pptx-strict/template.pptx` 53-slide reference is **not** a valid override).
- **Visual spec** = `<spec_path>` — the rendering contract for any slide that isn't a verbatim base-template slide. The operating manual for the renderer is `pptx-strict/pptx-prompt.md` §19 (reading order §19.2, 7-stage workflow §19.3, output contract + OOXML invariants §19.4, verification §19.5, anti-patterns §19.6). Pass it verbatim to the native skill as instructions context. When this skill and the spec disagree, **the spec wins**.

### Process (Path A)

0. **Resolve style** (see *Style resolution*). Cache `<spec_path>` (verify it exists for the style) and `<base_template_path>` (verify for the two `.pptx` styles). Emit `[pptx 0/8] Style resolved: <style> (spec=<spec_path>).`
1. **Verify prerequisites** (table above). Stop on any failure.
2. **Pre-process `final.md` with [`convert.py`](convert.py)** → the intermediate the pptx skill consumes:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/convert.py \
     talks/<Talk>/final.md -o talks/<Talk>/output/final.<style>.intermediate.md
   ```

   `convert.py` drops YAML frontmatter, HTML comments, and the `# Thesis` / `# Open questions` / `# Cut material` sections; strips numeric heading prefixes (`## 2. Why X` → `## Why X`); per H2, drops `### Content`'s label (keeps body), drops `### Sources`, renames `### Speaker notes` → `### Notes`, and drops any `### Presenter feedback`; preserves `![alt](images/...)` refs and `---` rules.

   > **Hard rule — author from the intermediate ONLY; never re-parse `final.md`.** `convert.py` has already resolved every field. A renderer that parses `final.md` directly will miss `### Notes` (only in the intermediate) and spill `### Sources` / speaker notes / section goals into the slide body — the exact bug this pre-processing prevents.

   **Per-mode paths.** Everywhere below, `output/final.pptx`, `output/final.intermediate.md`, `output/.critique/` resolve to the per-style forms `output/final.<style>.pptx`, `output/final.<style>.intermediate.md`, `output/.critique/<style>/`. After a successful render the per-style deck is also copied to the canonical `output/final.pptx`.

2.5. **Classify each slide against the catalog.** Walk each H2 in the intermediate and classify it per [`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) → *Classification procedure* — one best-fit template (or `fallback`), cards not bullets. Record + check by mode:
   - **pptx-strict** — apply the §15.6 pre-emit audit; emit one `[pptx audit N/M]` line per slide (chosen template + inputs). Re-checked deterministically at CONTROL by `audits/layout_fit.py`.
   - **pptx-free-form** — record the chosen id in the `.layout-log.md` sidecar (`<spec_path>` §3.1); no gate.
3. **Render** by invoking the pptx skill against the **7-stage workflow** in `<spec_path>` §19.3 (for strict: open base-template as working copy → cover §4 → agenda §5 → discard slides 3–15 → content slides §15/§6–§9/§13 → dividers §5.6 → backgrounds §1 → speaker notes). Pass: the intermediate, the image paths, the base template, the icon library, and the visual spec. All substantive rules live in `<spec_path>` and are not duplicated here.

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
   - `audits/block_coverage.py` *(floor)* — every source callout/image block survived into the deck (no silent drops on busy slides).
   - `audits/notes_coverage.py` *(floor)* — every `### Notes` block reached a non-empty notes pane (notes are load-bearing, template-independent).
   - `audits/palette_fonts.py` *(**pptx-strict only**)* — every color/font is in the strict §2/§3.1 set.
   - `audits/layout_fit.py` *(**pptx-strict only**)* — the emitted layout equals the layout predicted from the source signals (§15.5/§15.6.1); catches picking a plainer layout than the content warrants.
   - `audits/icon_coverage.py` *(**pptx-strict only**)* — a concept-breakdown/callout slide that should carry icons rendered at least one (catches a silently skipped §17 icon-fetch).

   Free-form runs the four floor audits only. Each is a standalone CLI: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/<name>.py talks/<Talk>/output/final.pptx [talks/<Talk>/final.md]`.
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
    ├── final.pptx                        # canonical deliverable — a copy of the most recent .pptx render
    ├── final.pptx-strict.pptx            # per-mode .pptx render, persists for comparison
    ├── final.pptx-strict.template-log.md # per-mode template-decision log (beside its .pptx)
    ├── final.pptx-free-form.pptx
    ├── final.pptx-free-form.template-log.md
    ├── final.<style>.intermediate.md     # per-mode transient pre-processed file (convert.py)
    ├── .critique/                        # critique-only slide previews for the .pptx modes (git-ignored)
    │   ├── pptx-strict/slide-NN.png
    │   └── pptx-free-form/slide-NN.png
    └── html/                             # html-strict deck — index.html + template-log.md + .icons/ (build_html.py; final.md deliverable OR draft.md live view)
```

**Per-mode isolation.** Each `.pptx` render writes a suffixed deck `output/final.<style>.pptx` (with its intermediate, `.critique/<style>/` PNGs, and `final.<style>.template-log.md`), so strict and free-form renders coexist. The latest is copied to the canonical `output/final.pptx`; the suffixed files persist. The template-decision log records per slide which catalog template was chosen and why (schema: `slide-templates.md` → *Template decision log*). `html-strict` writes only under `output/html/`.

## Progress reporting (log-only)

Rendering runs 30 s – 3 min; silence reads as a hang. The skill emits **one bracketed stage line per phase**; the orchestrator drives a live checklist from them and **never relays the raw tags to chat** (per [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Suppression rule*). Tag namespaces the skill owns: `[pptx`, `[cycle`, `[html`, `[block-drop`, `[off-palette`, `[off-font]`, `[unmatched]`, `[skipped]`. Any of these reaching chat verbatim is a leak.

**Rules:** emit a line at every phase boundary (after pre-process, deck built, CONTROL, each FEEDBACK batch, each REGENERATE); chunk slow phases and report between chunks (*"Reviewing slides 10 of 29…"*, *"Built 12 of 29…"*); **any phase quiet > 30 s emits a heartbeat**, and > 60 s of total silence is a defect. Strict cycles 2+ prefix every line `[cycle N/3] <PHASE>`; `html-strict` uses `[html]` / `[cycle N/2] <PHASE>`.

**Checklists** (orchestrator shows these, ticking `[ ]`→`[⟳]`→`[✓]`, `[—]` skipped, `[✗]` failed):

```
pptx-strict:                     pptx-free-form:            html-strict:
  [ ] Formatting source            [ ] Formatting source      [ ] Formatting source
  [ ] Building draft slides        [ ] Building slides        [ ] Rendering the deck
  [ ] Reviewing slides (cyc N/3)   [ ] Sanity check           [ ] Reviewing slides (cyc N/2)
  [ ] Applying fixes                                          [ ] Applying fixes (surface)
  [ ] Final check                                             [ ] Ready to view
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

Earlier iterations tried three *CLI-only, from-scratch* paths — **all abandoned**. This is about building a deck **without** the native `pptx` skill; the native skill's own `python-pptx`-from-base-template workflow is the sanctioned path.

| Attempt | Outcome |
|---|---|
| Hand-rolled `python-pptx` from a blank `Presentation()` | Brittle parsing, theme reimplementation, fails Keynote import. |
| Marp CLI | Required migrating `final.md` to Marp syntax — a change to the source of truth. |
| `pandoc --reference-doc` | Template-layout name mismatch → default theme; dividers split; tables dropped silently. |

The native `pptx` skill is the only tested-good `.pptx` path. `html-strict` (Path B) needs no Cowork at all — it's deterministic code. `final.md` is plain Markdown, so a presenter who needs one-off CLI rendering can use their own toolchain; Talksmith just won't maintain that path.
