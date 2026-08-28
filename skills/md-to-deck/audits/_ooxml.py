"""OOXML reading — and model-walking — shared by the audits.

Five of the audits open the rendered `.pptx` and walk its slide XML, and they were each carrying
their own copy of the same three things: the namespace map, the relationship-file reader, and the
solid-fill colour reader. Identical code, three different names (`_slide_rels` / `_load_slide_rels`,
`_shape_solid_fill` / `_solid_fill_hex`) — which is how a fix lands in one audit and not the others.

Imported the way the polish skills import `_shared`:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _ooxml import NS, slide_rels, solid_fill_hex, read_png_dims

It also holds `model_strings`, which is not OOXML at all but has the same problem: two audits walk a
model slide for its content strings, and both had to remember the same non-obvious exclusion rule.

Only the genuinely shared plumbing lives here. What each audit *checks* stays in the audit — that is
the part worth reading per file.
"""
from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import PurePosixPath

# The four namespaces every slide walk needs. An audit that needs more (aspect_ratios reads embedded
# SVG) extends a copy: `NS_LOCAL = {**NS, "svg": …}` — never mutates this one.
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def slide_rels(zf: zipfile.ZipFile, slide_path: str) -> dict[str, str]:
    """`{r:id → target}` for one slide, from its sibling `_rels/<slide>.rels`.

    A slide with no rels part, or an unparseable one, yields `{}` — an audit reports what it can
    see, and a malformed relationship file is the render's defect to surface, not this reader's to
    raise on.
    """
    p = PurePosixPath(slide_path)
    rels_path = str(p.parent / "_rels" / (p.name + ".rels"))
    if rels_path not in zf.namelist():
        return {}
    try:
        root = ET.fromstring(zf.read(rels_path))
    except (ET.ParseError, KeyError):
        return {}
    out: dict[str, str] = {}
    for rel in root.findall(f"{{{NS['rel']}}}Relationship"):
        rid, target = rel.get("Id"), rel.get("Target", "")
        if rid and target:
            out[rid] = target
    return out


def solid_fill_hex(sp: ET.Element) -> str | None:
    """A shape's solid fill as uppercase `RRGGBB`, or `None`.

    Only a literal `srgbClr` counts: a theme-colour reference (`schemeClr`) resolves through the
    theme and is not a colour this shape asserts, so the palette audit must not read it as one.
    """
    sf = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}solidFill")
    if sf is None:
        return None
    clr = sf.find(f"{{{NS['a']}}}srgbClr")
    if clr is None:
        return None
    v = clr.get("val", "")
    return v.upper() if len(v) == 6 else None


def read_png_dims(blob: bytes) -> tuple[float, float] | None:
    """`(width, height)` from a PNG's IHDR, without decoding the image.

    The dimensions live at a fixed offset right after the signature, so this is a 24-byte read
    rather than a Pillow dependency in an audit that only needs a ratio.
    """
    if len(blob) < 24 or blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", blob[16:24])
    return (float(w), float(h)) if w and h else None


def model_strings(obj) -> list[str]:
    """Every content string under a model slide (or a whole model), depth-first.

    **Keys beginning with `_` are excluded, and that exclusion is load-bearing.** `_choice` is the
    classification trace, and it restates the slide's source text in its own rationale — so a line
    the fill step actually dropped would still turn up in the walk, and a coverage audit would
    cheerfully confirm its own blind spot. `_source` is a freshness stamp, not content, for the
    same reason.
    """
    out: list[str] = []

    def walk(o) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if not k.startswith("_"):
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, str):
            out.append(o)

    walk(obj)
    return out
