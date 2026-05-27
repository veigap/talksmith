---
name: talksmith:feedback-cycle
description: Runs the full Step 5 (Review) feedback iteration on a Talk's `draft.md` — detect unstamped Presenter-feedback bullets, stamp each as `[open]`, close it with a resolution when the Editor applies the fix, mirror every `[closed]` to `feedback-backlog.md`, and sanity-check that the mirror is complete. Also exposes the `rescue-open` pass used by Step 6 (c) against `final.md`. CLI-safe, stdlib-only Python — the LLM Editor authors only the content fix, the resolution wording, and the tag list; every line edit on `draft.md` and every row appended to `feedback-backlog.md` goes through this skill.
---

# talksmith:feedback-cycle — Step 5 (Review) iteration helper

Owns the **mechanical bookkeeping** of the Step 5 feedback loop end-to-end:

1. **Detect** unstamped presenter bullets in `draft.md`.
2. **Stamp** each as `[open] YYYY-MM-DD — "<verbatim>"`.
3. **Close** each (after the Editor applies the content fix) as `[closed]` with a `Resolution:` continuation line.
4. **Mirror** every `[closed]` row to `config/feedback-backlog.md` for the cross-Talk audit trail.
5. **Sanity-check** that no `[closed]` bullet in `draft.md` is missing its mirror row.

Plus a sixth subcommand used at Step 6:

6. **Rescue** still-`[open]` bullets from `final.md` into the `# Open questions` section (so they survive the strip pass).

The LLM Editor calls these as CLI subcommands and **only authors three things per bullet**: the per-slide content fix, the one-sentence resolution, and the tag list. Every line edit on `draft.md` and every row appended to `feedback-backlog.md` goes through this skill — the Editor does not read `draft.md` end-to-end during a normal Review round.

## When to use

- **Every Step 5 (Review) round.** Start with `find-open` to get the precise bullet list, then `stamp` / *apply fix* / `close` / `mirror-row` per bullet, then `find-closed-unmirrored` as a sanity check.
- **Step 6 (c) Polish.** Run `rescue-open` once against `final.md` to copy any surviving `[open]` bullets into `# Open questions` before Step 6 (d) strips Presenter-feedback fields.
- **Spot-check** after applying feedback — re-run `find-open` to confirm nothing was missed.

## Subcommands

### `find-open` — detect unstamped bullets *(Step 5 entry)*

Scans `draft.md` for bullets inside `### Presenter feedback` blocks that don't yet carry `[open]` or `[closed]`. Returns line number, slide/section location, and verbatim text.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/find_open_notes.py <draft_path>
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/find_open_notes.py <draft_path> --format tsv
```

Output (human):
```
found 2 open note(s):

  line   523 | 2.8 Pan-Tompkins — la matemática (parte 2)
             | Let's add another slide about highpass(lowpass(x[n])).
```

Read-only — never modifies the file.

### `stamp` — mark a bullet `[open]`

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py stamp \
  --draft talks/<Talk>/draft.md --line N [--date YYYY-MM-DD]
```

Rewrites a single bullet (by line number) from `- "feedback"` to `- [open] YYYY-MM-DD — "feedback"`. Date defaults to today.

### `close` — flip `[open]` → `[closed]` with a resolution

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py close \
  --draft talks/<Talk>/draft.md --line N --resolution "<text>"
```

Flips the bullet to `[closed]` (keeping the original date) and inserts a `  Resolution: <text>` continuation line.

### `mirror-row` — append the closed bullet to `feedback-backlog.md`

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py mirror-row \
  --draft talks/<Talk>/draft.md --backlog config/feedback-backlog.md \
  --line N [--tags "tag1,tag2"]
```

Writes one fully-formed row to `feedback-backlog.md` with talk folder, date, location (nearest H1/H2 above the bullet), verbatim feedback, the resolution text, and the tag list. Location is auto-derived; tags are passed in.

### `find-closed-unmirrored` — sanity check at end of round

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py find-closed-unmirrored \
  --draft talks/<Talk>/draft.md --backlog config/feedback-backlog.md \
  [--format json|human]
```

Returns the list of `[closed]` bullets in `draft.md` that don't yet have a matching row in `feedback-backlog.md`. Empty list = the round is complete.

### `rescue-open` — *(Step 6 (c), against `final.md`)*

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py rescue-open \
  --final talks/<Talk>/final.md [--dry-run]
```

Walks `final.md`, finds every still-`[open]` bullet, and appends it to the `# Open questions` section (idempotent). Without this, the `[open]` bullets would be silently destroyed by Step 6 (d)'s `Presenter feedback` strip — they are **not** in `feedback-backlog.md`, which only mirrors `[closed]` entries.

This subcommand runs against `final.md`, not `draft.md` — the `--final` flag is deliberate so the call site is unambiguous.

## Inputs by subcommand

| Subcommand | Required | Optional |
|---|---|---|
| `find-open` *(separate script)* | `draft_path` | `--format human\|tsv` |
| `stamp` | `--draft`, `--line` | `--date` (default: today) |
| `close` | `--draft`, `--line`, `--resolution` | — |
| `mirror-row` | `--draft`, `--backlog`, `--line` | `--tags` |
| `find-closed-unmirrored` | `--draft`, `--backlog` | `--format json\|human` |
| `rescue-open` | `--final` | `--dry-run` |

## What this skill does NOT author

- **The content fix.** The Editor writes the per-slide content change (rephrase the bullet, swap slides, split a slide, etc.) directly in `draft.md` between `stamp` and `close`. This skill does not modify slide content.
- **The resolution wording.** Passed in via `--resolution` on `close`.
- **The tag list.** Passed in via `--tags` on `mirror-row`. The Editor picks tags by reusing existing ones in `feedback-backlog.md` before inventing new ones.

Everything else — line edits to `draft.md`, the `[open]`/`[closed]` format, the `Resolution:` continuation line, the `feedback-backlog.md` row format, location auto-derivation, idempotent `rescue-open` — is mechanical and lives here.

## Companion to other roles

- **Editor** ([`${CLAUDE_PLUGIN_ROOT}/agents/editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md) → *Step 5 — apply feedback*) is the sole caller for the Step-5 subcommands and the Step-6 (c) `rescue-open` pass.
- **Step 6 (d)** strips `Presenter feedback` fields from `final.md` *after* `rescue-open` has saved any `[open]` survivors — that ordering is enforced by Step 6's recipe in editor.md.
