# Talksmith

**Talksmith** is a Presenter Agent that helps a human presenter turn raw exploration — articles, papers, LLM chat sessions, screenshots, notes — into a well-structured presentation outline (`master.md`), and optionally renders it to PowerPoint.

It is **not** a slide generator. The deliverable is a single structured Markdown file describing the deck: thesis, agenda, sections, slides, sources, and speaker notes. Downstream tooling consumes that file to render slides.

## How it works

Three roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `knowledge/compile/`. Preserves; does not compress.
- **Editor** — challenges the presenter on thesis clarity, audience fit, narrative arc, and evidence. Pushes back when something is vague or unsupported.
- **Scribe** — keeps `master.md` and `memory.md` current as the single source of truth. Every decision lands in the file; nothing important lives only in chat.

The Editor role is handled directly by the orchestrator. Librarian and Scribe run as dedicated subagents at [.claude/agents/](.claude/agents/).

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
3. Launch Claude Code from the repo root:
   ```bash
   claude
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
2. Load [`profile.md`](profile.md) if filled, or offer to fill it (Step 0.5).
3. Ask via `AskUserQuestion` whether you're starting a **new** talk or **resuming** an existing one under `talks/`.

Everything else flows from there. For the full operating spec, see [CLAUDE.md](CLAUDE.md).

## Workflow

```
  TALKSMITH WORKFLOW
  ==================

  [1] Scaffold   <-- presenter: topic + folder name
       v
  [2] Collect    <-- presenter: upload PDFs/papers, chat ZIPs
       v
  [3] Compile     -- Librarian: sources -> knowledge/compile/*.md  (auto)
       v
  [4] Draft      <-- presenter (one of three modes)
       v
  [5] Review     <-- presenter edits master.md in their editor; loops N times
       v
     master.md ready
       v
  [6] Render      -- md-to-ppt skill: master.md + template -> .pptx (optional)
```

Steps 0 (Introduce) and 4 (Template copy) happen automatically and are not shown above. The full step-by-step instructions live in [CLAUDE.md](CLAUDE.md).

### Draft has three modes

When filling `master.md` from empty, the presenter picks how to work:

- **Interview** — agent asks structured questions, presenter answers.
- **Agent Draft** — agent reads compiled knowledge + profile, drafts everything, then asks targeted clarifying questions.
- **Presenter Outline** — presenter supplies sections + slide titles, agent fills the body from compiled knowledge.

### Review is a loop

The first Draft is rarely final. In Review, the presenter opens `master.md` in their editor of choice (VS Code, Obsidian, plain text — anything), drops plain-text feedback bullets inside `Presenter feedback` fields:

```
**Presenter feedback:**
- "this slide is too dense; trim to 90 seconds"
- "swap with the slide above"
```

The Scribe then stamps each bullet with status + date (`[open] 2026-05-12 — "..."`), applies the change, and flips the bullet to `[closed]` with a `Resolution:` line. Closed entries are never deleted — they're the audit trail for why each slide looks the way it does.

Review repeats as many times as needed until the presenter declares the document final.

## Repo layout

```
.
├── README.md                      # this file
├── CLAUDE.md                      # full agent instructions (Talksmith spec)
├── profile.md                     # global presenter profile (persistent context)
├── workflow-diagram.md            # Mermaid diagrams of the flow
├── templates/
│   ├── master-template.md         # canonical structure of master.md
│   └── template.pptx              # default PowerPoint template (Step 6 Render)
├── talks/
│   └── <talk-folder>/             # one folder per talk
│       ├── master.md              # the outline (deliverable)
│       ├── memory.md              # progress log / restore point
│       └── knowledge/
│           ├── articles/          # PDFs, HTML, papers
│           ├── llm-chats/         # ZIP exports of LLM chat sessions
│           └── compile/           # Librarian's structured Markdown output
└── .claude/
    ├── agents/
    │   ├── librarian.md           # Librarian subagent prompt
    │   └── scribe.md              # Scribe subagent prompt
    └── skills/
        └── md-to-ppt/SKILL.md     # Optional renderer (Step 6)
```

## Key conventions

- **Folder names are kebab-case** (e.g. `gan-networks`, `quantum-computing-intro`).
- **Cite sources by filename.** Slide `Sources` reference files under `knowledge/compile/` (e.g. `compile/transformer-paper.md`).
- **Never silently drop content.** Anything removed goes to `Cut material` or `Open questions` in `master.md`.
- **`AskUserQuestion` is the default interaction.** The agent proposes 2–4 concrete options for every decision rather than leaving the presenter to free-text. Genuinely open questions (e.g. "what's your thesis?") fall back to free-text.
- **`profile.md` is session-wide context.** Once filled, it's loaded automatically and passed into every subagent dispatch.
- **`memory.md` is append-only.** Updated after every completed step; used to resume an in-progress talk.

## Author

Paulo Gustavo Veiga — [@veigap](https://github.com/veigap)

## License

[Unlicense](LICENSE) — released into the public domain.
