# Schema: `slide-model.json` — the deck's structured intermediate representation

`slide-model.json` is the **single intermediate representation** between the authored
`final.md` and the renderers. The **`md-to-deck` skill** fills it with an LLM: it reads
`final.md` and **decomposes each slide into the fields its template requires** — doing all the
*semantic* work (choosing the template, splitting a metric from its caption, recognizing that a
line is really a speaker note, grouping two symmetric blocks into comparison columns). The
renderers are then **purely mechanical**: `build_html.py` (HTML / Reveal.js) and the PPTX renderer
both **load this JSON and render fields** — no classification, no regex, no `final.md` parsing.

> **Why.** Classification and information-breakdown are semantic judgments. Encoding them as
> Python regex heuristics (the since-removed `slide_model.py` parser) is brittle and never-ending — every deck surfaces a
> new edge case. Moving that work to the LLM, against a **fixed per-type field contract**, makes it
> robust and keeps the renderers deterministic and shared across HTML and PPTX.

Written to `talks/<Talk>/output/slide-model.json`. One file per rendered deck (`final.md` →
deliverable; `draft.md` → live in-progress view).

## Top-level shape

```json
{
  "deck": {
    "title": "Inteligencia Artificial: de lo conceptual a lo práctico",
    "lang": "es",
    "institution": "Máster en Management, Escuela de Negocios (ejemplo)",
    "class": "Seguridad e IA para Managers",
    "presenter": "Nombre Apellido, Profesor",
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

- **`deck`** — cover + deck-wide data. **`lang`** (`"en"` default, or `"es"`, …; from the profile's
  *Presentation language*) localizes the **renderer-emitted chrome labels** — the cover's
  author/last-modified lines, the `pros-cons` column headers, and the `quiz` answer label — so an
  English deck never shows Spanish chrome. It does **not** translate authored content. `logo: null` → the renderer resolves it (frontmatter
  `logo:` → the Talk's `images/logo.*` → the subject repo's `config/logo.*` (set once at repo
  setup) → the bundled neutral placeholder — the plugin ships no institution branding). `sections` is the ordered
  section list that drives the section-separator roadmap; the cover slide is synthesized from
  `deck`, never authored as a slide.
- **`slides`** — ordered. Every slide object has **`template`** (one of the ids below), and may
  carry **`section`** (the section it belongs to, for the pill), **`notes`** (speaker notes,
  verbatim → Reveal `<aside class="notes">` / the PPTX notes pane, **never** on the slide face), and
  **`highlights`** (see below). Beyond those, each template requires exactly the fields in its row.
- **`highlights`** — an **optional** common field on any content slide: a list of one or more
  emphasized lines, rendered in an accented band under the slide body. Each entry is a string **or**
  `{body, label?, kind?}` (the `label` renders bold before a colon). Use it for a line that deserves
  emphasis — e.g. the takeaway a diagram builds to — instead of dropping or burying it. The **fill
  picks the `kind`** (it's a semantic choice, like a callout's tone); each kind has its own accent
  colour + icon. Defaults to `takeaway`.

  | `kind` | The job the line does | e.g. |
  |---|---|---|
  | `takeaway` *(default)* | the point to remember — thesis / summary | "Si se llevan un solo slide, es este." |
  | `important` | a risk / critical caveat / a "don't" | "Nunca pegues credenciales en un prompt." |
  | `definition` | a term being defined | "DPA: el contrato de tratamiento obligatorio (Art. 28)." |
  | `example` | an illustration / concrete scenario | "Ej.: pegar la lista de clientes en un chatbot gratuito." |
  | `quote` | a pull-quote / cited line (rendered italic) | "Una falla de seguridad no siempre tiene un atacante." |
  | `note` | an aside / minor context | "Convención con respaldo en ISO 27001 / NIST." |
- **`aside`** — an **optional** common field on any content slide: `{image: {src, alt}, side?}`,
  where `side` is `"right"` *(default)* or `"left"`. Renders the image as a **full-bleed column down
  that edge** of the slide, with the title and body laid out in the remaining width. Its job is
  **visual reinforcement** — an evocative image that sets the tone of the point being made — not
  information the slide needs. Anything load-bearing (a diagram, a chart, a screenshot the audience
  must actually read) belongs in a template that *owns* its image (`content-image`, `figures`,
  `content+cards+image`, `process`), because the aside column crops to fill and is not read closely.
  Set it from an author `<!-- aside: ... -->` hint (see [`draft.md`](draft.md)). Don't put an `aside`
  on a template that already carries an image.
- **`reveal`** — an **optional opt-out** on any slide that reveals progressively. By **default** —
  field absent — the HTML deck steps through the slide on click (Reveal fragments):
  first the enumerated items one at a time (`stat`, `card-row`, `concept-breakdown`, `icon-list`,
  `content+cards+image`), then `highlights` as one final block, so the takeaway text below the
  body lands *after* what it comments on rather than being readable from the start.
  `"reveal": "together"` shows the whole slide at once instead. A slide with only `highlights`
  and no enumeration still gets that one closing step.
  The `.pptx` render is static and always shows everything at once, whatever this says.
  Set it from an author `<!-- reveal: together -->` hint in `draft.md`/`final.md`.
  Only `"together"` is recognized; any other value (including the legacy `"sequential"`) leaves
  the default in place, so a typo animates rather than silently flattening the slide.
- **Never drop content.** Every load-bearing line in the source must be *translated* into the
  model — as a field value, a card/row/step, a fact, or a `highlights` entry. Do not omit a line
  because it looks redundant with an image or another slide; move it to `highlights` if it's a
  comment or takeaway, but keep it.

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
| `process` | `title`, `steps:[{body}]` (ordered) | `lead`, per-step `label`, `image:{src,alt}` (supporting diagram/example) |
| `figures` | `title`, `figures:[{image,label,body}]` | `lead` |
| `image-grid` | `images:[{src,alt}]` (≥4) | `title` |
| `content-image` | `title`, `image:{src,alt}`, `facts:[{body,label?}]` | `lead`, `layout` (`text-left`\|`image-top`) |
| `content+cards+image` | `title`, `cards:[{label,body}]`, `image:{src,alt}` | `lead` |
| `comparison` | `title`, `columns:[{header,cells:[str]}]` (2–3) | — |
| `stat` | `title`, `stats:[{value,caption}]` (2–4) | `lead` |
| `big-number` | `number`, `caption` | `title` |
| `quote` | `quote` | `attribution`, `section` |
| `timeline` | `title`, `milestones:[{label,body}]` | per-milestone `marker` |
| `pros-cons` | `title`, `pros:[str]`, `cons:[str]` | — |
| `quiz` | `question`, `answer` | `title` (topic), `options:[str]` (choices), `correct` (the right choice — option text, 1-based index, or letter A/B/C…; highlighted on reveal), `explanation` (extra reveal), `image:{src,alt}` (shown at right, never cropped), `answer_label` (label on the answer panel; default "Respuesta") |
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
(before) and `institution` (after); take `class`, `presenter`, `date`; set `lang` from the profile's
*Presentation language* (`en` if absent); `logo: null` (the renderer
resolves it). `sections` = the ordered section list read from the Agenda slide's "**Sections (in
delivery order):**" block (drop each item's "— description" tail and any "(~N min)", keep "(2023)").

**Walking the body.** In document order:
- **Drop scaffolding entirely:** the `# Thesis` / `# Open questions` / `# Cut material` sections,
  the standalone `# Agenda` slide (it only feeds `deck.sections`), every `### Sources` and
  `### Presenter feedback` block, HTML comments, and `〔divisor〕` markers. **Exception — honour author
  directives:** a `<!-- template: <type> -->` comment pins that slide's `template` (skip
  classification), and `<!-- reveal: together -->` sets its `reveal` field. These are the only
  HTML comments read rather than dropped. (They ride from `draft.md` into `final.md` unchanged —
  Polish only strips `Presenter feedback` and rewrites ASCII fences — so the hint the author wrote
  while drafting is exactly what reaches this FILL step.)
- **An H1 that names a `deck.sections` entry** → a `section-agenda` slide (`title` = the section
  name, number stripped) — the roadmap. A `〔divisor〕` sub-opener (or an H1 that is not a real
  section) → a plain `divider`.
- **An H2** → a content slide: strip its leading `N. `, **classify it against the catalog** to set
  `template` (**unless a `<!-- template: … -->` hint pins it**), decompose `### Content`'s body into
  that template's required fields (below), set `section` to the current section, and carry a
  `<!-- reveal: … -->` hint into `reveal`.
- **`### Speaker notes`** → lifted **verbatim** into the slide's `notes` (never onto the slide
  face). Keep image `src` paths exactly as written (`images/…`).

**Decomposing the body into fields** — the field-mapping judgment, once the template is chosen:
- **Labeled set** (`- **Label** body`, `### Subhead` + paragraph) → `cards` / `rows` / `steps` /
  `figures` `[{label,body}]`, **never plain bullets**. A short unlabeled parallel enumeration (an
  anaphora) → `icon-list` `rows:[{label}]` with `body:""`; drop a row that just repeats the title.
- **Process ordinals** are renderer chrome, not content. When filling `process.steps`, strip any
  ordinal/step marker from the extracted `label` or `body`. Then apply the colon lead-in rule:
  anything before `:` becomes the highlighted `label`, anything after becomes `body`. Examples:
  `1 · Leave feedback: drop bullets in draft.md` → `label:"Leave feedback"`,
  `body:"drop bullets in draft.md"`; `1. **Leave feedback** drop bullets...` and
  `Paso 1: Leave feedback` → `label:"Leave feedback"`. The renderer supplies the visible 1/2/3,
  so keeping the source ordinal would duplicate it.
- **Standalone metrics** — the number is `value`, its trailing text the `caption` (`stat.stats`;
  a lone hero metric fills `big-number.number` + `caption`).
- **A pipe table** → `comparison.columns:[{header,cells}]` (header row → `header`, body cells in
  column order); a label/value table decomposes as `cards`. *(Which template a given shape gets is
  the catalog's Match rules — not restated here.)*
- **Images** — carry `src` paths exactly as written into `image:{src,alt}` / `images` / `figures`;
  on `content-image`, add `"layout":"image-top"` when the text is very short. A fenced code block
  fills `code-example.code` (+ `explanation`).
- **Labeled lines (colon lead-ins).** When a line reads `Label: rest` (a short lead-in before a
  colon), split it into `{label, body}` yourself — the renderer bolds `label` and never parses the
  colon. This applies to `content-image` `facts` and `highlights` (both accept `{label, body}`), and
  matches how `cards`/`rows`/`steps` already carry an explicit `label`.
- **Highlights over dropping.** If a line is a comment or the key takeaway (often what a diagram
  builds to, e.g. "PII es un subconjunto de Personal Data"), put it in the slide's `highlights`
  rather than omitting it — content is never dropped (see the top-level rule).
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
