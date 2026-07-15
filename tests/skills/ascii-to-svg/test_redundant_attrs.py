#!/usr/bin/env python3
"""Tests for `validate_svg.redundant_inherited()` — the hoisting lint.

Run:  python3 tests/skills/ascii-to-svg/test_redundant_attrs.py

The lint backs `SKILL.md` step 5's rule: declare inheritable attributes once at the root,
override only the exception. The render step is output-token-bound, so redundant attributes
cost wall-clock directly — measured at 24.6% of file bytes across this repo's fixtures, with
0 differing pixels once hoisted.

**The case that matters is `nested_override_is_not_redundant`.** The obvious lint — count how
often `font-family` appears — is wrong, and wrong exactly where it hurts: a `<tspan>` carrying
the dominant family inside a `<text>` carrying a different one is *load-bearing*, because it
inherits from its parent rather than the root. A naive implementation of this optimisation
stripped that tspan in a real fixture and silently reverted an inline code span to the wrong
face — invisible in the XML, visible only in the pixels. Redundancy has to be resolved down
the tree, never counted flat.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "ascii-to-svg"))
from validate_svg import redundant_inherited  # noqa: E402

HELV = "Helvetica, Arial, sans-serif"
MONO = "'DejaVu Sans Mono', monospace"


def _svg(body: str, root_attrs: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" {root_attrs}>'
            f'{body}</svg>')


CASES = [
    (
        "flat_repetition_is_redundant",
        _svg("".join(f'<text font-family="{HELV}">t{i}</text>' for i in range(4)),
             f'font-family="{HELV}"'),
        4,
        "four <text> repeating the family the root already declares",
    ),
    (
        "no_root_declaration_is_still_hoistable",
        _svg("".join(f'<text font-family="{HELV}">t{i}</text>' for i in range(4))),
        4,
        "THE common case, and the one a 'does an ancestor already say this?' lint misses "
        "entirely: no root declaration, four children each restating the same family. Nothing "
        "is redundant in the strict sense, yet all four are avoidable — this is exactly what "
        "real renders do, so a lint that stays quiet here is decorative",
    ),
    (
        "nested_override_is_not_redundant",
        _svg(f'<text font-family="{HELV}">La '
             f'<tspan font-family="{MONO}" font-weight="bold">description</tspan>'
             f' decide cuándo</text>',
             f'font-family="{MONO}"'),
        0,
        "THE case: the tspan re-declares the root's own family, but its parent <text> is "
        "Helvetica — so the declaration is what keeps it monospace. Flagging it as redundant "
        "invites stripping it, which silently breaks the code span",
    ),
    (
        "nested_matching_parent_is_redundant",
        _svg(f'<text font-family="{MONO}">a<tspan font-family="{MONO}">b</tspan>'
             f'<tspan font-family="{MONO}">c</tspan><tspan font-family="{MONO}">d</tspan></text>',
             f'font-family="{MONO}"'),
        4,
        "text + three tspans all restating what the root already gives",
    ),
    (
        "group_and_its_children",
        _svg(f'<g font-family="{HELV}">'
             + "".join(f'<text font-family="{HELV}">t{i}</text>' for i in range(3))
             + "</g>"),
        4,
        "a <g> is a declaring ancestor like any other — and once the root carries the family, "
        "the <g>'s own declaration is droppable too, so it's 4 (the group + its 3 children), "
        "not 3",
    ),
]


def main() -> int:
    failures = 0
    for name, svg, want, why in CASES:
        found = redundant_inherited(svg)
        got = sum(n for attr, _, n, _ in found if attr == "font-family")
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:34} redundant={got} (want {want})")
        if not ok:
            print(f"      the case: {why}")
            print(f"      lint saw: {found}")
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(CASES)} redundancy tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
