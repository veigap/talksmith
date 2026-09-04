#!/usr/bin/env python3
"""Deterministically strip `Presenter feedback` fields out of a Talk's `final.md` (Step 6, d).

Why a script and not an LLM edit: a hand-strip once left `paragraph\\n---` — no blank line before
the slide boundary — and Markdown parsed the `---` as a **setext H2 underline**, silently fusing
the paragraph and the next slide and corrupting every separator after it. The guard against that
must live in code with a test, not in operator memory. This helper removes every feedback block and
then **guarantees a blank line before every `---` thematic break**, so the boundary can never be
reinterpreted as a heading underline.

Both authored forms are recognized (see `agents/editor.md` (d)):
  - H3 field:  `### Presenter feedback`     (slide-level; runs to the next heading / `---`)
  - paragraph: `**Presenter feedback:**`    (section/agenda-level; runs over its bullets)

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
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
# Indent-tolerant on the same terms as _HEADING, and it has to be: `# Cut material` archives a whole
# cut slide as one indented bullet — its `### Presenter feedback` heading AND its closing `---`
# both carry that indent. Anchored at column 0, this matched the heading but not the separator, so
# the sweep ran straight past the end of the record and swallowed the next one whole.
_HR = re.compile(r"^\s{0,3}-{3,}\s*$")
_BULLET = re.compile(r"^(\s*)[-*+]\s")
_BLANK = re.compile(r"^\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")


def _fenced(lines: list[str]) -> list[bool]:
    """Mark every line that belongs to a fenced block, its two delimiters included.

    Every pattern above means something *else* inside a fence. A `---` drawn in ASCII art is a
    rule the author drew, not a slide boundary. A `#` starting a code comment is not a heading.
    And the blank lines an ASCII diagram puts between its bands are load-bearing art, not stray
    whitespace — collapsing a pair of them closed the gap between two bands of a rendered
    diagram, silently, and the `---` case would have cut a diagram in half by inserting a blank
    line through the middle of it. So the stripper reads a fence as one opaque unit and never
    touches what is inside it.

    CommonMark's rule, minus what a Talk cannot produce: a fence opens on three or more backticks
    or tildes and closes on the same character, at least as long, with nothing after it. A fence
    left open at EOF protects the rest of the file, which is also how a Markdown parser reads it.
    """
    mask = [False] * len(lines)
    char, length = "", 0
    for i, ln in enumerate(lines):
        m = _FENCE.match(ln)
        if not char:
            if m:
                char, length = m.group(1)[0], len(m.group(1))
                mask[i] = True
            continue
        mask[i] = True
        if m and m.group(1)[0] == char and len(m.group(1)) >= length and not m.group(2).strip():
            char, length = "", 0
    return mask


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _in_block(line: str) -> bool:
    """Is this line still inside the feedback block being swept?

    A block is its bullets **plus their wrapped continuation lines**. Testing for a bullet alone was
    the bug: a `Resolution:` that wraps onto an indented continuation line is neither blank nor a
    bullet, so the sweep stopped there and the tail survived the strip. So: any bullet at any
    indent continues the block, and so does any indented non-bullet line. A heading or a `---`
    boundary ends it no matter how it is indented."""
    if _HEADING.match(line) or _HR.match(line):
        return False
    return bool(_BULLET.match(line)) or _indent(line) > 0


def _ends_block(lines: list[str], fence: list[bool], j: int) -> bool:
    """Does line `j` close the feedback block being swept?

    A fenced block ends it, whichever line of the fence we are looking at. A diagram or a code
    listing is never part of a feedback field, and stopping at the fence is the safe direction to
    be wrong in: the worst case is a few surviving feedback bullets, where reading *into* the
    fence would eat the diagram. Outside a fence, the old boundaries stand."""
    if fence[j]:
        return True
    return bool(_HEADING.match(lines[j]) or _HR.match(lines[j]))


def _strip_body(lines: list[str]) -> tuple[list[str], dict]:
    """Drop every feedback block from a body (frontmatter already removed). Returns (kept, stats)."""
    drop = [False] * len(lines)
    fence = _fenced(lines)
    stats = {"h3": 0, "paragraph": 0}
    i = 0
    while i < len(lines):
        ln = lines[i]

        if fence[i]:                       # inside a fence nothing is a field label
            i += 1
            continue

        if _H3_FEEDBACK.match(ln):
            # A slide-level H3 field: runs until the next heading (any level), `---`, a dedent, or
            # EOF. The dedent is the boundary the other two cannot supply: inside `# Cut material`
            # a whole archived slide is one indented bullet, and the last record of a run has no
            # closing `---` to stop at. A bullet shallower than this heading is by definition a new
            # record, never a continuation of this one. For an un-indented feedback field — every
            # ordinary slide — no bullet can be shallower than column 0, so nothing changes there.
            base = _indent(ln)
            j = i + 1
            while j < len(lines) and not (
                _ends_block(lines, fence, j)
                or (_BULLET.match(lines[j]) and _indent(lines[j]) < base)
            ):
                j += 1
            for k in range(i, j):
                drop[k] = True
            stats["h3"] += 1
            i = j
            continue

        if _PARA_FEEDBACK.match(ln):
            # Section/agenda paragraph label: runs over its following bullet list (any indent) and
            # over each bullet's indented continuation lines, stopping at the first line back at
            # column 0 that is not a bullet — a heading, `---`, or prose.
            j = i + 1
            while j < len(lines):
                if fence[j]:
                    break
                if _BLANK.match(lines[j]):
                    k = j
                    while k < len(lines) and _BLANK.match(lines[k]):
                        k += 1
                    if k < len(lines) and not fence[k] and _in_block(lines[k]):
                        j = k
                        continue
                    break
                if _in_block(lines[j]):
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
    """Collapse blank runs to one, guarantee a blank line before every `---`, trim edge blanks.

    Every rule here applies **outside fences only** (`_fenced`). Inside one the bytes are art or
    source and pass through untouched, blank runs and dash rules included."""
    fence = _fenced(lines)
    collapsed: list[str] = []
    cfence: list[bool] = []
    for i, ln in enumerate(lines):
        if fence[i]:
            collapsed.append(ln)
            cfence.append(True)
        elif _BLANK.match(ln):
            if collapsed and not cfence[-1] and _BLANK.match(collapsed[-1]):
                continue
            collapsed.append("")            # normalize any whitespace-only line to empty
            cfence.append(False)
        else:
            collapsed.append(ln)
            cfence.append(False)

    # THE guard: a `---` thematic break must never sit directly under a non-blank line, or Markdown
    # reads the pair as a setext H2 and the slide boundary is lost. A closing fence counts as that
    # non-blank line — a boundary right under one still needs its blank.
    guarded: list[str] = []
    gfence: list[bool] = []
    for i, ln in enumerate(collapsed):
        if not cfence[i] and _HR.match(ln) and guarded and not _BLANK.match(guarded[-1]):
            guarded.append("")
            gfence.append(False)
        guarded.append(ln)
        gfence.append(cfence[i])

    while guarded and not gfence[0] and _BLANK.match(guarded[0]):
        guarded.pop(0)
        gfence.pop(0)
    while guarded and not gfence[-1] and _BLANK.match(guarded[-1]):
        guarded.pop()
        gfence.pop()
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
    if not args.dry_run and (total or cleaned != original):
        path.write_text(cleaned, encoding="utf-8")
        print(f"  wrote {path} ({total} block(s) removed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
