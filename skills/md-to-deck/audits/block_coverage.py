"""Load-bearing blocks survive the FILL step.

Run:  python3 audits/block_coverage.py <slide-model.json> --source final.md

A busy slide is where content quietly goes missing: six cards become four, a callout beside an
image is dropped, a figure loses its caption. None of that looks broken afterwards — the slide
just says less than the author wrote. So this walks `final.md` for the structured blocks each
slide authored (callouts, images, labeled sets) and asserts they reached the model.

`--source` is auto-resolved from the model's `_source` stamp (written by `model_freshness.py
stamp` after FILL); with neither a stamp nor an explicit `--source` there is nothing to compare
against and the audit exits 2.

> This used to have a second stage that re-read a rendered `.pptx` and matched its slides back to
> the model by title, fill colour and font, to check the blocks had survived the *render* too.
> That stage existed because the deck was authored by an LLM following a prose spec, so the deck
> could disagree with the model and something had to notice. The `.pptx` is now measured from the
> rendered HTML, which emits what the template is given, so there is no longer an interpreting
> step between model and deck for a block to fall out of. What remains — did FILL keep what the
> author wrote — is the half that was always the real risk.

CLI-safe; standard library only. `notes_coverage.py` imports its source-parsing machinery.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict, field
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _model import model_strings  # noqa: E402  (shared audit plumbing)


sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_coverage import tokens  # noqa: E402  (one tokenizer, shared by every coverage audit)


# Emoji ranges from ${CLAUDE_PLUGIN_ROOT}/config/pptx-styles/pptx-strict/pptx-prompt.md §17.7 detection ranges.
EMOJI_CLASS = r"[\U0001F300-\U0001FAFF☀-➿⌀-⏿]"

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
    `media` (composed slides) or `image` (`image-full`, which names its own picture field) +
    `images[]` + each `figures[].image`; a callout block = a `callout`-template slide. Matched to
    the deck by normalized title (its `title`, or `section` for dividers)."""
    import json
    model = json.loads(open(path, encoding="utf-8").read())
    slides: list[SourceSlide] = []
    for idx, s in enumerate(model.get("slides", []), start=1):
        images = (1 if (s.get("media") or s.get("image")) else 0) + len(s.get("images", []))
        images += sum(1 for f in s.get("figures", []) if f.get("image"))
        callouts = 1 if s.get("template") == "callout" else 0
        title = s.get("title") or s.get("section") or ""
        slides.append(SourceSlide(h2_line=idx, h2_title=title, callouts=callouts, images=images))
    return slides


# --------------------------------------------------------------------------- #
# final.md parsing — the source stage (no .pptx needed)
def _normalize_title(s: str) -> str:
    # Source headings carry a locator (`## 3. Título`); model titles do not. The number is
    # addressing, not content — strip it on both sides or every numbered slide reads unmatched.
    s = _HEADING_NUM.sub("", s.strip())
    s = s.lower()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:40]


# --------------------------------------------------------------------------- #

@dataclass
class MdSlide:
    """One `##` slide of `final.md`, with the callout blocks its author wrote."""
    line: int
    title: str
    callouts: int = 0
    callout_lines: list[int] = field(default_factory=list)
    quote_blocks: int = 0        # of those callouts, how many are plain `>` blockquotes
    body: list[str] = field(default_factory=list)

    def windows(self, window: int = 5, limit: int = 8) -> list[str]:
        """Distinctive word windows of this slide's body, for matching a slide by its text."""
        return content_windows(self.body, window=window, limit=limit)


def content_windows(body: list[str], window: int = 5, limit: int = 8) -> list[str]:
    """Up to `limit` `window`-word runs drawn from a slide's body text."""
    out: list[str] = []
    for line in body:
        tk = tokens(line)
        for i in range(0, max(1, len(tk) - window + 1)):
            run = tk[i:i + window]
            if len(run) >= window:
                out.append(" ".join(run))
                if len(out) >= limit:
                    return out
    return out


class SlideIndex:
    """Model slides addressable by title **or** by the text they carry.

    Title alone is not an address. `quote`, `big-number`, `image-grid`, `quiz` and `callout` have
    no `title` field at all (schemas/slide-model.md), so a title-only index reports every slide of
    those templates as unmatched — and then never audits them. Falling back to a text match fixes
    that without loosening the title path: a source slide is matched by content only when exactly
    one model slide carries a distinctive run of its words.
    """

    def __init__(self, entries: list[tuple[str, str]]):
        """entries: (title, full slide text) in model order."""
        self.by_title: dict[str, int] = {}
        self.texts: list[str] = []
        for idx, (title, text) in enumerate(entries, start=1):
            key = _normalize_title(title)
            if key and key not in self.by_title:
                self.by_title[key] = idx
            self.texts.append(" " + " ".join(tokens(text)) + " ")

    def find(self, title: str, windows: list[str] | None = None) -> int | None:
        key = _normalize_title(title)
        if key in self.by_title:
            return self.by_title[key]
        if key:
            cands = [i for k, i in self.by_title.items()
                     if k.startswith(key[:20]) or key.startswith(k[:20])]
            if len(cands) == 1:
                return cands[0]
        if not windows:
            return None
        hits: dict[int, int] = {}
        for w in windows:
            needle = f" {w} "
            for i, text in enumerate(self.texts, start=1):
                if needle in text:
                    hits[i] = hits.get(i, 0) + 1
        if not hits:
            return None
        best = max(hits.values())
        winners = [i for i, n in hits.items() if n == best]
        return winners[0] if len(winners) == 1 else None


def slide_text(slide: dict) -> str:
    """Every content string of one model slide (`_`-prefixed keys excluded — see `model_strings`)."""
    return " ".join(model_strings(slide))


def parse_source_md(path: str) -> list[MdSlide]:
    """Callout blocks (and body text, for matching) per slide of `final.md`.

    Only `##` blocks are slides (schemas/draft.md): the thesis claim, the agenda arc and a
    section's `**Goal of this section:**` live under an `#` heading and are working meta the deck
    never renders. Also skipped: fenced code, `# Cut material` / `# Open questions`, and the
    `### Sources`, `### Presenter feedback` and `### Speaker notes` sub-blocks — a callout quoted
    in the notes is prose the presenter says, not a block the slide owes the audience.
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
        if raw.startswith("## "):
            cur = MdSlide(line=i, title=_HEADING_NUM.sub("", raw[3:].strip()))
            out.append(cur)
            skip = False
            continue
        if raw.startswith("# "):
            cur, skip = None, False          # a section heading opens meta, not a slide
            continue
        if raw.startswith("### "):
            head = re.sub(r"[^\w\s]", "", raw[4:].strip().lower()).strip()
            skip = head in _SKIP_H3
            continue
        if skip or cur is None:
            continue
        is_quote = bool(_CALLOUT_ADMONITION.match(raw) or _CALLOUT_QUOTE_BOLD.match(raw))
        if is_quote or _CALLOUT_BULLET.match(raw):
            cur.callouts += 1
            cur.callout_lines.append(i)
            if is_quote:
                cur.quote_blocks += 1
        if raw.strip() and raw.strip() not in {"---", "***", "___"}:
            cur.body.append(raw)
    return out


@dataclass
class ModelSlot:
    """What one model slide offers a source callout, and what template it resolved to."""
    title: str
    slots: int
    template: str


def model_callout_slots(path: str) -> tuple[list[ModelSlot], SlideIndex]:
    """Per model slide: its callout-shaped landing places and template, plus the slide index.

    A source callout may legitimately land as a `callout`-template slide, a `callout` field, or a
    `highlights` entry — the schema lets the fill route an aside either way, so all three count.
    """
    model = json.loads(open(path, encoding="utf-8").read())
    out: list[ModelSlot] = []
    entries: list[tuple[str, str]] = []
    for sl in model.get("slides", []):
        slots = 1 if (sl.get("template") == "callout" or sl.get("callout")) else 0
        slots += len(sl.get("highlights") or [])
        title = sl.get("title") or sl.get("section") or ""
        out.append(ModelSlot(title=title, slots=slots, template=sl.get("template") or ""))
        entries.append((title, slide_text(sl)))
    return out, SlideIndex(entries)


def reconcile_source(md: list[MdSlide], slots: list[ModelSlot],
                     index: SlideIndex) -> tuple[list[Drop], list[Unmatched]]:
    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    for m in md:
        if not m.callouts:
            continue                      # only a slide that authored one can drop one
        idx = index.find(m.title, m.windows())
        if idx is None:
            unmatched.append(Unmatched(h2_line=m.line, h2_title=m.title))
            continue
        slot = slots[idx - 1]
        # Classify the source blocks against the template the slide RESOLVED to, not in the
        # abstract. On a `quote` slide the blockquote *is* the slide — it lands in the `quote`
        # field, which is not a callout slot — so counting it as an aside reports a drop on every
        # correctly-filled quote slide. Same blind spot as the title matching fixed in 0.88.0,
        # one layer down: the slide matched, and then its content was read as if it were a body.
        expected = m.callouts
        if slot.template == "quote":
            expected -= m.quote_blocks
        if expected <= 0:
            continue
        n = slot.slots
        if expected > n:
            drops.append(Drop(
                slide_num=idx, h2_title=m.title, block_type="callout(s)",
                source_count=expected, render_count=n, target="model",
                note=f"final.md lines {m.callout_lines}; the model gives this slide "
                     f"{n} callout/highlights slot(s)",
            ))
    return drops, unmatched


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
    if not source_md:
        print("audit_block_coverage: nothing to compare the model against — pass "
              "`--source final.md` (an unstamped model cannot resolve its own source; run "
              "`model_freshness.py stamp` after FILL).", file=sys.stderr)
        return 2

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    stages: list[str] = []
    n_sources = n_content = m_blocks = 0

    if source_md:
        try:
            md = parse_source_md(source_md)
            slots, index = model_callout_slots(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_block_coverage: cannot run the source stage: {e}", file=sys.stderr)
            return 2
        d, u = reconcile_source(md, slots, index)
        drops += d
        unmatched += u
        stages.append(f"source({Path(source_md).name})")
        m_blocks += sum(x.callouts for x in md)   # authored blocks, before template classification

    if args.json:
        print(json.dumps({
            "model_json": args.model_json,
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
