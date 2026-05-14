# Feedback backlog

Cross-presentation log of every `Presenter feedback` bullet captured during Step 5 (Review). The Scribe appends to this file whenever a feedback bullet is closed in a Talk's `master.md`. The orchestrator scans this file at presentation completion to detect repeated patterns and promote them to [`learnings.md`](learnings.md).

> **Do not edit by hand during a Review round.** Add feedback to the Talk's `master.md` `Presenter feedback` fields; the Scribe mirrors closed bullets here.

## Format

One entry per closed feedback bullet, newest at the bottom:

```
- talk: <talk-folder>
  date: YYYY-MM-DD
  location: <Thesis | Agenda | Section "<name>" | Slide "<title>">
  feedback: "<verbatim presenter wording>"
  resolution: <one-line summary of what changed in master.md>
  tags: [<short kebab-case tags — see Tagging below>]
```

## Tagging

Tags are how patterns surface. Reuse existing tags from prior entries before inventing new ones. Common axes:

- **Surface**: `thesis`, `agenda`, `section-goal`, `slide-content`, `speaker-notes`, `sources`, `cut-material`.
- **Concern**: `too-dense`, `too-academic`, `too-vague`, `off-thesis`, `wrong-audience`, `missing-evidence`, `bad-order`, `redundant`, `tone`, `visual`, `length`.
- **Action**: `rewrite`, `reorder`, `cut`, `merge`, `split`, `add-source`, `add-visual`.

## Pattern detection

At presentation completion (when the presenter declares `master.md` final, before Step 8), the orchestrator:

1. Scans the entries added during this Talk and combines them with prior backlog history.
2. Groups by tag and by recurring resolution shape.
3. For any pattern that has appeared **3+ times across all Talks**, prompts the presenter via `AskUserQuestion` whether to promote it to [`learnings.md`](learnings.md) as a durable rule.
4. For each promoted pattern, **moves** the contributing entries from this file to [`feedback-processed.md`](feedback-processed.md) — adding `promoted_to` and `promoted_at` fields — so this backlog stays lean and only holds patterns that haven't yet crossed the promotion threshold.

## Entries

<!-- Scribe appends entries below this line. -->

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🎬 Title" (Section 1, Slide 1)
  feedback: "Split this slide into 2."
  resolution: Split old Slide 1.1 into Slide 1 "🎬 Title" (title/subtitle/thesis hook) and Slide 2 "🗺️ Roadmap" (three-section overview + scope); renumbered Section 1 slides and changed Architecture emoji 🗺️ → 🏛️ to avoid clash.
  tags: [slide-content, too-dense, split]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🗺️ Roadmap" (Section 1, Slide 2)
  feedback: "Expland the roadmap with more details and charts."
  resolution: Expanded Roadmap slide with a 3-section journey table (slides, time budget, core question), an ASCII flow chart Foundations → Failures → Variants → Takeaways, and an In/Out-of-scope table; kept Sources and Speaker notes unchanged.
  tags: [slide-content, too-vague, add-visual]

- talk: gan-networks
  date: 2026-05-12
  location: Section "Conclusions"
  feedback: "Last slide should be a takeaway, not Q&A — reorder so the one-sentence takeaway is the final visible slide."
  resolution: Swapped Conclusions slide order — new Slide 1 is Q&A + further-study pointers, new Slide 2 is Key takeaways with the one-sentence memorable line promoted to the final visible line.
  tags: [slide-content, bad-order, reorder]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "⚔️ The minimax game" (Section 1, Slide 6)
  feedback: "Pandoc's pptx writer can't render LaTeX reliably — replace the inline equation with a labeled visual, and move the non-saturating loss aside to speaker notes."
  resolution: Replaced the `$$\min_G \max_D ...$$` LaTeX block with a plain-text labeled rendering inside a fenced code block (picked up by render_pandoc.py as a chart-style SVG); moved the non-saturating-loss bullet from Content to Speaker notes.
  tags: [slide-content, visual, rewrite]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🏛️ Architecture overview (diagram)" (Section 1, Slide 5)
  feedback: "The slide says 'Show gan_architecture_overview.svg' but never actually embeds the image — embed it."
  resolution: Extracted gan_architecture_overview.svg from knowledge/llm-chats/gans_explanation.zip to knowledge/compile/assets/, replaced the "Show ..." stage direction with a real Markdown image embed, updated Sources.
  tags: [slide-content, visual, add-visual]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🔁 The training loop (diagram)" (Section 1, Slide 7)
  feedback: "Same as the architecture slide — embed gan_training_loop.svg instead of telling the reader to imagine it."
  resolution: Extracted gan_training_loop.svg to knowledge/compile/assets/, replaced the "Show ..." stage direction with a real Markdown image embed, updated Sources.
  tags: [slide-content, visual, add-visual]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🔄 Why gradients flow the way they do" (Section 1, Slide 8)
  feedback: "Trickiest concept in the lecture — split into two slides so each carries one idea."
  resolution: Split into Slide 1.8 "🔄 Forward pass — who's in the loop when" (the 4×4 table only) and new Slide 1.9 "💡 Consequence — D must be differentiable"; renumbered Section 1 to 9 slides and updated the Roadmap journey table accordingly.
  tags: [slide-content, too-dense, split]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "😰 GANs are notoriously hard to train" (Section 2, Slide 1)
  feedback: "The 'Why this section matters' line is meta-justification — push it to speaker notes."
  resolution: Removed the "🛠️ Why this section matters: the variants in Section 3 are largely engineered fixes..." bullet from Content and appended it to Speaker notes.
  tags: [slide-content, redundant, cut]

- talk: gan-networks
  date: 2026-05-12
  location: Section "💥 Why GANs are hard — three failure modes and the Nash equilibrium tension"
  feedback: "Bullets like '**Why it happens:** ...' are full sentences the speaker will narrate — Mayer's redundancy principle. Tighten to noun phrases; push the why into speaker notes."
  resolution: Across Slides 2.2/2.3/2.4 shortened each `**Why it happens:**` line to a 3–6 word noun phrase (2.2 "rewarded for fooling D, not for coverage"; 2.3 "`log(1 − D(G(z)))` saturates near 0"; 2.4 "no convergence guarantee in non-convex minimax") and moved the original full-sentence explanations to each slide's Speaker notes.
  tags: [slide-content, redundant, rewrite]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🤔 What is a GAN?" (Section 1, Slide 3)
  feedback: "Same redundancy concern — the italic 'the problem they solve' quote is a full sentence that duplicates narration."
  resolution: Removed the italic full-sentence quote from Content and appended it verbatim to Speaker notes as the planned spoken framing.
  tags: [slide-content, redundant, cut]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🗺️ Roadmap" (Section 1, Slide 2)
  feedback: "Four ideas on one slide (journey table, flow chart, scope table, interrupt note) — fold the scope table into speaker notes; you'll say it once."
  resolution: Removed the In/Out-of-scope table from Content and appended it (as the same table) to Speaker notes with the spoken framing "We will explicitly NOT cover code or hyperparameter tuning — flag this here, move on." Kept the journey table, ASCII flow, and interrupt note on the slide.
  tags: [slide-content, too-dense, cut]

- talk: gan-networks
  date: 2026-05-12
  location: Section "🧬 Variants and applications — DCGAN to StyleGAN, and the diffusion handover"
  feedback: "Five variants in three slides risks name-drop overload — pre-commit to staying at the 'what problem does each solve' depth, and flag where to expand only if asked."
  resolution: Added a one-line presenter-discipline note to Section 3's Goal — "**Depth contract:** stay at 'what problem each variant solves' — no architecture deep-dive unless a student asks." No variant slide cut.
  tags: [section-goal, too-dense, rewrite]

- talk: gan-networks
  date: 2026-05-12
  location: Slide "🎬 Title" (Section 1, Slide 1)
  feedback: "The first slide audiences engage with should be a hook, not a title — add a one-line counter-intuitive hook to the title slide so the lecture opens on tension."
  resolution: Added an italicized third line under title/subtitle, separated by a horizontal rule: *"The math is beautiful. The training is brutal. That tension is the whole field."* Kept existing title, subtitle, and thesis hook.
  tags: [slide-content, tone, rewrite]
