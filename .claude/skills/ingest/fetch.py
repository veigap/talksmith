"""Fetch a web page and save its contents under `talks/<Talk>/knowledge/web/<folder-name>/`.

Outputs:
    metadata.yaml      url, fetched_at, title, http_status, byte_size
    original.html      raw fetched HTML — the source of truth
    page.md            best-effort HTML → Markdown extraction
    assets/            referenced images, downloaded best-effort

Stdlib only (urllib, html.parser, pathlib). CLI-safe.

Usage:
    python fetch.py <url> --talk-path <talks/<Talk>> [--folder-name <slug>]

If --folder-name is omitted, it's derived from the URL host + first path
segment (slugified). Existing folders are NOT overwritten — fetch.py refuses
to overwrite to keep the captured snapshot stable; pass --force to override.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

_USER_AGENT = (
    "Mozilla/5.0 (compatible; TalksmithIngest/1.0; +https://github.com/anthropics/claude-code)"
)
_REQUEST_TIMEOUT_SEC = 30
_IMG_TIMEOUT_SEC = 15

# Tags whose content should be dropped entirely (boilerplate, navigation, ads).
_DROP_TAGS = {"script", "style", "noscript", "nav", "footer", "aside", "form", "iframe"}

# Inline-text tags whose text we keep but which don't add structure.
_INLINE_TAGS = {"span", "em", "i", "strong", "b", "u", "small", "sub", "sup"}

# Tags handled specifically (heading, list, etc.). Anything else is treated as
# a generic block that emits a paragraph break before/after.
_BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "header",
    "blockquote", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "pre", "code", "table", "tr", "td", "th",
    "hr", "br",
}


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "page"


def _default_folder_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "site"
    path = parsed.path.strip("/")
    first_seg = path.split("/", 1)[0] if path else ""
    raw = f"{host}-{first_seg}" if first_seg else host
    return _slugify(raw)


def _fetch_url(url: str) -> tuple[bytes, int, str]:
    """Return (body, status, final_url) for a single GET. Raises on hard failure."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
        body = resp.read()
        status = resp.status
        final_url = resp.geturl()
    return body, status, final_url


class _HtmlExtractor(HTMLParser):
    """Best-effort HTML → Markdown extractor.

    Captures title from `<title>`. Skips _DROP_TAGS subtrees. Emits Markdown
    for headings, paragraphs, lists, links, code, strong/em, and image refs.
    Collects image URLs encountered for later download.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self._title_capture = False
        self._drop_depth = 0
        self._stack: list[str] = []
        self._md_parts: list[str] = []
        self._list_stack: list[str] = []  # "ul" or "ol"
        self._list_counters: list[int] = []
        self._pending_link_href: str | None = None
        self._link_text_buffer: list[str] | None = None
        self._image_urls: list[tuple[str, str]] = []  # (src, alt)
        self._in_pre = False

    # ------------------ public ------------------
    @property
    def markdown(self) -> str:
        text = "".join(self._md_parts)
        # Collapse runs of 3+ blank lines.
        return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    @property
    def image_urls(self) -> list[tuple[str, str]]:
        return self._image_urls

    # ------------------ HTMLParser hooks ------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        if tag in _DROP_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth > 0:
            return
        if tag == "title":
            self._title_capture = True
            return
        self._stack.append(tag)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._md_parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            self._md_parts.append("\n\n")
        elif tag == "br":
            self._md_parts.append("  \n")
        elif tag == "hr":
            self._md_parts.append("\n\n---\n\n")
        elif tag == "blockquote":
            self._md_parts.append("\n\n> ")
        elif tag in {"ul", "ol"}:
            self._list_stack.append(tag)
            self._list_counters.append(0)
            self._md_parts.append("\n")
        elif tag == "li":
            if self._list_stack:
                kind = self._list_stack[-1]
                if kind == "ol":
                    self._list_counters[-1] += 1
                    self._md_parts.append(f"\n{self._list_counters[-1]}. ")
                else:
                    self._md_parts.append("\n- ")
            else:
                self._md_parts.append("\n- ")
        elif tag == "pre":
            self._in_pre = True
            self._md_parts.append("\n\n```\n")
        elif tag == "code" and not self._in_pre:
            self._md_parts.append("`")
        elif tag in {"strong", "b"}:
            self._md_parts.append("**")
        elif tag in {"em", "i"}:
            self._md_parts.append("*")
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href:
                self._pending_link_href = href
                self._link_text_buffer = []
        elif tag == "img":
            src = attr_dict.get("src", "")
            alt = attr_dict.get("alt", "")
            if src:
                self._image_urls.append((src, alt))
                self._md_parts.append(f"![{alt}]({src})")

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROP_TAGS:
            if self._drop_depth > 0:
                self._drop_depth -= 1
            return
        if self._drop_depth > 0:
            return
        if tag == "title":
            self._title_capture = False
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote"}:
            self._md_parts.append("\n\n")
        elif tag in {"ul", "ol"}:
            if self._list_stack and self._list_stack[-1] == tag:
                self._list_stack.pop()
                self._list_counters.pop()
            self._md_parts.append("\n")
        elif tag == "pre":
            self._in_pre = False
            self._md_parts.append("\n```\n\n")
        elif tag == "code" and not self._in_pre:
            self._md_parts.append("`")
        elif tag in {"strong", "b"}:
            self._md_parts.append("**")
        elif tag in {"em", "i"}:
            self._md_parts.append("*")
        elif tag == "a" and self._pending_link_href is not None:
            inner = "".join(self._link_text_buffer or []).strip()
            href = self._pending_link_href
            self._pending_link_href = None
            self._link_text_buffer = None
            if inner:
                self._md_parts.append(f"[{inner}]({href})")
            else:
                self._md_parts.append(f"<{href}>")

    def handle_data(self, data: str) -> None:
        if self._drop_depth > 0:
            return
        if self._title_capture:
            self.title += data.strip()
            return
        text = data
        if not self._in_pre:
            # Collapse internal whitespace, preserve a single trailing space.
            text = re.sub(r"\s+", " ", text)
            if not text or text == " ":
                # Preserve word boundary but don't emit lone whitespace as a token.
                if text == " " and self._md_parts and not self._md_parts[-1].endswith((" ", "\n")):
                    self._md_parts.append(" ")
                return
        if self._link_text_buffer is not None:
            self._link_text_buffer.append(text)
        else:
            self._md_parts.append(text)


def _download_assets(image_urls: list[tuple[str, str]], base_url: str, assets_dir: Path) -> list[dict]:
    """Best-effort download of `<img src>` references. Returns a manifest list."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    seen: dict[str, str] = {}  # absolute_url -> local filename
    for src, alt in image_urls:
        absolute = urllib.parse.urljoin(base_url, src)
        if not absolute.startswith(("http://", "https://")):
            manifest.append({"src": src, "absolute": absolute, "skipped": "non-http"})
            continue
        if absolute in seen:
            manifest.append({"src": src, "absolute": absolute, "saved_as": seen[absolute], "alt": alt, "deduped": True})
            continue
        # Build local filename.
        parsed = urllib.parse.urlparse(absolute)
        basename = Path(parsed.path).name or "image"
        if "." not in basename:
            basename = basename + ".bin"
        local = assets_dir / basename
        # Collision: append numeric suffix.
        idx = 2
        while local.exists():
            stem, _, ext = basename.rpartition(".")
            local = assets_dir / f"{stem}-{idx}.{ext}" if ext else assets_dir / f"{basename}-{idx}"
            idx += 1
        try:
            req = urllib.request.Request(absolute, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=_IMG_TIMEOUT_SEC) as resp:
                local.write_bytes(resp.read())
            seen[absolute] = local.name
            manifest.append({"src": src, "absolute": absolute, "saved_as": local.name, "alt": alt})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            manifest.append({"src": src, "absolute": absolute, "skipped": f"fetch-failed: {exc.__class__.__name__}"})
    return manifest


def _write_metadata_yaml(target: Path, url: str, title: str, status: int, byte_size: int, asset_manifest: list[dict]) -> None:
    """Write a simple YAML (hand-formatted; stdlib has no yaml dumper)."""
    fetched_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        f'url: "{url}"',
        f'fetched_at: "{fetched_at}"',
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"http_status: {status}",
        f"byte_size: {byte_size}",
        "assets:",
    ]
    if not asset_manifest:
        lines.append("  []")
    else:
        for a in asset_manifest:
            inline = ", ".join(
                f'{k}: "{str(v).replace(chr(34), chr(39))}"' if isinstance(v, str) else f"{k}: {v}"
                for k, v in a.items()
            )
            lines.append(f"  - {{ {inline} }}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch(url: str, talk_path: Path, folder_name: str | None = None, force: bool = False) -> Path:
    """Fetch `url` and persist into `talk_path/knowledge/web/<folder_name>/`. Returns the folder."""
    folder = folder_name or _default_folder_name(url)
    folder = _slugify(folder)
    target = talk_path / "knowledge" / "web" / folder
    if target.exists() and not force:
        if any(target.iterdir()):
            raise FileExistsError(
                f"{target} already exists and is non-empty. Pass --force to overwrite."
            )
    target.mkdir(parents=True, exist_ok=True)

    body, status, final_url = _fetch_url(url)
    raw_html = body.decode("utf-8", errors="replace")

    extractor = _HtmlExtractor()
    extractor.feed(raw_html)
    extractor.close()

    (target / "original.html").write_bytes(body)
    (target / "page.md").write_text(
        f"# {extractor.title or final_url}\n\n_Source: <{final_url}>_\n\n{extractor.markdown}",
        encoding="utf-8",
    )

    assets_dir = target / "assets"
    asset_manifest = _download_assets(extractor.image_urls, final_url, assets_dir)
    if not any(assets_dir.iterdir()):
        # Remove empty assets dir for cleanliness.
        try:
            assets_dir.rmdir()
        except OSError:
            pass

    _write_metadata_yaml(
        target / "metadata.yaml",
        url=final_url,
        title=extractor.title,
        status=status,
        byte_size=len(body),
        asset_manifest=asset_manifest,
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a web page into talks/<Talk>/knowledge/web/<folder-name>/."
    )
    parser.add_argument("url", help="URL to fetch (http/https).")
    parser.add_argument(
        "--talk-path", type=Path, required=True,
        help="Absolute or repo-relative path to the active Talk folder (talks/<Talk>/).",
    )
    parser.add_argument(
        "--folder-name", default=None,
        help="Output sub-folder name under knowledge/web/. Default = slug of URL host + first path segment.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing knowledge/web/<folder-name>/ directory.",
    )
    args = parser.parse_args()

    if not args.url.startswith(("http://", "https://")):
        print(f"error: url must be http(s)://, got {args.url!r}", file=sys.stderr)
        return 2
    if not args.talk_path.is_dir():
        print(f"error: --talk-path {args.talk_path} is not a directory", file=sys.stderr)
        return 2

    try:
        out = fetch(args.url, args.talk_path, folder_name=args.folder_name, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"error: fetch failed: {exc}", file=sys.stderr)
        return 1
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
