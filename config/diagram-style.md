# Diagram style

Standing rules the [`talksmith:ascii-to-svg`](${CLAUDE_PLUGIN_ROOT}/skills/ascii-to-svg/SKILL.md) skill applies to every SVG it renders. Master-owned (mirrored to forks via [`talksmith:upgrade`](${CLAUDE_PLUGIN_ROOT}/skills/upgrade/SKILL.md)). The presenter can extend this file at any time — new bullets take effect on the next render.

Keep this file short. One rule per bullet, in plain language. If a rule is genuinely complex, explain it inline; otherwise let the rule speak for itself.

---

- **Flat style only.** Diagrams must not use 3D effects, perspective, drop shadows, isometric projections, or any depth illusion. Two-dimensional vector shapes only — flat fills and outlines.

- **Light mode only.** Text and outlines are dark on light, never light on dark. Do not produce inverted / dark-themed variants.

- **Background must be white.** The SVG background is pure white (`#ffffff`) — not light gray, not off-white, not transparent. Panel fills inside the diagram may be tinted, but the canvas itself is always solid white.

- **Palette discipline — neutral by default, deck-palette accents only.** Default element fills are light-grey or white; default text is `#3B3535`; the focal element (one per diagram) is accented with `#DA1B2E`. Per-element categorical color — a different tint per signal, per pipeline stage, per actor, per state — is reserved for diagrams where the categorical distinction is the *point* (e.g. a legend-driven comparison), and even then accent colors must be drawn from the deck's existing palette in [`pptx-prompt.md`](pptx-prompt.md) §2 (text inks + fills), never arbitrary pastels. Categorical pastels clash with the deck's tightly restrained palette and read as out-of-system; a single red accent + grey neutrals is the in-system idiom and is almost always sufficient.
