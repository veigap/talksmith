#!/usr/bin/env python3
"""Tests for the monospace-resolution guard in `rasterize.py`.

**The case that matters is `unresolved_family_is_detected`.** cairo does not walk a CSS font
stack: given `font-family="'DejaVu Sans Mono', monospace"` on a machine without DejaVu it takes
the first name literally, fails to find it, and falls back to its own default *sans* — silently.
A whole deck of diagrams once shipped with every code block, table and token trace set in
proportional type; the SVG was valid, the PNG was written, the aspect audit passed, and the only
way it was ever found was an illustrator measuring glyph widths by hand.

The measurement here is the same one `renders_monospaced` makes: a run of the narrowest glyph and
a run of the widest span the same distance in a monospaced face and wildly different distances in
a proportional one.

Run:  python3 tests/skills/ascii-to-svg/test_mono_font.py
      (the probes need cairosvg; without it they report SKIP and the parsing tests still run)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "ascii-to-svg"))
from rasterize import (  # noqa: E402
    _declared_mono_stacks,
    _load_cairosvg,
    renders_monospaced,
    resolve_mono_family,
)

_FAILURES = 0


def _report(name: str, ok: bool, detail: str = "") -> None:
    global _FAILURES
    if not ok:
        _FAILURES += 1
    print(f"{'PASS' if ok else 'FAIL'}  {name:38} {detail}")


def _skip(name: str, why: str) -> None:
    print(f"SKIP  {name:38} {why}")


# ── what the SVG asks for ────────────────────────────────────────────────────────────────
# Only a stack that *names* a family can silently fall back; bare `monospace` is the generic and
# always resolves to something monospaced, so it is not worth probing or warning about.
_STACK_CASES = [
    ("named_mono_stack", '<text font-family="\'Andale Mono\', monospace">x</text>', ["Andale Mono"]),
    ("bare_generic_ignored", '<text font-family="monospace">x</text>', []),
    ("sans_stack_ignored", '<text font-family="Helvetica, Arial, sans-serif">x</text>', []),
    ("deduped_in_order",
     '<svg font-family="\'A Mono\', monospace">'
     '<text font-family="\'A Mono\', monospace">x</text>'
     '<tspan font-family="\'B Mono\', monospace">y</tspan></svg>',
     ["A Mono", "B Mono"]),
]

for name, svg, want in _STACK_CASES:
    got = _declared_mono_stacks(svg)
    _report(name, got == want, f"{got} (want {want})")


# ── what the renderer actually draws ─────────────────────────────────────────────────────
mod = _load_cairosvg()
if mod is None:
    _skip("proportional_face_is_not_mono", "cairosvg unavailable")
    _skip("unresolved_family_is_detected", "cairosvg unavailable")
    _skip("a_mono_family_resolves", "cairosvg unavailable")
else:
    # Helvetica is proportional wherever it resolves, and where it doesn't, cairo's default
    # fallback is proportional too — so this answers False on any machine.
    _report("proportional_face_is_not_mono", renders_monospaced(mod, "Helvetica") is False)

    # A family that cannot exist must read exactly like the proportional case above: that identity
    # IS the bug — an absent family is indistinguishable from asking for a sans one.
    _report("unresolved_family_is_detected",
            renders_monospaced(mod, "NoSuchFontXYZ Mono") is False)

    # The generic never fails, so at least one candidate must always be found. A machine where
    # this fails cannot draw a legible diagram at all, which is what `--check` refuses to start on.
    fam = resolve_mono_family(mod)
    _report("a_mono_family_resolves", fam is not None and renders_monospaced(mod, fam) is True,
            f"resolved {fam!r}")


print()
if _FAILURES:
    print(f"{_FAILURES} test(s) FAILED.")
    sys.exit(1)
print("all mono-font tests pass.")
