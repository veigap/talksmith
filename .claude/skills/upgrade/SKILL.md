---
name: talksmith:upgrade
description: Sync a downstream Talksmith fork with `https://github.com/veigap/talksmith` @ `main`. Two subcommands. `diff` reports every file that would be created, modified, or deleted in the target fork. `apply` mirrors master into the fork — **user-owned content** (`talks/`, `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`, plus `.claude/settings.local.json`) is never touched; **master-owned content** (`.claude/`, `CLAUDE.md`, `README.md`, `config/principles.md`, `config/diagram-style.md`) is strict-mirrored, so renames and removals upstream propagate automatically. When structural changes affect user-owned paths too (e.g. per-Talk file naming conventions), the orchestrator infers the required adjustment from the upgrade diff and applies it by hand when next resuming the Talk — the skill never auto-edits user-owned content. Requires `git` on `PATH`. CLI-safe, stdlib-only Python.
---

# talksmith:upgrade — Mirror master into a downstream fork

Talksmith is forked-once-per-subject (see [README.md](../../../README.md) → *One fork per subject*). Every fork accumulates per-subject state — talks, profile, learnings, feedback log — that **must survive** across upgrades. The **core machinery** (orchestrator spec, role specs, skills, schemas, design principles, image-style catalog) lives in master and improves over time. This skill keeps a fork's master-owned tree in lockstep with master without touching the fork's accumulated state.

**Single source of master.** Always `https://github.com/veigap/talksmith` @ `main`. No flags to override.

**The master-owned path set is itself shipped from master.** On each run, the script reads `.claude/upgrade-paths.txt` from the freshly cloned master and uses it as the list of paths to mirror. This means: when master adds a new master-owned path, the **next** `upgrade apply` in any fork picks it up — no two-step upgrade needed, even when the running script predates the addition. A hardcoded `FALLBACK_CORE_PATHS` inside the script is used only when the manifest is missing or malformed (e.g. running against an older master).

## Two paths, two rules

| Tree | Policy on `apply` |
|---|---|
| **User-owned** — `talks/` (every byte under it), `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md`, `.claude/settings.local.json` | **Never touched.** Full stop. |
| **Master-owned** — `.claude/`, `CLAUDE.md`, `README.md`, `config/principles.md`, `config/diagram-style.md` | **Strict mirror.** Files missing in fork → created. Files in both that differ → fork's copy overwritten. Files in the fork's master-owned tree that no longer exist in master → **deleted** from the fork. |

A rename in master is naturally just "old path gone + new path appears" under strict mirror — both halves happen in one `apply`.

## What strict-mirror catches

| Master change | What `apply` does in the fork |
|---|---|
| New file added under `.claude/skills/foo/SKILL.md` | Creates it. |
| Existing file edited (e.g. `CLAUDE.md`) | Overwrites the fork's copy. |
| File renamed (e.g. `.claude/schemas/master.md` → `.claude/schemas/draft.md`) | Deletes `master.md` from the fork, creates `draft.md` from master. |
| Skill directory renamed (e.g. `.claude/skills/upgrade-fork/` → `.claude/skills/upgrade/`) | Deletes every file under the old dir, creates every file under the new dir. Empty parent directories get cleaned up. |
| File removed (e.g. an obsolete style template) | Deletes it from the fork. |

## What strict-mirror does NOT do

- Touch any byte under `talks/` — your per-Talk content is yours, full creative authority.
- Touch the four top-level `config/` files (`profile`, `learnings`, `feedback-backlog`, `feedback-processed`) — accumulated per-fork state.
- Touch `.claude/settings.local.json` — gitignored user-local config.
- Delete build artifacts (`__pycache__`, `.pyc`, `.DS_Store`) — those are ignored on both sides of the comparison.

## Handling stale user-owned content after an upgrade

When master ships a structural change, the strict-mirror step updates the spec (CLAUDE.md, role specs, schemas) but leaves user-owned content alone. This is correct — the skill must never silently edit a user's drafts, feedback logs, learnings, or rendered output. **But it does mean user-owned paths can drift out of alignment with the updated spec.** The most common case: master renames a per-Talk file convention (e.g. `master.md` → `draft.md`), so existing `talks/<Talk>/master.md` files in the fork no longer match what the orchestrator expects to read.

**The rule for handling this is on the orchestrator, not the skill.** After `upgrade apply` reports its diff, the orchestrator (the LLM operating the fork) is expected to:

1. **Read the upgrade diff** — the list of files that were created, modified, or deleted in the master-owned tree gives a complete picture of what restructured upstream.
2. **Infer the corresponding adjustment for user-owned content.** A schema rename like `.claude/schemas/master.md` → `draft.md` strongly implies a matching per-Talk rename `talks/*/master.md` → `talks/*/draft.md`. A renamed output file (e.g. `output/master.pptx` → `output/final.pptx` documented in the new CLAUDE.md spec for Step 8) implies the existing rendered output in any Talk should be renamed similarly.
3. **Apply the inferred adjustment when next opening the affected Talk** — typically at the Step-0 Resume hand-off, before reading `memory.md` and continuing the workflow. A rename preserves the file's bytes; only the path changes. If a path conflict exists (both old and new already present), stop and ask the presenter which to keep.
4. **Never touch user content** beyond renaming paths. If the new spec implies a *semantic* change (e.g. "re-run Step 6 to produce `final.md` from `draft.md`"), surface it to the presenter and let them decide whether to re-run; don't silently re-execute workflow steps.

This puts inference where it belongs — the LLM has the context to read the diff and reason about implications. The skill's job is just to surface what changed mechanically and to leave user data alone.

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
| `--dry-run` | optional | Print actions but don't touch the fork. Useful when reviewing a large delete list before committing. |
| `--yes` | optional | Skip the interactive confirmation prompt (for scripted runs). Without it, `apply` prints a summary, lists the files that would be deleted, and waits for `y/N` on stdin. |

## Output

### `diff`

```
fork:   /Users/me/Documents/courses/llm-systems
master: https://github.com/veigap/talksmith.git@main

Summary:
    4 file(s) would be created
    3 file(s) would be modified
    6 file(s) would be deleted (no longer in master)
   18 file(s) already up-to-date

Created (new in master, missing in fork):
  + .claude/skills/upgrade/SKILL.md
  + .claude/skills/upgrade/upgrade.py
  + .claude/schemas/draft.md
  + .claude/roles/global-librarian.md

Modified (differ between master and fork):
  ~ CLAUDE.md  (+1234 bytes)
  ~ .claude/roles/editor.md  (+512 bytes)

Deleted (in fork but no longer in master — usually a rename or removal upstream):
  - .claude/schemas/master.md
  - .claude/skills/upgrade-fork/SKILL.md
  - .claude/skills/upgrade-fork/upgrade_fork.py
```

### `apply` — summary

```
applied to /Users/me/Documents/courses/llm-systems:
  created:  4 file(s)
  modified: 3 file(s)
  deleted:  6 file(s)
  preserved (user-owned, not touched): talks/, config/profile.md, config/learnings.md, config/feedback-backlog.md, config/feedback-processed.md
```

The output is the orchestrator's input for the inference step described above — read the created/modified/deleted lists and reason about whether any user-owned content needs to be renamed when next opening an affected Talk.

## Safety

- **`--fork` must contain `CLAUDE.md`** at its root. Otherwise the skill refuses to act — guards against pointing at the wrong directory.
- **`--fork` must not resolve to the same path as the freshly cloned master.** Self-upgrade is rejected with exit 2.
- **Deletions are scoped to master-owned paths only.** The `_collect()` walk only ever returns paths listed in `.claude/upgrade-paths.txt` (or the hardcoded fallback), so the `f_files - m_files` set difference can never reach user-owned content. `talks/` and the user-owned config files are structurally unreachable by the delete step.
- **`.claude/settings.local.json` is explicitly excluded.** The skill subtracts it from the delete set unconditionally.
- Every write is atomic per file (`.tmp + os.replace`). On per-file failure the partial state is the original file; the rest of the upgrade aborts.
- Empty directories left behind after deletions (e.g. an emptied `.claude/skills/upgrade-fork/`) are removed bottom-up so the fork tree stays clean.

## Exit codes

- `0` — success or clean diff (no changes needed).
- `2` — bad input (fork doesn't exist, lacks `CLAUDE.md`, equals master, etc.).
- `3` — `apply` aborted by the user at the confirmation prompt.
- `4` — per-file copy or delete failure mid-upgrade (rare; the file that failed is named in stderr).
