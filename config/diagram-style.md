# Diagram style

Standing rules the [`talksmith:ascii-to-svg`](${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/SKILL.md) skill applies to every SVG it renders. Ships with the plugin and updates via `/plugin update talksmith`. The presenter can extend this file at any time — new bullets take effect on the next render.

Keep this file short. One rule per bullet, in plain language. If a rule is genuinely complex, explain it inline; otherwise let the rule speak for itself.

---

- **Flat style only.** Diagrams must not use 3D effects, perspective, drop shadows, isometric projections, or any depth illusion. Two-dimensional vector shapes only — flat fills and outlines.

- **Light mode only.** Text and outlines are dark on light, never light on dark. Do not produce inverted / dark-themed variants.

- **Background must be white.** The SVG background is pure white (`#ffffff`) — not light gray, not off-white, not transparent. Panel fills inside the diagram may be tinted, but the canvas itself is always solid white.

- **Draw arrows as paths, never as glyphs.** Arrowheads are `<path>` / `<marker>` geometry. The arrow *characters* (`←` `→` `↑` `↓` `⇒` U+2190-21FF) rasterize as **tofu boxes** — they are absent from the fonts cairosvg resolves to. Every ASCII diagram is full of arrows, and the ASCII source uses those very characters, so copying them into a `<text>` element is the single easiest way to ship a broken diagram. The SVG XML looks perfect; only the pixels show the tofu.

- **Fonts: `'DejaVu Sans Mono', monospace` for code, `Helvetica, Arial, sans-serif` for everything else.** Name the family explicitly — cairosvg's font resolution is not a browser's, and a family that exists on every macOS machine is not therefore available to the renderer. **`Menlo` in particular is a trap:** it resolves, so nothing errors, but its hyphen (U+002D) draws at near-full-em width, so `a-b` renders as `a–b` and a YAML `---` fuses into a single rule. On a panel whose whole purpose is to show a literal file, that is a quiet wrong answer of the worst kind — the source string is correct and the picture lies. Accented Latin, `—`, curly quotes and `·` are all safe.

- **Palette discipline — neutral by default, deck-palette accents only.** Default element fills are light-grey or white; default text is `#3B3535`; the focal element (one per diagram) is accented with `#DA1B2E`. Per-element categorical color — a different tint per signal, per pipeline stage, per actor, per state — is reserved for diagrams where the categorical distinction is the *point* (e.g. a legend-driven comparison), and even then accent colors must be drawn from the deck's existing palette in [`pptx-prompt.md`](${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md) §2 (text inks + fills), never arbitrary pastels. Categorical pastels clash with the deck's tightly restrained palette and read as out-of-system; a single red accent + grey neutrals is the in-system idiom and is almost always sufficient.

- **No Unicode symbol glyphs in text nodes — not just arrows.** The arrows rule above covers `←→↑↓⇒`; the same tofu trap applies to check/cross/bullet/star symbols (`✓ ✔ ✗ ✘ ☑ ★ ● •` and similar). cairosvg's fonts don't carry them, so they rasterize as empty boxes while the XML looks perfect. Draw a check or cross as `<path>` geometry, or use a plain word (`sí` / `no`, `ok`). Accented Latin, `—`, curly quotes and `·` remain safe.

- **Arrowhead markers: `markerUnits="userSpaceOnUse"`.** The SVG default (`strokeWidth`) scales the arrowhead with the line's thickness, so a thicker line grows an oversized head that overshoots — and can visibly punch into — the destination box. `userSpaceOnUse` keeps the head a fixed size regardless of stroke width.

- **Arrow shafts terminate on the destination edge.** The shaft should meet the target box's border, with `refX` / marker geometry handling the head inset. A shaft that stops short of the edge leaves a visible gap between arrow and box; one that runs past pokes through it.

- **No inline `<tspan>` runs inside centered text.** Inside a `<text text-anchor="middle">`, mixed inline `<tspan>`s can be *overprinted* by cairosvg — it stacks the runs at the same x instead of advancing. Use separate positioned `<text>` nodes for the parts, or make the whole `<text>` element a single style (e.g. all bold, or all monospace). (Left-anchored text advances normally; the trap is specific to centered text.)

- **Preserve leading whitespace with `xml:space="preserve"`.** Code-like labels, indented lists, and YAML continuations rely on their leading spaces; without `xml:space="preserve"` on the `<text>` element, the renderer collapses the indentation and the alignment (and sometimes the meaning) is lost.

- **No decorative XML comments.** Never emit comments as ASCII decoration (`<!-- ---- -->`, `<!-- ==== -->`). A `--` sequence is illegal *inside* an XML comment, so the whole SVG is rejected as malformed (cairosvg and `validate_svg.py` both fail it). Keep any comment free of `--` runs; better, don't emit decorative comments at all.
