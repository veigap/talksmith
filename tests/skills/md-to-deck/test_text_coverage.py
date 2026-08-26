#!/usr/bin/env python3
"""Regression tests for `audits/text_coverage.py` — source lines that MUST be reported as
dropped, and lines that must not be.

Run:  python3 tests/skills/md-to-deck/test_text_coverage.py

## Why this file exists

The audit exists because a real deck shipped with 37 live sentences of `final.md` absent from
`slide-model.json` — among them the one line saying whether a formula's Σ ran over examples or
over output units. The deck rendered, every audit was green, and the presenter read the slide
wrong.

The two failure modes pull in opposite directions and both are fatal to the audit's usefulness:
*miss a drop* and it is indistinguishable from no audit at all; *flag a line the fill legitimately
decomposed* (a sentence split across a card's `label` and `body`, a list marker consumed, a
separator dropped) and the report becomes noise a presenter learns to skip. So the cases below
come in pairs — the same content, once genuinely dropped and once merely restructured.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "skills" / "md-to-deck" / "audits" / "text_coverage.py"

SRC = """---
presentation: Prueba
---

# 1. Sección

---

## 3. El número que hay que derivar

### Content

La red produce una salida y la comparamos con el objetivo. `y` es lo que la red
predijo y `t` el objetivo. La suma recorre todas las unidades de salida.

- **Error** La diferencia entre lo predicho y lo esperado.

```python
codigo_que_no_se_audita = "las llaves son el contenido"
```

<!-- template: content-text -->

### Sources

- Bishop 2006, capítulo cinco, una fuente que nadie renderiza jamás.

### Speaker notes

Acá conviene aclarar que la sumatoria no corre sobre ejemplos.

---

# Cut material

Esto está cortado y no debe auditarse jamás bajo ninguna circunstancia.
"""

# Every load-bearing line of SRC, faithfully decomposed the way FILL is supposed to.
FAITHFUL = {
    "deck": {"title": "Prueba", "sections": ["Sección"]},
    "slides": [{
        "template": "content-text",
        "title": "El número que hay que derivar",
        "section": "Sección",
        "panels": [
            {"body": "La red produce una salida y la comparamos con el objetivo."},
            {"body": "`y` es lo que la red predijo y `t` el objetivo."},
            {"body": "La suma recorre todas las unidades de salida."},
            {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado."},
        ],
        "notes": "Acá conviene aclarar que la sumatoria no corre sobre ejemplos.",
    }],
}


def _variant(**changes):
    """FAITHFUL with one slide-level field replaced."""
    m = json.loads(json.dumps(FAITHFUL))
    m["slides"][0].update(changes)
    return m


# (name, source, model, want_exit_strict, why)
CASES = [
    # ---- must be flagged (exit 1 under --strict) ----------------------
    ("clause-dropped",
     SRC,
     _variant(panels=FAITHFUL["slides"][0]["panels"][:1]
              + FAITHFUL["slides"][0]["panels"][3:]),
     1, "the production defect: the two clauses that disambiguate the formula never reach a field"),
    ("notes-dropped",
     SRC,
     _variant(notes=""),
     1, "notes are lifted verbatim; an empty `notes` is a dropped block, not a shorter one"),
    ("whole-slide-dropped",
     SRC,
     {"deck": FAITHFUL["deck"], "slides": []},
     1, "a slide that vanished entirely must report, not pass for lack of anything to compare"),
    ("alibi-in-_choice",
     SRC,
     _variant(panels=FAITHFUL["slides"][0]["panels"][:1] + FAITHFUL["slides"][0]["panels"][3:],
              _choice={"signals": "La suma recorre todas las unidades de salida."}),
     1, "`_choice` quotes the source; counting it would let the trace alibi the drop it caused"),

    # ---- must NOT be flagged (exit 0) ---------------------------------
    ("faithful",
     SRC, FAITHFUL,
     0, "the control: nothing dropped, so nothing may be reported"),
    ("decomposed-across-fields",
     SRC,
     _variant(panels=[
         {"body": "La red produce una salida y la comparamos con el objetivo. "
                  "`y` es lo que la red predijo y `t` el objetivo."},
         {"body": "La suma recorre todas las unidades de salida."},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado."}],
     ),
     0, "regrouping lines across fields is what FILL is FOR — never a drop"),
    ("marks-and-markers-normalized",
     SRC,
     _variant(panels=[
         {"body": "La red produce una salida y la comparamos con el objetivo."},
         {"body": "y es lo que la red predijo y t el objetivo"},
         {"body": "**La suma** recorre *todas* las unidades de salida"},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado"}],
     ),
     0, "inline marks and punctuation differ on the two sides; matching must see through them"),
    ("waived-explicitly",
     SRC.replace("### Sources", "<!-- deck-omit-text: La suma recorre -->\n\n### Sources"),
     _variant(panels=FAITHFUL["slides"][0]["panels"][:2]
              + FAITHFUL["slides"][0]["panels"][3:]),
     0, "an author who waives a line in writing has answered the audit"),
]


def run(source: str, model: dict, tmp: Path) -> tuple[int, str]:
    (tmp / "final.md").write_text(source, encoding="utf-8")
    (tmp / "slide-model.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(AUDIT), str(tmp / "final.md"), str(tmp / "slide-model.json"),
         "--strict"],
        capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, source, model, want, why in CASES:
            got, out = run(source, model, tmp)
            ok = got == want
            verb = "flag" if want == 1 else "pass"
            print(f"{'PASS' if ok else 'FAIL'}  {name:28} must {verb} · exit {got} (want {want})")
            if not ok:
                failures += 1
                print(f"      stands for: {why}")
                for ln in out.splitlines()[-4:]:
                    print(f"      audit said: {ln}")
    if failures:
        print(f"\n{failures} regression(s) FAILED — the audit has lost a capability.")
        return 1
    print(f"\nall {len(CASES)} audit regressions pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
