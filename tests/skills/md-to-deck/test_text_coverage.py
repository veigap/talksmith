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

# Thesis

La tesis de la charla es una línea de trabajo que ninguna diapositiva renderiza jamás.

---

# Agenda

**Sections (in delivery order):**

- 1. Sección

---

# 1. Sección

**Goal of this section:** que el alumno entienda de dónde sale el gradiente.

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

Acá conviene aclarar que la sumatoria no corre sobre ejemplos. Por qué media
armónica y no promedio: la armónica tiende al más chico de los dos.

---

## 4. Una cita sin título

> El objetivo no es memorizar la fórmula sino saber qué se está derivando.

— Alguien, 2026

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
        "notes": "Acá conviene aclarar que la sumatoria no corre sobre ejemplos. "
                 "Por qué media armónica y no promedio: la armónica tiende al más chico "
                 "de los dos.",
    }, {
        # `quote` has NO `title` field in the schema — this slide is unaddressable by title, and
        # a title-only match reports it missing every single time.
        "template": "quote",
        "section": "Sección",
        "quote": "El objetivo no es memorizar la fórmula sino saber qué se está derivando.",
        "attribution": "Alguien, 2026",
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
     1, "the production defect: the two clauses that disambiguate the formula never reach a field",
     (), "", ""),
    ("notes-dropped",
     SRC,
     _variant(notes=""),
     1, "notes are lifted verbatim; an empty `notes` is a dropped block, not a shorter one",
     (), "", ""),
    ("whole-slide-dropped",
     SRC,
     {"deck": FAITHFUL["deck"], "slides": []},
     1, "a slide that vanished entirely must report, not pass for lack of anything to compare",
     (), "slide-missing", ""),
    ("alibi-in-_choice",
     SRC,
     _variant(panels=FAITHFUL["slides"][0]["panels"][:1] + FAITHFUL["slides"][0]["panels"][3:],
              _choice={"signals": "La suma recorre todas las unidades de salida."}),
     1, "`_choice` quotes the source; counting it would let the trace alibi the drop it caused",
     (), "", ""),

    # ---- must NOT be flagged (exit 0) ---------------------------------
    ("faithful",
     SRC, FAITHFUL,
     0, "the control: nothing dropped, so nothing may be reported",
     (), "", "text-drop"),
    ("decomposed-across-fields",
     SRC,
     _variant(panels=[
         {"body": "La red produce una salida y la comparamos con el objetivo. "
                  "`y` es lo que la red predijo y `t` el objetivo."},
         {"body": "La suma recorre todas las unidades de salida."},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado."}],
     ),
     0, "regrouping lines across fields is what FILL is FOR — never a drop",
     (), "", "text-drop"),
    ("marks-and-markers-normalized",
     SRC,
     _variant(panels=[
         {"body": "La red produce una salida y la comparamos con el objetivo."},
         {"body": "y es lo que la red predijo y t el objetivo"},
         {"body": "**La suma** recorre *todas* las unidades de salida"},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado"}],
     ),
     0, "inline marks and punctuation differ on the two sides; matching must see through them",
     (), "", "text-drop"),
    ("waived-explicitly",
     SRC.replace("### Sources", "<!-- deck-omit-text: La suma recorre -->\n\n### Sources"),
     _variant(panels=FAITHFUL["slides"][0]["panels"][:2]
              + FAITHFUL["slides"][0]["panels"][3:]),
     0, "an author who waives a line in writing has answered the audit",
     (), "", "text-drop"),
    ("quote-slide-has-no-title",
     SRC, FAITHFUL,
     0, "`quote` carries no `title` field; matching a slide by title alone reports every one of "
        "them missing — a false positive that discredits the whole report",
     (), "", "slide-missing"),
    ("meta-blocks-are-not-slides",
     SRC, FAITHFUL,
     0, "the thesis claim, the agenda arc and a section goal are working meta under an `#` "
        "heading — the deck builds its agenda from `deck.sections` and renders none of them",
     (), "", "tesis de la charla"),
    ("rewritten-not-dropped",
     SRC,
     _variant(panels=[
         {"label": "Salida vs objetivo",
          "body": "comparamos la salida que produce la red con el objetivo"},
         {"label": "y", "body": "lo que la red predijo"},
         {"label": "t", "body": "el objetivo"},
         {"label": "Σ", "body": "recorre las unidades de salida, todas"},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado."}]),
     0, "verified in production: two prose bullets became a comparison table, every word moved, "
        "nothing lost — a literal matcher calls that a drop and the report becomes noise",
     (), "restructured", "text-drop"),
    ("rewrites-are-listable",
     SRC,
     _variant(panels=[
         {"label": "Salida vs objetivo",
          "body": "comparamos la salida que produce la red con el objetivo"},
         {"label": "y", "body": "lo que la red predijo"},
         {"label": "t", "body": "el objetivo"},
         {"label": "Σ", "body": "recorre las unidades de salida, todas"},
         {"label": "Error", "body": "La diferencia entre lo predicho y lo esperado."}]),
     0, "downgraded is not discarded — an author who wants to check the rewrites must be able to",
     ("--show-rewrites",), "text-rewritten", ""),
    ("notes-paraphrase-is-a-drop",
     SRC,
     _variant(notes="Acá conviene aclarar que la sumatoria no corre sobre ejemplos."),
     1, "the production defect: notes were summarized, and the sentence answering the question "
        "the note itself poses was cut. Notes are copied verbatim, so the rewrite tier must "
        "never apply to them however many of their words survive elsewhere",
     ("--strict-notes",), "notes", ""),
    ("strict-notes-ignores-body",
     SRC,
     _variant(panels=FAITHFUL["slides"][0]["panels"][:1]
              + FAITHFUL["slides"][0]["panels"][3:]),
     0, "--strict-notes gates on the unambiguous half only; a dropped body line still reports "
        "but must not fail the build",
     ("--strict-notes",), "text-drop", ""),
]


def run(source: str, model: dict, tmp: Path, argv: tuple = ()) -> tuple[int, str]:
    (tmp / "final.md").write_text(source, encoding="utf-8")
    (tmp / "slide-model.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(AUDIT), str(tmp / "final.md"), str(tmp / "slide-model.json"),
         *(argv or ("--strict",))],
        capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, source, model, want, why, argv, says, not_says in CASES:
            got, out = run(source, model, tmp, argv)
            ok = got == want
            if ok and says and says not in out:
                ok, why = False, f"{why} — report must mention {says!r}"
            if ok and not_says and not_says in out:
                ok, why = False, f"{why} — report must NOT mention {not_says!r}"
            verb = "flag" if want == 1 else "pass"
            print(f"{'PASS' if ok else 'FAIL'}  {name:28} must {verb} · exit {got} (want {want})")
            if not ok:
                failures += 1
                print(f"      stands for: {why}")
                for ln in out.splitlines()[-6:]:
                    print(f"      audit said: {ln}")
    if failures:
        print(f"\n{failures} regression(s) FAILED — the audit has lost a capability.")
        return 1
    print(f"\nall {len(CASES)} audit regressions pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
