#!/usr/bin/env python3
"""Tests for the animated sibling — `<stem>.anim.svg` beside an untouched base `<stem>.svg`.

Run:  python3 tests/skills/polish-ascii/test_anim_sibling.py

`animate-svg` never edits the base: it writes the animated version beside it, and the slide points
at the animated one. Four pieces of the pipeline have to agree on that, and each one failing has a
concrete cost:

- **`cleanup` points the slide at the animated version** when one exists — or the deck shows the
  still and the animation was made for nothing.
- **`gc` keeps the base alive** when final.md names only the animated version — or the approved
  still is swept to the trash — and retires the animated version together with its base.
- **Reuse never takes an animated file for a render** — or a renumbered slide gets an animation
  copied in as its base drawing.
- **The deck upgrades `<stem>.anim.png` to its SVG** — or the animated slide ships as a raster
  that cannot move.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(_ROOT / "skills" / "_shared"))
sys.path.insert(0, str(_ROOT / "skills" / "md-to-deck" / "scripts"))
from test_render_reuse import _DIAGRAM, _check, _plan, _render, _run  # noqa: E402
import test_render_reuse as base  # noqa: E402
from _plan import referenced_stems  # noqa: E402
from html_style import _vector_twin  # noqa: E402

STEM = "s1-1-1-entrada-modelo"
ANIM_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" class="ts-anim-x"><title>t</title>'
            '<style>/* talksmith-animation */\n.ts-anim-x *{}</style><rect/></svg>\n')


def _talk(tmp: Path) -> tuple[Path, Path, Path]:
    talk = tmp / "talk"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(f"# 1. Sección\n\n## 1. Slide\n\n{_DIAGRAM}")
    return talk, images, final


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        talk, images, final = _talk(Path(d))
        ann = _plan(talk, {"s1-1-1": f"{STEM}.svg"})
        _render(images, STEM)
        _run("stamp-renders", "--final", str(final), "--plan", str(ann))
        (images / f"{STEM}.anim.svg").write_text(ANIM_SVG)
        (images / f"{STEM}.anim.png").write_bytes(b"\x89PNG anim")
        base_before = (images / f"{STEM}.svg").read_text()

        _run("cleanup", "--final", str(final), "--plan", str(ann))
        text = final.read_text()
        _check("cleanup: the slide points at the animated version",
               f"images/{STEM}.anim.svg" in text and f"images/{STEM}.svg)" not in text, text[:200])
        _check("cleanup: the base is left untouched", (images / f"{STEM}.svg").read_text() == base_before)

        _check("live set: a ref to <stem>.anim keeps <stem> alive",
               {STEM, f"{STEM}.anim"} <= referenced_stems(text))
        code, out = _run("gc", "--final", str(final))
        _check("gc: nothing orphaned while the animated version is referenced", code == 0)
        _run("gc", "--final", str(final), "--apply")
        _check("gc: base and animated version both survive",
               (images / f"{STEM}.svg").exists() and (images / f"{STEM}.anim.svg").exists())

        # Retire the slide: the base and its animated version go to the trash together.
        final.write_text("# 1. Sección\n\n## 1. Slide\n\nSin diagrama.\n")
        _run("gc", "--final", str(final), "--apply")
        _check("gc: an orphaned base takes its animated version with it",
               not (images / f"{STEM}.svg").exists() and not (images / f"{STEM}.anim.svg").exists()
               and not (images / f"{STEM}.anim.png").exists())

    with tempfile.TemporaryDirectory() as d:
        talk, images, final = _talk(Path(d))
        ann = _plan(talk, {"s1-1-1": f"{STEM}.svg"})
        _render(images, STEM)
        _run("stamp-renders", "--final", str(final), "--plan", str(ann))
        # An animated copy that kept the base's stamp must still never act as a donor render.
        (images / f"{STEM}.anim.svg").write_text((images / f"{STEM}.svg").read_text().replace("<rect/>", "<circle/>"))
        (images / f"{STEM}.svg").unlink()
        ann = _plan(talk, {"s1-1-1": f"{STEM}.svg"})
        args = Path(d) / "args"
        _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
        _check("reuse: an animated file is never copied in as the base render",
               (args / "s1-1-1.json").exists() and not (images / f"{STEM}.svg").exists())

    with tempfile.TemporaryDirectory() as d:
        images = Path(d)
        (images / "x.anim.svg").write_text(ANIM_SVG)
        (images / "x.anim.png").write_bytes(b"\x89PNG")
        (images / "chart.anim.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (images / "chart.anim.png").write_bytes(b"\x89PNG")
        _check("deck: <stem>.anim.png upgrades to its animated SVG",
               _vector_twin(images / "x.anim.png") == images / "x.anim.svg")
        _check("deck: an unproven .anim twin is not swapped in",
               _vector_twin(images / "chart.anim.png") is None)

    print()
    if base.failures:
        print(f"{base.failures} check(s) FAILED.")
        return 1
    print("all animated-sibling checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
