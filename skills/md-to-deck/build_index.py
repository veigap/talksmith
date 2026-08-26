#!/usr/bin/env python3
"""Working-directory landing page: one card per rendered Talk, linking to its HTML deck.

    python3 build_index.py [--root .]

A rendered deck lives at `talks/<Talk>/output/html/index.html` — three levels down, with a
filename that is the same for every Talk. The presenter has no way to *find* it, and no single
link to hand someone. So every `html-strict` render (final or the Step-5.5 live view) rewrites
`<root>/index.html`: the whole set is re-scanned each time, so the page self-heals if it is
deleted, and a Talk rendered months ago keeps its card.

Each render stamps `output/html/.render.json` (mode + deck metadata + slide count) so this scan
stays a cheap read of small sidecars rather than a re-parse of every model. A deck rendered
before the stamp existed still shows up — the metadata falls back to its `slide-model.json`.

**Never clobbers a hand-written page.** The generated file carries `MARKER`; a root `index.html`
without it belongs to the user (a site, a README-as-page), so the index goes to
`talksmith-index.html` instead and says so on stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The HTML path's one non-stdlib dependency (jinja2) is imported by `html_style`.
# Surface its absence as the one-line `failed:` this CLI uses everywhere else — the
# message html_style raises names the missing module, the interpreter, and the fix.
# Only when run as a command: an importer (the render tests) still gets the ImportError.
try:
    import html_style as _hs  # noqa: E402
    import model_freshness as _fresh  # noqa: E402
except ImportError as _e:     # noqa: E402
    if __name__ != "__main__":
        raise
    print(f"failed: {_e}", file=sys.stderr)
    raise SystemExit(2) from None

MARKER = "<!-- talksmith:index -->"
INDEX_NAME = "index.html"
FALLBACK_NAME = "talksmith-index.html"
STAMP = ".render.json"


def workspace_root(talk: Path) -> Path | None:
    """The working directory a Talk belongs to — the parent of its `talks/` folder. Returns None
    for a Talk that isn't under a `talks/` dir (ad-hoc renders, the committed style test), which
    is the signal to skip the index entirely rather than scatter one next to a fixture."""
    for p in talk.resolve().parents:
        if p.name == "talks":
            return p.parent
    return None


def stamp_render(out_dir: Path, model: dict, slides: int, draft: bool) -> None:
    """Record what this render was, beside the deck it produced.

    `source` copies the model's `_source` binding (file + SHA-256 of the markdown it was filled
    from) so a later run can tell whether this deck is still current *without* re-running FILL —
    the live view's refresh is a full LLM pass, expensive enough to skip and therefore expensive
    enough to fall behind quietly. See `model_freshness.stamp_state`.
    """
    deck = model.get("deck", {})
    payload = {
        "mode": "draft" if draft else "final",
        "slides": slides,
        "rendered": datetime.now().isoformat(timespec="seconds"),
        "source": model.get("_source") or {},
        **{k: deck.get(k, "") for k in
           ("title", "institution", "class", "presenter", "date", "lang")},
    }
    (out_dir / STAMP).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")


def _entry(deck_html: Path, root: Path) -> dict | None:
    """One card's data, from the render stamp — or, for a deck rendered before stamps existed,
    from its on-disk model. A deck we can describe neither way still gets a card (the folder name
    is a usable title); a link the presenter can click beats a perfect card they never see."""
    html_dir = deck_html.parent
    talk = html_dir.parent.parent
    info: dict = {}
    stamped = False
    stamp = html_dir / STAMP
    if stamp.is_file():
        try:
            info = json.loads(stamp.read_text(encoding="utf-8"))
            stamped = True
        except (json.JSONDecodeError, OSError):
            info = {}
    if not info:
        for name, mode in (("slide-model.json", "final"), ("slide-model.draft.json", "draft")):
            src = talk / "output" / name
            if src.is_file():
                try:
                    model = json.loads(src.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                info = {**model.get("deck", {}), "mode": mode,
                        "slides": len(model.get("slides", []))}
                break
    try:
        mtime = deck_html.stat().st_mtime
    except OSError:
        return None
    rendered = info.get("rendered") or datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
    href = "/".join(quote(part) for part in
                    deck_html.relative_to(root).as_posix().split("/"))
    # Is the deck on disk still the current one? Only the stamp can answer — the model fallback
    # below describes a *model*, which says nothing about when the HTML was written. A card that
    # cannot tell stays unbadged: "out of date" is a claim, not a default.
    stale = stamped and _fresh.stamp_state(info, talk)[0] == "stale"
    return {
        "href": href,
        "stale": stale,
        "title": info.get("title") or talk.name.replace("-", " "),
        "institution": info.get("institution", ""),
        "cls": info.get("class", ""),
        "presenter": info.get("presenter", ""),
        "date": info.get("date", ""),
        "slides": info.get("slides") or 0,
        "draft": info.get("mode") == "draft",
        "lang": info.get("lang", ""),
        "rendered": rendered[:10],
        "sort": mtime,
    }


def collect(root: Path) -> list[dict]:
    """Every rendered deck under `<root>/talks/`, newest render first."""
    entries = [e for e in (_entry(p, root)
                           for p in sorted((root / "talks").glob("*/output/html/index.html")))
               if e]
    entries.sort(key=lambda e: e["sort"], reverse=True)
    return entries


def render(entries: list[dict], lang: str = "en") -> str:
    """The page, marker-first — the marker is what tells a later run this file is ours to
    overwrite, so it has to survive being read back as plain text (an HTML comment before the
    doctype is ignored by browsers, which parse from `<!doctype`)."""
    return f"{MARKER}\n{_hs.index_page(entries, lang)}"


def update_index(root: Path) -> Path | None:
    """(Re)write the working-directory landing page. Returns the path written, or None when there
    is nothing to list."""
    entries = collect(root)
    if not entries:
        return None
    lang = next((e["lang"] for e in entries if e["lang"]), "en")   # newest render's language
    out = root / INDEX_NAME
    if out.exists() and MARKER not in out.read_text(encoding="utf-8", errors="ignore"):
        print(f"[html] {INDEX_NAME} is not Talksmith's — writing {FALLBACK_NAME} instead",
              file=sys.stderr)
        out = root / FALLBACK_NAME
    out.write_text(render(entries, lang), encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("."),
                    help="working directory holding talks/ (default: cwd)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not (root / "talks").is_dir():
        print(f"failed: no talks/ under {root}", file=sys.stderr)
        return 2
    out = update_index(root)
    if out is None:
        print("[html] no rendered decks yet — no index written", file=sys.stderr)
        return 0
    print(f"[html] index → {os.path.relpath(out, Path.cwd())}", file=sys.stderr)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
