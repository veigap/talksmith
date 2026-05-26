"""Audit that every color and font in a rendered `final.pptx` is within
the §2 palette + §3.1 font set.

Why this exists:
    `${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/{strict,free-form}/pptx-prompt.md` §2 declares
    a tight color palette and §3.1 declares three permitted typefaces.
    Both rules are part of the **floor** that holds in every render
    style — strict and free-form alike. Off-palette colors (e.g. an
    Office theme accent leaking in from a copy-paste) and system-font
    fallbacks (e.g. Calibri, Helvetica, Arial creeping in because a
    text run forgot its `<a:latin typeface="…"/>`) are invisible to
    the layout-fit, block-coverage, and aspect-ratio audits — they
    surface only at visual review when the slide reads "off-brand"
    in some hard-to-name way. This script is the deterministic catch.

What it does:
    Walks every slide in the .pptx, collects every `<a:srgbClr val="…"/>`
    color reference and every `<a:latin typeface="…"/>` font reference
    (recursing into <a:rPr>, <a:solidFill>, <a:ln>, <p:bg>, theme
    overrides, etc.), then reports any value outside the allowed
    palette / font set as `[off-palette]` / `[off-font]`. Exits
    non-zero on any violation.

    Allowed palette (union of §2.1 text inks + §2.2 fills):
      #3B3535 #1F1E1E #000000 #FFFFFF #6A737D #D73A49 #DA1B2E
      #F33447 #005CC5 #F2F2F2 #F2EEEE #F9D2D6 #F7BBC1 #B8E6F5
      #D8D4D4

    Allowed fonts (§3.1):
      Roboto Mono Medium · Roboto · Consolas · Roboto Mono Light
      (Roboto Mono Light is the 8-run accent face the source deck used;
       treated as same family as Roboto Mono Medium for floor purposes.)

    Scope:
      - Iterates `ppt/slides/slide*.xml` only (not masters / layouts /
        themes — those carry the brand theme's residual colors and
        fonts which slide-level runs override per §3.1 contract).
      - Case-insensitive on hex (`F33447` == `f33447`).
      - Whitespace-trimmed on typeface ("Roboto " == "Roboto").
      - Skips `<a:schemeClr>` references — those are theme-bound and
        should not appear in slide-level content per §2, but if they
        do they surface separately as `[scheme-clr]`.

Usage:
    python3 audit_palette_fonts.py <final.pptx> [--json] [--warn-only]

Exit codes:
    0  every color + font in slide content is in the allowed set
    1  one or more violations; build should stop and re-render
    2  audit could not run (file missing, malformed)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict, field

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

# §2 palette — union of text inks (§2.1) + fills (§2.2). Uppercase hex.
ALLOWED_COLORS = {
    "3B3535", "1F1E1E", "000000", "FFFFFF", "6A737D", "D73A49",
    "DA1B2E", "F33447", "005CC5", "F2F2F2", "F2EEEE", "F9D2D6",
    "F7BBC1", "B8E6F5", "D8D4D4",
}

# §3.1 fonts — slide-level run typefaces must be one of these.
# Treat Roboto Mono Light and Roboto Mono Medium as the same family for floor purposes.
ALLOWED_FONTS = {"Roboto Mono Medium", "Roboto Mono Light", "Roboto", "Consolas"}


@dataclass
class Violation:
    slide: str
    kind: str            # "color" | "font" | "scheme-clr"
    value: str
    context: str = ""    # e.g. "<a:rPr> in <a:r>", "<p:bg>"

    def fmt(self) -> str:
        tag = {"color": "off-palette", "font": "off-font", "scheme-clr": "scheme-clr"}[self.kind]
        slide_m = re.search(r"slide(\d+)\.xml", self.slide)
        sid = slide_m.group(1) if slide_m else "?"
        ctx = f" — {self.context}" if self.context else ""
        return f"[{tag}] slide {sid} · {self.kind}={self.value!r}{ctx}"


def _slide_paths(zf: zipfile.ZipFile) -> list[str]:
    return sorted(
        (n for n in zf.namelist()
         if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
        key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)),
    )


def _ancestor_local_name(parent_map: dict, el: ET.Element) -> str:
    """Best-effort: return the local name of the nearest meaningful
    ancestor (rPr, solidFill, bgPr, ln, blipFill, etc.) for the context
    column. Falls back to immediate parent's local name."""
    cur = parent_map.get(el)
    if cur is None:
        return ""
    tag = cur.tag.rsplit("}", 1)[-1] if "}" in cur.tag else cur.tag
    return tag


def audit_slide(slide_path: str, xml_bytes: bytes) -> list[Violation]:
    out: list[Violation] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        out.append(Violation(slide=slide_path, kind="color", value="", context=f"XML PARSE ERROR: {e}"))
        return out

    parent_map = {child: parent for parent in root.iter() for child in parent}

    # Colors — srgbClr
    for el in root.iter(f"{{{NS['a']}}}srgbClr"):
        v = (el.get("val") or "").upper()
        if not v:
            continue
        if v not in ALLOWED_COLORS:
            ctx = _ancestor_local_name(parent_map, el)
            out.append(Violation(slide=slide_path, kind="color", value=f"#{v}", context=ctx))

    # Scheme colors — should not appear in slide content per §2
    for el in root.iter(f"{{{NS['a']}}}schemeClr"):
        v = el.get("val", "")
        ctx = _ancestor_local_name(parent_map, el)
        # bg scheme reference in <p:bgRef> is technically allowed in layout chains
        # but §1 mandates inline white solid; surface as scheme-clr regardless.
        out.append(Violation(slide=slide_path, kind="scheme-clr", value=v, context=ctx))

    # Fonts — latin typeface
    for el in root.iter(f"{{{NS['a']}}}latin"):
        face = (el.get("typeface") or "").strip()
        if not face:
            continue
        if face not in ALLOWED_FONTS:
            # try cs / ea attributes too if latin missing? — out of scope
            ctx = _ancestor_local_name(parent_map, el)
            out.append(Violation(slide=slide_path, kind="font", value=face, context=ctx))

    return out


def audit(pptx_path: str) -> tuple[list[Violation], int, dict]:
    with zipfile.ZipFile(pptx_path) as zf:
        slides = _slide_paths(zf)
        violations: list[Violation] = []
        seen_colors: dict[str, int] = defaultdict(int)
        seen_fonts: dict[str, int] = defaultdict(int)
        for sp in slides:
            try:
                xml_bytes = zf.read(sp)
            except KeyError:
                continue
            for v in audit_slide(sp, xml_bytes):
                violations.append(v)
                if v.kind == "color":
                    seen_colors[v.value] += 1
                elif v.kind == "font":
                    seen_fonts[v.value] += 1
        summary = {
            "slides": len(slides),
            "violations": len(violations),
            "off_palette_colors": dict(seen_colors),
            "off_fonts": dict(seen_fonts),
        }
    return violations, len(slides), summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("pptx")
    p.add_argument("--json", action="store_true")
    p.add_argument("--warn-only", action="store_true",
                   help="report violations but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    try:
        violations, n_slides, summary = audit(args.pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_palette_fonts: cannot read {args.pptx}: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "pptx": args.pptx,
            "summary": summary,
            "violations": [asdict(v) for v in violations],
        }, indent=2))
    else:
        if not violations:
            print(f"audit_palette_fonts: ok — {n_slides} slides, every color in "
                  f"§2 palette, every font in §3.1 set")
        else:
            print(f"audit_palette_fonts: {len(violations)} violation(s) across {n_slides} slides")
            for v in violations:
                print("  " + v.fmt())
            if summary["off_palette_colors"]:
                print(f"  off-palette colors seen: {summary['off_palette_colors']}")
            if summary["off_fonts"]:
                print(f"  off-fonts seen:          {summary['off_fonts']}")

    if args.warn_only:
        return 0
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
