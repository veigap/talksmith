#!/usr/bin/env python3
"""Preflight: flag model fields the chosen template will silently ignore.

Why this exists:
    Each template renders a fixed set of fields (its `schemas/slide-model.md` contract). When the
    FILL step puts a *content* field on a slide whose template has no slot for it — a second image
    on `content-image` (which renders one `image`, not `images`), a banner image on `divider` /
    `statement` (full-bleed, no image field) — the field is dropped with no error and the slide
    renders missing content. This audit compares each slide's populated fields against the set its
    template consumes and reports the leftovers, so a misclassification surfaces before rendering.

    It is the model-only complement of `block_coverage.py` (which checks the model against
    `final.md`): it needs no source, so it guards every mode, the `--draft` live view included.

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

# Fields any slide may legitimately carry whatever its template renders — metadata the renderer
# reads itself (`template`, `notes`, `lang`, `id`), the slide's `section` (set on every content
# slide by FILL, whether or not its template shows it), and the layout knobs `reveal`, `design` and
# `icons` (`"none"` turns content-matched icons off for the slide's item set — read by html_style,
# not a template), which carry no content of their own. Never flagged.
#
# Content the shared macros render (`highlights`, `media`, `lead`, `stats`, `title`, …) is NOT
# here: it is consumed only by the templates that call those macros (see `_consumed`). It used to
# be — "every content template calls `stage()`" — and that is exactly how `quote`, which calls no
# macro at all, silently dropped a `title` this audit then called consumed.
#
# Every `_`-prefixed key is metadata by the model's own convention (`_model.py` → `model_strings`;
# `_source` the freshness stamp, `_choice` the classification trace) — never rendered, so its
# being unconsumed is the design, not a finding. That rule is applied in `audit`, not listed here.
_UNIVERSAL = {"template", "section", "notes", "reveal", "lang", "id", "design", "icons"}

# Fields a template consumes only in part. `image-full` reads `highlights` for its citation line
# and nothing else (image-full.j2), so any other `kind` is dropped there — flag it by name.
_PARTIAL = {"image-full": {"highlights": {"source"}}}

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
# for that pattern is the answer, and it cannot be stale. The shared `_macros.j2` is folded in
# **per macro**: a template gets the fields of each macro it calls (`m.stage(`, `m.header(`, …),
# and of every macro those call in turn — so `image-full` (header only) and `quote` (no macro)
# are held to what they actually draw.
#
# Read as text, not imported: this audit is stdlib-only and CLI-safe, and importing `html_style`
# to reach `_TMPL` would drag `jinja2` in as a hard dependency of a preflight check.
_HTML = Path(__file__).resolve().parent.parent          # md-to-deck/scripts/ — html_style.py lives here
_TPL_DIR = _HTML.parent / "templates" / "html"
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


_MACRO_RE = re.compile(r"\{%-?\s*macro\s+(\w+)\s*\(.*?%\}(.*?)\{%-?\s*endmacro", re.S)
_CALL_RE = re.compile(r"\bm\.(\w+)\s*\(")


def _macro_fields(text: str) -> dict[str, set[str]]:
    """Macro name -> the slide fields it reads, directly or through the macros it calls."""
    bodies = dict(_MACRO_RE.findall(text))
    calls = {n: {o for o in bodies if o != n and re.search(rf"\b{o}\s*\(", b)}
             for n, b in bodies.items()}
    out: dict[str, set[str]] = {}
    for name in bodies:
        seen, todo, acc = set(), [name], set()
        while todo:
            x = todo.pop()
            if x not in seen:
                seen.add(x)
                acc |= _fields(bodies[x])
                todo += calls[x]
        out[name] = acc
    return out


def _consumed() -> dict[str, set[str]]:
    tmpl = _template_map()
    if not tmpl:
        return {}
    try:
        macros = _macro_fields((_TPL_DIR / "_macros.j2").read_text(encoding="utf-8"))
    except OSError:
        macros = {}
    out: dict[str, set[str]] = {}
    for tid, fname in tmpl.items():
        if tid == "fallback":
            continue          # renders whatever it can; a fallback slide is already flagged
        try:
            body = (_TPL_DIR / fname).read_text(encoding="utf-8")
        except OSError:
            continue
        shared = set().union(*(macros.get(n, set()) for n in _CALL_RE.findall(body)))
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
# accepts either text shape. (`image-full` names its own picture field `image` and reads nothing
# else; a `media` on it is reported as ignored, not accepted as the picture.)
_REQUIRES = {
    "statement": ("title",),
    "concept-breakdown": ("title", "cards"),
    "process": ("title", "steps"),
    "figures": ("title", "figures"),
    "image-grid": ("images",),
    "image-full": ("title", "image"),
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
        extra = sorted(k for k, v in s.items()
                       if k not in allowed and not k.startswith("_") and _nonempty(v))
        for field, kinds in _PARTIAL.get(t, {}).items():
            dropped = sorted({str(h.get("kind")) for h in (s.get(field) or [])
                              if isinstance(h, dict) and h.get("kind") not in kinds})
            if dropped:
                extra.append(f"{field}[kind={'|'.join(dropped)}]")
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
