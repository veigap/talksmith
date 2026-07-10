"""Build the Step-5.5 draft preview end-to-end — one committed command.

This is the preview's renderer. It exists so the preview is **reproducible and lives
in the skill**, instead of the agent hand-rolling a throwaway script each run (which
defeats the point of a plugin). Run this; never improvise a renderer.

The preview is a fast, throwaway visual of `draft.md` — ordered, numbered per-slide PNGs
(`slide-01.png … slide-NN.png`) so the presenter can flip through slide order and rough
content before Polish. Because the deliverable is images (not a deck), it renders **by code**
with Pillow — no native `pptx` skill, no LibreOffice, no Cowork dependency. Styling is
deliberately provisional (a wireframe): monospace text, ASCII diagrams as PNGs, image
refs as thumbnails/placeholders. The real look comes from Step 8 (strict/free-form).

The wireframe is **template-aware**: each slide is classified against the shared catalog
`config/pptx-styles/slide-templates.md` (`_classify`) and drawn in that template's shape —
concept-breakdown/process/figures as **cards** (never bullets, per the catalog's universal
invariant), content+image as a text/image split, code-example as a mono block, statement as
one large claim, image-grid as a dense grid — falling back to a plain title+body flow when
nothing matches. Bump `preview_plan.RENDER_VERSION` when this render recipe changes.

Pipeline (all deterministic, all reusing the sibling substrate):
    1. convert.py  --draft --split-dir → per-slide `slide-NN.md` units + intermediate
    2. preview_plan.py                 → per-slide reuse|render (content-addressed cache)
    3. render_ascii.py                 → ASCII fences → PNG (for the render units only)
    4. this file                       → render each render-unit to a slide PNG (Pillow),
                                          reuse cached PNGs for unchanged units, then emit
                                          ordered, numbered review images slide-01.png …

Outputs under `talks/<Talk>/output/draft-preview/`:
    slide-01.png … slide-NN.png   ← the numbered review images (open these, in order)
    units/slide-NN.md             preview.intermediate.md
    ascii/ascii-<hash>.png        .previews/slide-<hash>.png   ← content-addressed cache
    .preview-cache.json

The `.previews/slide-<hash>.png` files are the incremental cache (stable across runs so
unchanged slides are reused); the top-level `slide-NN.png` are the ordered copies the
presenter reviews. No grid, no `.pptx`, no `.pdf`.

Requires Pillow. Degrades: a missing monospace font falls back to Pillow's default.

Usage:
    python3 build_preview.py --talk talks/<Talk> [--font-size 22]
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

# Labeled-item signals (detected BEFORE inline-markdown is stripped) — a labeled
# enumeration renders as cards, never bullets (slide-templates.md universal invariant).
_EMOJI = r"(?:[^\w\s]️?\s*)?"
_BOLD_ITEM_RE = re.compile(rf"^\s*[-*+]\s+{_EMOJI}\*\*(.+?)\*\*[:：]?\s*(.*)$")   # - **Label** body
_H34_RE = re.compile(r"^(#{3,4})\s+(.+?)\s*$")                                     # ### / #### Label
_ORDERED_RE = re.compile(
    r"^\s*(?:\d+\s*[.)]|paso\s+\w+|step\s+\w+|fase\s+\w+|etapa\s+\w+|caso\s+\w+)\b", re.I)
_PLAIN_BULLET_RE = re.compile(r"^\s*[-*+•]\s+")
_FENCE_RE = re.compile(r"^\s*```")

# Wireframe palette for template shapes.
_CARD_FILL = (242, 238, 238)     # #F2EEEE
_CARD_LINE = (214, 210, 210)
_CODE_FILL = (242, 242, 242)     # #F2F2F2
_NUM_FILL = (218, 27, 46)        # #DA1B2E numbered strip


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


def _parse_unit(md: str, talk_root: Path, preview_dir: Path) -> dict:
    """Extract the catalog classification signals from a slide unit.

    Returns a dict: title, level (1=divider/H1), body (plain lines, no items),
    items (list of {label, body}), ordered (bool), images (resolved), has_code,
    code_lines. Labeled items are detected on the *raw* line (before inline markdown
    is stripped) so a labeled enumeration is never mistaken for prose/bullets.
    """
    title, level, body, images = "", 0, [], []
    items: list[dict] = []
    code_lines: list[str] = []
    in_code = False
    cur: dict | None = None            # the item currently accumulating body lines

    def _flush():
        nonlocal cur
        if cur is not None:
            cur["body"] = cur["body"].strip()
            items.append(cur)
            cur = None

    for raw in md.splitlines():
        if _FENCE_RE.match(raw):
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(raw)
            continue
        head = _HEAD_RE.match(raw.strip())
        if head and not title:
            title = _clean_inline(head.group(2))
            level = len(head.group(1))
            continue
        for im in _IMG_RE.finditer(raw):
            images.append((im.group(1), im.group(2)))
        line = _IMG_RE.sub("", raw).rstrip()
        if not line.strip():
            continue
        bold = _BOLD_ITEM_RE.match(line)
        sub = _H34_RE.match(line)
        if bold:
            _flush()
            cur = {"label": _clean_inline(bold.group(1)), "body": _clean_inline(bold.group(2))}
        elif sub:
            _flush()
            cur = {"label": _clean_inline(sub.group(2)), "body": ""}
        elif cur is not None and not head:
            cur["body"] = (cur["body"] + " " + _clean_inline(line)).strip()
        elif not head:
            body.append(_clean_inline(_PLAIN_BULLET_RE.sub("", line)))
    _flush()

    ordered = any(_ORDERED_RE.match(it["label"]) for it in items) or \
        any(_ORDERED_RE.match(b) for b in body)

    resolved = []
    for alt, ref in images:
        if ref.startswith(("http://", "https://")):
            resolved.append((alt, None)); continue
        cand = [preview_dir / ref, talk_root / ref, Path(ref)]
        resolved.append((alt, next((c for c in cand if c.is_file()), None)))

    return {"title": title, "level": level, "body": body, "items": items,
            "ordered": ordered, "images": resolved,
            "has_code": bool(code_lines), "code_lines": code_lines}


def _classify(u: dict) -> str:
    """Map a parsed unit to a catalog template id (slide-templates.md)."""
    if u["level"] == 1:
        return "divider"
    if u["has_code"]:
        return "code-example"
    ni, nimg = len(u["items"]), len(u["images"])
    words = sum(len(b.split()) for b in u["body"])
    if nimg >= 4 and ni < 3:
        return "image-grid"
    if ni >= 3:
        if u["ordered"]:
            return "process"
        if nimg >= ni and nimg >= 2:
            return "figures"
        return "concept-breakdown"           # unordered labeled card set
    if nimg >= 1:
        return "content-image"
    if ni == 0 and len(u["body"]) <= 2 and words <= 18 and u["title"]:
        return "statement"
    return "fallback"


def _header(d, img_title: str, font_size: int, index: int, total: int, tag: str = ""):
    """Draw the shared wireframe chrome (border, accent, title, footer). Returns body-top y."""
    ft = _font(int(font_size * 1.4))
    for ln in _wrap(d, img_title or "(untitled)", ft, SLIDE_W - 2 * _PAD)[:2]:
        d.text((_PAD, _PAD), ln, font=ft, fill=_TEXT)
        break
    d.text((_PAD, SLIDE_H - _PAD), f"{index}/{total}{tag}", font=_font(font_size - 6), fill=_MUTED)
    return _PAD + int(ft.size * 1.7)


def _paste_or_box(img, d, path, alt, box, font_size):
    from PIL import Image
    x0, y0, x1, y1 = box
    if path is not None:
        try:
            thumb = Image.open(path).convert("RGB")
            thumb.thumbnail((x1 - x0, y1 - y0))
            img.paste(thumb, (x0, y0))
            return
        except Exception:
            pass
    d.rectangle(box, fill=_PLACEHOLDER, outline=(200, 200, 200))
    d.text((x0 + 8, (y0 + y1) // 2 - 8), f"[{(alt or 'image')[:22]}]",
           font=_font(font_size - 6), fill=_MUTED)


def _draw_card(img, d, box, label, body, font_size, number=None, image=None):
    """One card: light panel + (optional number strip) + label + wrapped body. Never a bullet."""
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=_CARD_FILL, outline=_CARD_LINE)
    tx = x0 + 14
    if number is not None:
        d.rectangle([x0, y0, x0 + 8, y1], fill=_NUM_FILL)
        tx = x0 + 22
        d.text((tx, y0 + 10), str(number), font=_font(font_size - 4), fill=_NUM_FILL)
        tx += 22
    ty = y0 + 10
    if image is not None:
        ih = min((y1 - y0) // 2, 120)
        _paste_or_box(img, d, image, "", [tx, ty, x1 - 12, ty + ih], font_size)
        ty += ih + 8
    fl = _font(font_size - 2)
    for ln in _wrap(d, label or "", fl, x1 - tx - 12)[:2]:
        d.text((tx, ty), ln, font=fl, fill=_TEXT); ty += fl.size + 4
    fb = _font(font_size - 5)
    for ln in _wrap(d, body or "", fb, x1 - tx - 12):
        if ty > y1 - fb.size - 6:
            break
        d.text((tx, ty), ln, font=fb, fill=(90, 90, 90)); ty += fb.size + 3


def _grid_boxes(n, top, with_images=False):
    """Card boxes for n items: a row for ≤3 (or images), else a 2/3-col grid."""
    cols = 1 if n == 1 else (3 if (n == 3 or n >= 5) else 2)
    rows = (n + cols - 1) // cols
    gx, gy = 20, 18
    x0, y0 = _PAD, top
    cw = (SLIDE_W - 2 * _PAD - (cols - 1) * gx) // cols
    ch = (SLIDE_H - top - _PAD - (rows - 1) * gy) // rows
    boxes = []
    for i in range(n):
        r, c = divmod(i, cols)
        bx = x0 + c * (cw + gx)
        by = y0 + r * (ch + gy)
        boxes.append([bx, by, bx + cw, by + ch])
    return boxes


def _render_slide(unit_md: str, out_png: Path, talk_root: Path, preview_dir: Path,
                  font_size: int, index: int, total: int) -> None:
    from PIL import Image, ImageDraw
    u = _parse_unit(unit_md, talk_root, preview_dir)
    kind = _classify(u)

    img = Image.new("RGB", (SLIDE_W, SLIDE_H), _BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, SLIDE_W - 1, SLIDE_H - 1], outline=(225, 225, 225))
    d.line([0, 0, SLIDE_W, 0], fill=_ACCENT, width=6)

    # ── divider / section ──
    if kind == "divider":
        f = _font(int(font_size * 2.2))
        lines = _wrap(d, u["title"] or "(section)", f, SLIDE_W - 2 * _PAD)
        y = (SLIDE_H - sum(f.size + 12 for _ in lines)) // 2
        for ln in lines:
            w = d.textlength(ln, font=f)
            d.text(((SLIDE_W - w) / 2, y), ln, font=f, fill=_TEXT); y += f.size + 12
        d.text((_PAD, SLIDE_H - _PAD), f"{index}/{total} · section",
               font=_font(font_size - 6), fill=_MUTED)
        img.save(out_png); return

    # ── statement: one large claim, no cards ──
    if kind == "statement":
        f = _font(int(font_size * 2.0))
        y = SLIDE_H // 3
        for ln in _wrap(d, u["title"] or "", f, SLIDE_W - 2 * _PAD):
            d.text((_PAD, y), ln, font=f, fill=_TEXT); y += f.size + 10
        fb = _font(font_size)
        for b in u["body"][:2]:
            for ln in _wrap(d, b, fb, SLIDE_W - 2 * _PAD):
                d.text((_PAD, y), ln, font=fb, fill=(90, 90, 90)); y += fb.size + 6
        d.text((_PAD, SLIDE_H - _PAD), f"{index}/{total} · statement",
               font=_font(font_size - 6), fill=_MUTED)
        img.save(out_png); return

    top = _header(d, u["title"], font_size, index, total, f" · {kind}")

    # ── code-example: mono block right, explanation left ──
    if kind == "code-example":
        code_w = int((SLIDE_W - 2 * _PAD) * 0.5)
        cx0 = SLIDE_W - _PAD - code_w
        d.rectangle([cx0, top, SLIDE_W - _PAD, SLIDE_H - _PAD], fill=_CODE_FILL, outline=_CARD_LINE)
        fc = _font(font_size - 6)
        cy = top + 10
        for ln in u["code_lines"][:22]:
            d.text((cx0 + 10, cy), ln[:52], font=fc, fill=(31, 30, 30)); cy += fc.size + 3
        fb = _font(font_size - 2)
        ey = top
        for b in u["body"]:
            for ln in _wrap(d, b, fb, code_w - 20):
                if ey > SLIDE_H - _PAD - fb.size:
                    break
                d.text((_PAD, ey), ln, font=fb, fill=_TEXT); ey += fb.size + 6
        img.save(out_png); return

    # ── figures / image-grid: image cards ──
    if kind in ("figures", "image-grid"):
        cells = u["items"] if (kind == "figures" and u["items"]) else \
            [{"label": a, "body": ""} for a, _ in u["images"]]
        imgs = [p for _, p in u["images"]]
        boxes = _grid_boxes(max(1, len(cells)), top, with_images=True)
        for i, (box, cell) in enumerate(zip(boxes, cells)):
            _draw_card(img, d, box, cell["label"], cell["body"], font_size,
                       image=imgs[i] if i < len(imgs) else None)
        img.save(out_png); return

    # ── card sets: concept-breakdown / process (+ folded stat/comparison) ──
    if kind in ("concept-breakdown", "process"):
        boxes = _grid_boxes(len(u["items"]), top)
        for i, (box, it) in enumerate(zip(boxes, u["items"]), 1):
            _draw_card(img, d, box, it["label"], it["body"], font_size,
                       number=i if kind == "process" else None)
        img.save(out_png); return

    # ── content+image: text left, images right ──
    if kind == "content-image":
        text_w = int((SLIDE_W - 2 * _PAD) * 0.55)
        fb = _font(font_size)
        y = top
        for line in u["body"]:
            for wl in _wrap(d, line, fb, text_w):
                if y > SLIDE_H - _PAD - fb.size:
                    break
                d.text((_PAD, y), wl, font=fb, fill=_TEXT); y += fb.size + 8
        for it in u["items"]:                       # any labeled bits become mini-cards inline
            d.text((_PAD, y), f"{it['label']}: {it['body']}"[:70], font=_font(font_size - 3),
                   fill=(90, 90, 90)); y += font_size + 4
        ix = _PAD + text_w + 24
        iw = SLIDE_W - _PAD - ix
        per = (SLIDE_H - top - _PAD) // min(len(u["images"]), 3) - 16
        iy = top
        for alt, path in u["images"][:3]:
            _paste_or_box(img, d, path, alt, [ix, iy, ix + iw, iy + per], font_size)
            iy += per + 16
        img.save(out_png); return

    # ── fallback: title + plain body (NO bullet flattening) + optional side images ──
    fb = _font(font_size)
    text_w = (SLIDE_W - 2 * _PAD) if not u["images"] else int((SLIDE_W - 2 * _PAD) * 0.55)
    y = top
    for line in u["body"]:
        for wl in _wrap(d, line, fb, text_w):
            if y > SLIDE_H - _PAD - fb.size:
                d.text((_PAD, y), "…", font=fb, fill=_MUTED); break
            d.text((_PAD, y), wl, font=fb, fill=_TEXT); y += fb.size + 8
    if u["images"]:
        ix = _PAD + text_w + 24
        iw = SLIDE_W - _PAD - ix
        per = (SLIDE_H - top - _PAD) // min(len(u["images"]), 3) - 16
        iy = top
        for alt, path in u["images"][:3]:
            _paste_or_box(img, d, path, alt, [ix, iy, ix + iw, iy + per], font_size)
            iy += per + 16
    img.save(out_png)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--font-size", type=int, default=22)
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

    # Emit ordered, numbered review images (slide-01.png, slide-02.png, …). The
    # hash-named PNGs under .previews/ stay as the incremental cache; these numbered
    # copies are what the presenter opens to review, in order.
    import shutil
    nwidth = max(2, len(str(len(plan))))
    review: list[Path] = []
    for i, u in enumerate(plan, 1):
        src = Path(u["slide_png"])
        if not src.is_file():
            continue
        dst = pdir / f"slide-{i:0{nwidth}d}.png"
        shutil.copyfile(src, dst)
        review.append(dst)
    # Drop stale numbered images from a previous, longer run.
    for old in pdir.glob("slide-*.png"):
        if old not in review:
            old.unlink()

    manifest_path.write_text(json.dumps(
        {"render_version": _plan.RENDER_VERSION, "units": new_units}, indent=2), encoding="utf-8")
    print(f"[preview 4/4] {len(review)} review images → {pdir}/slide-NN.png", file=sys.stderr)
    print(str(pdir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
