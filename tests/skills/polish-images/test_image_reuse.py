#!/usr/bin/env python3
"""Tests for `polish_images` image reuse and stamping — the idempotency half of the aside pass.

Run:  python3 tests/skills/polish-images/test_image_reuse.py

The aside twin of `tests/skills/polish-ascii/test_render_reuse.py`, and the same two regressions —
costlier here, because a miss means a fresh image generation:

- **Digest reuse across a rename.** Aside names are positional (`<slide-id>-<n>-aside.png`), so
  inserting a slide renames every aside after it while its description does not change.
  `prepare-render-args` used to check only the planned basename and order a new generation. It must
  copy the stamped PNG (and its `.imgstamp`) across instead — and, because a shift is a *chain*
  (2 → 3 while 3 → 4) or a swap, it must read every donor before writing any destination.
- **No stamp on a stale image.** `stamp-renders` stamped whatever PNG sat at each planned basename.
  An old image there — its generation still pending, failed or unavailable — got marked current and
  never regenerated. It must be skipped when older than its `.imgprompt` and stamped from another
  description; `--only` stamps just the named ids once they land.
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
sys.path.insert(0, str(_ROOT / "skills" / "polish-images" / "scripts"))
from polish_images import STAMP_SUFFIX, main  # noqa: E402

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


def _directive(desc: str) -> str:
    return f"<!-- generate-image: right | {desc} -->\n"


def _slides(*bodies: str) -> str:
    """One section whose slides are numbered 1..n in order; each body is the slide's content."""
    return "# 1. Sección\n\n" + "".join(f"## {i}. Slide {i}\n\nTexto.\n\n{b}\n"
                                         for i, b in enumerate(bodies, 1))


def _plan(talk: Path) -> Path:
    """scan → annotate (positional basenames, as the illustrator names them) → extract."""
    final, plan, ann, gen = (talk / "final.md", talk / "plan.json", talk / "plan.annotated.json",
                             talk / "gen.json")
    _run("scan", str(final), "-o", str(plan))
    directives = json.loads(plan.read_text())["directives"]
    gen.write_text(json.dumps({
        d["slide_id"]: {"png_basename": f"{d['slide_id']}-aside.png", "alt": "x",
                        "description": d["directive"]["description"],
                        "prompt": f"enriched {d['directive']['description']} {os.urandom(4).hex()}"}
        for d in directives}))
    _run("annotate", "--plan", str(plan), "--gen", str(gen), "-o", str(ann))
    _run("extract", "--final", str(final), "--plan", str(ann))
    return ann


def _generate(images: Path, stem: str, tag: str) -> None:
    """Stand-in for generate-image: a PNG whose bytes say which description it was made from."""
    (images / f"{stem}.png").write_bytes(b"\x89PNG " + tag.encode())


def _png(images: Path, stem: str) -> bytes | None:
    p = images / f"{stem}.png"
    return p.read_bytes() if p.exists() else None


def test_digest_reuse_across_rename(tmp: Path) -> None:
    talk = tmp / "reuse"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(_slides(_directive("vertigo of scale")))
    ann = _plan(talk)
    _generate(images, "s1-1-1-aside", "A")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))

    # Renumber: a new slide 1 pushes the aside to slide 2. Same description, new basename.
    final.write_text(_slides("", _directive("vertigo of scale")))
    ann = _plan(talk)
    args = tmp / "args-reuse"
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("reuse: no generation args for an unchanged, renamed aside",
           code == 0 and not list(args.glob("*.json")), err)
    _check("reuse: PNG copied under the new name", _png(images, "s1-2-1-aside") == b"\x89PNG A")
    old_stamp, new_stamp = (images / f"s1-1-1-aside{STAMP_SUFFIX}"), (images / f"s1-2-1-aside{STAMP_SUFFIX}")
    _check("reuse: .imgstamp copied with it",
           new_stamp.exists() and new_stamp.read_text() == old_stamp.read_text())
    _check("reuse: the new .imgprompt is extract's, not the donor's",
           (images / "s1-2-1-aside.imgprompt").read_text() != (images / "s1-1-1-aside.imgprompt").read_text())
    _check("reuse: the old image is left in place (gc retires it later)", _png(images, "s1-1-1-aside") is not None)
    _check("reuse: the copy is reported", "s1-1-1-aside.png → s1-2-1-aside.png" in err, err)
    _check("reuse: no staging directory left behind", not list(images.glob(".reuse-*")))

    # A second pass is a plain hit at the planned name.
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("reuse: next pass reuses in place", code == 0 and not list(args.glob("*.json")), err)

    # A changed description is a changed digest: no donor matches, so it generates.
    final.write_text(final.read_text().replace("vertigo of scale", "weight of a single choice"))
    ann = _plan(talk)
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("reuse: a changed description still emits generation args", (args / "s1-2-1.json").exists())


def test_chain_and_swap(tmp: Path) -> None:
    talk = tmp / "chain"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(_slides(_directive("alpha"), _directive("beta")))
    ann = _plan(talk)
    _generate(images, "s1-1-1-aside", "A")
    _generate(images, "s1-2-1-aside", "B")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))

    # Insert a slide in front: alpha 1 → 2 (onto beta's old name), beta 2 → 3.
    final.write_text(_slides("", _directive("alpha"), _directive("beta")))
    ann = _plan(talk)
    args = tmp / "args-chain"
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("chain: nothing regenerates", code == 0 and not list(args.glob("*.json")), err)
    _check("chain: each slide keeps its own image",
           _png(images, "s1-2-1-aside") == b"\x89PNG A" and _png(images, "s1-3-1-aside") == b"\x89PNG B",
           f"{_png(images, 's1-2-1-aside')!r} / {_png(images, 's1-3-1-aside')!r}")

    # Swap the two: beta now at slide 2, alpha at slide 3.
    final.write_text(_slides("", _directive("beta"), _directive("alpha")))
    ann = _plan(talk)
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("swap: nothing regenerates", code == 0 and not list(args.glob("*.json")), err)
    _check("swap: the images trade places",
           _png(images, "s1-2-1-aside") == b"\x89PNG B" and _png(images, "s1-3-1-aside") == b"\x89PNG A",
           f"{_png(images, 's1-2-1-aside')!r} / {_png(images, 's1-3-1-aside')!r}")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    args2 = tmp / "args-swap2"
    code, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args2))
    _check("swap: stamps travelled with their images (next pass is a clean hit)",
           code == 0 and not list(args2.glob("*.json")), err)


def test_stamp_skips_stale_image(tmp: Path) -> None:
    talk = tmp / "stamp"
    images = talk / "images"
    images.mkdir(parents=True)
    final = talk / "final.md"
    final.write_text(_slides(_directive("alpha")))
    ann = _plan(talk)
    png, stamp = images / "s1-1-1-aside.png", images / f"s1-1-1-aside{STAMP_SUFFIX}"
    _generate(images, "s1-1-1-aside", "A")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    old_digest = stamp.read_text()

    # Edit the description: extract rewrites the sidecar; the old PNG (older) keeps the old stamp.
    os.utime(png, (1_000_000_000, 1_000_000_000))
    final.write_text(final.read_text().replace("alpha", "alpha, revised"))
    ann = _plan(talk)
    code, err = _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    _check("stamp: a stale image keeps its old stamp", code == 0 and stamp.read_text() == old_digest)
    _check("stamp: the skip is reported by slide id", "NOT stamped" in err and "s1-1-1" in err, err)
    args = tmp / "args-stamp"
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("stamp: so the next pass still orders the generation", (args / "s1-1-1.json").exists())

    # `--only` with another id touches nothing.
    _generate(images, "s1-1-1-aside", "A2")
    code, err = _run("stamp-renders", "--final", str(final), "--plan", str(ann), "--only", "s9-9-9")
    _check("stamp: --only with another id touches nothing",
           stamp.read_text() == old_digest and "s9-9-9" in err, err)

    # The generation lands (newer than the sidecar) → `--only` stamps it.
    _run("stamp-renders", "--final", str(final), "--plan", str(ann), "--only", "s1-1-1")
    _check("stamp: --only stamps the fresh image", stamp.read_text() != old_digest)

    # An unstamped PNG (hand-placed) is stamped normally, whatever its age.
    stamp.unlink()
    os.utime(png, (1_000_000_000, 1_000_000_000))
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    _check("stamp: an unstamped image is stamped", stamp.exists())


def main_() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("image reuse:")
        test_digest_reuse_across_rename(tmp)
        print("chain / swap:")
        test_chain_and_swap(tmp)
        print("stamp-renders:")
        test_stamp_skips_stale_image(tmp)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print("all polish-images reuse / stamp tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
