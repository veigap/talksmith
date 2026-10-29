#!/usr/bin/env python3
"""Capture an animated diagram's key frames, and a contact sheet, for the blind critic.

Usage:
    python3 capture_frames.py <svg> --out <dir>

The blind `diagram-critic` judges an animation from pixels alone — never the SVG — so it needs to
see the animation as it plays. This loads the SVG in headless Chrome (the browser the deck plays
in, located by `md-to-deck/_chrome.py`), reads the animation's own timeline, and captures a frame
at the start, at the end of every short animation (an appearance: its settled state) — plus its
midpoint when it moves something, so a quick journey is seen under way and not only arrived — at a
quarter, half and three quarters of every long one (something travelling or on screen for a
while, which often ends faded out, so its end alone would show nothing), and a last one once
everything has ended: the still as the animation leaves it. They land as `frame-01.png` … plus
`contact.png`, every frame labelled with its time — and, when the base `<stem>.svg` sits beside
`<stem>.anim.svg`, `still.png`: the approved still drawn by the same browser (see `write_still`).

It checks nothing: the rules an animation honours are in `PRACTICES.md`, applied by the author and
judged by the critic on these frames.

Exit codes: 0 = frames written; 2 = the SVG could not be read, has no animation, or no Chrome.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_FRAMES = 16
LONG = 2.0                        # s — an animation at least this long is a journey, sampled inside
FRAME_W = 800                     # px per captured frame


_TIMES_JS = """<script>
(function(){
  var a=document.getAnimations(), t=[0], last=0;
  a.forEach(function(x){ var c=x.effect.getComputedTiming();
    var d=c.duration/1000, s=c.delay/1000;
    last=Math.max(last, s+d);
    var moves=x.effect.getKeyframes().some(function(k){ return ('offsetDistance' in k)||('transform' in k); });
    if(d>=LONG){ t.push(s+d*0.25, s+d*0.5, s+d*0.75); }
    else if(moves){ t.push(s+d*0.5, s+d); }   /* a short journey: its end alone shows it already arrived */
    else { t.push(s+d); } });
  t.push(last+0.05);   /* the end: the still as the animation leaves it */
  document.body.setAttribute('data-times', JSON.stringify(t));
})();
</script>"""

_GRID_JS = """<script>
(function(){
  var times=JSON.parse(decodeURIComponent(location.hash.slice(1)));
  var src=document.getElementById('src'), grid=document.getElementById('grid');
  times.forEach(function(t,i){
    var cell=document.createElement('div'); cell.className='cell';
    cell.innerHTML='<div class="lbl">'+(i+1)+' \\u00b7 t = '+t.toFixed(1)+' s</div>'+src.innerHTML;
    grid.appendChild(cell);
    cell.querySelector('svg').getAnimations({subtree:true}).forEach(function(x){ x.pause(); x.currentTime=t*1000; });
  });
  src.remove();
})();
</script>"""


def _key_times(raw: list[float]) -> list[float]:
    ts = []
    for t in sorted(raw):
        if not ts or t - ts[-1] > 0.25:
            ts.append(round(t, 2))
    # The last time is the still as the animation leaves it, and it must survive the merge above
    # — which keeps the first of a close cluster, so a fade ending just before would replace it and
    # the critic would see the still caught mid-fade.
    end = round(max(raw), 2)
    if ts[-1] != end:
        ts[-1] = end
    if len(ts) > MAX_FRAMES:                 # keep the first and the last, sample between
        step = (len(ts) - 1) / (MAX_FRAMES - 1)
        ts = [ts[round(i * step)] for i in range(MAX_FRAMES)]
    return ts


def write_frames(svg_text: str, ratio: float, out_dir: Path) -> str:
    sys.path.insert(0, str(HERE.parents[1] / "md-to-deck" / "scripts"))
    try:
        import _chrome
        if not _chrome.find():
            return "frames: failed (no Chrome/Chromium found)"
    except Exception as e:
        return f"frames: failed ({e})"
    svg = re.sub(r"<\?xml.*?\?>", "", svg_text, flags=re.DOTALL)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("frame-*.png"), out_dir / "contact.png"]:
        old.unlink(missing_ok=True)          # a revision with fewer frames must not leave strays
    probe = out_dir / ".probe.html"
    probe.write_text(f'<!doctype html><meta charset="utf-8"><body>{svg}{_TIMES_JS.replace("LONG", str(LONG))}</body>', encoding="utf-8")
    try:
        dom = _chrome.run(["--dump-dom", "--virtual-time-budget=2000"], _chrome.file_url(probe)).decode()
        times = _key_times(json.loads(re.search(r'data-times="([^"]*)"', dom).group(1).replace("&quot;", '"')))
    except Exception as e:
        probe.unlink(missing_ok=True)
        return f"frames: failed (could not read the timeline: {e})"
    cols = min(3, len(times))
    rows = -(-len(times) // cols)
    fh = round(FRAME_W / ratio)
    cell_h = fh + 28
    page = out_dir / ".grid.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><style>'
        f'body{{margin:0;background:#D8D2CE;font:14px Helvetica,Arial,sans-serif}}'
        f'#grid{{display:grid;grid-template-columns:repeat({cols},{FRAME_W}px);gap:0}}'
        f'.cell{{width:{FRAME_W}px;height:{cell_h}px;overflow:hidden}}'
        f'.lbl{{height:28px;line-height:28px;padding-left:8px;color:#1F1E1E}}'
        f'.cell svg{{display:block;width:{FRAME_W}px;height:{fh}px;background:#fff}}</style>'
        f'<body><div id="src" hidden>{svg}</div><div id="grid"></div>{_GRID_JS}</body>', encoding="utf-8")
    contact = out_dir / "contact.png"
    try:
        _chrome.run([f"--screenshot={contact}", f"--window-size={cols * FRAME_W},{rows * cell_h}",
                     "--force-device-scale-factor=1", "--hide-scrollbars"],
                    _chrome.file_url(page) + "#" + json.dumps(times).replace(" ", ""))
        from PIL import Image
        sheet = Image.open(contact)
        for i in range(len(times)):
            x, y = (i % cols) * FRAME_W, (i // cols) * cell_h + 28
            sheet.crop((x, y, x + FRAME_W, y + fh)).save(out_dir / f"frame-{i + 1:02d}.png")
    except Exception as e:
        return f"frames: failed ({e})"
    finally:
        probe.unlink(missing_ok=True)
        page.unlink(missing_ok=True)
    return f"frames: {out_dir} ({len(times)} frames, t = " + ", ".join(f"{t:g}" for t in times) + " s)"


def write_still(base_text: str, ratio: float, out_dir: Path) -> str:
    """The approved base, drawn by the same browser as the frames, as `still.png`.

    The critic compares the animation against the approved still, so both must come from one
    engine: the base's critique PNG is drawn by cairosvg, which does not synthesize italic, and
    every italic label of the approved drawing then read as one the animation restyled.
    """
    import _chrome
    svg = re.sub(r"<\?xml.*?\?>", "", base_text, flags=re.DOTALL)
    fh = round(FRAME_W / ratio)
    page, still = out_dir / ".still.html", out_dir / "still.png"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#fff}'
        f'svg{{display:block;width:{FRAME_W}px;height:{fh}px}}</style><body>{svg}</body>', encoding="utf-8")
    try:
        _chrome.run([f"--screenshot={still}", f"--window-size={FRAME_W},{fh}",
                     "--force-device-scale-factor=1", "--hide-scrollbars"], _chrome.file_url(page))
    except Exception as e:
        return f"still: failed ({e})"
    finally:
        page.unlink(missing_ok=True)
    return f"still: {still}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="directory for frame-*.png and contact.png")
    a = ap.parse_args(argv)
    try:
        text = a.svg.read_text(encoding="utf-8")
        root = ET.fromstring(text)
    except (OSError, ET.ParseError) as e:
        print(f"failed: frames: {e}")
        return 2
    if "@keyframes" not in text:
        print("failed: frames: the SVG has no animation")
        return 2
    vb = (root.get("viewBox") or "").replace(",", " ").split()
    ratio = float(vb[2]) / float(vb[3]) if len(vb) == 4 and float(vb[3]) else 16 / 9
    line = write_frames(text, ratio, a.out)
    print(line)
    if line.startswith("frames: failed"):
        return 2
    base = a.svg.with_name(a.svg.name.replace(".anim.svg", ".svg"))
    if base != a.svg and base.is_file():
        print(write_still(base.read_text(encoding="utf-8"), ratio, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
