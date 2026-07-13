"""Render a Talk to a **styled static HTML site** — the code-generated Talksmith renderer.

One renderer, two uses:
  - **preview** (`--draft`): a fast, throwaway HTML of `draft.md` before Polish — replaces the
    old Pillow wireframe. Same template classification, but now fully *styled* (real cards,
    icons, callout boxes, code surfaces), not a grey wireframe.
  - **html deliverable**: a shareable static site built from `final.md`, offered as a render
    option alongside `strict`/`free-form`.

Why it exists: unlike the native `.pptx` render (which follows prose and silently drops the
styled layer), this is **deterministic code** — icons, callouts, code surfaces, and card
strips always render, because the same `html_style` components emit them every time. It needs
no Cowork and no native skill.

Pipeline: `convert.py` (→ per-slide units, `--draft` for the preview) → classify each slide
against the catalog (`slide_model._classify`) → render its template via `html_style`
(content-matched Material icons fetched by `icon_fetch.py`, inlined) → one self-contained
`.html` file. Only images are external (shown as placeholders until real assets are wired).

Usage:
    python3 build_html.py --talk talks/<Talk> [--draft] [-o <out.html>]

Requires network on first run (icon fetch, cached under output/.icons). Output is offline.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import convert as _convert            # noqa: E402
import slide_model as _sm             # noqa: E402  (_parse_unit, _classify, template log)
import html_style as _hs              # noqa: E402

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Optional author hint: `<!-- template: concept-breakdown -->` under a slide's heading forces
# that template instead of the auto-classification. Read from the raw md (convert.py strips
# comments), keyed by the slide's normalized title so it survives conversion.
_HINT_RE = re.compile(r"<!--\s*(?:template|slide|type)\s*:\s*([a-z][a-z+-]*)\s*-->", re.I)
_HEAD_RE = re.compile(r"^#{1,6}\s+(.*)$")


def _norm(t: str) -> str:
    t = re.sub(r"^\d+\.\s*", "", (t or "").strip().lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


def _template_hints(raw: str) -> dict:
    hints, cur = {}, None
    in_code = False
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = _HEAD_RE.match(s)
        if m:
            cur = _norm(m.group(1))
        h = _HINT_RE.search(line)
        if h and cur is not None:
            hints[cur] = h.group(1).lower()
    return hints


def _frontmatter(text: str) -> dict:
    m = _FM_RE.match(text)
    out: dict[str, str] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def render(md_text: str, talk_root: Path, out_dir: Path, draft: bool, title: str, subtitle: str):
    cache = out_dir / ".icons"
    hints = _template_hints(md_text)
    converted = _convert.convert(md_text, draft=draft)
    units = _convert._split_into_slide_units(converted)

    sections = []
    log_entries = []
    section = ""
    n = len(units)
    for i, unit in enumerate(units, 1):
        u = _sm._parse_unit(unit, talk_root, out_dir)
        kind = hints.get(_norm(u["title"])) or _sm._classify(u)  # author hint overrides
        if kind in ("fallback", "content-text") and sum(1 for b in u["body"] if b.count("|") >= 2) >= 2:
            kind = "comparison"                                   # a pipe-table → comparison
        if kind == "divider":
            section = u["title"] or section
        inner = _hs.render_slide(kind, u, section, cache)
        notes = u.get("notes", "")
        aside = f'<aside class="notes">{_hs._esc(notes)}</aside>' if notes else ""
        sections.append(f'<section class="slide" data-kind="{kind}">{inner}{aside}</section>')
        log_entries.append((i, u, kind))

    fm = _frontmatter(md_text)
    if fm.get("presentation"):                                    # contractually-fixed cover first
        sections.insert(0, f'<section class="slide cover-slide">{_hs.cover_slide(fm)}</section>')

    # per-slide template-decision log beside the deck (slide-templates.md → Template decision log)
    style = "preview" if draft else "html"
    _sm._write_template_log(log_entries, talk_root, style, out_dir / "template-log.md")

    return _hs.page("".join(sections), title=title, subtitle=subtitle), n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="preview mode — read draft.md (pre-Polish)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="output .html (default under output/)")
    args = ap.parse_args(argv)

    src = args.talk / ("draft.md" if args.draft else "final.md")
    if not src.is_file():
        print(f"failed: {src} not found", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    title = fm.get("presentation", args.talk.name)
    subtitle = " · ".join(x for x in (fm.get("class", ""), fm.get("presenter", "")) if x) \
        or ("Draft preview" if args.draft else "")

    out_dir = args.talk / "output" / ("draft-preview" if args.draft else "html")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = args.output or (out_dir / ("preview.html" if args.draft else "index.html"))

    html, n = render(text, args.talk, out_dir, args.draft, title, subtitle)
    out.write_text(html, encoding="utf-8")
    print(f"[html] {n} slides → {out}", file=sys.stderr)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
