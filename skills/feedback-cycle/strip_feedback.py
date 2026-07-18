#!/usr/bin/env python3
"""Deterministically strip `Presenter feedback` fields out of a Talk's `final.md` (Step 6, d).

Why a script and not an LLM edit: a hand-strip once left `paragraph\\n---` — no blank line before
the slide boundary — and Markdown parsed the `---` as a **setext H2 underline**, silently fusing
the paragraph and the next slide and corrupting every separator after it. The guard against that
must live in code with a test, not in operator memory. This helper removes every feedback block and
then **guarantees a blank line before every `---` thematic break**, so the boundary can never be
reinterpreted as a heading underline.

Three authored forms are recognized (see `agents/editor.md` (d)):
  - H3 field:      `### Presenter feedback`        (slide-level; runs to the next heading / `---`)
  - paragraph:     `**Presenter feedback:**`       (section/agenda-level; runs over its bullets)
  - legacy bullet: `- **Presenter feedback:**`     (older inline form; runs over deeper sub-bullets)

A leading YAML frontmatter block (delimited by `---`) is detected and passed through untouched.

CLI:
    python3 strip_feedback.py <final.md> [--dry-run]

Importable:
    from strip_feedback import strip_feedback
    cleaned = strip_feedback(text)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_H3_FEEDBACK = re.compile(r"^\s{0,3}#{3}\s+Presenter feedback\s*:?\s*$", re.I)
_PARA_FEEDBACK = re.compile(r"^\s{0,3}\*\*\s*Presenter feedback\s*:?\s*\*\*\s*$", re.I)
_BULLET_FEEDBACK = re.compile(r"^(\s*)[-*+]\s+\*\*\s*Presenter feedback\s*:?\s*\*\*", re.I)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_HR = re.compile(r"^-{3,}\s*$")
_BULLET = re.compile(r"^(\s*)[-*+]\s")
_BLANK = re.compile(r"^\s*$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _strip_body(lines: list[str]) -> tuple[list[str], dict]:
    """Drop every feedback block from a body (frontmatter already removed). Returns (kept, stats)."""
    drop = [False] * len(lines)
    stats = {"h3": 0, "paragraph": 0, "bullet": 0}
    i = 0
    while i < len(lines):
        ln = lines[i]

        if _H3_FEEDBACK.match(ln):
            # A slide-level H3 field: runs until the next heading (any level) or `---` or EOF.
            j = i + 1
            while j < len(lines) and not (_HEADING.match(lines[j]) or _HR.match(lines[j])):
                j += 1
            for k in range(i, j):
                drop[k] = True
            stats["h3"] += 1
            i = j
            continue

        m = _BULLET_FEEDBACK.match(ln)
        if m:
            # Legacy inline bullet: consume it plus any deeper-indented sub-bullets (and the blank
            # lines strictly between them).
            base = _indent(ln)
            j = i + 1
            while j < len(lines):
                if _BLANK.match(lines[j]):
                    k = j
                    while k < len(lines) and _BLANK.match(lines[k]):
                        k += 1
                    if k < len(lines) and _BULLET.match(lines[k]) and _indent(lines[k]) > base:
                        j = k
                        continue
                    break
                if _BULLET.match(lines[j]) and _indent(lines[j]) > base:
                    j += 1
                    continue
                break
            for k in range(i, j):
                drop[k] = True
            stats["bullet"] += 1
            i = j
            continue

        if _PARA_FEEDBACK.match(ln):
            # Section/agenda paragraph label: runs over its following bullet list (any indent),
            # stopping at the first non-bullet, non-blank line (a heading, `---`, or prose).
            j = i + 1
            while j < len(lines):
                if _BLANK.match(lines[j]):
                    k = j
                    while k < len(lines) and _BLANK.match(lines[k]):
                        k += 1
                    if k < len(lines) and _BULLET.match(lines[k]):
                        j = k
                        continue
                    break
                if _BULLET.match(lines[j]):
                    j += 1
                    continue
                break
            for k in range(i, j):
                drop[k] = True
            stats["paragraph"] += 1
            i = j
            continue

        i += 1

    kept = [ln for k, ln in enumerate(lines) if not drop[k]]
    return _normalize(kept), stats


def _normalize(lines: list[str]) -> list[str]:
    """Collapse blank runs to one, guarantee a blank line before every `---`, trim edge blanks."""
    collapsed: list[str] = []
    for ln in lines:
        if _BLANK.match(ln):
            if collapsed and _BLANK.match(collapsed[-1]):
                continue
            collapsed.append("")            # normalize any whitespace-only line to empty
        else:
            collapsed.append(ln)

    # THE guard: a `---` thematic break must never sit directly under a non-blank line, or Markdown
    # reads the pair as a setext H2 and the slide boundary is lost.
    guarded: list[str] = []
    for ln in collapsed:
        if _HR.match(ln) and guarded and not _BLANK.match(guarded[-1]):
            guarded.append("")
        guarded.append(ln)

    while guarded and _BLANK.match(guarded[0]):
        guarded.pop(0)
    while guarded and _BLANK.match(guarded[-1]):
        guarded.pop()
    return guarded


def _split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Peel a leading `---`…`---` YAML frontmatter block off (passed through untouched)."""
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                return lines[: j + 1], lines[j + 1:]
    return [], lines


def strip_feedback(text: str) -> str:
    """Return `text` with every Presenter-feedback block removed and slide boundaries preserved."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]                  # drop the artifact of a trailing newline
    prefix, body = _split_frontmatter(lines)
    kept, _ = _strip_body(body)
    if prefix:
        result = prefix + ([""] + kept if kept else [])
    else:
        result = kept
    return "\n".join(result) + "\n"


def strip_feedback_stats(text: str) -> dict:
    """The removal counts by form, for the CLI summary."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    _, body = _split_frontmatter(lines)
    _, stats = _strip_body(body)
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("final", help="path to the Talk's final.md (Step-6 derived file)")
    ap.add_argument("--dry-run", action="store_true", help="report what would be removed; write nothing")
    args = ap.parse_args(argv)

    path = Path(args.final)
    if not path.is_file():
        print(f"error: final.md not found: {path}", file=sys.stderr)
        return 2
    original = path.read_text(encoding="utf-8")
    stats = strip_feedback_stats(original)
    cleaned = strip_feedback(original)
    total = sum(stats.values())

    tag = "  [dry-run]" if args.dry_run else ""
    print(f"stripped Presenter feedback from {path}:{tag}")
    print(f"  H3 fields:        {stats['h3']}")
    print(f"  paragraph labels: {stats['paragraph']}")
    print(f"  legacy bullets:   {stats['bullet']}")
    if not args.dry_run and (total or cleaned != original):
        path.write_text(cleaned, encoding="utf-8")
        print(f"  wrote {path} ({total} block(s) removed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
