"""Render a Talk to a **styled static HTML site** — the code-generated Talksmith renderer.

One `html` render type, two sources:
  - **in-progress** (`--draft`): renders the current `draft.md` — auto-fired by the orchestrator
    after the first complete draft and kept in sync on every review, so the presenter always has a
    live styled view of the deck as it takes shape.
  - **deliverable**: renders `final.md` as the shareable static site,     `strict`/`free-form`.
Both produce the same styled Reveal.js deck to `output/html/index.html`; only the source md differs.

Why it exists: unlike the native `.pptx` render (which follows prose and silently drops the
styled layer), this is **deterministic code** — icons, callouts, code surfaces, and card
strips always render, because the same `html_style` components emit them every time. It needs
no Cowork and no native skill.

Pipeline: `convert.py` (→ per-slide units, `--draft` for the in-progress view) → classify each slide
against the catalog (`slide_model._classify`) → render its template via `html_style`
(content-matched Material icons fetched by `icon_fetch.py`, inlined) → one self-contained
`.html` file. Only images are external (shown as placeholders until real assets are wired).

Usage:
    python3 build_html.py --talk talks/<Talk> [--draft] [-o <out.html>]

Requires **jinja2** (`pip install jinja2`) — the per-slide-type markup lives in Jinja templates
under `templates/html/`. Requires network on first run (icon catalog + icon fetch, cached under
output/.icons); the output HTML is fully offline/self-contained.
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


# Authored duplicate title pages — a slide whose whole purpose is a second cover
# (title/subtitle/author). The real cover is synthesized from frontmatter (see render()),
# so these are always redundant and get dropped, like the standalone Agenda.
_COVER_DUP = {"portada", "cover", "caratula", "titulo", "title", "title slide", "portada de la charla"}

_SEC_SPLIT_RE = re.compile(r"\s+[—–-]\s+")


def _sections(parsed: list) -> list:
    """The canonical ordered section list, parsed from the Agenda slide's
    '**Sections (in delivery order):**' block — used to re-show the agenda at each section start."""
    for u in parsed:
        if _norm(u.get("title", "")) == "agenda":
            out = []
            for b in u.get("body", []):
                if re.search(r"sections?\b.*\bdelivery|narrative\s+arc", b, re.I):
                    continue                                      # header lines, not sections
                nm = _SEC_SPLIT_RE.split(b, 1)[0]                 # drop the '— description' tail
                nm = re.sub(r"^\d+[.)]\s*", "", nm).strip()       # drop a leading 'N.'
                nm = re.sub(r"\s*\([^)]*\bmin\b[^)]*\)\s*$", "", nm).strip()  # drop a trailing '(~N min)' (keep '(2023)')
                if nm:
                    out.append(nm)
            return out
    return []


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
    _hs.load_catalog(cache)               # match concepts against the live Material Symbols catalog
    hints = _template_hints(md_text)
    converted = _convert.convert(md_text, draft=draft)
    units = _convert._split_into_slide_units(converted)

    parsed = [_sm._parse_unit(unit, talk_root, out_dir) for unit in units]
    agenda = _sections(parsed)                                    # canonical section list (from the Agenda slide)
    agenda_norm = [_norm(s) for s in agenda]

    slides_html = []
    log_entries = []
    section = ""              # current section name (for the pill)
    active = -1               # index of the active section (for the re-shown agenda)
    secno = 0                 # running section counter (for the divider's big number)
    n = len(units)
    for i, u in enumerate(parsed, 1):
        if _norm(u["title"]) in _COVER_DUP:
            continue                                              # authored duplicate title page — the cover is synthesized
        kind = hints.get(_norm(u["title"])) or _sm._classify(u)   # author hint overrides
        if kind in ("fallback", "content-text") and sum(1 for b in u["body"] if b.count("|") >= 2) >= 2:
            kind = "comparison"                                   # a pipe-table → comparison
        if kind == "divider":
            nt = _norm(u["title"])
            if nt == "agenda":
                continue                                          # drop the standalone agenda — it re-shows at each section start
            mi = next((j for j, sn in enumerate(agenda_norm)
                       if sn and (sn == nt or sn in nt or nt in sn)), -1)
            # A section start is: an agenda-matched divider, or — when there's no agenda list —
            # every divider (they *are* the sections). Sub-openers (agenda exists, no match) keep
            # the current section. Enrich `section` here so every following slide carries it.
            number = None
            if mi >= 0:
                active = mi
                section = agenda[mi]
                number = mi + 1
            elif not agenda:
                section = re.sub(r"^\d+[.)]\s*", "", u["title"])
                secno += 1
                number = secno
            if agenda and (mi >= 0 or nt == "agenda"):            # the Agenda slide, or a section start → the agenda list
                inner = _hs.section_agenda(agenda, active, u["title"])
            else:                                                 # no agenda list, or a sub-opener → styled section title
                u["_number"] = number                             # None for sub-openers (no number shown)
                u["title"] = re.sub(r"^\d+[.)]\s*", "", u["title"])
                inner = _hs.render_slide(kind, u, "", cache)
        else:
            inner = _hs.render_slide(kind, u, section, cache)
        notes = u.get("notes", "")
        aside = f'<aside class="notes">{_hs._esc(notes)}</aside>' if notes else ""
        slides_html.append(f'<section class="slide" data-kind="{kind}">{inner}{aside}</section>')
        log_entries.append((i, u, kind))

    fm = _frontmatter(md_text)
    if fm.get("presentation"):                                    # contractually-fixed cover first
        slides_html.insert(0, f'<section class="slide cover-slide">{_hs.cover_slide(fm, talk_root)}</section>')

    # per-slide template-decision log beside the deck (slide-templates.md → Template decision log)
    _sm._write_template_log(log_entries, talk_root, "html", out_dir / "template-log.md")

    return _hs.page("".join(slides_html), title=title, subtitle=subtitle), n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="render the in-progress draft.md (default: final.md)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="output .html (default under output/html/)")
    args = ap.parse_args(argv)

    src = args.talk / ("draft.md" if args.draft else "final.md")
    if not src.is_file():
        print(f"failed: {src} not found", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    title = fm.get("presentation", args.talk.name)
    subtitle = " · ".join(x for x in (fm.get("class", ""), fm.get("presenter", "")) if x)

    out_dir = args.talk / "output" / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = args.output or (out_dir / "index.html")

    html, n = render(text, args.talk, out_dir, args.draft, title, subtitle)
    out.write_text(html, encoding="utf-8")
    print(f"[html] {n} slides → {out}", file=sys.stderr)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
