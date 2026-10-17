#!/usr/bin/env python3
"""Tests for `polish_ascii` render reuse, stamping and `gc` — the idempotency half of Step 6.

Run:  python3 tests/skills/polish-ascii/test_render_reuse.py

Three behaviours, each a regression from a real renumbered Talk:

- **Digest reuse across a rename.** Inserting a slide renumbers every slide after it, so each
  diagram's planned basename changes while its ASCII does not. `prepare-render-args` used to check
  only the planned path, ignore the identically-stamped SVG under the old name, and order a fresh
  render (and critique) of a drawing that already existed. It must copy it across instead —
  SVG, PNG, critique PNG and log, with the log's H1 renamed.
- **No stamp on a stale SVG.** `stamp-renders` stamped whatever SVG sat at each planned basename.
  An old drawing there — its render still pending or failed — got marked current and never
  re-rendered. It must be skipped when it is older than its sidecar and stamped from other ASCII;
  `--only` stamps just the named ids once they do render.
- **`gc --apply` is recoverable.** It used to `unlink()`; it must move into `images/.trash/<ts>/`.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "skills" / "polish-ascii"))
from polish_ascii import main, read_svg_digest  # noqa: E402

_DIAGRAM = "```ascii\n+-------+    +-------+\n| input | -> | model |\n+-------+    +-------+\n```\n" \
           "<!-- ascii-note:\nintent: el modelo transforma la entrada\nemphasize: model\n-->\n"
_SVG = '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect/></svg>\n'

failures = 0


def _check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{f' ({detail})' if detail and not ok else ''}")


def _run(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, err.getvalue()


def _plan(talk: Path, renders: dict[str, str]) -> Path:
    """scan → annotate → extract, returning the annotated plan path."""
    final, plan, ann, rmap = (talk / "final.md", talk / "plan.json", talk / "plan.annotated.json",
                              talk / "renders.json")
    _run("scan", str(final), "-o", str(plan))
    rmap.write_text(json.dumps({sid: {"svg_basename": bn, "alt": "x"} for sid, bn in renders.items()}))
    _run("annotate-renders", "--plan", str(plan), "--renders", str(rmap), "-o", str(ann))
    _run("extract", "--final", str(final), "--plan", str(ann))
    return ann


def _render(images: Path, stem: str) -> None:
    """Stand-in for ascii-to-svg + the critique loop: an SVG, its PNG, the critique pair."""
    (images / f"{stem}.svg").write_text(_SVG)
    (images / f"{stem}.png").write_bytes(b"\x89PNG fake")
    (images / ".critique").mkdir(exist_ok=True)
    (images / ".critique" / f"{stem}.png").write_bytes(b"\x89PNG fake")
    (images / ".critique" / f"{stem}.md").write_text(f"# Critique log — {stem}\n\n## Run — 2026-10-01\nclean\n")


def test_digest_reuse_across_rename(tmp: Path) -> None:
    talk = tmp / "reuse"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(f"# 1. Sección\n\n## 1. Slide\n\n{_DIAGRAM}")
    ann = _plan(talk, {"s1-1-1": "s1-1-1-entrada-modelo.svg"})
    _render(images, "s1-1-1-entrada-modelo")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))

    # Renumber: a new slide 1 pushes the diagram to slide 2. Same ASCII, new basename.
    final.write_text(f"# 1. Sección\n\n## 1. Nuevo\n\nTexto.\n\n## 2. Slide\n\n{_DIAGRAM}")
    ann = _plan(talk, {"s1-2-1": "s1-2-1-entrada-modelo.svg"})
    args = tmp / "args"
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    new = images / "s1-2-1-entrada-modelo.svg"
    _check("reuse: no render args emitted for an unchanged, renamed block",
           code == 0 and not list(args.glob("*.json")), err)
    _check("reuse: SVG copied under the new name, stamp intact",
           new.exists() and read_svg_digest(new) == read_svg_digest(images / "s1-1-1-entrada-modelo.svg"))
    _check("reuse: deliverable PNG and critique PNG copied",
           (images / "s1-2-1-entrada-modelo.png").exists()
           and (images / ".critique" / "s1-2-1-entrada-modelo.png").exists())
    log = (images / ".critique" / "s1-2-1-entrada-modelo.md")
    text = log.read_text() if log.exists() else ""
    _check("reuse: critique log H1 names the new stem and records the reuse",
           text.startswith("# Critique log — s1-2-1-entrada-modelo\n") and "## Reused" in text
           and "s1-1-1-entrada-modelo" in text, text[:80])
    _check("reuse: the old render is left in place (gc retires it later)",
           (images / "s1-1-1-entrada-modelo.svg").exists())

    # A changed note is a changed digest: no donor matches, so it renders.
    final.write_text(final.read_text().replace("emphasize: model", "emphasize: input"))
    ann = _plan(talk, {"s1-2-1": "s1-2-1-entrada-modelo.svg"})
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("reuse: a changed ascii-note still emits render args", (args / "s1-2-1.json").exists())


def test_stamp_skips_stale_svg(tmp: Path) -> None:
    talk = tmp / "stamp"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(f"# 1. Sección\n\n## 1. Slide\n\n{_DIAGRAM}")
    ann = _plan(talk, {"s1-1-1": "s1-1-1-x.svg"})
    svg = images / "s1-1-1-x.svg"
    _render(images, "s1-1-1-x")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    old_digest = read_svg_digest(svg)

    # Edit the ASCII: extract rewrites the sidecar, the old SVG (older) still holds the old stamp.
    os.utime(svg, (1_000_000_000, 1_000_000_000))
    final.write_text(final.read_text().replace("| model |", "| MODEL |"))
    ann = _plan(talk, {"s1-1-1": "s1-1-1-x.svg"})
    code, err = _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    _check("stamp: a stale SVG keeps its old stamp", code == 0 and read_svg_digest(svg) == old_digest)
    _check("stamp: the skip is reported by slide id", "NOT stamped" in err and "s1-1-1" in err, err)

    # The render lands (newer than the sidecar) → `--only` stamps it.
    svg.write_text(_SVG)
    _run("stamp-renders", "--final", str(final), "--plan", str(ann), "--only", "s1-1-1")
    new_digest = read_svg_digest(svg)
    _check("stamp: --only stamps the fresh render", new_digest is not None and new_digest != old_digest)

    # `--only` leaves other ids alone.
    svg.write_text(_SVG)
    _run("stamp-renders", "--final", str(final), "--plan", str(ann), "--only", "s9-9-9")
    _check("stamp: --only with another id touches nothing", read_svg_digest(svg) is None)


def test_gc_moves_to_trash(tmp: Path) -> None:
    talk = tmp / "gc"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text("# 1. Sección\n\n## 1. Slide\n\n![x](images/vivo.svg)\n")
    _render(images, "vivo")
    (images / "vivo.svg").write_text(f"<!-- talksmith-ascii-sha256: {'a' * 64} -->\n{_SVG}")
    _render(images, "huerfano")
    (images / "huerfano.ascii").write_text("A --> B\n")
    (images / "foto.png").write_bytes(b"\x89PNG presenter")   # presenter-owned: no sidecar, no stamp

    _run("gc", "--final", str(final))
    _check("gc: dry-run touches nothing", (images / "huerfano.svg").exists())
    code, _ = _run("gc", "--final", str(final), "--apply")
    trash = list((images / ".trash").glob("*"))
    moved = {str(p.relative_to(trash[0])) for p in trash[0].rglob("*") if p.is_file()} if trash else set()
    _check("gc: --apply moves the orphan set into one images/.trash/<timestamp>/",
           code == 0 and len(trash) == 1 and moved == {
               "huerfano.svg", "huerfano.png", "huerfano.ascii",
               ".critique/huerfano.png", ".critique/huerfano.md"}, str(sorted(moved)))
    _check("gc: nothing left behind under the orphan's stem",
           not any(images.glob("huerfano.*")) and not any((images / ".critique").glob("huerfano.*")))
    _check("gc: referenced and presenter-owned images untouched",
           (images / "vivo.svg").exists() and (images / "foto.png").exists())
    _run("gc", "--final", str(final), "--apply")
    _check("gc: trashed files are not orphans on the next pass", len(list((images / ".trash").glob("*"))) == 1)


def main_() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("render reuse:")
        test_digest_reuse_across_rename(tmp)
        print("stamp-renders:")
        test_stamp_skips_stale_svg(tmp)
        print("gc:")
        test_gc_moves_to_trash(tmp)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print("all polish-ascii reuse / stamp / gc tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
