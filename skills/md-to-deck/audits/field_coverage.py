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
import re
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

# Per-template consumed fields, **derived from the templates rather than restated**.
#
# This used to be a hand-maintained map of template id -> field set, kept in sync with
# `schemas/slide-model.md` by discipline. It drifted, as that arrangement always does: five of the
# twenty-five entries were wrong by the time anyone measured — `closing-cta` declared an `items`
# field its template never reads, and `callout`, `quote`, `fallback` and `single-point` were each
# missing fields their templates do read. An audit whose job is to spot unconsumed fields was
# itself reporting the wrong answer for a fifth of the deck.
#
# A template's consumed set is not a fact that needs stating: it is *visible in the template*.
# Every one reads its schema fields directly off the slide as `s.<field>`, so scanning the file
# for that pattern is the answer, and it cannot be stale. The shared `_macros.j2` is folded into
# every content template because `stage()` reads a handful of fields on every slide.
#
# Read as text, not imported: this audit is stdlib-only and CLI-safe, and importing `html_style`
# to reach `_TMPL` would drag `jinja2` in as a hard dependency of a preflight check.
_HTML = Path(__file__).resolve().parent.parent
_TPL_DIR = _HTML / "templates" / "html"
# Both access forms, because both are load-bearing. A template normally reads `s.field`, but
# a field whose name collides with a dict method — `items`, `keys`, `values`, `get` — must be
# read as `s['field']` or Jinja hands back the bound method instead of the content. Matching
# only the dotted form reported `closing-cta`'s `items` as an ignored field, which is exactly
# the false alarm this audit exists to not raise.
_FIELD_RE = re.compile(r"""\bs(?:\.([a-z_][a-z0-9_]*)|\[['"]([a-z_][a-z0-9_]*)['"]\])""")


def _fields(text: str) -> set[str]:
    return {a or b for a, b in _FIELD_RE.findall(text)}


def _template_map() -> dict[str, str]:
    """`html_style._TMPL` — template id -> `.j2` filename — read out of the source."""
    try:
        src = (_HTML / "html_style.py").read_text(encoding="utf-8")
        body = re.search(r"_TMPL\s*=\s*\{(.*?)\n\}", src, re.S)
        return dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body.group(1))) if body else {}
    except (OSError, AttributeError):
        return {}


def _consumed() -> dict[str, set[str]]:
    tmpl = _template_map()
    if not tmpl:
        return {}
    try:
        shared = _fields((_TPL_DIR / "_macros.j2").read_text(encoding="utf-8"))
    except OSError:
        shared = set()
    out: dict[str, set[str]] = {}
    for tid, fname in tmpl.items():
        if tid == "fallback":
            continue          # renders whatever it can; a fallback slide is already flagged
        try:
            body = (_TPL_DIR / fname).read_text(encoding="utf-8")
        except OSError:
            continue
        out[tid] = _fields(body) | shared
    return out


_CONSUMES = _consumed()


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
