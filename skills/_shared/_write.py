"""Write primitives shared across skills.

(Named `_write`, not `_io`: `_io` is CPython's built-in accelerator module for `io`, and a
`sys.path`-inserted file of that name shadows it — the import fails with a bewildering
"unknown location".)

Small, but not incidental: every skill that edits a user's `draft.md` / `final.md` in place must do
it the same way, because a half-written source file is the one failure the presenter cannot recover
from. Two copies of that meant two chances to get it subtly different.
"""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write_lines(path: Path, lines: list[str]) -> None:
    """Replace `path` with `lines`, atomically, always newline-terminated.

    Write-then-`os.replace` rather than truncate-then-write: `os.replace` is atomic on POSIX, so a
    crash mid-write leaves the original intact instead of a truncated `draft.md`. The trailing
    newline is enforced here rather than by each caller — a source file that loses it makes every
    later diff show a spurious last-line change.
    """
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
