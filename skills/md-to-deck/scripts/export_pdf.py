#!/usr/bin/env python3
"""Export the rendered HTML deck to PDF.

Same principle as the `.pptx` export and far less machinery: the deck already knows how to lay
itself out for print (Reveal's `?print-pdf` view, plus the deck's own re-fit pass on `pdf-ready`
and the print pins in theme.css), so this drives a headless browser through that view and takes
the page it produces. The output is vector with selectable text and embedded font subsets, one
page per slide at exactly 960x540 pt — not a stack of screenshots.

Usage:
    python3 export_pdf.py --talk talks/<Talk> [--style <skin>] [--theme light|dark]
    python3 export_pdf.py --deck path/to/index.html -o out.pdf
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import _chrome  # noqa: E402


def export(deck: Path, out: Path, style: str = "", theme: str = "", timeout: int = 180) -> int:
    """Render and return the page count."""
    q = "print-pdf"
    if theme:
        q += "&deck-theme=" + theme
    if style and style != "default":
        q += "&deck-style=" + style
    out.parent.mkdir(parents=True, exist_ok=True)
    _chrome.run(["--no-pdf-header-footer", "--print-to-pdf=%s" % out,
                 "--virtual-time-budget=%d" % (timeout * 1000)],
                _chrome.file_url(deck, q), timeout=timeout)
    if not out.exists() or out.stat().st_size < 1024:
        raise RuntimeError("the browser produced no PDF — is the deck readable at %s?" % deck)
    blob = out.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", blob))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export the rendered HTML deck to PDF.")
    ap.add_argument("--talk", help="Talk root (talks/<Talk>); deck = output/html/index.html")
    ap.add_argument("--deck", help="an HTML deck to export directly")
    ap.add_argument("-o", "--output", help="output .pdf (default: <talk>/output/final.pdf)")
    ap.add_argument("--style", default="", help="deck skin to pin (default: the deck's own)")
    ap.add_argument("--theme", default="", help="light | dark")
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args(argv)

    if a.deck:
        deck = Path(a.deck)
        out = Path(a.output) if a.output else deck.parent / "final.pdf"
    elif a.talk:
        deck = Path(a.talk) / "output" / "html" / "index.html"
        out = Path(a.output) if a.output else Path(a.talk) / "output" / "final.pdf"
    else:
        ap.error("one of --talk or --deck is required")

    if not deck.is_file():
        sys.stderr.write("[pdf] no deck at %s — render the HTML first (build_html.py)\n" % deck)
        return 2
    try:
        pages = export(deck, out, a.style, a.theme, a.timeout)
    except (_chrome.ChromeMissing, RuntimeError) as e:
        sys.stderr.write("[pdf] %s\n" % e)
        return 2
    sys.stderr.write("[pdf] %d pages → %s\n" % (pages, out))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
