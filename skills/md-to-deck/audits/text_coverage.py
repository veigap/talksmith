#!/usr/bin/env python3
"""Preflight: every load-bearing *line* of `final.md` must survive into `slide-model.json`.

Why this exists:
    The schema's hardest rule is **"Never drop content"**
    ([`schemas/slide-model.md`](${CLAUDE_PLUGIN_ROOT}/schemas/slide-model.md) → *Never drop
    content*): every load-bearing line of the source has to be translated into the model — as a
    field value, a card/row/step, a fact, or a `highlights` entry. Nothing enforced it. FILL is an
    LLM decomposition, and an LLM that reads a dense paragraph and writes three cards will quietly
    leave the fourth clause behind; the model stays *valid*, every other audit passes, and the
    slide ships missing the sentence that disambiguated it.

    That is not hypothetical. On one deck a manual sweep found **37 live sentences** of `final.md`
    absent from the model — among them the one line that said whether a formula's Σ ran over
    examples or over output units. The deck rendered, every audit was green, and the presenter
    read the slide wrong. `audits/block_coverage.py` and `audits/notes_coverage.py` could not have
    caught it: both compare the model against a rendered `.pptx`, so they are blind to what FILL
    dropped *before* the render — and on an HTML-only deck they had no `.pptx` to run against at
    all.

    This audit is that check, mechanised, and it is **format-independent**: it compares the source
    to the model, so it guards `html-strict` exactly as it guards the `.pptx` paths. It is the text
    counterpart of `audits/image_coverage.py`, which does the same for image refs.

How it decides a line was dropped:
    A source fragment is **present** when any window of `--window` consecutive words (default 5)
    from it appears, in order, in the model's text. That tolerates the decomposition FILL is
    *supposed* to do — a sentence split across a card's `label` and `body`, a lead-in separator
    consumed, punctuation normalized — while still catching a clause that simply is not there.
    Short fragments (3-4 words) must appear whole; anything shorter is skipped as too weak to
    judge. Matching is deck-wide, not per-slide: a line moved to a neighbouring slide is a
    judgment call, not a drop.

What it reads on the source side:
    Slide bodies (`### Content` or bare prose under the `##`) and `### Speaker notes` — notes are
    lifted verbatim into `notes`, so a missing notes line is a hard defect. Skipped: `### Sources`
    and `### Presenter feedback` blocks, fenced code (bulky enough that a drop is visible, and
    `code` carries its own bytes), HTML comments (directives and `<!-- ascii-source: … -->`
    echoes), image refs, YAML frontmatter, and everything under `# Cut material` /
    `# Open questions`. A line explicitly waived with `<!-- deck-omit-text: <any substring> -->`
    anywhere in the file is never reported.

What it reads on the model side:
    Every string in `slide-model.json` except keys beginning with `_` — notably `_choice`, whose
    rationale prose quotes the source and would mask exactly the drops this looks for.

Usage:
    python3 text_coverage.py <final.md> <slide-model.json> [--window N] [--strict] [--json]

Exit codes:
    0  no drops (or drops found without `--strict` — the list goes to stderr)
    1  drops found AND --strict
    2  a file could not be read / parsed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_MARKS = re.compile(r"(\*\*|\*|~~|`|__|_)")
_NONSLIDE_HEADING = re.compile(r"^#\s+(Cut material|Open questions)\b", re.IGNORECASE)
_OMIT_RE = re.compile(r"<!--\s*deck-omit-text:\s*([^>]+?)\s*-->", re.IGNORECASE)
# H3 sub-blocks of a slide that never reach the model (schemas/draft.md → slide anatomy).
_SKIP_H3 = {"sources", "presenter feedback"}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
# Slide headings are numbered in the source (`## 3. Título`) and unnumbered in the model
# (`"title": "Título"`); the numbering is locator, not content, and must not defeat matching.
_HEADING_NUM = re.compile(r"^\s*\d+[.)]\s*")
# A line that starts its own unit: list item, numbered item, or table row.
_NEW_UNIT = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\|)")


# --------------------------------------------------------------------------- #
# normalization
# --------------------------------------------------------------------------- #

def tokens(s: str) -> list[str]:
    """Markdown text → comparable word tokens (marks stripped, link titles kept, lowercased)."""
    s = _IMG.sub(" ", s)
    s = _LINK.sub(r"\1", s)
    s = _MD_MARKS.sub(" ", s)
    s = re.sub(r"[^\w\s]+", " ", s.lower(), flags=re.UNICODE)
    return s.split()


def _haystack(model: dict) -> str:
    """Every model string that is content, as one padded token stream.

    Keys beginning with `_` are excluded: `_choice` restates the source in its rationale, so a
    dropped line would still be "found" there — the audit would confirm its own blind spot.
    """
    chunks: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if not k.startswith("_"):
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, str):
            chunks.append(o)

    walk(model)
    return " " + " ".join(" ".join(tokens(c)) for c in chunks) + " "


def _title_haystack(model: dict) -> str:
    """Model slide titles / section names only — for the whole-slide-missing check."""
    out: list[str] = []
    for s in model.get("slides", []):
        for k in ("title", "section", "lead"):
            v = s.get(k)
            if isinstance(v, str) and v:
                out.append(" ".join(tokens(v)))
    deck = model.get("deck", {})
    for k in ("title", "subtitle"):
        v = deck.get(k)
        if isinstance(v, str) and v:
            out.append(" ".join(tokens(v)))
    for sec in deck.get("sections", []) or []:
        out.append(" ".join(tokens(sec if isinstance(sec, str) else str(sec.get("title", "")))))
    return " " + "  ".join(out) + " "


def present(frag_tokens: list[str], hay: str, window: int) -> bool:
    """True when any `window`-word run of the fragment appears in the model text."""
    n = len(frag_tokens)
    if n < 3:
        return True                      # too short to judge — never reported
    if n <= window:
        return f" {' '.join(frag_tokens)} " in hay
    return any(
        f" {' '.join(frag_tokens[i:i + window])} " in hay
        for i in range(n - window + 1)
    )


# --------------------------------------------------------------------------- #
# final.md parsing
# --------------------------------------------------------------------------- #

@dataclass
class Fragment:
    line: int
    slide: str
    where: str        # "content" | "notes"
    text: str


def _mask(lines: list[str]) -> list[str]:
    """Blank out fenced code and HTML comments, keeping every line's index intact."""
    out: list[str] = []
    in_fence = in_comment = False
    for raw in lines:
        s = raw
        if in_comment:
            if "-->" in s:
                s, in_comment = s.split("-->", 1)[1], False
            else:
                out.append("")
                continue
        if in_fence:
            if _FENCE.match(s):
                in_fence = False
            out.append("")
            continue
        if _FENCE.match(s):
            in_fence = True
            out.append("")
            continue
        s = re.sub(r"<!--.*?-->", " ", s)
        if "<!--" in s:
            s, in_comment = s.split("<!--", 1)[0], True
        out.append(s)
    return out


def fragments(text: str) -> tuple[list[Fragment], list[tuple[int, str]], list[str]]:
    """(checkable fragments, [(line, slide title)] per source slide, explicit waivers)."""
    raw = text.split("\n")
    waivers = [m.group(1).strip().lower() for ln in raw for m in [_OMIT_RE.search(ln)] if m]

    start = 0
    if raw and raw[0].strip() == "---":                     # YAML frontmatter
        for i in range(1, len(raw)):
            if raw[i].strip() == "---":
                start = i + 1
                break

    lines = _mask(raw)
    frags: list[Fragment] = []
    titles: list[tuple[int, str]] = []
    slide = ""
    where = "content"

    # A paragraph wrapped across source lines is ONE sentence; splitting per line would report
    # each half separately and, worse, cut a real sentence below the window. Accumulate
    # consecutive body lines into a unit, flushing on a blank line, a heading, a rule, or the
    # start of a new list item / table row.
    unit: list[str] = []
    unit_line = 0

    def flush():
        nonlocal unit
        if unit:
            body = " ".join(unit)
            for part in _SENTENCE_SPLIT.split(body):
                part = part.strip()
                if part:
                    frags.append(Fragment(line=unit_line, slide=slide, where=where, text=part))
            unit = []

    for i in range(start, len(lines)):
        original = raw[i]
        if _NONSLIDE_HEADING.match(original):
            flush()
            break                                            # not delivered material
        s = lines[i].strip()
        if not s:
            flush()
            continue
        if original.startswith("## ") or original.startswith("# "):
            flush()
            slide = _HEADING_NUM.sub("", original.split(" ", 1)[1].strip()) if " " in original else ""
            titles.append((i + 1, slide))
            where = "content"
            continue
        if original.startswith("### "):
            flush()
            head = re.sub(r"[^\w\s]", "", original[4:].strip().lower()).strip()
            where = "notes" if "speaker notes" in head or head == "notes" else (
                "skip" if head in _SKIP_H3 else "content")
            continue
        if s in {"---", "***", "___"}:
            flush()
            continue
        if where == "skip":
            continue
        if _NEW_UNIT.match(s):                               # list marker / table row
            flush()
        if not unit:
            unit_line = i + 1
        body = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)    # list marker
        body = re.sub(r"^\|", "", body).replace("|", " ")    # table row
        unit.append(body.strip())
    flush()
    return frags, titles, waivers


# --------------------------------------------------------------------------- #
# audit
# --------------------------------------------------------------------------- #

@dataclass
class Drop:
    line: int
    slide: str
    where: str
    text: str

    def fmt(self, src: str) -> str:
        t = self.text if len(self.text) <= 110 else self.text[:107] + "…"
        return f'[text-drop] {src}:{self.line} ({self.where}) "{self.slide}" — "{t}"'


@dataclass
class MissingSlide:
    line: int
    title: str

    def fmt(self, src: str) -> str:
        return f'[slide-missing] {src}:{self.line} "{self.title}" — no model slide carries this title'


def audit(text: str, model: dict, window: int = 5) -> tuple[list[Drop], list[MissingSlide], int]:
    frags, titles, waivers = fragments(text)
    hay = _haystack(model)
    thay = _title_haystack(model)

    drops: list[Drop] = []
    checked = 0
    for f in frags:
        tk = tokens(f.text)
        if len(tk) < 3:
            continue
        checked += 1
        low = f.text.lower()
        if any(w and w in low for w in waivers):
            continue
        if not present(tk, hay, window):
            drops.append(Drop(line=f.line, slide=f.slide, where=f.where, text=f.text))

    missing: list[MissingSlide] = []
    for line, title in titles:
        tk = tokens(title)
        if len(tk) < 2:
            continue
        if not present(tk, thay, min(window, 4)) and not present(tk, hay, min(window, 4)):
            missing.append(MissingSlide(line=line, title=title))
    return drops, missing, checked


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("final", type=Path, help="path to the Talk's final.md (or draft.md)")
    ap.add_argument("model", type=Path, help="path to slide-model.json")
    ap.add_argument("--window", type=int, default=5,
                    help="consecutive words that must match to call a line present (default 5)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when lines are missing (default: warn, exit 0)")
    ap.add_argument("--json", action="store_true", help="emit the full report on stdout")
    args = ap.parse_args(argv)

    try:
        text = args.final.read_text(encoding="utf-8")
    except OSError as e:
        print(f"text_coverage: cannot read {args.final}: {e}", file=sys.stderr)
        return 2
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"text_coverage: cannot read model {args.model}: {e}", file=sys.stderr)
        return 2

    drops, missing, checked = audit(text, model, window=max(2, args.window))

    if args.json:
        print(json.dumps({
            "final": str(args.final),
            "model": str(args.model),
            "window": args.window,
            "summary": {"checked": checked, "drops": len(drops), "missing_slides": len(missing)},
            "drops": [asdict(d) for d in drops],
            "missing_slides": [asdict(m) for m in missing],
        }, ensure_ascii=False, indent=2))

    if not drops and not missing:
        print(f"text_coverage: ok — {checked} source lines, all present in {args.model.name}")
        return 0

    pct = (100.0 * len(drops) / checked) if checked else 0.0
    print(f"text_coverage: {len(drops)}/{checked} source line(s) ({pct:.0f}%) MISSING from the "
          f"model, {len(missing)} slide(s) with no model counterpart — content the deck will "
          f"never show. Re-check the FILL step (schemas/slide-model.md → \"Never drop content\"): "
          f"move each line into a field, a card, a fact or `highlights`; waive a deliberate "
          f"omission with `<!-- deck-omit-text: <substring> -->`.", file=sys.stderr)
    for m in missing:
        print("  " + m.fmt(args.final.name), file=sys.stderr)
    for d in drops:
        print("  " + d.fmt(args.final.name), file=sys.stderr)
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
