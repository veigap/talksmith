---
name: talksmith:animate-svg
description: Evolve one finished, static diagram SVG into its animated version, from the note's `animation:` brief and the slide's context. The model reads the diagram and its subject and authors the motion itself, honouring the practices in PRACTICES.md; frames of the result go to the blind critic. Writes the animated version beside the base (`<stem>.anim.svg`), never over it. Dispatched by the diagram-animator once a diagram's static render is approved (Step 6), or directly on a hand-authored diagram SVG that carries a note.
---

# talksmith:animate-svg — evolve a finished diagram into its animation

A static diagram shows the parts. Its animation shows **what the slide is about happening** — and what that is depends entirely on the diagram and its subject. So there is no catalogue of animation kinds here, and no parameters to fill: you read the diagram, the note's `animation:` brief and the slide, and you **evolve the SVG**. You know the subject; use it. If the honest answer to *"what does the audience need to see happen that the still cannot show?"* needs something the still does not draw — what a block actually produces at each stage, the datum a decision sends one way or the other — draw it.

**Every rule lives in [`PRACTICES.md`](PRACTICES.md)** — where the animated version goes (F1–F4), what the deck needs to play it (C1–C6), how the motion must read (P1–P13), each with why and where it was learned. This file says only what the pass is and the steps it takes. **Load it before you author and honour every entry**; nothing checks them for you afterwards. The blind [`animation-critic`](${CLAUDE_PLUGIN_ROOT}/agents/animation-critic.md) holds the frames to the same file.

[`examples/`](examples/) holds an evolution of a real diagram (a vanilla GAN: its parts arriving, then a ball travelling each of the three training routes with a caption naming the case). Read it to see the practices in practice — **not** as a template: another diagram calls for another evolution.

## Inputs

| Input | Required? | Meaning |
|---|---|---|
| `svg_path` | yes | The finished static SVG — for an ASCII diagram, the render the critic approved. **Read-only:** the base is never edited. |
| `note` | yes | The diagram's whole note, verbatim. Its `animation:` section is the brief (grammar: [`editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md) → *ASCII diagrams*); `animation: loop` on the key line asks for a cycle. |
| `slide_title`, `slide_content_prose`, `speaker_notes`, `presentation_language` | recommended | What the slide says around the diagram — the point the animation serves, and the language of every word it adds. |
| `previous_defects` | on a revision | The critic's defects on the last attempt, verbatim. |

## Process

1. **Start the animated copy** (F1). Copy `<stem>.svg` to `<stem>.anim.svg` beside it and work only on that. **On a revision** (`previous_defects` given) the copy already exists: start from it and fix what the defects name.
2. **Read** [`PRACTICES.md`](PRACTICES.md), then the SVG, the note and the slide. Decide what the motion is for, then what moves.
3. **Evolve `<stem>.anim.svg`**, honouring every rule in [`PRACTICES.md`](PRACTICES.md). Add whatever the animation needs — narration or content (P8) — and nothing else (F4).
4. **Capture the frames** the critic will judge:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/animate-svg/scripts/capture_frames.py <stem>.anim.svg --out <images>/.critique/<stem>.anim/
   ```

   Beside the frames it writes `still.png` — the base drawn by the same browser, the critic's approved still (another rasterizer would show differences that are only the renderer's, such as italic it does not synthesize). `frames: failed` (no Chrome) is not your failure: the critic will judge the still only.
5. **Give the animated version its companions** — its still can differ from the base (content added, viewBox grown to make room): run [`ascii-to-svg`](../ascii-to-svg/SKILL.md)'s `validate_svg.py`, both `rasterize.py` PNGs (`<stem>.anim.png`, `.critique/<stem>.anim.png`) and `audit_aspect.py` on `<stem>.anim.svg`, exactly as its steps 6–9 do.
6. **Return** one line: `animated: <stem>.anim.svg · frames: <dir> (<n> frames) · png_deliverable: <stem>.anim.png · png_critique: <path> · aspect_audit: <ok|defect: …>` — or `failed: <reason>` after deleting the `.anim.*` files, which leaves the slide on its approved still (F1). For a hand-drawn diagram, point its image ref at the animated version (F2).

You do not critique your own animation, for the reason the critic exists: you would verify it against the CSS you remember writing, not against what plays.
