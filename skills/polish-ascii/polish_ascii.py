#!/usr/bin/env python3
"""talksmith:polish-ascii — Step 6 helper.

Subcommands:
  scan              <final.md> [--format json|human]
  inspect-intents   --plan <plan.json|->
  annotate-renders  --plan <plan.json|-> --renders <renders.json|-> [-o <out.json|->]
  prepare-render-args --plan <plan.json|-> --out-dir <dir> [--repo-root <path>]
  extract           --final <final.md> --plan <plan.json|-> [--dry-run]
  cleanup           --final <final.md> --plan <plan.json|-> [--dry-run]
  apply             --final <final.md> --plan <plan.json|-> [--dry-run]   # extract + cleanup in one pass (compat)

All subcommands operate on `talks/<Talk>/final.md` — the Step-6 derived file
produced from `draft.md` by the editor's Polish copy step. `draft.md` itself
is never read or written by this skill.

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
    FENCE_OPEN, FENCE_CLOSE, COMMENT_CLOSE,
    H1_ANY, H1_SECTION, H1_AGENDA, H1_CONCL, H2_SLIDE, H1_OR_H2, IMAGE_REF,
    strip_prose as _strip_prose,
    skip_frontmatter as _skip_frontmatter,
    extract_thesis as _extract_thesis,
    strip_h1 as _strip_h1,
    strip_h2 as _strip_h2,
    is_section_heading as _is_section_heading,
    section_of_h1 as _section_of_h1,
    fence_line_mask as _fence_line_mask,
    extract_block_context as _extract_block_context,
)

CANONICAL_ASCII_TAG = "ascii"
LEGACY_ASCII_LANG_TAGS = {"", "text", "diagram"}
BOX_OR_ARROW = re.compile(r"[─│┌┐└┘├┤┬┴┼+|→←↑↓⇒⇐⇑⇓]|->|==>|<-|=>")
NOTE_OPEN = "<!-- ascii-note:"
# Per-block render override: `<!-- ascii-render: force -->` makes a block render-driving even on a
# slide that also carries an image ref (the default would mark it documentation-only); `<!-- ascii-
# render: documentation-only -->` suppresses a block that would otherwise render. Binds to the fence
# it sits immediately above.
_RENDER_HINT = re.compile(r"<!--\s*ascii-render:\s*(force|documentation-only|doc-only)\s*-->", re.IGNORECASE)


def is_ascii_payload(payload: str) -> bool:
    if BOX_OR_ARROW.search(payload):
        return True
    return payload.count("\n") >= 2


def scan(final_path: Path, presentation_language: str | None = None) -> dict[str, Any]:
    text = final_path.read_text()
    lines = text.splitlines()

    section: str | int | None = 0  # 0 = pre-Agenda / Agenda; "c" = Conclusions; None = no slides here
    slide = 0
    ascii_n = 0
    skipped_non_slide = 0

    in_fence = False
    fence_lang: str | None = None
    fence_open_line = 0  # 1-based
    buf: list[str] = []

    blocks: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        ln = lines[i]
        line_no = i + 1
        if not in_fence:
            if _is_section_heading(ln):
                # Any H1 ends the current section, whether or not we can name it.
                section, slide, ascii_n = _section_of_h1(ln), 0, 0
            else:
                m_sld = H2_SLIDE.match(ln)
                if m_sld:
                    slide = int(m_sld.group(1))
                    ascii_n = 0
            m_f = FENCE_OPEN.match(ln)
            if m_f:
                in_fence = True
                # First token of the info string is the language tag (```python title=x → "python").
                info = m_f.group(1).strip().lower()
                fence_lang = info.split()[0] if info else ""
                fence_open_line = line_no
                buf = []
        else:
            if FENCE_CLOSE.match(ln):
                close_line = line_no
                is_canonical = (fence_lang == CANONICAL_ASCII_TAG)
                is_legacy_candidate = (fence_lang in LEGACY_ASCII_LANG_TAGS)
                if is_canonical or is_legacy_candidate:
                    payload = "\n".join(buf)
                    # Canonical `ascii` tag: trust unconditionally (deterministic block).
                    # Legacy (empty/text/diagram): keep the glyph heuristic + flag detection_mode.
                    accept = False
                    detection_mode = "canonical"
                    if is_canonical and payload.strip():
                        accept = True
                    elif is_legacy_candidate and payload.strip() and is_ascii_payload(payload):
                        accept = True
                        detection_mode = "legacy-heuristic"
                    if accept and section is None:
                        # Under Thesis / Open questions / Cut material — no slide to attach to.
                        accept = False
                        skipped_non_slide += 1
                    if accept:
                        ascii_n += 1
                        slide_id = f"s{section}-{slide}-{ascii_n}"
                        # Render-override hint on the line(s) immediately above the fence (1 blank
                        # line of tolerance) binds to THIS block — same proximity idea as ascii-note.
                        render_hint = None
                        p = fence_open_line - 2  # 0-based index of the line just above the fence
                        blanks_before = 0
                        while p >= 0:
                            if lines[p].strip() == "":
                                blanks_before += 1
                                if blanks_before > 1:
                                    break
                                p -= 1
                                continue
                            hm = _RENDER_HINT.search(lines[p])
                            if hm:
                                render_hint = hm.group(1).lower().replace("doc-only", "documentation-only")
                            break
                        # Look for ascii-note right after, with up to 1 blank line tolerance
                        note = None
                        j = i + 1
                        blanks = 0
                        while j < len(lines) and lines[j].strip() == "" and blanks < 1:
                            blanks += 1
                            j += 1
                        if j < len(lines) and lines[j].lstrip().startswith(NOTE_OPEN):
                            note_start = j + 1
                            k = j
                            while k < len(lines) and not COMMENT_CLOSE.search(lines[k]):
                                k += 1
                            if k < len(lines):
                                note_end = k + 1
                                note_payload = "\n".join(lines[j:k + 1])
                                note = {
                                    "start_line": note_start,
                                    "end_line": note_end,
                                    "payload": note_payload,
                                }
                        blocks.append({
                            "slide_id": slide_id,
                            "ascii": {
                                "start_line": fence_open_line,
                                "end_line": close_line,
                                "payload": payload,
                            },
                            "note": note,
                            "render": None,
                            "detection_mode": detection_mode,
                            "render_hint": render_hint,   # force | documentation-only | None
                            "documentation_only": False,  # filled by _annotate_documentation_only below
                        })
                in_fence = False
                fence_lang = None
                buf = []
            else:
                buf.append(ln)
        i += 1

    fence_mask = _fence_line_mask(lines)
    _annotate_documentation_only(lines, blocks, fence_mask)

    # Per-block context (mechanical extraction so callers don't re-parse final.md per render).
    thesis = _extract_thesis(lines)
    for b in blocks:
        ctx = _extract_block_context(lines, b["ascii"]["start_line"], fence_mask)
        ctx["talk_thesis"] = thesis
        if presentation_language:
            ctx["presentation_language"] = presentation_language
        b["context"] = ctx

    return {"final_path": str(final_path), "blocks": blocks, "skipped_non_slide": skipped_non_slide}


def _annotate_documentation_only(lines: list[str], blocks: list[dict[str, Any]], fence_mask: list[bool] | None = None) -> None:
    """Flag each ASCII block as documentation_only when its containing slide has a Markdown image ref.

    Slide scope = lines between the most recent H1/H2 boundary at-or-before the block and the next
    H1/H2 boundary after it. An image ref anywhere in that scope (outside the ASCII block lines
    themselves and outside `<!-- ascii-source: ... -->` HTML comments left by prior Polish passes)
    means the block is documentation-only — the pipeline must skip it. Boundary detection skips
    lines inside fences (a `# ...` payload line is not a heading).
    """
    if fence_mask is None:
        fence_mask = _fence_line_mask(lines)
    boundaries = [i + 1 for i, ln in enumerate(lines) if H1_OR_H2.match(ln) and not fence_mask[i]]
    boundaries.append(len(lines) + 1)

    def slide_range(line_no: int) -> tuple[int, int]:
        start = 1
        end = len(lines)
        for b in boundaries:
            if b <= line_no:
                start = b
            else:
                end = b - 1
                break
        return start, end

    # Pre-compute ranges that are inside <!-- ascii-source: ... --> comments (legacy artifacts of
    # earlier Polish passes) so we don't count their image-ref echo as a "real" image link.
    ignored_ranges: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if "<!-- ascii-source:" in lines[i]:
            j = i
            while j < len(lines) and not COMMENT_CLOSE.search(lines[j]):
                j += 1
            ignored_ranges.append((i + 1, min(j + 1, len(lines))))
            i = j + 1
        else:
            i += 1

    def in_ignored(line_no: int) -> bool:
        return any(lo <= line_no <= hi for lo, hi in ignored_ranges)

    for b in blocks:
        # An explicit render override wins over the image-ref heuristic (both directions).
        hint = b.get("render_hint")
        if hint == "force":
            b["documentation_only"] = False
            continue
        if hint == "documentation-only":
            b["documentation_only"] = True
            continue
        ascii_start = b["ascii"]["start_line"]
        ascii_end = b["ascii"]["end_line"]
        s_start, s_end = slide_range(ascii_start)
        has_image_ref = False
        for ln_no in range(s_start, s_end + 1):
            if ascii_start <= ln_no <= ascii_end:
                continue
            if in_ignored(ln_no):
                continue
            if IMAGE_REF.search(lines[ln_no - 1]):
                has_image_ref = True
                break
        b["documentation_only"] = has_image_ref


def cmd_scan(args: argparse.Namespace) -> int:
    # Resolve so the plan's final_path is absolute — `prepare-render-args` may run from a
    # different cwd and re-anchors off this field.
    final_path = Path(args.final_path).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    result = scan(final_path, presentation_language=args.language)
    if args.format == "human":
        legacy_count = sum(1 for b in result["blocks"] if b.get("detection_mode") == "legacy-heuristic")
        doc_only_count = sum(1 for b in result["blocks"] if b.get("documentation_only"))
        print(f"found {len(result['blocks'])} ASCII block(s) in {result['final_path']}:")
        if legacy_count:
            print(f"  ⚠  {legacy_count} block(s) detected via legacy glyph-heuristic — re-tag opening fence as ``` ascii ``` to make them canonical")
        if doc_only_count:
            print(f"  ℹ  {doc_only_count} block(s) marked documentation-only (slide has Markdown image ref) — pipeline will skip them")
        if result.get("skipped_non_slide"):
            print(f"  ℹ  {result['skipped_non_slide']} block(s) skipped — under a heading that carries no slides (Thesis / Open questions / Cut material)")
        if result["blocks"]:
            print()
        for b in result["blocks"]:
            a = b["ascii"]
            n = b["note"]
            ascii_lines = a["payload"].count("\n") + 1
            note_part = f"note: yes (lines {n['start_line']}–{n['end_line']})" if n else "note: no"
            flags = []
            if b.get("detection_mode") != "canonical":
                flags.append("legacy")
            if b.get("documentation_only"):
                flags.append("doc-only")
            if b.get("render_hint"):
                flags.append(f"hint:{b['render_hint']}")
            tag_part = f"  [{', '.join(flags)}]" if flags else ""
            print(f"  {b['slide_id']:<10} lines {a['start_line']}–{a['end_line']} ({ascii_lines} ASCII lines)   {note_part}{tag_part}")
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


def build_sidecar_content(ascii_payload: str, note_payload: str | None) -> str:
    body = ascii_payload
    if note_payload:
        body += "\n\n" + note_payload
    if not body.endswith("\n"):
        body += "\n"
    return body


# ── render idempotency: the ASCII hash stamped into the SVG ──────────────────
# The one and only signal that decides re-render. It is stamped into the SVG at render
# time, so it records what *that file* was drawn from, and stays true no matter what
# later passes do to the `.ascii` sidecar (which `extract` overwrites before every
# render). Filenames never decide: a slide_id is minted from position in final.md, so
# it renames itself the moment slides move and can point at a diagram on another topic.
SVG_HASH_MARKER = "talksmith-ascii-sha256"
SVG_HASH_RE = re.compile(rf"^<!--\s*{SVG_HASH_MARKER}:\s*([0-9a-f]{{64}})\s*-->\s*$", re.MULTILINE)
_XML_DECL_RE = re.compile(r"^<\?xml[^>]*\?>\s*")


def ascii_digest(ascii_payload: str, note_payload: str | None) -> str:
    """SHA-256 of exactly what `ascii-to-svg` reads: the sidecar (payload + ascii-note).

    The note carries the render intent, so a changed note must re-render just as a changed
    diagram does — hashing the sidecar rather than the payload alone gets that for free.
    """
    return hashlib.sha256(build_sidecar_content(ascii_payload, note_payload).encode()).hexdigest()


def read_svg_digest(svg_path: Path) -> str | None:
    """The ASCII digest an SVG was stamped with, or None if unstamped/unreadable."""
    try:
        m = SVG_HASH_RE.search(svg_path.read_text())
    except (OSError, UnicodeDecodeError):
        return None
    return m.group(1) if m else None


def stamp_svg_digest(svg_path: Path, digest: str) -> None:
    """Write the digest into the SVG, replacing any previous stamp.

    The marker goes after the XML declaration (nothing may precede it) and before the root
    element, where a comment is legal and no SVG consumer will render it.
    """
    text = SVG_HASH_RE.sub("", svg_path.read_text()).lstrip("\n")
    marker = f"<!-- {SVG_HASH_MARKER}: {digest} -->\n"
    m = _XML_DECL_RE.match(text)
    if m:
        text = text[:m.end()] + marker + text[m.end():]
    else:
        text = marker + text
    svg_path.write_text(text)


def _load_plan(args: argparse.Namespace) -> tuple[Path, dict[str, Any]] | int:
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


def _write_sidecars(final_path: Path, plan: dict[str, Any], dry_run: bool) -> tuple[int, int, int, list[dict[str, Any]]]:
    """Write .ascii sidecars. Returns (written, unchanged, skipped_no_render, sidecar_records)."""
    blocks = plan.get("blocks") or []
    images_dir = final_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    unchanged = 0
    skipped_no_render = 0
    sidecar_records: list[dict[str, Any]] = []

    for b in blocks:
        if b.get("documentation_only"):
            skipped_no_render += 1
            continue
        render = b.get("render")
        if not render:
            skipped_no_render += 1
            continue
        note = b.get("note")
        note_payload = note["payload"] if note else None
        svg_basename = render["svg_basename"]
        stem = svg_basename[:-4] if svg_basename.endswith(".svg") else svg_basename
        sidecar_path = images_dir / f"{stem}.ascii"
        content = build_sidecar_content(b["ascii"]["payload"], note_payload)
        if sidecar_path.exists() and sidecar_path.read_text() == content:
            unchanged += 1
            status = "unchanged"
        else:
            if not dry_run:
                sidecar_path.write_text(content)
            written += 1
            status = "written"
        sidecar_records.append({
            "slide_id": b["slide_id"],
            "path": str(sidecar_path.relative_to(final_path.parent)),
            "status": status,
        })
    return written, unchanged, skipped_no_render, sidecar_records


def _stale_error(lines: list[str], b: dict[str, Any]) -> tuple[int, str] | None:
    """Return (exit_code, message) when block `b`'s recorded lines no longer match final.md.

    Three checks: line range in bounds (2), fences still bracket the range (3), and the payload
    between them still matches the plan byte-for-byte (3) — an in-place edit preserves line count
    and fence positions, so without the payload check the guard silently reverts the user's edit.
    """
    start_idx = b["ascii"]["start_line"] - 1
    end_idx = b["ascii"]["end_line"] - 1
    if start_idx < 0 or end_idx >= len(lines):
        return 2, (f"line range out of bounds for {b['slide_id']}: {start_idx + 1}-{end_idx + 1} "
                   f"(file has {len(lines)} lines)")
    if not lines[start_idx].lstrip().startswith("```") or lines[end_idx].strip() != "```":
        return 3, (f"stale plan — {b['slide_id']} line {start_idx + 1} no longer opens an ASCII fence; "
                   f"re-run `scan` (final.md changed since the plan was captured)")
    if lines[start_idx + 1:end_idx] != b["ascii"]["payload"].splitlines():
        return 3, (f"stale plan — {b['slide_id']} payload at lines {start_idx + 2}-{end_idx} differs "
                   f"from the plan; re-run `scan` (final.md changed since the plan was captured)")
    return None


def _renderable(b: dict[str, Any]) -> bool:
    return not b.get("documentation_only") and bool(b.get("render"))


def _assert_plan_fresh(final_path: Path, plan: dict[str, Any]) -> None:
    """Fail loudly (exit 2/3) if any renderable block's recorded lines have drifted — writes nothing."""
    lines = final_path.read_text().splitlines(keepends=False)
    for b in plan.get("blocks") or []:
        if not _renderable(b):
            continue
        err = _stale_error(lines, b)
        if err:
            code, msg = err
            print(f"error: {msg}", file=sys.stderr)
            raise SystemExit(code)


def _rewrite_final(final_path: Path, plan: dict[str, Any], dry_run: bool) -> tuple[int, int]:
    """Rewrite final.md fences. Returns (rewritten, skipped_no_render)."""
    blocks = plan.get("blocks") or []
    lines = final_path.read_text().splitlines(keepends=False)
    line_endings = "\n"

    rewritten = 0
    skipped_no_render = 0

    # Sort descending by ascii.start_line so line-number rewrites don't shift.
    blocks_sorted = sorted(blocks, key=lambda b: b["ascii"]["start_line"], reverse=True)
    for b in blocks_sorted:
        if b.get("documentation_only"):
            skipped_no_render += 1
            continue
        render = b.get("render")
        if not render:
            skipped_no_render += 1
            continue
        svg_basename = render["svg_basename"]
        if not svg_basename.endswith(".svg"):
            svg_basename = f"{svg_basename}.svg"
        alt = render.get("alt") or b["slide_id"]
        start_idx = b["ascii"]["start_line"] - 1
        end_idx = b["ascii"]["end_line"] - 1
        # Stale-plan guard: bounds, fences, AND payload must still match the plan. Aborts (exit 2/3)
        # rather than silently rewriting wrong or user-edited lines. Nothing has been written yet
        # (the file is written once, after the loop), so aborting here is safe.
        err = _stale_error(lines, b)
        if err:
            code, msg = err
            print(f"error: {msg}", file=sys.stderr)
            raise SystemExit(code)
        # Neutralize any `-->` inside the ASCII so it can't close the `<!-- ascii-source: … -->`
        # comment early (which would leak the rest of the diagram into the visible body, and throw
        # off the doc-only comment-range scan). The `.ascii` sidecar keeps the exact source; this
        # echo is provenance for whoever reads final.md, so an escaped arrow is fine.
        source_lines = [ln.replace("-->", "--&gt;") for ln in b["ascii"]["payload"].splitlines()]
        rewrite_lines = [
            f"![{alt}](images/{svg_basename})",
            "<!-- ascii-source:",
            *source_lines,
            "-->",
        ]
        lines[start_idx:end_idx + 1] = rewrite_lines
        rewritten += 1

    if not dry_run and rewritten:
        new_text = line_endings.join(lines)
        if not new_text.endswith("\n"):
            new_text += "\n"
        tmp = final_path.with_suffix(final_path.suffix + ".tmp")
        tmp.write_text(new_text)
        os.replace(tmp, final_path)
    return rewritten, skipped_no_render


def cmd_extract(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    written, unchanged, skipped_no_render, _ = _write_sidecars(final_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"extracted sidecars from {final_path}:{tag}")
    print(f"  written:   {written}")
    print(f"  unchanged: {unchanged}")
    print(f"  skipped:   {skipped_no_render} (no render mapping)")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    rewritten, skipped_no_render = _rewrite_final(final_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"cleaned up {final_path}:{tag}")
    print(f"  fences rewritten: {rewritten}")
    print(f"  skipped:          {skipped_no_render} (no render mapping)")
    return 0


_INTENT_LINE = re.compile(r"^\s*(?:[#\-*<!]\s*)*intent\s*:\s*(.+?)\s*-*>?\s*$", re.IGNORECASE | re.MULTILINE)


def _read_json_arg(value: str) -> Any:
    text = sys.stdin.read() if value == "-" else Path(value).read_text()
    return json.loads(text)


def cmd_inspect_intents(args: argparse.Namespace) -> int:
    plan = _read_json_arg(args.plan)
    print(f"{'slide_id':<10} | {'title':<50} | intent")
    print(f"{'-' * 10}-+-{'-' * 50}-+-{'-' * 60}")
    for b in plan.get("blocks", []):
        sid = b.get("slide_id", "")
        title = (b.get("context", {}).get("slide_title") or "")[:50]
        note = b.get("note") or {}
        payload = (note.get("payload") or "")
        m = _INTENT_LINE.search(payload)
        intent = (m.group(1).strip() if m else "")[:80]
        flags = []
        if b.get("documentation_only"):
            flags.append("doc-only")
        if b.get("detection_mode") == "legacy-heuristic":
            flags.append("legacy")
        flag_part = f"  [{','.join(flags)}]" if flags else ""
        print(f"{sid:<10} | {title:<50} | {intent}{flag_part}")
    return 0


def cmd_annotate_renders(args: argparse.Namespace) -> int:
    plan = _read_json_arg(args.plan)
    renders = _read_json_arg(args.renders)
    if not isinstance(renders, dict):
        print("error: --renders JSON must be an object mapping slide_id → {svg_basename, alt}", file=sys.stderr)
        return 2

    missing: list[str] = []
    annotated = 0
    skipped_doc = 0
    for b in plan.get("blocks", []):
        sid = b.get("slide_id", "")
        if b.get("documentation_only"):
            b["render"] = None
            skipped_doc += 1
            continue
        entry = renders.get(sid)
        if not entry:
            b["render"] = None
            missing.append(sid)
            continue
        basename = entry.get("svg_basename") or entry.get("basename")
        if not basename:
            b["render"] = None
            missing.append(sid)
            continue
        if not basename.endswith(".svg"):
            basename = f"{basename}.svg"
        b["render"] = {"svg_basename": basename, "alt": entry.get("alt") or ""}
        annotated += 1

    out_text = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    if args.output and args.output != "-":
        Path(args.output).write_text(out_text)
    else:
        sys.stdout.write(out_text)

    print(f"annotated {annotated} block(s); skipped {skipped_doc} documentation-only", file=sys.stderr)
    if missing:
        print(f"  ⚠  {len(missing)} block(s) had no render entry (set to render: null): {', '.join(missing)}", file=sys.stderr)
    return 0


def cmd_prepare_render_args(args: argparse.Namespace) -> int:
    plan = _read_json_arg(args.plan)
    final_path_str = plan.get("final_path")
    if not final_path_str:
        print("error: plan missing 'final_path' field — re-run `scan` to regenerate", file=sys.stderr)
        return 2
    final_path = Path(final_path_str).resolve()
    # A plan carries absolute paths captured at `scan` time. If final.md isn't where the plan says,
    # the plan is stale or from a different session/mount — fail loudly instead of emitting args
    # that point at a path that no longer exists.
    if not final_path.exists():
        print(f"error: plan's final.md not found: {final_path} — the plan is stale or from a different "
              f"session/mount; re-run `scan` in this session", file=sys.stderr)
        return 2
    talk_root = final_path.parent
    images_dir = (talk_root / "images").resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None

    # Path anchoring (mount-portability). The absolute paths below are captured in *this* session's
    # filesystem view; a render worker in a different mount (VM vs host) can't use them. So we also
    # emit Talk-root-relative paths (`images/<name>`) plus `talk_rel` (the Talk dir relative to
    # repo_root), letting the worker re-anchor on the repo_root *it* was dispatched with. If the
    # Talk isn't under repo_root, that mapping is impossible — warn loudly rather than emit a
    # relative path that resolves nowhere.
    talk_rel: str | None = None
    if repo_root:
        try:
            talk_rel = str(talk_root.resolve().relative_to(repo_root))
        except ValueError:
            print(f"warning: --repo-root {repo_root} is not an ancestor of the Talk at "
                  f"{talk_root.resolve()} — emitting absolute paths only; a differently-mounted "
                  f"worker may not resolve them", file=sys.stderr)

    # Pre-flight: every renderable block needs its `.ascii` sidecar (written by `extract`). Check them
    # all before writing any args, so a missing sidecar is a loud precondition error — never a silent
    # args file pointing at a file that isn't there.
    renderables = [b for b in plan.get("blocks", [])
                   if not b.get("documentation_only") and b.get("render")]
    skipped = len(plan.get("blocks", [])) - len(renderables)

    def _stem(b: dict) -> str:
        bn = b["render"]["svg_basename"]
        return (bn if bn.endswith(".svg") else f"{bn}.svg")[:-4]

    missing = [(b.get("slide_id", ""), images_dir / f"{_stem(b)}.ascii")
               for b in renderables if not (images_dir / f"{_stem(b)}.ascii").exists()]
    if missing:
        print("error: missing .ascii sidecar(s) — run `extract` before `prepare-render-args`:", file=sys.stderr)
        for sid, p in missing:
            print(f"  {sid} → {p}", file=sys.stderr)
        return 2

    written = 0
    reused = 0
    for b in renderables:
        sid = b.get("slide_id", "")
        basename = b["render"]["svg_basename"]
        if not basename.endswith(".svg"):
            basename = f"{basename}.svg"
        stem = basename[:-4]
        # Idempotency, in full: an SVG is reused iff it was stamped with the digest of the
        # ASCII we are about to render. Nothing else is consulted — not the filename, not
        # the fence form, not the sidecar (already overwritten by `extract` by now).
        svg_path = images_dir / basename
        digest = ascii_digest(b["ascii"]["payload"], (b.get("note") or {}).get("payload"))
        if svg_path.exists() and read_svg_digest(svg_path) == digest:
            reused += 1
            continue
        ctx = b.get("context") or {}
        payload: dict[str, Any] = {
            "ascii_file": str(images_dir / f"{stem}.ascii"),
            "output_path": str(images_dir / basename),
            # Talk-root-relative twins (mount-portable — see anchoring note above). `talk_rel` is the
            # Talk dir relative to repo_root, so the worker resolves <its repo_root>/<talk_rel>/<*_rel>.
            "ascii_file_rel": f"images/{stem}.ascii",
            "output_path_rel": f"images/{basename}",
            "talk_rel": talk_rel,
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

    print(f"wrote args for {written} block(s) to {out_dir}", file=sys.stderr)
    if reused:
        print(f"  reused {reused} block(s) (SVG stamped with the same ASCII digest — no re-render)", file=sys.stderr)
    if skipped:
        print(f"  skipped {skipped} block(s) (documentation-only or no render mapping)", file=sys.stderr)
    return 0


def cmd_stamp_renders(args: argparse.Namespace) -> int:
    """Stamp each freshly rendered SVG with the digest of the ASCII it was drawn from.

    Must run after the renders and before the next pass — an unstamped SVG simply re-renders
    (the safe direction), so a missed stamp costs work, never correctness.
    """
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    images_dir = final_path.parent / "images"

    stamped = 0
    missing: list[tuple[str, Path]] = []
    for b in plan.get("blocks") or []:
        if b.get("documentation_only") or not b.get("render"):
            continue
        basename = b["render"]["svg_basename"]
        if not basename.endswith(".svg"):
            basename = f"{basename}.svg"
        svg_path = images_dir / basename
        if not svg_path.exists():
            missing.append((b.get("slide_id", ""), svg_path))
            continue
        if not args.dry_run:
            stamp_svg_digest(svg_path, ascii_digest(b["ascii"]["payload"], (b.get("note") or {}).get("payload")))
        stamped += 1

    tag = "  [dry-run]" if args.dry_run else ""
    print(f"stamped {stamped} SVG(s) with their ASCII digest{tag}")
    if missing:
        print(f"  ⚠  {len(missing)} render(s) produced no SVG — they will re-render next pass:", file=sys.stderr)
        for sid, p in missing:
            print(f"     {sid} → {p}", file=sys.stderr)
    return 0


# ── gc: prune orphaned generated diagram triplets ───────────────────────────
_IMG_REF_RE = re.compile(r"!\[[^\]]*\]\(\s*(?:\./)?images/([^)\s]+?)\s*\)")
_IMG_EXT_RE = re.compile(r"\.(svg|png|jpe?g|gif|webp|avif)$", re.IGNORECASE)


def _referenced_stems(final_text: str) -> set[str]:
    """Every `images/<name>` basename referenced by final.md, extension stripped → stem."""
    out: set[str] = set()
    for m in _IMG_REF_RE.finditer(final_text):
        name = m.group(1).rsplit("/", 1)[-1]
        out.add(_IMG_EXT_RE.sub("", name))
    return out


def _generated_diagram_stems(images_dir: Path) -> set[str]:
    """Stems that are *generated diagram* assets — proven by a digest-stamped `.svg` or a `.ascii`
    sidecar. A bare `.png` is NEVER treated as generated, so presenter-owned images are untouchable."""
    stems: set[str] = set()
    for p in images_dir.glob("*.ascii"):
        stems.add(p.stem)
    for p in images_dir.glob("*.svg"):
        if read_svg_digest(p) is not None:      # carries talksmith-ascii-sha256 → we drew it
            stems.add(p.stem)
    return stems


def cmd_gc(args: argparse.Namespace) -> int:
    """List (and, with --apply, delete) generated diagram triplets no longer referenced by final.md.

    Non-destructive by default. Only assets *proven generated* (stamped `.svg` or `.ascii` sidecar)
    are ever considered — orphaned `<stem>.svg` / `<stem>.png` / `<stem>.ascii` plus the
    `.critique/<stem>.png` companion. Presenter-owned images (a plain screenshot with no sidecar or
    stamp) are never candidates, so a missing reference can never delete a source asset.
    """
    final_path = Path(args.final).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    images_dir = (final_path.parent / "images")
    if not images_dir.is_dir():
        print("gc: no images/ directory — nothing to collect")
        return 0

    referenced = _referenced_stems(final_path.read_text())
    orphans = sorted(s for s in _generated_diagram_stems(images_dir) if s not in referenced)

    targets: list[Path] = []
    for s in orphans:
        for cand in (images_dir / f"{s}.svg", images_dir / f"{s}.png",
                     images_dir / f"{s}.ascii", images_dir / ".critique" / f"{s}.png"):
            if cand.exists():
                targets.append(cand)

    if not orphans:
        print("gc: no orphaned generated diagram assets — images/ is clean")
        return 0

    print(f"gc: {len(orphans)} orphaned generated diagram(s), {len(targets)} file(s):")
    for f in targets:
        print(f"  {f.relative_to(final_path.parent)}")
    if args.apply:
        removed = 0
        for f in targets:
            try:
                f.unlink()
                removed += 1
            except OSError as e:
                print(f"  ⚠  could not remove {f}: {e}", file=sys.stderr)
        print(f"gc: removed {removed} file(s)")
    else:
        print("gc: dry-run — pass --apply to delete")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Convenience wrapper — extract + cleanup in one pass."""
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
    # Validate the plan against final.md BEFORE writing sidecars, so a stale plan aborts with
    # nothing written (the exit-3 contract) instead of leaving stale .ascii sidecars behind.
    _assert_plan_fresh(final_path, plan)
    written, unchanged, skipped_no_render, _ = _write_sidecars(final_path, plan, args.dry_run)
    rewritten, _ = _rewrite_final(final_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"applied {rewritten + skipped_no_render} block(s) to {final_path}:{tag}")
    print(f"  sidecars: {written} written, {unchanged} unchanged")
    print(f"  fences:   {rewritten} rewritten")
    if skipped_no_render:
        print(f"  no-render: {skipped_no_render} block(s) had no render mapping (left untouched)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="polish_ascii", description="Step 6 ASCII extractor / final.md rewriter for Talksmith.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="emit JSON describing every ASCII block + ascii-note + per-block context in a Talk's final.md")
    p_scan.add_argument("final_path", help="path to the Talk's final.md (the Step-6 derived file)")
    p_scan.add_argument("--format", choices=["json", "human"], default="json")
    p_scan.add_argument("--language", help="presentation language (e.g. 'Spanish'); stamped into each block's context.presentation_language so the caller doesn't need to add it post-hoc")
    p_scan.set_defaults(func=cmd_scan)

    def _add_plan_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--final", required=True, help="path to the Talk's final.md")
        p.add_argument("--plan", required=True)
        p.add_argument("--dry-run", action="store_true")

    p_inspect = sub.add_parser("inspect-intents", help="print one row per ASCII block — slide_id | slide_title | ascii-note intent — for quick eyeballing of a scan plan")
    p_inspect.add_argument("--plan", required=True, help="path to a scan JSON (or '-' for stdin)")
    p_inspect.set_defaults(func=cmd_inspect_intents)

    p_annot = sub.add_parser("annotate-renders", help="merge a slide_id→{svg_basename,alt} renders map into a scan plan, emitting an annotated plan ready for extract/cleanup/apply")
    p_annot.add_argument("--plan", required=True, help="path to a scan JSON (or '-' for stdin)")
    p_annot.add_argument("--renders", required=True, help="path to a JSON object mapping slide_id → {svg_basename, alt} (or '-' for stdin)")
    p_annot.add_argument("-o", "--output", help="write the annotated plan here (default: stdout). Use '-' for stdout explicitly.")
    p_annot.set_defaults(func=cmd_annotate_renders)

    p_prep = sub.add_parser("prepare-render-args", help="fan an annotated plan out to one <slide_id>.json args file per renderable block, ready to drive parallel `talksmith:ascii-to-svg` invocations")
    p_prep.add_argument("--plan", required=True, help="path to an annotated plan JSON (or '-' for stdin) — must have render fields set")
    p_prep.add_argument("--out-dir", required=True, help="directory to write per-block args files into (created if missing)")
    p_prep.add_argument("--repo-root", help="presenter's working directory (where /talksmith:init ran), stamped into each args file so ascii-to-svg can anchor Talk-relative paths. Plugin-bundled assets are reached via ${CLAUDE_PLUGIN_ROOT}/ independently. Optional.")
    p_prep.set_defaults(func=cmd_prepare_render_args)

    p_extract = sub.add_parser("extract", help="write .ascii sidecars from an annotated scan plan (no final.md mutation)")
    _add_plan_args(p_extract)
    p_extract.set_defaults(func=cmd_extract)

    p_stamp = sub.add_parser("stamp-renders", help="stamp each rendered SVG with the digest of the ASCII it was drawn from — the sole re-render signal for the next pass")
    _add_plan_args(p_stamp)
    p_stamp.set_defaults(func=cmd_stamp_renders)

    p_cleanup = sub.add_parser("cleanup", help="rewrite final.md fences to image refs from an annotated scan plan (no sidecar writing)")
    _add_plan_args(p_cleanup)
    p_cleanup.set_defaults(func=cmd_cleanup)

    p_apply = sub.add_parser("apply", help="extract + cleanup in one pass (convenience)")
    _add_plan_args(p_apply)
    p_apply.set_defaults(func=cmd_apply)

    p_gc = sub.add_parser("gc", help="list (or --apply delete) generated diagram triplets (.svg/.png/.ascii + .critique png) no longer referenced by final.md; presenter-owned images are never touched")
    p_gc.add_argument("--final", required=True, help="path to the Talk's final.md")
    p_gc.add_argument("--apply", action="store_true", help="delete the orphaned files (default: dry-run list only)")
    p_gc.add_argument("--dry-run", action="store_true", help="explicit no-op; gc is dry by default (kept for symmetry)")
    p_gc.set_defaults(func=cmd_gc)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
