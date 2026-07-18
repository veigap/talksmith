#!/usr/bin/env python3
"""Tests for `strip_feedback.strip_feedback()` — the Step-6 (d) Presenter-feedback stripper.

Run:  python3 tests/skills/feedback-cycle/test_strip_feedback.py

**The case that matters is `no_blank_before_boundary_is_repaired`.** A hand-strip once left
`paragraph\\n---` with no blank line, and Markdown parsed the `---` as a setext H2 underline,
fusing the paragraph into the next slide and corrupting every separator downstream. The stripper
must guarantee a blank line before every `---`, so the boundary always stays a thematic break.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "feedback-cycle"))
from strip_feedback import strip_feedback  # noqa: E402


def _check(name: str, src: str, want_contains: list[str], want_absent: list[str]) -> bool:
    out = strip_feedback(src)
    ok = True
    for frag in want_contains:
        if frag not in out:
            ok = False
    for frag in want_absent:
        if frag in out:
            ok = False
    # The universal invariant: no non-blank line immediately precedes a `---` thematic break.
    # Skip a leading YAML frontmatter block, whose closing `---` legitimately follows a non-blank
    # metadata line (that `---` is a fence, not a slide boundary).
    lines = out.split("\n")
    scan_from = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                scan_from = j + 1
                break
    for i in range(scan_from, len(lines)):
        if lines[i].strip() == "---" and i > 0 and lines[i - 1].strip() != "":
            ok = False
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print("  --- output ---")
        print("  " + out.replace("\n", "\n  "))
    return ok


CASES = []

# 1. The headline: an H3 feedback field flush against a paragraph, boundary right after.
CASES.append((
    "no_blank_before_boundary_is_repaired",
    "## 1. Slide\n\n### Content\n\nsome text\n### Presenter feedback\n- [open] 2026-01-01 — \"tighten this\"\n---\n## 2. Next\n",
    ["some text", "## 2. Next"],
    ["Presenter feedback", "tighten this"],
))

# 2. The report's exact fixture: paragraph, blank, H3 block, boundary → paragraph, blank, boundary.
CASES.append((
    "report_fixture_paragraph_blank_boundary",
    "paragraph\n\n### Presenter feedback\n- [open] 2026-01-01 — \"note\"\n---\n",
    ["paragraph"],
    ["Presenter feedback", "note"],
))

# 3. Section/agenda paragraph form with a bullet list.
CASES.append((
    "paragraph_form_with_bullets",
    "# 1. Section\n\n**Goal of this section:** teach X\n\n**Presenter feedback:**\n- [open] 2026-01-01 — \"reorder\"\n- [closed] 2026-01-02 — \"done\"\n\n## 1. Slide\n",
    ["Goal of this section", "## 1. Slide"],
    ["Presenter feedback", "reorder", "done"],
))

# 4. Legacy inline bullet with deeper sub-bullets.
CASES.append((
    "legacy_bullet_with_subbullets",
    "### Content\n\n- a real point\n- **Presenter feedback:**\n  - [open] 2026-01-01 — \"x\"\n  - [open] 2026-01-02 — \"y\"\n- another real point\n",
    ["a real point", "another real point"],
    ["Presenter feedback", "\"x\"", "\"y\""],
))

# 5. Multiple slides, feedback on each — every boundary preserved.
CASES.append((
    "multiple_slides_all_boundaries_preserved",
    ("## 1. A\n### Content\ntext A\n### Presenter feedback\n- [open] d — \"a\"\n---\n"
     "## 2. B\n### Content\ntext B\n### Presenter feedback\n- [open] d — \"b\"\n---\n"
     "## 3. C\n### Content\ntext C\n"),
    ["text A", "text B", "text C", "## 2. B", "## 3. C"],
    ["Presenter feedback"],
))

# 6. Frontmatter is passed through untouched.
CASES.append((
    "frontmatter_preserved",
    "---\npresentation: X\npresenter: Y\n---\n\n# Thesis\n\n### Presenter feedback\n- [open] d — \"z\"\n\n## 1. Slide\n",
    ["presentation: X", "presenter: Y", "# Thesis", "## 1. Slide"],
    ["Presenter feedback", "\"z\""],
))

# 7. No feedback at all → structurally unchanged (idempotent, boundaries intact).
CASES.append((
    "no_feedback_is_noop",
    "## 1. A\n\n### Content\n\ntext\n\n---\n\n## 2. B\n\n### Content\n\nmore\n",
    ["text", "more", "## 2. B"],
    [],
))


def main() -> int:
    failures = 0
    for name, src, want_contains, want_absent in CASES:
        failures += not _check(name, src, want_contains, want_absent)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(CASES)} strip-feedback tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
