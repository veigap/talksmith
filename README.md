# Talksmith

**Talksmith** is a Presenter Agent that helps a human presenter turn raw exploration — articles, papers, LLM chat sessions, screenshots, notes — into a well-structured presentation outline (`master.md`), and optionally renders it to PowerPoint.

It is **not** a slide generator. The deliverable is a single structured Markdown file describing the deck: thesis, agenda, sections, slides, sources, and speaker notes. Downstream tooling consumes that file to render slides.

## How it works

Three roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `knowledge/compile/`. Preserves; does not compress.
- **Editor** — challenges the presenter on thesis clarity, audience fit, narrative arc, and evidence. Pushes back when something is vague or unsupported.
- **Scribe** — keeps `master.md` and `memory.md` current as the single source of truth. Every decision lands in the file; nothing important lives only in chat.

The Editor role is handled directly by the orchestrator. Librarian and Scribe run as dedicated subagents at [.claude/agents/](.claude/agents/).

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

## Getting started

Open the repo with a Claude Code session. The Presenter Agent will introduce itself, show the workflow, and ask via `AskUserQuestion` whether you're starting a new talk or resuming an existing one. Everything else flows from there.

For the full operating spec, see [CLAUDE.md](CLAUDE.md).
