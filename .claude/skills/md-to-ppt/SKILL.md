---
name: md-to-ppt
description: Convert a Talk's cleaned `master.md` into a PowerPoint (.pptx) deck via Anthropic's native `pptx` skill. **Cowork-only** — requires the native `pptx` skill in the session registry. Optional Step 7 of the Presenter Agent workflow, invoked after Step 6.5 (Polish) has rendered SVGs and cleaned `master.md`. Consumes the SVGs already on disk under `images/`; does not render anything itself.
---

# md-to-ppt — Render `master.md` to PowerPoint

**Cowork-only.** Delegates `.pptx` authoring to Anthropic's official `pptx` skill, available in Claude Cowork (desktop app and web) but not in the plain Claude Code CLI. If the skill is not in the session registry, stop and tell the presenter to run this step inside Cowork. No CLI fallback — see *Why Cowork-only* at the bottom.

**Single responsibility.** This skill **only** assembles the PPTX. ASCII → SVG conversion is the [`illustrator`](../../agents/illustrator.md) subagent's job, dispatched in Step 6.5 (Polish) before this skill ever runs. `master.md` arrives already cleaned (image refs inlined, `Presenter feedback` stripped) and the SVGs are already on disk.

## When to use

After Step 6.5 (Polish) completes and the presenter picks **Render to PowerPoint** from the terminal branch. Optional — many presenters stop at the outline.

## Prerequisites

| Prereq | What to check | If missing |
|---|---|---|
| Native `pptx` skill in session registry | Skill list includes `pptx` | Stop. Tell presenter to run this step inside Cowork. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `master.md` | No `Presenter feedback` fields; ASCII blocks replaced by `![...](images/...)` refs | Stop. Polish hasn't run — return to Step 6.5. |
| Pre-rendered SVGs | `talks/<Talk>/images/*.svg` exist for every image ref in `master.md` | Stop. Dispatch `illustrator` to fill the gap. |
| Reference template | [`knowledge/template.pptx`](../../../knowledge/template.pptx) exists (or the presenter-supplied override path) | Stop and ask. |

## Inputs

- **Active `Talk` path** — absolute.
- **`knowledge/profile.md` content** — pass the global presenter profile when non-empty so any rendering-relevant preferences inform pre-processing.
- **Reference template** — defaults to [`knowledge/template.pptx`](../../../knowledge/template.pptx). Override only if the presenter explicitly passes a different path.

## Output

```
talks/<Talk>/output/
├── master.pptx              # this skill writes
├── master.intermediate.md   # transient pre-processed file
└── svg/                     # already populated by illustrator (Step 6.5)
    ├── s1-1.svg
    ├── s1-2.svg
    └── ...
```

## Process

1. Verify all prerequisites (table above). Stop on any failure.
2. **Pre-process `master.md`** into `output/master.intermediate.md`:
   - Strip remaining working-notes sections: `# Thesis`, `# Open questions`, `# Cut material`. (`Presenter feedback` is already gone — cleaned by Polish.)
   - Map structure: every numbered H1 (`# N. <name>` current, legacy `# N — <name>` / `# Section N: <name>`) → a dedicated divider slide. Named H1s `# Agenda` and `# Conclusions` are passed through. `# Open questions` and `# Cut material` are stripped. Every H2 inside a section or `Conclusions` → a content slide. Slide-heading forms: current `## N. <title>`, legacy `## N — <title>` and `## Slide N: <title>` — strip the leading prefix when extracting the title.
   - Slide fields are H4 headings: `### Content`, `### Sources`, `### Speaker notes`. Speaker-note content goes into the slide's notes pane, not the body. Legacy `- **Field:** …` bullet form also accepted.
   - **Resolve image references.** Every `![alt](images/<file>.svg)` in `master.md` is a slide image. Pass the file path to the native skill — do not re-render. Ignore any `<!-- ascii-source: ... -->` HTML comments.
3. **Render** by invoking the native `pptx` skill with three inputs: the intermediate file, the SVG asset paths, and the reference template. The native skill must inherit the template's theme, fonts, colors, and master slide layouts — it must **not** author the deck from scratch using its own default theme. Use the inherit-wholesale mode if the skill offers a choice between modes.
4. Verify `talks/<Talk>/output/master.pptx` exists and is non-empty.
5. **Verify visual fidelity.** Spot-check that the rendered deck matches the reference template's look (theme, fonts, layouts). If it doesn't, treat as a failure — see *Failure modes*.
6. Report: slide count, image references resolved, any warnings from the native skill.

## Rules

- **The base template is mandatory, not advisory.** Every render inherits theme, fonts, colors, and master layouts from [`knowledge/template.pptx`](../../../knowledge/template.pptx) (or the explicit override). Decks authored from scratch with the native skill's default theme are a render failure even if the file is otherwise correct.
- **One divider slide per Section.** Each numbered H1 produces a dedicated divider slide. Never collapse Sections.
- **Never modify `master.md` during render.** All transformation happens in memory or in `output/master.intermediate.md`. The cleaned `master.md` from Polish stays the source of truth.
- **Never re-render SVGs.** If an image ref points at a missing SVG, stop and dispatch `illustrator` rather than improvising.
- **Speaker notes go into the notes pane**, never on the slide body.

## Failure modes to surface

- Native `pptx` skill not available → stop, instruct presenter to run inside Cowork.
- Reference template missing or unreadable → stop and ask.
- Reference template was loaded but not honored (rendered deck's theme/fonts/layouts don't match) → surface loudly; offer to rerun. Do not silently ship a deck with the wrong look.
- `master.md` not yet cleaned (still contains `Presenter feedback` fields or unrendered ASCII fenced blocks) → stop; return to Step 6.5.
- An image ref points at a missing SVG → stop; dispatch `illustrator` to render it.
- A Section has zero Slides.
- Native skill exits non-zero → surface its error message verbatim in the final report.

## Why Cowork-only

Earlier iterations tried three CLI rendering paths:

| Attempt | Outcome |
|---|---|
| Hand-rolled `python-pptx` script | Brittle parsing of `master.md`, layout-by-layout reimplementation of theme. Abandoned. |
| Marp CLI | Required migrating `master.md` to Marp syntax — a structural change to the source of truth. Reverted. |
| `pandoc --reference-doc=…` | Template-layout name mismatch (pandoc expects `Title Slide`, `Section Header`, etc. — our template doesn't have them), so theme fell back to pandoc's defaults. Section dividers also split into two slides because of body content between H1 and the first H2. Tables sometimes dropped silently. Removed. |

Each path produced a deck with subtle correctness or fidelity issues. The native `pptx` skill is the only tested-good rendering path. `master.md` is plain Markdown, so a presenter who really needs CLI rendering for a one-off can pipe it through their own toolchain — Talksmith just won't maintain that path.
