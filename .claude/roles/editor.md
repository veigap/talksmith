# Editor role

Maintains `master.md` and `memory.md` for the active Talk. `master.md` is the deliverable; `memory.md` is the progress log. Active during Steps 1, 4, 5, 6, and 7.

`knowledge/profile.md` is in context — use it. Apply `Presentation language` to all prose written into `master.md`.

**Canonical slide locator** (used in composer punch-lists and presenter feedback): `<section-N>.<slide-M>` — e.g. `2.1` = Section 2 → Slide 1. Special tokens: `thesis`, `agenda`, `agenda.section:<N>` (n-th section bullet), `agenda.<n>` (n-th agenda ASCII block), `conclusions.N`, `conclusions.N.<k>` (k-th ASCII in conclusions slide N). Parse this notation before applying any change. If the target doesn't exist, report `target not found: <expected location>` — never apply to a best-guess neighbor.

**Pending-stub awareness.** When a slide's `### Sources` cites a `knowledge/compile/` file that contains `<!-- pending: ... -->` markers, keep the citation and add a note to `Open questions`: `Slide <section>.<slide> cites pending stub compile/<file>.md — re-verify after librarian Phase 2`.

## Steps

**Step 1 — bootstrap `memory.md`.** Copy the canonical empty form from `.claude/schemas/memory.md`. Write the verbatim `## Talk briefing` text. Open the Step 1 entry with `Status: in_progress`, empty `Asks log:`, unfilled closure fields. Set `**Current step:** 1 — Frame in_progress`. Never touch `## Talk briefing` again.

**Step-closure (any step 1–8).** Fill the step entry's `What was decided`, `Key inputs`, `Files created/modified`, `Pending open questions`. Flip `Status: complete` and update `**Current step:**` at top of file. Do not touch `Asks log:` or any prior step's entry.

The orchestrator owns live-state lines (`**Awaiting:**`, `Status: in_progress|awaiting_presenter`, `Asks log:` rows). Do not write those.

**Step 4 — draft `master.md`.** If `master.md` is missing or empty, bootstrap it from `.claude/schemas/master.md` → `## Canonical empty form`: extract the fenced markdown block, strip all HTML comments and YAML-comment lines, keep headings, frontmatter keys, and field labels. Then:
- Fill frontmatter (presenter, audience, duration, date).
- Write the one-sentence `Thesis` (Claim + Why it matters).
- Add/edit/reorder Sections in `Agenda` (each with a "Goal of this section" line).
- Add/edit/reorder Slides within Sections (each with `Content`, `Sources`, `Speaker notes`).
- Move dropped content to `Cut material`. Log unresolved items in `Open questions`.

**ASCII diagrams — predefined block syntax + render-time hints.** Every ASCII diagram the editor writes into `master.md` **must** use the explicit `ascii` language tag on its opening fence. This is what makes diagram detection deterministic (no glyph-heuristic guessing) — exactly the same role `<!-- ascii-note: ... -->` plays for the note half. The full block convention:

```markdown
\`\`\`ascii
+-------+    +-------+
| input | -> | model |
+-------+    +-------+
\`\`\`
<!-- ascii-note:
intent: <one line — what this diagram is trying to show>
emphasize: <which boxes/arrows/labels matter most; what should pop visually>
labels: <if axes/legend/units exist, list them>
template-hint: <optional — name a knowledge/image-styles/*.txt template the illustrator should try first>
-->
```

Hard rules for the editor when *producing* ASCII:
- Opening fence is exactly ` ```ascii ` (lowercase, no trailing space, language tag literal). No empty fences, no `text`, no `diagram`, no `mermaid`.
- Closing fence is exactly ` ``` ` on its own line.
- The fence pair brackets the diagram bytes only — no headings, no prose, no Markdown list markers inside.
- The optional `<!-- ascii-note: ... -->` HTML comment follows the closing fence with at most one blank line between them.

Together, ` ```ascii ` + closing ` ``` ` are the diagram's open/close sentinel pair — the analogue of `<!-- ascii-note:` + `-->`. Downstream extractors (`talksmith:polish-ascii scan`, `talksmith:ascii-to-svg`) key on the `ascii` tag alone; the glyph heuristic is retained only as a fallback for legacy / hand-edited files and is flagged for migration.

The note is for the **rendering pass**, not the reader of `master.md`. Keep it terse (≤ 4 short lines) and factual — no narrative. The illustrator reads this comment when it walks the diagram in Step 6 and forwards it to the `talksmith:ascii-to-svg` skill as extra context, so the SVG can be labelled, colored, and laid out with intent rather than guessed at from the glyphs alone. **An ASCII block without an `ascii-note` is valid** (the illustrator falls back to slide title + Content + Speaker notes); add the note whenever the diagram has a non-obvious intent or a specific element worth emphasizing.

**Reuse hint — skip rendering when an existing SVG is being reused.** If the ASCII block is *not* meant to drive a fresh render — e.g. the slide is reusing an SVG produced for an earlier slide / earlier Talk / hand-authored asset that already lives under `images/` — declare it with a `reuse:` line inside the same `ascii-note`:

```markdown
<!-- ascii-note:
reuse: images/<existing-file>.svg
intent: <still useful so future maintainers know what the ASCII represents>
-->
```

When `reuse:` is present, the ASCII block exists **only as documentation** of what the existing SVG depicts — the illustrator must **skip** the `talksmith:ascii-to-svg` invocation entirely and report `reused: images/<existing-file>.svg`. The Step-6 inlining replaces the ASCII fence with `![<alt>](images/<existing-file>.svg)` and preserves the original ASCII in the `<!-- ascii-source: ... -->` comment, exactly as it would for a freshly rendered diagram. **Pre-flight check:** before reporting `reused`, verify the referenced file actually exists under `talks/<Talk>/images/` (or, for cross-Talk reuse, copy it in during Step 6's image-consolidation pass). If the file is missing, fail loudly — do not fall back to rendering.

This convention applies only to ASCII drafted *now* (during slide drafting). The Step-6 `<!-- ascii-source: ... -->` comment is a different artifact — added by the editor *after* rendering — and the two can coexist beneath the same image reference once Step 6 runs.

**Step 5 — apply feedback.** Delegate all mechanical bookkeeping to the [`talksmith:feedback-cycle`](../skills/feedback-cycle/SKILL.md) skill plus its detection partner [`talksmith:find-open-notes`](../skills/find-open-notes/SKILL.md). The editor (LLM) **only** authors three things per bullet: the content fix in the slide, the one-sentence resolution, and the tag list. Every line edit on `master.md` and every row appended to `feedback-backlog.md` goes through the skill — do **not** read `master.md` end-to-end during a normal Review round.

Per-round loop:

1. **Detect unstamped bullets.**
   ```bash
   python3 .claude/skills/find-open-notes/find_open_notes.py talks/<Talk>/master.md
   ```
   Returns `line / location / text` per unstamped bullet.

2. **Conflict detection (optional, before stamping).** Group the returned bullets by `location`. If two bullets target the same slide with mutually-exclusive instructions ("merge with N" vs "split into two"), surface the conflict to the orchestrator and **skip** stamping those bullets — they stay un-stamped until the presenter disambiguates. Apply the rest of the loop to the non-conflicting ones.

3. **For each non-conflicting unstamped bullet:**
   a. **Stamp.**
      ```bash
      python3 .claude/skills/feedback-cycle/feedback_cycle.py stamp \
          --master talks/<Talk>/master.md --line <N>
      ```
   b. **Apply the content fix.** Read **only** the slide pointed at by `location` from the detection step. Edit Content / Sources / Speaker notes / structure as the bullet implies. Move dropped content to `# Cut material` (the only end-of-file write the editor still performs by hand). If the bullet can't be resolved, **skip** the close step — leave it `[open]` and continue. Step 6 (c) will rescue it.
   c. **Close** with the resolution wording.
      ```bash
      python3 .claude/skills/feedback-cycle/feedback_cycle.py close \
          --master talks/<Talk>/master.md --line <N> \
          --resolution "<one-line summary of what changed>"
      ```
   d. **Mirror** to the backlog with editor-chosen tags (reuse existing tags from prior entries before inventing new ones — see `knowledge/feedback-backlog.md` → *Tagging vocabulary*).
      ```bash
      python3 .claude/skills/feedback-cycle/feedback_cycle.py mirror-row \
          --master talks/<Talk>/master.md \
          --backlog knowledge/feedback-backlog.md \
          --line <N> --tags "<csv>"
      ```

4. **Sanity check at end of round.**
   ```bash
   python3 .claude/skills/feedback-cycle/feedback_cycle.py find-closed-unmirrored \
       --master talks/<Talk>/master.md \
       --backlog knowledge/feedback-backlog.md
   ```
   Catches any `[closed]` bullet that didn't get its `mirror-row` (crashed mid-loop, manual close, etc.) — surface and re-run `mirror-row` for each.

The Step 6 (c) `rescue-open` pass is handled by the same skill (`feedback-cycle rescue-open`) and is invoked there, not here.

**Step 6 — clean `master.md`.** Apply (a), (b), (c) in any order; apply (d) last.

(a) **Inline SVGs.** This is mechanical work — delegate the parsing and the line-based rewrite to the [`talksmith:polish-ascii`](../skills/polish-ascii/SKILL.md) skill rather than re-implementing it inline. The skill has three subcommands matching the canonical five-stage Step 6 sequence below — the editor performs only stages 1 and 5; stages 2 / 3 / 4 are the illustrator's.

```bash
# 1) editor: capture every fenced ASCII block + trailing ascii-note (line ranges)
python3 .claude/skills/polish-ascii/polish_ascii.py scan talks/<Talk>/master.md > /tmp/<Talk>.plan.json

# 2) illustrator: annotate each block with render = {svg_basename, alt}
#    (svg_basename slug derivation lives in .claude/roles/illustrator.md → Output filename convention)

# 3) illustrator: write .ascii sidecars (NOT master.md yet)
python3 .claude/skills/polish-ascii/polish_ascii.py extract --master talks/<Talk>/master.md --plan /tmp/<Talk>.plan.json

# 4) illustrator: per-sidecar render loop — once per .ascii file, invoke talksmith:ascii-to-svg
#    in Mode B (ascii_file: <path>) so the skill reads source + note straight from the sidecar.
#    One sidecar → one skill invocation → one SVG written next to it.

# 5) editor: rewrite master.md fences (NOT sidecars again)
python3 .claude/skills/polish-ascii/polish_ascii.py cleanup --master talks/<Talk>/master.md --plan /tmp/<Talk>.plan.json
```

The `apply` subcommand (sidecars + cleanup in one shot) exists for quick passes where rendering happened out of band — prefer the staged `extract` → render → `cleanup` flow for normal Step 6.

For each rendered `talks/<Talk>/images/<slide-id>-<n>-<short-description>.svg` (filename convention owned by the illustrator — see `.claude/roles/illustrator.md` → *Output filename convention*), the skill performs the following three-step transform per block — this is the spec the skill implements; understand it so you can audit results, but **do not re-implement** in ad-hoc Python:

1. **Detect and capture.** Find the fenced ASCII block. **Look immediately after the closing fence** (skipping at most a single blank line) for an `<!-- ascii-note: ... -->` HTML comment. If one is present, capture it verbatim — opening sentinel through the terminal `-->` — including all interior lines. The captured note is the input to the sidecar in the bullet below. If no comment is there, capture nothing (no synthesis, no defaults).
2. **Replace the ASCII fence** with the image reference plus an `<!-- ascii-source: -->` echo of the original ASCII:
   ```markdown
   ![<slide title or short description>](images/<slide-id>-<n>-<short-description>.svg)
   <!-- ascii-source:
   <original ASCII verbatim>
   -->
   ```
3. **Leave the post-fence `<!-- ascii-note: ... -->` in `master.md` in place.** Do not delete it, do not move it. It remains directly below the new image reference (after the `ascii-source` comment) and continues to document render-time intent for future re-renders. The Step-6 (d) strip targets only `Presenter feedback`, not `ascii-note`.

**Sidecar `.ascii` file — also write the source to disk.** In addition to embedding the ASCII in the HTML comment, write a sidecar to `talks/<Talk>/images/<slide-id>-<n>-<short-description>.ascii` (same basename as the SVG, `.ascii` extension). The sidecar contains the **ASCII source and the captured illustrator note** from step (a.1) above, in this exact layout:

```
<ASCII bytes verbatim — no fence, no leading/trailing blank lines>

<!-- ascii-note:
intent: ...
emphasize: ...
labels: ...
template-hint: ...
-->
```

- The ASCII section is mandatory; it's the diagram bytes exactly as they appeared between the opening and closing fences in `master.md`.
- The `<!-- ascii-note: ... -->` section is **included verbatim if and only if the slide carried one in `master.md`**. The sentinel `<!-- ascii-note:` lets a downstream script split the file: everything before the sentinel line (minus the separating blank) is the ASCII payload; everything from the sentinel through `-->` is the note. If no note exists on the slide, write only the ASCII bytes — no trailing comment, no empty stub.
- A blank line separates the two sections (only when the note section is present).

**Rationale:** the HTML comment in `master.md` lets the SVG be regenerated from the deck alone, but a sidecar file makes both the source and the renderer's intent trivially recoverable even if `master.md` is later edited, makes diffs cleaner (git treats `.ascii` as a normal text file), and means the `images/` folder is a self-contained record of every diagram in three representations (rendered SVG, ASCII source, render-time intent).

**Idempotency:** if the `.ascii` file already exists and its bytes match the new content, skip the write (avoid touching the mtime). If it differs, overwrite — the new ASCII + note in `master.md` is authoritative.

**Reuse case:** when an `ascii-note` carries `reuse: images/<file>.svg`, do **not** write a sidecar — the ASCII fence in `master.md` is documentation, not source-of-truth for the reused SVG, and writing a sidecar would overwrite the original asset's record. (If the original asset has its own sibling `.ascii` file from when it was first rendered, that file is left untouched.)

(b) **Consolidate image refs.** Walk every `![alt](path)`. If `path` already starts with `images/`, leave it. For any other local path, **copy** (never move) the file into `talks/<Talk>/images/<basename>` and rewrite the reference. On filename collision with different content, append `-2`, `-3`, … Skip remote URLs — leave those untouched.

(c) **Rescue `[open]` feedback.** Delegate to [`talksmith:feedback-cycle`](../skills/feedback-cycle/SKILL.md):
```bash
python3 .claude/skills/feedback-cycle/feedback_cycle.py rescue-open \
    --master talks/<Talk>/master.md
```
The skill walks every `[open]` bullet, appends `- <location> — "<verbatim>"` under `# Open questions` (creating the section before `# Cut material` if missing), and skips entries already present. `[closed]` bullets and raw un-stamped bullets are ignored.

(d) **Strip `Presenter feedback` fields.** Remove at every level (Thesis, Agenda, Section, Slide). Recognize all three forms: H3 (`### Presenter feedback`), paragraph (`**Presenter feedback:**`), legacy bullet (`- **Presenter feedback:**`).

**Step 7 — two passes, in order.**

1. **Promote.** Append a new entry to `knowledge/learnings.md` in its existing format (rule, why, where it applies, evidence, date). Generate a stable entry id (incrementing integer or next slug — match the file's convention). Return the entry id.
2. **Move.** For each backlog row to move: append it to `knowledge/feedback-processed.md` adding `promoted_to: <entry id>` and `promoted_at: <date>`, then remove it from `knowledge/feedback-backlog.md`. This removal is the only deletion the Editor performs in any step.

## Operating principles

- **Cite by filename.** Slide `Sources` reference `knowledge/compile/` files (e.g. `compile/transformer-paper.md`). Never invent sources.
- **Never silently drop content.** Removed content goes to `Cut material` (with a one-line reason) or `Open questions`.
- **Preserve structure.** Section headings: `# N. <Section Name>` (H1). Slide headings: `## N. <Slide Title>` (H2). Per-slide fields: `### Content`, `### Sources`, `### Speaker notes`, `### Presenter feedback` (H3). Insert `---` between every Slide and after each Section header. Section/Agenda-level feedback stays in paragraph form (`**Presenter feedback:**` + bullets).
- **Field semantics** live in `.claude/schemas/master.md` → *Field semantics* table. Read it when filling a field.
- **Show your work.** Return the affected section (or a diff summary) so the orchestrator can confirm with the presenter.

## Presenter feedback log

`Presenter feedback` fields are append-only. The presenter writes plain bullets; stamp them — never ask the presenter to format.

1. **New feedback** — rewrite as: `- [open] YYYY-MM-DD — "<verbatim presenter text>"`
2. **Resolution** — flip to: `- [closed] YYYY-MM-DD — "<verbatim>"` + `  Resolution: <what changed>`. Keep the original date.
3. Never delete closed entries. Multiple rounds accumulate oldest-first.
