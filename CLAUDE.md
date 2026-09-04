# Talksmith — plugin development notes

This file is the project-instruction file for **plugin authors and contributors** working in this repo. It is loaded by Claude Code only when a session is opened at the root of this repo to develop the plugin. End users never see it.

> **Two unrelated `CLAUDE.md` files — don't confuse them.**
> - **This file** (`/Users/.../talksmith/CLAUDE.md`) is the plugin source repo's dev notes. It exists only here.
> - A **user's `CLAUDE.md`** is a per-directory stub that activates Talksmith for one subject working directory. It is created by `/talksmith:init` from [`talksmith-orch.md`](talksmith-orch.md), lives in the user's cwd, and is completely separate from this file.
>
> Installing the plugin (`/plugin install talksmith@talksmith`) is a one-time, machine-wide action — it does **not** create any `CLAUDE.md` anywhere. Initializing Talksmith for a working directory (`/talksmith:init`) is a separate, per-directory action that writes the stub. A user can install the plugin once and then run `/talksmith:init` in many different directories.

For the user-facing project overview, see [`README.md`](README.md). For the full Presenter Agent operating spec (eight subagents, eight steps, schemas, interaction defaults), see [`orchestrator.md`](orchestrator.md) — that file stays in the plugin install and is auto-imported at session start by the thin [`talksmith-orch.md`](talksmith-orch.md) stub that `/talksmith:init` writes into a user's subject working directory.

## What this repo is

The **Talksmith** Claude Code plugin. Installable surface:

| Path | Purpose |
|---|---|
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Plugin manifest (name, version, description). |
| [`agents/`](agents/) | Eight Claude Code subagents — `librarian`, `composer`, `editor`, `diagram-illustrator`, `image-illustrator`, `diagram-critic`, `slide-classifier-critic`, `global-librarian`. Each has YAML frontmatter (`name:`, `description:`) so it can be dispatched by name. **`diagram-illustrator`** and **`image-illustrator`** are Step-6 siblings: the former renders authored ASCII → SVG (diagrams); the latter generates atmospheric aside imagery from `<!-- generate-image: … -->` directives (tool-agnostic, degrades when no image capability is present). **`diagram-critic`** is the odd one out: it is dispatched by the `diagram-illustrator`'s per-block subagent rather than by the orchestrator, and its `tools: Read` restriction is load-bearing — it reviews a rendered diagram from the PNG alone, and never receives the SVG path. That blindness is the point (see its own file). **`slide-classifier-critic`** is its twin one artifact earlier: dispatched by the `md-to-deck` skill (not the orchestrator) once per content slide between FILL and RENDER, it re-runs the catalog's discriminator walk on one slide's source and confirms or overturns the template the fill chose. Its `tools: Read` restriction is load-bearing for the same reason — it is blind to every *other* slide's classification, because a critic that can see the deck is `concept-breakdown` twenty times reads the twenty-first as normal. |
| [`commands/`](commands/) | Slash commands. Currently one: [`/talksmith:init`](commands/init.md). |
| [`skills/`](skills/) | Thirteen skills, **all** namespaced `talksmith:<skill>` in their SKILL.md frontmatter (the namespace is the convention — an un-namespaced `name:` collides with a user's own same-named skill instead of coexisting with it): `ingest` (web capture), `ascii-to-svg` (one ASCII block → one SVG; owns the viewBox, rasterizer, and aspect-audit contracts), `polish-ascii` (Step-6 mechanical scan / sidecar / stamp / cleanup for diagrams — `stamp-renders` arms render idempotency), `polish-images` (its **sibling** — the same staged scan / sidecar / stamp / cleanup for `<!-- generate-image: … -->` aside directives) and `generate-image` (tool-agnostic backend the image-illustrator dispatches; produces a raster or returns `unavailable`, never blocks), `feedback-cycle` (Step-5 bookkeeping CLI), `md-to-deck` (Step-7 render, three modes), and the **reverse pipeline** `pptx-extract` → `pptx-diff` → `pptx-merge` (reconcile an externally-edited `.pptx` back into `draft.md`; artifacts under `talks/<Talk>/reconcile/`) plus `pptx-learn` (mines hand-corrections into strict conformance-pattern candidates). Shared code lives **once** under [`skills/_shared/`](skills/_shared/), `sys.path`-imported by its consumers: [`_pptxlib.py`](skills/_shared/_pptxlib.py) (pptx parsing — the three reverse-pipeline scripts), [`_context.py`](skills/_shared/_context.py) (the slide-context scanner — **both** polish skills), [`_plan.py`](skills/_shared/_plan.py) (the plan-file envelope, `--final/--plan/--dry-run`, and the `gc` live set — **both** polish skills, which are otherwise near-twins), and [`_write.py`](skills/_shared/_write.py) (the atomic in-place write every skill that edits `draft.md`/`final.md` must use — `feedback-cycle` + `pptx-merge`). The deck-parsing audits have their own sibling module, [`skills/md-to-deck/audits/_ooxml.py`](skills/md-to-deck/audits/_ooxml.py) (namespace map, slide relationships, solid-fill colour, PNG dimensions, and the `_`-key-excluding model walk). Two more are **anti-slop passes the Editor applies to a Talk's prose**, one per language: `stop-slop` (English, vendored from Hardik Pandya) and `desrobotizar` (Spanish) — both are **explicit-invocation only**, so neither fires on ordinary drafting or editing; the dispatch table lives in [`agents/editor.md`](agents/editor.md). `pptx-extract` / `pptx-learn` need `python-pptx`; none require Cowork. Everything else lives in each SKILL.md — don't restate it here. |
| [`schemas/`](schemas/) | File-format specs (canonical empty forms for `draft.md`, `memory.md`, `profile.md`, `principles.md`, `learnings.md`, `feedback-backlog.md`, `feedback-processed.md`, `corpus-record.md`, `talksmith-bugs.md`), plus [`slide-model.md`](schemas/slide-model.md) — the structured `slide-model.json` the `md-to-deck` skill fills (LLM) and the renderers consume. |
| [`config/principles.md`](config/principles.md), [`config/diagram-style.md`](config/diagram-style.md), [`config/pptx-styles/`](config/pptx-styles/) | Bundled read-only design assets. |
| [`talksmith-orch.md`](talksmith-orch.md) | The thin **working-directory stub** copied to `CLAUDE.md` in the user's cwd by `/talksmith:init`. Tells the agent to load the full spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` at session start. Edit only when the session-start contract changes (new mandatory load, new directive) — and warn users to re-run `/talksmith:init` when you do. |
| [`talksmith-agents.md`](talksmith-agents.md) | The **Codex working-directory stub** copied to `AGENTS.md` in the user's cwd by `/talksmith:init`. A thin **pointer to `CLAUDE.md`** (which owns the boot instructions) that re-states the two Claude-Code-specific fallbacks a non-Claude-Code agent needs — the `@`-import is inert, `${CLAUDE_PLUGIN_ROOT}` is unset. Carries no independent workflow content, so it never drifts from `CLAUDE.md`. Edit only when those fallbacks change; re-init to redeploy. |
| [`orchestrator.md`](orchestrator.md) | The full Presenter Agent operating spec — workflow Steps 0 → 8, role dispatch, schemas, interaction defaults. Stays in the plugin install; never copied. Edit freely when you change workflow, role contracts, or step-by-step behavior — plugin updates roll out automatically and existing user working directories pick up the change on their next session reload, without re-init. |

There is intentionally **no `templates/` folder**. `/talksmith:init` only copies `talksmith-orch.md` → user's `CLAUDE.md` and `talksmith-agents.md` → user's `AGENTS.md` (a pointer to the former). Everything else the user might need (`config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`, `talks/<folder>/…`) is created by the orchestrator itself once the stub is loaded, bootstrapping from the *Canonical empty form* sections inside [`schemas/`](schemas/). Adding a `templates/` shortcut would duplicate the canonical empty forms and immediately drift from them.

> **The same rule applies to this repo's own `config/`.** Those four files were once committed here — `config/profile.md` was a verbatim second copy of `schemas/profile.md`'s canonical empty form — and shipped in every install as exactly the drift-prone duplicate the paragraph above argues against. They are now gitignored. If a dev session in this repo creates them (it shouldn't — test in a scratch directory), leave them untracked. The only bundled config is `principles.md`, `diagram-style.md` and `pptx-styles/`.

## Ownership map — where a fact lives

**Every fact is stated once, in the file that owns it; every other file points there.** These files are LLM context — duplication costs tokens on every load and drifts. When editing, move detail to its owner rather than restating it; when you find a rule stated twice, keep the owner's copy and turn the other into a pointer.

| Fact domain | Sole owner |
|---|---|
| Workflow steps, role dispatch, interaction defaults | [`orchestrator.md`](orchestrator.md) |
| Template **Match + Format + classification procedure** | [`config/pptx-styles/slide-templates.md`](config/pptx-styles/slide-templates.md) |
| Template **field contracts** (`slide-model.json`) | [`schemas/slide-model.md`](schemas/slide-model.md) |
| Strict **EMU geometry / OOXML recipes** (binding catalog ids to §-recipes) | [`config/pptx-styles/pptx-strict/pptx-prompt.md`](config/pptx-styles/pptx-strict/pptx-prompt.md) |
| Blind-critique rationale, defect checklist, report format | [`agents/diagram-critic.md`](agents/diagram-critic.md) |
| **Template-classification critique** — independence rule, verdict vocabulary, the bar for overturning a pick | [`agents/slide-classifier-critic.md`](agents/slide-classifier-critic.md) |
| **The classification trace** `_choice` (signals / candidates / rejections) | [`schemas/slide-model.md`](schemas/slide-model.md) → *The classification trace* |
| **Template-distribution thresholds** (dominance share, run length, fallback = failure) | [`skills/md-to-deck/audits/template_diversity.py`](skills/md-to-deck/audits/template_diversity.py) |
| **Content survival through FILL** — how a `final.md` line is judged present in the model (word-window match), the `deck-omit-text` waiver, why `_choice` is excluded | [`skills/md-to-deck/audits/text_coverage.py`](skills/md-to-deck/audits/text_coverage.py) (the *rule* it enforces is [`schemas/slide-model.md`](schemas/slide-model.md) → *Never drop content*) |
| **Polymorphic `media`** (image \| code panel \| aligned grid) + the universal `stats` band — the stage places them, no template branches | [`skills/md-to-deck/templates/html/_macros.j2`](skills/md-to-deck/templates/html/_macros.j2) (`smedia`, `stage`); contract in [`schemas/slide-model.md`](schemas/slide-model.md) |
| ASCII detection tiers, sidecar layout, fence-rewrite rules | [`skills/polish-ascii/SKILL.md`](skills/polish-ascii/SKILL.md) (behavior enforced in `polish_ascii.py`) |
| `generate-image` directive detection, `.imgprompt` sidecar, `.imgstamp` idempotency, directive→aside rewrite | [`skills/polish-images/SKILL.md`](skills/polish-images/SKILL.md) (behavior enforced in `polish_images.py`) |
| Shared slide-context scanner (headings, prose strip, thesis, per-block context bundle) | [`skills/_shared/_context.py`](skills/_shared/_context.py) (imported by both polish skills) |
| Atmospheric-aside prompt enrichment + palette overlay + graceful degradation | [`agents/image-illustrator.md`](agents/image-illustrator.md) (backend contract in [`skills/generate-image/SKILL.md`](skills/generate-image/SKILL.md)) |
| SVG viewBox/aspect contract, rasterizer (`cairosvg`-only), aspect audit | [`skills/ascii-to-svg/SKILL.md`](skills/ascii-to-svg/SKILL.md) |
| Render modes, progress checklists, suppression vocabulary, **Path B (`html-strict`)** | [`skills/md-to-deck/SKILL.md`](skills/md-to-deck/SKILL.md) |
| **Path A (`.pptx`) render — prerequisites, process, render flow, Keynote rules** | [`skills/md-to-deck/pptx-render.md`](skills/md-to-deck/pptx-render.md) — split out of `SKILL.md` so an `html-strict` render (including every Step-5.5 live view) never loads it; `SKILL.md` resolves `style:` first and points here only on a `pptx-*` value |
| **Model + rendered-deck freshness** — the `_source` stamp, the render sidecar's `source` copy, the `stamp` / `check` / `rendered` verdicts and their exit codes | [`skills/md-to-deck/model_freshness.py`](skills/md-to-deck/model_freshness.py) |
| Working-directory landing page (root `index.html`) — scan, render stamp, marker guard, card fields | [`skills/md-to-deck/build_index.py`](skills/md-to-deck/build_index.py) (markup `templates/html/index.j2`, layout `templates/html/index.css`) |
| **The code panel** — editor-window chrome, the always-dark ground it keeps in every theme, and the `.hljs-*` → VS Code Dark+ token palette | [`skills/md-to-deck/templates/html/theme.css`](skills/md-to-deck/templates/html/theme.css) (the `.codebox` block); the language-alias map and the text prep (dedent / tab expand) in [`html_style.py`](skills/md-to-deck/html_style.py) → *code panels*, the shrink-to-fit in its `fitCode`, markup in [`_macros.j2`](skills/md-to-deck/templates/html/_macros.j2) `codepanel` |
| **Inline markup grammar** in text fields (`**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `[title](url)`, naked URLs) | [`skills/md-to-deck/html_style.py`](skills/md-to-deck/html_style.py) `_inline_md` (styled in `templates/html/theme.css`; declared to the fill step in [`schemas/slide-model.md`](schemas/slide-model.md), to the author in [`schemas/draft.md`](schemas/draft.md), and to the PPTX path in [`pptx-prompt.md`](config/pptx-styles/pptx-strict/pptx-prompt.md) §3.6) |
| Two-file contract (`draft.md` read-only from Step 6) | [`schemas/draft.md`](schemas/draft.md) |
| **The export geometry contract** — what a harvested display list contains, the tree-walk rule, pseudo-element reconstruction, why the file may never contain a closing script tag | [`skills/md-to-deck/templates/html/harvest.js`](skills/md-to-deck/templates/html/harvest.js) |
| **HTML → `.pptx`** — the 9525 EMU-per-pixel mapping, shape selection, per-side accent borders, wrap-vs-no-wrap, SVG rasterization and image encoding | [`skills/md-to-deck/export_pptx.py`](skills/md-to-deck/export_pptx.py) |
| **HTML → PDF** | [`skills/md-to-deck/export_pdf.py`](skills/md-to-deck/export_pdf.py) |
| **The export font profile** — why the `.pptx`'s fonts are substituted in the browser *before* layout rather than named at emit time | [`skills/md-to-deck/html_style.py`](skills/md-to-deck/html_style.py) `_EXPORT_FONT_CSS` / `_EXPORT_EARLY` |
| Locating and driving headless Chrome (shared by both exports) | [`skills/md-to-deck/_chrome.py`](skills/md-to-deck/_chrome.py) |
| **Defect logging** — what counts as a Talksmith bug, the entry fields (context / repro / *suggested* fix), dedup, suggestion discipline | [`schemas/talksmith-bugs.md`](schemas/talksmith-bugs.md) (obligation + dispatch in [`orchestrator.md`](orchestrator.md) → *Defect log*) |
| Per-mode critique matrix (which phases fire per style) | [`config/pptx-styles/render-modes.md`](config/pptx-styles/render-modes.md) |
| Shared pptx parsing code | [`skills/_shared/_pptxlib.py`](skills/_shared/_pptxlib.py) |
| Plan-file envelope + `gc` live set shared by the two polish skills | [`skills/_shared/_plan.py`](skills/_shared/_plan.py) |
| Atomic in-place write of a user's `draft.md` / `final.md` | [`skills/_shared/_write.py`](skills/_shared/_write.py) — named `_write`, never `_io`, which shadows a CPython builtin |
| OOXML reading shared by the deck audits (+ the `_`-key exclusion in the model walk) | [`skills/md-to-deck/audits/_ooxml.py`](skills/md-to-deck/audits/_ooxml.py) |

## Path conventions

Every cross-reference from one bundled file to another uses `${CLAUDE_PLUGIN_ROOT}/…`. Examples:

- `${CLAUDE_PLUGIN_ROOT}/agents/editor.md`
- `${CLAUDE_PLUGIN_ROOT}/schemas/draft.md`
- `${CLAUDE_PLUGIN_ROOT}/config/principles.md`
- `${CLAUDE_PLUGIN_ROOT}/talksmith-orch.md`

References to **user data** (the bytes the user owns in their subject working directory) stay cwd-relative: `talks/…`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`. Never prefix these with `${CLAUDE_PLUGIN_ROOT}/`.

When developing the plugin in-repo (Claude Code opened at this directory), `${CLAUDE_PLUGIN_ROOT}` should resolve to the repo root. If your dev tooling doesn't auto-set it, export `CLAUDE_PLUGIN_ROOT="$(pwd)"` before launching `claude`.

> **A cloned marketplace is not an installed plugin.** Having this repo on disk (even registered in `~/.claude/plugins/known_marketplaces.json`) is enough to *read* the specs by absolute path, and that is the documented fallback when `${CLAUDE_PLUGIN_ROOT}` is unset. It is **not** enough to run anything: with no `enabledPlugins` entry there are no `talksmith:*` skills and no `/talksmith:*` slash commands in the session, so every skill has to be invoked as a plain script by absolute path and the orchestrator's role dispatch silently has nothing to dispatch to. Check with `echo ${CLAUDE_PLUGIN_ROOT}` (empty = not installed) — `~/.claude/plugins/config.json` missing is the same signal. Fix with `/plugin install talksmith@talksmith`, then reload the session. **In some environments `/plugin` itself is unavailable** ("isn't available in this environment"), and there is then no in-session way to install: work through the absolute-path fallback and install from a Claude Code CLI session on the same machine, which shares the install.

## Common edits

| You want to… | Edit |
|---|---|
| Change the Presenter Agent workflow (steps, role contracts, interaction defaults) | [`orchestrator.md`](orchestrator.md) — users get it on next session reload, no re-init needed |
| Change the session-start contract (what the stub instructs to load, additional mandatory directives) | [`talksmith-orch.md`](talksmith-orch.md) — **users must re-run `/talksmith:init`** to pick up this change |
| Tighten or relax a subagent's behavior | the matching file under [`agents/`](agents/) |
| Change a skill's interface or recipe | the matching `SKILL.md` (and helper scripts) under [`skills/`](skills/) |
| Adjust a file-format schema or its canonical empty form | the matching file under [`schemas/`](schemas/) (the canonical empty form is a fenced block inside the schema spec — the orchestrator reads it from there) |
| Change what `/talksmith:init` copies | [`commands/init.md`](commands/init.md) (copies `talksmith-orch.md` → `CLAUDE.md` and `talksmith-agents.md` → `AGENTS.md`, and appends a marker-guarded build-artifact block to `.gitignore` — keep it minimal) |
| Change the Codex boot pointer or its fallbacks | [`talksmith-agents.md`](talksmith-agents.md) — **users must re-run `/talksmith:init`** to pick up this change |
| Update PPTX rendering rules | [`config/pptx-styles/pptx-strict/pptx-prompt.md`](config/pptx-styles/pptx-strict/pptx-prompt.md) or [`config/pptx-styles/pptx-free-form/pptx-prompt.md`](config/pptx-styles/pptx-free-form/pptx-prompt.md) |
| Update standing visual rules for ASCII → SVG | [`config/diagram-style.md`](config/diagram-style.md) |
| Update design principles applied at Composer reviews | [`config/principles.md`](config/principles.md) |

**Two-file split.** `talksmith-orch.md` is a thin stub; `orchestrator.md` is the full operating spec. Plugin updates carry the new `orchestrator.md` automatically — existing user working directories pick up the change on their next session reload because the stub auto-imports it via `@${CLAUDE_PLUGIN_ROOT}/orchestrator.md`. The stub itself is only redeployed when its session-start contract changes (rare). When you do edit `talksmith-orch.md`, tell affected users to re-run `/talksmith:init` in each Talksmith working directory — the command now always overwrites, so no manual delete is needed.

## Versioning

The plugin version lives in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) (`"version"` field). **Bump it on every commit** — even one-line edits. Marketplace clients use this field to decide whether to pull an update, so an unbumped commit ships invisibly. Use semver: patch for fixes and doc tweaks, minor for new agents/skills/commands or workflow changes, major for breaking schema or session-start contract changes.

## Changelog

Every commit **must** record a **functional description** of what changed and why in [`CHANGELOG.md`](CHANGELOG.md) — user-visible behavior, not the mechanics of the diff. Group entries under the version being shipped (matching the `plugin.json` bump), using the `Added` / `Changed` / `Fixed` / `Removed` headings of [Keep a Changelog](https://keepachangelog.com/).

**Keep the changelog useful, not exhaustive — less is more.** As entries age, run *compaction*: collapse a superseded fix into the feature it fixed, fold a run of tiny commits into one summary line, and drop detail that no longer helps a reader understand the current state. A first-time reader should be able to skim the file and understand what each release actually delivered — not wade through every intermediate patch. When in doubt, compact. The goal is a document someone reads, not an append-only commit log (git already is that).

## Testing changes

1. Reload the plugin in your Claude Code session (`/plugin reload talksmith` or restart the session).
2. In a **separate** scratch directory (never this repo), run `/talksmith:init` and walk through Step 0 → Step 1 to confirm the orchestrator boots and the subagents dispatch correctly.
3. For skill changes, invoke the skill directly via its slash form (e.g. `/talksmith:ingest <url>`) on a representative input.

## HTML render + the style test — run after ANY style change

Talksmith renders from a **structured `slide-model.json`** (schema: [`schemas/slide-model.md`](schemas/slide-model.md)) — the intermediate the `md-to-deck` skill produces by having an **LLM decompose `final.md`** into per-slide `{template, …fields…, notes}` (all the *semantic* work: classification + information-breakdown). `skills/md-to-deck/build_html.py` then **renders that model mechanically** — `html_style.render_model_slide` hands the slide to its Jinja template as `s`, and the template reads its own schema fields off it (`s.cards`, `s.stats`, …). Python does only what a template can't: resolve content-matched Material Symbols icons (via `icon_fetch.py`), resolve and embed image paths, normalize the fields the schema allows in two shapes, and supply localized chrome labels. **Layout lives in `theme.css`, markup in the `.j2`** — neither belongs in Python. The whole thing is wrapped in a **[Reveal.js](https://revealjs.com/)** shell vendored + inlined under `skills/md-to-deck/vendor/reveal/`. The renderer does no classification: the `template` and fields are given. Reveal owns navigation, deck-to-window scaling, transitions, the slide overview, **speaker notes** (`notes` → `<aside class="notes">`, shown with `s`), and **PDF export** (`?print-pdf`); the only custom presentation code is a per-slide content-fit (scale-to-fill-width + fit-height, which Reveal/CSS can't do). The same model feeds the live **in-progress view** (`slide-model.draft.json`) and the **HTML deliverable** (`slide-model.json`), and is the deck the PDF and `.pptx` exports are then measured from.

**Code panels** are the one place a second vendored library runs: **highlight.js** (`vendor/highlight/`, BSD-3, 37 grammars) tokenizes `pre.cbcode > code` in the page, and is inlined **only into decks that contain a code panel**. Python does not tokenize — it maps the model's `language` to a grammar id and dedents the snippet (`_codeprep`), and the look of every token is `theme.css`. **No snippet is ever truncated:** the panel is bounded in CSS and `fitCode` (beside `fitContent` in the deck script) shrinks its type until every line fits; past ~28 lines the render warns that the slide wants splitting. The `.pptx` export inherits all of it: it measures the rendered page, so the panel arrives in PowerPoint with the same dark ground and the same per-token colours highlight.js gave it on screen.

The canonical visual reference is [`tests/skills/md-to-deck/`](tests/skills/md-to-deck/): a directive-forced `final.md` with **one slide per template type plus edge cases** (2/3/4/6 concept cards, long titles/bodies, 2/3-col comparison, …) and `pipeline.svg`. Its `style-reference.html` is nothing more than the `build_html` output of that `final.md` — a presentable deck (cover + present mode), committed so a diff shows any visual regression.

> **After any change to `theme.css`, `html_style.py`, a `.j2` template, the catalog, or the render, regenerate BOTH references and eyeball them:**
> ```
> python3 skills/md-to-deck/build_html.py  --model tests/skills/md-to-deck/slide-model.json --talk-root tests/skills/md-to-deck -o tests/skills/md-to-deck/style-reference.html
> python3 skills/md-to-deck/export_pptx.py --deck  tests/skills/md-to-deck/style-reference.html -o tests/skills/md-to-deck/style-reference.pptx
> ```
> Open the refreshed HTML (Present ▶ for full-screen), confirm no slide fell to `fallback` and every template still reads right. Then open the `.pptx` beside it and confirm the same, and commit both alongside your change.
>
> **The `.pptx` is not a second reference — it is the same one, measured.** It is derived from that exact HTML file by laying it out in a headless browser and rebuilding the measured display list as native shapes, so a style change that looks fine on screen and breaks in PowerPoint is a real and reachable failure: a font-family that stops resolving through `--sans`/`--mono` (the export substitutes system fonts *in the browser, before layout*, and only reaches surfaces that read the tokens), a new `::before` whose position can't be derived, a construct with no shape equivalent. Regenerating only the HTML hides exactly those. Run `python3 tests/skills/md-to-deck/test_export_pptx.py` too — it catches the mechanical half (font tokens, picture and notes parity, shapes off the slide) so your eyes are free for the visual half.

## Adding a new slide type

The HTML pipeline is: **LLM fills `slide-model.json` → render fields**, one Jinja template per type. To add a slide type, touch these in order (the catalog is the source of truth; everything else implements it):

1. **Catalog (source of truth)** — add the type to [`config/pptx-styles/slide-templates.md`](config/pptx-styles/slide-templates.md): its **Match** criteria (what content signals select it, and what it is *not*) and its **Format**. This is the "clearly documented criteria" the LLM applies when filling the model.
2. **Schema (field contract)** — add the type's **required/optional fields** to [`schemas/slide-model.md`](schemas/slide-model.md)'s per-template table, so the fill step knows what to decompose the slide into.
3. **Template (markup)** — add `skills/md-to-deck/templates/html/<type>.j2`. It receives the slide as `s` and reads the schema fields from step 2 directly off it (`s.cards`, …). Content slides wrap their body in the `_macros.j2` `stage(s)` call — which also gives them `highlights` and the optional `aside` image column for free; full-bleed slides (cover/divider/statement) emit their own `.stage cover`.
4. **Registration** — register `"<type>": "<type>.j2"` in `_TMPL` in [`html_style.py`](skills/md-to-deck/html_style.py). That is normally the *only* Python edit: `render_model_slide` passes the slide through, so a type needs no branch there. Add one only for something a template genuinely can't do (e.g. a new field that needs icon resolution → add it to `_ICON_LISTS`).
5. **CSS** — add the component classes the template uses to `templates/html/theme.css` (cqw units; 16:9 fixed). Layout that varies with item *count* belongs here too, selected with `:has()` — not computed in Python and passed in as a class.
6. **Fixture + regen** — add a slide of the new type to `tests/skills/md-to-deck/slide-model.json`, regenerate `style-reference.html` (command above), eyeball it, commit both.
7. **PPTX** — the same `slide-model.json` is the intended IR for PPTX; add the type's recipe to the PPTX style spec so the PPTX renderer maps the same fields.
8. **Version + changelog** — bump `plugin.json`, add a `CHANGELOG.md` entry.

## Refreshing the plugin so Cowork picks up changes (fast loop, no full reinstall)

The marketplace **is this git repo** ([`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) → `source: "./"`); Cowork (desktop) and the CLI share one install and update via `/plugin update talksmith`. You almost never need the "full" cycle (remove marketplace → reinstall → re-init). Two facts make the loop short:

- **Everything under `${CLAUDE_PLUGIN_ROOT}/`** — `orchestrator.md`, `agents/`, `skills/`, `schemas/`, `config/` — is **read fresh at every session start** (the stub loads `orchestrator.md`; skills/agents/config load just-in-time). So once the *install* has the new files, a **new session** picks them up with **no `/talksmith:init` and no reinstall**.
- **Only the stub** (`talksmith-orch.md` → a working dir's `CLAUDE.md`) is frozen until `/talksmith:init` re-runs. Change the stub → users re-init; change *anything else* → they just start a fresh session after the install updates.

**Recommended when Cowork is on the same machine as this repo — a local marketplace (no GitHub push):**

Cowork (desktop) and the CLI share one install on the machine. Point the marketplace at this repo instead of GitHub, and updates flow from your local commits:

1. One-time: `/plugin marketplace add <path-to-this-repo>` then `/plugin install talksmith@talksmith` (reinstall from the local marketplace).
2. Per change: **bump `plugin.json` `version`** (the marketplace checks it to detect an update), then **`/plugin update talksmith`** (re-syncs the files from this repo on disk), then **`/plugin reload talksmith`** *or* start a new session.

No push, no reinstall, and no `/talksmith:init` unless the stub (`talksmith-orch.md`) changed.

**If installed from the GitHub marketplace instead:** the marketplace pulls from what's **pushed** — so first `git push`, then bump the version, then `/plugin update talksmith` + reload/new session. Same short loop, plus a push.

Either way, a spec/skill/agent/config edit needs **no re-init and no reinstall** — only a stub change does (the changelog entry says so).

> **Caveat.** The in-session reload affordance varies by environment (the CLI has `/plugin reload`; the desktop plugin manager may differ). When in doubt, a **fresh session always re-reads** `${CLAUDE_PLUGIN_ROOT}/`, so "start a new session" is the reliable fallback after `/plugin update`.
