"""Slide parsing + template classification for the Talksmith deck renderer.

The *input* half of the renderer: it reads one slide's markdown and decides **what it is**.
`_parse_unit` extracts the catalog signals (title, body, labeled items, images, code);
`_classify` maps those to a template id from `config/pptx-styles/slide-templates.md`. The
markdown-cleaning rules live here too (off-slide `### Notes`/`### Sources` skipping, blockquote
/ strikethrough / empty-bullet handling).

The *output* half — turning a classified unit into styled HTML — lives in `html_style.py`.
`build_html.py` wires them together. (This module was extracted from the retired Pillow
`build_preview.py`; only the parse/classify logic survived.)
"""

from __future__ import annotations

import re
from pathlib import Path

_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_INLINE_MD_RE = re.compile(r"\*\*|__|~~|`|(?<!\w)[*_](?!\s)")   # bold/italic/code/strikethrough markers
_BLOCKQUOTE_RE = re.compile(r"^\s*>+\s*")                        # leading `> ` blockquote marker(s)

# Labeled-item signals (detected BEFORE inline-markdown is stripped) — a labeled
# enumeration renders as cards, never bullets (slide-templates.md universal invariant).
_EMOJI = r"(?:[^\w\s]️?\s*)?"
_BOLD_ITEM_RE = re.compile(rf"^\s*[-*+]\s+{_EMOJI}\*\*(.+?)\*\*[:：]?\s*(.*)$")   # - **Label** body
_H34_RE = re.compile(r"^(#{3,4})\s+(.+?)\s*$")                                     # ### / #### Label
# H3/H4 sections that are off-slide: presenter notes are CAPTURED (emitted as Reveal speaker
# notes — `<aside class="notes">`, shown in speaker view, never on the slide face); pure
# provenance is dropped. This mirrors the native .pptx render (notes → notes pane).
_NOTES_SECTIONS = {"notes", "speaker notes", "presenter notes", "presenter comments", "comments"}
_DROP_SECTIONS = {"sources", "source", "provenance"}
_ORDERED_RE = re.compile(
    r"^\s*(?:\d+\s*[.)]|paso\s+\w+|step\s+\w+|fase\s+\w+|etapa\s+\w+|caso\s+\w+)\b", re.I)
_PLAIN_BULLET_RE = re.compile(r"^\s*[-*+•]\s+")
_EMPTY_BULLET_RE = re.compile(r"^\s*[-*+•]\s*$")                 # a bullet marker with no content ("- ")
_NUM_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")               # a numbered step line "1. …" (NOT bullet-prefixed)
_NUM_LABEL_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*[—–:\-]*\s*(.*)$")  # "**Label** — body" inside a step
_FENCE_RE = re.compile(r"^\s*```")
# Author section-break markers in a title, e.g. `## 1. 〔divisor〕 …` — stripped from the shown
# title; `divisor`/`backup` force the slide to a divider even at H2 (slide-templates.md §is_divider).
_MARKER_RE = re.compile(r"〔([^〕]*)〕")
_DIVIDER_MARKERS = {"divisor", "divider", "backup", "sección", "seccion", "section"}


def _clean_inline(s: str) -> str:
    """Strip inline markdown emphasis (**bold**, *italic*, `code`, ~~strike~~) and a leading
    blockquote marker, leaving readable plain text."""
    return _INLINE_MD_RE.sub("", _BLOCKQUOTE_RE.sub("", s)).strip()


_LAZY_NUM_RE = re.compile(r"^(\s*)(\d+)[.)]\s+.+$")   # a "1. …" / "1) …" ordered-item line


def _recover_ordered(lines: list[str]) -> list[str]:
    """Curate a numbered list whose continuation items lost their markers.

    Authoring (or a reconcile round-trip) sometimes drops the `2.`/`3.` markers of an
    ordered list, leaving `1. first` followed by bare continuation lines. The parser
    already renders those bare lines as *separate* blocks — so they were three items all
    along — but without the markers they come out as a big numbered lead plus mismatched
    panels instead of one uniform list. Restore the markers so the slide reads as the
    ordered list it is. Well-formed lists (real `2.`, `3.` already present) are untouched.
    """
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        m = _LAZY_NUM_RE.match(lines[i])
        out.append(lines[i])
        if m and int(m.group(2)) == 1:
            j, run = i + 1, []
            while j < n:
                s = lines[j].strip()
                if not s:
                    break                                   # blank line ends the list
                if _LAZY_NUM_RE.match(lines[j]):
                    run = []                                # already-numbered sibling → well-formed, leave alone
                    break
                if (_PLAIN_BULLET_RE.match(lines[j]) or _H34_RE.match(lines[j]) or
                        _FENCE_RE.match(lines[j]) or _IMG_RE.search(lines[j]) or
                        s[0] in "*_>#"):
                    break                                   # a bullet/subhead/code/image/quote is not a lost item
                run.append(j); j += 1
            if run:
                indent = m.group(1)
                for k, idx in enumerate(run, start=2):
                    out.append(f"{indent}{k}. {lines[idx].strip()}")
                i = j
                continue
        i += 1
    return out


def _parse_unit(md: str, talk_root: Path, asset_dir: Path) -> dict:
    """Extract the catalog classification signals from a slide unit.

    Returns a dict: title, level (1=divider/H1), body (plain lines, no items),
    items (list of {label, body}), ordered (bool), images (resolved), has_code,
    code_lines. Labeled items are detected on the *raw* line (before inline markdown
    is stripped) so a labeled enumeration is never mistaken for prose/bullets.
    """
    title, level, body, images = "", 0, [], []
    items: list[dict] = []
    code_lines: list[str] = []
    notes: list[str] = []              # captured presenter notes → Reveal speaker view
    in_code = False
    mode: str | None = None            # None | 'notes' (capture) | 'drop' (discard)
    cur: dict | None = None            # the item currently accumulating body lines
    saw_numbered = False
    # A numbered list (≥2 "1. …" lines) is a step sequence → parse those lines as ordered items.
    # A single numbered line is left as prose (so it doesn't swallow the lines that follow it).
    # Sources with dropped 2./3. markers are repaired upstream by `curate.py` (deterministic
    # `_recover_ordered`), not silently here — the source stays the single source of truth.
    numbered_mode = sum(1 for ln in md.splitlines() if _NUM_ITEM_RE.match(ln)) >= 2

    def _flush():
        nonlocal cur
        if cur is not None:
            cur.pop("_num", None)
            cur["body"] = cur["body"].strip()
            items.append(cur)
            cur = None

    for raw in md.splitlines():
        if _FENCE_RE.match(raw):
            if mode is None:
                in_code = not in_code
            elif mode == "notes":
                notes.append(raw)
            continue
        if in_code:
            code_lines.append(raw)
            continue
        head = _HEAD_RE.match(raw.strip())
        if head and not title:
            title = _clean_inline(head.group(2))
            level = len(head.group(1))
            m = _MARKER_RE.search(title)              # 〔divisor〕/〔Backup〕 → divider even at H2 (slide-templates.md)
            if m:
                if m.group(1).strip().lower() in _DIVIDER_MARKERS:
                    level = 1
                title = re.sub(r"\s{2,}", " ", _MARKER_RE.sub("", title)).strip()
            continue
        if mode is None:
            for im in _IMG_RE.finditer(raw):
                images.append((im.group(1), im.group(2)))
        line = _IMG_RE.sub("", raw).rstrip()
        if not line.strip():
            if mode is None and cur is not None and cur.get("_num"):
                _flush()                              # a blank line ends a numbered step, so a trailing
                                                      # pull-quote / paragraph stays a separate block
            continue
        if _EMPTY_BULLET_RE.match(line):
            continue                                  # empty bullet ("- ") — not content
        bold = _BOLD_ITEM_RE.match(line)
        sub = _H34_RE.match(line)
        num = _NUM_ITEM_RE.match(line) if numbered_mode else None
        if bold:
            _flush(); mode = None
            cur = {"label": _clean_inline(bold.group(1)), "body": _clean_inline(bold.group(2))}
        elif num:
            _flush(); mode = None; saw_numbered = True
            lm = _NUM_LABEL_RE.match(num.group(1))     # "**Label** — body" or a plain sentence
            if lm:
                cur = {"label": _clean_inline(lm.group(1)), "body": _clean_inline(lm.group(2)), "_num": True}
            else:
                cur = {"label": "", "body": _clean_inline(num.group(1)), "_num": True}
        elif sub:
            _flush()
            low = _clean_inline(sub.group(2)).strip().lower()
            if low in _NOTES_SECTIONS:
                mode = "notes"; cur = None            # capture into speaker notes
            elif low in _DROP_SECTIONS:
                mode = "drop"; cur = None             # provenance — discard
            else:
                mode = None
                cur = {"label": _clean_inline(sub.group(2)), "body": ""}
        elif mode == "notes":
            notes.append(_clean_inline(_PLAIN_BULLET_RE.sub("", line)))
        elif mode == "drop":
            continue
        elif cur is not None and not head:
            cur["body"] = (cur["body"] + " " + _clean_inline(_PLAIN_BULLET_RE.sub("", line))).strip()
        elif not head:
            body.append(_clean_inline(_PLAIN_BULLET_RE.sub("", line)))
    _flush()

    ordered = saw_numbered or any(_ORDERED_RE.match(it["label"]) for it in items) or \
        any(_ORDERED_RE.match(b) for b in body)

    resolved = []
    for alt, ref in images:
        if ref.startswith(("http://", "https://")):
            resolved.append((alt, None)); continue
        cand = [asset_dir / ref, talk_root / ref, Path(ref)]
        resolved.append((alt, next((c for c in cand if c.is_file()), None)))

    return {"title": title, "level": level, "body": body, "items": items,
            "ordered": ordered, "images": resolved,
            "has_code": bool(code_lines), "code_lines": code_lines,
            "notes": " ".join(n for n in notes if n).strip()}


def _classify(u: dict) -> str:
    """Map a parsed unit to a catalog template id (slide-templates.md)."""
    if u["level"] == 1:
        return "divider"
    if u["has_code"]:
        return "code-example"
    ni, nimg = len(u["items"]), len(u["images"])
    words = sum(len(b.split()) for b in u["body"])
    if nimg >= 4 and ni < 2:
        return "image-grid"
    if ni >= 2:
        if u["ordered"]:
            return "process"
        if nimg >= 1:                        # any source image → figures, never concept-breakdown
            return "figures"
        return "concept-breakdown"           # labeled set, no source image (renderer adds icons)
    if ni == 1:
        return "single-point"
    if nimg >= 4:
        return "image-grid"
    if nimg >= 1:
        return "content-image"
    if len(u["body"]) <= 2 and words <= 18 and u["title"]:
        return "statement"
    # A few short parallel lines under a title (no labels, images or code) — an anaphora /
    # enumeration like "No hubo hackers. No hubo malware. No hubo intrusión." Render as an
    # icon-list (icon + line per row), not a prose fallback. Most lines must be short (a long
    # paragraph stays fallback); the render synthesizes the rows from the lines.
    short = [b for b in u["body"] if len(b.split()) <= 9]
    if u["title"] and 2 <= len(u["body"]) <= 5 and len(short) >= len(u["body"]) - 1 and len(short) >= 2:
        return "icon-list"
    return "fallback"


def _signals(u: dict) -> dict:
    """The classification signals for one unit (mirrors slide-templates.md glossary)."""
    return {
        "labeled_items": len(u["items"]),
        "images": len(u["images"]),
        "has_code": u["has_code"],
        "ordered": u["ordered"],
        "body_words": sum(len(b.split()) for b in u["body"]),
        "level": u["level"],
    }


def _log_entry(index: int, u: dict, kind: str) -> str:
    # The per-template "why it applies" rationale is NOT restated here — it lives once in
    # slide-templates.md (this log's header points there). We log only what's computed from the
    # slide: the chosen template, the raw signals, and any review flags.
    s = _signals(u)
    flags = []
    if kind == "fallback":
        flags.append("fallback — catalog gap, review")
    if kind == "content-image" and s["body_words"] > 60 and s["images"] == 1:
        flags.append("prose-heavy — could be content-text/restructure")
    if s["labeled_items"] == 1 and kind != "single-point":
        flags.append("single-labeled-item — verify single-point vs concept")
    sig = " ".join(f"{k}={v}" for k, v in s.items())
    lines = [
        f"## Slide {index:02d} — {u['title'] or '(untitled)'}",
        f"- template: `{kind}`  (rationale → slide-templates.md)",
        f"- signals: {sig}",
        f"- flags: {', '.join(flags) if flags else '—'}",
    ]
    return "\n".join(lines)


def _write_template_log(entries: list, talk: Path, style: str, out_path: Path) -> None:
    """Persist the per-slide template-decision log (slide-templates.md → Template decision log)."""
    from collections import Counter
    tally = Counter(k for _, _, k in entries)
    fallbacks = tally.get("fallback", 0)
    head = [
        f"# Template decision log — {talk.name} · {style} · {len(entries)} slides",
        "",
        "Per-slide record of which catalog template was chosen and why, for review and to "
        "improve `slide-templates.md`. See that file → *Template decision log*.",
        "",
        "**Tally:** " + ", ".join(f"{k} ×{n}" for k, n in tally.most_common()),
        f"**Fallbacks:** {fallbacks}",
        "",
        "---",
        "",
    ]
    body = "\n\n".join(_log_entry(i, u, k) for i, u, k in entries)
    out_path.write_text("\n".join(head) + body + "\n", encoding="utf-8")
