#!/usr/bin/env python3
"""Rasterize an SVG to a PNG whose aspect ratio matches the SVG's viewBox.

Every PNG Step 6 produces goes through here:

  * the **deliverable** `images/<basename>.png` — the bytes the Step-7 PPTX renderer
    embeds (PIL can't decode SVG, so the .pptx references the PNG).
  * the **critique companion** `images/.critique/<basename>.png` — the only thing the
    blind `diagram-critic` ever sees.

A PNG whose aspect doesn't match the viewBox corrupts both: the deck embeds a distorted
or letterboxed picture, and the critic reviews a shape the audience will never see.

## cairosvg is required. There is no fallback, and that is deliberate.

`qlmanage` used to be the documented macOS fallback. It is gone, for two measured reasons:

1. **It letterboxes.** `-s N` does not mean "render N wide" — it fits the art into an
   N x N square and pads the short axis with *opaque white*. A 640x360 SVG comes back
   1200x1200 with white bands, not 1200x675. That square is what reached the deck.
2. **It doesn't agree with cairosvg.** Even after cropping the letterbox back to the
   viewBox ratio, its geometry diverges: on one of this repo's own fixtures the cropped
   qlmanage render put the ink 100px off from cairosvg's at identical dimensions.

A backend that draws differently isn't a fallback, it's a second renderer that disagrees
silently — and it would put the critic and the deck on different pixels. Better to fail
loudly and tell the operator to install cairo than to ship a diagram nobody reviewed.

The one thing that legitimately goes wrong with cairosvg is *finding* libcairo; that is
what `_load_cairosvg` exists to fix, and it is not a reason to reach for another tool.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import re
import sys
from pathlib import Path

# Where libcairo actually lives, when ctypes can't find it on its own.
_CAIRO_CANDIDATES = (
    "/opt/homebrew/lib/libcairo.2.dylib",   # Homebrew, Apple silicon
    "/usr/local/lib/libcairo.2.dylib",      # Homebrew, Intel
    "/usr/lib/x86_64-linux-gnu/libcairo.so.2",
    "/usr/lib/aarch64-linux-gnu/libcairo.so.2",
    "/usr/lib64/libcairo.so.2",
    "/usr/lib/libcairo.so.2",
)

_INSTALL_HINT = (
    "  Install it:  brew install cairo && pip install cairosvg\n"
    "               (Linux: apt install libcairo2 && pip install cairosvg)\n"
    "  On macOS `pip install cairosvg` alone is NOT enough — the package installs fine and\n"
    "  then fails at import, because the stock python3 (Xcode's) can't see Homebrew's\n"
    "  libcairo: ctypes searches dyld's default paths, which exclude /opt/homebrew/lib, and\n"
    "  SIP strips DYLD_* from Apple-signed interpreters. This script already works around\n"
    "  that by preloading the dylib — but the C library itself still has to be installed."
)

_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*"([^"]+)"')


def viewbox_ratio(svg_path: Path) -> float:
    """The width:height ratio the SVG declares. Raises if there isn't a usable one."""
    m = _VIEWBOX_RE.search(svg_path.read_text(errors="replace"))
    if not m:
        raise ValueError(f"no viewBox in {svg_path}")
    parts = re.split(r"[\s,]+", m.group(1).strip())
    if len(parts) != 4:
        raise ValueError(f"malformed viewBox in {svg_path}: {m.group(1)!r}")
    w, h = float(parts[2]), float(parts[3])
    if w <= 0 or h <= 0:
        raise ValueError(f"non-positive viewBox extent in {svg_path}: {w}x{h}")
    return w / h


def _load_cairosvg():
    """Import cairosvg, teaching it where libcairo is if it can't work that out itself.

    `ctypes.util.find_library()` searches dyld's default paths. On macOS those do not
    include /opt/homebrew/lib, and SIP strips DYLD_* from Apple-signed interpreters — so
    the stock `python3` cannot see a perfectly healthy Homebrew cairo. `pip install
    cairosvg` succeeds, the import raises OSError, and without this shim the whole
    pipeline would look like "cairosvg is unavailable" when it is in fact installed.

    Returns the module, or None if cairo genuinely isn't on the machine.
    """
    try:
        import cairosvg  # noqa: F401
        return cairosvg
    except OSError:
        pass          # library-not-found — worth searching the known locations
    except ImportError:
        return None   # package not installed at all

    lib = next((p for p in _CAIRO_CANDIDATES if Path(p).exists()), None)
    if not lib:
        return None
    try:
        ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
        _orig = ctypes.util.find_library
        ctypes.util.find_library = lambda name: (lib if "cairo" in name else _orig(name))
        import cairosvg  # noqa: F811
        return cairosvg
    except Exception:
        return None


def rasterize(svg: Path, out: Path, width: int, tolerance: float = 0.02) -> int:
    ratio = viewbox_ratio(svg)

    mod = _load_cairosvg()
    if mod is None:
        print(f"failed: cairosvg unavailable — cannot rasterize {svg}\n{_INSTALL_HINT}", file=sys.stderr)
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        mod.svg2png(url=str(svg), write_to=str(out), output_width=width)
    except Exception as e:
        print(f"failed: cairosvg could not render {svg}: {e}", file=sys.stderr)
        return 2
    if not out.exists() or out.stat().st_size == 0:
        print(f"failed: cairosvg wrote no bytes for {svg}", file=sys.stderr)
        return 2

    # Verify the bytes on disk have the shape the viewBox promised, rather than trusting it.
    try:
        from PIL import Image
        w, h = Image.open(out).size
    except Exception as e:
        print(f"failed: wrote {out} but can't read it back: {e}", file=sys.stderr)
        return 2

    drift = abs((w / h) - ratio) / ratio
    if drift > tolerance:
        print(f"failed: rendered {w}x{h} ({w/h:.3f}:1) but the viewBox declares {ratio:.3f}:1 "
              f"— {drift*100:.1f}% off. Refusing to ship a mis-shaped PNG; the deck would "
              f"embed it and the critic would review it.", file=sys.stderr)
        out.unlink(missing_ok=True)
        return 2

    print(f"rasterized: {out} · {w}x{h} ({w/h:.2f}:1)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("svg", type=Path)
    p.add_argument("-o", "--out", type=Path, required=True, help="output PNG path")
    p.add_argument("--width", type=int, required=True, help="output width in px; height follows the viewBox")
    a = p.parse_args(argv)
    if not a.svg.exists():
        print(f"failed: no such SVG: {a.svg}", file=sys.stderr)
        return 2
    try:
        return rasterize(a.svg, a.out, a.width)
    except ValueError as e:
        print(f"failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
