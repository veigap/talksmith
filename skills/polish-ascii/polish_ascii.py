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
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CANONICAL_ASCII_TAG = "ascii"
LEGACY_ASCII_LANG_TAGS = {"", "text", "diagram"}
BOX_OR_ARROW = re.compile(r"[─│┌┐└┘├┤┬┴┼+|→←↑↓]|->|==>|<-|=>")
FENCE_OPEN = re.compile(r"^```(\w*)\s*$")
FENCE_CLOSE = re.compile(r"^```\s*$")
H1_SECTION = re.compile(r"^# (\d+)\.")
H1_AGENDA = re.compile(r"^# (?:Agenda|Índice|Indice)\b", re.IGNORECASE)
H1_CONCL = re.compile(r"^# (?:Conclusion|Conclusiones|Conclusions)\b", re.IGNORECASE)
H2_SLIDE = re.compile(r"^## (\d+)\.")
H1_OR_H2 = re.compile(r"^#{1,2} ")
IMAGE_REF = re.compile(r"!\[[^\]]*\]\([^)]+\)")
NOTE_OPEN = "<!-- ascii-note:"


def is_ascii_payload(payload: str) -> bool:
    if BOX_OR_ARROW.search(payload):
        return True
    return payload.count("\n") >= 2


# ── per-block context extraction ────────────────────────────────────────────

_H3 = re.compile(r"^###\s+(.+?)\s*$")
_GOAL_LINE = re.compile(r"^\*\*Goal of this section:\*\*\s*(.*)$")
_H1_NUMBERED_STRIP = re.compile(r"^#\s+\d+\.\s*")
_H2_NUMBERED_STRIP = re.compile(r"^##\s+\d+\.\s*")
_H1_PLAIN_STRIP = re.compile(r"^#\s+")
_INLINE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_prose(body_lines: list[str]) -> str:
    """Return body text with fenced code blocks, HTML comments, and `---` horizontal rules removed."""
    if not body_lines:
        return ""
    text = "\n".join(body_lines)
    # Strip single-line and multi-line HTML comments first (handles nested ascii-source / ascii-note echoes).
    text = _INLINE_COMMENT.sub("", text)
    # Strip fenced code blocks (any language) and horizontal rules.
    out_lines: list[str] = []
    in_fence = False
    for ln in text.splitlines():
        if FENCE_OPEN.match(ln) or FENCE_CLOSE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if ln.strip() in ("---", "***", "___"):
            continue
        out_lines.append(ln)
    return "\n".join(out_lines).strip()


def _skip_frontmatter(lines: list[str]) -> int:
    """If `lines` opens with a YAML `---` frontmatter block, return the 0-based index
    of the first line *after* the closing `---`. Otherwise return 0."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    # Unclosed frontmatter — treat whole file as frontmatter-less to be safe.
    return 0


def _extract_thesis(lines: list[str]) -> str:
    """Body of the `# Thesis` block (Claim + Why it matters paragraphs), stripped.

    Skips YAML frontmatter so that comments like `# thesis: ...` inside it aren't
    misread as the Thesis heading. Matches the heading exactly (case-insensitively
    after strip) to avoid matching ad-hoc headings like `# Thesis revision 2`.
    """
    start = _skip_frontmatter(lines)
    body: list[str] = []
    in_thesis = False
    for ln in lines[start:]:
        if ln.startswith("# ") and not ln.startswith("## "):
            if ln.strip().lower() == "# thesis":
                in_thesis = True
                continue
            if in_thesis:
                break
        if in_thesis:
            body.append(ln)
    return _strip_prose(body)


def _strip_h1(line: str) -> str:
    """Strip the leading `# ` (and any numbered prefix `N. `) from an H1 heading, preserving the heading text."""
    if H1_SECTION.match(line):
        return _H1_NUMBERED_STRIP.sub("", line).strip()
    # Agenda, Conclusions, anything else: strip just the `# ` prefix and preserve the rest verbatim.
    return _H1_PLAIN_STRIP.sub("", line).strip()


def _strip_h2(line: str) -> str:
    return _H2_NUMBERED_STRIP.sub("", line).strip()


def _is_section_heading(ln: str) -> bool:
    return bool(H1_SECTION.match(ln) or H1_AGENDA.match(ln) or H1_CONCL.match(ln))


def _extract_block_context(lines: list[str], ascii_start_line: int) -> dict[str, str]:
    """Walk back from the ASCII block (1-based line) to gather slide + section context."""
    start_idx = ascii_start_line - 1  # 0-based

    # Walk back to find the most recent H2 (slide), then the most recent section H1.
    slide_idx = -1
    section_idx = -1
    for i in range(start_idx - 1, -1, -1):
        ln = lines[i]
        if slide_idx < 0 and H2_SLIDE.match(ln):
            slide_idx = i
            continue
        if _is_section_heading(ln):
            section_idx = i
            break

    slide_title = _strip_h2(lines[slide_idx]) if slide_idx >= 0 else ""
    section_title = _strip_h1(lines[section_idx]) if section_idx >= 0 else ""

    # section_goal: scan lines between section heading and the first H2 inside the section.
    section_goal = ""
    if section_idx >= 0:
        end_idx = slide_idx if slide_idx >= 0 else len(lines)
        # If no slide above us, scan to next H2 or H1 below the section heading.
        if slide_idx < 0:
            for j in range(section_idx + 1, len(lines)):
                if H2_SLIDE.match(lines[j]) or _is_section_heading(lines[j]):
                    end_idx = j
                    break
        for j in range(section_idx + 1, end_idx):
            m = _GOAL_LINE.match(lines[j])
            if not m:
                continue
            goal_text = m.group(1).strip()
            # If the goal continues on subsequent lines, accumulate until a blank line / structural marker.
            if not goal_text:
                continuation: list[str] = []
                for k in range(j + 1, end_idx):
                    nxt = lines[k]
                    if not nxt.strip():
                        if continuation:
                            break
                        continue
                    if nxt.startswith("**") or nxt.startswith("#") or nxt.strip() == "---":
                        break
                    continuation.append(nxt.strip())
                section_goal = " ".join(continuation).strip()
            else:
                section_goal = goal_text
            break

    # slide body: from the H2 line up to the next H2 / H1.
    slide_content_prose = ""
    speaker_notes = ""
    if slide_idx >= 0:
        slide_end = len(lines)
        for j in range(slide_idx + 1, len(lines)):
            if H2_SLIDE.match(lines[j]) or _is_section_heading(lines[j]):
                slide_end = j
                break
        # Walk H3 fields within the slide.
        j = slide_idx + 1
        while j < slide_end:
            m = _H3.match(lines[j])
            if not m:
                j += 1
                continue
            h3_title = m.group(1).strip().lower()
            body_start = j + 1
            body_end = slide_end
            for k in range(j + 1, slide_end):
                if _H3.match(lines[k]):
                    body_end = k
                    break
            body = lines[body_start:body_end]
            if h3_title == "content":
                slide_content_prose = _strip_prose(body)
            elif h3_title in ("speaker notes", "notes"):
                speaker_notes = _strip_prose(body)
            j = body_end

    return {
        "slide_title": slide_title,
        "section_title": section_title,
        "section_goal": section_goal,
        "slide_content_prose": slide_content_prose,
        "speaker_notes": speaker_notes,
    }


def scan(final_path: Path, presentation_language: str | None = None) -> dict[str, Any]:
    text = final_path.read_text()
    lines = text.splitlines()

    section: str | int = 0  # 0 = pre-Agenda / Agenda; "c" = Conclusions
    slide = 0
    ascii_n = 0

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
            if H1_AGENDA.match(ln):
                section, slide, ascii_n = 0, 0, 0
            elif H1_CONCL.match(ln):
                section, slide, ascii_n = "c", 0, 0
            else:
                m_sec = H1_SECTION.match(ln)
                m_sld = H2_SLIDE.match(ln)
                if m_sec:
                    section = int(m_sec.group(1))
                    slide = 0
                    ascii_n = 0
                elif m_sld:
                    slide = int(m_sld.group(1))
                    ascii_n = 0
            m_f = FENCE_OPEN.match(ln)
            if m_f:
                in_fence = True
                fence_lang = m_f.group(1).lower()
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
                    if accept:
                        ascii_n += 1
                        slide_id = f"s{section}-{slide}-{ascii_n}"
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
                            while k < len(lines) and "-->" not in lines[k]:
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
                            "documentation_only": False,  # filled by _annotate_documentation_only below
                        })
                in_fence = False
                fence_lang = None
                buf = []
            else:
                buf.append(ln)
        i += 1

    _annotate_documentation_only(lines, blocks)

    # Per-block context (mechanical extraction so callers don't re-parse final.md per render).
    thesis = _extract_thesis(lines)
    for b in blocks:
        ctx = _extract_block_context(lines, b["ascii"]["start_line"])
        ctx["talk_thesis"] = thesis
        if presentation_language:
            ctx["presentation_language"] = presentation_language
        b["context"] = ctx

    return {"final_path": str(final_path), "blocks": blocks}


def _annotate_documentation_only(lines: list[str], blocks: list[dict[str, Any]]) -> None:
    """Flag each ASCII block as documentation_only when its containing slide has a Markdown image ref.

    Slide scope = lines between the most recent H1/H2 boundary at-or-before the block and the next
    H1/H2 boundary after it. An image ref anywhere in that scope (outside the ASCII block lines
    themselves and outside `<!-- ascii-source: ... -->` HTML comments left by prior Polish passes)
    means the block is documentation-only — the pipeline must skip it.
    """
    boundaries = [i + 1 for i, ln in enumerate(lines) if H1_OR_H2.match(ln)]
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
            while j < len(lines) and "-->" not in lines[j]:
                j += 1
            ignored_ranges.append((i + 1, min(j + 1, len(lines))))
            i = j + 1
        else:
            i += 1

    def in_ignored(line_no: int) -> bool:
        return any(lo <= line_no <= hi for lo, hi in ignored_ranges)

    for b in blocks:
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
    final_path = Path(args.final_path)
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
        if start_idx < 0 or end_idx >= len(lines):
            raise SystemExit(f"error: line range out of bounds for {b['slide_id']}: {start_idx + 1}-{end_idx + 1} (file has {len(lines)} lines)")
        rewrite_lines = [
            f"![{alt}](images/{svg_basename})",
            "<!-- ascii-source:",
            *b["ascii"]["payload"].splitlines(),
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
    images_dir = (final_path.parent / "images").resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None

    written = 0
    skipped = 0
    for b in plan.get("blocks", []):
        sid = b.get("slide_id", "")
        if b.get("documentation_only") or not b.get("render"):
            skipped += 1
            continue
        basename = b["render"]["svg_basename"]
        if not basename.endswith(".svg"):
            basename = f"{basename}.svg"
        stem = basename[:-4]
        ctx = b.get("context") or {}
        payload: dict[str, Any] = {
            "ascii_file": str(images_dir / f"{stem}.ascii"),
            "output_path": str(images_dir / basename),
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
    if skipped:
        print(f"  skipped {skipped} block(s) (documentation-only or no render mapping)", file=sys.stderr)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Convenience wrapper — extract + cleanup in one pass."""
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    final_path, plan = loaded
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

    p_cleanup = sub.add_parser("cleanup", help="rewrite final.md fences to image refs from an annotated scan plan (no sidecar writing)")
    _add_plan_args(p_cleanup)
    p_cleanup.set_defaults(func=cmd_cleanup)

    p_apply = sub.add_parser("apply", help="extract + cleanup in one pass (convenience)")
    _add_plan_args(p_apply)
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
