---
name: talksmith:ascii-to-svg
description: Render one ASCII diagram block into one SVG file, applying the standing visual rules in `config/diagram-style.md` plus optional caller style directives. Invoked by the `illustrator` role once per fenced ASCII block during Step 6 (Polish), with pre-extracted slide context passed in. CLI-safe.
---

# talksmith:ascii-to-svg — Render one ASCII block to one SVG

This skill renders **a single** ASCII diagram to **a single** SVG file. It is invoked once per fenced ASCII block by the [`illustrator`](${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md) role during Step 6 (Polish). Its scope is intentionally narrow:

| | Caller (`illustrator` role) does | This skill does |
|---|---|---|
| 1 | Invoke [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `scan` once; the scan output enumerates every fenced ASCII block **and** carries each block's pre-extracted slide context (`slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, optional `presentation_language`) | — |
| 2 | Pick the output filename `<slide-id>-<n>-<short-description>.svg` (kebab-case slug — see [`${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md`](${CLAUDE_PLUGIN_ROOT}/agents/illustrator.md) → *Output filename convention*) | — |
| 3 | Pass through the scan's `context` bundle + sidecar path + (optional) `style_directives` | — |
| 4 | — | **Render the SVG for that one block** |
| 5 | Aggregate results, report rendered/unchanged/failed counts | — |

The agent is the coordinator; this skill is the worker. One invocation = one SVG file. The caller never re-parses `final.md` — every context field comes from the scan bundle. This makes the dispatch trivially parallelizable across subagents.

## Caller contract

The agent must pass the following in the skill invocation prompt. **Two input modes** for the ASCII payload — exactly one must be provided:

- **Mode A — inline (legacy / one-off renders):** pass `ascii_block` as a verbatim string. Used when no `.ascii` sidecar exists yet.
- **Mode B — from file (Step 6 standard):** pass `ascii_file` = absolute path to a `.ascii` sidecar produced by [`talksmith:polish-ascii`](../polish-ascii/SKILL.md) → `extract`. The skill reads the file and **splits it on the `<!-- ascii-note:` sentinel**: everything before the sentinel (minus the separating blank line) is the ASCII payload; the comment from sentinel through `-->` populates the `ascii_note` context input. This is the canonical input mode during a normal Step 6 pass — the sidecar already carries both the source and the illustrator's render-time intent.

| Input | Required? | Example |
|---|---|---|
| `ascii_block` | Mode A | the fenced block's payload, verbatim |
| `ascii_file` | Mode B | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.ascii` |
| `ascii_note` | optional (Mode A only) | the captured `<!-- ascii-note: ... -->` if available. In Mode B the skill parses it from the sidecar; in Mode A you can pass it explicitly. The `intent:` / `emphasize:` / `labels:` lines drive per-diagram emphasis. |
| `output_path` | yes | absolute path, e.g. `talks/<Talk>/images/s1-2-1-cuatro-senales.svg`. In Mode B, if omitted, the skill defaults to the sibling SVG path (same basename as `ascii_file`, `.svg` extension). |
| `slide_title` | yes | from the slide's H2 heading (prefix-stripped) |
| `slide_content_prose` | recommended | the `### Content` body — used for subtitles, panel headings, in-panel callouts. Pass an empty string for sparse-context slides; the skill falls back to minimal labelling. |
| `speaker_notes` | recommended | the `### Speaker notes` body — used for `<desc>` and pedagogical-intent cues. Pass an empty string when the field is empty. |
| `section_title` | recommended | from the H1 the slide lives under |
| `section_goal` | recommended | from the section's `**Goal of this section:**` line |
| `talk_thesis` | recommended | top of `final.md` |
| `presentation_language` | recommended | from `config/profile.md` — determines language of all text in the SVG |
| `style_directives` | optional | freeform string with per-render visual instructions from the presenter (e.g. *"use orange for the model panel"*, *"don't use arrows, use plain lines"*). Applied **on top of** the standing rules in `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md`; if it conflicts with a standing rule, the directive wins for this render only — note the deviation in the report. |
| `repo_root` | yes | absolute path to the presenter's **working directory** (the folder where `/talksmith:init` ran — contains `CLAUDE.md`, `config/profile.md`, `talks/`). The skill uses this to anchor Talk-relative paths the caller passes. Plugin-bundled assets like `diagram-style.md` are loaded via `${CLAUDE_PLUGIN_ROOT}/` directly and do **not** depend on `repo_root`. The illustrator role passes it from its own dispatch context. |

## Process

0. **Resolve input mode.** If `ascii_file` is provided, read it, split on the first line starting with `<!-- ascii-note:`. The ASCII payload is everything before that line (rstrip a trailing blank line); the `ascii_note` is everything from the sentinel through the line containing `-->` (inclusive). If no sentinel is present, the whole file is the ASCII payload and `ascii_note` is empty. If `ascii_block` was passed instead, use it directly and treat any caller-supplied `ascii_note` as authoritative.

1. **Detect diagram vs code.** If the resolved ASCII payload is a real programming language (Python, bash, JSON, YAML, etc.) or contains no diagram glyphs (`+-|`, `─│┌┐└┘├┤┬┴┼`, `→ ← ↑ ↓ ⇒ -->`, `=>`, `~~~`, `/\`, `<>v^`), stop and return `skipped: not a diagram`.

2. **Load standing visual rules.** Read `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md` — a **plugin-bundled asset**, never `<repo_root>/config/…` (the presenter's working directory has no such file; looking there silently drops the palette). Treat its bullets as hard constraints. If the file genuinely doesn't exist (a broken install), render with sensible defaults (light background, flat 2D, plain typography) and note `deviations: no diagram-style.md` — that line means *the plugin is broken*, say so in the report. `repo_root` is still required (it anchors Talk-relative paths); if missing, stop with `failed: repo_root input missing`.

3. **Merge with per-render directives.** Apply `style_directives` (if any) on top of the standing rules. A per-render directive that contradicts a standing rule wins for this render only — note the deviation in the report. A directive that adds to the standing rules (e.g. a specific color for a panel) is taken verbatim.

4. **Generate text from context, not from the ASCII.** The ASCII gives layout. The labels come from:
   - SVG `<title>`: `slide_title`
   - SVG `<desc>`: the first sentence of `speaker_notes` (one line); fall back to a `slide_title`-derived sentence if `speaker_notes` is empty
   - Per-panel heading: pull from `slide_content_prose` — the words the audience will hear
   - Per-panel subhead: the secondary phrase from `slide_content_prose`
   - In-panel callouts (axis labels, peak markers, equation captions): drawn from `speaker_notes` when it flags something to emphasize
   - **All text in `presentation_language`** — never mix languages. If unclear, fall back to the dominant language of `slide_content_prose`.

5. **Render the SVG.** Use a `viewBox` proportional to the diagram's aspect ratio (commonly `0 0 680 H` for landscape diagrams). Include `<title>` and `<desc>` as the first two children of the root `<svg>` for accessibility. Choose colors and shapes that satisfy *every* standing rule + any non-conflicting per-render directive. When the diagram has semantic structure (input/output, before/after, baseline/improved), use distinct hues to make the structure visible; default palette is the presenter's choice or a tasteful neutral if no directive is provided.

   **Aspect-ratio contract — the SVG's intrinsic aspect is load-bearing downstream.** The Step 7 PPTX renderer sizes each picture's slot from this SVG's `viewBox` ratio (per [`${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md) §12) and an audit (`audits/aspect_ratios.py`) fails the build at 1% tolerance if the rendered `cx:cy` diverges from `viewBox_w:viewBox_h`. So:
   **How to arrive at the viewBox — lay the art out first, then frame it.** The viewBox is an *output* of the layout, not an input to it. In order:

   1. **Lay out the art** from the content: box sizes from the text they hold, gaps from the labels that sit in them, rows from what stacks. Do not pick a target ratio first and fit the art to it.
   2. **Measure the ink** you just laid out — its full extent, left-most to right-most, top to bottom.
   3. **Add an even margin** on all four sides. Even in *viewBox units*, not in percent: a 20-unit frame is 20 units everywhere, whatever the aspect.
   4. **The viewBox is that framed rectangle.** Round to whole units. Its ratio is whatever it is — it will read slightly *less* extreme than the ink's own ratio, because the margin is a bigger fraction of the short axis. That is correct and expected; do not "fix" it.

   The margin frame is the part `audit_aspect.py` actually verifies (step 9), so this is the procedure that passes it. Nothing checks a ratio *target* — there is no such thing.

   - **Do not derive the ratio from the character grid.** It is tempting (`chars × 0.5 : lines`) and unreliable: it cannot know that a label column needs real width, that a callout drawn from `speaker_notes` per step 4 adds a row the ASCII never had, or that three cramped ASCII lines become a bracket plus a pill plus a caption. The grid is the source's shape; you are drawing the art's. A smell test at most, never the answer.

   **Hoist inheritable attributes to the root — this step is output-token-bound.** Emitting the XML is the whole cost of the render; every byte you don't emit is time you don't spend. Declare `font-family` **once on the root `<svg>`** and never repeat it on each `<text>` — SVG inherits it down the tree, so the render is pixel-identical while the file gets meaningfully smaller. The same applies to any presentation attribute most children share (`font-size` when one size dominates, `fill` for the default ink): declare high, override only the exception.

   - **Inheritance is by tree, not by document order** — the part that bites. An attribute may only be omitted when the element's nearest declaring *ancestor* supplies the same value. A `<tspan font-family="'DejaVu Sans Mono', monospace">` inside a `<text font-family="Helvetica, …">` **must keep its declaration** even when the root declares monospace — the tspan inherits from its parent `<text>`, not the root; dropping it silently reverts an inline code span to Helvetica, invisible in the XML.
   - This is an authoring rule, not a cleanup — a post-processing pass cannot recover the seconds already spent emitting the redundant bytes.

   - Do **not** set `width="…"` / `height="…"` attributes on the root `<svg>` at values that disagree with the viewBox ratio. Either omit them entirely (consumers honor viewBox alone — preferred) or set them to the same numbers as the viewBox so there is one source of truth.
   - Do **not** set `preserveAspectRatio="none"` anywhere. The default `xMidYMid meet` is correct; `none` signals to consumers that anamorphic scaling is OK and defeats every downstream guarantee.
   - When the same diagram could plausibly fit two ratios (e.g. a flow that reads either as a wide row or a tall column), pick the one the *content* actually demands and commit — never split the difference. A near-square viewBox to "hedge" against the eventual slot is the bug — the slot adapts to the SVG, not the other way around.
   - `W` is free. `0 0 680 H` is a common choice for moderate aspects, not a rule — very wide art needs a larger `W` to leave legible height (a 6.7:1 diagram at W=680 gets ~102 units of height, too little for three rows of text).
   - **There is no useful self-check you can run in your head** — any "would the raster match" arithmetic derives from the viewBox and confirms itself by construction. The real check is mechanical and runs in step 9.

6. **Write the SVG** to `output_path`. Create the parent directory if it doesn't exist (`mkdir -p`). Overwrite if the file already exists — idempotency is the caller's concern, not this skill's.

   **Then validate it against the aspect-ratio contract** by running [`validate_svg.py`](validate_svg.py) on the file you just wrote:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/validate_svg.py <output_path>
   ```

   The validator checks the same contract spelled out in step 5 and rewrites the file in place when it can auto-repair:
   - **viewBox present + parseable** with positive W, H → unfixable; exit 2 if missing or malformed.
   - **No `preserveAspectRatio="none"`** on the root `<svg>` or any nested `<svg>`/`<image>` → auto-fixed by dropping the attribute (default `xMidYMid meet` restored).
   - **Root `width`/`height` either absent or agree with the viewBox W:H ratio within 1%** → auto-fixed by dropping both attributes (viewBox is authoritative).

   A non-zero exit means the SVG is broken in a way this skill can't mechanically repair (no viewBox, malformed XML, root element isn't `<svg>`). When that happens, **do not return success** — return `failed: svg_validation: <error>` per step 9. A broken SVG must not reach disk: the downstream PPTX renderer trusts the viewBox to size its placement slot, and a faulty viewBox poisons the [`audits/aspect_ratios.py`](../md-to-deck/audits/aspect_ratios.py) gate at PPTX-build time (one full render cycle wasted). Catching it here is cheap; catching it there is expensive. If repair happened, note the fix count in the step-9 report under `svg_validation:`.

7. **Rasterize a deliverable PNG companion** at `<output_path with .png extension>` (same directory, same basename). This is the **build deliverable** the Step-7 PPTX renderer consumes (it loads images via PIL, which cannot decode SVG). Every render produces both files (illustrator's *Output contract*); [`md-to-deck`](../md-to-deck/SKILL.md)'s prereqs stop the build if the `.png` a `final.md` ref points at is missing.

   **Always rasterize through [`rasterize.py`](rasterize.py). Never call `cairosvg` (or anything else) inline.**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/rasterize.py <output_path> \
       -o <output_path with .png> --width <viewBox_w * 2>
   ```

   Width = SVG `viewBox` width × 2 (e.g. `viewBox="0 0 680 318"` → `--width 1360`); the height follows the viewBox automatically. The script verifies the PNG it wrote actually matches the viewBox ratio and deletes it + exits non-zero if it doesn't — so a mis-shaped PNG can't reach the deck. On a non-zero exit, return `failed: png_deliverable: <reason>` per step 9; the SVG alone is not a successful render.

   Going through the script is not a style preference. It owns the libcairo lookup that inline `import cairosvg` gets wrong (see the *Rasterizer* section below), and it is the only thing standing between a silently wrong PNG and the .pptx.

8. **Rasterize a critique-companion PNG.** Same script, different width and destination — write to `<output_path parent>/.critique/<basename>.png` (the script creates `.critique/` if missing):

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/rasterize.py <output_path> \
       -o <parent>/.critique/<basename>.png --width 1600
   ```

   This PNG is **not** referenced from `final.md`, **not** consumed by the Step-7 PPTX renderer, and **distinct from the deliverable PNG in step 7**. It exists for exactly one reader: the blind [`diagram-critic`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-critic.md) subagent, whose only view of the render this is. Get its shape wrong and the critique is performed on a diagram that doesn't exist.

   If it fails, still report the SVG as `rendered` but add `png_critique: failed` to the report — no pixels means the critique loop is blind for that block (the illustrator records it `unresolved`), but the SVG itself is intact. Never delete the SVG because a PNG step failed.

9. **Aspect audit — the one defect no critique can see.** Run [`audit_aspect.py`](audit_aspect.py) against the SVG and the deliverable PNG from step 7:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/audit_aspect.py <output_path> \
       --png <output_path with .png>
   ```

   Exit 0 = the frame is sound. Exit 1 = the viewBox doesn't fit the art: report `aspect_audit: <the tool's defect line, verbatim>` in step 10 and return it as a **defect**, not a failure — the SVG stays on disk and the illustrator folds the finding into its next-iteration `style_directives` exactly like a critic defect. Exit 2 = the audit itself couldn't run (no viewBox, blank raster); surface as `failed: aspect_audit: <reason>`.

   **Why a script and not the critic.** This is the single defect class visual review is *structurally* incapable of catching: the critique PNG is rasterized **from** the viewBox, so a wrong viewBox produces a correct-looking PNG with the surplus reading as deliberate whitespace — nothing for an eye to find. Caught here it costs one iteration; uncaught, it detonates a full render cycle later when the PPTX slot is sized from the viewBox.

   **What it does and does not guarantee.** It checks that the frame *fits the art* — even margins around the ink. It does **not** check that the proportions were right for the art in the first place: evenly-framed art passes at any aspect, so `ok` means "this frame fits this art", never "this was the right shape". That second judgement is the renderer's, and nothing verifies it.

   Pass the tool's line through **verbatim** — it proposes a corrected viewBox that is a pure crop, precise enough that the re-render usually lands in one pass. Do **not** apply the suggestion yourself: whitespace is sometimes intentional, and reframing the presenter's diagram isn't this skill's call.

10. **Return** a one-line report:
    - On success: `rendered: <output_path> · svg_validation: <ok|N fix(es)> · png_deliverable: <path> · png_critique: <path|failed> · aspect_audit: <ok|defect: …> · directives_applied: <count> · deviations: <none|description>`
    - On skip: `skipped: <reason>`
    - On failure: `failed: <reason>` — and do **not** write a broken SVG. Validation failures from step 6 (unfixable viewBox) surface here as `failed: svg_validation: <error>` and must delete (or never have written) the broken file. Deliverable-PNG failures from step 7 surface as `failed: png_deliverable: <reason>` — without the PNG the Step-7 PPTX renderer cannot consume the asset, so the render is incomplete; the SVG bytes may stay on disk but the report must not declare success.

    An `aspect_audit` defect is **not** a failure — the render succeeded and the SVG is on disk; the frame is wrong. Report it on the success line so the illustrator can act on it in the next iteration.

## Rasterizer — cairosvg, required, no fallback

[`rasterize.py`](rasterize.py) uses **`cairosvg`**, and nothing else. `qlmanage` was the documented macOS fallback and has been removed on measured evidence:

- **It letterboxes.** `qlmanage -t -s N` does not render N wide — it fits the art into an N × N square and pads the short axis with *opaque* white. A 640×360 SVG came back as a 1200×1200 PNG with white bands. That square went into the deck, and the PPTX slot (sized from the viewBox, correctly 16:9) got a 1:1 image.
- **It disagrees with cairosvg.** Even cropped back to the viewBox ratio, its geometry diverges — on one of this repo's own fixtures the cropped qlmanage output placed the ink 100px away from cairosvg's at identical dimensions.

A backend that draws differently isn't a fallback; it's a second renderer that disagrees in silence, and it would put the critic and the deck on different pixels. Failing loudly is better.

**Installing it — `pip install cairosvg` is not enough on macOS.** The package installs cleanly and then raises `OSError` at import, because the stock `python3` (Xcode's) cannot see Homebrew's libcairo: `ctypes.util.find_library()` searches dyld's default paths, which exclude `/opt/homebrew/lib`, and SIP strips `DYLD_*` from Apple-signed interpreters. `rasterize.py` already works around this by preloading the dylib from a list of known locations — but the C library has to exist:

```bash
brew install cairo && pip install cairosvg        # macOS
apt install libcairo2 && pip install cairosvg     # Linux
# Cowork sandboxes: pip install cairosvg --break-system-packages
```

If `rasterize.py` reports `cairosvg unavailable`, that is the real message and its hint text says exactly this — do **not** work around it with another tool.

## You cannot ask questions

This skill cannot ask follow-ups. If the standing rules + slide context + `style_directives` together don't disambiguate a critical choice, return `failed: ambiguous · <what's unresolved>`. The illustrator role surfaces the ambiguity to the orchestrator, which asks the presenter and re-invokes this skill with the disambiguation baked in.

**Sparse-context is not ambiguous.** When `slide_content_prose` and/or `speaker_notes` are empty, render with whatever context is present (`slide_title`, `section_title`, `section_goal`, `talk_thesis`) and pick neutral colors derived from box order rather than slide-prose keywords. Add `deviations: sparse-context (no <field>)` to the success report. Do **not** return `failed: ambiguous` just because prose is empty — an empty SVG is worse than a sparsely-labelled one.

## Boundaries

- **Never write outside `output_path`** (+ its PNG companions) — no edits to `final.md`, no sibling files.
- **Never read network resources.** Pure local file work.
- **No template catalog.** The standing rules in `${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md` plus per-render directives are the full styling input; rules accumulate there over time as patterns crystallize.
