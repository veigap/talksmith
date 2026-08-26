#!/usr/bin/env python3
"""Regression test for the coverage pass **built into the render** (`build_html._coverage_warn`).

Run:  python3 tests/skills/md-to-deck/test_render_coverage.py

## Why this file exists

The three coverage audits had tests. Their call site inside the renderer did not — and that is
where they broke. Recalibrating the audits changed two signatures (`model_notes` began returning
its slide index alongside the model; `reconcile_source` began taking it), every caller inside the
audits was updated, and the one in `build_html.py` was missed. The `except Exception` wrapping it
turned the `TypeError` into a warning that read like the icon warnings printed beside it, so the
render kept succeeding and the safety net was simply down — through two releases, on every deck,
saying nothing anyone would read as "broken".

So this file asserts the two things the audits' own tests cannot: that the renderer's call site
still *matches* their signatures, and that a genuine drop reaches the render's output. A test that
only checked "does the render succeed" would have passed throughout the outage — the point is to
fail when the check goes quiet.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "md-to-deck"))

SRC = """---
presentation: Prueba
---

# 1. Sección

---

## 1. El número que hay que derivar

### Content

La red produce una salida y la comparamos con el objetivo. La suma recorre todas
las unidades de salida.

### Speaker notes

Acá conviene aclarar que la sumatoria no corre sobre ejemplos.
"""

FAITHFUL = {
    "deck": {"title": "Prueba", "sections": ["Sección"]},
    "slides": [{
        "template": "content-text",
        "title": "El número que hay que derivar",
        "section": "Sección",
        "big": "La red produce una salida",
        "panels": ["La red produce una salida y la comparamos con el objetivo.",
                   "La suma recorre todas las unidades de salida."],
        "notes": "Acá conviene aclarar que la sumatoria no corre sobre ejemplos.",
    }],
}


def _dropped():
    m = json.loads(json.dumps(FAITHFUL))
    m["slides"][0]["panels"] = m["slides"][0]["panels"][:1]
    m["slides"][0]["notes"] = ""
    return m


def run(model: dict, tmp: Path) -> str:
    import build_html                                   # noqa: PLC0415  (needs jinja2)
    talk = tmp / "talk"
    (talk / "output").mkdir(parents=True, exist_ok=True)
    (talk / "final.md").write_text(SRC, encoding="utf-8")
    mp = talk / "output" / "slide-model.json"
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    err, out = io.StringIO(), io.StringIO()
    with redirect_stderr(err), redirect_stdout(out):
        build_html._coverage_warn(model, mp, talk / "final.md")
    return (err.getvalue() + out.getvalue()).strip()


# (name, model, must_say, must_not_say, why)
CASES = [
    ("signatures-still-match", FAITHFUL, "coverage: ok", "BUG:",
     "the outage itself: the renderer called the audits with signatures that had moved on, and "
     "the failure surfaced as a skipped-check warning nobody reads"),
    ("check-actually-ran", FAITHFUL, "coverage: ok", "skipped",
     "'skipped' is how a broken check looks from outside — a passing render is not evidence the "
     "check ran"),
    ("drop-reaches-the-render", _dropped(), "text-drop", "coverage: ok",
     "the capability the whole pass exists for: a line and a notes block dropped by FILL must be "
     "named in the render's own output, for the presenter who never runs the audits by hand"),
    ("notes-counted-apart", _dropped(), "speaker-notes line", "",
     "notes are copied verbatim, so they are reported and counted separately from body prose"),
]


def main() -> int:
    try:
        import build_html  # noqa: F401,PLC0415
    except ImportError as e:
        print(f"SKIP — build_html is not importable here ({e}); it needs jinja2, as the render "
              f"itself does.")
        return 0

    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, model, says, not_says, why in CASES:
            out = run(model, tmp)
            ok = (says in out) and not (not_says and not_says in out)
            print(f"{'PASS' if ok else 'FAIL'}  {name:26} · must say {says!r}"
                  + (f", never {not_says!r}" if not_says else ""))
            if not ok:
                failures += 1
                print(f"      stands for: {why}")
                for ln in out.splitlines()[:4]:
                    print(f"      render said: {ln}")
    if failures:
        print(f"\n{failures} regression(s) FAILED — the render's coverage pass is not running.")
        return 1
    print(f"\nall {len(CASES)} render-coverage regressions pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
