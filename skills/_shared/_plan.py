"""Plan-file plumbing shared by the two Step-6 polish skills.

`polish-ascii` and `polish-images` are deliberate siblings: same staged sequence (scan → extract →
prepare-render-args → stamp-renders → cleanup), same plan JSON envelope, same `gc` pass. Only the
*block* differs — a ` ```ascii ` fence versus a `<!-- generate-image: … -->` directive. Everything
around that block is identical, and when it lived in both files it drifted: one grew an `-o` flag
the other didn't, one's error text said "plan" where the other's said "plan JSON".

So the scaffolding lives here, imported the same way both already import `_context`:

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
    from _plan import add_plan_args, load_plan, read_json_arg, referenced_stems, relocate_staged, run_gc

The block-specific parts — what a scan detects, what a sidecar holds, how a stamp is computed —
stay in each skill. This is the shared frame, not shared behavior.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence

# Every `![…](images/<name>)` reference, including the ones inside the `<!-- aside: … -->` comments
# polish-images writes — the pattern is the same either way, so `gc` sees the same live set.
IMG_REF_RE = re.compile(r"!\[[^\]]*\]\(\s*(?:\./)?images/([^)\s]+?)\s*\)")
IMG_EXT_RE = re.compile(r"\.(svg|png|jpe?g|gif|webp|avif)$", re.IGNORECASE)


def add_plan_args(p: argparse.ArgumentParser) -> None:
    """The argument trio every plan-consuming subcommand takes."""
    p.add_argument("--final", required=True, help="path to the Talk's final.md")
    p.add_argument("--plan", required=True)
    p.add_argument("--dry-run", action="store_true")


def add_scan_args(p: argparse.ArgumentParser, help_final: str) -> None:
    """`scan`'s input and output, spelled the way every other subcommand spells them.

    `final.md` is accepted positionally (the original form) **or** as `--final`, and the JSON can
    go to a file with `-o/--output`. The two skills' SKILL.md tables promised `--final` and `-o`
    on every subcommand; `scan` alone refused them with an argparse exit 2, and the role had to
    fall back to the positional and a shell redirect to recover.
    """
    p.add_argument("final_path", nargs="?", help=help_final)
    p.add_argument("--final", dest="final_flag", help="same as the positional path")
    p.add_argument("-o", "--output", help="write the JSON here instead of stdout ('-' = stdout)")


def scan_final_path(args: argparse.Namespace) -> Path | int:
    """The resolved `final.md` for `scan` — or an exit code, already reported on stderr."""
    given = {v for v in (args.final_path, args.final_flag) if v}
    if len(given) != 1:
        print("error: scan takes final.md once — positionally or as --final", file=sys.stderr)
        return 2
    final_path = Path(given.pop()).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    return final_path


def write_json(obj: Any, output: str | None) -> None:
    """Write `obj` as indented JSON to `output`, or to stdout when it is unset or `-`."""
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if output and output != "-":
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def load_plan(args: argparse.Namespace) -> tuple[Path, dict[str, Any]] | int:
    """`(resolved final.md path, plan dict)` — or an exit code, already reported on stderr.

    Returning the code rather than raising keeps every caller a plain `if isinstance(x, int)`, and
    keeps the exit-code contract (2 = malformed input) in one place instead of eight.
    """
    final_path = Path(args.final).resolve()
    if not final_path.exists():
        print(f"error: final.md not found: {final_path}", file=sys.stderr)
        return 2
    if args.plan == "-":
        plan_text = sys.stdin.read()
    else:
        plan_path = Path(args.plan)
        if not plan_path.exists():
            print(f"error: plan not found: {plan_path}", file=sys.stderr)
            return 2
        plan_text = plan_path.read_text()
    try:
        plan = json.loads(plan_text)
    except json.JSONDecodeError as e:
        print(f"error: plan JSON invalid: {e}", file=sys.stderr)
        return 2
    return final_path, plan


def read_json_arg(value: str) -> Any:
    """Read a JSON argument that may be a path or `-` for stdin."""
    text = sys.stdin.read() if value == "-" else Path(value).read_text()
    return json.loads(text)


def referenced_stems(final_text: str) -> set[str]:
    """Every `images/<name>` basename referenced by final.md, extension stripped → stem.

    This is `gc`'s live set: a generated file whose stem is absent here is orphaned.
    """
    return {IMG_EXT_RE.sub("", m.group(1).rsplit("/", 1)[-1]) for m in IMG_REF_RE.finditer(final_text)}


# ── gc: list, then (with --apply) move to a recoverable trash ───────────────
# `gc --apply` used to `unlink()`. The orphan test is "no image ref in final.md", and final.md is
# exactly the file a renumbering pass rewrites — so a render that was orphaned only for one pass
# (or reusable under a new name) was gone for good. Moving it under `images/.trash/<timestamp>/`
# costs nothing, keeps the relative layout (`.critique/` included) so restoring is one `mv`, and is
# invisible to every other stage: they all glob `images/*`, never recursively.
TRASH_DIRNAME = ".trash"


def trash_dir(images_dir: Path) -> Path:
    """A fresh `images/.trash/<YYYYMMDD-HHMMSS>[-N]/` — never an existing one, so two runs never mix."""
    base = images_dir / TRASH_DIRNAME / datetime.now().strftime("%Y%m%d-%H%M%S")
    dest, n = base, 1
    while dest.exists():
        n += 1
        dest = base.with_name(f"{base.name}-{n}")
    return dest


def run_gc(talk_root: Path, images_dir: Path, orphans: list[str], targets: list[Path],
           apply: bool, noun: str) -> int:
    """Report `gc`'s orphans and, with `apply`, move `targets` into a fresh trash folder.

    The skill decides *what* is orphaned (each proves "generated" its own way); this decides what
    happens to it, identically for both. Returns the exit code.
    """
    if not orphans:
        print(f"gc: no orphaned generated {noun} assets — images/ is clean")
        return 0
    print(f"gc: {len(orphans)} orphaned generated {noun}(s), {len(targets)} file(s):")
    for f in targets:
        print(f"  {f.relative_to(talk_root)}")
    if not apply:
        print("gc: dry-run — pass --apply to move them to images/.trash/")
        return 0
    dest = trash_dir(images_dir)
    moved = 0
    for f in targets:
        to = dest / f.relative_to(images_dir)
        try:
            to.parent.mkdir(parents=True, exist_ok=True)
            os.replace(f, to)
            moved += 1
        except OSError as e:
            print(f"  ⚠  could not move {f}: {e}", file=sys.stderr)
    print(f"gc: moved {moved} file(s) to {dest.relative_to(talk_root)}/ — restore with `mv`, "
          f"or delete that folder once you are sure")
    return 0


# ── render reuse: copy a stamped render to its renumbered name ──────────────
# Both skills reuse a render by digest when a renumbering renamed its slide: the donor's files are
# copied to the new stem instead of ordering a fresh render. Each skill finds its own donor (the
# digest lives inside an SVG for one, in an `.imgstamp` for the other) and names its own companion
# files; the copy itself is this, because the hazard is the same for both. Names are positional,
# so a renumbering is a chain (slide 2 → 3 while 3 → 4) or a swap, and the file being written to
# `s1-3-…` is the very one that must move on to `s1-4-…`. Copying in plan order hands the second
# slide the first one's picture; reading every donor first cannot.

def relocate_staged(stage_dir: Path, moves: Sequence[tuple[Sequence[Path], Sequence[Path]]],
                    rewrite: Callable[[Path, Path, Path], str | None] | None = None) -> list[Path]:
    """Copy each donor's files to its destination's, position by position, staging every donor first.

    `moves` holds `(donor_files, destination_files)` pairs of equal length. Every donor file that
    exists is copied into a temporary directory under `stage_dir` before any destination is
    written, so the copies see the pre-pass state whatever the order. `rewrite(src, dst, staged)`
    may return replacement text for a file (e.g. a log that names its stem); `None` copies it
    byte-for-byte. A copy, never a move: the old name may stay referenced until `cleanup`, and `gc`
    retires it afterwards. Returns the donor files that were absent (nothing is written for them).
    """
    missing: list[Path] = []
    if not moves:
        return missing
    with tempfile.TemporaryDirectory(prefix=".reuse-", dir=stage_dir) as td:
        staged: dict[Path, Path] = {}
        for srcs, _ in moves:
            for src in srcs:
                if src not in staged and src.exists():
                    staged[src] = Path(td) / f"{len(staged)}{src.suffix}"   # by index: names collide across dirs
                    shutil.copy2(src, staged[src])
        for srcs, dsts in moves:
            for src, dst in zip(srcs, dsts):
                if src not in staged:
                    missing.append(src)
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                text = rewrite(src, dst, staged[src]) if rewrite else None
                if text is None:
                    shutil.copy2(staged[src], dst)
                else:
                    dst.write_text(text)
    return missing
