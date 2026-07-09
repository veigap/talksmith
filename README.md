# Talksmith

**Talksmith** is a Claude Code plugin that ships a Presenter Agent — an orchestrator, five role-specific subagents (Librarian, Composer, Editor, Illustrator, Global-Librarian), and a set of skills — to help a human presenter turn raw exploration (articles, papers, LLM chat sessions, screenshots, notes) into a structured presentation outline (`draft.md`), then a polished deliverable (`final.md`), and optionally a rendered PowerPoint. Install it once into Claude Code; run `/talksmith:init` inside each subject repo to scaffold per-subject files.

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

## One shared repo per subject

Talksmith's expected setup is **one repository per subject, shared by all the presenters who teach it** — a university course's lecturer team, a workshop's rotating instructors, a research group that takes turns presenting. The plugin is installed once into each presenter's Claude Code; the **subject directory itself is a Git repo** (or a GitHub-backed Cowork workspace) that the team pushes to and pulls from like any other codebase. `/talksmith:init` is run once at repo creation; from then on every presenter who clones the repo is set up by virtue of having the stub `CLAUDE.md` already in it.

Inside that repo, `talks/` accumulates class by class across the whole team: every Talk anyone gives on the subject lives in the same place. This isn't disk hygiene — it's how the subject's knowledge compounds across presenters and across semesters:

- **Corpus knowledge is reusable across classes and across presenters.** A paper Alice indexed for class 3 is queryable when Bob preps class 7. The subject directory becomes a shared, domain-specific knowledge base owned by the team.
- **`profile.md` calibrates to the subject's audience, not to any one presenter.** "AI students in Biomedicine, undergraduate" is set once and inherited by every class. The `Presenter:` field can hold one name or several (one per line) — whichever presenter is actually giving a given class overrides it per-Talk in `draft.md` frontmatter, while the audience / consumption-mode / duration / language stay constant.
- **`learnings.md` accumulates the team's editorial taste.** Recurring feedback ("don't open with the algorithm — open with the dataset") promoted in Step 7 applies to every future class anyone teaches on the subject. New team members inherit the accumulated style automatically.
- **The audit trail stays scoped and visible to the team.** Feedback backlog, cut material, and open questions live next to the subject they came from, in Git history that everyone on the team can read.
- **`knowledge-library/`** (built by the Global-Librarian on Step 7 promotion) is the team's curated cross-Talk index of topics, also shared via the repo.

### Collaboration mechanics

Treat the subject repo like any code repo: branch per Talk if multiple presenters work simultaneously, merge when each Talk is finalized, resolve conflicts in `learnings.md` / `feedback-backlog.md` as you would in any shared file. Cowork's GitHub-backed cloud workspaces handle this natively; CLI users can use plain Git. The plugin install itself is per-presenter (each laptop) and not part of the repo — so plugin upgrades land independently of subject data.

If the team presents on three subjects, that's three repos. Mixing subjects in one repo erodes every advantage above.

**Keeping the plugin current.** The plugin and your subject working directories are now decoupled: subject directories hold only your data plus a **thin `CLAUDE.md` stub** (~30 lines) that points at the plugin install. The operating spec itself — workflow, role contracts, schemas — lives entirely under `${CLAUDE_PLUGIN_ROOT}/` and updates through the normal plugin update mechanism (`/plugin update talksmith` in the CLI, or the desktop app's plugin manager). Because your `CLAUDE.md` is just a stub, **plugin updates flow straight through without re-running `/talksmith:init`** — the agent reads the latest orchestrator spec from the plugin on every session reload. The only time you'd re-init is if a plugin upgrade explicitly changes the session-start contract (new mandatory load, new directive); the upgrade notes will say so. No fork-sync, no `talksmith:upgrade` workflow, no master vs. user-owned path table to memorize.

## Install

Talksmith ships as a **Claude Code plugin** — each presenter installs it once on their machine; the **subject repo** (a Git repository shared by the team) is set up once and cloned by everyone who teaches the subject.

### Step 1 — Create the subject repo *(strongly recommended: GitHub)*

Before installing anything, create the home for your subject's material: a Git repository that every presenter on the team will clone and push to. **Strongly recommended: a GitHub repository** (private or public, your call) — it gives the team an off-machine source of truth, history, and conflict resolution for the shared files (`config/learnings.md`, `config/feedback-backlog.md`, `knowledge-library/`, and the `talks/` tree). Cowork users can equivalently create a GitHub-backed cloud workspace; CLI users clone the repo locally with `git`. A purely local folder works for a single presenter, but you lose the team sharing the rest of the design is built around — don't pick this if anyone else might teach the subject.

```bash
# CLI example — create on GitHub first, then:
git clone git@github.com:<your-team>/ai-in-biomedicine.git
cd ai-in-biomedicine
```

One repo per subject. If your team presents on three subjects, create three repos. Don't mix subjects in one repo (see [*One shared repo per subject*](#one-shared-repo-per-subject) for why).

### Step 2 — Install the plugin (each presenter, once)

**Claude Code CLI** — install the CLI, then add Talksmith from the marketplace:

```bash
npm install -g @anthropic-ai/claude-code
```

Then inside any Claude Code session:

```
/plugin marketplace add veigap/talksmith
/plugin install talksmith@talksmith
```

Updates later: `/plugin update talksmith`. (If you want to modify the plugin yourself, clone the repo and `/plugin marketplace add ~/plugins/talksmith` instead — see [`CLAUDE.md`](CLAUDE.md).)

**Cowork (desktop app)** — install from [claude.com/download](https://claude.com/download), sign in, open the plugin manager, add the `veigap/talksmith` marketplace, install **talksmith**. The desktop app and CLI share the install. **Step 8 (Render PPTX) only works in Cowork** — it depends on Anthropic's native `pptx` skill which isn't available in the CLI.

### Step 3 — Initialize the repo (once, by the first presenter)

The first time anyone on the team opens the subject repo in Claude Code, run:

```
/talksmith:init
```

This drops a thin `CLAUDE.md` stub into the repo — the only file `/talksmith:init` writes. Commit and push it. Every other presenter who clones the repo afterward will get the stub automatically and does **not** need to run `/talksmith:init` again. The stub auto-loads the plugin's spec on every session, so plugin upgrades flow through without re-init.

### Step 4 — Start a session

CLI:

```bash
cd ai-in-biomedicine
claude --model opus
```

Cowork: open the workspace.

Say *"Hi Talksmith"*. The Presenter Agent introduces itself, loads [`config/profile.md`](config/profile.md) (or walks you through filling it in Step 0.5 if it's the repo's first session), and asks whether you're starting a **new** Talk or **resuming** an existing one under `talks/`. From there, follow the workflow.

---

## How it works

Five roles, one file as source of truth:

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `research/corpus/`, with a companion `<source-stem>/images/` folder per source so the corpus is self-contained. Preserves; does not compress.
- **Composer** — the brain. Reviews drafted slides against thesis, audience, sources, design principles, and learned rules promoted from prior Talks; returns a punch-list of critiques. Read-only batch reviewer, invoked at every drafting milestone.
- **Editor** — the muscle. Keeps `draft.md` (Steps 1–5), `final.md` (Step 6+), and `memory.md` current as the single source of truth: bootstraps from template, transcribes presenter decisions, drafts prose from corpus records, applies feedback in `draft.md`, then in Step 6 copies `draft.md` → `final.md` and cleans `final.md` for delivery.
- **Illustrator** — converts every ASCII diagram in `final.md` into a styled SVG during the Polish step.
- **Global-Librarian** — cross-Talk curator. On Step 7 promotion, reads the finalized Talk's corpus + `final.md` and curates reusable, topic-organized knowledge into a shared `knowledge-library/` at the repo root, merging with existing topic folders when they overlap. Curation, not 1-to-1 copy.

Role specs live at [agents/](agents/) and are dispatched as Claude Code subagents from the orchestrator ([`orchestrator.md`](orchestrator.md) — loaded at session start by the [`talksmith-orch.md`](talksmith-orch.md) stub that `/talksmith:init` copies into your working directory). Skills live at [skills/](skills/) and are invoked by name (`talksmith:ascii-to-svg`, `talksmith:polish-ascii`, `talksmith:md-to-pptx`, etc.).

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
       v                (a rough preview deck renders in the background from
      (5.5) Preview      draft.md — optional, Cowork only; peek before Polish)
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

## Reconciling an externally-edited deck (reverse pipeline)

The forward pipeline is one-directional: `draft.md` → `final.md` → `output/final.pptx`. But presenters routinely open that `.pptx` in Keynote or PowerPoint and tweak it directly — fix a bullet, swap a photo, reword a speaker note. Those edits live only in the deck. The **reverse pipeline** pulls them back into `draft.md`, the editable source of truth, so the next Polish re-derives a `final.md` that reflects them.

It's three skills run in order. All artifacts land under `talks/<Talk>/reconcile/`; nothing touches `final.md` directly.

```
  final.pptx  --[pptx-extract]-->  finalpptx.md   (deck rebuilt as draft.md-shaped Markdown)
                                        v
   final.md   --[pptx-diff]------>  finalpptx.diff.json   (what changed, per slide)
                                        v
   draft.md   <--[pptx-merge]----  apply simple changes; route complex ones to the Editor
                                        v
              re-run Step 6 (Polish)  ->  final.md refreshed
```

**Prerequisite:** `pptx-extract` reads the deck via `python-pptx` — `pip install python-pptx`. The other two stages are stdlib-only. None require Cowork; the whole reverse pipeline is CLI-safe.

### 1. `pptx-extract` — deck → `finalpptx.md`

```
/talksmith:pptx-extract talks/<Talk>/output/final.pptx --talk talks/<Talk> --style <strict|free-form>
```

Parses the deck in true presentation order, classifies each slide (cover / agenda / section-divider / content), stages every content image into `reconcile/staging/` with slot-anchored names, and writes `reconcile/finalpptx.md` (in `draft.md` shape) plus a `reconcile/finalpptx.inventory.json` sidecar. `--style` is mandatory and must match the style the deck was rendered with. Thesis and Sources can't be recovered from a deck, so they come back as stubs marked with `<!-- reconstruct: … -->` for the Editor to restore.

### 2. `pptx-diff` — explain what changed

```
/talksmith:pptx-diff --final talks/<Talk>/final.md --pptx talks/<Talk>/reconcile/finalpptx.md \
  --talk talks/<Talk> --inventory talks/<Talk>/reconcile/finalpptx.inventory.json --human
```

Aligns the reconstructed slides against the original `final.md` (by section + slide number, with a title-similarity fallback for renumbered/edited slides) and reports every title, content, speaker-note, and image change — bullet-granular, with low-confidence matches flagged. Writes `reconcile/finalpptx.diff.json` for the merge step. Read-only; it never edits anything.

### 3. `pptx-merge` — reincorporate into `draft.md`

```
# See the accept/reject surface first:
/talksmith:pptx-merge plan --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md
# Then land the simple changes:
/talksmith:pptx-merge apply-auto --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md
```

Re-anchors each change structurally (by section + slide title + pre-change text, since Polish rewrites line numbers) and applies the **simple, high-confidence** ones automatically — bullet/note edits, new-image inserts, diagram overwrites. **Complex or confusing** ones (low-confidence matches, removals, added/deleted slides, ASCII-sourced images) are routed to the Editor with a reason rather than guessed. Every write is atomic and anchor-guarded. Writes only `draft.md` and `images/` — never `final.md`.

When it's done, re-run **Step 6 (Polish)** and the deck edits are back in the source of truth.

## Layout

What `/talksmith:init` produces inside your subject repo — the files you and your team actually touch:

```
<your-subject-repo>/
├── CLAUDE.md                          # thin stub written by /talksmith:init; auto-loads the plugin's spec each session — leave it alone
├── config/
│   ├── profile.md                     # filled in Step 0.5 (Subject, Presenter(s), audience, duration, language)
│   ├── learnings.md                   # durable editorial rules promoted from recurring feedback
│   ├── feedback-backlog.md            # cross-Talk feedback log (mirrored from each Talk's draft.md)
│   └── feedback-processed.md          # archived feedback that's been promoted to learnings
├── talks/
│   └── <talk-folder>/                 # one folder per Talk (one class / session / pitch)
│       ├── draft.md                   # the working outline (Steps 1–5; presenter edits this directly)
│       ├── final.md                   # the polished deliverable (produced in Step 6 from draft.md)
│       ├── memory.md                  # progress log / restore point — used to resume
│       ├── research/
│       │   ├── articles/              # drop PDFs, HTML, papers here
│       │   ├── llm-chats/             # drop chat-session ZIP exports here
│       │   ├── web/                   # captured pages (created by /talksmith:ingest)
│       │   └── corpus/                # the structured knowledge base (built in Step 3)
│       ├── images/                    # rendered diagrams + consolidated images (built in Step 6)
│       └── output/                    # rendered final.pptx (Step 8, optional, Cowork only)
└── knowledge-library/                 # team's curated cross-Talk index (built on Step 7 promotion)
```

`config/` is set up once when the repo is first initialized and then accumulates as the team learns. `talks/<talk-folder>/` is created per Talk; everything else inside it is built by the workflow as you move through the steps. `knowledge-library/` appears the first time a presenter promotes a finalized Talk in Step 7.

> The plugin's own internals (orchestrator spec, subagents, skills, schemas, design assets) live under `${CLAUDE_PLUGIN_ROOT}/` on each presenter's Claude Code install and never land in your repo. Plugin upgrades flow through `/plugin update talksmith` independently of your repo's content. Contributors editing the plugin itself should see [`CLAUDE.md`](CLAUDE.md) in the plugin repo for the developer layout.

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
