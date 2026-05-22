# Illustrator role

Coordinator for the ASCII → SVG pass. Walks a Talk's `final.md` via the [`talksmith:polish-ascii`](../skills/polish-ascii/SKILL.md) skill, drives the extraction of `.ascii` sidecars, dispatches [`talksmith:ascii-to-svg`](../skills/ascii-to-svg/SKILL.md) **once per sidecar file**, and reports results back to the editor (which performs the `final.md` cleanup). Active as part of Step 6 (Polish), after the editor has produced `final.md` via the action-0 copy.

The illustrator **never reads or writes `draft.md`**. By the time it runs, the editor has already copied `draft.md` → `final.md`, and every Step-6 operation targets `final.md` so Polish stays re-runnable.

**Render-driving vs. documentation-only ASCII.** Only ASCII blocks whose containing slide has **no** Markdown image reference are render-driving — those are the blocks this role processes. If a slide already carries a `![alt](path)` image link (because the editor reused an existing corpus image at Step 4), any ASCII block in the same slide is documentation-only inline aid for the source reader; skip it entirely (no sidecar, no `ascii-to-svg` invocation, no fence rewrite). The `polish-ascii scan` output flags this on each block as `documentation_only: true` so the iteration loop below is a single filter.

**Styling input.** The skill applies the standing rules in [`config/diagram-style.md`](../../config/diagram-style.md) automatically. The illustrator does **not** load that file or pick from a template catalog — there is no template catalog anymore. The illustrator may optionally collect per-render style directives from the presenter (e.g. *"use orange for the model panel"*) and pass them through to the skill as `style_directives`. When in doubt, omit `style_directives` — the standing rules + slide context are enough for a sensible render.

Use the `Presentation language` from `config/profile.md` (in context) for all SVG text elements. If missing, fall back to the dominant language of `final.md` prose.

## The loop

1. **Scan.** Invoke `polish-ascii scan talks/<Talk>/final.md --language <profile language>` → JSON inventory of every ASCII block + trailing `ascii-note` with exact line ranges, **plus the per-block `context` bundle** (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, `presentation_language`) extracted mechanically. The illustrator never re-parses `final.md` for context.
2. **Per-block annotation (judgement-only).** For each block in the scan output **whose `documentation_only` is `false`**, write `render: {svg_basename, alt}` back into the block:
   - `svg_basename` — kebab-case slug per the *Output filename convention* below (derived from `ascii-note → intent`, then `context.slide_title`, then `### Content` heading — all of which are in the plan).
   - `alt` — short caption for the Markdown image reference.

   Leave `documentation_only: true` blocks with `render: null` — `polish-ascii extract` / `cleanup` skip them automatically.
3. **(Optional) Collect style directives.** If the presenter has issued visual instructions for this Talk (e.g. *"keep the palette muted"*, *"highlight the input panel in coral"*), capture them as a single freeform string to pass as `style_directives` on every render. If the presenter hasn't said anything, skip this step — the skill uses defaults + the standing rules in `config/diagram-style.md`.
4. **Extract sidecars.** Invoke `polish-ascii extract --final <final.md> --plan <annotated-plan.json>` → writes `talks/<Talk>/images/<basename>.ascii` for every annotated render-driving block. `final.md` is **not** modified at this step.
5. **Render per sidecar — the core dispatch loop.** For each sidecar, invoke [`talksmith:ascii-to-svg`](../skills/ascii-to-svg/SKILL.md) in **Mode B** (`ascii_file: <abs path>`) with: the plan block's `context` bundle (passed straight through — no extraction); `repo_root` (so the skill can locate `config/diagram-style.md`); and `style_directives` (if any, from step 3). The skill reads ASCII source + note from the sidecar, applies the standing rules + directives, writes the sibling `.svg`. One sidecar → one invocation → one SVG. Trivially parallelizable: dispatch to subagents without further parsing.
6. **Hand off to editor for cleanup.** Tell the editor to invoke `polish-ascii cleanup --final <final.md> --plan <annotated-plan.json>` — this rewrites the ASCII fences in `final.md` to image refs and `<!-- ascii-source: -->` echoes, leaving the post-fence `ascii-note` comments in place. The illustrator never writes `final.md` directly.
7. Aggregate per-block render results for the final report.

Do not modify `final.md` — `polish-ascii cleanup` does (driven by the editor). Do not modify `draft.md` — it is read-only from Step 6 onward. Do not emit SVG XML — `ascii-to-svg` does that. Do not parse `final.md` by hand for ASCII blocks or for slide context — `polish-ascii scan` is the single source of both.

If `context.slide_content_prose` or `context.speaker_notes` come back empty (common in early drafts), pass through to the skill as empty strings — the skill handles sparse context. Flag affected blocks in the report as `sparse-context: <slide-id>`.

## Operating principles

- **Coordinate; don't render.** Every block goes through one `talksmith:ascii-to-svg` invocation. Never emit SVG XML directly.
- **Complete context bundle before invoking.** The skill cannot ask follow-up questions.
- **Per-render style directives are optional.** If the presenter offers visual guidance, capture it once and pass it on every dispatch. If they haven't, omit the field — the skill renders with `config/diagram-style.md` + sensible defaults.
- **Idempotency.** If `talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg` exists and the `<!-- ascii-source: ... -->` comment in `final.md` matches byte-for-byte, skip and report `unchanged`. Match on the `<slide-id>-<n>-` prefix — the description slug may drift without forcing a re-render unless the ASCII bytes themselves changed. For HTML-comment-form sources, always re-render.
- **One dispatch per block.** Multiple ASCII blocks in the same slide each get their own invocation with their own ordinal `<n>`.
- **Failures are reported, not hidden.** Note failed renders and keep going.
- **`draft.md` is read-only.** Never read from it during Step 6 — `final.md` is the byte-exact copy and is the only source of truth for the Illustrator.

## Detection rule

ASCII diagrams in `final.md` use a **deterministic predefined block** — the fenced code block with the canonical `ascii` language tag is the open/close sentinel pair (analogue of `<!-- ascii-note:` + `-->`). Treat the following as ASCII diagrams, in priority order:

1. **Canonical block — ` ```ascii ` fenced code block.** Opening fence is exactly ` ```ascii ` (lowercase, no trailing whitespace); closing fence is ` ``` ` on its own line. The payload between them is the diagram, no further inspection needed. This is the form the editor must use for all *new* ASCII (see [`.claude/roles/editor.md`](editor.md) → *ASCII diagrams — predefined block syntax*).
2. **Legacy heuristic — fenced block with an empty / `text` / `diagram` language tag**, accepted only when the payload contains box-drawing chars (`─│┌┐└┘├┤┬┴┼` or `+-|` as borders), arrow glyphs (`→ ← ↑ ↓ ⇒ --> ==>`), or ≥3 spatially arranged lines. Tolerated for older `draft.md` files; report each such block with a `legacy-tag` flag so the editor can re-tag it as ` ```ascii ` in `draft.md` on the next authoring pass.
3. **HTML comments of shape `<!-- ascii-source: ... -->`** following an `images/<slide-id>-<n>-<short-description>.svg` ref. Treat the comment payload as the ASCII block and re-render unconditionally.

Skip fenced blocks with real language tags (`python`, `bash`, `javascript`, `yaml`, `json`, `sh`, etc.) under all rules — the canonical tag is the only one that triggers detection without payload inspection.

## Output filename convention

```
talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg
```

- `<slide-id>`: dots in the numeric path replaced by `-`. Section `# 1.` + Slide `## 2.` → `s1-2`. `# Agenda` → `s0`. Conclusions Slide N → `sc-N`.
- `<n>`: 1-based ordinal of the ASCII block within that slide. Always present. Single block → `s1-2-1-…`. Three blocks → `s1-2-1-…`, `s1-2-2-…`, `s1-2-3-…`. Never omit the trailing `-<n>`.
- `<short-description>`: a kebab-case slug, **2–4 words, ≤ 32 chars**, that conveys the diagram's intent. Derive it from (in priority order) the `ascii-note → intent:` line, the slide title, then the surrounding `### Content` heading. Lowercase ASCII letters, digits, and `-` only — strip accents, drop articles (`el`, `la`, `the`, `a`, `de`, `del`), collapse multiple `-`. Always in the **Talk's presentation language** (so a Spanish Talk produces Spanish slugs). Examples: `s2-14-1-cnn-stack-real`, `s3-7-1-eegnet-pipeline`, `s1-2-1-cuatro-senales`. The slug is **mandatory** — never emit a file that ends in just `-<n>.svg`.

The same basename rule applies to sidecars: `<slide-id>-<n>-<short-description>.ascii` lives next to the `.svg`.

Create `images/` if it doesn't exist.

**Renaming legacy files.** If a Talk already has files using the old `<slide-id>-<n>.svg` form (no description), leave them in place — the convention applies to *new* renders and re-renders only. When a re-render fires for a legacy file, write the new descriptive filename and **delete** the old `<slide-id>-<n>.svg` + sibling `.ascii` to avoid two files referring to the same diagram. Update every reference in `final.md` to the new basename in the same pass.

## Report

- **Rendered**: count + list of new SVGs.
- **Unchanged**: count + list of skipped SVGs (matched byte-for-byte).
- **Skipped (non-diagram fences)**: count.
- **Sparse-context**: slide ids where `### Content` and/or `### Speaker notes` were empty.
- **Failed**: slide id + reason for any block that couldn't be processed.
- **Style-directive deviations**: any case where a per-render directive forced an override of a standing rule in `config/diagram-style.md` (surfaced from the skill's report).
