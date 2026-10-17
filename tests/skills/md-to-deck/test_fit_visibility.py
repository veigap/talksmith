#!/usr/bin/env python3
"""The clipped-slide flag must not depend on which slide the deck was opened at.

Run:  python3 tests/skills/md-to-deck/test_fit_visibility.py

Reveal keeps every slide past its view distance at `display:none`. The fit pass used to measure
those too: a slide with no box has zero height, so `fitCover` found no room for a statement four
slides ahead of the cover and marked it `data-overflow` — a false "clipped" report that vanished
when the same deck was opened straight at that slide (bug log BUG-20261017-07). The pass now fits
only laid-out slides, and re-fits a slide (clearing its stale flag) when it is entered.

Both halves are checked, because "never flag anything" would pass the first one:
  * opened at the cover, a short statement deep in the deck carries no flag;
  * a statement that genuinely cannot fit is still flagged once it is laid out.

Needs Chrome (it is a layout question); skips without one.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "md-to-deck"
sys.path.insert(0, str(SKILL))

import _chrome  # noqa: E402

_FILL = [{"template": "statement", "section": "S", "title": f"Filler statement {i}"} for i in range(6)]
_SHORT = {"template": "statement", "section": "S", "title": "A short statement, far from the cover"}
_LONG = {"template": "statement", "section": "S",
         "title": " ".join(["An impossibly long statement that cannot fit the slide at any size."] * 40)}


def _flags(deck: Path, frag: str = "") -> list[str]:
    dom = _chrome.run(["--dump-dom", "--virtual-time-budget=8000", "--window-size=1280,720"],
                      _chrome.file_url(deck) + frag).decode("utf-8", "replace")
    return [("data-overflow" in a) for a in re.findall(r"<section([^>]*)>", dom)]


def main() -> int:
    if not _chrome.find():
        print("SKIP  test_fit_visibility (no Chrome/Chromium)")
        return 0
    slides = _FILL + [_SHORT] + _FILL + [_LONG]
    short_i, long_i = len(_FILL), len(slides) - 1
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "slide-model.json").write_text(json.dumps(
            {"deck": {"title": "Fit visibility", "lang": "en"}, "slides": slides}), encoding="utf-8")
        out = td / "out" / "index.html"
        out.parent.mkdir()
        subprocess.run([sys.executable, str(SKILL / "build_html.py"), "--model",
                        str(td / "slide-model.json"), "--talk-root", str(td), "-o", str(out)],
                       check=True, capture_output=True)
        # section index = slide index + 1: the deck opens with its generated cover
        at_cover = _flags(out)
        at_long = _flags(out, f"#/{long_i + 1}")
    fails = []
    if not at_cover or at_cover[short_i + 1]:
        fails.append("  opened at the cover, an unrendered statement was flagged clipped")
    if any(at_cover):
        fails.append(f"  opened at the cover, unrendered slides carry flags: "
                     f"{[i for i, f in enumerate(at_cover) if f]}")
    if not at_long or not at_long[long_i + 1]:
        fails.append("  a statement that cannot fit must still be flagged once it is laid out")
    print(f"{'PASS' if not fails else 'FAIL'}  test_fit_visibility")
    for f in fails:
        print(f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
