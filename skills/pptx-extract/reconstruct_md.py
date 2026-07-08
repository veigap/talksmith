#!/usr/bin/env python3
"""reconstruct_md.py — rebuild finalpptx.md in the canonical draft.md shape from
a slide inventory. Design B of the Talksmith reverse pipeline.

Consumes the inventory produced by pptx_inventory.py (never re-parses the .pptx).
Skips cover/agenda/divider slides; groups content slides into `# <k>. <Section>`
by divider boundaries; renumbers `## <M>.` within each section; fills
`### Content`, `### Sources` (stub), `### Speaker notes`, and image refs.

What round-trips faithfully: section structure, slide titles, bullets/paragraphs/
tables, speaker notes, byte-identical generated images.

What is inherently lossy (emitted as a stub + `<!-- reconstruct: ... -->` marker
for the Editor to resolve): `# Thesis` and `### Sources` (both dropped by the
forward convert.py), callout source-form, card/icon-list layout, multi-column
reading order.

Usage:
  python3 reconstruct_md.py <inventory.json> --talk <talk_root> [-o <finalpptx.md>]

Exit codes:
  0  finalpptx.md written
  2  could not run (bad inventory, missing talk root)

stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _emit_frontmatter(inv: dict) -> list[str]:
    cover_title = ""
    for s in inv["slides"]:
        if s["classification"] == "cover" and s["title"]:
            cover_title = s["title"]
            break
    return [
        "---",
        f"presentation: {cover_title}" if cover_title
        else "presentation: <!-- reconstruct: presentation title not recovered from deck -->",
        "class:",
        "research: research/corpus/",
        "description: Slides are grouped into Sections. Each Section contains one or more Slides.",
        "presenter:",
        "audience:",
        "duration:",
        "date:",
        "---",
        "",
    ]


def _emit_body_block(block: dict) -> list[str]:
    role = block.get("role")
    if role == "bullets":
        return [f"- {item}" for item in block.get("items", [])]
    if role == "table":
        rows = block.get("rows", [])
        if not rows:
            return []
        out = ["| " + " | ".join(rows[0]) + " |",
               "| " + " | ".join("---" for _ in rows[0]) + " |"]
        for r in rows[1:]:
            out.append("| " + " | ".join(r) + " |")
        return out
    if role == "callout":
        text = block.get("text", "").replace("\n", " ")
        return [f"> {text}",
                "<!-- reconstruct: callout source-form inferred (blockquote) -->"]
    # paragraph
    return block.get("text", "").split("\n")


def _emit_content(slide: dict) -> list[str]:
    lines: list[str] = ["### Content", ""]
    has_card = False
    for block in slide["body"]:
        block_lines = _emit_body_block(block)
        lines.extend(block_lines)
        lines.append("")
        if block.get("role") == "paragraph" and len(slide["body"]) >= 3:
            has_card = True
    # image refs — every content image points at its reconcile/staging/ copy.
    # pptx-diff decides whether each staged image is unchanged / modified / added
    # by slot alignment (byte-hash fast-path + positional match); reconstruct
    # does not itself resolve image identity.
    for im in slide["images"]:
        if im["cls"] != "content":
            continue
        alt = slide["title"] or "diagram"
        lines.append(f"![{alt}]({im['staged_path']})")
        lines.append("")
    if has_card and len(slide["body"]) >= 4:
        lines.append("<!-- reconstruct: multiple text blocks — card/icon-list layout may have been flattened to prose -->")
        lines.append("")
    return lines


def _emit_slide(slide: dict, slide_num: int) -> list[str]:
    title = slide["title"] or "<!-- reconstruct: slide title not recovered -->"
    lines = [f"## {slide_num}. {title}", ""]
    lines += _emit_content(slide)
    lines += ["### Sources", "",
              "<!-- reconstruct: Sources dropped during pptx render; restore from draft.md if needed -->", ""]
    notes = slide.get("notes") or ""
    lines += ["### Speaker notes", ""]
    if notes:
        lines += notes.split("\n") + [""]
    else:
        lines += [""]
    comments = slide.get("comments") or []
    if comments:
        lines += ["### Reviewer comments", ""]
        for c in comments:
            who = c.get("author") or "(unknown)"
            when = c.get("created") or ""
            kind = c.get("kind", "")
            hdr = f"- **{who}**"
            if when:
                hdr += f" · {when}"
            if kind == "threaded":
                hdr += " · threaded"
            lines.append(hdr)
            for tl in (c.get("text") or "").split("\n"):
                lines.append(f"  > {tl}")
        lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def reconstruct(inv: dict) -> str:
    lines: list[str] = []
    lines += _emit_frontmatter(inv)

    lines += ["# Thesis", "",
              "<!-- reconstruct: Thesis is not present in the deck (dropped by the forward render); restore from draft.md -->",
              "", "---", ""]

    section_names = inv.get("section_names") or []
    lines += ["# Agenda", ""]
    if section_names:
        lines += ["**Sections (in delivery order):**", ""]
        lines += [f"- {i}. {name}" for i, name in enumerate(section_names, 1)]
        lines += [""]
    lines += ["---", ""]

    # Group content slides into sections by section_index (divider boundaries),
    # preserving deck order.
    content = [s for s in inv["slides"] if s["classification"] == "content"]
    # Determine ordered section indices as they appear.
    order_seen: list[int] = []
    for s in content:
        si = s.get("section_index")
        if si is None:
            si = 0
        if si not in order_seen:
            order_seen.append(si)

    for si in order_seen:
        sec_slides = [s for s in content if (s.get("section_index") or 0) == si]
        if not sec_slides:
            continue
        name = None
        if si and section_names and 1 <= si <= len(section_names):
            name = section_names[si - 1]
        if not name:
            name = sec_slides[0].get("section_name") or f"Section {si or '?'}"
        heading_num = si if si else (order_seen.index(si) + 1)
        lines += [f"# {heading_num}. {name}", "",
                  "**Goal of this section:**", "", "---", ""]
        for m, s in enumerate(sec_slides, start=1):
            lines += _emit_slide(s, m)

    lines += ["# Open questions", "", "# Cut material", ""]
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inventory")
    ap.add_argument("--talk", required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("-o", "--output", help="default: <talk>/reconcile/finalpptx.md")
    args = ap.parse_args(argv)

    talk_root = Path(args.talk)
    if not talk_root.is_dir():
        print(f"failed: talk root not found: {talk_root}", file=sys.stderr)
        return 2
    try:
        inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"failed: cannot read inventory {args.inventory}: {e}", file=sys.stderr)
        return 2

    md = reconstruct(inv)
    out_path = Path(args.output) if args.output else talk_root / "reconcile" / "finalpptx.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    n_sections = len(inv.get("section_names") or [])
    n_content = sum(1 for s in inv["slides"] if s["classification"] == "content")
    n_markers = md.count("<!-- reconstruct:")
    n_staged = inv["summary"].get("images_staged", 0)
    print(f"reconstruct: {n_content} content slides across {n_sections} sections "
          f"→ {out_path} ({n_markers} reconstruct markers, {n_staged} staged image(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
