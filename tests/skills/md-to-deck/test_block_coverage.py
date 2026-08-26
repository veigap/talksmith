#!/usr/bin/env python3
"""Regression tests for `audits/block_coverage.py`'s **source stage** — the half that compares
`final.md` against `slide-model.json` without a rendered deck.

Run:  python3 tests/skills/md-to-deck/test_block_coverage.py

## Why this file exists

Every bug this stage has had was the same bug at a different layer: reading a source slide as if
every template were a body-plus-asides slide.

  * It matched slides by title — and `quote`, `big-number`, `image-grid`, `quiz` and `callout`
    have no title field, so every slide of those templates came back `[unmatched]`, permanently,
    in the one line where a genuinely lost slide would show.
  * Then it counted a `quote` slide's blockquote as a callout — the blockquote *is* the slide, it
    lands in the `quote` field, and a `quote` template offers no callout slot, so every correctly
    filled quote slide reported a drop.

A false positive that fires on every deck is worse than no audit: it trains the reader to skim
past the line that matters. So each case below pairs a shape that must stay silent with the real
defect it could mask.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "skills" / "md-to-deck" / "audits" / "block_coverage.py"

HEAD = """---
presentation: Prueba
---

# 1. Sección

---
"""

QUOTE_SLIDE = """
## 1. Qué es un MLP

### Content

> **Multi-Layer Perceptron**, o perceptrón multicapa: capas de neuronas donde cada una ve todas
> las salidas de la anterior.

---
"""

ASIDE_SLIDE = """
## 2. Una slide con aside de verdad

### Content

Texto de cuerpo cualquiera que ocupa la diapositiva entera sin ningún problema.

> **Ojo** Esta sí es una acotación al margen y el modelo debería alojarla en algún lado.

---
"""

NOTES_ONLY_QUOTE = """
## 3. Una slide común

### Content

Una línea de cuerpo que alcanza para identificar la diapositiva por su texto.

### Speaker notes

> **Nota al pie** Una cita dentro de las notas no es un bloque que la diapositiva deba mostrar.

---
"""

MODEL_QUOTE = {
    "template": "quote",
    "section": "Sección",
    "quote": "**Multi-Layer Perceptron**, o perceptrón multicapa: capas de neuronas donde cada "
             "una ve todas las salidas de la anterior.",
}
MODEL_ASIDE_HELD = {
    "template": "content-text",
    "title": "Una slide con aside de verdad",
    "big": "Texto",
    "panels": ["Texto de cuerpo cualquiera que ocupa la diapositiva entera sin ningún problema."],
    "highlights": [{"kind": "note",
                    "text": "Esta sí es una acotación al margen y el modelo debería alojarla."}],
}
MODEL_ASIDE_LOST = {k: v for k, v in MODEL_ASIDE_HELD.items() if k != "highlights"}
MODEL_PLAIN = {
    "template": "content-text",
    "title": "Una slide común",
    "big": "Una línea",
    "panels": ["Una línea de cuerpo que alcanza para identificar la diapositiva por su texto."],
}


def _model(*slides):
    return {"deck": {"title": "Prueba", "sections": ["Sección"]}, "slides": list(slides)}


# (name, source, model, want_exit, why, must_not_say)
CASES = [
    ("quote-block-is-the-slide",
     HEAD + QUOTE_SLIDE, _model(MODEL_QUOTE),
     0, "a `quote` slide's blockquote lands in the `quote` field, not in a callout slot — "
        "counting it as an aside reports a drop on every correctly filled quote slide",
     "block-drop"),
    ("quote-slide-is-addressable",
     HEAD + QUOTE_SLIDE, _model(MODEL_QUOTE),
     0, "`quote` carries no `title`; without a text fallback the slide is unmatchable and every "
        "deck with a pull-quote reports `[unmatched]` forever",
     "unmatched"),
    ("real-aside-still-caught",
     HEAD + ASIDE_SLIDE, _model(MODEL_ASIDE_LOST),
     1, "the capability the two silences must not cost: an authored aside with nowhere to land "
        "in the model is a genuine drop",
     ""),
    ("aside-held-in-highlights",
     HEAD + ASIDE_SLIDE, _model(MODEL_ASIDE_HELD),
     0, "the schema lets an aside land in `highlights` as well as in a `callout` — both count",
     "block-drop"),
    ("quote-inside-speaker-notes",
     HEAD + NOTES_ONLY_QUOTE, _model(MODEL_PLAIN),
     0, "a quote in the notes is prose the presenter says, not a block the slide owes the room",
     "block-drop"),
    ("meta-blocks-are-not-slides",
     HEAD.replace("# 1. Sección", "# Agenda\n\n> **Arco** Una nota de trabajo que no es "
                                 "diapositiva.\n\n---\n\n# 1. Sección")
     + NOTES_ONLY_QUOTE, _model(MODEL_PLAIN),
     0, "the agenda block and a section goal live under an `#` heading and are working meta; "
        "the deck builds its agenda from its section list",
     "block-drop"),
]


def run(source: str, model: dict, tmp: Path) -> tuple[int, str]:
    (tmp / "final.md").write_text(source, encoding="utf-8")
    (tmp / "slide-model.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(AUDIT), str(tmp / "slide-model.json"),
         "--source", str(tmp / "final.md")],
        capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, source, model, want, why, not_says in CASES:
            got, out = run(source, model, tmp)
            ok = got == want
            if ok and not_says and not_says in out:
                ok, why = False, f"{why} — report must NOT mention {not_says!r}"
            verb = "flag" if want == 1 else "pass"
            print(f"{'PASS' if ok else 'FAIL'}  {name:26} must {verb} · exit {got} (want {want})")
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
