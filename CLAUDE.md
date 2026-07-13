# Talksmith — plugin development notes

This file is the project-instruction file for **plugin authors and contributors** working in this repo. It is loaded by Claude Code only when a session is opened at the root of this repo to develop the plugin. End users never see it.

> **Two unrelated `CLAUDE.md` files — don't confuse them.**
> - **This file** (`/Users/.../talksmith/CLAUDE.md`) is the plugin source repo's dev notes. It exists only here.
> - A **user's `CLAUDE.md`** is a per-directory stub that activates Talksmith for one subject working directory. It is created by `/talksmith:init` from [`talksmith-orch.md`](talksmith-orch.md), lives in the user's cwd, and is completely separate from this file.
>
> Installing the plugin (`/plugin install talksmith@talksmith`) is a one-time, machine-wide action — it does **not** create any `CLAUDE.md` anywhere. Initializing Talksmith for a working directory (`/talksmith:init`) is a separate, per-directory action that writes the stub. A user can install the plugin once and then run `/talksmith:init` in many different directories.

For the user-facing project overview, see [`README.md`](README.md). For the full Presenter Agent operating spec (five subagents, eight steps, schemas, interaction defaults), see [`orchestrator.md`](orchestrator.md) — that file stays in the plugin install and is auto-imported at session start by the thin [`talksmith-orch.md`](talksmith-orch.md) stub that `/talksmith:init` writes into a user's subject working directory.

## What this repo is

The **Talksmith** Claude Code plugin. Installable surface:

| Path | Purpose |
|---|---|
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Plugin manifest (name, version, description). |
| [`agents/`](agents/) | Five Claude Code subagents — `librarian`, `composer`, `editor`, `illustrator`, `global-librarian`. Each has YAML frontmatter (`name:`, `description:`) so it can be dispatched by name. |
| [`commands/`](commands/) | Slash commands. Currently one: [`/talksmith:init`](commands/init.md). |
| [`skills/`](skills/) | Nine skills — `ingest`, `ascii-to-svg`, `polish-ascii`, `feedback-cycle`, `md-to-pptx`, the reverse-pipeline trio `pptx-extract`, `pptx-diff`, `pptx-merge`, and `pptx-learn`. Skill names are namespaced as `talksmith:<skill>` in their SKILL.md frontmatter. The `feedback-cycle` skill carries both its `feedback_cycle.py` CLI (stamp / close / mirror-row / find-closed-unmirrored / rescue-open) and the companion `find_open_notes.py` detector — Step-5/Step-6 mechanical bookkeeping consolidated into one skill. The **reverse pipeline** reconciles an externally-edited `.pptx` back into `draft.md`, writing all its artifacts under `talks/<Talk>/reconcile/` (`finalpptx.md`, `finalpptx.inventory.json`, `finalpptx.diff.json`, `staging/`): `pptx-extract` (`pptx_inventory.py` + `reconstruct_md.py`) reads the deck via **`python-pptx`** (with three targeted `lxml` drop-throughs on `picture._element` for SVG-twin lookup, raster-path resolution via rels, and bullet-marker detection) and rebuilds `reconcile/finalpptx.md` in `draft.md` shape; `pptx-diff` (`align_md.py`) explains the text/image changes vs `final.md`; `pptx-merge` (`merge_draft.py`) applies the simple changes back into `draft.md` and routes the complex ones to the Editor. All three share a copied-verbatim `_pptxlib.py`. `pptx-extract` requires `python-pptx` (`pip install python-pptx`); `pptx-diff` and `pptx-merge` do no pptx parsing themselves and stay stdlib-only. **`pptx-learn`** (strict-only, `learn_patterns.py`, needs `python-pptx`) closes the loop the other direction: it diffs a hand-corrected deck's per-shape geometry against the as-generated baseline (`output/final.generated.geometry.json`, snapshotted at strict render), aggregates recurring deltas into candidate conformance patterns in the project file `config/strict-learnings.md`, and a human promotes chosen ones at Step 7 into the plugin's `config/pptx-styles/strict/conformance-patterns.md`. Runs auto after `pptx-merge` (strict + baseline present) and on-demand. None require Cowork. |
| [`schemas/`](schemas/) | File-format specs (canonical empty forms for `draft.md`, `memory.md`, `profile.md`, `principles.md`, `learnings.md`, `feedback-backlog.md`, `feedback-processed.md`, `corpus-record.md`). |
| [`config/principles.md`](config/principles.md), [`config/diagram-style.md`](config/diagram-style.md), [`config/pptx-styles/`](config/pptx-styles/) | Bundled read-only design assets. |
| [`talksmith-orch.md`](talksmith-orch.md) | The thin **working-directory stub** copied to `CLAUDE.md` in the user's cwd by `/talksmith:init`. Tells the agent to load the full spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` at session start. Edit only when the session-start contract changes (new mandatory load, new directive) — and warn users to re-run `/talksmith:init` when you do. |
| [`orchestrator.md`](orchestrator.md) | The full Presenter Agent operating spec — workflow Steps 0 → 8, role dispatch, schemas, interaction defaults. Stays in the plugin install; never copied. Edit freely when you change workflow, role contracts, or step-by-step behavior — plugin updates roll out automatically and existing user working directories pick up the change on their next session reload, without re-init. |

There is intentionally **no `templates/` folder**. `/talksmith:init` only copies `talksmith-orch.md` → user's `CLAUDE.md`. Everything else the user might need (`config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`, `talks/<folder>/…`) is created by the orchestrator itself once the stub is loaded, bootstrapping from the *Canonical empty form* sections inside [`schemas/`](schemas/). Adding a `templates/` shortcut would duplicate the canonical empty forms and immediately drift from them.

## Path conventions

Every cross-reference from one bundled file to another uses `${CLAUDE_PLUGIN_ROOT}/…`. Examples:

- `${CLAUDE_PLUGIN_ROOT}/agents/editor.md`
- `${CLAUDE_PLUGIN_ROOT}/schemas/draft.md`
- `${CLAUDE_PLUGIN_ROOT}/config/principles.md`
- `${CLAUDE_PLUGIN_ROOT}/talksmith-orch.md`

References to **user data** (the bytes the user owns in their subject working directory) stay cwd-relative: `talks/…`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`. Never prefix these with `${CLAUDE_PLUGIN_ROOT}/`.

When developing the plugin in-repo (Claude Code opened at this directory), `${CLAUDE_PLUGIN_ROOT}` should resolve to the repo root. If your dev tooling doesn't auto-set it, export `CLAUDE_PLUGIN_ROOT="$(pwd)"` before launching `claude`.

## Common edits

| You want to… | Edit |
|---|---|
| Change the Presenter Agent workflow (steps, role contracts, interaction defaults) | [`orchestrator.md`](orchestrator.md) — users get it on next session reload, no re-init needed |
| Change the session-start contract (what the stub instructs to load, additional mandatory directives) | [`talksmith-orch.md`](talksmith-orch.md) — **users must re-run `/talksmith:init`** to pick up this change |
| Tighten or relax a subagent's behavior | the matching file under [`agents/`](agents/) |
| Change a skill's interface or recipe | the matching `SKILL.md` (and helper scripts) under [`skills/`](skills/) |
| Adjust a file-format schema or its canonical empty form | the matching file under [`schemas/`](schemas/) (the canonical empty form is a fenced block inside the schema spec — the orchestrator reads it from there) |
| Change what `/talksmith:init` copies | [`commands/init.md`](commands/init.md) (currently a single-file `talksmith-orch.md` → `CLAUDE.md` copy — keep it minimal) |
| Update PPTX rendering rules | [`config/pptx-styles/strict/pptx-prompt.md`](config/pptx-styles/strict/pptx-prompt.md) or [`config/pptx-styles/free-form/pptx-prompt.md`](config/pptx-styles/free-form/pptx-prompt.md) |
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
2. In a **separate** scratch directory (never this repo), run `/talksmith:init` and walk through Step 0 → Step 1 to confirm the orchestrator boots and the five agents dispatch correctly.
3. For skill changes, invoke the skill directly via its slash form (e.g. `/talksmith:ingest <url>`) on a representative input.

## HTML render + the style test — run after ANY style change

Talksmith renders to a **styled static HTML site** as well as `.pptx`: `skills/md-to-pptx/build_html.py` (shared components + tokens in `html_style.py`; content-matched Material Symbols icons via `icon_fetch.py`). Unlike the native `.pptx` render, this is deterministic code — icons, callout boxes, code surfaces, and card strips always render — and it drives both the fast **preview** (from `draft.md`) and an **HTML deliverable** (from `final.md`, with arrow-key + full-screen present mode). An optional `<!-- template: X -->` comment under a slide heading forces that template.

The canonical visual reference **and** regression test is [`tests/skills/md-to-pptx/`](tests/skills/md-to-pptx/): a directive-forced `final.md` with **one slide per template type plus edge cases** (2/3/4/6 concept cards, long titles/bodies, 2/3-col comparison, …) and `pipeline.svg`.

> **After any change to the strict style tokens (`strict/pptx-prompt.md` §1–§17), `html_style.py`, the catalog, or the render, run `python3 tests/skills/md-to-pptx/run.py`.** It regenerates `tests/skills/md-to-pptx/style-reference.html` and **fails** if any forced type falls back, HTML bullets appear, or a styled element (icons / callouts / code surface / card strips / present-mode) goes missing. Open the refreshed HTML to eyeball the result before committing.

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
