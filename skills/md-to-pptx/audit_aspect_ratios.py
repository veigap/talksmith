"""Audit every `<p:pic>` in a rendered .pptx for aspect-ratio preservation.

Why this exists:
    `config/pptx-styles/strict/pptx-prompt.md` §12 forbids non-uniform image scaling — the
    rendered `cx:cy` of every `<p:pic>` must equal the source asset's
    intrinsic `width:height`. Prose alone is not enough: renderers can
    place a wide-aspect SVG (e.g. 2.143:1) into a narrower placeholder
    (e.g. 1.400:1) and fill by non-uniform stretch, producing ~35%
    horizontal compression. The defect is invisible during build
    (no error raised) and easy to miss during visual review when
    the diagram is "the same shape, just compressed." This script is
    the automated catch.

What it does:
    Walks every slide in a .pptx, finds every `<p:pic>`, resolves the
    source asset via the slide's rels file, reads the asset's intrinsic
    aspect ratio (SVG `viewBox`, PNG/JPG header), and compares to the
    rendered `cx:cy`. Flags any mismatch above `--tolerance` (default
    1%). Exits non-zero on any flag so the SKILL workflow can fail the
    render.

    For SVG `<p:pic>` shapes the rendered geometry lives on the
    fallback raster's `<p:pic>` wrapper, but `r:embed` may resolve to
    either the SVG or its PNG fallback depending on how the native
    renderer emitted §17.4. We check both: prefer the SVG's `viewBox`
    when present (it is the authoritative intrinsic ratio), otherwise
    fall back to the raster header.

    `noChangeAspect="1"` on `<p:cNvPicPr><a:picLocks>` is reported as a
    presence flag, not enforced — its absence is a soft warning, not a
    failure, because the cx:cy check is the load-bearing assertion.

Usage:
    python3 audit_aspect_ratios.py <path-to-final.pptx> [--tolerance 0.01] [--json]

Exit codes:
    0  all `<p:pic>` shapes within tolerance (or zero pictures found)
    1  one or more mismatches at or above tolerance
    2  audit could not run (bad .pptx, unreadable asset, missing rel)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, asdict
from pathlib import PurePosixPath

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "svg": "http://www.w3.org/2000/svg",
}


@dataclass
class PicReport:
    slide: str                       # e.g. "ppt/slides/slide7.xml"
    shape_name: str                  # `<p:nvPicPr><p:cNvPr name=…>` or ""
    src_path: str                    # e.g. "ppt/media/image-7-1.svg"
    src_w: float
    src_h: float
    src_aspect: float                # src_w / src_h
    cx_emu: int
    cy_emu: int
    rendered_aspect: float           # cx_emu / cy_emu
    ratio_error: float               # |rendered/src − 1|
    no_change_aspect: bool
    status: str                      # "ok" | "warn" | "fail"
    note: str = ""


# --------------------------------------------------------------------------- #
# intrinsic-dimension readers
# --------------------------------------------------------------------------- #

def _read_svg_dims(blob: bytes) -> tuple[float, float] | None:
    """Return (w, h) from <svg viewBox=…>, falling back to width/height
    attributes. Returns None if neither is parseable."""
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return None
    vb = root.get("viewBox")
    if vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            try:
                _x, _y, w, h = (float(p) for p in parts)
                if w > 0 and h > 0:
                    return w, h
            except ValueError:
                pass
    w_attr = root.get("width")
    h_attr = root.get("height")
    if w_attr and h_attr:
        try:
            w = float(re.sub(r"[a-zA-Z%]+$", "", w_attr))
            h = float(re.sub(r"[a-zA-Z%]+$", "", h_attr))
            if w > 0 and h > 0:
                return w, h
        except ValueError:
            return None
    return None


def _read_png_dims(blob: bytes) -> tuple[float, float] | None:
    if len(blob) < 24 or blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", blob[16:24])
    return (float(w), float(h)) if w and h else None


def _read_jpeg_dims(blob: bytes) -> tuple[float, float] | None:
    if len(blob) < 4 or blob[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(blob)
    while i < n:
        # find next 0xFF marker
        while i < n and blob[i] != 0xFF:
            i += 1
        while i < n and blob[i] == 0xFF:
            i += 1
        if i >= n:
            return None
        marker = blob[i]
        i += 1
        # SOFn markers carry dimensions (0xC0–0xCF, excluding 0xC4/0xC8/0xCC)
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 7 > n:
                return None
            h, w = struct.unpack(">HH", blob[i + 3 : i + 7])
            return (float(w), float(h)) if w and h else None
        # other markers: read segment length, skip
        if i + 2 > n:
            return None
        seg_len = struct.unpack(">H", blob[i : i + 2])[0]
        i += seg_len
    return None


def _intrinsic_dims(name: str, blob: bytes) -> tuple[float, float] | None:
    lower = name.lower()
    if lower.endswith(".svg"):
        return _read_svg_dims(blob)
    if lower.endswith(".png"):
        return _read_png_dims(blob)
    if lower.endswith((".jpg", ".jpeg")):
        return _read_jpeg_dims(blob)
    return None


# --------------------------------------------------------------------------- #
# .pptx walking
# --------------------------------------------------------------------------- #

def _slide_rels_path(slide_path: str) -> str:
    p = PurePosixPath(slide_path)
    return str(p.parent / "_rels" / (p.name + ".rels"))


def _resolve_rels(slide_path: str, target: str) -> str:
    # PurePosixPath has no resolve(); do manual `..` collapse
    parts: list[str] = list(PurePosixPath(slide_path).parent.parts)
    for p in PurePosixPath(target).parts:
        if p == "..":
            if parts:
                parts.pop()
        elif p == ".":
            continue
        else:
            parts.append(p)
    return str(PurePosixPath(*parts))


def _load_rels(zf: zipfile.ZipFile, slide_path: str) -> dict[str, tuple[str, str]]:
    """Return {rId: (target_path_in_zip, raw_target)}.

    raw_target is kept for diagnostics; target_path_in_zip is normalized
    relative to the zip root.
    """
    rels_path = _slide_rels_path(slide_path)
    if rels_path not in zf.namelist():
        return {}
    out: dict[str, tuple[str, str]] = {}
    try:
        rels_root = ET.fromstring(zf.read(rels_path))
    except (ET.ParseError, KeyError):
        return {}
    for rel in rels_root.findall("rel:Relationship", NS):
        rid = rel.get("Id")
        target = rel.get("Target", "")
        if not rid or not target:
            continue
        resolved = _resolve_rels(slide_path, target)
        out[rid] = (resolved, target)
    return out


def _slide_paths(zf: zipfile.ZipFile) -> list[str]:
    return sorted(
        n for n in zf.namelist()
        if n.startswith("ppt/slides/slide") and n.endswith(".xml")
    )


def _walk_pics(slide_xml: bytes):
    """Yield each <p:pic> element along with its enclosing context."""
    try:
        tree = ET.fromstring(slide_xml)
    except ET.ParseError:
        return
    for pic in tree.iter(f"{{{NS['p']}}}pic"):
        yield pic


def _pic_geometry(pic: ET.Element) -> tuple[int, int] | None:
    """Return (cx, cy) in EMU from <p:spPr><a:xfrm><a:ext/>. None if absent."""
    ext = pic.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}xfrm/{{{NS['a']}}}ext")
    if ext is None:
        return None
    try:
        return int(ext.get("cx", "0")), int(ext.get("cy", "0"))
    except (TypeError, ValueError):
        return None


def _pic_no_change_aspect(pic: ET.Element) -> bool:
    locks = pic.find(
        f"{{{NS['p']}}}nvPicPr/{{{NS['p']}}}cNvPicPr/{{{NS['a']}}}picLocks"
    )
    return bool(locks is not None and locks.get("noChangeAspect") == "1")


def _pic_name(pic: ET.Element) -> str:
    cnv = pic.find(f"{{{NS['p']}}}nvPicPr/{{{NS['p']}}}cNvPr")
    return cnv.get("name", "") if cnv is not None else ""


def _pic_embed_rids(pic: ET.Element) -> list[str]:
    """Return [primary_rId, *fallback_rIds]. <a:blip r:embed=…> is the
    raster fallback for SVG shapes; <asvg:svgBlip r:embed=…> points to
    the SVG itself."""
    rids: list[str] = []
    blip = pic.find(f"{{{NS['p']}}}blipFill/{{{NS['a']}}}blip")
    if blip is not None:
        primary = blip.get(f"{{{NS['r']}}}embed")
        if primary:
            rids.append(primary)
        svgblip = blip.find(f"{{{NS['a']}}}extLst/{{{NS['a']}}}ext/{{{NS['asvg']}}}svgBlip")
        if svgblip is not None:
            svg_rid = svgblip.get(f"{{{NS['r']}}}embed")
            if svg_rid:
                rids.append(svg_rid)
    return rids


# --------------------------------------------------------------------------- #
# audit
# --------------------------------------------------------------------------- #

def audit(pptx_path: str, tolerance: float) -> tuple[list[PicReport], list[str]]:
    """Return (per-picture reports, hard errors that prevented full audit)."""
    reports: list[PicReport] = []
    errors: list[str] = []
    try:
        zf = zipfile.ZipFile(pptx_path)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        return [], [f"cannot open {pptx_path}: {e}"]
    with zf:
        for slide_path in _slide_paths(zf):
            try:
                slide_xml = zf.read(slide_path)
            except KeyError:
                continue
            rels = _load_rels(zf, slide_path)
            for pic in _walk_pics(slide_xml):
                geom = _pic_geometry(pic)
                if geom is None or geom[0] == 0 or geom[1] == 0:
                    continue
                cx, cy = geom
                name = _pic_name(pic)
                rids = _pic_embed_rids(pic)
                if not rids:
                    errors.append(f"{slide_path}: <p:pic> '{name}' has no r:embed")
                    continue
                # Resolve every embed; prefer SVG intrinsic dims when present.
                best: tuple[str, float, float] | None = None  # (src_path, w, h)
                for rid in rids:
                    if rid not in rels:
                        continue
                    src_path, _raw = rels[rid]
                    try:
                        blob = zf.read(src_path)
                    except KeyError:
                        continue
                    dims = _intrinsic_dims(src_path, blob)
                    if dims is None:
                        continue
                    if best is None or src_path.lower().endswith(".svg"):
                        best = (src_path, dims[0], dims[1])
                if best is None:
                    errors.append(
                        f"{slide_path}: <p:pic> '{name}' — could not read intrinsic dims "
                        f"from any rId {rids}"
                    )
                    continue
                src_path, src_w, src_h = best
                src_aspect = src_w / src_h
                rendered_aspect = cx / cy
                ratio_error = abs(rendered_aspect / src_aspect - 1.0)
                no_change = _pic_no_change_aspect(pic)
                if ratio_error >= tolerance:
                    status = "fail"
                    note = (
                        f"rendered {rendered_aspect:.4f} vs source {src_aspect:.4f} "
                        f"({ratio_error * 100:.2f}% off) — distorted"
                    )
                elif not no_change:
                    status = "warn"
                    note = "within tolerance but no <a:picLocks noChangeAspect=\"1\">"
                else:
                    status = "ok"
                    note = ""
                reports.append(PicReport(
                    slide=slide_path,
                    shape_name=name,
                    src_path=src_path,
                    src_w=src_w,
                    src_h=src_h,
                    src_aspect=src_aspect,
                    cx_emu=cx,
                    cy_emu=cy,
                    rendered_aspect=rendered_aspect,
                    ratio_error=ratio_error,
                    no_change_aspect=no_change,
                    status=status,
                    note=note,
                ))
    return reports, errors


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _format_text_report(reports: list[PicReport], errors: list[str]) -> str:
    lines: list[str] = []
    fails = [r for r in reports if r.status == "fail"]
    warns = [r for r in reports if r.status == "warn"]
    oks = [r for r in reports if r.status == "ok"]
    lines.append(
        f"audit: {len(reports)} <p:pic> shapes — "
        f"{len(fails)} fail, {len(warns)} warn, {len(oks)} ok"
    )
    if errors:
        lines.append(f"audit: {len(errors)} hard error(s) prevented full coverage")
        for e in errors:
            lines.append(f"  ERROR  {e}")
    for r in fails:
        slide_id = re.search(r"slide(\d+)\.xml", r.slide)
        sid = slide_id.group(1) if slide_id else "?"
        lines.append(
            f"  FAIL   slide {sid}  {r.src_path}  "
            f"src={r.src_w:g}x{r.src_h:g} ({r.src_aspect:.4f})  "
            f"rendered cx:cy={r.cx_emu}:{r.cy_emu} ({r.rendered_aspect:.4f})  "
            f"err={r.ratio_error * 100:.2f}%"
        )
    for r in warns:
        slide_id = re.search(r"slide(\d+)\.xml", r.slide)
        sid = slide_id.group(1) if slide_id else "?"
        lines.append(
            f"  WARN   slide {sid}  {r.src_path}  "
            f"missing noChangeAspect=\"1\" (ratio within tolerance)"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("pptx", help="path to the rendered .pptx")
    p.add_argument(
        "--tolerance", type=float, default=0.01,
        help="max |rendered/source − 1| ratio error before failing (default: 0.01 = 1%%)",
    )
    p.add_argument("--json", action="store_true", help="emit JSON report on stdout")
    p.add_argument(
        "--warn-only", action="store_true",
        help="report fails but exit 0 (for diagnostic runs; default fails build on any mismatch)",
    )
    args = p.parse_args(argv)

    reports, errors = audit(args.pptx, args.tolerance)

    if args.json:
        payload = {
            "pptx": args.pptx,
            "tolerance": args.tolerance,
            "errors": errors,
            "pictures": [asdict(r) for r in reports],
            "summary": {
                "fail": sum(1 for r in reports if r.status == "fail"),
                "warn": sum(1 for r in reports if r.status == "warn"),
                "ok": sum(1 for r in reports if r.status == "ok"),
            },
        }
        print(json.dumps(payload, indent=2))
    else:
        print(_format_text_report(reports, errors))

    if errors and not reports:
        return 2
    if args.warn_only:
        return 0
    if any(r.status == "fail" for r in reports):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
