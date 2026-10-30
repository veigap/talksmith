#!/usr/bin/env python3
"""Tests for `feedback_cycle.py rescue-open` — the Step-6 (c) pass that saves `[open]` bullets.

Run:  python3 tests/skills/feedback-cycle/test_rescue_open.py

**The case that matters is the malformed bullet.** `rescue-open` matched only the canonical
`- [open] <date> — "<text>"` form, so a bullet with text after its closing quote was passed over
and the summary still said "0 skipped" — and Step 6 (d) then stripped it with the rest of the
feedback. A bullet that opens `- [open]` is an open question whatever its shape: it is rescued
verbatim and named.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_CLI = _ROOT / "skills" / "feedback-cycle" / "scripts" / "feedback_cycle.py"

_FINAL = '''# 1. Sección

## 1. Primer slide

### Content

- algo.

### Presenter feedback

- [open] 2026-10-01 — "¿cifra de 2025 o de 2026?"

---

## 2. Tabla de disponibilidad

### Content

- otra cosa.

### Presenter feedback

- [open] 2026-10-02 — "revisar la fila de Gemini" falta la fuente
---

## 3. Sin fecha

### Presenter feedback

- [open] sin fecha ni comillas
'''

failures = 0


def _check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")


def _rescue(final: Path) -> str:
    r = subprocess.run([sys.executable, str(_CLI), "rescue-open", "--final", str(final)],
                       capture_output=True, text=True, check=True)
    return r.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        final = Path(d) / "final.md"
        final.write_text(_FINAL)
        out = _rescue(final)
        text = final.read_text()
        oq = text.split("# Open questions", 1)[1] if "# Open questions" in text else ""
        _check("well-formed bullet is rescued quoted", '— "¿cifra de 2025 o de 2026?"' in oq, oq)
        _check("text after the closing quote is rescued verbatim",
               '— "revisar la fila de Gemini" falta la fuente' in oq, oq)
        _check("a bullet with no date or quotes is rescued", "— sin fecha ni comillas" in oq, oq)
        _check("the summary counts the malformed bullets", "2 malformed" in out, out)
        _check("each malformed bullet is named by line", out.count("malformed [open] bullet") == 2, out)

        before = final.read_text()
        out = _rescue(final)
        _check("a second run is idempotent", final.read_text() == before and "3 skipped" in out, out)

    print()
    if failures:
        print(f"{failures} check(s) FAILED.")
        return 1
    print("all rescue-open checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
