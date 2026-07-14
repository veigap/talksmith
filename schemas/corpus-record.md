# Schema — `research/corpus/<filename>.md` (+ companion folder)

Specification for the per-source corpus records the Librarian role emits during Step 3 (Corpus). One record per raw source — article, chat-export ZIP, web capture, or image — paired with a sibling **companion folder** that holds the source's image bytes. Together they form a self-contained unit that every downstream role queries; the raw asset folders (`articles/`, `llm-chats/`, `web/`) are inputs to Step 3 only and are not read after.

## Purpose

Lossless restructuring of every raw source under `talks/<Talk>/research/articles/`, `research/llm-chats/`, and `research/web/` into a uniform Markdown shape, plus a companion folder of extracted/copied image bytes. The librarian preserves, never compresses — long quotes belong in `Raw / preserved excerpts`, contradictions in `Inconsistencies / open questions`. Downstream consumers cite these records by filename in slide `Sources` fields and reference their companion-folder images directly from `draft.md` (and from the Step-6-derived `final.md`, which inherits those refs and then consolidates them into the Talk's `images/` folder).

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| Librarian role (writer) | Step 3 (Corpus), Phase 1 and Phase 2. **Sole writer.** | One output record per source. Phase 1 writes text-source records, copies/extracts image bytes into the companion folder, and writes image stubs; Phase 2 fills the stubs when `process_images: true` is set. |
| Editor role (reader) | Step 4 (Draft) in Modes B and C; Step 5 (Review) when applying source citations | Draft slide Content / Sources from corpus records. Cite the record by filename; reference its images by companion-folder path. |
| Composer role (reader) | Every drafting milestone in Step 4 | Verify every cited record exists and supports the slide's claim; flag pending stubs as `[major]` and overreaches as `[blocker]`. |
| Global-Librarian role (reader) | Step 8 (Learnings) on promotion | Reads corpus records + companion images to curate cross-Talk topic folders under `knowledge-library/`. |

The orchestrator never reads or writes corpus records directly.

## Filename convention

`research/corpus/<original-filename>.<original-ext>.md` — keep the original extension as part of the basename so collisions don't lose distinct sources. Examples:

- `paper.pdf` → `research/corpus/paper.pdf.md`
- `paper.html` → `research/corpus/paper.html.md` (a related-but-distinct record from the PDF)
- chat-export ZIP `gans-explainer.zip` → `research/corpus/gans-explainer.zip.md`
- web capture `talks/<Talk>/research/web/arxiv-2401/` → `research/corpus/arxiv-2401.web.md` (folder-name + `.web.md`)

## Companion folder

Every record `research/corpus/<source-stem>.md` has a sibling folder `research/corpus/<source-stem>/` (same basename, no `.md`) containing an `images/` subfolder with every image the source carried:

```
research/corpus/
├── paper.pdf.md
├── paper.pdf/
│   └── images/
│       ├── figure-1.png
│       └── figure-2.png
├── gans-explainer.zip.md
├── gans-explainer.zip/
│   └── images/
│       └── diagram-1.png
└── arxiv-2401.web.md
    arxiv-2401.web/
    └── images/
        └── hero.png
```

The Librarian writes the image bytes to `<source-stem>/images/<file>.<ext>` during Phase 1 (always — not deferred). Image filenames inside the corpus record's `## Images / diagrams` section are relative paths of the form `<source-stem>/images/<file>` (resolvable from `research/corpus/`). When `draft.md` references one of these images, the path is `research/corpus/<source-stem>/images/<file>` from the Talk root; Step 6 copies the draft to `final.md` and (b) consolidates the reference into the Talk's `images/` folder.

**Sources without images** (pure text articles, transcript-only chat exports) still get a companion folder, but it's empty until images are added. An empty companion folder is valid.

## `source_type` enum

Exactly one of:

| Value | When to use |
|---|---|
| `article` | PDFs, HTML exports, papers, article screenshots from `research/articles/`. |
| `chat-export` | LLM chat-session ZIPs from `research/llm-chats/` (Claude / ChatGPT / Gemini exports, plus the live-exploration `explore-*.md` files captured during Step 2). |
| `web-capture` | Pages captured by `talksmith:ingest` into `research/web/<folder>/`. |
| `image` | Standalone `.svg`/`.png`/`.jpg`/`.jpeg`/`.gif`/`.webp` files (loose in `articles/`, inside `web/<folder>/assets/`, or extracted from a chat ZIP). Always written as a stub in Phase 1; filled in Phase 2. |
| `other` | Anything that doesn't fit the four above. Use sparingly. |

## Pending markers

The librarian uses HTML-comment markers when a record is incomplete:

- `<!-- pending: process_images -->` — image stub from Phase 1; Phase 2 fills `Depiction` / `Why it matters` / `Transcribed text` when the Librarian role is re-run with `process_images: true`. The image bytes are already on disk in the companion folder regardless — only the prose is pending.
- `<!-- pending: failed: <one-line reason> -->` — image unreadable (corrupted, unsupported codec, zero bytes); listed under `Unparseable` in the librarian's final report.

A corpus record is **complete** iff it exists, is non-empty, **and** contains no `<!-- pending: ... -->` markers anywhere. The librarian's idempotency check skips complete records unless the orchestrator passes `force: true`.

The Editor role watches for these markers via its *Pending-stub awareness* rule (in `${CLAUDE_PLUGIN_ROOT}/agents/editor.md`): a slide that cites a pending stub triggers an `Open questions` note in `draft.md` rather than silently dropping the citation. The Composer role flags pending-stub citations as `[major]` punch-list items.

## Canonical empty form

The librarian writes each corpus record using this shape verbatim:

```markdown
---
source_file: <original filename>
source_type: article | web-capture | chat-export | image | other
ingested_at: <ISO date>
---

# <Title or filename>

## Provenance
- Original location: <relative path under research/>
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
<Per image: filename (always `<source-stem>/images/<file>` — resolvable from research/corpus/), depiction, relevance, transcribed text. For image-type stubs, leave Depiction / Why it matters / Transcribed text empty in Phase 1 and add the appropriate <!-- pending: ... --> marker. Phase 1 has already copied the bytes into the companion folder.>

## Raw / preserved excerpts
<Long quotes or full sections kept verbatim. Over-include rather than lose.>
```
