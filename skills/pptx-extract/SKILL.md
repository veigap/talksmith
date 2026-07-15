---
name: talksmith:pptx-extract
description: Reconstruct a Talk's presentation Markdown (`reconcile/finalpptx.md` + inventory + staged images) from a possibly hand-edited `.pptx`. First stage of the reverse pipeline — run before `talksmith:pptx-diff` and `talksmith:pptx-merge`. Mandatory `--style {strict|free-form}`. Requires `python-pptx`; no Cowork dependency.
---

# talksmith:pptx-extract — Rebuild the presentation Markdown from a deck

Talksmith's forward pipeline is one-directional: `draft.md` → `final.md` → `talks/<Talk>/output/final.pptx`. When a presenter opens that deck in Keynote/PowerPoint and **edits text or swaps/adds images**, those edits live only in the `.pptx`. This skill reads the edited deck back into the canonical Markdown shape so the changes can be diffed (`talksmith:pptx-diff`) and merged into `draft.md` (`talksmith:pptx-merge`).

| The caller does | This skill does |
|---|---|
| Points at the edited `.pptx` + the active Talk + the render style | Parses the deck, classifies slides, de-dups images, writes `finalpptx.md` + inventory |
| Refines the mechanical draft (resolves `<!-- reconstruct: ... -->` markers) | Emits a conservative first pass; never invents Thesis/Sources |

Reading a `.pptx` needs only `python-pptx` (a `pip install`), not the native `pptx` skill — so, unlike [`md-to-deck`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/SKILL.md), which is Cowork-only because *authoring* a deck needs the native `pptx` skill, this skill is fully CLI-safe.

## When to use

- A presenter edited the generated deck externally and wants those edits pulled back into the Talk source.
- Any time you need a Markdown view of what a `.pptx` actually contains, in `draft.md` shape.

Run this **first** in the reverse pipeline, then `talksmith:pptx-diff`, then `talksmith:pptx-merge`.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| `pptx` | yes | Path to the edited deck, e.g. `talks/<Talk>/output/final.pptx`. |
| `--talk` | yes | Talk root, e.g. `talks/<Talk>`. Its `images/` folder is the reference set for image de-duplication. |
| `--style` | yes | `strict` or `free-form` — **no default**. Cover fingerprint, section-pill fill, and agenda dot colors are style-specific. `strict` supports full cover/agenda/divider classification; `free-form` only reliably identifies the cover (content grouping is flat — a warning is emitted). |
| `--stage-new` | deprecated | No-op kept for backward compat — **every** content image is always staged under `reconcile/staging/`. Image identity is resolved later by `pptx-diff`. |

## Subcommands

### 1. `pptx_inventory.py` — deck → inventory JSON

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-extract/pptx_inventory.py \
  talks/<Talk>/output/final.pptx --talk talks/<Talk> --style <strict|free-form> \
  --stage-new [--human]
```

Resolves true presentation order (`ppt/presentation.xml` `<p:sldIdLst>` + rels — not filename order). Per slide: detected title, body blocks (bullets/paragraph/callout/table), speaker notes (`notesSlideN.xml`), and embedded images.

Classifies each slide **cover / agenda / section-divider / content** — a divider is an agenda re-emit with **exactly one active red dot**; the active dot's row index is the section number.

Each image is either `template` (logo / branded icon / reused chrome → ignored) or `content` (staged to `reconcile/staging/slide<order>-img<ordinal>.<ext>` and recorded with its byte hash + intrinsic dimensions + 1-based slot ordinal). **Template asset detection is a five-tier ladder** — Keynote/PowerPoint rename icons on export, so filename regex alone is not enough:

1. **Known template basenames** — regex against `icon-*.svg/png`, cover logo `image-1-*`.
2. **Same-image reused within the slide** — the strict template's card-layout chrome pattern (e.g. `image-5-1.png` placed 3× on slide 5 as a card-divider banner). Any raster whose media path appears ≥2× on the same slide is chrome, not content — every occurrence is dropped.
3. **SVG-content sniffing (three triggers)** — an SVG is non-content when it carries `class="colorable-icon"`, `data-icon="..."`, `data-prefix="fa..."`; OR small root render dimensions (`width`/`height` both ≤128 px); OR **zero `<text>` elements at any dimension**. The text-absence trigger catches Satori-rendered card backgrounds, decorative rectangles, and blank separators regardless of size — in this pipeline the ASCII illustrator always emits SVGs with label text, so a text-less SVG is by construction decorative. Applied to the SVG side of an `<p:pic>` even when we stage the PNG raster (see below), so PNG-with-SVG-twin decorations are caught reliably by SVG content.
4. **PNG-only icons by size** — for PNG rasters with no SVG twin (Cowork sometimes emits PNG-only accents like a 50×40 red badge), any PNG with `max(width, height) ≤ 128` is an icon.
5. **Sub-10 KB raster floor** — any staged PNG/JPEG under 10 240 bytes is dropped. Calibrated against on-disk content: the smallest ASCII-generated diagram is 30 KB, deck photos are 30 KB+, and no legitimate content image was ever below 10 KB. Catches thin decorative bars (170×300, 2.3 KB) that survive the icon/size/reuse filters because they're used only once at non-icon dimensions.

Bytes-per-pixel is deliberately NOT a signal: real ASCII-generated diagrams compress to 0.02–0.05 bytes/pixel (line art on white backgrounds) and would be false-positived as "blank" by that metric.

**Pic-blob preference: PNG over SVG** for staging/comparison. When a `<p:pic>` carries both an SVG source and a PNG raster fallback (§17.4 pattern), the extractor picks the PNG bytes — PNG encoders are deterministic, so the same rendered visual reliably byte-matches across the round-trip. SVG serialization drifts across Keynote/PowerPoint saves. `final.md` refs `.png` (Keynote-safe) anyway, so PNG-to-PNG is the canonical comparison shape.

The inventory also carries a `known_hashes` map (`sha256 → images/<file>`) so downstream diff can fast-path byte-identical images. Writes `talks/<Talk>/reconcile/finalpptx.inventory.json`.

### 2. `reconstruct_md.py` — inventory → `finalpptx.md`

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pptx-extract/reconstruct_md.py \
  talks/<Talk>/reconcile/finalpptx.inventory.json --talk talks/<Talk>
```

Skips cover/agenda/divider; groups content slides into `# <k>. <Section>` by divider boundaries; renumbers `## <M>.` within each section; fills `### Content`, `### Sources` (stub), `### Speaker notes`, and image refs. Writes `talks/<Talk>/reconcile/finalpptx.md`. **Every content image ref points at its `reconcile/staging/…` copy** — reconstruct never guesses whether the deck's image is the "same" as one in `images/`; that decision is made by `talksmith:pptx-diff` via slot alignment. Refs stay Talk-root-relative so downstream stages resolve them against the Talk root.

## Output

```
talks/<Talk>/reconcile/           # all reverse-pipeline artifacts live here
├── finalpptx.inventory.json      # ordered slide inventory (consumed by pptx-diff)
├── finalpptx.md                  # reconstructed presentation in draft.md shape
└── staging/                      # EVERY content image extracted from the deck
    ├── slide3-img1.png           #   (slot-anchored names: slide<order>-img<ordinal>)
    ├── slide5-img1.png           #   pptx-diff decides which of these differ from
    └── ...                       #   images/ via slot alignment; merge copies only
                                  #   the differing bytes over.
```

## What round-trips vs. what is lossy

**Faithful (mechanical):** section structure, slide titles, bullets/paragraphs/tables, speaker notes, byte-identical generated images.

**Lossy — emitted as a stub + `<!-- reconstruct: ... -->` marker for the Editor to resolve:**
- `# Thesis` and `### Sources` — both dropped by the forward render's FILL step (scaffolding never reaches the deck); unrecoverable from the deck.
- Callout source-form (three Markdown forms collapse to one rendered shape).
- Card / icon-list layouts (flattened to text).
- Multi-column reading order (geometry-inferred).

## Hand-off

The **Editor role** does a refine pass over `finalpptx.md`, resolving every `<!-- reconstruct: ... -->` marker — restoring Thesis/Sources from `draft.md` where round-trip fidelity is wanted, and fixing callout/card structure. Then run [`talksmith:pptx-diff`](../pptx-diff/SKILL.md).

## Boundaries

- **Read-only against the deck and `draft.md`/`final.md`.** Only writes under `talks/<Talk>/reconcile/` (`finalpptx.md`, `finalpptx.inventory.json`, and `staging/` — every content image is always staged).
- **No deck authoring.** This skill never writes a `.pptx`.
- Returns one-line status reports (`inventory: ...`, `reconstruct: ...`, `failed: ...`); it never prompts the user.
