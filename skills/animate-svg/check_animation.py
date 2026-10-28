#!/usr/bin/env python3
"""Check an animated diagram against the deck's contract, and capture its frames for the critic.

Usage:
    python3 check_animation.py <svg> [--ascii <sidecar.ascii> | --loop] [--frames <dir>]

The `animate-svg` pass **authors** a diagram's animation: the model reads the finished diagram and
its subject and evolves the SVG (`SKILL.md`). No script could parametrize that — every diagram
calls for its own motion. What a script can own is the part that does not depend on the
diagram: the contract the deck relies on to play, gate and replay an animation. That is this
file. It never writes the SVG, and passing it says nothing about whether the animation is good —
the blind critic judges that, from the frames this file captures.

The contract, and why each clause exists:

1. **One marked `<style>`** (`/* talksmith-animation */`), every selector starting with the root's
   scope class `.ts-anim-<stem>` and every `@keyframes` name with `ts-anim-<stem>-`. The deck
   inlines every SVG into one document, so an unscoped rule or keyframe in one diagram reaches —
   or is overwritten by — another's.
2. **CSS animations only** — no SMIL (`<animate*>`, `<set>`), no `<script>`, no `on*` handlers.
   The deck's off-switch (`animation: none` off the present slide, in print, with animations
   off) and its back-to-replay (`getAnimations()`) only reach CSS animations; SMIL would keep
   running on hidden slides and in the PDF.
3. **Plays once unless the note says `animation: loop`** — no `infinite`, no iteration count
   above 1, otherwise.
4. **Finished animations hold** — every animated rule says `both` or `forwards`. A play-once
   animation that has finished is otherwise no longer "in effect", `getAnimations()` stops
   returning it, and back-to-replay finds nothing on exactly the slide where it is done.
5. **Reduced motion respected** — a `prefers-reduced-motion` rule that turns it off.

One clause is not checked here because only pixels can: **the still is the complete diagram**.
Elements' own attributes draw the final static picture; whatever only narrates (a token, a
caption, a highlight) starts at `opacity="0"` and is shown only by the animation. cairosvg ignores
`@keyframes`, so the deliverable and critique PNGs show exactly that still, and the critic judges
it (`[A13]`).

`--frames <dir>` loads the SVG in headless Chrome (the browser the deck plays in, located by
`md-to-deck/_chrome.py`), reads the animation's own timeline, and captures a frame at the start,
at the end of every short animation (an appearance: its settled state) — plus its midpoint when it
moves something, so a quick journey is seen under way and not only arrived — at a quarter, half and
three quarters of every long one (something travelling or on screen for a while, which often
ends faded out, so its end alone would show nothing), and a last one once everything has ended,
as `frame-01.png` …, plus `contact.png` with every frame labelled by its time. They are for one reader: the blind
`diagram-critic`, which judges the animation from these pixels alone, never the SVG.

Exit codes: 0 = conforms (or no animation: `animation: none`); 1 = a contract defect — reported
verbatim back to the renderer, like an aspect-audit one; 2 = the SVG could not be read or parsed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "/* talksmith-animation */"
_STYLE_RE = re.compile(r"<style[^>]*>\s*" + re.escape(MARK) + r"(.*?)</style>", re.DOTALL)
_NOTE_OPEN = re.compile(r"<!--\s*(?:ascii|image)-note:")   # ASCII-drawn or hand-drawn diagram
_SMIL = {"animate", "animateMotion", "animateTransform", "animateColor", "set", "script"}
MAX_FRAMES = 16
LONG = 2.0                        # s — an animation at least this long is a journey, sampled inside
FRAME_W = 800                     # px per captured frame


def note_animation(sidecar_text: str) -> str | None:
    """The mode on the note's `animation:` key line ("" or "loop"); None when there is no section."""
    at = _NOTE_OPEN.search(sidecar_text)
    if not at:
        return None
    m = re.search(r"^\s*animation\s*:(.*)$", sidecar_text[at.start():].split("-->", 1)[0], re.MULTILINE)
    return m.group(1).strip().lower() if m else None


def _blocks(css: str):
    """Top-level (prelude, body) pairs of a stylesheet, comments stripped; bodies keep nesting."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            return
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        yield css[i:j].strip(), css[j + 1:k - 1]
        i = k


def check_css(css: str, scope: str, loop: bool) -> list[str]:
    defects: list[str] = []
    animated, reduced = False, False

    def rule(prelude: str, body: str) -> None:
        nonlocal animated
        for sel in prelude.split(","):
            if not re.match(rf"\.{re.escape(scope)}(?![\w-])", sel.strip()):
                defects.append(f"selector \"{sel.strip()}\" is not scoped — start it with .{scope}")
        if re.search(r"\banimation(-name)?\s*:", body) and not re.search(r"\banimation(-name)?\s*:\s*none\b", body):
            animated = True
            if not loop and not re.search(r"\b(both|forwards)\b", body):
                defects.append(f"\"{prelude}\" animates without fill-mode both/forwards — a finished "
                               "animation would drop out of reach of back-to-replay")
        if not loop and (re.search(r"\binfinite\b", body) or
                         any(float(c) > 1 for c in re.findall(r"animation-iteration-count\s*:\s*([\d.]+)", body))):
            defects.append(f"\"{prelude}\" repeats, but the note does not say `animation: loop`")

    for prelude, body in _blocks(css):
        if prelude.startswith("@keyframes"):
            name = prelude.split(None, 1)[1].strip() if len(prelude.split()) > 1 else ""
            if not name.startswith(scope + "-"):
                defects.append(f"@keyframes {name} is not scoped — name it {scope}-…")
        elif prelude.startswith("@media"):
            if "prefers-reduced-motion" in prelude:
                reduced = True
            for p, b in _blocks(body):
                rule(p, b)
        elif prelude.startswith("@"):
            defects.append(f"{prelude.split()[0]} is not allowed in a diagram's animation")
        else:
            rule(prelude, body)
    if not animated:
        defects.append("the marked <style> animates nothing")
    if not reduced:
        defects.append("no @media (prefers-reduced-motion: reduce) rule turning the animation off")
    return defects


def check(svg_text: str, root: ET.Element, scope: str, mode: str | None) -> tuple[bool, list[str]]:
    """(has an animation, defects) for the SVG given the note's mode (None = the note has none)."""
    defects: list[str] = []
    for el in root.iter():
        name = el.tag.rsplit("}", 1)[-1]
        if name in _SMIL:
            defects.append(f"<{name}> — animate with CSS only (the deck cannot gate or replay SMIL or script)")
        for attr in el.attrib:
            if attr.lower().startswith("on"):
                defects.append(f"<{name} {attr}=…> — no event handlers in a diagram")
    styles = _STYLE_RE.findall(svg_text)
    if not styles:
        if mode is not None:
            defects.append("the note has an `animation:` section but the SVG carries no "
                           f"`<style>{MARK}` block")
        return False, defects
    if len(styles) > 1:
        defects.append("more than one talksmith-animation <style> — keep it in one block")
    if scope not in (root.get("class") or "").split():
        defects.append(f"the root <svg> lacks class=\"{scope}\" — every selector hangs off it")
    if mode not in (None, "", "loop"):
        defects.append(f"unknown animation mode \"{mode}\" — `animation:` plays once, `animation: loop` cycles")
    defects += check_css("\n".join(styles), scope, mode == "loop")
    return True, defects


# --- frames ------------------------------------------------------------------------------------

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
    sys.path.insert(0, str(HERE.parent / "md-to-deck"))
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("svg", type=Path)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ascii", type=Path, help="the .ascii sidecar, or any file holding the diagram's note — it says whether, and how, it animates")
    g.add_argument("--loop", action="store_true", help="Mode A: the note says `animation: loop`")
    ap.add_argument("--frames", type=Path, help="also capture the animation's key frames + a contact sheet here, for the critic")
    a = ap.parse_args(argv)

    try:
        text = a.svg.read_text(encoding="utf-8")
        root = ET.fromstring(text)
    except (OSError, ET.ParseError) as e:
        print(f"failed: animation: {e}")
        return 2
    if root.tag.rsplit("}", 1)[-1] != "svg":
        print("failed: animation: root element is not <svg>")
        return 2

    mode: str | None = "loop" if a.loop else None      # no sidecar: no expectation either way
    if a.ascii is not None:
        try:
            mode = note_animation(a.ascii.read_text(encoding="utf-8"))
        except OSError as e:
            print(f"failed: animation: {e}")
            return 2

    stem = a.svg.stem[:-len(".anim")] if a.svg.stem.endswith(".anim") else a.svg.stem   # x.anim.svg → x
    scope = "ts-anim-" + (re.sub(r"[^a-z0-9-]+", "-", stem.lower()).strip("-") or "svg")
    animated, defects = check(text, root, scope, mode)
    if defects:
        print("animation: defect: " + "; ".join(dict.fromkeys(defects)))
        return 1
    if not animated:
        print("animation: none")
        return 0
    line = "animation: ok" + (", loop" if mode == "loop" else "")
    if a.frames is not None:
        vb = (root.get("viewBox") or "").replace(",", " ").split()
        ratio = float(vb[2]) / float(vb[3]) if len(vb) == 4 and float(vb[3]) else 16 / 9
        line += " · " + write_frames(text, ratio, a.frames)
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
