"""Incremental render plan for the draft preview — content-addressed cache.

Draft-preview only. The Step-5.5 preview re-renders on every `draft.md` change,
but most slides don't change between rounds. This script diffs the current
per-slide units (from `convert.py --split-dir`) against a manifest of what was
rendered last time and decides, per slide, whether to **reuse** the already-
rendered PNG (and its cached critique verdict) or **render** it fresh.

Cache key = a content hash of the slide unit's markdown, salted with
`RENDER_VERSION` (bump the constant when the render recipe changes, so every
cached slide invalidates at once). The rendered PNG is named by that hash
(`slide-<hash>.png`), so an unchanged slide maps to the same file and a reordered
slide reuses its PNG for free. A changed slide gets a new hash → a `render`
action → the skill re-authors + re-critiques only that slide.

Emits a plan (JSON) listing, in slide order, each unit's hash, title, target PNG,
action (`reuse`|`render`), and — for reused slides — the carried-forward critique
verdict. The skill renders the `render` slides, critiques them, and writes the
updated manifest back.

stdlib-only; no Cowork, no python-pptx.

Usage:
    python3 preview_plan.py --units-dir <dir> --slides-dir <dir> \
        [--manifest <prior.json>] [--render-version <str>] [--gc] [-o <plan.json>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Bump when the preview render recipe changes (spec, base-template, ASCII font,
# layout dispatch) so every cached slide is treated as changed on the next run.
RENDER_VERSION = "1"

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")


def _unit_title(text: str) -> str:
    """First heading text, else first non-empty line (truncated)."""
    for line in text.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:60]
    return "(empty)"


def _unit_hash(text: str, render_version: str) -> str:
    payload = f"{render_version}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def compute_plan(
    unit_files: list[Path],
    prior: dict[str, dict],
    slides_dir: Path,
    render_version: str,
) -> list[dict]:
    """Pure planner: classify each unit as reuse|render. `prior` maps hash → entry."""
    plan: list[dict] = []
    for idx, unit_path in enumerate(unit_files, 1):
        text = unit_path.read_text(encoding="utf-8")
        h = _unit_hash(text, render_version)
        png_name = f"slide-{h}.png"
        png_path = slides_dir / png_name
        cached = prior.get(h)
        # Reuse only when both the PNG is on disk AND we have a prior record
        # (so we can carry the critique verdict forward without re-walking it).
        reuse = png_path.is_file() and cached is not None
        plan.append({
            "index": idx,
            "title": _unit_title(text),
            "hash": h,
            "unit_md": str(unit_path),
            "slide_png": str(png_path),
            "action": "reuse" if reuse else "render",
            "verdict": cached.get("verdict") if (reuse and cached) else None,
        })
    return plan


def _load_manifest(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    # Manifest shape: {"render_version": "...", "units": {hash: {...}}}
    units = data.get("units", {})
    return units if isinstance(units, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Incremental render plan for the draft preview (content-addressed)."
    )
    parser.add_argument("--units-dir", type=Path, required=True,
                        help="Directory of slide-NN.md units (from convert.py --split-dir).")
    parser.add_argument("--slides-dir", type=Path, required=True,
                        help="Directory where per-slide PNGs live (named slide-<hash>.png).")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="Prior manifest JSON (default: <slides-dir>/../.preview-cache.json).")
    parser.add_argument("--render-version", default=RENDER_VERSION,
                        help=f"Cache salt (default: {RENDER_VERSION}).")
    parser.add_argument("--gc", action="store_true",
                        help="Delete slide-*.png in --slides-dir not referenced by the new plan.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Plan JSON output (default: stdout).")
    args = parser.parse_args()

    if not args.units_dir.is_dir():
        print(f"error: {args.units_dir} not found", file=sys.stderr)
        return 2

    # Only the numbered unit files — never derived siblings like
    # slide-01.rendered.md that a rewrite step may drop in the same dir.
    unit_re = re.compile(r"^slide-\d+\.md$")
    unit_files = sorted(p for p in args.units_dir.glob("slide-*.md")
                        if unit_re.match(p.name))
    if not unit_files:
        print(f"error: no slide-*.md units in {args.units_dir}", file=sys.stderr)
        return 2

    manifest_path = args.manifest or (args.slides_dir.parent / ".preview-cache.json")
    prior = _load_manifest(manifest_path)

    plan = compute_plan(unit_files, prior, args.slides_dir, args.render_version)

    if args.gc and args.slides_dir.is_dir():
        keep = {Path(u["slide_png"]).name for u in plan}
        for png in args.slides_dir.glob("slide-*.png"):
            if png.name not in keep:
                png.unlink()

    n_render = sum(1 for u in plan if u["action"] == "render")
    doc = {
        "render_version": args.render_version,
        "manifest": str(manifest_path),
        "total": len(plan),
        "render": n_render,
        "reuse": len(plan) - n_render,
        "units": plan,
    }
    out = json.dumps(doc, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        sys.stdout.write(out + "\n")
    # One-line summary to stderr for the skill's progress log.
    print(f"[preview] plan: {len(plan)} slides — {n_render} to render, "
          f"{len(plan) - n_render} reused", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
