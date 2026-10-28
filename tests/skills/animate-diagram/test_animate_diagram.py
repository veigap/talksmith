#!/usr/bin/env python3
"""End-to-end test of `talksmith:animate-diagram`: a generator script → GIF + final-frame PNG +
critique frames, all to the contract in skills/animate-diagram/SKILL.md.

Run:  python3 tests/skills/animate-diagram/test_animate_diagram.py

This file is stdlib-only, like every other test here; the animation itself needs numpy,
matplotlib and Pillow, so it is run under whatever interpreter `find_python.py` finds — the same
probe Step 6 uses — and the whole test SKIPS (exit 0) when there is none, exactly as Step 6
degrades to static SVG then.

The fixture is the skill's own reference script (`examples/inference_pipeline.py`, a 3-block
pipeline), copied to where Step 6 puts a generator: `talks/<Talk>/images/.anim/<stem>.py`. The
training reference runs in `--preview` (its gradient check and key frames, without the GIF).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "animate-diagram"
failures = 0


def _check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")


def _python() -> str | None:
    r = subprocess.run([sys.executable, str(SKILL / "find_python.py")], capture_output=True, text=True)
    m = re.match(r"python: (.+)", r.stdout.strip())
    return m.group(1) if r.returncode == 0 and m else None


_INSPECT = r"""
import json, sys
from PIL import Image
g = Image.open(sys.argv[1]); n = g.n_frames; durs = []
for i in range(n):
    g.seek(i); durs.append(g.info.get("duration", 0))
last = g.convert("RGB"); png = Image.open(sys.argv[2]).convert("RGB")
diff = sum(abs(a - b) for a, b in zip(last.resize((160, 90)).tobytes(), png.resize((160, 90)).tobytes()))
print(json.dumps({"size": g.size, "loop": g.info.get("loop"), "frames": n, "durs": durs,
                  "png_size": png.size, "diff": diff / (160 * 90 * 3)}))
"""


_INTERRUPT = r"""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import anim_helpers as ah
from PIL import Image
images = Path(sys.argv[2])
gif = images / "interrupted.gif"
gif.write_bytes(b"GIF89a previous complete render")
real_save = Image.Image.save
def dying_save(self, fp, *a, **k):
    if str(fp).endswith(".tmp") and k.get("format") == "GIF":
        Path(fp).write_bytes(b"GIF89a half")          # partial bytes, then the process dies
        raise KeyboardInterrupt("killed mid-write")
    return real_save(self, fp, *a, **k)
Image.Image.save = dying_save
anim = ah.Anim(str(images / ".anim" / "interrupted.py"))
for n in range(3):
    anim.frame(lambda ax, st: ah.caption(ax, f"stage {st}"), n, seconds=5, key=True)
try:
    anim.save()
except KeyboardInterrupt:
    pass
print("intact" if gif.read_bytes() == b"GIF89a previous complete render" else "CLOBBERED")
"""


def main() -> int:
    py = _python()
    if not py:
        print("skip: no Python with numpy, matplotlib and Pillow (find_python.py) — Step 6 renders static SVG then")
        return 0
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    print(f"animate-diagram (under {py})")

    r = subprocess.run([py, str(SKILL / "anim_helpers.py"), "--check"], capture_output=True, text=True, env=env)
    _check("--check: deps importable and the palette complete from diagram-style.md",
           r.returncode == 0 and "palette: complete" in r.stdout, r.stdout + r.stderr)

    with tempfile.TemporaryDirectory() as td:
        images = Path(td) / "talk" / "images"
        (images / ".anim").mkdir(parents=True)
        script = images / ".anim" / "s1-2-1-pipeline-conv.py"
        shutil.copy(SKILL / "examples" / "inference_pipeline.py", script)
        r = subprocess.run([py, str(script)], capture_output=True, text=True, env=env, timeout=600)
        report = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        _check("generator runs and reports", r.returncode == 0 and report.startswith("animated:"),
               r.stderr[-400:])
        gif, png = images / "s1-2-1-pipeline-conv.gif", images / "s1-2-1-pipeline-conv.png"
        _check("outputs land beside the generator's stem: <stem>.gif + <stem>.png",
               gif.is_file() and png.is_file())
        _check("the mechanical audits found nothing (layout, captions, timing, size)",
               report.endswith("warnings: none"), report)
        if gif.is_file() and png.is_file():
            info = json.loads(subprocess.run([py, "-c", _INSPECT, str(gif), str(png)], capture_output=True,
                                             text=True).stdout)
            cycle = sum(info["durs"]) / 1000
            _check("GIF is 1600×900 and loops", tuple(info["size"]) == (1600, 900) and info["loop"] == 0,
                   str(info["size"]))
            _check("several frames, 12–20 s per cycle", info["frames"] > 10 and 12 <= cycle <= 20, f"{cycle}s")
            _check("the final frame is held ≥ 3 s", info["durs"][-1] >= 3000, str(info["durs"][-1]))
            _check("≤ 5 MB", gif.stat().st_size <= 5_000_000, f"{gif.stat().st_size} bytes")
            _check("<stem>.png IS the final frame (same picture, full size)",
                   tuple(info["png_size"]) == (1600, 900) and info["diff"] < 3, str(info["diff"]))
        _check("no temporary files left behind", not list(images.glob(".*.tmp")),
               str(list(images.glob(".*.tmp"))))
        frames = sorted((images / ".critique" / "s1-2-1-pipeline-conv.frames").glob("*.png"))
        _check("3–5 sampled critique frames + a contact sheet",
               3 <= len(frames) <= 5 and (images / ".critique" / "s1-2-1-pipeline-conv.png").is_file(),
               str(len(frames)))
        if gif.is_file():
            out = Path(td) / "sampled"
            r = subprocess.run([py, str(SKILL / "anim_helpers.py"), "frames", str(gif), "-o", str(out)],
                               capture_output=True, text=True, env=env)
            _check("`frames` CLI samples any GIF", r.returncode == 0 and 3 <= len(list(out.glob("*.png"))) <= 5,
                   r.stderr[-300:])

        # An interrupted write must never leave a 0-byte (or partial) GIF under the real name:
        # the deliverable is written to a temporary sibling and renamed into place.
        r = subprocess.run([py, "-c", _INTERRUPT, str(SKILL), str(images)], capture_output=True,
                           text=True, env=env)
        _check("an interrupted save leaves the previous GIF intact (atomic write)",
               r.stdout.strip() == "intact", (r.stdout + r.stderr)[-400:])

        tscript = images / ".anim" / "s2-1-1-head-training.py"
        shutil.copy(SKILL / "examples" / "training_loop.py", tscript)
        r = subprocess.run([py, str(tscript), "--preview"], capture_output=True, text=True, env=env, timeout=600)
        tframes = list((images / ".critique" / "s2-1-1-head-training.frames").glob("*.png"))
        _check("training reference: gradient check passes, key frames rendered (preview)",
               r.returncode == 0 and r.stdout.startswith("preview:") and len(tframes) >= 3
               and "warnings: none" in r.stdout, (r.stdout + r.stderr)[-400:])

    if failures:
        print(f"\n{failures} check(s) FAILED")
        return 1
    print("\nall animate-diagram checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
