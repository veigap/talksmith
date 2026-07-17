---
name: talksmith:polish-ascii
description: Deterministic CLI helper for Step 6 (Polish), used by the editor + diagram-illustrator roles — scans a Talk's `final.md` for fenced ASCII diagram blocks (with per-block slide context) and mechanically handles sidecar extraction, render-arg fan-out, idempotency stamping, and fence-to-image cleanup. The canonical subcommand sequence is in the skill body. CLI-safe, stdlib-only Python.
---

# talksmith:polish-ascii — Mechanical ASCII extraction + final.md rewrite

The diagram-illustrator picks templates and dispatches `talksmith:ascii-to-svg` per block; the editor owns the surrounding rewrite of `final.md` and the sidecar files. This skill is the editor's deterministic helper for that work — Python where Python belongs, no LLM reasoning needed.

**Always operates on `final.md`.** Step 6 begins with the editor copying `draft.md` → `final.md`; every subsequent Step-6 read/write — including every invocation of this skill — targets `final.md`. `draft.md` is read-only from Step 6 onward. The `--final <path>` flag (and the `final_path` positional for `scan`) is deliberately named so a `final draft.md` mix-up surfaces immediately as a mismatched argument rather than silently mutating the working file.

**Canonical Step 6 sequence** (matches the editor + diagram-illustrator role specs):

1. **`scan`** — read `final.md` once, emit JSON inventory of every ASCII block + trailing `ascii-note` with line ranges, **plus the per-block `context` bundle** (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, optional `presentation_language` when `--language` is passed). After `scan`, no consumer should need to re-parse `final.md` for slide context.
2. **`inspect-intents`** *(optional)* — eyeball the scan as a 3-column table (`slide_id | slide_title | intent`) before authoring slugs. Pure read; no mutation.
3. **Diagram-Illustrator authors a renders map** (judgement-only) — `{slide_id: {svg_basename, alt}}` JSON keyed by `slide_id`, with the slug per the *Output filename convention* in [`${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md) (derived from `ascii-note → intent`, slide title, etc.). Skip documentation-only blocks — `annotate-renders` zeros them out automatically.
4. **`annotate-renders`** — merge the renders map into the scan plan, emitting an annotated plan with `render: {svg_basename, alt}` set per block (and `render: null` for documentation-only / unmapped blocks). Reports missing slide_ids on stderr.
5. **`extract`** — write `.ascii` sidecars per the annotated plan. `final.md` is **not** modified at this stage. After this step every diagram lives on disk as a self-describing `.ascii` file (source + note).
6. **`prepare-render-args`** *(parallel fan-out)* — emit one `<slide_id>.json` args file per renderable block under `--out-dir`, each containing the full context bundle expected by `talksmith:ascii-to-svg` Mode B (`ascii_file`, `output_path`, slide/section/thesis context, `presentation_language`, optional `repo_root`). Subagents read their args file and dispatch one render each.
7. **Per-sidecar render** — invoke [`talksmith:ascii-to-svg`](../ascii-to-svg/SKILL.md) **once per `.ascii` file** in Mode B (`ascii_file: <path>`). The skill reads ASCII source + note from the sidecar; the caller passes the rest of the context bundle straight from the args file. Easily parallelizable across subagents.
8. **`stamp-renders`** *(mandatory — never skip)* — stamp each rendered SVG with the SHA-256 digest of the ASCII it was drawn from. This is what makes step 6 (`prepare-render-args`) able to skip unchanged blocks on the **next** pass: it is the one and only signal consulted, so an unstamped SVG re-renders every time, forever. Run once after **all** renders complete, before `cleanup`. Blocks whose render failed have no SVG on disk and are skipped + reported on stderr — they correctly re-render next pass.
9. **`cleanup`** — rewrite `final.md` fences to image references, leaving the post-fence `ascii-note` HTML comments in place. Sidecars are not touched.

A single-pass `apply` subcommand exists for quick passes (does steps 5 + 9 together, skipping the per-sidecar render — useful when you've already rendered SVGs separately and just want to finish the cleanup). **`apply` does not stamp** — if you use it after rendering SVGs by hand, run `stamp-renders` yourself or the next pass re-renders everything.

## When to use

- Step 6 (Polish), transformation (a) — replacing every fenced ASCII block in `final.md` with an image reference and producing the matching sidecar.
- Re-rendering a single diagram after the presenter edits an ASCII fence in `draft.md`: re-run Step 6 from action 0 (`cp draft.md final.md`), then `scan` reports the new line numbers; `apply` overwrites just that slide.

## Inputs

### `scan`

| Input | Required? | Notes |
|---|---|---|
| `final_path` | yes | Positional. Path to the Talk's `final.md`. |
| `--format` | optional | `json` (default) or `human` |
| `--language` | optional | Presentation language (e.g. `Spanish`). When provided, stamped into each block's `context.presentation_language` so the caller doesn't need to splice it in post-hoc. |

### `extract` / `cleanup` / `apply`

| Input | Required? | Notes |
|---|---|---|
| `--final` | yes | Path to the Talk's `final.md` (will be rewritten in place by `cleanup` / `apply`; left untouched by `extract`). |
| `--plan` | yes | Path to a JSON file: `scan` output **annotated** with `svg_basename` and `alt` per block (see schema below). Pass `-` to read from stdin. |
| `--dry-run` | optional | Print the planned rewrite to stdout instead of touching disk. |

The plan JSON has this shape:

```json
{
  "final_path": "/abs/path/to/talks/<Talk>/final.md",
  "blocks": [
    {
      "slide_id": "s1-2-1",
      "ascii": {"start_line": 84, "end_line": 101, "payload": "<verbatim>"},
      "note": {"start_line": 102, "end_line": 106, "payload": "<!-- ascii-note: ... -->"},
      "context": {
        "slide_title": "Cuatro señales 1D",
        "slide_content_prose": "Audio, ECG, accelerometer, EEG ...",
        "speaker_notes": "Pause for ~10 seconds before clicking ...",
        "section_title": "Foundations",
        "section_goal": "Establish the vocabulary the audience needs ...",
        "talk_thesis": "**Claim:** Signals are interesting. **Why it matters:** ...",
        "presentation_language": "Spanish"
      },
      "render": {
        "svg_basename": "s1-2-1-cuatro-senales.svg",
        "alt": "Cuatro señales 1D"
      }
    }
  ]
}
```

`context` is emitted by `scan` automatically — derived mechanically from `final.md`'s structure (nearest H2 above the block = `slide_title`; nearest H1 above = `section_title`; `**Goal of this section:**` line under the H1 = `section_goal`; `### Content` and `### Speaker notes` bodies inside the slide; `# Thesis` block at top of file). Fenced code blocks, HTML comments, and `---` horizontal rules are stripped from prose. `presentation_language` is present only when the caller passes `--language`.

`render` is added by the diagram-illustrator (judgement: template choice, slug, alt) before `extract` / `cleanup` / `apply` is invoked.

A block with `"render": null` is skipped (not rewritten, no sidecar).

A block with `"documentation_only": true` is **also skipped automatically** — the slide already carries a Markdown image reference, so any ASCII in that slide is treated as inline visual aid for the source reader and bypassed by every Step-6 stage (no render, no sidecar, no fence rewrite). The flag is set by `scan` based on the surrounding slide content; the diagram-illustrator does not need to annotate it.

`start_line` / `end_line` are **1-based**, **inclusive**, and refer to the opening and closing fence lines respectively (the fences themselves, not just the payload). For notes, they refer to the `<!-- ascii-note:` line and the line containing the terminal `-->`.

## Invocation

```bash
# Phase 1 — scan
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    scan talks/<Talk>/final.md --language Spanish > /tmp/plan.json

# Phase 2 — eyeball (optional) and author a renders map
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py inspect-intents --plan /tmp/plan.json
#   diagram-illustrator writes /tmp/renders.json:
#     {"s1-2-1": {"svg_basename": "s1-2-1-cuatro-senales.svg", "alt": "Cuatro señales"}, ...}

# Phase 3 — annotate the plan, write sidecars, fan args out for parallel rendering
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    annotate-renders --plan /tmp/plan.json --renders /tmp/renders.json -o /tmp/plan.annotated.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    extract --final talks/<Talk>/final.md --plan /tmp/plan.annotated.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    prepare-render-args --plan /tmp/plan.annotated.json \
        --out-dir /tmp/ts-args --repo-root "$(pwd)"

# Phase 4 — parallel renders (one Agent per /tmp/ts-args/<slide_id>.json)

# Phase 5 — stamp the renders (MANDATORY: this is what lets the *next* pass skip
#           unchanged blocks; skip it and every pass re-renders everything, forever)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    stamp-renders --final talks/<Talk>/final.md --plan /tmp/plan.annotated.json

# Phase 6 — cleanup
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py \
    cleanup --final talks/<Talk>/final.md --plan /tmp/plan.annotated.json
```

`apply` is a single-shot wrapper around `extract` + `cleanup` for re-running Polish after every SVG already exists on disk; it does **not** stamp, so pair it with `stamp-renders` when you've rendered by hand. Read-only subcommands (`scan`, `inspect-intents`, `annotate-renders`, `prepare-render-args`) and `extract`/`stamp-renders` are idempotent; a second `cleanup`/`apply` with the same plan exits 3 by design (the fences are gone — re-run `scan` for a fresh plan).

## Output

### `scan` — JSON (default)

Exactly the plan shape shown under *Inputs* above, with `render: null` on every block (the diagram-illustrator's `annotate-renders` fills it later).

### `scan` — human

```
found 22 ASCII block(s) in talks/senales-1d-biomedicina/final.md:

  s1-2-1   lines 84–101 (18 ASCII lines)   note: yes (lines 102–106)
  s1-3-1   lines 147–151 (5 ASCII lines)   note: yes (lines 152–155)
  …
```

### `apply` — summary

```
applied 22 block(s) to talks/senales-1d-biomedicina/final.md:
  sidecars: 21 written, 1 unchanged
  fences:   22 rewritten
```

## Detection rules (used by `scan`)

- **ASCII block** — two tiers, same rules as [diagram-illustrator.md](${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md) → *Detection rule*: the canonical ` ```ascii ` fence (`detection_mode: "canonical"`, no glyph inspection) or the legacy glyph heuristic on empty/`text`/`diagram`-tagged fences (`detection_mode: "legacy-heuristic"`, migration warning per block in `human` output). Real-language fences (`python`, `bash`, …) are ignored under both tiers.
- **Note** = an HTML comment of shape `<!-- ascii-note: ... -->` whose opening `<!-- ascii-note:` line appears **within 1 blank-line tolerance** after the closing fence. The comment is captured verbatim from its opening sentinel through the line containing `-->`.
- **`slide_id`** = `s<section-N>-<slide-M>-<n>`. Section is the most recent `# N.` H1; slide is the most recent `## M.` H2 inside that section; `n` is the 1-based ordinal of the ASCII block within the current slide. Special locators: `# Agenda` → section `0`; `# Conclusiones` / `# Conclusions` → section `c`.
- **`documentation_only`** = `true` when the ASCII block's containing slide (lines from the most recent H1/H2 to the next H1/H2) carries a Markdown image reference (`![alt](path)`) outside the ASCII fence itself and outside any `<!-- ascii-source: ... -->` HTML comment left by an earlier Polish pass. These blocks exist purely as inline visual aid for whoever reads the source and are skipped by `extract`/`cleanup`/`apply`.

## Rewrite rules (used by `apply` / `cleanup`)

For each block with `render` non-null:

**`svg_basename` is accepted with or without the `.svg` extension.** The canonical form (per the diagram-illustrator's filename convention in [`${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md)) includes `.svg` — e.g. `s1-2-1-cuatro-senales.svg`. If a stem-only form is passed (`s1-2-1-cuatro-senales`), both `extract` and `cleanup` normalize it: the sidecar lands at `<stem>.ascii` and the `final.md` image reference resolves to `images/<stem>.svg`. Mismatched leniency between the two subcommands was a real bug — an extension-less annotation used to land a correct sidecar but a 404-ing image reference. Both paths are now symmetric.

1. **Sidecar.** Write `talks/<Talk>/images/<stem>.ascii` where `<stem>` is `svg_basename` minus `.svg`. Content layout:
   - ASCII payload verbatim (no fence, no leading/trailing blank-line manipulation).
   - If `note.payload` exists: one blank line, then the captured note verbatim through `-->`.
   - Trailing `\n` to keep POSIX-friendly.
   - Idempotency: skip the write if existing bytes match exactly.
2. **`final.md` rewrite.** Replace lines `ascii.start_line` … `ascii.end_line` (inclusive) in `final.md` with:
   ```
   ![<alt>](images/<svg_basename>)
   <!-- ascii-source:
   <ascii.payload>
   -->
   ```
   Any `-->` inside `<ascii.payload>` (e.g. `A --> B` arrows) is escaped to `--&gt;` in the echo, so it can't close the `<!-- ascii-source: … -->` comment early and leak the rest of the diagram into the visible body. The `.ascii` sidecar keeps the exact, un-escaped source; this echo is provenance only.

   Do **not** modify the note region (lines `note.start_line` … `note.end_line`). It stays where it was, directly after the new image reference + `ascii-source` echo.

Blocks are processed bottom-up so line numbers stay valid through the pass. The skill writes `final.md` atomically (write to `.tmp`, then `os.replace`). `draft.md` is **never** touched.

## Boundaries

- Reads `final.md`; in `scan` it is read-only; in `apply` / `cleanup` it is rewritten atomically.
- Writes only under `talks/<Talk>/images/` (sidecars) and to `final.md` itself.
- Never reads or writes `draft.md`.
- Does **not** render SVGs — that's `talksmith:ascii-to-svg`.
- Does **not** assign `svg_basename` — the diagram-illustrator does (filename convention spec in `${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md`).
- Does **not** strip `Presenter feedback` (Step 6 (d)) or consolidate non-ASCII image refs (Step 6 (b)) — those remain editor responsibilities.

## Exit codes

- `0` — success.
- `2` — malformed input (missing file, plan JSON missing required fields, line numbers out of range). Also `prepare-render-args` when the plan's `final.md` is absent (stale plan / different session mount) or a renderable block's `.ascii` sidecar is missing (run `extract` first) — it validates both up front and writes **no** args on failure, rather than silently emitting args that point at nothing.
- `3` — `cleanup` / `apply` aborted on a **stale plan**: `final.md` changed since `scan` — a block's recorded lines no longer bracket an ASCII fence, **or the payload between them differs from the plan** (an in-place edit preserves line count, so the payload is checked byte-for-byte). Nothing is written — `apply` validates the whole plan before writing any sidecar. Re-run `scan` and redo the annotate/extract/cleanup pass.
