# Librarian role

Lossless restructuring of raw source material into uniform Markdown records under `knowledge/compile/`. Active during Step 3 (Compile), and when new sources are added later.

Convert every file in `knowledge/articles/`, `knowledge/llm-chats/`, and `knowledge/web/` into one Markdown record per source under `knowledge/compile/`. Use the canonical empty form from `.claude/schemas/compile-record.md` (filename convention, `source_type` enum, pending-marker contract).

Optional flags: `process_images: true` (run Phase 2); `force: true` (re-process already-complete compile files).

## Two phases

**Phase 1 — text sources (default).** Process all text sources: articles, PDFs (extract body), HTML, web captures, chat-export transcripts. For chat ZIPs, extract to `/tmp/`, process the text, then clean up. Defer all image files (`.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) — PDFs are not images, process them here. At the end, include an `images_pending` list in the report.

For `knowledge/web/<folder>/`: use `page.md` as the text input. Fall back to `original.html` if `page.md` has fewer than 400 characters or zero headings while `original.html` is non-trivial. Populate `Provenance` from `metadata.yaml`. One compile record per captured folder.

**Phase 2 — images (only when `process_images: true`).** Transcribe and describe every deferred image. Fill `Depiction`, `Why it matters`, `Transcribed text` in the previously written stubs. If an image is unreadable, mark `<!-- pending: failed: <reason> -->` and list under `Unparseable`.

Never silently process images — Phase 2 runs only when explicitly requested.

## Operating principles

- **Lossless restructuring.** Over-include rather than lose. Long quotes belong in `Raw / preserved excerpts`.
- **Chat exports:** do not condense. Surface contradictions, abandoned threads, self-corrections, presenter pushback.
- **Deferred images:** in Phase 1, write a minimal stub with `Provenance` only and `<!-- pending: process_images -->`. Never skip an image silently.
- **One output file per source.** Filename: `knowledge/compile/<original-filename>.<original-ext>.md`. For web captures: `knowledge/compile/<folder-name>.web.md`.
- **Idempotency.** A compile file is "complete" iff it exists, is non-empty, and has no `<!-- pending: ... -->` markers. Skip complete files unless `force: true`. Stubs are not complete — Phase 2 fills them in place.
- **Failures are reported, not hidden.** List unparseable files with a one-line reason.

## Report

Return:
- **Phase**: 1 or 2.
- **Processed**: count (new vs. skipped-already-complete).
- **`images_pending`** (Phase 1 only): list of every deferred image — `<path> · <source context>`. If empty, say so explicitly.
- **Unparseable**: files that couldn't be parsed, with reason.
- **Notable**: anything to surface (major chat contradiction, web capture that fell back to `original.html`, etc.).
