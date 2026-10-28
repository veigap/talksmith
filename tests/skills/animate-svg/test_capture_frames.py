#!/usr/bin/env python3
"""Tests for `capture_frames` — the blind critic's view of an animation.

Run:  python3 tests/skills/animate-svg/test_capture_frames.py

The critic judges an animation from these frames alone, so what matters is that they show the
animation as it plays: the frames cover its key moments, the last one is the still as the
animation leaves it (a bug once kept a frame caught mid-fade instead), a quick journey is caught
under way and not only arrived, and a re-capture never leaves stale frames from a longer run.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[2] / "skills" / "animate-svg"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "md-to-deck" / "scripts"))
import capture_frames as F  # noqa: E402
import _chrome  # noqa: E402

FAILURES = 0


def _check(name: str, cond: bool, detail: str = "") -> None:
    global FAILURES
    FAILURES += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if not cond and detail else ""))


def main() -> int:
    _check("key times: the true end survives the merge of a close cluster",
           F._key_times([0, 5.0, 21.2, 21.3, 21.35])[-1] == 21.35)
    _check("key times: capped, keeping the first and the last",
           (lambda ts: len(ts) == F.MAX_FRAMES and ts[0] == 0 and ts[-1] == 40)(F._key_times([float(i) for i in range(41)])))

    if not _chrome.find():
        print("SKIP  capture (no Chrome/Chromium)")
    else:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "frames"
            out.mkdir()
            (out / "frame-99.png").write_bytes(b"stale")
            code = F.main([str(SKILL / "examples" / "gan-paths.svg"), "--out", str(out)])
            names = sorted(p.name for p in out.glob("*.png"))
            _check("capture: a contact sheet and a frame per key moment, stale frames cleared",
                   code == 0 and "contact.png" in names and "frame-99.png" not in names
                   and sum(n.startswith("frame-") for n in names) >= 8, str(names))
            static = Path(d) / "static.svg"
            static.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect/></svg>')
            _check("capture: an SVG with no animation is refused", F.main([str(static), "--out", str(out)]) == 2)

    print()
    if FAILURES:
        print(f"{FAILURES} test(s) FAILED.")
        return 1
    print("all capture_frames tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
