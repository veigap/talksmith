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
    there; html-strict has no `.pptx`.

Usage:
    python3 audits/icon_coverage.py <slide-model.json> <final.pptx> [--json] [--warn-only]

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
from block_coverage import (  # noqa: E402
    NS,
    _slide_paths,
    _normalize_title,
    _extract_title,
    _looks_like_agenda,
)

# Icon size band: Material-Symbols icons are placed at ~0.41–0.44 in (§7.2.1 / §17.3).
# Content images and the cover logo are much larger, so a picture ≤ this is an icon.
ICON_MAX_EMU = int(0.6 * 914400)


# --------------------------------------------------------------------------- #
# final.md — icons a slide should have
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    expected_icons: int = 0


def parse_model(path: str) -> list[SourceSlide]:
    """Icons a slide should carry, from `slide-model.json` (the template is given — no md
    parsing, no re-classification): one per card / row / item for the icon-bearing templates,
    one for a callout or single-point. Matched to the deck by normalized title."""
    import json
    model = json.loads(open(path, encoding="utf-8").read())
    out: list[SourceSlide] = []
    for idx, s in enumerate(model.get("slides", []), start=1):
        t = s.get("template", "")
        if t in ("concept-breakdown", "card-row", "content+cards+image"):
            n = len(s.get("cards", []))
        elif t == "icon-list":
            n = len(s.get("rows", []))
        elif t == "closing-cta":
            n = len(s.get("items", []))
        elif t in ("callout", "single-point"):
            n = 1
        else:
            n = 0
        title = s.get("title") or s.get("section") or ""
        out.append(SourceSlide(h2_line=idx, h2_title=title, expected_icons=n))
    return out


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
    p.add_argument("model_json", help="slide-model.json (the expected content)")
    p.add_argument("final_pptx")
    p.add_argument("--json", action="store_true")
    p.add_argument("--warn-only", action="store_true")
    args = p.parse_args(argv)
    try:
        sources = parse_model(args.model_json)
    except (FileNotFoundError, OSError, ValueError) as e:
        print(f"audit_icon_coverage: cannot read {args.model_json}: {e}", file=sys.stderr)
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
