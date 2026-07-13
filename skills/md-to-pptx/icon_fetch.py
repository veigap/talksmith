"""Fetch a Material Symbols (outlined) icon SVG **by name, on demand** — no bundled icon set.

Talksmith does not ship or generate an icon library. Per-concept icons (the §7.2.1
`concept-breakdown` glyph, the §7.4/§7.5 card icons) are **content-matched**: the caller
picks the Material Symbols name that fits the concept (e.g. `shield` for security, `payments`
for cost, `schedule` for time, `database` for data, `group` for people, `code`, `lightbulb`),
and this fetches just that one icon from the jsdelivr CDN, caches it, optionally recolors it
to a brand hex, and returns the local path. A deck needs only a handful of icons, so the
render pulls exactly those — never the whole set.

Material Symbols are Apache-2.0 (safe to embed in a delivered deck). The **outlined** weight-400
variant is clean 2px line-art, matching the strict §17.2 line-art spec.

Usage:
    python3 icon_fetch.py <name> [<name> …] --cache <dir> [--color DA1B2E] [--style outlined]
    → prints one local SVG path per line (fetched or cached).

    from icon_fetch import fetch_icon
    p = fetch_icon("shield", cache_dir, color="3B3535")

Network is required only on a cache miss. Offline / fetch failure returns None (the caller
falls back to a plain card — the icon is an enhancement, never a hard dependency).
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CDN = "https://cdn.jsdelivr.net/npm/@material-symbols/svg-{weight}/{style}/{name}.svg"
_SLUG_RE = re.compile(r"[^a-z0-9_]")


def _slug(name: str) -> str:
    return _SLUG_RE.sub("", name.strip().lower().replace("-", "_").replace(" ", "_"))


def _recolor(svg: str, color: str) -> str:
    """Set the fill on the root <svg> so every child path inherits the brand colour.

    Material SVGs are a single black `<path>` with no explicit fill; a root `fill` applies.
    """
    hexv = color if color.startswith("#") else "#" + color
    return re.sub(r"<svg\b", f'<svg fill="{hexv}"', svg, count=1)


def fetch_icon(name: str, cache_dir, weight: int = 400, style: str = "outlined",
               color: str | None = None, timeout: int = 10) -> Path | None:
    """Return a local path to the named Material Symbols icon (cached), or None on failure."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug(name)
    if not slug:
        return None
    suffix = f".{color.lstrip('#')}" if color else ""
    dest = cache_dir / f"{slug}.{style}{suffix}.svg"
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    url = CDN.format(weight=weight, style=style, name=slug)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "talksmith-icon-fetch"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            svg = r.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    if "<svg" not in svg:
        return None
    if color:
        svg = _recolor(svg, color)
    dest.write_text(svg, encoding="utf-8")
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="+", help="Material Symbols icon name(s)")
    ap.add_argument("--cache", type=Path, required=True, help="cache directory for fetched SVGs")
    ap.add_argument("--color", default=None, help="recolor hex, e.g. DA1B2E (default: leave black)")
    ap.add_argument("--style", default="outlined", help="outlined | rounded | sharp (default outlined)")
    ap.add_argument("--weight", type=int, default=400)
    args = ap.parse_args(argv)
    rc = 0
    for name in args.names:
        p = fetch_icon(name, args.cache, weight=args.weight, style=args.style, color=args.color)
        if p:
            print(p)
        else:
            print(f"failed: {name}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
