#!/usr/bin/env python3
"""Tests for `validate_svg.cairo_traps()` — markup cairosvg draws differently from the browser.

Run:  python3 tests/skills/ascii-to-svg/test_cairo_traps.py

Both traps were found in real renders, and both are invisible in the XML:

- **Italic in a Helvetica-first family** is upright in cairosvg (Helvetica's slanted face is
  "Oblique") and slanted in the deck. The critic, shown the cairosvg PNG, charged an animation
  for "restyling" twelve labels it never touched.
- **A `<tspan>` run inside end- or middle-anchored text** is overprinted or pushed off the
  canvas. An end-anchored `objetivo = r − beta ·` rasterized as `objetivo =` alone.

The case that matters for false positives is `positioned_tspans_are_lines`: multi-line text
written as `<tspan x=…>` rows is anchored per row and draws correctly — it must not warn.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "ascii-to-svg" / "scripts"))
from validate_svg import cairo_traps  # noqa: E402

HELV = "Helvetica, Arial, sans-serif"
ARIAL = "Arial, Helvetica, sans-serif"


def _svg(body: str, root_attrs: str = "") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" {root_attrs}>{body}</svg>'


# (name, svg, expected substrings — empty list means no warning)
CASES = [
    ("italic_inherits_helvetica_from_root",
     _svg('<text font-style="italic">z</text>', f'font-family="{HELV}"'), ["italic run"]),
    ("italic_with_arial_first_is_fine",
     _svg(f'<text font-style="italic" font-family="{ARIAL}">z</text>', f'font-family="{HELV}"'), []),
    ("italic_helvetica_neue_is_fine",
     _svg('<text font-style="italic" font-family="Helvetica Neue, Arial">z</text>'), []),
    ("upright_helvetica_is_fine", _svg(f'<text font-family="{HELV}">z</text>'), []),
    ("end_anchor_with_inline_run",
     _svg('<text text-anchor="end">objetivo = <tspan font-weight="bold">r</tspan> - beta</text>'),
     ['text-anchor="end"']),
    ("middle_anchor_inherited_from_group",
     _svg('<g text-anchor="middle"><text>a <tspan font-weight="bold">b</tspan></text></g>'),
     ['text-anchor="middle"']),
    ("start_anchor_with_inline_run_is_fine",
     _svg('<text>objetivo = <tspan font-weight="bold">r</tspan> - beta</text>'), []),
    ("single_whole_tspan_is_fine",
     _svg('<text text-anchor="middle"><tspan font-weight="bold">all bold</tspan></text>'), []),
    ("positioned_tspans_are_lines",
     _svg('<text text-anchor="middle"><tspan x="50" dy="0">one</tspan><tspan x="50" dy="12">two</tspan></text>'),
     []),
]


def main() -> int:
    failures = 0
    for name, svg, want in CASES:
        got = cairo_traps(svg)
        ok = (not got) if not want else (len(got) == len(want) and all(w in g for w, g in zip(want, got)))
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}{'' if ok else f' → {got}'}")
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(CASES)} cairo-trap tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
