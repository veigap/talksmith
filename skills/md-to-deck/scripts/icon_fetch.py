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
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CDN = "https://cdn.jsdelivr.net/npm/@material-symbols/svg-{weight}/{style}/{name}.svg"
# Icons bundled with the plugin (Apache-2.0, see icons/NOTICE) — the offline floor. A deck must
# render real glyphs with no network and an empty cache, so a curated set covering the seed map,
# the neutral fallbacks and the common concepts ships in the repo. Consulted only *after* the
# cache and the network, so an online render still picks any icon in the full catalog.
BUNDLED_DIR = Path(__file__).resolve().parent / "icons"
# The full Material Symbols catalog metadata (icon name + English search tags + categories +
# popularity) — the source of truth for content-matched icon selection, instead of a hardcoded map.
CATALOG_URL = "https://fonts.google.com/metadata/icons?incomplete=true"
_SLUG_RE = re.compile(r"[^a-z0-9_]")


def fetch_catalog(cache_dir, timeout: int = 20) -> dict | None:
    """Return the Material Symbols catalog as `{name: {"tags": [...], "pop": float}}` (cached).

    Fetched once from Google Fonts metadata and cached to `<cache>/_catalog.json`. Returns None
    on failure (offline) — the caller falls back to a minimal built-in seed. Never committed.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / "_catalog.json"
    if dest.is_file() and dest.stat().st_size > 0:
        try:
            return json.loads(dest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    try:
        req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "talksmith-icon-fetch"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    raw = raw[raw.find("{"):]                       # strip the )]}' XSSI guard prefix
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    cat: dict[str, dict] = {}
    for it in data.get("icons", []):
        name = it.get("name")
        if not name:
            continue
        tags = {t.lower() for t in it.get("tags", [])} | {c.lower() for c in it.get("categories", [])}
        tags.add(name.replace("_", " "))
        prev = cat.get(name)
        if prev is None or it.get("popularity", 0) > prev["pop"]:
            cat[name] = {"tags": sorted(tags), "pop": float(it.get("popularity", 0))}
    try:
        dest.write_text(json.dumps(cat), encoding="utf-8")
    except OSError:
        pass
    return cat


def _slug(name: str) -> str:
    return _SLUG_RE.sub("", name.strip().lower().replace("-", "_").replace(" ", "_"))


def _recolor(svg: str, color: str) -> str:
    """Set the fill on the root <svg> so every child path inherits the brand colour.

    Material SVGs are a single black `<path>` with no explicit fill; a root `fill` applies.
    """
    hexv = color if color.startswith("#") else "#" + color
    return re.sub(r"<svg\b", f'<svg fill="{hexv}"', svg, count=1)


def bundled_icon(name: str, style: str = "outlined") -> Path | None:
    """Return the plugin-bundled SVG for `name`, or None if this icon isn't in the shipped set.

    No network, no cache, no side effects — the offline floor for `fetch_icon`, and the reason a
    deck built with no connectivity still shows real glyphs instead of a placeholder.
    """
    slug = _slug(name)
    if not slug:
        return None
    p = BUNDLED_DIR / f"{slug}.{style}.svg"
    return p if p.is_file() and p.stat().st_size > 0 else None


def fetch_icon(name: str, cache_dir, weight: int = 400, style: str = "outlined",
               color: str | None = None, timeout: int = 10) -> Path | None:
    """Return a local path to the named Material Symbols icon, or None if it can't be resolved.

    Resolution order: **cache → network → bundled**. The bundled set is last so that an online
    render still gets any icon in the full catalog; it only catches the offline / fetch-failure
    case, where the alternative is no icon at all.
    """
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
            svg = r.read().decode("utf-8") if r.status == 200 else ""
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        svg = ""
    if "<svg" not in svg:
        return bundled_icon(slug, style)        # offline, or a name the CDN doesn't carry
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
