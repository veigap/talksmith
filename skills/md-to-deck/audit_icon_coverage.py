"""Audit that a **strict** render actually placed the icons its slides call for.

Why this exists:
    Strict §7.2.1 concept-breakdown cards and §8 callouts each carry a small branded
    line-art icon (Material Symbols, fetched by name per §17). But the render fetches +
    embeds those icons by following prose — and it can silently *skip* that step: the deck
    renders as plain colored shapes + text, the layout log may even claim icons were used,
    and it slips through because none of the other six strict audits look at icons (they
    check palette, fonts, cover fidelity, layout fit, block coverage, notes). This is the
    deterministic catch: a strict deck whose concept/callout slides carry **zero** icon
    media fails the build, turning a silent skip into a hard failure.

What it does:
    From `final.md`, per H2 slide, counts the icons the slide *should* have:
      - a **concept-breakdown** shape (≥2 labeled items — `- **Label** …` / `#### Label` /
        `### Subhead` groups — and no source `![]()` image) → one icon per card;
      - each **callout** (single emoji-bold bullet / `> **bold**` / `> [!x]`) → one icon.
    From `final.pptx`, per slide, counts **small `<p:pic>`** shapes (≤ ~0.6 in — the icon
    size band; content images and the cover logo are larger and excluded). Matches slides by
    H2 title (reusing audit_block_coverage's machinery). A slide that should have icons but
    rendered **zero** is an `[icon-drop]`; exits non-zero.

    **Strict-only.** Free-form makes icons optional (its §3.2), so this audit does not apply
    there; preview has no `.pptx`.

Usage:
    python3 audit_icon_coverage.py <final.md> <final.pptx> [--json] [--warn-only]

Exit codes:
    0  every slide that should carry icons has at least one; nothing skipped wholesale
    1  one or more slides call for icons but rendered none; build should stop and re-render
    2  audit could not run (file missing, malformed)

CLI-safe; standard library only. Shares pptx machinery with audit_block_coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_block_coverage import (  # noqa: E402
    NS,
    EMOJI_CLASS,
    _slide_paths,
    _normalize_title,
    _extract_title,
    _looks_like_agenda,
    _is_callout_line,
)

# Icon size band: Material-Symbols icons are placed at ~0.41–0.44 in (§7.2.1 / §17.3).
# Content images and the cover logo are much larger, so a picture ≤ this is an icon.
ICON_MAX_EMU = int(0.6 * 914400)

_BOLD_ITEM_RE = re.compile(rf"^\s*[-*+]\s+(?:{EMOJI_CLASS}️?\s*)?\*\*[^*]+\*\*")
_H34_RE = re.compile(r"^#{3,4}\s+\S")
_IMG_RE = re.compile(r"!\[[^\]]*\]\(images/[^)]+\)")


# --------------------------------------------------------------------------- #
# final.md — icons a slide should have
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    labeled_items: int = 0
    callouts: int = 0
    images: int = 0

    @property
    def expected_icons(self) -> int:
        # concept-breakdown (≥2 labeled items, no source image) → one icon per card
        concept = self.labeled_items if (self.labeled_items >= 2 and self.images == 0) else 0
        return concept + self.callouts


def parse_final_md(path: str) -> list[SourceSlide]:
    lines = open(path, encoding="utf-8").read().splitlines()
    slides: list[SourceSlide] = []
    cur: SourceSlide | None = None
    in_code = False
    SKIP_H1 = {"thesis", "open questions", "cut material"}
    in_skip = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if s.startswith("# ") and not s.startswith("## "):
            in_skip = re.sub(r"^\d+\.\s*", "", s[2:].strip().lower()).strip() in SKIP_H1
            cur = None
            continue
        if in_skip:
            continue
        if s.startswith("## "):
            title = re.sub(r"^(?:\d+\.\s*|Slide\s+\d+:\s*|\d+\s+—\s*)", "", s[3:].strip())
            cur = SourceSlide(h2_line=i, h2_title=title)
            slides.append(cur)
            continue
        if cur is None:
            continue
        if _IMG_RE.search(line):
            cur.images += len(_IMG_RE.findall(line))
        if _is_callout_line(line):
            cur.callouts += 1
        elif _BOLD_ITEM_RE.match(line) or _H34_RE.match(line):
            cur.labeled_items += 1
    return slides


# --------------------------------------------------------------------------- #
# final.pptx — small icon pictures per slide
# --------------------------------------------------------------------------- #

@dataclass
class RenderSlide:
    slide_num: int
    is_chrome: bool
    title_text: str
    small_pics: int = 0


def parse_pptx(path: str) -> list[RenderSlide]:
    out: list[RenderSlide] = []
    with zipfile.ZipFile(path) as zf:
        for idx, sp_path in enumerate(_slide_paths(zf), 1):
            try:
                root = ET.fromstring(zf.read(sp_path))
            except (ET.ParseError, KeyError):
                continue
            chrome = (idx == 1) or _looks_like_agenda(root)
            title = "" if chrome else _extract_title(root)
            small = 0
            for pic in root.iter(f"{{{NS['p']}}}pic"):
                ext = pic.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}xfrm/{{{NS['a']}}}ext")
                if ext is None:
                    continue
                try:
                    cx, cy = int(ext.get("cx", "0")), int(ext.get("cy", "0"))
                except ValueError:
                    continue
                if 0 < cx <= ICON_MAX_EMU and 0 < cy <= ICON_MAX_EMU:
                    small += 1
            out.append(RenderSlide(slide_num=idx, is_chrome=chrome, title_text=title,
                                   small_pics=small))
    return out


# --------------------------------------------------------------------------- #
# reconcile
# --------------------------------------------------------------------------- #

@dataclass
class Drop:
    slide_num: int
    h2_title: str
    expected: int

    def fmt(self) -> str:
        return (f"[icon-drop] slide {self.slide_num} \"{self.h2_title}\" — "
                f"expects {self.expected} icon(s) (concept cards / callouts), render has 0")


@dataclass
class Unmatched:
    h2_line: int
    h2_title: str

    def fmt(self) -> str:
        return (f"[unmatched] line {self.h2_line} \"{self.h2_title}\" — "
                f"no rendered slide with matching title")


def reconcile(sources, renders):
    by_title = {}
    for r in renders:
        if r.is_chrome or not r.title_text:
            continue
        k = _normalize_title(r.title_text)
        if k and k not in by_title:
            by_title[k] = r
    drops, unmatched = [], []
    for s in sources:
        if s.expected_icons <= 0:
            continue
        k = _normalize_title(s.h2_title)
        m = by_title.get(k)
        if m is None:
            cands = [r for r in by_title.values() if r.title_text and (
                _normalize_title(r.title_text).startswith(k[:20])
                or k.startswith(_normalize_title(r.title_text)[:20]))]
            if len(cands) == 1:
                m = cands[0]
        if m is None:
            unmatched.append(Unmatched(s.h2_line, s.h2_title))
            continue
        if m.small_pics == 0:
            drops.append(Drop(m.slide_num, s.h2_title, s.expected_icons))
    return drops, unmatched


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("final_md")
    p.add_argument("final_pptx")
    p.add_argument("--json", action="store_true")
    p.add_argument("--warn-only", action="store_true")
    args = p.parse_args(argv)
    try:
        sources = parse_final_md(args.final_md)
    except (FileNotFoundError, OSError) as e:
        print(f"audit_icon_coverage: cannot read {args.final_md}: {e}", file=sys.stderr)
        return 2
    try:
        renders = parse_pptx(args.final_pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_icon_coverage: cannot read {args.final_pptx}: {e}", file=sys.stderr)
        return 2
    drops, unmatched = reconcile(sources, renders)
    need = sum(1 for s in sources if s.expected_icons > 0)
    if args.json:
        print(json.dumps({
            "summary": {"slides_needing_icons": need, "drops": len(drops),
                        "unmatched": len(unmatched)},
            "drops": [asdict(d) for d in drops],
            "unmatched": [asdict(u) for u in unmatched],
        }, indent=2))
    else:
        if not drops and not unmatched:
            print(f"audit_icon_coverage: ok — {need} slide(s) call for icons, none skipped")
        else:
            print(f"audit_icon_coverage: {len(drops)} icon-drop(s), "
                  f"{len(unmatched)} unmatched")
            for d in drops:
                print("  " + d.fmt())
            for u in unmatched:
                print("  " + u.fmt())
    if args.warn_only:
        return 0
    return 1 if drops else 0


if __name__ == "__main__":
    sys.exit(main())
