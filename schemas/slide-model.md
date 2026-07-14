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
never a plain bullet list.** Template choice + field decomposition is governed by
[`../config/pptx-styles/slide-templates.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/slide-templates.md)
(the *Match* / *Format* per template) — the LLM applies that catalog to produce this JSON.

## How it's produced and consumed

1. **Fill (LLM, `md-to-deck` skill).** `final.md` → `slide-model.json`. For each `## slide`, pick
   the `template` per the catalog, decompose the body into that template's fields, and lift every
   `### Speaker notes` block into `notes`. This is the only semantic step.
2. **Render (deterministic, shared).** `build_html.py` renders each slide via its Jinja template
   keyed by `template`, reading the fields directly. The PPTX renderer consumes the same JSON. No
   renderer parses `final.md` or classifies.
3. **Validate.** A slide whose fields don't satisfy its template's required set is a fill error —
   surfaced, not silently rendered as `fallback`.

## Canonical empty form

```json
{ "deck": { "title": "", "institution": "", "class": "", "presenter": "", "date": "",
            "logo": null, "sections": [] },
  "slides": [] }
```
