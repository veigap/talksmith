# Diagram style

Standing rules the [`talksmith:ascii-to-svg`](../.claude/skills/ascii-to-svg/SKILL.md) skill applies to every SVG it renders. Master-owned (mirrored to forks via [`talksmith:upgrade`](../.claude/skills/upgrade/SKILL.md)). The presenter can extend this file at any time — new bullets take effect on the next render.

Keep this file short. One rule per bullet, in plain language. If a rule is genuinely complex, explain it inline; otherwise let the rule speak for itself.

---

- **Flat style only.** Diagrams must not use 3D effects, perspective, drop shadows, isometric projections, or any depth illusion. Two-dimensional vector shapes only — flat fills and outlines.

- **Light mode only.** Text and outlines are dark on light, never light on dark. Do not produce inverted / dark-themed variants.

- **Background must be white.** The SVG background is pure white (`#ffffff`) — not light gray, not off-white, not transparent. Panel fills inside the diagram may be tinted, but the canvas itself is always solid white.
