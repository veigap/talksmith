# Presentation Principles

> Loading semantics, who reads this file, and interpretation rules live in [`.claude/schemas/principles.md`](../.claude/schemas/principles.md). The principles below are the file's data — read when performing the Composer role at every Step 4 drafting milestone.

---

## Foundations — what a presentation is for

- **A presentation is not a document.** Slides exist to support a talk, not to substitute for one. If a slide reads as a self-contained essay, it should probably be a doc instead. Cut prose; keep what the speaker can't say but needs to show.
- **The audience is the hero.** Every slide should serve them — not the presenter's ego, the source material's completeness, or the deck's symmetry. Ask "what does the audience need to walk away with?" before "what do I want to say?"
- **One idea per slide.** If a slide makes two points, split it. If it makes none, cut it. Decks that respect this rule are slower to assemble and faster to deliver.
- **Thesis-first, audience-aware.** Every section and every slide is challenged against a one-sentence thesis and a stated audience. Slides that don't serve either are moved to `Cut material`, never silently deleted.

## Structure — how the deck is organized

- **Narrative arc.** A deck is a story: setup → conflict → resolution. Open with a concrete hook (a problem, a thought experiment, a counter-intuitive fact). Close with a clear takeaway and call to action. Avoid "agenda → topic 1 → topic 2 → … → thanks" structures with no tension.
- **Sections are signposts.** Each Section gets a dedicated divider slide with a one-line goal. Sections of more than ~8 slides should probably split.
- **Pacing roughly 1–2 minutes per content slide** for live talks. A 30-minute talk has room for ~15–25 content slides; pack more in and you'll either rush or run over. Note this is a heuristic — dense reference slides and quick visual punctuations both bend it.
- **The first slide is a hook, not a title.** A title slide is fine, but the *first slide audiences engage with* should give them a reason to lean in.
- **The last slide is a takeaway, not "Thank you."** Leave a closing image, a key question, or a call to action — something the audience can act on or remember.

## Content — what goes on each slide

- **Cite by filename.** Every slide's `Sources` references files under `knowledge/compile/` (e.g. `compile/transformer-paper.md`). No floating assertions; no "as I recall…"
- **Never silently drop content.** Anything removed goes to `Cut material` (with a one-line reason) or `Open questions`. The audit trail matters more than tidiness.
- **Image-first when a concept has shape.** If an idea has structure — a flow, a hierarchy, a comparison, a before/after, an architecture, a state machine — capture it as a visual, not as bullets. The **first draft of any such visual is an ASCII diagram inside `master.md`** (tight, labeled, load-bearing — not decoration). Treat the ASCII as the *outline* of the image: faithful enough to review during drafting, and later promoted to a styled SVG by the `illustrator` during Step 6 (Polish) — or reused from `knowledge/compile/` if a compiled figure fits. Don't wait for a polished image to introduce a visual; draft it in ASCII first.
- **Aim for a balanced visual mix — not a rule, a default.** None of the below is mandatory; use judgement per slide. The goal is to avoid wall-of-bullets decks and reach for the lightest format that actually sharpens the point:
  - *Emoji as anchors when they help* — ✅/❌ for trade-offs, ⚠️ for caveats, 🎯 for goals, 📊 for data, 🧠 for insight, 🔁 for loops/iteration. Skip them when they'd feel forced or noisy.
  - *Tables when there are 2+ dimensions* — comparisons, trade-offs, before/after, structured data. A bulleted list is usually fine for simple enumerations.
  - *Reuse images from the compiled knowledge base when relevant* — scan the `Images / diagrams` sections of `knowledge/compile/*.md` before proposing a new visual. If a compiled figure fits, embed it (`![<alt>](<path>)`) and cite its source. If it doesn't fit, don't force it.
  - *ASCII diagrams as the drafting form for any new visual* — flowcharts, sequence/state, bar charts, simple architecture, before/after. Keep them tight (~≤ 60 cols), labeled, and load-bearing. They are the working form during Draft and Review; the `illustrator` renders them to SVG in Step 6 (Polish), or they're replaced with a compiled figure when one becomes available.
- **Avoid walls of bullets.** Three short bullets beats six long ones. Six long bullets means the slide is doing too much; split it.
- **Words should not duplicate the spoken narration.** If the speaker is going to read the slide aloud, the slide is the wrong format — turn it into a visual or speaker note. (Mayer's *redundancy principle* — see citations.)
- **Speaker notes are the talk; the slide is the punctuation.** Write the slide to be glanced at; write the notes to be delivered.

## Visual design — how slides look

- **High signal-to-noise ratio.** Strip anything that doesn't carry information: gratuitous gradients, decorative icons, stock photos that don't illustrate, page numbers in serif italic, dates. Every pixel earns its place. (Tufte's *data-ink ratio*.)
- **Whitespace is content.** Padding around a chart or a sentence makes it easier to absorb. Crowded slides feel anxious.
- **Pick contrast over decoration.** Bold + regular weight on the same line directs the eye better than three colors and a drop shadow.
- **Type hierarchy: title > emphasized phrase > body > footnote.** Three levels max. If you find yourself reaching for a fourth, the slide is too dense.
- **Spatially co-locate words and the visuals they describe.** Don't put a caption on the opposite side of the chart it labels. (Mayer's *spatial contiguity principle*.)

## Feedback discipline — how the deck improves

- **Feedback is an audit trail.** Review rounds annotate `master.md` in place with `[open]` → `[closed]` bullets that are never deleted. You can always trace why a slide looks the way it does.
- **Decisions are choices, not free-form prompts.** When the agent needs the presenter to decide between framings, orderings, or cut/keep, it proposes 2–4 concrete options rather than asking open-ended questions. Faster, less decision fatigue, easier to redirect.
- **The presenter signs off explicitly.** "Looks good", "ready", "move to review" closes a phase. Until then, the agent keeps drafting and asking targeted clarifications.
- **Patterns become principles.** When the same kind of feedback recurs 3+ times across talks, promote it from [`feedback-backlog.md`](feedback-backlog.md) to [`learnings.md`](learnings.md) so it informs future drafts automatically.

## Process — how the agent collaborates

- **Explore first, structure second.** The agent works from sources the presenter has actually engaged with (papers, chat exports, notes). It will not invent content out of thin air.
- **Lossless before lossy.** Sources are restructured, not summarized. Contradictions and abandoned threads from the presenter's exploration are surfaced, not silently resolved.
- **Roles are explicit.** Librarian preserves, Composer challenges, Editor records. None of them are "yes-man assistants."
- **Resume, don't restart.** `memory.md` captures progress after every step so the presenter can put a talk down for weeks and pick it up exactly where they left off.
- **Drive, don't wait.** During Step 4 (Draft), the agent asks the next useful question rather than letting the presenter stall.

---

## Citations and influences

These principles draw on:

- **Mayer, R. E.** *Multimedia Learning* (2nd ed., 2009) and *Cambridge Handbook of Multimedia Learning*. Empirical research on cognitive load, the redundancy/coherence/spatial-contiguity/signaling principles, and how text + image combinations affect retention.
- **Sweller, J.** Cognitive load theory (1988+). Working-memory constraints on instructional design — the basis for "one idea per slide" and "avoid splitting attention."
- **Tufte, E. R.** *The Visual Display of Quantitative Information* (2001) and *Beautiful Evidence* (2006). Data-ink ratio, chartjunk, small multiples, sparklines.
- **Reynolds, G.** *Presentation Zen* (2008+). Simplicity, image-over-text, whitespace, signal-to-noise.
- **Duarte, N.** *Slide:ology* (2008) and *Resonate* (2010). Audience-as-hero, narrative arc (story structure adapted to talks), contrast as a design tool.
- **Atkinson, C.** *Beyond Bullet Points* (2011). Headline-driven slides; one claim per slide.
- **Miller, G. A.** "The Magical Number Seven, Plus or Minus Two" (1956) — often misapplied to "items on a slide," but the underlying point (working memory is small) is the load-bearing one.

These references are pointers, not gospel. When the audience, topic, or format makes a principle inappropriate, override it. Just record *why* in the relevant `Presenter feedback` field so it shows up in the audit trail and feeds future learnings.
