# Roles & architecture

The internals behind Talksmith's user experience. For what using Talksmith *feels* like — the chat-driven workflow and the Markdown you end up with — see the [README](../README.md); this document is the implementational reference.

## The Presenter Agent

Talksmith ships a **Presenter Agent**: an orchestrator that drives the [eight-step workflow](../README.md#how-a-talk-gets-made) and dispatches five role-specific Claude Code subagents as each step needs them. One file is always the source of truth — `draft.md` through Review, `final.md` after Polish. The presenter never dispatches an agent by hand; the orchestrator does, and narrates outcomes in plain language.

## The five roles

- **Librarian** — restructures raw sources (PDFs, papers, chat ZIP exports, images) into a uniform Markdown knowledge base under `research/corpus/`, one record per source with a companion `<source-stem>/images/` folder so the corpus is self-contained. Preserves; does not compress. Runs in Step 3.
- **Composer** — the brain. Reviews drafted slides against thesis, audience, sources, design principles, and rules promoted from prior Talks; returns a punch-list of critiques. Read-only batch reviewer, invoked at every drafting milestone in Step 4.
- **Editor** — the muscle. Keeps `draft.md`, `final.md`, and `memory.md` current: bootstraps the file, transcribes decisions, drafts prose from corpus records, applies feedback, then in Step 6 copies `draft.md` → `final.md` and cleans it for delivery.
- **Diagram-Diagram-Illustrator** — converts every ASCII diagram in `final.md` into a styled SVG during Polish (Step 6).
- **Global-Librarian** — cross-Talk curator. On Step 8 promotion, curates reusable, topic-organized knowledge from the finalized Talk into a shared `knowledge-library/` at the repo root. Curation, not 1-to-1 copy.

Role specs live under [`agents/`](../agents/) and are dispatched as Claude Code subagents from [`orchestrator.md`](../orchestrator.md), the full operating spec loaded at session start by the [`talksmith-orch.md`](../talksmith-orch.md) stub.

## Skills

Skills live under [`skills/`](../skills/) and are invoked by name (namespaced `talksmith:<skill>`):

- **`ingest`** — fetch a URL into `research/web/` (HTML + Markdown extraction + referenced images).
- **`ascii-to-svg`, `polish-ascii`** — render and clean ASCII diagrams into styled SVGs.
- **`md-to-deck`** — decompose `final.md` into a structured `slide-model.json` and render it to an HTML (Reveal.js) deck or a `.pptx`.
- **`feedback-cycle`** — Step-5/Step-6 mechanical bookkeeping (stamp / close / mirror / rescue feedback).
- **Reverse pipeline** (`pptx-extract`, `pptx-diff`, `pptx-merge`) — reconcile an externally-edited `.pptx` back into `draft.md`. See [reverse-pipeline.md](reverse-pipeline.md).
- **`pptx-learn`** — diff a hand-corrected deck against the generated baseline to surface recurring conformance patterns.

## The render pipeline

Talksmith renders from a structured **`slide-model.json`** (schema: [`schemas/slide-model.md`](../schemas/slide-model.md)) — the intermediate the `md-to-deck` skill produces by having an LLM decompose `final.md` into per-slide `{template, …fields…, notes}`. The renderer then maps those fields onto templates *mechanically*; it does no classification. The same model feeds both the HTML deliverable and the PPTX renderer, so the two stay in sync. Slides are always a *projection* of the Markdown — never the source of truth.
