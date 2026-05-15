# Schema — `knowledge/compile/<filename>.md`

Specification for the per-source compile records the `librarian` subagent emits during Step 3 (Compile). One record per raw source — article, chat-export ZIP, web capture, or image. Each record is what downstream consumers (the `editor` for drafting, the `composer` for citation verification) read when they need source material.

## Purpose

Lossless restructuring of every raw source under `talks/<Talk>/knowledge/articles/`, `knowledge/llm-chats/`, and `knowledge/web/` into a uniform Markdown shape. The librarian preserves, never compresses — long quotes belong in `Raw / preserved excerpts`, contradictions in `Inconsistencies / open questions`. Downstream consumers cite these files by filename in slide `Sources` fields.

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| `librarian` subagent (writer) | Step 3 (Compile), Phase 1 and Phase 2. **Sole writer.** | One output file per source. Phase 1 writes text-source records and image stubs; Phase 2 fills the stubs when the orchestrator dispatches with `process_images: true`. |
| `editor` subagent (reader) | Step 4 (Draft) in Modes B and C; Step 5 (Review) when applying source citations | Draft slide Content / Sources from compiled records. Cite by filename. |
| `composer` subagent (reader) | Every drafting milestone in Step 4 | Verify every cited file exists and supports the slide's claim; flag pending stubs as `[major]` and overreaches as `[blocker]`. |

The orchestrator never reads or writes this file directly.

## Filename convention

`knowledge/compile/<original-filename>.<original-ext>.md` — keep the original extension as part of the basename so collisions don't lose distinct sources. Examples:

- `paper.pdf` → `knowledge/compile/paper.pdf.md`
- `paper.html` → `knowledge/compile/paper.html.md` (a related-but-distinct record from the PDF)
- chat-export ZIP `gans-explainer.zip` → `knowledge/compile/gans-explainer.zip.md`
- web capture `talks/<Talk>/knowledge/web/arxiv-2401/` → `knowledge/compile/arxiv-2401.web.md` (folder-name + `.web.md`)

## `source_type` enum

Exactly one of:

| Value | When to use |
|---|---|
| `article` | PDFs, HTML exports, papers, article screenshots from `knowledge/articles/`. |
| `chat-export` | LLM chat-session ZIPs from `knowledge/llm-chats/` (Claude / ChatGPT / Gemini exports, plus the live-exploration `explore-*.md` files captured during Step 2). |
| `web-capture` | Pages captured by `talksmith:ingest` into `knowledge/web/<folder>/`. |
| `image` | Standalone `.svg`/`.png`/`.jpg`/`.jpeg`/`.gif`/`.webp` files (loose in `articles/`, inside `web/<folder>/assets/`, or extracted from a chat ZIP). Always written as a stub in Phase 1; filled in Phase 2. |
| `other` | Anything that doesn't fit the four above. Use sparingly. |

## Pending markers

The librarian uses HTML-comment markers when a record is incomplete:

- `<!-- pending: process_images -->` — image stub from Phase 1; Phase 2 fills `Depiction` / `Why it matters` / `Transcribed text` when the orchestrator dispatches with `process_images: true`.
- `<!-- pending: failed: <one-line reason> -->` — image unreadable (corrupted, unsupported codec, zero bytes); listed under `Unparseable` in the librarian's final report.

A compile file is **complete** iff it exists, is non-empty, **and** contains no `<!-- pending: ... -->` markers anywhere. The librarian's idempotency check skips complete files unless the orchestrator passes `force: true`.

The `editor` watches for these markers via its *Pending-stub awareness* rule (in `.claude/agents/editor.md`): a slide that cites a pending stub triggers an `Open questions` note in `master.md` rather than silently dropping the citation. The `composer` flags pending-stub citations as `[major]` punch-list items.

## Canonical empty form

The librarian writes each compile record using this shape verbatim:

```markdown
---
source_file: <original filename>
source_type: article | web-capture | chat-export | image | other
ingested_at: <ISO date>
---

# <Title or filename>

## Provenance
- Original location: <relative path under knowledge/>
- Format: <pdf | html | zip-chat | png | svg | ...>
- Author / source (if known):
- Date of original (if known):

## Key claims
<Bullet list of main factual claims or arguments. Verbatim quotes allowed.>

## Definitions and terminology
<Terms the source defines or uses in a specific way.>

## Evidence and examples
<Data, anecdotes, case studies, figures referenced.>

## Inconsistencies / open questions
<Chat exports: contradictions, abandoned threads, corrections, pushback. Articles: gaps, unsupported claims, follow-ups. Web captures: extraction gaps from thin page.md fallbacks.>

## Images / diagrams
<Per image: filename, depiction, relevance, transcribed text. For image-type stubs, leave Depiction / Why it matters / Transcribed text empty in Phase 1 and add the appropriate <!-- pending: ... --> marker.>

## Raw / preserved excerpts
<Long quotes or full sections kept verbatim. Over-include rather than lose.>
```
