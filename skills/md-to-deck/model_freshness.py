"""Freshness guard binding a rendered slide-model to its source markdown.

`slide-model.json` (deliverable) and `slide-model.draft.json` (live view) are **generated
artifacts** — the md-to-deck FILL step decomposes `final.md` / `draft.md` into them with an LLM.
They are never hand-maintained. A renderer must never consume one that is stale relative to its
source, so the FILL step stamps the model with the SHA-256 of the exact bytes it was filled from
(`stamp`), and every render verifies that stamp first (`check` / `verify_fresh`), refusing to
render — never silently falling back — when the stamp is missing or no longer matches the source.

CLI:
    python3 model_freshness.py stamp --talk talks/<Talk> [--draft]   # after FILL
    python3 model_freshness.py check --talk talks/<Talk> [--draft]   # before RENDER

`stamp` records a `_source` block into the model; `check` exits 0 (fresh), 3 (stale/unstamped),
or 2 (IO error). `verify_fresh(model, source_path)` is the importable core the HTML renderer calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def source_path(talk: Path, draft: bool) -> Path:
    """The markdown the model is filled from: draft.md for the live view, else final.md."""
    return talk / ("draft.md" if draft else "final.md")


def model_path(talk: Path, draft: bool) -> Path:
    name = "slide-model.draft.json" if draft else "slide-model.json"
    return talk / "output" / name


def digest(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def verify_fresh(model: dict, src: Path) -> tuple[bool, str]:
    """(is_fresh, reason). Fresh iff the model's stamped digest equals the current source's."""
    meta = model.get("_source")
    if not isinstance(meta, dict) or "sha256" not in meta:
        return False, ("model carries no _source stamp — it was never bound to a source "
                       "(re-run the FILL step, then `model_freshness.py stamp`)")
    if not src.is_file():
        return False, f"source {src} not found — cannot confirm the model is current"
    sha, _ = digest(src)
    if sha != meta["sha256"]:
        return False, (f"model is STALE — {src.name} changed since it was filled "
                       f"(source {sha[:12]}… ≠ stamped {str(meta['sha256'])[:12]}…); "
                       f"re-run the FILL step, then `model_freshness.py stamp`")
    return True, "fresh"


def stamp(talk: Path, draft: bool) -> int:
    src, mdl = source_path(talk, draft), model_path(talk, draft)
    if not src.is_file():
        print(f"failed: source {src} not found", file=sys.stderr)
        return 2
    if not mdl.is_file():
        print(f"failed: model {mdl} not found — run the FILL step first", file=sys.stderr)
        return 2
    sha, n = digest(src)
    model = json.loads(mdl.read_text(encoding="utf-8"))
    model["_source"] = {"file": src.name, "sha256": sha, "bytes": n}
    mdl.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[fresh] stamped {mdl.name} ← {src.name} ({sha[:12]}…, {n} bytes)", file=sys.stderr)
    return 0


def check(talk: Path, draft: bool) -> int:
    src, mdl = source_path(talk, draft), model_path(talk, draft)
    if not mdl.is_file():
        print(f"failed: model {mdl} not found — run the FILL step first", file=sys.stderr)
        return 2
    model = json.loads(mdl.read_text(encoding="utf-8"))
    ok, reason = verify_fresh(model, src)
    if ok:
        print(f"[fresh] {mdl.name} matches {src.name}", file=sys.stderr)
        return 0
    print(f"failed: {reason}", file=sys.stderr)
    return 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["stamp", "check"], help="stamp after FILL; check before RENDER")
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="operate on slide-model.draft.json / draft.md")
    args = ap.parse_args(argv)
    return (stamp if args.cmd == "stamp" else check)(args.talk, args.draft)


if __name__ == "__main__":
    raise SystemExit(main())
