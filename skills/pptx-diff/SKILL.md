---
name: talksmith:pptx-diff
description: Align a Talk's `final.md` against the `reconcile/finalpptx.md` reconstructed by `talksmith:pptx-extract` and explain the differences. Parses both files into slide trees, aligns slides by (section, slide#) with a normalized-title similarity fallback, then reports per-slide title changes, content edits (bullet/line granularity via difflib), speaker-notes edits, and image changes (added/removed/replaced/renamed by basename+hash). Emits a human-readable report and a machine `talks/<Talk>/reconcile/finalpptx.diff.json` consumed by `talksmith:pptx-merge`. Second stage of the reverse pipeline. CLI-safe, stdlib-only Python (no pptx parsing here); no Cowork dependency.
---

# talksmith:pptx-diff — Explain what changed in the deck

The middle stage of the reverse pipeline. Given the original deliverable `final.md` and the `finalpptx.md` reconstructed from the edited deck by [`talksmith:pptx-extract`](../pptx-extract/SKILL.md), this skill produces a precise, reviewable list of every text and image change so the presenter can decide what to reincorporate.

| The caller does | This skill does |
|---|---|
| Provides `final.md` + `finalpptx.md` (+ optional inventory) | Aligns slides, computes text/image deltas, writes the report + diff JSON |
| Reads the report and decides which changes to accept | Never edits any file; classification of accept/reject is the merge step's job |

## When to use

Run **after** `talksmith:pptx-extract` has produced `finalpptx.md`, and **before** `talksmith:pptx-merge`. Also useful standalone to answer "what did the presenter change in the deck?"

## Inputs

| Input | Required? | Notes |
|---|---|---|
| `--final` | yes | The Talk's original `final.md` (pre-edit deliverable). |
| `--pptx` | yes | The reconstructed `reconcile/finalpptx.md`. |
| `--talk` | optional | Talk root (default: parent dir of `--final`). Image refs on **both** sides resolve against this — needed because `finalpptx.md` lives under `reconcile/` while its refs are Talk-root-relative. |
| `--inventory` | optional | `reconcile/finalpptx.inventory.json` — enriches image classification. |
| `--human` / `--json` | optional | Report format on stdout. The `reconcile/finalpptx.diff.json` sidecar is always written. |

## Subcommand

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-diff/align_md.py \
  --final talks/<Talk>/final.md --pptx talks/<Talk>/reconcile/finalpptx.md \
  --talk talks/<Talk> [--inventory talks/<Talk>/reconcile/finalpptx.inventory.json] --human
```

### Alignment

Slides align by `(section_key, slide_num)` primary, with a normalized-title `SequenceMatcher ≥ 0.6` fallback (handles renumbering and lightly-edited titles), greedy best-ratio within the match set. Matches with ratio `0.6–0.75` are tagged `⚠ low-confidence` so the Editor double-checks before accepting.

### Per aligned slide

- **title** — exact normalized compare.
- **content** — bullet/line-granular diff via `difflib.SequenceMatcher` over prose-normalized units (cosmetic Markdown noise suppressed). Image-ref lines are excluded here — they are reported as image ops.
- **speaker notes** — same line-granular diff.
- **images** — compared by **slot** (ordinal within the slide), with byte-hash as a fast path. Per aligned slide:
  1. **Pass 1 (order-agnostic byte match):** any image whose `sha256` matches on both sides is `unchanged` — no change emitted. Handles trivial reordering of unmodified images.
  2. **Pass 1.5 (ASCII-backed silent absorb):** if an unpaired final image has an `images/<basename>.ascii` sidecar on disk, it's a Polish-generated ASCII diagram — the source of truth is the ASCII fence in `draft.md`, and Polish will regenerate the PNG from that ASCII on the next run. Any deck-side byte drift (Keynote recompressing on save) is disposable. Positional: the k-th ASCII-backed final image silently absorbs the k-th unpaired deck image — no change emitted, `images/<basename>.png` is never touched, and the merge planner isn't bothered with a spurious `[needs-editor]` "edit the ASCII, not the image" warning.
  3. **Pass 2 (slot-positional):** the remaining non-ASCII-backed images pair by ordinal within the slide (1↔1, 2↔2, …). Each pair emits `replaced` with `target_basename = <the final.md side's basename>` — that's the file in `images/` the merge will overwrite. **This is the case byte-hash and dim heuristics both miss:** if Keynote resized or re-encoded a hand-uploaded photo/diagram, its bytes and dimensions differ from `images/photo.png`, but it's still the same slot on the same slide → same conceptual image, modified.
  4. **Extras:** deck has more images than `final.md` → the leftovers are `added`; `final.md` has more → the leftovers are `removed`.

### Unaligned slides

- `slide_added` — present only in the deck; carries a full payload so merge can insert it.
- `slide_deleted` — present only in `final.md`; **suggested only, never auto-applied** (a slide missing from the deck may have been cut at render, and the draft is source of truth).

## Output

```
talks/<Talk>/reconcile/finalpptx.diff.json    # stable change ids, ops, confidence — consumed by pptx-merge
```

Each change has a stable `id` (e.g. `c001`) used by the merge step, a `kind` (title/content/notes/image/slide_added/slide_deleted), an `op`, and a `confidence`.

The `--human` report groups changes as `Section k › Slide m "Title"` with `+`/`-`/`~` prefixed lines, `⟳ image replaced`, and `⚠ low-confidence match` tags.

## Hand-off

Feed `finalpptx.diff.json` to [`talksmith:pptx-merge`](../pptx-merge/SKILL.md), which re-anchors each change to `draft.md`, auto-applies the simple ones, and surfaces the complex ones.

## Boundaries

- **Read-only.** Writes only `finalpptx.diff.json`.
- Exit 0 even when there are zero changes (that is a valid result). Exit 2 only when an input file is missing.
