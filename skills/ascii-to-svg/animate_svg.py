#!/usr/bin/env python3
"""Turn a rendered diagram's beat tags into its animation.

Usage:
    python3 animate_svg.py <svg> [--ascii <sidecar.ascii> | --beats N]

The renderer's only animation work is *tagging*: it wraps the elements each beat of the
`ascii-note`'s `animation:` section brings in as `<g data-beat="N">` (or marks an element that is
already on screen and lights up at beat N with `data-beat="N" data-beat-effect="pulse"`). This
script owns everything else — the timing, the keyframes, the scoping — so the motion is the same
fixed CSS in every diagram and none of it is model-authored.

Why CSS, and why the *still* state is the end state. The animation is a `<style>` block whose
keyframes start from hidden (`animation-fill-mode: backwards`); the elements' own attributes stay
fully visible. Everything that cannot or should not play it therefore draws the complete diagram
with no special case: cairosvg ignores `@keyframes` (the deliverable PNG, the critic's PNG and
the aspect audit all see the last beat), the deck switches `animation` off outside the present
slide, in the print view and with animations off, and the `.pptx` export switches it off in its
own raster page.

Why a per-diagram scope class. The deck inlines every SVG into one document, so a `<style>` in one
diagram applies to all of them. Every selector here hangs off `ts-anim-<stem>` on the root, so one
diagram's beat timings can never reach another's.

Exit codes: 0 = animated, or nothing to animate (`animation: none`); 1 = a tagging defect — the
file is left untouched (static and complete) and the line goes back to the renderer as a defect,
like an aspect-audit one; 2 = the SVG could not be read or parsed.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LEAD = 0.5         # s before beat 1 — lets the slide transition land first
STEP = 1.1         # s between beats
APPEAR = 0.6       # s a beat takes to fade in
PULSE = 0.8        # s an already-visible element takes to pulse

MARK = "/* talksmith-animation */"
_STYLE_RE = re.compile(r"<style[^>]*>\s*" + re.escape(MARK) + r".*?</style>\s*", re.DOTALL)
_ROOT_RE = re.compile(r"<svg\b[^>]*>")
_NOTE_OPEN = "<!-- ascii-note:"
_BEAT_LINE = re.compile(r"^\s*\d+\s*[.)]\s+\S")
_KEY_LINE = re.compile(r"^\s*[A-Za-z_-]+\s*:")
# Not rendered in place, so a beat there animates nothing the eye can follow.
_INERT = {"defs", "marker", "symbol", "clipPath", "mask", "pattern", "style", "title", "desc"}
_EFFECTS = {"appear", "pulse"}


def note_beats(sidecar_text: str) -> int | None:
    """Count the numbered beats under the note's `animation:` key; None when there is no key."""
    at = sidecar_text.find(_NOTE_OPEN)
    if at < 0:
        return None
    lines = sidecar_text[at:].split("-->", 1)[0].splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*animation\s*:", line):
            n = 0
            for rest in lines[i + 1:]:
                if _BEAT_LINE.match(rest):
                    n += 1
                elif _KEY_LINE.match(rest):
                    break
            return n
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
                eff = ch.get("data-beat-effect", "appear")
                if eff not in _EFFECTS:
                    defects.append(f"{where}: unknown data-beat-effect \"{eff}\" (appear | pulse)")
            elif ch.get("data-beat-effect") is not None:
                defects.append(f"<{name}> has data-beat-effect without data-beat")
            walk(ch, raw if raw is not None else tagged, inert or name in _INERT)

    walk(root, None, False)
    return beats, defects


def css(scope: str, n: int) -> str:
    s = "." + scope
    rules = [
        f"{s} [data-beat]{{animation:ts-beat-in {APPEAR:g}s ease-out backwards}}",
        f"{s} [data-beat-effect=pulse]{{animation-name:ts-beat-pulse;animation-duration:{PULSE:g}s;"
        "animation-fill-mode:none;transform-box:fill-box;transform-origin:center}",
    ]
    rules += [f'{s} [data-beat="{k}"]{{animation-delay:{LEAD + (k - 1) * STEP:.2f}s}}' for k in range(1, n + 1)]
    rules += [
        "@keyframes ts-beat-in{from{opacity:0}to{opacity:1}}",
        "@keyframes ts-beat-pulse{0%,100%{transform:none}50%{transform:scale(1.08)}}",
        f"@media (prefers-reduced-motion:reduce){{{s} [data-beat]{{animation:none}}}}",
    ]
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


def apply(svg_text: str, scope: str, n: int) -> str:
    """Strip any earlier animation, then (n > 0) inject the scoped style after <desc>/<title>."""
    out = _set_scope(_STYLE_RE.sub("", svg_text), scope if n else None)
    if not n:
        return out
    block = css(scope, n)
    for anchor in ("</desc>", "</title>"):
        i = out.find(anchor)
        if i >= 0:
            i += len(anchor)
            return out[:i] + "\n" + block + out[i:].lstrip("\n")
    m = _ROOT_RE.search(out)
    return out[:m.end()] + "\n" + block + out[m.end():]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("svg", type=Path)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ascii", type=Path, help="the block's .ascii sidecar — its note's beat count is the expectation")
    g.add_argument("--beats", type=int, help="the note's beat count, when there is no sidecar (Mode A)")
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

    expected = a.beats
    if a.ascii is not None:
        try:
            expected = note_beats(a.ascii.read_text(encoding="utf-8"))
        except OSError as e:
            print(f"failed: animation: {e}")
            return 2

    beats, defects = collect(root)
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
    new = apply(text, scope, top)
    if new != text:
        a.svg.write_text(new, encoding="utf-8")
    print(f"animation: {top} beats" if top else "animation: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
