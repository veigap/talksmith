#!/usr/bin/env python3
"""Regression tests for offline icon resolution — a deck must never render a bare shape.

Run:  python3 tests/skills/md-to-deck/test_icon_offline.py

## Why this file exists

`icon_for()` picks a Material Symbols *name*; `_svg()` then had to obtain the actual glyph from
the CDN or a warm cache. With no network and an empty cache it returned

    <svg viewBox="0 -960 960 960"><circle cx="480" cy="-480" r="360" .../></svg>

— a plain disc. The deck promised a semantic icon per concept and delivered a bullet, silently:
no warning, no error, and a slide about metacognition looked identical to one about payments.

Two things fix that and both are pinned below: a **bundled** icon subset (the offline floor) and
a resolution chain that ends at a real glyph with a warning, never at a shape.

Every test here runs with **sockets disabled**, so a passing run cannot be an artifact of the
machine happening to be online.
"""
from __future__ import annotations

import importlib
import shutil
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "md-to-deck"))

CIRCLE = 'circle cx="480" cy="-480" r="360"'      # the placeholder that must never come back


class _NoNetwork(socket.socket):
    """Any attempt to open a socket raises — stronger than pointing the CDN at a bad host."""

    def __init__(self, *a, **k):
        raise OSError("network disabled for this test")


def _fresh_module(offline=True):
    """Re-import html_style with sockets disabled and module state cleared, so no test inherits
    another's warm catalog / used-icon set."""
    if offline:
        socket.socket = _NoNetwork
    for m in ("html_style", "icon_fetch"):
        sys.modules.pop(m, None)
    h = importlib.import_module("html_style")
    h._CAT_INDEX = None
    return h


def _empty_cache():
    d = Path(tempfile.mkdtemp()) / ".icons"
    shutil.rmtree(d, ignore_errors=True)
    return d


def _check(svg, why, name=""):
    """Every icon must be a real glyph: a <path>, no placeholder circle, themeable."""
    out = []
    if "<path" not in svg:
        out.append(f"  {why}: no <path> in the rendered icon {name} -> {svg[:80]!r}")
    if CIRCLE in svg:
        out.append(f"  {why}: fell back to the placeholder circle {name}")
    if "currentColor" not in svg:
        out.append(f"  {why}: not themeable — no currentColor {name}")
    return out


def test_reproduction_case():
    """The reported slide: no network, empty cache, no author-supplied icon."""
    h = _fresh_module()
    cache = _empty_cache()
    h.load_catalog(cache)
    fails = []
    if h._CAT_INDEX:
        fails.append("  catalog should be unavailable offline (test would not exercise the seed)")
    name = h.icon_for(
        "El capital humano se vuelve tóxico cuando solo representa conocimiento y habilidades rutinarias.",
        "Su valor vuelve a crecer cuando desarrolla metacognición, creatividad, adaptación y juicio.")
    if name != "psychology":
        fails.append(f"  offline concept match: want 'psychology', got {name!r}")
    fails += _check(h._svg(name, cache), "reproduction case", name)
    if list(cache.glob("*.svg")):
        fails.append("  offline render must not populate the cache")
    return fails


def test_single_point_without_icon():
    """`single-point` with no `point.icon` — the renderer content-matches and still draws a glyph."""
    h = _fresh_module()
    cache = _empty_cache()
    h.load_catalog(cache)
    slide = {"template": "single-point", "title": "¿Qué hace valioso al capital humano?",
             "point": {"label": "El capital humano se vuelve tóxico cuando solo representa "
                                "conocimiento y habilidades rutinarias.",
                       "body": "Su valor vuelve a crecer cuando desarrolla metacognición, "
                               "creatividad, adaptación y juicio."}}
    html = h.render_model_slide(slide, cache)
    fails = _check(html, "single-point without icon")
    if not slide["point"].get("icon"):
        fails.append("  the renderer should have resolved and recorded an icon on the point")
    return fails


def test_single_point_with_icon():
    """An author-supplied `point.icon` is honoured, not overwritten by content matching."""
    h = _fresh_module()
    cache = _empty_cache()
    h.load_catalog(cache)
    slide = {"template": "single-point", "title": "t",
             "point": {"label": "l", "body": "b", "icon": "psychology"}}
    html = h.render_model_slide(slide, cache)
    fails = _check(html, "single-point with icon")
    if slide["point"]["icon"] != "psychology":
        fails.append(f"  suggested icon was replaced: {slide['point']['icon']!r}")
    want = h._svg("psychology", cache)
    if want not in html:
        fails.append("  rendered glyph is not the requested psychology icon")
    return fails


def test_icon_list_three_concepts():
    """Three distinct concepts on one slide → three real, *different* glyphs."""
    h = _fresh_module()
    cache = _empty_cache()
    h.load_catalog(cache)
    slide = {"template": "icon-list", "title": "t", "rows": [
        {"label": "Seguridad de los datos", "body": "cifrado y control de acceso"},
        {"label": "Creatividad", "body": "imaginar soluciones originales"},
        {"label": "Juicio profesional", "body": "criterio ético para decidir"},
    ]}
    html = h.render_model_slide(slide, cache)
    fails = _check(html, "icon-list")
    names = [r.get("icon") for r in slide["rows"]]
    if len(set(names)) != 3:
        fails.append(f"  icons repeat within one slide: {names}")
    if any(not n for n in names):
        fails.append(f"  a row got no icon: {names}")
    glyphs = {h._svg(n, cache) for n in names}
    if len(glyphs) != 3:
        fails.append(f"  distinct names resolved to the same glyph: {names}")
    return fails


def test_unknown_icon_warns_and_substitutes():
    """A name in no catalog and no bundle → a real generic glyph plus a warning naming both."""
    h = _fresh_module()
    cache = _empty_cache()
    fails = []
    import io
    from contextlib import redirect_stderr
    buf = io.StringIO()
    with redirect_stderr(buf):
        svg = h._svg("definitely_not_an_icon_xyz", cache)
    fails += _check(svg, "unknown icon", "definitely_not_an_icon_xyz")
    err = buf.getvalue()
    if "definitely_not_an_icon_xyz" not in err:
        fails.append(f"  warning must name the requested icon; got {err!r}")
    if h._GENERIC_ICON not in err:
        fails.append(f"  warning must name the fallback used; got {err!r}")
    if h._svg(h._GENERIC_ICON, cache) != svg:
        fails.append("  unknown icon should render exactly the generic icon")
    return fails


def test_cached_icon_is_used():
    """A warm cache entry is served as-is — the bundled set never shadows it."""
    h = _fresh_module()
    cache = _empty_cache()
    cache.mkdir(parents=True, exist_ok=True)
    marker = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960">'
              '<path d="M1 2 L3 4 Z" data-marker="cached"/></svg>')
    (cache / "psychology.outlined.DA1B2E.svg").write_text(marker, encoding="utf-8")
    svg = h._svg("psychology", cache)
    fails = _check(svg, "cached icon", "psychology")
    if 'data-marker="cached"' not in svg:
        fails.append("  cache must win over the bundled copy")
    return fails


def test_alias_for_catalog_only_names():
    """`insights` is in Google's catalog but not in the CDN package — it must still draw."""
    h = _fresh_module()
    cache = _empty_cache()
    fails = []
    for name in ("insights", "message", "business"):
        fails += _check(h._svg(name, cache), "catalog-only name", name)
    return fails


def test_every_reachable_name_is_bundled():
    """Every name the offline paths can produce must exist in the bundled set — otherwise the
    offline floor has a hole that only shows up on someone's plane."""
    h = _fresh_module()
    from icon_fetch import bundled_icon
    need = {n for _, n in h._SEED} | set(h._FALLBACK_ICONS) | set(h._HL_ICON.values())
    need |= set(h._ICON_ALIAS.values()) | {h._DEFAULT_ICON, h._GENERIC_ICON}
    missing = sorted(n for n in need if not bundled_icon(n))
    return [f"  not bundled: {missing}"] if missing else []


def test_no_external_urls():
    """A rendered icon must not *load* anything off-host — the deck stays self-contained.

    `xmlns="http://www.w3.org/2000/svg"` is excluded on purpose: it is a namespace identifier, not
    a fetch. What would break offline delivery is a reference that resolves at display time, so
    those are what this looks for.
    """
    import re as _re
    h = _fresh_module()
    cache = _empty_cache()
    h.load_catalog(cache)
    svg = h._svg(h.icon_for("Seguridad de los datos", "cifrado"), cache)
    bad = _re.findall(r'(?:href|src)\s*=\s*"https?://[^"]*"', svg)
    bad += _re.findall(r'url\(\s*["\']?https?://[^)]*\)', svg)
    bad += _re.findall(r'@import[^;]*https?://[^;]*', svg)
    return [f"  external reference in icon markup: {bad}"] if bad else []


TESTS = [
    ("reproduction case (offline, empty cache)", test_reproduction_case),
    ("single-point without point.icon", test_single_point_without_icon),
    ("single-point with point.icon=psychology", test_single_point_with_icon),
    ("icon-list, three concepts", test_icon_list_three_concepts),
    ("unknown icon warns + substitutes", test_unknown_icon_warns_and_substitutes),
    ("previously cached icon", test_cached_icon_is_used),
    ("catalog-only names resolve via alias", test_alias_for_catalog_only_names),
    ("every reachable name is bundled", test_every_reachable_name_is_bundled),
    ("no external URLs in icon markup", test_no_external_urls),
]


def main() -> int:
    failures = []
    for name, fn in TESTS:
        try:
            fs = fn()
        except Exception as e:                      # noqa: BLE001 — a crash is a failure
            fs = [f"  raised {type(e).__name__}: {e}"]
        if fs:
            failures.append(f"{name}\n" + "\n".join(fs))
    if failures:
        print(f"FAIL — {len(failures)} of {len(TESTS)} groups:\n" + "\n".join(failures))
        return 1
    print(f"ok — {len(TESTS)} offline-icon groups pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
