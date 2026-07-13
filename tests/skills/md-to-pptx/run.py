#!/usr/bin/env python3
"""Regenerate + check the md-to-pptx HTML style reference.

Renders `final.md` (a directive-forced deck with one slide per template type, plus edge
cases) through `build_html.py`, writes `style-reference.html` next to it, and asserts the
visual contract holds: every template type present, no fallbacks, no HTML bullets, and the
styled layer (icons, code surfaces, card strips, embedded SVG, present-mode) is emitted.

Run after any change to the HTML render or the strict style tokens:
    python3 tests/skills/md-to-pptx/run.py

Exit 0 = pass (and `style-reference.html` is refreshed for visual review); non-zero = fail.
"""
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "skills" / "md-to-pptx"))
import build_html  # noqa: E402

OUT = HERE / "style-reference.html"
EXPECTED_TYPES = {
    "divider", "agenda", "statement", "single-point", "concept-breakdown", "card-row",
    "icon-list", "process", "comparison", "stat", "figures", "image-grid", "content-image",
    "content+cards+image", "code-example", "callout", "content-text", "closing-cta",
    "closing-hero",
}


def main() -> int:
    rc = build_html.main(["--talk", str(HERE), "-o", str(OUT)])
    if rc != 0:
        print("FAIL: build_html did not exit 0")
        return 1
    # drop the transient icon cache — the html is self-contained
    import shutil
    shutil.rmtree(HERE / "output", ignore_errors=True)

    h = OUT.read_text(encoding="utf-8")
    tmpls = re.findall(r'· ([a-z+-]+)</span>', h)
    tally = Counter(tmpls)
    fails = []

    missing = EXPECTED_TYPES - set(tmpls)
    if missing:
        fails.append(f"missing template types: {sorted(missing)}")
    if tally.get("fallback"):
        fails.append(f"{tally['fallback']} slide(s) fell to fallback (a forced type didn't render)")
    if h.count("<li>"):
        fails.append(f"{h.count('<li>')} HTML bullets present — the invariant is cards, not bullets")
    for name, needle in [("inline icons", "<svg"), ("code surface", "codebox"),
                         ("card strip", "ncard"), ("callout box", 'class="callout'),
                         ("embedded svg", "imgph svg"), ("present mode", "present-btn"),
                         ("comparison table", 'class="compare"'), ("stat card", 'class="stat"')]:
        if needle not in h:
            fails.append(f"styled element missing: {name}")

    print(f"slides={len(tmpls)}  types={len(set(tmpls))}  tally={dict(tally)}")
    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"PASS — {OUT} refreshed for review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
