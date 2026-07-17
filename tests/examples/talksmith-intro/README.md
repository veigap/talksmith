# Example — a talk *about* Talksmith, built *with* Talksmith

[`draft.md`](draft.md) is a complete, realistic Talksmith working file: a ~40-minute intro talk on Talksmith itself — what it is, how to install it, how to use it, and what happens behind the scenes. It doubles as a reference fixture:

- **Follows the full `draft.md` schema** ([`schemas/draft.md`](../../../schemas/draft.md)) — Thesis, Agenda, numbered Sections/Slides, Sources, Speaker notes, an append-only `Presenter feedback` audit trail (`[open]`/`[closed]` with `Resolution:` lines), plus Open questions and Cut material.
- **Exercises (almost) every slide type** — each slide carries a `<!-- template: … -->` hint spanning `statement`, `stat`, `comparison`, `quote`, `content+image`, `single-point`, `divider`, `code-example`, `process`, `icon-list`, `card-row`, `concept-breakdown`, `quiz`, `content+cards+image`, `pros-cons`, `image-grid`, `big-number`, `timeline`, `content-text`, `closing-cta`, `closing-hero`. (Only `figures` — a near-duplicate of `content+image` — and the last-resort `fallback` are omitted.)
- **Showcases ASCII → SVG** — three render-driving ` ```ascii ` diagrams (the three-layer knowledge base, the feedback loop, and the forward/reverse pipeline) that the Diagram-Illustrator turns into styled SVGs at Polish.

## The rendered deck

The deck is committed at [`output/html/index.html`](output/html/index.html) — a self-contained [Reveal.js](https://revealjs.com/) file (open it in a browser; Present ▶ for full screen). It was produced by the normal two-step `md-to-deck` pipeline:

1. **Assets** — `images/workflow.png` (the plugin's own diagram) plus three ASCII→SVG diagrams (`images/s2-3-1.svg`, `s4-3-1.svg`, `s5-2-1.svg`) that stand in for the Diagram-Illustrator's Polish output, and four `images/deck-*.png` placeholders for the `image-grid` slide.
2. **FILL** — `draft.md` decomposed into [`output/slide-model.json`](output/slide-model.json): per slide, the template and its required fields (see [`schemas/slide-model.md`](../../../schemas/slide-model.md)). This is the semantic step an LLM performs.
3. **RENDER** (mechanical, deterministic) —
   ```bash
   python3 ../../../skills/md-to-deck/build_html.py \
     --model output/slide-model.json --talk-root . -o output/html/index.html
   ```

In a real subject repo this is automatic: the orchestrator fires the live HTML view during Review and the final render at the end of the workflow. This folder just carries the source + a committed render so the README can point at a concrete, self-referential example.
