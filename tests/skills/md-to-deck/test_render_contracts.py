#!/usr/bin/env python3
"""Small render/audit contracts that each once failed silently.

Run:  python3 tests/skills/md-to-deck/test_render_contracts.py

  * a backslash escape (`P\\*`) opened an italic span instead of rendering a literal `*`;
  * `field_coverage` treated every `_macros.j2` field as consumed by every template — so `quote`,
    which calls no macro, dropped a `title` with nothing said — and exempted only two of the
    `_`-prefixed metadata keys;
  * `image-full` could not draw a code-panel `image` and dropped its `source` highlight;
  * `concept-columns` drew content-matched icons the catalog says it never uses;
  * the working-directory index sorted by render time, so touching an old class moved it first;
  * a card set sharing two diagrams had no `media` shape that held both, so one was dropped;
  * a PPTX import's icons and card frames were rendered as `figures`, and the only way to leave
    them out was a hand-written `deck-omit` per image — the model-side `_omitted` trace now waives
    decoration (closed vocabulary, listed, never read as a render), and `[decoration?]` flags an
    icon-sized raster or a formula strip the fill rendered as a per-item figure;
  * every card got a content-matched icon with no way to say "none" (`icon`/`icons: "none"`);
  * `figures` was always three columns, so two figures left a third of the slide empty;
  * a value-columns table styled its first column as row labels even when it was data.

No network: icons resolve offline (see test_icon_offline.py), and none of these slides needs one.
"""
from __future__ import annotations

import json
import re
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "md-to-deck"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(SKILL / "audits"))


class _NoNetwork(socket.socket):
    def __init__(self, *a, **k):
        raise OSError("network disabled for this test")


socket.socket = _NoNetwork

import html_style as h  # noqa: E402
import field_coverage as fc  # noqa: E402
import build_index as bi  # noqa: E402
import image_coverage as ic  # noqa: E402

FIXTURE = Path(__file__).resolve().parent


def t_backslash_escape():
    fails = []
    for src, want in [(r"P\* y P\*", "P* y P*"), (r"\*no italic\*", "*no italic*"),
                      (r"`a\*b`", r"<code>a\*b</code>"), (r"\`x\`", "`x`"),
                      ("*it*", "<i>it</i>")]:
        got = h._inline_md(src)
        if got != want:
            fails.append(f"  _inline_md({src!r}) = {got!r}, want {want!r}")
    return fails


def t_field_coverage():
    fails = []
    q = {"template": "quote", "quote": "x", "title": "Dropped title", "_note": {"a": 1}}
    got = fc.audit({"slides": [q]})
    if not got or got[0][2] != ["title"]:
        fails.append(f"  quote: want only `title` flagged (never `_note`), got {got}")
    img = {"template": "image-full", "title": "t", "image": {"src": "a.png"},
           "highlights": [{"kind": "source", "body": "s"}]}
    if fc.audit({"slides": [img]}):
        fails.append("  image-full: a `source` highlight is rendered, must not be flagged")
    img["highlights"].append({"kind": "takeaway", "body": "t"})
    got = fc.audit({"slides": [img]})
    if not got or not any("kind=takeaway" in x for x in got[0][2]):
        fails.append(f"  image-full: a non-source highlight is dropped and must be named, got {got}")
    stage = {"template": "process", "title": "t", "steps": [{"body": "a"}, {"body": "b"}],
             "lead": "l", "highlights": [{"kind": "note", "body": "n"}], "_choice": {}}
    if fc.audit({"slides": [stage]}):
        fails.append("  process: fields the shared stage renders must count as consumed")
    return fails


def _render(slide):
    with tempfile.TemporaryDirectory() as td:
        return h.render_model_slide(slide, Path(td) / ".icons")


def t_image_full():
    fails = []
    html = _render({"template": "image-full", "title": "t",
                    "image": {"code": "a --> b", "language": "text"},
                    "highlights": [{"kind": "source", "body": "Fuente: X"},
                                   {"kind": "takeaway", "body": "not here"}]})
    if "codebox" not in html:
        fails.append("  image-full: a code-panel `image` must render as a code panel")
    if "hl-source" not in html or "Fuente: X" not in html:
        fails.append("  image-full: the `source` highlight must render")
    if "not here" in html:
        fails.append("  image-full: only `source` highlights render")
    return fails


def t_media_picture_set():
    """`media: {images:[…]}` renders one frame per picture inside the one media box, on every
    template that takes media and on `image-full`; the audits see both pictures."""
    fails = []
    pair = [{"src": "images/pipeline.svg", "alt": "Pipeline"},
            {"src": "images/portrait.svg", "alt": "Portrait"}]
    cci = {"template": "content+cards+image", "title": "t", "design": "split-right",
           "cards": [{"label": "A", "body": "a"}, {"label": "B", "body": "b"}],
           "media": {"images": pair}}
    with tempfile.TemporaryDirectory() as td:
        html = h.render_model_slide(json.loads(json.dumps(cci)), Path(td) / ".icons", FIXTURE)
    media = html.split('class="smedia"', 1)[-1]
    if html.count('class="smedia"') != 1 or media.count('class="imgph svg"') != 2:
        fails.append("  content+cards+image: a picture pair must embed both pictures in one media box")
    for t, extra in [("content-image", {"facts": [{"body": "f"}]}), ("process", {"steps": [{"body": "s"}]})]:
        got = _render({"template": t, "title": "t", "design": "banded", "media": {"images": pair}, **extra})
        if got.split('class="smedia"', 1)[-1].count('class="imgph') != 2:
            fails.append(f"  {t}: `smedia` must draw a picture set on every media-taking template")
    full = _render({"template": "image-full", "title": "t", "image": {"images": pair}})
    if full.split('class="iffill"', 1)[-1].count('class="imgph') != 2:
        fails.append("  image-full: a picture-set `image` must draw both pictures in the fill")
    if fc.audit({"slides": [cci]}):
        fails.append(f"  field_coverage: a picture-set `media` satisfies content+cards+image, got "
                     f"{fc.audit({'slides': [cci]})}")
    final = "## t\n\n- **A** a\n\n![](images/pipeline.svg)\n![](images/portrait.svg)\n"
    if ic.audit(final, {"slides": [cci]}):
        fails.append("  image_coverage: both pictures of a set must count as present")
    cci["media"]["images"] = pair[:1]
    if ic.audit(final, {"slides": [cci]}) != ["portrait.svg"]:
        fails.append("  image_coverage: a picture dropped from the set must still be caught")
    return fails


def _png(path: Path, w: int, h: int) -> None:
    import struct
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                     + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00")


def t_decoration_omitted():
    fails = []
    final = ("## Tres modelos\n\n![](images/ico-a.png) **GANs** a\n\n![](images/ico-b.png) **Diffusion** b"
             "\n\n![](images/frame.png)\n\n![](images/formula.png)\n")
    cards = {"template": "concept-breakdown", "title": "Tres modelos",
             "cards": [{"label": "GANs", "body": "a", "icon": "none"},
                       {"label": "Diffusion", "body": "b", "icon": "blur_on"}],
             "_choice": {"signals": ["n_images=0", "decoration=3"], "src": "images/frame.png"}}
    if ic.audit(final, {"slides": [cards]}) != ["ico-a.png", "ico-b.png", "frame.png", "formula.png"]:
        fails.append("  image_coverage: a `src` inside `_choice` must not count as rendered")
    cards["_omitted"] = [{"src": "images/ico-a.png", "reason": "icon"},
                         {"src": "images/ico-b.png", "reason": "icon"},
                         {"src": "images/frame.png", "reason": "frame"},
                         {"src": "images/formula.png", "reason": "formula"}]
    if ic.audit(final, {"slides": [cards]}):
        fails.append(f"  image_coverage: `_omitted` decoration must waive, got "
                     f"{ic.audit(final, {'slides': [cards]})}")
    cards["_omitted"][2]["reason"] = "looks bad"
    if ic.audit(final, {"slides": [cards]}) != ["frame.png"]:
        fails.append("  image_coverage: an `_omitted` reason outside the vocabulary must waive nothing")
    if ic.model_omitted({"slides": [cards]})[1] != [("frame.png", "looks bad")]:
        fails.append("  image_coverage: an invalid `_omitted` reason must be reported")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "images").mkdir()
        _png(root / "images" / "ico.png", 70, 56)
        _png(root / "images" / "eq.png", 1600, 104)
        _png(root / "images" / "photo.png", 1404, 2106)
        fig = {"template": "figures", "title": "t", "figures": [
            {"image": {"src": "images/ico.png"}, "label": "A", "body": "a"},
            {"image": {"src": "images/eq.png"}, "label": "B", "body": "b"},
            {"image": {"src": "images/photo.png"}, "label": "C", "body": "c"}]}
        banded = {"template": "content-image", "title": "u", "design": "banded",
                  "media": {"src": "images/eq.png"}, "facts": [{"body": "f"}],
                  "_omitted": [{"src": "images/ico.png", "reason": "icon"}]}
        got = ic.decoration_suspects({"slides": [fig, banded]}, root)
    if len(got) != 2 or "ico.png" not in got[0] or "eq.png" not in got[1] or "slide 2" in " ".join(got):
        fails.append(f"  image_coverage: want an icon and a per-item strip flagged on slide 1 only "
                     f"(a full-width strip and an `_omitted` icon are fine), got {got}")
    return fails


def t_concept_columns_no_inferred_icon():
    html = _render({"template": "concept-columns", "title": "t",
                    "columns": [{"label": "Debate", "body": "Agents argue."},
                                {"label": "Mixture-of-Agents", "body": "Layers of agents."}]})
    return ['  concept-columns: drew an inferred icon'] if 'class="ic' in html else []


def t_icon_opt_out():
    """`icon: "none"` drops one item's icon, `icons: "none"` turns inference off for the slide
    (a named icon still draws), and no icon-bearing template leaves an empty slot behind."""
    fails = []
    cards = [{"label": "Speed", "body": "fast"}, {"label": "Cost", "body": "cheap"},
             {"label": "Scale", "body": "wide"}]
    def cb(**kw):
        return {"template": "concept-breakdown", "title": "t",
                "cards": json.loads(json.dumps(cards)), **kw}
    one = cb()
    one["cards"][0]["icon"] = "none"
    if _render(one).count('class="ic"') != 2:
        fails.append("  concept-breakdown: `icon: \"none\"` must drop exactly that card's icon")
    if _render(cb()).count('class="ic"') != 3:
        fails.append("  concept-breakdown: a missing `icon` must still be content-matched")
    named = cb(icons="none")
    named["cards"][1]["icon"] = "bolt"
    if _render(named).count('class="ic"') != 1:
        fails.append("  concept-breakdown: `icons: \"none\"` keeps only the icon an item names")
    for fmt, cls in [("grid", 'class="ic"'), ("editorial", 'class="ic"'), ("row", 'class="chip"')]:
        if cls in _render(cb(icons="none", format=fmt)):
            fails.append(f"  concept-breakdown/{fmt}: `icons: \"none\"` must emit no icon element")
    others = [{"template": "content+cards+image", "title": "t", "icons": "none",
               "cards": json.loads(json.dumps(cards[:2])), "media": {"src": "images/pipeline.svg"}},
              {"template": "closing-cta", "title": "t", "icons": "none",
               "items": [{"label": "Docs", "body": "x"}, {"label": "Repo", "body": "y"}]},
              {"template": "single-point", "title": "t",
               "point": {"label": "One", "body": "thing", "icon": "none"}}]
    for s in others:
        if 'class="ic"' in _render(s):
            fails.append(f"  {s['template']}: the opt-out must emit no icon element")
    if fc.audit({"slides": [cb(icons="none")]}):
        fails.append(f"  field_coverage: `icons` is a knob, not an ignored field, got "
                     f"{fc.audit({'slides': [cb(icons='none')]})}")
    css = (SKILL / "templates" / "html" / "theme.css").read_text(encoding="utf-8")
    if ".ccard:not(:has(>.ic))" not in css or ".eitem:not(:has(>.ic))" not in css:
        fails.append("  theme.css: an icon-less card must drop the icon track (no empty slot)")
    return fails


def t_figures_columns():
    """`figures` takes its column count from the number of figures, like `.cards`/`.stats` — a
    fixed three left a third of the slide empty under two."""
    fails = []
    css = (SKILL / "templates" / "html" / "theme.css").read_text(encoding="utf-8")
    want = {"only-child": "minmax(0,56%)", "nth-child(2):last-child": "repeat(2,1fr)",
            "nth-child(4):last-child": "repeat(2,1fr)"}
    for sel, cols in want.items():
        m = re.search(r"\.figs:has\(>\.figc:" + re.escape(sel) + r"\)[^{]*\{grid-template-columns:([^;}]+)", css)
        if not m or m.group(1) != cols:
            fails.append(f"  theme.css: .figs with {sel} must lay out as {cols}, got {m and m.group(1)}")
    two = {"template": "figures", "title": "t", "figures": [
        {"image": {"src": "images/pipeline.svg"}, "label": "A", "body": "a"},
        {"image": {"src": "images/pipeline.svg"}, "label": "B", "body": "b"}]}
    with tempfile.TemporaryDirectory() as td:
        html = h.render_model_slide(two, Path(td) / ".icons", FIXTURE)
    if html.count('class="figc"') != 2:
        fails.append("  figures: each figure must be a direct `.figc` child the count rules can see")
    return fails


def t_value_columns_factor():
    """The row-label column: explicit `columns[0].factor` always wins; unset, 3+ columns or an
    empty first header keep the classic factor column (saved models render unchanged), and a
    two-column table is two data columns at equal weight."""
    fails = []
    def vc(c0, n=2):
        rest = [{"header": f"C{i}", "cells": ["1", "2"]} for i in range(n - 1)]
        return {"template": "value-columns", "title": "t",
                "columns": [{**c0, "cells": ["x", "y"]}, *rest]}
    cases = [({"header": "A"}, 2, False), ({"header": "Factor", "factor": True}, 2, True),
             ({"header": ""}, 2, True), ({"header": "", "factor": False}, 2, False),
             ({"header": "Factor"}, 3, True), ({"header": "A", "factor": False}, 3, False)]
    for c0, n, fac in cases:
        got = 'class="compare fac"' in _render(vc(c0, n))
        if got != fac:
            fails.append(f"  value-columns: {n} columns, first {c0} → factor={fac}, rendered {got}")
    media = {"template": "concept-breakdown", "title": "t", "design": "split-right",
             "cards": [{"label": "a", "body": "b"}, {"label": "c", "body": "d"}],
             "media": {"columns": [{"header": "Situation", "factor": True, "cells": ["s"]},
                                   {"header": "Reach for", "cells": ["r"]}]}}
    if 'class="compare mtable fac"' not in _render(media):
        fails.append("  media table: `factor: true` must mark the row-label column there too")
    css = (SKILL / "templates" / "html" / "theme.css").read_text(encoding="utf-8")
    if re.search(r"(?<!\.fac )\.crow>span:first-child", css):
        fails.append("  theme.css: the row-label style must be scoped to `.compare.fac`")
    return fails


def t_index_order():
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name, date, cls in [("c10", "2026-05-20", "Clase 10"), ("x", "TBD", ""),
                                ("c2", "2026-03-11", "Clase 2"), ("c7", "2026-04-22", "Clase 7")]:
            d = root / "talks" / name / "output" / "html"
            d.mkdir(parents=True)
            (d / "index.html").write_text("x")
            (d / ".render.json").write_text(json.dumps(
                {"mode": "final", "slides": 1, "title": name, "class": cls, "date": date}))
        got = [e["title"] for e in bi.collect(root)]
        if got != ["c2", "c7", "c10", "x"]:
            fails.append(f"  index: want delivery order c2, c7, c10 then undated, got {got}")
    return fails


def main() -> int:
    tests = [t_backslash_escape, t_field_coverage, t_image_full, t_media_picture_set,
             t_decoration_omitted, t_concept_columns_no_inferred_icon, t_icon_opt_out,
             t_figures_columns, t_value_columns_factor, t_index_order]
    failed = 0
    for t in tests:
        fails = t()
        print(f"{'PASS' if not fails else 'FAIL'}  {t.__name__}")
        for f in fails:
            print(f)
        failed += bool(fails)
    if failed:
        print(f"\n{failed} contract(s) FAILED.")
        return 1
    print(f"\nall {len(tests)} render contracts pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
