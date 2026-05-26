"""Audit that slide 1 (cover) of a rendered `final.pptx` is byte-equivalent
to slide 1 of the style's `base-template.pptx`, modulo only the four §4.3
content substitution slots.

Why this exists:
    §4 of the per-style `pptx-prompt.md` (both `strict/` and `free-form/`)
    declares the cover slide as **contractually fixed**: "must be
    reproduced byte-for-byte structurally. Only the *content* of the
    four text/image shapes changes per Talk; positions, sizes, fonts,
    colors, and z-order are fixed." This rule is part of the floor —
    every render style ships the same cover. Renderers that emit a
    visually-similar cover with subtly different geometry (e.g. logo
    shifted 0.1 in, title size 38pt instead of 40.5pt, author block
    using Roboto Mono instead of Roboto) are off-spec even though the
    output "looks like a cover." This audit catches the drift.

What it does:
    Extracts a structural fingerprint of every shape on slide 1 of
    `base-template.pptx` and on slide 1 of `final.pptx`:
      - shape_type (sp | pic)
      - cNvPr name (shape identity in §4.2)
      - geometry (off x, off y, ext cx, ext cy)
      - prstGeom prst attribute (rect, roundRect, ellipse, ...)
      - solid fill color (if any)
      - stroke color (if any)
      - primary text-run font (typeface + sz) — first <a:r><a:rPr>
        inside <p:txBody>
      - body-text alignment (<a:pPr algn>)
      - image rId target (for <p:pic>) — resolved via slide rels

    Then compares fingerprints by shape index (order is contractual
    per §4.2 z-order). The four allowed-to-differ slots are:
      - shape #1 text content (cover title — substitution)
      - shape #2 text content (subtitle — substitution)
      - shape #3 text content (author + date — substitution)
      - shape #4 image rId Target if it points at a logo file the
        presenter explicitly overrode (rare; §4.3 says "preserved
        verbatim unless the presenter explicitly swaps brands")

    Text content (`<a:t>` runs) is NOT part of the fingerprint — that's
    the substitution. Everything else must match.

    Failures surface as:
      [cover-fidelity] shape N "<name>" differs in <field>: base=<X> rendered=<Y>

Usage:
    python3 audit_cover_fidelity.py <final.pptx> <base-template.pptx>
                                    [--json] [--warn-only]

Exit codes:
    0  cover fidelity preserved
    1  cover structurally differs from base-template's slide 1
    2  audit could not run (file missing, malformed, slide 1 absent)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, asdict, field
from pathlib import PurePosixPath

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class ShapeFingerprint:
    index: int                                  # 0-based ordinal within spTree
    shape_type: str                             # "sp" | "pic"
    name: str                                   # <p:cNvPr name=…>
    off: tuple[int, int] | None                 # x, y EMU
    ext: tuple[int, int] | None                 # cx, cy EMU
    prst_geom: str                              # e.g. "rect", "roundRect"
    fill_hex: str | None                        # solid fill srgbClr val (upper)
    stroke_hex: str | None                      # ln/solidFill/srgbClr val (upper)
    primary_font: tuple[str, int] | None        # (typeface, sz_hundredths)
    primary_color: str | None                   # first run rPr solidFill srgbClr
    align: str | None                           # first <a:pPr algn=…>
    pic_target: str | None = None               # for <p:pic>, resolved rels target


def _load_slide_rels(zf: zipfile.ZipFile, slide_path: str) -> dict[str, str]:
    p = PurePosixPath(slide_path)
    rels_path = str(p.parent / "_rels" / (p.name + ".rels"))
    if rels_path not in zf.namelist():
        return {}
    out: dict[str, str] = {}
    try:
        root = ET.fromstring(zf.read(rels_path))
    except (ET.ParseError, KeyError):
        return {}
    for rel in root.findall(f"{{{NS['rel']}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target", "")
        if rid and target:
            out[rid] = target
    return out


def _parse_xfrm(sp: ET.Element) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    xfrm = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}xfrm")
    if xfrm is None:
        return None, None
    off = xfrm.find(f"{{{NS['a']}}}off")
    ext = xfrm.find(f"{{{NS['a']}}}ext")
    off_t = None
    ext_t = None
    if off is not None:
        try:
            off_t = (int(off.get("x", "0")), int(off.get("y", "0")))
        except (TypeError, ValueError):
            pass
    if ext is not None:
        try:
            ext_t = (int(ext.get("cx", "0")), int(ext.get("cy", "0")))
        except (TypeError, ValueError):
            pass
    return off_t, ext_t


def _solid_fill_hex(sp: ET.Element) -> str | None:
    sf = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}solidFill")
    if sf is None:
        return None
    clr = sf.find(f"{{{NS['a']}}}srgbClr")
    if clr is None:
        return None
    v = clr.get("val", "")
    return v.upper() if len(v) == 6 else None


def _stroke_hex(sp: ET.Element) -> str | None:
    ln = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}ln")
    if ln is None:
        return None
    sf = ln.find(f"{{{NS['a']}}}solidFill")
    if sf is None:
        return None
    clr = sf.find(f"{{{NS['a']}}}srgbClr")
    if clr is None:
        return None
    v = clr.get("val", "")
    return v.upper() if len(v) == 6 else None


def _prst_geom(sp: ET.Element) -> str:
    pg = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}prstGeom")
    return pg.get("prst", "") if pg is not None else ""


def _primary_run(sp: ET.Element) -> tuple[tuple[str, int] | None, str | None, str | None]:
    """Return ((typeface, sz), color_hex, algn) for the first text run + paragraph."""
    txbody = sp.find(f"{{{NS['p']}}}txBody")
    if txbody is None:
        return None, None, None
    first_p = txbody.find(f"{{{NS['a']}}}p")
    if first_p is None:
        return None, None, None
    ppr = first_p.find(f"{{{NS['a']}}}pPr")
    algn = ppr.get("algn") if ppr is not None and ppr.get("algn") else None
    first_r = first_p.find(f"{{{NS['a']}}}r")
    if first_r is None:
        return None, None, algn
    rpr = first_r.find(f"{{{NS['a']}}}rPr")
    if rpr is None:
        return None, None, algn
    sz = int(rpr.get("sz", "0")) if rpr.get("sz") else 0
    latin = rpr.find(f"{{{NS['a']}}}latin")
    face = (latin.get("typeface") or "").strip() if latin is not None else ""
    font = (face, sz) if face or sz else None
    sf = rpr.find(f"{{{NS['a']}}}solidFill")
    color = None
    if sf is not None:
        clr = sf.find(f"{{{NS['a']}}}srgbClr")
        if clr is not None:
            v = clr.get("val", "")
            if len(v) == 6:
                color = v.upper()
    return font, color, algn


def _pic_target(pic: ET.Element, rels: dict[str, str]) -> str | None:
    blip = pic.find(f"{{{NS['p']}}}blipFill/{{{NS['a']}}}blip")
    if blip is None:
        return None
    rid = blip.get(f"{{{NS['r']}}}embed")
    if not rid:
        return None
    return rels.get(rid)


def fingerprint_slide1(pptx_path: str) -> list[ShapeFingerprint]:
    """Extract shape fingerprints from slide 1 of a .pptx file."""
    with zipfile.ZipFile(pptx_path) as zf:
        sp_path = "ppt/slides/slide1.xml"
        if sp_path not in zf.namelist():
            raise FileNotFoundError(f"{pptx_path} has no slide 1")
        try:
            root = ET.fromstring(zf.read(sp_path))
        except ET.ParseError as e:
            raise FileNotFoundError(f"{pptx_path} slide 1 malformed: {e}")
        rels = _load_slide_rels(zf, sp_path)
        # Walk children of spTree in document order
        sptree = root.find(f"{{{NS['p']}}}cSld/{{{NS['p']}}}spTree")
        if sptree is None:
            raise FileNotFoundError(f"{pptx_path} slide 1 has no spTree")
        out: list[ShapeFingerprint] = []
        for i, el in enumerate(list(sptree)):
            tag = el.tag.rsplit("}", 1)[-1]
            if tag not in ("sp", "pic"):
                continue
            cnv = el.find(f"{{{NS['p']}}}nvSpPr/{{{NS['p']}}}cNvPr") \
                  if tag == "sp" \
                  else el.find(f"{{{NS['p']}}}nvPicPr/{{{NS['p']}}}cNvPr")
            name = cnv.get("name", "") if cnv is not None else ""
            off, ext = _parse_xfrm(el)
            prst = _prst_geom(el)
            fill = _solid_fill_hex(el)
            stroke = _stroke_hex(el)
            font, color, algn = _primary_run(el)
            target = _pic_target(el, rels) if tag == "pic" else None
            out.append(ShapeFingerprint(
                index=len(out),
                shape_type=tag,
                name=name,
                off=off,
                ext=ext,
                prst_geom=prst,
                fill_hex=fill,
                stroke_hex=stroke,
                primary_font=font,
                primary_color=color,
                align=algn,
                pic_target=target,
            ))
    return out


# --------------------------------------------------------------------------- #
# reconciliation
# --------------------------------------------------------------------------- #

@dataclass
class CoverDiff:
    index: int
    name: str
    field: str
    base: object
    rendered: object

    def fmt(self) -> str:
        return (f"[cover-fidelity] shape #{self.index} \"{self.name}\" "
                f"differs in {self.field}: base={self.base!r} rendered={self.rendered!r}")


def reconcile(
    base: list[ShapeFingerprint], rendered: list[ShapeFingerprint]
) -> list[CoverDiff]:
    diffs: list[CoverDiff] = []
    if len(base) != len(rendered):
        diffs.append(CoverDiff(
            index=-1, name="(shape count)", field="shape_count",
            base=len(base), rendered=len(rendered)))
        # Continue with pairwise compare up to shorter
    for i in range(min(len(base), len(rendered))):
        b, r = base[i], rendered[i]
        if b.shape_type != r.shape_type:
            diffs.append(CoverDiff(i, b.name, "shape_type", b.shape_type, r.shape_type))
            continue
        # Geometry, fonts, fills must match. Text content (a:t) is allowed to
        # differ — not in the fingerprint.
        for field_name in ("off", "ext", "prst_geom", "fill_hex", "stroke_hex",
                            "primary_font", "primary_color", "align"):
            bv = getattr(b, field_name)
            rv = getattr(r, field_name)
            if bv != rv:
                diffs.append(CoverDiff(i, b.name, field_name, bv, rv))
        # For <p:pic>, the rels target should resolve to the same logo path
        # (file basename comparison — accepts ../media/image-1-1.png vs.
        #  /ppt/media/image-1-1.png if the basename matches).
        if b.shape_type == "pic":
            b_base = PurePosixPath(b.pic_target or "").name
            r_base = PurePosixPath(r.pic_target or "").name
            if b_base and r_base and b_base != r_base:
                diffs.append(CoverDiff(i, b.name, "pic_target_basename",
                                       b_base, r_base))
    return diffs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("final_pptx", help="path to talks/<Talk>/output/final.pptx")
    p.add_argument("base_template", help="path to the style's base-template.pptx")
    p.add_argument("--json", action="store_true")
    p.add_argument("--warn-only", action="store_true")
    args = p.parse_args(argv)

    try:
        base = fingerprint_slide1(args.base_template)
        rendered = fingerprint_slide1(args.final_pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_cover_fidelity: {e}", file=sys.stderr)
        return 2

    diffs = reconcile(base, rendered)

    if args.json:
        print(json.dumps({
            "final_pptx": args.final_pptx,
            "base_template": args.base_template,
            "summary": {
                "base_shapes": len(base),
                "rendered_shapes": len(rendered),
                "diffs": len(diffs),
            },
            "diffs": [asdict(d) for d in diffs],
        }, indent=2))
    else:
        if not diffs:
            print(f"audit_cover_fidelity: ok — slide 1 byte-equivalent to "
                  f"{args.base_template} cover (modulo text content substitution)")
        else:
            print(f"audit_cover_fidelity: {len(diffs)} diff(s)")
            for d in diffs:
                print("  " + d.fmt())

    if args.warn_only:
        return 0
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
