# Schema — `talks/<Talk>/master.md`

Specification for `talks/<Talk>/master.md`: the per-Talk deliverable file Talksmith produces. Each Talk has exactly one. The shape defined here is parsed downstream by the `composer` and `editor` subagents and by the `talksmith:md-to-pptx` skill's `convert.py` — do not rename or restructure the canonical headings, frontmatter keys, or field labels.

## Purpose

`master.md` is the **single source of truth for one Talk**. It captures the thesis, the agenda, every Section and Slide (with Content, Sources, Speaker notes, and an in-place Presenter-feedback log), plus closing material (Conclusions, Open questions, Cut material). Downstream tooling renders the slides; the shape of this file matters more than its prose polish.

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| `editor` subagent (writer) | Step 4 (Draft), Step 5 (Review), Step 6 (Polish). **Sole writer.** | Bootstrap on first Step 4 dispatch from the *Canonical empty form* below; fill thesis / agenda / sections / slides during Draft; apply presenter feedback during Review; inline SVGs + strip feedback fields during Polish. |
| `composer` subagent (reader) | Every drafting milestone in Step 4 | Critique the scoped slice (`thesis` / `agenda` / `section:N` / `full`) against thesis alignment, audience fit, citations, principles, and learnings. Returns a punch-list; does **not** edit. |
| `illustrator` subagent (reader) | Step 6 (Polish) action 1 | Walk for fenced ASCII blocks and `<!-- ascii-source: ... -->` HTML comments; extract per-slide context; dispatch the `talksmith:ascii-to-svg` skill per block. Read-only. |
| `talksmith:md-to-pptx` skill / `convert.py` (reader) | Step 8 (Render PPTX) | Pre-process into an intermediate Markdown shape and hand to `skill://antropic-skills:/pptx`. Read-only. |

The orchestrator does **not** write `master.md` directly — every change goes through the editor.

## Lifecycle

1. **Step 1 (Frame).** Folder tree created; `master.md` not yet created.
2. **Step 4 (Draft) — first editor dispatch.** Editor bootstraps `master.md` from the *Canonical empty form* (below): copy the form, strip every HTML comment and every YAML frontmatter comment line, keep all headings / frontmatter keys (with empty values) / field labels. Then fill.
3. **Steps 4–5 — iterate.** Editor fills and applies presenter feedback rounds.
4. **Step 6 (Polish).** Illustrator renders ASCII → SVG; editor inlines image refs (preserving the ASCII as an HTML comment), consolidates other image refs into `images/`, strips every `Presenter feedback` field.
5. **Step 7 (Learnings).** `master.md` is finalized; the orchestrator scans the cross-Talk feedback backlog.
6. **Step 8 (Render PPTX, optional).** `convert.py` produces `output/master.intermediate.md`; native `pptx` skill renders to `output/master.pptx`. `master.md` itself is not modified.

## Canonical block structure

| Block | Heading | Sub-fields |
|---|---|---|
| Frontmatter | YAML between `---` fences | `presentation`, `presenter`, `audience`, `duration`, `date`, plus pass-through keys `knowledge` and `description` that downstream tooling reads — do not edit those last two |
| Thesis | `# Thesis` | `**Claim:**`, `**Why it matters:**`, `**Presenter feedback:**` |
| Agenda | `# Agenda` | `**Narrative arc:**`, `**Sections (in delivery order):**`, `**Presenter feedback:**` |
| Section | `# <N>. <Section Name>` (H1, numbered with period) | `**Goal of this section:**`, `**Presenter feedback:**` |
| Slide | `## <N>. <Slide Title>` (H2, same numbering, scoped within its Section) | `### Content`, `### Sources`, `### Speaker notes`, `### Presenter feedback` |
| Conclusions | `# Conclusions` | Contains slides (`## N. <Slide Title>`) like any other Section |
| Open questions | `# Open questions` | Free-form list |
| Cut material | `# Cut material` | Free-form list (do not delete content; relocate here instead) |

**Separator rule:** insert a `---` horizontal rule between every Slide and after each Section header. Section/Agenda-level `Presenter feedback` stays in paragraph form (`**Presenter feedback:**` followed by bullets); per-Slide `Presenter feedback` uses the H3 form (`### Presenter feedback`).

## Field semantics

| Field | Where | Meaning |
|---|---|---|
| `Thesis.Claim` | top of file | One sentence — what the audience walks away believing or able to do. |
| `Thesis.Why it matters` | top of file | The stakes / gap / decision unlocked by the claim. |
| `Thesis.Presenter feedback` | top of file | Feedback log on the framing of the thesis. |
| `Agenda.Narrative arc` | top of file | Short paragraph describing how the Sections connect. |
| `Agenda.Sections` | top of file | The ordered bullets the audience sees. |
| `Agenda.Presenter feedback` | top of file | Feedback log about agenda ordering, pacing, cut/keep. |
| `Section.Goal of this section` | per Section | What this Section accomplishes for the overall thesis. |
| `Section.Presenter feedback` | per Section | Feedback log on the framing/scope of this Section. |
| `Slide.Content` | per Slide | What appears on the slide — bullets, claim, visual, demo, code. |
| `Slide.Sources` | per Slide | Files in `knowledge/compile/` that back the slide. Cite by filename. |
| `Slide.Speaker notes` | per Slide | What the presenter says aloud, transitions, timing. |
| `Slide.Presenter feedback` | per Slide | Feedback log on this specific slide. |
| `Conclusions` | end of file | Closing slides — key takeaways, call to action, Q&A. |
| `Open questions` | end of file | Things still undecided. Revisit before finalizing. |
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

## Presenter feedback log

`Presenter feedback` fields at Thesis, Agenda, every Section, and every Slide are append-only logs during Steps 4–5, then stripped wholesale during Step 6 (Polish). The audit trail survives because every `[closed]` bullet is mirrored into [`knowledge/feedback-backlog.md`](../../knowledge/feedback-backlog.md) by the editor during Review, and git history preserves prior `master.md` states.

Workflow (per the editor's Step 5 contract):

1. **Raw bullet** (presenter): `- "this needs tightening"` — no status tag, no date, no resolution.
2. **Stamped open** (editor on first scan): `- [open] YYYY-MM-DD — "<verbatim presenter text>"` — today's date.
3. **Stamped closed** (editor after applying):

   ```
   - [closed] YYYY-MM-DD — "<verbatim presenter text>"
     Resolution: <what you changed and why>.
   ```

   Keep the original date — do not bump it to "today".

Never delete closed entries during Step 5 (they're the audit trail). Step 6 strips the entire `Presenter feedback` field once mirrored to the backlog.

## Canonical empty form

The editor bootstraps `talks/<Talk>/master.md` from this form on its first Step 4 dispatch: copy verbatim, strip every HTML comment (`<!-- ... -->`) and every YAML frontmatter comment line (lines beginning with `#` between the `---` fences), then start filling.

```markdown
---
# presentation: one-line subject of the talk (e.g. "Intro to GANs for non-ML engineers")
presentation: <One-line subject of the talk>
# knowledge: relative path to the compiled knowledge base for this Presentation
knowledge: knowledge/compile/
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
