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
  (its *Match* rules) — set `template`, **and record the walk in `_choice`** (signals, ≥2
  candidates, the pick, the catalog rule rejecting each other candidate; contract in the schema's
  *The classification trace*);
- **decompose** the body into exactly that template's **required fields** (e.g. `stat` →
  `stats:[{value,caption}]`; `concept-breakdown` → `cards:[{label,body}]`; `value-columns` →
  `columns:[{header,cells}]`) — splitting a metric from its caption, grouping symmetric blocks into
  columns, honouring the universal invariant (labeled sets → cards, never bullets), and **consuming
  the separator** when splitting `- **Label**: body` (it belongs to neither side — see the schema's
  *colon lead-ins* rule);
- lift every `### Speaker notes` block **verbatim** into `notes` (never onto the slide face), and
  set `section` to the section the slide belongs to.
The judgment is the LLM's, against a fixed field contract. Write to
`talks/<Talk>/output/slide-model.json` (or `slide-model.draft.json` for `--draft`).

> **Fill one section at a time, not the deck in one pass — and re-read the catalog's
> *Classification procedure* at the head of each batch.** Classifying 40 slides inside a single
> generation puts the catalog at the top of the context and the model's own accumulating output
> everywhere else; by the back half, the strongest prior is not the catalog but the twenty
> templates already written, and each `concept-breakdown` emitted makes the next one likelier.
> That anchoring is what produces a deck collapsed onto one template. Batching by section breaks
> the loop: each batch restarts from the walk, and the batches stay short enough that the
> discriminators are still the salient thing in context. Assemble the batches into one
> `slides` array in document order — the batching is a working discipline, not a change to the
> output, which is a single `slide-model.json`.

> **Copy the author's inline markup verbatim too — it is resolved, not shipped as characters.**
> Every text field of every template accepts `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``,
> `[title](url)`, a **naked `https://…`** and a **schemeless `app.sli.do/event/x`** (a dotted host
> followed by a path); the render turns each into markup (links open in a
> new tab, styled as `.mdlink`). Speaker notes take the same grammar and additionally keep their
> paragraph breaks. So do not strip marks while decomposing, and do not flatten a URL to plain
> text — a citation that arrives as an address must leave as a working link. The contract, and the
> `[title](url)`-over-bare-URL preference, live in the schema's *Inline markup survives* rule; the
> grammar itself is implemented once in [`html_style.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/html_style.py)
> (`_inline_md`) and styled once in `templates/html/theme.css`. **Block** markdown inside a field
> (headings, lists, tables) is *not* resolved — structure belongs to the model's fields. The one
> field excluded from all of it is `code`, whose bytes are the content.

> **Copy every image `src` verbatim — extension included.** A `final.md` ref to
> `images/<name>.svg` fills the model as `images/<name>.svg`. This render **inlines SVG as vector
> markup**; silently substituting the `.png` companion downgrades the diagram to a raster and is a
> render defect. The `.svg`-forbidden rule in *Prerequisites (Path A)* below belongs to the `.pptx`
> path alone — it is a prerequisite check on `final.md`, never an instruction for this fill step.

**`slide-model.json` is a generated artifact, refreshed every render — never a hand-maintained
file.** FILL always runs from the *current* source immediately before RENDER; a renderer must never
consume a model left over from a prior source. Right after writing the model, **stamp it** with the
source digest so the render step can prove freshness:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py stamp --talk talks/<Talk>          # final.md → slide-model.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py stamp --talk talks/<Talk> --draft  # draft.md → slide-model.draft.json
```

This writes a `_source` block (`{file, sha256, bytes}`) into the model. **If FILL fails, stop the
render and surface the failure — do not fall back to an existing model.**

**Step 1.5 — CHECK the model (deterministic floor, before RENDER).** The FILL judgment is the
LLM's, so it can slip; this is the mechanical catch, run on the model alone (no `.pptx` needed —
it guards every mode, including html-strict, which otherwise runs no deck-parsing audit):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/degenerate_enum.py output/slide-model.json
# was the template chosen, or defaulted into? distribution + fallback + anchoring runs
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/template_diversity.py output/slide-model.json
```

`degenerate_enum` and the two coverage preflights below all check the **internal consistency of a
choice already made**. `template_diversity` asks the other question — *was a richer template
available and passed over?* — which nothing used to ask, and which matters most in `html-strict`
(CONTROL is `audit-none`, FEEDBACK is `no-critique`, so an unexamined model shipped straight to the
deck). It **fails** on any `fallback` slide (the catalog defines it as "nothing matched": either the
walk missed a signal or the catalog needs an entry — resolve which). Its other findings are
**advisory** and are the worklist for Step 1.6, never an instruction to rewrite a choice:
`[dominance]` one template over 40% of content slides (15% for `content-text`/`fallback`),
**`[composition]`** more than half the deck *looking* the same, `[run]` 4+ consecutive slides on one
template, `[format-flat]` every `concept-breakdown` composed the same way, `[no-alternative]` slides
whose `_choice` names fewer than two candidates.

> **`[composition]` is the one that catches the monotony a per-template count misses.** The catalog
> groups templates by what a slide *does*; a deck reads as monotonous by what its slides *look
> like*, and the two do not coincide. `content+cards+image` is `concept-breakdown` with a picture
> beside it — different families in the catalog, the same grid of labeled cards on screen. A real
> 54-slide deck held 18 of the first and 11 of the second: **54% card grids with nothing above
> 33%**, so every per-template threshold passed while the audience saw one slide repeated. So
> dominance is checked twice, per template and per composition group, and the report always prints
> the composition rollup — read that line before the template table. **Diversity is not
the goal** — a deck genuinely made of labeled sets *is* mostly `concept-breakdown`, and forcing
variety classifies slides into templates their content can't support. The finding says *re-examine
this*, and Step 1.6 is what re-examines it. Pass `--warn-only` for the `--draft` live view.

Alongside it, four **coverage preflights** catch content that would silently vanish. None needs a rendered deck, so they guard every mode — `html-strict` included (advisory by default, `--strict` to fail):

```bash
# fields the chosen template will ignore (e.g. an image on a `divider`, a second image on `content-image`)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/field_coverage.py output/slide-model.json
# image refs in final.md that never made it into the model (a slide would render with no image)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/image_coverage.py final.md output/slide-model.json
# lines of final.md the model does not carry — the content the deck will simply never show
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/text_coverage.py final.md output/slide-model.json --strict-notes
# `### Speaker notes` blocks and callouts that never reached their slide's model entry
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/notes_coverage.py output/slide-model.json --source final.md
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/block_coverage.py output/slide-model.json --source final.md
```

`field_coverage` flags a **misclassification** (the field belongs, the template doesn't render it → re-classify the slide). `image_coverage` flags a **dropped image ref** (re-add it to the model, or waive an intentional omission with `<!-- deck-omit: <path> -->` in `final.md`). Both are advisory (exit 0 + a stderr list) so an in-progress `--draft` model isn't blocked; surface the list and fix before the deliverable render. `image_coverage` reads `final.md` — skip it, and the three below, for the `--draft` live view (which fills from `draft.md`).

`text_coverage` is the one that enforces the schema's hardest rule, **[*Never drop content*](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)**: every load-bearing line of `final.md` has to be translated into the model, and an LLM decomposition drops clauses silently — the model stays valid, every other audit stays green, and the slide ships missing the sentence that disambiguated it. A line counts as present when any five consecutive words of it survive anywhere in the model. The `_choice` trace is excluded from the search on purpose: its rationale quotes the source, so counting it would let the classification alibi the drop.

> **Notes and body prose are read differently, and the difference is the whole point.** `notes` is copied **verbatim** — it never competes for room on screen, so compressing it can only lose — which makes a missing notes line unambiguous, and `--strict-notes` (above) **fails the step on one**. Body prose is *decomposed*, and decomposition legitimately rewrites: two prose bullets folded into a comparison table keep every idea while changing every word. So a body line with no literal match is sorted into `[text-drop]` (its distinctive words are absent too — nothing of it is on the deck) or `[text-rewritten]` (its words are all there in another shape), and only the first counts. Rewrites are hidden unless `--show-rewrites`. Without that split roughly nine in ten body rows on a real deck are innocent, and a report that cries wolf is a report the presenter stops reading. Fix a real drop by moving the line into a field, a card, a fact or `highlights`; fix a notes drop by **copying the block over verbatim instead of summarizing it**; waive a deliberate omission with `<!-- deck-omit-text: <substring> -->`.

`notes_coverage --source` and `block_coverage --source` are the same two audits that run at CONTROL against a `.pptx`, pointed one step earlier at the model: a `### Speaker notes` block that never reached `notes`, and a callout the fill left with nowhere to land. Both take `--source` implicitly from the model's freshness stamp, so `--source` can be omitted on a stamped model.

> **A source block is classified against the template its slide resolved to, not in the abstract.** On a `quote` slide the blockquote *is* the slide — it lands in the `quote` field, which is not a callout slot — so reading it as an aside reports a drop on every correctly filled quote slide. And a **markdown table is audited cell by cell**: the source row is row-major, `value-columns` and `matrix` store it column-major, so no run of a row's words is ever consecutive in the model however completely its cells survived. Both were false positives that fired on every deck that had the shape, which is worse than a missing check — it teaches the reader to skim the line where a real drop appears.

> **All three match a slide by title *or* by its text.** `quote`, `big-number`, `image-grid`, `quiz` and `callout` carry no `title` field at all (see the schema's per-template contract), so a title-only match reports every slide of those templates as unmatched — permanent noise in exactly the line (`[unmatched]`) where a genuinely missing slide would appear. When the title does not resolve, the audits look for a distinctive run of the source slide's words and match the one model slide that carries it.

A non-zero exit from `degenerate_enum` is a FILL failure, not a render failure: an enumeration template
(`content-text` panels, `concept-breakdown` cards, `stat` stats, `process` steps, …)
was filled with a **single** item, which renders as a stray grid cell — the tell of a
misclassification (a lead + one point is `single-point`, per the catalog's `labeled_items == 1`
rule). Surface the FAIL line, **re-classify that slide in the model**, and re-check before
rendering. Skip with `--warn-only` only for the `--draft` live view, where an in-progress model is
expected to be incomplete.

**Step 1.6 — CLASSIFY-REVIEW (the independent critique, LLM).** The deterministic checks above can
only spot *shapes* — a one-item enum, an ignored field, a template holding half the deck. They
cannot tell a slide that is rightly a `concept-breakdown` from one that was never walked. That
judgment needs a second reading of the content, and it has to be **independent** of the pass that
made the choice: a fill that anchored on its own output will re-confirm that output, because the
same accumulated context is what produced it.

Dispatch the [`slide-classifier-critic`](${CLAUDE_PLUGIN_ROOT}/agents/slide-classifier-critic.md)
**once per content slide, in parallel**. Each critic gets one slide's `source` unit (verbatim from
`final.md`/`draft.md`), its `template`, its `_choice`, its `position`, `deck.sections` and the
presentation language — and **nothing about any other slide's classification**. That blindness is
the mechanism, exactly as it is for the `diagram-critic`: a critic that can see the deck is
`concept-breakdown` twenty times over reads the twenty-first as normal. Skip the frame templates
(`section-agenda`, `divider`, `closing-hero`, `closing-cta`) — those are positional, not content
choices, and the cover is synthesized.

Each returns one JSON verdict — `confirm`, `reclassify`, `format`, or `weak-trace` — with the
catalog rule it applied. Then:

| Verdict | What you do |
|---|---|
| `confirm` | Nothing. This is the expected majority — a repeated template that survives an independent walk is a correct classification, not a defect. |
| `reclassify` | The critic named a catalog rule the pick violates. **Re-classify that slide in the model** and re-decompose its body into the new template's required fields (a template change is a field change — a `process` becoming a `timeline` needs `milestones`, not `steps`). Update `_choice` to the walk that now holds. |
| `format` | Set the `concept-breakdown` `format` the critic gives. No re-decomposition — the fields are the same. |
| `weak-trace` | The pick stands but the trace doesn't support it. Rewrite that slide's `_choice` with the walk you can actually defend; if you can't, it was a `reclassify` the critic was too generous about. |

Re-run `degenerate_enum` + `template_diversity` + `field_coverage` after applying any change — a
re-classification moves fields, and moved fields are exactly what those audits check. **One pass
only:** re-dispatching critics over the slides you just edited buys little and risks churning a
slide between two defensible templates. Report the counts in the render log
(`N confirmed, M re-classified, K format, J weak-trace`) and surface any `reclassify` you chose not
to apply, with the reason.

**Skip this step for the `--draft` live view.** The draft model is expected to be in flux and the
live view re-renders on every review; the critique belongs to the deliverable render, where the
classification is what ships.

**Step 2 — RENDER (mechanical, deterministic).** [`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)
loads the model and maps each slide's fields onto its Jinja template — no parsing, no classification:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py --talk talks/<Talk>          # output/slide-model.json → deliverable
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py --talk talks/<Talk> --draft  # output/slide-model.draft.json → live view
```

**Built-in freshness guard.** In `--talk` mode `build_html.py` re-verifies the model's `_source`
stamp against the current `final.md`/`draft.md` before rendering and **refuses (exit 2) on a stale
or unstamped model** — it never silently renders an outdated one. So if FILL+stamp ran (as it always
should, immediately before), the render proceeds; if the source changed underneath a stale model, it
stops with a clear message telling you to re-run FILL. (`--model` direct mode — the committed style
test — has no resolvable source and is exempt; `--allow-stale` is the explicit override.)

**Built-in coverage warning.** The freshness guard proves the model was filled from *this*
source; it says nothing about whether the fill kept the source's content. So in `--talk` mode
`build_html.py` also runs the source stage of all three coverage audits (`text_coverage`,
`notes_coverage`, `block_coverage`) and prints what `final.md` says that the model does not carry.
It **warns, never blocks** — the deck renders and is delivered; the presenter decides whether a
flagged line matters. Surface the lines (never the audit's name — see the suppression vocabulary)
and offer to re-fill those slides. `--no-coverage` skips it.

> **`[html] BUG:` is not a deck problem.** If that line appears, the coverage pass itself failed
> to run and the render is **unchecked** — the deck below it was never compared against the
> source. It means a defect in the plugin (this exact pass once sat broken for two releases behind
> a `TypeError` that printed as an ordinary "skipped" warning). Do not report it as a content
> finding: run the three audits by hand, and log it per `${CLAUDE_PLUGIN_ROOT}/schemas/talksmith-bugs.md`.
> A plain `coverage check skipped` line, by contrast, is benign — an unreadable or malformed file.

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
  **`jinja2` is the only non-stdlib dependency, and the commands here say bare `python3`** — on a
  machine with more than one interpreter (a Homebrew python and the system one, a venv that isn't
  active) PATH can hand the render the one without it. That failure now names itself: the render
  prints the missing module, the interpreter it actually ran under, and the `-m pip install`
  command for that interpreter. Verify any candidate up front with `<python> -c "import jinja2"`.
- **Is the deck on disk still current?** One cheap check — a hash, no FILL, no LLM:
  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py rendered --talk talks/<Talk>
  ```
  Exit `0` current · `3` stale · `4` can't tell · `2` nothing rendered. Every render copies the
  model's `_source` binding into `output/html/.render.json`, so this compares the rendered deck
  against the markdown as it stands now. It exists because a live-view refresh is a full FILL pass
  and therefore gets skipped: without this, a stale deck is indistinguishable from a current one.
  A stale deck is also badged **out of date** on the working-directory landing page.
- **No critique loop.** `html-strict` is a single-pass GENERATE — no automated FEEDBACK/critique
  cycles. The presenter reviews the deck and resolves anything by editing the source (which re-fills
  the model) and re-rendering.
- **Landing page.** Every `html-strict` render (deliverable *and* Step-5.5 live view) also rewrites
  `index.html` **at the working-directory root** — a card per rendered Talk, linking to its deck
  ([`build_index.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_index.py)). A deck buried at
  `talks/<Talk>/output/html/index.html` is unfindable and unshareable; the root page is the one link
  the presenter keeps. The whole set is re-scanned on every render, so it self-heals if deleted and
  older Talks keep their cards; each render leaves a `output/html/.render.json` stamp (mode + deck
  metadata + slide count) that the scan reads. Live views are listed with an *in progress* badge.
  **It never clobbers a hand-written page:** a root `index.html` without Talksmith's
  `<!-- talksmith:index -->` marker is left alone and the page goes to `talksmith-index.html`
  instead. Failure here is logged, never fatal — the deck is still delivered. Regenerate on demand
  with `python3 build_index.py --root .`.

The rest of this file (Path A) does not apply to `html-strict`.

---

## Path A — native `.pptx` (`pptx-strict`, `pptx-free-form`)

**This path is a thin orchestrator over the official `pptx` skill.** All `.pptx` authoring goes through [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx), which authors the deck **programmatically with `python-pptx`** starting from a working copy of the style's `base-template.pptx` (`Presentation(<base_template_path>)`). "Delegate to the pptx skill" means **drive that skill's `python-pptx` workflow from the base template + visual spec** — writing `python-pptx` that way is the mechanism, not a workaround.

**Forbidden** is *bypassing* that path: authoring from a blank `Presentation()`, reimplementing the theme, or using another tool (`pandoc`, Marp, hand-written XML) — all abandoned because they fail Keynote import (see *Why Cowork-only*). A generator that starts from `base-template.pptx`, substitutes the cover, and builds each slide per the visual spec is the **correct** render.

**The base template is mandatory and non-negotiable.** `pptx-strict`'s is a 15-slide foundation (cover + agenda + 12 layout-reference slides + 1 divider example); the renderer substitutes placeholders, deletes the layout-reference zone (slides 3–15), and inserts content per `<spec_path>`. `pptx-free-form`'s is a 1-slide cover-only foundation; it substitutes the cover's four §2 placeholders, then designs every other slide fresh per its §3. Decks built from scratch are a render failure in either style.

**Single responsibility.** This skill prepares the inputs and invokes the pptx skill. ASCII → SVG is the Diagram-Illustrator's job (Step 6, before this runs); `final.md` arrives cleaned with every referenced image already under `talks/<Talk>/images/`.

### Prerequisites (Path A)

| Prereq | What to check | If missing |
|---|---|---|
| [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) in registry | Skill list includes `pptx` | Stop. Tell the presenter to run inside Cowork. No CLI fallback. |
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
- **Base template** = `<base_template_path>` (opened as a working copy, not a theme reference; presenter override optional — the legacy `pptx-strict/template.pptx` 53-slide reference is **not** a valid override).
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

## Output layout

```
talks/<Talk>/
├── draft.md                              # working file (Steps 1–5) — read-only here (except html-strict --draft)
├── final.md                              # source for this skill (cleaned by Polish)
├── images/                               # populated by diagram-illustrator + editor (Step 6)
└── output/
    ├── slide-model.json                 # GENERATED by FILL (never hand-edited) — HTML + PPTX both render from it; carries a `_source` freshness stamp
    ├── slide-model.draft.json            # GENERATED in-progress model (html-strict --draft live view)
    ├── final.pptx                        # canonical deliverable — a copy of the most recent .pptx render
    ├── final.pptx-strict.pptx            # per-mode .pptx render, persists for comparison
    ├── final.pptx-free-form.pptx
    ├── .critique/                        # critique-only slide previews for the .pptx modes (git-ignored)
    │   ├── pptx-strict/slide-NN.png
    │   └── pptx-free-form/slide-NN.png
    └── html/                             # html-strict deck — index.html + .icons/ (build_html.py; final or draft model)
                                          #   + .render.json (render stamp read by the root landing page)
```

Plus one file **outside** the Talk, at the working-directory root: `index.html` — the landing page
listing every rendered Talk (see *Landing page* above).

**Per-mode isolation.** Each `.pptx` render writes a suffixed deck `output/final.<style>.pptx` (with its `.critique/<style>/` PNGs), so strict and free-form renders coexist; the latest is copied to the canonical `output/final.pptx`. Each slide's chosen `template` lives in the shared `slide-model.json`. `html-strict` writes only under `output/html/`.

## Progress reporting (log-only)

Rendering runs 30 s – 3 min; silence reads as a hang. The skill emits **one bracketed stage line per phase**; the orchestrator drives a live stage rail from them and **never relays the raw tags to chat** (per [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Suppression rule*). Tag namespaces the skill owns: `[pptx`, `[cycle`, `[html`, `[classify`, `[block-drop`, `[off-palette`, `[off-font]`, `[unmatched]`, `[skipped]`, `[fallback]`, `[dominance]`, `[composition]`, `[run]`, `[format-flat]`, `[no-alternative]`, `[degenerate-enum]`. Any of these reaching chat verbatim is a leak.

**Rules:** emit a line at every phase boundary (after pre-process, deck built, CONTROL, each FEEDBACK batch, each REGENERATE); chunk slow phases and report between chunks (*"Reviewing slides 10 of 29…"*, *"Built 12 of 29…"*); **any phase quiet > 30 s emits a heartbeat**, and > 60 s of total silence is a defect. Strict cycles 2+ prefix every line `[cycle N/3] <PHASE>`; `html-strict` uses `[html]` (single pass, no cycles).

**Suppression vocabulary — what must never reach chat verbatim.** Beyond the bracketed tags: phase names (CONTROL / FEEDBACK / REGENERATE / GENERATE), audit/script names (`audits/palette_fonts.py`, `audits/block_coverage.py`, `audits/aspect_ratios.py`, `audits/cover_fidelity.py`, `audits/layout_fit.py`, `audits/degenerate_enum.py`, `audits/template_diversity.py`, `audits/field_coverage.py`, `audits/text_coverage.py`), the internal vocabulary of classification (template ids like `concept-breakdown` / `content+cards+image`, `slide-model.json`, `_choice`, `slide-classifier-critic`, the verdicts `confirm`/`reclassify`/`weak-trace`), library/tool names (`python-pptx`, `cairosvg`, `qlmanage`, `pandoc`, Marp, libreoffice, pdftoppm), XML internals (`<p:style>`, `<p:bg>`, `<a:srgbClr>`, `<p:pic>`, OOXML, `ppt/media/…`, `[Content_Types].xml`), slide-XML coordinates (EMU values), rubric-row format (`slide N · <catalog-id> · …`), and the phrases *"final.md frontmatter"* / *"draft.md frontmatter"*. Translation pattern: name the *outcome* (what got fixed, how many, which slides — slide numbers are presenter-actionable and stay); strip the *mechanism* (which audit, XML element, library, phase tag). **Don't:** *"Three issues were caught and fixed during CONTROL: a palette false-positive from python-pptx's `<p:style>` boilerplate (stripped), the cover logo relationship (corrected to embed image-1-1.png directly), and 4 slides with missing callout shapes (slides 9, 12, 24, 27 — callouts added)."* **Do:** *"Checked the deck and applied 3 small automatic fixes (a palette check, the cover image, and 4 slides where a block needed re-adding — 9, 12, 24, 27). Done."*

**Stage rails** — the orchestrator renders these as a one-line rail and edits it in place; glyphs and rules are its own (`orchestrator.md` → *Interaction defaults* → *stage rail*). This skill owns only the stage names per mode:

```
pptx-strict:      Formatting source → Choosing slide layouts → Double-checking layouts → Building draft slides → Reviewing slides (N/3) → Applying fixes → Final check
pptx-free-form:   Formatting source → Choosing slide layouts → Double-checking layouts → Building slides → Sanity check
html-strict:      Formatting source → Choosing slide layouts → Double-checking layouts → Rendering the deck → Ready to view
```

*Choosing slide layouts* is FILL + the model audits; *Double-checking layouts* is the per-slide
classification critique (Step 1.6), which is the slow one on a long deck — chunk it
(*"Double-checking layouts, 18 of 34…"*). The `--draft` live view skips both extra stages and keeps
the original three-stage rail. Report the outcome in presenter language: **"adjusted the layout on
4 slides (7, 12, 20, 28)"**, never the verdict vocabulary or a template id.

`html-strict` "Ready to view" = `index.html` on disk under `output/html/`; open it (Reveal deck: → / ← advance, `Esc` overview, `F` full screen, `s` speaker notes, `?print-pdf` to export PDF).

## Rules

- **Base template is mandatory** (Path A, Keynote-compat): `Presentation(<base_template_path>)`, never blank. Scratch decks fail Keynote import (no master/layout/theme chain). Enforced by `audits/cover_fidelity.py`.
- **System fonts only** (Path A, Keynote-compat): every `<a:latin>` must resolve to a font on the import target (Arial / Helvetica / Courier New on the macOS/Keynote path). Custom fonts (Roboto, Consolas, …) fail import even with valid OOXML. Enforced by `audits/palette_fonts.py`. (Path B embeds its own IBM Plex fonts as data-URIs — HTML, not Keynote, so this does not apply.)
- **The spec is the contract** (Path A): pass `<spec_path>` verbatim to the native renderer; if it's ignored, that's a render failure — rerun, don't patch post-hoc.
- **Never modify `final.md`/`draft.md`.** All work is in memory or `output/…`. `html-strict --draft` reads `draft.md` read-only.
- **Never re-render SVGs.** A missing SVG ref → stop, the orchestrator dispatches the Diagram-Illustrator.
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
- **Stale / unstamped `slide-model.json`** → the render is refusing an outdated model (Path B exit 2; Path A `check` exit 3). This is the freshness guard working — **re-run FILL + `model_freshness.py stamp` from the current source**, then re-render. Never bypass with `--allow-stale` to ship a deck (it exists only for deliberate ad-hoc renders).
- **FILL failed / produced no model** → stop the render and surface it; do **not** fall back to a pre-existing `slide-model.json`.
- **html-strict render error** (Path B) → report the deck/live view is unavailable (never fatal).

## Why Cowork-only (Path A)

Every CLI-only, from-scratch path (blank `Presentation()`, Marp, `pandoc --reference-doc`) was tried and abandoned — each fails Keynote import or mangles the source of truth. The native `pptx` skill's `python-pptx`-from-base-template workflow is the only sanctioned path; there is no CLI fallback.

The native `pptx` skill is the only tested-good `.pptx` path. `html-strict` (Path B) needs no Cowork at all — it's deterministic code. `final.md` is plain Markdown, so a presenter who needs one-off CLI rendering can use their own toolchain; Talksmith just won't maintain that path.
