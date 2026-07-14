"""Curate a Talksmith `draft.md` / `final.md` in place — deterministic markdown normalization.

Repairs source-authoring defects that make a slide render oddly, **without changing wording**.
Today it fixes one thing (more can be added as they're found):

  - **Ordered lists whose 2./3. markers were dropped.** Authoring (or a reconcile round-trip)
    sometimes leaves `1. first` followed by bare continuation lines — three items that lost
    their markers. `slide_model._recover_ordered` restores them so the slide renders as the
    uniform ordered list it always was, instead of a big numbered lead plus mismatched panels.

This is the "same script that curates it" — run it on the **source** so `draft.md` stays the
single source of truth, rather than hand-editing a derived file or papering over it at render
time. Idempotent: a clean file is rewritten byte-identical (exit 0, nothing changed).

Usage:
    python3 curate.py talks/<Talk>/draft.md            # fix in place, report changed lines
    python3 curate.py talks/<Talk>/draft.md --check     # report only, don't write (exit 1 if dirty)
    python3 curate.py talks/<Talk>/draft.md -o out.md   # write elsewhere
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import slide_model as _sm             # noqa: E402  (_recover_ordered — the shared curation logic)


def curate(text: str) -> str:
    """Apply every deterministic normalization pass. Line-scoped and idempotent."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split("\n") if nl == "\n" else text.replace("\r\n", "\n").split("\n")
    lines = _sm._recover_ordered(lines)
    return nl.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path, help="the draft.md / final.md to curate")
    ap.add_argument("--check", action="store_true", help="report changes but do not write (exit 1 if dirty)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="write here instead of in place")
    a = ap.parse_args(argv)

    if not a.path.is_file():
        print(f"failed: {a.path} not found", file=sys.stderr)
        return 2
    src = a.path.read_text(encoding="utf-8")
    out = curate(src)

    if out == src:
        print(f"[curate] {a.path} already clean")
        return 0

    diff = difflib.unified_diff(src.splitlines(), out.splitlines(), lineterm="", n=1)
    for d in diff:
        if not d.startswith(("+++", "---", "@@")):
            print(d)
    changed = sum(1 for x in out.splitlines()) - sum(1 for x in src.splitlines())
    if a.check:
        print(f"[curate] {a.path} would change ({changed:+d} line(s)) — run without --check to apply")
        return 1
    (a.output or a.path).write_text(out, encoding="utf-8")
    print(f"[curate] wrote {a.output or a.path} ({changed:+d} line(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
