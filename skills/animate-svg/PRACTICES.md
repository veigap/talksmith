# Animation rules and practices

The practices every animated diagram is written to. [`animate-svg`](SKILL.md) **loads this file before writing a single keyframe and honours every entry**; nothing checks them mechanically afterwards. The blind [`animation-critic`](${CLAUDE_PLUGIN_ROOT}/agents/animation-critic.md) reads it too and holds the frames to it, citing an entry by its number (`[C3]`, `[P5]`) — what pixels can show, it judges; the rest rests on the author.

Three groups, by what they protect:

- **The files (F1–F4)** — where the animated version lives and what it may touch, so the approved still always survives.
- **The playback contract (C1–C6)** — what the deck needs to play, stop and replay an animation, in every browser. Break one and the deck misbehaves (an animation that never stops, one back cannot replay, one Safari draws wrong) however good the motion is.
- **The craft (P1–P13)** — how the motion itself reads. The drawing rules (A1–A12) are the [`diagram-critic`](${CLAUDE_PLUGIN_ROOT}/agents/diagram-critic.md)'s, for the still; a practice that is the animation side of one says so.

Neither is a catalogue of animation kinds: they say how anything that moves must behave, never what should move — that is the author's call, from the diagram and its subject. Each entry records where it was learned, so none is relaxed without knowing what it prevents. **When a new defect earns a practice, add it here** — what to do, why, and where it was seen.

---

## The files

- **F1 · Never touch the base; the animation is a sibling.** Copy `<stem>.svg` to `<stem>.anim.svg` beside it and work only on the copy; its companions are `<stem>.anim.png` (its own still) and `.critique/<stem>.anim.png`. *Why:* the approved still survives whatever happens — an animation that does not work costs nothing (delete the `.anim.*` files and the slide shows the still), a re-animation always starts from what was approved, and the critic always has the approved still to compare against.
- **F2 · The slide points at the animated version.** For an ASCII diagram `polish-ascii cleanup` writes `images/<stem>.anim.svg` whenever it exists; for a hand-drawn one, point its image ref at `images/<stem>.anim.png` yourself. *Why:* otherwise the deck shows the still and the animation was made for nothing.
- **F3 · The animated version is not a render.** Drop any `talksmith-ascii-sha256` stamp the copy carried. *Why:* that stamp is how Polish recognises a render for idempotency and reuse; on the animated copy it would make reuse take an animation for a base drawing.
- **F4 · Change only what the animation needs.** The approved drawing stays as it is; what you add is either narration or content (P8). *Why:* the still was approved; anything else you change re-opens a review nobody asked for. *Seen in:* `gan-discriminador-cara`, which recoloured two of the approved still's dots.

## The playback contract

The deck plays an animation **once**, restarting it each time its slide is entered, and a back press replays it once it has finished or run past 5 s ([`html_style.py`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/scripts/html_style.py) → `_DIAGRAM_REPLAY`); it never plays it in the PDF, the `.pptx`, the print view or with animations off ([`theme.css`](${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/templates/html/theme.css) → *Animated diagrams*) — there, and in every PNG, the diagram is its still. Opened on its own, the `.svg` plays once on load. These rules are what make all of that work:

- **C1 · One scoped stylesheet.** One `<style>` marked `/* talksmith-animation */`, right after `<title>`/`<desc>`; the root carries `class="ts-anim-<stem>"`, every selector starts with `.ts-anim-<stem>` and every `@keyframes` name with `ts-anim-<stem>-`. *Why:* the deck inlines every SVG into one page, so an unscoped rule or keyframe reaches — or is overwritten by — another diagram's.
- **C2 · CSS animations only.** No SMIL (`<animate*>`, `<set>`), no `<script>`, no `on*` handlers. *Why:* the deck stops animations off the present slide, in print and with animations off, and back replays them, through `animation: none` and `getAnimations()` — which reach CSS animations only; SMIL would keep running on hidden slides and in the PDF.
- **C3 · Play once, unless the note says `animation: loop`.** No `infinite`, no iteration count above 1, otherwise. *Why:* a diagram that cycles forever competes with the presenter.
- **C4 · Hold the end.** Every animated rule says `both` or `forwards`. *Why:* a play-once animation that has finished is otherwise no longer "in effect", drops out of `getAnimations()`, and back-to-replay finds nothing on exactly the slide where it is done.
- **C5 · Respect reduced motion.** A `@media (prefers-reduced-motion: reduce)` rule turns the animation off. *Why:* viewers who ask for no motion get the still.
- **C6 · No motion paths — move with `translate`.** No `offset-path` / `offset-distance`. Anything that travels moves by `transform: translate(Xpx, Ypx)` keyframes through its route's points, in the diagram's own coordinates (no transform above the moving element, which is drawn around its origin; in SVG a CSS `px` is one viewBox unit). A straight run is two keyframes at its ends, stops placed by distance so the speed stays even; a curve is sampled into enough points to read as one, computed along the very path its drawn connector uses. *Why:* Chrome places a CSS motion path exactly, but **Safari misplaces it on SVG elements** — the same ball rides its arrow in one browser and floats off it in the other. *Seen in:* the GAN talk's "El ciclo completo" and "Discriminador como red neuronal", in Safari.

## The practices

### Motion

- **P1 · Travel along lines the audience can see.** A moving token follows a drawn connector from end to end; it never crosses blank space, a panel or a label to get somewhere no line goes. If the motion needs a route the still does not draw, draw the connector as content first — or don't travel: fade the thing in where it arrives. *Seen in:* `gan-ciclo-lote`, whose error balls cut across the panel to boxes no arrow reaches.
- **P2 · A moving thing never covers a label.** Route it, size it or time it to clear every label it passes. A token that goes *through* a box rides **under** it (drawn before it), so the box swallows it while "processing" and it comes out the other side. *Seen in:* `react-bifurcacion` (the ring ran into "observación"), `difusion` (the noise token covered "predictor"), the shipped GAN example (a moving "falsa" label hit "veredictos sobre generadas").

### Order

- **P3 · Nothing arrives before what produces it.** A label, a caption, a count or a result comes in with the element it belongs to, or after it — never before. *Seen in:* `clip-matriz` (axis captions over an empty canvas), `unet` ("+ 256 canales" before its skip landed), `stylegan` (block frames floating before their blocks).
- **P4 · An arrow arrives with what it carries.** A connector draws itself as the thing travels along it, and its arrowhead appears when the thing gets there — never a finished arrow pointing at something not there yet. *Seen in:* `unet` (the skip arrow touched the decoder while its dot was half-way), `stylegan` (an arrow to the next block pointing at nothing for seconds).
- **P5 · One step at a time.** Each step the brief names is its own visible moment; two never land together, and the input of a step settles before the step's machinery appears. *Seen in:* `gan-discriminador-cara` (the values reached x₁…x₄ in the instant the weights and σ appeared).
- **P6 · Say what is on screen now.** A caption describes what the audience can see at that moment — never announces something that has not landed. *Seen in:* `sam2-memoria` (the caption said the mask took the cone a frame before the wrong mask appeared).

### What stays

- **P7 · Containers stay; their contents animate.** A box, panel or frame that holds changing content stays drawn the whole time, empty if need be; only what is inside comes and goes. An arrow always starts and ends at something. *Seen in:* `sam2-memoria` (the "frame t" / "máscara t" boxes vanished, leaving arrows into blank space).
- **P8 · The still is the complete diagram.** Everything you add is one of two kinds, and the difference matters. **Narration** — anything that only exists to tell the motion: tokens, captions, highlights, counters — starts and ends at `opacity="0"`, so the last frame is the still with nothing half-faded. **Content** — something that belongs to the diagram: the image a block produces, a value it outputs — is visible at rest, part of the animated version's still, and as correct as the rest of the diagram; the critic judges it in the still too. *(C4 holds the end; this says what the end must look like.)* *Seen in:* `reflexion-lazo`, whose ending once left the counter and memory chips washed out.

### Legibility

- **P9 · One caption at a time, in one place.** Captions share a reserved band; the outgoing one is fully gone before the next starts fading in. *Seen in:* `reflexion-lazo` (two captions cross-fading read as gibberish).
- **P10 · Narration is readable at slide size.** Nothing the animation adds is smaller or paler than the diagram's own secondary text. *Seen in:* `pipeline-sd` (the "en cámara rápida" note was the smallest text in any frame).
- **P11 · One colour, one meaning, for the whole run.** An element keeps its colour from its first frame to the still, and no colour changes meaning as the animation runs. *(The animation side of A10.)* *Seen in:* `gan-discriminador-cara` (the verdict point turned from red to blue, the colour of a −1 weight).
- **P12 · Pictograms survive occlusion.** When one drawn object passes in front of another, enough of both stays visible that each reads as itself — and a marker on top (a click, a pointer) does not merge with them into a third figure. *(The animation side of A6.)* *Seen in:* `sam2-memoria` (ball over cone plus a click marker read as a snowman).

### Pacing

- **P13 · A pace the eye can follow.** Roughly a second per settled step; a journey slow enough to follow, fast enough not to drag; the whole run well under half a minute. A loop the brief says runs ~50 times is shown by a few passes, the later ones faster, with a counter — never by fifty. Each key moment is a **settled** state for a beat, which is also what the critic's frames are sampled on. *Seen in:* `pipeline-sd`, whose "cámara rápida" laps and step counter carried a 50-pass loop in four.
