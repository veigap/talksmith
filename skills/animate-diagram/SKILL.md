---
name: talksmith:animate-diagram
description: Render one ASCII diagram block as an ANIMATION — a looping GIF whose final frame (also written as the block's PNG) is the complete static diagram — by writing and running a short Python generator script on the bundled helpers. Owns the animation contract (canvas, timing, palette, final-frame rule) and the animation checklist the blind critic also applies. Invoked by the `diagram-illustrator` role during Step 6 (Polish) for blocks whose `ascii-note` says `animate:`; sibling of `talksmith:ascii-to-svg`.
---

# talksmith:animate-diagram — Render one ASCII block as an animation

The sibling of [`talksmith:ascii-to-svg`](../ascii-to-svg/SKILL.md). Same input (one `.ascii` sidecar + its slide context), same caller (the [`diagram-illustrator`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-illustrator.md) coordinator, one invocation per args file), same blind critique afterwards — but the output shows the operations being **applied live**: data entering, each block activating in order, tensors changing shape with their exact dimensions, the result building up, one caption per stage. The final frame holds the complete diagram, so the same render is also the static picture the PDF and the `.pptx` use.

Which blocks come here is decided upstream: the note's `animate:` field (grammar: [`editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md) → *ASCII diagrams*), capped by the presenter's one answer at Polish entry ([`orchestrator.md`](${CLAUDE_PLUGIN_ROOT}/orchestrator.md) → *Step 6*), routed by [`polish-ascii`](../polish-ascii/SKILL.md) → `prepare-render-args`, which writes one args file per animation with `"renderer": "animate-diagram"`.

## Caller contract — the args file

One JSON args file from `prepare-render-args`, plus the last three rows, which the coordinator adds to the dispatch.

| Field | Meaning |
|---|---|
| `kind` | `inference` (how the model / pipeline / algorithm runs) or `training` (how it learns). Recipes below. |
| `ascii_file` | The block's `.ascii` sidecar — ASCII payload + `ascii-note`, split on `<!-- ascii-note:` exactly as `ascii-to-svg` Mode B does. The ASCII is the **layout and the content**: every block, arrow and dimension it shows must appear, and nothing may contradict it or the slide's prose. |
| `script_path` | Where the generator goes: `talks/<Talk>/images/.anim/<stem>.py`. |
| `gif_path`, `png_path` | `images/<stem>.gif`, `images/<stem>.png` — written by the script, never by hand. |
| `frames_dir`, `contact_sheet` | `images/.critique/<stem>.frames/` and `images/.critique/<stem>.png` — the critic's view. |
| `slide_title`, `slide_content_prose`, `speaker_notes`, `section_title`, `section_goal`, `talk_thesis`, `presentation_language` | The scan's context bundle. Captions and labels are in `presentation_language`; terms listed on the note's `terms:` line stay verbatim. |
| `companion` | Only on the training half of an `animate: both` block: the `title` (and `notes`) of the new slide the animation will sit on. |
| `rerun` | `true` when the stamped script is current and only its outputs are missing: **run it, write nothing**, no critique. |
| `*_rel`, `talk_rel`, `repo_root` | Mount-portable path twins — resolve them exactly as [`ascii-to-svg`](../ascii-to-svg/SKILL.md) → *Path resolution* says. |
| `python` *(dispatch)* | The interpreter to run the script with, from the coordinator's preflight (below). |
| `style_directives`, `defects` *(dispatch)* | Optional, as for `ascii-to-svg`; `defects` is the critic's verbatim list on a revision. |

**Return** one line — the last line the script prints, verbatim: `animated: <gif> · png: <png> · critique_frames: <frames_dir> · contact_sheet: <path> · cycle_s: <s> · size_mb: <MB> · warnings: <none|…>` — or `failed: <reason>`. The block subagent returns only that line (plus, on a revision, the edits it made) — never a self-assessment.

## Python — find it, or degrade

The generator needs **numpy, matplotlib and Pillow**. The `python3` on PATH often lacks numpy, so never assume it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/animate-diagram/find_python.py
# → "python: /abs/path/to/python3"   (exit 0) — use exactly this interpreter for every script
# → "unavailable: …"                  (exit 2) — no animations this pass
```

It probes `$TALKSMITH_ANIM_PYTHON`, the running interpreter, PATH, an active conda/venv, and the usual conda/Homebrew locations. The coordinator runs it **once per Step 6**, before dispatching. Exit 2 is not a failure of the Talk: every block falls back to the static SVG route (`annotate-renders --animations none`), the deck is complete, and the closing report says animations were unavailable and why. **Never block Polish on it.** `anim_helpers.py --check` (run under the found interpreter) confirms the deps, the font it resolved, and that the palette parsed.

## The animation contract

[`anim_helpers.py`](anim_helpers.py) enforces every number here when the script calls `Anim.save()`; this section is their prose owner.

- **Canvas.** 1600×900 (16:9), white ground, pixel coordinates with the origin top-left. Content centred, **40–60 px margins**, the whole canvas used — no empty half, nothing cut at an edge. The final frame's ink extent is audited mechanically (`layout_audit`).
- **Timing.** ~12 fps on transitions; **12–20 s per cycle**; the **final frame is held ≥ 3 s**; the GIF loops forever. A stage ends on a short hold (≈1 s) so the eye can read it.
- **Final-frame rule.** The last frame is the **complete static diagram** — every block, label, dimension and the finished result visible at once, caption summarizing the whole. It is written as `<stem>.png`: the still the PDF and the `.pptx` export use and the reference the critic judges the drawing by. An animation whose last frame is a mid-step is a broken still.
- **Atomic outputs.** `save()` writes the GIF and the PNG to hidden temporary siblings (`.<name>.tmp`) and renames them into place only when both are complete, so an interrupted run leaves the previous render (or nothing) — never a 0-byte or half-written GIF under the real name. Downstream, an **empty file counts as missing**: `prepare-render-args` re-runs a stamped script whose GIF or PNG is 0 bytes, `stamp-renders` never stamps one, and the coordinator's on-disk check asks for non-empty files. A stray `.tmp` from a killed run is harmless and overwritten next time.
- **Size.** ≤ 5 MB. One shared palette, brand colours pinned exactly; `save()` reduces colours, then frame rate on transitions, before it gives up and warns.
- **Palette.** The deck palette, read at run time from [`config/diagram-style.md`](${CLAUDE_PLUGIN_ROOT}/config/diagram-style.md) — its sole owner — and exposed as `ACCENT`, `INK`, `TITLE`, `FILL`, `RULE`, `PILL`, `CALLOUT_PINK`, `CALLOUT_BLUE`, `GROUND`; neutrals between them via `mix()`. **The accent marks what is active in this stage** (one focal thing at a time); `diagram-style.md`'s flat, light-mode, single-accent rules apply to every frame.
- **Type.** Sans (Helvetica/Arial/Liberation, DejaVu behind it for symbols), **never below 18 pt = 25 px at 1600 wide = 20 px at the deck's 1280**. `label()` raises anything smaller and reports it. Small blocks keep a minimum legible size; if text does not fit a block, the block grows, the text does not shrink below the floor.
- **Captions.** One line per stage at the bottom (`caption()`): **which operation is applied and what changes** (*"Max-pool 2×2: maximum of each 2×2 block → 15×15×4"*). Never anthropomorphize a model or a layer — no *asks / knows / understands / looks / wants / consults / writes / thinks / decides* (*pide, sabe, entiende, mira, quiere, consulta, escribe, piensa, decide*); `caption()` lints for them. No title inside the image — the slide has one.
- **Honesty.** Real computation (numpy) whenever possible, on **synthetic inputs made in the script** — no third-party images. A toy model is labelled as one once (`t("toy")`); anything illustrative is never presented as a measured result; a simulated predictor (the true noise standing in for a U-Net's prediction) is labelled as simulated. Real figures from papers only as small labels (*"SAM: 11 M images, 1.1 B masks"*).

## Two kinds

**Inference** (`kind: inference`) — how the model, pipeline or algorithm runs. Show the input entering; each block activating **in the order the computation runs** (accent border on the active block, ghosted blocks ahead of the data); tensors appearing with their **exact shapes** as each operation produces them; the output building up; one caption per stage. [`examples/inference_pipeline.py`](examples/inference_pipeline.py) is the reference.

**Training** (`kind: training`) — how it learns. One caption per scene, in this order:

1. the training datum **and its target** (label, true mask, the image itself, the added noise…);
2. **forward** through the model;
3. **loss**: the model's real formula on screen, with its **numeric value**;
4. **backward**: the gradient travels from the loss back, layer by layer, and reaches the weights;
5. **update**: `W ← W − η·∂L/∂W` (or *"optimizer: Adam"*, said so);
6. **several fast steps**: a loss curve drops in a corner (`curve()`, fixed scale) while the output visibly improves.

Mark **what is trained** (`box(state="trained")` — accent border, *se entrena* / *trained*) and **what is frozen** (`state="frozen"` — grey, lock, *congelado* / *frozen*). Check every analytic gradient with `grad_check()` before drawing it. Fixed colour scales across steps: the gradient strip must fade as the loss falls. [`examples/training_loop.py`](examples/training_loop.py) is the reference.

**For every model the talk explains, both are offered** (`animate: both`): the inference animation on the slide, the training animation on a companion slide right after it.

## Animation checklist

Both sides apply this list: the generator **while writing** the script, and the blind [`diagram-critic`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-critic.md) in its animation mode **while judging the frames** (it cites `[A#]`). Every item was a real defect on a real talk.

| # | Rule |
|---|---|
| A1 | **Feature maps are not the input shrunk.** An intermediate tensor shows ONE channel, labelled `1 de C canales` / `1 of C channels` (`tensor(channels=C)`). A position's vector through the depth is the embedding of that region — draw it pulled out (`vector()`). *Exception:* an SD-style VAE latent genuinely resembles the image. |
| A2 | **Exact, consistent dimensions, arithmetic checked** (224/2⁵ = 7, 7×32 = 224, 786 432 / 16 384 = 48, 32 − 3 + 1 = 30) and the same everywhere — frames, caption, slide prose. Technical claims correct (stride is not receptive field). Put the arithmetic in an `assert`. |
| A3 | **Arrows connect the right inputs to the right modules** (captions do not feed an image encoder). |
| A4 | **No line crosses a block or a label** — route around, or through a junction (`node()`, a Σ bus). |
| A5 | **Natural symmetry is drawn symmetric**: a U-Net's mirrored levels at equal heights; encoder/decoder pairs aligned. |
| A6 | **Synthetic subjects are recognizable at ~60 px** — a blurred cat read as a person, then as a dog. Check the silhouette small. |
| A7 | **Concepts right**: jointly trained encoders are what make a shared embedding space; CLIP has two encoders and no decoder; in Stable Diffusion training only the U-Net is trained (VAE and CLIP frozen). Mark trained / frozen accordingly. |
| A8 | **Every colour that encodes a class has a legend** (red = class, white = background, dashed = ground truth). |
| A9 | **Simulated is labelled simulated** (a predictor that uses the true noise; an illustrative encoder). |
| A10 | **Order of activation = order of computation**; exactly one stage active at a time; nothing appears before the operation that produces it. |
| A11 | **Fixed colour scales across frames** for the same quantity (`vmin`/`vmax`); a heatmap never re-normalizes per step. |
| A12 | **Captions** name the operation and the change, one line, presentation language, never anthropomorphic. |
| A13 | **Legible, balanced, complete**: ≥ 18 pt, whole canvas used, 40–60 px margins, final frame = the whole diagram. |

## Writing the generator

1. **Read** the sidecar (ASCII + note) and the context bundle. Decide the stages from the ASCII's left-to-right / top-to-bottom order and the slide's prose. List every dimension and check its arithmetic first (A2).
2. **Write the script** at `script_path` — short, because the helpers carry the drawing. Header, verbatim except for the paths:

   ```python
   #!/usr/bin/env python3
   """<one line: what this animation shows>. Generated by talksmith:animate-diagram from
   images/<stem>.ascii; regenerate with: <python> images/.anim/<stem>.py"""
   import os, sys
   sys.path.insert(0, os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT") or "<absolute plugin root now>",
                                   "skills", "animate-diagram"))
   from anim_helpers import *  # noqa: F401,F403
   ```

   Then: compute (numpy, synthetic input); define `draw(ax, st)` that paints the **whole** scene for one state; build the timeline with `anim = Anim(__file__, lang="<es|en|…>")`, `anim.frame(draw, state, seconds=…, key=True at each stage's end)`, `anim.tween(...)`, `anim.hold(...)`; finish with `anim.save()`. Never hardcode a hex colour — use the palette names.
3. **Preview first**: `<python> <script_path> --preview` renders only the key frames and the final one into `frames_dir`. Look at them for gross breakage (something cut, overlapping, unreadable) and fix it — a sanity pass, **not** the critique; the blind critic's verdict stays authoritative.
4. **Render**: `<python> <script_path>`. Its last stdout line is the report. Every `warnings:` entry (layout, caption lint, cycle length, size, raised fonts, palette) is a defect to fix and re-run before returning, unless fixing it would break a checklist rule — then report it.
5. **Revision** (`defects` given): translate each visual defect into an edit of the script — the critic describes pixels, you own the code — re-run, return the same line plus the edits made.

**Helpers, by name** (`anim_helpers.py` docstrings are the reference): `canvas`, `box` (states `idle` · `active` · `done` · `ghost` · `trained` · `frozen`), `arrow`, `node`, `window`, `tensor`, `vector`, `curve`, `formula`, `label`, `caption`, `badge`, `lock`, `mix`, `num` (decimal comma in Spanish), `t` (localized badge strings), `ease`, `grad_check`, `SEQ`/`DIV` colormaps, and `Anim` (`frame`, `tween`, `hold`, `save`).

## Boundaries

- Writes only `script_path` and what the script writes (`gif_path`, `png_path`, `frames_dir`, `contact_sheet`). Never `final.md`, never the sidecar, never another block's files.
- No network, no third-party images, no installs (a missing dependency is the coordinator's `unavailable`, not a `pip install` mid-pass).
- Never stamps — the coordinator's `stamp-renders` stamps the script once every wave has drained ([`polish-ascii`](../polish-ascii/SKILL.md)).
- You cannot ask questions: an ambiguity you cannot resolve from the ASCII, note and context is `failed: ambiguous · <what>` — the coordinator falls the block back to a static SVG.
