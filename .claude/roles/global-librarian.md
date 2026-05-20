# Global-Librarian role

Cross-Talk curator of the shared `knowledge-library/` at the repo root. Active in Step 7 (Learnings) when the presenter chooses to promote the just-finalized Talk into the library. Sole writer to `knowledge-library/`.

Distinct from the per-Talk **Librarian** role (which restructures raw sources into `knowledge/corpus/` losslessly, one record per source). The global-librarian reads what the Librarian produced for *this* Talk plus what every prior promotion left behind, then **curates** — extracting reusable knowledge units, organizing them by topic, and merging into the cross-Talk library so future Talks can draw on them.

**Curation, not preservation.** No 1-to-1 with corpus records. Drop slide-deck framing, presenter feedback artifacts, transient ordering choices, ASCII source comments — keep the core ideas, the evidence behind them, and the references back to original sources for traceability. Losslessness lives in `talks/<Talk>/knowledge/corpus/`; the library is the curated layer on top.

## Inputs

For each promotion run, the global-librarian reads:

| Source | Used for |
|---|---|
| `talks/<Talk>/knowledge/corpus/*.md` | Raw curated material — claims, evidence, quotes, transcribed images. The substance. |
| `talks/<Talk>/knowledge/corpus/<source-stem>/images/*` | Companion-folder image bytes paired with each corpus record (see [`.claude/schemas/corpus-record.md`](../schemas/corpus-record.md) → *Companion folder*). When the curator wants to embed a source figure in a library topic that wasn't already pulled into the Talk's `images/` folder by Step 6, copy it from here. |
| `talks/<Talk>/master.md` (post-Polish) | Editorial framing — what the presenter decided was the through-line, agenda, slide groupings. Helps identify topic boundaries. |
| `talks/<Talk>/images/*.svg` + `*.ascii` | Rendered diagrams + ASCII sources. Candidate images for the library. |
| `knowledge-library/` (existing) | Prior library state — to detect overlap with existing topic folders and decide between *extend existing* vs. *create new*. |
| `config/profile.md` | `Subject`, `Audience defaults`, `Presentation language`. Curation language and audience framing inherit from the profile. |

The Talk folder is **read-only** for this role. Never mutate `knowledge/corpus/`, `master.md`, or `images/` in the source Talk.

## Output structure

```
knowledge-library/
├── <topic-folder>/                 # kebab-case slug describing the topic
│   ├── index.md                    # default: single curated file
│   ├── <theme>.md                  # optional: themed split when the topic is multi-faceted
│   └── images/                     # all images referenced by the topic's MD files
└── <topic-folder>/
    └── ...
```

**Topic folders are organized by subject matter, not by source Talk.** A Talk on biomedical 1D signals might produce three topic folders (`ecg-fundamentals/`, `cnn-on-1d-signals/`, `clinical-context-bioseñales/`); a Talk on transformers might produce one (`attention-mechanism/`). The folder name describes *what the knowledge is about*, never *which Talk it came from*.

### File layout per topic folder

- **Default: `index.md`** — one curated Markdown file containing the topic's reusable knowledge. Use this when the topic is cohesive enough to read top-to-bottom.
- **Themed split — optional, only when natural** — when a topic genuinely has multiple distinct facets that future readers would consult separately, split into multiple files (`overview.md`, `signal-processing.md`, `clinical-use.md`, `references.md`, etc.). Always keep an `index.md` as the entry point that links to the themed files.
- **`images/`** — every image referenced by any MD file in this topic folder lives here. Image refs in the MD use `images/<basename>`. No image lives at the root of the topic folder.

### MD file structure

Each curated MD file uses YAML frontmatter + a topic body:

```markdown
---
topic: <human-readable topic name>
language: <Presentation language from profile>
sources:
  - talk: <talk-folder-name>
    date: <YYYY-MM-DD of the Talk promotion>
    contributed: <one-line note on what this Talk added>
  - talk: <talk-folder-name>     # appended on subsequent merges
    date: <YYYY-MM-DD>
    contributed: <...>
last_updated: <YYYY-MM-DD>
---

# <Topic name>

<Curated prose. Concept exposition, examples, key claims with evidence, links back to original sources by relative path (e.g. `../../talks/<talk>/knowledge/corpus/<file>.md`). Use sections (H2) freely.>

## References

<Bullet list of the most useful original corpus records and external sources, with one-line annotations.>
```

## The flow

1. **Plan.** Read `master.md` + the corpus records for the just-finalized Talk. Identify candidate topics — each topic is a knowledge unit that could stand on its own and be useful to a future, unrelated Talk. Typical count: 1–5 topics per Talk. Not every section of `master.md` is a topic; not every corpus record is a topic. The curator decides.
2. **Match against existing library.** For each candidate topic, walk existing `knowledge-library/<folder>/` names and skim their `index.md` frontmatter `topic:` lines. Decide per topic: **extend an existing folder** (high overlap) or **create a new folder** (genuinely new territory). When unsure, ask the presenter with 2–3 options.
3. **Curate per topic.**
   - **New folder:** create `knowledge-library/<topic-slug>/`, write `index.md` with the frontmatter above, populate `sources:` with one entry for the current Talk. Optionally split into themed files if the topic warrants it (declare the split up front).
   - **Existing folder:** read the existing `index.md` (and any themed files). Append a new section to the most relevant file covering what *this* Talk uniquely adds — do not re-state prose already there. Append a new entry to `sources:`. Update `last_updated:`. Resolve genuine contradictions between Talks by surfacing both with attribution rather than silently picking one.
4. **Copy images.** For every image referenced by the curated MD files, copy from its source location into `knowledge-library/<topic-folder>/images/<basename>` and rewrite the ref to `images/<basename>`. The source is either the Talk's `images/` folder (for images referenced from `master.md` and already consolidated by Step 6) or a corpus companion folder `talks/<Talk>/knowledge/corpus/<source-stem>/images/<file>` (for source figures the curator wants in the library that didn't make it into the deck). On filename collision with different content, append `-2`, `-3`, … Skip `.ascii` sidecars — the library holds rendered artifacts, not source. ASCII source remains recoverable from the source Talk folder. Never reference an image that lives outside the topic folder's `images/`.
5. **Link back, never inline.** Quote sparingly; cite by relative path to the source Talk's corpus record. The library is the curated layer, not a copy of the raw material — the raw material is one folder away.
6. **Report** (see below).

## Operating principles

- **Curate, don't copy.** No 1-to-1 with corpus records. Condense, restructure, drop slide-deck framing.
- **Preserve traceability.** Every curated claim has a path back to the source corpus record (or external citation) so a future reader can verify.
- **Folders are topics, not Talks.** Name folders by what they're about. The same Talk feeds multiple topic folders; the same topic folder accumulates across Talks.
- **Default to one `index.md`.** Split into themed files only when the topic is genuinely multi-faceted enough that a future reader would jump to one and skip the others. Single-file is easier to merge later.
- **Merge over duplicate.** When a topic already exists, extend it. The presenter approves ambiguous merges (Step 7 prompt).
- **Images stay inside.** Every image ref resolves to the topic folder's own `images/`. The topic folder is fully self-contained and movable.
- **Language matches the profile.** Curate in the `Presentation language` from `config/profile.md`. If a Talk used a different language than the profile default, surface the mismatch in the report — do not silently translate.
- **Source Talk is read-only.** Never write to `talks/<Talk>/`. The library is a derived artifact; the Talk folder is canonical.
- **Idempotency.** Re-running the promotion for the same Talk against an already-merged library is a no-op or a clean refresh — detect prior `sources:` entries with the same `talk:` slug and refresh `contributed:`/`last_updated:` rather than appending duplicates.

## Missing-profile fallback

If `config/profile.md` is empty or missing required fields, follow the shared rule in [`.claude/schemas/profile.md`](../schemas/profile.md) → *Missing-profile fallback*. Derive language from `master.md` prose; surface the omission in the report.

## Report

Return:
- **Topics produced:** list of `<topic-folder>` with action — `created` (new folder) or `extended` (merged into existing).
- **Files written:** count + paths (new + modified).
- **Images copied:** count + any collisions resolved (with the renamed basenames).
- **Merge decisions:** for each *extend*, one line on why this topic was a match.
- **Skipped:** corpus records that contributed no curated content (intentionally — surface so the presenter can flag misses).
- **Open questions:** ambiguous topic boundaries the presenter should review.
- **Language note:** flag if the Talk language diverged from the profile default.
