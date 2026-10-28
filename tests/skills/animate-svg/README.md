# animate-svg — reference cases

Twelve real diagrams from three talks in `talksmith-ing` (*Redes generativas antagónicas*, *Agentes y multiagentes*, *Segmentación y Stable Diffusion*), each one an input to [`talksmith:animate-svg`](../../../skills/animate-svg/SKILL.md) as the diagram-illustrator would hand it over:

| File | What it is |
|---|---|
| `base.svg` | The approved static diagram — any earlier animation stripped. |
| `note.txt` | Its note, verbatim; the `animation:` section is the brief. |
| `context.json` | The slide around it: title, content prose, speaker notes, language. |
| `source.ascii` | The `.ascii` sidecar (ASCII + note), for every diagram drawn from ASCII. |

**Two starting points.** The first seven carry a `base.svg`: the skill runs on it directly. The last five, from *Segmentación y Stable Diffusion*, carry only `source.ascii` — that talk animated them as GIFs, so there is no static SVG to start from: render `source.ascii` with [`talksmith:ascii-to-svg`](../../../skills/ascii-to-svg/SKILL.md) first, then animate the result. Their notes had no `animation:` section, so the brief in each was written for this fixture, from the slide.

**Run a case:** copy `base.svg` to `output/<case>.svg` (the skill edits in place; `output/` is gitignored) and invoke the skill with that path, `note.txt`, `source.ascii` when there is one, and the fields of `context.json`. Then dispatch the blind `diagram-critic` on the frames the skill reports, as the illustrator does (8f). `test_check_animation.py` checks every `output/*.svg` it finds against the playback contract.

There is no expected output to diff against — an animation is authored, and two good ones can differ. Judge a result the way the critic does: does it show what the brief asks, and does it make the slide's point better than the still?

| Case | The slide | Why it is here |
|---|---|---|
| `gan-vanilla` | The architecture of a vanilla GAN | Fixed parts, but three different journeys through them — D on a real sample, D on a fake, G — and the slide's point is the difference between them. |
| `stylegan` | StyleGAN: mapping network, synthesis network | The blocks from 4×4 to 1024×1024 carry empty frames: what the image looks like at each resolution is the thing to see, and the still does not draw it. |
| `gan-ciclo-lote` | One training batch, step by step | Dense: numbers, verdicts, errors and two update paths in one picture — the animation has to order a lot without drowning it. |
| `gan-discriminador-cara` | A one-neuron discriminator on a 2×2 face | A calculation: pixels become inputs, weights, a sum, a sigmoid, a probability. |
| `react-bifurcacion` | ReAct: thinking is an action too | One decision, two branches with different consequences for the context. |
| `reflexion-lazo` | Reflexion: try, evaluate, reflect | A loop that repeats until it passes, with an exit. |
| `arbol-decision` | How to choose the architecture | A decision tree: a question at each level, and each answer ends somewhere else. |
| `unet` | U-Net: the U and its shortcuts | The image shrinks and grows again; the skips carry detail across at the right moment. |
| `sam2-memoria` | SAM 2: memory for video | A loop across time: each frame's mask is stored and conditions the next one. |
| `difusion` | Diffusion: adding and removing noise | Two directions over the same chain, and a condition that changes where the reverse lands. |
| `pipeline-sd` | The full inference pipeline | A loop that runs ~50 times; what changes on each pass is the point, and the still cannot show it. |
| `clip-matriz` | CLIP: the text ↔ image bridge | A matrix filled cell by cell, then trained: the diagonal against the rest. |

The reference evolution of one of these (the vanilla GAN) ships with the skill: [`skills/animate-svg/examples/gan-paths.svg`](../../../skills/animate-svg/examples/gan-paths.svg).
