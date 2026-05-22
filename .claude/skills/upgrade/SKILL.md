---
name: talksmith:upgrade
description: Sync a downstream Talksmith fork with the latest core scripts, skills, role specs, and shared config files from `https://github.com/veigap/talksmith` @ `main`. Two subcommands. `diff` walks master's core paths (`.claude/`, `CLAUDE.md`, `README.md`, `MIGRATION.md`, `config/principles.md`, `config/image-styles/`) and reports every file that would be created or modified in the target fork. `apply` performs the copy — **create and modify only**; the fork is never deleted from. Per-fork content (`talks/`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`) is **never touched**. When `MIGRATION.md` was just created or updated, `apply` surfaces a banner pointing the user to it for manual steps (renames, removals) the skill is intentionally not allowed to perform. Requires `git` on `PATH`. CLI-safe, stdlib-only Python.
---

# talksmith:upgrade — Sync a downstream fork with master core

Talksmith is forked-once-per-subject (see [README.md](../../../README.md) → *One fork per subject*). Every fork accumulates per-subject state — talks, profile, learnings, feedback log — that **must survive** across master upgrades. At the same time, the **core machinery** (orchestrator spec, role specs, skills, schemas, design principles, image-style catalog) lives in master and improves over time. This skill keeps a downstream fork current with that core without ever clobbering the fork's accumulated state.

**Single source of master.** Always `https://github.com/veigap/talksmith` @ `main`. No flags to override — that's deliberate. If you need to upgrade from somewhere else, this isn't the tool.

**Additive only.** `apply` creates and modifies files. It never deletes anything from the fork. If master removed or renamed a file (e.g. `master.md` schema → `draft.md`), the old file lingers in your fork until you delete it by hand. The skill stays simple, predictable, and non-destructive.

**Structural changes are surfaced via `MIGRATION.md`.** When master ships a rename, removal, or restructure, it documents the manual steps in [`MIGRATION.md`](../../../MIGRATION.md) at the repo root. `apply` copies that file into the fork like any other core file, **and** detects when it was just created or updated and prints a banner pointing the user to it. The user reads the dated section(s) added since their last upgrade and runs the suggested commands by hand. The skill never auto-executes — predictability over magic, especially because per-Talk content under `talks/` can need renames the skill is forbidden from doing.

## What gets touched

| Path | Action on `apply` | Why |
|---|---|---|
| `.claude/` | **Mirror** from master (create new files; overwrite changed files) | Skills, agents, role specs, schemas, settings spec. Pure core. |
| `CLAUDE.md` | **Overwrite** from master | Orchestrator spec. Pure core. |
| `README.md` | **Overwrite** from master | Project README. Pure core. |
| `MIGRATION.md` | **Overwrite** from master | Manual-step log for structural changes. After `apply`, a banner points the user here if the file was just created or updated. |
| `config/principles.md` | **Overwrite** from master | Design principles — shared spec. |
| `config/image-styles/` | **Mirror** from master (create + overwrite) | SVG style catalog — shared spec. |

## What is never touched

| Path | Reason |
|---|---|
| `talks/` | Per-Talk content. Fork's product. |
| `config/profile.md` | Subject + presenter identity, set per fork in Step 0.5. |
| `config/learnings.md` | Cross-Talk learnings accumulated *within this fork*. |
| `config/feedback-backlog.md` | Live feedback audit trail. |
| `config/feedback-processed.md` | Promoted-feedback archive. |
| Anything else not in the *touched* list above | Default deny — never overwrite files outside the explicit core path list. |
| **Any fork-only file**, even under `.claude/` or `config/image-styles/` | The skill never deletes from the fork. Old/renamed files from master are not cleaned up automatically. |

If a fork has hand-added skills, custom role specs, or extra image-style templates that don't exist in master, they are **always preserved**.

## When to use

- A teaching collaborator opens an old fork after master has shipped new skills.
- Mid-semester: master adds a Step 6 improvement; you want it in your active fork without re-cloning and losing this semester's talks.
- After hand-editing a skill in master, you want to pull the change into a fork before resuming work.

## Invocation

```bash
# 1) read-only diff against upstream main
python3 .claude/skills/upgrade/upgrade.py diff --fork /path/to/your/fork

# 2) apply (interactive y/N)
python3 .claude/skills/upgrade/upgrade.py apply --fork /path/to/your/fork

# 3) apply, scripted (no prompt)
python3 .claude/skills/upgrade/upgrade.py apply --fork /path/to/your/fork --yes

# 4) preview an apply without writing
python3 .claude/skills/upgrade/upgrade.py apply --fork /path/to/your/fork --dry-run
```

## Inputs

### `diff`

| Input | Required? | Notes |
|---|---|---|
| `--fork` | yes | Path to the fork directory. Must exist and contain a `CLAUDE.md` (sanity check that it's a Talksmith fork, not a random dir). |

### `apply`

| Input | Required? | Notes |
|---|---|---|
| `--fork` | yes | Same sanity check as `diff`. |
| `--dry-run` | optional | Print actions but don't touch the fork. |
| `--yes` | optional | Skip the interactive confirmation prompt (for scripted runs). Without it, `apply` prints a summary and waits for `y/N` on stdin. |

## Output

### `diff`

```
fork:   /Users/me/Documents/courses/llm-systems
master: https://github.com/veigap/talksmith.git@main

Summary:
  4 file(s) would be created
  3 file(s) would be modified
  18 file(s) already up-to-date

Created (new in master, missing in fork):
  + .claude/skills/upgrade/SKILL.md
  + .claude/skills/upgrade/upgrade.py
  + .claude/skills/feedback-cycle/SKILL.md
  + .claude/skills/feedback-cycle/feedback_cycle.py

Modified (differ between master and fork):
  ~ CLAUDE.md        (+1234 bytes)
  ~ .claude/roles/editor.md  (+512 bytes)
  ~ config/image-styles/style.md  (-87 bytes)
```

### `apply` — summary

```
applied to /Users/me/Documents/courses/llm-systems:
  created:  4 file(s)
  modified: 3 file(s)
  preserved (fork-owned, not touched): talks/, config/profile.md, config/learnings.md, config/feedback-backlog.md, config/feedback-processed.md
```

When `MIGRATION.md` was created or updated in the run, an additional banner is printed:

```
────────────────────────────────────────────────────────────────────────
⚠  MIGRATION.md was updated in this upgrade.

   Master shipped structural changes (renames, removals, restructures)
   that this skill is intentionally not allowed to perform on your fork.
   Open the file and run the manual steps in the dated section(s) added
   since your last upgrade:

     /Users/me/Documents/courses/llm-systems/MIGRATION.md

   Without those steps, your fork will keep working but may carry stale
   files from upstream renames, and per-Talk content under talks/ may
   drift out of alignment with the new spec.
────────────────────────────────────────────────────────────────────────
```

## Safety

- **`--fork` must contain `CLAUDE.md`** at its root. Otherwise the skill refuses to act — guards against pointing at the wrong directory.
- **`--fork` must not resolve to the same path as the freshly cloned master.** Self-upgrade is rejected with exit 2.
- Every write is atomic per file (`.tmp + os.replace`). On per-file failure the partial state is the original file; the rest of the upgrade aborts.
- **`apply` never deletes.** A fork can never lose data to this skill. If master removed or renamed a file, the old file remains in the fork until you delete it by hand (consulting MIGRATION.md).

## Exit codes

- `0` — success or clean diff (no changes needed).
- `2` — bad input (fork doesn't exist, lacks `CLAUDE.md`, equals master, etc.).
- `3` — `apply` aborted by the user at the confirmation prompt.
- `4` — per-file copy failure mid-upgrade (rare; the file that failed is named in stderr).
