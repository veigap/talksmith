# Talksmith — plugin development notes

This file is the project-instruction file for **plugin authors and contributors** working in this repo. If you're a user who just installed the plugin, you don't see this file — you see the copy of [`CLAUDE-INIT.md`](CLAUDE-INIT.md) that `/talksmith:init` wrote into your subject working directory.

For the user-facing project overview, see [`README.md`](README.md). For the full Presenter Agent operating spec (five subagents, eight steps, schemas, interaction defaults), see [`orchestrator.md`](orchestrator.md) — that file stays in the plugin install and is loaded at session start by the thin [`CLAUDE-INIT.md`](CLAUDE-INIT.md) stub that `/talksmith:init` copies into a user's subject working directory.

## What this repo is

The **Talksmith** Claude Code plugin. Installable surface:

| Path | Purpose |
|---|---|
| [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) | Plugin manifest (name, version, description). |
| [`agents/`](agents/) | Five Claude Code subagents — `librarian`, `composer`, `editor`, `illustrator`, `global-librarian`. Each has YAML frontmatter (`name:`, `description:`) so it can be dispatched by name. |
| [`commands/`](commands/) | Slash commands. Currently one: [`/talksmith:init`](commands/init.md). |
| [`skills/`](skills/) | Seven skills — `ingest`, `ascii-to-svg`, `polish-ascii`, `feedback-cycle`, `find-open-notes`, `md-to-pptx`. Skill names are namespaced as `talksmith:<skill>` in their SKILL.md frontmatter. The `upgrade/` skill is legacy (pre-plugin fork-sync) and slated for removal. |
| [`schemas/`](schemas/) | File-format specs (canonical empty forms for `draft.md`, `memory.md`, `profile.md`, `principles.md`, `learnings.md`, `feedback-backlog.md`, `feedback-processed.md`, `corpus-record.md`). |
| [`config/principles.md`](config/principles.md), [`config/diagram-style.md`](config/diagram-style.md), [`config/pptx-styles/`](config/pptx-styles/) | Bundled read-only design assets. |
| [`CLAUDE-INIT.md`](CLAUDE-INIT.md) | The thin **working-directory stub** copied to `CLAUDE.md` in the user's cwd by `/talksmith:init`. Tells the agent to load the full spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` at session start. Edit only when the session-start contract changes (new mandatory load, new directive) — and warn users to re-run `/talksmith:init` when you do. |
| [`orchestrator.md`](orchestrator.md) | The full Presenter Agent operating spec — workflow Steps 0 → 8, role dispatch, schemas, interaction defaults. Stays in the plugin install; never copied. Edit freely when you change workflow, role contracts, or step-by-step behavior — plugin updates roll out automatically and existing user working directories pick up the change on their next session reload, without re-init. |

There is intentionally **no `templates/` folder**. `/talksmith:init` only copies `CLAUDE-INIT.md` → user's `CLAUDE.md`. Everything else the user might need (`config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`, `talks/<folder>/…`) is created by the orchestrator itself once `CLAUDE.md` is loaded, bootstrapping from the *Canonical empty form* sections inside [`schemas/`](schemas/). Adding a `templates/` shortcut would duplicate the canonical empty forms and immediately drift from them.

## Path conventions

Every cross-reference from one bundled file to another uses `${CLAUDE_PLUGIN_ROOT}/…`. Examples:

- `${CLAUDE_PLUGIN_ROOT}/agents/editor.md`
- `${CLAUDE_PLUGIN_ROOT}/schemas/draft.md`
- `${CLAUDE_PLUGIN_ROOT}/config/principles.md`
- `${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md`

References to **user data** (the bytes the user owns in their subject working directory) stay cwd-relative: `talks/…`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`. Never prefix these with `${CLAUDE_PLUGIN_ROOT}/`.

When developing the plugin in-repo (Claude Code opened at this directory), `${CLAUDE_PLUGIN_ROOT}` should resolve to the repo root. If your dev tooling doesn't auto-set it, export `CLAUDE_PLUGIN_ROOT="$(pwd)"` before launching `claude`.

## Common edits

| You want to… | Edit |
|---|---|
| Change the Presenter Agent workflow (steps, role contracts, interaction defaults) | [`orchestrator.md`](orchestrator.md) — users get it on next session reload, no re-init needed |
| Change the session-start contract (what the stub instructs to load, additional mandatory directives) | [`CLAUDE-INIT.md`](CLAUDE-INIT.md) — **users must re-run `/talksmith:init`** to pick up this change |
| Tighten or relax a subagent's behavior | the matching file under [`agents/`](agents/) |
| Change a skill's interface or recipe | the matching `SKILL.md` (and helper scripts) under [`skills/`](skills/) |
| Adjust a file-format schema or its canonical empty form | the matching file under [`schemas/`](schemas/) (the canonical empty form is a fenced block inside the schema spec — the orchestrator reads it from there) |
| Change what `/talksmith:init` copies | [`commands/init.md`](commands/init.md) (currently a single-file `CLAUDE-INIT.md` → `CLAUDE.md` copy — keep it minimal) |
| Update PPTX rendering rules | [`config/pptx-styles/strict/pptx-prompt.md`](config/pptx-styles/strict/pptx-prompt.md) or [`config/pptx-styles/free-form/pptx-prompt.md`](config/pptx-styles/free-form/pptx-prompt.md) |
| Update standing visual rules for ASCII → SVG | [`config/diagram-style.md`](config/diagram-style.md) |
| Update design principles applied at Composer reviews | [`config/principles.md`](config/principles.md) |

**Two-file split.** `CLAUDE-INIT.md` is a 30-line stub; `orchestrator.md` is the 1000+-line operating spec. Plugin updates carry the new `orchestrator.md` automatically — existing user working directories pick up the change on their next session reload, no re-init needed. The stub is only re-deployed if it itself changed (rare). When you do edit `CLAUDE-INIT.md`, tell affected users to delete their working-directory `CLAUDE.md` and re-run `/talksmith:init`.

## Versioning

The plugin version lives in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) (`"version"` field). **Bump it on every commit** — even one-line edits. Marketplace clients use this field to decide whether to pull an update, so an unbumped commit ships invisibly. Use semver: patch for fixes and doc tweaks, minor for new agents/skills/commands or workflow changes, major for breaking schema or session-start contract changes.

## Testing changes

1. Reload the plugin in your Claude Code session (`/plugin reload talksmith` or restart the session).
2. In a **separate** scratch directory (never this repo), run `/talksmith:init` and walk through Step 0 → Step 1 to confirm the orchestrator boots and the five agents dispatch correctly.
3. For skill changes, invoke the skill directly via its slash form (e.g. `/talksmith:ingest <url>`) on a representative input.
