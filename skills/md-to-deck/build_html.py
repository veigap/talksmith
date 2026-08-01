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

import html_style as _hs              # noqa: E402
import model_freshness as _fresh       # noqa: E402


# Which `layout` values each template understands (schemas/slide-model.md). `image-left` is
# universal to every body+image composition; `image-top` stacks the image over the body and is
# defined only where that body is prose — a card set, a step list or a quiz under a full-width
# image is a different slide, not a layout of this one. Templates absent from this map (including
# `process`/`quiz` without an image) take no `layout` at all.
_LAYOUTS = {
    "content-image":        ("text-left", "image-left", "image-top"),
    "content+cards+image":  ("text-left", "image-left"),
    "process":              ("text-left", "image-left"),
    "quiz":                 ("text-left", "image-left"),
}


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

    unknown, bad_layouts = [], []
    for s in model.get("slides", []):
        t = s.get("template", "fallback")
        # `layout` places the slide's own image against its body, so it means nothing without one
        # and not every template defines every value. Either way it renders as the default — say
        # so rather than let an author's pinned intent disappear silently.
        lay, name = s.get("layout"), s.get("title", "") or "(untitled)"
        if lay and lay not in _LAYOUTS.get(t, ()):
            bad_layouts.append((name, t, lay, f"expected {'|'.join(_LAYOUTS.get(t, ())) or 'no layout'}"))
        elif lay and not s.get("image"):
            bad_layouts.append((name, t, lay, "the slide carries no image"))
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
        aside = f'<aside class="notes">{_hs._esc(notes)}</aside>' if notes else ""
        slides_html.append(f'<section class="slide"{sid} data-kind="{t}">{inner}{aside}</section>')

    for slide_title, bad in unknown:
        print(f"[html] warning: unknown template {bad!r} → fallback  ({slide_title})", file=sys.stderr)
    for slide_title, tmpl, bad, why in bad_layouts:
        print(f"[html] warning: layout {bad!r} ignored on {tmpl!r} ({why}) "
              f"→ default  ({slide_title})", file=sys.stderr)

    title = deck.get("title", talk_root.name if talk_root else "")
    subtitle = " · ".join(x for x in (deck.get("class", ""), deck.get("presenter", "")) if x)
    return _hs.page("".join(slides_html), title=title, subtitle=subtitle,
                    lang=lang), len(model.get("slides", []))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, default=None, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="render the in-progress slide-model.draft.json")
    ap.add_argument("--model", type=Path, default=None, help="a slide-model.json to render directly")
    ap.add_argument("--talk-root", type=Path, default=None, help="asset root for --model (image resolution)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="output .html")
    ap.add_argument("--allow-stale", action="store_true",
                    help="skip the source-freshness guard (--talk mode); render the on-disk model as-is")
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

    html, n = render(model, talk_root, out_dir)
    out = args.output or (out_dir / "index.html")
    out.write_text(html, encoding="utf-8")
    print(f"[html] {n} slides → {out}", file=sys.stderr)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
