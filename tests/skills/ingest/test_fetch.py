#!/usr/bin/env python3
"""Tests for `skills/ingest/fetch.py` — image collection, HTTP-error captures, all-or-nothing folders.

Run:  python3 tests/skills/ingest/test_fetch.py

Offline: every "remote" page and asset is served by a loopback `http.server` started here.

**The cases that matter:**
- `object_svg_figures_are_collected` — arXiv/ar5iv figures are `<object type="image/svg+xml">`;
  reading only `<img src>` captured 1 of 26 figures of a paper.
- `http_403_body_is_saved` — SKILL.md says a 403/paywall body "is what gets saved"; the script
  used to exit 1 with no folder.
- `camo_long_name_is_hashed` + `failure_leaves_no_folder` — a GitHub camo badge's last path
  segment is the whole hex-encoded URL (>255 bytes); the OSError escaped the per-asset guard
  and left `original.html` + `page.md` with no `metadata.yaml`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_CLI = _ROOT / "skills" / "ingest" / "fetch.py"
sys.path.insert(0, str(_ROOT / "skills" / "ingest"))
import fetch as F  # noqa: E402

_RESULTS: list[tuple[str, bool]] = []

_CAMO = "/camo/95de7ff0b618be50/" + ("68747470733a2f2f696d672e736869656c64732e696f" * 8)

_PAPER = f"""<html><head><title>Debate</title></head><body>
<h1>Multiagent Debate</h1>
<figure><object type="image/svg+xml" data="/assets/fig1.svg" width="476"></object>
<figcaption>Figure 1</figcaption></figure>
<object data="/assets/fig2.svg"><img src="/assets/fig2-fallback.png" alt="twin"></object>
<object type="text/html" data="/widget.html"></object>
<embed type="image/svg+xml" src="/assets/fig3.svg">
<img src="data:image/gif;base64,R0lGOD" data-src="/assets/lazy.png" alt="lazy">
<img src="/assets/small.png" srcset="/assets/small.png 480w, /assets/large.png 1200w" alt="resp">
<picture><source srcset="/assets/pic.webp 1x, /assets/pic@2x.webp 2x"><img alt="nosrc"></picture>
<svg><image xlink:href="/assets/inline.png" /></svg>
<img src="{_CAMO}" alt="badge">
<img src="/assets/missing.png" alt="gone">
</body></html>"""

_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
_PNG = b"\x89PNG\r\n\x1a\n"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a) -> None:  # keep test output clean
        pass

    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        p = self.path
        if p == "/paper":
            self._send(200, "text/html; charset=utf-8", _PAPER.encode())
        elif p == "/forbidden":
            self._send(403, "text/html", b"<html><head><title>Just a moment</title></head>"
                                         b"<body><p>Subscribe to read.</p><img src='/assets/logo.png'></body></html>")
        elif p.startswith("/camo/"):
            self._send(200, "image/svg+xml", _SVG)
        elif p.endswith(".svg"):
            self._send(200, "image/svg+xml", _SVG)
        elif p == "/assets/missing.png":
            self._send(404, "text/plain", b"nope")
        elif p.startswith("/assets/"):
            self._send(200, "image/png", _PNG)
        else:
            self._send(404, "text/plain", b"not found")


def _record(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail and not ok else ''}")


def _extract(html: str) -> list[str]:
    ex = F._HtmlExtractor()
    ex.feed(html)
    ex.close()
    return [u for u, _ in ex.image_urls]


def _leftovers(web: Path) -> list[str]:
    return sorted(p.name for p in web.iterdir()) if web.is_dir() else []


def main() -> int:
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"

    print("srcset / image selection:")
    _record("srcset_largest_width",
            F._largest_srcset_candidate("a.png 480w, b.png 1200w, c.png 800w") == "b.png")
    _record("srcset_largest_density",
            F._largest_srcset_candidate("a.png, b.png 3x, c.png 2x") == "b.png")
    _record("srcset_data_uri_commas_survive",
            F._largest_srcset_candidate("data:image/png;base64,AA== 1x, real.png 2x") == "real.png")
    _record("img_data_placeholder_yields_to_data_src",
            F._img_url({"src": "data:image/gif;base64,R0", "data-src": "real.jpg"}) == "real.jpg")
    _record("img_plain_src", F._img_url({"src": "x.png"}) == "x.png")

    print("extractor:")
    urls = _extract(_PAPER)
    _record("object_svg_figures_are_collected", "/assets/fig1.svg" in urls and "/assets/fig2.svg" in urls, str(urls))
    _record("object_fallback_img_not_duplicated", "/assets/fig2-fallback.png" not in urls, str(urls))
    _record("non_image_object_skipped", "/widget.html" not in urls, str(urls))
    _record("embed_svg_collected", "/assets/fig3.svg" in urls, str(urls))
    _record("lazy_data_src_collected", "/assets/lazy.png" in urls and not any(u.startswith("data:") for u in urls),
            str(urls))
    _record("img_srcset_largest_collected", "/assets/large.png" in urls and "/assets/small.png" not in urls, str(urls))
    _record("picture_source_used_when_img_empty", "/assets/pic@2x.webp" in urls, str(urls))
    _record("svg_image_xlink_href_collected", "/assets/inline.png" in urls, str(urls))
    md = F._HtmlExtractor()
    md.feed(_PAPER)
    _record("page_md_refs_match_collected_urls", "![](/assets/fig1.svg)" in md.markdown, md.markdown)

    print("asset names:")
    long_url = "http://h" + _CAMO
    name = F._asset_name(long_url, "image/svg+xml")
    _record("camo_long_name_is_hashed", len(name.encode()) <= F._MAX_ASSET_NAME_BYTES and name.endswith(".svg"), name)
    name = F._asset_name("http://h/" + "a" * 300 + ".png", "")
    _record("long_name_keeps_extension", name.endswith(".png") and len(name) == 16, name)
    _record("short_name_unchanged", F._asset_name("http://h/x/fig1.svg", "image/svg+xml") == "fig1.svg")
    _record("extensionless_name_gets_content_type_ext", F._asset_name("http://h/badge", "image/png") == "badge.png")

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            talk = Path(tmp) / "talk"
            talk.mkdir()
            web = talk / "research" / "web"

            print("fetch (paper):")
            out, status = F.fetch(f"{base}/paper", talk, folder_name="paper")
            meta = (out / "metadata.yaml").read_text()
            saved = sorted(p.name for p in (out / "assets").iterdir())
            _record("paper_status_200", status == 200 and "http_status: 200" in meta)
            _record("paper_figures_downloaded", {"fig1.svg", "fig2.svg", "fig3.svg", "large.png"} <= set(saved), str(saved))
            _record("paper_camo_badge_saved", any(len(n) == 16 and n.endswith(".svg") for n in saved), str(saved))
            _record("paper_404_asset_skipped_not_fatal", "fetch-failed: HTTPError" in meta, meta)
            _record("paper_no_staging_leftovers", _leftovers(web) == ["paper"], str(_leftovers(web)))

            print("fetch (HTTP 403):")
            r = subprocess.run([sys.executable, str(_CLI), f"{base}/forbidden", "--talk-path", str(talk),
                                "--folder-name", "medium"], capture_output=True, text=True)
            dst = web / "medium"
            _record("http_403_exit_code_3", r.returncode == F.EXIT_HTTP_ERROR, f"rc={r.returncode} {r.stderr}")
            _record("http_403_body_is_saved",
                    b"Subscribe to read." in (dst / "original.html").read_bytes()
                    and "http_status: 403" in (dst / "metadata.yaml").read_text())
            _record("http_403_page_md_banner", "**HTTP 403.**" in (dst / "page.md").read_text())
            _record("http_403_no_assets", not (dst / "assets").exists())
            _record("http_403_reported", "http-error: 403" in r.stdout, r.stdout)

            print("all-or-nothing folder:")
            real = F._write_metadata_yaml

            def _boom(*a, **k):
                raise OSError(63, "File name too long")

            F._write_metadata_yaml = _boom
            try:
                try:
                    F.fetch(f"{base}/paper", talk, folder_name="broken")
                    raised = False
                except OSError:
                    raised = True
                _record("failure_raises", raised)
                _record("failure_leaves_no_folder", _leftovers(web) == ["medium", "paper"], str(_leftovers(web)))
                before = (web / "paper" / "metadata.yaml").read_text()
                try:
                    F.fetch(f"{base}/paper", talk, folder_name="paper", force=True)
                except OSError:
                    pass
                _record("failed_force_keeps_previous_capture",
                        (web / "paper" / "metadata.yaml").read_text() == before
                        and _leftovers(web) == ["medium", "paper"], str(_leftovers(web)))
            finally:
                F._write_metadata_yaml = real

            out, _ = F.fetch(f"{base}/paper", talk, folder_name="paper", force=True)
            _record("force_replaces_capture", (out / "metadata.yaml").is_file()
                    and _leftovers(web) == ["medium", "paper"], str(_leftovers(web)))
            try:
                F.fetch(f"{base}/paper", talk, folder_name="paper")
                refused = False
            except FileExistsError:
                refused = True
            _record("existing_folder_refused_without_force", refused)
    finally:
        server.shutdown()

    failures = sum(1 for _, ok in _RESULTS if not ok)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(_RESULTS)} ingest tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
