---
name: talksmith:md-to-pptx
description: Convert a Talk's cleaned `final.md` into a PowerPoint (.pptx) deck by delegating all .pptx authoring to Anthropic's official `pptx` skill at `skill://antropic-skills:/pptx`. **Cowork-only** — requires that skill in the session registry. Optional Step 8 of the Presenter Agent workflow, invoked after Step 6 (Polish) has rendered SVGs and produced `final.md`. Consumes images already on disk under `talks/<Talk>/images/`; does not author the deck itself. **Starts from [`config/base-template.pptx`](../../../config/base-template.pptx)** (the mandatory working foundation — cover + agenda + 10 layout-reference slides) and follows the visual spec in [`config/pptx-prompt.md`](../../../config/pptx-prompt.md). Output: `talks/<Talk>/output/final.pptx`.
---

# md-to-pptx — Render `final.md` to PowerPoint

**This skill is a thin orchestrator. All `.pptx` authoring must be delegated to Anthropic's official `pptx` skill at [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx).** Do not author the deck with any other tool — no `python-pptx`, no `pandoc`, no Marp, no hand-written XML. Pre-process `final.md`, then invoke `skill://antropic-skills:/pptx` with the intermediate file, the image paths, **the base template, and the visual spec**. If that skill is not in the current session's registry (i.e. the session is not running inside Claude Cowork), stop and tell the presenter to run this step inside Cowork. No CLI fallback — see *Why Cowork-only* at the bottom.

**The base template is mandatory and non-negotiable.** Every render **starts from a working copy of [`config/base-template.pptx`](../../../config/base-template.pptx)**, not from a blank deck. This file is not a "style reference" — it is the literal starting deck. It already contains the correct theme, fonts, colors, master, the cover slide, the agenda slide, and 10 layout-reference slides demonstrating every recurring pattern. The renderer **substitutes placeholders** on the cover + agenda, **deletes the layout-reference zone**, and **inserts generated content slides** built from the recipes in [`config/pptx-prompt.md`](../../../config/pptx-prompt.md). Decks rendered from scratch — even if they "look similar" — are a render failure. See [`pptx-prompt.md`](../../../config/pptx-prompt.md) §18 for the slide-by-slide treatment, and §15 for layout selection rules.

**Single responsibility.** This skill **only** prepares the inputs and invokes `skill://antropic-skills:/pptx`. ASCII → SVG conversion is the Illustrator role's job, performed in Step 6 (Polish) before this skill ever runs. `final.md` arrives already cleaned (image refs inlined, `Presenter feedback` stripped) and every referenced image already lives under `talks/<Talk>/images/`.

**Reads `final.md`, never `draft.md`.** The working file (`draft.md`) still carries `Presenter feedback` blocks and raw ASCII fences and is not a valid PPTX input. The skill's CLI takes the path to `final.md` as a positional argument; passing `draft.md` produces malformed output (Presenter feedback bullets leaking into slide bodies, ASCII fences rendered as code blocks).

## When to use

After Step 6 (Polish) completes and the presenter picks **Render to PowerPoint** from the terminal branch. Optional — many presenters stop at the outline.

## Prerequisites

| Prereq | What to check | If missing |
|---|---|---|
| [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) in session registry | Skill list includes the `pptx` entry | Stop. Tell presenter to run this step inside Cowork. |
| Active `Talk` path | Passed in by orchestrator | Stop and ask. |
| Cleaned `final.md` | Exists; no `Presenter feedback` fields; ASCII blocks replaced by `![...](images/...)` refs | Stop. Polish hasn't run — return to Step 6. |
| Pre-rendered local images | `talks/<Talk>/images/<file>` exists on disk for every **local** image ref in `final.md` (i.e. every `![...](images/...)` reference). Remote URLs (`http://`, `https://`) are checked separately — see below. | Stop. Dispatch `illustrator` to render missing SVGs, or stop and ask the presenter to drop a missing non-SVG asset into `images/`. |
| Remote image refs handled | `final.md` contains no `![...](http(s)://...)` references — they survived Step 6 Polish unchanged, but `skill://antropic-skills:/pptx`'s behavior on remote URLs is implementation-defined and not guaranteed. | Stop and ask the presenter to either (a) download the asset into `images/` and rewrite the ref to `images/<file>`, or (b) explicitly accept the risk that the slide may ship without that image. Never silently ship a deck where a remote image was dropped. |
| Base template | [`config/base-template.pptx`](../../../config/base-template.pptx) exists (or the presenter-supplied override path). This is the mandatory starting deck — not a style reference. | Stop and ask. |
| Visual spec | [`config/pptx-prompt.md`](../../../config/pptx-prompt.md) exists. Sections referenced during render: §4 (cover), §5 (agenda + section dividers), §6 (section pill), §7 (cards), §8 (callouts), §9 (code), §13 (layout taxonomy), §15 (emit-rules), §17 (icon library), §18 (base-template walkthrough). | Stop and ask — the spec is the rendering contract. |
| Icon library | [`config/base-template.pptx`](../../../config/base-template.pptx) `ppt/media/icon-*.svg` (15 branded line-art icons in `#DA1B2E`) — see [`pptx-prompt.md`](../../../config/pptx-prompt.md) §17 for the catalog. | Stop and ask — without the icons the no-emoji rule (see *Rules*) cannot be enforced. |

## Inputs

- **Active `Talk` path** — absolute.
- **`config/profile.md` content** — pass the global presenter profile (the cover placeholders `{{PRESENTATION_TITLE}}` and `{{PRESENTER}}` substitute from `Subject` and `Presenter`; agenda placeholder language follows `Presentation language`).
- **Base template** — defaults to [`config/base-template.pptx`](../../../config/base-template.pptx). Override only if the presenter explicitly passes a different path. The legacy [`config/template.pptx`](../../../config/template.pptx) (53-slide reference deck) is **not** a valid override — it is the source the spec was distilled from, not a rendering input.
- **Visual spec** — [`config/pptx-prompt.md`](../../../config/pptx-prompt.md). The renderer treats it as the rendering contract for any slide that isn't a direct copy of a base-template slide.
- **Operating guide for the renderer** — [`pptx-prompt.md`](../../../config/pptx-prompt.md) §19. Self-contained: required reading order (§19.2), 7-stage workflow (§19.3), output contract + OOXML invariants (§19.4), verification (§19.5), consolidated anti-patterns (§19.6), and a navigation index (§19.7). SKILL.md is a thin orchestrator; **§19 is the operating manual**. Pass `pptx-prompt.md` verbatim to the native skill (or rendering subagent) as instructions context.

## Output

```
talks/<Talk>/
├── draft.md                 # working file (Steps 1–5) — read-only here
├── final.md                 # source for this skill (cleaned by Polish)
├── images/                  # populated by illustrator + editor (Step 6)
│   ├── s1-1.svg
│   └── ...
└── output/
    ├── final.pptx               # this skill writes via skill://antropic-skills:/pptx
    ├── final.intermediate.md    # transient pre-processed file (produced by convert.py)
    └── .critique/               # critique-only slide previews (git-ignored)
        ├── slide-01.png
        ├── slide-02.png
        └── ...
```

## Process

1. Verify all prerequisites (table above). Stop on any failure.
2. **Pre-process `final.md` with [`convert.py`](convert.py)** — a CLI-safe, dependency-free Python script that emits the Markdown shape `skill://antropic-skills:/pptx` consumes:

   ```bash
   python3 .claude/skills/md-to-pptx/convert.py \
     talks/<Talk>/final.md \
     -o talks/<Talk>/output/final.intermediate.md
   ```

   The script performs these transformations (specified in its docstring; see [`convert.py`](convert.py) for the canonical contract):
   - Drops YAML frontmatter, HTML comments (including `<!-- ascii-source: ... -->` blocks), and the sections `# Thesis`, `# Open questions`, `# Cut material`.
   - Strips the numeric / legacy prefix from H1 / H2 headings: `# 1. Foundations` → `# Foundations`, `## 2. Why X` → `## Why X`. Legacy forms `# Section N:` / `## Slide N:` / `# N —` / `## N —` accepted.
   - For each H2 slide, processes its H3 fields: drops the `### Content` label (keeps body), drops `### Sources` entirely (presenter-internal), renames `### Speaker notes` → `### Notes` (keeps body), defensively drops any lingering `### Presenter feedback`.
   - Preserves `![alt](images/...)` image refs verbatim. Preserves `---` rules.
   - Collapses runs of 3+ blank lines to 1.

   Output Markdown shape — one H1 per section divider, one H2 per content slide, `### Notes` for speaker notes, inline image refs. This is what `skill://antropic-skills:/pptx` receives.

3. **Render** by invoking [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx). The invocation follows the **base-template workflow** described in [`pptx-prompt.md`](../../../config/pptx-prompt.md) §18.2 — the native skill is the executor, this skill is the recipe-bearer. Pass:
   - the intermediate file at `output/final.intermediate.md`,
   - the image paths under `talks/<Talk>/images/` (the intermediate already references them — resolved relative to the intermediate's parent),
   - the **base template** at [`config/base-template.pptx`](../../../config/base-template.pptx) (or explicit override) — opened as a **working copy**, not as a theme reference,
   - the **icon library** rooted at the base template's `ppt/media/icon-*.svg` (15 branded line-art SVGs, see [`pptx-prompt.md`](../../../config/pptx-prompt.md) §17),
   - the **visual spec** [`config/pptx-prompt.md`](../../../config/pptx-prompt.md) (the layout recipes the skill emits against).

   The invocation follows the **7-stage workflow in [`pptx-prompt.md`](../../../config/pptx-prompt.md) §19.3** verbatim — open base-template as working copy → cover substitution (§4) → agenda substitution (§5) → discard slides 3–13 → build content slides (§15 + §6–§9 + §13) → section dividers (§5.6) → backgrounds (§1) → speaker notes. All substantive rules (placeholder edge cases, slide-count formula, OOXML invariants, callout pink-vs-blue, no native tables, emoji→icon swap, palette, fonts, corner radius) live in [`pptx-prompt.md`](../../../config/pptx-prompt.md) and are **not duplicated here**. The skill's sole §19 obligation is to **pass the spec to the native renderer** and verify the output against §19.4 + §19.5. When this skill and the spec disagree, the spec wins.

   Acceptance bar: open the rendered `final.pptx` next to `base-template.pptx` — slides 1–2 must be pixel-equivalent modulo placeholder text. Author-from-scratch with the native skill's default theme = render failure.
4. Verify `talks/<Talk>/output/final.pptx` exists and is non-empty.
5. **Verify visual fidelity.** Spot-check that the rendered deck matches the reference template's look (theme, fonts, layouts). If it doesn't, treat as a failure — see *Failure modes*.
6. **Render per-slide critique PNGs.** Rasterize every slide to `talks/<Talk>/output/.critique/slide-NN.png` (zero-padded 2-digit slide number, `01` … `NN`). These PNGs are critique-only — not referenced from `final.pptx`, not part of the deliverable — and exist so the orchestrator's post-render visual review can perform visual analysis on actual pixels rather than slide-XML inspection (see [CLAUDE.md](../../../CLAUDE.md) → *Step 8 — Post-render visual review*).

   Path priority (use the first that works):

   1. If [`skill://antropic-skills:/pptx`](skill://antropic-skills:/pptx) exposes a slide-to-image render endpoint, call it. The native skill is the most faithful source — it knows the deck's true layout post-render.
   2. Fallback: `libreoffice --headless --convert-to pdf <output_dir> talks/<Talk>/output/final.pptx`, then `pdftoppm -r 150 -png talks/<Talk>/output/final.pdf talks/<Talk>/output/.critique/slide` to produce one PNG per slide. Rename / pad to `slide-NN.png`. Requires `libreoffice` (`brew install --cask libreoffice`) and `poppler` (`brew install poppler`); document the dependency.

   If both paths fail, the deck is still valid — report `slide_previews: failed: <reason>` and continue. The orchestrator will surface this as `unresolved: slide_previews_failed` for the post-render review (visual critique can't run without pixels), but the `.pptx` itself is unaffected.

7. Report: slide count, image references resolved, `slide_previews: <count|failed>`, any warnings surfaced by `skill://antropic-skills:/pptx`.

The **post-render visual review** — the 10-point check for type hierarchy / overflow / bullet density / balance / focal point / theme consistency / etc. — is performed by the **orchestrator** after this skill returns, not by the skill itself. The orchestrator reads each `slide-NN.png` via the `Read` tool (visual analysis on rasterized pixels — XML inspection is forbidden) and dispatches targeted edits back to the skill (capped at 2 iterations beyond the initial render). See [CLAUDE.md](../../../CLAUDE.md) → *Step 8 — Render PPTX* → *Post-render visual review* for the full checklist. The skill stays focused on rendering; the orchestrator stays focused on judgement.

## Rules

This skill is an orchestrator. Visual rules (palette, fonts, icons, emoji swap, callouts, tables, corner radius, agenda count, layout selection) live in [`pptx-prompt.md`](../../../config/pptx-prompt.md) — the consolidated anti-pattern list is §19.6 and the renderer must enforce it. The rules below are skill-local — they govern IO and orchestration, not visual style.

- **The base template is mandatory, not advisory.** Every render **starts from a working copy of [`config/base-template.pptx`](../../../config/base-template.pptx)** (or the explicit override) per [`pptx-prompt.md`](../../../config/pptx-prompt.md) §19.3. Decks authored from scratch with the native skill's default theme are a render failure even if the file is otherwise correct.
- **The spec is the contract.** Pass [`pptx-prompt.md`](../../../config/pptx-prompt.md) verbatim to the native renderer as instructions context. If the native skill ignores it, that's a render failure — surface and rerun, do not paper over with post-hoc edits.
- **Never modify `final.md` during render.** All transformation happens in memory or in `output/final.intermediate.md`. The cleaned `final.md` from Polish stays the source of truth for the render.
- **Never read or modify `draft.md`.** It is the working file from Steps 1–5 and is read-only from Step 6 onward.
- **Never re-render SVGs.** If an image ref points at a missing SVG, stop and tell the orchestrator to perform the Illustrator role rather than improvising.
- **Speaker notes go into the notes pane**, never on the slide body.

## Failure modes to surface

Operational / IO failures only. **Visual-spec violations** (emoji survived, non-template color/font, native `<a:tbl>` emitted, wrong callout variant, missing section pill, mixed icon style, flat `#F2F2F2` background, non-5760 corner radius, base-template slides 3–13 leaking through) are catalogued in [`pptx-prompt.md`](../../../config/pptx-prompt.md) §19.6; surface any §19.6 violation as a render failure and rerun.

- Native `pptx` skill not available → stop, instruct presenter to run inside Cowork.
- Base template missing or unreadable → stop and ask.
- Base template was loaded but not honored — slides 1–2 in the rendered deck are not pixel-equivalent to base-template slides 1–2 (placeholders aside), or slides 3–13 leaked into the output, or theme/fonts/layouts don't match → surface loudly; offer to rerun.
- **Agenda capacity exceeded.** `final.md` has N H1 sections; the agenda emits one row per section per §5.3 / §5.5 (no fixed count). N ≤ 8 fits cleanly; for 9 ≤ N ≤ 10 emit with a tightness warning; for N > 10 stop and ask the presenter — the agenda chrome is out of vertical room and an alternate layout is needed. Never pad the agenda to 7 rows with blanks, and never truncate sections to fit.
- **OOXML integrity broken** per §19.4 invariants (dangling overrides / rels, `[Content_Types].xml` not first in zip, `sldIdLst` / `sldLayoutIdLst` without matching rels). Most often after Stage-3 deletion. Stop, repair, re-verify before declaring success.
- `final.md` not yet produced (Step 6 Polish hasn't run) or still contains `Presenter feedback` fields or unrendered ASCII fenced blocks → stop; return to Step 6.
- The path passed in points at `draft.md` instead of `final.md` → stop and ask. `draft.md` is never a valid input to this skill.
- An image ref points at a missing SVG → stop; orchestrator performs Illustrator role to render it.
- A Section has zero Slides.
- Native skill exits non-zero → surface its error message verbatim in the final report.
- **H1-as-content-slide regression.** `convert.py` only strips the numeric prefix and passes H1 through — the H1→divider semantic is the native skill's job. Spot-check after render: every numbered section in `final.md` must produce exactly one divider slide (per §5.6). H1 rendered as a content slide = contract violation, do not ship.

## Why Cowork-only

Earlier iterations tried three CLI rendering paths:

| Attempt | Outcome |
|---|---|
| Hand-rolled `python-pptx` script | Brittle parsing of `final.md`, layout-by-layout reimplementation of theme. Abandoned. |
| Marp CLI | Required migrating `final.md` to Marp syntax — a structural change to the source of truth. Reverted. |
| `pandoc --reference-doc=…` | Template-layout name mismatch (pandoc expects `Title Slide`, `Section Header`, etc. — our template doesn't have them), so theme fell back to pandoc's defaults. Section dividers also split into two slides because of body content between H1 and the first H2. Tables sometimes dropped silently. Removed. |

Each path produced a deck with subtle correctness or fidelity issues. The native `pptx` skill is the only tested-good rendering path. `final.md` is plain Markdown, so a presenter who really needs CLI rendering for a one-off can pipe it through their own toolchain — Talksmith just won't maintain that path.
