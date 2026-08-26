"""Audit that every slide's speaker notes survive both steps that can drop them:
`final.md` → `slide-model.json` (FILL) and `slide-model.json` → `final.pptx` (RENDER).

Why this exists:
    Speaker notes are load-bearing (the prose the slide replaces — see
    `${CLAUDE_PLUGIN_ROOT}/config/principles.md` → *Speaker notes are the talk*). The specs require
    the fill step to lift every `### Speaker notes` block **verbatim** into `notes`, and the
    renderer to emit it into the slide's notes pane (strict §15.5 rule 10 / §19.3 stage 7;
    free-form §19) — but until now nothing *enforced* either half. A fill that skipped a notes
    block, or a renderer that forgot the notes stage, shipped silently: no audit and no
    visual-review rubric looks at the notes pane.

    This is the deterministic catch, mirroring `audits/block_coverage.py` for slide bodies. Like
    that audit it used to require a `.pptx`, which meant it never ran on an `html-strict` deck —
    exactly the mode with the least other checking. The source stage below needs no deck.

Two modes:

  **Source stage** (`--source final.md`, no `.pptx` needed) — every slide whose source carries a
  non-empty `### Speaker notes` block must carry a non-empty `notes` in the model. Format-
  independent, so it guards every render mode.

  **Render stage** (`<final.pptx>`) — every model slide carrying `notes` reached a non-empty notes
  pane in the deck. Reads each slide's linked `notesSlide` part, excluding the slide-number
  placeholder.

  Slides with no notes at their input stage are never flagged (no false positives). Matching is by
  normalized title, reusing `audit_block_coverage`'s slide/title/chrome machinery. Drops report as
  `[notes-drop] slide N "<title>" — …` and exit non-zero.

Usage:
    python3 audits/notes_coverage.py <slide-model.json> [final.pptx] [--source final.md]
                                     [--json] [--warn-only]

    With neither a `.pptx` nor a resolvable `--source` there is nothing to compare against and the
    audit exits 2. `--source` is auto-resolved from the model's `_source` stamp (written by
    `model_freshness.py stamp`).

Exit codes:
    0  every slide that has notes at the input stage still has them at the output stage
    1  one or more notes drops; build should stop and re-fill / re-render
    2  audit could not run (file missing, malformed, nothing to compare against)

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
from block_coverage import (  # noqa: E402  (shared pptx / source machinery)
    NS,
    _slide_paths,
    _slide_rels,
    _normalize_title,
    _extract_title,
    _looks_like_agenda,
    _HEADING_NUM,
    _NONSLIDE_HEADING,
    resolve_source,
)


# --------------------------------------------------------------------------- #
# final.md parsing — which slides carry a non-empty `### Notes` block
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    has_notes: bool = False


def parse_model(path: str) -> list[SourceSlide]:
    """Which slides carry notes, read straight from `slide-model.json`: a slide's `notes` field
    (lifted verbatim during FILL) is non-empty. Matched to the deck by normalized title (its
    `title`, or `section` for dividers). No markdown to parse."""
    import json
    model = json.loads(open(path, encoding="utf-8").read())
    out: list[SourceSlide] = []
    for idx, s in enumerate(model.get("slides", []), start=1):
        title = s.get("title") or s.get("section") or ""
        out.append(SourceSlide(h2_line=idx, h2_title=title,
                               has_notes=bool((s.get("notes") or "").strip())))
    return out


# --------------------------------------------------------------------------- #
# final.md parsing — which slides authored notes (the source stage)
# --------------------------------------------------------------------------- #

def parse_source_md(path: str) -> list[SourceSlide]:
    """Per `##` slide of `final.md`: does it carry a non-empty `### Speaker notes` block?

    Everything under `# Cut material` / `# Open questions` is out of scope, as is fenced code
    (a notes heading inside a code sample is a sample, not a notes block).
    """
    text = open(path, encoding="utf-8").read()
    out: list[SourceSlide] = []
    cur: SourceSlide | None = None
    in_notes = in_fence = False
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
            cur = SourceSlide(h2_line=i, h2_title=title)
            out.append(cur)
            in_notes = False
            continue
        if raw.startswith("### "):
            head = re.sub(r"[^\w\s]", "", raw[4:].strip().lower()).strip()
            in_notes = "speaker notes" in head or head == "notes"
            continue
        if in_notes and cur is not None and raw.strip() and raw.strip() not in {"---", "***"}:
            cur.has_notes = True
    return out


def model_notes(path: str) -> list[tuple[str, bool]]:
    """(title, model slide carries non-empty `notes`) per model slide."""
    model = json.loads(open(path, encoding="utf-8").read())
    return [((sl.get("title") or sl.get("section") or ""),
             bool((sl.get("notes") or "").strip()))
            for sl in model.get("slides", [])]


def reconcile_source(md: list[SourceSlide],
                     model: list[tuple[str, bool]]) -> tuple[list[Drop], list[Unmatched]]:
    by_title: dict[str, tuple[int, bool]] = {}
    for idx, (title, has) in enumerate(model, start=1):
        key = _normalize_title(title)
        if key and key not in by_title:
            by_title[key] = (idx, has)

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    for sslide in md:
        if not sslide.has_notes:
            continue
        key = _normalize_title(sslide.h2_title)
        hit = by_title.get(key)
        if hit is None:
            cands = [v for k, v in by_title.items()
                     if k.startswith(key[:20]) or key.startswith(k[:20])]
            if len(cands) == 1:
                hit = cands[0]
        if hit is None:
            unmatched.append(Unmatched(h2_line=sslide.h2_line, h2_title=sslide.h2_title))
            continue
        idx, has = hit
        if not has:
            drops.append(Drop(slide_num=idx, h2_title=sslide.h2_title, target="model"))
    return drops, unmatched


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
    target: str = "render"        # "model" (fill dropped them) | "render" (renderer did)

    def fmt(self) -> str:
        landed = ("model carries no `notes`" if self.target == "model"
                  else "render notes pane empty")
        return (f"[notes-drop] slide {self.slide_num} \"{self.h2_title}\" — "
                f"source has notes, {landed}")


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
    p.add_argument("model_json", help="slide-model.json (the model under audit)")
    p.add_argument("final_pptx", nargs="?", default=None,
                   help="rendered deck — omit for an HTML-only render (source stage only)")
    p.add_argument("--source", default=None,
                   help="final.md; enables the source stage. Auto-resolved from the model's "
                        "_source stamp when omitted")
    p.add_argument("--json", action="store_true", help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report drops but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    source_md = resolve_source(args.model_json, args.source)
    if args.source and source_md is None:
        print(f"audit_notes_coverage: cannot read source {args.source}", file=sys.stderr)
        return 2
    if not args.final_pptx and not source_md:
        print("audit_notes_coverage: nothing to compare the model against — pass a rendered "
              "final.pptx, or `--source final.md` for the source stage (an unstamped model "
              "cannot resolve its own source; run `model_freshness.py stamp` after FILL).",
              file=sys.stderr)
        return 2

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    stages: list[str] = []
    with_notes = total = 0

    if source_md:
        try:
            md = parse_source_md(source_md)
            model = model_notes(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_notes_coverage: cannot run the source stage: {e}", file=sys.stderr)
            return 2
        d, u = reconcile_source(md, model)
        drops += d
        unmatched += u
        stages.append(f"source({Path(source_md).name})")
        with_notes += sum(1 for x in md if x.has_notes)
        total += len(md)

    if args.final_pptx:
        try:
            sources = parse_model(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_notes_coverage: cannot read {args.model_json}: {e}", file=sys.stderr)
            return 2
        try:
            renders = parse_pptx(args.final_pptx)
        except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
            print(f"audit_notes_coverage: cannot read {args.final_pptx}: {e}", file=sys.stderr)
            return 2
        d, u = reconcile(sources, renders)
        drops += d
        unmatched += u
        stages.append("render(final.pptx)")
        with_notes += sum(1 for x in sources if x.has_notes)
        total += len(sources)

    if args.json:
        print(json.dumps({
            "model_json": args.model_json,
            "final_pptx": args.final_pptx,
            "source_md": source_md,
            "stages": stages,
            "summary": {
                "slides": total,
                "slides_with_notes": with_notes,
                "drops": len(drops),
                "unmatched": len(unmatched),
            },
            "drops": [asdict(d) for d in drops],
            "unmatched": [asdict(u) for u in unmatched],
        }, ensure_ascii=False, indent=2))
    else:
        if not drops and not unmatched:
            print(f"audit_notes_coverage: ok — {' + '.join(stages)}, {with_notes}/{total} slides "
                  f"carry notes, 0 dropped")
        else:
            print(f"audit_notes_coverage: {len(drops)} notes-drop(s), "
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
