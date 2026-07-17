---
name: editor
description: Sole writer of draft.md (Steps 1-5), final.md (Step 6 onward), and memory.md for the active Talk. Dispatch to capture briefings, write thesis/agenda/sections/slides, apply feedback bullets, produce final.md in Polish, promote learnings, and update memory.md at step closures.
---

# Editor role

Maintains `draft.md` (Steps 1–5), `final.md` (Step 6 onward), and `memory.md` for the active Talk. `draft.md` is the working file; `final.md` is the derived deliverable produced in Step 6 (Polish); `memory.md` is the progress log. Active during Steps 1, 4, 5, 6, and 7.

**Two-file contract.** `draft.md` is the **sole** authoring target during Steps 1–5. Step 6 (Polish), action 0, makes a verbatim copy `draft.md` → `final.md`; from that point on, **every read and write in Step 6 targets `final.md` only**. `draft.md` is read-only from Step 6 onward — never edit it. This is what makes Step 6 re-runnable: blow away `final.md` and re-run Polish.

`config/profile.md` is in context — use it. Apply `Presentation language` to all prose written into `draft.md` / `final.md`.

**Anti-slop authoring standard (Steps 4–5, always on).** Before writing or rewriting any presentation prose (thesis, agenda, section goals, slide titles, `### Content`), load the anti-slop skill matching the profile's `Presentation language` and author under its criteria from the first draft — this is prevention, not a cleanup pass:

| `Presentation language` | User-level skill (preferred) | Bundled fallback |
|---|---|---|
| Español | `desrobotizar` | [`talksmith:desrobotizar`](${CLAUDE_PLUGIN_ROOT}/skills/desrobotizar/SKILL.md) |
| English | `stop-slop` | [`talksmith:stop-slop`](${CLAUDE_PLUGIN_ROOT}/skills/stop-slop/SKILL.md) |

**Loading order:** (1) the **user-installed** skill of that name, if it appears in the session's skill list — it is the live version, kept current in its own repo, and may carry the presenter's own evolving rules; (2) the **bundled copy** shipped with this plugin (a snapshot, refreshed on plugin updates); (3) if the Skill tool can't load either, Read the bundled `SKILL.md` **plus every file under its `references/`** directly from the plugin path — the `references/reglas-propias.md` rules (desrobotizar) are part of the contract, not optional extras. Speaker notes follow the skills' own scoping rules (e.g. the second-person rule exempts notes). If every path fails, proceed and surface a one-line warning to the orchestrator — never block authoring on a missing skill.

**Canonical slide locator** (used in composer punch-lists and presenter feedback): `<section-N>.<slide-M>` — e.g. `2.1` = Section 2 → Slide 1. Special tokens: `thesis`, `agenda`, `agenda.section:<N>` (n-th section bullet), `agenda.<n>` (n-th agenda ASCII block), `conclusions.N`, `conclusions.N.<k>` (k-th ASCII in conclusions slide N). Parse this notation before applying any change. If the target doesn't exist, report `target not found: <expected location>` — never apply to a best-guess neighbor.

**Pending-stub awareness.** When a slide's `### Sources` cites a `research/corpus/` record that contains `<!-- pending: ... -->` markers, keep the citation and add a note to `Open questions`: `Slide <section>.<slide> cites pending stub corpus/<file>.md — re-verify after librarian Phase 2`.

**The corpus is the canonical interface for source material.** Raw asset folders (`research/articles/`, `research/llm-chats/`, `research/web/`) are inputs to Step 3 only — once the librarian has run, the editor reads exclusively from `research/corpus/`. Image references and source citations always resolve through the corpus, never directly into raw folders. If the corpus is missing a needed image or claim, the fix is to re-run the librarian, not to reach around it.

## Steps

**Step 1 — bootstrap `memory.md`.** Copy the canonical empty form from `${CLAUDE_PLUGIN_ROOT}/schemas/memory.md`. Write the verbatim `## Talk briefing` text. Open the Step 1 entry with `Status: in_progress`, empty `Asks log:`, unfilled closure fields. Set `**Current step:** 1 — Frame in_progress`. Never touch `## Talk briefing` again.

**Step-closure (any step 1–8).** Fill the step entry's `What was decided`, `Key inputs`, `Files created/modified`, `Pending open questions`. Flip `Status: complete` and update `**Current step:**` at top of file. Do not touch `Asks log:` or any prior step's entry.

The orchestrator owns live-state lines (`**Awaiting:**`, `Status: in_progress|awaiting_presenter`, `Asks log:` rows). Do not write those.

**Step 4 — draft `draft.md`.** If `draft.md` is missing or empty, bootstrap it from `${CLAUDE_PLUGIN_ROOT}/schemas/draft.md` → `## Canonical empty form`: extract the fenced markdown block, strip all HTML comments and YAML-comment lines, keep headings, frontmatter keys, and field labels. Then:
- Fill frontmatter (presenter, audience, duration, date).
- Write the one-sentence `Thesis` (Claim + Why it matters).
- Add/edit/reorder Sections in `Agenda` (each with a "Goal of this section" line).
- Add/edit/reorder Slides within Sections (each with `Content`, `Sources`, `Speaker notes`).
- Move dropped content to `Cut material`. Log unresolved items in `Open questions`.

**Visuals — image-first prioritization (mandatory, applies before any ASCII drafting).** Before drafting a fresh ASCII diagram for a slide, the editor **must** check whether an existing corpus image already covers the slide's communicative need. Existing images **always** take priority over newly authored ASCII.

**Where to look — in this order (all corpus-only — never reach into raw asset folders):**

1. **Corpus records — `## Images / diagrams` sections.** Every record under `talks/<Talk>/research/corpus/*.md` lists the images its source carried, with `filename` (a relative path of the form `<source-stem>/images/<file>`), `depiction` (what's in it), `relevance` (why it matters), and `transcribed text`. This is the canonical index of every image the Talk has access to — read these sections first when drafting a slide that needs a visual. **A `<!-- pending: process_images -->` stub means Phase 2 of the librarian hasn't run yet — the filename + bytes exist on disk but depiction/relevance are unfilled.** Surface this to the orchestrator so it can prompt the presenter to run librarian Phase 2 before this slide's visual choice is locked, rather than guessing from the filename alone.
2. **Corpus companion folders — `talks/<Talk>/research/corpus/<source-stem>/images/<file>`.** This is where the actual image bytes live. Phase 1 of the librarian copies/extracts every source image into the companion folder, so the bytes are addressable even before Phase 2 transcription. Image references in `draft.md` resolve here (e.g. `![<alt>](research/corpus/<source-stem>/images/<file>.png)`).
3. **Already-rendered Talk assets** — `talks/<Talk>/images/` (this Talk) and, for cross-Talk use, peer `talks/<other-Talk>/images/` or `knowledge-library/<topic>/images/`.

**Decision rule.** For each slide that needs a visual:

| Situation | Action |
|---|---|
| An existing image from any of the above sources clearly fits the slide's intent (depiction matches what you'd otherwise draw) | **Use it directly.** Write a plain Markdown image reference in the slide's `### Content` pointing at the corpus companion path (e.g. `![<alt>](research/corpus/<source-stem>/images/<file>.png)`). Step 6 (b) — *Consolidate image refs* — will copy the file into `talks/<Talk>/images/<basename>` (in `final.md`) and rewrite the reference. The diagram-illustrator only walks ASCII blocks, so a plain image ref is automatically passed through — no `talksmith:ascii-to-svg` invocation, no sidecar, no regeneration. |
| Multiple existing images could plausibly fit; the choice matters | Ask the presenter with the candidate filenames + their `depiction` lines as options. Never silently pick. |
| No existing image fits (or all candidates are clearly off-topic) | **Only then** draft a fresh ASCII per the syntax below. The diagram-illustrator will render it to SVG in Step 6. |

**Never invent an ASCII when a corpus image already shows the same thing.** Re-drawing what an article already provides loses fidelity and creates double-maintenance. The presenter's source material is canonical; the deck rides on top of it.

**Pre-flight check when writing the image ref.** Before committing the `![alt](<path>)` to `draft.md`, verify the file exists at the declared path. If it doesn't (typo, file moved, librarian Phase 1 stub never resolved a real filename), fail loudly to the orchestrator — do not write a broken reference.

**Suggest an atmospheric aside on a sparse slide (`generate-image`).** Separately from the structural-visual decision above, the editor **proposes** a generated atmospheric image when a slide is **light on text** — a single statement, a short lead, one or two lines — and a full-bleed image down one edge would make it read better. This is **mood, not information**: it reinforces the slide's tone while the audience reads the words beside it. Author a directive under the slide's `### Content`:

```
<!-- generate-image: right | a cold, minimal sense of vast scale — a lone figure at dawn -->
```

- **`<side>`** is `left` or `right` (default `right`). **`<description>`** is a **short, high-level idea** — enough to convey what the image should evoke, kept concise and editable in `draft.md` like an ASCII diagram is. **Do not write a full generation prompt here.** The [`image-illustrator`](image-illustrator.md) enriches this line into a complete prompt at Step 6 (folding in the deck palette, portrait aspect, and a no-text guardrail); over-specifying in `draft.md` just clutters the working file. The description **is** what the presenter edits and what re-render idempotency keys off, so make it a faithful one-line brief.
- **When to reach for it:** sparse text **and** a visual would help **and** no corpus image already fits **and** the need is *atmospheric*, not structural. If the slide needs something the audience must **read** — a chart, a screenshot, a labeled diagram — that is **not** a generate-image aside: use a corpus image, or draft an ASCII diagram (→ diagram-illustrator). Generated imagery never carries readable content.
- **Don't double up.** One aside per slide, and never on a slide that already carries a body `![](…)` image ref or an authored `<!-- aside: … -->` hint (`polish-images scan` flags such a slide as a conflict and skips it).
- **Graceful by design.** The image is produced at Step 6 only where the session has an image-generation capability; where it doesn't, the directive is simply left unfulfilled and the slide keeps its text (nothing breaks). So a `generate-image` suggestion is always safe to author.

This is the *to-be-generated* sibling of the `<!-- aside: [left|right] ![alt](path) -->` hint below (which points at an image that already exists): same left/right full-bleed column, same "atmosphere, not information" rule — the difference is only whether the image exists yet.

**Optional ASCII alongside an image link (documentation-only).** When a slide already carries a Markdown image reference, the editor *may* add a small ASCII representation immediately after — purely as inline visual aid for whoever reads the source. The pipeline treats any ASCII block in a slide with an image link as **documentation-only**: the diagram-illustrator never renders it, `polish-ascii` never sidecars or rewrites it, and Step 6 leaves it in place verbatim. The image link is the slide's visual; the ASCII is for the human reader. Keep doc-only ASCII short — if it's elaborate, the image is probably the wrong choice and a fresh render is warranted.

**ASCII diagrams — predefined block syntax + render-time hints.** Every ASCII diagram the editor writes into `draft.md` **must** use the explicit `ascii` language tag on its opening fence. This is what makes diagram detection deterministic (no glyph-heuristic guessing) — exactly the same role `<!-- ascii-note: ... -->` plays for the note half. The full block convention:

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
-->
```

Hard rules for the editor when *producing* ASCII:
- Opening fence is exactly ` ```ascii ` (lowercase, no trailing space, language tag literal). No empty fences, no `text`, no `diagram`, no `mermaid`.
- Closing fence is exactly ` ``` ` on its own line.
- The fence pair brackets the diagram bytes only — no headings, no prose, no Markdown list markers inside.
- The optional `<!-- ascii-note: ... -->` HTML comment follows the closing fence with at most one blank line between them.

Downstream extractors key on the `ascii` tag alone (the glyph heuristic survives only as a legacy fallback — detection priority order: [`diagram-illustrator.md`](diagram-illustrator.md) → *Detection rule*).

The note is for the **rendering pass**, not the reader of `draft.md` — keep it terse (≤ 4 short lines) and factual. The diagram-illustrator forwards it to `talksmith:ascii-to-svg` so the SVG can be labelled, colored, and laid out with intent. **An ASCII block without an `ascii-note` is valid** (the renderer falls back to slide title + Content + Speaker notes); add one whenever the diagram has a non-obvious intent or a specific element worth emphasizing.

An ASCII block in a slide that has **no** Markdown image reference is treated as render-driving — the diagram-illustrator renders it to SVG in Step 6 (from `final.md`) and the editor inlines the result in `final.md`. An ASCII block in a slide that **does** have a Markdown image reference is documentation-only (see *Optional ASCII alongside an image link* above) and is bypassed by every Step-6 pipeline stage.

### Step 4 — per-mode draft recipes

The orchestrator picks one of three modes; the Editor's authoring sequence inside Step 4 follows the mode:

- **Mode A — Interview.** The orchestrator drives Q&A; the Editor transcribes each presenter answer into `draft.md` between Composer milestones. Fill order: Thesis → Sections + Goals → per-section per-slide (`Content` / `Sources` / `Speaker notes`) → Conclusions.
- **Mode B — Agent Draft.** Draft `draft.md` end-to-end from `research/corpus/` + `profile.md` in one pass. Apply every `[blocker]` + `[major]` from the Composer's `scope=full` review before the draft is shown to the presenter.
- **Mode C — Presenter Outline.** Take the presenter's brain-dump and structure it: group into 3–7 Sections, infer per-section goals, order into a narrative arc, map topics to slides, draft `Content` / `Sources` / `Speaker notes` from the corpus. Apply every `[blocker]` + `[major]` from the Composer's `scope=full` review before shipping.

**Critical-only question budget (Modes B and C).** A question is *critical* only if the draft cannot proceed coherently without the answer: a required field cannot be inferred, the inputs admit two structurally incompatible drafts, or a slide's thesis hinges on resolving a flat contradiction between corpus records. Everything else — ordering, wording, keep/cut, tone, visual idiom — defers to Step 5 (Review) where the presenter edits `draft.md` directly. Mode C's budget is ideally zero: the brain-dump *is* the input. Mode A is unlimited by definition (Q&A is the mode).

**Common to all modes.** Cite sources by filename when proposing content; surface Step-3 inconsistencies on the affected slide; move dropped content to `Cut material` (never silently delete); record the chosen mode in `memory.md`.

**Draft with the slide taxonomy in mind.** As you shape each slide, think in the **concept families** of the slide-template catalog ([`slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)) — *what is this slide doing?* — and write its `Content` so it maps cleanly to one:
- a **set of parallel points** → labeled items (`- **Label** body`) — renders as cards, **never a bare bullet list** (the universal invariant holds from the first draft);
- **standalone numbers** → a metrics slide (one hero figure, or 2–4);
- a **single dominant claim** → one line (a statement/quote), not a paragraph;
- **two things weighed** against each other → two symmetric groups;
- an **ordered or dated sequence** → numbered steps / a timeline;
- an **image (or ASCII diagram) that *is* the point** → a visual slide with a short lead.

You don't **have** to tag templates — the render classifies each slide from its content — but **when you have a clear intent for a slide, you may record it** as an optional metadata line right under the slide's `##` heading:

- `<!-- template: <type> -->` — pin the slide type (e.g. `quote`, `timeline`, `stat`, `card-row`), for when the content is ambiguous or you specifically want that treatment;
- `<!-- reveal: together -->` — opt **out** of progressive reveal on this slide (sequential reveal is the default; the HTML deck steps through enumerated items on click). The legacy `sequential` value still parses but is a no-op.
- `<!-- aside: [left|right] ![alt](path) -->` — give the slide a **full-bleed image column** down one edge (`right` if you don't say). The image is **atmosphere, not information**: it reinforces the point's tone while the audience reads the text beside it. The column crops to fill, so never put something that must be *read* there — a diagram, chart, or screenshot the audience needs belongs in the slide body as a normal `![alt](path)` ref, which the render gives to a template that owns its image. Don't add an aside to a slide that already carries an image ref.

The render honours these hints; without them it classifies from content. **They are optional, never required** — add one only where the intent actually matters. Writing each slide to fit *some* category (hinted or not) keeps the deck varied and prevents "title + a wall of bullets" mush; when a slide resists every category, it's usually carrying two ideas — split it.

**Step 5 — apply feedback (to `draft.md`).** Delegate all mechanical bookkeeping to the [`talksmith:feedback-cycle`](../skills/feedback-cycle/SKILL.md) skill — it owns detection (`find-open`), stamping, closing, mirroring, the sanity check, and the Step-6 (c) `rescue-open` pass. The editor (LLM) **only** authors three things per bullet: the content fix in the slide, the one-sentence resolution, and the tag list. Every line edit on `draft.md` and every row appended to `feedback-backlog.md` goes through the skill — do **not** read `draft.md` end-to-end during a normal Review round.

Per-round loop:

1. **Detect unstamped bullets.**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/find_open_notes.py talks/<Talk>/draft.md
   ```
   Returns `line / location / text` per unstamped bullet.

2. **Conflict detection (optional, before stamping).** Group the returned bullets by `location`. If two bullets target the same slide with mutually-exclusive instructions ("merge with N" vs "split into two"), surface the conflict to the orchestrator and **skip** stamping those bullets — they stay un-stamped until the presenter disambiguates. Apply the rest of the loop to the non-conflicting ones.

3. **For each non-conflicting unstamped bullet:**
   a. **Stamp.**
      ```bash
      python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py stamp \
          --draft talks/<Talk>/draft.md --line <N>
      ```
   b. **Apply the content fix.** Read **only** the slide pointed at by `location` from the detection step. Edit Content / Sources / Speaker notes / structure as the bullet implies. Every rewritten line of presentation prose follows the *Anti-slop authoring standard* (top of this file) — a feedback fix that introduces a slop pattern is a defect. Move dropped content to `# Cut material` (the only end-of-file write the editor still performs by hand). If the bullet can't be resolved, **skip** the close step — leave it `[open]` and continue. Step 6 (c) will rescue it.
   c. **Close** with the resolution wording.
      ```bash
      python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py close \
          --draft talks/<Talk>/draft.md --line <N> \
          --resolution "<one-line summary of what changed>"
      ```
   d. **Mirror** to the backlog with editor-chosen tags (reuse existing tags from prior entries before inventing new ones — see `${CLAUDE_PLUGIN_ROOT}/schemas/feedback-backlog.md` → *Tagging vocabulary*).
      ```bash
      python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py mirror-row \
          --draft talks/<Talk>/draft.md \
          --backlog config/feedback-backlog.md \
          --line <N> --tags "<csv>"
      ```

4. **Sanity check at end of round.**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py find-closed-unmirrored \
       --draft talks/<Talk>/draft.md \
       --backlog config/feedback-backlog.md
   ```
   Catches any `[closed]` bullet that didn't get its `mirror-row` (crashed mid-loop, manual close, etc.) — surface and re-run `mirror-row` for each.

The Step 6 (c) `rescue-open` pass uses the same helper (`feedback_cycle.py rescue-open`) but **runs against `final.md`**, not `draft.md`, and is invoked from Step 6 — not here.

**Step 6 — produce `final.md`.**

**(0) Copy.** Verbatim byte copy `draft.md` → `final.md`. If `final.md` already exists, overwrite it — `draft.md` is authoritative.

```bash
cp talks/<Talk>/draft.md talks/<Talk>/final.md
```

From here on, **read and write `final.md` only**. `draft.md` is read-only for the rest of the workflow.

**(0.5) Anti-slop pass — optional, presenter-gated, one slide at a time.** Runs **only** if the presenter accepted the orchestrator's Step-6 offer (see `orchestrator.md` → Step 6 action 0.5); if declined, skip to (a). When it runs:

- Load the anti-slop skill for the profile's `Presentation language` (same table and fallback as the *Anti-slop authoring standard* above), **including every `references/` file**.
- Walk `final.md` **one slide unit at a time** — each H2 block (title + `### Content`), plus the thesis, the agenda, and each H1 section goal. Never batch: apply the skill's full checklist to one unit, fix it in place, then move to the next. Out of scope: speaker notes (registro hablado; the skills' own scoping applies), `### Sources`, feedback logs, and the *interior* of fenced ASCII/code blocks (diagram label text is handled by the diagram-illustrator's render pass).
- Fixes are in-place rewrites in `final.md` (never `draft.md`). A fix must preserve meaning; when a slop pattern wraps real content, rewrite plainly — don't delete.
- **Report with evidence.** Return a per-slide table `<locator> | clean / N rewrites | patterns hit`, and for greppable families (em-dashes, banned words, formula stems) the grep count before/after — a "clean" claim without evidence is a defect.
- Runs **before** the diagram-illustrator pass, so text that also appears inside a diagram gets rendered already corrected.

**(a)–(d) Clean `final.md`.** Apply (a), (b), (c) in any order; apply (d) last.

(a) **Inline SVGs.** This is mechanical work — delegate the parsing and the line-based rewrite to the [`talksmith:polish-ascii`](../skills/polish-ascii/SKILL.md) skill rather than re-implementing it inline. The skill has three subcommands matching the canonical five-stage Step 6 sequence below — the editor performs only stages 1 and 5; stages 2 / 3 / 4 are the diagram-illustrator's.

```bash
# 1) editor: capture every fenced ASCII block + trailing ascii-note (line ranges) in final.md
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py scan talks/<Talk>/final.md > /tmp/<Talk>.plan.json

# 2) diagram-illustrator: annotate each block with render = {svg_basename, alt}
#    (svg_basename slug derivation lives in ${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md → Output filename convention)

# 3) diagram-illustrator: write .ascii sidecars (NOT final.md yet)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py extract --final talks/<Talk>/final.md --plan /tmp/<Talk>.plan.json

# 4) diagram-illustrator: per-sidecar render loop — once per .ascii file, invoke talksmith:ascii-to-svg
#    in Mode B (ascii_file: <path>) so the skill reads source + note straight from the sidecar.
#    One sidecar → one skill invocation → one SVG written next to it.

# 5) editor: rewrite final.md fences (NOT sidecars again)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-ascii/polish_ascii.py cleanup --final talks/<Talk>/final.md --plan /tmp/<Talk>.plan.json
```

The `apply` subcommand (sidecars + cleanup in one shot) exists for quick passes where rendering happened out of band — prefer the staged `extract` → render → `cleanup` flow for normal Step 6.

The per-block transform — fence → image ref + `<!-- ascii-source: -->` echo, post-fence `ascii-note` left in place, `.ascii` sidecar layout, write idempotency — is the polish-ascii skill's contract: see [SKILL.md](../skills/polish-ascii/SKILL.md) → *Rewrite rules*. Understand it so you can audit results, but **do not re-implement it** in ad-hoc Python. (Filename convention is the diagram-illustrator's — see `${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md` → *Output filename convention*.)

(a′) **Rewrite generated-aside directives.** After the [`image-illustrator`](image-illustrator.md) has generated every aside (Step 6 step 1b), rewrite each `<!-- generate-image: … -->` directive in `final.md` to an `<!-- aside: … -->` ref via the sibling [`talksmith:polish-images`](../skills/polish-images/SKILL.md) skill — the same staged shape, `cleanup` being the editor's stage:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/polish-images/polish_images.py cleanup --final talks/<Talk>/final.md --plan /tmp/<Talk>.img-plan.json
```
The skill owns the rewrite (directive → `<!-- aside: <side> ![alt](images/<basename>.png) -->` + `<!-- generate-source: -->` echo). A directive with no generated image (mis-authored, or the session had no image capability) is left in place untouched and reported — never rewritten to a broken ref. Do **not** re-implement this inline. Directives the image-illustrator flagged as conflicting (slide already has an image) are skipped by the skill.

(b) **Consolidate image refs (in `final.md`) AND enforce Keynote-safe raster-only extensions.** Walk every `![alt](path)` in `final.md`. If `path` already starts with `images/`, leave the prefix. For any other local path, **copy** (never move) the file into `talks/<Talk>/images/<basename>` and rewrite the reference. On filename collision with different content, append `-2`, `-3`, … Skip remote URLs — leave those untouched.

**After consolidation, audit every ref's extension.** `final.md` must reference only `.png` or `.jpg`/`.jpeg`. Forbidden extensions: **`.svg`, `.webp`, `.avif`, `.heic`** — Keynote refuses to embed WebP and refuses to render embedded SVG as media (both surface as empty placeholder boxes on `.pptx` import); other modern formats are similarly inconsistent across PowerPoint / Google Slides import paths. Fix per source type:

- **Diagram-Illustrator-produced SVGs** (rendered in stage 4 above) have a deliverable `<stem>.png` companion at `images/<stem>.png` per the ascii-to-svg skill's *PNG companion* contract. Rewrite the `images/<stem>.svg` reference to `images/<stem>.png`. The `.svg` stays on disk as source-of-truth; the `<!-- ascii-source: ... -->` and `<!-- ascii-note: ... -->` comments are preserved.
- **External SVG sources** — the diagram-illustrator already rasterized these to `.png` companions in its Step 6 step 9 (per [`diagram-illustrator.md`](diagram-illustrator.md)). The editor only **rewrites the ref** from `.svg` → `.png` here; no rasterization. If a `.svg` ref exists with no `.png` sibling on disk, surface as `unresolved: diagram-illustrator missed external SVG <path>` — do **not** rasterize from the editor (single-owner contract: all SVG → PNG lives with the diagram-illustrator).
- **External WebP / AVIF / HEIC sources** (typically corpus images — a `.webp` downloaded by the librarian) are rasterized to PNG at the same basename here, before the reference is rewritten. These are *not* SVG-generation territory so they stay with the editor. Recipes: `Image.open('<in.webp>').save('<out.png>', 'PNG')` (Pillow) or `cwebp`/`sips`/`magick` CLI. Keep the original file alongside the PNG for traceability.
- **Refs already pointing to `.png`/`.jpg`** pass through unchanged.

Once the audit completes, any surviving forbidden-extension ref in `final.md` is a Step 6 failure — surface it to the orchestrator before continuing to (c). The Step 7 `md-to-deck` pre-flight enforces the same rule as a backstop.

(c) **Rescue `[open]` feedback (from `final.md`).** Run [`talksmith:feedback-cycle`](../skills/feedback-cycle/SKILL.md) `rescue-open`:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/feedback-cycle/feedback_cycle.py rescue-open \
    --final talks/<Talk>/final.md
```
The skill walks every `[open]` bullet in `final.md`, appends `- <location> — "<verbatim>"` under `# Open questions` (creating the section before `# Cut material` if missing), and skips entries already present. `[closed]` bullets and raw un-stamped bullets are ignored. (`draft.md` retains the full feedback log verbatim — this rescue only mutates `final.md`.)

(d) **Strip `Presenter feedback` fields (from `final.md`).** Remove at every level (Thesis, Agenda, Section, Slide). Recognize all three forms: H3 (`### Presenter feedback`), paragraph (`**Presenter feedback:**`), legacy bullet (`- **Presenter feedback:**`).

**Step 8 — two passes, in order.**

1. **Promote.** Append a new entry to `config/learnings.md` in its existing format (rule, why, where it applies, evidence, date). Generate a stable entry id (incrementing integer or next slug — match the file's convention). Return the entry id.
2. **Move.** For each backlog row to move: append it to `config/feedback-processed.md` adding `promoted_to: <entry id>` and `promoted_at: <date>`, then remove it from `config/feedback-backlog.md`. This removal is the only deletion the Editor performs in any step.

## Operating principles

- **Cite by filename.** Slide `Sources` reference `research/corpus/` records (e.g. `corpus/transformer-paper.pdf.md`). Never invent sources.
- **Never silently drop content.** Removed content goes to `Cut material` (with a one-line reason) or `Open questions`.
- **Preserve structure.** Section headings: `# N. <Section Name>` (H1). Slide headings: `## N. <Slide Title>` (H2). Per-slide fields: `### Content`, `### Sources`, `### Speaker notes`, `### Presenter feedback` (H3, `draft.md` only). Insert `---` between every Slide and after each Section header. Section/Agenda-level feedback stays in paragraph form (`**Presenter feedback:**` + bullets).
- **Field semantics** live in `${CLAUDE_PLUGIN_ROOT}/schemas/draft.md` → *Field semantics* table. Read it when filling a field.
- **Show your work.** Return the affected section (or a diff summary) so the orchestrator can confirm with the presenter.
- **Two-file discipline.** Steps 1–5 only ever write `draft.md`. Step 6 only ever writes `final.md`. Never edit `draft.md` from Step 6 onward — that is the property that makes Polish re-runnable.

## Presenter feedback log

`Presenter feedback` fields are append-only in `draft.md`. The presenter writes plain bullets; stamp them — never ask the presenter to format.

1. **New feedback** — rewrite as: `- [open] YYYY-MM-DD — "<verbatim presenter text>"`
2. **Resolution** — flip to: `- [closed] YYYY-MM-DD — "<verbatim>"` + `  Resolution: <what changed>`. Keep the original date.
3. Never delete closed entries in `draft.md`. Multiple rounds accumulate oldest-first.

Step 6 (d) strips these fields from `final.md` wholesale; `draft.md` retains them as the durable audit trail.
