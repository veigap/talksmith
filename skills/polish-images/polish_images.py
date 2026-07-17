#!/usr/bin/env python3
"""talksmith:polish-images — Step 6 helper (generated-aside pass).

Sibling of polish_ascii.py. Where that skill extracts ` ```ascii ` fences for the
diagram-illustrator, this one extracts `<!-- generate-image: <side> | <desc> -->`
directives for the image-illustrator, and rewrites each into an `aside` image ref.

Subcommands:
  scan                <final.md> [--format json|human] [--language <lang>]
  annotate            --plan <plan.json|-> --gen <gen.json|-> [-o <out.json|->]
  extract             --final <final.md> --plan <plan.json|->
  prepare-render-args --plan <plan.json|-> --out-dir <dir> [--repo-root <path>]
  stamp-renders       --final <final.md> --plan <plan.json|-> [--dry-run]
  cleanup             --final <final.md> --plan <plan.json|-> [--dry-run]

Like polish_ascii, every subcommand operates on `talks/<Talk>/final.md`; `draft.md`
is never read or written. The per-block slide-context scanner is shared: see
`skills/_shared/_context.py`.

See SKILL.md for the full contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
from _context import (  # noqa: E402  (shared slide-context scanner)
    FENCE_OPEN,
    FENCE_CLOSE,
    COMMENT_CLOSE,
    H2_SLIDE,
    IMAGE_REF,
    fence_line_mask,
    is_section_heading,
    section_of_h1,
    extract_thesis,
    extract_block_context,
)

DIRECTIVE_OPEN = "<!-- generate-image:"
_DIRECTIVE_PREFIX = re.compile(r"^\s*<!--\s*generate-image:\s*", re.IGNORECASE)
_GEN_SOURCE_OPEN = "<!-- generate-source:"
VALID_SIDES = ("left", "right")
DEFAULT_SIDE = "right"


# ── directive parsing ────────────────────────────────────────────────────────

def parse_directive(inner: str) -> tuple[str, str]:
    """Split a directive's inner text into (side, description).

    Inner text is everything between `generate-image:` and the closing `-->`.
    Form: `<side> | <description>`. If the part before the first `|` is not a valid
    side, the whole inner is the description and side defaults to `right`.
    """
    if "|" in inner:
        head, _, rest = inner.partition("|")
        side = head.strip().lower()
        if side in VALID_SIDES:
            return side, rest.strip()
    return DEFAULT_SIDE, inner.strip()


def _directive_inner(lines: list[str], start: int, end: int) -> str:
    """Raw inner text of a directive spanning 0-based lines [start, end] inclusive.

    Strips the `<!-- generate-image:` opener and the trailing `-->`.
    """
    block = "\n".join(lines[start:end + 1])
    block = _DIRECTIVE_PREFIX.sub("", block, count=1)
    # Drop the trailing --> (and anything after it on that line).
    idx = block.rfind("-->")
    if idx != -1:
        block = block[:idx]
    return " ".join(block.split())


# ── scan ─────────────────────────────────────────────────────────────────────

def scan(final_path: Path, presentation_language: str | None = None) -> dict[str, Any]:
    text = final_path.read_text()
    lines = text.splitlines()
    fmask = fence_line_mask(lines)

    section: str | int | None = 0
    slide = 0
    gen_n = 0
    skipped_non_slide = 0

    directives: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        ln = lines[i]
        # Structural tracking (only outside fenced code blocks).
        if not fmask[i]:
            if is_section_heading(ln):
                section, slide, gen_n = section_of_h1(ln), 0, 0
                i += 1
                continue
            m_sld = H2_SLIDE.match(ln)
            if m_sld:
                slide = int(m_sld.group(1))
                gen_n = 0
                i += 1
                continue

        # Directive detection: a `<!-- generate-image:` comment, outside fences.
        if not fmask[i] and _DIRECTIVE_PREFIX.match(ln):
            start = i
            k = i
            while k < len(lines) and not COMMENT_CLOSE.search(lines[k]):
                k += 1
            end = k if k < len(lines) else len(lines) - 1
            inner = _directive_inner(lines, start, end)
            side, description = parse_directive(inner)
            if section is None:
                # Under Thesis / Open questions / Cut material — no slide to attach to.
                skipped_non_slide += 1
                i = end + 1
                continue
            gen_n += 1
            slide_id = f"s{section}-{slide}-{gen_n}"
            directives.append({
                "slide_id": slide_id,
                "directive": {
                    "start_line": start + 1,
                    "end_line": end + 1,
                    "side": side,
                    "description": description,
                },
                "render": None,
            })
            i = end + 1
            continue
        i += 1

    _annotate_conflicts(lines, directives, fmask)

    thesis = extract_thesis(lines)
    for d in directives:
        ctx = extract_block_context(lines, d["directive"]["start_line"], fmask)
        ctx["talk_thesis"] = thesis
        if presentation_language:
            ctx["presentation_language"] = presentation_language
        d["context"] = ctx

    return {"final_path": str(final_path), "directives": directives,
            "skipped_non_slide": skipped_non_slide}


def _slide_boundaries(lines: list[str], fmask: list[bool]) -> list[int]:
    bounds = [i + 1 for i, ln in enumerate(lines)
              if not fmask[i] and (H2_SLIDE.match(ln) or is_section_heading(ln))]
    bounds.append(len(lines) + 1)
    return bounds


def _annotate_conflicts(lines: list[str], directives: list[dict[str, Any]],
                        fmask: list[bool]) -> None:
    """Flag a directive `conflicting_image: true` when its slide already carries a
    real body image ref — an aside on such a slide is mis-authored (the existing
    `aside` rule forbids it). The directive's own lines and any prior
    `<!-- generate-source: … -->` echo are excluded from the check.
    """
    bounds = _slide_boundaries(lines, fmask)

    def slide_range(line_no: int) -> tuple[int, int]:
        start, end = 1, len(lines)
        for b in bounds:
            if b <= line_no:
                start = b
            else:
                end = b - 1
                break
        return start, end

    # Ranges inside <!-- generate-source: … --> echoes (provenance from prior passes).
    ignored: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if _GEN_SOURCE_OPEN in lines[i]:
            j = i
            while j < len(lines) and not COMMENT_CLOSE.search(lines[j]):
                j += 1
            ignored.append((i + 1, min(j + 1, len(lines))))
            i = j + 1
        else:
            i += 1

    def in_ignored(n: int) -> bool:
        return any(lo <= n <= hi for lo, hi in ignored)

    for d in directives:
        d_start = d["directive"]["start_line"]
        d_end = d["directive"]["end_line"]
        s_start, s_end = slide_range(d_start)
        conflict = False
        for n in range(s_start, s_end + 1):
            if d_start <= n <= d_end or in_ignored(n):
                continue
            if IMAGE_REF.search(lines[n - 1]):
                conflict = True
                break
        d["conflicting_image"] = conflict


# ── idempotency: digest of the *original* description + side ──────────────────
# PNGs can't carry an inline comment the way SVGs can, so the stamp lives in a
# companion `<basename>.imgstamp` file (independent of the `.imgprompt` sidecar,
# which `extract` overwrites every pass). The key is the presenter-owned authored
# input — description + side — never the LLM-enriched prompt (which varies per run).

STAMP_SUFFIX = ".imgstamp"


def imgprompt_digest(description: str, side: str) -> str:
    return hashlib.sha256(f"{side}\n{description}\n".encode()).hexdigest()


def _stamp_path(images_dir: Path, png_basename: str) -> Path:
    stem = png_basename[:-4] if png_basename.lower().endswith(".png") else png_basename
    return images_dir / f"{stem}{STAMP_SUFFIX}"


def read_stamp(stamp_path: Path) -> str | None:
    try:
        return stamp_path.read_text().strip() or None
    except OSError:
        return None


# ── sidecar (.imgprompt) ──────────────────────────────────────────────────────

def build_sidecar_content(description: str, prompt: str, side: str) -> str:
    return (
        f"side: {side}\n\n"
        f"# Original description (presenter-editable, idempotency anchor)\n{description}\n\n"
        f"# Enriched generation prompt (what image generation consumes)\n{prompt}\n"
    )


# ── plan I/O helpers (mirror polish_ascii) ────────────────────────────────────

def _read_json_arg(value: str) -> Any:
    text = sys.stdin.read() if value == "-" else Path(value).read_text()
    return json.loads(text)


def _load_plan(args: argparse.Namespace) -> "tuple[Path, dict[str, Any]] | int":
    final_path = Path(args.final).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    if args.plan == "-":
        plan_text = sys.stdin.read()
    else:
        plan_path = Path(args.plan)
        if not plan_path.exists():
            print(f"error: plan not found: {plan_path}", file=sys.stderr)
            return 2
        plan_text = plan_path.read_text()
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError as e:
        print(f"error: plan JSON invalid: {e}", file=sys.stderr)
        return 2
    return final_path, plan


def _renderable(d: dict[str, Any]) -> bool:
    return bool(d.get("render"))


def _stale_error(lines: list[str], d: dict[str, Any]) -> "tuple[int, str] | None":
    """Return (exit_code, message) when directive `d`'s recorded lines no longer match.

    Bounds (2), opener still a generate-image comment (3), and the parsed
    (side, description) still match the plan (3) — an in-place edit preserves line
    count, so without the content check the guard would silently revert the edit.
    """
    start_idx = d["directive"]["start_line"] - 1
    end_idx = d["directive"]["end_line"] - 1
    if start_idx < 0 or end_idx >= len(lines):
        return 2, (f"line range out of bounds for {d['slide_id']}: "
                   f"{start_idx + 1}-{end_idx + 1} (file has {len(lines)} lines)")
    if not _DIRECTIVE_PREFIX.match(lines[start_idx]) or not COMMENT_CLOSE.search(lines[end_idx]):
        return 3, (f"stale plan — {d['slide_id']} line {start_idx + 1} no longer opens a "
                   f"generate-image directive; re-run `scan`")
    side, description = parse_directive(_directive_inner(lines, start_idx, end_idx))
    if side != d["directive"]["side"] or description != d["directive"]["description"]:
        return 3, (f"stale plan — {d['slide_id']} directive text at line {start_idx + 1} "
                   f"differs from the plan; re-run `scan`")
    return None


# ── scan command ──────────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> int:
    final_path = Path(args.final_path).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    result = scan(final_path, presentation_language=args.language)
    if args.format == "human":
        conflicts = sum(1 for d in result["directives"] if d.get("conflicting_image"))
        print(f"found {len(result['directives'])} generate-image directive(s) in {result['final_path']}:")
        if conflicts:
            print(f"  ⚠  {conflicts} directive(s) on a slide that already has an image ref — mis-authored aside")
        if result.get("skipped_non_slide"):
            print(f"  ℹ  {result['skipped_non_slide']} directive(s) skipped — under a heading with no slides")
        if result["directives"]:
            print()
        for d in result["directives"]:
            dd = d["directive"]
            desc = (dd["description"][:54] + "…") if len(dd["description"]) > 55 else dd["description"]
            flag = "  [conflict]" if d.get("conflicting_image") else ""
            print(f"  {d['slide_id']:<10} lines {dd['start_line']}–{dd['end_line']}  side={dd['side']:<5}  {desc}{flag}")
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


# ── annotate ──────────────────────────────────────────────────────────────────

def cmd_annotate(args: argparse.Namespace) -> int:
    plan = _read_json_arg(args.plan)
    gen = _read_json_arg(args.gen)
    if not isinstance(gen, dict):
        print("error: --gen JSON must map slide_id → {png_basename, alt, description, prompt}", file=sys.stderr)
        return 2

    missing: list[str] = []
    annotated = 0
    for d in plan.get("directives", []):
        sid = d.get("slide_id", "")
        entry = gen.get(sid)
        if not entry or not entry.get("prompt"):
            d["render"] = None
            missing.append(sid)
            continue
        basename = entry.get("png_basename") or entry.get("basename") or f"{sid}-aside.png"
        if not basename.lower().endswith(".png"):
            basename = f"{basename}.png"
        d["render"] = {
            "png_basename": basename,
            "alt": entry.get("alt") or "",
            "description": entry.get("description") or d["directive"]["description"],
            "prompt": entry["prompt"],
        }
        annotated += 1

    out_text = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    if args.output and args.output != "-":
        Path(args.output).write_text(out_text)
    else:
        sys.stdout.write(out_text)
    print(f"annotated {annotated} directive(s)", file=sys.stderr)
    if missing:
        print(f"  ⚠  {len(missing)} directive(s) had no gen entry (render: null): {', '.join(missing)}", file=sys.stderr)
    return 0


# ── extract ───────────────────────────────────────────────────────────────────

def cmd_extract(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    images_dir = final_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    written = unchanged = skipped = 0
    for d in plan.get("directives", []):
        render = d.get("render")
        if not render:
            skipped += 1
            continue
        basename = render["png_basename"]
        stem = basename[:-4] if basename.lower().endswith(".png") else basename
        sidecar = images_dir / f"{stem}.imgprompt"
        content = build_sidecar_content(
            render.get("description") or d["directive"]["description"],
            render["prompt"],
            d["directive"]["side"],
        )
        if sidecar.exists() and sidecar.read_text() == content:
            unchanged += 1
        else:
            if not args.dry_run:
                sidecar.write_text(content)
            written += 1
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"extracted image sidecars from {final_path}:{tag}")
    print(f"  written:   {written}")
    print(f"  unchanged: {unchanged}")
    print(f"  skipped:   {skipped} (no render mapping)")
    return 0


# ── prepare-render-args ───────────────────────────────────────────────────────

def cmd_prepare_render_args(args: argparse.Namespace) -> int:
    plan = _read_json_arg(args.plan)
    final_path_str = plan.get("final_path")
    if not final_path_str:
        print("error: plan missing 'final_path' — re-run `scan`", file=sys.stderr)
        return 2
    final_path = Path(final_path_str).resolve()
    if not final_path.exists():
        print(f"error: plan's final.md not found: {final_path} — stale plan; re-run `scan`", file=sys.stderr)
        return 2
    images_dir = (final_path.parent / "images").resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None

    renderables = [d for d in plan.get("directives", []) if d.get("render")]
    skipped = len(plan.get("directives", [])) - len(renderables)

    # Pre-flight: every renderable directive needs its `.imgprompt` sidecar (from `extract`).
    def _stem(d: dict) -> str:
        bn = d["render"]["png_basename"]
        return bn[:-4] if bn.lower().endswith(".png") else bn

    miss = [(d.get("slide_id", ""), images_dir / f"{_stem(d)}.imgprompt")
            for d in renderables if not (images_dir / f"{_stem(d)}.imgprompt").exists()]
    if miss:
        print("error: missing .imgprompt sidecar(s) — run `extract` first:", file=sys.stderr)
        for sid, p in miss:
            print(f"  {sid} → {p}", file=sys.stderr)
        return 2

    written = reused = 0
    for d in renderables:
        sid = d.get("slide_id", "")
        basename = d["render"]["png_basename"]
        stem = _stem(d)
        png_path = images_dir / basename
        digest = imgprompt_digest(d["directive"]["description"], d["directive"]["side"])
        stamp = _stamp_path(images_dir, basename)
        if png_path.exists() and read_stamp(stamp) == digest:
            reused += 1
            continue
        ctx = d.get("context") or {}
        payload: dict[str, Any] = {
            "prompt_file": str(images_dir / f"{stem}.imgprompt"),
            "prompt": d["render"]["prompt"],
            "output_path": str(png_path),
            "aspect": "portrait",
            "side": d["directive"]["side"],
            "slide_title": ctx.get("slide_title", ""),
            "slide_content_prose": ctx.get("slide_content_prose", ""),
            "speaker_notes": ctx.get("speaker_notes", ""),
            "section_title": ctx.get("section_title", ""),
            "section_goal": ctx.get("section_goal", ""),
            "talk_thesis": ctx.get("talk_thesis", ""),
            "presentation_language": ctx.get("presentation_language", ""),
        }
        if repo_root:
            payload["repo_root"] = str(repo_root)
        (out_dir / f"{sid}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        written += 1

    print(f"wrote args for {written} directive(s) to {out_dir}", file=sys.stderr)
    if reused:
        print(f"  reused {reused} (PNG stamped with the same description digest — no regenerate)", file=sys.stderr)
    if skipped:
        print(f"  skipped {skipped} (no render mapping)", file=sys.stderr)
    return 0


# ── stamp-renders ─────────────────────────────────────────────────────────────

def cmd_stamp_renders(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    images_dir = final_path.parent / "images"

    stamped = 0
    missing: list[tuple[str, Path]] = []
    for d in plan.get("directives", []):
        render = d.get("render")
        if not render:
            continue
        basename = render["png_basename"]
        png_path = images_dir / basename
        if not png_path.exists():
            missing.append((d.get("slide_id", ""), png_path))
            continue
        if not args.dry_run:
            digest = imgprompt_digest(d["directive"]["description"], d["directive"]["side"])
            _stamp_path(images_dir, basename).write_text(digest + "\n")
        stamped += 1

    tag = "  [dry-run]" if args.dry_run else ""
    print(f"stamped {stamped} image(s) with their description digest{tag}")
    if missing:
        print(f"  ⚠  {len(missing)} image(s) not on disk — they regenerate next pass:", file=sys.stderr)
        for sid, p in missing:
            print(f"     {sid} → {p}", file=sys.stderr)
    return 0


# ── cleanup ───────────────────────────────────────────────────────────────────

def cmd_cleanup(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    lines = final_path.read_text().splitlines(keepends=False)

    rewritten = skipped = 0
    directives = plan.get("directives", [])
    # Bottom-up so line numbers stay valid.
    for d in sorted(directives, key=lambda x: x["directive"]["start_line"], reverse=True):
        render = d.get("render")
        if not render:
            skipped += 1
            continue
        err = _stale_error(lines, d)
        if err:
            code, msg = err
            print(f"error: {msg}", file=sys.stderr)
            raise SystemExit(code)
        basename = render["png_basename"]
        alt = render.get("alt") or d["slide_id"]
        side = d["directive"]["side"]
        desc = (render.get("description") or d["directive"]["description"]).replace("-->", "--&gt;")
        start_idx = d["directive"]["start_line"] - 1
        end_idx = d["directive"]["end_line"] - 1
        rewrite = [
            f"<!-- aside: {side} ![{alt}](images/{basename}) -->",
            f"<!-- generate-source: {desc} -->",
        ]
        lines[start_idx:end_idx + 1] = rewrite
        rewritten += 1

    if not args.dry_run and rewritten:
        new_text = "\n".join(lines)
        if not new_text.endswith("\n"):
            new_text += "\n"
        tmp = final_path.with_suffix(final_path.suffix + ".tmp")
        tmp.write_text(new_text)
        os.replace(tmp, final_path)

    tag = "  [dry-run]" if args.dry_run else ""
    print(f"cleaned up {final_path}:{tag}")
    print(f"  directives rewritten to aside refs: {rewritten}")
    print(f"  skipped: {skipped} (no render mapping)")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="polish_images",
                                     description="Step 6 generate-image extractor / final.md rewriter for Talksmith.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="emit JSON describing every generate-image directive + per-block context in a Talk's final.md")
    p_scan.add_argument("final_path", help="path to the Talk's final.md")
    p_scan.add_argument("--format", choices=["json", "human"], default="json")
    p_scan.add_argument("--language", help="presentation language; stamped into each directive's context.presentation_language")
    p_scan.set_defaults(func=cmd_scan)

    p_annot = sub.add_parser("annotate", help="merge a slide_id→{png_basename,alt,description,prompt} map into a scan plan")
    p_annot.add_argument("--plan", required=True, help="scan JSON (or '-' for stdin)")
    p_annot.add_argument("--gen", required=True, help="JSON mapping slide_id → {png_basename, alt, description, prompt} (or '-')")
    p_annot.add_argument("-o", "--output", help="write annotated plan here (default: stdout)")
    p_annot.set_defaults(func=cmd_annotate)

    def _add_plan_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--final", required=True, help="path to the Talk's final.md")
        p.add_argument("--plan", required=True)
        p.add_argument("--dry-run", action="store_true")

    p_extract = sub.add_parser("extract", help="write .imgprompt sidecars from an annotated scan plan (no final.md mutation)")
    _add_plan_args(p_extract)
    p_extract.set_defaults(func=cmd_extract)

    p_prep = sub.add_parser("prepare-render-args", help="fan an annotated plan out to one <slide_id>.json args file per renderable directive")
    p_prep.add_argument("--plan", required=True, help="annotated plan JSON (or '-')")
    p_prep.add_argument("--out-dir", required=True, help="directory to write per-directive args files into")
    p_prep.add_argument("--repo-root", help="presenter working directory, stamped into each args file")
    p_prep.set_defaults(func=cmd_prepare_render_args)

    p_stamp = sub.add_parser("stamp-renders", help="stamp each generated image with the digest of its description+side — the sole re-generate signal")
    _add_plan_args(p_stamp)
    p_stamp.set_defaults(func=cmd_stamp_renders)

    p_cleanup = sub.add_parser("cleanup", help="rewrite generate-image directives in final.md to aside image refs")
    _add_plan_args(p_cleanup)
    p_cleanup.set_defaults(func=cmd_cleanup)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
