#!/usr/bin/env python3
"""Find a Python interpreter that can run an animation generator (numpy + matplotlib + Pillow).

Stdlib only, so it runs under whatever `python3` the session has — which is the point: the
interpreter on PATH is often the system one, and the system one often lacks numpy. Probing is
cheap (one `-c "import …"` per candidate), so this answers once per Step 6, before anything is
dispatched, instead of halfway through a wave of renders.

    python3 find_python.py          # → "python: /abs/path/to/python3", exit 0
                                    # → "unavailable: …", exit 2 (degrade to the static SVG path)

`$TALKSMITH_ANIM_PYTHON` is tried first, so a presenter can pin an interpreter explicitly.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROBE = "import numpy, matplotlib, PIL"


def candidates() -> list[str]:
    home = Path.home()
    env = os.environ
    raw = [
        env.get("TALKSMITH_ANIM_PYTHON"),
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
        env.get("CONDA_PREFIX") and str(Path(env["CONDA_PREFIX"]) / "bin" / "python"),
        env.get("VIRTUAL_ENV") and str(Path(env["VIRTUAL_ENV"]) / "bin" / "python"),
        str(Path.cwd() / ".venv" / "bin" / "python"),
        str(home / ".venv" / "bin" / "python"),
        str(home / "miniconda3" / "bin" / "python3"),
        str(home / "anaconda3" / "bin" / "python3"),
        str(home / "miniforge3" / "bin" / "python3"),
        str(home / "mambaforge" / "bin" / "python3"),
        "/opt/conda/bin/python",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    ]
    out, seen = [], set()
    for c in raw:
        if not c or not os.path.isfile(c) or not os.access(c, os.X_OK):
            continue
        key = os.path.realpath(c)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def main() -> int:
    tried = candidates()
    for exe in tried:
        try:
            r = subprocess.run([exe, "-c", PROBE], capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            print(f"python: {exe}")
            return 0
    print("unavailable: no Python with numpy, matplotlib and Pillow "
          f"(tried: {', '.join(tried) or 'none found'}). Animated diagrams fall back to static "
          "SVG. To enable them: `<python3> -m pip install numpy matplotlib pillow`, or point "
          "$TALKSMITH_ANIM_PYTHON at an interpreter that has them.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
