#!/usr/bin/env python3
"""Small render/audit contracts that each once failed silently.

Run:  python3 tests/skills/md-to-deck/test_render_contracts.py

  * a backslash escape (`P\\*`) opened an italic span instead of rendering a literal `*`;
  * `field_coverage` treated every `_macros.j2` field as consumed by every template — so `quote`,
    which calls no macro, dropped a `title` with nothing said — and exempted only two of the
    `_`-prefixed metadata keys;
  * `image-full` could not draw a code-panel `image` and dropped its `source` highlight;
  * `concept-columns` drew content-matched icons the catalog says it never uses;
  * the working-directory index sorted by render time, so touching an old class moved it first.

No network: icons resolve offline (see test_icon_offline.py), and none of these slides needs one.
"""
from __future__ import annotations

import json
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


def t_concept_columns_no_inferred_icon():
    html = _render({"template": "concept-columns", "title": "t",
                    "columns": [{"label": "Debate", "body": "Agents argue."},
                                {"label": "Mixture-of-Agents", "body": "Layers of agents."}]})
    return ['  concept-columns: drew an inferred icon'] if 'class="ic' in html else []


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
    tests = [t_backslash_escape, t_field_coverage, t_image_full,
             t_concept_columns_no_inferred_icon, t_index_order]
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
