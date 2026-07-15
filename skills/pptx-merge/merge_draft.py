#!/usr/bin/env python3
"""merge_draft.py — apply a finalpptx.diff.json back into draft.md. Design D of
the Talksmith reverse pipeline.

draft.md is the editable source of truth; final.md is derived and re-runnable, so
changes made in the deck land in draft.md and Step-6 Polish re-derives final.md.
Because Polish only strips feedback / rewrites ASCII / rescues [open] bullets, a
change is re-anchored to draft.md *structurally* — by (section, slide title) then
by the pre-change text — not by line number.

Per the operating decision, `apply-auto` applies the SIMPLE, high-confidence,
unambiguously-anchored changes automatically and leaves everything COMPLEX or
CONFUSING for the Editor (low-confidence matches, removals, added/deleted slides,
and image edits that trace back to an ASCII source). `plan` shows the split;
granular `apply` subcommands let the Editor land the complex ones after authoring
the wording.

Subcommands:
  plan          --diff <diff.json> --draft <draft.md> [--format json|human]
  apply-auto    --diff <diff.json> --draft <draft.md> [--dry-run]
  replace-line  --draft <draft.md> --line N --text "<new>" [--expect "<old>"]
  append-line   --draft <draft.md> --section <key> --slide-title "<t>" --field <content|speaker notes> --text "<new>"
  remove-line   --draft <draft.md> --line N [--expect "<old>"]
  add-image     --draft <draft.md> --section <key> --slide-title "<t>" --alt "<a>" --src <staged/path> [--dest-basename <b>]
  replace-image --draft <draft.md> --basename <b> --src <staged/path>
  retitle       --draft <draft.md> --section <key> --old-title "<o>" --new-title "<n>"

Exit codes: 0 ok · 2 bad input / anchor not found · 3 anchor drift (re-run plan)

stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
import _pptxlib as L

FIELD_ALIASES = {"content": "content", "notes": "speaker notes", "speaker notes": "speaker notes"}


# --------------------------------------------------------------------------- #
# shared draft helpers
# --------------------------------------------------------------------------- #

def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _atomic_write(path: Path, lines: list[str]) -> None:
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _find_slide(tree: dict, section_key, title: str, slide_num=None):
    """Locate a draft slide by normalized title within a section; fall back to
    (section_key, slide_num). Returns the MdSlide or None."""
    slides = tree["slides"]
    ntitle = L.normalize_title(title or "")
    # 1. same section + title
    for s in slides:
        if str(s.section_key) == str(section_key) and L.normalize_title(s.title) == ntitle:
            return s
    # 2. title anywhere
    if ntitle:
        cands = [s for s in slides if L.normalize_title(s.title) == ntitle]
        if len(cands) == 1:
            return cands[0]
    # 3. section + slide number
    if slide_num:
        for s in slides:
            if str(s.section_key) == str(section_key) and s.slide_num == slide_num:
                return s
    return None


def _field_for_kind(kind: str) -> str:
    return "content" if kind == "content" else "speaker notes"


def _slide_has_ascii(slide) -> bool:
    for f in slide.fields.values():
        joined = "\n".join(f.body_lines)
        if re.search(r"```ascii", joined) or "<!-- ascii-source:" in joined:
            return True
    return False


def _looks_like_chrome(talk_root: Path, src: str | None) -> tuple[bool, str]:
    """Assess whether a staged image looks like template chrome rather than
    content the presenter intentionally added.

    Extract has already dropped obvious icons and reused-within-slide chrome.
    Merge is more conservative for single-occurrence decorations that survive:
      - `max(w, h) ≤ 128` — an icon that slipped through extract (e.g.
        because it had no SVG twin AND wasn't reused).
      - `min(w, h) < 250` — one dimension too small for real slide content;
        typical of divider bars, quote decorations, ribbon accents.
      - `max(w, h) / min(w, h) > 4` — extreme aspect ratio; typical of
        banner/divider chrome. Real content diagrams sit in 1.5–2.8 range.

    Returns (True, reason) → route to [needs-editor] rather than auto-add.
    A dimension read failure returns (False, "") so we don't reject on
    metadata errors alone.
    """
    if not src:
        return False, ""
    path = talk_root / src if not Path(src).is_absolute() else Path(src)
    if not path.is_file():
        return False, ""
    try:
        blob = path.read_bytes()
    except OSError:
        return False, ""
    dims = L.intrinsic_dims(path.name, blob)
    if not dims:
        return False, ""
    w, h = int(dims[0]), int(dims[1])
    if max(w, h) <= 128:
        return True, f"image {w}×{h} is icon-sized"
    if min(w, h) < 250:
        return True, f"image {w}×{h} has a small dimension (<250 px)"
    ratio = max(w, h) / max(min(w, h), 1)
    if ratio > 4:
        return True, f"image {w}×{h} has extreme aspect ratio {ratio:.1f}:1"
    return False, ""


# --------------------------------------------------------------------------- #
# plan — classify each change appliable vs needs-editor, resolve draft anchors
# --------------------------------------------------------------------------- #

def _resolve_anchor_line(slide, kind: str, from_text: str):
    """Return the 1-based draft line whose normalized prose == from_text, within
    the change's field. None if not found."""
    fname = _field_for_kind(kind)
    fld = slide.fields.get(fname)
    if not fld:
        return None
    target = L.normalize_prose(from_text)
    for off, raw in enumerate(fld.body_lines):
        if L.normalize_prose(raw) == target and target:
            return fld.body_start + off
    return None


def _plan_action(change: dict, tree: dict, talk_root: Path) -> dict:
    kind = change["kind"]
    conf = change.get("confidence", "high")
    base = {"id": change["id"], "kind": kind, "op": change.get("op")}

    if kind in ("slide_added", "slide_deleted"):
        return {**base, "appliable": False, "command": None,
                "reason": f"{kind} — Editor decides (structural change)"}

    section = change.get("section")
    title = change.get("title")
    slide = _find_slide(tree, section, title, change.get("slide"))
    if slide is None:
        return {**base, "appliable": False, "command": None,
                "reason": "no draft.md slide anchor (title not found)"}

    if conf == "low":
        return {**base, "appliable": False, "command": None,
                "reason": "low-confidence alignment — Editor confirms"}

    if kind == "title":
        return {**base, "appliable": True,
                "command": ["retitle", "--section", str(section),
                            "--old-title", change["from"], "--new-title", change["to"]],
                "reason": "retitle H2"}

    if kind in ("content", "notes"):
        op = change["op"]
        if op == "removed":
            return {**base, "appliable": False, "command": None,
                    "reason": "content/notes removal — Editor confirms before deleting"}
        if op == "modified":
            line = _resolve_anchor_line(slide, kind, change["from"])
            if line is None:
                return {**base, "appliable": False, "command": None,
                        "reason": "pre-change text not found in draft field"}
            return {**base, "appliable": True,
                    "command": ["replace-line", "--line", str(line),
                                "--expect", change["from"], "--text", change["to"]],
                    "reason": f"replace {kind} line {line}"}
        if op == "added":
            return {**base, "appliable": True,
                    "command": ["append-line", "--section", str(section),
                                "--slide-title", slide.title,
                                "--field", _field_for_kind(kind), "--text", change["to"]],
                    "reason": f"append {kind} line"}

    if kind == "image":
        op = change["op"]
        if op == "added":
            if _slide_has_ascii(slide):
                return {**base, "appliable": False, "command": None,
                        "reason": "slide has an ASCII source — Editor decides image vs ASCII"}
            src = change.get("pptx_path")
            # Content-vs-chrome heuristic. Extract has already filtered obvious
            # icons and reused chrome, but single-occurrence decorations (a
            # 170×300 divider used once, a thin banner not repeated) survive
            # extract because we can't be sure without cross-referencing final.md.
            # Merge sees the full picture, so it can guard `add-image` on
            # visual characteristics that suggest template decoration rather
            # than content the presenter intentionally placed.
            suspicious, why = _looks_like_chrome(talk_root, src)
            if suspicious:
                return {**base, "appliable": False, "command": None,
                        "reason": f"{why} — presenter confirms whether this is real content "
                                  f"(use granular `add-image` to force)"}
            # Staging names look like `slideN-imgM.png` — that's a slot key, not
            # a meaningful destination name. Fall back to the slide's slug.
            raw_base = change.get("basename") or Path(src or "").name
            if re.match(r"^slide\d+-img\d+\.", raw_base):
                dest = f"s{section}-{slide.slide_num}-{change.get('slot', 'x')}-new.png"
            else:
                dest = re.sub(r"^(?:slide\d+-img\d+|s\d+)-", "", raw_base)
            if any(im.basename == dest for im in slide.images):
                return {**base, "appliable": False, "command": None,
                        "reason": f"image {dest} already present in draft slide — nothing to add"}
            alt = change.get("alt")
            if not alt or alt.upper() == "NEW":
                alt = slide.title
            return {**base, "appliable": True,
                    "command": ["add-image", "--section", str(section),
                                "--slide-title", slide.title,
                                "--alt", alt,
                                "--src", src, "--dest-basename", dest],
                    "reason": f"add new image {dest}"}
        if op == "replaced":
            target = change.get("target_basename") or change.get("basename")
            if not target:
                return {**base, "appliable": False, "command": None,
                        "reason": "replaced image has no target basename in diff"}
            # If the draft diagram is an ASCII source, the edit belongs in the ASCII.
            sidecar = talk_root / "images" / (Path(target).stem + ".ascii")
            if _slide_has_ascii(slide) or sidecar.exists():
                return {**base, "appliable": False, "command": None,
                        "reason": f"image maps to a draft ASCII source ({sidecar.name}) — edit the ASCII, not the image"}
            return {**base, "appliable": True,
                    "command": ["replace-image", "--basename", target,
                                "--src", change.get("pptx_path")],
                    "reason": f"overwrite images/{target} from deck slot {change.get('slot','?')}"}
        # removed / renamed
        return {**base, "appliable": False, "command": None,
                "reason": f"image {op} — Editor confirms"}

    return {**base, "appliable": False, "command": None, "reason": "unhandled change kind"}


def cmd_plan(args) -> int:
    diff = json.loads(Path(args.diff).read_text(encoding="utf-8"))
    draft = Path(args.draft)
    if not draft.is_file():
        print(f"failed: draft not found: {draft}", file=sys.stderr)
        return 2
    tree = L.parse_md_slides(str(draft))
    talk_root = draft.resolve().parent
    actions = [_plan_action(c, tree, talk_root) for c in diff.get("changes", [])]
    appliable = [a for a in actions if a["appliable"]]
    needs = [a for a in actions if not a["appliable"]]

    if args.format == "json":
        print(json.dumps({"draft": str(draft), "actions": actions,
                          "summary": {"total": len(actions),
                                      "appliable": len(appliable),
                                      "needs_editor": len(needs)}},
                         indent=2, ensure_ascii=False))
        return 0

    print(f"plan: {len(actions)} changes — {len(appliable)} appliable, "
          f"{len(needs)} needs-editor")
    for a in actions:
        tag = "[appliable]  " if a["appliable"] else "[needs-editor]"
        print(f"  {tag} {a['id']} {a['kind']}/{a['op']}: {a['reason']}")
    return 0


# --------------------------------------------------------------------------- #
# apply-auto — run every appliable action
# --------------------------------------------------------------------------- #

def cmd_apply_auto(args) -> int:
    diff = json.loads(Path(args.diff).read_text(encoding="utf-8"))
    draft = Path(args.draft)
    if not draft.is_file():
        print(f"failed: draft not found: {draft}", file=sys.stderr)
        return 2
    talk_root = draft.resolve().parent

    applied, skipped, failed = 0, 0, 0
    reports: list[str] = []
    # Apply retitles LAST (stable sort): every change carries the slide's PRE-change title
    # as its anchor, so landing a retitle first orphans the same slide's remaining edits —
    # they re-plan against the renamed slide and skip with "no draft.md slide anchor"
    # (the slide-number fallback can't rescue unnumbered H2 slides).
    changes = sorted(diff.get("changes", []), key=lambda c: 1 if c.get("kind") == "title" else 0)
    for change in changes:
        # Re-plan against the CURRENT draft each time (line numbers shift).
        tree = L.parse_md_slides(str(draft))
        action = _plan_action(change, tree, talk_root)
        if not action["appliable"]:
            skipped += 1
            reports.append(f"  skip {action['id']} ({action['kind']}/{action['op']}): {action['reason']}")
            continue
        rc = _dispatch(action["command"], draft, dry_run=args.dry_run)
        if rc == 0:
            applied += 1
            reports.append(f"  apply {action['id']}: {action['reason']}")
        else:
            failed += 1
            reports.append(f"  FAIL {action['id']}: rc={rc} ({action['reason']})")

    tag = " [dry-run]" if args.dry_run else ""
    print(f"merge{tag}: {applied} applied, {skipped} needs-editor, {failed} failed")
    for r in reports:
        print(r)
    return 0 if failed == 0 else 3


def _dispatch(command: list[str], draft: Path, dry_run: bool) -> int:
    argv = [command[0], "--draft", str(draft)] + command[1:]
    if dry_run:
        argv.append("--dry-run")
    return main(argv)


# --------------------------------------------------------------------------- #
# granular ops
# --------------------------------------------------------------------------- #

def cmd_replace_line(args) -> int:
    draft = Path(args.draft)
    lines = _read_lines(draft)
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f"failed: line {args.line} out of range", file=sys.stderr)
        return 2
    if args.expect is not None and L.normalize_prose(lines[idx]) != L.normalize_prose(args.expect):
        print(f"failed: line {args.line} no longer matches expected text — re-run plan", file=sys.stderr)
        return 3
    # Preserve leading indentation + bullet/blockquote marker of the old line.
    m = re.match(r"^(\s*(?:[-*+]\s+|>\s+)?)", lines[idx])
    prefix = m.group(1) if m else ""
    new = args.text
    if prefix and not re.match(r"^\s*(?:[-*+]\s+|>\s+)", new):
        new = prefix + new
    if args.dry_run:
        print(f"[dry-run] line {args.line}: {lines[idx]!r} → {new!r}")
        return 0
    lines[idx] = new
    _atomic_write(draft, lines)
    print(f"replace-line: draft line {args.line}")
    return 0


def cmd_remove_line(args) -> int:
    draft = Path(args.draft)
    lines = _read_lines(draft)
    idx = args.line - 1
    if idx < 0 or idx >= len(lines):
        print(f"failed: line {args.line} out of range", file=sys.stderr)
        return 2
    if args.expect is not None and L.normalize_prose(lines[idx]) != L.normalize_prose(args.expect):
        print(f"failed: line {args.line} no longer matches expected text — re-run plan", file=sys.stderr)
        return 3
    if args.dry_run:
        print(f"[dry-run] remove line {args.line}: {lines[idx]!r}")
        return 0
    del lines[idx]
    _atomic_write(draft, lines)
    print(f"remove-line: draft line {args.line}")
    return 0


def _field_insert_point(tree, slide, field_name):
    fld = slide.fields.get(field_name.lower())
    if not fld:
        return None
    # last non-blank body line, else the heading line
    end = fld.body_end if fld.body_end else fld.heading_line
    lines = tree["lines"]
    ins = end
    while ins > fld.heading_line and (ins - 1 < len(lines)) and lines[ins - 1].strip() == "":
        ins -= 1
    return ins  # 1-based line after which to insert


def cmd_append_line(args) -> int:
    draft = Path(args.draft)
    tree = L.parse_md_slides(str(draft))
    slide = _find_slide(tree, args.section, args.slide_title)
    if slide is None:
        print(f"failed: slide not found: {args.section} / {args.slide_title!r}", file=sys.stderr)
        return 2
    field = FIELD_ALIASES.get(args.field.lower())
    if not field or field not in slide.fields:
        print(f"failed: field {args.field!r} not in slide", file=sys.stderr)
        return 2
    ins = _field_insert_point(tree, slide, field)
    lines = list(tree["lines"])
    new_line = args.text
    if field == "content" and not re.match(r"^\s*(?:[-*+]\s+|>\s+|!\[|\|)", new_line):
        new_line = f"- {new_line}"
    if args.dry_run:
        print(f"[dry-run] append after line {ins}: {new_line!r}")
        return 0
    lines[ins:ins] = [new_line]
    _atomic_write(draft, lines)
    print(f"append-line: after draft line {ins} in {field}")
    return 0


def _copy_image(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = src.read_bytes()
    if not (dest.exists() and dest.read_bytes() == blob):
        dest.write_bytes(blob)


def cmd_add_image(args) -> int:
    draft = Path(args.draft)
    talk_root = draft.resolve().parent
    tree = L.parse_md_slides(str(draft))
    slide = _find_slide(tree, args.section, args.slide_title)
    if slide is None:
        print(f"failed: slide not found: {args.section} / {args.slide_title!r}", file=sys.stderr)
        return 2
    src = talk_root / args.src if not Path(args.src).is_absolute() else Path(args.src)
    if not src.is_file():
        print(f"failed: source image not found: {src}", file=sys.stderr)
        return 2
    dest_base = args.dest_basename or re.sub(r"^s\d+-", "", src.name)
    dest = talk_root / "images" / dest_base
    if any(im.basename == dest_base for im in slide.images):
        print(f"noop: image {dest_base} already referenced in slide")
        return 0
    ref = f"![{args.alt}](images/{dest_base})"
    ins = _field_insert_point(tree, slide, "content")
    if ins is None:
        print("failed: slide has no ### Content field", file=sys.stderr)
        return 2
    lines = list(tree["lines"])
    if args.dry_run:
        print(f"[dry-run] copy {src} → {dest}; insert {ref!r} after line {ins}")
        return 0
    _copy_image(src, dest)
    lines[ins:ins] = ["", ref]
    _atomic_write(draft, lines)
    print(f"add-image: {dest_base} → draft slide {args.section} \"{slide.title}\"")
    return 0


def cmd_replace_image(args) -> int:
    draft = Path(args.draft)
    talk_root = draft.resolve().parent
    src = talk_root / args.src if not Path(args.src).is_absolute() else Path(args.src)
    if not src.is_file():
        print(f"failed: source image not found: {src}", file=sys.stderr)
        return 2
    dest = talk_root / "images" / args.basename
    if args.dry_run:
        print(f"[dry-run] overwrite {dest} from {src}")
        return 0
    _copy_image(src, dest)
    print(f"replace-image: {args.basename} overwritten from deck")
    return 0


def cmd_retitle(args) -> int:
    draft = Path(args.draft)
    tree = L.parse_md_slides(str(draft))
    slide = _find_slide(tree, args.section, args.old_title)
    if slide is None:
        print(f"failed: slide not found for retitle: {args.section} / {args.old_title!r}", file=sys.stderr)
        return 2
    lines = list(tree["lines"])
    idx = slide.heading_line - 1
    num = f"{slide.slide_num}. " if slide.slide_num else ""
    new = f"## {num}{args.new_title}"
    if args.dry_run:
        print(f"[dry-run] retitle line {slide.heading_line}: {lines[idx]!r} → {new!r}")
        return 0
    lines[idx] = new
    _atomic_write(draft, lines)
    print(f"retitle: draft line {slide.heading_line}")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--diff", required=True)
    p.add_argument("--draft", required=True)
    p.add_argument("--format", choices=["json", "human"], default="human")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("apply-auto")
    p.add_argument("--diff", required=True)
    p.add_argument("--draft", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_apply_auto)

    p = sub.add_parser("replace-line")
    p.add_argument("--draft", required=True)
    p.add_argument("--line", type=int, required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--expect")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_replace_line)

    p = sub.add_parser("remove-line")
    p.add_argument("--draft", required=True)
    p.add_argument("--line", type=int, required=True)
    p.add_argument("--expect")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_remove_line)

    p = sub.add_parser("append-line")
    p.add_argument("--draft", required=True)
    p.add_argument("--section", required=True)
    p.add_argument("--slide-title", required=True)
    p.add_argument("--field", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_append_line)

    p = sub.add_parser("add-image")
    p.add_argument("--draft", required=True)
    p.add_argument("--section", required=True)
    p.add_argument("--slide-title", required=True)
    p.add_argument("--alt", required=True)
    p.add_argument("--src", required=True)
    p.add_argument("--dest-basename")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_add_image)

    p = sub.add_parser("replace-image")
    p.add_argument("--draft", required=True)
    p.add_argument("--basename", required=True)
    p.add_argument("--src", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_replace_image)

    p = sub.add_parser("retitle")
    p.add_argument("--draft", required=True)
    p.add_argument("--section", required=True)
    p.add_argument("--old-title", required=True)
    p.add_argument("--new-title", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_retitle)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
