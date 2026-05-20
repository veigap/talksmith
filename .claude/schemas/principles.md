# Schema — `config/principles.md`

Specification for [`config/principles.md`](../../config/principles.md): Talksmith's design defaults (Mayer / Tufte / Reynolds / Duarte house rules) used when performing the Composer role to critique a draft.

## Purpose

Encodes the methodology and evidence-based guidance Talksmith uses to evaluate slide content. The content is a mix of:

1. **Talksmith opinions** — encoded methodology and house defaults.
2. **Evidence-based guidance** — drawn from established research and well-known practitioners (citations live at the bottom of the file).

## Loading semantics

**Lazy-loaded** — never in session context at start.

| Reader | Read when | What for |
|---|---|---|
| Composer role | Every drafting milestone in Step 4 (after thesis, after agenda, after each section in Mode A; after the full draft in Modes B/C) | Apply each principle as a soft rule when producing the punch-list of critiques. Cite by name in every punch-list item that invokes one: `(principles.md: <principle-name>)`. |

No other role and no orchestrator step loads this file. **No writer** — there is no automated promotion path into `principles.md` (unlike `learnings.md`); maintain it by hand.

## How to interpret the principles

- **Each principle is a default, not a rule.** The presenter can override any of them per slide or per talk.
- **Push back when a principle is broken without a stated reason.** If the presenter has already justified the break in a `Presenter feedback` bullet (e.g. "yes I know this slide is dense — it's a reference slide"), do **not** re-flag it. The composer's `Don't re-litigate closed feedback` rule applies.
- **Principles are weaker than learnings.** When `config/learnings.md` has a promoted entry whose "Where it applies" surface overlaps a principle, the learning wins. Cite the learning, not the principle.

## Maintenance

Principles change rarely. To add or modify: edit `config/principles.md` directly. There is no automated path. Persistent presenter feedback that warrants a new default is captured via the `feedback-backlog.md` → `learnings.md` promotion pipeline, not as a principles edit.
