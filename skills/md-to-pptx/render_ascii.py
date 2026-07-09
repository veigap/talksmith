"""Render the ASCII fenced blocks in a Markdown file to PNG images — by code.

Draft-preview only. In the Step-5.5 draft preview the ASCII diagrams are NOT
sent through the Illustrator's ASCII→SVG pipeline (that is Step 6's job for the
final deck). Instead each fenced block is rasterized deterministically here, in
a monospace font, to a PNG the renderer can drop straight onto the slide as an
image. This is fast, requires no model call, parallelizes trivially, and gives
the presenter a diagram-shaped stand-in for the eventual SVG.

What it does:
    - Finds every fenced block (``` … ``` or ~~~ … ~~~) in the input Markdown.
    - Renders each block's text to a PNG in a monospace font (Courier-family),
      near-black text on white, sized to the content.
    - Names each PNG by a content hash (`ascii-<sha1[:12]>.png`) so an unchanged
      diagram maps to the same file — this is what lets the incremental preview
      cache skip re-rendering untouched slides.
    - Rewrites the fence in the Markdown to an image ref `![diagram](<relpath>)`
      (relative to the rewritten file's directory, or --rel-to).

Contract:
    - Preview-only. Never invoked by the strict / free-form render paths.
    - Requires Pillow. If Pillow (or any usable monospace font) is unavailable,
      exits non-zero with a clear message so the caller can fall back to raw
      monospace text boxes rather than failing the whole preview.
    - stdlib + Pillow only.

Usage:
    python3 render_ascii.py <input.md> --img-dir <dir> [-o <out.md>] \
        [--rel-to <dir>] [--font-size 18]
    # -o omitted → rewritten Markdown to stdout. Manifest of PNGs → stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# Fenced block: opening fence (``` or ~~~, optional info string) to the next
# line that is the same fence marker. DOTALL so the body spans lines.
_FENCE_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>```|~~~)[^\n]*\n"
    r"(?P<body>.*?)"
    r"^(?P=indent)(?P=fence)[ \t]*$\n?",
    re.DOTALL | re.MULTILINE,
)

# Monospace TTF/TTC candidates, tried in order. Menlo/SFMono cover macOS;
# DejaVu/Liberation cover Linux (Cowork); Courier New is the shared fallback and
# the font the preview slides label the box with.
_FONT_CANDIDATES = (
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/Library/Fonts/Courier New.ttf",
)

_TEXT_COLOR = (31, 30, 30)       # #1F1E1E — matches the deck's near-black
_BG_COLOR = (255, 255, 255)      # white
_PAD = 20                        # px padding around the diagram


def _load_font(font_size: int):
    """Return a Pillow monospace ImageFont, or raise RuntimeError if none work.

    A TrueType monospace font is required — the default bitmap font does not
    carry the box-drawing glyphs (│ ─ ┌ ┐ └ ┘ ▶ …) ASCII diagrams rely on.
    """
    from PIL import ImageFont  # local import so a missing Pillow is caught by caller

    for path in _FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, font_size)
            except OSError:
                continue
    raise RuntimeError(
        "no usable monospace TrueType font found (looked for Menlo / SF Mono / "
        "Courier New / DejaVu Sans Mono / Liberation Mono)"
    )


def render_block_to_png(text: str, out_path: Path, font_size: int = 18) -> None:
    """Rasterize one ASCII block to `out_path` as a monospace PNG."""
    from PIL import Image, ImageDraw

    font = _load_font(font_size)
    # Normalize away trailing whitespace/newlines; keep interior lines verbatim.
    lines = text.rstrip("\n").split("\n")
    if not lines:
        lines = [""]

    ascent, descent = font.getmetrics()
    line_h = ascent + descent  # tight so box-drawing verticals connect
    # Monospace: every glyph shares the advance width of a reference char.
    char_w = font.getlength("M") or (font_size * 0.6)
    max_len = max((len(line) for line in lines), default=1)

    width = int(round(char_w * max_len)) + 2 * _PAD
    height = line_h * len(lines) + 2 * _PAD

    img = Image.new("RGB", (max(width, 1), max(height, 1)), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((_PAD, _PAD + i * line_h), line, font=font, fill=_TEXT_COLOR)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")


def _content_name(text: str) -> str:
    """Content-addressed PNG basename for a block (stable across runs)."""
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"ascii-{digest}.png"


def rewrite(markdown: str, img_dir: Path, rel_to: Path, font_size: int) -> tuple[str, list[Path]]:
    """Render every fenced block to a PNG and replace it with an image ref.

    Returns the rewritten Markdown and the list of PNG paths (in document order,
    with duplicates for repeated identical diagrams collapsed to one file).
    """
    made: list[Path] = []
    seen: set[Path] = set()

    def _replace(m: "re.Match[str]") -> str:
        body = m.group("body")
        if not body.strip():
            return m.group(0)  # empty fence — leave as-is
        png_path = img_dir / _content_name(body)
        if png_path not in seen:
            render_block_to_png(body, png_path, font_size)
            seen.add(png_path)
            made.append(png_path)
        try:
            ref = png_path.relative_to(rel_to)
        except ValueError:
            ref = png_path
        indent = m.group("indent")
        return f"{indent}![diagram]({ref})\n"

    return _FENCE_RE.sub(_replace, markdown), made


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render ASCII fenced blocks in a Markdown file to monospace "
                    "PNGs and rewrite the fences to image refs (draft-preview only)."
    )
    parser.add_argument("input_md", type=Path, help="Markdown file (a slide unit).")
    parser.add_argument("--img-dir", type=Path, required=True,
                        help="Directory to write the rendered PNGs into.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Rewritten Markdown (default: stdout).")
    parser.add_argument("--rel-to", type=Path, default=None,
                        help="Base dir for the image refs (default: output's dir).")
    parser.add_argument("--font-size", type=int, default=18,
                        help="Monospace font size in px (default: 18).")
    args = parser.parse_args()

    if not args.input_md.is_file():
        print(f"error: {args.input_md} not found", file=sys.stderr)
        return 2

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("error: Pillow is required for ASCII→PNG rendering "
              "(`pip install Pillow`); fall back to monospace text boxes",
              file=sys.stderr)
        return 3

    rel_to = args.rel_to or (args.output.parent if args.output else Path.cwd())
    markdown = args.input_md.read_text(encoding="utf-8")
    try:
        rewritten, made = rewrite(markdown, args.img_dir, rel_to, args.font_size)
    except RuntimeError as exc:
        print(f"error: {exc}; fall back to monospace text boxes", file=sys.stderr)
        return 3

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rewritten, encoding="utf-8")
    else:
        sys.stdout.write(rewritten)

    for p in made:
        print(p, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
