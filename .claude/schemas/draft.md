# Schema — `talks/<Talk>/draft.md` (+ derived `final.md`)

Specification for `talks/<Talk>/draft.md`: the per-Talk **working file** Talksmith produces during Steps 1–5, and for `talks/<Talk>/final.md`: the **derived deliverable** Step 6 (Polish) produces from it.

Each Talk has at most one of each. The shape defined here is parsed downstream by the Composer and Editor roles and by the `talksmith:md-to-pptx` skill's `convert.py` — do not rename or restructure the canonical headings, frontmatter keys, or field labels.

## Two files, one shape

`draft.md` and `final.md` share **the same Markdown shape** — the canonical block structure, frontmatter, field semantics, and slide locator notation below apply to both. They differ only in what fields are populated:

| Field family | In `draft.md` | In `final.md` |
|---|---|---|
| Frontmatter, Thesis claim, Agenda arc, Section goals, Slide Content / Sources / Speaker notes, Conclusions, Cut material | Present | Present (verbatim copy from `draft.md`) |
| `Presenter feedback` blocks (Thesis / Agenda / Section / Slide) | Append-only log of `- "..."`, `[open]`, and `[closed]` bullets — the audit trail | **Removed entirely** by Step 6 (d) (the strip targets the field at every level, in all three syntactic forms) |
| Fenced ` ```ascii ` blocks (render-driving — slide has no Markdown image ref) | Present, with optional trailing `<!-- ascii-note: ... -->` HTML comment | Replaced by `![alt](images/<slide-id>-<n>-<short-description>.svg)` plus a `<!-- ascii-source: ... -->` echo. The `<!-- ascii-note: ... -->` HTML comment stays in place |
| Fenced ` ```ascii ` blocks (documentation-only — slide already carries a Markdown image ref) | Present | **Left verbatim** — no render, no sidecar, no fence rewrite. The image link wins; the ASCII is inline aid for whoever reads `final.md` source. (See [editor.md](../roles/editor.md) → *Optional ASCII alongside an image link* and [illustrator.md](../roles/illustrator.md) → *Render-driving vs. documentation-only*.) |
| `![alt](path)` image refs | Present, may point at corpus-companion paths, external paths, etc. | Present, **all** rewritten to `images/<basename>` (remote URLs are the only exception — left untouched) |
| `# Open questions` | Present, anything genuinely undecided | Present, also receives any **un-applied `[open]`** bullets rescued from feedback blocks before the strip |

That is the entire diff between the two files. Step 6 (Polish) is the only producer of `final.md`; it is **always** derived from `draft.md` and **never** edited by hand. `draft.md` is **never** mutated after Step 5 ends.

## Purpose

`draft.md` is the **single source of truth for one Talk during authoring**. It captures the thesis, the agenda, every Section and Slide (with Content, Sources, Speaker notes, and an in-place Presenter-feedback log), plus closing material (Conclusions, Open questions, Cut material). The presenter edits it directly in Step 5; the Editor stamps and applies bullets via the [`talksmith:feedback-cycle`](../skills/feedback-cycle/SKILL.md) skill.

`final.md` is the **single source of truth for one Talk as deliverable**. It carries no working-meta: no `Presenter feedback`, no raw ASCII fences for render-driving diagrams. Step 7 (Global-Librarian) and Step 8 (PPTX render) both read `final.md`. Downstream tooling renders the slides; the shape of these files matters more than their prose polish.

The split exists so Step 6 stays re-runnable: re-render diagrams, re-tweak the Polish pipeline, regenerate `final.md` from scratch — `draft.md` always survives.

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| Editor role (writer of `draft.md`) | Step 4 (Draft), Step 5 (Review). **Sole writer of `draft.md`.** | Bootstrap on first Step 4 pass from the *Canonical empty form* below; fill thesis / agenda / sections / slides during Draft; apply presenter feedback during Review. |
| Editor role (writer of `final.md`) | Step 6 (Polish), action 0 onward. **Sole writer of `final.md`.** | Step 6 (0): `cp draft.md final.md`. Step 6 (a)–(d): inline SVGs, consolidate image refs, rescue `[open]` feedback, strip `Presenter feedback`. Never reads or writes `draft.md` after Step 6 begins. |
| Composer role (reader of `draft.md`) | Every drafting milestone in Step 4 | Critique the scoped slice (`thesis` / `agenda` / `section:N` / `full`) against thesis alignment, audience fit, citations, principles, and learnings. Returns a punch-list; does **not** edit. |
| Illustrator role (reader of `final.md`) | Step 6 (Polish) action 1 | Walk for fenced ASCII blocks and `<!-- ascii-source: ... -->` HTML comments; extract per-slide context; invoke the `talksmith:ascii-to-svg` skill per block. Read-only. |
| Global-Librarian role (reader of `final.md`) | Step 7 (Learnings) on promotion | Curate reusable knowledge into `knowledge-library/`. Read-only. |
| `talksmith:md-to-pptx` skill / `convert.py` (reader of `final.md`) | Step 8 (Render PPTX) | Pre-process into an intermediate Markdown shape and hand to `skill://antropic-skills:/pptx`. Read-only. |

The orchestrator does **not** write either file directly — every change goes through the editor.

## Lifecycle

1. **Step 1 (Frame).** Folder tree created; neither file exists yet.
2. **Step 4 (Draft) — first Editor role pass.** Editor bootstraps `draft.md` from the *Canonical empty form* (below): copy the form, strip every HTML comment and every YAML frontmatter comment line, keep all headings / frontmatter keys (with empty values) / field labels. Then fill.
3. **Steps 4–5 — iterate.** Editor fills `draft.md` and applies presenter feedback rounds.
4. **Step 6 (Polish).** Editor copies `draft.md` → `final.md` (action 0). Illustrator renders ASCII → SVG. Editor inlines image refs in `final.md` (preserving the ASCII as an HTML comment), consolidates other image refs into `images/`, rescues any remaining `[open]` feedback bullets into `# Open questions`, then strips every `Presenter feedback` field from `final.md`. **`draft.md` is never touched.**
5. **Step 7 (Learnings).** `final.md` is finalized; the orchestrator scans the cross-Talk feedback backlog. If the presenter promotes the Talk, the Global-Librarian curates `final.md` + corpus records into `knowledge-library/`.
6. **Step 8 (Render PPTX, optional).** `convert.py` produces `output/final.intermediate.md` from `final.md`; native `pptx` skill renders to `output/final.pptx`. Neither `draft.md` nor `final.md` is modified.

## Canonical block structure

Identical in `draft.md` and `final.md` (modulo the Step-6 differences listed in *Two files, one shape* above).

| Block | Heading | Sub-fields |
|---|---|---|
| Frontmatter | YAML between `---` fences | `presentation`, `presenter`, `audience`, `duration`, `date`, plus pass-through keys `research` and `description` that downstream tooling reads — do not edit those last two |
| Thesis | `# Thesis` | `**Claim:**`, `**Why it matters:**`, `**Presenter feedback:**` (in `draft.md` only) |
| Agenda | `# Agenda` | `**Narrative arc:**`, `**Sections (in delivery order):**`, `**Presenter feedback:**` (in `draft.md` only) |
| Section | `# <N>. <Section Name>` (H1, numbered with period) | `**Goal of this section:**`, `**Presenter feedback:**` (in `draft.md` only) |
| Slide | `## <N>. <Slide Title>` (H2, same numbering, scoped within its Section) | `### Content`, `### Sources`, `### Speaker notes`, `### Presenter feedback` (in `draft.md` only) |
| Conclusions | `# Conclusions` | Contains slides (`## N. <Slide Title>`) like any other Section |
| Open questions | `# Open questions` | Free-form list. In `final.md` it **also contains rescued `[open]` Presenter feedback rows** mirrored by the editor during Step 6 (Polish) — transformation (c), before the `Presenter feedback` strip in (d) — in the form `- <location> — "<verbatim feedback>"` where `<location>` is the slide/section locator (e.g. `Slide 2.1`, `Agenda`, `Thesis`). |
| Cut material | `# Cut material` | Free-form list (do not delete content; relocate here instead) |

**Separator rule:** insert a `---` horizontal rule between every Slide and after each Section header. Section/Agenda-level `Presenter feedback` stays in paragraph form (`**Presenter feedback:**` followed by bullets); per-Slide `Presenter feedback` uses the H3 form (`### Presenter feedback`).

## Field semantics

| Field | Where | Meaning |
|---|---|---|
| `Thesis.Claim` | top of file | One sentence — what the audience walks away believing or able to do. |
| `Thesis.Why it matters` | top of file | The stakes / gap / decision unlocked by the claim. |
| `Thesis.Presenter feedback` | top of `draft.md` | Feedback log on the framing of the thesis. Stripped from `final.md`. |
| `Agenda.Narrative arc` | top of file | Short paragraph describing how the Sections connect. |
| `Agenda.Sections` | top of file | The ordered bullets the audience sees. |
| `Agenda.Presenter feedback` | top of `draft.md` | Feedback log about agenda ordering, pacing, cut/keep. Stripped from `final.md`. |
| `Section.Goal of this section` | per Section | What this Section accomplishes for the overall thesis. |
| `Section.Presenter feedback` | per Section in `draft.md` | Feedback log on the framing/scope of this Section. Stripped from `final.md`. |
| `Slide.Content` | per Slide | What appears on the slide — bullets, claim, visual, demo, code. |
| `Slide.Sources` | per Slide | Files in `research/corpus/` that back the slide. Cite by filename. |
| `Slide.Speaker notes` | per Slide | What the presenter says aloud, transitions, timing. |
| `Slide.Presenter feedback` | per Slide in `draft.md` | Feedback log on this specific slide. Stripped from `final.md`. |
| `Conclusions` | end of file | Closing slides — key takeaways, call to action, Q&A. |
| `Open questions` | end of file | Things still undecided. Revisit before finalizing. In `final.md` also holds rescued `[open]` bullets. |
| `Cut material` | end of file | Ideas considered and dropped, kept in case they come back. |

## Canonical slide locator

The `editor` parses composer punch-lists and presenter feedback on this locator syntax:

- `<section-N>.<slide-M>` — e.g. `2.1` = the slide under `# 2. <Section Name>` → `## 1. <Slide Title>`.
- `thesis` — the `# Thesis` block.
- `agenda` — the `# Agenda` block as a whole (narrative arc, ordering, framing).
- `agenda.section:<N>` — the n-th bullet inside `**Sections (in delivery order):**` (for reordering, renaming, or keep/cut at the agenda level).
- `agenda.<n>` — the n-th ASCII diagram embedded under `# Agenda`, matching the illustrator's `s0-<n>.svg` filename.
- `conclusions.N` — slide N under `# Conclusions`.
- `conclusions.N.<k>` — the k-th ASCII diagram inside that conclusions slide, matching the illustrator's `sc-N-<k>.svg` filename.

The illustrator derives SVG filenames from the same numbering: `s<section>-<slide>-<n>.svg` for regular slides, `s0-<n>.svg` for agenda diagrams, `sc-<N>-<n>.svg` for conclusions diagrams. The trailing `-<n>` is mandatory in every case (even when only one diagram exists).

## Presenter feedback log (in `draft.md`)

`Presenter feedback` fields at Thesis, Agenda, every Section, and every Slide are append-only logs during Steps 4–5, then **stripped wholesale from `final.md`** during Step 6 (Polish). They remain in `draft.md` verbatim — `draft.md` is the audit trail. The audit trail also survives because:

1. every `[closed]` bullet is mirrored into [`config/feedback-backlog.md`](../../config/feedback-backlog.md) by the editor during Review,
2. any `[open]` bullets still un-applied at the moment of Polish are rescued by the editor into `# Open questions` **in `final.md`** (location + verbatim quote) **before** the strip, and
3. git history preserves prior `draft.md` states.

Workflow (per the editor's Step 5 contract):

1. **Raw bullet** (presenter): `- "this needs tightening"` — no status tag, no date, no resolution.
2. **Stamped open** (editor on first scan): `- [open] YYYY-MM-DD — "<verbatim presenter text>"` — today's date.
3. **Stamped closed** (editor after applying):

   ```
   - [closed] YYYY-MM-DD — "<verbatim presenter text>"
     Resolution: <what you changed and why>.
   ```

   Keep the original date — do not bump it to "today".

Never delete closed entries during Step 5 (they're the audit trail). Step 6 strips the entire `Presenter feedback` field from `final.md` once mirrored to the backlog; `draft.md` retains everything.

## Canonical empty form

The Editor role bootstraps `talks/<Talk>/draft.md` from this form on its first Step 4 pass: copy verbatim, strip every HTML comment (`<!-- ... -->`) and every YAML frontmatter comment line (lines beginning with `#` between the `---` fences), then start filling.

```markdown
---
# presentation: one-line subject of the talk (e.g. "Intro to GANs for non-ML engineers")
# Fork-level — same across every Talk in this fork (sourced from profile.md Subject).
presentation: <One-line subject of the talk>
# subtitle: per-class topic — renders on the cover slide below the Subject in smaller font.
# Required (not optional). One short line; do not duplicate the Subject. Example for a fork
# whose Subject is "Inteligencia Artificial Generativa Para Biomedicina":
#   subtitle: "Clase 3 — Ingeniería de prompts y técnicas avanzadas"
subtitle: <Per-class topic, one line>
# research: relative path to the corpus research base for this Presentation
research: research/corpus/
# description: structural shape downstream tooling expects — do not edit
description: Slides are grouped into Sections. Each Section contains one or more Slides.
# presenter: who is delivering the talk (name, role, org)
presenter:
# audience: who is in the room or watching — technical level, role, what they care about
audience:
# duration: total talk length including Q&A (e.g. "30 min + 10 min Q&A")
duration:
# date: when the talk is delivered (ISO format YYYY-MM-DD)
date:
---

# Thesis

**Claim:**

**Why it matters:**

**Presenter feedback:**

---

# Agenda

**Narrative arc:**

**Sections (in delivery order):**

- 1. <Section Name>
- 2. <Section Name>
- 3. <Section Name>

**Presenter feedback:**

---

# 1. <Section Name>

**Goal of this section:**

**Presenter feedback:**

---

## 1. <Slide Title>

### Content

### Sources

### Speaker notes

### Presenter feedback

---

## 2. <Slide Title>

### Content

### Sources

### Speaker notes

### Presenter feedback

---

# 2. <Section Name>

**Goal of this section:**

**Presenter feedback:**

---

## 1. <Slide Title>

### Content

### Sources

### Speaker notes

### Presenter feedback

---

# 3. <Section Name>

**Goal of this section:**

**Presenter feedback:**

---

## 1. <Slide Title>

### Content

### Sources

### Speaker notes

### Presenter feedback

---

# Conclusions

## 1. Key takeaways

### Content

### Sources

### Speaker notes

### Presenter feedback

---

## 2. <Call to action / next steps / Q&A>

### Content

### Sources

### Speaker notes

### Presenter feedback

---

# Open questions

# Cut material
```
