# Talksmith

**Talksmith** is a Presenter Agent that helps a human presenter turn raw exploration — articles, papers, LLM chat sessions, screenshots, notes — into a well-structured presentation outline (`master.md`), and optionally renders it to PowerPoint.

It is **not** a slide generator. The deliverable is a single structured Markdown file describing the deck: thesis, agenda, sections, slides, sources, and speaker notes. Downstream tooling consumes that file to render slides.

## An opinionated methodology

Talksmith isn't a generic "ask an LLM to make a deck" tool. It encodes a four-phase methodology, and pushes back when you deviate:

```
  Explore  -->  Compile  -->  Draft  -->  Refine
  (sources)    (knowledge)   (outline)    (loop)
```

- **Explore — LLMs are the brainstorming partner, not the deck generator.** Use Claude (or any LLM) to learn the topic, stress-test ideas, generate charts, and chase tangents. Read papers, capture notes. Actually engage with the material before structuring anything.
- **Compile — preserve, don't summarize.** Drop papers and notes into `knowledge/articles/`, export worthwhile chat sessions to ZIP under `knowledge/llm-chats/`. The Librarian restructures every source into uniform Markdown — contradictions, abandoned threads, and course-corrections preserved — so the next phase works from your actual thinking, not a blank prompt.
- **Draft — thesis-first, sourced.** Every slide is challenged against a one-sentence thesis and cited back to a compiled source. Talksmith won't invent content out of thin air.
- **Refine — audit-tracked loop.** Feedback bullets land in `master.md` in your editor of choice; cut material and closed feedback stay in the file as an audit trail, never silently deleted.

One substrate underneath all of it: **Markdown.** Compiled sources, the outline (`master.md`), the progress log (`memory.md`), feedback rounds — every artifact is a plain `.md` file. Diffable, versionable, editable in any tool, portable across renderers. Slides are a *projection* of the Markdown, not the source of truth.

If that doesn't fit how you work, this is the wrong tool.

## One fork per subject

Talksmith expects **one fork of this repo per subject** — a university course, a recurring workshop, a research area you keep presenting in. Inside that fork, `talks/` accumulates class by class: every Talk you give on the subject lives in the same place.

This isn't about repo hygiene — it's about compounding value over time:

- **Compiled knowledge is reusable across classes.** A paper compiled in class 3 is still queryable for class 7. Each fork becomes a domain-specific knowledge base.
- **`profile.md` calibrates to one audience.** "AI students in Biomedicine, undergraduate" is set once and inherited by every class in the fork. Different subject → different fork → different audience defaults. No global state to bleed.
- **`learnings.md` accumulates per-subject editorial taste.** Recurring feedback ("don't open with the algorithm — open with the dataset") promoted in Step 7 applies to the next class on the same subject, not to unrelated topics.
- **The audit trail stays scoped.** Feedback backlog, cut material, and open questions live next to the subject they came from. No cross-subject contamination.

If you present on three subjects, that's three forks. Mixing subjects in one repo erodes every advantage above.

## How it works

Four roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `knowledge/compile/`. Preserves; does not compress.
- **Composer** — the brain. Reviews drafted slides against thesis, audience, sources, design principles, and learned rules promoted from prior Talks; returns a punch-list of critiques. Read-only batch reviewer, invoked at every drafting milestone.
- **Editor** — the muscle. Keeps `master.md` and `memory.md` current as the single source of truth: bootstraps from template, transcribes presenter decisions, drafts prose from compiled sources, applies feedback, and cleans the file for delivery.
- **Illustrator** — converts every ASCII diagram in `master.md` into a styled SVG during the Polish step.

Role specs live at [.claude/roles/](.claude/roles/) — performed inline by the orchestrator, not as separate agents.

## Getting started

Talksmith runs inside a Claude Code session — the agent definition lives in [CLAUDE.md](CLAUDE.md) and is loaded automatically when Claude Code opens the repo. Pick one of the two ways to start it:

### Option 1 — Claude Code CLI (local terminal)

1. Install the CLI if you don't already have it:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
2. Clone this repo and `cd` into it:
   ```bash
   git clone <this-repo-url> talksmith
   cd talksmith
   ```
3. Launch Claude Code from the repo root with the Opus model (recommended for Talksmith's editorial work) and a kickoff prompt that boots the agent:
   ```bash
   claude --model opus "Hi Talksmith"
   ```

The Presenter Agent introduces itself on the first turn. Your talk folders live under `talks/` on your local disk, so source uploads in Step 2 are just drag-and-drop (or `cp`) into `talks/<folder>/knowledge/articles/` and `knowledge/llm-chats/`.

### Option 2 — Claude Code on the web (Cowork)

1. Push this repo to GitHub (or any Git host Claude Code on the web supports).
2. Open [claude.com/code](https://claude.com/code) and connect the repo as a workspace.
3. Start a new session against the repo — the agent boots from `CLAUDE.md` the same way as in the CLI.

In the web/Cowork flow, upload source files (PDFs, chat ZIPs, images) via the session's file attachment UI; the agent will place them under the active talk's `knowledge/articles/` or `knowledge/llm-chats/` folder before Step 3 (Compile).

### Option 3 — Claude Code Cowork on Desktop

1. Install the Claude Code desktop app (Mac or Windows) from [claude.com/download](https://claude.com/download) and sign in.
2. Connect the repo to Cowork in one of two ways:
   - **Local folder** — point Cowork at your cloned `talksmith/` directory on disk (same as Option 1, but driven from the desktop UI instead of the terminal).
   - **GitHub-backed workspace** — connect the GitHub repo, same as Option 2; the desktop app uses the cloud workspace.
3. Open a new session on the workspace — the agent boots from `CLAUDE.md` automatically.

The desktop app is the most ergonomic option day-to-day: drag-and-drop source uploads into `knowledge/articles/` and `knowledge/llm-chats/` work natively, and you can keep `master.md` open in an external editor (VS Code, Obsidian) alongside the Cowork session for the Step 5 Review loop.

### What happens next

In either mode, the Presenter Agent will:

1. Introduce itself and show the workflow chart.
2. Load [`knowledge/profile.md`](knowledge/profile.md) if filled, or offer to fill it (Step 0.5).
3. Ask in chat (with numbered options) whether you're starting a **new** talk or **resuming** an existing one under `talks/`.

Everything else flows from there. For the full operating spec, see [CLAUDE.md](CLAUDE.md).

## Workflow

```
  TALKSMITH WORKFLOW
  ==================

  [1] Frame       <-- presenter: topic + folder name
       v
  [2] Collect     <-- presenter: upload PDFs/papers, chat ZIPs, URLs
       v
  [3] Compile      -- librarian: sources -> knowledge/compile/*.md
       v
  [4] Draft       <-- one of three modes (A Interview / B Agent Draft / C Outline)
                     editor writes; composer critiques at every milestone
       v
  [5] Review      <-- presenter edits master.md; loops N times
       v
  [6] Polish       -- illustrator: ASCII -> SVG; editor: consolidate images,
                     rescue open feedback, clean master.md
       v
  [7] Learnings    -- promote >=3x recurring feedback to learnings.md
       v
  [8] Render PPTX  -- md-to-pptx (optional, Cowork only)
```

Step 0 (Introduce) runs automatically on session start and isn't shown above. The full step-by-step instructions live in [CLAUDE.md](CLAUDE.md).

### Draft has three modes

When filling `master.md` from empty, the presenter picks how to work:

- **Interview** — agent asks structured questions, presenter answers.
- **Agent Draft** — agent reads compiled knowledge + profile, drafts everything, then asks targeted clarifying questions.
- **Presenter Outline** — presenter supplies sections + slide titles, agent fills the body from compiled knowledge.

### Review is a loop

The first Draft is rarely final. In Review, the presenter opens `master.md` in their editor of choice (VS Code, Obsidian, plain text — anything), drops plain-text feedback bullets inside `Presenter feedback` fields:

```
### Presenter feedback
- "this slide is too dense; trim to 90 seconds"
- "swap with the slide above"
```

The Editor then stamps each bullet with status + date (`[open] 2026-05-12 — "..."`), applies the change, and flips the bullet to `[closed]` with a `Resolution:` line. Closed entries are never deleted — they're the audit trail for why each slide looks the way it does.

Review repeats as many times as needed until the presenter declares the document final.

## Repo layout

```
.
├── README.md                          # this file
├── CLAUDE.md                          # full agent instructions (Talksmith spec)
├── knowledge/
│   ├── profile.md                     # presenter's filled-in profile (created from template in Step 0.5; gitignored if personal)
│   ├── principles.md                  # what makes a good presentation (loaded at session start)
│   ├── learnings.md                   # durable rules promoted from feedback patterns
│   ├── feedback-backlog.md            # cross-Talk feedback log
│   ├── feedback-processed.md          # archived feedback promoted to learnings
│   ├── image-styles/                  # SVG style spec + recurring shape templates (illustrator/ascii-to-svg)
│   └── template.pptx                  # PowerPoint reference template (Step 8 Render)
├── talks/
│   └── <talk-folder>/                 # one folder per talk
│       ├── master.md                  # the outline (deliverable)
│       ├── memory.md                  # progress log / restore point
│       ├── knowledge/
│       │   ├── articles/              # PDFs, HTML, papers
│       │   ├── llm-chats/             # ZIP exports of LLM chat sessions
│       │   ├── web/                   # captured pages (one folder per URL, written by talksmith:ingest)
│       │   └── compile/               # Librarian's structured Markdown output
│       ├── images/                    # SVGs rendered in Step 6 (Polish) + consolidated images
│       └── output/                    # rendered .pptx (Step 8, optional)
└── .claude/
    ├── settings.json                  # shared Claude Code settings
    ├── settings.local.json            # local overrides (gitignored)
    ├── schemas/                       # file-format specs (each holds spec + canonical empty form)
    │   ├── master.md                  # talks/<Talk>/master.md schema (seeds the deliverable in Step 4)
    │   ├── memory.md                  # talks/<Talk>/memory.md schema (per-Talk progress log / resume point)
    │   ├── profile.md                 # knowledge/profile.md schema (seeds the profile in Step 0.5)
    │   ├── principles.md              # knowledge/principles.md schema (composer's design defaults)
    │   ├── learnings.md               # knowledge/learnings.md schema (promoted rules)
    │   ├── feedback-backlog.md        # knowledge/feedback-backlog.md schema (cross-Talk feedback log)
    │   ├── feedback-processed.md      # knowledge/feedback-processed.md schema (promoted-feedback archive)
    │   └── compile-record.md          # knowledge/compile/<file>.md schema (librarian's per-source records)
    ├── roles/
    │   ├── librarian.md               # Librarian role spec
    │   ├── composer.md                # Composer role spec (design critic)
    │   ├── editor.md                  # Editor role spec (master.md/memory.md maintainer)
    │   └── illustrator.md             # Illustrator role spec (ASCII → SVG coordinator)
    └── skills/
        ├── ingest/                    # talksmith:ingest — capture a web page into knowledge/web/
        ├── ascii-to-svg/              # talksmith:ascii-to-svg — render one ASCII block to one SVG
        └── md-to-pptx/                # talksmith:md-to-pptx — render master.md to .pptx (Step 8)
```

## Key conventions

- **Folder names are kebab-case** (e.g. `gan-networks`, `quantum-computing-intro`).
- **Cite sources by filename.** Slide `Sources` reference files under `knowledge/compile/` (e.g. `compile/transformer-paper.md`).
- **Never silently drop content.** Anything removed goes to `Cut material` or `Open questions` in `master.md`.
- **Chat-prompt is the canonical interaction.** The agent asks every decision in chat with 2–4 numbered prose options derived from current context. Genuinely open questions (e.g. "what's your thesis?") fall back to free-text.
- **`knowledge/profile.md` is session-wide context.** Once filled, it's loaded automatically and kept in context across all role work.
- **`memory.md` is append-only.** Updated after every completed step; used to resume an in-progress talk.

## Author

Paulo Gustavo Veiga — [@veigap](https://github.com/veigap)

## License

[Unlicense](LICENSE) — released into the public domain.
