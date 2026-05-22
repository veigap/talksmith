---
name: talksmith:upgrade
description: Sync a downstream Talksmith fork with `https://github.com/veigap/talksmith` @ `main`. Two subcommands. `diff` reports every file that would be created, modified, deleted, or renamed in the target fork. `apply` does both layers in one pass — (1) strict-mirror within master-owned paths (`.claude/`, `CLAUDE.md`, `README.md`, `MIGRATION.md`, `config/principles.md`, `config/image-styles/`), and (2) declared renames parsed from `<!-- migration:rename from=... to=... -->` directives embedded in master's MIGRATION.md, typically renaming per-Talk paths under `talks/` so they match new specs. Renames preserve file content — only paths change. User-owned data (the *bytes inside* `talks/<Talk>/*.md`, `config/profile.md`, etc.) is never overwritten or deleted. Conflicts (both old and new exist) are skipped and reported. `.claude/settings.local.json` is excluded from strict-mirror. Requires `git` on `PATH`. CLI-safe, stdlib-only Python.
---

# talksmith:upgrade — Mirror master into a downstream fork (with declared migrations)

Talksmith is forked-once-per-subject (see [README.md](../../../README.md) → *One fork per subject*). A fork accumulates per-subject state — talks, profile, learnings, feedback log — that **must survive** across upgrades. Master ships the core machinery (orchestrator spec, role specs, skills, schemas, design principles, image-style catalog) and the migration directives needed to keep per-fork content aligned with structural changes upstream. This skill applies both, in one pass.

**Single source of master.** Always `https://github.com/veigap/talksmith` @ `main`. No flags to override.

## Two layers, one `apply`

### Layer 1 — strict mirror within master-owned paths

These paths are owned by master. The fork is brought into exact alignment with master's tree:

- `.claude/` (skills, roles, schemas, settings spec)
- `CLAUDE.md`, `README.md`, `MIGRATION.md`
- `config/principles.md`
- `config/image-styles/`

Files in master that are missing in the fork → created. Files in both that differ → fork's copy overwritten. Files in the fork's master-owned tree that no longer exist in master → **deleted from the fork.** A rename upstream (e.g. `.claude/schemas/master.md` → `.claude/schemas/draft.md`) becomes "old path deleted + new path created" automatically.

**Exclusion:** `.claude/settings.local.json` is user-local config (gitignored, never shipped by master) and is never touched.

### Layer 2 — declared renames outside the strict-mirror tree

Master can ship structural renames that affect content *outside* its owned tree — typically per-Talk path renames under `talks/`. These are declared inline in `MIGRATION.md` using HTML-comment directives the skill parses:

```html
<!-- migration:rename from="talks/*/master.md" to="draft.md" -->
```

- `from` is a relative-path glob with a single `*` matching one path segment.
- `to` is the new basename — same-directory rename. The file's parent path is preserved; only the leaf changes.

For each directive, the skill walks the matching paths in the fork and applies the rename **idempotently**:

| Fork state | Skill behavior |
|---|---|
| old exists, new doesn't | Rename (`os.replace`). File content preserved unchanged. |
| old doesn't exist | Already done. Silent no-op. |
| both exist | Conflict — **skipped** and reported. User resolves by hand, then re-runs. |

**Renames preserve content.** They change the path of a file, not its bytes. The skill never opens, overwrites, or merges file content during a rename.

## What is never touched

| Path / data | Why |
|---|---|
| The *bytes inside* `talks/<Talk>/*` | Your per-Talk content — drafts, feedback, corpus records, images. Renames may move the path; the content is preserved verbatim. |
| `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md` | Per-fork accumulated state. Neither mirrored nor renamed. |
| `.claude/settings.local.json` | User-local config master never ships. |
| Build artifacts (`__pycache__`, `*.pyc`, `.DS_Store`) | Ignored on both sides of the comparison. |

If a fork has hand-added skills under `.claude/skills/` that aren't in master, **they will be deleted** by the strict-mirror step. The model is: customize via the user-owned trees, not by adding files inside master-owned paths.

## When to use

- A teaching collaborator opens an old fork after master has shipped new skills, restructures, or per-Talk file renames.
- Mid-semester: master adds a Step 6 improvement and a path rename; you want both in your active fork without losing this semester's talks.
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
| `--dry-run` | optional | Print actions but don't touch the fork. Useful when reviewing a large delete or rename plan before committing. |
| `--yes` | optional | Skip the interactive confirmation prompt. Without it, `apply` prints the plan, lists the files that would be deleted or renamed, and waits for `y/N`. |

## Output

### `diff`

```
fork:   /Users/me/Documents/courses/llm-systems
master: https://github.com/veigap/talksmith.git@main

Summary:
  4 file(s) would be created   (master-owned paths)
  3 file(s) would be modified  (master-owned paths)
  6 file(s) would be deleted   (master-owned paths, no longer in master)
  5 file(s) would be renamed   (declared migrations, content preserved)
  18 file(s) already up-to-date (master-owned paths)

Created (new in master, missing in fork):
  + .claude/skills/upgrade/SKILL.md
  + .claude/skills/upgrade/upgrade.py
  + .claude/schemas/draft.md
  + MIGRATION.md

Modified (differ between master and fork):
  ~ CLAUDE.md  (+1234 bytes)
  ~ .claude/roles/editor.md  (+512 bytes)

Deleted (in fork but no longer in master — usually a rename or removal upstream):
  - .claude/schemas/master.md
  - .claude/skills/upgrade-fork/SKILL.md
  - .claude/skills/upgrade-fork/upgrade_fork.py

Renamed (per declared migrations — content preserved, only path changes):
  → talks/biomedical-signals/master.md  →  talks/biomedical-signals/draft.md
  → talks/biomedical-signals/output/master.pptx  →  talks/biomedical-signals/output/final.pptx
  → talks/quantum-intro/master.md  →  talks/quantum-intro/draft.md
```

### `apply` — summary

```
applied to /Users/me/Documents/courses/llm-systems:
  created:  4 file(s)
  modified: 3 file(s)
  deleted:  6 file(s)
  renamed:  5 file(s) (content preserved)
  preserved (user-owned, not touched): talks/  (content), config/profile.md, config/learnings.md, config/feedback-backlog.md, config/feedback-processed.md
```

When `MIGRATION.md` was created or updated in the run, an additional banner is printed pointing the user at it for *non-mechanical* steps (renames are already done; the banner is for things like "re-run Step 6 on a finalized Talk" that need user judgement).

If any declared rename hit a conflict (both old and new paths existed), the conflict list is printed and those renames are skipped. The user resolves by hand and re-runs.

## Safety

- **`--fork` must contain `CLAUDE.md`** at its root. Otherwise the skill refuses to act.
- **`--fork` must not resolve to the same path as the freshly cloned master.** Self-upgrade is rejected with exit 2.
- **Strict-mirror deletes are scoped to master-owned paths only.** The `_collect()` walk only ever returns paths within `CORE_PATHS`, so the `f_files - m_files` set difference can never reach user-owned content.
- **Migration renames only change paths, never content.** The implementation uses `os.replace(old, new)` — a single atomic rename. The file's bytes are not opened, read, or written. If the rename fails (e.g. permission denied), the original file is intact.
- **Conflicts halt the rename, never overwrite.** If both old and new paths exist for a declared migration, the skill skips that rename and reports the conflict. Neither file is touched.
- Every strict-mirror write is atomic per file (`.tmp + os.replace`).
- Empty directories left behind after deletions are removed bottom-up so the fork tree stays clean.

## Exit codes

- `0` — success or clean diff (no changes needed).
- `2` — bad input (fork doesn't exist, lacks `CLAUDE.md`, equals master, etc.).
- `3` — `apply` aborted by the user at the confirmation prompt.
- `4` — per-file copy or delete failure mid-upgrade (rare; the file that failed is named in stderr).

## Migration directive syntax (for master maintainers)

To declare a same-directory rename that should be applied to forks on the next upgrade, embed an HTML comment inside a dated section of `MIGRATION.md`:

```html
<!-- migration:rename from="<glob>" to="<basename>" -->
```

- `from` — relative-path glob from the repo root. Single `*` allowed at one path segment (matches any name at that level).
- `to` — new basename. Same-directory rename only; the parent path of each match is preserved.

Idempotent by construction: each directive is safe to ship and safe to re-apply. The skill never tracks "which migrations have been applied" because the filesystem state itself is the record — if the old path is gone, the rename is done.
