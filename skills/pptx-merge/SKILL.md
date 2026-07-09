---
name: talksmith:pptx-merge
description: Apply a `finalpptx.diff.json` (from `talksmith:pptx-diff`) back into a Talk's `draft.md` — the editable source of truth — then re-run Step 6 Polish to re-derive `final.md`. Re-anchors each change structurally (by section + slide title + pre-change text, not by line number, since Polish rewrites lines). `apply-auto` lands the SIMPLE high-confidence changes automatically (bullet/notes edits, new-image insert+copy, diagram overwrite) and leaves the COMPLEX/CONFUSING ones for the Editor (low-confidence matches, removals, added/deleted slides, and image edits that trace back to a draft ASCII source). Every write is atomic and anchor-guarded (re-apply after drift fails loudly). Follows the `feedback-cycle` precedent: Python does the line surgery, the LLM authors wording. Third/final stage of the reverse pipeline. CLI-safe, stdlib-only Python (no pptx parsing here); no Cowork dependency.
---

# talksmith:pptx-merge — Reincorporate deck edits into draft.md

The final stage of the reverse pipeline. `draft.md` is the editable source of truth; `final.md` is derived and re-runnable. So changes made in the deck land in **`draft.md`**, and Step 6 (Polish) re-derives `final.md` — keeping the forward pipeline intact.

| The caller does | This skill does |
|---|---|
| Runs `plan`, then `apply-auto`; authors wording for the complex ops | Re-anchors each change to `draft.md`, applies the simple ones atomically, reports the rest |
| Re-runs Step 6 Polish after merging | Never writes `final.md` — only `draft.md` and `images/` |

Follows the [`talksmith:feedback-cycle`](../feedback-cycle/SKILL.md) precedent: **Python performs every byte-level edit; the LLM/Editor only authors content strings and accept/reject decisions.**

## When to use

Run **after** `talksmith:pptx-diff` has produced `finalpptx.diff.json`. After merging, tell the presenter to re-run Step 6 (Polish) so `final.md` (and any downstream `.pptx`) picks up the reincorporated changes.

## The re-anchoring problem

`final.md` is derived from `draft.md` (Polish strips `Presenter feedback`, rewrites ASCII fences to image refs, rescues `[open]` bullets), so a change found against `final.md`-space cannot be applied by line number. This skill re-anchors **structurally**: locate the draft slide by `(section, slide title)` (titles survive Polish unchanged), then the field by its `### ` heading, then the exact line by matching the change's pre-change text. A failed anchor routes to the Editor rather than guessing.

## The auto vs. Editor split

Per the operating decision — *apply the simple changes, ask on the complex or confusing ones*:

**`apply-auto` lands automatically** (simple, high-confidence, unambiguously anchored):
- content/notes **modified** → `replace-line` (anchor re-validated against the pre-change text)
- content/notes **added** → `append-line`
- **new image added** → `add-image` (copies the staged image out of `reconcile/staging/` into `images/` and inserts the `![alt](images/…)` ref into `### Content`; idempotent). **Chrome-guarded**: the image is inspected before the copy — if `max(w, h) ≤ 128` (icon-sized), `min(w, h) < 250` (thin decoration/banner), or `max/min > 4` (extreme aspect), the change is routed to `[needs-editor]` with a specific reason. Real content (photos, screenshots, diagrams ~1.5–2.8:1 aspect, both dims ≥ 250) auto-applies. This is the intelligence layer for content-vs-template-chrome — `pptx-extract` intentionally stays broad so single-occurrence decorations that its filters can't catch (survives icon/reused-chrome checks) still get flagged here rather than silently landing in `draft.md`.
- **image slot modified** (deck's slot-N image differs from `final.md`'s slot-N — Keynote resized/re-encoded/edited) → `replace-image` overwrites `images/<target_basename>` with the deck's bytes. The **target basename comes from the `final.md` side** so `draft.md` refs continue to resolve unchanged. Slot alignment (not byte or dim comparison) drives this.
- **title changed** → `retitle`

**Only actually-different bytes ever land in `images/`.** Byte-identical images are already flagged `unchanged` by `pptx-diff` and produce no work here — the deck-side staged copies stay in `reconcile/staging/` as a snapshot but never overwrite anything in `images/`.

**Routed to the Editor (`[needs-editor]`)** — complex or confusing:
- low-confidence alignments (title similarity `0.6–0.75`)
- content/notes **removals** (never auto-delete)
- `slide_added` / `slide_deleted` (structural)
- **ASCII-became-image**: a safety-net guard — if `pptx-diff` somehow emits an image `replaced` change whose target has an ASCII sidecar or the slide has a raw ASCII fence, refuse the copy with `edit the ASCII, not the image`. In practice `pptx-diff`'s Pass 1.5 silently absorbs these before they ever reach the merge, so this branch is only exercised on hand-crafted diffs.
- image `removed` / `renamed`

## Subcommands

### `plan` — classify every change, resolve draft anchors

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-merge/merge_draft.py plan \
  --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md [--format json|human]
```

Prints each change as `[appliable]` or `[needs-editor]` with the resolved op and reason. This is the accept/reject surface.

### `apply-auto` — apply every appliable change

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-merge/merge_draft.py apply-auto \
  --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md [--dry-run]
```

Re-plans against the *current* `draft.md` before each op (line numbers shift as edits land), applies the appliable ones, and reports the `[needs-editor]` remainder.

### Granular ops (for the Editor, after authoring wording)

`replace-line` · `append-line` · `remove-line` · `add-image` · `replace-image` · `retitle` — each takes explicit args, does one atomic edit, and re-validates its anchor (`--expect`) before writing. Use these to land the complex changes once the Editor has authored the exact content.

## Output

Edits `talks/<Talk>/draft.md` in place (atomic `.tmp` + `os.replace`). Copies accepted NEW/replaced images into `talks/<Talk>/images/`. **Never touches `final.md`.**

## Safety

- Every `apply` re-validates the anchor; on drift it exits `3` with `failed: line N no longer matches expected text — re-run plan` rather than corrupting `draft.md`.
- `add-image` is idempotent (skips if the ref already exists); re-running `apply-auto` after a successful merge applies nothing.

## Hand-off

After merging, the presenter re-runs **Step 6 (Polish)** (`cp draft.md final.md` + the Polish transforms) to re-derive `final.md`. The reverse pipeline is then closed: deck edits are back in the source of truth.

**Then, if the reconciled deck was rendered `strict` and an as-generated geometry baseline exists** (`output/final.generated.geometry.json`), auto-invoke [`talksmith:pptx-learn`](${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/SKILL.md) on the edited deck to mine recurring styling/distribution/positioning patterns from the human's corrections into `config/strict-learnings.md`. It **no-ops silently** for free-form/preview or when no baseline exists — never block or delay the merge on it.

## Boundaries

- **Writes only `draft.md` and `images/`.** Never `final.md`, never a `.pptx`.
- Returns one-line status reports; never prompts the user (the orchestrator/Editor drives accept/reject).
