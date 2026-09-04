# Schema — `talksmith-bugs.md`

Specification for `talksmith-bugs.md`: the running defect log at the **root of the subject working directory** (sibling of `CLAUDE.md`, `config/`, `talks/`), where Talksmith records every inconsistency, malfunction, or self-contradiction it runs into while executing the workflow.

## Purpose

Talksmith is a long pipeline of specs, schemas, skills and subagents. When one of them misbehaves — a script errors, a file the spec promises isn't there, two documents say opposite things, a role returns an off-contract report — the run is supposed to **degrade and keep going**. Without a log, that recovery is also where the evidence dies: the presenter sees a slightly worse deck and nobody ever learns why.

This file is that evidence, and it exists to be **acted on**: an entry here is what someone later turns into an upstream issue and a fix. It is **about Talksmith, not about the talk**.

## The obligation

**Documenting a bug or inconsistency is mandatory, not discretionary.** Whenever Talksmith hits one, writing the entry is part of handling it — the step is not done until the entry exists. There is no "too small to log", no "I already worked around it", no "the presenter didn't notice". Silence is the failure mode this file was created to end.

Two rules that follow from it:

- **Log *and* handle.** The entry never replaces the fallback the step already specifies, never blocks the workflow, never becomes a question to the presenter, and never turns a graceful degradation into a stop.
- **Write it while you have the evidence.** Log at the moment of the defect, with the error text in hand — not reconstructed from memory at the end of the step.

## An entry must be reportable and fixable

The reader of an entry is someone who was not in the session and cannot ask you anything. Write for them. Every entry carries:

1. **All the relevant context** — the Talk, the step, the exact file/skill/spec section, what was being processed (slide id, block, source), what the inputs were. Enough that the situation can be reconstructed without this session's transcript.
2. **How to reproduce it, when you know** — the concrete sequence that triggers it, ideally down to a command someone can paste. If you *don't* know, say so explicitly (`repro: unknown — observed once, trigger not isolated`). Never guess a repro and present it as fact.
3. **Potential fixes you'd suggest** — where you can see one. Root cause if you have it, and what you would change to fix it.

**Suggestions must read as suggestions.** Anything under `suggested_fix:` is a hypothesis formed mid-run, not a verified diagnosis: phrase it that way (*"likely…"*, *"possibly…"*, *"worth checking whether…"*), keep it separate from the observed facts in `expected:` / `actual:`, and never state it as the cause. Offering none is fine — `suggested_fix: none — cause not understood` is an honest and useful entry; a confident wrong fix costs a maintainer more than an empty field.

**Never act on your own suggestion.** Talksmith does not edit the plugin's own specs, skills, or scripts to fix a defect it logged — it records, works around, and moves on. The fix happens upstream, by a human, in the plugin repo.

## What belongs here

- A skill or helper script that errors, crashes, or returns malformed output.
- A **contract violation**: a file, field, or path the spec/schema promises exists and doesn't; a writer that wrote outside its ownership; a step entered with its precondition unmet.
- An **inconsistency between specs**: the orchestrator, a schema, an agent spec, the template catalog or a style spec saying incompatible things — including when following one makes another impossible.
- A **subagent report that can't be used as specified** (missing required fields, verdict vocabulary the caller doesn't recognize, an empty result where the contract requires one).
- Output that is structurally wrong: a render that produced a broken deck, a rewrite that damaged a file, a schema-violating file Talksmith itself wrote.
- A **repeat pattern that points at the tool**, not the content: the same block unresolved every run, the same audit failing on every slide, an instruction in this plugin's own docs that cannot be followed as written.

## What does not belong here

- **Presenter feedback about the talk** — content, wording, ordering, tone. That is `Presenter feedback` in `draft.md` → [`config/feedback-backlog.md`](config/feedback-backlog.md).
- **Editorial preferences** worth making durable → [`config/learnings.md`](config/learnings.md) via Step 8.
- **Missing or ambiguous presenter input.** Ask, don't log.
- **Degradations a spec explicitly declares**: no image capability (`unavailable`), no browser for the PDF and `.pptx` exports, an empty corpus, an optional step skipped. These are designed outcomes — log them only when they *misbehave* (e.g. the declared fallback itself fails).
- Anything already surfaced and resolved inside the same step with no lasting effect on the deliverable.

## Loading semantics

**Lazy** — never in session context at start. Never read to answer a presenter question about the talk.

| Reader / writer | When | What for |
|---|---|---|
| Orchestrator | On any defect, in any step | **Sole writer.** Append a new entry, or bump `seen:` on a matching open one. |
| Orchestrator | Before appending | Read the existing entries once per session, to deduplicate. |
| Presenter / maintainer | Any time | Read it; file issues upstream. Free to edit or prune by hand. |

Roles (Librarian, Composer, Editor, Illustrators, Global-Librarian, critics) **never write this file**. They surface anomalies in their closing report — the orchestrator decides what is a defect and logs it. One writer keeps parallel subagents from racing on the same file.

## Entry format

Append-only, newest at the bottom. One entry per distinct defect:

```
- id: BUG-YYYYMMDD-NN
  date: YYYY-MM-DD
  talk: <talk-folder | ->
  step: <0-8 | the skill or role that was running>
  where: <smallest thing you can point at — file:line, skill name, spec section>
  what: <one line: the inconsistency or malfunction observed>
  context: <what was being processed and with what inputs — slide id, block, source
    file, mode, flags; anything needed to reconstruct the situation cold>
  expected: <what the spec, schema or contract says should happen — cite it>
  actual: <what happened — verbatim error text, trimmed to 5 lines max>
  repro: <concrete steps or a pasteable command | "unknown — <why not isolated>">
  impact: <blocked | degraded | cosmetic>
  workaround: <what you did to keep going, or "none">
  suggested_fix: <SUGGESTION, unverified — hypothesis + the change you'd make
    | "none — cause not understood">
  seen: <N>
  status: <open | fixed>
  plugin_version: <version from .claude-plugin/plugin.json, or "-" if unknown>
```

- **`id`** — `NN` is the sequence within that date, zero-padded: `BUG-20260825-01`.
- **`impact`** — `blocked` (the step could not complete its job), `degraded` (completed, worse output), `cosmetic` (no effect on the deliverable).
- **`expected` / `actual`** — observed facts only. The pair is what makes an entry actionable; an entry that can't state both is usually a vague hunch, so either sharpen it or don't log it.
- **`suggested_fix`** — always reads as a suggestion, never as a verdict. Keep it out of `what:` / `actual:`.
- **`status: fixed`** is set by a human, not by the workflow. Talksmith only ever appends or bumps.

### Example

```
- id: BUG-20260825-01
  date: 2026-08-25
  talk: agentes-2026
  step: 6 (Polish)
  where: skills/polish-ascii/polish_ascii.py — cleanup pass
  what: cleanup left the ASCII fence in place for a block whose SVG rendered fine
  context: block s3-2-1 in talks/agentes-2026/final.md; sidecar and SVG both on disk,
    stamp written; 21 other blocks in the same run were rewritten correctly
  expected: cleanup rewrites every rendered block's fence into an image reference
    (skills/polish-ascii/SKILL.md — Fence-rewrite rules)
  actual: fence untouched; no error raised, exit 0
  repro: unknown — the block is the only one in the deck whose fence is indented
    inside a list item, which may be the trigger
  impact: degraded — one slide shows raw ASCII in the rendered deck
  workaround: none applied; the block is reported unresolved and left as-is
  suggested_fix: SUGGESTION, unverified — the fence-matching regex looks anchored at
    column 0, so an indented fence would not match. Worth checking whether it should be
    indent-tolerant the way the feedback-strip matcher already is.
  seen: 1
  status: open
  plugin_version: 0.86.0
```

## Deduplication

Before appending, scan for an **open entry with the same `where` + same `what`**. If one exists, bump its `seen:` and update its `date:` instead of adding a row — and if the new occurrence adds evidence (a repro you couldn't isolate before, a second context that narrows the trigger), fold that into the existing entry. A recurring defect is one entry with `seen: 7`, not seven entries — the count is the signal that it is systemic.

## Presenter-facing behavior

Per the orchestrator's *Speak human, not internal*: **never narrate logging in running chat**. No error text, no skill names, no ids mid-step. At most, when a step closes with defects logged, one plain line — *"I hit a couple of rough edges in the tool while doing this; they're written down in `talksmith-bugs.md`."* Nothing at all when the log stayed empty.

## Canonical empty form

```markdown
# Talksmith bugs

> Inconsistencies and malfunctions **Talksmith itself** hit while running this working
> directory's workflow — not feedback about the talk. Written by Talksmith, append-only;
> safe to edit or prune by hand. Every entry carries context, a repro (or an explicit
> "unknown"), and — where offered — a **suggested** fix: a hypothesis from the session,
> never a verified diagnosis. Format: [`${CLAUDE_PLUGIN_ROOT}/schemas/talksmith-bugs.md`](${CLAUDE_PLUGIN_ROOT}/schemas/talksmith-bugs.md).
> Worth reporting upstream: https://github.com/veigap/talksmith/issues

## Entries

<!-- Talksmith appends entries below this line, newest at the bottom. -->
```
