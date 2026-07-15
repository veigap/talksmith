# Changelog

All notable changes to the Talksmith plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses [semantic
versioning](https://semver.org/): patch for fixes and docs, minor for new
agents/skills/commands or workflow changes, major for breaking schema or
session-start contract changes. The authoritative version is the `"version"`
field in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

> **Maintenance note (for contributors):** keep this file *useful*, not exhaustive.
> Every commit adds a functional description of what changed and why, but old
> entries get compacted as they age — collapse superseded fixes, fold noise into
> the release summary, drop detail that no longer helps a reader. Less is more.
> Releases older than the last few are compacted into milestone bands below.

## [0.59.1] — 2026-07-15

Post-restructure audit sweep: three parallel audits (cross-reference integrity, stale claims, Python bug hunt with fixture repros) over the whole plugin; every confirmed finding fixed.

### Fixed
- **`polish_ascii.py` — seven verified bugs:** a fence opener with a non-word tag or info string (```` ```c++ ````, ```` ```python title=x ````) flipped fence parity and could mint a phantom block spanning the next slide's headings (structural corruption on `cleanup`); a mid-line `-->` in an `ascii-note` (e.g. `emphasize: the input --> model arrow`) truncated the note; an in-place payload edit passed the stale-plan guard and was silently reverted (guard now compares payload byte-for-byte → exit 3); slide-boundary detection read `#`-prefixed lines *inside* fences as headings, breaking `documentation_only` and context extraction; a stale `apply` wrote sidecars before aborting (now validates first — exit 3 writes nothing); the `⇒` arrow glyph documented in the legacy heuristic wasn't detected; scan plans stored a cwd-relative `final_path` that `prepare-render-args` mis-anchored from another cwd (now resolved absolute).
- **`merge_draft.py`:** `apply-auto` landed a slide's retitle first, orphaning that slide's remaining edits on unnumbered slides (anchored by the pre-change title); retitles now apply last.
- **`pptx_inventory.py`:** the SVG-only picture fallback was dead code — link-only / SVG-only pictures were silently dropped from the inventory; the fallback is now reachable.
- **Stale docs:** `editor.md`/`schemas/draft.md` documented the no-op legacy `<!-- reveal: sequential -->` instead of the real opt-out `<!-- reveal: together -->`; `principles.md` justified the title budget with the retired Roboto Mono face; the strict spec still attributed the icon picture-shape format to Marp, overstated `template-previews/` coverage, and carried two malformed relative links; one pointer targeted `config/feedback-backlog.md` for a section that lives in `schemas/feedback-backlog.md`; three pointers named a README heading that doesn't exist (*One shared repo per subject* → *One repo per subject*); `polish-ascii` SKILL.md's "all subcommands are idempotent" and exit-code contract corrected to match actual behavior.
- **Dev-data leak:** `config/learnings.md` in the plugin repo carried a real learning entry from a development talk (already promoted into the strict spec's §15 meta-rule); reset to the canonical empty form.

## [0.59.0] — 2026-07-15

A plugin-wide **prose diet + single-source restructure**. Every spec file is LLM context, and an audit found the same facts stated in 2–9 places, plus large rationale/history blocks in high-frequency files. This release establishes an **ownership map** (now in the dev `CLAUDE.md`): every fact lives in exactly one owning file — the catalog owns template Match/Format, `schemas/slide-model.md` owns field contracts, the strict prompt owns EMU recipes, `diagram-critic.md` owns the blind-critique rationale, each skill owns its own mechanics — and every other file points there. ~17k words (~22k tokens) of restatement removed; **no rule, CLI contract, or schema form was dropped**, and the regenerated `tests/.../style-reference.html` is byte-identical.

### Changed
- **Skill descriptions** (always in session context) cut from ~1,120 to ~350 words — now concise triggers; interface detail lives in each SKILL.md body.
- **`orchestrator.md`** (loaded every session) slimmed ~12%: Step 5.5 detail now points at `md-to-deck` → *Path B*; the Step-7 suppression vocabulary + don't/do examples moved to `md-to-deck` SKILL.md → *Progress reporting*; the memory-writer contract defers to `schemas/memory.md`; repeated "Speak human" / "style is render-time" statements reduced to one each.
- **`diagram-critic.md`** (dispatched per block per critique iteration) trimmed ~16% — one tight statement of the blind-critique rule; checklist and report format intact. **`illustrator.md`** (−14%) and **`editor.md`** (−12%) now point at `diagram-critic.md` and the `polish-ascii`/`ascii-to-svg` contracts instead of restating them.
- **`pptx-strict/pptx-prompt.md`** (−1,760 words): dropped §16 "Recipes summary" and the §19.7 navigation recap; §15.5's discriminator column compacted to defer to the catalog's *Match* rules; pill/agenda-capacity/cover/icon rules now stated once at their home section.
- **`ascii-to-svg` SKILL.md** (−15%): benchmark evidence and spec-history removed; every rule kept; step 9 renamed *Aspect audit* (the anchor other files reference).
- **`polish-ascii` SKILL.md**: the plan-JSON shape is printed once; detection tiers defer to `illustrator.md`.

### Fixed
- Literal duplicated/empty table header in the strict spec's §11.
- Two stale claims: the `md-to-deck` Path-A prerequisite and the strict spec's §19.1 asset row still said icons ship inside `base-template.pptx` (§17.6 documents they never did — icons are fetched by name via `icon_fetch.py`).

### Removed
- The two duplicate copies of `_pptxlib.py`: the canonical module now lives once at `skills/_shared/_pptxlib.py`, `sys.path`-imported by the three reverse-pipeline scripts (all CLIs verified).
- ~1,240 lines of superseded changelog history, compacted into milestone bands per this file's own maintenance note.

## [0.58.2] — 2026-07-15

The SVG authoring step is the pipeline's only real cost — measured at ~36 s against 0.34 s
for every script around it, and it is bound by *output* tokens, so bytes not emitted are
seconds not spent. This release stops emitting about a fifth of them.

### Changed

- **Inheritable attributes are hoisted to the root** (`SKILL.md` step 5). `font-family`
  belongs once on the `<svg>`, not on all fifteen `<text>` children; same for `font-size`
  and `fill` where one value dominates. SVG inherits down the tree, so the render is
  unchanged — measured across the fixtures: **0 differing pixels out of 3.9M**, files
  **24.6% smaller** (~1450 tokens over seven diagrams; 19.9% of bytes across all nine once
  `fill` and `font-size` are counted).

  The rule carries the trap that makes it non-obvious: **inheritance is by tree, not by
  document order**. A `<tspan font-family="…mono">` inside a `<text font-family="Helvetica">`
  must keep its declaration even when mono is the root's value — it inherits from its
  parent. Dropping it there silently reverts an inline code span to the wrong face,
  invisible in the XML and visible only in pixels. That case exists in this repo's fixtures
  and a naive implementation of this very optimisation broke it.

  This is deliberately an authoring rule and not a cleanup pass: by the time any script
  runs, the seconds were already spent emitting the bytes, so shrinking the file afterwards
  saves nothing.

### Added

- **A hoisting lint** in `validate_svg.py` — advisory, never repaired (repairing would save
  no time, per above). It reports how many declarations a root declaration would make
  unnecessary. It measures *hoistability* by resolving the tree, not repetition: the common
  waste pattern has no root declaration at all and fifteen children restating the same
  value — nothing is redundant in the strict sense, yet all fifteen are avoidable — while
  the nested-override case above is a legitimate repeat that must not be flagged. Tests in
  `tests/skills/ascii-to-svg/test_redundant_attrs.py`.

### Investigated, no change

- **Whether `talk_thesis` / `section_goal` earn their place in the context bundle** —
  hypothesis was that ~67% of the bundle leaves no trace in the render. **No evidence
  either way, and the pixel-diff A/B cannot produce any**: a control arm (two renders from
  byte-identical input) differs from itself in **12%, 32% and 46% of pixels** depending on
  the block. That noise floor swamps the effect. Moot regardless: the bundle is **input**,
  and this step is output-bound — removing 2.1 KB of input saves ~0 s, so even a
  proven-dead field would not be worth the risk. The bundle stays as it is.

## [0.58.1] — 2026-07-15

Hardening of the blind critic, from what a nine-diagram test run actually surfaced.

### Fixed

- **A defect naming something that isn't there had no legal outcome.** A critic reported a
  gradient on a panel that was flat `#FFFFFF`. The illustrator is told to treat the verdict
  as authoritative and never check it against the XML — so obeying meant fabricating an edit
  for a non-existent element, and not obeying meant the arithmetic self-review the split
  exists to kill. There is now an `unreproducible` verdict, scoped tightly: it applies only
  when a defect's *subject* is verifiably absent from the source, never when its *judgement*
  is merely one you'd rather overrule.
- **A critic that couldn't load the standing rules failed silently.** Its output would carry
  no rule violations, which reads exactly like a diagram that has none. It now returns
  `missing_rules:` and the block is recorded `unresolved: critique_unavailable` rather than
  passing.

### Changed

- **The critic's checklist learned the two glyph traps** that were the only real defects in
  the whole test run: arrow characters rasterizing as tofu, and hyphens drawing as long
  dashes. Both make the XML look perfect and the picture lie, so the blind critic is the only
  thing that can catch them.
- **The standing-rule item no longer invites confabulated gradients** — the one false defect
  of the run. Paired with a general rule: report only what you could point at with a finger.
  The renderer cannot catch a wrong defect, by design — it acts on it.

## [0.58.0] — 2026-07-15

Step 6 (Polish) reviewed diagrams it could not actually see, and re-rendered diagrams
that hadn't changed. This release fixes both, and removes a rasterizer that was quietly
corrupting every image the pipeline produced.

### Added

- **A fixture Talk for the whole Step-6 pipeline** at `tests/skills/ascii-to-svg/` — nine
  slides lifted verbatim from production Talks, spanning 1.4:1 to 7.9:1 plus a
  no-`ascii-note` block and a legacy-tagged fence. Its `test_audit_aspect.py` holds the
  audit's real regression tests: synthetic, deliberately broken, required to *fail*.
- **Standing font rules in `config/diagram-style.md`**: arrow glyphs (`←` `→` `↑`,
  U+2190-21FF) rasterize as **tofu** — absent from the fonts cairosvg resolves — so arrows
  must be drawn as paths. And `Menlo` is a trap: it resolves, so nothing errors, but its
  hyphen draws at near-full-em width, turning `a-b` into `a–b` and fusing YAML `---` into
  one rule. Both produce a correct-looking XML and a lying picture.
- **A blind diagram critic.** Visual review of a rendered diagram now happens in its own
  `diagram-critic` subagent that receives the PNG and nothing else — no SVG path, and
  `tools: Read` so pixels are all it can reach. Previously the agent that *wrote* the SVG
  also critiqued it, which cannot work: with every coordinate already in context it
  reviewed by arithmetic rather than by eye, "confirming" text was centred by re-deriving
  the formula it had just used to place it. The critic now describes what it sees in visual
  language and the renderer, which has the coordinates, translates that into the edit.
- **A mechanical aspect audit** (`audit_aspect.py`), because one defect class is invisible
  to *any* visual review: the critique PNG is rasterized **from** the viewBox, so a viewBox
  that doesn't fit its art renders a correct-looking picture whose dead canvas reads as
  deliberate whitespace. It now surfaces at render time as an ordinary defect, with a
  suggested corrected viewBox that is a pure crop. It measures margins in viewBox units
  (ratio drift flags healthy diagrams), samples the background from the image corners
  (not hard-coded white), and claims only that the frame *fits the art* — `ok` never means
  "this was the right shape".

### Fixed

- **The viewBox contract taught the wrong method, and its self-check was a tautology.**
  Step 5 said to derive the aspect from the character grid; measured across the nine
  fixtures that diverged from the honest layout in six, by up to 2×. And the offered
  self-check (rasterize and compare) is true by construction, since the raster derives from
  the viewBox. Step 5 now says: lay out the art, measure the ink, add an even margin, and
  the viewBox is that rectangle.
- **Render idempotency was built but never armed.** `stamp-renders` — the step that writes
  the ASCII digest deciding what re-renders next pass — existed as a working subcommand but
  appeared in no sequence, so SVGs went unstamped, no digest ever matched, and every pass
  re-rendered a Talk whose ASCII hadn't changed — minutes instead of sub-second. It is now
  step 9 of the illustrator's loop.
- **`qlmanage` removed as a rasterizer.** It was the documented macOS fallback and was
  silently mangling output: `-s N` fits the art into an N×N square padded with *opaque
  white*, and its geometry disagrees with cairosvg's, placing ink 100px off at identical
  dimensions. **`cairosvg` is now required, with no fallback** — if it's missing the render
  fails and says how to install it.
- **`pip install cairosvg` was never sufficient on macOS**, which is why the fallback kept
  firing: the stock python3 can't see Homebrew's libcairo (dyld default paths exclude
  `/opt/homebrew/lib`, and SIP strips `DYLD_*`). All rasterization now goes through
  `rasterize.py`, which preloads the dylib by absolute path and re-measures every PNG
  against the viewBox before letting it reach disk.
- **`ascii-to-svg` looked for `diagram-style.md` in the wrong place** — `<repo_root>/config/`
  instead of `${CLAUDE_PLUGIN_ROOT}/config/`. The render didn't fail; it silently dropped
  the palette and reported `deviations: no diagram-style.md`.

### Changed

- **Critique cap lowered from 3 iterations to 2** (initial + 1 revision). Historically half
  the blocks land clean on the first pass and nearly all the rest on the second.
- **Diagram dispatch is a sliding window of 5, not fixed batches of 5** — a barrier parked
  up to four slots waiting on the slowest straggler.

## [0.57.0] — 2026-07-15

### Changed

- **Slides now animate by default.** Enumeration slides (`stat`, `card-row`,
  `concept-breakdown`, `icon-list`, `content+cards+image`) reveal their items one at a time
  in the HTML deck, and a slide's `highlights` arrive as one final step — so the takeaway
  lands after what it comments on. Animation used to be opt-in via `<!-- reveal: sequential -->`,
  which in practice meant decks never had any. The hint is now an opt-*out* —
  `<!-- reveal: together -->` shows a slide all at once. Old `sequential` hints keep working.
  Unchanged for `.pptx`, which is static; viewers can still switch every animation off from
  the deck's animations button.
- **The deck fills the window.** The 4% inset margin is gone, so a slide — and an `aside`
  column in particular — runs to the window's edge. Side bands in a non-16:9 window are
  letterboxing, not margin.

### Fixed

- **A slide's `aside` image column is full-bleed again.** The rules that make an inline
  figure look like a figure tied the aside's own rules on CSS specificity and quietly won.
  Note for authors: a **photo** aside crops to fill on its own, but an **SVG** aside must
  carry `preserveAspectRatio="… slice"` itself or it will letterbox.
- **Polish no longer attributes a discarded diagram to a real slide.** ASCII under
  `# Cut material`, `# Open questions`, or `# Thesis` was inherited by the preceding section —
  the scan only recognized `# N.`, `# Agenda` and `# Conclusiones` as boundaries. Any
  heading now ends a section, and ASCII under one that carries no slides is skipped and
  reported.
- **Polish no longer reuses a stale diagram, or one from another topic.** Re-render was
  decided from a filename prefix minted from position in `final.md`, which renames itself
  as soon as slides move. Each rendered SVG is now stamped with a digest of the ASCII it
  was drawn from (diagram + `ascii-note` intent), and that digest is the only thing
  consulted; an unstamped SVG re-renders rather than being trusted.

## [0.45.0 – 0.56.0] — 2026-07-13 → 2026-07-15

The HTML deck matured from a working renderer into the polished deliverable: viewer
chrome, richer slide semantics, the example talk, and the docs/workflow reorganization.

### Added

- **Aside image column.** `<!-- aside: ![alt](…) -->` under a slide heading devotes ~a third
  of the slide's width to a full-bleed edge image (right by default, `left` supported) on
  every content slide type — atmosphere, not information; readable figures stay in the body.
- **Highlights band.** Any content slide may carry `highlights` — emphasized takeaways in a
  soft accent band under the body, each with a `kind` (`takeaway`, `important`,
  `definition`, `example`, `quote`, `note`) carrying its own accent + icon; facts and
  highlights accept `{label,body}` labeled lines. The schema documents the "never drop
  content" rule: every source line is translated as a field, card, fact, or highlight.
- **`quiz` slide type.** Question + optional lettered choices shown up front; the answer
  reveals on next-nav, the named `correct` choice highlights in sync, with optional image
  and explanation. Static (visible) in `.pptx`.
- **Icons never repeat within a slide** — a distinct content-matched icon per item, with
  fill-suggested `icon` names honoured and a neutral fallback pool for unmatched labels;
  emoji stripping is a FILL rule (the matched icon stands in for the emoji).
- **Deck viewer chrome:** animations on/off toggle, PDF export and fullscreen buttons, an
  auto-hiding bottom nav cluster, and **six selectable styles** (`editorial`, `terminal`,
  `ocean`, `forest`, `sunset`, `business`) — one CSS file per style, composing with
  light/dark, persisted and shareable via `?deck-style=` / `?deck-theme=` URL params.
  Documented in the README's "Presenting the HTML deck" section.
- **Optional author hints in `draft.md`:** `<!-- template: <type> -->` and `<!-- reveal: … -->`
  under a slide heading — Polish copies them through and the FILL honours them (the only
  HTML comments read rather than dropped).
- **Example talk fixture** [`tests/examples/talksmith-intro/`](tests/examples/talksmith-intro/):
  a complete ~40-min talk *about* Talksmith exercising nearly every slide type, with its
  rendered HTML deck committed and linked from the README; its slide notes are written as
  documentation, not stage directions.
- **Institution logo setup.** Setup asks for your logo; drop it at `config/logo.*` and
  every rendered deck (HTML + PPTX) uses it, with a documented resolution order down to a
  neutral placeholder.
- **`/talksmith:init` also writes a `.gitignore`** — a marked, idempotent block ignoring
  regenerable `output/`, caches, and local settings; talk source stays tracked.
- Renderer chrome labels localize from `deck.lang` (was hardcoded Spanish).

### Changed

- **Workflow order: Polish (6) → Render (7, optional) → Learnings (8, mandatory)**, and the
  step is named just "Render" (it produces a `.pptx` *or* a shareable HTML/Reveal.js deck).
  The suffixed-output guarantee (`output/final.<style>.…`, canonical copy last) is stated in
  the orchestrator, not only the skill.
- **Docs overhaul — README is usage-first** (~300 → ~120 lines): Quickstart up top, one
  rendered workflow diagram, a reference-artifacts table; deep material moved to
  `docs/methodology.md`, `docs/roles.md`, `docs/reverse-pipeline.md`. Added the Karpathy
  "LLM wiki" framing for the corpus/memory/learnings knowledge base.
- **Slide-template catalog reorganized into 7 concept families** with a per-family
  selection signal — pure clarity, classification byte-identical. The Editor drafts with
  the taxonomy in mind (shape each slide's content to a family).
- **Layout polish:** three-card concept slides lay out 2-on-top + 1 full-width; stat slides
  pick column count from stat count; icons follow the active accent (`currentColor`);
  quieter section pill; soft highlight box on the image-top caption.
- **Style reference rebuilt as a self-documenting English deck** — every slide's copy
  explains the template it demonstrates.
- **License is MIT, consistent everywhere** (`LICENSE`, README, plugin + marketplace
  manifests).

### Fixed

- **Slide templates are self-contained** — each `.j2` reads its own `slide-model.json`
  fields directly; the Python field-renaming layer is gone, so a markup change is a
  one-file edit (see CLAUDE.md → *Adding a new slide type*).
- **Full-bleed HTML slides no longer overflow** — `quote`/`statement`/`closing-hero` gained
  a `fitCover()` shrink-to-fit pass; the closing-hero title was right-sized.
- **Content images always show in full** (size to their own aspect, never force-cropped);
  `image-top` captions stay in view; `comparison` uses the actual column count; icon-list
  label-only rows center their icon; colon lead-in labels render bold.
- **Polish provenance echo escapes `-->`** so ASCII arrows can't close the
  `<!-- ascii-source -->` comment early and leak onto the slide; `prepare-render-args`
  fails loud on a stale plan or missing `.ascii` sidecars instead of emitting invalid
  render args.
- **Per-skill consistency audit** reconciled every SKILL.md with its scripts.

### Removed

- **The html-strict critique/FEEDBACK cycle** — html-strict is a single-pass GENERATE; the
  presenter reviews the deck and resolves issues by editing the source.
- **Institution branding from the plugin** — the bundled Universidad Austral logo is gone;
  templates ship a neutral placeholder and the logo is repo-supplied (above).
- Dead renderer code: the orphaned `agenda` template (superseded by `section-agenda`) and
  never-applied CSS.

## [0.23.1 – 0.44.0] — 2026-07-13

The HTML renderer, built from scratch and then rebuilt model-driven: a code-rendered
Reveal.js deck that always emits the full styled layer, fed by an LLM-filled
`slide-model.json` shared with the PPTX path.

### Added

- **The code-rendered HTML deck** (`build_html.py` + `html_style.py`): a self-contained
  styled deck that always emits cards (never bullets), per-concept Material Symbols icons,
  callouts, and code surfaces — fixing the native-`.pptx` failure where the styled layer
  was silently dropped. Icons are content-matched against the **live Material Symbols
  catalog** (~4200 icons, cached), with a Spanish→English bridge and an offline seed
  fallback; a strict icon-coverage audit backs it.
- **Built on vendored, inlined Reveal.js**: Reveal owns navigation, deck-to-window scaling,
  the overview, transitions, **speaker notes** (`### Speaker notes` → `<aside class="notes">`),
  and **PDF export** (`?print-pdf`). The only custom presentation code is the per-slide
  content-fit, reworked so busy slides neither clip nor shrink into a centred block.
- **`slide-model.json`, the structured IR** ([`schemas/slide-model.md`](schemas/slide-model.md)):
  the `md-to-deck` FILL step has an **LLM decompose `final.md`** into per-slide
  `{template, …fields…, notes}`, and the renderer maps fields mechanically onto one Jinja
  template per slide type. The same model is the shared IR for the PPTX render and the
  live view, and the CONTROL audits validate against it instead of re-parsing markdown.
- **Slide-type growth:** `quote`, `timeline`, `big-number`, `pros-cons`, numbered steps,
  auto-detected `stat` slides, anaphora/enumerations as `icon-list`, and the
  `section-agenda` separator — the numbered roadmap re-shown at every section start with
  the active section accented, each row deep-linking to its section.
- **Deck identity:** vendored IBM Plex Sans/Mono; a persisted Light/Dark theme toggle
  (`?deck-theme=`); every slide shows its section (pill or eyebrow); redesigned section
  dividers; the cover splits title and institution subtitle.
- **Canonical visual fixture** at `tests/skills/md-to-deck/` — one directive-forced slide
  per template plus edge cases, rendered to the committed `style-reference.html` so a diff
  shows any visual regression.

### Changed

- **Render modes consolidated and renamed: `pptx-strict`, `pptx-free-form`, `html-strict`**
  — three peers, with `md-to-deck/SKILL.md` rewritten around them and the audit suite
  consolidated into one CONTROL list. The html-strict renderer serves both the **live
  view** (`--draft`, auto-refreshed during review) and the **deliverable**
  (`output/html/index.html`).
- **Skill renamed `md-to-pptx` → `md-to-deck`** (it renders HTML too); the `pptx-*`
  reverse-pipeline skills keep their names.
- End-to-end render of a real 74-slide deck drove a fix wave: speaker-notes/`### Sources`
  blocks captured instead of leaking onto slides, literal markdown markers stripped, cover
  title band reserved, mojibake fixed.

### Removed

- **The separate `preview` render style and the Pillow wireframe renderer**
  (`build_preview.py` and friends) — the html-strict deck took over both the live-view and
  deliverable roles; the `preview/` style folder is deleted.
- **The regex classifier/parser** (`slide_model.py` heuristics, `curate.py` marker
  recovery) — superseded by the LLM FILL against a fixed field contract.
- **`convert.py`**, the markdown→prose pre-processor for the PPTX path — superseded by the
  shared `slide-model.json`.
- **The standalone `# Agenda` slide** — the roadmap re-shows at every section start, so a
  separate agenda slide added nothing. Authored duplicate cover slides are dropped too (the
  cover is synthesized from frontmatter).

## [0.10.0 – 0.19.1] — 2026-07-09 → 2026-07-12

The shared design system and a session start that actually boots.

### Added

- **The shared slide-template catalog**
  ([`config/pptx-styles/slide-templates.md`](config/pptx-styles/slide-templates.md)) — the
  single home for which template a slide is, when it applies, and its prescriptive Format,
  distilled from three real hand-built decks (131 slides, 0 bullet lists). Every render
  mode classifies each slide against it at GENERATE; the universal invariant — **labeled
  enumerations render as cards, never plain bullets** — holds in every mode. A signal
  glossary, discriminator order, and worked examples make classification deterministic;
  dry-running a real 74-slide deck closed the gaps so **every slide classifies** into a
  real template.
- **The layered design bar:** `visual-guidance.md` (the medium-agnostic floor: principles +
  hard must-never-happen defects), `slide-design.md` (the per-slide visual-transformation
  mandate the critique enforces), and `render-modes.md` (the phase × format → action matrix
  centralizing per-format render config that had drifted across ~6 files).
- **Every render writes a template-decision log** beside its output — per slide: the
  template chosen, why, the raw signals, and flags.
- **`concept-breakdown` carries a per-concept icon by default**, with balanced card
  content; any source image disqualifies the template. **Speaker-notes coverage is
  audited**, so a forgotten notes stage can't ship silently.

### Changed

- **The session start is reliable.** The stub (`talksmith-orch.md`) now *forces* the spec
  to load and the workflow to start: verify `orchestrator.md` is in context and Read it
  explicitly if the `@`-import didn't resolve (Cowork doesn't expand it), then execute
  Step 0 — the self-introduction + new-vs-resume ask — as the first response no matter what
  the user typed, folding their message into Step 1. All evolving behavior lives in
  `orchestrator.md`, which reloads fresh every session; the stub stays stable.
- **Free-form honors the shared design bar at GENERATE**, staying single-pass — its freedom
  is scoped to visual execution. The strict spec's duplicated layout guidance was
  consolidated into the catalog; strict keeps only its EMU realizations.

### Fixed

- **The shipped base-template covers were re-authored in Helvetica** so the
  system-fonts-only palette audit and the cover-fidelity audit stop contradicting each
  other on the shipped asset (they made every strict render fail one or the other).
- **HTML-comment stripping is line-based**, so `-->` arrows inside preserved ASCII can
  never close an `ascii-source` block early and spill onto the slide.

## [0.2.0 – 0.9.2] — 2026-07-09

The reverse pipeline, the learning loop, and the render-QA foundations.

### Added

- **The reverse pipeline** — reconcile an externally-edited `.pptx` back into `draft.md`,
  all artifacts under `talks/<Talk>/reconcile/`: **`pptx-extract`** (python-pptx; rebuilds
  the deck as `draft.md`-shaped Markdown + inventory), **`pptx-diff`** (stdlib; explains
  every title/content/note/image change vs `final.md`), **`pptx-merge`** (auto-applies the
  simple high-confidence changes to `draft.md`, routes complex ones to the Editor).
- **`pptx-learn`** (strict-only) — mines a presenter's hand-corrections into candidate
  conformance patterns: `learn_patterns.py` diffs the edited deck's per-shape geometry
  against the as-generated baseline (`output/final.generated.geometry.json`), the LLM
  judges which deltas are generalizable template rules vs content one-offs, survivors land
  in `config/strict-learnings.md` for human promotion into the declarative
  `conformance-patterns.md`. Runs auto after `pptx-merge` and on-demand.
- **The categorized critique rubric** — CONTENT / AESTHETIC / DISTRIBUTION /
  LAYOUT-CONFORMANCE (strict-only), each concern checked in exactly one place, enriched
  with established design guidance.
- **Per-mode output isolation** (`output/final.<style>.pptx`, latest copied to the
  canonical `final.pptx`) and **live per-phase render progress** in every mode — no more
  opaque multi-minute dispatches; any phase silent >60s surfaces as a stall.

### Fixed

- **Working-meta never leaks onto slides** (section goals, narrative arc, presenter
  feedback) — stripped in every render mode, with the hard rule that the render authors
  from the intermediate and never re-parses `final.md` raw.
- **Deep contradiction sweeps** left the render instructions internally consistent across
  all modes: the base-template delete range corrected to 3–15 (a real render bug), audit
  membership reconciled per mode, the "no python-pptx" wording fixed (driving the native
  skill's python-pptx-from-base-template workflow is required; *bypassing* it is
  forbidden), and every dangling cross-reference repaired.
- **Section dividers stopped vanishing** — a trailing stripped field could swallow the
  following `# N.` divider; field bodies now terminate at the next rule or heading.

*(A Step-5.5 "draft preview" was also built in this band — first a throwaway `.pptx`, then a
code-only Pillow wireframe — later superseded by the live HTML view; see the band above.)*

## [0.1.0]

Initial plugin release: the Presenter Agent orchestrator, five subagents
(Librarian, Composer, Editor, Illustrator, Global-Librarian), the `/talksmith:init`
command, and the forward-pipeline skills (`ingest`, `ascii-to-svg`, `polish-ascii`,
`feedback-cycle`, `md-to-deck`) driving the 8-step workflow from raw sources to
`draft.md`, `final.md`, and an optional `.pptx`.
