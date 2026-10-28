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
_FONT_RE = re.compile(r'font-family\s*=\s*"([^"]*)"')

# Monospace families worth asking for, best first. There is no family present on every machine:
# DejaVu ships with most Linux distributions and with **no** stock macOS, Andale and Courier New
# ship with macOS and not with a bare Linux container. So the family is resolved per machine
# rather than prescribed — see `resolve_mono_family`.
#
# `Menlo` is deliberately absent even though every macOS has it: it resolves, so nothing errors,
# but its hyphen draws at near-full-em width, so `a-b` renders as `a–b` and a YAML `---` fuses
# into a single rule. A diagram whose whole job is to quote a literal file then lies quietly.
_MONO_CANDIDATES = (
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Noto Sans Mono",
    "Andale Mono",
    "Courier New",
    "Nimbus Mono PS",
)

_PROBE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="80" viewBox="0 0 1200 80">'
    '<rect width="1200" height="80" fill="#ffffff"/>'
    '<text x="4" y="56" font-family="{fam}" font-size="40" fill="#000000">{txt}</text></svg>'
)


def _ink_width(mod, family: str, text: str) -> float | None:
    """How wide `text` actually draws in `family`, in pixels, as cairo draws it."""
    import io
    try:
        png = mod.svg2png(bytestring=_PROBE_SVG.format(fam=family, txt=text).encode(),
                          output_width=1200)
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("L")
        box = Image.eval(im, lambda v: 255 - v).getbbox()   # ink = anything darker than the page
    except Exception:
        return None
    return None if box is None else float(box[2] - box[0])


def renders_monospaced(mod, family: str) -> bool | None:
    """Does `family` actually draw monospaced *here*? None when the question can't be answered.

    cairo does not walk a CSS font stack the way a browser does: given
    `font-family="'DejaVu Sans Mono', monospace"` on a machine without DejaVu it takes the first
    name literally, fails to find it, and falls back to its own default sans — silently. Every
    code block, table and token trace in the diagram then draws proportional, the columns stop
    aligning, and nothing anywhere reports a problem. The SVG is valid, the PNG is written, the
    aspect audit passes, and the defect is visible only to someone looking at the picture who
    knows monospace was intended. That is the worst shape a bug can take, so this asks the
    renderer directly instead of trusting the name.

    The measurement is the definition: draw a run of the narrowest glyph and a run of the widest,
    and compare how far each run spans. A monospaced face gives both runs the same advance, so
    they differ only by one glyph's ink (a few percent). A proportional face draws the `M` run
    three to four times wider than the `i` run.
    """
    thin = _ink_width(mod, family, "i" * 24)
    wide = _ink_width(mod, family, "M" * 24)
    if not thin or not wide:
        return None
    return (wide / thin) < 1.35


def resolve_mono_family(mod) -> str | None:
    """The first of `_MONO_CANDIDATES` that this machine actually draws monospaced."""
    for fam in _MONO_CANDIDATES:
        if renders_monospaced(mod, fam):
            return fam
    return None


def _declared_mono_stacks(svg_text: str) -> list[str]:
    """Every distinct `font-family` in the SVG that asks for monospace, in document order."""
    seen, out = set(), []
    for raw in _FONT_RE.findall(svg_text):
        parts = [p.strip().strip("'\"") for p in raw.split(",") if p.strip()]
        if not parts or parts[-1].lower() != "monospace" or len(parts) < 2:
            continue                       # bare `monospace` is generic and always resolves
        if parts[0] not in seen:
            seen.add(parts[0])
            out.append(parts[0])
    return out


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

    warn_unresolved_mono(mod, svg)
    print(f"rasterized: {out} · {w}x{h} ({w/h:.2f}:1)")
    return 0


def warn_unresolved_mono(mod, svg: Path) -> list[str]:
    """Say so, loudly, when a monospace family the SVG asks for isn't drawing monospaced.

    A warning and not a failure: the PNG on disk is the best this machine can draw, and refusing
    to write it would leave the operator with nothing. But it must be *said* — this was found by
    an illustrator measuring glyph widths by hand after 28 diagrams had already shipped with
    every code block, table and token trace set in proportional type."""
    try:
        families = _declared_mono_stacks(svg.read_text(errors="replace"))
    except Exception:
        return []
    bad = [f for f in families if renders_monospaced(mod, f) is False]
    if not bad:
        return []
    have = resolve_mono_family(mod)
    fix = (f"Use '{have}' instead — it draws monospaced here."
           if have else "No candidate monospace family resolves on this machine; install one "
                        "(e.g. `brew install --cask font-dejavu`).")
    print(f"warning: {svg.name} asks for {', '.join(repr(f) for f in bad)} but cairo draws "
          f"{'them' if len(bad) > 1 else 'it'} PROPORTIONALLY — the family isn't installed and "
          f"cairo does not walk the rest of the stack. Every column in this diagram is misaligned. "
          f"{fix}", file=sys.stderr)
    return bad


def check() -> int:
    """Preflight: can this interpreter rasterize at all?

    Step 6 renders a batch, and cairosvg is only reached *after* the first SVG is written — so a
    machine without libcairo used to discover the problem halfway through, with SVGs on disk and
    no PNG beside any of them. One cheap question, asked before the batch starts, turns that into
    a message you act on before anything is written. Exit 0 = ready, 2 = install cairo first.
    """
    mod = _load_cairosvg()
    if mod is None:
        print(f"failed: cairosvg unavailable — this interpreter cannot rasterize\n{_INSTALL_HINT}",
              file=sys.stderr)
        return 2
    fam = resolve_mono_family(mod)
    if fam is None:
        print("failed: no monospace font resolves for cairo on this machine — every code block, "
              "table and token trace would draw proportionally, silently. Install one first "
              "(macOS: Andale Mono ships with the system; Linux: `apt install fonts-dejavu`).",
              file=sys.stderr)
        return 2
    print(f"ok: cairosvg available ({sys.executable})", file=sys.stderr)
    print(f"mono-family: {fam}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("svg", type=Path, nargs="?", help="the SVG to rasterize (omit with --check)")
    p.add_argument("-o", "--out", type=Path, help="output PNG path")
    p.add_argument("--width", type=int, help="output width in px; height follows the viewBox")
    p.add_argument("--check", action="store_true",
                   help="preflight only: verify cairosvg + libcairo are usable, then exit")
    a = p.parse_args(argv)
    if a.check:
        return check()
    if a.svg is None or a.out is None or a.width is None:
        p.error("svg, --out and --width are required (or pass --check on its own)")
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
