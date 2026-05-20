---
name: talksmith:find-open-notes
description: Scan a Talk's master.md for unstamped Presenter feedback bullets — bullets inside `### Presenter feedback` blocks that have not yet received `[open]` or `[closed]` status tags. Returns line number, slide/section location, and verbatim text. CLI-safe, stdlib-only Python.
---

# talksmith:find-open-notes — Find unstamped feedback notes

Scans `master.md` and returns every bullet inside a `Presenter feedback` block
that the orchestrator has not yet stamped. Stamped bullets carry `[open]` or
`[closed]` prefixes; anything else is an open note waiting to be processed.

Use this skill at the start of any Step 5 (Review) pass, or whenever the
presenter says "process new note" / "process feedback" — it tells you exactly
which lines to act on without reading the whole file.

## When to use

- Presenter adds a bullet to `master.md` externally and asks you to process it.
- Starting a Step 5 round: run the skill first to get a precise list before
  performing the Editor role.
- Spot-check after applying feedback to confirm no bullets were missed.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| `master_path` | yes | Path to the Talk's `master.md`, e.g. `talks/senales-1d-biomedicina/master.md` |
| `--format` | optional | `human` (default, readable) or `tsv` (machine-readable, for piping) |

## Invocation

```bash
python3 .claude/skills/find-open-notes/find_open_notes.py <master_path>
python3 .claude/skills/find-open-notes/find_open_notes.py <master_path> --format tsv
```

## Output

**Human format (default):**
```
found 2 open note(s):

  line   523 | 2.8 Pan-Tompkins — la matemática (parte 2)
             | Let's add another slide about highpass(lowpass(x[n])).

  line  1042 | 4.1 ¿Qué es la PPG?
             | revisar la convención de polaridad del dip
```

**TSV format:**
```
line	location	text
523	2.8 Pan-Tompkins — la matemática (parte 2)	Let's add another slide...
1042	4.1 ¿Qué es la PPG?	revisar la convención de polaridad del dip
```

When no open notes exist:
```
no open notes found.
```

## What counts as "open"

A bullet is open when ALL of the following are true:
1. It appears inside a `### Presenter feedback` block (H3 heading or `**Presenter feedback:**` paragraph form).
2. It starts with `- ` (a Markdown list bullet).
3. It does NOT start with `- [open]` or `- [closed]`.

Continuation lines (`  Resolution: ...`) and blank lines are ignored.
Content inside fenced code blocks (` ``` `) is never scanned.

## Orchestrator workflow after running this skill

For each note returned:

1. **Stamp** the bullet in-place: `- [open] YYYY-MM-DD — "<verbatim text>"`
2. **Apply** the change the bullet implies to the surrounding slide/section (perform Editor role).
3. **Close**: flip to `- [closed] YYYY-MM-DD — "<verbatim>"` + `  Resolution: <what changed>`.
4. **Mirror** to `config/feedback-backlog.md`.

See `CLAUDE.md` → Step 5 for the full protocol.

## Boundaries

- Read-only: never modifies `master.md` or any other file.
- Scans a single file per invocation.
- Does not validate whether the stamped bullets were correctly applied — it only
  finds bullets that haven't been touched yet.
