---
description: Drop the Talksmith working-directory stub (CLAUDE.md) and a build-artifact .gitignore into the current project root.
---

# /talksmith:init

One-shot bootstrap, run **once per working directory**. It writes the Talksmith working-directory stub as `CLAUDE.md` in the current directory, and adds a `.gitignore` covering Talksmith's regenerable build artifacts and caches (so they never get committed to the shared subject repo). On the next session, that stub loads the full operating spec and Talksmith introduces itself and starts; this command does not replicate that, it just puts the stub in place.

The stub is intentionally minimal and stable — it only knows how to load the real spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md`. The spec itself is **not** copied; it lives in the plugin install and refreshes automatically on `/plugin update`, so `/talksmith:init` rarely needs re-running.

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
   If `${CLAUDE_PLUGIN_ROOT}` is unset or that path fails, **locate the plugin install** (find `talksmith-orch.md` under the Claude Code plugins directory) and copy that file to `./CLAUDE.md`. Re-running `/talksmith:init` is the supported way to pick up stub changes; user content belongs in `config/`, `talks/`, never in `CLAUDE.md`. Emit:
   ```
   [init] CLAUDE.md written from the Talksmith stub (talksmith-orch.md). Any prior CLAUDE.md was overwritten.
   ```
4. **Add a `.gitignore` for build artifacts.** Talksmith regenerates decks, icon caches, and critique previews on every render — those must never be committed to the shared subject repo. Append the Talksmith ignore block to `./.gitignore` (creating the file if it doesn't exist), **guarded by a marker so it's idempotent and any pre-existing `.gitignore` is preserved** — never overwrite the user's own entries:
   ```bash
   # Idempotent: append only if the marker isn't already present; existing entries untouched.
   # printf (quoted args) so the written lines never inherit stray leading whitespace.
   grep -qF "# --- Talksmith ---" ./.gitignore 2>/dev/null || printf '%s\n' \
     '' \
     '# --- Talksmith --- (regenerable build artifacts & caches — keep out of Git)' \
     '.DS_Store' '.venv/' '__pycache__/' '*.pyc' \
     'talks/*/output/' 'talks/*/images/.critique/' '.icons/' \
     '.claude/settings.local.json' \
     >> ./.gitignore
   ```
   The source a Talk is built from — `draft.md`, `final.md`, `memory.md`, `research/corpus/`, `images/` (the committed SVG/PNG diagrams), and `config/` — stays tracked; only the regenerable `output/`, caches, and local settings are ignored. Emit:
   ```
   [init] .gitignore updated with Talksmith build-artifact ignores (any existing entries preserved).
   ```
5. Finish by telling the user to restart:
   ```
   Done. Close this session and open a new one in this directory to start creating —
   the stub will load Talksmith, which introduces itself and walks you through
   Step 0 → Step 0.5 (profile) → Step 1 (Frame your first Talk).

   Everything else — config/profile.md, config/learnings.md, the feedback logs,
   and the talks/ tree — is created by the orchestrator on demand. Nothing to scaffold by hand.
   ```

That's the entire command: write the stub, add the `.gitignore`, then hand off to the next session. Do not load the spec, run the workflow, or create `config/` / `talks/` here — the freshly-opened session does all of that.
