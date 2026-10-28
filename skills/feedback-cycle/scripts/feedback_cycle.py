#!/usr/bin/env python3
"""talksmith feedback_cycle helper — Step 5 / Step 6 mechanical bookkeeping.

Subcommands:
  find-closed-unmirrored  --draft <path> --backlog <path> [--format json|human]   # Step 5
  stamp                   --draft <path> --line N [--date YYYY-MM-DD]              # Step 5
  close                   --draft <path> --line N --resolution "<text>"            # Step 5
  mirror-row              --draft <path> --backlog <path> --line N --expect-text "<verbatim>"
                          [--tags "a,b"]                                           # Step 5
  rescue-open             --final <path> [--dry-run]                               # Step 6 (c)
  move                    --backlog <path> --processed <path> [--rows <json|->
                          --promoted-to <id> [--promoted-at YYYY-MM-DD]] [--dry-run] # Step 8

`--draft` targets the Talk's working file (`talks/<Talk>/draft.md`), edited by the
presenter during Step 5. `--final` targets the Step-6 derived file
(`talks/<Talk>/final.md`), produced from `draft.md` by the Polish copy step. The
two flags are deliberately distinct so each subcommand makes it explicit which
file it expects.

See SKILL.md for the full contract.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
from _write import atomic_write_lines  # noqa: E402  (shared atomic file write)
from typing import Any

H1 = re.compile(r"^# (?!#)(.+?)\s*$")
H2 = re.compile(r"^## (?!#)(.+?)\s*$")
H3_FEEDBACK = re.compile(r"^### Presenter feedback", re.IGNORECASE)
PARA_FEEDBACK = re.compile(r"^\*\*Presenter feedback:\*\*", re.IGNORECASE)
# A stamped bullet carries an optional **origin** qualifier between the date and the em dash:
#   - [open] 2026-08-28 — "tighten this"              → presenter (the default; every pre-existing
#                                                        draft.md parses unchanged)
#   - [closed] 2026-08-28 (editor) — "tighten this"   → the Editor's own change log
# Only presenter-origin bullets belong in the cross-Talk backlog: an editor-origin bullet is
# internal bookkeeping for one Talk, and mirroring it pollutes the shared backlog with entries no
# presenter ever asked for.
PRESENTER, EDITOR = "presenter", "editor"
_STAMPED_BULLET = (
    r'^- \[{status}\] (?P<date>\d{{4}}-\d{{2}}-\d{{2}})'
    r'(?: \((?P<origin>presenter|editor)\))? — "(?P<text>.*)"\s*$'
)
OPEN_BULLET = re.compile(_STAMPED_BULLET.format(status="open"))
CLOSED_BULLET = re.compile(_STAMPED_BULLET.format(status="closed"))
ANY_STAMPED = re.compile(r"^- \[(open|closed)\]", re.IGNORECASE)
PLAIN_BULLET = re.compile(r"^- (.+?)\s*$")
RESOLUTION_LINE = re.compile(r"^  Resolution:\s*(.*)\s*$")
FENCE = re.compile(r"^```")


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"error: file not found: {path}")
    return path.read_text(encoding="utf-8").splitlines()


def _strip_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _section_kind(h1_title: str | None) -> str | None:
    if h1_title is None:
        return None
    t = h1_title.strip().lower()
    if t.startswith("thesis"):
        return "Thesis"
    if t.startswith("agenda") or t in {"índice", "indice"}:
        return "Agenda"
    if t.startswith(("conclusion", "conclusiones", "conclusions")):
        return "Conclusions"
    return None


def _location_for_line(lines: list[str], line_idx: int) -> str:
    """Walk backward from line_idx (0-based) to find nearest H2 and H1."""
    slide_title: str | None = None
    section_title: str | None = None
    in_code = False
    for i in range(line_idx - 1, -1, -1):
        # Naive fence tracking (walking backward — toggle counts)
        if FENCE.match(lines[i]):
            in_code = not in_code
            continue
        if in_code:
            continue
        if slide_title is None:
            m = H2.match(lines[i])
            if m:
                slide_title = m.group(1).strip()
                continue
        m = H1.match(lines[i])
        if m:
            section_title = m.group(1).strip()
            break
    kind = _section_kind(section_title)
    if kind == "Thesis":
        return "Thesis"
    if kind == "Agenda":
        return "Agenda"
    if slide_title:
        return f'Slide "{slide_title}"'
    if section_title:
        return f'Section "{section_title}"'
    return "Thesis"


def _talk_folder(md_path: Path) -> str:
    return md_path.resolve().parent.name


def _origin_of(m: "re.Match[str]") -> str:
    """Origin of a stamped bullet — unqualified bullets are presenter feedback."""
    return m.group("origin") or PRESENTER


def _origin_suffix(origin: str) -> str:
    """Render the origin qualifier. Presenter is the default and stays implicit."""
    return "" if origin == PRESENTER else f" ({origin})"


# ─── find-closed-unmirrored ───────────────────────────────────────────────────

def _all_closed_bullets(md_path: Path) -> list[dict[str, Any]]:
    lines = _read_lines(md_path)
    in_feedback = False
    in_code = False
    results: list[dict[str, Any]] = []
    for i, raw in enumerate(lines):
        if FENCE.match(raw):
            in_code = not in_code
            continue
        if in_code:
            continue
        if H1.match(raw):
            in_feedback = False
        if H2.match(raw):
            in_feedback = False
        if H3_FEEDBACK.match(raw) or PARA_FEEDBACK.match(raw):
            in_feedback = True
            continue
        if in_feedback and (raw.startswith("#") or raw.strip().startswith("---")):
            in_feedback = False
        if not in_feedback:
            continue
        m = CLOSED_BULLET.match(raw)
        if not m:
            continue
        date, verbatim = m.group("date"), m.group("text")
        resolution = ""
        if i + 1 < len(lines):
            rm = RESOLUTION_LINE.match(lines[i + 1])
            if rm:
                resolution = rm.group(1).strip()
        results.append({
            "line": i + 1,
            "date": date,
            "origin": _origin_of(m),
            "text": verbatim,
            "resolution": resolution,
            "location": _location_for_line(lines, i),
        })
    return results


# ─── backlog / processed rows ─────────────────────────────────────────────────
# Both files hold the same row shape (schemas/feedback-backlog.md → *Entry format*): a `- talk:`
# line followed by two-space-indented `key: value` lines. A row runs until the next unindented or
# blank line. Parsing keeps each row's line span so `move` can delete exactly what it archived.

ROW_START = re.compile(r"^- talk:")
ROW_FIELD = re.compile(r"^(?:- |  )(\w+):\s?(.*?)\s*$")


def _parse_rows(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        if not ROW_START.match(lines[i]):
            i += 1
            continue
        start = i
        i += 1
        while i < len(lines) and lines[i].strip() and lines[i][:1].isspace():
            i += 1
        fields: dict[str, str] = {}
        for raw in lines[start:i]:
            m = ROW_FIELD.match(raw)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2)
        rows.append({"start": start, "end": i, "fields": fields})
    return rows


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return _parse_rows(path.read_text(encoding="utf-8").splitlines()) if path.exists() else []


def _row_text(fields: dict[str, str]) -> str:
    return _strip_quotes(fields.get("feedback", ""))


def _same_row(a: dict[str, str], b: dict[str, str]) -> bool:
    """Are two rows (field dicts) the same feedback bullet?

    Same talk, date and verbatim — and then the same location **or** the same resolution. Location
    alone is not stable: a slide renamed after the row was written changes it, and a copy-only Move
    left rows whose two copies disagree on it. Verbatim alone is not unique either: the presenter
    pastes the same note on two slides, and those twins differ in both location and resolution
    (each slide got its own fix), which is what keeps one from hiding the other.
    """
    if (a.get("talk"), a.get("date"), _row_text(a)) != (b.get("talk"), b.get("date"), _row_text(b)):
        return False
    if a.get("location") == b.get("location"):
        return True
    return bool(a.get("resolution")) and a.get("resolution") == b.get("resolution")


def _is_recorded(probe: dict[str, str], rows: list[dict[str, Any]], text_is_unique: bool = False) -> bool:
    """Does `rows` already hold `probe`? With `text_is_unique` (the verbatim occurs once in its
    Talk's draft), (talk, verbatim) is enough — the long-standing rule for draft → backlog."""
    if any(_same_row(probe, r["fields"]) for r in rows):
        return True
    return text_is_unique and any(r["fields"].get("talk") == probe.get("talk")
                                  and _row_text(r["fields"]) == _row_text(probe) for r in rows)


def _probe(talk: str, bullet: dict[str, Any]) -> dict[str, str]:
    """A draft bullet as backlog-row fields, for `_is_recorded`."""
    return {"talk": talk, "date": bullet["date"], "feedback": bullet["text"],
            "location": bullet["location"], "resolution": bullet.get("resolution", "")}


def cmd_find_closed_unmirrored(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft).resolve()
    backlog_path = Path(args.backlog).resolve()
    talk = _talk_folder(draft_path)
    closed = _all_closed_bullets(draft_path)
    rows = _read_rows(backlog_path)
    texts = [c["text"] for c in closed]
    # Only presenter-origin bullets are candidates for the cross-Talk backlog. Editor-origin bullets
    # are this Talk's internal change log — counting them once reported 52 "pending" rows of which
    # almost none belonged in the backlog, drowning the real ones.
    considered = closed if args.origin == "all" else [c for c in closed if c["origin"] == args.origin]
    excluded = len(closed) - len(considered)
    unmirrored = [c for c in considered
                  if not _is_recorded(_probe(talk, c), rows, texts.count(c["text"]) == 1)]
    if args.format == "json":
        json.dump(unmirrored, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    suffix = f" ({excluded} non-{args.origin}-origin bullet(s) excluded)" if excluded else ""
    if not unmirrored:
        print(f"no closed-and-unmirrored bullets for talk {talk}.{suffix}")
        return 0
    print(f"found {len(unmirrored)} closed bullet(s) not yet in backlog{suffix}:\n")
    for c in unmirrored:
        origin_part = "" if c["origin"] == PRESENTER else f"  [{c['origin']}]"
        print(f"  line {c['line']:4d}  {c['location']}{origin_part}")
        print(f"            \"{c['text']}\"")
        if c["resolution"]:
            print(f"            Resolution: {c['resolution']}")
        print()
    return 0


# ─── stamp ────────────────────────────────────────────────────────────────────

def cmd_stamp(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft).resolve()
    lines = _read_lines(draft_path)
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f"error: line {args.line} out of range (file has {len(lines)} lines)", file=sys.stderr)
        return 2
    raw = lines[idx]
    if ANY_STAMPED.match(raw):
        print(f"noop: line {args.line} already stamped")
        return 0
    m = PLAIN_BULLET.match(raw)
    if not m:
        print(f"error: line {args.line} is not a bullet: {raw!r}", file=sys.stderr)
        return 2
    text = _strip_quotes(m.group(1))
    date = args.date or datetime.date.today().isoformat()
    origin = args.origin or PRESENTER
    lines[idx] = f'- [open] {date}{_origin_suffix(origin)} — "{text}"'
    atomic_write_lines(draft_path, lines)
    print(f"stamped: line {args.line} → [open] {date} ({origin})")
    return 0


# ─── close ────────────────────────────────────────────────────────────────────

def cmd_close(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft).resolve()
    lines = _read_lines(draft_path)
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f"error: line {args.line} out of range", file=sys.stderr)
        return 2
    raw = lines[idx]
    m = OPEN_BULLET.match(raw)
    if not m:
        if CLOSED_BULLET.match(raw):
            print(f"error: line {args.line} is already [closed]", file=sys.stderr)
            return 2
        print(f"error: line {args.line} is not an [open] bullet: {raw!r}", file=sys.stderr)
        return 2
    date, verbatim, origin = m.group("date"), m.group("text"), _origin_of(m)
    lines[idx] = f'- [closed] {date}{_origin_suffix(origin)} — "{verbatim}"'
    resolution_line = f"  Resolution: {args.resolution}"
    if idx + 1 < len(lines) and RESOLUTION_LINE.match(lines[idx + 1]):
        lines[idx + 1] = resolution_line
    else:
        lines.insert(idx + 1, resolution_line)
    atomic_write_lines(draft_path, lines)
    print(f"closed: line {args.line} (date {date}) + Resolution")
    return 0


# ─── mirror-row ───────────────────────────────────────────────────────────────

def cmd_mirror_row(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft).resolve()
    backlog_path = Path(args.backlog).resolve()
    lines = _read_lines(draft_path)
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f"error: line {args.line} out of range", file=sys.stderr)
        return 2
    raw = lines[idx]
    m = CLOSED_BULLET.match(raw)
    if not m:
        print(f"error: line {args.line} is not a [closed] bullet: {raw!r}", file=sys.stderr)
        return 2
    date, verbatim, origin = m.group("date"), m.group("text"), _origin_of(m)
    # The line number is the caller's claim about *which* bullet; the verbatim is the proof. Line
    # numbers go stale inside a round — every `close` inserts a Resolution line, shifting every
    # bullet below it — and a stale --line used to land on a neighbouring [closed] bullet and mirror
    # it with the tags meant for another one. Nothing downstream could tell.
    expected = _strip_quotes(args.expect_text)
    if verbatim != expected:
        where = [c["line"] for c in _all_closed_bullets(draft_path) if c["text"] == expected]
        hint = (f"that bullet is now at line(s) {', '.join(map(str, where))}" if where
                else "no [closed] bullet carries that text")
        print(f"error: line {args.line} holds \"{verbatim}\", not the expected \"{expected}\" — {hint}. "
              f"Line numbers shift as `close` inserts Resolution lines; re-read them from "
              f"`find-closed-unmirrored --format json`. Nothing written.", file=sys.stderr)
        return 5
    if origin != PRESENTER and not args.allow_editor_origin:
        print(f"error: line {args.line} is an {origin}-origin bullet — the cross-Talk backlog mirrors "
              f"presenter feedback only. Pass --allow-editor-origin to override.", file=sys.stderr)
        return 4
    if idx + 1 >= len(lines):
        print(f"error: no Resolution line after closed bullet at {args.line}", file=sys.stderr)
        return 3
    rm = RESOLUTION_LINE.match(lines[idx + 1])
    if not rm:
        print(f"error: line {args.line + 1} is not a Resolution: continuation", file=sys.stderr)
        return 3
    resolution = rm.group(1).strip()
    talk = _talk_folder(draft_path)
    location = _location_for_line(lines, idx)
    texts = [c["text"] for c in _all_closed_bullets(draft_path)]
    probe = {"talk": talk, "date": date, "feedback": verbatim, "location": location, "resolution": resolution}
    if _is_recorded(probe, _read_rows(backlog_path), texts.count(verbatim) == 1):
        print(f"error: line {args.line} (\"{verbatim}\") already has a row in {backlog_path.name} — "
              f"refusing a duplicate. Nothing written.", file=sys.stderr)
        return 6

    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    elif not args.allow_empty_tags:
        print("warning: no tags provided; appending row with tags: [] (use --tags or --allow-empty-tags to silence)", file=sys.stderr)

    row_lines = [
        f"- talk: {talk}",
        f"  date: {date}",
        f"  location: {location}",
        f'  feedback: "{verbatim}"',
        f"  resolution: {resolution}",
        f"  tags: [{', '.join(tags)}]",
    ]
    existing = (backlog_path.read_text(encoding="utf-8").splitlines() if backlog_path.exists()
                else BACKLOG_EMPTY.splitlines())
    atomic_write_lines(backlog_path, existing + row_lines)
    print(f"mirrored: {talk} :: {location} :: line {args.line}")
    return 0


# ─── move ─────────────────────────────────────────────────────────────────────
# Step 8's Move used to be a hand edit, and in practice it only ever copied: rows promoted to L8–L10
# reached feedback-processed.md and stayed in the backlog too, so every later recurrence scan
# counted them again. `move` makes it one operation — append to processed, delete from backlog,
# then prove the invariant held.

# Canonical empty forms — schemas/feedback-backlog.md and schemas/feedback-processed.md own them.
BACKLOG_EMPTY = (
    "# Feedback backlog\n\n"
    "> Format spec, tagging vocabulary, and pattern-detection rules live in "
    "[`${CLAUDE_PLUGIN_ROOT}/schemas/feedback-backlog.md`](${CLAUDE_PLUGIN_ROOT}/schemas/feedback-backlog.md).\n\n"
    "## Entries\n\n<!-- Editor appends entries below this line. -->\n"
)
PROCESSED_EMPTY = (
    "# Feedback — processed\n\n"
    "> Format spec and audit-trail invariant live in "
    "[`${CLAUDE_PLUGIN_ROOT}/schemas/feedback-processed.md`](${CLAUDE_PLUGIN_ROOT}/schemas/feedback-processed.md).\n\n"
    "## Entries\n\n<!-- Editor role appends entries below this line during the Step 8 Move pass. -->\n"
)


def _archived(backlog: list[dict[str, Any]], processed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backlog rows that already sit in processed — the rows the invariant says must not exist."""
    return [r for r in backlog if _is_recorded(r["fields"], processed)]


def _select(backlog: list[dict[str, Any]], sel: dict[str, Any]) -> list[dict[str, Any]]:
    want = {k: (_strip_quotes(str(v)) if k == "feedback" else str(v).strip())
            for k, v in sel.items() if k in {"talk", "date", "location", "feedback"} and v}
    out = []
    for r in backlog:
        f = r["fields"]
        if all((_row_text(f) if k == "feedback" else f.get(k, "")) == v for k, v in want.items()):
            out.append(r)
    return out


def _load_selectors(spec: str) -> list[dict[str, Any]]:
    raw = sys.stdin.read() if spec == "-" else Path(spec).read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not all(isinstance(d, dict) for d in data):
        raise SystemExit("error: --rows must be a JSON object or a list of objects")
    return data


def cmd_move(args: argparse.Namespace) -> int:
    backlog_path = Path(args.backlog).resolve()
    processed_path = Path(args.processed).resolve()
    b_lines = _read_lines(backlog_path)
    p_lines = (processed_path.read_text(encoding="utf-8").splitlines() if processed_path.exists()
               else PROCESSED_EMPTY.splitlines())
    backlog, processed = _parse_rows(b_lines), _parse_rows(p_lines)

    selectors = _load_selectors(args.rows) if args.rows else []
    if selectors and not args.promoted_to:
        print("error: --promoted-to is required when --rows selects rows to move", file=sys.stderr)
        return 2
    # Resolve every selector before touching either file: one bad selector aborts the whole move.
    chosen: list[dict[str, Any]] = []
    for sel in selectors:
        if not sel.get("talk") or not sel.get("feedback"):
            print(f"error: selector needs at least `talk` and `feedback`: {sel}", file=sys.stderr)
            return 2
        hits = _select(backlog, sel)
        if not hits and any(p["fields"].get("promoted_to") == args.promoted_to
                            for p in _select(processed, sel)):
            print(f"noop: already moved to {args.promoted_to}: \"{_strip_quotes(sel['feedback'])[:70]}\"")
            continue  # an idempotent re-run (e.g. after a crash between the two writes)
        if len(hits) != 1:
            what = "matches no backlog row" if not hits else (
                f"matches {len(hits)} backlog rows (lines "
                f"{', '.join(str(h['start'] + 1) for h in hits)}) — add `date` and/or `location`")
            print(f"error: selector {json.dumps(sel, ensure_ascii=False)} {what}. Nothing written.",
                  file=sys.stderr)
            return 2
        if hits[0] not in chosen:
            chosen.append(hits[0])

    date = args.promoted_at or datetime.date.today().isoformat()
    appended: list[str] = []
    n_appended = 0
    same_learning = [p for p in processed if p["fields"].get("promoted_to") == args.promoted_to]
    for r in chosen:
        if _is_recorded(r["fields"], same_learning):
            continue  # re-run after a crash between the two writes — the archive copy is there
        block = [ln for ln in b_lines[r["start"]:r["end"]]
                 if not re.match(r"^  promoted_(to|at):", ln)]
        appended += block + [f"  promoted_to: {args.promoted_to}", f"  promoted_at: {date}"]
        n_appended += 1

    new_p = list(p_lines)
    while new_p and not new_p[-1].strip():
        new_p.pop()
    new_p += appended
    # Delete the moved rows *and* any row already archived by an earlier copy-only Move — the
    # invariant is "nothing in processed is still in the backlog", not "nothing moved today is".
    gone = {id(r) for r in chosen} | {id(r) for r in _archived(backlog, _parse_rows(new_p))}
    drop = {i for r in backlog if id(r) in gone for i in range(r["start"], r["end"])}
    new_b = [ln for i, ln in enumerate(b_lines) if i not in drop]
    swept = len(gone) - len(chosen)

    if args.dry_run:
        print(f"[dry-run] would append {n_appended} row(s) to {processed_path.name}"
              + (f" (promoted_to: {args.promoted_to})" if selectors else "")
              + f" and remove {len(gone)} row(s) from "
              f"{backlog_path.name} ({swept} already archived)")
        for r in backlog:
            if id(r) in gone:
                f = r["fields"]
                print(f"  line {r['start'] + 1:4d}  {f.get('talk')} {f.get('date')}  \"{_row_text(f)[:70]}\"")
        return 0

    # Processed first: a crash between the two writes leaves a row in both files, which the next
    # `move` repairs (the sweep above). The reverse order could lose a row.
    if appended:
        atomic_write_lines(processed_path, new_p)
    if drop:
        atomic_write_lines(backlog_path, new_b)

    # Post-check, from disk: every moved row is archived, and no archived row is still in the backlog.
    after_b, after_p = _read_rows(backlog_path), _read_rows(processed_path)
    leftover = _archived(after_b, after_p)
    missing = [r for r in chosen if not _is_recorded(r["fields"], after_p)]
    if leftover or missing:
        for r in leftover:
            print(f"error: backlog line {r['start'] + 1} is still present after the move: "
                  f"\"{_row_text(r['fields'])[:70]}\"", file=sys.stderr)
        for r in missing:
            print(f"error: moved row \"{_row_text(r['fields'])[:70]}\" is missing from "
                  f"{processed_path.name}", file=sys.stderr)
        return 1
    print(f"moved: {n_appended} row(s) appended to {processed_path.name}, {len(gone)} removed from "
          f"{backlog_path.name}" + (f" ({swept} already archived by an earlier Move)" if swept else ""))
    return 0


# ─── rescue-open ──────────────────────────────────────────────────────────────

def _find_open_questions_section(lines: list[str]) -> tuple[int, int]:
    """Return (header_line_idx, insert_idx) for `# Open questions` section.

    If absent, return (-1, insert_idx_before_cut_material_or_end).
    Indices are 0-based; insert_idx is where to append the next bullet.
    """
    open_header_idx = -1
    cut_idx = -1
    for i, ln in enumerate(lines):
        if ln.strip() == "# Open questions":
            open_header_idx = i
        elif ln.strip() == "# Cut material":
            cut_idx = i
    if open_header_idx >= 0:
        # find next H1 after the open-questions header
        end = len(lines)
        for j in range(open_header_idx + 1, len(lines)):
            if lines[j].startswith("# ") and not lines[j].startswith("## "):
                end = j
                break
        # insert at end of the section (skip trailing blank lines)
        ins = end
        while ins > open_header_idx + 1 and lines[ins - 1].strip() == "":
            ins -= 1
        return open_header_idx, ins
    # No section yet — return insertion point before # Cut material or at EOF
    if cut_idx >= 0:
        ins = cut_idx
        while ins > 0 and lines[ins - 1].strip() == "":
            ins -= 1
        return -1, ins
    return -1, len(lines)


def _all_open_bullets(lines: list[str]) -> list[dict[str, Any]]:
    in_feedback = False
    in_code = False
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(lines):
        if FENCE.match(raw):
            in_code = not in_code
            continue
        if in_code:
            continue
        if H1.match(raw) or H2.match(raw):
            in_feedback = False
        if H3_FEEDBACK.match(raw) or PARA_FEEDBACK.match(raw):
            in_feedback = True
            continue
        if in_feedback and (raw.startswith("#") or raw.strip().startswith("---")):
            in_feedback = False
        if not in_feedback:
            continue
        m = OPEN_BULLET.match(raw)
        if not m:
            continue
        out.append({
            "line": i + 1,
            "date": m.group("date"),
            "origin": _origin_of(m),
            "text": m.group("text"),
            "location": _location_for_line(lines, i),
        })
    return out


def cmd_rescue_open(args: argparse.Namespace) -> int:
    final_path = Path(args.final).resolve()
    lines = _read_lines(final_path)
    open_bullets = _all_open_bullets(lines)
    if not open_bullets:
        print("no [open] bullets to rescue.")
        return 0

    header_idx, insert_idx = _find_open_questions_section(lines)

    # Build the section if needed
    new_lines = list(lines)
    if header_idx < 0:
        block = ["# Open questions", ""]
        # Insert block at insert_idx; insert_idx becomes the new header position
        new_lines[insert_idx:insert_idx] = block + [""]
        header_idx = insert_idx
        insert_idx = insert_idx + len(block)

    # Existing lines in Open Questions section (to avoid duplicates)
    existing_lines = set()
    end = len(new_lines)
    for j in range(header_idx + 1, len(new_lines)):
        if new_lines[j].startswith("# ") and not new_lines[j].startswith("## "):
            end = j
            break
    for j in range(header_idx + 1, end):
        existing_lines.add(new_lines[j].strip())

    appended = 0
    skipped = 0
    to_append: list[str] = []
    for b in open_bullets:
        new_line = f'- {b["location"]} — "{b["text"]}"'
        if new_line.strip() in existing_lines:
            skipped += 1
            continue
        to_append.append(new_line)
        appended += 1

    if to_append:
        new_lines[insert_idx:insert_idx] = to_append

    if args.dry_run:
        print(f"[dry-run] would append {appended} line(s) under # Open questions, skip {skipped} duplicate(s)")
        for line in to_append:
            print(f"  {line}")
        return 0

    atomic_write_lines(final_path, new_lines)
    print(f"rescued: {appended} appended to # Open questions, {skipped} skipped (already present)")
    return 0


# ─── arg parsing ──────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="feedback_cycle", description="Step 5 / Step 6 mechanical bookkeeping for Talksmith.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("find-closed-unmirrored", help="list [closed] bullets in draft.md not yet mirrored to feedback-backlog.md (Step 5)")
    pf.add_argument("--draft", required=True, help="path to the Talk's draft.md")
    pf.add_argument("--backlog", required=True)
    pf.add_argument("--format", choices=["json", "human"], default="human")
    pf.add_argument("--origin", choices=["presenter", "editor", "all"], default="presenter",
                    help="which bullets count as mirror candidates (default: presenter — the only "
                         "origin the cross-Talk backlog takes)")
    pf.set_defaults(func=cmd_find_closed_unmirrored)

    ps = sub.add_parser("stamp", help="rewrite a single unstamped bullet in draft.md to [open] form (Step 5)")
    ps.add_argument("--draft", required=True, help="path to the Talk's draft.md")
    ps.add_argument("--line", type=int, required=True)
    ps.add_argument("--date")
    ps.add_argument("--origin", choices=["presenter", "editor"], default="presenter",
                    help="who authored the bullet (default: presenter). `editor` marks a bullet the "
                         "Editor wrote as its own change log, keeping it out of the cross-Talk backlog")
    ps.set_defaults(func=cmd_stamp)

    pc = sub.add_parser("close", help="flip a single [open] bullet in draft.md to [closed] + Resolution (Step 5)")
    pc.add_argument("--draft", required=True, help="path to the Talk's draft.md")
    pc.add_argument("--line", type=int, required=True)
    pc.add_argument("--resolution", required=True)
    pc.set_defaults(func=cmd_close)

    pm = sub.add_parser("mirror-row", help="append one [closed]-bullet row from draft.md to feedback-backlog.md (Step 5)")
    pm.add_argument("--draft", required=True, help="path to the Talk's draft.md")
    pm.add_argument("--backlog", required=True)
    pm.add_argument("--line", type=int, required=True)
    pm.add_argument("--expect-text", required=True,
                    help="the bullet's verbatim feedback; refused (exit 5) if --line holds anything else")
    pm.add_argument("--tags")
    pm.add_argument("--allow-empty-tags", action="store_true")
    pm.add_argument("--allow-editor-origin", action="store_true",
                    help="mirror an editor-origin bullet anyway (refused by default)")
    pm.set_defaults(func=cmd_mirror_row)

    pr = sub.add_parser("rescue-open", help="rescue still-[open] bullets in final.md into # Open questions (Step 6 (c))")
    pr.add_argument("--final", required=True, help="path to the Talk's final.md")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_rescue_open)

    pv = sub.add_parser("move", help="move promoted rows feedback-backlog.md → feedback-processed.md (Step 8)")
    pv.add_argument("--backlog", required=True, help="path to config/feedback-backlog.md")
    pv.add_argument("--processed", required=True, help="path to config/feedback-processed.md")
    pv.add_argument("--rows", help="JSON selector(s) — a file path, or - for stdin: "
                                   '[{"talk": …, "feedback": …, "date"?: …, "location"?: …}, …]')
    pv.add_argument("--promoted-to", help="the learnings.md entry id the rows evidence")
    pv.add_argument("--promoted-at", help="YYYY-MM-DD (default: today)")
    pv.add_argument("--dry-run", action="store_true")
    pv.set_defaults(func=cmd_move)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
