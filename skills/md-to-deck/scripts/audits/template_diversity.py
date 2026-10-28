#!/usr/bin/env python3
"""Preflight: catch a FILL step that collapsed the deck onto one default template.

Why this exists:
    The catalog (`config/pptx-styles/slide-templates.md`) defines a *discriminator walk*:
    collect signals, enumerate **every** entry whose Match fires, then pick one — and it
    forbids falling to a plainer template when a richer one fits. That walk is real work,
    and until `_choice` existed the model emitted only its conclusion (`"template": …`),
    so nothing recorded whether the walk happened. It reliably degraded: two thirds of a
    deck classified `concept-breakdown` / `content-text` because those are the cheapest
    field contracts to fill (a near-transcription of the source bullets), while `timeline`,
    `stat`, `value-columns`, `figures`, `quiz` all demand restructuring the content first.

    The existing model-only audits all check the *internal consistency of a choice already
    made* — `degenerate_enum` (a one-item enumeration), `field_coverage` (a field the
    template ignores), `image_coverage` (a dropped image). None of them asks the question
    that matters here: **was a richer template available and passed over?** And
    `html-strict` runs `audit-none` at CONTROL with `no-critique` at FEEDBACK, so a deck
    that fell entirely to one template shipped with no signal at all beyond a stderr
    `fallback` warning emitted at render time, long past the point of decision.

    This is the deterministic catch. It reads the model alone — the shared IR for both
    renderers — so it guards every mode, and it runs before any render or critique.

    **Diversity is not a virtue in itself.** A deck genuinely built from parallel labeled
    sets *is* mostly `concept-breakdown`, and forcing variety would classify slides into
    templates their content does not support — a worse defect than monotony. So every
    distribution finding here is *advisory*: it marks a deck worth re-examining (and hands
    the classification critic its worklist), it never rewrites a choice. The one hard
    failure is `fallback`, which the catalog already defines as "nothing matched" — a
    classification gap, not a judgment call.

What it does:
    Walks `slide-model.json` and reports:

      [fallback]      a slide classified `fallback`, or carrying a template the schema
                      doesn't define. FAIL — the catalog needs an entry, or the slide
                      needs re-classifying.
      [dominance]     one non-frame template holds more than --max-share of the content
                      slides. Advisory.
      [composition]   more than half the content slides *look* the same — one composition
                      group (card grid, aligned columns, one big claim, …) dominates even
                      though no single template does. Advisory, and the one that catches the
                      monotony a per-template count misses.
      [run]           --max-run or more *consecutive* content slides share a template.
                      Advisory — the tell of the FILL pass anchoring on its own output.
      [format-flat]   every `concept-breakdown` in the deck carries the same `format`
                      (grid/row/list/editorial), with 4+ of them. Advisory — the family
                      has four compositions and a deck that uses one is monotonous even
                      when the template choice is right.
      [no-alternative] a slide whose `_choice.candidates` names fewer than two templates:
                      the walk recorded no rejected alternative, so nothing shows a
                      richer option was considered. Advisory.

    Frame templates (`section-agenda`, `divider`, `closing-hero`, `closing-cta`, `cover`)
    are excluded from every share and run computation: they are positional, not content
    choices, and a deck legitimately repeats them once per section.

    Always prints the full distribution — that table is the point as much as the findings.

Usage:
    python3 audits/template_diversity.py <slide-model.json>
        [--max-share 0.40] [--max-run 4] [--min-slides 6]
        [--strict] [--warn-only] [--json]

Exit codes:
    0  no fallback slides (advisories may still be listed)
    1  a [fallback] slide, or any finding under --strict
    2  the model could not be read
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Positional templates — chosen by where the slide sits in the deck, never by its content.
# A 6-section deck holds 6 `section-agenda` slides by design, so counting them would drown
# every share computation in structural repetition.
_FRAME = {"cover", "section-agenda", "divider", "closing-hero", "closing-cta"}

# Every template the schema defines (`schemas/slide-model.md` → *Per-template field
# contract*). Anything else in a model renders as `fallback` and is reported as such here —
# the same set the HTML build warns about, checked before the render instead of during it.
_KNOWN = _FRAME | {
    "statement", "concept-breakdown", "process", "figures",
    "image-grid", "image-full", "content-image", "content+cards+image", "value-columns",
    "concept-columns", "stat", "big-number", "quote", "timeline", "pros-cons", "quiz",
    "single-point", "callout", "code-example", "content-text", "matrix", "fallback",
}

# `content-text` is the catalog's own declared last resort ("flag as restructure candidate")
# and `fallback` is the no-match sink. They get the dominance check at a tighter share: a
# deck leaning on either is the exact failure this audit exists to surface, and a quarter of
# the slides is already too many.
_LAST_RESORT = {"content-text", "fallback"}
_LAST_RESORT_SHARE = 0.15


# --- composition groups: what the *audience* sees -----------------------------------------
# The catalog's families group templates by what a slide **does**; monotony is about what a
# slide **looks like**, and the two do not coincide. `content+cards+image` is
# `concept-breakdown` with a picture beside it — the catalog files them under different
# families ("Visual" vs "Labeled set") because they answer different content questions, but on
# screen they are the same slide: a grid of labeled cards. A deck can hold no template above
# the per-template cap and still read as one slide repeated, which is exactly what a real
# 54-slide deck did (18 `content+cards+image` + 11 `concept-breakdown` = 54% card grids, with
# nothing over 33%). So dominance is checked twice: per template, and per composition.
_COMPOSITION = {
    "cards":    {"concept-breakdown", "content+cards+image", "figures"},
    "columns":  {"value-columns", "concept-columns", "pros-cons", "matrix"},
    "sequence": {"process", "timeline"},
    "claim":    {"statement", "quote", "callout", "single-point"},
    "metrics":  {"stat", "big-number"},
    "visual":   {"image-full", "image-grid", "content-image"},
    "verbatim": {"code-example", "content-text", "quiz"},
}
_COMP_OF = {t: g for g, ts in _COMPOSITION.items() for t in ts}

# A composition may legitimately carry more of the deck than any one template — a talk really
# can be mostly card grids. Past half, though, the audience is looking at one slide over and
# over regardless of which templates produced it.
_COMP_SHARE = 0.50


def _fam(slide: dict) -> str:
    """The template a slide renders as."""
    return slide.get("template", "fallback")


def _ref(slide: dict, idx: int) -> str:
    """A human-locatable name for a slide: its title, else its position."""
    for k in ("title", "question", "quote", "number"):
        v = slide.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:60]
    return f"slide[{idx}]"


def audit(model: dict, max_share: float, max_run: int, min_slides: int) -> dict:
    slides = model.get("slides", [])
    content = [(i, s) for i, s in enumerate(slides) if _fam(s) not in _FRAME]
    dist = Counter(s.get("template", "fallback") for s in slides)
    fails: list[str] = []
    warns: list[str] = []

    # --- FAIL: no-match slides -------------------------------------------------------
    for i, s in enumerate(slides):
        t = s.get("template", "fallback")
        if t == "fallback":
            fails.append(f"[fallback] slide {i + 1} {_ref(s, i)!r} — nothing in the catalog "
                         f"matched. Re-run the discriminator walk, or the catalog needs an entry.")
        elif t not in _KNOWN:
            fails.append(f"[fallback] slide {i + 1} {_ref(s, i)!r} — template {t!r} is not in the "
                         f"schema; it renders as `fallback`. Fix the spelling or the choice.")

    n = len(content)
    if n >= min_slides:
        # --- share of the content slides ---------------------------------------------
        cdist = Counter(_fam(s) for _i, s in content)
        for t, c in cdist.most_common():
            share = c / n
            cap = _LAST_RESORT_SHARE if t in _LAST_RESORT else max_share
            if share > cap:
                warns.append(f"[dominance] {t} holds {c}/{n} content slides ({share:.0%} > "
                             f"{cap:.0%}) — re-check these against the catalog's richer entries "
                             f"before accepting the deck.")

        # --- share of the composition (what the eye sees, across templates) -----------
        comp = Counter(_COMP_OF.get(_fam(s), "other") for _i, s in content)
        for g, c in comp.most_common(1):
            if g != "other" and c / n > _COMP_SHARE and c > cdist.most_common(1)[0][1]:
                spread = ", ".join(f"{t} {k}" for t, k in cdist.most_common()
                                   if _COMP_OF.get(t) == g)
                warns.append(f"[composition] {c}/{n} content slides ({c / n:.0%}) render as "
                             f"`{g}` — {spread}. No single template is dominant, but the "
                             f"audience sees one slide repeated: these templates differ in what "
                             f"they mean, not in what they look like.")

        # --- consecutive runs ---------------------------------------------------------
        run_t, run_start, run_len = None, 0, 0
        for pos, (i, s) in enumerate(content + [(None, {"template": "\0"})]):
            t = _fam(s)
            if t == run_t:
                run_len += 1
                continue
            if run_t is not None and run_len >= max_run:
                first, last = content[run_start][0] + 1, content[pos - 1][0] + 1
                warns.append(f"[run] slides {first}–{last} are {run_len} consecutive {run_t} — "
                             f"the tell of the fill anchoring on its own previous output.")
            run_t, run_start, run_len = t, pos, 1

        # --- concept-breakdown composed one single way --------------------------------
        cb = [s for _i, s in content if _fam(s) == "concept-breakdown"]
        if len(cb) >= 4:
            fmts = {s.get("format") or "grid" for s in cb}
            if len(fmts) == 1:
                warns.append(f"[format-flat] all {len(cb)} concept-breakdown slides use "
                             f"format={fmts.pop()!r} — the family composes four ways "
                             f"(grid/row/list/editorial); pick each by count + body length.")

    # --- the walk left no alternative ---------------------------------------------------
    untraced = [(i, s) for i, s in content
                if len(((s.get("_choice") or {}).get("candidates") or [])) < 2]
    if untraced:
        head = ", ".join(f"{_ref(s, i)!r}" for i, s in untraced[:4])
        more = f" (+{len(untraced) - 4} more)" if len(untraced) > 4 else ""
        warns.append(f"[no-alternative] {len(untraced)}/{n} content slides record fewer than two "
                     f"`_choice.candidates` — no rejected alternative, so nothing shows a richer "
                     f"template was considered: {head}{more}")

    comp_dist = Counter(_COMP_OF.get(_fam(s), "other") for _i, s in content)
    return {"distribution": dict(dist.most_common()),
            "composition": dict(comp_dist.most_common()), "content_slides": n,
            "distinct": len({_fam(s) for _i, s in content}),
            "fails": fails, "warns": warns}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model", type=Path, help="path to slide-model.json")
    ap.add_argument("--max-share", type=float, default=0.40,
                    help="flag a template holding more than this share of content slides (default 0.40)")
    ap.add_argument("--max-run", type=int, default=4,
                    help="flag this many consecutive content slides on one template (default 4)")
    ap.add_argument("--min-slides", type=int, default=6,
                    help="skip share/run checks under this many content slides (default 6)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any finding, advisories included")
    ap.add_argument("--warn-only", action="store_true", help="never exit non-zero (for the --draft live view)")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args(argv)

    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"template_diversity: cannot read model {args.model}: {e}", file=sys.stderr)
        return 2

    r = audit(model, args.max_share, args.max_run, args.min_slides)
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        n, d = r["content_slides"], r["distinct"]
        print(f"template_diversity: {d} distinct template(s) over {n} content slide(s)")
        for t, c in r["distribution"].items():
            mark = "  ←" if any(f"] {t} holds" in w for w in r["warns"]) else ""
            print(f"    {c:3}  {t}{mark}")
        if r["composition"]:
            print("  as the audience sees them: "
                  + ", ".join(f"{g} {c}" for g, c in r["composition"].items()))
        for line in r["fails"]:
            print(f"  {line}", file=sys.stderr)
        for line in r["warns"]:
            print(f"  {line}", file=sys.stderr)
        if not r["fails"] and not r["warns"]:
            print("template_diversity: ok — no dominant template, no fallback slide")

    if args.warn_only:
        return 0
    if r["fails"]:
        return 1
    return 1 if (args.strict and r["warns"]) else 0


if __name__ == "__main__":
    sys.exit(main())
