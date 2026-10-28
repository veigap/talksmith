#!/usr/bin/env python3
"""Tests for the animated-diagram route through `polish_ascii` (the `animate:` note field).

Run:  python3 tests/skills/polish-ascii/test_animate_routing.py

Stdlib only — the animations themselves are stood in for by fake GIF/PNG/script files; the real
GIF render is covered by tests/skills/animate-diagram/. What is checked here is the plumbing:

- `scan` reads `animate:` off the note (and flags an unknown value), and the digest ignores it,
  so switching a block's route never re-renders a drawing whose ASCII did not change.
- `annotate-renders --animations` applies the presenter's one Polish-entry answer, a renders-map
  `animate` override wins over the note, and `both` refuses to proceed without a companion name.
- `prepare-render-args` routes each output to its renderer (`both` → two animation args), reuses
  a stamped script, re-runs one whose GIF is gone, and retires the other route's leftovers.
- `stamp-renders` stamps the generator script; `cleanup` points the slide at the GIF and inserts
  the training slide right after the source slide.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "skills" / "polish-ascii"))
from polish_ascii import ascii_digest, main, read_script_digest, scan  # noqa: E402

_ASCII = "```ascii\n+-------+    +-------+\n| input | -> | model |\n+-------+    +-------+\n```\n"


def _note(extra: str = "") -> str:
    return f"<!-- ascii-note:\nintent: el modelo transforma la entrada\nemphasize: model\n{extra}-->\n"


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


def _talk(tmp: Path, name: str, body: str) -> Path:
    talk = tmp / name
    (talk / "images").mkdir(parents=True)
    (talk / "final.md").write_text(
        "# 1. Sección\n\n**Goal of this section:** g\n\n---\n\n## 1. Slide\n\n### Content\n\n"
        f"{body}\n### Speaker notes\n\nNotas.\n\n---\n\n## 2. Otra\n\n### Content\n\nTexto.\n")
    return talk


def _plan(talk: Path, entry: dict, policy: str = "all") -> tuple[int, Path, str]:
    final, plan, ann, rmap = (talk / "final.md", talk / "plan.json", talk / "plan.ann.json",
                              talk / "renders.json")
    _run("scan", str(final), "-o", str(plan))
    rmap.write_text(json.dumps({"s1-1-1": entry}))
    code, err = _run("annotate-renders", "--plan", str(plan), "--renders", str(rmap), "-o", str(ann),
                     "--animations", policy)
    if code == 0:
        _run("extract", "--final", str(final), "--plan", str(ann))
    return code, ann, err


def _fake_anim(images: Path, stem: str) -> None:
    (images / ".anim").mkdir(exist_ok=True)
    (images / ".anim" / f"{stem}.py").write_text("#!/usr/bin/env python3\nprint('anim')\n")
    (images / f"{stem}.gif").write_bytes(b"GIF89a fake")
    (images / f"{stem}.png").write_bytes(b"\x89PNG fake")


def test_scan_and_digest(tmp: Path) -> None:
    talk = _talk(tmp, "scan", _ASCII + _note("animate: both\n"))
    b = scan(talk / "final.md")["blocks"][0]
    _check("scan: `animate:` is read off the note", b.get("animate") == "both", str(b.get("animate")))
    bad = _talk(tmp, "bad", _ASCII + _note("animate: sometimes\n"))
    b2 = scan(bad / "final.md")["blocks"][0]
    _check("scan: an unknown value is static and flagged",
           b2.get("animate") is None and b2.get("animate_invalid") == "sometimes")
    with_line = ascii_digest("x", _note("animate: inference\n"))
    _check("digest: the animate line is routing, not content", with_line == ascii_digest("x", _note()))


def test_policy_and_override(tmp: Path) -> None:
    talk = _talk(tmp, "policy", _ASCII + _note("animate: both\n"))
    entry = {"svg_basename": "s1-1-1-modelo.svg", "alt": "m",
             "training": {"basename": "s1-1-1-modelo-entrenamiento", "title": "Entrenamiento del modelo",
                          "notes": "La pérdida baja."}}
    for policy, want in (("all", "both"), ("no-training", "inference"), ("none", None)):
        code, ann, err = _plan(talk, entry, policy)
        got = json.loads(ann.read_text())["blocks"][0]["render"].get("animate")
        _check(f"annotate: --animations {policy} → {want}", code == 0 and got == want, err)
    code, ann, _ = _plan(talk, {**entry, "animate": "no"})
    _check("annotate: a renders-map `animate: no` falls back to static",
           json.loads(ann.read_text())["blocks"][0]["render"].get("animate") is None)
    plain = _talk(tmp, "plain", _ASCII + _note())
    code, ann, _ = _plan(plain, {"basename": "s1-1-1-modelo", "animate": "inference"})
    _check("annotate: an override animates a note that predates the field",
           json.loads(ann.read_text())["blocks"][0]["render"].get("animate") == "inference")
    code, _, err = _plan(talk, {"svg_basename": "s1-1-1-modelo.svg", "alt": "m"})
    _check("annotate: `both` without a training name/title is refused", code == 2 and "training" in err, err)


def test_routing_stamp_cleanup(tmp: Path) -> None:
    talk = _talk(tmp, "route", _ASCII + _note("animate: both\n"))
    images, final = talk / "images", talk / "final.md"
    entry = {"svg_basename": "s1-1-1-modelo.svg", "alt": "El modelo",
             "training": {"basename": "s1-1-1-modelo-entrenamiento", "title": "Cómo se entrena el modelo",
                          "alt": "Entrenamiento", "notes": "La pérdida baja paso a paso."}}
    _, ann, _ = _plan(talk, entry)
    args = talk / "args"
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    a1, a2 = args / "s1-1-1.json", args / "s1-1-1.training.json"
    p1 = json.loads(a1.read_text()) if a1.exists() else {}
    p2 = json.loads(a2.read_text()) if a2.exists() else {}
    _check("prepare: `both` emits an inference and a training animation args file",
           p1.get("renderer") == "animate-diagram" and p1.get("kind") == "inference"
           and p2.get("kind") == "training" and p2.get("companion", {}).get("title"))
    _check("prepare: the script lives in images/.anim/<stem>.py",
           p1.get("script_path", "").endswith("images/.anim/s1-1-1-modelo.py"))

    _fake_anim(images, "s1-1-1-modelo")
    _fake_anim(images, "s1-1-1-modelo-entrenamiento")
    _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    s1 = read_script_digest(images / ".anim" / "s1-1-1-modelo.py")
    s2 = read_script_digest(images / ".anim" / "s1-1-1-modelo-entrenamiento.py")
    _check("stamp: each generator script is stamped, kinds kept apart", s1 and s2 and s1 != s2)
    _check("stamp: the shebang stays first",
           (images / ".anim" / "s1-1-1-modelo.py").read_text().startswith("#!/usr/bin/env python3\n# talksmith-ascii-sha256:"))

    for f in args.glob("*.json"):
        f.unlink()
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("prepare: stamped animations are reused", not list(args.glob("*.json")))
    (images / "s1-1-1-modelo.gif").unlink()
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("prepare: a current script whose GIF is gone is re-run, not re-authored",
           json.loads(a1.read_text()).get("rerun") is True if a1.exists() else False)
    # An interrupted write once left 0-byte GIFs under their real names: empty is missing.
    a1.unlink()
    (images / "s1-1-1-modelo.gif").write_bytes(b"")
    _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    _check("prepare: a 0-byte GIF counts as missing — its script is re-run",
           json.loads(a1.read_text()).get("rerun") is True if a1.exists() else False)
    (images / ".anim" / "s1-1-1-modelo-entrenamiento.py").write_text("#!/usr/bin/env python3\n")
    (images / "s1-1-1-modelo-entrenamiento.gif").write_bytes(b"")
    _, err = _run("stamp-renders", "--final", str(final), "--plan", str(ann))
    _check("stamp: a 0-byte GIF is never stamped as a finished render",
           read_script_digest(images / ".anim" / "s1-1-1-modelo-entrenamiento.py") is None
           and "s1-1-1-modelo-entrenamiento.gif" in err, err)
    _fake_anim(images, "s1-1-1-modelo")
    _fake_anim(images, "s1-1-1-modelo-entrenamiento")

    code, _ = _run("cleanup", "--final", str(final), "--plan", str(ann))
    text = final.read_text()
    src_slide, rest = text.split("## 2. Otra", 1) if "## 2. Otra" in text else (text, "")
    _check("cleanup: the slide plays the GIF", "![El modelo](images/s1-1-1-modelo.gif)" in src_slide)
    _check("cleanup: the training slide is inserted before the next slide, with its notes",
           "## Cómo se entrena el modelo" in src_slide
           and src_slide.index("### Speaker notes\n\nNotas.") < src_slide.index("## Cómo se entrena")
           and "![Entrenamiento](images/s1-1-1-modelo-entrenamiento.gif)" in src_slide
           and "La pérdida baja paso a paso." in src_slide)
    _check("cleanup: every `---` keeps a blank line before it", "\n\n---" in text and "\n---\n" in text
           and not any(ln == "---" and prev.strip() for prev, ln in zip(text.splitlines(), text.splitlines()[1:])))
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        main(["gc", "--final", str(final)])
    _check("gc: both animations are live (referenced), nothing orphaned",
           "no orphaned" in out.getvalue(), out.getvalue())


def test_route_switch_retires(tmp: Path) -> None:
    talk = _talk(tmp, "switch", _ASCII + _note("animate: inference\n"))
    images = talk / "images"
    _, ann, _ = _plan(talk, {"basename": "s1-1-1-modelo", "alt": "m"})
    _fake_anim(images, "s1-1-1-modelo")
    _run("stamp-renders", "--final", str(talk / "final.md"), "--plan", str(ann))
    # The presenter now asks for still images: the block routes to the SVG.
    _, ann, _ = _plan(talk, {"basename": "s1-1-1-modelo", "alt": "m"}, "none")
    args = talk / "args"
    _, err = _run("prepare-render-args", "--plan", str(ann), "--out-dir", str(args))
    p = json.loads((args / "s1-1-1.json").read_text())
    _check("switch: a static route gets ascii-to-svg args", p.get("renderer") == "ascii-to-svg")
    _check("switch: the animation's GIF, script and (ambiguous) PNG are retired to .trash",
           not (images / "s1-1-1-modelo.gif").exists() and not (images / "s1-1-1-modelo.png").exists()
           and list((images / ".trash").rglob("s1-1-1-modelo.py")), err)


def main_() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for t in (test_scan_and_digest, test_policy_and_override, test_routing_stamp_cleanup,
                  test_route_switch_retires):
            print(t.__name__)
            t(tmp)
    if failures:
        print(f"\n{failures} check(s) FAILED")
        return 1
    print("\nall polish-ascii animation routing tests pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_())
