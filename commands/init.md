---
description: Drop the Talksmith working-directory stub into the current project root as CLAUDE.md.
---

# /talksmith:init

One-shot bootstrap. Runs in the **current working directory** (the project root where the user opened Claude Code) and copies the Talksmith working-directory stub into it as `CLAUDE.md`.

The stub is intentionally minimal — it tells the LLM to read the full operating spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` at session start. The orchestrator spec itself is **not** copied; it lives in the plugin install and updates automatically whenever the plugin is updated. This means `/talksmith:init` runs **once per working directory** and rarely needs to be re-run, even across plugin upgrades.

This command does **only** the stub drop. No `config/` files, no `talks/` directory, no profile bootstrap — those are the orchestrator's job, performed by the Editor subagent in Step 0.5 and Step 1 once the spec is loaded.

## What to do

1. Resolve the destination as `./CLAUDE.md` (cwd-relative — the user's project root).
2. Copy the stub byte-for-byte, **always overwriting** any existing `./CLAUDE.md`:
   ```bash
   cp -f "${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md" ./CLAUDE.md
   ```
   This is intentional: the stub is the session-start contract, and re-running `/talksmith:init` is the supported way to pick up changes to it. Any user-specific content belongs in `config/profile.md`, `config/learnings.md`, or the `talks/` tree — never in `CLAUDE.md`. Emit:
   ```
   [init] CLAUDE.md written from ${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md (stub — the orchestrator spec is loaded at session start from ${CLAUDE_PLUGIN_ROOT}/orchestrator.md). Any prior CLAUDE.md in this directory was overwritten.
   ```
3. Print the next-step block:
   ```
   Next: run /clear to reload this Claude Code session (or start a new one in this directory).
   The stub will tell the agent to read the orchestrator spec from the plugin install,
   then walk you through Step 0 → Step 0.5 (profile setup) → Step 1 (Frame your first Talk).

   Everything else — config/profile.md, config/learnings.md, the feedback logs,
   and the talks/ directory tree — will be created by the orchestrator on demand.
   You do not need to scaffold anything by hand.
   ```

That's the entire command. Do not run any other setup steps. Do not create directories. Do not write template files into `config/`. The orchestrator handles all of that once it's loaded.
