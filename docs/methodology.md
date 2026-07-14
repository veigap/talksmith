# The methodology behind Talksmith

Talksmith isn't a generic "ask an LLM to make a deck" tool. It encodes an opinionated method — and pushes back when you deviate. This document is the *why*; for how to use it, see the [README](../README.md).

## Four phases

```
  Explore  -->  Corpus   -->  Draft  -->  Refine
  (sources)    (knowledge)   (outline)    (loop)
```

- **Explore** — LLMs are your brainstorming *partner*, not the deck generator. Learn the topic, stress-test ideas, chase tangents, read papers, capture notes — actually engage with the material before structuring anything.
- **Corpus — preserve, don't summarize.** The Librarian restructures every source into uniform Markdown — contradictions, abandoned threads, and course-corrections kept — with a companion image folder per source, so the corpus is self-contained. You draft from your actual thinking, not a blank prompt.
- **Draft — thesis-first, sourced.** Every slide is challenged against a one-sentence thesis and cited back to a corpus record. Talksmith won't invent content out of thin air.
- **Refine — audit-tracked loop.** Feedback bullets land in `draft.md`; cut material and closed feedback stay in the file as an audit trail, never silently deleted. Step 6 makes a separate `final.md`, so polishing never overwrites that trail.

One substrate underneath all of it: **Markdown.** Every artifact — corpus records, the outline, the progress log, feedback rounds — is a plain `.md` file. Diffable, versionable, editable in any tool, portable across renderers. If that doesn't fit how you work, this is the wrong tool.

## A knowledge base in the Karpathy sense

Structurally, Talksmith is an instance of the **LLM wiki** pattern Andrej Karpathy described ([write-up](https://medium.com/@urvvil08/andrej-karpathys-llm-wiki-create-your-own-knowledge-base-8779014accd5)): **compilation over retrieval.** Instead of re-reading raw documents on every request (RAG), the agent *compiles* raw sources once into a persistent, cross-linked Markdown knowledge base and keeps it updated — the way source code compiles once and runs efficiently thereafter. The tedious part of a knowledge base is the bookkeeping, not the reading; Talksmith hands that to the agent so the human curates and thinks.

The pattern's **three layers** map directly onto Talksmith:

| Karpathy's LLM wiki | In Talksmith |
|---|---|
| **Raw sources** — immutable ground truth the agent reads but never rewrites | `research/articles/`, `research/llm-chats/` — papers, notes, exported chat ZIPs you drop in |
| **The wiki** — synthesized, cross-linked Markdown the agent owns | `research/corpus/*.md`, `memory.md`, `draft.md` → `final.md`, `learnings.md`, `knowledge-library/` |
| **The schema** — config that turns a generic agent into a disciplined maintainer | the `CLAUDE.md` stub → `orchestrator.md` + the canonical forms under `schemas/` |

Its **three operations** are Talksmith steps, not new machinery: **Ingest** (Librarian → uniform corpus records, *preserve don't summarize*), **Query** (the Draft phase reads the *compiled* corpus, never the raw pile), and **Lint** (Step 8 promotion, the Global-Librarian's cross-Talk merge, and the reverse pipeline's reconciliation — the periodic audits that keep the base from decaying).

**Where it diverges (on purpose).** Talksmith is a *task-specialized* wiki — tuned for "draft a thesis-first talk," not open-ended Q&A — and it is **multi-presenter and Git-native** (a shared subject repo, branch-per-Talk), where Karpathy's idea file is single-author. The plain-Markdown substrate means an Obsidian-style graph view works out of the box: corpus citations and `knowledge-library/` links *are* the knowledge graph.
