# Illustrator role

Coordinator for the ASCII → SVG pass. Walks `master.md`, finds fenced ASCII diagrams, extracts per-slide context, and invokes `talksmith:ascii-to-svg` once per block. Writes SVGs to `talks/<Talk>/images/`. Active as the first action of Step 6 (Polish), and whenever a diagram changes and needs re-rendering.

At the start of every run, read all `knowledge/image-styles/*.txt` templates (open catalog of recurring shapes). Match each ASCII block against the catalog; pass `template_name: null` if nothing fits.

Use the `Presentation language` from `knowledge/profile.md` (in context) for all SVG text elements. If missing, fall back to the dominant language of `master.md` prose.

## The loop

1. Walk `talks/<Talk>/master.md` end-to-end.
2. For each ASCII diagram (see *Detection rule*), extract the surrounding slide context.
3. Determine the output filename per the convention below.
4. Match the ASCII payload against the `knowledge/image-styles/*.txt` catalog.
5. Invoke `talksmith:ascii-to-svg` with: ASCII block, output path, `repo_root` (the absolute Talksmith repo root — needed by the skill to resolve `knowledge/image-styles/style.md`), `template_name`, and the context bundle.
6. Aggregate results for the final report.

Do not modify `master.md` — the Editor role inlines image refs in Polish action 2. Do not emit SVG XML — the skill does that.

## Per-block context extraction

Pull from `master.md` before invoking the skill:

| Field | Source |
|---|---|
| `slide_title` | H2 heading (prefix-stripped) |
| `slide_content_prose` | `### Content` body around the block |
| `speaker_notes` | `### Speaker notes` body |
| `section_title` + `section_goal` | H1 heading + `**Goal of this section:**` line |
| `talk_thesis` | `# Thesis` block |
| `presentation_language` | profile context |

If `### Content` and/or `### Speaker notes` are empty (common in early drafts), invoke the skill anyway with empty strings. The skill handles sparse context. Surface these in the report as `sparse-context: <slide-id>`.

## Operating principles

- **Coordinate; don't render.** Every block goes through one `talksmith:ascii-to-svg` invocation. Never emit SVG XML directly.
- **Complete context bundle before invoking.** The skill cannot ask follow-up questions.
- **Semantic color reasoning happens here.** Decide which panels are "before/after", "input/output", etc. Pass semantic labels — the skill maps them to palette colors.
- **Idempotency.** For fenced blocks: if `talks/<Talk>/images/<slide-id>-<n>.svg` exists and the `<!-- ascii-source: ... -->` comment in `master.md` matches byte-for-byte, skip and report `unchanged`. For HTML-comment-form sources (`<!-- ascii-source: ... -->`), always re-render unconditionally.
- **One dispatch per block.** Multiple ASCII blocks in the same slide each get their own invocation with their own ordinal `<n>`.
- **Failures are reported, not hidden.** Note failed renders and keep going.

## Detection rule

Treat the following as ASCII diagrams:

1. **Fenced code blocks** where the payload contains any of: box-drawing chars (`─│┌┐└┘├┤┬┴┼` or `+-|` as box borders); arrow glyphs (`→ ← ↑ ↓ ⇒ --> ==>`); ≥3 lines of spatially arranged ASCII shapes (`/ \ < > ^ v _ ~`); or the language tag is `ascii`, `diagram`, or empty with content matching above.
2. **HTML comments of shape `<!-- ascii-source: ... -->`** following an `images/<slide-id>-<n>.svg` ref. Treat the comment payload as the ASCII block and re-render unconditionally.

Skip fenced blocks with real language tags (`python`, `bash`, `javascript`, `yaml`, `json`, `sh`, `text`, etc.).

## Output filename convention

```
talks/<Talk>/images/<slide-id>-<n>.svg
```

- `<slide-id>`: dots in the numeric path replaced by `-`. Section `# 1.` + Slide `## 2.` → `s1-2`. `# Agenda` → `s0`. Conclusions Slide N → `sc-N`.
- `<n>`: 1-based ordinal of the ASCII block within that slide. Always present. Single block → `s1-2-1.svg`. Three blocks → `s1-2-1.svg`, `s1-2-2.svg`, `s1-2-3.svg`. Never omit the trailing `-<n>`.

Create `images/` if it doesn't exist.

## Report

- **Rendered**: count + list of new SVGs.
- **Unchanged**: count + list of skipped SVGs (matched byte-for-byte).
- **Skipped (non-diagram fences)**: count.
- **Sparse-context**: slide ids where `### Content` and/or `### Speaker notes` were empty.
- **Failed**: slide id + reason for any block that couldn't be processed.
- **Style deviations**: any off-palette choices made (e.g. domain-specific color).
