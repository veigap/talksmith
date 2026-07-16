"""Audit that no enumeration slide in `slide-model.json` carries a lone item.

Why this exists:
    Several templates render a *set* of parallel items in a fixed grid:
    `concept-breakdown`/`card-row`/`content+cards+image` cards, `icon-list`
    rows, `stat` stats, `content-text` panels, etc. Their layout is built
    for two or more — e.g. `content-text`'s panel strip is `repeat(3,1fr)`,
    so a single panel renders as a lonely third-width card at the bottom.

    When the FILL step (LLM) drops a slide's punchline into a one-item
    enumeration, the result is not a render bug — the template does exactly
    what it is told — it is a *misclassification*: a lead + one restatement
    is `single-point`, not a one-panel `content-text` (the catalog's
    `labeled_items == 1 -> single-point` rule). The catalog already forbids
    it in prose; nothing enforced it. html-strict runs no deck-parsing
    audits, so a degenerate model shipped straight to the deck with a
    punchline shrunk into a secondary card.

    This is the deterministic catch. It reads the model alone (the shared IR
    for both the HTML and PPTX renderers), so it guards every mode, and it
    runs before any human or LLM visual review begins.

What it does:
    Walks each slide in `slide-model.json`. For a slide whose `template` is
    an enumeration template, counts its enumeration field. Fewer than the
    template's floor (2 for every enumeration — a set needs two) is a
    `[degenerate-enum]` failure naming the slide, the count, and the
    single-item template it should have been instead.

    Enumeration fields audited (template -> field):

      concept-breakdown, card-row, content+cards+image -> cards
      icon-list      -> rows
      process        -> steps
      figures        -> figures
      stat           -> stats
      timeline       -> milestones
      comparison     -> columns
      closing-cta    -> items
      content-text   -> panels

    Not audited: templates with no parallel set (`single-point`, `callout`,
    `content-image`, `code-example`, `quiz`, `fallback`, `section-agenda`,
    cover). A missing field counts as zero and fails — a `stat` with no
    `stats` is as broken as one with a single stat.

Usage:
    python3 audits/degenerate_enum.py <slide-model.json> [--json] [--warn-only]

Exit codes:
    0  no degenerate enumerations
    1  one or more found; build should stop and the model be restructured
    2  audit could not run (file missing, malformed)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

# template -> (enumeration field, floor). Floor is 2 for every entry: a set of
# parallel items needs at least two; one item is the degenerate case this audit
# exists to catch. The single-item template to reach for instead is in ADVICE.
ENUM_FIELD = {
    "concept-breakdown": ("cards", 2),
    "card-row": ("cards", 2),
    "content+cards+image": ("cards", 2),
    "icon-list": ("rows", 2),
    "process": ("steps", 2),
    "figures": ("figures", 2),
    "stat": ("stats", 2),
    "timeline": ("milestones", 2),
    "comparison": ("columns", 2),
    "closing-cta": ("items", 2),
    "content-text": ("panels", 2),
}

# What a lone-item slide most likely should have been — steers the repair.
ADVICE = {
    "content-text": "single-point (lead + one point), or add the missing supporting panels",
    "concept-breakdown": "single-point (one labeled item)",
    "card-row": "single-point (one labeled item)",
    "content+cards+image": "content-image (one image + prose), or single-point",
    "icon-list": "single-point (one labeled item)",
    "stat": "single-point, or a `big` number in another template",
    "figures": "a single-image template (content-image)",
    "process": "single-point — a one-step process is not a process",
    "timeline": "single-point — a one-milestone timeline is not a timeline",
    "comparison": "single-point — a one-column comparison compares nothing",
    "closing-cta": "single-point (one call to action)",
}


@dataclass
class Degenerate:
    index: int          # 0-based position in model["slides"]
    title: str
    template: str
    field: str
    count: int
    floor: int

    def fmt(self) -> str:
        advice = ADVICE.get(self.template, "single-point")
        return (f'[degenerate-enum]: slide {self.index + 1} "{self.title}" — '
                f"{self.template} has {self.count} {self.field} "
                f"(needs ≥{self.floor}); a lone item renders as a stray "
                f"grid cell → restructure as {advice}")


def _count(value) -> int:
    return len(value) if isinstance(value, list) else 0


def audit_model(path: str) -> list[Degenerate]:
    """Parse the model and return every degenerate enumeration slide."""
    with open(path, encoding="utf-8") as fh:
        model = json.load(fh)
    if not isinstance(model, dict):
        raise ValueError("slide-model root is not an object")

    found: list[Degenerate] = []
    for i, slide in enumerate(model.get("slides", [])):
        if not isinstance(slide, dict):
            continue
        spec = ENUM_FIELD.get(slide.get("template", ""))
        if not spec:
            continue
        field, floor = spec
        n = _count(slide.get(field))
        if n < floor:
            found.append(Degenerate(
                index=i,
                title=str(slide.get("title", "") or "")[:60],
                template=slide["template"],
                field=field,
                count=n,
                floor=floor,
            ))
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("model_json", help="slide-model.json (the model to check)")
    p.add_argument("--json", action="store_true",
                   help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report degenerate slides but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    try:
        found = audit_model(args.model_json)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"audit_degenerate_enum: cannot read {args.model_json}: {e}",
              file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "model_json": args.model_json,
            "summary": {"degenerate": len(found)},
            "degenerate": [asdict(d) for d in found],
        }, indent=2))
    elif not found:
        print("audit_degenerate_enum: ok — no lone-item enumerations")
    else:
        print(f"audit_degenerate_enum: {len(found)} degenerate enumeration(s)")
        for d in found:
            print("  " + d.fmt())

    if args.warn_only:
        return 0
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
