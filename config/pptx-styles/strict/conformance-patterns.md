# Strict conformance patterns — declarative data

**Strict-only.** This file holds the strict template's LAYOUT-CONFORMANCE rules as
**declarative data** the renderer applies at GENERATE and the FEEDBACK critique checks
at review — rather than prose scattered through [`pptx-prompt.md`](pptx-prompt.md). The
`CONFORMANCE-*` entries in [`../slide-design.md`](../slide-design.md) name the
intent; the measurable rules live here, so they can be **grown from real edits**: the
[`talksmith:pptx-learn`](${CLAUDE_PLUGIN_ROOT}/skills/pptx-learn/SKILL.md) skill mines
patterns from decks a presenter hand-corrected and, after human curation, appends them
here. Free-form and preview never read this file.

## How it's used

- **At GENERATE (strict):** the renderer treats each `bundled` / `promoted` pattern as
  a target — position, size, fill, or font rule to emit. Ambiguous rules (`interpret:`
  present) are applied with LLM judgement rather than as a hard constant.
- **At FEEDBACK (strict):** the `CONFORMANCE-*` walk checks the rendered slide against
  these patterns; a deviation is a finding.
- **Learning:** `pptx-learn` proposes new patterns into the *project* file
  `config/strict-learnings.md`; a human promotes chosen ones **into this file** (status
  `promoted`). Nothing lands here automatically.

## Entry schema

```
- id:         section-pill-position        # stable kebab id
  applies-to: content-slide                # cover | agenda | section-divider | content-slide | any
  rule:       "Section pill sits at the top-left; ALL CAPS section name."
  why:        "Anchors the reader in the section; a fixed top-left slot keeps navigation consistent across the deck."
  measure:    { off_x_emu: 457200, off_y_emu: 274638, fill: "F9D2D6" }   # optional, machine-checkable
  interpret:  false                        # true → apply with LLM judgement, not as a hard constant
  status:     bundled                      # bundled | promoted | candidate
  evidence:   "strict template invariant"
  since:      2026-07-09
```

`measure` fields are EMU (914400 = 1 inch) or hex fills / point sizes; omit for a
purely qualitative rule.

**`why` is the load-bearing field — the design *decision*, not the measurement.**
`learn_patterns.py` supplies the measured delta (`measure`) and the recurrence
(`evidence`); the **LLM analyst** supplies the `why` and the judgement that the pattern
*generalizes* (a template rule) rather than being a content-specific one-off. A pattern
without a defensible `why` is not promotable — the number alone is not a rule.

---

## Bundled patterns (the strict template invariants)

```
- id: section-pill-present
  applies-to: content-slide
  rule: "Every non-cover, non-agenda slide carries the section pill (rounded-rect, ALL-CAPS section name) at top-left."
  measure: { fill: "F9D2D6" }
  interpret: false
  status: bundled
  evidence: "strict §6 / pptx-prompt.md §20 CONFORMANCE-04"
  since: 2026-07-09

- id: section-divider-no-body
  applies-to: section-divider
  rule: "A numbered H1 renders as a divider slide — large title, no body content."
  interpret: false
  status: bundled
  evidence: "strict CONFORMANCE-02"
  since: 2026-07-09

- id: corner-radius
  applies-to: any
  rule: "Rounded-rectangle shapes use a 5760-EMU corner radius."
  measure: { corner_radius_emu: 5760 }
  interpret: false
  status: bundled
  evidence: "strict §15 rule 7"
  since: 2026-07-09

- id: callout-fills
  applies-to: content-slide
  rule: "Callout round-rects are pink #F7BBC1 (caution/emphasis) or blue #B8E6F5 (info); no other callout fill."
  measure: { fill_pink: "F7BBC1", fill_blue: "B8E6F5" }
  interpret: true
  status: bundled
  evidence: "strict §8"
  since: 2026-07-09

- id: white-background
  applies-to: any
  rule: "Every slide carries a pure-white background solid fill."
  measure: { bg_fill: "FFFFFF" }
  interpret: false
  status: bundled
  evidence: "strict §1"
  since: 2026-07-09

- id: branded-icons
  applies-to: content-slide
  rule: "Iconographic marks are #DA1B2E line-art icons from the §17 catalog; one consistent style; no system emoji."
  measure: { icon_fill: "DA1B2E" }
  interpret: true
  status: bundled
  evidence: "strict §17 / CONFORMANCE-05"
  since: 2026-07-09
```

## Promoted patterns (learned from real edits, human-curated)

*(none yet — `pptx-learn` proposes candidates into `config/strict-learnings.md`; promote them here.)*
