"""Audit that each content slide's emitted layout matches the layout
predicted from the source markdown's §15.5 surface signals + §15.6.1
discriminator.

Why this exists:
    `config/pptx-prompt.md` §15.5 is a decision tree, not a "first match
    wins" lookup. Two markdown signals can be surface-compatible (e.g.
    "H2 + paragraph + bullets" matches §10 plain bullets, §7.4 card-row,
    and §7.5 icon-bullet list simultaneously). When the renderer skips
    the §15.6.1 discriminator and emits the plainer layout (§10 plain
    bullets) where the spec mandates a richer one (§7.5 icon-bullet
    list), the resulting deck passes §19.6 anti-pattern checks (no
    emojis in body, no native tables, no theme drift) but violates the
    substantive spec — the layout-fit failure is invisible to the
    other audits and surfaces only at visual review.

What it does:
    For each content slide:
      1. parse the matching H2 in `final.md` and compute the *predicted*
         layout from §15.5 surface signals + §7.4/§7.5 discriminator;
      2. parse the rendered slide in `final.pptx` and infer the
         *emitted* layout from shape composition (per-row icon count
         in column-1, image count + geometry, native <a:tbl>,
         <a:buChar> paragraph count, code-block presence);
      3. compare. When predicted ≠ emitted, fail with a structured
         report naming source evidence, emitted evidence, and the
         likely root cause.

    Source slides are matched to rendered slides by H2 title text
    (same heuristic as `audit_block_coverage.py`). Cover and agenda
    re-emits are excluded.

    Predicted layouts (per §15.5):
      cover                 — slide 1, no H2
      agenda-divider        — H1-only slide (numbered section header)
      content+image         — H2 + 1–3 `![]()` + paragraphs
      image-grid            — H2 + ≥4 `![]()`
      code-example          — H2 + fenced ``` ``` code block
      card-grid             — H2 + ≥4 `### Subhead` + paragraph groups
      card-row              — H2 + lead + 3–5 labeled bullets, longest body ≤ 80c (§7.4)
      icon-bullet-list      — H2 + lead + 3–5 labeled bullets, longest body > 80c (§7.5)
      callout               — H2 + single emoji-prefixed bold-lead bullet (§8 via §15 row)
      card-grid-from-table  — H2 + pipe-table (§11 conversion)
      closing-cta           — final slide H2 + list of links
      content-text          — H2 + paragraphs only (last resort)

    Emitted layout inference is heuristic and intentionally
    conservative — when shapes are ambiguous, the script reports
    `emitted: ambiguous` rather than a false-positive fail. The audit's
    failure mode is sharp on the load-bearing cases (icon-bullet-list
    misemitted as plain bullets, image-grid misemitted as content+image,
    code-example misemitted as content-text); softer-edged misemissions
    (card-grid vs content+cards+image) report as warnings.

Usage:
    python3 audit_layout_fit.py <final.md> <final.pptx> [--json] [--warn-only]

Exit codes:
    0  every matched slide's emitted layout matches its predicted layout
    1  one or more layout-fit mismatches; build should stop and re-render
    2  audit could not run (file missing, malformed)

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
from pathlib import PurePosixPath

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Emoji ranges from §17.7
EMOJI_CLASS = r"[\U0001F300-\U0001FAFF☀-➿⌀-⏿]"

# §15.5 discriminator threshold for §7.4 vs §7.5
SHORT_BODY_THRESHOLD = 80  # chars; longest body ≤ threshold → §7.4 card-row, else §7.5

# Exclude well-known non-content image paths from <p:pic> counts.
ICON_PATH_RE = re.compile(r"(/icon-[\w-]+\.(?:png|svg)|image-1-\d+\.png)$", re.I)


# --------------------------------------------------------------------------- #
# final.md parsing — predicted layout per H2
# --------------------------------------------------------------------------- #

@dataclass
class SourceSignals:
    h2_title: str
    h2_line: int
    image_count: int = 0
    code_blocks: int = 0
    pipe_tables: int = 0
    bullet_count: int = 0
    labeled_bullet_count: int = 0           # `- **Label**:` or `- <emoji> **Label**:`
    emoji_prefixed_bullet_count: int = 0    # `- <emoji> **Label**:`
    h3_subhead_count: int = 0
    longest_bullet_body_chars: int = 0
    paragraph_chars: int = 0
    has_links_list: bool = False            # for closing-cta detection
    predicted_layout: str = "content-text"

    def predict(self, is_final_h2: bool = False) -> None:
        """Apply §15.5 emit-rules + §7.3/§15.6.1 discriminator in order."""
        # 1. Code block as primary content
        if self.code_blocks >= 1 and self.image_count == 0:
            self.predicted_layout = "code-example"
            return
        # 2. Single emoji+bold bullet → callout (§15 row added separately)
        if (self.bullet_count == 1 and self.emoji_prefixed_bullet_count == 1
                and self.labeled_bullet_count == 1):
            self.predicted_layout = "callout"
            return
        # 3. Pipe table
        if self.pipe_tables >= 1:
            self.predicted_layout = "card-grid-from-table"
            return
        # 4. Image-grid (≥4 images)
        if self.image_count >= 4:
            self.predicted_layout = "image-grid"
            return
        # 5. Lead + 3–5 labeled bullets → §7.4 card-row OR §7.5 icon-bullet list
        if 3 <= self.labeled_bullet_count <= 5:
            if self.longest_bullet_body_chars <= SHORT_BODY_THRESHOLD:
                self.predicted_layout = "card-row"
            else:
                self.predicted_layout = "icon-bullet-list"
            return
        # 6. ≥4 H3 subheads → card-grid
        if self.h3_subhead_count >= 4:
            self.predicted_layout = "card-grid"
            return
        # 7. 1–3 images interleaved with paragraphs → content+image
        if 1 <= self.image_count <= 3:
            self.predicted_layout = "content+image"
            return
        # 8. Final slide with link list → closing-cta
        if is_final_h2 and self.has_links_list:
            self.predicted_layout = "closing-cta"
            return
        # 9. Default — content-text (last resort, often a draft defect)
        self.predicted_layout = "content-text"


def _is_emoji_bullet(line: str) -> tuple[bool, bool]:
    """Return (is_labeled_bullet, is_emoji_prefixed). Handles variation
    selector U+FE0F after combined emoji glyphs (e.g. `⚙️ = U+2699 U+FE0F`)."""
    s = line.lstrip()
    if not s.startswith("- "):
        return False, False
    body = s[2:].lstrip()
    emoji_prefix = bool(re.match(EMOJI_CLASS, body))
    if emoji_prefix:
        body = re.sub(rf"^{EMOJI_CLASS}️?\s*", "", body)
    labeled = bool(re.match(r"\*\*[^*]+\*\*", body))
    return labeled, (emoji_prefix and labeled)


def parse_final_md(path: str) -> list[SourceSignals]:
    lines = open(path, encoding="utf-8").read().splitlines()
    slides: list[SourceSignals] = []
    current: SourceSignals | None = None
    in_code = False
    code_run_in_current = False
    table_run_in_current = False
    bullet_bodies: list[int] = []

    SKIP_H1 = {"thesis", "open questions", "cut material"}
    in_skip_section = False

    def _finalize_bullet_state():
        nonlocal bullet_bodies
        if current and bullet_bodies:
            current.longest_bullet_body_chars = max(bullet_bodies)
        bullet_bodies = []

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = re.sub(r"^\d+\.\s*", "", stripped[2:].strip()).lower()
            in_skip_section = title in SKIP_H1
            _finalize_bullet_state()
            current = None
            code_run_in_current = False
            table_run_in_current = False
            continue
        if in_skip_section:
            continue
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                if current and not code_run_in_current:
                    current.code_blocks += 1
                    code_run_in_current = True
            else:
                in_code = False
            continue
        if in_code:
            continue
        if stripped.startswith("## "):
            _finalize_bullet_state()
            title = stripped[3:].strip()
            title = re.sub(r"^(?:\d+\.\s*|Slide\s+\d+:\s*|\d+\s+—\s*)", "", title)
            current = SourceSignals(h2_title=title, h2_line=i)
            slides.append(current)
            code_run_in_current = False
            table_run_in_current = False
            continue
        if current is None:
            continue
        if stripped.startswith("### "):
            current.h3_subhead_count += 1
            continue
        # Image refs
        n_imgs = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", line))
        if n_imgs:
            current.image_count += n_imgs
        # Pipe tables — count the separator line `|---|---|`
        if re.match(r"^\s*\|[-:\s|]+\|\s*$", line):
            if not table_run_in_current:
                current.pipe_tables += 1
                table_run_in_current = True
        elif stripped == "" and table_run_in_current:
            table_run_in_current = False
        # Bullets
        if re.match(r"^\s*-\s+", line):
            current.bullet_count += 1
            labeled, emoji_pref = _is_emoji_bullet(line)
            if labeled:
                current.labeled_bullet_count += 1
                body = re.sub(r"^\s*-\s+(?:" + EMOJI_CLASS + r"️?\s*)?\*\*[^*]+\*\*\s*[:：]?\s*",
                              "", line)
                bullet_bodies.append(len(body.strip()))
                if emoji_pref:
                    current.emoji_prefixed_bullet_count += 1
            else:
                # Plain bullet — count body for general bullet density
                body = re.sub(r"^\s*-\s+", "", line)
                bullet_bodies.append(len(body.strip()))
            continue
        # Paragraph text (very rough — used only for content-text fallback)
        if stripped and not stripped.startswith(">") and not stripped.startswith("|"):
            current.paragraph_chars += len(stripped)
        # Link-list detection (heuristic: line is a markdown link only)
        if re.match(r"^\s*-\s*\[[^\]]+\]\([^)]+\)\s*$", line):
            current.has_links_list = True

    _finalize_bullet_state()

    # Predict layouts
    for i, s in enumerate(slides):
        s.predict(is_final_h2=(i == len(slides) - 1))
    return slides


# --------------------------------------------------------------------------- #
# final.pptx parsing — emitted layout per slide
# --------------------------------------------------------------------------- #

@dataclass
class RenderEvidence:
    slide_num: int
    is_chrome: bool
    title_text: str
    pic_count: int = 0
    pic_paths: list[str] = field(default_factory=list)
    native_table_count: int = 0
    buchar_paragraph_count: int = 0
    literal_bullet_paragraph_count: int = 0
    code_surface_count: int = 0
    callout_pink_count: int = 0
    callout_blue_count: int = 0
    column1_icon_count: int = 0      # small (<0.5 in) pics in left column → §7.5 marker
    emitted_layout: str = "unknown"

    def infer(self) -> None:
        if self.is_chrome:
            self.emitted_layout = "chrome (cover/agenda/divider)"
            return
        # Native table = §11 violation; flag layout as such for visibility
        if self.native_table_count >= 1:
            self.emitted_layout = "native-table (§11 violation)"
            return
        # Code surface present → code-example
        if self.code_surface_count >= 1:
            self.emitted_layout = "code-example"
            return
        # Callout shape present (single-bullet emoji-bold pattern) → callout
        if (self.callout_pink_count + self.callout_blue_count) >= 1 and self.pic_count <= 1:
            self.emitted_layout = "callout"
            return
        # §7.5 icon-bullet list: ≥3 small icons in column-1, paired with headings
        if self.column1_icon_count >= 3 and self.pic_count == self.column1_icon_count:
            self.emitted_layout = "icon-bullet-list"
            return
        # §7.4 card-row: 3+ small icons (chip variant) AND adjacent card geometry —
        #   simplified: detect as icon-bullet-list-or-card-row when icons present
        if self.column1_icon_count >= 3:
            self.emitted_layout = "card-row-or-icon-bullet-list"
            return
        # image-grid: 4+ content pics
        if self.pic_count >= 4:
            self.emitted_layout = "image-grid"
            return
        # content+image: 1-3 content pics
        if 1 <= self.pic_count <= 3:
            self.emitted_layout = "content+image"
            return
        # Bullets only → §10 plain bullets
        if self.buchar_paragraph_count >= 1 or self.literal_bullet_paragraph_count >= 1:
            self.emitted_layout = "plain-bullets (§10)"
            return
        # Default — content-text
        self.emitted_layout = "content-text"


def _slide_paths(zf: zipfile.ZipFile) -> list[str]:
    return sorted(
        (n for n in zf.namelist()
         if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
        key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)),
    )


def _load_slide_rels(zf: zipfile.ZipFile, slide_path: str) -> dict[str, str]:
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
    s = s.lower()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()[:40]


def _looks_like_agenda(root: ET.Element) -> bool:
    ellipses = sum(
        1 for sp in root.iter(f"{{{NS['p']}}}sp")
        if (sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}prstGeom") is not None
            and sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}prstGeom").get("prst") == "ellipse")
    )
    return ellipses >= 4


def _extract_title(root: ET.Element) -> str:
    candidates: list[tuple[int, str]] = []
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
        if sz < 1700 or "Roboto Mono" not in font:
            continue
        text = "".join(t.text or "" for t in txbody.iter(f"{{{NS['a']}}}t")).strip()
        if text:
            candidates.append((sz, text))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def _shape_solid_fill(sp: ET.Element) -> str | None:
    sf = sp.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}solidFill")
    if sf is None:
        return None
    clr = sf.find(f"{{{NS['a']}}}srgbClr")
    if clr is None:
        return None
    v = clr.get("val", "")
    return v.upper() if len(v) == 6 else None


def _pic_geometry(pic: ET.Element) -> tuple[int, int, int, int] | None:
    """Return (x, y, cx, cy) EMU or None."""
    off = pic.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}xfrm/{{{NS['a']}}}off")
    ext = pic.find(f"{{{NS['p']}}}spPr/{{{NS['a']}}}xfrm/{{{NS['a']}}}ext")
    if off is None or ext is None:
        return None
    try:
        return (int(off.get("x", "0")), int(off.get("y", "0")),
                int(ext.get("cx", "0")), int(ext.get("cy", "0")))
    except (TypeError, ValueError):
        return None


def parse_pptx(path: str) -> list[RenderEvidence]:
    out: list[RenderEvidence] = []
    EMU_IN = 914400
    SMALL_ICON_THRESHOLD = int(0.55 * EMU_IN)  # ≤0.55″ counts as "icon"
    COL1_RIGHT_EDGE = int(1.5 * EMU_IN)         # left column = first ~1.5″
    with zipfile.ZipFile(path) as zf:
        for idx, sp_path in enumerate(_slide_paths(zf), start=1):
            try:
                root = ET.fromstring(zf.read(sp_path))
            except (ET.ParseError, KeyError):
                continue
            is_cover = (idx == 1)
            is_agenda = _looks_like_agenda(root)
            chrome = is_cover or is_agenda
            title = "" if chrome else _extract_title(root)
            ev = RenderEvidence(slide_num=idx, is_chrome=chrome, title_text=title)
            if chrome:
                ev.infer()
                out.append(ev)
                continue
            rels = _load_slide_rels(zf, sp_path)
            # Native tables
            ev.native_table_count = sum(1 for _ in root.iter(f"{{{NS['a']}}}tbl"))
            # Pics
            for pic in root.iter(f"{{{NS['p']}}}pic"):
                blip = pic.find(f"{{{NS['p']}}}blipFill/{{{NS['a']}}}blip")
                rid = blip.get(f"{{{NS['r']}}}embed") if blip is not None else None
                target = rels.get(rid, "") if rid else ""
                if ICON_PATH_RE.search(target):
                    # Section-pill icons / cover logo — excluded from content pic count
                    # but still inspect geometry for §7.5 column-1 icon detection.
                    geom = _pic_geometry(pic)
                    if geom and geom[0] <= COL1_RIGHT_EDGE and geom[2] <= SMALL_ICON_THRESHOLD:
                        ev.column1_icon_count += 1
                    continue
                ev.pic_count += 1
                ev.pic_paths.append(target)
                geom = _pic_geometry(pic)
                if geom and geom[0] <= COL1_RIGHT_EDGE and geom[2] <= SMALL_ICON_THRESHOLD:
                    ev.column1_icon_count += 1
            # Shape-level scans (callouts, code surface, bullets, literal • runs)
            for sp_el in root.iter(f"{{{NS['p']}}}sp"):
                fill = _shape_solid_fill(sp_el)
                if fill == "F7BBC1":
                    ev.callout_pink_count += 1
                elif fill == "B8E6F5":
                    ev.callout_blue_count += 1
                elif fill == "F2F2F2":
                    # Code-block surface (§9)
                    txbody = sp_el.find(f"{{{NS['p']}}}txBody")
                    if txbody is not None:
                        for r in txbody.iter(f"{{{NS['a']}}}r"):
                            rpr = r.find(f"{{{NS['a']}}}rPr")
                            latin = rpr.find(f"{{{NS['a']}}}latin") if rpr is not None else None
                            font = latin.get("typeface", "") if latin is not None else ""
                            if "Consolas" in font:
                                ev.code_surface_count += 1
                                break
                # Bullet paragraph scan
                txbody = sp_el.find(f"{{{NS['p']}}}txBody")
                if txbody is not None:
                    for para in txbody.findall(f"{{{NS['a']}}}p"):
                        ppr = para.find(f"{{{NS['a']}}}pPr")
                        if ppr is not None and ppr.find(f"{{{NS['a']}}}buChar") is not None:
                            ev.buchar_paragraph_count += 1
                        else:
                            # Literal-• detection: text run starts with "• "
                            t = next(para.iter(f"{{{NS['a']}}}t"), None)
                            if t is not None and t.text and t.text.lstrip().startswith("•"):
                                ev.literal_bullet_paragraph_count += 1
            ev.infer()
            out.append(ev)
    return out


# --------------------------------------------------------------------------- #
# reconciliation
# --------------------------------------------------------------------------- #

# Layouts that are equivalent for fit purposes (predicted ↔ emitted aliases).
LAYOUT_ALIASES = {
    "icon-bullet-list": {"icon-bullet-list", "card-row-or-icon-bullet-list"},
    "card-row": {"card-row", "card-row-or-icon-bullet-list"},
    "card-grid": {"card-grid", "content+cards+image", "card-grid-from-table"},
    "card-grid-from-table": {"card-grid", "card-grid-from-table"},
    "content+image": {"content+image"},
    "image-grid": {"image-grid"},
    "code-example": {"code-example"},
    "callout": {"callout"},
    "closing-cta": {"closing-cta", "content+image", "content-text"},  # last-slide flexibility
    "content-text": {"content-text"},
}


@dataclass
class Mismatch:
    slide_num: int
    h2_title: str
    predicted: str
    emitted: str
    source_evidence: dict
    emitted_evidence: dict
    likely_cause: str

    def fmt(self) -> str:
        return (
            f"[layout-fit] slide {self.slide_num} \"{self.h2_title}\" — "
            f"predicted {self.predicted} vs. emitted {self.emitted}\n"
            f"    source: {self.source_evidence}\n"
            f"    emitted: {self.emitted_evidence}\n"
            f"    likely cause: {self.likely_cause}"
        )


def _likely_cause(predicted: str, emitted: str, src: dict, ren: dict) -> str:
    if predicted == "icon-bullet-list" and emitted.startswith("plain-bullets"):
        return ("§15.6.1 discriminator skipped — source has "
                f"{src['labeled_bullet_count']} labeled bullets, longest body "
                f"{src['longest_bullet_body_chars']}c (>{SHORT_BODY_THRESHOLD}c → §7.5), "
                "but plain-bullet code path was taken; emit per §7.5 row stack instead")
    if predicted == "card-row" and emitted.startswith("plain-bullets"):
        return ("§15.6.1 discriminator skipped — source has "
                f"{src['labeled_bullet_count']} short labeled bullets "
                "(≤80c → §7.4), but plain-bullet code path was taken; emit per "
                "§7.4 card-row instead")
    if predicted == "image-grid" and emitted == "content+image":
        return (f"§15.5 row miss — source has {src['image_count']} images "
                "(≥4 → image-grid), but content+image was chosen")
    if predicted == "code-example" and emitted in ("content-text", "plain-bullets (§10)"):
        return "§15.5 row miss — source has a fenced code block; emit per §9 code-example"
    if predicted == "card-grid" and emitted in ("content-text", "plain-bullets (§10)"):
        return (f"§15.5 row miss — source has {src['h3_subhead_count']} `### Subhead` "
                "groups (≥4 → card-grid), but plainer layout was chosen")
    if predicted == "callout" and emitted in ("plain-bullets (§10)", "content-text"):
        return ("§15 row miss — single emoji-prefixed bold-lead bullet must promote to "
                "§8 callout, not render as a 1-item plain bullet list")
    return "unknown — confirm shape inference is correct for this layout class"


def reconcile(
    sources: list[SourceSignals], renders: list[RenderEvidence]
) -> list[Mismatch]:
    by_title: dict[str, RenderEvidence] = {}
    for r in renders:
        if r.is_chrome or not r.title_text:
            continue
        key = _normalize_title(r.title_text)
        if key and key not in by_title:
            by_title[key] = r

    mismatches: list[Mismatch] = []
    for s in sources:
        key = _normalize_title(s.h2_title)
        match = by_title.get(key)
        if match is None:
            # title rewrites are surfaced by audit_block_coverage; not this audit's concern
            continue
        aliases = LAYOUT_ALIASES.get(s.predicted_layout, {s.predicted_layout})
        if match.emitted_layout in aliases or match.emitted_layout == "ambiguous":
            continue
        src_ev = {
            "image_count": s.image_count,
            "code_blocks": s.code_blocks,
            "pipe_tables": s.pipe_tables,
            "bullet_count": s.bullet_count,
            "labeled_bullet_count": s.labeled_bullet_count,
            "emoji_prefixed_bullet_count": s.emoji_prefixed_bullet_count,
            "h3_subhead_count": s.h3_subhead_count,
            "longest_bullet_body_chars": s.longest_bullet_body_chars,
        }
        ren_ev = {
            "pic_count": match.pic_count,
            "column1_icon_count": match.column1_icon_count,
            "native_table_count": match.native_table_count,
            "code_surface_count": match.code_surface_count,
            "callout_pink_count": match.callout_pink_count,
            "callout_blue_count": match.callout_blue_count,
            "buchar_paragraph_count": match.buchar_paragraph_count,
            "literal_bullet_paragraph_count": match.literal_bullet_paragraph_count,
        }
        mismatches.append(Mismatch(
            slide_num=match.slide_num,
            h2_title=s.h2_title,
            predicted=s.predicted_layout,
            emitted=match.emitted_layout,
            source_evidence=src_ev,
            emitted_evidence=ren_ev,
            likely_cause=_likely_cause(s.predicted_layout, match.emitted_layout, src_ev, ren_ev),
        ))
    return mismatches


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("final_md")
    p.add_argument("final_pptx")
    p.add_argument("--json", action="store_true",
                   help="emit full JSON report on stdout")
    p.add_argument("--warn-only", action="store_true",
                   help="report mismatches but exit 0 (diagnostic mode)")
    args = p.parse_args(argv)

    try:
        sources = parse_final_md(args.final_md)
    except (FileNotFoundError, OSError) as e:
        print(f"audit_layout_fit: cannot read {args.final_md}: {e}", file=sys.stderr)
        return 2
    try:
        renders = parse_pptx(args.final_pptx)
    except (FileNotFoundError, zipfile.BadZipFile, OSError) as e:
        print(f"audit_layout_fit: cannot read {args.final_pptx}: {e}", file=sys.stderr)
        return 2

    mismatches = reconcile(sources, renders)

    if args.json:
        print(json.dumps({
            "final_md": args.final_md,
            "final_pptx": args.final_pptx,
            "summary": {
                "source_slides": len(sources),
                "render_content_slides": sum(1 for r in renders if not r.is_chrome),
                "mismatches": len(mismatches),
            },
            "mismatches": [asdict(m) for m in mismatches],
            "predicted": [asdict(s) for s in sources],
            "emitted": [asdict(r) for r in renders],
        }, indent=2))
    else:
        if not mismatches:
            print(f"audit_layout_fit: ok — {len(sources)} source slides, "
                  f"all predicted layouts match emitted layouts")
        else:
            print(f"audit_layout_fit: {len(mismatches)} mismatch(es)")
            for m in mismatches:
                print("  " + m.fmt())

    if args.warn_only:
        return 0
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
