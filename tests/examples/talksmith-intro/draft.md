---
presentation: Talksmith — build a talk from what you already know
class: "Intro — what it is, how to install it, how to use it"
research: research/corpus/
description: Slides are grouped into Sections. Each Section contains one or more Slides.
presenter: Paulo Veiga (@veigap)
audience: People who prepare talks, lectures, or training on the same subject repeatedly — teachers, workshop leads, technical presenters. Comfortable with Git and Claude Code; new to Talksmith.
duration: 40 min + 10 min Q&A
date: 2026-07-14
---

# Thesis

**Claim:** Talksmith turns the recurring work of preparing a talk into a durable, traceable knowledge base — so each class compounds on the last instead of starting from a blank page.

**Why it matters:** Most presentation tools optimize the *deck*, which is thrown away after one delivery. The expensive, reusable asset is the *understanding* behind it — the sources, the framing, the decisions. Talksmith treats that asset as the product and the slides as a disposable projection of it. And because the outline is plain Markdown, even the visuals are generated *from your content*: you sketch a diagram in ASCII and Talksmith renders it to a styled SVG — no drawing tool, no fiddling.

**Presenter feedback:**

- [closed] 2026-07-09 — "Lead with the pain, not the architecture — people don't care that it's five agents yet."
  Resolution: Reframed the claim around 'starting from a blank page' and moved the agent breakdown to the last section.
- [closed] 2026-07-10 — "Make it explicit that this is NOT a slide generator, up front."
  Resolution: Added slide 1.2 contrasting Talksmith with deck generators; echoed the line in the thesis.
- [closed] 2026-07-14 — "Say early that diagrams are auto-generated from the content — it's a wow moment."
  Resolution: Added it to 'Why it matters' and gave it its own slide (2.5), rendered from the ASCII in this draft.

---

# Agenda

**Narrative arc:** Open on the problem everyone recognizes — rebuilding a talk from scratch every time. Reframe the deck as a byproduct of a knowledge base. Walk the eight-step workflow the way they'll actually experience it, then lift the hood on the five agents that make it work. Only then show how to get started — installed and running in three commands — and close on the compounding payoff across a semester.

**Sections (in delivery order):**

- 1. What problems are we addressing?
- 2. What is Talksmith?
- 3. The workflow in practice
- 4. Behind the scenes
- 5. Getting started
- 6. Conclusions

**Presenter feedback:**

- [closed] 2026-07-11 — "Put 'Getting started' before the deep workflow so people can follow along live."
  Resolution: Swapped order — install now precedes the workflow walk-through.
- [closed] 2026-07-14 — "Actually, move Getting started to the very end — sell the value first, then show how to start."
  Resolution: Reordered so Getting started is the last content section (after Behind the scenes, before Conclusions), reversing the 2026-07-11 decision.
- [open] 2026-07-14 — "Could the whole thing be 20 minutes for a lightning version? Mark which sections are cuttable."

---

# 1. What problems are we addressing?

**Goal of this section:** Name the pain out loud — the blank page, scattered sources, knowledge trapped in decks — before anyone hears a solution.

**Presenter feedback:**

---

## 1. Slides are where knowledge goes to die
<!-- template: statement -->

A one-line indictment of the deck-first workflow — the emotional hook that frames everything after it.

### Content

Slides are where knowledge goes to die.

### Sources

- corpus/readme.md

### Speaker notes

The claim behind the line: in a deck-first workflow, all the expensive work — reading the sources, deciding the framing, choosing what to cut — happens *outside* the artifact and is discarded when the deck ships. What survives is a set of compressed fragments that can't be queried, diffed, or safely reused, because the context that made them true is gone. The deck isn't a knowledge container; it's a lossy projection of one that was never saved.

### Presenter feedback

- [closed] 2026-07-09 — "This line lands — make it a full statement slide, no bullets."
  Resolution: Promoted to a standalone `statement` slide.

---

## 2. The cost of the blank page
<!-- template: stat -->
<!-- reveal: sequential -->

The problem in three numbers, so it isn't just a vibe.

### Content

What starting from scratch costs, in three numbers:

- **6 hrs** — typical time to rebuild a class you already gave
- **~0%** — of last time's material you actually re-find and reuse
- **3×** — times the same source serves different classes, if you keep it

### Sources

- corpus/readme.md
- corpus/instructor-survey-2025.md

### Speaker notes

What's behind each number. 6 hrs: rebuilding a class you already gave means recreating the structure and re-finding sources — the search usually costs more than the redo, so people redo. ~0%: slide fragments carry no provenance or context, so even when found they can't be safely reused — you can't tell if a claim is still true or where it came from. 3×: a single well-kept source (a paper, a case) typically serves an intro class, an advanced class, and a workshop — but only if it's kept somewhere findable. The numbers are illustrative; the mechanism — search cost exceeding redo cost — is the real point.

### Presenter feedback

---

## 3. Four problems, one root cause
<!-- template: concept-breakdown -->
<!-- reveal: sequential -->

The pain, broken into the pieces Talksmith picks off one by one.

### Content

- **Scattered sources** Papers, chats, and downloads live in a dozen places; finding last time's material costs more than redoing it.
- **Knowledge trapped in decks** Once it's in slides, you can't query, diff, or reuse it.
- **No reuse across classes** Every class starts cold, even when it overlaps last semester's.
- **No record of decisions** Why is this slide here? Why was that one cut? The reasoning evaporates.

### Sources

- corpus/readme.md
- corpus/instructor-survey-2025.md

### Speaker notes

The four pains share one root cause: the deck is the only artifact that survives preparation, and a deck is write-only. Scattered sources make search cost exceed redo cost. Deck-trapped knowledge can't be queried or diffed, so it can't be verified or updated. Cold starts happen because nothing structured carries over between overlapping classes. And decision rationale (why this slide, why not that one) lives only in memory, so the same debates repeat. Fix the artifact — make the surviving thing a queryable knowledge base — and all four resolve.

### Presenter feedback

---

# 2. What is Talksmith?

**Goal of this section:** Reframe — the knowledge base is the product, the deck is a projection, and even the diagrams come from your content.

**Presenter feedback:**

---

## 1. This is how you'll work — day to day
<!-- template: content-image -->

What a session actually looks like — the agent greets you and takes over.

### Content

![Talksmith introducing itself in Claude](images/claude.png)

- **It's all chat:** no new UI, no slide editor to learn.
- **New or resume:** start a fresh talk, or pick up one under `talks/` where you left off.
- **Drop & review:** add sources, answer a few questions, leave feedback bullets — it does the rest.
- **Always in view:** the Progress and Context panels show what it's reading and doing.

### Sources

- corpus/readme.md

### Speaker notes

What's actually on screen: a normal Claude Code (Cowork) session in a subject repo. The repo's CLAUDE.md stub — written once by /talksmith:init — loads the Talksmith orchestrator at session start; the greeting, the workflow chart, and the new-vs-resume prompt are the orchestrator introducing itself. 'Resume' works because every talk keeps a memory.md progress log — the agent reads it and continues from the last completed step. The Progress and Context panels are standard Cowork UI: they show which files the agent is reading and what it's doing, so the work is observable rather than a black box.

### Presenter feedback

---

## 2. Not a slide generator
<!-- template: comparison -->

Kill the wrong mental model before it forms: this is not "AI makes slides."

### Content

- **Deck generator** · Produces slides directly. The deck *is* the artifact; nothing is reusable next time.
- **RAG chatbot** · Re-reads the raw pile on every question. Nothing is compiled or curated; no durable outline.
- **Talksmith** · Compiles sources into a knowledge base once, drafts a thesis-first outline, renders slides on demand. The base is the asset.

### Sources

- corpus/readme.md
- corpus/karpathy-llm-wiki.md

### Speaker notes

The taxonomy that matters. A deck generator optimizes producing the artifact: prompt in, slides out — nothing durable remains, and the next talk starts from zero. A RAG chatbot indexes the raw pile and re-retrieves per question — useful for lookup, but nothing is ever synthesized or curated, and there's no outline to iterate on. Talksmith compiles: sources are restructured once into uniform corpus records, the outline is drafted thesis-first from them, and slides are rendered on demand from the outline. The durable asset is the compiled base; slides are a by-product.

### Presenter feedback

- [closed] 2026-07-10 — "Three-way compare is clearer than just us-vs-them."
  Resolution: Added the RAG-chatbot column.

---

## 3. Compilation over retrieval
<!-- template: quote -->

Anchor the idea in a name the audience may already trust.

### Content

> Instead of re-reading raw documents on every request, compile them once into a persistent, cross-linked knowledge base — the way source code compiles once and runs efficiently thereafter.

— on Andrej Karpathy's "LLM wiki" pattern

### Sources

- corpus/karpathy-llm-wiki.md

### Speaker notes

The pattern being quoted: instead of re-reading raw documents on every request (retrieval), have the agent maintain a synthesized, cross-linked knowledge base it updates as sources arrive — analogous to compiling source code once and running the binary many times. Talksmith is an implementation of this: the Librarian compiles each raw source into a uniform Markdown corpus record (metadata, claims, quotes, citations), and every downstream step reads the records, not the originals.

### Presenter feedback

---

## 4. The three layers
<!-- template: content+image -->

Make the knowledge-base idea concrete with a picture — and note the picture itself was auto-generated.

### Content

- **Raw sources** — immutable ground truth the agent reads but never rewrites.
- **The wiki** — synthesized, cross-linked Markdown the agent owns and keeps updated.
- **Projections** — `final.md`, then HTML or `.pptx`, rendered on demand and disposable.

```ascii
   RAW SOURCES            THE WIKI  (agent-owned)          PROJECTIONS
  ┌────────────┐         ┌─────────────────────┐         ┌────────────┐
  │ papers     │         │ corpus/*.md          │         │ final.md   │
  │ PDFs       │ ──────► │ memory.md            │ ──────► │    │       │
  │ chat logs  │ ingest  │ draft.md → final.md  │ render  │    ▼       │
  │ notes, URLs│         │ learnings.md         │         │ HTML / pptx│
  └────────────┘         └─────────────────────┘         └────────────┘
    read, never            compiled once,                   rebuilt
    rewritten              kept updated forever              on demand
```
<!-- ascii-note: three-layer knowledge-base diagram — keep the arrows left-to-right and the captions under each box -->

### Sources

- corpus/karpathy-llm-wiki.md
- corpus/orchestrator-spec.md

### Speaker notes

The ownership boundaries are the design. Raw sources (research/) are immutable ground truth — the agent reads them but never rewrites them, so provenance is always checkable. The wiki (research/corpus/) is agent-owned synthesis: uniform, cross-linked Markdown records the agent keeps current — humans read it but don't have to maintain it. Projections (final.md, then HTML or .pptx) are derived and disposable — regenerate them anytime, delete them without loss. Each layer can be trusted precisely because of who is *not* allowed to write it.

### Presenter feedback

- [closed] 2026-07-12 — "Cite the Karpathy write-up so people can go read it."
  Resolution: Added corpus/karpathy-llm-wiki.md; the record carries the URL.

---

## 5. Your diagrams draw themselves
<!-- template: single-point -->

The wow moment, stated plainly and demonstrated by the slide before it.

### Content

**You don't draw diagrams.** Talksmith proposes an outline version of each diagram as ASCII right in your draft — edit it if you want — then renders it to a clean, styled SVG at Polish. No more time spent making diagrams look nicer. Every diagram in this talk was generated that way.

### Sources

- corpus/diagram-style.md

### Speaker notes

How the mechanism works: diagrams live in draft.md as fenced ASCII blocks — proposed by the agent, editable by you like any text. At Polish, the Illustrator scans final.md for these blocks, renders each to a styled SVG (one standing visual spec governs colors, fonts, and shapes, so all diagrams in a talk match), and swaps the fence for an image reference — keeping the ASCII source alongside, so editing the ASCII and re-running Polish regenerates the picture. The consequence: diagrams are versionable, diffable text until the moment of rendering.

### Presenter feedback

---

# 3. The workflow in practice

**Goal of this section:** Show the eight steps as the presenter experiences them — chat-driven, Markdown-backed, audit-tracked.

**Presenter feedback:**

- [closed] 2026-07-11 — "Don't enumerate all 8 steps as a wall — show the flow, the modes, and the review LOOP, that's the differentiator."
  Resolution: Collapsed to four slides: the flow diagram, the draft modes, the review loop, the artifacts.

---

## 1. Eight steps, driven from chat
<!-- template: content+image -->

The whole arc in one picture — reuse the plugin's own diagram.

### Content

- You talk to Talksmith in chat; it does the work and keeps `draft.md` / `final.md` as the single source of truth.
- The live HTML preview (as you review) and the final `.pptx` render are optional, Cowork-only extras.

![Talksmith workflow](images/workflow.png)

### Sources

- corpus/orchestrator-spec.md

### Speaker notes

The shape of the workflow: setup happens once per talk (profile the audience, frame the thesis, collect and compile sources into the corpus); the middle is a loop (draft, review with inline feedback, repeat until right); rendering comes last and is optional. draft.md is the single source of truth throughout — the live HTML preview and the final deck are projections of it. Nothing blocks on the optional steps: a talk is complete as an outline even if it's never rendered.

### Presenter feedback

---

## 2. Draft your way
<!-- template: card-row -->
<!-- reveal: sequential -->

Three modes, one line each.

### Content

- **Interview** Talksmith asks; you answer.
- **Agent Draft** It drafts from your corpus, then asks.
- **Presenter Outline** You give titles; it fills them.

### Sources

- corpus/orchestrator-spec.md

### Speaker notes

The three drafting modes produce the same draft.md — they differ in who moves first. Interview: the agent asks structured questions (audience, arc, emphasis) and builds the outline from your answers — best for a first talk or a blank corpus. Agent Draft: the agent proposes a complete thesis-first outline from the corpus, and you react — best once the corpus is rich, since every slide arrives pre-grounded in sources. Presenter Outline: you supply the section and slide titles, and the agent fills the bodies from the corpus — best when the talk already exists in your head.

### Presenter feedback

---

## 3. Review is a loop
<!-- template: process -->

The differentiator: feedback is applied *and* kept forever — and it's about content, not looks. Second render-driving diagram.

### Content

You refine `draft.md` in **rounds** — leave inline feedback, it's applied, you review again, until the talk is right.

1. **Leave feedback** Drop plain-text bullets right in `draft.md`, under each slide's `### Presenter feedback` — as many as you want, in any editor.
2. **Talksmith applies** It stamps each bullet, makes the change, and closes it with a one-line resolution kept as an audit trail.
3. **Review and repeat** Look again, add more feedback, go around once more — the loop runs as many rounds as it takes until you say "final".

**Important:** Every round is about the **content**, not how it looks — visuals and styling come later at Polish.

```ascii
     you edit draft.md
           │
           ▼
   - "trim this slide"                (raw bullet)
           │  editor stamps + dates
           ▼
   [open] 2026-07-14 — "..."  ──────► apply the change
           │                                │
           ▼                                │
   [closed] 2026-07-14 — "..."  ◄───────────┘
     Resolution: what changed & why
           │
           ▼
   mirrored to feedback-backlog.md         (audit trail — never deleted)
           │
           └──────────► loop until you say "final"
```
<!-- ascii-note: feedback lifecycle — raw → open → apply → closed → backlog, with the loop-back arrow at the bottom -->

### Sources

- corpus/orchestrator-spec.md
- corpus/editor-contract.md

### Speaker notes

How feedback actually flows: you write plain-text bullets under any slide's 'Presenter feedback' heading, in any editor. Talksmith stamps each bullet [open] with a date, makes the change, then closes it in place with a one-line resolution — so draft.md accumulates a decision trail: what was asked, what was done, when. Closed items are mirrored to a backlog file, and recurring feedback gets promoted into learnings.md as standing editorial rules that every future talk inherits. This is the direct answer to 'no record of decisions' from the opening section.

### Presenter feedback

- [closed] 2026-07-13 — "Make the self-referential point — this talk was drafted in Talksmith."
  Resolution: Added the live-demo cue and this diagram.

---

## 4. What you end up with
<!-- template: concept-breakdown -->

The concrete artifacts, so it isn't abstract.

### Content

- **draft.md** The working outline you edit, with its feedback audit trail.
- **final.md** The polished, delivery-ready derivative — diagrams rendered, feedback stripped.
- **research/corpus/** The compiled knowledge base backing every claim.
- **memory.md** The progress log that lets you stop and resume anytime.

### Sources

- corpus/readme.md

### Speaker notes

The durable/derived split: draft.md and research/corpus/ are the assets — they accumulate and are never regenerated. final.md is derived: Polish copies draft.md, strips the feedback machinery, renders diagrams, and produces the delivery-ready file — deleting it loses nothing, because the next Polish re-derives it. memory.md is the progress log: which step is done, what's pending — it's what lets a session stop anywhere and a later session (or a teammate) resume without re-explaining.

### Presenter feedback

---

## 5. One source, three outputs
<!-- template: card-row -->

Sell the projection idea concretely: the same source ships in three formats.

### Content

The same `final.md` renders to any of these — pick per audience:

- **HTML deck** A self-contained Reveal.js deck — present in the browser or share a link.
- **PowerPoint** A native `.pptx` (strict or free-form) for Keynote / PowerPoint.
- **PDF** Export the HTML deck to PDF for handouts.

**Note:** you're looking at one right now — this deck was rendered from its `draft.md` with Talksmith.

### Sources

- corpus/readme.md

### Speaker notes

The render paths from one final.md: the HTML deck is a single self-contained file (Reveal.js, fonts and scripts inlined) that works offline and shares as a link; the native .pptx comes in two styles — strict (conforms to an institutional template) and free-form — for venues that require PowerPoint; PDF comes from the HTML deck's print view, for handouts. Because all three are projections, presentation-day format changes are a re-render, not a rebuild.

### Presenter feedback

---

## 6. Presenting the HTML deck: shortcuts
<!-- template: icon-list -->

Show that the HTML deliverable is a real presentation tool, not just a web page — live, on this very deck.

### Content

The deck is a Reveal.js app — these come with the framework (try them now):

- **Navigate** → / ← / Space. The URL hash (#/12) makes every slide a shareable deep link.
- **Overview** O or Esc — a zoomed-out grid of the whole deck; click a slide to jump.
- **Speaker view** S — presenter window with current + next slide, your notes, and a timer.
- **Fullscreen** F to go fullscreen; Esc returns.

### Sources

- corpus/readme.md

### Speaker notes

What the framework provides and why it matters: navigation is keyboard-first (arrows/Space), and the URL hash tracks the slide — so #/12 is a deep link you can send, bookmark, or open on stage. Overview (O) shows the whole deck as a grid for orientation and jumping. Speaker view (S) opens a second, synchronized window — current slide, next slide, these notes, and a timer — put it on the laptop while the audience sees the deck. Fullscreen is F. All of it ships with Reveal.js; none of it needed custom code.

### Presenter feedback

---

## 7. Presenting the HTML deck: the buttons
<!-- template: icon-list -->

Finish the tour with the Talksmith chrome — the affordances presenters reach for without keyboard shortcuts.

### Content

Five discreet buttons top-right (they fade in when the pointer moves, and never print):

- **Light / dark** Flips the theme; a link can force it with ?deck-theme=dark.
- **Animations** Transitions and fragments off, for a static read-through.
- **Export to PDF** Opens the print view with your theme and style, and fires the print dialog.
- **Fullscreen** Same as pressing F.
- **Style** Token-only skins — fonts, colors, background — layout untouched; ?deck-style= per link.

### Sources

- corpus/readme.md

### Speaker notes

What each button does under the hood: light/dark swaps the CSS token set and persists the choice in the browser (a link can pin it with ?deck-theme=dark). Animations toggles Reveal's fragments and transitions — useful for reading a deck straight through. Export to PDF opens the print-layout view carrying the active theme and style, then fires the print dialog — 'Save as PDF' finishes it. Fullscreen mirrors the F key. Style switches between token-only skins: fonts, colors, and backgrounds change; layout never does, because every component reads the same design tokens. The cluster hides while idle and is excluded from print.

### Presenter feedback

---

# 4. Behind the scenes

**Goal of this section:** Pay off the curiosity — the five agents and the Markdown substrate — now that the audience knows what they're for.

**Presenter feedback:**

---

## 1. Five roles, one source of truth
<!-- template: icon-list -->

Who's actually doing the work.

### Content

- **Librarian** Restructures raw sources into a uniform corpus. Preserves; doesn't compress.
- **Composer** Reviews slides against thesis, audience, sources, and learned rules.
- **Editor** The muscle: writes `draft.md`, applies feedback, produces `final.md`.
- **Illustrator** Turns your ASCII into styled SVGs at Polish.
- **Global-Librarian** Curates finalized Talks into the shared knowledge library.

### Sources

- corpus/orchestrator-spec.md

### Speaker notes

The design principle is separation of powers over one file. The Editor is the only role allowed to write draft.md, final.md, and memory.md — one writer means no conflicting edits and one accountable trail. The Composer is deliberately its opposite: read-only, and its only output is criticism — a punch-list graded blocker/major/minor against thesis, audience, sources, and learned rules. The Librarian compiles raw sources into corpus records; the Illustrator renders ASCII diagrams to SVG at Polish; the Global-Librarian curates finished talks into the shared cross-talk library. You never dispatch any of them — the orchestrator does, and reports outcomes in plain language.

### Presenter feedback

---

## 2. It's Markdown all the way down
<!-- template: content+cards+image -->

Why the substrate choice is the whole point — with a picture of the round trip.

### Content

Every artifact is a plain `.md` file: diffable, versionable, portable across renderers. Slides are a projection — and you can even round-trip edits made in PowerPoint back into the source.

- **Diffable** Every change shows up in `git diff`.
- **Portable** The same outline renders to HTML or `.pptx`.
- **Round-trippable** Edited the deck in Keynote? Reconcile it back into `draft.md`.

```ascii
  FORWARD
  draft.md ─────► final.md ─────► output/final.pptx
     ▲                                   │
     │            REVERSE                │  you edit in Keynote / PowerPoint
     └─ pptx-merge ◄─ pptx-diff ◄─ pptx-extract
```
<!-- ascii-note: forward + reverse pipeline — top row left-to-right, reverse row right-to-left back into draft.md -->

**Note:** the reverse path is optional — you only need it when you've edited the deck *outside* the cycle (e.g. tweaked the `.pptx` in PowerPoint).

### Sources

- corpus/readme.md
- corpus/reverse-pipeline.md

### Speaker notes

Why plain text is the load-bearing choice: Markdown makes every artifact diffable (each change is a reviewable git diff), portable (the same outline renders to HTML or .pptx), and durable (no tool lock-in). The reverse pipeline closes the loop: a deck edited in PowerPoint or Keynote can be read back, diffed against final.md, and reconciled into draft.md — simple edits land automatically, ambiguous ones are routed for judgment. That round-trip is the guarantee that no downstream edit is ever lost, which is what makes 'the deck is disposable' safe to say.

### Presenter feedback

---

## 3. Markdown vs. a binary deck
<!-- template: pros-cons -->

Make the trade-off explicit and honest.

### Content

**Markdown source of truth**

- Diffable, versionable, greppable
- Portable across any renderer
- Outlives any single tool

**Binary deck as source**

- Opaque to version control
- Locked to one application
- Knowledge trapped in the format

### Sources

- corpus/readme.md

### Speaker notes

The honest trade-off: a binary deck gives direct WYSIWYG control — PowerPoint is a better pixel editor than any text file. The cost is that the format is opaque to version control (a .pptx diff is meaningless), locked to one application, and traps the content. The resolution isn't to argue pixels don't matter — it's to move them to the right layer: the source stays plain text (diffable, greppable, portable), and pixel-perfection is the renderer's job, applied at projection time.

### Presenter feedback

---

## 4. One base, many decks
<!-- template: image-grid -->

Show the same corpus rendered several ways.

### Content

- ![Strict style cover](images/deck-strict.png)
- ![Free-form style cover](images/deck-free-form.png)
- ![Live HTML preview](images/deck-html.png)
- ![PDF export](images/deck-pdf.png)

### Sources

- corpus/orchestrator-spec.md

### Speaker notes

Four renders of the same source, shown side by side: strict .pptx (conforms to an institutional template — placement, colors, typography follow the template's rules), free-form .pptx (the renderer designs each slide freely), the HTML deck, and its PDF export. Same outline, same content, four presentations — the visual proof of 'the deck is a projection.' Restyling a talk for a new venue is a parameter change, not an editing session.

### Presenter feedback

---

## 5. Knowledge that compounds
<!-- template: big-number -->

Land the payoff on a single number.

### Content

- **1** knowledge base per subject that outlives every renderer, every semester, and every teammate handoff.

### Sources

- corpus/readme.md

### Speaker notes

The unit of accumulation is the subject, not the talk. One repo holds the profile (audience, duration, language — set once), the corpus, the learnings, and every talk's outline for that subject. Renderers can change, semesters roll over, teammates rotate — the base persists because it's plain text in git. 'Per subject' is also the scaling advice: the subject you teach most often compounds fastest.

### Presenter feedback

---

## 6. A semester, compounding
<!-- template: timeline -->

Show the compounding across real time.

### Content

- **Class 1** Corpus seeded from three papers; first outline drafted.
- **Class 3** Alice's indexed sources answer Bob's new questions — zero re-reading.
- **Class 7** Recurring feedback promoted to `learnings.md`; every future class inherits it.
- **Next semester** New teammate clones the repo and is productive on day one.

### Sources

- corpus/orchestrator-spec.md

### Speaker notes

The compounding mechanics, milestone by milestone: seeding — the first class compiles its sources into corpus records, the one-time cost. Cross-teammate reuse — because the repo is shared, Alice's indexed sources answer Bob's questions without Bob re-reading anything. Learnings — feedback that recurs ('shorter titles', 'always cite the case') is promoted to learnings.md and applied automatically to every future draft. Onboarding — a new teammate clones the repo and inherits the corpus, the rules, and every past decision trail on day one.

### Presenter feedback

---

# 5. Getting started

**Goal of this section:** Get the audience from zero to a running session in three commands, live.

**Presenter feedback:**

---

## 1. Setup, once
<!-- template: divider -->

A light sub-opener before the hands-on part.

Hands on — from zero to a running session.

### Content

_(divider — no body)_

### Sources

### Speaker notes

Transition into the hands-on part: everything so far was the model; what follows is the mechanical setup — three commands, then a running session.

### Presenter feedback

---

## 2. Three commands
<!-- template: code-example -->

The whole install, copy-paste.

### Content

```bash
# Install the plugin (once per machine), inside a Claude Code session
/plugin marketplace add veigap/talksmith
/plugin install talksmith@talksmith

# Scaffold your subject repo
/talksmith:init

# Open a fresh session in that repo and say:
Hi Talksmith
```

### Sources

- corpus/readme.md

### Speaker notes

What each command actually does. The two /plugin commands register the marketplace and install the plugin — once per machine; updates arrive with /plugin update. /talksmith:init runs once per subject repo and writes exactly one file: a thin CLAUDE.md stub that loads the Talksmith orchestrator at session start — commit it, and every teammate who clones the repo is set up with zero steps. 'Hi Talksmith' in a fresh session triggers the orchestrator's introduction: it detects existing talks and offers to start or resume.

### Presenter feedback

- [closed] 2026-07-13 — "Show that init only writes ONE file — people worry it'll dump config everywhere."
  Resolution: Added the 'writes exactly one file' note.

---

## 3. From nothing to running
<!-- template: process -->

The setup as an ordered path, so nobody loses the thread.

### Content

1. **Create the repo** — one Git repo per subject; the shared home for its material.
2. **Install the plugin** — once per machine, from the marketplace.
3. **Initialize** — `/talksmith:init` drops the `CLAUDE.md` stub; commit it.
4. **Start** — open a session, say "Hi Talksmith", and follow the workflow.

### Sources

- corpus/readme.md

### Speaker notes

The scopes are the point of this slide: create the repo once per subject (it's the shared, versioned home for everything the subject accumulates); install the plugin once per machine; initialize once per repo; and only the greeting repeats, once per session. Everything after the greeting is the workflow itself — there is no separate configuration surface to maintain.

### Presenter feedback

---

## 4. What lives in the repo
<!-- template: icon-list -->

Orient them in the folder they'll be committing to.

### Content

- **profile.md** — subject, audience, duration, language — set once, inherited by every class.
- **learnings.md** — the team's editorial taste, grown from recurring feedback.
- **logo.\*** — your institution logo, dropped in at setup; a neutral placeholder if you skip it.
- **talks/** — one folder per class; where the corpus and outlines accumulate.
- **knowledge-library/** — the curated cross-Talk topic index shared by the team.

### Sources

- corpus/readme.md
- corpus/orchestrator-spec.md

### Speaker notes

What each entry is for. profile.md holds the subject's constants — audience, duration, language — set once and inherited by every talk, so you never re-answer them. learnings.md is the team's editorial taste made executable: standing rules grown from recurring feedback, applied to every future draft. logo.* brands every render (a neutral placeholder if absent). talks/ holds one folder per class — its corpus, images, outline, and outputs. knowledge-library/ is the cross-talk topic index the Global-Librarian curates from finished talks, so material outlives the talk that produced it.

### Presenter feedback

---

## 5. Quick check
<!-- template: quiz -->

A check-for-understanding before we walk the workflow.

### Content

**Question:** You render a `.pptx`, then tweak it in PowerPoint. What's the source of truth?

- A. The `.pptx` you just edited
- B. `final.md`
- C. `draft.md`

**Answer:** C — `draft.md`. The deck is a projection; edits made downstream are reconciled *back* into `draft.md`, so the next Polish re-derives `final.md`.

### Sources

- corpus/readme.md
- corpus/reverse-pipeline.md

### Speaker notes

Why draft.md is the answer: final.md is derived from it at every Polish, and the rendered deck is derived from final.md — both are projections. Edits made downstream (even in PowerPoint) are reconciled back into draft.md by the reverse pipeline, so truth always flows to the source, never the copy. The wrong answers are instructive: the edited .pptx is the most recent artifact but not the source; final.md is closer but still regenerable. One file is authoritative precisely so that everything else can be safely thrown away.

### Presenter feedback

---

# Conclusions

## 1. Key takeaways
<!-- template: content-text -->

The three things to remember, in prose.

### Content

Stop rebuilding talks from scratch. Build a knowledge base that compounds, and let the deck be a disposable projection of it. Three commands get you started; chat and `draft.md` run the whole loop; and every decision — including why each slide looks the way it does — is preserved in a closed-forever audit trail. The diagrams even draw themselves.

### Sources

- corpus/readme.md

### Speaker notes

The three claims, compressed: (1) the durable asset of talk preparation is the knowledge base — sources compiled once, decisions recorded — and the deck is its disposable projection; (2) adoption is deliberately thin — three commands, then everything happens in chat and one Markdown file; (3) the by-products that usually cost extra (audit trail, consistent diagrams, multi-format output) fall out of the model for free.

### Presenter feedback

---

## 2. Try it today
<!-- template: closing-cta -->

One clear next action.

### Content

- Install it now: `/plugin marketplace add veigap/talksmith`
- Pick one subject you teach repeatedly and make it your first repo.
- Questions? Let's talk.

### Sources

- corpus/readme.md

### Speaker notes

Practical starting advice: pick the subject you teach or present most often — highest repetition means fastest compounding. The first session's real work is seeding the corpus: drop in the papers, notes, and past materials you already have; everything after that gets cheaper. The install command stays on screen for Q&A.

### Presenter feedback

---

## 3. Build a talk from what you already know
<!-- template: closing-hero -->

The closing image — the thesis as a send-off.

### Content

Build a talk from what you already know.

### Sources

- corpus/readme.md

### Speaker notes

The thesis in one line: the understanding you already have is the raw material; Talksmith compiles it into a base that every future talk draws from. The blank page was never necessary — it was just the default artifact.

### Presenter feedback

---

# Open questions

- Should there be a 20-minute "lightning" cut? Candidate sections to drop: 4 (Behind the scenes) and slides 2.3 (quote) and 3.4 (artifacts).
- Do we need a live-demo fallback if the room has no internet for `/plugin install`? (Pre-recorded 60s clip?)
- The `image-grid` slide (4.4) needs four real render thumbnails captured before delivery — placeholder paths for now.

# Cut material

- A detailed `profile.md` field-by-field walkthrough — belongs in a hands-on workshop, not a 40-min intro.
- An extended live-coding demo building a corpus from scratch — great for a workshop, too long for an intro.
- A deep dive on `pptx-learn` (mining styling patterns from hand-corrected decks) — too advanced for an intro; mention only if asked.
