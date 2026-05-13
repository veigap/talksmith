"""Convert a cleaned `master.md` into the slimmed Markdown that
`skill://antropic-skills:/pptx` consumes.

Input contract:
    A Talk's cleaned `master.md` (post Step 6.5 Polish). Image refs already
    point at `images/<file>`; `Presenter feedback` already stripped; ASCII
    source preserved only in `<!-- ascii-source: ... -->` HTML comments.

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
    python convert.py <path-to-master.md> [-o <output.md>]
    python convert.py <path-to-master.md>            # writes to stdout

The script is dependency-free (stdlib only) and CLI-safe — no Cowork required.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

# Sections at H1 that must be stripped wholesale (heading + body until the
# next H1 or EOF).
_STRIP_H1 = {"Thesis", "Open questions", "Cut material"}

# Fields at H4 that must be stripped wholesale (heading + body until the
# next H1/H2/H3/H4 or EOF). Order matters only for clarity.
_STRIP_H3 = {"Sources", "Presenter feedback"}

# H4 field that should have its label dropped but body kept.
_UNWRAP_H3 = {"Content"}

# H4 field that should have its label renamed (label → "Notes") but body kept.
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
    pattern = re.compile(rf"^{'#' * level}\s+(.*)$", re.MULTILINE)
    chunks: list[tuple[str | None, str]] = []
    last_idx = 0
    last_title: str | None = None
    for m in pattern.finditer(text):
        # Stop at deeper headings? No — we just match the requested level. But
        # we must ensure we don't match `####` when looking for `###` — handled
        # by the boundary: pattern requires exactly `level` hashes followed by space.
        # However, `^#{3}\s` will also match `####` because `####` starts with `###`.
        # Use negative-lookahead to be precise.
        pass
    # Re-do with proper boundary.
    boundary = re.compile(rf"^({'#' * level})(?!#)\s+(.*)$", re.MULTILINE)
    chunks = []
    last_idx = 0
    last_title = None
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


def _rewrite_h3_within_slide(slide_body: str) -> str:
    """Within a single slide's body, drop/rename/unwrap H3 fields."""
    h3_chunks = _split_by_heading_level(slide_body, 3)
    out: list[str] = []
    for h3_title, h3_body in h3_chunks:
        if h3_title is None:
            out.append(h3_body)
            continue
        field = h3_title.strip()
        if field in _STRIP_H3:
            # Drop the heading and its body.
            continue
        if field in _RENAME_H3:
            new_label = _RENAME_H3[field]
            out.append(f"### {new_label}\n{h3_body}")
            continue
        if field in _UNWRAP_H3:
            # Drop the label; keep the body.
            # Trim leading blank line if the body starts with one.
            out.append(h3_body.lstrip("\n"))
            continue
        # Unknown H3: keep as-is.
        out.append(f"### {field}\n{h3_body}")
    return "".join(out)


def _collapse_blank_lines(text: str) -> str:
    """Replace runs of 3+ blank lines with a single blank line."""
    return re.sub(r"\n{3,}", "\n\n", text)


def convert(master_md: str) -> str:
    """Run the full conversion pipeline on the contents of `master.md`."""
    text = master_md
    text = _strip_frontmatter(text)
    text = _strip_html_comments(text)
    text = _strip_h1_sections(text, _STRIP_H1)
    text = _process_h3_fields(text)
    # After H4 processing, re-walk and normalize remaining H1 / H2 prefixes
    # for any heading we didn't touch.
    text = "\n".join(_normalize_heading(line) for line in text.splitlines())
    text = _collapse_blank_lines(text)
    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a cleaned master.md into the Markdown shape "
                    "consumed by skill://antropic-skills:/pptx."
    )
    parser.add_argument("master_md", type=Path, help="Path to talks/<Talk>/master.md")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output file (default: stdout)."
    )
    args = parser.parse_args()

    if not args.master_md.is_file():
        print(f"error: {args.master_md} not found", file=sys.stderr)
        return 2

    source = args.master_md.read_text(encoding="utf-8")
    converted = convert(source)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(converted, encoding="utf-8")
    else:
        sys.stdout.write(converted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
