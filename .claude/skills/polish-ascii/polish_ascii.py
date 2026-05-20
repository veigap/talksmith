#!/usr/bin/env python3
"""talksmith:polish-ascii — Step 6 helper.

Subcommands:
  scan     <master.md> [--format json|human]
  extract  --master <master.md> --plan <plan.json|-> [--dry-run]
  cleanup  --master <master.md> --plan <plan.json|-> [--dry-run]
  apply    --master <master.md> --plan <plan.json|-> [--dry-run]   # extract + cleanup in one pass (compat)

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
NOTE_OPEN = "<!-- ascii-note:"


def is_ascii_payload(payload: str) -> bool:
    if BOX_OR_ARROW.search(payload):
        return True
    return payload.count("\n") >= 2


def scan(master_path: Path) -> dict[str, Any]:
    text = master_path.read_text()
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
                        })
                in_fence = False
                fence_lang = None
                buf = []
            else:
                buf.append(ln)
        i += 1

    return {"master_path": str(master_path), "blocks": blocks}


def cmd_scan(args: argparse.Namespace) -> int:
    master_path = Path(args.master_path)
    if not master_path.exists():
        print(f"error: master not found: {master_path}", file=sys.stderr)
        return 2
    result = scan(master_path)
    if args.format == "human":
        legacy_count = sum(1 for b in result["blocks"] if b.get("detection_mode") == "legacy-heuristic")
        print(f"found {len(result['blocks'])} ASCII block(s) in {result['master_path']}:")
        if legacy_count:
            print(f"  ⚠  {legacy_count} block(s) detected via legacy glyph-heuristic — re-tag opening fence as ``` ascii ``` to make them canonical")
        if result["blocks"]:
            print()
        for b in result["blocks"]:
            a = b["ascii"]
            n = b["note"]
            ascii_lines = a["payload"].count("\n") + 1
            note_part = f"note: yes (lines {n['start_line']}–{n['end_line']})" if n else "note: no"
            tag_part = "" if b.get("detection_mode") == "canonical" else "  [legacy]"
            print(f"  {b['slide_id']:<10} lines {a['start_line']}–{a['end_line']} ({ascii_lines} ASCII lines)   {note_part}{tag_part}")
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


def is_reuse_note(note_payload: str | None) -> bool:
    if not note_payload:
        return False
    for raw_line in note_payload.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("reuse:"):
            return True
    return False


def build_sidecar_content(ascii_payload: str, note_payload: str | None) -> str:
    body = ascii_payload
    if note_payload:
        body += "\n\n" + note_payload
    if not body.endswith("\n"):
        body += "\n"
    return body


def _load_plan(args: argparse.Namespace) -> tuple[Path, dict[str, Any]] | int:
    master_path = Path(args.master).resolve()
    if not master_path.exists():
        print(f"error: master not found: {master_path}", file=sys.stderr)
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
    return master_path, plan


def _write_sidecars(master_path: Path, plan: dict[str, Any], dry_run: bool) -> tuple[int, int, int, int, list[dict[str, Any]]]:
    """Write .ascii sidecars. Returns (written, unchanged, skipped_reuse, skipped_no_render, sidecar_records)."""
    blocks = plan.get("blocks") or []
    images_dir = master_path.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    unchanged = 0
    skipped_reuse = 0
    skipped_no_render = 0
    sidecar_records: list[dict[str, Any]] = []

    for b in blocks:
        render = b.get("render")
        if not render:
            skipped_no_render += 1
            continue
        note = b.get("note")
        note_payload = note["payload"] if note else None
        if is_reuse_note(note_payload):
            skipped_reuse += 1
            continue
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
            "path": str(sidecar_path.relative_to(master_path.parent)),
            "status": status,
        })
    return written, unchanged, skipped_reuse, skipped_no_render, sidecar_records


def _rewrite_master(master_path: Path, plan: dict[str, Any], dry_run: bool) -> tuple[int, int, int]:
    """Rewrite master.md fences. Returns (rewritten, skipped_reuse, skipped_no_render)."""
    blocks = plan.get("blocks") or []
    lines = master_path.read_text().splitlines(keepends=False)
    line_endings = "\n"

    rewritten = 0
    skipped_reuse = 0
    skipped_no_render = 0

    # Sort descending by ascii.start_line so line-number rewrites don't shift.
    blocks_sorted = sorted(blocks, key=lambda b: b["ascii"]["start_line"], reverse=True)
    for b in blocks_sorted:
        render = b.get("render")
        if not render:
            skipped_no_render += 1
            continue
        note = b.get("note")
        note_payload = note["payload"] if note else None
        if is_reuse_note(note_payload):
            skipped_reuse += 1
            continue
        svg_basename = render["svg_basename"]
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
        tmp = master_path.with_suffix(master_path.suffix + ".tmp")
        tmp.write_text(new_text)
        os.replace(tmp, master_path)
    return rewritten, skipped_reuse, skipped_no_render


def cmd_extract(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    master_path, plan = loaded
    written, unchanged, skipped_reuse, skipped_no_render, _ = _write_sidecars(master_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"extracted sidecars from {master_path}:{tag}")
    print(f"  written:   {written}")
    print(f"  unchanged: {unchanged}")
    print(f"  skipped:   {skipped_reuse} (reuse:), {skipped_no_render} (no render mapping)")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    master_path, plan = loaded
    rewritten, skipped_reuse, skipped_no_render = _rewrite_master(master_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"cleaned up {master_path}:{tag}")
    print(f"  fences rewritten: {rewritten}")
    print(f"  skipped:          {skipped_reuse} (reuse:), {skipped_no_render} (no render mapping)")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Convenience wrapper — extract + cleanup in one pass."""
    loaded = _load_plan(args)
    if isinstance(loaded, int):
        return loaded
    master_path, plan = loaded
    written, unchanged, skipped_reuse, skipped_no_render, _ = _write_sidecars(master_path, plan, args.dry_run)
    rewritten, _, _ = _rewrite_master(master_path, plan, args.dry_run)
    tag = "  [dry-run]" if args.dry_run else ""
    print(f"applied {rewritten + skipped_reuse + skipped_no_render} block(s) to {master_path}:{tag}")
    print(f"  sidecars: {written} written, {unchanged} unchanged, {skipped_reuse} skipped (reuse:)")
    print(f"  fences:   {rewritten} rewritten")
    if skipped_no_render:
        print(f"  no-render: {skipped_no_render} block(s) had no render mapping (left untouched)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="polish_ascii", description="Step 6 ASCII extractor / master.md rewriter for Talksmith.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="emit JSON describing every ASCII block + ascii-note in a master.md")
    p_scan.add_argument("master_path")
    p_scan.add_argument("--format", choices=["json", "human"], default="json")
    p_scan.set_defaults(func=cmd_scan)

    def _add_plan_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--master", required=True)
        p.add_argument("--plan", required=True)
        p.add_argument("--dry-run", action="store_true")

    p_extract = sub.add_parser("extract", help="write .ascii sidecars from an annotated scan plan (no master.md mutation)")
    _add_plan_args(p_extract)
    p_extract.set_defaults(func=cmd_extract)

    p_cleanup = sub.add_parser("cleanup", help="rewrite master.md fences to image refs from an annotated scan plan (no sidecar writing)")
    _add_plan_args(p_cleanup)
    p_cleanup.set_defaults(func=cmd_cleanup)

    p_apply = sub.add_parser("apply", help="extract + cleanup in one pass (convenience)")
    _add_plan_args(p_apply)
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
