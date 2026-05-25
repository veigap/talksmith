"""Audit that every load-bearing block in `final.md` appears as a
corresponding shape in the rendered `final.pptx`.

Why this exists:
    Renderers that lay out content top-to-bottom can run out of
    vertical room on a busy slide and silently skip the trailing
    block from emission (e.g. a callout bullet whose preceding table
    consumed the body area, pushing it past `effective_bottom`).
    The visual-review rubric in `CLAUDE.md` → Step 8 does not ask
    "is every source block present in the render," so a silent drop
    produces no rubric hit — the slide ships missing content. This
    audit is the deterministic catch: a build-time gate that fails
    the render before any human or LLM visual review begins.

What it does:
    Walks `final.md` per H2 (each H2 = one content slide), counts
    load-bearing block types per slide. Walks `final.pptx` per slide,
    counts the shapes that correspond to each block type. Matches
    slides by H2 title text (ordinal matching breaks because section
    dividers shift counts). Reports drops as `[block-drop]: slide N
    "<H2>" — source has X <type>, render has Y` and exits non-zero.

    Block types audited (the high-value drops):

      callout — single-bullet `- <emoji> **<bold>:** …`, blockquote
                `> **<bold>** …`, or `> [!callout]` admonition. In
                render: <p:sp> with solidFill #F7BBC1 (pink, §8.1) or
                #B8E6F5 (blue, §8.2).
      image   — Markdown `![alt](images/<path>)`. In render: <p:pic>
                shape, excluding well-known icon paths (cover logo
                image-1-*.png, section-pill icons) — heuristic count.

    Block types NOT audited:

      paragraph, bullet_list (≥3 items), numbered_list, table, code,
      blockquote. Tables and code surfaces are bulky enough that
      silent drop is implausible; paragraphs and lists are hard to
      differentiate reliably in OOXML without false positives. The
      reported failure mode is callouts and images — extend later
      when a new drop class surfaces.

    Slide matching:
      Normalize title text (lowercase, strip punctuation, collapse
      whitespace) and compare on the first 40 chars. Unmatched H2 =
      `[unmatched]` warning. Cover (slide 1) and agenda re-emits
      (slides with ≥4 small ellipses on the agenda spine) are excluded
      from matching since they have no source H2.

Usage:
    python3 audit_block_coverage.py <final.md> <final.pptx> [--json] [--warn-only]

Exit codes:
    0  no drops detected
    1  one or more drops; build should stop and re-render
    2  audit could not run (file missing, malformed)

CLI-safe; standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, asdict, field
from pathlib import PurePosixPath

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Emoji ranges from config/pptx-prompt.md §17.7 detection ranges.
EMOJI_CLASS = r"[\U0001F300-\U0001FAFF☀-➿⌀-⏿]"

# Callout colors (case-insensitive); see config/pptx-prompt.md §8.
CALLOUT_FILLS = {"F7BBC1", "B8E6F5"}

# Known non-content image paths to exclude from the per-slide <p:pic> count:
# - cover logo ppt/media/image-1-*.png (institution mark, slide 1 only)
# - section-pill icons (small icon-*.png/svg in branded library)
ICON_PATH_RE = re.compile(r"(/icon-[\w-]+\.(?:png|svg)|image-1-\d+\.png)$", re.I)


# --------------------------------------------------------------------------- #
# final.md parsing
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    callouts: int = 0
    images: int = 0
    callout_lines: list[int] = field(default_factory=list)
    image_lines: list[int] = field(default_factory=list)


def _is_callout_line(line: str) -> bool:
    """Detect the three callout shapes used in Talksmith final.md."""
    s = line.lstrip()
    # 1. single-bullet `- <emoji> **<bold>** …` (a 1-item bullet with
    #    emoji + bold lead reads as emphasis, not enumeration —
    #    renderer must promote to callout per §15; colon may be inside
    #    the bold or absent)
    if re.match(rf"-\s+{EMOJI_CLASS}\s+\*\*[^*]+\*\*", s):
        return True
    # 2. blockquote `> **<bold>** …`
    if re.match(r">\s+\*\*[^*]+\*\*", s):
        return True
    # 3. admonition `> [!callout]` / `> [!note]` / `> [!warning]` …
    if re.match(r">\s+\[!\w+\]", s):
        return True
    return False


def parse_final_md(path: str) -> list[SourceSlide]:
    lines = open(path, encoding="utf-8").read().splitlines()
    slides: list[SourceSlide] = []
    current: SourceSlide | None = None
    in_code = False

    # Sections to skip entirely (per convert.py — these never become slides).
    SKIP_H1 = {"thesis", "open questions", "cut material"}
    in_skip_section = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        # H1 — section header (or skip-section marker)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip().lower()
            # Strip leading numeric prefix
            title = re.sub(r"^\d+\.\s*", "", title).strip()
            in_skip_section = title in SKIP_H1
            current = None
            continue
        if in_skip_section:
            continue
        # Fenced code toggle
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        # H2 — slide
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            # Strip the `N. ` / `Slide N: ` prefix
            title = re.sub(r"^(?:\d+\.\s*|Slide\s+\d+:\s*|\d+\s+—\s*)", "", title)
            current = SourceSlide(h2_line=i, h2_title=title)
            slides.append(current)
            continue
        if current is None:
            continue
        # Image refs (count one per line occurrence)
        for _ in re.finditer(r"!\[[^\]]*\]\(images/[^)]+\)", line):
            current.images += 1
            current.image_lines.append(i)
        # Callout detection
        if _is_callout_line(line):
            current.callouts += 1
            current.callout_lines.append(i)

    return slides


# --------------------------------------------------------------------------- #
# final.pptx parsing
# --------------------------------------------------------------------------- #

@dataclass
class RenderSlide:
    slide_num: int               # ordinal in deck (1-based)
    is_chrome: bool              # cover / agenda / divider — excluded from matching
    title_text: str              # extracted from the title shape (empty if chrome)
    pink_callouts: int = 0
    blue_callouts: int = 0
    pics: int = 0
    pic_paths: list[str] = field(default_factory=list)


def _slide_paths(zf: zipfile.ZipFile) -> list[str]:
    return sorted(
        (n for n in zf.namelist()
         if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
        key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)),
    )


def _slide_rels(zf: zipfile.ZipFile, slide_path: str) -> dict[str, str]:
    p = PurePosixPath(slide_path)
    rels_path = str(p.parent / "_rels" / (p.name + ".rels"))
    if rels_path not in zf.namelist():
        return {}
    out: dict[str, str] = {}
    try:
        root = ET.fromstring(zf.read(rels_path))
    except (ET.ParseError, KeyError):
        return {}
    for rel in root.findall(f"{{{NS['rel']}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target", "")
        if rid and target:
            out[rid] = target
    return out


def _normalize_title(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:40]


def _looks_like_agenda(root: ET.Element) -> bool:
    """Cover (slide 1) and agenda re-emits both feature ≥4 small ellipse
    shapes (the agenda dots). The cover does not; only the agenda chrome
    does. Slide 1 is handled by ordinal."""
    ellipses = 0
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        prst = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}prstGeom")
        if prst is not None and prst.get("prst") == "ellipse":
            ellipses += 1
    return ellipses >= 4


def _extract_title(root: ET.Element) -> str:
    """Pick the first text shape whose primary run is Roboto Mono Medium
    at sz ≥ 1700 and that is not the section pill (section pill text is
    sz ≤ 900). Returns empty string if no title-shaped text found."""
    candidates: list[tuple[int, str]] = []  # (sz, text)
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        txbody = sp.find(f"{{{NS['p']}}}txBody")
        if txbody is None:
            continue
        first_run = next(txbody.iter(f"{{{NS['a']}}}r"), None)
        if first_run is None:
            continue
        rpr = first_run.find(f"{{{NS['a']}}}rPr")
        sz = int(rpr.get("sz", "0")) if rpr is not None and rpr.get("sz") else 0
        latin = rpr.find(f"{{{NS['a']}}}latin") if rpr is not None else None
        font = latin.get("typeface", "") if latin is not None else ""
        if sz < 1700 or "Roboto Mono" not in font:
            continue
        # Concatenate text runs in this shape
        text = "".join(
            t.text or "" for t in txbody.iter(f"{{{NS['a']}}}t")
        ).strip()
        if text:
            candidates.append((sz, text))
    if not candidates:
        return ""
    # Largest sz wins (titles are bigger than headings)
    candidates.sort(reverse=True)
    return candidates[0][1]


def _shape_solid_fill(sp: ET.Element) -> str | None:
    """Return uppercase 6-char hex of the shape's solid fill, or None."""
    sf = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}solidFill")
    if sf is None:
        return None
    clr = sf.find(f"{{{NS['a']}}}srgbClr")
    if clr is None:
        return None
    v = clr.get("val", "")
    return v.upper() if len(v) == 6 else None


def parse_pptx(path: str) -> list[RenderSlide]:
    out: list[RenderSlide] = []
    with zipfile.ZipFile(path) as zf:
        slide_paths = _slide_paths(zf)
        for idx, sp_path in enumerate(slide_paths, start=1):
            try:
                root = ET.fromstring(zf.read(sp_path))
            except (ET.ParseError, KeyError):
                continue
            is_cover = (idx == 1)
            is_agenda = _looks_like_agenda(root)
            chrome = is_cover or is_agenda
            title = "" if chrome else _extract_title(root)
            slide = RenderSlide(slide_num=idx, is_chrome=chrome, title_text=title)
            if not chrome:
                # Count callouts by fill color
                for sp_el in root.iter(f"{{{NS['p']}}}sp"):
                    fill = _shape_solid_fill(sp_el)
                    if fill == "F7BBC1":
                        slide.pink_callouts += 1
                    elif fill == "B8E6F5":
                        slide.blue_callouts += 1
                # Count pics, excluding icon library
                rels = _slide_rels(zf, sp_path)
                for pic in root.iter(f"{{{NS['p']}}}pic"):
                    blip = pic.find(
                        f"{{{NS['p']}}}blipFill/{{{NS['a']}}}blip"
                    )
                    rid = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
                    target = rels.get(rid, "") if rid else ""
                    if ICON_PATH_RE.search(target):
                        continue  # icon — not content
                    slide.pics += 1
                    slide.pic_paths.append(target)
            out.append(slide)
    return out


# --------------------------------------------------------------------------- #
# reconciliation
# --------------------------------------------------------------------------- #

@dataclass
class Drop:
    slide_num: int
    h2_title: str
    block_type: str
    source_count: int
    render_count: int
    note: str = ""

    def fmt(self) -> str:
        return (
            f"[block-drop] slide {self.slide_num} \"{self.h2_title}\" — "
            f"source has {self.source_count} {self.block_type}, "
            f"render has {self.render_count}"
            + (f" — {self.note}" if self.note else "")
        )


@dataclass
class Unmatched:
    h2_line: int
    h2_title: str

    def fmt(self) -> str:
        return f"[unmatched] line {self.h2_line} \"{self.h2_title}\" — no rendered slide with matching title"


def reconcile(
    sources: list[SourceSlide], renders: list[RenderSlide]
) -> tuple[list[Drop], list[Unmatched]]:
    # Build index of render content slides by normalized title prefix.
    by_title: dict[str, RenderSlide] = {}
    for r in renders:
        if r.is_chrome or not r.title_text:
            continue
        key = _normalize_title(r.title_text)
        if key and key not in by_title:
            by_title[key] = r

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    for s in sources:
        key = _normalize_title(s.h2_title)
        match = by_title.get(key)
        if match is None:
            # Try a looser fallback: any render whose title starts with key,
            # or key starts with render title (handles truncation either side)
            cands = [
                r for r in by_title.values()
                if r.title_text and (
                    _normalize_title(r.title_text).startswith(key[:20])
                    or key.startswith(_normalize_title(r.title_text)[:20])
                )
            ]
            if len(cands) == 1:
                match = cands[0]
        if match is None:
            unmatched.append(Unmatched(h2_line=s.h2_line, h2_title=s.h2_title))
            continue
        rendered_callouts = match.pink_callouts + match.blue_callouts
        if s.callouts > rendered_callouts:
            drops.append(Drop(
                slide_num=match.slide_num,
                h2_title=s.h2_title,
                block_type="callout(s)",
                source_count=s.callouts,
                render_count=rendered_callouts,
                note=f"source lines {s.callout_lines}",
            ))
        if s.images > match.pics:
            drops.append(Drop(
                slide_num=match.slide_num,
                h2_title=s.h2_title,
                block_type="image(s)",
                source_count=s.images,
                render_count=match.pics,
                note=f"source lines {s.image_lines}; rendered pics: {match.pic_paths}",
            ))
    return drops, unmatched


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("final_md")
    p.add_argument("final_pptx")
    p.add_argument("--json", action="store_true",
                   help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report drops but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    try:
        sources = parse_final_md(args.final_md)
    except (FileNotFoundError, OSError) as e:
        print(f"audit_block_coverage: cannot read {args.final_md}: {e}",
              file=sys.stderr)
        return 2
    try:
        renders = parse_pptx(args.final_pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_block_coverage: cannot read {args.final_pptx}: {e}",
              file=sys.stderr)
        return 2

    drops, unmatched = reconcile(sources, renders)

    if args.json:
        print(json.dumps({
            "final_md": args.final_md,
            "final_pptx": args.final_pptx,
            "summary": {
                "source_slides": len(sources),
                "render_slides": len(renders),
                "render_content_slides": sum(1 for r in renders if not r.is_chrome),
                "drops": len(drops),
                "unmatched": len(unmatched),
            },
            "drops": [asdict(d) for d in drops],
            "unmatched": [asdict(u) for u in unmatched],
            "sources": [asdict(s) for s in sources],
            "renders": [asdict(r) for r in renders],
        }, indent=2))
    else:
        n_content = sum(1 for r in renders if not r.is_chrome)
        m_blocks = sum(s.callouts + s.images for s in sources)
        if not drops and not unmatched:
            print(f"audit_block_coverage: ok — {len(sources)} source slides, "
                  f"{n_content} render content slides, {m_blocks} load-bearing "
                  f"blocks, 0 dropped")
        else:
            print(f"audit_block_coverage: {len(drops)} drop(s), "
                  f"{len(unmatched)} unmatched source slide(s)")
            for d in drops:
                print("  " + d.fmt())
            for u in unmatched:
                print("  " + u.fmt())

    if args.warn_only:
        return 0
    return 1 if drops else 0


if __name__ == "__main__":
    sys.exit(main())
