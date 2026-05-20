---
name: talksmith:upgrade-fork
description: Upgrade a downstream Talksmith fork with the latest core scripts, skills, role specs, and shared config files from upstream master. By default, shallow-clones `https://github.com/veigap/talksmith` at `main` into a tempdir and uses that as master — override with `--upstream <git-url>`, `--ref <branch-tag-or-sha>`, or `--local-master <path>` (offline / dev). Two subcommands. `diff` walks master's core paths (`.claude/`, `CLAUDE.md`, `README.md`, `config/principles.md`, `config/image-styles/`) and reports every file that would be created, modified, or pruned in the target fork, with optional unified diffs for text files. `apply` performs the copy. Per-fork content (`talks/`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`) is **never touched** — those files are the fork's accumulated state and belong to it. Requires `git` on `PATH` unless `--local-master` is used. CLI-safe, stdlib-only Python.
---

# talksmith:upgrade-fork — Sync a downstream fork with master core

Talksmith is forked-once-per-subject (see [README.md](../../../README.md) → *One fork per subject*). Every fork accumulates per-subject state — talks, profile, learnings, feedback log — that **must survive** across master upgrades. At the same time, the **core machinery** of Talksmith (orchestrator spec, role specs, skills, schemas, design principles, image-style catalog) lives in this master repo and improves over time. This skill keeps a downstream fork current with that core without ever clobbering the fork's accumulated state.

## What gets touched

| Path | Action on `apply` | Why |
|---|---|---|
| `.claude/` | **Mirror** from master (create/modify; with `--prune`, also remove files no longer in master) | Skills, agents, role specs, schemas, settings spec. Pure core. |
| `CLAUDE.md` | **Overwrite** from master | Orchestrator spec. Pure core. |
| `README.md` | **Overwrite** from master | Project README. Pure core. |
| `config/principles.md` | **Overwrite** from master | Design principles — shared spec. |
| `config/image-styles/` | **Mirror** from master (`--prune` removes stale templates) | SVG style catalog — shared spec. |

## What is never touched

| Path | Reason |
|---|---|
| `talks/` | Per-Talk content. Fork's product. |
| `config/profile.md` | Subject + presenter identity, set per fork in Step 0.5. |
| `config/learnings.md` | Cross-Talk learnings accumulated *within this fork*. |
| `config/feedback-backlog.md` | Live feedback audit trail. |
| `config/feedback-processed.md` | Promoted-feedback archive. |
| `knowledge/corpus/` *(if present at top level)* | Should not exist at top level — corpus records live under `talks/<Talk>/knowledge/corpus/`. Skipped defensively. |
| Anything else not in the *touched* list above | Default deny — never overwrite or delete files outside the explicit core path list. |

If a fork has hand-added skills in `.claude/skills/` that don't exist in master, they are **preserved** by default — `apply` only adds and modifies. Pass `--prune` to also delete files under `.claude/` and `config/image-styles/` that don't exist in master (use when you want a clean mirror).

## When to use

- A teaching collaborator opens an old fork after master has shipped new skills (e.g. `polish-ascii`, `feedback-cycle`, `upgrade-fork` itself).
- Mid-semester: master adds a Step 6 improvement; you want it in your active fork without re-cloning and losing this semester's talks.
- After hand-editing a skill in master, you want to push the change to several forks before resuming work.

## Invocation

The master repo is fetched from GitHub by default (`https://github.com/veigap/talksmith@main`). Override with `--upstream` / `--ref`, or skip the fetch entirely with `--local-master <path>`.

```bash
# 1) read-only diff against upstream main
python3 .claude/skills/upgrade-fork/upgrade_fork.py diff --fork /path/to/your/fork

# 2) apply (interactive y/N) against upstream main
python3 .claude/skills/upgrade-fork/upgrade_fork.py apply --fork /path/to/your/fork

# 3) apply against a specific tag / branch / sha
python3 .claude/skills/upgrade-fork/upgrade_fork.py apply --fork /path/to/your/fork --ref v1.2.0

# 4) apply against a fork (e.g. a teammate's branch on a different remote)
python3 .claude/skills/upgrade-fork/upgrade_fork.py apply --fork /path/to/your/fork \
    --upstream https://github.com/someone/talksmith.git --ref experimental

# 5) offline / dev: use a local clone of master instead of cloning from GitHub
python3 .claude/skills/upgrade-fork/upgrade_fork.py apply --fork /path/to/your/fork \
    --local-master /path/to/local/talksmith

# 6) apply + prune stale fork-only files under .claude/ and config/image-styles/
python3 .claude/skills/upgrade-fork/upgrade_fork.py apply --fork /path/to/your/fork --prune
```

## Inputs

### Master-source flags (common to `diff` and `apply`)

| Input | Required? | Default | Notes |
|---|---|---|---|
| `--upstream` | no | `https://github.com/veigap/talksmith.git` | Git URL to clone master from. Any URL `git clone` accepts. |
| `--ref` | no | `main` | Branch, tag, or sha to check out. Shallow-cloned (depth 1). |
| `--local-master` | no | — | Path to a local Talksmith repo to use instead of cloning. Required marker: the directory must contain `CLAUDE.md`. Skips the network entirely. |
| `--keep-clone` | no | off | Don't delete the cloned master tempdir on exit (debug). The path is printed to stderr. |

### `diff`-only

| Input | Required? | Notes |
|---|---|---|
| `--fork` | yes | Path to the fork directory. Must exist and contain a `CLAUDE.md` (sanity check that it's a Talksmith fork, not a random dir). |
| `--format` | optional | `human` (default, grouped + counts) or `json` (list of `{path, action, master_size, fork_size}`). JSON form also includes the resolved `upstream` and `ref` when the master came from a clone. |
| `--verbose` | optional | Print unified-diff bodies for every text file that differs (not just status lines). |

### `apply`-only

| Input | Required? | Notes |
|---|---|---|
| `--fork` | yes | Same sanity check as `diff`. |
| `--prune` | optional | Also delete files under `.claude/` and `config/image-styles/` that exist in fork but not in master. Default off. |
| `--dry-run` | optional | Print actions but don't touch the fork. |
| `--yes` | optional | Skip the interactive confirmation prompt (for scripted runs). Without it, `apply` prints a summary and waits for `y/N` on stdin. |

## Output

### `diff` — human (default)

```
upgrading fork: /Users/me/Documents/courses/llm-systems
master:        /Users/me/Documents/Austral/talksmith

Summary:
  4 files would be created
  3 files would be modified
  1 file would be pruned (with --prune)
  0 conflicts

Created (new in master, missing in fork):
  + .claude/skills/upgrade-fork/SKILL.md
  + .claude/skills/upgrade-fork/upgrade_fork.py
  + .claude/skills/feedback-cycle/SKILL.md
  + .claude/skills/feedback-cycle/feedback_cycle.py

Modified (differ between master and fork):
  ~ CLAUDE.md            (1.2 KiB smaller in fork)
  ~ .claude/roles/editor.md
  ~ config/image-styles/style.md

Pruneable (in fork only, not in master):
  - .claude/skills/old-skill-name/SKILL.md           (use --prune to remove)
```

### `apply` — summary

```
applied to /Users/me/Documents/courses/llm-systems:
  created:  4 file(s)
  modified: 3 file(s)
  pruned:   0 file(s)
  preserved (fork-owned, not touched): talks/, config/profile.md, config/learnings.md, config/feedback-backlog.md, config/feedback-processed.md
```

## Safety

- **`--fork` must contain `CLAUDE.md`** at its root. Otherwise the skill refuses to act — guards against pointing at the wrong directory.
- **`--fork` must not resolve to the same path as master.** Self-upgrade is rejected with exit 2.
- Every write is atomic per file (`.tmp + os.replace`). On per-file failure the partial state is the original file; the rest of the upgrade aborts.
- `--prune` deletions are restricted to subtrees under `.claude/` and `config/image-styles/` — never under `talks/`, `config/profile.md`, `config/learnings.md`, etc., even if you ask.

## Exit codes

- `0` — success or clean diff (no changes needed).
- `2` — bad input (fork doesn't exist, lacks `CLAUDE.md`, equals master, etc.).
- `3` — `apply` aborted by the user at the confirmation prompt.
- `4` — per-file copy failure mid-upgrade (rare; the file that failed is named in stderr).
