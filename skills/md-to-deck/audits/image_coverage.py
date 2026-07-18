#!/usr/bin/env python3
"""Preflight: every load-bearing image ref in `final.md` must survive into `slide-model.json`.

Why this exists:
    The FILL step decomposes `final.md` into the model by hand (LLM). On a slide that mixes a
    documentation-only ASCII banner with a real screenshot, the fill once dropped the screenshot
    ref — the model was otherwise valid and would have rendered a slide with no image, invisible
    unless someone diffed the model against `final.md`. This audit is that diff, mechanised: it
    lists every `![](…)` in `final.md` (slide body only) that the model does not reference, so a
    silent image drop is caught **before** rendering, not after.

What it ignores (never counted as a missing image):
    - refs inside `<!-- ascii-source: … -->` provenance comments (echoes of ASCII source, not a
      slide image);
    - anything under `# Cut material` / `# Open questions` (not delivered slides);
    - a ref explicitly waived with `<!-- deck-omit: <path> -->` on any line (intentional omission).

Aside refs (`<!-- aside: <side> ![](images/…) -->`) DO render, so they are counted — a dropped
aside is a real defect too.

Usage:
    python3 image_coverage.py <final.md> <slide-model.json> [--strict]

Exit codes:
    0  every final.md image ref is present in the model (warnings, if any, are advisory)
    0  missing refs found, default (warn-only) — prints the list to stderr
    1  missing refs found AND --strict
    2  a file could not be read / parsed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_IMG_REF_ANY = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+?)\s*\)")
_OMIT_RE = re.compile(r"<!--\s*deck-omit:\s*([^>]+?)\s*-->", re.IGNORECASE)
_NONSLIDE_HEADING = re.compile(r"^#\s+(Cut material|Open questions)\b", re.IGNORECASE)


def _base(path: str) -> str:
    return path.rsplit("/", 1)[-1].strip().lower()


def final_image_refs(text: str) -> tuple[list[str], set[str]]:
    """(ordered basenames referenced in slide bodies, set of explicitly-omitted basenames)."""
    lines = text.split("\n")
    end = len(lines)
    for i, ln in enumerate(lines):
        if _NONSLIDE_HEADING.match(ln):
            end = i
            break
    lines = lines[:end]

    # Mask `<!-- ascii-source: … -->` comment ranges (their echoed ASCII isn't a slide image).
    skip = [False] * len(lines)
    i = 0
    while i < len(lines):
        if "<!-- ascii-source:" in lines[i]:
            j = i
            while j < len(lines) and "-->" not in lines[j]:
                j += 1
            for k in range(i, min(j + 1, len(lines))):
                skip[k] = True
            i = j + 1
        else:
            i += 1

    refs: list[str] = []
    omit: set[str] = set()
    for i, ln in enumerate(lines):
        m = _OMIT_RE.search(ln)
        if m:
            omit.add(_base(m.group(1)))
        if skip[i]:
            continue
        for mm in _IMG_REF_ANY.finditer(ln):
            refs.append(_base(mm.group(1)))
    return refs, omit


def model_image_srcs(model: dict) -> set[str]:
    """Every image basename the model will render — any `src` value, at any nesting depth."""
    out: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "src" and isinstance(v, str) and v:
                    out.add(_base(v))
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(model)
    return out


def audit(final_text: str, model: dict) -> list[str]:
    """Return the ordered, de-duplicated list of image basenames present in final.md but missing
    from the model (excluding explicitly-omitted ones)."""
    refs, omit = final_image_refs(final_text)
    have = model_image_srcs(model)
    missing: list[str] = []
    seen: set[str] = set()
    for r in refs:
        if r in have or r in omit or r in seen:
            continue
        seen.add(r)
        missing.append(r)
    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("final", type=Path, help="path to the Talk's final.md")
    ap.add_argument("model", type=Path, help="path to slide-model.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 when refs are missing (default: warn, exit 0)")
    args = ap.parse_args(argv)

    try:
        final_text = args.final.read_text(encoding="utf-8")
    except OSError as e:
        print(f"image_coverage: cannot read {args.final}: {e}", file=sys.stderr)
        return 2
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"image_coverage: cannot read model {args.model}: {e}", file=sys.stderr)
        return 2

    missing = audit(final_text, model)
    if not missing:
        print(f"image_coverage: ok — every final.md image ref is present in {args.model.name}")
        return 0

    print(f"image_coverage: {len(missing)} image ref(s) in {args.final.name} MISSING from the model "
          f"(a slide may render with no image — re-check the FILL step, or waive with "
          f"`<!-- deck-omit: <path> -->`):", file=sys.stderr)
    for m in missing:
        print(f"  - {m}", file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
