# Talksmith — working directory entry

This directory is a Talksmith **subject working directory**, initialized via `/talksmith:init`. The full Presenter Agent operating spec — workflow Steps 0 through 8, role contracts, schemas, interaction defaults — lives in the plugin install, **not** in this file. This stub exists so Claude Code (which auto-loads `CLAUDE.md` from the current directory) knows where to find everything else.

The split is deliberate. Plugin updates (`/plugin update talksmith`) refresh everything under `${CLAUDE_PLUGIN_ROOT}/` automatically. `/talksmith:init` is no-clobber and never rewrites this file. By keeping `CLAUDE.md` minimal, most plugin updates do **not** require re-running `/talksmith:init` — the orchestrator content the agent loads at session start is always the latest from the plugin.

## Operating spec — auto-loaded

The full Presenter Agent spec is imported below via Claude Code's `@`-import mechanism. It loads into context at session start alongside this stub — no separate Read call required. Treat its content as if it were inline in this file.

@${CLAUDE_PLUGIN_ROOT}/orchestrator.md

If the import above failed to resolve (plugin not installed, `${CLAUDE_PLUGIN_ROOT}` unset, file missing after a partial install), stop immediately and tell the user: "The Talksmith plugin's orchestrator spec is unreachable at `${CLAUDE_PLUGIN_ROOT}/orchestrator.md`. Re-install the plugin (`/plugin install talksmith@talksmith`) and reload this session." Do not attempt to proceed from this stub alone — it intentionally carries no operational detail.

## Working directory layout

This directory holds **user-owned** per-subject state. The Editor subagent (defined at `${CLAUDE_PLUGIN_ROOT}/agents/editor.md`) is the sole writer.

| Path | Purpose | Created by |
|---|---|---|
| `CLAUDE.md` | This stub. | `/talksmith:init` |
| `config/profile.md` | Subject-level presenter profile (Subject, Audience, Language, …). | Editor in Step 0.5 |
| `config/learnings.md` | Promoted editorial rules. | Editor in Step 7 |
| `config/feedback-backlog.md` | Cross-Talk feedback audit log. | Editor in Step 5 |
| `config/feedback-processed.md` | Archived feedback after promotion. | Editor in Step 7 |
| `talks/<folder>/` | One folder per Talk (`draft.md`, `final.md`, `memory.md`, `research/`, `images/`, `output/`). | Orchestrator in Step 1 |
| `knowledge-library/` | Cross-Talk curated knowledge, organized by topic. | Global-Librarian subagent in Step 7 on promotion |

All operational content — the five subagents, the seven skills, the eight file-format schemas, design principles, ASCII-to-SVG style rules, PPTX style packs — lives under `${CLAUDE_PLUGIN_ROOT}/` and is shared across every Talksmith working directory on this machine.

## Updating

- **Plugin updates** (`/plugin update talksmith`) refresh everything under `${CLAUDE_PLUGIN_ROOT}/` automatically. The orchestrator spec, agents, skills, schemas, and bundled config update without touching this directory.
- **`/talksmith:init` is one-shot.** It refuses to overwrite an existing `CLAUDE.md`. If a future plugin version changes the session-start contract documented above (new mandatory load, new directive), the upgrade notes will say "re-run `/talksmith:init`" — delete this file and re-init then.
