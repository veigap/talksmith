#!/usr/bin/env python3
"""talksmith feedback_cycle helper — Step 5 / Step 6 mechanical bookkeeping.

Subcommands:
  find-closed-unmirrored  --draft <path> --backlog <path> [--format json|human]   # Step 5
  stamp                   --draft <path> --line N [--date YYYY-MM-DD]              # Step 5
  close                   --draft <path> --line N --resolution "<text>"            # Step 5
  mirror-row              --draft <path> --backlog <path> --line N [--tags "a,b"]  # Step 5
  rescue-open             --final <path> [--dry-run]                               # Step 6 (c)

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
import os
import re
import sys
from pathlib import Path
from typing import Any

H1 = re.compile(r"^# (?!#)(.+?)\s*$")
H2 = re.compile(r"^## (?!#)(.+?)\s*$")
H3_FEEDBACK = re.compile(r"^### Presenter feedback", re.IGNORECASE)
PARA_FEEDBACK = re.compile(r"^\*\*Presenter feedback:\*\*", re.IGNORECASE)
OPEN_BULLET = re.compile(r'^- \[open\] (\d{4}-\d{2}-\d{2}) — "(.*)"\s*$')
CLOSED_BULLET = re.compile(r'^- \[closed\] (\d{4}-\d{2}-\d{2}) — "(.*)"\s*$')
ANY_STAMPED = re.compile(r"^- \[(open|closed)\]", re.IGNORECASE)
PLAIN_BULLET = re.compile(r"^- (.+?)\s*$")
RESOLUTION_LINE = re.compile(r"^  Resolution:\s*(.*)\s*$")
FENCE = re.compile(r"^```")


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"error: file not found: {path}")
    return path.read_text(encoding="utf-8").splitlines()


def _atomic_write(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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
        date, verbatim = m.group(1), m.group(2)
        resolution = ""
        if i + 1 < len(lines):
            rm = RESOLUTION_LINE.match(lines[i + 1])
            if rm:
                resolution = rm.group(1).strip()
        results.append({
            "line": i + 1,
            "date": date,
            "text": verbatim,
            "resolution": resolution,
            "location": _location_for_line(lines, i),
        })
    return results


def _existing_backlog_keys(backlog_path: Path, talk: str) -> set[tuple[str, str]]:
    """Return set of (talk, verbatim-text) already present in backlog."""
    if not backlog_path.exists():
        return set()
    text = backlog_path.read_text(encoding="utf-8")
    keys: set[tuple[str, str]] = set()
    current_talk: str | None = None
    feedback_re = re.compile(r'^\s*feedback:\s*"(.*)"\s*$')
    talk_re = re.compile(r"^- talk:\s*(\S+)\s*$")
    for raw in text.splitlines():
        tm = talk_re.match(raw)
        if tm:
            current_talk = tm.group(1).strip()
            continue
        fm = feedback_re.match(raw)
        if fm and current_talk is not None:
            keys.add((current_talk, fm.group(1)))
    return keys


def cmd_find_closed_unmirrored(args: argparse.Namespace) -> int:
    draft_path = Path(args.draft).resolve()
    backlog_path = Path(args.backlog).resolve()
    talk = _talk_folder(draft_path)
    closed = _all_closed_bullets(draft_path)
    existing = _existing_backlog_keys(backlog_path, talk)
    unmirrored = [c for c in closed if (talk, c["text"]) not in existing]
    if args.format == "json":
        json.dump(unmirrored, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if not unmirrored:
        print(f"no closed-and-unmirrored bullets for talk {talk}.")
        return 0
    print(f"found {len(unmirrored)} closed bullet(s) not yet in backlog:\n")
    for c in unmirrored:
        print(f"  line {c['line']:4d}  {c['location']}")
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
    lines[idx] = f'- [open] {date} — "{text}"'
    _atomic_write(draft_path, lines)
    print(f"stamped: line {args.line} → [open] {date}")
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
    date, verbatim = m.group(1), m.group(2)
    lines[idx] = f'- [closed] {date} — "{verbatim}"'
    resolution_line = f"  Resolution: {args.resolution}"
    if idx + 1 < len(lines) and RESOLUTION_LINE.match(lines[idx + 1]):
        lines[idx + 1] = resolution_line
    else:
        lines.insert(idx + 1, resolution_line)
    _atomic_write(draft_path, lines)
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
    date, verbatim = m.group(1), m.group(2)
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
    if not backlog_path.exists():
        backlog_path.write_text(
            "# Feedback backlog\n\n## Entries\n\n<!-- Editor appends entries below this line. -->\n",
            encoding="utf-8",
        )
    existing = backlog_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    existing += "\n".join(row_lines) + "\n"
    tmp = backlog_path.with_suffix(backlog_path.suffix + ".tmp")
    tmp.write_text(existing, encoding="utf-8")
    os.replace(tmp, backlog_path)
    print(f"mirrored: {talk} :: {location} :: line {args.line}")
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
            "date": m.group(1),
            "text": m.group(2),
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

    _atomic_write(final_path, new_lines)
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
    pf.set_defaults(func=cmd_find_closed_unmirrored)

    ps = sub.add_parser("stamp", help="rewrite a single unstamped bullet in draft.md to [open] form (Step 5)")
    ps.add_argument("--draft", required=True, help="path to the Talk's draft.md")
    ps.add_argument("--line", type=int, required=True)
    ps.add_argument("--date")
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
    pm.add_argument("--tags")
    pm.add_argument("--allow-empty-tags", action="store_true")
    pm.set_defaults(func=cmd_mirror_row)

    pr = sub.add_parser("rescue-open", help="rescue still-[open] bullets in final.md into # Open questions (Step 6 (c))")
    pr.add_argument("--final", required=True, help="path to the Talk's final.md")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_rescue_open)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
