---
name: talksmith:ingest
description: Fetch a web page (HTML + best-effort Markdown extraction + referenced images) into `talks/<Talk>/research/web/<folder-name>/` for the librarian to ingest at Step 3. Invoke when the presenter hands over a URL to capture; pass the URL and the active Talk path. CLI-safe, stdlib-only Python.
---

# talksmith:ingest — Capture a web page as Talk research

This skill downloads one web page and stores it under the active Talk's `research/web/<folder-name>/` so the [`librarian`](${CLAUDE_PLUGIN_ROOT}/agents/librarian.md) picks it up in Step 3 (Corpus) alongside articles and chat exports.

The actual fetch is performed by [`fetch.py`](fetch.py) — a stdlib-only Python script (no `requests`, no `beautifulsoup4`, no external deps). The skill is the orchestration wrapper: it locates the active Talk, runs the script, surfaces errors back to the orchestrator.

## When to use

- Presenter mentions a URL during Collect (Step 2) and wants its content captured.
- Presenter realizes mid-Draft that a referenced URL would back a slide and the page isn't yet in the knowledge base.
- New sources arrive after Step 3 has already run — invoke `ingest` for each URL, then perform the Librarian role to add the new web folder to the corpus.

## Inputs

| Input | Required? | Source |
|---|---|---|
| `url` | yes | Presenter (free-text — there's no useful context to propose candidates from). Must be `http://` or `https://`. |
| `talk_path` | yes | The orchestrator (active Talk path, e.g. `talks/gen-models-bio/`). |
| `folder_name` | optional | Defaults to a slugified `<URL-host>-<first-path-segment>` — see [`fetch.py`](fetch.py) `_default_folder_name` + `_slugify` for the canonical definition (lowercase, non-alphanumeric → `-`, 80-char cap). Override when the presenter wants a more meaningful name (e.g. `transformer-paper-google` instead of `arxiv-org-abs`). |

## Output

```
talks/<Talk>/research/web/<folder-name>/
├── metadata.yaml      # url, fetched_at (UTC ISO 8601), title, http_status, byte_size, asset manifest
├── original.html      # raw fetched HTML — the source of truth (preserved verbatim)
├── page.md            # best-effort HTML → Markdown extraction (headings, paragraphs, lists, links, code, images)
└── assets/            # best-effort image downloads (only when at least one image was reachable; folder removed if empty)
```

The folder is **never overwritten by default** — if it already exists and is non-empty, the script aborts with an error. Pass `--force` only when the presenter has explicitly approved a re-fetch (e.g. the page has been updated and they want the latest version captured).

## Process

1. **Validate inputs.** URL must be http(s). `talk_path` must be an existing directory.
2. **Run the fetcher:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ingest/fetch.py \
     <url> \
     --talk-path talks/<Talk>/ \
     [--folder-name <slug>] \
     [--force]
   ```

   The script:
   - Fetches the URL with a UA string identifying Talksmith and a 30-second timeout.
   - Parses the HTML with `html.parser` (stdlib). Strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<aside>`, `<form>`, `<iframe>` subtrees as boilerplate.
   - Extracts a Markdown rendering covering headings (h1–h6), paragraphs, ordered/unordered lists, links, code (`<code>` + `<pre>`), strong/em, blockquotes, `<hr>`, and image refs (`![alt](src)`).
   - Resolves every `<img src>` to an absolute URL and downloads it into `assets/` (best effort: HTTP errors and timeouts are logged in `metadata.yaml` but do not abort the run).
   - Writes `original.html`, `page.md`, `metadata.yaml`. Removes `assets/` if no image succeeded.

3. **Report.** Return a one-line summary:
   - On success: `saved: <output-folder> · title: "<page title>" · assets: <n-saved> (of <n-total>)`
   - On failure: `failed: <error class> · <message>` — and do not leave a partial folder behind.

## Re-running and edits

- If the presenter wants to refresh a previously ingested page: confirm explicitly, then pass `--force`.
- If the extracted `page.md` is poor (the page used heavy JS rendering or a custom DOM), suggest the presenter extract by hand from `original.html` (which is preserved verbatim regardless of `page.md` quality) and overwrite `page.md` with the corrected Markdown. The librarian will ingest whichever Markdown is present at Step 3.

## Boundaries

- **Local file work only.** The script does not call out to AI services, OCR APIs, or external tooling beyond Python stdlib. JS-heavy sites that render content client-side will produce a thin `page.md` — `original.html` still captures whatever the server returned.
- **No table structure.** `<table>`, `<tr>`, `<td>`, `<th>` are not specially handled — cell text is concatenated into the surrounding flow with no Markdown table syntax. For pages where tabular data matters, the librarian should be pointed at `original.html` and/or the presenter should hand-edit `page.md`.
- **No paywall bypass.** If the page returns 403 / 401 / paywall HTML, that's what gets saved. Do not invent content.
- **One URL per invocation.** For multiple URLs, call the skill once per URL with a distinct `folder_name` each time.
- **Does not modify `draft.md`, `final.md`, `corpus/`, or any other Talk file.** Only writes under `research/web/<folder-name>/`. The librarian handles the corpus build in Step 3.

## Hand-off

After `talksmith:ingest` succeeds, the orchestrator should:

1. Mention to the presenter what got saved (folder, page title, asset count).
2. If Step 3 (Corpus) has already run for this Talk, perform the Librarian role on the new `research/web/<folder-name>/` folder. Otherwise the Librarian role will pick it up naturally when Step 3 runs.
