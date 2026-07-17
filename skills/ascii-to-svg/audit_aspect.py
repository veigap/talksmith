#!/usr/bin/env python3
"""Check that an SVG's viewBox actually fits the art drawn inside it.

## The blind spot this exists to cover

Every other Step-6 check is visual: the `diagram-critic` looks at a rasterized PNG and
says what it sees. That catches a lot, but it is *structurally incapable* of catching a
mis-declared viewBox — because the PNG is rasterized **from** the viewBox. Declare
`0 0 680 295` around art that really wants 2.91:1 and the PNG comes back at exactly
2.30:1, looking entirely correct, with the art sitting in a pool of dead canvas that
reads as "the author wanted whitespace here". No amount of looking reveals it. The
defect only surfaces a full render cycle later, when `audits/aspect_ratios.py` sizes a
PPTX slot from the viewBox and the picture lands wrong on the slide.

So this check is mechanical, and it runs at render time where the fix costs one iteration
instead of one PPTX build.

## What it measures, and why not the obvious thing

The obvious metric — content aspect vs. viewBox aspect — is a **false-positive machine**.
Measured against this repo's own fixtures, a perfectly well-formed diagram (`s5-2-1`:
even ~40-unit margins on all four sides) shows 21% "drift", purely because equal margins
in *units* are unequal in *percent* when the axes have different scales. Thresholding on
that either flags healthy diagrams or misses broken ones.

What actually separates good from bad is the **margins, expressed in viewBox units**:

    s5-2-1    39 / 39 / 41 / 43   → max/min 1.12   healthy: even frame
    pipeline  38 / 38 / 148 / 148 → max/min 3.86   canvas far too tall for the art
    s2-3-1    23 / 23 / 69 / 89   → max/min 3.86   same
    workflow  40 / 39 / 27 / 147  → max/min 5.46   art sits high, dead band below
    s4-3-1   175 / 78 / 23 / 123  → max/min 7.60   off-centre on both axes

Healthy lands at 1.12; broken starts at 3.86. The default threshold sits in that gap with
room on both sides, so it is a measured number, not a guess.

## Reporting only

A finding is emitted as a defect line for the diagram-illustrator to fold into its `style_directives`,
alongside a suggested corrected viewBox. The suggestion is always a pure **crop** — changing
`viewBox` min-y/height moves no element coordinate — but it is *not* applied automatically:
whitespace is sometimes intentional, and silently reflowing a diagram the presenter framed
on purpose is worse than asking.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"([^"]+)"')

# Ratio of largest to smallest margin above which the frame is judged wrong.
# Calibrated on the fixtures in the module docstring: healthy ≤1.12, broken ≥3.86.
DEFAULT_THRESHOLD = 2.5

# Below this (as a fraction of the smaller viewBox side) a margin counts as "no margin":
# full-bleed art legitimately runs to the edge, and 0/0/0/0 must not divide by zero.
_FULL_BLEED_EPS = 0.01


def parse_viewbox(svg_path: Path) -> tuple[float, float, float, float]:
    m = _VIEWBOX_RE.search(svg_path.read_text(errors="replace"))
    if not m:
        raise ValueError(f"no viewBox in {svg_path}")
    parts = re.split(r"[\s,]+", m.group(1).strip())
    if len(parts) != 4:
        raise ValueError(f"malformed viewBox in {svg_path}: {m.group(1)!r}")
    x, y, w, h = (float(p) for p in parts)
    if w <= 0 or h <= 0:
        raise ValueError(f"non-positive viewBox extent in {svg_path}: {w}x{h}")
    return x, y, w, h


def ink_bbox(png_path: Path, tol: int = 8):
    """Bounding box of everything that isn't the background, in PNG pixels.

    Measured on the rasterized PNG rather than parsed out of the SVG geometry: computing
    a true bbox from arbitrary paths, markers, strokes and text metrics means
    reimplementing a renderer, and would disagree with the one that actually draws.

    **The background colour is sampled from the corners, not assumed to be white.** An
    earlier version hard-coded white, which made this whole audit silently useless on any
    diagram carrying a full-canvas tinted rect: every pixel differed from white, the ink
    bbox became the entire image, and the check returned "full-bleed — art runs to every
    edge" and exit 0. Same diagram, same framing defect, `#FFFFFF` background → correctly
    flagged at 3.86x; `#F2EEEE` background → passed clean. A check that reports ok when it
    cannot see is worse than no check, because it launders the defect as verified.

    The corners are the one place guaranteed to be background: whatever the outermost pixel
    is, the art is framed against it. Taking the majority of the four is what survives a
    single corner clipped by a bleeding element.
    """
    from PIL import Image, ImageChops
    from collections import Counter
    im = Image.open(png_path).convert("RGB")
    W, H = im.size
    corners = [im.getpixel(p) for p in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1))]
    bg_colour = Counter(corners).most_common(1)[0][0]
    bg = Image.new("RGB", im.size, bg_colour)
    mask = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > tol else 0)
    return im.size, mask.getbbox(), bg_colour


def audit(svg: Path, png: Path, threshold: float = DEFAULT_THRESHOLD) -> tuple[int, str]:
    vx, vy, vw, vh = parse_viewbox(svg)
    (W, H), bbox, bg_colour = ink_bbox(png)
    if bbox is None:
        return 2, f"failed: {svg.name} rasterizes to a blank image — nothing is drawn"
    bg_hex = "#%02X%02X%02X" % bg_colour

    # PNG pixels → viewBox units. rasterize.py guarantees the PNG matches the viewBox ratio,
    # so a single scale factor per axis is exact.
    sx, sy = vw / W, vh / H
    x0, y0, x1, y1 = bbox
    left, right = x0 * sx, (W - x1) * sx
    top, bottom = y0 * sy, (H - y1) * sy
    margins = {"left": left, "right": right, "top": top, "bottom": bottom}

    smallest_side = min(vw, vh)
    if max(margins.values()) < smallest_side * _FULL_BLEED_EPS:
        return 0, (f"ok: {svg.name} · full-bleed (art runs to every edge) · "
                   f"background sampled as {bg_hex}")

    lo = max(min(margins.values()), smallest_side * 0.001)  # floor: avoid /0 on one flush edge
    hi = max(margins.values())
    imbalance = hi / lo

    fmt = " / ".join(f"{k[0].upper()}{v:.0f}" for k, v in margins.items())
    if imbalance <= threshold:
        return 0, (f"ok: {svg.name} · margins {fmt} units · "
                   f"imbalance {imbalance:.2f}× (defect at >{threshold}×) · background {bg_hex}")

    # Suggest a pure crop: keep the art where it is, tighten the frame to an even margin.
    pad = min(margins.values())
    nx = vx + left - pad
    ny = vy + top - pad
    nw = vw - left - right + 2 * pad
    nh = vh - top - bottom + 2 * pad
    worst = max(margins, key=lambda k: margins[k])
    msg = (
        f"defect: {svg.name} · viewBox declares {vw:.0f}x{vh:.0f} ({vw/vh:.2f}:1) but the art "
        f"is framed unevenly — margins {fmt} units, {imbalance:.2f}× imbalance (max {threshold}×). "
        f"The {worst} margin is {margins[worst]:.0f} units against a tightest edge of {pad:.0f}. "
        f"That dead canvas is invisible in the PNG (it rasterizes from this very viewBox) but "
        f"the PPTX slot is sized from it, so the picture lands wrong on the slide.\n"
        f"  suggested viewBox=\"{nx:.0f} {ny:.0f} {nw:.0f} {nh:.0f}\" "
        f"({nw/nh:.2f}:1) — a pure crop to an even {pad:.0f}-unit frame; no element coordinate changes."
    )
    return 1, msg


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("svg", type=Path)
    p.add_argument("--png", type=Path, required=True,
                   help="the PNG rasterized from this SVG (rasterize.py output)")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help=f"max tolerated margin imbalance (default {DEFAULT_THRESHOLD})")
    a = p.parse_args(argv)
    for f in (a.svg, a.png):
        if not f.exists():
            print(f"failed: no such file: {f}", file=sys.stderr)
            return 2
    try:
        code, msg = audit(a.svg, a.png, a.threshold)
    except ValueError as e:
        print(f"failed: {e}", file=sys.stderr)
        return 2
    print(msg, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
