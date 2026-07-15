#!/usr/bin/env python3
"""Regression tests for `audit_aspect.py` — inputs that MUST be flagged, and must not be.

Run:  python3 tests/skills/ascii-to-svg/test_audit_aspect.py

## Why this file exists

The nine rendered fixtures in `images/` all pass the audit. That is the *right* outcome —
they're good renders — but it means they verify nothing about the audit itself. A check
that only ever sees healthy inputs is indistinguishable from a check that always returns
ok, and that is not a hypothetical: this audit shipped with a bug that made it return
`ok: full-bleed` for *every* diagram carrying a full-canvas tinted background, and the
fixture suite was green throughout, because it hard-coded white as the background colour
instead of measuring it.

So the cases below are synthetic and deliberately broken. Each one names the defect it
stands for. If a case stops failing, the audit has lost a capability — that is the signal
this file exists to produce.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RASTERIZE = ROOT / "skills" / "ascii-to-svg" / "rasterize.py"
AUDIT = ROOT / "skills" / "ascii-to-svg" / "audit_aspect.py"

# A thin strip of art marooned in a tall canvas: viewBox says 1.78:1, the ink says ~9:1.
# This is the production defect — declared 2.30:1 around art that wanted 2.91:1 — in
# miniature. A PNG cannot reveal it (it rasterizes *from* the viewBox), so only this
# mechanical check stands between it and the PPTX build.
_MAROONED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="{bg}"/>
  <rect x="40" y="150" width="140" height="60" fill="#DA1B2E"/>
  <rect x="250" y="150" width="140" height="60" fill="#DA1B2E"/>
  <rect x="460" y="150" width="140" height="60" fill="#DA1B2E"/>
</svg>"""

# Art that fills its frame evenly. The audit must stay quiet here or it is a nuisance.
_WELL_FRAMED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200">
  <rect width="640" height="200" fill="{bg}"/>
  <rect x="30" y="30" width="180" height="140" fill="#DA1B2E"/>
  <rect x="230" y="30" width="180" height="140" fill="#DA1B2E"/>
  <rect x="430" y="30" width="180" height="140" fill="#DA1B2E"/>
</svg>"""

# Off-centre on one axis: even top/bottom, but the art hugs the right edge.
_OFF_CENTRE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200">
  <rect width="640" height="200" fill="{bg}"/>
  <rect x="380" y="30" width="230" height="140" fill="#DA1B2E"/>
</svg>"""

CASES = [
    # (name, template, background, expected_exit, what it stands for)
    ("marooned-art/white-bg", _MAROONED, "#FFFFFF", 1,
     "the production defect: viewBox far taller than the art it frames"),
    ("marooned-art/tinted-bg", _MAROONED, "#F2EEEE", 1,
     "same defect behind a tinted full-canvas rect — the bug that blinded this audit: "
     "assuming white made every pixel count as ink, so it reported 'full-bleed' and exit 0"),
    ("marooned-art/dark-bg", _MAROONED, "#3B3535", 1,
     "same defect behind a dark full-canvas rect"),
    ("well-framed/white-bg", _WELL_FRAMED, "#FFFFFF", 0,
     "healthy art in an even frame must not be flagged"),
    ("well-framed/tinted-bg", _WELL_FRAMED, "#F2EEEE", 0,
     "background colour must not change the verdict for healthy art"),
    ("off-centre/white-bg", _OFF_CENTRE, "#FFFFFF", 1,
     "art shoved against one edge — even margins on the other axis must not excuse it"),
]


def run(tmp: Path, name: str, tpl: str, bg: str) -> tuple[int, str]:
    svg = tmp / (name.replace("/", "_") + ".svg")
    png = svg.with_suffix(".png")
    svg.write_text(tpl.format(bg=bg))
    r = subprocess.run([sys.executable, str(RASTERIZE), str(svg), "-o", str(png), "--width", "1200"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return -1, f"rasterize failed: {r.stderr.strip()[:200]}"
    r = subprocess.run([sys.executable, str(AUDIT), str(svg), "--png", str(png)],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[0]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, tpl, bg, want, why in CASES:
            got, line = run(tmp, name, tpl, bg)
            ok = got == want
            failures += not ok
            verb = "flag" if want == 1 else "pass"
            print(f"{'PASS' if ok else 'FAIL'}  {name:26} must {verb} · exit {got} (want {want})")
            if not ok:
                print(f"      stands for: {why}")
                print(f"      audit said: {line}")
    print()
    if failures:
        print(f"{failures} regression(s) FAILED — the audit has lost a capability.")
        return 1
    print(f"all {len(CASES)} audit regressions pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
