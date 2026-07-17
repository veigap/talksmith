"""Shared slide-context scanner for Talksmith Step-6 helpers.

Both `polish-ascii` (diagram → SVG) and `polish-images` (generate-image → aside)
need the *same* mechanical extraction of per-block slide context from a Talk's
`final.md`: the nearest H2 title above a block, its section H1, the section goal,
the slide's `### Content` / `### Speaker notes` bodies, and the top-of-file
`# Thesis`. That logic lives here **once**, `sys.path`-imported by both skills'
scripts (the same pattern `_pptxlib.py` uses for the reverse pipeline).

This module owns only the *structural* scan — headings, fences, prose stripping,
context assembly. Each pipeline keeps its own block-detection (an ` ```ascii `
fence vs. a `<!-- generate-image: … -->` directive) and its own rewrite rules.
"""
from __future__ import annotations

import re

# ── structural regexes (shared by both pipelines) ────────────────────────────
# Any ```-prefixed line toggles fence state. `^```(\w*)\s*$` failed to match openers
# like ```c++ or ```python title=x, flipping fence parity so the closing ``` opened a
# phantom fence that swallowed following slides. Group 1 is the full info string.
FENCE_OPEN = re.compile(r"^```(.*)$")
FENCE_CLOSE = re.compile(r"^```\s*$")
# End-of-line comment closer: a mid-line `-->` (e.g. a note line `the input --> model`)
# must not terminate the comment.
COMMENT_CLOSE = re.compile(r"(?<!-)-->\s*$")
H1_ANY = re.compile(r"^# (?!#)")
H1_SECTION = re.compile(r"^# (\d+)\.")
H1_AGENDA = re.compile(r"^# (?:Agenda|Índice|Indice)\b", re.IGNORECASE)
H1_CONCL = re.compile(r"^# (?:Conclusion|Conclusiones|Conclusions)\b", re.IGNORECASE)
H2_SLIDE = re.compile(r"^## (\d+)\.")
H1_OR_H2 = re.compile(r"^#{1,2} ")
IMAGE_REF = re.compile(r"!\[[^\]]*\]\([^)]+\)")

_H3 = re.compile(r"^###\s+(.+?)\s*$")
_GOAL_LINE = re.compile(r"^\*\*Goal of this section:\*\*\s*(.*)$")
_H1_NUMBERED_STRIP = re.compile(r"^#\s+\d+\.\s*")
_H2_NUMBERED_STRIP = re.compile(r"^##\s+\d+\.\s*")
_H1_PLAIN_STRIP = re.compile(r"^#\s+")
_INLINE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_prose(body_lines: list[str]) -> str:
    """Return body text with fenced code blocks, HTML comments, and `---` rules removed."""
    if not body_lines:
        return ""
    text = "\n".join(body_lines)
    text = _INLINE_COMMENT.sub("", text)
    out_lines: list[str] = []
    in_fence = False
    for ln in text.splitlines():
        if FENCE_OPEN.match(ln) or FENCE_CLOSE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if ln.strip() in ("---", "***", "___"):
            continue
        out_lines.append(ln)
    return "\n".join(out_lines).strip()


def skip_frontmatter(lines: list[str]) -> int:
    """0-based index of the first line after a leading YAML `---` block, else 0."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return 0


def extract_thesis(lines: list[str]) -> str:
    """Body of the `# Thesis` block (Claim + Why it matters), stripped.

    Skips YAML frontmatter so a `# thesis:` comment inside it isn't misread as the
    heading. Matches the heading exactly (case-insensitively) to avoid ad-hoc headings.
    """
    start = skip_frontmatter(lines)
    body: list[str] = []
    in_thesis = False
    for ln in lines[start:]:
        if ln.startswith("# ") and not ln.startswith("## "):
            if ln.strip().lower() == "# thesis":
                in_thesis = True
                continue
            if in_thesis:
                break
        if in_thesis:
            body.append(ln)
    return strip_prose(body)


def strip_h1(line: str) -> str:
    """Strip `# ` (and any numbered prefix `N. `) from an H1, preserving the title."""
    if H1_SECTION.match(line):
        return _H1_NUMBERED_STRIP.sub("", line).strip()
    return _H1_PLAIN_STRIP.sub("", line).strip()


def strip_h2(line: str) -> str:
    return _H2_NUMBERED_STRIP.sub("", line).strip()


def is_section_heading(ln: str) -> bool:
    """Every H1 is a section boundary; the title only labels it (see `section_of_h1`)."""
    return bool(H1_ANY.match(ln))


def section_of_h1(ln: str) -> "str | int | None":
    """Section id for an H1 line, or None when the heading carries no slides
    (Thesis, Open questions, Cut material, and any section the schema grows later)."""
    m = H1_SECTION.match(ln)
    if m:
        return int(m.group(1))
    if H1_AGENDA.match(ln):
        return 0
    if H1_CONCL.match(ln):
        return "c"
    return None


def fence_line_mask(lines: list[str]) -> list[bool]:
    """True for every line inside (or delimiting) a fenced code block.

    Heading/boundary detection must skip these — a `# legend: ...` line inside a fence
    is content, not a structural boundary.
    """
    mask = [False] * len(lines)
    in_f = False
    for i, ln in enumerate(lines):
        if not in_f:
            if FENCE_OPEN.match(ln):
                in_f = True
                mask[i] = True
        else:
            mask[i] = True
            if FENCE_CLOSE.match(ln):
                in_f = False
    return mask


def extract_block_context(lines: list[str], block_start_line: int,
                          fence_mask: "list[bool] | None" = None) -> dict:
    """Walk back from a block (1-based line) to gather slide + section context.

    Returns slide_title, section_title, section_goal, slide_content_prose, speaker_notes.
    `talk_thesis` / `presentation_language` are added by the caller (see the skills).
    """
    start_idx = block_start_line - 1  # 0-based
    if fence_mask is None:
        fence_mask = fence_line_mask(lines)

    slide_idx = -1
    section_idx = -1
    for i in range(start_idx - 1, -1, -1):
        if fence_mask[i]:
            continue
        ln = lines[i]
        if slide_idx < 0 and H2_SLIDE.match(ln):
            slide_idx = i
            continue
        if is_section_heading(ln):
            section_idx = i
            break

    slide_title = strip_h2(lines[slide_idx]) if slide_idx >= 0 else ""
    section_title = strip_h1(lines[section_idx]) if section_idx >= 0 else ""

    section_goal = ""
    if section_idx >= 0:
        end_idx = slide_idx if slide_idx >= 0 else len(lines)
        if slide_idx < 0:
            for j in range(section_idx + 1, len(lines)):
                if not fence_mask[j] and (H2_SLIDE.match(lines[j]) or is_section_heading(lines[j])):
                    end_idx = j
                    break
        for j in range(section_idx + 1, end_idx):
            m = _GOAL_LINE.match(lines[j])
            if not m:
                continue
            goal_text = m.group(1).strip()
            if not goal_text:
                continuation: list[str] = []
                for k in range(j + 1, end_idx):
                    nxt = lines[k]
                    if not nxt.strip():
                        if continuation:
                            break
                        continue
                    if nxt.startswith("**") or nxt.startswith("#") or nxt.strip() == "---":
                        break
                    continuation.append(nxt.strip())
                section_goal = " ".join(continuation).strip()
            else:
                section_goal = goal_text
            break

    slide_content_prose = ""
    speaker_notes = ""
    if slide_idx >= 0:
        slide_end = len(lines)
        for j in range(slide_idx + 1, len(lines)):
            if not fence_mask[j] and (H2_SLIDE.match(lines[j]) or is_section_heading(lines[j])):
                slide_end = j
                break
        j = slide_idx + 1
        while j < slide_end:
            m = _H3.match(lines[j]) if not fence_mask[j] else None
            if not m:
                j += 1
                continue
            h3_title = m.group(1).strip().lower()
            body_start = j + 1
            body_end = slide_end
            for k in range(j + 1, slide_end):
                if not fence_mask[k] and _H3.match(lines[k]):
                    body_end = k
                    break
            body = lines[body_start:body_end]
            if h3_title == "content":
                slide_content_prose = strip_prose(body)
            elif h3_title in ("speaker notes", "notes"):
                speaker_notes = strip_prose(body)
            j = body_end

    return {
        "slide_title": slide_title,
        "section_title": section_title,
        "section_goal": section_goal,
        "slide_content_prose": slide_content_prose,
        "speaker_notes": speaker_notes,
    }
