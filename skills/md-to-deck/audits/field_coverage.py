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
    "template", "section", "notes", "reveal", "highlights", "lang", "id", "_source",
    # consumed by the shared `stage` macro, so they are template-independent by construction:
    # `design` divides the canvas and `media` is what it places; `lead` is the title's sub-line,
    # emitted by the shared head block.
    "design", "media", "lead",
    # `_choice` is the classification trace (schemas/slide-model.md -> *The classification
    # trace*): metadata about *why* this template was picked, read by template_diversity.py
    # and the slide-classifier-critic, never by a renderer. Like `_source`, its being
    # unconsumed is the design, not a finding.
    "_choice",
    # `stats` is a band the shared `stage` macro renders under any content body (the
    # "stat pair as the lower band" composition), so like `highlights` it is consumed
    # regardless of template. The `stat` template renders its own and suppresses the band.
    "stats",
}

# Per-template consumed fields = the schema contract (required ∪ optional). Source of truth:
# schemas/slide-model.md → *Per-template field contract*. Keep in sync when a template gains or
# loses a field — and when the two disagree, the schema is what needs fixing, not this map: the
# schema is what the FILL step reads, so a field only this map knows about is one the model will
# never be told to produce.
#
# `build_html` is the finer-grained authority — it also validates field *values* and warns when a
# design rides a slide with no media (or media rides a slide with no design), which this set-based
# audit can't express.
_CONSUMES = {
    "section-agenda": {"title"},
    "divider": {"title", "number"},
    "statement": {"title", "sub"},
    # one labeled set; `format` is the arrangement that used to be three separate template ids.
    "concept-breakdown": {"title", "cards", "lead", "format"},
    "process": {"title", "steps"},
    "figures": {"title", "figures", "lead"},
    "image-grid": {"images", "title"},
    "image-full": {"title", "image", "lead"},
    "content-image": {"title", "facts"},
    "content+cards+image": {"title", "cards"},
    "value-columns": {"title", "columns"},
    # a column here is a whole explanation, not a cell: label + body + its own feature list,
    # its label, a closing example line, and the emphasis flag on at most one of them
    "concept-columns": {"title", "columns", "subtitle"},
    "stat": {"title", "stats", "lead"},
    "big-number": {"number", "caption", "title"},
    "quote": {"quote", "attribution"},
    "timeline": {"title", "milestones", "lead"},
    # `pro_label`/`con_label` override the localized column headers (pros-cons.j2 reads
    # `s.pro_label or L.pros`), so a deck can name the two sides itself.
    "pros-cons": {"title", "pros", "cons", "pro_label", "con_label"},
    # a cross-tab: the axis names and tick labels are content, not chrome to drop
    "matrix": {"title", "columns", "rows", "cells", "x_label", "y_label"},
    "quiz": {"question", "answer", "title", "options", "correct", "explanation", "answer_label"},
    "single-point": {"title", "point"},
    "callout": {"callout", "tone", "title"},
    "code-example": {"title", "code", "language", "explanation"},
    "content-text": {"title", "big", "panels"},
    "closing-hero": {"title", "body"},
    "closing-cta": {"title", "items"},
    # `fallback` renders whatever it can — never audited (a fallback slide is already a flagged
    # classification miss elsewhere).
}


# The **required** half of the same contract (`schemas/slide-model.md` -> *Per-template field
# contract*). `_CONSUMES` catches a field the template will ignore; this catches the mirror
# defect — a template missing the field that *defines* it. A `content+cards+image` with no
# `media` is not that template at all: it is a `concept-breakdown` that recorded a picture it
# doesn't have, and it renders as a card set with a hole where the image column belongs. That
# is a misclassification, and nothing looked for it (an absent field is invisible to a
# set-difference check, which is why it needs its own map).
#
# Alternatives are listed as tuples: any one satisfies the requirement — `content-image` genuinely
# accepts either text shape, and `image-full` names its own picture field `image` while every
# composed template takes `media`.
_REQUIRES = {
    "statement": ("title",),
    "concept-breakdown": ("title", "cards"),
    "process": ("title", "steps"),
    "figures": ("title", "figures"),
    "image-grid": ("images",),
    "image-full": ("title", ("image", "media")),
    "content-image": ("title", "media", ("facts", "lead")),
    "content+cards+image": ("title", "cards", "media"),
    "value-columns": ("title", "columns"),
    "concept-columns": ("title", "columns"),
    "stat": ("title", "stats"),
    "big-number": ("number", "caption"),
    "quote": ("quote",),
    "timeline": ("title", "milestones"),
    "pros-cons": ("title", "pros", "cons"),
    "matrix": ("title", "columns", "rows", "cells"),
    "quiz": ("question", "answer"),
    "single-point": ("title", "point"),
    "callout": ("callout", "tone"),
    "code-example": ("title", "code"),
    "content-text": ("title", "big", "panels"),
    "closing-hero": ("title",),
    "closing-cta": ("title", "items"),
    # `section-agenda`/`divider` need only a title, which every slide has; `fallback` is
    # already a flagged classification miss and requires nothing.
}


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return True


def _missing(slide: dict, template: str) -> list[str]:
    """Required fields the slide doesn't carry. A tuple of names is satisfied by any one of
    them — an either-or contract."""
    out = []
    for req in _REQUIRES.get(template, ()):
        names = req if isinstance(req, tuple) else (req,)
        if not any(_nonempty(slide.get(nm)) for nm in names):
            out.append(" | ".join(names))
    return out


def audit(model: dict) -> list[tuple[str, str, list[str], list[str]]]:
    """Return (slide_ref, template, [unconsumed non-empty fields], [missing required fields])
    for each offending slide."""
    out: list[tuple[str, str, list[str], list[str]]] = []
    for idx, s in enumerate(model.get("slides", [])):
        t = s.get("template", "fallback")
        if t not in _CONSUMES:                 # fallback / unknown → not audited
            continue
        allowed = _CONSUMES[t] | _UNIVERSAL
        extra = sorted(k for k, v in s.items() if k not in allowed and _nonempty(v))
        gone = _missing(s, t)
        if extra or gone:
            ref = s.get("title") or f"slide[{idx}]"
            out.append((str(ref)[:60], t, extra, gone))
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
        print("field_coverage: ok — every template gets the fields it needs, and nothing it ignores")
        return 0

    print(f"field_coverage: {len(offenders)} slide(s) whose fields don't match their template "
          f"(likely a misclassification — the content won't render):", file=sys.stderr)
    for ref, t, extra, gone in offenders:
        if gone:
            print(f"  - {t:22} {ref!r}: MISSING required → {', '.join(gone)} "
                  f"(a template without the field that defines it is the wrong template)",
                  file=sys.stderr)
        if extra:
            print(f"  - {t:22} {ref!r}: ignored → {', '.join(extra)}", file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
