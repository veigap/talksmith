# Example — a talk *about* Talksmith, built *with* Talksmith

[`draft.md`](draft.md) is a complete, realistic Talksmith working file: a ~40-minute intro talk on Talksmith itself — what it is, how to install it, how to use it, and what happens behind the scenes. It doubles as a reference fixture:

- **Follows the full `draft.md` schema** ([`schemas/draft.md`](../../../schemas/draft.md)) — Thesis, Agenda, numbered Sections/Slides, Sources, Speaker notes, an append-only `Presenter feedback` audit trail (`[open]`/`[closed]` with `Resolution:` lines), plus Open questions and Cut material.
- **Exercises (almost) every slide type** — each slide carries a `<!-- template: … -->` hint spanning `statement`, `stat`, `value-columns`, `quote`, `content+image`, `single-point`, `divider`, `code-example`, `process`, `concept-breakdown` (all three `format`s), `quiz`, `content+cards+image`, `pros-cons`, `image-grid`, `big-number`, `timeline`, `content-text`, `closing-cta`, `closing-hero`. (Only `figures` — a near-duplicate of `content+image` — and the last-resort `fallback` are omitted.)
- **Showcases diagrams and their animations** — five ` ```ascii ` diagrams (the three-layer knowledge base, a diagram's own life from sketch to animation, the workflow, the feedback loop, and the forward/reverse pipeline). Polish drew each as a styled SVG, checked by the blind diagram critic, and four of them carry an `animation:` brief, so each also has an animated version (`<name>.anim.svg`) that passed its own blind critic. The slides point at the animated version; the base still beside it is what the PDF and `.pptx` show. The critiques are in `images/.critique/` (`<name>.md` for the drawing, `<name>.anim.md` for the animation).

## The rendered deck

The deck is committed at [`output/html/index.html`](output/html/index.html) — a self-contained [Reveal.js](https://revealjs.com/) file (open it in a browser; Present ▶ for full screen). It was produced by the normal Polish → `md-to-deck` pipeline:

1. **Polish** — [`final.md`](final.md) derived from `draft.md`: the ASCII diagrams drawn and animated into `images/` (the fences become image refs, the ASCII kept beside them as a comment), Presenter feedback stripped, the still-open bullet moved to Open questions. Four `images/deck-*.png` placeholders feed the `image-grid` slide.
2. **FILL** — `final.md` decomposed into [`output/slide-model.json`](output/slide-model.json): per slide, the template and its required fields (see [`schemas/slide-model.md`](../../../schemas/slide-model.md)). This is the semantic step an LLM performs.
3. **RENDER** (mechanical, deterministic) —
   ```bash
   python3 ../../../skills/md-to-deck/scripts/build_html.py \
     --model output/slide-model.json --talk-root . -o output/html/index.html
   ```

In a real subject repo this is automatic: the orchestrator fires the live HTML view during Review and the final render at the end of the workflow. This folder just carries the source + a committed render so the README can point at a concrete, self-referential example.
