"""Validate (and auto-repair) an SVG against the aspect-ratio contract
declared in SKILL.md step 5.

Why this exists:
    The downstream PPTX renderer trusts the SVG's intrinsic aspect
    ratio (viewBox) when sizing its placement slot. If the SVG arrives
    with a missing viewBox, a `preserveAspectRatio="none"` hint, or
    root width/height attrs that disagree with the viewBox, every
    downstream guarantee — including `${CLAUDE_PLUGIN_ROOT}/skills/md-to-deck/
    audits/aspect_ratios.py` — silently breaks. The PPTX audit is a
    backstop; this script is the upstream gate so a broken SVG never
    reaches disk.

What it checks:
    1. Root <svg> has a parseable `viewBox="x y W H"` with W>0, H>0.
       Unfixable — if missing/broken, exit 2.
    2. Root <svg> does not carry `preserveAspectRatio="none"`.
       Fixable — drop the attribute (default `xMidYMid meet` is correct).
    3. Root <svg> width/height attrs either absent or agree with the
       viewBox W:H ratio within tolerance (default 1%). Fixable — drop
       both when they disagree; the viewBox is authoritative.
    4. Any nested <svg> or <image> with `preserveAspectRatio="none"`.
       Fixable — drop the attribute on each.

What it does NOT check:
    Content bounding box vs viewBox extent. That requires geometry
    parsing (paths, transforms, text metrics) and is the author's
    responsibility. If the viewBox declares a 1:1 canvas but the
    content lives in a 2:1 region, the renderer will faithfully scale
    a half-empty 1:1 box — visually wrong but mechanically consistent.

Usage:
    python3 validate_svg.py <path-to-svg> [--check-only] [--tolerance 0.01]

Exit codes:
    0  valid (or repaired and rewritten)
    1  invalid; --check-only requested (no rewrite)
    2  unfixable (missing/unparseable viewBox, malformed XML)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


def _parse_viewbox(vb: str) -> tuple[float, float, float, float] | None:
    parts = re.split(r"[\s,]+", vb.strip())
    if len(parts) != 4:
        return None
    try:
        x, y, w, h = (float(p) for p in parts)
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _parse_length(v: str | None) -> float | None:
    if v is None:
        return None
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z%]*)\s*$", v)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    # Treat px, "", pt, mm, etc. as raw numbers for ratio purposes — we
    # only care about the W:H ratio, not the absolute unit.
    return n if n > 0 else None


def validate(svg_text: str, tolerance: float) -> tuple[str, list[str], list[str]]:
    """Return (repaired_text, fixes_applied, unfixable_errors).

    `repaired_text` equals `svg_text` if no fixes were needed.
    """
    fixes: list[str] = []
    errors: list[str] = []

    # Parse to locate the root element and its attributes; we'll do
    # rewrites by regex on the original text to preserve formatting,
    # comments, and namespace prefix style.
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        return svg_text, [], [f"malformed XML: {e}"]

    tag = root.tag
    local = tag.rsplit("}", 1)[-1] if "}" in tag else tag
    if local != "svg":
        return svg_text, [], [f"root element is <{local}>, expected <svg>"]

    # --- 1. viewBox present + parseable -----------------------------------
    vb = root.get("viewBox")
    if not vb:
        errors.append("root <svg> is missing required attribute viewBox")
    else:
        parsed = _parse_viewbox(vb)
        if parsed is None:
            errors.append(f"root <svg> viewBox=\"{vb}\" is unparseable or non-positive")
        else:
            _, _, vb_w, vb_h = parsed
            vb_ratio = vb_w / vb_h

            # --- 3. root width/height agree with viewBox ----------------------
            w_attr = _parse_length(root.get("width"))
            h_attr = _parse_length(root.get("height"))
            if w_attr is not None and h_attr is not None:
                attr_ratio = w_attr / h_attr
                if abs(attr_ratio / vb_ratio - 1.0) > tolerance:
                    svg_text, did = _drop_root_attrs(svg_text, ("width", "height"))
                    if did:
                        fixes.append(
                            f"dropped root width/height ({w_attr:g}x{h_attr:g}, ratio "
                            f"{attr_ratio:.4f}) — disagreed with viewBox ratio {vb_ratio:.4f}"
                        )

    # --- 2. preserveAspectRatio="none" on root ----------------------------
    if root.get("preserveAspectRatio", "").strip().lower().startswith("none"):
        svg_text, did = _drop_root_attrs(svg_text, ("preserveAspectRatio",))
        if did:
            fixes.append("dropped root preserveAspectRatio=\"none\" — default xMidYMid meet restored")

    # --- 4. preserveAspectRatio="none" on nested <svg>/<image> ------------
    nested_count = len(re.findall(
        r'(<(?:[a-zA-Z][\w.-]*:)?(?:svg|image)\b[^>]*?\bpreserveAspectRatio\s*=\s*"\s*none\b[^"]*")',
        svg_text,
    ))
    # Skip the root <svg> (already handled above) — but the regex above will
    # only re-match it if its preserveAspectRatio is still present, which it
    # isn't after the root-level fix. So count is nested-only.
    if nested_count:
        svg_text = re.sub(
            r'(<(?:[a-zA-Z][\w.-]*:)?(?:svg|image)\b[^>]*?)\s+preserveAspectRatio\s*=\s*"\s*none[^"]*"',
            r'\1',
            svg_text,
        )
        fixes.append(f"dropped preserveAspectRatio=\"none\" on {nested_count} nested <svg>/<image>")

    return svg_text, fixes, errors


def _drop_root_attrs(svg_text: str, attrs: tuple[str, ...]) -> tuple[str, bool]:
    """Drop the named attributes from the root <svg ...> open tag only.

    Operates on the first <svg ...> occurrence, preserving everything else.
    """
    m = re.search(r"<(?:[a-zA-Z][\w.-]*:)?svg\b[^>]*>", svg_text)
    if not m:
        return svg_text, False
    open_tag = m.group(0)
    new_open = open_tag
    for a in attrs:
        new_open = re.sub(
            rf'\s+{re.escape(a)}\s*=\s*"[^"]*"',
            "",
            new_open,
            count=1,
        )
    if new_open == open_tag:
        return svg_text, False
    return svg_text[: m.start()] + new_open + svg_text[m.end():], True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("svg", help="path to the SVG to validate")
    p.add_argument(
        "--tolerance", type=float, default=0.01,
        help="max |attr_ratio/viewBox_ratio − 1| before width/height are dropped (default 0.01)",
    )
    p.add_argument(
        "--check-only", action="store_true",
        help="report fixes that would be applied but do not rewrite the file",
    )
    args = p.parse_args(argv)

    try:
        with open(args.svg, encoding="utf-8") as f:
            original = f.read()
    except (FileNotFoundError, OSError) as e:
        print(f"validate_svg: cannot read {args.svg}: {e}", file=sys.stderr)
        return 2

    repaired, fixes, errors = validate(original, args.tolerance)

    if errors:
        for e in errors:
            print(f"validate_svg: ERROR  {args.svg}: {e}", file=sys.stderr)
        return 2

    if fixes:
        for f in fixes:
            print(f"validate_svg: FIX    {args.svg}: {f}")
        if args.check_only:
            return 1
        with open(args.svg, "w", encoding="utf-8") as f:
            f.write(repaired)
        print(f"validate_svg: rewrote {args.svg} ({len(fixes)} fix(es))")
        return 0

    print(f"validate_svg: ok     {args.svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
