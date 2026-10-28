#!/usr/bin/env python3
"""An animated diagram exports as its finished frame, never as its empty start.

Run:  python3 tests/skills/md-to-deck/test_animated_still.py

`talksmith:animate-diagram` writes `<stem>.gif` plus `<stem>.png`, the animation's final frame
(the complete static diagram). The HTML deck plays the GIF. The PDF and the `.pptx` are measured
from the deck frozen in the print view, and a frozen GIF is its *first* frame — for an animation,
the empty start. So:

  * the deck embeds the still beside the GIF (`data-still`), only when the sibling PNG exists;
  * the print view swaps the still in (the one early script both exports ride);
  * the `.pptx` export, handed a GIF with no still, falls back to the GIF's LAST frame;
  * end to end (needs Chrome + python-pptx; skipped without them): the picture in the `.pptx`
    is the still — painted a colour that appears in no GIF frame, so a backstop pass can't fake it.

Needs Pillow (the export's own dependency).
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "md-to-deck"
sys.path.insert(0, str(SKILL))

from PIL import Image  # noqa: E402

import html_style as h  # noqa: E402
import export_pptx as ex  # noqa: E402

RED, WHITE, BLUE = (218, 27, 46), (255, 255, 255), (40, 90, 220)
failures = 0


def _check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")


def _fixture(d: Path, still: bool = True) -> Path:
    """A two-frame GIF — white start, red end — and (optionally) a BLUE still beside it."""
    d.mkdir(parents=True, exist_ok=True)
    frames = [Image.new("RGB", (160, 90), WHITE), Image.new("RGB", (160, 90), RED)]
    gif = d / "anim.gif"
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=[100, 3000], loop=0)
    if still:
        Image.new("RGB", (160, 90), BLUE).save(d / "anim.png")
    return gif


def _dominant(blob: bytes) -> tuple[int, int, int]:
    im = Image.open(io.BytesIO(blob)).convert("RGB")
    return max(im.getcolors(1 << 16))[1]


def t_unit(tmp: Path) -> None:
    gif = _fixture(tmp / "u" / "images")
    html = h._embed("diagram", gif)
    _check("deck: a GIF with a sibling PNG carries the still as data-still",
           'data-still="data:image/png;base64,' in html and 'src="data:image/gif;base64,' in html)
    bare = _fixture(tmp / "v" / "images", still=False)
    _check("deck: a GIF with no PNG beside it carries no still", "data-still" not in h._embed("x", bare))
    _check("deck: a PNG never carries a still", "data-still" not in h._embed("x", gif.with_suffix(".png")))
    early = h._EXPORT_EARLY
    _check("print view: the still is swapped in under ?print-pdf",
           "print-pdf" in early and "img[data-still]" in early and early.index("print-pdf") < early.index("data-still"))
    _check("export: a GIF with no still exports its LAST frame",
           _dominant(ex._final_frame(gif.read_bytes(), "image/gif")) == RED)
    _check("export: a still image is passed through untouched",
           ex._final_frame(b"\x89PNG...", "image/png") == b"\x89PNG...")


def t_end_to_end(tmp: Path) -> None:
    import _chrome
    try:
        import pptx  # noqa: F401
    except ImportError:
        pptx = None
    if not _chrome.find() or pptx is None:
        print("  skip  end to end (needs Chrome and python-pptx)")
        return
    talk = tmp / "talk"
    _fixture(talk / "images")
    model = {"deck": {"title": "t", "lang": "en"},
             "slides": [{"template": "image-full", "title": "Animated diagram",
                         "image": {"src": "images/anim.gif", "alt": "anim"}}]}
    (talk / "output").mkdir(parents=True)
    (talk / "output" / "slide-model.json").write_text(json.dumps(model))
    import build_html
    deck = talk / "output" / "html" / "index.html"
    deck.parent.mkdir(parents=True)
    build_html.main(["--model", str(talk / "output" / "slide-model.json"), "--talk-root", str(talk),
                     "-o", str(deck)])
    out = talk / "output" / "final.pptx"
    ex.main(["--deck", str(deck), "-o", str(out)])
    with zipfile.ZipFile(out) as z:
        media = [z.read(n) for n in z.namelist() if n.startswith("ppt/media/")]
    colours = [_dominant(m) for m in media]
    _check("pptx: the animated diagram exports as its still", BLUE in colours, str(colours))
    _check("pptx: the still came from the print-view swap, not the last-frame backstop",
           RED not in colours, str(colours))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("animated diagram → still")
        t_unit(tmp)
        t_end_to_end(tmp)
    if failures:
        print(f"\n{failures} check(s) FAILED")
        return 1
    print("\nall animated-still checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
