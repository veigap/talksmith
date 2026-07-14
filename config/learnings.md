# Learnings

> Format spec, loading semantics, and promotion rules live in [`${CLAUDE_PLUGIN_ROOT}/schemas/learnings.md`](${CLAUDE_PLUGIN_ROOT}/schemas/learnings.md).

## Entries

<!-- Editor appends promoted learnings below this line when the orchestrator dispatches a Step 8 Promote. -->

### Renderer applies the layout the spec selects, not the layout that ships without violations

**Rule:** The renderer's job is to apply the layout the §15.5 emit-rules + §15.6.1 discriminator select per slide, not to ship whatever rendering happens not to violate §19.6. Satisfying anti-patterns by *deletion* (stripping an emoji, dropping a label, picking a plainer layout) is a render failure when the positive obligation calls for *substitution* (§17.7 catalog icon swap) or for a richer layout (§7.4 card-row, §7.5 icon-bullet list, §11 card-grid). The §15.6 pre-emit audit and the §19.5 layout-fit audit are the enforcement mechanisms; §19.6 anti-pattern compliance alone is necessary but not sufficient.

**Why:** A renderer that strips emojis instead of swapping them to §17 catalog icons, or picks §10 plain bullets when §15.5's discriminator selects §7.5, ships a §19.6-clean deck that still violates the substantive spec. The defect is invisible to the §19.6 anti-pattern scan and surfaces only at visual review — by which point the iteration budget is consumed on cosmetic re-renders that don't address the root cause (a renderer matching on surface signals rather than driving from the discriminator).

**Where it applies:** Every PPTX render (Step 7). Applies to all future Talks in this working directory, not just to the originating incident. Especially load-bearing for slides whose source has 3+ labeled bullets, ≥4 images, ≥4 `### Subhead` groups, fenced code blocks, or emoji prefixes on bullets.

**Evidence:** senales-1d-biomedicina:2026-05-25 — first render shipped §10 plain bullets on two slides where the §15.5 discriminator mandated §7.5 (longest body > 80 chars), stripped emojis on multiple bullets where §17.7 mandated catalog-icon swap, and emitted inconsistent bullet shapes (one code path used `<a:buChar>`, another used a literal `•` glyph in text runs). Root-caused to surface-match rendering rather than discriminator-driven layout selection.

**Added:** 2026-05-25
