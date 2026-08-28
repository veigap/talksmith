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

    That is not hypothetical. On one deck a manual sweep found 37 live sentences of `final.md`
    absent from the model — among them the one line that said whether a formula's Σ ran over
    examples or over output units. The deck rendered, every audit was green, and the presenter
    read the slide wrong. `audits/block_coverage.py` and `audits/notes_coverage.py` could not have
    caught it: both compare the model against a rendered `.pptx`, so they are blind to what FILL
    dropped *before* the render — and on an HTML-only deck they had no `.pptx` to run against.

    This audit is that check, mechanised, and it is **format-independent**: it compares source to
    model, so it guards `html-strict` exactly as it guards the `.pptx` paths. It is the text
    counterpart of `audits/image_coverage.py`, which does the same for image refs.

**Body prose and speaker notes are judged differently, because their contracts differ.**

    Notes are **copied verbatim** into `notes` — they never compete for room on the slide, so
    there is nothing to gain by compressing them and a missing notes line is simply a lost line.
    They are reported strictly: no match, no excuse.

    Body prose is **decomposed**, and decomposition legitimately rewrites. A verified case: two
    prose bullets became a comparison table, every word changed, nothing was lost. Any literal
    match counts that as a drop, and a report where most rows are innocent is a report a presenter
    learns to skip. So a body line with no literal match is sorted into two tiers:

      `[text-drop]`      — no word window matched **and** most of its distinctive words are absent
                           from the model. Nothing of this line is on the deck.
      `[text-rewritten]` — no window matched, but its distinctive words are almost all present.
                           Almost always a legitimate restructuring; hidden unless
                           `--show-rewrites`, and never counted as a failure.

How a line is judged present:
    Any window of `--window` consecutive words (default 5) appearing, in order, in the model's
    text. That tolerates the decomposition FILL is *supposed* to do — a sentence split across a
    card's `label` and `body`, a lead-in separator consumed, punctuation normalized — while still
    catching a clause that is not there. Short fragments (3-4 words) must appear whole; anything
    shorter is skipped as too weak to judge. Matching is deck-wide: a line moved to a neighbouring
    slide is a judgment call, not a drop.

What it reads on the source side:
    Slide bodies (`### Content` or bare prose under a `##`) and `### Speaker notes`. A markdown
    table is read **cell by cell**: the source is row-major and the model is column-major, so a
    row's words are never consecutive in the model however completely its cells survived. **Only `##`
    blocks are slides** (schemas/draft.md): the thesis claim, the agenda arc and a section's
    `**Goal of this section:**` sit under an `#` heading and are working meta the deck never
    renders — the agenda slide is built from `deck.sections`, not from the agenda block — so
    everything before a section's first `##` is out of scope. Also skipped: `### Sources` and
    `### Presenter feedback`, fenced code (bulky enough that a drop is visible, and `code` carries
    its own bytes), HTML comments, image refs, YAML frontmatter, and everything under
    `# Cut material` / `# Open questions`. A line waived with
    `<!-- deck-omit-text: <any substring> -->` anywhere in the file is never reported.

What it reads on the model side:
    Every string in `slide-model.json` except keys beginning with `_` — notably `_choice`, whose
    rationale prose quotes the source and would mask exactly the drops this looks for.

A whole missing slide:
    Reported only when **nothing** of the slide reached the model — neither its title nor any of
    its lines. Title alone is not enough to go on: `quote`, `big-number`, `image-grid`, `quiz` and
    `callout` slides carry no `title` field at all, so a title-only test calls every one of them
    missing.

Usage:
    python3 text_coverage.py <final.md> <slide-model.json>
        [--window N] [--strict | --strict-notes] [--show-rewrites] [--json]

Exit codes:
    0  no drops (or drops found without a --strict flag — the list goes to stderr)
    1  drops found AND --strict, or notes drops AND --strict-notes
    2  a file could not be read / parsed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ooxml import model_strings  # noqa: E402  (shared audit plumbing)

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
# A markdown table row, and its `|---|:--:|` separator (structure, carrying no content).
_TABLE_ROW = re.compile(r"^\s*\|")
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]*\|?\s*$")

# Below this length a token is a function word in Spanish and English alike (de, la, and, the),
# present in any text and worthless as evidence that a line survived.
_CONTENT_WORD_MIN = 4
# Share of a line's distinctive words that must be present for "rewritten" rather than "dropped".
_REWRITE_RECALL = 0.7


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

    `_`-prefixed keys are excluded by `model_strings` — see its docstring for why that matters
    here in particular: `_choice` restates the source, so a dropped line would still be "found".
    """
    return " " + " ".join(" ".join(tokens(c)) for c in model_strings(model)) + " "


def _title_haystack(model: dict) -> str:
    """Model slide titles / section names only — the first half of the missing-slide test."""
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


def word_recall(frag_tokens: list[str], vocab: set[str]) -> float | None:
    """Share of the fragment's distinctive words present anywhere in the model.

    High recall with no window match is the signature of a rewrite: the fill kept the content and
    changed the phrasing (two bullets folded into a table, a sentence recast as a card). Returns
    None when the fragment carries too few distinctive words to judge.
    """
    content = {t for t in frag_tokens if len(t) >= _CONTENT_WORD_MIN}
    if len(content) < 3:
        return None
    return len(content & vocab) / len(content)


# --------------------------------------------------------------------------- #
# final.md parsing
# --------------------------------------------------------------------------- #

@dataclass
class Fragment:
    line: int
    slide: str
    where: str        # "content" | "notes"
    text: str
    kind: str = "prose"   # "prose" | "cell" — a table cell is judged by its own rule


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
    in_slide = False        # only `##` blocks are slides; `#` bodies are working meta

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
        if original.startswith("## "):
            flush()
            slide = _HEADING_NUM.sub("", original[3:].strip())
            titles.append((i + 1, slide))
            where, in_slide = "content", True
            continue
        if original.startswith("# "):
            # A section / thesis / agenda heading. Its own body is meta — the deck builds its
            # agenda from `deck.sections`, and a section's goal is a note to the author.
            flush()
            slide = _HEADING_NUM.sub("", original[2:].strip())
            where, in_slide = "content", False
            continue
        if not s:
            flush()
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
        if where == "skip" or not in_slide:
            continue
        if _TABLE_ROW.match(s):
            # A table row is checked **cell by cell**, never as a row. The source is row-major
            # and the model is column-major (`value-columns` stores `columns[].cells[]`, `matrix`
            # stores cells in reading order), so no five consecutive words of a row survive
            # anywhere in the model even when every one of its cells is present — the row is the
            # one shape a word-window can never find. Verified on a real deck: 6 of 13 reported
            # drops were intact table rows.
            flush()
            if _TABLE_RULE.match(s):
                continue                                     # `|---|---|` is structure, not text
            for cell in s.strip().strip("|").split("|"):
                cell = cell.strip()
                for part in _SENTENCE_SPLIT.split(cell):
                    part = part.strip()
                    if part:
                        frags.append(Fragment(line=i + 1, slide=slide, where=where, text=part,
                                              kind="cell"))
            continue
        if _NEW_UNIT.match(s):                               # list marker
            flush()
        if not unit:
            unit_line = i + 1
        body = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)    # list marker
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
    where: str        # "content" | "notes"
    text: str
    tier: str         # "drop" | "rewritten"
    recall: float | None = None

    def fmt(self, src: str) -> str:
        t = self.text if len(self.text) <= 110 else self.text[:107] + "…"
        tag = "text-drop" if self.tier == "drop" else "text-rewritten"
        tail = "" if self.recall is None else f" [{self.recall:.0%} of its words are in the model]"
        return f'[{tag}] {src}:{self.line} ({self.where}) "{self.slide}" — "{t}"{tail}'


@dataclass
class MissingSlide:
    line: int
    title: str

    def fmt(self, src: str) -> str:
        return (f'[slide-missing] {src}:{self.line} "{self.title}" — nothing from this slide '
                f'(neither title nor any line) reached the model')


@dataclass
class Report:
    drops: list[Drop]            # tier "drop" only — notes and content
    rewrites: list[Drop]         # tier "rewritten" — advisory
    missing: list[MissingSlide]
    checked: int

    @property
    def notes_drops(self) -> list[Drop]:
        return [d for d in self.drops if d.where == "notes"]

    @property
    def content_drops(self) -> list[Drop]:
        return [d for d in self.drops if d.where == "content"]


def audit(text: str, model: dict, window: int = 5) -> Report:
    frags, titles, waivers = fragments(text)
    hay = _haystack(model)
    thay = _title_haystack(model)
    vocab = set(hay.split())

    drops: list[Drop] = []
    rewrites: list[Drop] = []
    checked = 0
    matched_slides: set[str] = set()
    for f in frags:
        tk = tokens(f.text)
        if len(tk) < 3:
            # Too short for a word window — but a one-word table cell can still be distinctive
            # ("Augmentation"), and dropping a cell is a real defect. Judge those by their
            # distinctive words instead; a cell of pure function words or bare figures
            # ("Sí", "70%") is genuinely unjudgeable and stays skipped.
            distinctive = [t for t in tk if len(t) >= _CONTENT_WORD_MIN]
            if f.kind != "cell" or not distinctive:
                continue
            checked += 1
            if all(t in vocab for t in distinctive):
                matched_slides.add(f.slide)
                continue
            low = f.text.lower()
            if any(w and w in low for w in waivers):
                matched_slides.add(f.slide)
                continue
            drops.append(Drop(f.line, f.slide, f.where, f.text, "drop", None))
            continue
        checked += 1
        if present(tk, hay, window):
            matched_slides.add(f.slide)
            continue
        low = f.text.lower()
        if any(w and w in low for w in waivers):
            matched_slides.add(f.slide)
            continue
        # Notes are copied verbatim, so there is no rewrite tier for them: a notes line that did
        # not match is a notes line that was summarized away, which is exactly the defect.
        recall = None if f.where == "notes" else word_recall(tk, vocab)
        if recall is not None and recall >= _REWRITE_RECALL:
            rewrites.append(Drop(f.line, f.slide, f.where, f.text, "rewritten", recall))
            matched_slides.add(f.slide)
        else:
            drops.append(Drop(f.line, f.slide, f.where, f.text, "drop", recall))

    # A slide is missing only when nothing of it landed — not merely when its title did not.
    # `quote`, `big-number`, `image-grid`, `quiz` and `callout` have no `title` field at all
    # (schemas/slide-model.md), so a title-only test reports every one of them.
    missing: list[MissingSlide] = []
    for line, title in titles:
        if title in matched_slides:
            continue
        tk = tokens(title)
        if len(tk) >= 2 and (present(tk, thay, min(window, 4)) or present(tk, hay, min(window, 4))):
            continue
        missing.append(MissingSlide(line=line, title=title))
    return Report(drops=drops, rewrites=rewrites, missing=missing, checked=checked)


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
                    help="exit 1 on any drop (default: warn, exit 0)")
    ap.add_argument("--strict-notes", action="store_true",
                    help="exit 1 on a dropped notes line only — notes are copied verbatim, so "
                         "those are unambiguous; body prose is legitimately restructured")
    ap.add_argument("--show-rewrites", action="store_true",
                    help="also list body lines that look restructured rather than dropped")
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

    r = audit(text, model, window=max(2, args.window))
    notes, content = r.notes_drops, r.content_drops

    if args.json:
        print(json.dumps({
            "final": str(args.final),
            "model": str(args.model),
            "window": args.window,
            "summary": {"checked": r.checked, "notes_drops": len(notes),
                        "content_drops": len(content), "rewritten": len(r.rewrites),
                        "missing_slides": len(r.missing)},
            "notes_drops": [asdict(d) for d in notes],
            "content_drops": [asdict(d) for d in content],
            "rewritten": [asdict(d) for d in r.rewrites],
            "missing_slides": [asdict(m) for m in r.missing],
        }, ensure_ascii=False, indent=2))

    if not r.drops and not r.missing:
        extra = f" ({len(r.rewrites)} restructured)" if r.rewrites else ""
        print(f"text_coverage: ok — {r.checked} source lines, all present in "
              f"{args.model.name}{extra}")
        # Downgraded is not discarded: an author who asked to see the restructured lines gets
        # them even when nothing failed — that list is how the tier itself gets audited.
        if args.show_rewrites:
            for d in r.rewrites:
                print("  " + d.fmt(args.final.name), file=sys.stderr)
        return 0

    print(f"text_coverage: {len(notes)} speaker-notes line(s), {len(content)} body line(s) and "
          f"{len(r.missing)} slide(s) of {args.final.name} are MISSING from the model "
          f"(of {r.checked} checked; {len(r.rewrites)} more were restructured, not lost"
          f"{'' if args.show_rewrites else ' — --show-rewrites to list them'}).",
          file=sys.stderr)
    if notes:
        print("  Notes are copied verbatim, so each of these is a line the presenter has lost:",
              file=sys.stderr)
    for m in r.missing:
        print("  " + m.fmt(args.final.name), file=sys.stderr)
    for d in notes + content:
        print("  " + d.fmt(args.final.name), file=sys.stderr)
    if args.show_rewrites:
        for d in r.rewrites:
            print("  " + d.fmt(args.final.name), file=sys.stderr)
    print(f"  Fix in the model (schemas/slide-model.md → \"Never drop content\"): move each line "
          f"into a field, a card, a fact or `highlights`; copy notes verbatim rather than "
          f"summarizing them; waive a deliberate omission with "
          f"`<!-- deck-omit-text: <substring> -->`.", file=sys.stderr)

    if args.strict and r.drops:
        return 1
    if args.strict_notes and notes:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
