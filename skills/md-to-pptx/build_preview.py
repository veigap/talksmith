"""Build the Step-5.5 draft preview end-to-end — one committed command.

This is the preview's renderer. It exists so the preview is **reproducible and lives
in the skill**, instead of the agent hand-rolling a throwaway script each run (which
defeats the point of a plugin). Run this; never improvise a renderer.

The preview is a fast, throwaway visual of `draft.md` — a per-slide PNG grid so the
presenter can eyeball slide order and rough content before Polish. Because the
deliverable is images (not a deliverable deck), the whole thing renders **by code**
with Pillow — no native `pptx` skill, no LibreOffice, no Cowork dependency. Styling is
deliberately provisional (a wireframe): monospace text, ASCII diagrams as PNGs, image
refs as thumbnails/placeholders. The real look comes from Step 8 (strict/free-form).

Pipeline (all deterministic, all reusing the sibling substrate):
    1. convert.py  --draft --split-dir → per-slide `slide-NN.md` units + intermediate
    2. preview_plan.py                 → per-slide reuse|render (content-addressed cache)
    3. render_ascii.py                 → ASCII fences → PNG (for the render units only)
    4. this file                       → render each render-unit to a slide PNG (Pillow)
                                          + assemble the contact-sheet grid; reuse cached
                                          slide PNGs for unchanged units

Outputs under `talks/<Talk>/output/draft-preview/`:
    units/slide-NN.md          preview.intermediate.md
    ascii/ascii-<hash>.png     .previews/slide-<hash>.png     grid.png
    .preview-cache.json

Requires Pillow. Degrades: a missing monospace font falls back to Pillow's default.

Usage:
    python3 build_preview.py --talk talks/<Talk> [--font-size 22] [--cols 4]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import convert as _convert           # noqa: E402
import preview_plan as _plan         # noqa: E402
import render_ascii as _ra           # noqa: E402

SLIDE_W, SLIDE_H = 1280, 720         # 16:9 wireframe canvas
_PAD = 48
_TEXT = (31, 30, 30)                 # #1F1E1E
_MUTED = (140, 140, 140)
_BG = (255, 255, 255)
_PLACEHOLDER = (238, 238, 238)
_ACCENT = (218, 27, 46)              # #DA1B2E hairline

_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_INLINE_MD_RE = re.compile(r"\*\*|__|`|(?<!\w)[*_](?!\s)")


def _clean_inline(s: str) -> str:
    """Strip inline markdown emphasis (**bold**, *italic*, `code`) for the wireframe."""
    return _INLINE_MD_RE.sub("", s).strip()


def _font(size: int):
    from PIL import ImageFont
    for p in _ra._FONT_CANDIDATES:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _parse_unit(md: str, talk_root: Path, preview_dir: Path):
    """Return (title, is_divider, body_lines, image_paths) from a unit's markdown."""
    title, is_divider, body, images = "", False, [], []
    for raw in md.splitlines():
        m = _HEAD_RE.match(raw.strip())
        if m and not title:
            title = _clean_inline(m.group(2))
            is_divider = len(m.group(1)) == 1  # H1 → section divider
            continue
        for im in _IMG_RE.finditer(raw):
            images.append((im.group(1), im.group(2)))
        line = _IMG_RE.sub("", raw).rstrip()
        if line.strip() and not m:
            body.append(_clean_inline(line))
    # Resolve image paths (relative to preview dir, then talk root).
    resolved = []
    for alt, ref in images:
        if ref.startswith(("http://", "https://")):
            resolved.append((alt, None))
            continue
        cand = [preview_dir / ref, talk_root / ref, Path(ref)]
        hit = next((c for c in cand if c.is_file()), None)
        resolved.append((alt, hit))
    return title, is_divider, body, resolved


def _render_slide(unit_md: str, out_png: Path, talk_root: Path, preview_dir: Path,
                  font_size: int, index: int, total: int) -> None:
    from PIL import Image, ImageDraw
    title, is_divider, body, images = _parse_unit(unit_md, talk_root, preview_dir)

    img = Image.new("RGB", (SLIDE_W, SLIDE_H), _BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, SLIDE_W - 1, SLIDE_H - 1], outline=(225, 225, 225))
    d.line([0, 0, SLIDE_W, 0], fill=_ACCENT, width=6)

    if is_divider:
        f = _font(int(font_size * 2.2))
        lines = _wrap(d, title or "(section)", f, SLIDE_W - 2 * _PAD)
        th = sum(f.size + 12 for _ in lines)
        y = (SLIDE_H - th) // 2
        for ln in lines:
            w = d.textlength(ln, font=f)
            d.text(((SLIDE_W - w) / 2, y), ln, font=f, fill=_TEXT)
            y += f.size + 12
        d.text((_PAD, SLIDE_H - _PAD), f"{index}/{total} · section", font=_font(font_size - 6), fill=_MUTED)
        img.save(out_png)
        return

    ft = _font(int(font_size * 1.5))
    for ln in _wrap(d, title or "(untitled)", ft, SLIDE_W - 2 * _PAD)[:2]:
        d.text((_PAD, _PAD), ln, font=ft, fill=_TEXT)
        break
    y = _PAD + int(ft.size * 1.8)

    # Layout: if images, text on left half, images stacked on right half.
    text_w = (SLIDE_W - 2 * _PAD) if not images else int((SLIDE_W - 2 * _PAD) * 0.55)
    fb = _font(font_size)
    for line in body:
        if y > SLIDE_H - _PAD - fb.size:
            d.text((_PAD, y), "…", font=fb, fill=_MUTED)
            break
        bullet = line.lstrip().startswith(("-", "*", "•"))
        txt = line.lstrip("-*• ").strip() if bullet else line.strip()
        prefix = "• " if bullet else ""
        for wl in _wrap(d, prefix + txt, fb, text_w):
            if y > SLIDE_H - _PAD - fb.size:
                break
            d.text((_PAD, y), wl, font=fb, fill=_TEXT)
            y += fb.size + 8

    if images:
        ix = _PAD + text_w + 24
        iw = SLIDE_W - _PAD - ix
        iy = _PAD + int(ft.size * 1.8)
        per = (SLIDE_H - iy - _PAD) // min(len(images), 3) - 16
        for alt, path in images[:3]:
            box = [ix, iy, ix + iw, iy + per]
            if path is not None:
                try:
                    thumb = Image.open(path).convert("RGB")
                    thumb.thumbnail((iw, per))
                    img.paste(thumb, (ix, iy))
                except Exception:
                    path = None
            if path is None:
                d.rectangle(box, fill=_PLACEHOLDER, outline=(200, 200, 200))
                lbl = (alt or "image")[:24]
                d.text((ix + 10, iy + per // 2 - 8), f"[{lbl}]", font=_font(font_size - 6), fill=_MUTED)
            iy += per + 16

    d.text((_PAD, SLIDE_H - _PAD), f"{index}/{total}", font=_font(font_size - 6), fill=_MUTED)
    img.save(out_png)


def _assemble_grid(slide_pngs: list[Path], out_png: Path, cols: int) -> None:
    from PIL import Image
    if not slide_pngs:
        return
    thumb_w = 320
    thumb_h = int(thumb_w * SLIDE_H / SLIDE_W)
    rows = (len(slide_pngs) + cols - 1) // cols
    gap = 12
    grid = Image.new("RGB", (cols * thumb_w + (cols + 1) * gap,
                             rows * thumb_h + (rows + 1) * gap), (245, 245, 245))
    for i, p in enumerate(slide_pngs):
        try:
            t = Image.open(p).convert("RGB").resize((thumb_w, thumb_h))
        except Exception:
            continue
        r, c = divmod(i, cols)
        grid.paste(t, (gap + c * (thumb_w + gap), gap + r * (thumb_h + gap)))
    grid.save(out_png)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--font-size", type=int, default=22)
    ap.add_argument("--cols", type=int, default=4)
    args = ap.parse_args(argv)

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("failed: Pillow is required for the preview build", file=sys.stderr)
        return 3

    talk = args.talk
    draft = talk / "draft.md"
    if not draft.is_file():
        print(f"failed: {draft} not found", file=sys.stderr)
        return 2

    pdir = talk / "output" / "draft-preview"
    units_dir, ascii_dir, slides_dir = pdir / "units", pdir / "ascii", pdir / ".previews"
    for dd in (units_dir, ascii_dir, slides_dir):
        dd.mkdir(parents=True, exist_ok=True)

    # 1. convert --draft --split-dir
    converted = _convert.convert(draft.read_text(encoding="utf-8"), draft=True)
    (pdir / "preview.intermediate.md").write_text(converted, encoding="utf-8")
    units = _convert._split_into_slide_units(converted)
    width = max(2, len(str(len(units))))
    for i, u in enumerate(units, 1):
        (units_dir / f"slide-{i:0{width}d}.md").write_text(u + "\n", encoding="utf-8")
    print(f"[preview 1/4] {len(units)} slides from draft.md", file=sys.stderr)

    # 2. incremental plan
    unit_files = sorted(p for p in units_dir.glob("slide-*.md")
                        if re.match(r"^slide-\d+\.md$", p.name))
    manifest_path = pdir / ".preview-cache.json"
    prior = _plan._load_manifest(manifest_path)
    plan = _plan.compute_plan(unit_files, prior, slides_dir, _plan.RENDER_VERSION)
    n_render = sum(1 for u in plan if u["action"] == "render")
    print(f"[preview 2/4] {n_render} to render, {len(plan) - n_render} reused", file=sys.stderr)

    # 3+4. render the changed slides (ASCII→PNG, then slide PNG); reuse the rest.
    total = len(plan)
    new_units = {}
    for u in plan:
        png = Path(u["slide_png"])
        if u["action"] == "reuse" and png.is_file():
            new_units[u["hash"]] = {"png": str(png), "verdict": (u.get("verdict"))}
            continue
        md = Path(u["unit_md"]).read_text(encoding="utf-8")
        md, _ = _ra.rewrite(md, ascii_dir, pdir, args.font_size)  # ASCII fences → PNG refs
        _render_slide(md, png, talk, pdir, args.font_size, u["index"], total)
        new_units[u["hash"]] = {"png": str(png), "verdict": None}
        if u["index"] % 8 == 0:
            print(f"[preview 3/4] rendered {u['index']}/{total}…", file=sys.stderr)
    print(f"[preview 3/4] slides ready ({total})", file=sys.stderr)

    # grid + manifest
    ordered = [Path(u["slide_png"]) for u in plan]
    grid = pdir / "grid.png"
    _assemble_grid(ordered, grid, args.cols)
    manifest_path.write_text(json.dumps(
        {"render_version": _plan.RENDER_VERSION, "units": new_units}, indent=2), encoding="utf-8")
    print(f"[preview 4/4] grid → {grid}", file=sys.stderr)
    print(str(grid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
