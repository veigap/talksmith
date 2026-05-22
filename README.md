# Talksmith

**Talksmith** is a Presenter Agent that helps a human presenter turn raw exploration — articles, papers, LLM chat sessions, screenshots, notes — into a well-structured presentation outline (`draft.md`), then a polished deliverable (`final.md`), and optionally renders it to PowerPoint.

It is **not** a slide generator. The deliverable is two plain Markdown files — `draft.md` (the working file the presenter edits during Steps 1–5) and `final.md` (the cleaned, Polish-stage derivative produced in Step 6) — describing the deck: thesis, agenda, sections, slides, sources, and speaker notes. Downstream tooling consumes `final.md` to render slides; `draft.md` stays around as the durable working file with the full feedback audit trail, untouched after Step 5.

## An opinionated methodology

Talksmith isn't a generic "ask an LLM to make a deck" tool. It encodes a four-phase methodology, and pushes back when you deviate:

```
  Explore  -->  Corpus   -->  Draft  -->  Refine
  (sources)    (knowledge)   (outline)    (loop)
```

- **Explore — LLMs are the brainstorming partner, not the deck generator.** Use Claude (or any LLM) to learn the topic, stress-test ideas, generate charts, and chase tangents. Read papers, capture notes. Actually engage with the material before structuring anything.
- **Corpus — preserve, don't summarize.** Drop papers and notes into `knowledge/articles/`, export worthwhile chat sessions to ZIP under `knowledge/llm-chats/`. The Librarian restructures every source into uniform Markdown — contradictions, abandoned threads, and course-corrections preserved — and copies every image into per-source companion folders so the corpus is self-contained. The next phase works from your actual thinking, not a blank prompt.
- **Draft — thesis-first, sourced.** Every slide is challenged against a one-sentence thesis and cited back to a corpus record. Talksmith won't invent content out of thin air.
- **Refine — audit-tracked loop.** Feedback bullets land in `draft.md` in your editor of choice; cut material and closed feedback stay in the file as an audit trail, never silently deleted. Step 6 (Polish) makes a separate `final.md` so polishing never overwrites the audit trail — you can re-run Polish as many times as you want against the same untouched `draft.md`.

One substrate underneath all of it: **Markdown.** Corpus records, the outline (`draft.md` → `final.md`), the progress log (`memory.md`), feedback rounds — every artifact is a plain `.md` file. Diffable, versionable, editable in any tool, portable across renderers. Slides are a *projection* of the Markdown, not the source of truth.

If that doesn't fit how you work, this is the wrong tool.

## One fork per subject

Talksmith expects **one fork of this repo per subject** — a university course, a recurring workshop, a research area you keep presenting in. Inside that fork, `talks/` accumulates class by class: every Talk you give on the subject lives in the same place.

This isn't about repo hygiene — it's about compounding value over time:

- **Corpus knowledge is reusable across classes.** A paper indexed into the corpus in class 3 is still queryable for class 7. Each fork becomes a domain-specific knowledge base.
- **`profile.md` calibrates to one audience.** "AI students in Biomedicine, undergraduate" is set once and inherited by every class in the fork. Different subject → different fork → different audience defaults. No global state to bleed.
- **`learnings.md` accumulates per-subject editorial taste.** Recurring feedback ("don't open with the algorithm — open with the dataset") promoted in Step 7 applies to the next class on the same subject, not to unrelated topics.
- **The audit trail stays scoped.** Feedback backlog, cut material, and open questions live next to the subject they came from. No cross-subject contamination.

If you present on three subjects, that's three forks. Mixing subjects in one repo erodes every advantage above.

**Keeping a fork current.** When master ships new skills, role specs, or shared knowledge (`principles.md`, `image-styles/`), the [`talksmith:upgrade`](.claude/skills/upgrade/SKILL.md) skill pulls the latest core from `github.com/veigap/talksmith` (shallow clone of `main`) into your fork without ever touching its accumulated state.

The skill exposes two operations:

- **`diff`** — read-only inventory of what would change in your fork: files to create, files to modify.
- **`apply`** — performs the copy after a confirmation prompt. Create + modify only; the fork is never deleted from. Files that were removed or renamed upstream linger in your fork until you delete them by hand.

When master ships structural changes (renames, removals, restructures), the manual steps land in [`MIGRATION.md`](MIGRATION.md) at the repo root. The skill copies that file into your fork like any other core file, and prints a banner after `apply` when it was just created or updated — pointing you to the dated section(s) added since your last upgrade. Per-Talk content under `talks/` is **never** mass-edited by the skill (each Talk is your product), so renames affecting per-Talk files always need the manual step.

The skill always pulls master from `https://github.com/veigap/talksmith` @ `main` — no flags to override. If you need to upgrade from anywhere else, this isn't the tool.

| Touched by the skill | Never touched |
|---|---|
| `.claude/` · `CLAUDE.md` · `README.md` · `MIGRATION.md` · `config/principles.md` · `config/image-styles/` | `talks/` · `config/profile.md` · `config/learnings.md` · `config/feedback-backlog.md` · `config/feedback-processed.md` |

See [`.claude/skills/upgrade/SKILL.md`](.claude/skills/upgrade/SKILL.md) for the full contract, safety rules, and exit codes.

## How it works

Five roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `knowledge/corpus/`, with a companion `<source-stem>/images/` folder per source so the corpus is self-contained. Preserves; does not compress.
- **Composer** — the brain. Reviews drafted slides against thesis, audience, sources, design principles, and learned rules promoted from prior Talks; returns a punch-list of critiques. Read-only batch reviewer, invoked at every drafting milestone.
- **Editor** — the muscle. Keeps `draft.md` (Steps 1–5), `final.md` (Step 6+), and `memory.md` current as the single source of truth: bootstraps from template, transcribes presenter decisions, drafts prose from corpus records, applies feedback in `draft.md`, then in Step 6 copies `draft.md` → `final.md` and cleans `final.md` for delivery.
- **Illustrator** — converts every ASCII diagram in `final.md` into a styled SVG during the Polish step.
- **Global-Librarian** — cross-Talk curator. On Step 7 promotion, reads the finalized Talk's corpus + `final.md` and curates reusable, topic-organized knowledge into a shared `knowledge-library/` at the repo root, merging with existing topic folders when they overlap. Curation, not 1-to-1 copy.

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

The Presenter Agent introduces itself on the first turn. Your talk folders live under `talks/` on your local disk, so source uploads in Step 2 are just drag-and-drop (or `cp`) into `talks/<folder>/knowledge/articles/` and `talks/<folder>/knowledge/llm-chats/`.

### Option 2 — Claude Code on the web (Cowork)

1. Push this repo to GitHub (or any Git host Claude Code on the web supports).
2. Open [claude.com/code](https://claude.com/code) and connect the repo as a workspace.
3. Start a new session against the repo — the agent boots from `CLAUDE.md` the same way as in the CLI.

In the web/Cowork flow, upload source files (PDFs, chat ZIPs, images) via the session's file attachment UI; the agent will place them under the active talk's `knowledge/articles/` or `knowledge/llm-chats/` folder before Step 3 (Corpus).

### Option 3 — Claude Code Cowork on Desktop

1. Install the Claude Code desktop app (Mac or Windows) from [claude.com/download](https://claude.com/download) and sign in.
2. Connect the repo to Cowork in one of two ways:
   - **Local folder** — point Cowork at your cloned `talksmith/` directory on disk (same as Option 1, but driven from the desktop UI instead of the terminal).
   - **GitHub-backed workspace** — connect the GitHub repo, same as Option 2; the desktop app uses the cloud workspace.
3. Open a new session on the workspace — the agent boots from `CLAUDE.md` automatically.

The desktop app is the most ergonomic option day-to-day: drag-and-drop source uploads into `knowledge/articles/` and `knowledge/llm-chats/` work natively, and you can keep `draft.md` open in an external editor (VS Code, Obsidian) alongside the Cowork session for the Step 5 Review loop.

### What happens next

In either mode, the Presenter Agent will:

1. Introduce itself and show the workflow chart.
2. Load [`config/profile.md`](config/profile.md) if filled, or offer to fill it (Step 0.5).
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
  [3] Corpus       -- librarian: sources -> knowledge/corpus/*.md + <source-stem>/images/
       v
  [4] Draft       <-- one of three modes (A Interview / B Agent Draft / C Outline)
                     editor writes; composer critiques at every milestone
       v
  [5] Review      <-- presenter edits draft.md; loops N times
       v
  [6] Polish       -- editor: cp draft.md -> final.md (draft.md frozen here);
                     illustrator: ASCII -> SVG; editor: consolidate images,
                     rescue open feedback, clean final.md
       v
  [7] Learnings    -- promote >=3x recurring feedback to learnings.md
       v
  [8] Render PPTX  -- md-to-pptx (optional, Cowork only)
```

Step 0 (Introduce) runs automatically on session start and isn't shown above. The full step-by-step instructions live in [CLAUDE.md](CLAUDE.md).

### Draft has three modes

When filling `draft.md` from empty, the presenter picks how to work:

- **Interview** — agent asks structured questions, presenter answers.
- **Agent Draft** — agent reads the corpus + profile, drafts everything, then asks targeted clarifying questions.
- **Presenter Outline** — presenter supplies sections + slide titles, agent fills the body from the corpus.

### Review is a loop

The first Draft is rarely final. In Review, the presenter opens `draft.md` in their editor of choice (VS Code, Obsidian, plain text — anything), drops plain-text feedback bullets inside `Presenter feedback` fields:

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
├── config/                            # fork-level configuration + accumulated editorial state
│   ├── profile.md                     # presenter's filled-in profile (created from template in Step 0.5; gitignored if personal)
│   ├── principles.md                  # what makes a good presentation (loaded at session start)
│   ├── learnings.md                   # durable rules promoted from feedback patterns
│   ├── feedback-backlog.md            # cross-Talk feedback log
│   ├── feedback-processed.md          # archived feedback promoted to learnings
│   ├── image-styles/                  # SVG style spec + recurring shape templates (illustrator/ascii-to-svg)
│   └── template.pptx                  # PowerPoint reference template (Step 8 Render)
├── talks/
│   └── <talk-folder>/                 # one folder per talk
│       ├── draft.md                   # the working outline (Steps 1–5, presenter edits this)
│       ├── final.md                   # the polished deliverable (produced in Step 6 from draft.md)
│       ├── memory.md                  # progress log / restore point
│       ├── knowledge/
│       │   ├── articles/              # PDFs, HTML, papers
│       │   ├── llm-chats/             # ZIP exports of LLM chat sessions
│       │   ├── web/                   # captured pages (one folder per URL, written by talksmith:ingest)
│       │   └── corpus/                # Librarian's structured Markdown output + per-source <stem>/images/ companion folders
│       ├── images/                    # SVGs rendered in Step 6 (Polish) + consolidated images
│       └── output/                    # rendered .pptx (Step 8, optional)
└── .claude/
    ├── settings.json                  # shared Claude Code settings
    ├── settings.local.json            # local overrides (gitignored)
    ├── schemas/                       # file-format specs (each holds spec + canonical empty form)
    │   ├── draft.md                   # talks/<Talk>/draft.md schema — also documents how final.md is derived from it (seeds the working file in Step 4)
    │   ├── memory.md                  # talks/<Talk>/memory.md schema (per-Talk progress log / resume point)
    │   ├── profile.md                 # config/profile.md schema (seeds the profile in Step 0.5)
    │   ├── principles.md              # config/principles.md schema (composer's design defaults)
    │   ├── learnings.md               # config/learnings.md schema (promoted rules)
    │   ├── feedback-backlog.md        # config/feedback-backlog.md schema (cross-Talk feedback log)
    │   ├── feedback-processed.md      # config/feedback-processed.md schema (promoted-feedback archive)
    │   └── corpus-record.md          # talks/<Talk>/knowledge/corpus/<file>.md schema (librarian's per-source records + companion folders)
    ├── roles/
    │   ├── librarian.md               # Librarian role spec
    │   ├── composer.md                # Composer role spec (design critic)
    │   ├── editor.md                  # Editor role spec (draft.md → final.md / memory.md maintainer)
    │   ├── illustrator.md             # Illustrator role spec (ASCII → SVG coordinator)
    │   └── global-librarian.md        # Global-Librarian role spec (cross-Talk curator of knowledge-library/)
    └── skills/
        ├── ingest/                    # talksmith:ingest — capture a web page into knowledge/web/
        ├── ascii-to-svg/              # talksmith:ascii-to-svg — render one ASCII block to one SVG
        └── md-to-pptx/                # talksmith:md-to-pptx — render final.md to .pptx (Step 8)
```

## Key conventions

- **Folder names are kebab-case** (e.g. `gan-networks`, `quantum-computing-intro`).
- **Cite sources by filename.** Slide `Sources` reference files under `knowledge/corpus/` (e.g. `corpus/transformer-paper.pdf.md`).
- **Never silently drop content.** Anything removed goes to `Cut material` or `Open questions` in `draft.md`.
- **Chat-prompt is the canonical interaction.** The agent asks every decision in chat with 2–4 numbered prose options derived from current context. Genuinely open questions (e.g. "what's your thesis?") fall back to free-text.
- **`config/profile.md` is session-wide context.** Once filled, it's loaded automatically and kept in context across all role work.
- **`memory.md` is append-only.** Updated after every completed step; used to resume an in-progress talk.

## Author

Paulo Gustavo Veiga — [@veigap](https://github.com/veigap)

## License

[Unlicense](LICENSE) — released into the public domain.
