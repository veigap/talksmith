---
name: talksmith:animate-svg
description: Evolve one finished, static diagram SVG into its animated version, from the note's `animation:` brief and the slide's context. The model reads the diagram and its subject and authors the motion itself; a checker enforces only the deck's playback contract and captures frames for the blind critic. Dispatched by the diagram-illustrator after a diagram's static render is approved (Step 6), or directly on a hand-authored diagram SVG that carries a note.
---

# talksmith:animate-svg — evolve a finished diagram into its animation

A static diagram shows the parts. Its animation shows **what the slide is about happening** — and what that is depends entirely on the diagram and its subject. So there is no catalogue of animation kinds here, and no parameters to fill: you read the diagram, the note's `animation:` brief and the slide, and you **evolve the SVG**. You know the subject; use it. If the honest answer to *"what does the audience need to see happen that the still cannot show?"* needs something the still does not draw — what a block actually produces at each stage, the datum a decision sends one way or the other — draw it.

The only fixed part is the deck's **playback contract** below: the few properties every animation must have for the deck to play it, stop it and replay it. [`check_animation.py`](check_animation.py) enforces that and nothing else — it does not judge the animation, and passing it says nothing about whether the animation makes the point. The blind [`diagram-critic`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-critic.md) judges that, from frames.

[`examples/`](examples/) holds an evolution of a real diagram (a vanilla GAN: its parts arriving, then a ball travelling each of the three training routes with a caption naming the case). Read it to see the contract in practice — **not** as a template: another diagram calls for another evolution.

## Inputs

| Input | Required? | Meaning |
|---|---|---|
| `svg_path` | yes | The finished static SVG — for an ASCII diagram, the render the critic approved. Edited in place. |
| `note` | yes | The diagram's whole note, verbatim. Its `animation:` section is the brief (grammar: [`editor.md`](${CLAUDE_PLUGIN_ROOT}/agents/editor.md) → *ASCII diagrams*); `animation: loop` on the key line asks for a cycle. |
| `slide_title`, `slide_content_prose`, `speaker_notes`, `presentation_language` | recommended | What the slide says around the diagram — the point the animation serves, and the language of every word it adds. |
| `ascii_file` | when there is one | The `.ascii` sidecar — passed to the checker so it reads the note's mode from the same bytes the render did. |
| `previous_defects` | on a revision | The critic's defects on the last attempt, verbatim. |

## Process

1. **Keep the approved still.** Copy `svg_path` to `<svg parent>/.critique/<basename>.static.svg` before touching it, and rasterize that copy to `.critique/<basename>.static.png` (`rasterize.py … --width 1600`) — the critic's reference for what the animation changed. If you return `failed`, copy it back: an animation that did not work never costs the slide its approved diagram. **On a revision** (`previous_defects` given) that copy already exists and is still the approved still — leave it alone, start from your previous animated SVG, and fix what the defects name.
2. **Read** the SVG, the note and the slide. Decide what the motion is for, then what moves.
3. **Evolve the SVG in place.** Add one `<style>` right after `<title>`/`<desc>`, add `class="ts-anim-<basename>"` to the root, and add whatever elements the animation needs. Two kinds of addition, and the difference matters:
   - **narration** — anything that only exists to tell the motion (a token, a caption, a highlight) — starts at `opacity="0"` and appears only through the animation, so the still never shows it;
   - **content** — something that belongs to the diagram (an image a block produces, a value it outputs) — is visible at rest, because it is now part of the still. It must be as correct as the rest of the diagram; the critic will judge it in the still too.

   Leave the approved drawing alone beyond what the animation needs.
4. **Check the contract and capture frames:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/animate-svg/check_animation.py <svg_path> --ascii <ascii_file> \
       --frames <svg parent>/.critique/<basename>/        # no sidecar: [--loop]
   ```

   A defect here is mechanical and yours to fix now — fix it and run again (twice at most) rather than handing it to the critic. `frames: failed` (no Chrome) is not a defect: the critic will judge the still only.
5. **Refresh the still's companions** — the still can have changed (content added, viewBox grown to make room): run [`ascii-to-svg`](../ascii-to-svg/SKILL.md)'s `validate_svg.py`, both `rasterize.py` PNGs and `audit_aspect.py` exactly as its steps 6–9 do.
6. **Return** one line: `animated: <svg_path> · animation: ok[, loop] · frames: <dir> (<n> frames) · png_deliverable: <path> · png_critique: <path> · aspect_audit: <ok|defect: …>` — or `failed: <reason>` with the still restored.

You do not critique your own animation, for the reason the critic exists: you would verify it against the CSS you remember writing, not against what plays.

## The playback contract

What the deck needs, and why — this is the whole of what is fixed:

| | Rule | Why |
|---|---|---|
| 1 | One `<style>` marked `/* talksmith-animation */`; every selector starts with `.ts-anim-<basename>`, every `@keyframes` name with `ts-anim-<basename>-` | The deck inlines every SVG into one page, so an unscoped rule or keyframe reaches — or is overwritten by — another diagram's. |
| 2 | CSS animations only — no SMIL (`<animate*>`, `<set>`), no `<script>`, no `on*` handlers | The deck stops animations off the present slide, in print and with animations off, and back replays them, through `animation: none` and `getAnimations()` — which reach CSS animations only. |
| 3 | Plays once unless the note says `animation: loop` | A diagram that cycles forever competes with the presenter. |
| 4 | Every animated rule holds its end (`both` or `forwards`) | A finished animation that does not hold drops out of `getAnimations()`, and back-to-replay finds nothing on exactly the slide where it is done. |
| 5 | A `prefers-reduced-motion` rule turns it off | Viewers who ask for no motion get the still. |
| 6 | **The still is the complete diagram** — not checked by the script; the critic judges it | cairosvg ignores `@keyframes`, and the deck's off-switch removes every animation, so the PDF, the `.pptx`, the PNGs and a deck with animations off all show the elements' own attributes. |

**Moving something along a path:** CSS `offset-path: path("…")` + an animated `offset-distance`, with the path in the diagram's own coordinates (no transform above the moving element) and the moving element drawn around the origin. SMIL `<animateMotion>` would break rule 2.

## How it plays in the deck

Once only, restarting each time the slide is entered; a back press replays it once it has finished or run past 5 s ([`html_style.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/html_style.py) → `_DIAGRAM_REPLAY`); never in the PDF, the `.pptx`, the print view or with animations off ([`theme.css`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/templates/html/theme.css) → *Animated diagrams*). Opened on its own, the `.svg` plays once on load.
