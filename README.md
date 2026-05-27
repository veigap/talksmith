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
- **Corpus — preserve, don't summarize.** Drop papers and notes into `research/articles/`, export worthwhile chat sessions to ZIP under `research/llm-chats/`. The Librarian restructures every source into uniform Markdown — contradictions, abandoned threads, and course-corrections preserved — and copies every image into per-source companion folders so the corpus is self-contained. The next phase works from your actual thinking, not a blank prompt.
- **Draft — thesis-first, sourced.** Every slide is challenged against a one-sentence thesis and cited back to a corpus record. Talksmith won't invent content out of thin air.
- **Refine — audit-tracked loop.** Feedback bullets land in `draft.md` in your editor of choice; cut material and closed feedback stay in the file as an audit trail, never silently deleted. Step 6 (Polish) makes a separate `final.md` so polishing never overwrites the audit trail — you can re-run Polish as many times as you want against the same untouched `draft.md`.

One substrate underneath all of it: **Markdown.** Corpus records, the outline (`draft.md` → `final.md`), the progress log (`memory.md`), feedback rounds — every artifact is a plain `.md` file. Diffable, versionable, editable in any tool, portable across renderers. Slides are a *projection* of the Markdown, not the source of truth.

If that doesn't fit how you work, this is the wrong tool.

## One working directory per subject

Talksmith expects **one working directory per subject** — a university course, a recurring workshop, a research area you keep presenting in. The plugin is installed once into Claude Code; you run `/talksmith:init` separately in each subject directory. Inside that directory, `talks/` accumulates class by class: every Talk you give on the subject lives in the same place.

This isn't about disk hygiene — it's about compounding value over time:

- **Corpus knowledge is reusable across classes.** A paper indexed into the corpus in class 3 is still queryable for class 7. Each subject directory becomes a domain-specific knowledge base.
- **`profile.md` calibrates to one audience.** "AI students in Biomedicine, undergraduate" is set once and inherited by every class in the directory. Different subject → different directory → different audience defaults. No global state to bleed.
- **`learnings.md` accumulates per-subject editorial taste.** Recurring feedback ("don't open with the algorithm — open with the dataset") promoted in Step 7 applies to the next class on the same subject, not to unrelated topics.
- **The audit trail stays scoped.** Feedback backlog, cut material, and open questions live next to the subject they came from. No cross-subject contamination.

If you present on three subjects, that's three working directories. Mixing subjects in one directory erodes every advantage above.

**Keeping the plugin current.** The plugin and your subject working directories are now decoupled: subject directories hold only your data plus a **thin `CLAUDE.md` stub** (~30 lines) that points at the plugin install. The operating spec itself — workflow, role contracts, schemas — lives entirely under `${CLAUDE_PLUGIN_ROOT}/` and updates through the normal plugin update mechanism (`/plugin update talksmith` in the CLI, or the desktop app's plugin manager). Because your `CLAUDE.md` is just a stub, **plugin updates flow straight through without re-running `/talksmith:init`** — the agent reads the latest orchestrator spec from the plugin on every session reload. The only time you'd re-init is if a plugin upgrade explicitly changes the session-start contract (new mandatory load, new directive); the upgrade notes will say so. No fork-sync, no `talksmith:upgrade` workflow, no master vs. user-owned path table to memorize.

## How it works

Five roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `research/corpus/`, with a companion `<source-stem>/images/` folder per source so the corpus is self-contained. Preserves; does not compress.
- **Composer** — the brain. Reviews drafted slides against thesis, audience, sources, design principles, and learned rules promoted from prior Talks; returns a punch-list of critiques. Read-only batch reviewer, invoked at every drafting milestone.
- **Editor** — the muscle. Keeps `draft.md` (Steps 1–5), `final.md` (Step 6+), and `memory.md` current as the single source of truth: bootstraps from template, transcribes presenter decisions, drafts prose from corpus records, applies feedback in `draft.md`, then in Step 6 copies `draft.md` → `final.md` and cleans `final.md` for delivery.
- **Illustrator** — converts every ASCII diagram in `final.md` into a styled SVG during the Polish step.
- **Global-Librarian** — cross-Talk curator. On Step 7 promotion, reads the finalized Talk's corpus + `final.md` and curates reusable, topic-organized knowledge into a shared `knowledge-library/` at the repo root, merging with existing topic folders when they overlap. Curation, not 1-to-1 copy.

Role specs live at [agents/](agents/) and are dispatched as Claude Code subagents from the orchestrator ([`orchestrator.md`](orchestrator.md) — loaded at session start by the [`talksmith-orch.md`](talksmith-orch.md) stub that `/talksmith:init` copies into your working directory). Skills live at [skills/](skills/) and are invoked by name (`talksmith:ascii-to-svg`, `talksmith:polish-ascii`, `talksmith:md-to-pptx`, etc.).

## Install

Talksmith ships as a **Claude Code plugin**: install once, then run `/talksmith:init` inside each subject working directory to scaffold the per-subject files. The plugin contains the orchestrator spec, the five subagents, the seven skills, the schemas, design principles, and the PPTX style packs; your subject directory holds only your own data.

### Claude Code CLI (terminal)

1. Install the CLI if you don't already have it:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
2. Install the plugin. Two ways, depending on whether you want a tracked install from GitHub or a local checkout for development:
   - **From GitHub** (recommended for normal use) — inside any Claude Code session, run:
     ```
     /plugin marketplace add veigap/talksmith
     /plugin install talksmith@talksmith
     ```
     Updates later: `/plugin update talksmith`.
   - **From a local clone** (recommended if you want to modify the plugin) — clone the repo and point Claude Code at it as a local plugin:
     ```bash
     git clone https://github.com/veigap/talksmith.git ~/plugins/talksmith
     ```
     Then inside Claude Code:
     ```
     /plugin marketplace add ~/plugins/talksmith
     /plugin install talksmith@talksmith
     ```
3. Make a subject working directory and initialize it:
   ```bash
   mkdir -p ~/talks/ai-in-biomedicine && cd ~/talks/ai-in-biomedicine
   claude --model opus
   ```
   Inside the session:
   ```
   /talksmith:init
   ```
   This drops a thin `CLAUDE.md` stub into the working directory — that's the only file `/talksmith:init` writes. The stub instructs the agent to load the full operating spec from `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` at session start. Everything else (`config/profile.md`, `config/learnings.md`, the feedback logs, `talks/<folder>/…`) is created on demand by the orchestrator's Editor subagent in Step 0.5 / Step 1, bootstrapping from the *Canonical empty form* sections inside the plugin's [`schemas/`](schemas/). `/talksmith:init` is no-clobber and rarely needs to be re-run — plugin updates flow through automatically without touching this `CLAUDE.md`.
4. Reload the Claude Code session (or start a new one in this directory). Say "Hi Talksmith" — the stub tells the agent to read the orchestrator spec from the plugin, then the Presenter Agent introduces itself and walks Step 0 → Step 0.5 → Step 1 from there.

Your talk folders live under `talks/` on your local disk, so source uploads in Step 2 are just drag-and-drop (or `cp`) into `talks/<folder>/research/articles/` and `talks/<folder>/research/llm-chats/`.

### Cowork (desktop app)

1. Install the Claude Code desktop app (Mac or Windows) from [claude.com/download](https://claude.com/download) and sign in.
2. Open the plugin manager in the desktop app and add the marketplace `veigap/talksmith`, then install the **talksmith** plugin. (Same plugin install as the CLI — the desktop app and CLI share the install.)
3. Create or open a workspace for your subject — either a local folder on disk or a GitHub-backed cloud workspace. The workspace folder is your **subject working directory**; do not point it at the plugin repo.
4. Start a session in the workspace and run:
   ```
   /talksmith:init
   ```
   Same scaffolding as the CLI flow. After it finishes, kick off the agent with any message.

The desktop app is the most ergonomic option day-to-day: drag-and-drop source uploads into `research/articles/` and `research/llm-chats/` work natively, and you can keep `draft.md` open in an external editor (VS Code, Obsidian) alongside the Cowork session for the Step 5 Review loop. **Step 8 (Render PPTX) only works in Cowork** — it relies on Anthropic's native `pptx` skill which isn't available in the CLI.

### What happens next

In either mode, after `/talksmith:init`, the Presenter Agent will:

1. Introduce itself and show the workflow chart.
2. Load [`config/profile.md`](config/profile.md) if filled, or offer to fill it (Step 0.5).
3. Ask in chat (with numbered options) whether you're starting a **new** talk or **resuming** an existing one under `talks/`.

Everything else flows from there. The full operating spec lives at [`orchestrator.md`](orchestrator.md) in the plugin install; the small [`talksmith-orch.md`](talksmith-orch.md) stub copied into your working directory by `/talksmith:init` is what loads it at session start.

## Workflow

```
  TALKSMITH WORKFLOW
  ==================

  [1] Frame       <-- presenter: topic + folder name
       v
  [2] Collect     <-- presenter: upload PDFs/papers, chat ZIPs, URLs
       v
  [3] Corpus       -- librarian: sources -> research/corpus/*.md + <source-stem>/images/
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

Step 0 (Introduce) runs automatically on session start and isn't shown above. The full step-by-step instructions live in [orchestrator.md](orchestrator.md); the small [talksmith-orch.md](talksmith-orch.md) stub copied into your subject working directory by `/talksmith:init` tells the agent to load that spec on every session.

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

## Layout

There are two layouts to know: the **plugin layout** (what's in this repo, installed as `talksmith` in Claude Code) and the **subject working directory layout** (what `/talksmith:init` produces in your cwd).

### Plugin layout (this repo)

```
.
├── README.md                          # this file
├── CLAUDE.md                          # plugin development notes (for contributors editing this repo)
├── talksmith-orch.md                     # thin stub (~30 lines) — copied into user cwd as CLAUDE.md by /talksmith:init
├── orchestrator.md                    # full Presenter Agent operating spec — loaded at session start via the stub; stays in the plugin install
├── .claude-plugin/
│   └── plugin.json                    # plugin manifest
├── agents/                            # five Claude Code subagents (dispatched by name)
│   ├── librarian.md
│   ├── composer.md
│   ├── editor.md
│   ├── illustrator.md
│   └── global-librarian.md
├── commands/
│   └── init.md                        # /talksmith:init slash command
├── skills/
│   ├── ingest/                        # talksmith:ingest — capture a web page into research/web/
│   ├── ascii-to-svg/                  # talksmith:ascii-to-svg — render one ASCII block to one SVG
│   ├── polish-ascii/                  # talksmith:polish-ascii — Step-6 scan + extract + cleanup
│   ├── feedback-cycle/                # talksmith:feedback-cycle — Step-5 stamp/close/mirror helper
│   ├── find-open-notes/               # talksmith:find-open-notes — detect unstamped feedback bullets
│   └── md-to-pptx/                    # talksmith:md-to-pptx — render final.md to .pptx (Step 8, Cowork only)
├── schemas/                           # file-format specs (each holds spec + canonical empty form)
│   ├── draft.md
│   ├── memory.md
│   ├── profile.md
│   ├── principles.md
│   ├── learnings.md
│   ├── feedback-backlog.md
│   ├── feedback-processed.md
│   └── corpus-record.md
└── config/                            # bundled read-only assets
    ├── principles.md                  # what makes a good presentation (loaded at composer reviews)
    ├── diagram-style.md               # standing visual rules the ascii-to-svg skill applies
    └── pptx-styles/{strict,free-form}/   # PPTX style packs (spec + base template)
```

There is no `templates/` folder. `/talksmith:init` copies a single file (`talksmith-orch.md` → cwd `CLAUDE.md`) — a ~30-line stub that points the agent at [`orchestrator.md`](orchestrator.md). Everything else — `config/profile.md`, `config/learnings.md`, the feedback logs, and the per-Talk directory tree under `talks/` — is created on demand by the orchestrator once the stub loads it, bootstrapping from the *Canonical empty form* sections inside each [`schemas/`](schemas/) spec.

### Subject working directory layout (after `/talksmith:init`)

```
<your-subject-dir>/
├── CLAUDE.md                          # thin stub copied from the plugin's talksmith-orch.md — Claude Code auto-loads this, which in turn loads ${CLAUDE_PLUGIN_ROOT}/orchestrator.md
├── config/
│   ├── profile.md                     # filled in Step 0.5 (Subject, Presenter, audience, …)
│   ├── learnings.md                   # durable rules promoted from feedback patterns
│   ├── feedback-backlog.md            # cross-Talk feedback log
│   └── feedback-processed.md          # archived feedback promoted to learnings
└── talks/
    └── <talk-folder>/                 # one folder per talk
        ├── draft.md                   # the working outline (Steps 1–5, presenter edits this)
        ├── final.md                   # the polished deliverable (produced in Step 6 from draft.md)
        ├── memory.md                  # progress log / restore point
        ├── research/
        │   ├── articles/              # PDFs, HTML, papers
        │   ├── llm-chats/             # ZIP exports of LLM chat sessions
        │   ├── web/                   # captured pages (one folder per URL, written by talksmith:ingest)
        │   └── corpus/                # Librarian's structured Markdown output + per-source <stem>/images/ companion folders
        ├── images/                    # SVGs rendered in Step 6 (Polish) + consolidated images
        └── output/                    # rendered .pptx (Step 8, optional, Cowork only)
```

Everything the plugin needs at runtime is reached via `${CLAUDE_PLUGIN_ROOT}/…` from inside the working directory. The plugin and the subject directory never collide.

## Key conventions

- **Folder names are kebab-case** (e.g. `gan-networks`, `quantum-computing-intro`).
- **Cite sources by filename.** Slide `Sources` reference files under `research/corpus/` (e.g. `corpus/transformer-paper.pdf.md`).
- **Never silently drop content.** Anything removed goes to `Cut material` or `Open questions` in `draft.md`.
- **Chat-prompt is the canonical interaction.** The agent asks every decision in chat with 2–4 numbered prose options derived from current context. Genuinely open questions (e.g. "what's your thesis?") fall back to free-text.
- **`config/profile.md` is session-wide context.** Once filled, it's loaded automatically and kept in context across all role work.
- **`memory.md` is append-only.** Updated after every completed step; used to resume an in-progress talk.

## Author

Paulo Gustavo Veiga — [@veigap](https://github.com/veigap)

## License

[Unlicense](LICENSE) — released into the public domain.
