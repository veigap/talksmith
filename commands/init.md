---
description: Initialize Talksmith here — drop the CLAUDE.md stub, load the operating spec into context, and start the workflow.
---

# /talksmith:init

One-shot bootstrap. Runs in the **current working directory** (the project root where the user opened Claude Code). It (1) writes the Talksmith working-directory stub as `CLAUDE.md`, (2) **loads the full operating spec into context immediately**, and (3) starts the workflow with the Step 0 introduction — all in this session, no reload required.

Loading the spec here is deliberate and important. The stub relies on an `@${CLAUDE_PLUGIN_ROOT}/orchestrator.md` import to pull the spec at session start, but that `@`-import is a Claude Code **CLI** convention that some environments — **notably Cowork** — do not expand. By reading the spec directly as part of init, this command guarantees Talksmith is fully operational right now regardless of environment, instead of depending on an import that may silently no-op. Subsequent sessions load the spec via the refreshed stub's directive #1 (verify it's loaded; Read it directly if not).

This command does **not** scaffold `config/` files, the `talks/` directory, or the profile — those are the orchestrator's job (Editor subagent, Step 0.5 and Step 1) once the workflow is running.

## What to do

1. Resolve the destination as `./CLAUDE.md` (cwd-relative — the user's project root).
2. **Refuse to run inside the plugin source repo.** If `./.claude-plugin/plugin.json` exists in the cwd, stop immediately and emit:
   ```
   [init] Refusing to run: this directory is the Talksmith plugin source repo (./.claude-plugin/plugin.json exists). /talksmith:init is for user subject working directories, not the plugin source. The dev CLAUDE.md here is the plugin development notes — overwriting it would clobber documentation. cd into a separate working directory and re-run.
   ```
   Do not write anything. This guard exists because `/talksmith:init` always overwrites — without it, running this command in the plugin repo would destroy the dev `CLAUDE.md`.
3. **Write the stub**, byte-for-byte, **always overwriting** any existing `./CLAUDE.md`:
   ```bash
   cp -f "${CLAUDE_PLUGIN_ROOT}/talksmith-orch.md" ./CLAUDE.md
   ```
   If `${CLAUDE_PLUGIN_ROOT}` is unset or that path fails (e.g. in Cowork), **locate the plugin install** — find `talksmith-orch.md` under the Claude Code plugins directory — and copy that file to `./CLAUDE.md`. Re-running `/talksmith:init` is the supported way to pick up stub changes; user content belongs in `config/`, `talks/`, never in `CLAUDE.md`. Emit:
   ```
   [init] CLAUDE.md written from the Talksmith stub (talksmith-orch.md). Any prior CLAUDE.md was overwritten.
   ```
4. **Load the operating spec into context now — required, before starting.** Read `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` so its full content is in your context. If `${CLAUDE_PLUGIN_ROOT}` is unset or that path fails, **locate the plugin install** (find `talksmith/orchestrator.md` under the Claude Code plugins directory) and Read it from there. Confirm you can see the spec's heading *"Talksmith — Presenter Agent (orchestrator spec)"* and its Steps 0–8. Only if `orchestrator.md` is genuinely unfindable, stop and emit: `[init] FAILED: could not load ${CLAUDE_PLUGIN_ROOT}/orchestrator.md — re-install the plugin (/plugin install talksmith@talksmith) and retry.` Do **not** proceed to step 5 without the spec loaded.
5. **Start the workflow.** With the spec loaded, immediately perform its **Step 0 — Introduce**: state you are Talksmith, name the five roles, show the workflow chart, note you produce structured Markdown (not rendered slides), then **ask the presenter "new presentation or resume existing?"** and drive the conversation forward. This introduction + question is what turns init into a working session (and confirms the spec actually loaded). Do not stop and wait for a reload.

That's the command: write the stub, load the spec, introduce, and hand the presenter their first question. Do not create `config/` or `talks/` directories or template files by hand — the orchestrator creates those on demand from Step 0.5 onward.
