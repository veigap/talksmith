# Migration notes

Structural changes shipped by Talksmith master. Applied to forks by [`talksmith:upgrade`](.claude/skills/upgrade/SKILL.md) in two layers, in one `apply`:

1. **Strict mirror within master-owned paths** (`.claude/`, `CLAUDE.md`, `README.md`, `MIGRATION.md`, `config/principles.md`, `config/image-styles/`) — create / modify / delete to match master exactly.
2. **Declared renames** parsed from `<!-- migration:rename from="<glob>" to="<basename>" -->` directives in the dated sections below — same-directory renames typically affecting per-Talk paths under `talks/`. Idempotent: rename if only old exists; no-op if only new exists; skip + report if both exist. **Renames preserve content** — file bytes are untouched, only paths change.

User-owned content (the *bytes inside* `talks/<Talk>/*` and the four `config/{profile,learnings,feedback-backlog,feedback-processed}.md` files) is never overwritten or deleted. The skill prints a banner pointing here whenever this file was created or updated in a run.

---

## 2026-05-21 — `master.md` split into `draft.md` + `final.md`

**What changed in master:**

- Per-Talk `master.md` split into `draft.md` (working file, Steps 1–5) + `final.md` (polished deliverable, produced by `cp draft.md final.md` at the start of Step 6 so Polish is re-runnable).
- PPTX output renamed: `output/master.pptx` → `output/final.pptx` (same for the transient `master.intermediate.md` → `final.intermediate.md`).
- Schema rename (`.claude/schemas/master.md` → `draft.md`) and skill rename (`upgrade-fork` → `upgrade`) — master-owned, handled by strict-mirror.
- CLI flag renames inside the affected skills (`--master` → `--draft`/`--final`) — internal; role specs already updated, no action needed.

**Declared renames** (applied automatically):

<!-- migration:rename from="talks/*/master.md" to="draft.md" -->
<!-- migration:rename from="talks/*/output/master.pptx" to="final.pptx" -->
<!-- migration:rename from="talks/*/output/master.intermediate.md" to="final.intermediate.md" -->

**Needs your judgement** (skill won't do it):

- **(Optional) Re-run Step 6 (Polish) on previously-finalized Talks** to produce a fresh `final.md`. The orchestrator does this automatically when you resume the Talk — only needed if you want it pre-rendered without re-opening.

---

<!--
Adding the next migration section:
- Paste a new `## YYYY-MM-DD — <title>` block above this comment.
- For mechanical renames (within talks/ or other user-owned trees), declare inline with `<!-- migration:rename from="<glob>" to="<basename>" -->`. Single `*` wildcard at one path segment; `to` is a same-directory basename. Idempotent.
- For master-owned-tree changes (`.claude/`, etc.), no directive needed — strict-mirror handles them.
- For non-mechanical steps that need user judgement, describe in prose.
-->
