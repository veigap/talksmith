---
name: talksmith:polish-images
description: Deterministic CLI helper for Step 6 (Polish), used by the image-illustrator role — scans a Talk's `final.md` for `<!-- generate-image: <side> | <description> -->` directives (with per-block slide context), and mechanically handles sidecar extraction, render-arg fan-out, idempotency stamping, and directive-to-aside cleanup. Sibling of talksmith:polish-ascii. CLI-safe, stdlib-only Python.
---

# talksmith:polish-images — Mechanical generate-image extraction + final.md rewrite

The **sibling of [`talksmith:polish-ascii`](../polish-ascii/SKILL.md)**: same shape, same Step-6 discipline, different block. Where `polish-ascii` extracts ` ```ascii ` fences for the diagram-illustrator, this skill extracts **`<!-- generate-image: … -->` directives** for the [`image-illustrator`](${CLAUDE_PLUGIN_ROOT}/agents/image-illustrator.md), and rewrites each into an `aside` image reference. The per-block **slide-context scanner is shared** — both skills `sys.path`-import [`skills/_shared/_context.py`](../_shared/_context.py), so a directive's `context` bundle (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, `presentation_language`) is computed by exactly the same code that feeds the diagram renders.

**Always operates on `final.md`.** Step 6 begins with the editor copying `draft.md` → `final.md`; every invocation of this skill targets `final.md`. `draft.md` is read-only from Step 6 onward.

## The directive

Authored by the editor into `draft.md` (see [`editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md)) on a **sparse-text slide** where an atmospheric image improves the slide:

```
<!-- generate-image: right | a cold, minimal sense of vast scale — a lone figure at dawn -->
```

- **`<side>`** — `left` or `right` (default `right` if omitted). Which edge the full-bleed aside column sits on.
- **`<description>`** — a **short, high-level** idea of what the image should convey. It stays concise and presenter-editable in `draft.md`; the image-illustrator **enriches** it into a full generation prompt at Step 6 (that enrichment is *not* stored in `draft.md`). The directive may span multiple lines up to the closing `-->`.

## Canonical Step 6 sequence

Mirrors polish-ascii; the image-illustrator role owns the judgement steps.

1. **`scan`** — read `final.md` once, emit JSON: every directive with 1-based inclusive line range, parsed `side` + `description`, the shared `context` bundle, and a `conflicting_image` flag (true when the directive's slide already carries a real `![](…)` image ref — a mis-authored aside per the existing *aside* rule). Pass `--language <lang>` to stamp `context.presentation_language`.
2. **Image-Illustrator composes the generation map** (judgement-only) — `{<slide_id>: {png_basename, alt, description, prompt}}`, where `description` is the editor's original line (verbatim) and `prompt` is the **enriched** generation instruction (expanded subject/mood/composition + the deck-palette / portrait-aspect / no-text overlay). See the agent spec.
3. **`annotate`** — `--plan <scan.json> --gen <gen.json> -o <annotated.json>` merges the map in, setting `render` per directive (`null` for unmapped / conflicting ones).
4. **`extract`** — write `talks/<Talk>/images/<basename>.imgprompt` sidecars: `side` + the **original description** + the **enriched prompt**, self-describing. `final.md` is **not** modified here.
5. **`prepare-render-args`** — one `<slide_id>.json` args file per renderable directive under `--out-dir`, carrying `prompt`, `prompt_file`, `output_path`, `aspect: portrait`, `side`, and the context bundle. Idempotency: a directive is **skipped** (no args written) when its PNG exists *and* its `<basename>.imgstamp` matches the digest of the current `description + side` — so an unchanged aside never regenerates.
6. **Generate** — the image-illustrator dispatches [`talksmith:generate-image`](../generate-image/SKILL.md) once per args file (tool-agnostic; degrades gracefully when no image capability is present).
7. **`stamp-renders`** *(mandatory — never skip)* — write each PNG's `<basename>.imgstamp` = `sha256(side + description)`. This is the **only** signal `prepare-render-args` consults next pass. Skip it and every pass regenerates forever.
8. **`cleanup`** — rewrite each `<!-- generate-image: … -->` directive in `final.md` into an aside ref + provenance echo:
   ```
   <!-- aside: <side> ![<alt>](images/<basename>.png) -->
   <!-- generate-source: <description> -->
   ```
   The render already owns the left/right full-bleed aside column, so the generated PNG at that path *just works*.

## Idempotency — why a companion `.imgstamp`, not an in-file stamp

`polish-ascii` stamps the SVG itself (`<!-- talksmith-ascii-sha256: … -->`) because an SVG is text. A generated image is **binary** and can't carry an inline comment, so the stamp lives in a sibling `talks/<Talk>/images/<basename>.imgstamp` file. It is independent of the `.imgprompt` sidecar (which `extract` overwrites every pass and therefore can't be the signal), and it is keyed on the **editor's original `description` + `side`** — never the enriched prompt, which is an LLM expansion that varies run to run. Editing the description in `draft.md` changes the digest and regenerates; a re-expansion alone does not. A missing/deleted stamp regenerates, which is the safe direction.

## Boundaries

- Reads `final.md`; `scan` is read-only, `cleanup` rewrites it atomically (`.tmp` + `os.replace`).
- Writes only under `talks/<Talk>/images/` (`.imgprompt` sidecars, `.imgstamp` stamps) and to `final.md`.
- Never reads or writes `draft.md`. Never generates images — that's [`talksmith:generate-image`](../generate-image/SKILL.md). Never authors the prompt — that's the image-illustrator.
- Does **not** touch ` ```ascii ` fences, existing `![](…)` refs, or authored `<!-- aside: … -->` hints — those belong to polish-ascii / the editor.

## Exit codes

- `0` — success.
- `2` — malformed input (missing file, plan JSON missing required fields, line numbers out of range; `prepare-render-args` when the plan's `final.md` is absent or a renderable directive's `.imgprompt` sidecar is missing — run `extract` first).
- `3` — `cleanup` aborted on a **stale plan**: a directive's recorded lines no longer open a `generate-image` comment, or the parsed `side`/`description` differ from the plan (an in-place edit preserves line count, so the content is checked). Nothing is written; re-run `scan`.
