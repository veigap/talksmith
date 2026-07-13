"""Audit that every `### Notes` block in `final.md` reaches a non-empty
notes pane on the corresponding slide of the rendered `.pptx`.

Why this exists:
    Speaker notes are load-bearing (the prose the slide replaces — see
    `${CLAUDE_PLUGIN_ROOT}/config/principles.md` → *Speaker notes are the
    talk*). The specs require the renderer to emit every `### Notes` block
    verbatim into the slide's notes pane (strict §15.5 rule 10 / §19.3
    stage 7; free-form §19), but until now nothing *enforced* it — a
    renderer that forgot the notes stage, or dropped a slide's notes,
    shipped silently because no audit and no visual-review rubric looks at
    the notes pane. This is the deterministic catch, mirroring
    `audits/block_coverage.py` for slide bodies: a build-time gate that fails
    the render when a source slide that carries notes lands with an empty
    notes pane.

What it does:
    Walks `final.md` per H2 (each H2 = one content slide) and records which
    slides carry a `### Notes` block with a non-empty body. Walks
    `final.pptx`, reads each slide's linked `notesSlide` part, and extracts
    the notes-body text (excluding the slide-number placeholder). Matches
    slides by normalized H2 title text (reusing `audit_block_coverage`'s
    slide/title/chrome machinery). Reports every source slide that *has*
    notes but whose rendered notes pane is empty as
    `[notes-drop] slide N "<H2>" — source has notes, render notes pane empty`
    and exits non-zero. Slides with no `### Notes` block are never flagged
    (no false positives).

Usage:
    python3 audits/notes_coverage.py <final.md> <final.pptx> [--json] [--warn-only]

Exit codes:
    0  every source slide with notes has a non-empty notes pane
    1  one or more notes drops; build should stop and re-render
    2  audit could not run (file missing, malformed)

CLI-safe; standard library only. Shares pptx helpers with audit_block_coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from block_coverage import (  # noqa: E402  (shared pptx machinery)
    NS,
    _slide_paths,
    _slide_rels,
    _normalize_title,
    _extract_title,
    _looks_like_agenda,
)


# --------------------------------------------------------------------------- #
# final.md parsing — which slides carry a non-empty `### Notes` block
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    has_notes: bool = False


def parse_final_md(path: str) -> list[SourceSlide]:
    lines = open(path, encoding="utf-8").read().splitlines()
    slides: list[SourceSlide] = []
    current: SourceSlide | None = None
    in_code = False
    in_notes = False

    # Sections skipped entirely (per convert.py — never become slides).
    SKIP_H1 = {"thesis", "open questions", "cut material"}
    in_skip_section = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        # H1 — section header (or skip marker); ends any current slide/notes.
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = re.sub(r"^\d+\.\s*", "", stripped[2:].strip().lower()).strip()
            in_skip_section = title in SKIP_H1
            current = None
            in_notes = False
            continue
        if in_skip_section:
            continue
        # H2 — new slide.
        if stripped.startswith("## "):
            title = re.sub(r"^(?:\d+\.\s*|Slide\s+\d+:\s*|\d+\s+—\s*)", "",
                           stripped[3:].strip())
            current = SourceSlide(h2_line=i, h2_title=title)
            slides.append(current)
            in_notes = False
            continue
        if current is None:
            continue
        # `### Notes` block start (convert.py normalizes `### Speaker notes` → `### Notes`).
        m = re.match(r"^#{3}\s+(.*)$", stripped)
        if m:
            in_notes = m.group(1).strip().lower() in ("notes", "speaker notes")
            continue
        # Any non-empty line inside the notes block marks the slide as carrying notes.
        if in_notes and stripped:
            current.has_notes = True

    return slides


# --------------------------------------------------------------------------- #
# final.pptx parsing — per-slide notes-pane text
# --------------------------------------------------------------------------- #

@dataclass
class RenderSlide:
    slide_num: int
    is_chrome: bool
    title_text: str
    notes_text: str = ""


def _notes_target(zf: zipfile.ZipFile, slide_path: str) -> str | None:
    """Package path of the notesSlide a slide's rels point to, if any.

    Rel targets are relative to the slide (e.g. `../notesSlides/notesSlide1.xml`);
    resolve against the slide's parent directory to a normalized package path
    like `ppt/notesSlides/notesSlide1.xml`.
    """
    parent = PurePosixPath(slide_path).parent          # ppt/slides
    for target in _slide_rels(zf, slide_path).values():
        if "notesSlide" in target:
            parts: list[str] = []
            for seg in (parent / target).parts:
                if seg == "..":
                    if parts:
                        parts.pop()
                elif seg != ".":
                    parts.append(seg)
            return "/".join(parts)
    return None


def _notes_text(zf: zipfile.ZipFile, notes_part: str) -> str:
    """Notes-body text of a notesSlide, excluding the slide-number placeholder."""
    if notes_part not in zf.namelist():
        return ""
    try:
        root = ET.fromstring(zf.read(notes_part))
    except (ET.ParseError, KeyError):
        return ""
    chunks: list[str] = []
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        ph = sp.find(f"{{{NS['p']}}}nvSpPr/{{{NS['p']}}}nvPr/{{{NS['p']}}}ph")
        if ph is not None and ph.get("type") == "sldNum":
            continue  # the "1", "2", … slide-number field, not real notes
        for t in sp.iter(f"{{{NS['a']}}}t"):
            if t.text:
                chunks.append(t.text)
    return "".join(chunks).strip()


def parse_pptx(path: str) -> list[RenderSlide]:
    out: list[RenderSlide] = []
    with zipfile.ZipFile(path) as zf:
        for idx, sp_path in enumerate(_slide_paths(zf), start=1):
            try:
                root = ET.fromstring(zf.read(sp_path))
            except (ET.ParseError, KeyError):
                continue
            chrome = (idx == 1) or _looks_like_agenda(root)
            title = "" if chrome else _extract_title(root)
            target = _notes_target(zf, sp_path)
            notes = _notes_text(zf, target) if target else ""
            out.append(RenderSlide(slide_num=idx, is_chrome=chrome,
                                   title_text=title, notes_text=notes))
    return out


# --------------------------------------------------------------------------- #
# reconciliation
# --------------------------------------------------------------------------- #

@dataclass
class Drop:
    slide_num: int
    h2_title: str

    def fmt(self) -> str:
        return (f"[notes-drop] slide {self.slide_num} \"{self.h2_title}\" — "
                f"source has notes, render notes pane empty")


@dataclass
class Unmatched:
    h2_line: int
    h2_title: str

    def fmt(self) -> str:
        return (f"[unmatched] line {self.h2_line} \"{self.h2_title}\" — "
                f"no rendered slide with matching title")


def reconcile(sources: list[SourceSlide],
              renders: list[RenderSlide]) -> tuple[list[Drop], list[Unmatched]]:
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
        if not s.has_notes:
            continue  # only slides that carry notes can drop them
        key = _normalize_title(s.h2_title)
        match = by_title.get(key)
        if match is None:
            cands = [r for r in by_title.values() if r.title_text and (
                _normalize_title(r.title_text).startswith(key[:20])
                or key.startswith(_normalize_title(r.title_text)[:20]))]
            if len(cands) == 1:
                match = cands[0]
        if match is None:
            unmatched.append(Unmatched(h2_line=s.h2_line, h2_title=s.h2_title))
            continue
        if not match.notes_text:
            drops.append(Drop(slide_num=match.slide_num, h2_title=s.h2_title))
    return drops, unmatched


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("final_md")
    p.add_argument("final_pptx")
    p.add_argument("--json", action="store_true", help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report drops but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    try:
        sources = parse_final_md(args.final_md)
    except (FileNotFoundError, OSError) as e:
        print(f"audit_notes_coverage: cannot read {args.final_md}: {e}", file=sys.stderr)
        return 2
    try:
        renders = parse_pptx(args.final_pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_notes_coverage: cannot read {args.final_pptx}: {e}", file=sys.stderr)
        return 2

    drops, unmatched = reconcile(sources, renders)
    with_notes = sum(1 for s in sources if s.has_notes)

    if args.json:
        print(json.dumps({
            "final_md": args.final_md,
            "final_pptx": args.final_pptx,
            "summary": {
                "source_slides": len(sources),
                "source_slides_with_notes": with_notes,
                "drops": len(drops),
                "unmatched": len(unmatched),
            },
            "drops": [asdict(d) for d in drops],
            "unmatched": [asdict(u) for u in unmatched],
        }, indent=2))
    else:
        if not drops and not unmatched:
            print(f"audit_notes_coverage: ok — {with_notes}/{len(sources)} source "
                  f"slides carry notes, 0 dropped")
        else:
            print(f"audit_notes_coverage: {len(drops)} notes-drop(s), "
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
