# Schema — `talks/<Talk>/memory.md`

Specification for `talks/<Talk>/memory.md`: the per-Talk progress log and live restore point. Each Talk has exactly one. Captures **both** finished steps (the audit trail) **and** in-flight state (what's being asked right now, what the agent is waiting for, what status the current step is in) so that a resume picks up at the exact moment the previous session paused — not just at the last completed step.

## Purpose

Two things live in this file:

1. **Live state** — a small block of header lines that change as the step progresses (status, what the agent is currently awaiting from the presenter). The orchestrator parses these on resume.
2. **Append-only history** — one entry per Talksmith step, dated, recording asks/answers as they happen and the closing fields (decisions, inputs, files, open questions) once the step completes.

The orchestrator updates the live-state block directly (lightweight, in-place). The Editor role owns the immutable Talk briefing and the closing fields of each step entry.

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| Orchestrator (writer) | On every step transition and every presenter ask/answer | Maintain `**Current step:**` and `**Awaiting:**` header lines; append to the current step entry's `Asks log` as questions are asked / answered. Lightweight in-place edits. |
| Editor role (writer) | (a) Step 1 init: bootstrap from canonical empty form, write the briefing block, open the Step 1 entry. (b) Step closure (1–8): fill `What was decided` / `Key inputs` / `Files created/modified` / `Pending open questions` for the closing step; flip its `Status:` to `complete`. | Capture decisions in a stable, audit-friendly form. The Editor role never overwrites prior step entries — only the currently-open one. |
| Orchestrator (reader) | Step 0 on a Resume session; ad-hoc throughout | Parse `**Current step:**` + `**Awaiting:**` to know where to resume and whether a question was mid-air. Read prior step entries when context is needed. |

## Live-state block (header)

The top of the file holds the always-current state. Three lines, two of them dynamic:

```
**Current step:** <integer> — <Phase name> <status>
**Awaiting:** <YYYY-MM-DD HH:MM> — "<verbatim question or one-line context>"
**Topic:** <one-line topic from Step 1>
**Folder:** talks/<folder-name>/
**Started:** <YYYY-MM-DD>
```

- `**Current step:**` — single source of truth for the resume target. `<status>` is one of: `in_progress` (working), `awaiting_presenter` (question outstanding), `complete` (step done; ready to advance).
- `**Awaiting:**` — present **only** when `<status> = awaiting_presenter`. Holds the timestamp the question was asked and a verbatim or one-line gloss of what's expected. The orchestrator removes this line the moment the answer is received (and flips status back to `in_progress`).
- `**Topic:**`, `**Folder:**`, `**Started:**` — written once at Step 1 init, never edited.

**Resume contract.** On a Resume session, the orchestrator reads `Current step:` and, if status is `awaiting_presenter`, also `Awaiting:` — then re-emits the outstanding question to the presenter rather than blindly advancing.

## Talk briefing block

A `## Talk briefing` section immediately below the header holds the verbatim Step-1 free-text answer from the presenter. **Immutable** for the lifetime of the Talk — every subsequent step leaves it untouched. Canonical context for all role work throughout the session.

## Append-only history

Below the briefing, one entry per step. The entry header is written when the step **starts**; the entry body grows during the step (asks/answers appended in real time) and is finalized when the step **completes**.

Per-step entry shape:

```
## <YYYY-MM-DD> — Step <N> (<Phase name>)
- Status: <in_progress | awaiting_presenter | complete>
- Asks log:
  - <YYYY-MM-DD HH:MM> — "<verbatim question>" → <verbatim or one-line answer | pending>
  - <...>
- What was decided: <one or two lines>            ← filled at closure
- Key inputs: <presenter answers, files added>    ← filled at closure
- Files created/modified: <list>                  ← may grow during the step
- Pending open questions: <list or "none">        ← filled at closure
```

Rules:

- **The orchestrator owns `Status:` and `Asks log:`** — updates them in place as work happens. Every chat-prompt question the orchestrator emits gets a new `Asks log` row (one ask, one row). When the presenter answers, the orchestrator rewrites the row's trailing `pending` with the verbatim or one-line answer (never deletes the row). Then it flips `Status:` from `awaiting_presenter` back to `in_progress` and removes the `Awaiting:` header line.
- **The editor owns the closing fields** — `What was decided`, `Key inputs`, `Pending open questions`, and the final flip of `Status:` to `complete`. The editor may also append to `Files created/modified` whenever it writes during the step.
- **Old entries are immutable.** Once a step entry's `Status:` flips to `complete`, no writer (orchestrator or editor) touches that entry again. The next step opens a new entry below.
- **One open entry at a time.** If `Current step:` points to step N, the step-N entry is the only one with `Status: in_progress` or `awaiting_presenter`. All prior entries are `complete`.

## What counts as an "ask" worth logging

Log every presenter-facing question that's part of the workflow — the chat-prompt protocol's numbered-option asks and free-text prompts. Do **not** log conversational acknowledgments ("ready?", "OK to proceed?") or transient clarifications that the orchestrator resolves itself. The rule of thumb: if the question gates the next step (or the next significant action within the step), it goes in the log.

## Canonical empty form

The Editor role bootstraps `talks/<Talk>/memory.md` from this form during its Step 1 init pass. Write the verbatim Step-1 briefing text under `## Talk briefing` exactly as provided. The very first step entry (Step 1, Frame) is opened in the same pass with `Status: in_progress` and finalized to `Status: complete` once Step 1 finishes.

```markdown
# memory.md — <Talk folder name>

**Current step:** <N> — <Phase name> <in_progress | awaiting_presenter | complete>
**Topic:** <one-line topic from Step 1>
**Folder:** talks/<folder-name>/
**Started:** <YYYY-MM-DD>

---

## Talk briefing

<Verbatim presenter answer to the Step 1 free-text prompt. Do not paraphrase. This is the canonical context for all role work throughout the session.>

---

## <YYYY-MM-DD> — Step <N> (<Phase name>)
- Status: <in_progress | awaiting_presenter | complete>
- Asks log:
  - <YYYY-MM-DD HH:MM> — "<verbatim question>" → <answer | pending>
- What was decided: <filled at closure>
- Key inputs: <filled at closure>
- Files created/modified: <list>
- Pending open questions: <list or "none">

## <YYYY-MM-DD> — Step <N+1> (<Phase name>)
...
```
