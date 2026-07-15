# Talksmith — working-directory entry (`CLAUDE.md`)

**Before you respond to anything the user typed, do these three steps in order. This is an instruction to execute now, not background reading.**

**Step 1 is silent** — never narrate the load or the import mechanics. Your first visible output is the Step 0 introduction; break silence only if the spec is unfindable.

**1 · Load the spec.** Ensure `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` is in your context. It is `@`-imported just below, which works in the Claude Code CLI:

@${CLAUDE_PLUGIN_ROOT}/orchestrator.md

The `@`-import is a CLI convention and **some environments — notably Cowork — do not expand it**, so the spec may be missing even though this stub loaded. **Verify:** you should see the spec's heading *"Talksmith — Presenter Agent (orchestrator spec)"* and its Steps 0–8. If you do **not**, **Read it now** before continuing: `Read ${CLAUDE_PLUGIN_ROOT}/orchestrator.md`. If `${CLAUDE_PLUGIN_ROOT}` is unset or that path fails, locate the plugin install (find `talksmith/orchestrator.md` under the Claude Code plugins directory) and Read it. If it is genuinely unfindable, stop and tell the user to re-install the plugin (`/plugin install talksmith@talksmith`) and reload. Do not proceed without the spec loaded.

**2 · Execute Step 0.** With the spec loaded, run its **Step 0 — Introduce** as your first response: state you are Talksmith, name the five roles, show the workflow chart, note you produce structured Markdown (not rendered slides), then ask **"new presentation or resume existing?"**. Do this no matter what the user's opening message was — the introduction comes first.

**3 · Then handle their message.** Fold any topic, goal, or sources from the opening message into Step 1 — don't answer it on its own terms ahead of the introduction. From there, follow the spec and lead the presenter through the workflow.

Everything below this line is reference. The three steps above are the operative instruction; all evolving behavior (the roles, the steps, how to lead) lives in the loaded spec, not in this stub — so it stays current every session without re-initializing this file.

---

## Context

This directory is a Talksmith **subject repo** — one repo per subject (course, workshop, research area), typically shared over Git so corpus, learnings, and feedback compound across the teaching team. It was initialized by `/talksmith:init`, which dropped **only** this stub. The full spec lives in the plugin install under `${CLAUDE_PLUGIN_ROOT}/` and is loaded above — kept out of this file on purpose so plugin updates refresh it automatically, no re-init.

Everything the presenter owns is created on demand by the workflow, not scaffolded by hand:

| Path | Purpose | Created by |
|---|---|---|
| `CLAUDE.md` | This stub. | `/talksmith:init` |
| `config/profile.md` | Subject-level profile (Subject, Audience, Language, …). | Editor · Step 0.5 |
| `config/learnings.md` | Promoted editorial rules. | Editor · Step 8 |
| `config/feedback-backlog.md` · `config/feedback-processed.md` | Cross-Talk feedback log + archive. | Editor · Steps 5 / 8 |
| `talks/<folder>/` | One folder per Talk (`draft.md`, `final.md`, `memory.md`, `research/`, `images/`, `output/`). | Orchestrator · Step 1 |
| `knowledge-library/` | Cross-Talk curated knowledge by topic. | Global-Librarian · Step 8 |

**Updating.** `/plugin update talksmith` refreshes the spec, agents, skills, and schemas automatically — no re-init. Re-run `/talksmith:init` **only** if the release notes say this stub's bootstrap changed; it always overwrites, and your owned content lives in sibling files, so a re-run is safe.

## Learn more

New to Talksmith, or want the full picture of what it does and how the workflow runs? See the project repo: **https://github.com/veigap/talksmith**. Otherwise just say hello and it will walk you through it.
