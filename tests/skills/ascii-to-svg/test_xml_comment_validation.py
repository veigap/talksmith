#!/usr/bin/env python3
"""Tests that `validate_svg` rejects decorative XML comments containing `--`.

Run:  python3 tests/skills/ascii-to-svg/test_xml_comment_validation.py

Backs the `config/diagram-style.md` rule *No decorative XML comments*. A `--` sequence is
illegal *inside* an XML comment (per the XML spec), so an SVG carrying `<!-- ---- -->` is
malformed and cairosvg / the PPTX pipeline reject it. `validate_svg.validate()` must catch this
as an unfixable error (surfacing as `failed: svg_validation`) rather than let a broken SVG reach
disk. A single hyphen inside a comment is legal and must still pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "ascii-to-svg"))
from validate_svg import validate  # noqa: E402


def _svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{body}</svg>'


# (name, svg, expect_error, why)
CASES = [
    (
        "decorative_dashes_rejected",
        _svg('<!-- ---- --><rect width="10" height="10"/>'),
        True,
        "a run of dashes as a comment separator — `--` is illegal inside XML comments, so the "
        "whole file is malformed; validate must fail it, not pass a broken SVG to disk",
    ),
    (
        "double_hyphen_in_comment_rejected",
        _svg('<!-- box a--b --><rect width="10" height="10"/>'),
        True,
        "even an incidental `--` inside a comment is illegal XML",
    ),
    (
        "equals_rule_comment_rejected",
        _svg('<!-- ==== section ==== --><rect width="10" height="10"/>'),
        False,
        "an `=`-based decorative comment is ugly but legal XML — validate does not (and cannot) "
        "reject it as malformed; it's the authoring rule's job to discourage it",
    ),
    (
        "clean_single_hyphen_comment_ok",
        _svg('<!-- input-output flow --><rect width="10" height="10"/>'),
        False,
        "single hyphens inside a comment are perfectly legal and must pass",
    ),
    (
        "no_comment_ok",
        _svg('<rect width="10" height="10"/>'),
        False,
        "the baseline: a valid SVG with no comment passes clean",
    ),
]


def main() -> int:
    failures = 0
    for name, svg, expect_error, why in CASES:
        _repaired, _fixes, errors = validate(svg, tolerance=0.01)
        got_error = bool(errors)
        ok = got_error == expect_error
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:34} error={got_error} (want {expect_error})")
        if not ok:
            print(f"      the case: {why}")
            print(f"      errors:   {errors}")
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(CASES)} XML-comment validation tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
