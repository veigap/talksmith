"""Convert a cleaned `final.md` into the slimmed Markdown that
`skill://antropic-skills:/pptx` consumes.

Input contract:
    A Talk's cleaned `final.md` (post Step 6 Polish — produced by the editor
    copying `draft.md` → `final.md` then applying Polish transforms a/b/c/d).
    Image refs already point at `images/<file>`; `Presenter feedback` already
    stripped; ASCII source preserved only in `<!-- ascii-source: ... -->`
    HTML comments. `draft.md` is not a valid input in the default mode — passing
    it leaks Presenter feedback bullets into slide bodies.

Draft-preview mode (`--draft`):
    For the optional Step-5.5 draft preview, `draft.md` IS a valid input. The
    `--draft` flag additionally strips the `**Presenter feedback:**` labeled
    blocks that `draft.md` carries in its Agenda and section-divider bodies
    (Polish removes these on the way to `final.md`; in a pre-Polish draft they
    are still present), and it does NOT require ASCII to have been rendered to
    SVG — raw ASCII fenced blocks pass through untouched so the renderer can lay
    them out as monospace text boxes. Everything else is identical to the
    default pipeline. The preview reads `draft.md` directly and never touches
    `final.md`, so it is available before Step 6 has run.

Output contract (Markdown):
    - YAML frontmatter is dropped.
    - `# Thesis`, `# Open questions`, `# Cut material` sections are dropped.
    - `# Agenda` and `# Conclusions` headings pass through.
    - Numbered H1s (`# N. <name>`, plus legacy `# N — <name>` / `# Section N: <name>`)
      pass through as section dividers; the leading prefix is stripped from the title.
    - H2s inside a section pass through as content slides; the leading
      `N. ` / `N — ` / `Slide N: ` prefix is stripped from the title.
    - H3 slide-field headings (`### …`) are dropped / unwrapped / renamed:
        - `### Content`         → label dropped, body kept
        - `### Sources`         → entire field dropped (presenter-internal)
        - `### Speaker notes`   → label rewritten to `### Notes`, body kept
        - `### Presenter feedback` → field dropped (defensive — Polish should have removed it)
    - HTML comments (`<!-- ... -->`) are stripped, including `ascii-source` preserves.
    - Horizontal rules (`---`) between slides pass through.
    - Image refs (`![alt](path)`) pass through verbatim.

Usage:
    python convert.py <path-to-final.md> [-o <output.md>]
    python convert.py <path-to-final.md>            # writes to stdout

The script is dependency-free (stdlib only) and CLI-safe — no Cowork required.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

# A line that is a horizontal rule (`---`) or an H1 heading (`# ...`). These
# delimit slides/sections and are never part of an H3 field's body.
_RULE_LINE_RE = re.compile(r"^-{3,}\s*$")
_H1_LINE_RE = re.compile(r"^#(?!#)\s+")

# Any ATX heading (`#`..`######`) and a bold field label line (`**Label:**`).
# Used by the draft-mode `**Presenter feedback:**` block stripper to find where
# a labeled block ends.
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s")
_BOLD_LABEL_RE = re.compile(r"^\*\*[^*]+:\*\*\s*$")
# Working-meta labels that are scaffolding, never slide content — stripped in draft
# mode so a preview slide shows only real content (the Agenda shows just its section
# list, not the narrative arc; nothing shows presenter feedback). Matches whether the
# label stands alone on its line or is followed by inline prose on the same line.
_STRIP_LABEL_RE = re.compile(r"^\*\*(?:Presenter feedback|Narrative arc):\*\*")

# Sections at H1 that must be stripped wholesale (heading + body until the
# next H1 or EOF).
_STRIP_H1 = {"Thesis", "Open questions", "Cut material"}

# Fields at H3 that must be stripped wholesale (heading + body until the
# next H1/H2/H3 or EOF). Order matters only for clarity.
_STRIP_H3 = {"Sources", "Presenter feedback"}

# H3 field that should have its label dropped but body kept.
_UNWRAP_H3 = {"Content"}

# H3 field that should have its label renamed (label → "Notes") but body kept.
_RENAME_H3 = {"Speaker notes": "Notes"}

# H1 / H2 numbered prefix patterns to strip:
#   "1. "         (current)
#   "1 — " / "1 - "  (legacy em-dash / hyphen)
#   "Section 1: " / "Slide 1: "  (legacy verbose)
_HEADING_PREFIX_RE = re.compile(
    r"^("
    r"(?:Section|Slide)\s+\d+\s*:\s*"          # "Section 1: " / "Slide 1: "
    r"|\d+\s*[.—\-]\s*"                    # "1. " / "1 — " / "1 - "
    r")"
)


def _strip_html_comments(text: str) -> str:
    return _HTML_COMMENT_RE.sub("", text)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _normalize_heading(line: str) -> str:
    """Strip numeric / 'Section X:' / 'Slide X:' prefix from an H1 or H2 title.

    `# 1. Foundations`  → `# Foundations`
    `## 2. Why X`       → `## Why X`
    `# Section 3: Y`    → `# Y`
    `# Agenda`          → `# Agenda`  (unchanged)
    """
    m = re.match(r"^(#{1,6})\s+(.*)$", line)
    if not m:
        return line
    hashes, title = m.group(1), m.group(2)
    cleaned = _HEADING_PREFIX_RE.sub("", title, count=1)
    return f"{hashes} {cleaned}".rstrip()


def _split_by_heading_level(text: str, level: int) -> list[tuple[str | None, str]]:
    """Split text into (heading_title, body) pairs at the given heading level.

    Body excludes the heading line itself. The first chunk has heading=None
    if the text doesn't start with a heading at this level.
    """
    boundary = re.compile(rf"^({'#' * level})(?!#)\s+(.*)$", re.MULTILINE)
    chunks: list[tuple[str | None, str]] = []
    last_idx = 0
    last_title: str | None = None
    for m in boundary.finditer(text):
        body = text[last_idx:m.start()]
        chunks.append((last_title, body))
        last_title = m.group(2).strip()
        last_idx = m.end() + 1  # skip the newline after the heading line
    chunks.append((last_title, text[last_idx:]))
    return chunks


def _strip_h1_sections(text: str, titles_to_strip: set[str]) -> str:
    """Remove any H1 section whose title (post-prefix-stripping) is in the set."""
    chunks = _split_by_heading_level(text, 1)
    out_parts: list[str] = []
    for title, body in chunks:
        if title is None:
            # Pre-first-H1 preamble — keep as-is.
            out_parts.append(body)
            continue
        clean_title = _HEADING_PREFIX_RE.sub("", title, count=1).strip()
        if clean_title in titles_to_strip:
            continue  # Drop this whole section.
        # Keep this H1 + body. Re-emit the heading line.
        out_parts.append(f"# {clean_title}\n{body}")
    return "".join(out_parts)


def _process_h3_fields(text: str) -> str:
    """Drop / rename / unwrap H3 slide fields inside the text.

    Operates per H2 slide chunk: within each H2 chunk, find each H3 and
    apply the rule (drop / rename / unwrap label).
    """
    chunks = _split_by_heading_level(text, 2)
    out_parts: list[str] = []
    for slide_title, slide_body in chunks:
        if slide_title is None:
            # Pre-first-H2 content (section-level prose, H1 prelude, etc.) — pass through.
            out_parts.append(slide_body)
            continue
        clean_slide_title = _HEADING_PREFIX_RE.sub("", slide_title, count=1).strip()
        new_body = _rewrite_h3_within_slide(slide_body)
        out_parts.append(f"## {clean_slide_title}\n{new_body}")
    return "".join(out_parts)


def _split_field_tail(body: str) -> tuple[str, str]:
    """Split an H3 field body into (field_content, structural_tail).

    Because slides are split at H2 only, the last H3 field of a slide owns
    everything up to the next H2 — including the between-slide `---` rule and
    the following section's `# N.` divider (+ its goal prose). Those are
    document structure, never field content, so the tail must survive even when
    the field itself is stripped. The tail begins at the first line that is a
    horizontal rule (`---`) or an H1 heading; interior fields end at the next
    H3 and so have no tail.
    """
    lines = body.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if _RULE_LINE_RE.match(line.strip()) or _H1_LINE_RE.match(line):
            return "".join(lines[:idx]), "".join(lines[idx:])
    return body, ""


def _rewrite_h3_within_slide(slide_body: str) -> str:
    """Within a single slide's body, drop/rename/unwrap H3 fields.

    The structural tail (between-slide `---` + following `# N.` divider) that a
    trailing field's body swallows is preserved verbatim regardless of the
    field's disposition, so stripping `### Sources` / `### Presenter feedback`
    never eats the next section divider.
    """
    h3_chunks = _split_by_heading_level(slide_body, 3)
    out: list[str] = []
    for h3_title, h3_body in h3_chunks:
        if h3_title is None:
            out.append(h3_body)
            continue
        field = h3_title.strip()
        field_body, tail = _split_field_tail(h3_body)
        if field in _STRIP_H3:
            # Drop the heading and its content, but keep the structural tail.
            out.append(tail)
            continue
        if field in _RENAME_H3:
            new_label = _RENAME_H3[field]
            out.append(f"### {new_label}\n{field_body}{tail}")
            continue
        if field in _UNWRAP_H3:
            # Drop the label; keep the body.
            # Trim leading blank line if the body starts with one.
            out.append(field_body.lstrip("\n") + tail)
            continue
        # Unknown H3: keep as-is.
        out.append(f"### {field}\n{field_body}{tail}")
    return "".join(out)


def _normalize_headings_outside_code(text: str) -> str:
    """Apply `_normalize_heading` to each line that is not inside a fenced
    code block. Fences are lines whose first non-space chars are ``` or ~~~.
    """
    out: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            out.append(line)
            continue
        if in_fence:
            if stripped.startswith(fence_marker or "```"):
                in_fence = False
                fence_marker = None
            out.append(line)
            continue
        out.append(_normalize_heading(line))
    return "\n".join(out)


def _strip_bold_feedback_blocks(text: str) -> str:
    """Remove working-meta labeled blocks (draft-mode only).

    `draft.md` carries `**Presenter feedback:**` (Agenda + section-divider bodies)
    and `**Narrative arc:**` (Agenda) blocks — scaffolding for the author, never
    slide content. Polish removes them on the way to `final.md`, so the default
    pipeline never sees them; in draft mode we strip them here so a preview slide
    shows only real content (the Agenda slide shows just its section list). A block
    runs from its `**Label:**` line up to (but not including) the next horizontal
    rule, ATX heading, or other bold field label; the label line and everything
    under it up to that terminator are dropped.
    """
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        if _STRIP_LABEL_RE.match(lines[i].strip()):
            i += 1  # drop the label line
            while i < n:
                stripped = lines[i].strip()
                if (
                    _RULE_LINE_RE.match(stripped)
                    or _ANY_HEADING_RE.match(lines[i])
                    or _BOLD_LABEL_RE.match(stripped)
                ):
                    break  # terminator — leave it in place
                i += 1  # drop a body line of the feedback block
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def _split_into_slide_units(text: str) -> list[str]:
    """Split converted markdown into per-slide units at top-level `---` rules.

    Fence-aware: a `---` line inside a fenced ASCII/code block is body content,
    not a slide boundary, so it never splits a diagram. Each returned unit is one
    renderable slide — a section-divider H1 or a content H2 with its body. Empty
    units are dropped. Used only by the draft-preview per-slide parallel path
    (`--split-dir`); the default single-file render never calls it.
    """
    units: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            current.append(line)
            continue
        if in_fence:
            if stripped.startswith(fence_marker or "```"):
                in_fence = False
                fence_marker = None
            current.append(line)
            continue
        if _RULE_LINE_RE.match(line.strip()):
            unit = "\n".join(current).strip()
            if unit:
                units.append(unit)
            current = []
            continue
        current.append(line)
    unit = "\n".join(current).strip()
    if unit:
        units.append(unit)
    return units


def _collapse_blank_lines(text: str) -> str:
    """Replace runs of 3+ blank lines with a single blank line."""
    return re.sub(r"\n{3,}", "\n\n", text)


def convert(final_md: str, draft: bool = False) -> str:
    """Run the full conversion pipeline on the contents of `final.md`.

    When `draft` is True, the input is a pre-Polish `draft.md`: additionally
    strip the `**Presenter feedback:**` labeled blocks it still carries, and
    let raw ASCII fenced blocks pass through unchanged (no SVG required).
    """
    text = final_md
    text = _strip_frontmatter(text)
    text = _strip_html_comments(text)
    if draft:
        text = _strip_bold_feedback_blocks(text)
    text = _strip_h1_sections(text, _STRIP_H1)
    text = _process_h3_fields(text)
    # After H3 processing, re-walk and normalize remaining H1 / H2 prefixes
    # for any heading we didn't touch.
    text = _normalize_headings_outside_code(text)
    text = _collapse_blank_lines(text)
    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a cleaned final.md into the Markdown shape "
                    "consumed by skill://antropic-skills:/pptx."
    )
    parser.add_argument(
        "final_md", type=Path,
        help="Path to talks/<Talk>/final.md (or draft.md with --draft)"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output file (default: stdout)."
    )
    parser.add_argument(
        "--draft", action="store_true",
        help="Draft-preview mode: accept a pre-Polish draft.md — strip its "
             "**Presenter feedback:** blocks and let raw ASCII fences pass "
             "through as monospace (no SVG required)."
    )
    parser.add_argument(
        "--split-dir", type=Path, default=None,
        help="Draft-preview only: also write one per-slide unit file "
             "(slide-NN.md) into this directory for the per-slide parallel "
             "render. Prints the ordered manifest of unit paths to stdout."
    )
    args = parser.parse_args()

    if not args.final_md.is_file():
        print(f"error: {args.final_md} not found", file=sys.stderr)
        return 2

    source = args.final_md.read_text(encoding="utf-8")
    converted = convert(source, draft=args.draft)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(converted, encoding="utf-8")

    if args.split_dir is not None:
        units = _split_into_slide_units(converted)
        args.split_dir.mkdir(parents=True, exist_ok=True)
        width = max(2, len(str(len(units))))
        for i, unit in enumerate(units, 1):
            unit_path = args.split_dir / f"slide-{i:0{width}d}.md"
            unit_path.write_text(unit + "\n", encoding="utf-8")
            # Manifest to stdout — one unit path per line, in slide order.
            print(unit_path)
    elif not args.output:
        sys.stdout.write(converted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
