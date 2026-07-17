# Talksmith — working-directory entry for Codex (`AGENTS.md`)

This directory is a Talksmith **subject working directory**. Its full operating instructions are **not** in this file — they live in **`CLAUDE.md`** in this same folder, a single source shared by every agent so the two files can never drift.

**Before you respond to anything the user typed: open `CLAUDE.md` in this directory and follow it exactly, top to bottom.** It is written for any capable agent, not only Claude Code — it tells you to load the Talksmith spec (`orchestrator.md`) and then run the introduction and the workflow.

Two of its instructions assume Claude Code conventions you don't have; use the fallback it already spells out:

- The `@…/orchestrator.md` **import line** (near the top of `CLAUDE.md`) does nothing in your environment — it won't pull the spec in. Load it yourself instead, as the next point describes.
- `${CLAUDE_PLUGIN_ROOT}` is **not set** for you. Wherever `CLAUDE.md` uses it, fall back to its own instruction: locate `talksmith/orchestrator.md` under the Claude Code plugins directory (typically `~/.claude/plugins/…`) and **Read it**. Do not proceed until the spec — heading *"Talksmith — Presenter Agent (orchestrator spec)"*, Steps 0–8 — is in your context. If it is genuinely unfindable, stop and tell the user the Talksmith plugin install can't be located.

Everything else in `CLAUDE.md` — the three-step boot, Step 0, the workflow — applies to you unchanged. `CLAUDE.md` is the source of truth; this file only points at it.
