#!/usr/bin/env python3
"""Tests for `polish_ascii.scan()` fence detection.

Run:  python3 tests/skills/polish-ascii/test_scan_detection.py

**The case that matters is the code-fence family.** Detection once had a fallback tier that sniffed
untagged fences for box glyphs — anything containing `->`, `|` or `+--`, or simply three or more
lines. On a deck about prompting that found 16 blocks of which 2 were diagrams; Step 6 rasterizes
what it detects *and deletes the source fence*, so the other 14 would have become unreadable
pictures. The tier is gone: the ` ```ascii ` tag is the entire rule. These tests pin that — every
other fence shape, however diagram-like, must be invisible to `scan`.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "skills" / "polish-ascii"))
from polish_ascii import scan  # noqa: E402

_HEAD = "---\ntitle: t\n---\n\n# 1. Sección\n"

# (name, fence lang, payload, expected detection)
CASES: list[tuple[str, str, str, bool]] = [
    # --- must be INVISIBLE: every fence that is not tagged `ascii` ---------------------------------
    ("untagged_ascii_box", "",
     "+-----------+      +-----------+\n|  Prompt   | ---> |  Modelo   |\n+-----------+      +-----------+", False),
    ("untagged_unicode_box", "", "┌─────────┐\n│ Sistema │\n└─────────┘", False),
    ("untagged_prompt_prose", "",
     "Sos un asistente experto.\nFormato: categoria -> subcategoria -> prioridad\nSi no sabés, decí \"desconocido\".", False),
    ("untagged_python", "", 'def clasificar(t):\n    if "urgente" in t:\n        return "alta"', False),
    ("untagged_json", "", '{\n  "model": "claude-opus-5",\n  "max_tokens": 1024\n}', False),
    ("untagged_xml", "", "<task>\n  <objetivo>clasificar</objetivo>\n</task>", False),
    ("untagged_markdown_table", "", "| campo | valor |\n|-------|-------|\n| a     | 1     |", False),
    ("text_tagged_box", "text", "+---+\n| A |\n+---+", False),
    ("diagram_tagged_box", "diagram", "+---+\n| A |\n+---+", False),
    ("python_tagged", "python", "def f():\n    return 1", False),
    # --- must be DETECTED: the tag, and only the tag ----------------------------------------------
    ("ascii_tagged_box", "ascii", "+---+\n| A |\n+---+", True),
    ("ascii_tagged_single_line", "ascii", "A --> B", True),
    ("ascii_tagged_prose_card", "ascii", "REGLA DE ORO: nunca es asesoramiento.\nSiempre aclaralo al final.", True),
]


def _detects(lang: str, payload: str, tmp: Path) -> bool:
    f = tmp / "final.md"
    f.write_text(f"{_HEAD}\n## 1. Slide\n\n```{lang}\n{payload}\n```\n")
    return len(scan(f)["blocks"]) == 1


def _check_empty_payload(tmp: Path) -> bool:
    f = tmp / "final.md"
    f.write_text(f"{_HEAD}\n## 1. Slide\n\n```ascii\n\n```\n")
    ok = scan(f)["blocks"] == []
    print(f"  {'ok  ' if ok else 'FAIL'}  empty_ascii_fence_is_not_a_block")
    return ok


def _check_no_slide(tmp: Path) -> bool:
    """A tagged block under a heading that carries no slides is counted, not attached."""
    f = tmp / "final.md"
    f.write_text("---\ntitle: t\n---\n\n# Cut material\n\n```ascii\n+---+\n| A |\n+---+\n```\n")
    r = scan(f)
    ok = r["blocks"] == [] and r["skipped_non_slide"] == 1
    print(f"  {'ok  ' if ok else 'FAIL'}  block_outside_a_slide_is_skipped_and_counted")
    return ok


def _check_force_does_not_resurrect(tmp: Path) -> bool:
    """`ascii-render: force` overrides the image-ref rule — it can NOT make an untagged fence render."""
    f = tmp / "final.md"
    f.write_text(f"{_HEAD}\n## 1. Slide\n\n<!-- ascii-render: force -->\n```\n+---+\n| A |\n+---+\n```\n")
    ok = scan(f)["blocks"] == []
    print(f"  {'ok  ' if ok else 'FAIL'}  force_hint_does_not_override_the_tag")
    return ok


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("fence detection:")
        for name, lang, payload, expected in CASES:
            got = _detects(lang, payload, tmp)
            ok = got == expected
            failures += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {name}: expected {expected}, got {got}")
        print("edges:")
        failures += not _check_empty_payload(tmp)
        failures += not _check_no_slide(tmp)
        failures += not _check_force_does_not_resurrect(tmp)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(CASES) + 3} polish-ascii detection tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
