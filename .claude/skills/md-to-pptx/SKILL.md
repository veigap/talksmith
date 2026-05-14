---
name: talksmith:md-to-pptx
description: Convert a Talk's cleaned `master.md` into a PowerPoint (.pptx) deck by delegating all .pptx authoring to Anthropic's official `pptx` skill at `skill://antropic-skills:/pptx`. **Cowork-only** — requires that skill in the session registry. Optional Step 8 of the Presenter Agent workflow, invoked after Step 6 (Polish) has rendered SVGs and cleaned `master.md`. Consumes images already on disk under `talks/<Talk>/images/`; does not author the deck itself.
---

# md-to-pptx — Render `master.md` to PowerPoint

**This skill is a thin orchestrator. All `.pptx` authoring must be delegated to Anthropic's official `pptx` skill at [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx).** Do not author the deck with any other tool — no `python-pptx`, no `pandoc`, no Marp, no hand-written XML. Pre-process `master.md`, then invoke `skill://antropic-skills:/pptx` with the intermediate file, the image paths, and the reference template. If that skill is not in the current session's registry (i.e. the session is not running inside Claude Cowork), stop and tell the presenter to run this step inside Cowork. No CLI fallback — see *Why Cowork-only* at the bottom.

**Single responsibility.** This skill **only** prepares the inputs and invokes `skill://antropic-skills:/pptx`. ASCII → SVG conversion is the [`illustrator`](../../agents/illustrator.md) subagent's job, dispatched in Step 6 (Polish) before this skill ever runs. `master.md` arrives already cleaned (image refs inlined, `Presenter feedback` stripped) and every referenced image already lives under `talks/<Talk>/images/`.

## When to use

After Step 6 (Polish) completes and the presenter picks **Render to PowerPoint** from the terminal branch. Optional — many presenters stop at the outline.

## Prerequisites

| Prereq | What to check | If missing |
|---|---|---|
| [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) in session registry | Skill list includes the `pptx` entry | Stop. Tell presenter to run this step inside Cowork. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `master.md` | No `Presenter feedback` fields; ASCII blocks replaced by `![...](images/...)` refs | Stop. Polish hasn't run — return to Step 6. |
| Pre-rendered local images | `talks/<Talk>/images/<file>` exists on disk for every **local** image ref in `master.md` (i.e. every `![...](images/...)` reference). Remote URLs (`http://`, `https://`) are checked separately — see below. | Stop. Dispatch `illustrator` to render missing SVGs, or stop and ask the presenter to drop a missing non-SVG asset into `images/`. |
| Remote image refs handled | `master.md` contains no `![...](http(s)://...)` references — they survived Step 6 Polish unchanged, but `skill://antropic-skills:/pptx`'s behavior on remote URLs is implementation-defined and not guaranteed. | Stop and ask the presenter to either (a) download the asset into `images/` and rewrite the ref to `images/<file>`, or (b) explicitly accept the risk that the slide may ship without that image. Never silently ship a deck where a remote image was dropped. |
| Reference template | [`knowledge/template.pptx`](../../../knowledge/template.pptx) exists (or the presenter-supplied override path) | Stop and ask. |

## Inputs

- **Active `Talk` path** — absolute.
- **`knowledge/profile.md` content** — pass the global presenter profile when non-empty so any rendering-relevant preferences inform pre-processing.
- **Reference template** — defaults to [`knowledge/template.pptx`](../../../knowledge/template.pptx). Override only if the presenter explicitly passes a different path.

## Output

```
talks/<Talk>/
├── master.md                # source (cleaned by Polish)
├── images/                  # populated by illustrator + editor (Step 6)
│   ├── s1-1.svg
│   └── ...
└── output/
    ├── master.pptx              # this skill writes via skill://antropic-skills:/pptx
    └── master.intermediate.md   # transient pre-processed file (produced by convert.py)
```

## Process

1. Verify all prerequisites (table above). Stop on any failure.
2. **Pre-process `master.md` with [`convert.py`](convert.py)** — a CLI-safe, dependency-free Python script that emits the Markdown shape `skill://antropic-skills:/pptx` consumes:

   ```bash
   python3 .claude/skills/md-to-pptx/convert.py \
     talks/<Talk>/master.md \
     -o talks/<Talk>/output/master.intermediate.md
   ```

   The script performs these transformations (specified in its docstring; see [`convert.py`](convert.py) for the canonical contract):
   - Drops YAML frontmatter, HTML comments (including `<!-- ascii-source: ... -->` blocks), and the sections `# Thesis`, `# Open questions`, `# Cut material`.
   - Strips the numeric / legacy prefix from H1 / H2 headings: `# 1. Foundations` → `# Foundations`, `## 2. Why X` → `## Why X`. Legacy forms `# Section N:` / `## Slide N:` / `# N —` / `## N —` accepted.
   - For each H2 slide, processes its H3 fields: drops the `### Content` label (keeps body), drops `### Sources` entirely (presenter-internal), renames `### Speaker notes` → `### Notes` (keeps body), defensively drops any lingering `### Presenter feedback`.
   - Preserves `![alt](images/...)` image refs verbatim. Preserves `---` rules.
   - Collapses runs of 3+ blank lines to 1.

   Output Markdown shape — one H1 per section divider, one H2 per content slide, `### Notes` for speaker notes, inline image refs. This is what `skill://antropic-skills:/pptx` receives.

3. **Render** by invoking [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) with three inputs:
   - the intermediate file at `output/master.intermediate.md`,
   - the image paths under `talks/<Talk>/images/` (the intermediate already references them — `skill://antropic-skills:/pptx` resolves them relative to the intermediate's parent),
   - the reference template at [`knowledge/template.pptx`](../../../knowledge/template.pptx) (or the explicit override).

   The skill must inherit the template's theme, fonts, colors, and master slide layouts — it must **not** author the deck from scratch using its own default theme. Use the inherit-wholesale mode if the skill offers a choice between modes.
4. Verify `talks/<Talk>/output/master.pptx` exists and is non-empty.
5. **Verify visual fidelity.** Spot-check that the rendered deck matches the reference template's look (theme, fonts, layouts). If it doesn't, treat as a failure — see *Failure modes*.
6. Report: slide count, image references resolved, any warnings surfaced by `skill://antropic-skills:/pptx`.

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
- `master.md` not yet cleaned (still contains `Presenter feedback` fields or unrendered ASCII fenced blocks) → stop; return to Step 6.
- An image ref points at a missing SVG → stop; dispatch `illustrator` to render it.
- A Section has zero Slides.
- Native skill exits non-zero → surface its error message verbatim in the final report.
- **H1-as-content-slide regression.** The H1-→-divider semantic is fully outsourced to `skill://antropic-skills:/pptx` — `convert.py` only strips the numeric prefix and passes H1 through. After render, spot-check: every numbered section in `master.md` must produce exactly one **divider** slide (large title, no body). If the native skill rendered an H1 as a normal content slide with the section name in the body, the contract was violated — surface as a render failure, do not silently ship.

## Why Cowork-only

Earlier iterations tried three CLI rendering paths:

| Attempt | Outcome |
|---|---|
| Hand-rolled `python-pptx` script | Brittle parsing of `master.md`, layout-by-layout reimplementation of theme. Abandoned. |
| Marp CLI | Required migrating `master.md` to Marp syntax — a structural change to the source of truth. Reverted. |
| `pandoc --reference-doc=…` | Template-layout name mismatch (pandoc expects `Title Slide`, `Section Header`, etc. — our template doesn't have them), so theme fell back to pandoc's defaults. Section dividers also split into two slides because of body content between H1 and the first H2. Tables sometimes dropped silently. Removed. |

Each path produced a deck with subtle correctness or fidelity issues. The native `pptx` skill is the only tested-good rendering path. `master.md` is plain Markdown, so a presenter who really needs CLI rendering for a one-off can pipe it through their own toolchain — Talksmith just won't maintain that path.
