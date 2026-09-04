# Deck design assets

Bundled, read-only. These four files are the deck's design system — what a slide *is*, what it
must look like, and what counts as a defect. They are format-neutral: the HTML deck is the only
render, and the PDF and `.pptx` are measured from it, so there is nothing here that varies by
output format.

| File | Owns |
|---|---|
| [`slide-templates.md`](slide-templates.md) | **The template catalog.** Every slide type, the content signals that select it, what it is *not*, and the format it must take. This is what the FILL step classifies against and what [`slide-classifier-critic`](${CLAUDE_PLUGIN_ROOT}/agents/slide-classifier-critic.md) re-derives from scratch. |
| [`visual-guidance.md`](visual-guidance.md) | **The generic visualization floor** — hard invariants (Part A) and principles (Part B) that hold for any slide. |
| [`slide-design.md`](slide-design.md) | **The design-quality catalog** — the per-slide checks that implement that floor: CONTENT, TEMPLATE, AESTHETIC, DISTRIBUTION. |
| `placeholder-logo.png` | The neutral cover mark used when the working directory has no `config/logo.*`. |

**The universal invariant, stated once and honoured everywhere:** a labeled enumeration renders as
cards, never as plain bullets. It lives in `slide-templates.md`; nothing else restates it.

## What used to be here

Two `.pptx` style specs — a 1143-line strict one and a 93-line free-form one — plus their base
templates, their conformance patterns and a per-format effort matrix. They existed because the
`.pptx` was authored by an LLM following prose, so every geometry rule, colour and classification
criterion had to be written a second time in EMU units and then verified by five OOXML audits.

The `.pptx` is now *measured* from the rendered HTML deck
([`export_pptx.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/export_pptx.py)), so a slide's geometry
has exactly one definition — [`theme.css`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/templates/html/theme.css) —
and the exporter cannot disagree with it. The per-format matrix went with them: there is one
render path, and a matrix with one row is a sentence.

**The deck's *looks* are not here either.** A skin is a token override under
[`templates/html/styles/`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/templates/html/styles/) — one CSS
file per skin, discovered from disk. Add a file to add a look; nothing in this directory changes.
