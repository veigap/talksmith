---
description: Drop the Talksmith orchestrator spec into the current project root as CLAUDE.md.
---

# /talksmith:init

One-shot bootstrap. Runs in the **current working directory** (the project root where the user opened Claude Code) and copies the Talksmith orchestrator spec into it as `CLAUDE.md`. After that file lands, the user reloads their Claude Code session and the spec takes over — every subsequent action (filling `config/profile.md` in Step 0.5, creating `talks/<folder>/` in Step 1, scaffolding the per-Talk folder tree, etc.) is performed by the orchestrator itself per the protocol in `CLAUDE.md`.

This command therefore does **only** the CLAUDE.md drop. No `config/` files, no `talks/` directory, no profile bootstrap — those are not init's job; they are the orchestrator's job once it's loaded.

## What to do

1. Resolve the destination as `./CLAUDE.md` (cwd-relative — the user's project root).
2. If `./CLAUDE.md` **already exists**, stop and emit one line:
   ```
   [init] CLAUDE.md already exists in this directory — leaving it untouched. Reload your Claude Code session if you want the orchestrator to take over.
   ```
   Do not overwrite. This is intentional — re-running `/talksmith:init` against a working Talksmith project must be a no-op.
3. Otherwise, copy the source file byte-for-byte:
   ```bash
   cp "${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md" ./CLAUDE.md
   ```
   Emit:
   ```
   [init] CLAUDE.md created from ${CLAUDE_PLUGIN_ROOT}/CLAUDE-INIT.md.
   ```
4. Print the next-step block:
   ```
   Next: reload this Claude Code session (or start a new one in this directory).
   The Talksmith Presenter Agent will boot from CLAUDE.md and walk you through
   Step 0 → Step 0.5 (profile setup) → Step 1 (Frame your first Talk).

   Everything else — config/profile.md, config/learnings.md, the feedback logs,
   and the talks/ directory tree — will be created by the orchestrator on demand.
   You do not need to scaffold anything by hand.
   ```

That's the entire command. Do not run any other setup steps. Do not create directories. Do not write template files into `config/`. The orchestrator handles all of that once it's loaded.
