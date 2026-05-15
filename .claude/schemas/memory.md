# Schema — `talks/<Talk>/memory.md`

Specification for `talks/<Talk>/memory.md`: the per-Talk progress log and restore point. Each Talk has exactly one. The orchestrator parses a single line — `**Current step:**` — on resume to know where to pick up; everything else is human-readable history.

## Purpose

Append-only history of every completed Talksmith step, plus a single-line top-of-file state marker that lets the orchestrator resume mid-flow weeks later. Captures decisions, key inputs, files changed, and pending open questions per step.

## Loading semantics

| Reader / Writer | When | What for |
|---|---|---|
| `editor` subagent (writer) | After every completed step (1–8). **Sole writer.** | Initialize at Step 1 with the verbatim Talk briefing; append one dated entry per completed step; atomically update the `Current step:` line in the top-of-file header. |
| Orchestrator (reader) | Step 0 on a Resume session; ad-hoc throughout | Parse the single `Current step:` line to determine where to resume. Read prior step entries when context is needed (rare — most session state lives in `master.md` and `knowledge/compile/`). |

The orchestrator never writes this file directly.

## Resume contract

The **`Current step:` line is the single source of truth for resume.** Format: `**Current step:** <integer> — <phase name> complete`. Examples:

- `**Current step:** 1 — Frame complete`
- `**Current step:** 4 — Draft complete`
- `**Current step:** 6 — Polish complete`

The editor updates this line atomically when appending a new dated entry — never leaves it stale. The orchestrator's resume logic reads only this line; everything below is human-readable history.

## Talk briefing block

A `## Talk briefing` section near the top holds the verbatim Step-1 free-text answer from the presenter. This is the canonical context handed to every `librarian`, `composer`, and `editor` dispatch throughout the session — do not paraphrase it away. Once written at Step 1, the briefing block is **immutable** for the lifetime of the Talk. The editor leaves it untouched on every subsequent step's append.

## Append-only history

After Step 1, every completed step appends a new dated entry below the briefing block. Old entries are never edited or deleted — they're the audit trail of how the Talk evolved.

Per-step entry shape:

```
## <YYYY-MM-DD> — Step <N> (<Phase name>)
- What was decided: <one or two lines>
- Key inputs: <presenter answers, files added, etc.>
- Files created/modified: <list>
- Pending open questions: <list or "none">
```

## Canonical empty form

The editor bootstraps `talks/<Talk>/memory.md` from this form on its Step 1 init dispatch. The orchestrator passes the verbatim Step-1 briefing text in the dispatch prompt — write it under `## Talk briefing` exactly as received. The very first dated step entry (Step 1, Frame) is appended in the same dispatch.

```markdown
# memory.md — <Talk folder name>

**Current step:** <N — Phase name complete>
**Topic:** <one-line topic from Step 1>
**Folder:** talks/<folder-name>/
**Started:** <YYYY-MM-DD>

---

## Talk briefing

<Verbatim presenter answer to the Step 1 free-text prompt. Do not paraphrase. This is the canonical context passed to librarian / composer / editor dispatches throughout the session.>

---

## <YYYY-MM-DD> — Step <N> (<Phase name>)
- What was decided: <one or two lines>
- Key inputs: <presenter answers, files added, etc.>
- Files created/modified: <list>
- Pending open questions: <list or "none">

## <YYYY-MM-DD> — Step <N+1> (<Phase name>)
...
```
