#!/usr/bin/env python3
"""Turn a rendered diagram's beat tags into its animation.

Usage:
    python3 animate_svg.py <svg> [--ascii <sidecar.ascii> | --beats N [--loop]] [--frames <dir>]

The renderer's only animation work is *tagging*: it wraps the elements each beat of the
`ascii-note`'s `animation:` section brings in as `<g data-beat="N">` (or marks an element that is
already on screen and lights up at beat N with `data-beat="N" data-beat-effect="pulse"`). This
script owns everything else — the timing, the keyframes, the scoping — so the motion is the same
fixed CSS in every diagram and none of it is model-authored.

It plays **once** and holds the complete diagram. Only a note that says `animation: loop` cycles:
the beats arrive, the whole holds, fades, and the sequence starts over until the slide is left.

Why CSS, and why the *still* state is the end state. The animation is a `<style>` block whose
keyframes start from hidden (`animation-fill-mode: both`); the elements' own attributes stay
fully visible. Everything that cannot or should not play it therefore draws the complete diagram
with no special case: cairosvg ignores `@keyframes` (the deliverable PNG, the critic's PNG and
the aspect audit all see the last beat), the deck switches `animation` off outside the present
slide, in the print view and with animations off, and the `.pptx` export switches it off in its
own raster page.

Why `both` and not `backwards`, which would draw the same. A play-once animation that has
finished stops being "in effect" under `backwards`, and `getAnimations()` stops returning it —
so the deck's back-to-replay (`html_style.py` → `_DIAGRAM_REPLAY`) would find nothing to replay
on exactly the slide where the animation is done. Holding the end state keeps it reachable. The
price is that the animation owns `opacity` and `transform` on a tagged element for good, which
is why a tag on an element that sets either itself is a defect: it would be silently overridden.

Why a per-diagram scope class. The deck inlines every SVG into one document, so a `<style>` in one
diagram applies to all of them. Every selector here hangs off `ts-anim-<stem>` on the root, so one
diagram's beat timings can never reach another's — a looping diagram's per-beat keyframes are
named after it too.

`--frames <dir>` also rasterizes the diagram as it stands after each beat — `beat-0.png` (what
the slide opens on, before beat 1) through `beat-N.png` (complete, the same picture as the static
render) — plus `contact.png`, the frames side by side. They are for one reader: the blind
`diagram-critic`, which judges the order things arrive in from these pixels alone, never the SVG.
A `pulse` beat introduces nothing, so its frame matches the previous one.

Exit codes: 0 = animated, or nothing to animate (`animation: none`); 1 = a tagging defect — the
file is left untouched (static and complete) and the line goes back to the renderer as a defect,
like an aspect-audit one; 2 = the SVG could not be read or parsed.
"""
from __future__ import annotations

import argparse
import re
import sys
import contextlib
import io
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LEAD = 0.5         # s before beat 1 — lets the slide transition land first
STEP = 1.1         # s between beats
APPEAR = 0.6       # s a beat takes to fade in
PULSE = 0.8        # s an already-visible element takes to pulse
HOLD = 2.0         # loop only: s the complete diagram holds before the cycle restarts
FADE = 0.4         # loop only: s it takes to clear for the next cycle

MARK = "/* talksmith-animation */"
_STYLE_RE = re.compile(r"<style[^>]*>\s*" + re.escape(MARK) + r".*?</style>\s*", re.DOTALL)
_ROOT_RE = re.compile(r"<svg\b[^>]*>")
_NOTE_OPEN = "<!-- ascii-note:"
_BEAT_LINE = re.compile(r"^\s*\d+\s*[.)]\s+\S")
_KEY_LINE = re.compile(r"^\s*[A-Za-z_-]+\s*:")
# Not rendered in place, so a beat there animates nothing the eye can follow.
_INERT = {"defs", "marker", "symbol", "clipPath", "mask", "pattern", "style", "title", "desc"}
_EFFECTS = {"appear", "pulse"}


def note_animation(sidecar_text: str) -> tuple[int, str] | None:
    """The note's `animation:` section as (numbered beats, mode); None when there is no section.
    The mode is whatever follows the key on its own line — "" (play once) or "loop"."""
    at = sidecar_text.find(_NOTE_OPEN)
    if at < 0:
        return None
    lines = sidecar_text[at:].split("-->", 1)[0].splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*animation\s*:(.*)$", line)
        if m:
            n = 0
            for rest in lines[i + 1:]:
                if _BEAT_LINE.match(rest):
                    n += 1
                elif _KEY_LINE.match(rest):
                    break
            return n, m.group(1).strip().lower()
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def collect(root: ET.Element) -> tuple[dict[int, int], list[str]]:
    """Beat number → element count, plus the structural defects found on the way."""
    beats: dict[int, int] = {}
    defects: list[str] = []
    if root.get("data-beat") is not None:
        defects.append("data-beat on the root <svg> — tag the groups inside it")

    def walk(el: ET.Element, tagged: str | None, inert: bool) -> None:
        for ch in el:
            raw = ch.get("data-beat")
            name = _local(ch.tag)
            if raw is not None:
                where = f"<{name} data-beat=\"{raw}\">"
                if not raw.strip().isdigit() or int(raw) < 1:
                    defects.append(f"{where}: a beat is a whole number from 1")
                elif tagged is not None:
                    defects.append(f"{where} nested inside data-beat=\"{tagged}\" — never nest beats")
                elif inert or name in _INERT:
                    defects.append(f"{where} inside <defs>/<marker>/… — tag what is drawn, not its definition")
                else:
                    beats[int(raw)] = beats.get(int(raw), 0) + 1
                style = ch.get("style", "")
                if ch.get("opacity") or ch.get("transform") or re.search(r"\b(opacity|transform)\s*:", style):
                    defects.append(f"{where} sets opacity/transform itself — the animation drives "
                                   "those on the tagged element; move them to a child")
                eff = ch.get("data-beat-effect", "appear")
                if eff not in _EFFECTS:
                    defects.append(f"{where}: unknown data-beat-effect \"{eff}\" (appear | pulse)")
            elif ch.get("data-beat-effect") is not None:
                defects.append(f"<{name}> has data-beat-effect without data-beat")
            walk(ch, raw if raw is not None else tagged, inert or name in _INERT)

    walk(root, None, False)
    return beats, defects


def css(scope: str, n: int, loop: bool = False) -> str:
    return _css_loop(scope, n) if loop else _css_once(scope, n)


def _css_once(scope: str, n: int) -> str:
    s = "." + scope
    rules = [
        f"{s} [data-beat]{{animation:ts-beat-in {APPEAR:g}s ease-out both}}",
        f"{s} [data-beat-effect=pulse]{{animation-name:ts-beat-pulse;animation-duration:{PULSE:g}s;"
        "transform-box:fill-box;transform-origin:center}",
    ]
    rules += [f'{s} [data-beat="{k}"]{{animation-delay:{LEAD + (k - 1) * STEP:.2f}s}}' for k in range(1, n + 1)]
    rules += [
        "@keyframes ts-beat-in{from{opacity:0}to{opacity:1}}",
        "@keyframes ts-beat-pulse{0%,100%{transform:none}50%{transform:scale(1.08)}}",
        f"@media (prefers-reduced-motion:reduce){{{s} [data-beat]{{animation:none}}}}",
    ]
    return "<style>" + MARK + "\n" + "\n".join(rules) + "\n</style>\n"


def _css_loop(scope: str, n: int) -> str:
    """One shared cycle; each beat gets keyframes placing its entrance at its own point in it.
    A delay would only offset the first pass, so the timing lives in the keyframe percentages."""
    s = "." + scope
    cycle = LEAD + (n - 1) * STEP + APPEAR + HOLD + FADE
    pct = lambda t: f"{100 * t / cycle:.2f}%"
    rules = []
    for k in range(1, n + 1):
        at = LEAD + (k - 1) * STEP
        rules += [
            f'{s} [data-beat="{k}"]{{animation:{scope}-b{k} {cycle:g}s linear infinite}}',
            f'{s} [data-beat="{k}"][data-beat-effect=pulse]{{animation-name:{scope}-p{k};'
            "transform-box:fill-box;transform-origin:center}",
            f"@keyframes {scope}-b{k}{{0%,{pct(at)}{{opacity:0}}"
            f"{pct(at + APPEAR)},{pct(cycle - FADE)}{{opacity:1}}100%{{opacity:0}}}}",
            f"@keyframes {scope}-p{k}{{0%,{pct(at)},{pct(at + PULSE)},100%{{transform:none}}"
            f"{pct(at + PULSE / 2)}{{transform:scale(1.08)}}}}",
        ]
    rules.append(f"@media (prefers-reduced-motion:reduce){{{s} [data-beat]{{animation:none}}}}")
    return "<style>" + MARK + "\n" + "\n".join(rules) + "\n</style>\n"


def _set_scope(svg_text: str, scope: str | None) -> str:
    """Put `scope` on the root's class list (dropping any earlier ts-anim-* token); None removes it."""
    m = _ROOT_RE.search(svg_text)
    tag = m.group(0)
    cm = re.search(r'\sclass="([^"]*)"', tag)
    tokens = [t for t in (cm.group(1).split() if cm else []) if not t.startswith("ts-anim-")]
    if scope:
        tokens.append(scope)
    if cm:
        new = tag.replace(cm.group(0), f' class="{" ".join(tokens)}"' if tokens else "", 1)
    elif tokens:
        new = tag[:4] + f' class="{" ".join(tokens)}"' + tag[4:]
    else:
        new = tag
    return svg_text[:m.start()] + new + svg_text[m.end():]


def apply(svg_text: str, scope: str, n: int, loop: bool = False) -> str:
    """Strip any earlier animation, then (n > 0) inject the scoped style after <desc>/<title>."""
    out = _set_scope(_STYLE_RE.sub("", svg_text), scope if n else None)
    if not n:
        return out
    block = css(scope, n, loop)
    for anchor in ("</desc>", "</title>"):
        i = out.find(anchor)
        if i >= 0:
            i += len(anchor)
            return out[:i] + "\n" + block + out[i:].lstrip("\n")
    m = _ROOT_RE.search(out)
    return out[:m.end()] + "\n" + block + out[m.end():]


def _prune(el: ET.Element, k: int) -> None:
    """Drop every element that has not arrived yet at beat k (a pulse is already on screen)."""
    for ch in list(el):
        raw = ch.get("data-beat", "")
        if raw.isdigit() and int(raw) > k and ch.get("data-beat-effect", "appear") != "pulse":
            el.remove(ch)
        else:
            _prune(ch, k)


def write_frames(svg_text: str, n: int, out_dir: Path, width: int = 1600) -> str:
    """Rasterize beat-0 … beat-n and the contact sheet into out_dir; returns the report fragment."""
    import rasterize as R
    if R._load_cairosvg() is None:
        return "frames: failed (cairosvg unavailable)"
    for ns, uri in (("", "http://www.w3.org/2000/svg"), ("xlink", "http://www.w3.org/1999/xlink")):
        ET.register_namespace(ns, uri)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("beat-*.png"), out_dir / "contact.png"]:
        old.unlink(missing_ok=True)          # a revision with fewer beats must not leave strays
    pngs = []
    for k in range(n + 1):
        root = ET.fromstring(svg_text)
        _prune(root, k)
        tmp = out_dir / f".beat-{k}.svg"
        tmp.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
        png = out_dir / f"beat-{k}.png"
        with contextlib.redirect_stdout(io.StringIO()):
            code = R.rasterize(tmp, png, width)
        tmp.unlink(missing_ok=True)
        if code:
            return f"frames: failed (beat {k} did not rasterize)"
        pngs.append(png)
    try:
        from PIL import Image, ImageDraw
        thumbs = [Image.open(p).convert("RGB") for p in pngs]
        tw = 480
        thumbs = [t.resize((tw, round(t.height * tw / t.width))) for t in thumbs]
        per_row, gap, th = min(4, len(thumbs)), 16, max(t.height for t in thumbs)
        rows = -(-len(thumbs) // per_row)
        sheet = Image.new("RGB", (per_row * (tw + gap) + gap, rows * (th + gap + 20) + gap), "#D8D2CE")
        draw = ImageDraw.Draw(sheet)
        for i, t in enumerate(thumbs):
            x, y = gap + (i % per_row) * (tw + gap), gap + (i // per_row) * (th + gap + 20)
            draw.text((x, y), f"beat {i}", fill="#1F1E1E")
            sheet.paste(t, (x, y + 20))
        sheet.save(out_dir / "contact.png")
    except Exception as e:                   # the frames alone still serve the critic
        return f"frames: {out_dir} (no contact sheet: {e})"
    return f"frames: {out_dir}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("svg", type=Path)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ascii", type=Path, help="the block's .ascii sidecar — its note's beat count is the expectation")
    g.add_argument("--beats", type=int, help="the note's beat count, when there is no sidecar (Mode A)")
    ap.add_argument("--loop", action="store_true", help="with --beats: the note says `animation: loop`")
    ap.add_argument("--frames", type=Path, help="also rasterize each beat + a contact sheet here, for the critic")
    a = ap.parse_args(argv)

    try:
        text = a.svg.read_text(encoding="utf-8")
        root = ET.fromstring(text)
    except (OSError, ET.ParseError) as e:
        print(f"failed: animation: {e}")
        return 2
    if _local(root.tag) != "svg" or not _ROOT_RE.search(text):
        print("failed: animation: root element is not <svg>")
        return 2

    expected, mode = a.beats, ("loop" if a.loop else "")
    if a.ascii is not None:
        try:
            note = note_animation(a.ascii.read_text(encoding="utf-8"))
        except OSError as e:
            print(f"failed: animation: {e}")
            return 2
        expected, mode = note if note else (None, "")

    beats, defects = collect(root)
    if mode not in ("", "loop"):
        defects.append(f"unknown animation mode \"{mode}\" — `animation:` plays once, `animation: loop` cycles")
    top = max(beats, default=0)
    missing = [k for k in range(1, top + 1) if k not in beats]
    if missing:
        defects.append("beats are not contiguous — nothing tagged for " + ", ".join(map(str, missing)))
    if expected is not None and top != expected:
        defects.append(f"the note's animation has {expected} beat(s), the SVG tags {top}")
    if defects:
        print("animation: defect: " + "; ".join(defects))
        return 1

    scope = "ts-anim-" + (re.sub(r"[^a-z0-9-]+", "-", a.svg.stem.lower()).strip("-") or "svg")
    loop = mode == "loop"
    new = apply(text, scope, top, loop)
    if new != text:
        a.svg.write_text(new, encoding="utf-8")
    line = f"animation: {top} beats" + (", loop" if loop else "") if top else "animation: none"
    if top and a.frames is not None:
        line += " · " + write_frames(new, top, a.frames)
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
