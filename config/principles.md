# Presentation Principles

> Loading semantics, who reads this file, and interpretation rules live in [`${CLAUDE_PLUGIN_ROOT}/schemas/principles.md`](${CLAUDE_PLUGIN_ROOT}/schemas/principles.md). The principles below are the file's data — read when performing the Composer role at every Step 4 drafting milestone.

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

- **Cite by filename.** Every slide's `Sources` references files under `research/corpus/` (e.g. `corpus/transformer-paper.pdf.md`). No floating assertions; no "as I recall…"
- **Never silently drop content.** Anything removed goes to `Cut material` (with a one-line reason) or `Open questions`. The audit trail matters more than tidiness.
- **Image-first when a concept has shape.** If an idea has structure — a flow, a hierarchy, a comparison, a before/after, an architecture, a state machine — capture it as a visual, not as bullets. **Reach for an existing corpus image first** — scan the `Images / diagrams` sections of `research/corpus/*.md` and reference the corpus companion image directly (`![<alt>](research/corpus/<source-stem>/images/<file>.png)`) when one fits. Only when no corpus image fits, **draft an ASCII diagram inside `draft.md`** (tight, labeled, load-bearing — not decoration). Treat the ASCII as the *outline* of the image: faithful enough to review during drafting, and later promoted to a styled SVG by the `diagram-illustrator` during Step 6 (Polish, on `final.md`). Don't wait for a polished image to introduce a visual; reach for the corpus first and draft in ASCII otherwise.
- **Aim for a balanced visual mix — not a rule, a default.** None of the below is mandatory; use judgement per slide. The goal is to avoid wall-of-bullets decks and reach for the lightest format that actually sharpens the point:
  - *Emoji as anchors when they help* — ✅/❌ for trade-offs, ⚠️ for caveats, 🎯 for goals, 📊 for data, 🧠 for insight, 🔁 for loops/iteration. Skip them when they'd feel forced or noisy.
  - *Tables when there are 2+ dimensions* — comparisons, trade-offs, before/after, structured data. A bulleted list is usually fine for simple enumerations.
  - *Reuse images from the corpus knowledge base when relevant* — scan the `Images / diagrams` sections of `research/corpus/*.md` before proposing a new visual. If a corpus image fits, embed it (`![<alt>](research/corpus/<source-stem>/images/<file>.png)`) and cite its source record. If it doesn't fit, don't force it.
  - *ASCII diagrams as the drafting form for any new visual* — flowcharts, sequence/state, bar charts, simple architecture, before/after. Keep them tight (~≤ 60 cols), labeled, and load-bearing. They are the working form during Draft and Review; the `diagram-illustrator` renders them to SVG in Step 6 (Polish), or they're replaced with a corpus image when one becomes available.
  - *An atmospheric aside on a sparse slide* — when a slide carries very little text (a statement, a short lead) and would simply read better with a full-bleed image down one edge, suggest a generated aside: `<!-- generate-image: right | <short high-level idea> -->`. This is **mood, not information** — never for anything the audience must read (that's a diagram or a corpus image). Keep the description a concise one-line brief; the `image-illustrator` enriches it into a full, palette-matched prompt at Step 6, and it degrades to nothing where the session can't generate images. Use sparingly — one per sparse slide, never on a slide that already carries a visual.
- **Avoid walls of bullets.** Three short bullets beats six long ones. Six long bullets means the slide is doing too much; split it.
- **Slide-density budget — hard ceiling, not guideline.** Each slide gets **at most one callout, one table-or-diagram, and one supporting block** (≤5 bullets or one short paragraph). The 5.625-in slide canvas does not accommodate a callout *plus* a table *plus* three or more additional blocks — slides that exceed the budget reliably overflow, with the overflow either clipped at the canvas edge or silently shoved into the speaker-notes pane where the audience cannot see it. When the Composer's Step-4 review finds a slide above budget, it is flagged for split (one concept becomes two slides) rather than shrunk to fit; "one idea per slide" is the natural splitting axis.
- **Title-length budget.** Section H1s ≤ **25 characters**; slide H2s ≤ **40 characters**. Titles beyond these lengths wrap to multiple lines at the title face's adaptive-size floor and push the body start far down the canvas, eating room the content needs. Longer titles are abbreviated, restructured, or moved to the body / section pill. This is a **content-authoring constraint** the Editor and Composer enforce during Step 4, not a rendering hack to patch up after Polish — by the time the renderer runs, the title shape is already over budget. Compound titles (`A: B`) collapse to the right-hand clause; explanatory subordinate clauses move to the slide body.
- **Words should not duplicate the spoken narration.** If the speaker is going to read the slide aloud, the slide is the wrong format — turn it into a visual or speaker note. (Mayer's *redundancy principle* — see citations.)
- **Speaker notes are the talk; the slide is the punctuation.** Write the slide to be glanced at; write the notes to be delivered. The contract is sharper than the aphorism: the speaker-notes pane carries the *prose the slide replaces*. Three diagnostic corollaries that should be enforced at Step-4 review:
  - **Empty notes = nothing to say.** A content slide whose notes pane is blank means the speaker has no line of thought attached to it. Either write the notes or cut the slide; do not ship a glance-able slide with no speech attached.
  - **Notes duplicating the slide = the slide is wrong.** If the notes would read aloud what is already on the slide, the slide is doing the speaker's job (and triggers Mayer's redundancy principle). Convert the slide to a visual / fewer words, or move the content entirely into notes.
  - **Notes longer than ~120 words for a 1–2 minute slide = the slide is two slides.** A notes block the speaker can't deliver in the slide's pacing budget signals an over-packed slide that should be split.

## Visual design — how slides look

- **High signal-to-noise ratio.** Strip anything that doesn't carry information: gratuitous gradients, decorative icons, stock photos that don't illustrate, page numbers in serif italic, dates. Every pixel earns its place. (Tufte's *data-ink ratio*.)
- **Whitespace is content.** Padding around a chart or a sentence makes it easier to absorb. Crowded slides feel anxious.
- **Pick contrast over decoration.** Bold + regular weight on the same line directs the eye better than three colors and a drop shadow.
- **Type hierarchy: title > emphasized phrase > body > footnote.** Three levels max. If you find yourself reaching for a fourth, the slide is too dense.
- **Spatially co-locate words and the visuals they describe.** Don't put a caption on the opposite side of the chart it labels. (Mayer's *spatial contiguity principle*.)

## Pipeline discipline — where each kind of fix belongs

The Talksmith pipeline has stages for a reason: each stage is the cheapest place to fix a class of defect, and the most expensive place to fix the others. A fix applied at the wrong stage either bloats the wrong artifact (a content fix in `images/`, a wording fix in the PPTX renderer) or papers over a problem that will recur on every re-render.

- **Shape defects belong at Step 4 (Draft).** A section that doesn't fit the arc, a slide that carries two ideas, a missing transition, a topic with no thesis hook — these are shape problems. They are cheap to fix in `draft.md` (rewrite a heading, reorder two slides, split or cut) and ruinous to fix later. The Composer's job at each Step-4 milestone is to surface shape defects *before* the section fills in.
- **Wording defects belong at Step 5 (Review).** Rephrasing, tightening, replacing a term, fixing a typo, adjusting tone — these are wording problems. They are cheap to fix as `Presenter feedback` bullets in `draft.md`; the Editor applies them via the `talksmith:feedback-cycle` skill. Wording fixes at Step 7 (renderer) are forbidden — they leak into `final.md` without an audit trail.
- **Rendering defects belong at Step 6 (Polish) or Step 7 (Render).** An ASCII diagram that needs SVG promotion, an image that needs consolidation into `images/`, an emoji that needs an icon swap, a callout color, an overflow — these are rendering problems. They are fixed inside the renderer (diagram-illustrator skill, md-to-deck skill) and never leak back into `draft.md`.
- **The renderer never fixes content.** When the post-render visual review (Step 7) flags a slide because the *title is too long*, the *body has too many bullets*, the *content is two ideas*, or the *speaker notes are empty* — those are Step-4 defects surfacing late. The fix is to re-open `final.md`'s source rules (or `draft.md` if the contract allowed), not to shrink-fit the title at render time or hand-edit the deck. Renderer compensation = next Talk re-introduces the same defect, because the authoring stage never learned.
- **When a Step-4 defect is caught at Step 7.** Stop the iteration budget, surface to the presenter, and offer either: (a) accept the defect for this ship (with a `feedback-backlog.md` entry tagged `late-catch`), or (b) re-open Step 4/5 to fix at source. Do not silently hack the render.

## Composer reviews — what "challenge" means

The Composer is the only role licensed to push back. *Challenge* doesn't mean "tone-police prose" and it doesn't mean "approve everything that looks plausible." It means producing a punch-list of specific, actionable defects scored by severity, against the thesis, the audience, the corpus, the principles, and the learnings. Each round must distinguish three severities:

- **`[blocker]`** — the slide / section is structurally broken and the deck *cannot ship as-is*. Examples: thesis is internally contradictory; section has no goal; slide makes a claim the corpus contradicts; section is unreachable from the previous section's arc; a key audience question is never addressed; the agenda promises a section the deck doesn't deliver. Composer must list these explicitly. The orchestrator does not advance to the next Step-4 milestone until every `[blocker]` is resolved (perform Editor to fix) or explicitly waived by the presenter on the record.
- **`[major]`** — the slide / section *will ship and embarrass the speaker* if unfixed. Examples: a claim is unsourced; a section's slides are out of pedagogical order; a slide is two ideas; a callout uses the wrong variant for its content; the audience can't follow the jump from slide N to slide N+1; a quantified result is stated without the comparison baseline. Surfaced to the presenter with the option to defer to Step 5; never silently absorbed.
- **`[minor]`** — the slide / section *works but could be sharper*. Examples: a heading could be one word shorter; a card body has a passive-voice construction; an image is fine but a corpus image would be better; a section name and its subtitle restate each other. Collected silently across the section reviews and surfaced as a single batched list at the final `scope=full` pass — do not interrupt drafting with minor items.

Counter-rules — what a Composer review is **not**:

- Not a stylistic preference engine. "I would have phrased it differently" is not a defect; "the phrasing contradicts the thesis" is.
- Not exhaustive. A review that flags 47 items is not more rigorous than one that flags 7 well-chosen ones — it's noise. Pick the load-bearing defects; trust the presenter for taste.
- Not a sycophancy carrier. "Looks great overall, here are some thoughts" is not a review opening. Lead with the worst defect.
- Not a rewrite. The Composer punches list, the Editor writes. A Composer that drafts replacement prose has stopped reviewing and started editing — that's a role boundary violation.

The Composer reads `principles.md` + `learnings.md` + the slice of the corpus relevant to the section under review on entry, and discards them on exit. Do not carry these in context outside the review pass.

## Feedback discipline — how the deck improves

- **Feedback is an audit trail.** Review rounds annotate `draft.md` in place with `[open]` → `[closed]` bullets that are never deleted. `draft.md` retains the full log forever; Step 6 strips it from the derived `final.md`. You can always trace why a slide looks the way it does by opening `draft.md`.
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
