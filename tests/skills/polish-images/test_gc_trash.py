#!/usr/bin/env python3
"""Tests for `polish_images gc` — the aside twin of `polish_ascii gc`.

Run:  python3 tests/skills/polish-images/test_gc_trash.py

`gc --apply` used to `unlink()` orphaned asides. The orphan test is "no image ref in final.md", and a
renumbering pass rewrites exactly that file, so a generation that was orphaned for one pass was gone
for good. Both skills now share one `run_gc` (in `skills/_shared/_plan.py`) that moves the set into
`images/.trash/<timestamp>/` instead; this pins the aside side of it.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "skills" / "polish-images" / "scripts"))
from polish_images import STAMP_SUFFIX, main  # noqa: E402


def _run(*argv: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(list(argv))


def run() -> int:
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")

    with tempfile.TemporaryDirectory() as td:
        talk = Path(td)
        images = talk / "images"
        images.mkdir()
        final = talk / "final.md"
        final.write_text("# 1. S\n\n## 1. Slide\n\n<!-- aside: right ![x](images/s1-1-1-aside.png) -->\n")
        for stem in ("s1-1-1-aside", "s2-1-1-aside"):
            (images / f"{stem}.png").write_bytes(b"\x89PNG")
            (images / f"{stem}.imgprompt").write_text("description: x\n")
            (images / f"{stem}{STAMP_SUFFIX}").write_text("0" * 64 + "\n")
        (images / "foto.png").write_bytes(b"\x89PNG presenter")

        print("gc:")
        _run("gc", "--final", str(final))
        check("dry-run touches nothing", (images / "s2-1-1-aside.png").exists())
        code = _run("gc", "--final", str(final), "--apply")
        trash = list((images / ".trash").glob("*"))
        moved = sorted(p.name for p in trash[0].iterdir()) if trash else []
        check("--apply moves the orphan triplet into images/.trash/<timestamp>/",
              code == 0 and len(trash) == 1
              and moved == sorted(["s2-1-1-aside.png", "s2-1-1-aside.imgprompt", f"s2-1-1-aside{STAMP_SUFFIX}"]),
              str(moved))
        check("referenced aside and presenter image untouched",
              (images / "s1-1-1-aside.png").exists() and (images / "foto.png").exists())
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print("all polish-images gc tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
