#!/usr/bin/env python3
"""Regression tests for `audits/degenerate_enum.py` — models that MUST be
flagged, and models that must not be.

Run:  python3 tests/skills/md-to-deck/test_degenerate_enum.py

## Why this file exists

The audit exists because a real deck shipped a `content-text` slide with a
single panel — a punchline shrunk into a stray third-width grid cell — and
nothing caught it. A check that only ever sees healthy models is
indistinguishable from one that always returns ok, so the cases below are
synthetic: each broken one names the defect it stands for, and the healthy
ones guard against a floor set so high it flags legitimate two-item sets.
If a "must flag" case stops failing, the audit has lost a capability.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "skills" / "md-to-deck" / "audits" / "degenerate_enum.py"


def _slide(template, **fields):
    return {"template": template, "title": f"a {template} slide", **fields}


# (name, slides, want_exit, why)
CASES = [
    # ---- must be flagged (exit 1) -------------------------------------
    ("content-text-1-panel",
     [_slide("content-text", big="lead", panels=["the lone punchline"])],
     1, "the production defect: a punchline demoted into a single panel"),
    ("concept-breakdown-1-card",
     [_slide("concept-breakdown", cards=[{"label": "L", "body": "b"}])],
     1, "one card in a multi-card grid — should be single-point"),
    ("stat-1-stat",
     [_slide("stat", stats=[{"value": "42%", "caption": "c"}])],
     1, "a lone metric is a big-number slide, not a stat strip"),
    ("icon-list-1-row",
     [_slide("icon-list", rows=[{"label": "L", "body": "b"}])],
     1, "one row is a single-point, not an icon-list"),
    ("comparison-1-column",
     [_slide("comparison", columns=[{"header": "h"}])],
     1, "a one-column comparison compares nothing"),
    ("stat-missing-field",
     [_slide("stat")],
     1, "a stat with no stats array — missing field counts as zero"),

    # ---- must NOT be flagged (exit 0) ---------------------------------
    ("content-text-2-panels",
     [_slide("content-text", big="lead", panels=["one", "two"])],
     0, "two panels is a legitimate set — floor must not over-reach"),
    ("concept-breakdown-3-cards",
     [_slide("concept-breakdown",
             cards=[{"label": "a"}, {"label": "b"}, {"label": "c"}])],
     0, "a healthy three-card breakdown"),
    ("single-point-is-exempt",
     [_slide("single-point", point={"label": "L", "body": "b"})],
     0, "single-point owns the one-item case — never flag it"),
    ("content-image-is-exempt",
     [_slide("content-image", facts=[{"body": "one fact"}])],
     0, "non-enumeration templates are out of scope"),
]


def run(slides, tmp: Path) -> tuple[int, str]:
    model = tmp / "slide-model.json"
    model.write_text(json.dumps({"deck": {"title": "t"}, "slides": slides}),
                     encoding="utf-8")
    r = subprocess.run([sys.executable, str(AUDIT), str(model)],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, slides, want, why in CASES:
            got, out = run(slides, tmp)
            ok = got == want
            verb = "flag" if want == 1 else "pass"
            print(f"{'PASS' if ok else 'FAIL'}  {name:26} must {verb} · "
                  f"exit {got} (want {want})")
            if not ok:
                failures += 1
                print(f"      stands for: {why}")
                print(f"      audit said: {out.splitlines()[-1] if out else '(no output)'}")
    if failures:
        print(f"\n{failures} regression(s) FAILED — the audit has lost a capability.")
        return 1
    print(f"\nall {len(CASES)} audit regressions pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
