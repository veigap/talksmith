#!/usr/bin/env python3
"""Preflight: flag model fields the chosen template will silently ignore.

Why this exists:
    Each template renders a fixed set of fields (its `schemas/slide-model.md` contract). When the
    FILL step puts a *content* field on a slide whose template has no slot for it — a second image
    on `content-image` (which renders one `image`, not `images`), a banner image on `divider` /
    `statement` (full-bleed, no image field) — the field is dropped with no error and the slide
    renders missing content. This audit compares each slide's populated fields against the set its
    template consumes and reports the leftovers, so a misclassification surfaces before rendering.

    It is the model-side complement of `block_coverage.py` (which checks the *rendered .pptx*). It
    needs only the model, so it guards every mode including `html-strict`.

Advisory by default (exit 0) — an unconsumed field usually means the slide was classified into the
wrong template, a judgment call the render shouldn't hard-block on. Pass `--strict` to exit 1.

Usage:
    python3 field_coverage.py <slide-model.json> [--strict]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Fields any content slide may legitimately carry (chrome / cross-cutting), consumed regardless of
# template by the shared `stage` macro or the renderer itself. Never flagged.
_UNIVERSAL = {
    "template", "section", "notes", "reveal", "highlights", "aside", "lang", "id", "_source",
}

# Per-template consumed fields = the schema contract (required ∪ optional) PLUS a few extras a
# template renders that the schema table omits (e.g. `divider` draws `number`). Source of truth for
# the schema half: schemas/slide-model.md → *Per-template field contract*. Keep in sync when a
# template gains/loses a field.
_CONSUMES = {
    "section-agenda": {"title"},
    "divider": {"title", "number"},
    "statement": {"title", "sub"},
    "concept-breakdown": {"title", "cards"},
    "card-row": {"title", "cards", "lead"},
    "icon-list": {"title", "rows", "lead"},
    "process": {"title", "steps", "lead", "image"},
    "figures": {"title", "figures", "lead"},
    "image-grid": {"images", "title"},
    "content-image": {"title", "image", "facts", "lead", "layout"},
    "content+cards+image": {"title", "cards", "image", "lead"},
    "comparison": {"title", "columns"},
    "stat": {"title", "stats", "lead"},
    "big-number": {"number", "caption", "title"},
    "quote": {"quote", "attribution"},
    "timeline": {"title", "milestones", "lead"},
    "pros-cons": {"title", "pros", "cons"},
    "quiz": {"question", "answer", "title", "options", "correct", "explanation", "image", "answer_label"},
    "single-point": {"title", "point"},
    "callout": {"callout", "tone", "title"},
    "code-example": {"title", "code", "language", "explanation"},
    "content-text": {"title", "big", "panels"},
    "closing-hero": {"title", "body"},
    "closing-cta": {"title", "items"},
    # `fallback` renders whatever it can — never audited (a fallback slide is already a flagged
    # classification miss elsewhere).
}


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return True


def audit(model: dict) -> list[tuple[str, str, list[str]]]:
    """Return (slide_ref, template, [unconsumed non-empty fields]) for each offending slide."""
    out: list[tuple[str, str, list[str]]] = []
    for idx, s in enumerate(model.get("slides", [])):
        t = s.get("template", "fallback")
        if t not in _CONSUMES:                 # fallback / unknown → not audited
            continue
        allowed = _CONSUMES[t] | _UNIVERSAL
        extra = sorted(k for k, v in s.items() if k not in allowed and _nonempty(v))
        if extra:
            ref = s.get("title") or f"slide[{idx}]"
            out.append((str(ref)[:60], t, extra))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model", type=Path, help="path to slide-model.json")
    ap.add_argument("--strict", action="store_true", help="exit 1 when unconsumed fields are found (default: warn, exit 0)")
    args = ap.parse_args(argv)

    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"field_coverage: cannot read model {args.model}: {e}", file=sys.stderr)
        return 2

    offenders = audit(model)
    if not offenders:
        print(f"field_coverage: ok — every populated field is consumed by its template")
        return 0

    print(f"field_coverage: {len(offenders)} slide(s) carry field(s) their template will ignore "
          f"(likely a misclassification — the content won't render):", file=sys.stderr)
    for ref, t, extra in offenders:
        print(f"  - {t:22} {ref!r}: ignored → {', '.join(extra)}", file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
