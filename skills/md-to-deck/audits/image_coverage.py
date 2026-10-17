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
    - a ref explicitly waived with `<!-- deck-omit: <path> -->` on any line (intentional omission);
    - a ref a slide's **`_omitted`** trace names with a known reason — `icon`, `frame` or `formula`.
      That is the FILL's half of the catalog rule *Decoration is not content*
      (`config/pptx-styles/slide-templates.md`): a PPTX import carries per-card icons and empty card
      frames that are not content, and the FILL never edits `final.md`, so the waiver has to live
      in the model. It is honest because it is **visible** — every such omission is listed on
      stdout by reason, never folded silently into "ok" — and **closed**: an unknown reason waives
      nothing. `_`-keys are otherwise never read as rendered images (an `_omitted` `src` is the
      opposite of one).

Advisory `[decoration?]` lines flag the reverse failure — the one that shipped twenty slides of
giant icons and empty frames: a **rendered** raster that is icon-sized (longer side <= 128 px), or
a formula strip (>= 4:1, <= 160 px tall) placed as a per-item `figures` image. They never change
the exit code: a small logo that identifies its item is legitimately content.

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
import struct
import sys
from pathlib import Path

_IMG_REF_ANY = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+?)\s*\)")
_OMIT_RE = re.compile(r"<!--\s*deck-omit:\s*([^>]+?)\s*-->", re.IGNORECASE)
_NONSLIDE_HEADING = re.compile(r"^#\s+(Cut material|Open questions)\b", re.IGNORECASE)

# The closed vocabulary of a model-side `_omitted` waiver (catalog → *Decoration is not content*).
OMIT_REASONS = ("icon", "frame", "formula")
ICON_MAX_PX = 128          # longer side at or under this → icon-sized
STRIP_ASPECT, STRIP_MAX_H = 4.0, 160   # wide and one text line tall → a formula strip


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
                elif not k.startswith("_"):   # `_choice`/`_omitted` are traces, not renders
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(model)
    return out


def model_omitted(model: dict) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """(basename → reason for every valid `_omitted` entry, [(basename, reason)] for invalid ones).

    `_omitted: [{src, reason}]` sits on a slide beside `_choice`. Only a reason in `OMIT_REASONS`
    waives; anything else is returned as invalid so the report can say why it did not count."""
    ok: dict[str, str] = {}
    bad: list[tuple[str, str]] = []
    for sl in model.get("slides") or []:
        for e in (sl.get("_omitted") or []) if isinstance(sl, dict) else []:
            if not isinstance(e, dict) or not isinstance(e.get("src"), str) or not e["src"]:
                continue
            reason = str(e.get("reason", "")).strip().lower()
            if reason in OMIT_REASONS:
                ok[_base(e["src"])] = reason
            else:
                bad.append((_base(e["src"]), reason or "<none>"))
    return ok, bad


def _px(path: Path) -> tuple[int, int] | None:
    """(width, height) of a PNG or GIF from its header; None for anything else or unreadable."""
    try:
        head = path.read_bytes()[:26]
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        return struct.unpack(">II", head[16:24])
    if head[:6] in (b"GIF87a", b"GIF89a") and len(head) >= 10:
        return struct.unpack("<HH", head[6:10])
    return None


def decoration_suspects(model: dict, root: Path) -> list[str]:
    """Rendered rasters that look like decoration: icon-sized anywhere, or a formula strip used as
    a per-item `figures` image. Advisory — a small logo that identifies its item is content."""
    out: list[str] = []

    def check(src: str, where: str, per_item: bool) -> None:
        wh = _px(root / src)
        if not wh or not all(wh):
            return
        w, h = wh
        if max(w, h) <= ICON_MAX_PX:
            out.append(f"{where}: {_base(src)} is {w}x{h} px — icon-sized; decoration is not "
                       f"content (map it to the item's `icon`, or omit it with `_omitted`)")
        elif per_item and w / h >= STRIP_ASPECT and h <= STRIP_MAX_H:
            out.append(f"{where}: {_base(src)} is a {w}x{h} px strip — a formula, not a figure "
                       f"(transcribe it, or give it full-width media)")

    def walk(o, where: str, per_item: bool) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "src" and isinstance(v, str) and v:
                    check(v, where, per_item)
                elif not k.startswith("_"):
                    walk(v, where, per_item or k == "figures")
        elif isinstance(o, list):
            for x in o:
                walk(x, where, per_item)

    for i, sl in enumerate(model.get("slides") or [], 1):
        title = sl.get("title") if isinstance(sl, dict) else None
        walk(sl, f"slide {i}" + (f" «{title}»" if title else ""), False)
    return out


def audit(final_text: str, model: dict) -> list[str]:
    """Return the ordered, de-duplicated list of image basenames present in final.md but missing
    from the model (excluding explicitly-omitted ones: a `deck-omit` waiver in final.md, or a
    valid `_omitted` entry in the model)."""
    refs, omit = final_image_refs(final_text)
    have = model_image_srcs(model)
    omit = omit | set(model_omitted(model)[0])
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
    omitted, bad = model_omitted(model)
    if omitted:
        by: dict[str, list[str]] = {}
        for b, r in omitted.items():
            by.setdefault(r, []).append(b)
        print(f"image_coverage: {len(omitted)} ref(s) left out by the fill as decoration/formula "
              f"(`_omitted`): " + "; ".join(f"{r} ×{len(v)}: {', '.join(sorted(v))}"
                                            for r, v in sorted(by.items())))
    for b, r in bad:
        print(f"image_coverage: `_omitted` {b} has reason {r!r} — not one of "
              f"{', '.join(OMIT_REASONS)}, so it waives nothing", file=sys.stderr)
    for line in decoration_suspects(model, args.final.parent):
        print(f"  [decoration?] {line}", file=sys.stderr)
    if not missing:
        print(f"image_coverage: ok — every final.md image ref is present in {args.model.name}")
        return 0

    print(f"image_coverage: {len(missing)} image ref(s) in {args.final.name} MISSING from the model "
          f"(a slide may render with no image — re-check the FILL step, or waive with "
          f"`<!-- deck-omit: <path> -->`; decoration the catalog excludes goes in the slide's "
          f"`_omitted`):", file=sys.stderr)
    for m in missing:
        print(f"  - {m}", file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
