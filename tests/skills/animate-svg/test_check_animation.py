#!/usr/bin/env python3
"""Tests for `check_animation` — the deck's playback contract, and the critic's frames.

Run:  python3 tests/skills/animate-svg/test_check_animation.py

The contract is the one fixed part of an animated diagram (`skills/animate-svg/SKILL.md` →
*The playback contract*); everything else is authored. So the synthetic cases each break one
clause, and the real ones check the two ends of the pass: every reference case's `base.svg`
starts with its note asking for an animation it does not have yet, and the shipped example —
plus anything a run of the skill left in `output/` — conforms.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[2] / "skills" / "animate-svg"
sys.path.insert(0, str(SKILL))
import check_animation as C  # noqa: E402

FAILURES = 0


def _check(name: str, cond: bool, detail: str = "") -> None:
    global FAILURES
    FAILURES += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if not cond and detail else ""))


S = "ts-anim-flow"
GOOD_CSS = (f".{S} .a{{animation:{S}-in .6s ease-out .5s both}}\n"
            f"@keyframes {S}-in{{from{{opacity:0}}}}\n"
            f"@media (prefers-reduced-motion:reduce){{.{S} *{{animation:none}}}}")


def _svg(css: str | None = GOOD_CSS, body: str = '<g class="a"><rect width="10" height="10"/></g>',
         cls: str = S) -> str:
    style = f"<style>{C.MARK}\n{css}\n</style>" if css is not None else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100" class="{cls}">'
            f"<title>t</title><desc>d</desc>{style}{body}</svg>")


def _run(tmp: Path, svg: str, *args: str, name: str = "flow") -> int:
    p = tmp / f"{name}.svg"
    p.write_text(svg, encoding="utf-8")
    return C.main([str(p), *args])


NOTE = "x\n<!-- ascii-note:\nintent: y\nanimation:\n  1. it arrives\n-->\n"


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        note = tmp / "flow.ascii"
        note.write_text(NOTE, encoding="utf-8")
        loop_note = tmp / "loop.ascii"
        loop_note.write_text(NOTE.replace("animation:", "animation: loop"), encoding="utf-8")

        _check("note_animation reads the mode", C.note_animation(NOTE) == ""
               and C.note_animation(NOTE.replace("animation:", "animation: loop")) == "loop"
               and C.note_animation("<!-- ascii-note:\nintent: y\n-->") is None)

        _check("a conforming animation passes", _run(tmp, _svg(), "--ascii", str(note)) == 0)
        _check("no animation and no brief → none", _run(tmp, _svg(css=None)) == 0)
        _check("a brief with no animation is a defect", _run(tmp, _svg(css=None), "--ascii", str(note)) == 1)
        _check("an unscoped selector is a defect",
               _run(tmp, _svg(GOOD_CSS.replace(f".{S} .a", ".a"))) == 1)
        _check("an unscoped @keyframes is a defect",
               _run(tmp, _svg(GOOD_CSS.replace(f"{S}-in", "fade-in"))) == 1)
        _check("a missing root scope class is a defect", _run(tmp, _svg(cls="diagram")) == 1)
        _check("SMIL is a defect", _run(tmp, _svg(body='<rect width="9" height="9"><animate attributeName="x" to="5" dur="1s"/></rect>')) == 1)
        _check("a script is a defect", _run(tmp, _svg(body='<script>1</script>')) == 1)
        _check("an event handler is a defect", _run(tmp, _svg(body='<rect width="9" height="9" onclick="x()"/>')) == 1)
        _check("no fill-mode both/forwards is a defect",
               _run(tmp, _svg(GOOD_CSS.replace(" both}", "}"))) == 1)
        _check("no reduced-motion rule is a defect",
               _run(tmp, _svg(GOOD_CSS.split("\n@media")[0])) == 1)
        looping = GOOD_CSS.replace(" both}", " both infinite}")
        _check("repeating without `animation: loop` is a defect", _run(tmp, _svg(looping), "--ascii", str(note)) == 1)
        _check("repeating with `animation: loop` passes", _run(tmp, _svg(looping), "--ascii", str(loop_note)) == 0)
        odd = tmp / "odd.ascii"
        odd.write_text(NOTE.replace("animation:", "animation: bounce"), encoding="utf-8")
        _check("an unknown mode is a defect", _run(tmp, _svg(), "--ascii", str(odd)) == 1)

        for case in sorted(p for p in HERE.iterdir() if (p / "base.svg").is_file()):
            src = case / "source.ascii"
            if not src.is_file():
                src = tmp / f"{case.name}.ascii"
                src.write_text((case / "note.txt").read_text(encoding="utf-8"), encoding="utf-8")
            code = C.main([str(case / "base.svg"), "--ascii", str(src)])
            _check(f"case {case.name}: the base asks for an animation it does not have yet", code == 1)

        for case in sorted(p for p in HERE.iterdir() if p.is_dir() and not (p / "base.svg").exists()
                           and (p / "source.ascii").is_file()):
            text = (case / "source.ascii").read_text(encoding="utf-8")
            _check(f"case {case.name}: ASCII + a note with an `animation:` brief, ready for ascii-to-svg",
                   C.note_animation(text) == "" and "<!-- ascii-note:" in text
                   and (case / "context.json").is_file())

        example = SKILL / "examples" / "gan-paths.svg"
        _check("the shipped example conforms", C.main([str(example)]) == 0)
        for out in sorted((HERE / "output").glob("*.svg")):
            _check(f"output {out.name} conforms", C.main([str(out)]) == 0)

        sys.path.insert(0, str(HERE.parents[2] / "skills" / "md-to-deck"))
        import _chrome
        if _chrome.find():
            fdir = tmp / "frames"
            fdir.mkdir()
            (fdir / "frame-99.png").write_bytes(b"stale")
            text = example.read_text(encoding="utf-8")
            line = C.write_frames(text, 990 / 400, fdir)
            names = sorted(p.name for p in fdir.glob("*.png"))
            _check("frames: a contact sheet and a frame per key moment, stale frames cleared",
                   "contact.png" in names and "frame-99.png" not in names
                   and sum(n.startswith("frame-") for n in names) >= 8, f"{line} {names}")
        else:
            print("SKIP  frames (no Chrome/Chromium)")

    print()
    if FAILURES:
        print(f"{FAILURES} test(s) FAILED.")
        return 1
    print("all check_animation tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
