---
name: talksmith:polish-ascii
description: Step 6 (Polish) helper for the editor role. Three primary subcommands plus a convenience wrapper. `scan` walks a Talk's `master.md` and emits structured JSON listing every fenced ASCII diagram block plus any `<!-- ascii-note: ... -->` HTML comment that follows it, with exact line ranges for both. `extract` takes that JSON (annotated by the illustrator with the rendered SVG basename per slide_id) and writes `talks/<Talk>/images/<basename>.ascii` sidecar files containing ASCII source + captured note in the spec'd layout, without touching `master.md`. `cleanup` takes the same annotated JSON and rewrites the matching ASCII fences in `master.md` to image references with `<!-- ascii-source: -->` echoes, leaving the post-fence `ascii-note` comments untouched, without touching sidecars. `apply` is a convenience wrapper that runs `extract` + `cleanup` in one pass (legacy / quick passes). CLI-safe, stdlib-only Python. Skip `reuse:`-tagged blocks in all write modes (no sidecar, no fence rewrite).
---

# talksmith:polish-ascii — Mechanical ASCII extraction + master.md rewrite

The illustrator picks templates and dispatches `talksmith:ascii-to-svg` per block; the editor owns the surrounding rewrite of `master.md` and the sidecar files. This skill is the editor's deterministic helper for that work — Python where Python belongs, no LLM reasoning needed.

**Canonical Step 6 sequence** (matches the editor + illustrator role specs):

1. **`scan`** — read `master.md`, emit JSON inventory of every ASCII block + trailing `ascii-note` with line ranges.
2. **Illustrator slug pass** — illustrator annotates each block in the plan with `render.svg_basename` (kebab-case slug from `ascii-note → intent`, slide title, etc. — see [`.claude/roles/illustrator.md`](../../roles/illustrator.md)) and `render.alt`.
3. **`extract`** — write `.ascii` sidecars per the annotated plan. `master.md` is **not** modified at this stage. After this step every diagram lives on disk as a self-describing `.ascii` file (source + note).
4. **Per-sidecar render** — illustrator iterates the sidecars and invokes [`talksmith:ascii-to-svg`](../ascii-to-svg/SKILL.md) **once per `.ascii` file** in Mode B (`ascii_file: <path>`). Each invocation reads the sidecar, splits source from note, and writes the sibling `.svg`. The sidecar is the renderer's authoritative input.
5. **`cleanup`** — rewrite `master.md` fences to image references, leaving the post-fence `ascii-note` HTML comments in place. Sidecars are not touched.

A single-pass `apply` subcommand exists for quick passes (does steps 3 + 5 together, skipping the per-sidecar render in step 4 — useful when you've already rendered SVGs separately and just want to finish the cleanup).

## When to use

- Step 6 (Polish), transformation (a) — replacing every fenced ASCII block with an image reference and producing the matching sidecar.
- Re-rendering a single diagram after the presenter edits an ASCII fence in `master.md` — `scan` reports the new line numbers; `apply` overwrites just that slide.

## Inputs

### `scan`

| Input | Required? | Notes |
|---|---|---|
| `master_path` | yes | Path to the Talk's `master.md` |
| `--format` | optional | `json` (default) or `human` |

### `apply`

| Input | Required? | Notes |
|---|---|---|
| `--master` | yes | Path to the Talk's `master.md` (will be rewritten in place) |
| `--plan` | yes | Path to a JSON file: `scan` output **annotated** with `svg_basename` and `alt` per block (see schema below). Pass `-` to read from stdin. |
| `--dry-run` | optional | Print the planned rewrite to stdout instead of touching disk. |

The plan JSON has this shape:

```json
{
  "master_path": "talks/<Talk>/master.md",
  "blocks": [
    {
      "slide_id": "s1-2-1",
      "ascii": {"start_line": 84, "end_line": 101, "payload": "<verbatim>"},
      "note": {"start_line": 102, "end_line": 106, "payload": "<!-- ascii-note: ... -->"},
      "render": {
        "svg_basename": "s1-2-1-cuatro-senales.svg",
        "alt": "Cuatro señales 1D"
      }
    }
  ]
}
```

A block with `"render": null` is skipped (not rewritten, no sidecar). A block whose captured `note.payload` contains a `reuse:` line is **also skipped automatically** — the skill never overwrites a reused asset's record.

`start_line` / `end_line` are **1-based**, **inclusive**, and refer to the opening and closing fence lines respectively (the fences themselves, not just the payload). For notes, they refer to the `<!-- ascii-note:` line and the line containing the terminal `-->`.

## Invocation

```bash
# Phase 1 — capture
python3 .claude/skills/polish-ascii/polish_ascii.py scan talks/<Talk>/master.md > /tmp/plan.json

# (illustrator picks templates, dispatches renders, annotates /tmp/plan.json with render fields)

# Phase 2 — write sidecars + rewrite master.md
python3 .claude/skills/polish-ascii/polish_ascii.py apply --master talks/<Talk>/master.md --plan /tmp/plan.json
```

`apply` is idempotent: re-running with the same plan produces no diff if sidecars and fence rewrites already match.

## Output

### `scan` — JSON (default)

```json
{
  "master_path": "talks/senales-1d-biomedicina/master.md",
  "blocks": [
    {
      "slide_id": "s1-2-1",
      "ascii": {"start_line": 84, "end_line": 101, "payload": "[gray]  Audio …"},
      "note": {"start_line": 102, "end_line": 106, "payload": "<!-- ascii-note:\nintent: …\n-->"},
      "render": null
    }
  ]
}
```

### `scan` — human

```
found 22 ASCII block(s) in talks/senales-1d-biomedicina/master.md:

  s1-2-1   lines 84–101 (18 ASCII lines)   note: yes (lines 102–106)
  s1-3-1   lines 147–151 (5 ASCII lines)   note: yes (lines 152–155)
  …
```

### `apply` — summary

```
applied 22 block(s) to talks/senales-1d-biomedicina/master.md:
  sidecars: 21 written, 1 unchanged, 1 skipped (reuse:)
  fences:   22 rewritten
```

## Detection rules (used by `scan`)

- **ASCII block** = a fenced code block whose language tag is empty, `ascii`, `text`, or `diagram`, AND whose payload either contains box / arrow glyphs (`─│┌┐└┘├┤┬┴┼+|→←↑↓` or `->`, `==>`, `─`, `│`) or spans ≥3 lines with spatially arranged characters. Fences tagged `python`, `bash`, etc. are ignored.
- **Note** = an HTML comment of shape `<!-- ascii-note: ... -->` whose opening `<!-- ascii-note:` line appears **within 1 blank-line tolerance** after the closing fence. The comment is captured verbatim from its opening sentinel through the line containing `-->`.
- **`slide_id`** = `s<section-N>-<slide-M>-<n>`. Section is the most recent `# N.` H1; slide is the most recent `## M.` H2 inside that section; `n` is the 1-based ordinal of the ASCII block within the current slide. Special locators: `# Agenda` → section `0`; `# Conclusiones` / `# Conclusions` → section `c`.

## Rewrite rules (used by `apply`)

For each block with `render` non-null and no `reuse:` in the captured note:

1. **Sidecar.** Write `talks/<Talk>/images/<stem>.ascii` where `<stem>` is `svg_basename` minus `.svg`. Content layout:
   - ASCII payload verbatim (no fence, no leading/trailing blank-line manipulation).
   - If `note.payload` exists: one blank line, then the captured note verbatim through `-->`.
   - Trailing `\n` to keep POSIX-friendly.
   - Idempotency: skip the write if existing bytes match exactly.
2. **Master rewrite.** Replace lines `ascii.start_line` … `ascii.end_line` (inclusive) in `master.md` with:
   ```
   ![<alt>](images/<svg_basename>)
   <!-- ascii-source:
   <ascii.payload>
   -->
   ```
   Do **not** modify the note region (lines `note.start_line` … `note.end_line`). It stays where it was, directly after the new image reference + `ascii-source` echo.

Blocks are processed bottom-up so line numbers stay valid through the pass. The skill writes `master.md` atomically (write to `.tmp`, then `os.replace`).

## Boundaries

- Reads `master.md`; in `scan` it is read-only; in `apply` it is rewritten atomically.
- Writes only under `talks/<Talk>/images/`.
- Does **not** render SVGs — that's `talksmith:ascii-to-svg`.
- Does **not** assign `svg_basename` — the illustrator does (filename convention spec in `.claude/roles/illustrator.md`).
- Does **not** strip `Presenter feedback` (Step 6 (d)) or consolidate non-ASCII image refs (Step 6 (b)) — those remain editor responsibilities.

## Exit codes

- `0` — success.
- `2` — malformed input (missing file, plan JSON missing required fields, line numbers out of range).
- `3` — `apply` aborted because `master.md` mtime drifted between the plan's capture and the apply (stale plan — re-`scan`).
