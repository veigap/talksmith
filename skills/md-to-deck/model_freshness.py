"""Freshness guard binding a rendered slide-model to its source markdown.

`slide-model.json` (deliverable) and `slide-model.draft.json` (live view) are **generated
artifacts** — the md-to-deck FILL step decomposes `final.md` / `draft.md` into them with an LLM.
They are never hand-maintained. A renderer must never consume one that is stale relative to its
source, so the FILL step stamps the model with the SHA-256 of the exact bytes it was filled from
(`stamp`), and every render verifies that stamp first (`check` / `verify_fresh`), refusing to
render — never silently falling back — when the stamp is missing or no longer matches the source.

The same question is worth asking one artifact later, about the **rendered deck** itself: a
refresh of the Step-5.5 live view is not a script but a full LLM FILL pass, so it is expensive
enough to skip and therefore expensive enough to fall behind silently — and a presenter reading
`output/html/index.html` has no way to tell it is two review rounds old. `rendered` answers that
in one cheap read: each render copies the model's `_source` stamp into `output/html/.render.json`,
so comparing it against the source markdown on disk costs one hash, no FILL and no LLM.

CLI:
    python3 model_freshness.py stamp --talk talks/<Talk> [--draft]   # after FILL
    python3 model_freshness.py check --talk talks/<Talk> [--draft]   # before RENDER
    python3 model_freshness.py rendered --talk talks/<Talk>          # is the deck on disk current?

`stamp` records a `_source` block into the model; `check` exits 0 (fresh), 3 (stale/unstamped),
or 2 (IO error). `rendered` exits 0 (fresh), 3 (stale), 4 (can't tell), or 2 (nothing rendered).
`verify_fresh(model, source_path)` is the importable core the HTML renderer calls; `stamp_state`
is the one `build_index` calls to badge a stale deck on the landing page.
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


def render_stamp_path(talk: Path) -> Path:
    """The sidecar `build_index.stamp_render` writes beside the rendered deck. The name is spelled
    out rather than imported from `build_index`, which pulls in `html_style` and jinja2 — this
    module stays stdlib-only so the staleness question can be asked anywhere, cheaply."""
    return talk / "output" / "html" / ".render.json"


def stamp_state(stamp: dict, talk: Path) -> tuple[str, str]:
    """(state, reason) for a **rendered** deck, from its `.render.json` and the source on disk.

    `fresh` — the deck was rendered from the bytes `draft.md`/`final.md` currently holds.
    `stale` — the source has changed since; what is on disk is an older deck, and saying so is
              the whole point: the alternative is a presenter reviewing slides that no longer
              match the outline and finding out by noticing the slide count.
    `unknown` — no source stamp (a deck rendered by an older Talksmith) or the source is gone.
                Never reported as fresh: "can't tell" and "current" are different answers.
    """
    meta = stamp.get("source") if isinstance(stamp.get("source"), dict) else {}
    sha = meta.get("sha256")
    name = meta.get("file") or ("draft.md" if stamp.get("mode") == "draft" else "final.md")
    if not sha:
        return "unknown", (f"the rendered deck carries no source stamp (rendered before Talksmith "
                           f"recorded one) — cannot tell whether it is current with {name}")
    src = talk / name
    if not src.is_file():
        return "unknown", f"{src} is gone — cannot tell whether the rendered deck is current"
    cur, _ = digest(src)
    if cur == sha:
        return "fresh", f"the rendered deck matches the current {name}"
    return "stale", (f"the rendered deck is STALE — {name} changed since it was rendered "
                     f"(source {cur[:12]}… ≠ rendered {str(sha)[:12]}…)")


def rendered(talk: Path) -> int:
    """Is `output/html/index.html` current with its source? One hash — no FILL, no LLM."""
    st = render_stamp_path(talk)
    deck = talk / "output" / "html" / "index.html"
    if not deck.is_file():
        print(f"failed: no rendered deck at {deck}", file=sys.stderr)
        return 2
    try:
        info = json.loads(st.read_text(encoding="utf-8")) if st.is_file() else {}
    except (json.JSONDecodeError, OSError):
        info = {}
    state, reason = stamp_state(info, talk)
    what = ("live view" if info.get("mode") == "draft" else "deck")
    at = f", rendered {info['rendered']}" if info.get("rendered") else ""
    n = f"{info['slides']} slides" if info.get("slides") else "unknown size"
    print(f"[{state}] {what} ({n}{at}): {reason}", file=sys.stderr)
    return {"fresh": 0, "stale": 3}.get(state, 4)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["stamp", "check", "rendered"],
                    help="stamp after FILL; check before RENDER; rendered = is the deck on disk current")
    ap.add_argument("--talk", type=Path, required=True, help="Talk root, e.g. talks/<Talk>")
    ap.add_argument("--draft", action="store_true", help="operate on slide-model.draft.json / draft.md")
    args = ap.parse_args(argv)
    if args.cmd == "rendered":            # the mode comes from the render's own stamp, not --draft
        return rendered(args.talk)
    return (stamp if args.cmd == "stamp" else check)(args.talk, args.draft)


if __name__ == "__main__":
    raise SystemExit(main())
