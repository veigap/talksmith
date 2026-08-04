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

> **This is a generated artifact — not a hand-maintained file.** It is (re)produced by the FILL
> step from the *current* source on **every** render; a renderer must never consume a model left
> over from a prior source. To make that enforceable, FILL stamps the model with a top-level
> **`_source`** block — `{"file": "final.md", "sha256": "<hex>", "bytes": <n>}` (via
> [`model_freshness.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/model_freshness.py) `stamp`).
> Before rendering, the digest is re-checked against the live source; a mismatch or a missing stamp
> is a **stale model** and the render refuses rather than silently using it. `_source` is metadata,
> not slide content — renderers ignore it. (`slide-model.draft.json` is stamped the same way from
> `draft.md`.)

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
  emphasized lines, rendered in an accented band beside the slide body. Each entry is a string **or**
  `{body, label?, kind?, position?}` (the `label` renders bold before a colon). Use it for a line that
  deserves emphasis — e.g. the takeaway a diagram builds to — instead of dropping or burying it. The
  **fill picks the `kind`** (it's a semantic choice, like a callout's tone); each kind has its own
  accent colour + icon — except `source`, which renders plain. Defaults to `takeaway`.

  | `kind` | The job the line does | e.g. |
  |---|---|---|
  | `takeaway` *(default)* | the point to remember — thesis / summary | "Si se llevan un solo slide, es este." |
  | `important` | a risk / critical caveat / a "don't" | "Nunca pegues credenciales en un prompt." |
  | `definition` | a term being defined | "DPA: el contrato de tratamiento obligatorio (Art. 28)." |
  | `example` | an illustration / concrete scenario | "Ej.: pegar la lista de clientes en un chatbot gratuito." |
  | `quote` | a pull-quote / cited line (rendered italic) | "Una falla de seguridad no siempre tiene un atacante." |
  | `note` | an aside / minor context | "Convención con respaldo en ISO 27001 / NIST." |
  | `source` | **a bare reference to where the material came from** — a citation, not a callout | "Fuente: OWASP Top 10 for LLM Applications (2025)." |

  `source` is the one kind rendered **plain**: no card background, no accent bar and **no icon** —
  just a small muted line, so the attribution never competes with the content it credits. Use it
  only for provenance (a paper, standard, dataset, report, URL); a line that *says something*
  about the source is a `note`.

  It is also the one kind that **leaves the content flow**: a citation is slide chrome, not a
  remark on the body, so it is pinned to the **bottom edge of the slide** rather than trailing
  wherever the content happens to end. Two things follow, and both are the reason for it — on a
  short slide it stays on the baseline instead of floating up under a half-empty body, and the
  per-slide content-fit pass can neither move nor shrink it. **`position` does not apply to a
  `source`**; every other kind is a remark and stays with what it remarks on.

  **`position`** — where the entry's band sits, `"bottom"` *(default)* or `"top"`. It is **per
  entry, not per slide**: the render groups all `top` entries into one band above the body and all
  `bottom` entries into one below, each in array order, so a slide can open with a framing line and
  still close with a takeaway. Choose by the job the line does, not by its `kind`:

  | `position` | The line's relation to the body | Typical kinds |
  |---|---|---|
  | `bottom` *(default)* | a **remark** — it comments on, concludes, or qualifies what the audience has just read | `takeaway`, `note`, `example` |
  | `top` | a **frame** — it has to be in the audience's head *before* the body makes sense | `quote` that sets the theme, `definition` a term the items use, `important` that is a warning up front |

  Both bands are the same piece in a different place: identical classes, accent colour and icon.
  An unrecognized value falls back to `bottom`, like an unrecognized `kind` falls back to `takeaway`.
- **`design` + `media`** — a slide is a **design** filled with a **style**, and the two are chosen
  in that order. The **design** is how the canvas is divided; the **style** is the `template`, the
  shape the content takes inside it. They are independent: **every content template accepts every
  design**, because the renderer's stage places the media and the template only emits content.

  `media` is `{src, alt}` — the one picture the design places. `design` is one of:

  | `design` | The canvas | Use it for |
  |---|---|---|
  | `full` *(default, omitted)* | content uses the whole stage; no media placed | anything that doesn't pair with a picture |
  | `split-right` | content left, media right — media **contained**, never cropped | a diagram, chart or screenshot the audience actually reads |
  | `split-left` | mirrored: media left, content right | the same, when the picture should be read *first* |
  | `banded` | media across the top, content as a band under it | one wide image with a short caption under it |
  | `column-right` | a narrow full-bleed strip of media down the right edge, **cropped to fill** | atmosphere — an evocative image that sets a tone, never read closely |
  | `column-left` | the same strip down the left edge | the same |
  | `bleed` | media fills the stage; the content sits over it | a picture that *is* the slide |

  **Contained vs cropped is the whole `split` / `column` distinction.** A split gives the media half
  the canvas and shows all of it; a column gives it a strip and crops to fill. Anything
  load-bearing must be a `split` (or a template that owns its image, like `figures`) — put a chart
  in a `column` and it gets cut. Set it from an author `<!-- design: … -->` hint, else pick it from
  the content.

  Only the two columns swap between `split-left` and `split-right`. The enumeration never mirrors:
  facts keep their left-edge dots, cards their icons, steps their numbering, all still left-aligned
  and in source order. Reading order is unchanged too — the markup is always head → content →
  media, whatever the design — so PDF export and screen readers are unaffected. A design with no
  `media` to place renders as `full` and warns rather than failing silently.

  > **The old spellings still work.** `image` is read as `media`; `layout: text-left / image-left /
  > image-top` as `split-right` / `split-left` / `banded`; `aside: {image, side}` as
  > `column-right` / `column-left`. Existing models render exactly as they did, with no warning.
  > New models should write `design` + `media`: `layout` only existed on five templates and only
  > when the slide carried an `image`, and `aside` was a second vocabulary for the same decision —
  > which is precisely what made a template that wasn't on the list impossible to compose.
- **`format`** — an **optional** field on `concept-breakdown`, choosing how the labeled set is
  arranged. Like `design`, it is a *formatting* decision made **after** the template, not a second
  classification: the shape ("N parallel labeled concepts") is what picks the template, and this
  picks its presentation. Pick it by count and body length:

  | `format` | When | Layout |
  |---|---|---|
  | `grid` *(default, omitted)* | any count 2–8, bodies up to ~2 sentences, or a bare anaphora | equal cards, icon **above** the label; 2 → side by side, 3 → a row, 4 → 2×2, 5+ → 3×N. A bodyless item is a label-only card |
  | `row` | a lead + 3–5 items, **every** body ≤ ~80 chars | one horizontal row of N cards, each headed by a filled accent chip |
  | `editorial` | 2–8 short-bodied concepts on a **flat** composition — no cards | a regular grid *without* panels: small icon beside the label, body indented under it. 2·4 → 2 cols, 3·5·6 → 3, 7·8 → 4; a short last row centers (5 → 3+2, 7 → 4+3) |

  **All three formats are grids.** A labeled set is N *parallel* concepts, and parallel concepts
  read side by side. The retired `list` format stacked them in one column, spending the full slide
  width on one item and making peers read as a sequence; there is no vertical-stack arrangement any
  more. A model that still carries `format: "list"` renders as `grid` and the build warns. If the
  per-item prose really needs a full-width column, the slide is not a labeled set → `content-text`,
  or split it.

  **`editorial` is the flat variant of `grid`** — same content, same fields, no card chrome. Choose
  it when the panels carry no meaning and the composition should read as a collection of concepts
  rather than an application screen: 2–8 parallel concepts, **short** bodies, icons as small
  reference marks, and no per-concept image. Keep `grid` when the panels are intentional design.
  Body budget shrinks with the column count — ~140 chars at 2–4 concepts, ~100 at 5–6, ~70 at 7–8;
  past that (or past 8 concepts) the build warns and the fix is falling back to `grid` (the card
  gives the body more room) or splitting the slide, **never** cutting the text down until it's
  unreadable. A `highlights` band stays
  full-width **below** the grid — a conclusion comments on the set, it is not another cell in it.
  *(Unrelated to the selectable deck **style** also named `editorial`, which only swaps colour and
  type tokens. This is composition; that is palette.)*

  The legacy template ids **`card-row`** and **`icon-list`** are still accepted: `card-row` means
  `concept-breakdown` with `format: row`, and `icon-list` — whose `list` format is retired —
  renders as the default `grid`, keeping its `lead` and its items. New
  models should emit `concept-breakdown`. Items go in `cards:[{label,body}]`; `rows:` is accepted
  as the legacy spelling of the same list. Set it from an author `<!-- format: … -->` hint in
  `draft.md`/`final.md` when there is one; otherwise pick it from the content by the table above.
  An unrecognized value renders as `grid` and warns, so a typo is visible rather than silent.
- **`reveal`** — an **optional opt-out** on any slide that reveals progressively. By **default** —
  field absent — the HTML deck steps through the slide on click (Reveal fragments):
  first the enumerated items one at a time (`stat`, `concept-breakdown`,
  `content+cards+image`), then the `bottom` `highlights` as one final block, so the takeaway text
  below the body lands *after* what it comments on rather than being readable from the start.
  The **`top` band is the symmetric case and therefore does not fragment**: it is on screen from
  the moment the slide opens, because a line that frames what is coming frames nothing if it
  arrives last. `"reveal": "together"` shows the whole slide at once instead. A slide with only
  `bottom` highlights and no enumeration still gets that one closing step.
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
| `concept-breakdown` | `title`, `cards:[{label,body}]` (2–6; 2–8 with `format:"editorial"`) | per-card `icon` (else content-matched), `lead`, `format` (`grid`\|`row`\|`list`\|`editorial`) — see below |
| `process` | `title`, `steps:[{body}]` (ordered) | `lead`, per-step `label`, and any `design` + `media` (a supporting diagram/example). **Steps with no `label` render as a numbered list** — one outlined number + the line per row — which is also where a **plain enumeration** of 3–8 unlabeled lines belongs (see below) |
| `figures` | `title`, `figures:[{image,label,body}]` | `lead` |
| `image-grid` | `images:[{src,alt}]` (≥4) | `title` |
| `image-full` | `title`, `image:{src,alt}` | `lead` (one line under the title) — the image fills everything below the header, edge to edge; **no** `facts`, `cards` or `highlights` belong here |
| `content-image` | `title`, `media:{src,alt}`, and **text** — `facts:[{body,label?}]` and/or `lead` | `design` (its caption band is what `banded` is for). With neither `lead` nor `facts` the slide is **`image-full`**, not this — the renderer still drops the empty text column defensively, but that shape belongs to the other template |
| `content+cards+image` | `title`, `cards:[{label,body}]`, `media:{src,alt}` | `lead`, per-card `icon` (else content-matched), `design` |
| `value-columns` | `title`, `columns:[{header,cells:[str]}]` (2–3) | `lead` (one framing line above the grid), `design` + `media` (a supporting diagram/example). Beside media the grid keeps ≤3 columns and ≤5 rows — past that the build warns and the slide should split |
| `stat` | `title`, `stats:[{value,caption}]` (2–4) | `lead` |
| `big-number` | `number`, `caption` | `title` |
| `quote` | `quote` | `attribution`, `section` |
| `timeline` | `title`, `milestones:[{label,body}]` | `lead`, per-milestone `marker` |
| `pros-cons` | `title`, `pros:[str]`, `cons:[str]` | — |
| `quiz` | `question`, `answer` | `title` (topic), `options:[str]` (choices), `correct` (the right choice — option text, 1-based index, or letter A/B/C…; highlighted on reveal), `explanation` (extra reveal), `design` + `media` (shown beside the quiz — use a `split`, never a `column`, so it is not cropped), `answer_label` (label on the answer panel; default "Respuesta") |
| `single-point` | `title`, `point:{label,body}` | `point.icon` (else content-matched) |
| `callout` | `callout:{label,body}`, `tone` (`pink`\|`blue`) | `title`, `callout.icon` (else content-matched) |
| `code-example` | `title`, `code` | `language`, `explanation:[str]` |
| `content-text` | `title`, `big`, `panels:[str]` | — *(last-resort prose; flag to restructure)* |
| `closing-hero` | `title` | `body` |
| `closing-cta` | `title`, `items:[{label,body}]` | — |
| `fallback` | `title` | `big` (the dominant line; defaults to `title`), `points:[str]` (rendered as accent panels, never plain bullets) — *last resort; the renderer warns, and a recurring fallback means the catalog needs a new entry. An unlabeled list is **not** a fallback: it is a `process` numbered list (or, for an anaphora, a label-only `concept-breakdown`)* |

> `cover` takes no row: it is **synthesized from the `deck` object**, never authored as a slide
> (see `deck` above). Every other `template` value the renderers accept is listed here — a value
> outside this table renders as `fallback` and the HTML build warns on stderr, naming the slide.

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
  classification), `<!-- design: <value> -->` pins its `design` field (how the
  canvas is divided — skip the design judgement below; the older `<!-- layout: … -->` spelling is
  read the same way), and `<!-- reveal: together -->` sets its
  `reveal` field. These are the only HTML comments read rather than dropped. (They ride from `draft.md` into `final.md` unchanged —
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
  `figures` `[{label,body}]`, **never plain bullets**; drop an item that just repeats the title.
- **A list with no labels** is one of two things, and neither is `fallback`:
  - a **plain enumeration** — 3–8 lines that each state something on their own (the logistics of a
    course, the rules of an assignment, a set of conditions) → **`process`** with
    `steps:[{body}]` and no `label`, which renders as a **numbered list**. Number them even when
    nothing is sequential: the count is what turns a loose list into a set the audience can hold
    and the presenter can point at.
  - an **anaphora** — 2–5 short parallel *fragments* sharing an opening, whose force is the
    rhythm ("No hubo hackers. No hubo malware.") → `concept-breakdown` (default `grid`) with
    `cards:[{label}]` and `body:""`, rendering as label-only cards. Numbering these would trade
    the rhetoric for a checklist, which is why they don't go to `process`.
- **Process ordinals** are renderer chrome, not content. When filling `process.steps`, strip any
  ordinal/step marker from the extracted `label` or `body`. Then apply the colon lead-in rule:
  anything before `:` becomes the highlighted `label`, anything after becomes `body`. Examples:
  `1 · Leave feedback: drop bullets in draft.md` → `label:"Leave feedback"`,
  `body:"drop bullets in draft.md"`; `1. **Leave feedback** drop bullets...` and
  `Paso 1: Leave feedback` → `label:"Leave feedback"`. The renderer supplies the visible 1/2/3,
  so keeping the source ordinal would duplicate it.
- **Standalone metrics** — the number is `value`, its trailing text the `caption` (`stat.stats`;
  a lone hero metric fills `big-number.number` + `caption`).
- **A pipe table** → `value-columns.columns:[{header,cells}]` (header row → `header`, body cells in
  column order); a label/value table decomposes as `cards`. *(Which template a given shape gets is
  the catalog's Match rules — not restated here.)*
- **Images** — carry `src` paths exactly as written into `image:{src,alt}` / `images` / `figures`.
  **Never rewrite the extension.** A `.svg` ref stays `.svg`: the HTML render inlines it as vector
  markup, and swapping it for the `.png` companion silently downgrades a crisp diagram to a raster.
  (`.svg` is forbidden only on the `.pptx` path, whose prerequisite check owns that rewrite — it is
  not a rule about filling the model.) A fenced code block fills `code-example.code`
  (+ `explanation`).
- **`design` — the picture's place is chosen after the template, never instead of it.** Set
  `"design":"split-left"` whenever the media should lead the eye (a diagram the prose then walks
  through, or to break up a run of split-right slides), `"banded"` when the text is too short to
  hold a column, and a `column-*` only for atmosphere that may be cropped. It means the same thing
  on **every** template — that is what the field is for.
  **Never pick the template to get the placement.** Wanting the image first is not a reason to
  demote a labeled set to `content-image` `facts` (which lose their per-concept icons) — keep
  `content+cards+image` and set `design`. The same holds one step up: a **table** with a supporting
  diagram keeps `value-columns` (its aligned columns) and takes `media` + `design` — flattening the
  rows into `content+cards+image` cards concatenates the two values into one body and throws away
  the column alignment that *is* the slide. An author `<!-- design: <value> -->` hint **pins** the
  field: copy it through instead of judging.
- **A slide that is only an image is `image-full`.** A screenshot or diagram the presenter narrates,
  its detail in `notes`, is a normal slide shape: fill `title` + `image` (plus a `lead` if one line
  of framing helps) and stop. The header stays; the image takes everything below it, edge to edge.
  Do **not** reach for `image-grid` (which wants ≥4 images) to get chrome-free art, do not invent
  filler prose to justify a `content-image` text column, and do not move the slide's substance out
  of `notes` onto the face — the whole point of the shape is that the presenter talks over it.
- **`lead` vs `highlights` — a line that *introduces* the body is the `lead`.** A single line before
  a slide's enumeration or image is its sub-line: it fills `lead`. Only a line that *comments on*
  the body belongs in `highlights` — and then its `position` follows the same test: a **remark**
  closes (`bottom`, the default), a **frame** the audience needs before the body makes sense opens
  (`top`). The `**Label:** text` shape is not evidence either way — an `**Idea clave:** …` line
  written above the diagram is a lead, not a takeaway; routing it to `highlights` both empties the
  lead and moves the line to the foot of the slide, where it reads as a summary of something the
  audience has not seen yet.
- **Labeled lines (colon lead-ins) — the separator is CONSUMED, never carried.** When a line reads
  `Label: rest` or `- **Label**: rest` (a short lead-in before a separator), split it into
  `{label, body}` yourself. The renderer never parses the separator: it either puts `label` in its
  own heading or emits its own `: `. So whichever side you leave it on, it renders twice or dangles.

  Split at the **separator**, not at the `**`. These are the two ways to get it wrong — both were
  shipped in real decks:

  ```jsonc
  // source line:  - **Problemas bien definidos**: cuando el objetivo y los datos están claros.
  { "label": "Problemas bien definidos", "body": ": cuando el objetivo y los datos están claros." }  // ✗ stranded on the body
  { "label": "Problemas bien definidos:", "body": "cuando el objetivo y los datos están claros." }   // ✗ stranded on the label
  { "label": "Problemas bien definidos", "body": "Cuando el objetivo y los datos están claros." }    // ✓
  ```

  The rule, precisely:
  - `label` never **ends** with `:` `：` `—` `–` `-`; `body` never **begins** with one.
  - Separator forms all behave the same: `**Label**: body`, `**Label:** body`, `**Label** — body`,
    `Label: body`.
  - **Capitalize the body's first letter** once the separator is gone (`cuando` → `Cuando`,
    `épocas` → `Épocas`, `¿cuál` → `¿Cuál` — the letter, not the opening punctuation). A body that
    was already a standalone sentence keeps the casing it had.
  - **Only the head of `body` and the tail of `label`.** A colon *inside* either is content and
    stays: `body: "el ratio recomendado: 3 a 1"`, `label: "Ratio 3:1"`. A body opening with a minus
    sign (`-5% de margen`) is a value, not a separator.
  - A line with **no** separator (`- **Label** body`) splits the same way and the body keeps its
    original first letter — there is nothing to consume.

  This applies to **every** field that carries `{label, body}`, not just the one you are filling:
  `cards`, `rows`, `steps`, `figures`, `milestones`, `items`, `facts`, `highlights`, `point`,
  `callout`.
- **Highlights over dropping.** If a line is a comment or the key takeaway (often what a diagram
  builds to, e.g. "PII es un subconjunto de Personal Data"), put it in the slide's `highlights`
  rather than omitting it — content is never dropped (see the top-level rule).
- **Icons vs. emoji.** Icon-bearing templates (`concept-breakdown`,
  `content+cards+image`, `closing-cta`, `callout`, `single-point`) show one icon per item. The
  fill **may suggest** a per-item `icon` (a Material Symbols name), choosing a **distinct** one per
  item; when none is given the renderer content-matches — and never repeats an icon within a slide
  either way. This includes the single-item templates: `single-point` takes `point.icon` and
  `callout` takes `callout.icon`, both optional in exactly the same way. A suggestion the renderer
  cannot resolve falls back to a real glyph and warns; it is never dropped and never becomes a
  bare shape. Because an icon stands in for the emoji, **strip leading/inline emoji from the labels
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
