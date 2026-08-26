"""Render a Talk's **`slide-model.json`** to a styled static HTML / Reveal.js deck.

The input is `slide-model.json` ([`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md)) —
the LLM-filled structured model the **`md-to-deck` skill** produces from `final.md` (deliverable)
or `draft.md` (live in-progress view). All the *semantic* work — choosing each slide's template
and decomposing its content into that template's fields — happened in the fill step. **This
renderer is purely mechanical:** it maps each slide's fields onto its Jinja template
(`templates/html/*.j2`) and wraps them in the vendored Reveal.js shell — the `template` and fields
are given, so the renderer only maps and lays out. The PPTX renderer consumes the same model.

Usage:
    python3 build_html.py --talk talks/<Talk> [--draft] [-o out.html]
    python3 build_html.py --model path/to/slide-model.json [--talk-root DIR] [-o out.html]

Requires **jinja2**. Network on first run (icon catalog + fetch, cached under output/.icons); the
output HTML is fully offline / self-contained.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# The HTML path's one non-stdlib dependency (jinja2) is imported by `html_style`.
# Surface its absence as the one-line `failed:` this CLI uses everywhere else — the
# message html_style raises names the missing module, the interpreter, and the fix.
# Only when run as a command: an importer (the render tests) still gets the ImportError.
try:
    import build_index as _idx             # noqa: E402
    import html_style as _hs              # noqa: E402
    import model_freshness as _fresh       # noqa: E402
except ImportError as _e:                  # noqa: E402
    if __name__ != "__main__":
        raise
    print(f"failed: {_e}", file=sys.stderr)
    raise SystemExit(2) from None

sys.path.insert(0, str(_HERE / "audits"))


# A slide is a **design** (how the canvas is divided) filled with a **style** (the template's
# content shape). `design` is universal — every content template takes every design, because the
# stage places the media and the template only emits content. That is the whole point of the
# field: the old per-template `layout` allowlist meant a template not on the list could not be
# composed at all. Resolution (including mapping the old `layout`/`image`/`aside` spellings
# forward) lives in html_style.py `_design`; this only validates what the author wrote.
_DESIGNS = _hs._DESIGNS
# Every design but `full` places a picture, so one without media is a slide that says it is
# composed and then has nothing to compose. It renders as `full` — the content is intact and
# nothing is silently cropped — but it is an authoring slip worth naming.
_LEGACY_LAYOUTS = tuple(_hs._LAYOUT_DESIGN)   # the old spellings, from the map that translates them

# A value-columns grid beside an image gets half the slide. Past this it still renders — the grid
# never degrades to a list — but the cells crowd and the fit pass pays for it in type size, so say
# so rather than let the slide silently squeeze. Split the rows, or drop the image.
_VC_MAX_COLS, _VC_MAX_ROWS = 3, 5

# The labeled set's `format` (schemas/slide-model.md). An unrecognized value renders as `grid`,
# which looks like a deliberate card set rather than a typo — the same reason `layout` warns.
_FORMATS = ("grid", "row", "editorial")
_LABELED_SET = ("concept-breakdown", "card-row", "icon-list")
# `list` (the single-column stack) was retired: a labeled set is N *parallel* concepts, and
# parallel concepts read side by side. A model that still carries it renders as `grid` like any
# other unusable value, but says why — it isn't a typo, it's a stale model.
_RETIRED_FORMATS = {"list": "a labeled set now always reads as a grid; if the per-item prose "
                            "needs a full-width column it is content-text, or split the slide"}

# `format: editorial` buys its density by dropping the card, so the body budget is what the
# *column count* leaves: (max items, max body chars). Past it the slide still renders — the fit
# pass shrinks it — but shrinking content until it is unreadable is not a fix, so name the real
# ways out: fewer/shorter concepts, or splitting the slide.
_ED_BODY_MAX = ((4, 140), (6, 100), (8, 70))
_ED_MAX_ITEMS = 8


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (t or "").lower())).strip()


def render(model: dict, talk_root: Path, out_dir: Path):
    """slide-model.json → (html, slide_count). Deterministic; one Jinja template per slide."""
    cache = out_dir / ".icons"
    _hs.load_catalog(cache)
    deck = model.get("deck", {})
    lang = deck.get("lang", "en")
    sections = deck.get("sections", [])
    sections_norm = [_norm(s) for s in sections]

    slides_html = []
    if deck.get("title"):                                          # contractually-fixed cover first
        slides_html.append(f'<section class="slide cover-slide">{_hs.cover_from_deck(deck, talk_root)}</section>')

    unknown, bad_layouts, dense = [], [], []
    bad_formats, crowded = [], []
    for s in model.get("slides", []):
        t = s.get("template", "fallback")
        # `design` divides the canvas, so every design but `full` needs media to put in the part
        # it reserves. Either way the slide renders as `full` — say so rather than let an author's
        # pinned intent disappear silently.
        name = s.get("title", "") or "(untitled)"
        des, lay = s.get("design"), s.get("layout")
        # `_design` is the one place that knows how media resolves (`media` → `image` →
        # `aside.image`); asking it, rather than re-spelling the chain here, keeps the warning and
        # the render agreeing about what counts as media.
        _, media = _hs._design(s, t)
        if des and des not in _DESIGNS:
            bad_layouts.append((name, t, des, f"expected {'|'.join(_DESIGNS)}"))
        elif des and des != "full" and not media:
            bad_layouts.append((name, t, des, "the slide carries no media to place"))
        elif lay and lay not in _LEGACY_LAYOUTS:
            bad_layouts.append((name, t, lay, f"expected {'|'.join(_LEGACY_LAYOUTS)} "
                                              f"(`layout` is the old spelling of `design`)"))
        fmt = s.get("format")
        if t in _LABELED_SET and fmt:
            if fmt not in _FORMATS:
                bad_formats.append((name, fmt, _RETIRED_FORMATS.get(
                    fmt, f"expected {'|'.join(_FORMATS)}")))
            elif fmt == "editorial":
                items = s.get("cards") or s.get("rows") or []
                cap = next((c for lim, c in _ED_BODY_MAX if len(items) <= lim), _ED_BODY_MAX[-1][1])
                longest = max((len(i.get("body") or "") for i in items), default=0)
                if len(items) > _ED_MAX_ITEMS:
                    crowded.append((name, len(items), longest,
                                    f"more than {_ED_MAX_ITEMS} concepts"))
                elif longest > cap:
                    crowded.append((name, len(items), longest,
                                    f"longest body {longest} chars, ~{cap} fits at that width"))
        if t == "value-columns" and media:
            cols = s.get("columns") or []
            rows = max((len(c.get("cells") or []) for c in cols), default=0)
            if len(cols) > _VC_MAX_COLS or rows > _VC_MAX_ROWS:
                dense.append((name, len(cols), rows))
        # An unrecognized `template` silently renders as fallback, which looks like a bad
        # classification rather than a typo — surface it so a misspelled catalog name
        # (`content+image` for `content-image`, `agenda` for `section-agenda`) is visible.
        if t not in _hs._TMPL and t != "section-agenda":
            unknown.append((s.get("title", "") or "(untitled)", t))
        sid = ""
        if t == "section-agenda":                                 # roadmap: active index from deck.sections
            name = _norm(s.get("title", ""))
            active = next((i for i, sn in enumerate(sections_norm) if sn and sn == name), -1)
            inner = _hs.section_agenda(sections, active)
            if active >= 0:
                sid = f' id="sec-{active}"'                        # so roadmap rows can deep-link here
        else:
            inner = _hs.render_model_slide(s, cache, talk_root, out_dir, lang)
        notes = s.get("notes", "")
        aside = f'<aside class="notes">{_hs.notes_html(notes)}</aside>' if notes else ""
        slides_html.append(f'<section class="slide"{sid} data-kind="{t}">{inner}{aside}</section>')

    for slide_title, bad in unknown:
        print(f"[html] warning: unknown template {bad!r} → fallback  ({slide_title})", file=sys.stderr)
    for slide_title, tmpl, bad, why in bad_layouts:
        print(f"[html] warning: design {bad!r} ignored on {tmpl!r} ({why}) "
              f"→ full  ({slide_title})", file=sys.stderr)
    for slide_title, bad, why in bad_formats:
        print(f"[html] warning: format {bad!r} → grid — {why}  ({slide_title})", file=sys.stderr)
    for slide_title, n, longest, why in crowded:
        print(f"[html] warning: editorial grid of {n} concepts — {why}; the fit pass would "
              f"shrink the slide rather than fix it. Shorten the bodies, drop to fewer concepts, "
              f"or split the slide  ({slide_title})", file=sys.stderr)
    for slide_title, ncols, nrows in dense:
        print(f"[html] warning: value-columns grid {ncols}×{nrows} beside an image "
              f"(max {_VC_MAX_COLS}×{_VC_MAX_ROWS} at half width) — cells will crowd; "
              f"split the rows or drop the image  ({slide_title})", file=sys.stderr)

    title = deck.get("title", talk_root.name if talk_root else "")
    subtitle = " · ".join(x for x in (deck.get("class", ""), deck.get("presenter", "")) if x)
    return _hs.page("".join(slides_html), title=title, subtitle=subtitle,
                    lang=lang), len(model.get("slides", []))


def _coverage_warn(model: dict, model_path: Path, source_md: Path, limit: int = 12) -> None:
    """Advisory FILL-coverage pass: what `final.md` says that the model does not carry.

    The freshness guard above proves the model was filled from *this* source; it says nothing
    about whether the fill kept the source's content. That is the FILL step's hardest rule
    (`schemas/slide-model.md` → *Never drop content*) and the one an LLM decomposition actually
    breaks — silently, because a model missing a clause is still a valid model and every other
    audit passes. Until now the two audits that could have caught it (`block_coverage`,
    `notes_coverage`) both required a rendered `.pptx`, so this path — the HTML render, which
    never produces one — shipped with no content check at all.

    **Warns, never blocks.** The match is a heuristic (see `audits/text_coverage.py`), and a deck
    that renders is still delivered; the presenter decides whether a flagged line matters. Run the
    audits directly for the full list.

    **A failure here is reported by kind.** An unreadable or malformed file is a condition of the
    deck: skip the check, say so quietly, render anyway. Anything else — a signature that drifted,
    a missing name — is a defect in the plugin, and it gets a loud, differently-worded line,
    because the failure mode this function had was precisely a silent one: a call site left stale
    by an audit refactor, its `TypeError` swallowed into a warning that read like the icon
    warnings beside it. The safety net was down for two releases and the render never said so in
    words anyone would read as "broken". `tests/skills/md-to-deck/test_render_coverage.py` now
    calls this directly so the drift cannot recur unnoticed.
    """
    try:
        import text_coverage as _tc            # noqa: PLC0415  (advisory, optional)
        import notes_coverage as _nc           # noqa: PLC0415
        import block_coverage as _bc           # noqa: PLC0415
        text = source_md.read_text(encoding="utf-8")
        r = _tc.audit(text, model)
        nmodel, nindex = _nc.model_notes(str(model_path))
        ndrops, _ = _nc.reconcile_source(_nc.parse_source_md(str(source_md)), nmodel, nindex)
        bslots, bindex = _bc.model_callout_slots(str(model_path))
        bdrops, _ = _bc.reconcile_source(_bc.parse_source_md(str(source_md)), bslots, bindex)
    except (OSError, ValueError) as e:         # a condition of the deck, not a bug in the check
        print(f"[html] warning: coverage check skipped ({type(e).__name__}: {e})", file=sys.stderr)
        return
    except Exception as e:                     # never let an advisory check break a render …
        print(f"[html] BUG: the built-in coverage check is broken and did NOT run — "
              f"{type(e).__name__}: {e}. This is a plugin defect, not a problem with your deck; "
              f"the render below is unchecked. Run audits/text_coverage.py, "
              f"audits/notes_coverage.py and audits/block_coverage.py by hand, and report it.",
              file=sys.stderr)
        return

    notes, content = r.notes_drops, r.content_drops
    ndrops = ndrops + bdrops
    if not r.drops and not r.missing and not ndrops:
        print(f"[html] coverage: ok — {r.checked} source lines present in the model",
              file=sys.stderr)
        return

    # Notes first, and counted apart from body prose. They are copied verbatim, so a missing notes
    # line is unambiguously lost — while a body line with no literal match is often just the fill
    # restructuring prose into fields, which `text_coverage` already sorts out into its own tier.
    print(f"[html] warning: {len(notes)} speaker-notes line(s), {len(content)} body line(s) and "
          f"{len(r.missing) + len(ndrops)} slide(s)/notes block(s) of {source_md.name} are missing "
          f"from the model (of {r.checked} checked). The deck renders; that content is not on it. "
          f"Full list: audits/text_coverage.py {source_md} {model_path}", file=sys.stderr)
    # Severe findings first — a whole slide, then a dropped notes block, then individual lines;
    # body lines fill whatever of the budget is left.
    lines = ([m.fmt(source_md.name) for m in r.missing] + [d.fmt() for d in ndrops]
             + [d.fmt(source_md.name) for d in notes + content])
    for ln in lines[:limit]:
        print("  " + ln, file=sys.stderr)
    if len(lines) > limit:
        print(f"  … {len(lines) - limit} more", file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, default=None, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="render the in-progress slide-model.draft.json")
    ap.add_argument("--model", type=Path, default=None, help="a slide-model.json to render directly")
    ap.add_argument("--talk-root", type=Path, default=None, help="asset root for --model (image resolution)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="output .html")
    ap.add_argument("--allow-stale", action="store_true",
                    help="skip the source-freshness guard (--talk mode); render the on-disk model as-is")
    ap.add_argument("--no-coverage", action="store_true",
                    help="skip the advisory FILL-coverage warning (--talk mode)")
    args = ap.parse_args(argv)

    if args.model:
        src = args.model
        talk_root = args.talk_root or src.resolve().parent.parent   # …/<Talk>/output/model.json → <Talk>
        out_dir = src.resolve().parent
    elif args.talk:
        name = "slide-model.draft.json" if args.draft else "slide-model.json"
        src = args.talk / "output" / name
        talk_root, out_dir = args.talk, args.talk / "output" / "html"
    else:
        print("failed: pass --talk or --model", file=sys.stderr)
        return 2

    if not src.is_file():
        print(f"failed: {src} not found — run the md-to-deck fill step first", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    model = json.loads(src.read_text(encoding="utf-8"))

    # Freshness guard. In the workflow (--talk) path, refuse to render a model that is stale or
    # unstamped relative to its source markdown — never silently fall back to an existing model.
    # --model direct mode (ad-hoc renders, the committed style test) has no resolvable source and
    # is exempt; --allow-stale is the explicit, documented override.
    if args.talk and not args.allow_stale:
        source_md = _fresh.source_path(args.talk, args.draft)
        ok, reason = _fresh.verify_fresh(model, source_md)
        if not ok:
            print(f"[html] FAILED: {reason}. Refusing to render — re-run the md-to-deck FILL step "
                  f"(or pass --allow-stale to override).", file=sys.stderr)
            return 2

    if args.talk and not args.no_coverage:
        source_md = _fresh.source_path(args.talk, args.draft)
        if source_md.is_file():
            _coverage_warn(model, src, source_md)

    html, n = render(model, talk_root, out_dir)
    out = args.output or (out_dir / "index.html")
    out.write_text(html, encoding="utf-8")
    print(f"[html] {n} slides → {out}", file=sys.stderr)

    # Refresh the working-directory landing page. Only for a workflow render written to its
    # canonical place: an ad-hoc `-o` render or a `--model` fixture render isn't a deck the
    # presenter is meant to find from the root. Never fatal — a deck that rendered is delivered
    # whether or not its index could be rewritten.
    if args.talk and out == out_dir / "index.html":
        try:
            _idx.stamp_render(out_dir, model, n, args.draft)
            root = _idx.workspace_root(args.talk)
            written = _idx.update_index(root) if root else None
            if written:
                print(f"[html] index → {written}", file=sys.stderr)
        except OSError as e:
            print(f"[html] warning: index not updated ({e})", file=sys.stderr)

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
