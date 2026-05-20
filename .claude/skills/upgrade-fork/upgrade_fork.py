#!/usr/bin/env python3
"""talksmith:upgrade-fork — sync a downstream Talksmith fork with master.

Subcommands:
  diff   --fork <path> [--upstream URL] [--ref REF] [--local-master PATH] [--format human|json] [--verbose] [--keep-clone]
  apply  --fork <path> [--upstream URL] [--ref REF] [--local-master PATH] [--prune] [--dry-run] [--yes] [--keep-clone]

Default behavior: shallow-clone the upstream repo at the specified ref and use
that as the master to compare/copy from. Pass --local-master to skip the clone
and use a local directory instead (useful for offline / dev iteration on the
upstream repo itself).

See SKILL.md for the full contract.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_UPSTREAM = "https://github.com/veigap/talksmith.git"
DEFAULT_REF = "main"

# Core paths owned by master, relative to repo root.
# Tuple: (path, kind) where kind ∈ {"dir", "file"}.
CORE_PATHS: list[tuple[str, str]] = [
    (".claude", "dir"),
    ("CLAUDE.md", "file"),
    ("README.md", "file"),
    ("knowledge/principles.md", "file"),
    ("knowledge/image-styles", "dir"),
]

# Subtrees where --prune is allowed to delete fork-only files.
PRUNE_ROOTS = {".claude", "knowledge/image-styles"}

# Sanity marker — the fork must contain this file at root.
FORK_MARKER = "CLAUDE.md"

# Paths that are *always* preserved (never touched), shown to the user as a courtesy.
PRESERVED_PATHS = [
    "talks/",
    "knowledge/profile.md",
    "knowledge/learnings.md",
    "knowledge/feedback-backlog.md",
    "knowledge/feedback-processed.md",
]


def _have_git() -> bool:
    return shutil.which("git") is not None


def _fetch_master(upstream: str, ref: str) -> Path:
    """Shallow-clone upstream@ref to a fresh tempdir; return the path.

    Caller owns cleanup (see `_cleanup_master`). Aborts loudly if git is missing
    or the clone fails — never falls back silently.
    """
    if not _have_git():
        raise SystemExit("error: `git` not found on PATH; install git or pass --local-master <path>")
    tmpdir = Path(tempfile.mkdtemp(prefix="talksmith-master-"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, upstream, str(tmpdir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise SystemExit(f"error: git clone failed for {upstream}@{ref}:\n{stderr.strip()}")
    return tmpdir


def _cleanup_master(path: Path, keep: bool) -> None:
    if keep:
        print(f"(kept master clone at {path})", file=sys.stderr)
        return
    shutil.rmtree(path, ignore_errors=True)


def _resolve_master(args: argparse.Namespace) -> tuple[Path, bool]:
    """Return (master_path, is_ephemeral). Ephemeral masters get cleaned up after the command."""
    if args.local_master:
        master = Path(args.local_master).resolve()
        if not master.exists() or not master.is_dir():
            raise SystemExit(f"error: --local-master path is not a directory: {master}")
        if not (master / FORK_MARKER).exists():
            raise SystemExit(f"error: --local-master is missing {FORK_MARKER} — not a Talksmith repo: {master}")
        return master, False
    master = _fetch_master(args.upstream, args.ref)
    return master, True


def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def _is_text(b: bytes) -> bool:
    # Heuristic: text iff no NUL bytes and most chars are printable/whitespace.
    if b"\0" in b:
        return False
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


# Path fragments that are always skipped during walks (build artifacts, OS junk).
IGNORE_DIRS = {"__pycache__", ".DS_Store", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORE_SUFFIXES = {".pyc", ".pyo"}


def _walk_files(root: Path, rel_root: Path) -> list[Path]:
    """Return list of file paths RELATIVE to rel_root, recursive. Skips build artifacts."""
    if not root.exists():
        return []
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Mutate dirnames in place so os.walk skips ignored subtrees.
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if name in IGNORE_DIRS:
                continue
            if any(name.endswith(s) for s in IGNORE_SUFFIXES):
                continue
            full = Path(dirpath) / name
            out.append(full.relative_to(rel_root))
    return sorted(out)


def _collect_master_files(master: Path) -> set[Path]:
    files: set[Path] = set()
    for rel, kind in CORE_PATHS:
        target = master / rel
        if kind == "file":
            if target.exists():
                files.add(Path(rel))
        else:
            for rp in _walk_files(target, master):
                files.add(rp)
    return files


def _collect_fork_files_in_core(fork: Path) -> set[Path]:
    files: set[Path] = set()
    for rel, kind in CORE_PATHS:
        target = fork / rel
        if kind == "file":
            if target.exists():
                files.add(Path(rel))
        else:
            for rp in _walk_files(target, fork):
                files.add(rp)
    return files


def _classify(master: Path, fork: Path) -> dict[str, list[Path]]:
    m_files = _collect_master_files(master)
    f_files = _collect_fork_files_in_core(fork)
    created = sorted(m_files - f_files)
    pruneable = sorted(f_files - m_files)
    common = sorted(m_files & f_files)
    modified: list[Path] = []
    identical: list[Path] = []
    for rel in common:
        mb = _read_bytes(master / rel)
        fb = _read_bytes(fork / rel)
        if mb != fb:
            modified.append(rel)
        else:
            identical.append(rel)
    return {
        "created": created,
        "modified": modified,
        "identical": identical,
        "pruneable": pruneable,
    }


def _within_prune_root(rel: Path) -> bool:
    s = str(rel)
    return any(s == r or s.startswith(r + "/") for r in PRUNE_ROOTS)


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


# ─── diff ─────────────────────────────────────────────────────────────────────

def _print_human_diff(master: Path, fork: Path, classes: dict[str, list[Path]], verbose: bool) -> None:
    print(f"upgrading fork: {fork}")
    print(f"master:        {master}")
    print()
    print("Summary:")
    print(f"  {len(classes['created']):3d} file(s) would be created")
    print(f"  {len(classes['modified']):3d} file(s) would be modified")
    print(f"  {len(classes['pruneable']):3d} file(s) only in fork (use --prune to remove)")
    print(f"  {len(classes['identical']):3d} file(s) already up-to-date")
    print()
    if classes["created"]:
        print("Created (new in master, missing in fork):")
        for p in classes["created"]:
            print(f"  + {p}")
        print()
    if classes["modified"]:
        print("Modified (differ between master and fork):")
        for p in classes["modified"]:
            m_size = (master / p).stat().st_size
            f_size = (fork / p).stat().st_size
            delta = m_size - f_size
            sign = "+" if delta >= 0 else "-"
            print(f"  ~ {p}  ({sign}{abs(delta)} bytes)")
        print()
        if verbose:
            print("Unified diffs (master ← fork):")
            for p in classes["modified"]:
                mb = _read_bytes(master / p)
                fb = _read_bytes(fork / p)
                if not (_is_text(mb) and _is_text(fb)):
                    print(f"--- {p}: binary differs ---")
                    continue
                print(f"--- {p} ---")
                lines = difflib.unified_diff(
                    fb.decode("utf-8").splitlines(keepends=True),
                    mb.decode("utf-8").splitlines(keepends=True),
                    fromfile=f"fork/{p}",
                    tofile=f"master/{p}",
                    n=2,
                )
                sys.stdout.writelines(lines)
                print()
    if classes["pruneable"]:
        print("Pruneable (in fork only, not in master) — use --prune to remove:")
        for p in classes["pruneable"]:
            print(f"  - {p}")
        print()


def _validate_fork(fork: Path, master: Path) -> int | None:
    if not fork.exists() or not fork.is_dir():
        print(f"error: fork path is not a directory: {fork}", file=sys.stderr)
        return 2
    if not (fork / FORK_MARKER).exists():
        print(f"error: fork is missing {FORK_MARKER} at root — refusing to act (is this a Talksmith fork?): {fork}", file=sys.stderr)
        return 2
    if fork.resolve() == master.resolve():
        print(f"error: fork resolves to the same path as master: {master}", file=sys.stderr)
        return 2
    return None


def cmd_diff(args: argparse.Namespace) -> int:
    fork = Path(args.fork).resolve()
    master, ephemeral = _resolve_master(args)
    try:
        err = _validate_fork(fork, master)
        if err is not None:
            return err
        classes = _classify(master, fork)
        if args.format == "json":
            payload = {
                "master": str(master),
                "upstream": args.upstream if not args.local_master else None,
                "ref": args.ref if not args.local_master else None,
                "fork": str(fork),
                "created": [str(p) for p in classes["created"]],
                "modified": [str(p) for p in classes["modified"]],
                "pruneable": [str(p) for p in classes["pruneable"]],
                "identical_count": len(classes["identical"]),
            }
            json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            _print_human_diff(master, fork, classes, args.verbose)
        return 0
    finally:
        if ephemeral:
            _cleanup_master(master, args.keep_clone)


# ─── apply ────────────────────────────────────────────────────────────────────

def cmd_apply(args: argparse.Namespace) -> int:
    fork = Path(args.fork).resolve()
    master, ephemeral = _resolve_master(args)
    try:
        return _cmd_apply_inner(args, fork, master)
    finally:
        if ephemeral:
            _cleanup_master(master, args.keep_clone)


def _cmd_apply_inner(args: argparse.Namespace, fork: Path, master: Path) -> int:
    err = _validate_fork(fork, master)
    if err is not None:
        return err
    classes = _classify(master, fork)

    if not args.yes and not args.dry_run:
        print(f"upgrading fork: {fork}")
        print(f"master:        {master}{'  (from ' + args.upstream + '@' + args.ref + ')' if not args.local_master else ''}")
        n_c = len(classes["created"])
        n_m = len(classes["modified"])
        n_p = len(classes["pruneable"]) if args.prune else 0
        print(f"plan: {n_c} create, {n_m} modify, {n_p} prune, {len(classes['identical'])} unchanged")
        print(f"preserved (fork-owned, never touched): {', '.join(PRESERVED_PATHS)}")
        print()
        try:
            resp = input("proceed? [y/N] ").strip().lower()
        except EOFError:
            resp = ""
        if resp not in {"y", "yes"}:
            print("aborted by user.")
            return 3

    created = 0
    modified = 0
    pruned = 0
    try:
        for rel in classes["created"]:
            src = master / rel
            dst = fork / rel
            if not args.dry_run:
                _atomic_copy(src, dst)
            created += 1
        for rel in classes["modified"]:
            src = master / rel
            dst = fork / rel
            if not args.dry_run:
                _atomic_copy(src, dst)
            modified += 1
        if args.prune:
            for rel in classes["pruneable"]:
                if not _within_prune_root(rel):
                    continue
                target = fork / rel
                if not args.dry_run and target.exists():
                    target.unlink()
                pruned += 1
            # Optionally clean empty dirs under prune roots
            if not args.dry_run:
                for root in PRUNE_ROOTS:
                    root_path = fork / root
                    if not root_path.exists():
                        continue
                    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
                        if not dirnames and not filenames and Path(dirpath) != root_path:
                            os.rmdir(dirpath)
    except OSError as exc:
        print(f"error: copy failed at {rel}: {exc}", file=sys.stderr)
        return 4

    tag = "  [dry-run]" if args.dry_run else ""
    print(f"applied to {fork}:{tag}")
    print(f"  created:  {created} file(s)")
    print(f"  modified: {modified} file(s)")
    print(f"  pruned:   {pruned} file(s)")
    print(f"  preserved (fork-owned, not touched): {', '.join(PRESERVED_PATHS)}")
    return 0


# ─── arg parsing ──────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="upgrade_fork", description="Sync a downstream Talksmith fork with master core.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def _add_master_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--upstream", default=DEFAULT_UPSTREAM, help=f"upstream git URL (default: {DEFAULT_UPSTREAM})")
        sp.add_argument("--ref", default=DEFAULT_REF, help=f"upstream branch / tag / sha (default: {DEFAULT_REF})")
        sp.add_argument("--local-master", help="use this local directory as master instead of cloning upstream")
        sp.add_argument("--keep-clone", action="store_true", help="keep the cloned master tempdir on exit (debug)")

    pd = sub.add_parser("diff", help="report which core files differ between master and a fork")
    pd.add_argument("--fork", required=True)
    _add_master_args(pd)
    pd.add_argument("--format", choices=["human", "json"], default="human")
    pd.add_argument("--verbose", action="store_true", help="print unified diffs for every modified text file")
    pd.set_defaults(func=cmd_diff)

    pa = sub.add_parser("apply", help="copy core files from master into a fork")
    pa.add_argument("--fork", required=True)
    _add_master_args(pa)
    pa.add_argument("--prune", action="store_true")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--yes", action="store_true")
    pa.set_defaults(func=cmd_apply)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
