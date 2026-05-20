#!/usr/bin/env python3
"""find_open_notes.py — scan a master.md for unstamped Presenter feedback bullets.

Unstamped = a bullet inside a Presenter feedback block that does NOT start with
[open] or [closed]. These are the notes the presenter has written but the
orchestrator has not yet processed via the Step 5 stamp→apply→close protocol.

Usage:
    python3 find_open_notes.py <master_path> [--format tsv|human]

Output (human, default):
    found N open note(s):

      line  523 | 2.8 Pan-Tompkins — la matemática (parte 2)
               | Let's add another slide about highpass(lowpass(x[n])).

Output (tsv):
    523\t2.8 Pan-Tompkins — la matemática (parte 2)\tLet's add another slide...

Exit codes:
    0  — ran successfully (zero or more notes found)
    1  — error (file not found, unreadable)
"""

import re
import sys
from pathlib import Path


# Patterns
_H1 = re.compile(r"^# (?!#)")
_H2 = re.compile(r"^## (?!#)")
_H3_FEEDBACK = re.compile(r"^### Presenter feedback", re.IGNORECASE)
_PARA_FEEDBACK = re.compile(r"^\*\*Presenter feedback:\*\*", re.IGNORECASE)
_STAMPED = re.compile(r"^- \[(open|closed)\]", re.IGNORECASE)
_BULLET = re.compile(r"^- ")
_FENCE = re.compile(r"^```")
_HR = re.compile(r"^---+\s*$")
_HEADING = re.compile(r"^#{1,6} ")


def find_open_notes(master_path: str) -> list[dict]:
    """Return list of {line, section, slide, location, text} for unstamped bullets."""
    path = Path(master_path)
    if not path.exists():
        raise FileNotFoundError(master_path)

    lines = path.read_text(encoding="utf-8").splitlines()

    results = []
    current_section = ""
    current_slide = ""
    in_feedback = False
    in_code_block = False

    for lineno, raw in enumerate(lines, start=1):
        # ── code fence toggle ──────────────────────────────────────────────────
        if _FENCE.match(raw):
            in_code_block = not in_code_block
        if in_code_block:
            continue

        # ── structural markers (reset feedback context) ────────────────────────
        if _H1.match(raw):
            current_section = raw.lstrip("# ").strip()
            current_slide = ""
            in_feedback = False
            continue

        if _H2.match(raw):
            current_slide = raw.lstrip("# ").strip()
            in_feedback = False
            continue

        # ── enter feedback block ───────────────────────────────────────────────
        if _H3_FEEDBACK.match(raw) or _PARA_FEEDBACK.match(raw):
            in_feedback = True
            continue

        # ── exit feedback block on any heading or HR ───────────────────────────
        if in_feedback and (_HEADING.match(raw) or _HR.match(raw)):
            in_feedback = False
            # Don't continue — fall through so H1/H2 above catch next heading
            # on the NEXT iteration; HR just ends the block.
            continue

        if not in_feedback:
            continue

        # ── inside feedback block ──────────────────────────────────────────────
        if not _BULLET.match(raw):
            continue  # blank lines, Resolution: continuations, etc.

        if _STAMPED.match(raw):
            continue  # already stamped [open] or [closed]

        text = raw[2:].strip()  # strip leading "- "
        location = current_slide or current_section
        results.append(
            {
                "line": lineno,
                "section": current_section,
                "slide": current_slide,
                "location": location,
                "text": text,
            }
        )

    return results


def _human(notes: list[dict]) -> str:
    if not notes:
        return "no open notes found."
    lines = [f"found {len(notes)} open note(s):\n"]
    for n in notes:
        lines.append(f"  line {n['line']:5d} | {n['location']}")
        lines.append(f"         | {n['text']}")
        lines.append("")
    return "\n".join(lines)


def _tsv(notes: list[dict]) -> str:
    rows = ["line\tlocation\ttext"]
    for n in notes:
        rows.append(f"{n['line']}\t{n['location']}\t{n['text']}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    fmt = "human"
    paths = []
    i = 0
    while i < len(argv):
        if argv[i] == "--format" and i + 1 < len(argv):
            fmt = argv[i + 1]
            i += 2
        else:
            paths.append(argv[i])
            i += 1

    if not paths:
        print("Usage: find_open_notes.py <master_path> [--format tsv|human]",
              file=sys.stderr)
        return 1

    master_path = paths[0]
    try:
        notes = find_open_notes(master_path)
    except FileNotFoundError:
        print(f"error: file not found: {master_path}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if fmt == "tsv":
        print(_tsv(notes))
    else:
        print(_human(notes))

    return 0


if __name__ == "__main__":
    sys.exit(main())
