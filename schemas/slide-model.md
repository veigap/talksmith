# Schema: `slide-model.json` — the deck's structured intermediate representation

`slide-model.json` is the **single intermediate representation** between the authored
`final.md` and the renderers. The **`md-to-deck` skill** fills it with an LLM: it reads
`final.md` and **decomposes each slide into the fields its template requires** — doing all the
*semantic* work (choosing the template, splitting a metric from its caption, recognizing that a
line is really a speaker note, grouping two symmetric blocks into comparison columns). The
renderers are then **purely mechanical**: `build_html.py` (HTML / Reveal.js) and the PPTX renderer
both **load this JSON and render fields** — no classification, no regex, no `final.md` parsing.

> **Why.** Classification and information-breakdown are semantic judgments. Encoding them as
> Python regex heuristics (`slide_model.py`) is brittle and never-ending — every deck surfaces a
> new edge case. Moving that work to the LLM, against a **fixed per-type field contract**, makes it
> robust and keeps the renderers deterministic and shared across HTML and PPTX.

Written to `talks/<Talk>/output/slide-model.json`. One file per rendered deck (`final.md` →
deliverable; `draft.md` → live in-progress view).

## Top-level shape

```json
{
  "deck": {
    "title": "Inteligencia Artificial: de lo conceptual a lo práctico",
    "institution": "Master in Management (MiM), IAE Business School, Universidad Austral",
    "class": "Seguridad e IA para Managers",
    "presenter": "Paulo Veiga, Profesor, IAE Business School",
    "date": "TBD",
    "logo": null,
    "sections": ["El caso Samsung (2023)", "Fundamentos", "MCP y agentes"]
  },
  "slides": [
    { "template": "stat", "section": "El caso Samsung (2023)",
      "title": "No es solo Samsung: los números",
      "lead": "Lo que esto cuesta, en tres números:",
      "stats": [
        { "value": "$4.44M", "caption": "" },
        { "value": "$670K",  "caption": "" },
        { "value": "18%", "caption": "de los empleados pega datos en herramientas GenAI — LayerX 2025" }
      ],
      "notes": "Ritmo liviano; conectar con la sala." }
  ]
}
```

- **`deck`** — cover + deck-wide data. `logo: null` → the renderer resolves it (frontmatter
  `logo:` → the Talk's `images/logo.*` → bundled institution logo). `sections` is the ordered
  section list that drives the section-separator roadmap; the cover slide is synthesized from
  `deck`, never authored as a slide.
- **`slides`** — ordered. Every slide object has **`template`** (one of the ids below), and may
  carry **`section`** (the section it belongs to, for the pill) and **`notes`** (speaker notes,
  verbatim → Reveal `<aside class="notes">` / the PPTX notes pane, **never** on the slide face).
  Beyond those, each template requires exactly the fields in its row.

## Per-template field contract

The LLM fills **required** fields for the chosen `template`; **optional** fields are included only
when the content warrants. Field names are the contract — the renderers read exactly these.

| `template` | Required fields | Optional |
|---|---|---|
| `section-agenda` | `title` (section name) | — (roadmap + active index derived from `deck.sections`) |
| `divider` | `title` | — (a plain sub-opener within a section) |
| `statement` | `title` (the one dominant claim) | `sub` (a one-line reveal) |
| `concept-breakdown` | `title`, `cards:[{label,body}]` (2–6) | per-card `icon` (else content-matched) |
| `card-row` | `title`, `cards:[{label,body}]` (3, short) | `lead` |
| `icon-list` | `title`, `rows:[{label,body}]` (3–5; `body` "" for a bare anaphora line) | `lead` |
| `process` | `title`, `steps:[{body}]` (ordered) | `lead`, per-step `label` |
| `figures` | `title`, `figures:[{image,label,body}]` | `lead` |
| `image-grid` | `images:[{src,alt}]` (≥4) | `title` |
| `content-image` | `title`, `image:{src,alt}`, `facts:[str]` | `lead`, `layout` (`text-left`\|`image-top`) |
| `content+cards+image` | `title`, `cards:[{label,body}]`, `image:{src,alt}` | `lead` |
| `comparison` | `title`, `columns:[{header,cells:[str]}]` (2–3) | — |
| `stat` | `title`, `stats:[{value,caption}]` (2–4) | `lead` |
| `big-number` | `number`, `caption` | `title` |
| `quote` | `quote` | `attribution`, `section` |
| `timeline` | `title`, `milestones:[{label,body}]` | per-milestone `marker` |
| `pros-cons` | `title`, `pros:[str]`, `cons:[str]` | — |
| `single-point` | `title`, `point:{label,body}` | — |
| `callout` | `callout:{label,body}`, `tone` (`pink`\|`blue`) | `title` |
| `code-example` | `title`, `code` | `language`, `explanation:[str]` |
| `content-text` | `title`, `big`, `panels:[str]` | — *(last-resort prose; flag to restructure)* |
| `closing-hero` | `title` | `body` |
| `closing-cta` | `title`, `items:[{label,body}]` | — |

The universal invariant still holds: **a parallel labeled set becomes `cards`/`rows`/`figures`,
never a plain bullet list.** Template *choice* is governed by the catalog
[`../config/pptx-styles/slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)
(its *Match* rules); how to decompose a slide into the chosen template's fields is *Filling the
model* below.

## Filling the model (the FILL step — the one semantic step)

The `md-to-deck` skill (an LLM) turns `final.md` into `slide-model.json`. **Which** template each
slide gets is governed entirely by the catalog
[`../config/pptx-styles/slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)
(its *Match* rules + *Classification procedure*) — this file does not restate classification. What
follows is only **how to build the deck object and decompose a slide's body into the chosen
template's fields.**

**The `deck` object.** From the frontmatter: split `presentation:` on the em/en-dash into `title`
(before) and `institution` (after); take `class`, `presenter`, `date`; `logo: null` (the renderer
resolves it). `sections` = the ordered section list read from the Agenda slide's "**Sections (in
delivery order):**" block (drop each item's "— description" tail and any "(~N min)", keep "(2023)").

**Walking the body.** In document order:
- **Drop scaffolding entirely:** the `# Thesis` / `# Open questions` / `# Cut material` sections,
  the standalone `# Agenda` slide (it only feeds `deck.sections`), every `### Sources` and
  `### Presenter feedback` block, HTML comments, and `〔divisor〕` markers.
- **An H1 that names a `deck.sections` entry** → a `section-agenda` slide (`title` = the section
  name, number stripped) — the roadmap. A `〔divisor〕` sub-opener (or an H1 that is not a real
  section) → a plain `divider`.
- **An H2** → a content slide: strip its leading `N. `, **classify it against the catalog** to set
  `template`, decompose `### Content`'s body into that template's required fields (below), and set
  `section` to the current section.
- **`### Speaker notes`** → lifted **verbatim** into the slide's `notes` (never onto the slide
  face). Keep image `src` paths exactly as written (`images/…`).

**Decomposing the body into fields** — the field-mapping judgment, once the template is chosen:
- **Labeled set** (`- **Label** body`, `### Subhead` + paragraph) → `cards` / `rows` / `steps` /
  `figures` `[{label,body}]`, **never plain bullets**. A short unlabeled parallel enumeration (an
  anaphora) → `icon-list` `rows:[{label}]` with `body:""`; drop a row that just repeats the title.
- **Standalone metrics** ($4.44M, 97%, USD 670.000) → `stat` `stats:[{value,caption}]` — the number
  is `value`, the trailing text its `caption`; a lone hero metric → `big-number`.
- **A pipe table** — two comparable value columns → `comparison` `columns:[{header,cells}]`; a
  label/value table → `concept-breakdown` `cards`.
- **One image + a little text** → `content-image` (`facts`, `image:{src,alt}`; add
  `"layout":"image-top"` when the text is very short). ≥4 images → `image-grid`; labeled images →
  `figures`. A fenced code block → `code-example` (`code`, `explanation`).
- A short **pull-quote** that is the point → `quote`; a single dominant claim → `statement`
  (`title` + optional `sub`); a lone analogy/tip → `callout` / `single-point`.
- **Icons vs. emoji.** Icon-bearing templates (`concept-breakdown`, `card-row`, `icon-list`,
  `content+cards+image`, `closing-cta`, `callout`, `single-point`) show one icon per item. The
  fill **may suggest** a per-item `icon` (a Material Symbols name), choosing a **distinct** one per
  item; when none is given the renderer content-matches — and never repeats an icon within a slide
  either way. Because an icon stands in for the emoji, **strip leading/inline emoji from the labels
  and bodies of those slides** — keeping both is redundant. (Emoji on a non-icon template, e.g. a
  `statement`, may stay.)

**Validate.** Every slide's fields must satisfy its template's required set (table above); a slide
that doesn't is a fill error to fix, not a silent `fallback`.

## Rendering (deterministic, shared)

`build_html.py` (HTML) and the PPTX renderer both load `slide-model.json` and render each slide via
its template keyed by `template`, reading the fields directly — **no renderer parses `final.md` or
classifies.**

## Canonical empty form

```json
{ "deck": { "title": "", "institution": "", "class": "", "presenter": "", "date": "",
            "logo": null, "sections": [] },
  "slides": [] }
```
