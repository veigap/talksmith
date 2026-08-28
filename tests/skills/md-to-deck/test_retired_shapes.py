#!/usr/bin/env python3
"""Tests for `build_html._retired_shapes()` — the stale-model *shape* guard.

Run:  python3 tests/skills/md-to-deck/test_retired_shapes.py

**Why this exists.** Removing the model's alias spellings (`image`→`media`, `layout`→`design`,
`aside`, `rows`→`cards`, and the `card-row`/`icon-list` template ids) made every model written
against the old contract render wrong. A retired *template* id is loud — it falls to `fallback` and
warns. A retired *field* name is silent: it is just a key nothing reads, so the picture or the cards
it carried vanish with nothing said. Measured on a real 21-slide deck, a pre-existing model lost
**8 of its 12 visuals** and warned about none of them.

The model is a build artifact the FILL step rewrites from `final.md` on every render, so the repair
is always "re-run FILL" — and that is what the guard says, refusing to render (exit 2) exactly the
way the `_source` freshness guard refuses a model that is stale in *content*. This one catches stale
in *shape*.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "md-to-deck"))
from build_html import _retired_shapes  # noqa: E402

RESULTS: list[tuple[str, bool]] = []


def check(name: str, model: dict, want: int, must_mention: list[str] | None = None) -> None:
    found = _retired_shapes(model)
    ok = len(found) == want
    if ok and must_mention:
        blob = " ".join(found)
        ok = all(m in blob for m in must_mention)
    RESULTS.append((name, ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: expected {want} finding(s), got {len(found)}")
    if not ok:
        for f in found:
            print(f"           {f}")


def m(*slides) -> dict:
    return {"slides": list(slides)}


# --- retired fields ------------------------------------------------------------------------------
check("image_on_a_composed_template_is_retired",
      m({"template": "content-image", "title": "t", "image": {"src": "a.png"}}), 1, ["`image`", "media"])
check("layout_is_retired",
      m({"template": "process", "title": "t", "layout": "image-left"}), 1, ["`layout`", "design"])
check("aside_is_retired",
      m({"template": "concept-breakdown", "title": "t", "aside": {"side": "left", "image": {}}}), 1, ["`aside`"])
check("rows_is_retired",
      m({"template": "concept-breakdown", "title": "t", "rows": [{"label": "a"}]}), 1, ["`rows`", "cards"])

# --- the fields that are NOT aliases on their owning template --------------------------------------
# Both of these were live regressions in the first cut of the guard: `matrix` is the one caught by
# the style-reference fixture, which is what that fixture is for.
check("image_full_keeps_its_own_image_field",
      m({"template": "image-full", "title": "t", "image": {"src": "a.png"}}), 0)
check("matrix_keeps_its_own_rows_field",
      m({"template": "matrix", "title": "t", "columns": ["a"], "rows": ["b"], "cells": [["x"]]}), 0)
check("but_rows_on_a_labeled_set_is_still_the_alias",
      m({"template": "concept-breakdown", "title": "t", "rows": [{"label": "a"}]}), 1, ["`rows`"])

# --- retired template ids -------------------------------------------------------------------------
check("card_row_is_retired",
      m({"template": "card-row", "title": "t", "cards": []}), 1, ["card-row", "format"])
check("icon_list_flags_both_its_id_and_its_items",
      m({"template": "icon-list", "title": "t", "rows": [{"label": "a"}]}), 2, ["icon-list", "`rows`"])

# --- the canonical shape is clean ------------------------------------------------------------------
check("a_current_model_has_no_findings",
      m({"template": "content-image", "title": "t", "design": "split-right",
         "media": {"src": "a.png"}, "facts": [{"body": "b"}]},
        {"template": "concept-breakdown", "title": "t", "format": "row",
         "cards": [{"label": "a", "body": "b"}]},
        {"template": "image-full", "title": "t", "image": {"src": "a.png"}}), 0)

# --- an empty retired field is not a finding (nothing was lost) ------------------------------------
check("empty_retired_field_is_not_a_finding",
      m({"template": "content-image", "title": "t", "design": "split-right",
         "media": {"src": "a.png"}, "layout": "", "rows": []}), 0)

# --- the real-deck shape that started this ---------------------------------------------------------
check("the_production_deck_that_lost_8_visuals",
      m(*([{"template": "content-image", "title": f"s{i}", "image": {"src": "a.png"}} for i in range(10)]
          + [{"template": "icon-list", "title": "x", "rows": [{"label": "a"}]}] * 2)), 14)


def main() -> int:
    fails = sum(1 for _, ok in RESULTS if not ok)
    print()
    if fails:
        print(f"{fails} test(s) FAILED.")
        return 1
    print(f"all {len(RESULTS)} retired-shape tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
