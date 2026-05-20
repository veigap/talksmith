---
name: talksmith:feedback-cycle
description: Step 5 (Review) bookkeeping helper for the editor role. Five subcommands wrapping the mechanical line-edits around the presenter-feedback protocol so the editor (LLM) only has to author the actual content fix, the resolution wording, and the tag list — everything else is done by stdlib Python with exact line numbers. `find-closed-unmirrored` lists `[closed]` bullets in `master.md` that don't yet have a matching row in `feedback-backlog.md`. `stamp` rewrites a single unstamped bullet (by line number) to `- [open] YYYY-MM-DD — "<verbatim>"`. `close` flips a single `[open]` bullet to `[closed]` and inserts the `  Resolution: <text>` continuation line. `mirror-row` appends a fully-formed entry to `feedback-backlog.md` for one `[closed]` bullet, with location auto-derived from the nearest H1/H2 above it. `rescue-open` walks every still-`[open]` bullet and appends them to `# Open questions` (Step 6 (c)). Companion to [`find-open-notes`](../find-open-notes/SKILL.md), which detects the unstamped bullets this skill then stamps. CLI-safe, stdlib-only Python.
---

# talksmith:feedback-cycle — Mechanical bookkeeping for Step 5 Review

The Step 5 cycle has eight operations. **Three are pure LLM work**: applying the content change a bullet implies, authoring the one-sentence resolution, and picking tags. **The other five are mechanical line ops** — finding, stamping, closing, mirroring, rescuing. This skill is those five ops, so the editor never reads `master.md` end-to-end during a normal Review round.

It is **the companion to [`find-open-notes`](../find-open-notes/SKILL.md)**, which already covers the first detection step. Together they bracket the whole cycle:

```
find-open-notes ──┐
                  │
                  ▼
   ┌──── for each unstamped bullet ────────────────────────────────┐
   │                                                                │
   │  feedback-cycle:stamp ─→ editor applies fix ─→ editor writes  │
   │                                                  resolution    │
   │                                                       │        │
   │                            feedback-cycle:close ◀─────┘        │
   │                                       │                        │
   │                            editor picks tags                   │
   │                                       │                        │
   │                            feedback-cycle:mirror-row           │
   │                                                                │
   └────────────────────────────────────────────────────────────────┘

at Step 6 (c):  feedback-cycle:rescue-open
```

## When to use

- **Step 5 (Review), every round** — once the presenter signals "ready" / "done", run `find-open-notes` then call `stamp` / `close` / `mirror-row` per bullet.
- **Step 6 (c)** — call `rescue-open` to preserve un-applied `[open]` bullets into `# Open questions` before the `Presenter feedback`-strip pass.

## Subcommands

### `find-closed-unmirrored`

List `[closed]` bullets in `master.md` whose verbatim text is **not** already an entry in `feedback-backlog.md` for the current Talk. Used to catch closed-but-not-mirrored bullets — e.g. when a previous session closed a bullet but crashed before the mirror step.

```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py find-closed-unmirrored \
    --master talks/<Talk>/master.md \
    --backlog knowledge/feedback-backlog.md \
    [--format json|human]
```

Output (human):
```
found 2 closed bullet(s) not yet in backlog:

  line 318  Slide "Pan-Tompkins — el filtro pasa-banda"
            "tighten the math notation in the integrator step"
            Resolution: replaced LaTeX-heavy notation with discrete-time difference equation
  line 624  Section "Conclusiones"
            "agregar takeaway sobre fs vs CPU budget"
            Resolution: added trade-off bullet to slide 3
```

JSON (one object per bullet): `{line, location, text, resolution, date}`.

### `stamp`

Rewrite a single **unstamped** bullet to `[open]` form. Atomic per call.

```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py stamp \
    --master talks/<Talk>/master.md \
    --line 523 \
    [--date 2026-05-15]
```

Behaviour:
- Reads line N. Expects `- <text>` or `- "<text>"`. If text isn't already double-quoted, wraps it.
- Rewrites in place to: `- [open] {date} — "<text>"`. Default date = today (`datetime.date.today().isoformat()`).
- If the bullet is already stamped (`[open]` or `[closed]`), exits 0 with `noop: line N already stamped`. Never re-stamps.
- Atomic write (`.tmp + os.replace`).

### `close`

Flip a single `[open]` bullet to `[closed]` and write the `Resolution:` continuation line.

```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py close \
    --master talks/<Talk>/master.md \
    --line 523 \
    --resolution "<one-line summary of what changed in the slide>"
```

Behaviour:
- Reads line N. Expects `- [open] YYYY-MM-DD — "<verbatim>"`. Keeps the original date.
- Rewrites L_N to `- [closed] YYYY-MM-DD — "<verbatim>"`.
- Looks at line N+1: if it already starts with `  Resolution:`, replace it; otherwise insert a new line `  Resolution: <resolution>` at N+1.
- The editor (LLM) is the only one who writes the resolution text — the skill never invents it.

### `mirror-row`

Append one closed-bullet entry to `feedback-backlog.md`.

```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py mirror-row \
    --master talks/<Talk>/master.md \
    --backlog knowledge/feedback-backlog.md \
    --line 523 \
    --tags "slide-content,too-dense,rewrite"
```

Behaviour:
- Reads line N + N+1 from `master.md`. Expects `[closed]` bullet + Resolution continuation.
- Auto-derives `location` by walking backwards from N to the nearest `## ` (slide) and `# ` (section). Special-cases `# Thesis`, `# Agenda`, `# Conclusion(es)`.
- Auto-derives `talk` folder from the master path (`talks/<folder>/master.md` → `<folder>`).
- Auto-uses the date already stamped on the `[closed]` line.
- Appends to `## Entries` in the backlog using the schema row format (see [`.claude/schemas/feedback-backlog.md`](../../schemas/feedback-backlog.md)). The skill never invents tags — the editor picks them; if `--tags` is omitted, the row is appended with `tags: []` and a warning is printed.

### `rescue-open`

Walk `master.md` for every still-`[open]` bullet and append entries under `# Open questions`. Used by Step 6 (c) Polish to preserve un-applied feedback before the `Presenter feedback` strip.

```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py rescue-open \
    --master talks/<Talk>/master.md \
    [--dry-run]
```

Behaviour:
- Finds every `- [open] YYYY-MM-DD — "<verbatim>"`.
- For each: appends `- <location> — "<verbatim>"` to the `# Open questions` section. Creates the section before `# Cut material` (or at end of file) if missing.
- Idempotent: skips lines already present in `# Open questions`.
- Atomic write.

## Roles & boundaries

- The editor (LLM) authors **only**: the slide content fix (Step 5 step 3), the resolution wording (input to `close`), and the tag list (input to `mirror-row`).
- The skill writes **only**: `master.md` line edits driven by `--line N` + the appended rows in `feedback-backlog.md` (for `mirror-row`) and `# Open questions` (for `rescue-open`).
- The skill **never** invents verbatim feedback text, resolution wording, dates beyond "today", or tags.
- The skill **never** reads or writes `feedback-processed.md` or `learnings.md` (those are Step 7 — out of scope).
- All edits are atomic (`.tmp + os.replace`) so a crash mid-cycle leaves either the pre-edit or fully-edited file, never a partial.

## Exit codes

- `0` — success (including `noop` paths).
- `2` — malformed input (file missing, line out of range, bullet at the given line doesn't match the expected stamp state).
- `3` — `mirror-row` aborted because the `[closed]` line at N is not followed by a `Resolution:` line.
