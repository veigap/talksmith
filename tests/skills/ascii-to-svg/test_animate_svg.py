#!/usr/bin/env python3
"""Tests for `animate_svg` — beat tags in, scoped CSS animation out.

Run:  python3 tests/skills/ascii-to-svg/test_animate_svg.py

Backs the animation contract in `skills/ascii-to-svg/SKILL.md`: the renderer only tags beats,
the script owns the motion. The cases pin down the three things that matter downstream — the
still state stays the complete diagram (cairosvg, when this interpreter has it, must draw every
beat), a mis-tagged diagram is reported and left untouched, and a re-run is a no-op.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
SKILL = HERE.parents[3] / "skills" / "ascii-to-svg"
sys.path.insert(0, str(SKILL))
from animate_svg import MARK, main as animate, note_animation  # noqa: E402
from validate_svg import validate  # noqa: E402

FAILURES = 0


def _check(name: str, cond: bool, detail: str = "") -> None:
    global FAILURES
    FAILURES += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if not cond and detail else ""))


def _svg(body: str, root_attrs: str = "") -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100"%s>'
            "<title>t</title><desc>d</desc>"
            '<rect width="300" height="100" fill="#ffffff"/>%s</svg>' % (root_attrs, body))


TWO_BEATS = ('<g data-beat="1"><rect x="10" y="30" width="80" height="40" fill="#F2EEEE"/></g>'
             '<g data-beat="2"><rect x="200" y="30" width="80" height="40" fill="#DA1B2E"/></g>')

NOTE = """+---+ -> +---+
<!-- ascii-note:
intent: x
animation:
  1. left box appears
  2. right box appears
emphasize: right
-->
"""


def _run(tmp: Path, svg: str, *args: str, name: str = "s1-2-1-flow") -> tuple[int, str]:
    p = tmp / f"{name}.svg"
    p.write_text(svg, encoding="utf-8")
    code = animate([str(p), *args])
    return code, p.read_text(encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        side = tmp / "s1-2-1-flow.ascii"
        side.write_text(NOTE, encoding="utf-8")

        _check("note_animation counts the numbered beats and stops at the next key",
               note_animation(NOTE) == (2, ""))
        _check("note_animation: a note without animation is no expectation",
               note_animation("x\n<!-- ascii-note: free text -->\n") is None)
        _check("note_animation reads `animation: loop` as the mode",
               note_animation(NOTE.replace("animation:", "animation: loop")) == (2, "loop"))

        code, out = _run(tmp, _svg(TWO_BEATS), "--ascii", str(side))
        _check("tagged diagram animates", code == 0 and MARK in out, out[:300])
        _check("scope class lands on the root", 'class="ts-anim-s1-2-1-flow"' in out)
        _check("style sits after <desc>, title/desc stay first",
               out.index("</desc>") < out.index(MARK))
        _check("every beat gets its own delay", '[data-beat="2"]{animation-delay:1.60s}' in out, out)
        _check("plays once by default — nothing loops", "infinite" not in out)
        _check("result still passes validate_svg", not validate(out, tolerance=0.01)[2])

        p = tmp / "s1-2-1-flow.svg"
        animate([str(p), "--ascii", str(side)])
        _check("re-run is a no-op", p.read_text(encoding="utf-8") == out)

        code, out = _run(tmp, _svg(TWO_BEATS, ' class="diagram"'), "--beats", "2")
        _check("an existing root class is kept", 'class="diagram ts-anim-s1-2-1-flow"' in out, out[:200])

        loop_side = tmp / "loop.ascii"
        loop_side.write_text(NOTE.replace("animation:", "animation: loop"), encoding="utf-8")
        code, out = _run(tmp, _svg(TWO_BEATS), "--ascii", str(loop_side))
        _check("`animation: loop` cycles, each beat on its own scoped keyframes",
               code == 0 and "infinite" in out and "@keyframes ts-anim-s1-2-1-flow-b2" in out
               and "animation-delay" not in out, out)
        _check("a looping diagram still passes validate_svg", not validate(out, tolerance=0.01)[2])
        code, _ = _run(tmp, _svg(TWO_BEATS), "--beats", "2", "--loop")
        _check("--loop does the same for Mode A", code == 0)
        odd = tmp / "odd.ascii"
        odd.write_text(NOTE.replace("animation:", "animation: bounce"), encoding="utf-8")
        code, _ = _run(tmp, _svg(TWO_BEATS), "--ascii", str(odd))
        _check("an unknown animation mode is a defect", code == 1)

        bad = _svg('<g data-beat="1"><g data-beat="2"><rect width="1" height="1"/></g></g>')
        code, out = _run(tmp, bad)
        _check("nested beats are a defect and the file is untouched", code == 1 and out == bad)

        code, out = _run(tmp, _svg('<g data-beat="1"/><g data-beat="3"/>'))
        _check("a gap in the beats is a defect", code == 1)

        code, _ = _run(tmp, _svg(TWO_BEATS), "--beats", "3")
        _check("tags disagreeing with the note's beat count is a defect", code == 1)

        code, _ = _run(tmp, _svg('<rect width="1" height="1"/>'), "--ascii", str(side))
        _check("a note with beats but an untagged SVG is a defect", code == 1)

        code, out = _run(tmp, _svg('<g data-beat="1" transform="translate(5 0)"/>'))
        _check("a tagged element that sets its own transform is a defect", code == 1)

        code, out = _run(tmp, _svg('<g data-beat="1"><g transform="translate(5 0)" opacity="0.5"/></g>'))
        _check("opacity/transform on a child of the tagged group is fine", code == 0)

        code, out = _run(tmp, _svg('<defs><marker id="m" data-beat="1"/></defs><g data-beat="1"/>'))
        _check("a beat inside <defs> is a defect", code == 1)

        animated = _run(tmp, _svg(TWO_BEATS), "--beats", "2")[1]
        untagged = animated.replace(' data-beat="1"', "").replace(' data-beat="2"', "")
        code, out = _run(tmp, untagged)
        _check("tags removed → earlier animation and scope are stripped",
               code == 0 and MARK not in out and "ts-anim-" not in out, out[:300])

        # The still state is the end state: a rasterizer that ignores @keyframes draws every beat.
        if subprocess.run([sys.executable, str(SKILL / "rasterize.py"), "--check"],
                          capture_output=True).returncode == 0:
            from PIL import Image
            svg = tmp / "s1-2-1-flow.svg"
            svg.write_text(animated, encoding="utf-8")
            png = tmp / "flow.png"
            subprocess.run([sys.executable, str(SKILL / "rasterize.py"), str(svg), "-o", str(png),
                            "--width", "600"], capture_output=True, check=True)
            im = Image.open(png).convert("RGB")
            _check("cairosvg draws the complete diagram (both beats)",
                   im.getpixel((100, 100)) == (242, 238, 238) and im.getpixel((480, 100)) == (218, 27, 46))
        else:
            print("SKIP  cairosvg end-state check (this interpreter cannot rasterize)")

    print()
    if FAILURES:
        print(f"{FAILURES} test(s) FAILED.")
        return 1
    print("all animate_svg tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
