#!/usr/bin/env python3
"""Shared helpers for the Talksmith reverse pipeline (pptx-extract / pptx-diff /
pptx-merge).

This module is **copied verbatim** into each of the three reverse-pipeline
skill directories so every skill stays independently installable. It holds
what `python-pptx` doesn't cover:

  1. Markdown-tree parsing — the `draft.md` / `final.md` shape (frontmatter,
     `# N. Section`, `## M. Slide`, `### Content|Sources|Speaker notes`),
     mirroring the regexes and field-walk logic in `polish_ascii.py`.
     `parse_md_slides()` returns a structured tree with 1-based line spans
     per field so callers (diff, merge) can anchor edits without re-parsing.
  2. Image content sniffing — `is_svg_icon()` and `is_png_icon()`, plus the
     intrinsic-dimension readers (`read_svg_dims`, `read_png_dims`,
     `read_jpeg_dims`) that back them. python-pptx's `image.size` uses
     Pillow, which doesn't parse SVG; and the icon signals (colorable-icon
     class, data-icon attr, zero `<text>` elements) live in SVG source.
  3. Two `lxml` drop-throughs for the pptx-parsing edge cases python-pptx
     doesn't expose cleanly:
       - `pic_svg_target(picture, slide_part)` — the `<asvg:svgBlip>` extension
         that carries the SVG twin of a raster `<p:pic>`.
       - `paragraph_is_bulleted(paragraph)` — checks `<a:pPr>` for `<a:buChar>`
         / `<a:buAutoNum>` (with `<a:buNone>` override).
  4. Utility: `sha256_bytes/file`, `TEMPLATE_MEDIA_RE` for logo/icon paths.

Requires: python-pptx (installed transitively via `pip install python-pptx`).
"""
from __future__ import annotations

import hashlib
import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Iterable

# --------------------------------------------------------------------------- #
# OOXML namespaces — used only by the two `_element` drop-throughs.
# --------------------------------------------------------------------------- #

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
_SVG = "http://www.w3.org/2000/svg"

# Namespaces bundle for lxml find/xpath calls in the drop-throughs.
_NS = {"p": _P, "a": _A, "r": _R, "asvg": _ASVG}


def _pic_blip(el):
    """Locate the primary `<a:blip>` inside a `<p:pic>`.

    Handles both spellings that appear across Cowork / python-pptx output:
    `<p:blipFill>/<a:blip>` (Cowork strict pictures) and `<a:blipFill>/<a:blip>`
    (some hand-authored pics). Returns the `<a:blip>` element or None.
    """
    blip = el.find("p:blipFill/a:blip", _NS)
    if blip is not None:
        return blip
    return el.find("a:blipFill/a:blip", _NS)


# --------------------------------------------------------------------------- #
# lxml drop-through 1: SVG twin of a `<p:pic>`
# --------------------------------------------------------------------------- #

def pic_raster_target(picture, slide_part) -> str | None:
    """Return the raster (PNG/JPG) target's package part-path for a picture.

    python-pptx's `picture.image.filename` returns only the media basename
    (`image.png`), which collides across slides and doesn't match the
    `image-1-*` cover-logo regex. Go through the relationship instead: the
    `<a:blip r:embed=…>` rId resolves to the actual `ppt/media/…` part.
    """
    blip = _pic_blip(picture._element)
    if blip is None:
        return None
    rid = blip.get(f"{{{_R}}}embed")
    if not rid:
        return None
    try:
        related = slide_part.related_part(rid)
    except (KeyError, AttributeError):
        return None
    return related.partname.lstrip("/")


def _pic_svg_blip(picture):
    """Locate the `<asvg:svgBlip>` extension inside a picture's blipFill."""
    blip = _pic_blip(picture._element)
    if blip is None:
        return None
    return blip.find("a:extLst/a:ext/asvg:svgBlip", _NS)


def pic_svg_target(picture, slide_part) -> str | None:
    """Return the SVG twin's package part-path for a picture, or None.

    A Cowork-emitted `<p:pic>` carries a raster in `<p:blipFill>/<a:blip>` and
    an SVG source in `<a:blip>/<a:extLst>/<a:ext>/<asvg:svgBlip>`. python-pptx
    exposes the raster via `picture.image` but not the SVG.
    """
    svg_blip = _pic_svg_blip(picture)
    if svg_blip is None:
        return None
    rid = svg_blip.get(f"{{{_R}}}embed")
    if not rid:
        return None
    try:
        related = slide_part.related_part(rid)
    except (KeyError, AttributeError):
        return None
    return related.partname.lstrip("/")


def pic_svg_blob(picture, slide_part) -> bytes | None:
    """Read the SVG twin's bytes for a picture, or None."""
    svg_blip = _pic_svg_blip(picture)
    if svg_blip is None:
        return None
    rid = svg_blip.get(f"{{{_R}}}embed")
    if not rid:
        return None
    try:
        related = slide_part.related_part(rid)
    except (KeyError, AttributeError):
        return None
    return related.blob


# --------------------------------------------------------------------------- #
# lxml drop-through 2: bullet-marker detection on a paragraph
# --------------------------------------------------------------------------- #

_P12_TC = "http://schemas.microsoft.com/office/powerpoint/2018/8/main"


def slide_comments(slide) -> list[dict]:
    """Extract reviewer comments (legacy `<p:cm>` + modern threaded `<p12:tc>`)
    for a slide. python-pptx doesn't expose these — we go through the slide
    part's relationships.

    Returns a list of dicts:
        {"kind": "legacy"|"threaded", "text": str, "author": str|None,
         "created": str|None, "pos": (x, y)|None}

    Both comment formats coexist in some decks (legacy for compatibility,
    threaded for Office 365 threads). Each is returned separately so a
    presenter can see the review history.
    """
    out: list[dict] = []
    try:
        rels = slide.part.rels
    except AttributeError:
        return out

    # Load author maps once per slide-part call (short-lived).
    def _load_authors(part) -> dict[str, str]:
        try:
            xml = part.blob
        except AttributeError:
            return {}
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return {}
        authors: dict[str, str] = {}
        # legacy <p:cmAuthor id="..." name="..."/>
        for el in root.findall(f".//{{{_P}}}cmAuthor"):
            aid = el.get("id"); name = el.get("name")
            if aid: authors[aid] = name or ""
        # threaded <p12:author id="..." name="..."/>
        for el in root.findall(f".//{{{_P12_TC}}}author"):
            aid = el.get("id"); name = el.get("name")
            if aid: authors[aid] = name or ""
        return authors

    for rel in rels.values():
        # Skip external-mode rels (hyperlinks) — `.target_part` raises on them.
        if getattr(rel, "is_external", False):
            continue
        try:
            target = getattr(rel.target_part, "partname", None)
        except ValueError:
            continue
        if not target:
            continue
        target_str = str(target).lower()
        try:
            xml = rel.target_part.blob
            root = ET.fromstring(xml)
        except (AttributeError, ET.ParseError):
            continue

        # Legacy comments part: `ppt/comments/commentN.xml`
        if "/comments/comment" in target_str:
            # Find the associated author part for id → name mapping.
            authors: dict[str, str] = {}
            try:
                for r2 in slide.part.package.iter_parts():
                    pn = str(r2.partname).lower()
                    if "commentauthors" in pn:
                        authors = _load_authors(r2)
                        break
            except AttributeError:
                pass
            for cm in root.findall(f".//{{{_P}}}cm"):
                text_el = cm.find(f"{{{_P}}}text")
                text = (text_el.text or "").strip() if text_el is not None else ""
                if not text:
                    continue
                aid = cm.get("authorId")
                pos_el = cm.find(f"{{{_P}}}pos")
                pos = None
                if pos_el is not None:
                    try:
                        pos = (int(pos_el.get("x", 0)), int(pos_el.get("y", 0)))
                    except ValueError:
                        pass
                out.append({
                    "kind": "legacy",
                    "text": text,
                    "author": authors.get(aid, "") if aid else None,
                    "created": cm.get("dt"),
                    "pos": pos,
                })

        # Modern threaded comments part: `ppt/threadedComments/threadedCommentN.xml`
        if "threadedcomment" in target_str:
            authors_t: dict[str, str] = {}
            try:
                for r2 in slide.part.package.iter_parts():
                    pn = str(r2.partname).lower()
                    if "authors" in pn and "threadedcomment" not in pn:
                        authors_t = _load_authors(r2)
                        break
            except AttributeError:
                pass
            for tc in root.findall(f".//{{{_P12_TC}}}tc"):
                text_el = tc.find(f"{{{_P12_TC}}}text")
                text = (text_el.text or "").strip() if text_el is not None else ""
                if not text:
                    continue
                pos_el = tc.find(f"{{{_P12_TC}}}pos")
                pos = None
                if pos_el is not None:
                    try:
                        pos = (int(pos_el.get("x", 0)), int(pos_el.get("y", 0)))
                    except ValueError:
                        pass
                out.append({
                    "kind": "threaded",
                    "text": text,
                    "author": authors_t.get(tc.get("authorId", ""), None),
                    "created": tc.get("created"),
                    "pos": pos,
                })
    return out


def paragraph_is_bulleted(paragraph) -> bool:
    """True if the paragraph renders with a bullet marker.

    python-pptx exposes `paragraph.level` but not "is a bullet char/number
    active." Check `<a:pPr>` for `<a:buChar>` / `<a:buAutoNum>`, with
    `<a:buNone>` overriding.
    """
    pPr = paragraph._pPr
    if pPr is None:
        return False
    if pPr.find(f"{{{_A}}}buNone") is not None:
        return False
    return (pPr.find(f"{{{_A}}}buChar") is not None
            or pPr.find(f"{{{_A}}}buAutoNum") is not None)


# --------------------------------------------------------------------------- #
# intrinsic-dimension readers
# --------------------------------------------------------------------------- #

def read_svg_dims(blob: bytes) -> tuple[float, float] | None:
    """Return (w, h) from `<svg viewBox=…>`, falling back to width/height.

    Used by both is_svg_icon (icon size threshold) and downstream diff/merge
    heuristics. python-pptx / Pillow don't parse SVG.
    """
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return None
    vb = root.get("viewBox")
    if vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            try:
                _x, _y, w, h = (float(p) for p in parts)
                if w > 0 and h > 0:
                    return w, h
            except ValueError:
                pass
    w_attr, h_attr = root.get("width"), root.get("height")
    if w_attr and h_attr:
        try:
            w = float(re.sub(r"[a-zA-Z%]+$", "", w_attr))
            h = float(re.sub(r"[a-zA-Z%]+$", "", h_attr))
            if w > 0 and h > 0:
                return w, h
        except ValueError:
            return None
    return None


def read_png_dims(blob: bytes) -> tuple[float, float] | None:
    if len(blob) < 24 or blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", blob[16:24])
    return (float(w), float(h)) if w and h else None


def read_jpeg_dims(blob: bytes) -> tuple[float, float] | None:
    if len(blob) < 4 or blob[:2] != b"\xff\xd8":
        return None
    i, n = 2, len(blob)
    while i < n:
        while i < n and blob[i] != 0xFF:
            i += 1
        while i < n and blob[i] == 0xFF:
            i += 1
        if i >= n:
            return None
        marker = blob[i]
        i += 1
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 7 > n:
                return None
            h, w = struct.unpack(">HH", blob[i + 3:i + 7])
            return (float(w), float(h)) if w and h else None
        if i + 2 > n:
            return None
        seg_len = struct.unpack(">H", blob[i:i + 2])[0]
        i += seg_len
    return None


def intrinsic_dims(name: str, blob: bytes) -> tuple[float, float] | None:
    lower = name.lower()
    if lower.endswith(".svg"):
        return read_svg_dims(blob)
    if lower.endswith(".png"):
        return read_png_dims(blob)
    if lower.endswith((".jpg", ".jpeg")):
        return read_jpeg_dims(blob)
    return None


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path) -> str | None:
    try:
        with open(path, "rb") as fh:
            h = hashlib.sha256()
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
            return h.hexdigest()
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# image content sniffing (icon detection)
# --------------------------------------------------------------------------- #

# Known non-content media (cover logo + branded icon library).
TEMPLATE_MEDIA_RE = re.compile(
    r"(/icon-[\w-]+\.(?:png|svg)|image-1-\d+\.(?:png|jpg|jpeg))$", re.I)


def is_png_icon(blob: bytes) -> bool:
    """PNG-only icons by intrinsic size (max ≤128 px).

    Bytes-per-pixel is deliberately NOT used: real ASCII-generated diagrams
    compress to 0.02–0.05 bytes/pixel and would be false-positived.
    """
    d = read_png_dims(blob)
    return bool(d and max(d[0], d[1]) <= 128)


def is_svg_icon(blob: bytes) -> bool:
    """Detect non-content SVGs (icons AND decorative containers).

    Three families surface in Cowork-generated decks:

      1. Branded icons — `class="colorable-icon"` or `data-icon="..."` /
         `data-prefix="fa..."` (FontAwesome).
      2. Tiny render size — root `<svg>` `width`/`height` both ≤ 128 px.
      3. Zero `<text>` elements — Satori-rendered card backgrounds,
         decorative masks. Real diagrams from the ASCII pipeline always
         carry label text; a text-less SVG at any dimension is decorative.

    Any of the three is decisive.
    """
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return False
    cls = root.get("class") or ""
    if "colorable-icon" in cls or "icon" in cls.split():
        return True
    if root.get("data-icon") or (root.get("data-prefix") or "").lower().startswith("fa"):
        return True

    def _px(v: str | None) -> float | None:
        if not v:
            return None
        try:
            return float(re.sub(r"[a-zA-Z%]+$", "", v))
        except ValueError:
            return None

    w = _px(root.get("width"))
    h = _px(root.get("height"))
    if w and h and w <= 128 and h <= 128:
        return True
    has_text = any(True for _ in root.iter(f"{{{_SVG}}}text"))
    if not has_text:
        return True
    return False


# --------------------------------------------------------------------------- #
# markdown-tree parsing (draft.md / final.md shape) — UNCHANGED
# --------------------------------------------------------------------------- #

H1_SECTION = re.compile(r"^# (\d+)\.\s*(.*)$")
H1_AGENDA = re.compile(r"^# (?:Agenda|Índice|Indice)\b", re.IGNORECASE)
H1_CONCL = re.compile(r"^# (?:Conclusion|Conclusiones|Conclusions)\b", re.IGNORECASE)
H1_ANY = re.compile(r"^# (?!#)(.+?)\s*$")
H2_SLIDE = re.compile(r"^## (\d+)\.\s*(.*)$")
H2_ANY = re.compile(r"^## (?!#)(.+?)\s*$")
H3_ANY = re.compile(r"^### (?!#)(.+?)\s*$")
H1_OR_H2 = re.compile(r"^#{1,2} ")
IMAGE_REF = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FENCE = re.compile(r"^```")
# HTML comment closer detection. In Markdown, `-->` closers always sit at the
# end of a line (often alone), never mid-line. Anchoring to end-of-line
# distinguishes real closers from ASCII payloads that happen to contain the
# substring `-->` mid-line — either as an ASCII arrow like `--->` (preceded
# by another `-`) OR as a rendered arrow like `<-- ... -->|` (followed by
# more content). The negative lookbehind AND end-of-line anchor together
# make this robust to both patterns.
COMMENT_CLOSE = re.compile(r"(?<!-)-->\s*$")

SKIP_SECTIONS = {"thesis", "open questions", "cut material"}


@dataclass
class MdImage:
    alt: str
    path: str
    line: int  # 1-based

    @property
    def basename(self) -> str:
        return PurePosixPath(self.path).name


@dataclass
class MdField:
    name: str
    heading_line: int
    body_start: int
    body_end: int
    body_lines: list[str] = field(default_factory=list)


@dataclass
class MdSlide:
    section_key: str
    section_title: str
    section_line: int
    slide_num: int
    title: str
    heading_line: int
    end_line: int
    fields: dict[str, MdField] = field(default_factory=dict)
    images: list[MdImage] = field(default_factory=list)

    @property
    def locator(self) -> str:
        return f"{self.section_key}.{self.slide_num}"

    def field_body(self, name: str) -> list[str]:
        f = self.fields.get(name.lower())
        return f.body_lines if f else []


def _section_key_for(line: str) -> tuple[str, str] | None:
    m = H1_SECTION.match(line)
    if m:
        return m.group(1), m.group(2).strip()
    if H1_AGENDA.match(line):
        m2 = H1_ANY.match(line)
        return "agenda", m2.group(1).strip() if m2 else "Agenda"
    if H1_CONCL.match(line):
        m2 = H1_ANY.match(line)
        return "conclusions", m2.group(1).strip() if m2 else "Conclusions"
    return None


def _read_lines(path_or_text: str, is_text: bool = False) -> list[str]:
    if is_text:
        return path_or_text.splitlines()
    with open(path_or_text, encoding="utf-8") as fh:
        return fh.read().splitlines()


def parse_md_slides(path_or_text: str, is_text: bool = False) -> dict:
    """Parse a draft.md/final.md-shaped file into a slide tree."""
    lines = _read_lines(path_or_text, is_text)
    n = len(lines)

    in_fence = False
    section_key = ""
    section_title = ""
    section_line = 0
    slide_bounds: list[tuple[int, str, str, int, int, str]] = []

    for i in range(n):
        ln = lines[i]
        if FENCE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        sec = _section_key_for(ln)
        if sec is not None:
            section_key, section_title = sec
            section_line = i + 1
            continue
        m2 = H2_SLIDE.match(ln)
        if m2:
            slide_bounds.append(
                (i, section_key, section_title, section_line,
                 int(m2.group(1)), m2.group(2).strip()))
            continue
        m2a = H2_ANY.match(ln)
        if m2a and not H2_SLIDE.match(ln):
            slide_bounds.append(
                (i, section_key, section_title, section_line, 0, m2a.group(1).strip()))

    slides: list[MdSlide] = []
    sections: dict[str, str] = {}
    for idx, (h_idx0, skey, stitle, sline, snum, stitle_slide) in enumerate(slide_bounds):
        end_idx0 = slide_bounds[idx + 1][0] - 1 if idx + 1 < len(slide_bounds) else n - 1
        clamp = end_idx0
        infence = False
        for j in range(h_idx0 + 1, end_idx0 + 1):
            if FENCE.match(lines[j]):
                infence = not infence
                continue
            if infence:
                continue
            if _section_key_for(lines[j]) is not None or H1_ANY.match(lines[j]):
                clamp = j - 1
                break
        end_idx0 = clamp
        slide = MdSlide(
            section_key=skey or "?", section_title=stitle, section_line=sline,
            slide_num=snum, title=stitle_slide, heading_line=h_idx0 + 1,
            end_line=end_idx0 + 1)
        if skey:
            sections[skey] = stitle
        _fill_slide_fields(lines, slide, h_idx0, end_idx0)
        slides.append(slide)

    return {"lines": lines, "slides": slides, "sections": sections}


def _fill_slide_fields(lines: list[str], slide: MdSlide, h_idx0: int, end_idx0: int) -> None:
    in_fence = False
    h3_positions: list[tuple[int, str]] = []
    for i in range(h_idx0 + 1, end_idx0 + 1):
        ln = lines[i]
        if FENCE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = H3_ANY.match(ln)
        if m:
            h3_positions.append((i, m.group(1).strip()))

    for k, (hi, name) in enumerate(h3_positions):
        body_start0 = hi + 1
        body_end0 = (h3_positions[k + 1][0] - 1) if k + 1 < len(h3_positions) else end_idx0
        body_lines = lines[body_start0:body_end0 + 1]
        slide.fields[name.lower()] = MdField(
            name=name, heading_line=hi + 1, body_start=body_start0 + 1,
            body_end=(body_end0 + 1) if body_end0 >= body_start0 else 0,
            body_lines=body_lines)

    in_fence = False
    in_comment = False
    for i in range(h_idx0 + 1, end_idx0 + 1):
        ln = lines[i]
        if FENCE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if "<!--" in ln and not COMMENT_CLOSE.search(ln):
            in_comment = True
            continue
        if in_comment:
            if COMMENT_CLOSE.search(ln):
                in_comment = False
            continue
        for m in IMAGE_REF.finditer(ln):
            slide.images.append(MdImage(alt=m.group(1), path=m.group(2), line=i + 1))


# --------------------------------------------------------------------------- #
# text normalization (shared by diff alignment + merge anchoring)
# --------------------------------------------------------------------------- #

_INLINE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def normalize_title(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Emoji-range regex — strips emoji + variation selectors used by prose
# normalization AND semantic-equivalence stripping. Defined before
# `normalize_prose` so it can reference it.
_EMOJI = re.compile(
    r"[\U0001F300-\U0001FAFF☀-➿⌀-⏿]️?", re.UNICODE)


def normalize_prose(s: str) -> str:
    s = _INLINE_COMMENT.sub("", s)
    s = _EMOJI.sub("", s)                  # ← was missing; caused difflib misalignments
    s = re.sub(r"^\s*[-*+]\s+", "", s)
    s = re.sub(r"^\s*>\s+", "", s)
    s = re.sub(r"[*_`#>]+", "", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _semantic_tokens(s: str) -> set[str]:
    """Reduce a content string to its semantically meaningful word set.

    Strips bullet/markdown markers, emojis, punctuation, and short filler
    words (articles, prepositions). What remains is the set of "meaningful"
    tokens — the ones that carry the sentence's meaning.
    """
    s = _INLINE_COMMENT.sub("", s.lower())
    s = _EMOJI.sub(" ", s)
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    STOPWORDS = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "by",
        "for", "with", "as", "is", "are", "was", "were", "be", "been",
        "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o",
        "de", "del", "en", "un", "que", "es", "se", "con", "por", "para",
        "un", "al", "lo", "las", "los", "sus",
    }
    return {w for w in s.split() if len(w) >= 3 and w not in STOPWORDS}


def content_semantically_contained(from_text: str, to_text: str,
                                    threshold: float = 0.8) -> bool:
    """True when `to_text` is a *formatting-reduced* version of `from_text`.

    Applies the rule "if the deck's rendered text carries a strict subset
    of the source's meaning (same key words, less prose), skip the change
    and preserve the original formatting". Distinguishes:

      - "🌡️ Baja (≈0)"                       (deck card heading — reduced)
      vs
      - "- Baja (≈0): casi siempre el candidato más probable → respuestas
         predecibles, repetibles, 'aburridas pero seguras'."   (source bullet)

    Both share the key tokens {baja}; the source strictly extends. Return
    True → the diff skips the change and the source wins.

    Rules:
      1. `to`'s meaningful tokens must be a subset of `from`'s (≥ threshold
         overlap ratio computed as |from ∩ to| / |to|).
      2. `from` must be strictly longer (more tokens) than `to` — the deck
         is a reduction, not an equal peer with different words.
      3. If `to` is empty after tokenizing (pure formatting/emoji), treat as
         reduction (skip).
    """
    to_toks = _semantic_tokens(to_text)
    if not to_toks:
        return True
    from_toks = _semantic_tokens(from_text)
    if not from_toks:
        return False
    if len(from_toks) < len(to_toks):
        return False
    overlap = len(from_toks & to_toks) / len(to_toks)
    return overlap >= threshold


def content_units(body_lines: Iterable[str]) -> list[str]:
    """Split a field body into comparable, non-empty, prose-normalized units."""
    units: list[str] = []
    in_fence = False
    in_comment = False
    for raw in body_lines:
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = raw.strip()
        if in_comment:
            if COMMENT_CLOSE.search(raw):
                in_comment = False
            continue
        if "<!--" in raw and not COMMENT_CLOSE.search(raw):
            in_comment = True
            continue
        if not stripped or stripped in ("---", "***", "___"):
            continue
        if stripped.startswith("<!--") or stripped.startswith("-->"):
            continue
        if IMAGE_REF.sub("", stripped).strip() == "":
            continue
        norm = normalize_prose(raw)
        if norm:
            units.append(norm)
    return units
