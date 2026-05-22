# Migration notes

Structural changes shipped by Talksmith master that downstream forks may need to align with by hand.

The [`talksmith:upgrade`](.claude/skills/upgrade/SKILL.md) skill is **additive only** — it creates and modifies files from master into your fork, but **never deletes** and **never touches per-Talk content under `talks/`**. That keeps the upgrade non-destructive, but it means structural changes (renames, removals, restructures) leave stale files in your fork and may leave per-Talk files misnamed against the new spec. This file is the channel for telling you what to fix.

The skill surfaces this file automatically: after `upgrade apply`, if this file was created or modified in the run, it prints a banner pointing you here. Read the dated section(s) added since your last upgrade and run the commands. Each section is dated and self-contained.

---

## 2026-05-21 — `master.md` split into `draft.md` + `final.md`, plus skill renames

### What changed in master

- **`master.md` was split into two files** per Talk:
  - `draft.md` — the working file used in Steps 1–5 (where the presenter authors and feedback bullets land).
  - `final.md` — the Step-6-derived deliverable, produced by `cp draft.md final.md` at the start of Polish. Steps 6–8 only touch `final.md`; `draft.md` is frozen after Step 5 so Polish is re-runnable.
- **Schema file renamed.** `.claude/schemas/master.md` → `.claude/schemas/draft.md` (the schema now documents both files in one spec).
- **PPTX output renamed.** `talks/<Talk>/output/master.pptx` → `talks/<Talk>/output/final.pptx`. Same for the transient `master.intermediate.md` → `final.intermediate.md`.
- **Skill renamed.** `.claude/skills/upgrade-fork/` → `.claude/skills/upgrade/`. Python file inside: `upgrade_fork.py` → `upgrade.py`. CLI prog name: `talksmith:upgrade-fork` → `talksmith:upgrade`.
- **CLI flag renames.** `feedback-cycle.py`: `--master` → `--draft` (Step 5 subcmds) or `--final` (rescue-open). `polish-ascii.py`: `--master` → `--final`, positional `master_path` → `final_path`. `md-to-pptx/convert.py` positional `master_md` → `final_md`. No behavior change otherwise.

### Manual steps for your fork

Run these from your fork's root. Each block is safe to copy-paste; each command is idempotent.

**1. Remove stale upstream files that `upgrade apply` couldn't delete.**

```bash
# old schema (the new one is .claude/schemas/draft.md)
rm -f .claude/schemas/master.md

# old skill directory (the new one is .claude/skills/upgrade/)
rm -rf .claude/skills/upgrade-fork
```

**2. Rename per-Talk files to match the new spec.** Per-Talk content under `talks/` is never touched by `upgrade apply`, so existing Talks will keep their `master.md` until you rename it. The orchestrator's Step 0 resume logic now expects `draft.md`.

```bash
# rename every existing Talk's master.md → draft.md
for talk in talks/*/; do
  if [ -f "$talk/master.md" ] && [ ! -f "$talk/draft.md" ]; then
    mv "$talk/master.md" "$talk/draft.md"
    echo "renamed: $talk/master.md → draft.md"
  fi
done

# rename rendered PPTX output(s), if any
for talk in talks/*/; do
  if [ -f "$talk/output/master.pptx" ] && [ ! -f "$talk/output/final.pptx" ]; then
    mv "$talk/output/master.pptx" "$talk/output/final.pptx"
    echo "renamed: $talk/output/master.pptx → final.pptx"
  fi
done
```

**3. (Optional) Re-run Step 6 (Polish) on any finalized Talks to produce a fresh `final.md`.** This is only needed if you want the Polish-cleaned version on disk for a Talk you already finalized under the old single-file model. The new model expects `draft.md` (the file you just renamed) to drive Step 6 — Talksmith will copy it to `final.md` and apply transforms (a) inline SVGs, (b) consolidate image refs, (c) rescue `[open]` feedback, (d) strip `Presenter feedback`. The orchestrator does this automatically; you don't need to.

**4. No action needed for these.**

- Your `config/profile.md`, `config/learnings.md`, `config/feedback-backlog.md`, `config/feedback-processed.md` — never touched by `upgrade apply`.
- Any custom skills you added under `.claude/skills/` that aren't in master — preserved.
- The `knowledge/corpus/` records inside each Talk — preserved (those are per-Talk content).
- The CLI flag renames in skills are mechanical implementation details — the editor role specs already point at the new flags, so no action required from you.

---

<!-- When adding the next migration section, paste a new `## YYYY-MM-DD — <title>` block above this comment, mirroring the structure above. Each section should be self-contained so a user reading from any starting point can apply only the sections added since their last upgrade. -->
