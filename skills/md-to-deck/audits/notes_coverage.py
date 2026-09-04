"""Speaker notes survive the FILL step.

Run:  python3 audits/notes_coverage.py <slide-model.json> --source final.md

Notes are load-bearing and template-independent: a slide can lose its whole notes pane without
anything else looking wrong, which is exactly the kind of drop nobody catches by eye. So this
walks `final.md` for slides whose source carries `### Speaker notes` and asserts each one reached
a `notes` field in the model.

`--source` is auto-resolved from the model's `_source` stamp (written by `model_freshness.py
stamp` after FILL); with neither a stamp nor an explicit `--source` there is nothing to compare
against and the audit exits 2.

> This used to have a second stage that re-read a rendered `.pptx` to check the notes had also
> reached its notes pane. That stage existed because the deck was authored by an LLM following a
> prose spec and had to be verified afterwards. The `.pptx` is now measured mechanically from the
> rendered HTML, where the notes are carried by the same code path as every other slide, so there
> is no longer a step between the model and the deck for notes to fall out of.

CLI-safe; standard library only. Shares source-parsing machinery with block_coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict, field as dc_field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from block_coverage import (  # noqa: E402  (shared source-parsing machinery)
    _HEADING_NUM,
    _NONSLIDE_HEADING,
    _SKIP_H3,
    SlideIndex,
    content_windows,
    resolve_source,
    slide_text,
)


# --------------------------------------------------------------------------- #
# final.md parsing — which slides carry a non-empty `### Notes` block
# --------------------------------------------------------------------------- #

@dataclass
class SourceSlide:
    h2_line: int
    h2_title: str
    has_notes: bool = False
    body: list[str] = dc_field(default_factory=list)

    def windows(self) -> list[str]:
        return content_windows(self.body)


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

    Only `##` blocks are slides (schemas/draft.md) — an `#` heading opens a section, whose body is
    working meta. Everything under `# Cut material` / `# Open questions` is out of scope, as is
    fenced code (a notes heading inside a code sample is a sample, not a notes block). The body is
    kept so a slide whose template has no `title` can still be matched by its text.
    """
    text = open(path, encoding="utf-8").read()
    out: list[SourceSlide] = []
    cur: SourceSlide | None = None
    in_notes = in_fence = skip = False
    for i, raw in enumerate(text.split("\n"), start=1):
        if _NONSLIDE_HEADING.match(raw):
            break
        if re.match(r"^\s*(?:```|~~~)", raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw.startswith("## "):
            cur = SourceSlide(h2_line=i, h2_title=_HEADING_NUM.sub("", raw[3:].strip()))
            out.append(cur)
            in_notes = skip = False
            continue
        if raw.startswith("# "):
            cur, in_notes, skip = None, False, False
            continue
        if raw.startswith("### "):
            head = re.sub(r"[^\w\s]", "", raw[4:].strip().lower()).strip()
            in_notes = "speaker notes" in head or head == "notes"
            skip = head in _SKIP_H3
            continue
        if cur is None or not raw.strip() or raw.strip() in {"---", "***", "___"}:
            continue
        if in_notes:
            cur.has_notes = True
        elif not skip:
            cur.body.append(raw)
    return out


def model_notes(path: str) -> tuple[list[tuple[str, bool]], SlideIndex]:
    """Per model slide: (title, carries non-empty `notes`), plus the title-or-text index."""
    model = json.loads(open(path, encoding="utf-8").read())
    out: list[tuple[str, bool]] = []
    entries: list[tuple[str, str]] = []
    for sl in model.get("slides", []):
        title = sl.get("title") or sl.get("section") or ""
        out.append((title, bool((sl.get("notes") or "").strip())))
        entries.append((title, slide_text(sl)))
    return out, SlideIndex(entries)


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



def reconcile_source(md: list[SourceSlide], model: list[tuple[str, bool]],
                     index: SlideIndex) -> tuple[list[Drop], list[Unmatched]]:
    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    for sslide in md:
        if not sslide.has_notes:
            continue
        idx = index.find(sslide.h2_title, sslide.windows())
        if idx is None:
            unmatched.append(Unmatched(h2_line=sslide.h2_line, h2_title=sslide.h2_title))
            continue
        if not model[idx - 1][1]:
            drops.append(Drop(slide_num=idx, h2_title=sslide.h2_title, target="model"))
    return drops, unmatched


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("model_json", help="slide-model.json (the model under audit)")
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
    if not source_md:
        print("audit_notes_coverage: nothing to compare the model against — pass "
              "`--source final.md` (an unstamped model cannot resolve its own source; run "
              "`model_freshness.py stamp` after FILL).", file=sys.stderr)
        return 2

    drops: list[Drop] = []
    unmatched: list[Unmatched] = []
    stages: list[str] = []
    with_notes = total = 0

    if source_md:
        try:
            md = parse_source_md(source_md)
            model, index = model_notes(args.model_json)
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"audit_notes_coverage: cannot run the source stage: {e}", file=sys.stderr)
            return 2
        d, u = reconcile_source(md, model, index)
        drops += d
        unmatched += u
        stages.append(f"source({Path(source_md).name})")
        with_notes += sum(1 for x in md if x.has_notes)
        total += len(md)

    if args.json:
        print(json.dumps({
            "model_json": args.model_json,
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
