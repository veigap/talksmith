# Reconciling an externally-edited deck (reverse pipeline)

The forward pipeline is one-directional: `draft.md` → `final.md` → `output/final.pptx`. But presenters routinely open that `.pptx` in Keynote or PowerPoint and tweak it directly — those edits live only in the deck. The **reverse pipeline** pulls them back into `draft.md`, so the next Polish re-derives a `final.md` that reflects them.

It's three skills run in order; all artifacts land under `talks/<Talk>/reconcile/`, and nothing touches `final.md` directly.

```
  final.pptx  --[pptx-extract]-->  finalpptx.md          (deck rebuilt as draft.md-shaped Markdown)
                                        v
   final.md   --[pptx-diff]------>  finalpptx.diff.json   (what changed, per slide)
                                        v
   draft.md   <--[pptx-merge]----  apply simple changes; route complex ones to the Editor
                                        v
                        re-run Step 6 (Polish)  ->  final.md refreshed
```

**Prerequisite:** `pptx-extract` reads the deck via `python-pptx` (`pip install python-pptx`); the other two stages are stdlib-only. None require Cowork — the whole reverse pipeline is CLI-safe.

1. **`pptx-extract`** — parses the deck in presentation order, classifies each slide, stages images, and writes `reconcile/finalpptx.md` (in `draft.md` shape) plus an inventory sidecar. Thesis and Sources can't be recovered from a deck, so they come back as stubs for the Editor to restore.
   ```
   /talksmith:pptx-extract talks/<Talk>/output/final.pptx --talk talks/<Talk> --style <strict|free-form>
   ```
2. **`pptx-diff`** — aligns the reconstructed slides against the original `final.md` and reports every title, content, speaker-note, and image change, bullet-granular. Read-only; writes `reconcile/finalpptx.diff.json`.
   ```
   /talksmith:pptx-diff --final talks/<Talk>/final.md --pptx talks/<Talk>/reconcile/finalpptx.md \
     --talk talks/<Talk> --inventory talks/<Talk>/reconcile/finalpptx.inventory.json --human
   ```
3. **`pptx-merge`** — re-anchors each change structurally and applies the **simple, high-confidence** ones automatically (bullet/note edits, new-image inserts). **Complex or confusing** ones (low-confidence matches, removals, added/deleted slides) are routed to the Editor rather than guessed. Writes only `draft.md` and `images/`.
   ```
   /talksmith:pptx-merge plan       --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md
   /talksmith:pptx-merge apply-auto --diff talks/<Talk>/reconcile/finalpptx.diff.json --draft talks/<Talk>/draft.md
   ```

When it's done, re-run **Step 6 (Polish)** and the deck edits are back in the source of truth.
