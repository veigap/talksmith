---
name: talksmith:md-to-deck
description: Render a Talk's `final.md` to a presentation. One render path — a code-rendered HTML/Reveal.js deck — plus optional PDF and editable `.pptx` exports measured from it. Optional Step 7 of the workflow; also the Step-5.5 live view from `draft.md` via `--draft`. No Cowork dependency.
---

# md-to-deck — render `final.md` to a presentation

This skill turns a Talk's cleaned `final.md` into a presentation. There is **one render** and
**two exports measured from it**:

- **RENDER — the HTML deck.** A styled **HTML / Reveal.js** deck built by code
  ([`build_html.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/build_html.py)) from the structured
  `slide-model.json`. Needs only Python + `jinja2`. This is also the **live in-progress view**
  (from `draft.md`, `--draft`) the orchestrator auto-fires at Step 5.5. **It is the deliverable
  and the source of truth for how a slide looks.**
- **EXPORT — PDF and `.pptx`, on request.** Both are *derived from the rendered deck*, not
  re-specified: a headless browser lays the deck out and
  [`export_pdf.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/export_pdf.py) prints it, while
  [`export_pptx.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/export_pptx.py) measures the
  laid-out page and rebuilds it as native PowerPoint shapes — real, editable text, not pictures
  of slides. Needs Chrome (or any Chromium); the `.pptx` also needs `python-pptx` and Pillow.

> **Why "measured" and not "rendered again".** The `.pptx` used to be authored by an LLM
> following a 1143-line prose spec that restated every geometry rule in EMU, checked by five
> OOXML audits. A card's corner radius had to be changed twice, in two languages, and verified
> by a third. Now there is one layout engine and the exports cannot disagree with it.

Every slide is classified against the shared catalog
[`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md) and rendered
as the matched template; the universal invariant (labeled enumerations → cards, never plain
bullets) always holds.

## What a render is asked for — two independent parameters

Neither is mandatory, and neither is written into `draft.md` or `final.md`: the same content can
be rendered any way at any time.

| Parameter | Values | Default |
|---|---|---|
| `formats:` | `html` (always produced) plus any of `pdf`, `pptx` | `html` |
| `style:` | the deck's visual skin: `default`, or any file under [`templates/html/styles/`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/templates/html/styles/) — currently `business`, `editorial`, `forest`, `ocean`, `sunset`, `terminal` | `default` |
| `theme:` | `light`, `dark` | `light` |

**The skin list is read from disk, never hardcoded** — `html_style.py` discovers `styles/*.css`
at import and the deck's own style button is built from the same list, so adding a file adds a
value here, in the browser, and in both exports at once. A skin overrides design *tokens* only
(colour, type, background); the layout is identical in all of them, which is why the choice is
cheap and reversible.

**`style:` and `theme:` are also runtime toggles in the HTML deck** (the style and theme
buttons). A render pins them for the *exports*, which are static files and must commit to one
look; the HTML deliverable keeps both toggles live regardless of what was chosen here.

An unknown `style:` fails render-blocking, naming the value and listing what is on disk — a
silent fallback to `default` would ship the wrong-looking deck without saying so.

> **Migrating from the old `style:` enum.** `style: the render` is accepted as a deprecated
> alias for `default` (one warning line). `style: pptx-strict` / `pptx-free-form` **fail
> loudly**, naming the replacement (`formats: html,pptx`) — those two named a whole different
> renderer, and quietly remapping them would hand back a deck that looks nothing like what was
> asked for.

**Reads `final.md`, never `draft.md` — one exception.** `final.md` is the cleaned source (image
refs inlined, `Presenter feedback` stripped by Polish). The **only** file-source exception is
`--draft` (the Step-5.5 live view), which reads the in-progress `draft.md` by design. No render
ever modifies `draft.md` or `final.md`; all transformation happens in memory or under `output/`.

## When to use

After Step 6 (Polish) completes and the presenter picks **Render** from the terminal branch. Optional — many presenters stop at the outline. (The same render also auto-runs earlier, from `draft.md`, as the Step-5.5 live view.)

---

## RENDER — the HTML deck (code render)

The render runs in **two steps: FILL, then RENDER.** The semantics live in the fill step (an
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
it is the only thing standing between a bad FILL and a shipped deck):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/degenerate_enum.py output/slide-model.json
# was the template chosen, or defaulted into? distribution + fallback + anchoring runs
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/audits/template_diversity.py output/slide-model.json
```

`degenerate_enum` and the two coverage preflights below all check the **internal consistency of a
choice already made**. `template_diversity` asks the other question — *was a richer template
available and passed over?* — which nothing used to ask, and which matters most here
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

Alongside it, four **coverage preflights** catch content that would silently vanish. None needs a rendered deck, so they guard every mode — `the render` included (advisory by default, `--strict` to fail):

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

**The explicit form** — `--model <path> --talk-root <dir> -o <out.html>` — renders an arbitrary
model to an arbitrary path, **bypassing the freshness guard** (there is no Talk to check the stamp
against). It exists for the committed style reference and for one-off renders, never for shipping a
deck: use `--talk` for anything a presenter will see.

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
  shown with `s`), and **PDF export** (`?print-pdf` → Print → **destination `Save as PDF`**, which is
  the only destination that honours the deck's `@page` size — a printer destination substitutes its
  own paper and shrink-to-fits the slide onto it). The only custom code is
  a per-slide content-fit. A discreet Light/Dark toggle (moon/sun) is top-right. Fonts are IBM Plex
  Sans/Mono (vendored, inlined). **Code panels** are drawn as a dark editor window (title bar,
  language badge) and syntax-coloured by **highlight.js** — vendored and inlined like the rest,
  but only into decks that actually carry a code panel. A snippet longer than the panel holds
  **shrinks to fit — it is never truncated**; past ~28 lines the render warns that the slide
  wants splitting.
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
- **No critique loop.** `the render` is a single-pass GENERATE — no automated FEEDBACK/critique
  cycles. The presenter reviews the deck and resolves anything by editing the source (which re-fills
  the model) and re-rendering.
- **Landing page.** Every `the render` render (deliverable *and* Step-5.5 live view) also rewrites
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

The rest of this file (Path A) does not apply to `the render`.

---

## EXPORT — PDF and `.pptx` (measured from the rendered deck)

Runs only when `formats:` asks for them, and only **after** RENDER has written
`output/html/index.html` — both take that file as their input, not `final.md` and not the model.
Neither re-derives anything: they lay the finished deck out in a headless browser and take what
it draws.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/export_pdf.py  --talk talks/<Talk> [--style <skin>] [--theme dark]
python3 ${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/export_pptx.py --talk talks/<Talk> [--style <skin>] [--theme dark]
```

Each prints its output path on stdout and its progress on stderr, the same contract as
`build_html.py`. Both are safe to re-run and never touch `draft.md`, `final.md` or the model.

**PDF** drives Reveal's own print view straight to paper-less paper: one page per slide at exactly
960x540 pt, vector, with selectable text and embedded font subsets. Not a stack of screenshots.

**`.pptx`** is the deck *measured*. `templates/html/harvest.js` walks the laid-out page and reports
a display list — boxes with their fills, radii and per-side accent borders; text with its styled
runs; pictures at their painted rect — and `export_pptx.py` rebuilds it as native shapes. What
that buys, concretely:

- **The text is real text.** Editable runs, with bold/italic/strike/colour/links intact, one
  textbox per block. Speaker notes land in the notes pane.
- **The code panel survives whole** — dark ground, window chrome, and highlight.js's per-token
  colours, because those are read off the rendered page rather than re-implemented.
- **Fonts are substituted in the browser, before layout** (`_EXPORT_FONT_CSS`), so the deck's fit
  pass measures the same metrics PowerPoint will re-wrap with. See *Rules* below.
- **The roadmap still navigates:** `#sec-N` anchors become real slide jumps.

Known limits, reported as warnings rather than hidden: video and YouTube embeds become a dark
poster (a `.pptx` cannot play them); a missing image's placeholder is approximated as a flat fill;
CSS gradients used as backgrounds are approximated.

**Prerequisites.** Chrome or any Chromium (probed in `_chrome.py`; `$TALKSMITH_CHROME` overrides),
plus `python-pptx` and Pillow for the `.pptx`. Missing Chrome fails the *export* with a message
naming what was probed — it never fails the HTML render, which is the deliverable.

## Output layout

```
talks/<Talk>/
├── draft.md                      # working file (Steps 1–5) — read-only here (except --draft)
├── final.md                      # source for this skill (cleaned by Polish)
├── images/                       # populated by diagram-illustrator + editor (Step 6)
└── output/
    ├── slide-model.json          # GENERATED by FILL (never hand-edited); carries a `_source` freshness stamp
    ├── slide-model.draft.json    # GENERATED in-progress model (--draft live view)
    ├── html/                     # THE DELIVERABLE — index.html + .icons/ + .render.json (the stamp the landing page reads)
    ├── final.pdf                 # only when `formats:` includes pdf
    ├── final.pptx                # only when `formats:` includes pptx
    └── .export/                  # scratch sprite sheets from the .pptx export (git-ignored)
```

Plus one file **outside** the Talk, at the working-directory root: `index.html` — the landing page
listing every rendered Talk (see *Landing page* above).

**One deck, one name.** The old style-suffixed `final.<style>.pptx` scheme existed because two
`.pptx` styles were two different renderers whose output had to be compared side by side. A skin
is a token override of one render, so there is nothing to compare: to see another skin, re-render
with it. The HTML deliverable carries every skin at once anyway, on a button.

## Progress reporting (log-only)

Rendering runs 30 s – 3 min; silence reads as a hang. The skill emits **one bracketed stage line per phase**; the orchestrator drives a live stage rail from them and **never relays the raw tags to chat** (per [`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Suppression rule*). Tag namespaces the skill owns: `[html`, `[pdf`, `[pptx`, `[classify`, `[block-drop`, `[unmatched]`, `[skipped]`, `[fallback]`, `[dominance]`, `[composition]`, `[run]`, `[format-flat]`, `[no-alternative]`, `[degenerate-enum]`. Any of these reaching chat verbatim is a leak.

**Rules:** emit a line at every phase boundary (after FILL, after the model audits, after the classification critique, after the render, after each export); chunk slow phases and report between chunks (*"Double-checking layouts, 18 of 34…"*); **any phase quiet > 30 s emits a heartbeat**, and > 60 s of total silence is a defect.

**Suppression vocabulary — what must never reach chat verbatim.** Beyond the bracketed tags: phase names (CONTROL / FEEDBACK / REGENERATE / GENERATE), audit/script names (`audits/block_coverage.py`, `audits/notes_coverage.py`, `audits/degenerate_enum.py`, `audits/template_diversity.py`, `audits/field_coverage.py`, `audits/text_coverage.py`, `export_pptx.py`, `harvest.js`), the internal vocabulary of classification (template ids like `concept-breakdown` / `content+cards+image`, `slide-model.json`, `_choice`, `slide-classifier-critic`, the verdicts `confirm`/`reclassify`/`weak-trace`), library/tool names (`python-pptx`, Pillow, Chrome/Chromium, headless, `cairosvg`, libreoffice, pdftoppm), XML internals (`<p:bg>`, `<a:srgbClr>`, `<p:pic>`, OOXML, `ppt/media/…`, `[Content_Types].xml`), EMU coordinates, and the mechanics of the export itself (display list, harvest, `--dump-dom`), rubric-row format (`slide N · <catalog-id> · …`), and the phrases *"final.md frontmatter"* / *"draft.md frontmatter"*. Translation pattern: name the *outcome* (what got fixed, how many, which slides — slide numbers are presenter-actionable and stay); strip the *mechanism* (which audit, XML element, library, phase tag). **Don't:** *"Harvested the display list via --dump-dom and rebuilt 1,283 nodes as OOXML shapes; two slides carry a `<p:pic>` poster because a `<video>` has no PowerPoint equivalent."* **Do:** *"The PowerPoint file is ready. Two slides have a video that only the HTML deck can play — they show a still instead (slides 71 and 72)."*

**Stage rails** — the orchestrator renders these as a one-line rail and edits it in place; glyphs and rules are its own (`orchestrator.md` → *Interaction defaults* → *stage rail*). This skill owns only the stage names:

```
render:            Formatting source → Choosing slide layouts → Double-checking layouts → Rendering the deck → Ready to view
+ pdf:             … → Printing the PDF
+ pptx:            … → Measuring the deck → Building the PowerPoint
```

The export stages append to the render's rail rather than replacing it — the deck is finished and
viewable before either export starts, so a slow export never reads as a stalled render.

*Choosing slide layouts* is FILL + the model audits; *Double-checking layouts* is the per-slide
classification critique (Step 1.6), which is the slow one on a long deck — chunk it
(*"Double-checking layouts, 18 of 34…"*). The `--draft` live view skips both extra stages and keeps
the original three-stage rail. Report the outcome in presenter language: **"adjusted the layout on
4 slides (7, 12, 20, 28)"**, never the verdict vocabulary or a template id.

"Ready to view" = `index.html` on disk under `output/html/`; open it (Reveal deck: → / ← advance, `Esc` overview, `F` full screen, `s` speaker notes, `?print-pdf` to export PDF — pick `Save as PDF` as the print destination, or the paper size overrides the deck's 16:9 page).

## Rules

- **Never modify `final.md`/`draft.md`.** All work is in memory or `output/…`. `the render --draft` reads `draft.md` read-only.
- **Never re-render SVGs.** A missing SVG ref → stop, the orchestrator dispatches the Diagram-Illustrator.
- **Speaker notes** go into the Reveal `<aside class="notes">` (Path B) / the notes pane (Path A), never on the slide body.

Path A adds four more (base template, system fonts, spec-as-contract) — in [`pptx-render.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/pptx-render.md) → *Rules (Path A)*.

## Failure modes to surface

- **`style:` missing** → `[pptx 0/8] FAILED: style: invocation parameter missing …`; do not default.
- **Style resolution failed** — value not a directory under `config/pptx-styles/`, or a resolved path missing → surface verbatim.
- **`final.md` not produced / still has `Presenter feedback` or raw ASCII fences**, or the path points at `draft.md` → stop; return to Step 6 / ask.
- **Stale / unstamped `slide-model.json`** → the render is refusing an outdated model (Path B exit 2; Path A `check` exit 3). This is the freshness guard working — **re-run FILL + `model_freshness.py stamp` from the current source**, then re-render. Never bypass with `--allow-stale` to ship a deck (it exists only for deliberate ad-hoc renders).
- **FILL failed / produced no model** → stop the render and surface it; do **not** fall back to a pre-existing `slide-model.json`.
- **the render render error** (Path B) → report the deck/live view is unavailable (never fatal).

The `.pptx`-only failure modes (pptx skill unavailable, base template, CONTROL audits, OOXML, agenda capacity) are in [`pptx-render.md`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/pptx-render.md) → *Failure modes to surface (Path A)*.
