"""Audit that a slide's load-bearing blocks survive the two steps that can drop them:
`final.md` → `slide-model.json` (FILL) and `slide-model.json` → `final.pptx` (RENDER).

Why this exists:
    Renderers that lay out content top-to-bottom can run out of vertical room on a busy slide and
    silently skip the trailing block (e.g. a callout whose preceding table consumed the body area).
    The visual-review rubric in `${CLAUDE_PLUGIN_ROOT}/orchestrator.md` → Step 8 does not ask "is
    every source block present in the render," so a silent drop produces no rubric hit — the slide
    ships missing content. This audit is the deterministic catch, a build-time gate that fails the
    render before any human or LLM visual review begins.

    The same drop happens one step earlier, in FILL, and used to be invisible here: this audit
    required a `.pptx`, so an `html-strict` deck — which never produces one — ran it never. Hence
    the two modes below; the source-stage one is format-independent and guards every mode.

Two modes:

  **Source stage** (`--source final.md`, no `.pptx` needed) — every callout block authored in
  `final.md` must land somewhere in that slide's model entry: a `callout`-template slide, a
  `callout` field, or a `highlights` entry (the schema's *Never drop content* rule). Runs on the
  model alone, so it guards `html-strict` too. Prose coverage is `audits/text_coverage.py`'s
  question and image refs are `audits/image_coverage.py`'s; this one owns callouts.

  **Render stage** (`<final.pptx>`) — every block the model carries reached the deck. Counted:

      callout — in the model, a `callout`-template slide. In the render, a <p:sp> with solidFill
                #F7BBC1 (pink, §8.1) or #B8E6F5 (blue, §8.2).
      image   — in the model, `image` + `images[]` + each `figures[].image`. In the render, a
                <p:pic> shape, excluding well-known icon paths (cover logo image-1-*.png,
                section-pill icons) — heuristic count.

    Not counted: paragraph, bullet_list, numbered_list, table, code, blockquote. Tables and code
    surfaces are bulky enough that silent drop is implausible; paragraphs and lists are hard to
    differentiate reliably in OOXML without false positives.

  Both modes report as `[block-drop] slide N "<title>" — source has X <type>, render has Y` and
  exit non-zero.

Slide matching:
    Normalize title text (strip a leading `3.` locator, lowercase, strip punctuation, collapse
    whitespace) and compare on the first 40 chars. Unmatched = `[unmatched]` warning. Cover
    (slide 1) and agenda re-emits (slides with >=4 small ellipses on the agenda spine) are excluded
    from matching since they have no source title.

Usage:
    python3 audits/block_coverage.py <slide-model.json> [final.pptx] [--source final.md]
                                     [--json] [--warn-only]

    With neither a `.pptx` nor a resolvable `--source`, there is nothing to compare the model
    against and the audit exits 2. `--source` is auto-resolved from the model's `_source` stamp
    (written by `model_freshness.py stamp`) when the file sits beside the Talk root.

Exit codes:
    0  no drops detected
    1  one or more drops; build should stop and re-render
    2  audit could not run (file missing, malformed, nothing to compare against)

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
from pathlib import Path, PurePosixPath

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Emoji ranges from ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md §17.7 detection ranges.
EMOJI_CLASS = r"[\U0001F300-\U0001FAFF☀-➿⌀-⏿]"

# Callout colors (case-insensitive); see ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md §8.
CALLOUT_FILLS = {"F7BBC1", "B8E6F5"}

# Known non-content image paths to exclude from the per-slide <p:pic> count:
# - cover logo ppt/media/image-1-*.png (institution mark, slide 1 only)
# - section-pill icons (small icon-*.png/svg in branded library)
ICON_PATH_RE = re.compile(r"(/icon-[\w-]+\.(?:png|svg)|image-1-\d+\.png)$", re.I)

_HEADING_NUM = re.compile(r"^\s*\d+[.)]\s*")

# The three ways a callout is authored in `final.md` (schemas/draft.md; strict §8).
_CALLOUT_ADMONITION = re.compile(r"^\s*>\s*\[!\w+\]")
_CALLOUT_QUOTE_BOLD = re.compile(r"^\s*>\s*\*\*[^*]+\*\*")
_CALLOUT_BULLET = re.compile(rf"^\s*[-*+]\s+{EMOJI_CLASS}\s*\*\*[^*]+\*\*")
_NONSLIDE_HEADING = re.compile(r"^#\s+(Cut material|Open questions)\b", re.IGNORECASE)
# H3 blocks of a slide whose body is not slide face (schemas/draft.md → slide anatomy).
_SKIP_H3 = ("sources", "presenter feedback", "speaker notes")


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


def parse_model(path: str) -> list[SourceSlide]:
    """Expected callout/image blocks per slide, read straight from `slide-model.json` — the
    structured model already enumerates them, so there is no markdown to parse. Images = an
    `image` field + `images[]` + each `figures[].image`; a callout block = a `callout`-template
    slide. Matched to the deck by normalized title (its `title`, or `section` for dividers)."""
    import json
    model = json.loads(open(path, encoding="utf-8").read())
    slides: list[SourceSlide] = []
    for idx, s in enumerate(model.get("slides", []), start=1):
        images = (1 if s.get("image") else 0) + len(s.get("images", []))
        images += sum(1 for f in s.get("figures", []) if f.get("image"))
        callouts = 1 if s.get("template") == "callout" else 0
        title = s.get("title") or s.get("section") or ""
        slides.append(SourceSlide(h2_line=idx, h2_title=title, callouts=callouts, images=images))
    return slides


# --------------------------------------------------------------------------- #
# final.md parsing — the source stage (no .pptx needed)
# --------------------------------------------------------------------------- #

@dataclass
class MdSlide:
    """One `##` slide of `final.md`, with the callout blocks its author wrote."""
    line: int
    title: str
    callouts: int = 0
    callout_lines: list[int] = field(default_factory=list)


def parse_source_md(path: str) -> list[MdSlide]:
    """Callout blocks per slide of `final.md`.

    Skipped: fenced code, `# Cut material` / `# Open questions`, and the `### Sources`,
    `### Presenter feedback` and `### Speaker notes` sub-blocks — a callout quoted in the notes is
    prose the presenter says, not a block the slide owes the audience.
    """
    text = open(path, encoding="utf-8").read()
    out: list[MdSlide] = []
    cur: MdSlide | None = None
    in_fence = skip = False
    for i, raw in enumerate(text.split("\n"), start=1):
        if _NONSLIDE_HEADING.match(raw):
            break
        if re.match(r"^\s*(?:```|~~~)", raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw.startswith("## ") or raw.startswith("# "):
            title = _HEADING_NUM.sub("", raw.split(" ", 1)[1].strip()) if " " in raw else ""
            cur = MdSlide(line=i, title=title)
            out.append(cur)
            skip = False
            continue
        if raw.startswith("### "):
            head = re.sub(r"[^\w\s]", "", raw[4:].strip().lower()).strip()
            skip = head in _SKIP_H3
            continue
        if skip or cur is None:
            continue
        if (_CALLOUT_ADMONITION.match(raw) or _CALLOUT_QUOTE_BOLD.match(raw)
                or _CALLOUT_BULLET.match(raw)):
            cur.callouts += 1
            cur.callout_lines.append(i)
    return out


def model_callout_slots(path: str) -> list[tuple[str, int]]:
    """(title, callout-shaped landing places) per model slide.

    A source callout may legitimately land as a `callout`-template slide, a `callout` field, or a
    `highlights` entry — the schema lets the fill route an aside either way, so all three count.
    """
    model = json.loads(open(path, encoding="utf-8").read())
    out: list[tuple[str, int]] = []
    for sl in model.get("slides", []):
        slots = 1 if (sl.get("template") == "callout" or sl.get("callout")) else 0
        slots += len(sl.get("highlights") or [])
        out.append((sl.get("title") or sl.get("section") or "", slots))
    return out


def reconcile_source(md: list[MdSlide],
                     slots: list[tuple[str, int]]) -> tuple[list[Drop], list[Unmatched]]:
    by_title: dict[str, tuple[int, str, int]] = {}
    for idx, (title, n) in enumerate(slots, start=1):
        key = _normalize_title(title)
        if key and key not in by_title:
            by_title[key] = (idx, title, n)

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    for m in md:
        if not m.callouts:
            continue                      # only a slide that authored one can drop one
        key = _normalize_title(m.title)
        hit = by_title.get(key)
        if hit is None:
            cands = [v for k, v in by_title.items()
                     if k.startswith(key[:20]) or key.startswith(k[:20])]
            if len(cands) == 1:
                hit = cands[0]
        if hit is None:
            unmatched.append(Unmatched(h2_line=m.line, h2_title=m.title))
            continue
        idx, _title, n = hit
        if m.callouts > n:
            drops.append(Drop(
                slide_num=idx, h2_title=m.title, block_type="callout(s)",
                source_count=m.callouts, render_count=n, target="model",
                note=f"final.md lines {m.callout_lines}; the model gives this slide "
                     f"{n} callout/highlights slot(s)",
            ))
    return drops, unmatched


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
    # Source headings carry a locator (`## 3. Título`); model titles do not. The number is
    # addressing, not content — strip it on both sides or every numbered slide reads unmatched.
    s = _HEADING_NUM.sub("", s.strip())
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


# Fonts a title run may use. Historically the reference deck used Roboto Mono
# Medium; since the Roboto→Helvetica migration (0.10.3) generated decks title in
# Helvetica/Arial Bold. Accept any of them so title extraction (and thus the
# title-matched block/notes audits) works across both eras. The sz ≥ 1700 floor
# already excludes section pills (≤900) and card headings (~1350).
TITLE_FONTS = ("Roboto Mono", "Helvetica", "Arial")


def _extract_title(root: ET.Element) -> str:
    """Pick the largest text shape (sz ≥ 1700) whose run uses a title font,
    excluding the section pill (≤ 900). Empty string if none found."""
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
        if sz < 1700 or not any(tf in font for tf in TITLE_FONTS):
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
    target: str = "render"        # what the source was compared against: "model" | "render"

    def fmt(self) -> str:
        return (
            f"[block-drop] slide {self.slide_num} \"{self.h2_title}\" — "
            f"source has {self.source_count} {self.block_type}, "
            f"{self.target} has {self.render_count}"
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

def resolve_source(model_json: str, given: str | None) -> str | None:
    """The `final.md` to audit against: what was passed, else the model's `_source` stamp.

    `model_freshness.py stamp` records the source *name* next to its digest, and the model lives
    at `<talk>/output/slide-model.json` — so the stamp plus the layout is enough to find the file
    without the caller repeating it. Returns None when neither yields a readable path.
    """
    if given:
        return given if Path(given).is_file() else None
    try:
        model = json.loads(Path(model_json).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    name = (model.get("_source") or {}).get("file")
    if not name:
        return None
    cand = Path(model_json).resolve().parent.parent / name
    return str(cand) if cand.is_file() else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("model_json", help="slide-model.json (the model under audit)")
    p.add_argument("final_pptx", nargs="?", default=None,
                   help="rendered deck — omit for an HTML-only render (source stage only)")
    p.add_argument("--source", default=None,
                   help="final.md; enables the source stage. Auto-resolved from the model's "
                        "_source stamp when omitted")
    p.add_argument("--json", action="store_true",
                   help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report drops but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    source_md = resolve_source(args.model_json, args.source)
    if args.source and source_md is None:
        print(f"audit_block_coverage: cannot read source {args.source}", file=sys.stderr)
        return 2
    if not args.final_pptx and not source_md:
        print("audit_block_coverage: nothing to compare the model against — pass a rendered "
              "final.pptx, or `--source final.md` for the source stage (an unstamped model "
              "cannot resolve its own source; run `model_freshness.py stamp` after FILL).",
              file=sys.stderr)
        return 2

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    stages: list[str] = []
    n_sources = n_content = m_blocks = 0

    if source_md:
        try:
            md = parse_source_md(source_md)
            slots = model_callout_slots(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_block_coverage: cannot run the source stage: {e}", file=sys.stderr)
            return 2
        d, u = reconcile_source(md, slots)
        drops += d
        unmatched += u
        stages.append(f"source({Path(source_md).name})")
        m_blocks += sum(x.callouts for x in md)

    if args.final_pptx:
        try:
            sources = parse_model(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_block_coverage: cannot read {args.model_json}: {e}", file=sys.stderr)
            return 2
        try:
            renders = parse_pptx(args.final_pptx)
        except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
            print(f"audit_block_coverage: cannot read {args.final_pptx}: {e}", file=sys.stderr)
            return 2
        d, u = reconcile(sources, renders)
        drops += d
        unmatched += u
        stages.append("render(final.pptx)")
        n_sources = len(sources)
        n_content = sum(1 for r in renders if not r.is_chrome)
        m_blocks += sum(x.callouts + x.images for x in sources)

    if args.json:
        print(json.dumps({
            "model_json": args.model_json,
            "final_pptx": args.final_pptx,
            "source_md": source_md,
            "stages": stages,
            "summary": {
                "model_slides": n_sources,
                "render_content_slides": n_content,
                "blocks": m_blocks,
                "drops": len(drops),
                "unmatched": len(unmatched),
            },
            "drops": [asdict(d) for d in drops],
            "unmatched": [asdict(u) for u in unmatched],
        }, ensure_ascii=False, indent=2))
    else:
        if not drops and not unmatched:
            print(f"audit_block_coverage: ok — {' + '.join(stages)}, {m_blocks} load-bearing "
                  f"block(s), 0 dropped")
        else:
            print(f"audit_block_coverage: {len(drops)} drop(s), "
                  f"{len(unmatched)} unmatched slide(s) [{' + '.join(stages)}]")
            for d in drops:
                print("  " + d.fmt())
            for u in unmatched:
                print("  " + u.fmt())

    if args.warn_only:
        return 0
    return 1 if drops else 0


if __name__ == "__main__":
    sys.exit(main())
