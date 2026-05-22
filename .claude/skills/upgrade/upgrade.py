#!/usr/bin/env python3
"""talksmith:upgrade — sync a downstream Talksmith fork with master.

Subcommands:
  diff   --fork <path>                       # report what would change
  apply  --fork <path> [--dry-run] [--yes]   # copy create + modify; never deletes

Always pulls master from https://github.com/veigap/talksmith @ main. Shallow
clones to a tempdir, copies the core paths into the fork, cleans up the
tempdir.

`apply` only **creates and modifies** files. It never deletes anything from
the fork — fork-only files (per-fork customizations, removed-upstream
artifacts, anything) are left in place. Structural changes (renames,
removals) are documented in MIGRATION.md at the repo root, which `apply`
copies in like any other core file and surfaces with a banner when it was
just created or updated. The user runs the manual steps from there.

See SKILL.md for the full contract.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM = "https://github.com/veigap/talksmith.git"
REF = "main"

# Core paths owned by master, relative to repo root. (path, kind ∈ {"dir","file"}).
CORE_PATHS: list[tuple[str, str]] = [
    (".claude", "dir"),
    ("CLAUDE.md", "file"),
    ("README.md", "file"),
    ("MIGRATION.md", "file"),
    ("config/principles.md", "file"),
    ("config/image-styles", "dir"),
]

# When this file was just created or modified, `apply` prints a banner.
MIGRATION_NOTES = Path("MIGRATION.md")

# The fork must have this file at root (sanity check).
FORK_MARKER = "CLAUDE.md"

# Always preserved (never touched), shown to the user as a courtesy.
PRESERVED_PATHS = [
    "talks/",
    "config/profile.md",
    "config/learnings.md",
    "config/feedback-backlog.md",
    "config/feedback-processed.md",
]

# Build artifacts / OS junk skipped during walks.
IGNORE_DIRS = {"__pycache__", ".DS_Store", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORE_SUFFIXES = {".pyc", ".pyo"}


def _fetch_master() -> Path:
    """Shallow-clone upstream@main to a fresh tempdir; return the path."""
    if not shutil.which("git"):
        raise SystemExit("error: `git` not found on PATH; install git and retry")
    tmpdir = Path(tempfile.mkdtemp(prefix="talksmith-master-"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", REF, UPSTREAM, str(tmpdir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise SystemExit(f"error: git clone failed for {UPSTREAM}@{REF}:\n{stderr.strip()}")
    return tmpdir


def _walk_files(root: Path, rel_root: Path) -> list[Path]:
    """List files under `root`, paths relative to `rel_root`. Skips build artifacts."""
    if not root.exists():
        return []
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if name in IGNORE_DIRS or any(name.endswith(s) for s in IGNORE_SUFFIXES):
                continue
            out.append((Path(dirpath) / name).relative_to(rel_root))
    return sorted(out)


def _collect(root: Path) -> set[Path]:
    """Set of relative paths under `root` covered by CORE_PATHS."""
    files: set[Path] = set()
    for rel, kind in CORE_PATHS:
        target = root / rel
        if kind == "file":
            if target.exists():
                files.add(Path(rel))
        else:
            files.update(_walk_files(target, root))
    return files


def _classify(master: Path, fork: Path) -> dict[str, list[Path]]:
    """Return {created, modified, identical} — what apply would do."""
    m_files = _collect(master)
    f_files = _collect(fork)
    created = sorted(m_files - f_files)
    common = sorted(m_files & f_files)
    modified: list[Path] = []
    identical: list[Path] = []
    for rel in common:
        if (master / rel).read_bytes() != (fork / rel).read_bytes():
            modified.append(rel)
        else:
            identical.append(rel)
    return {"created": created, "modified": modified, "identical": identical}


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


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


# ─── diff ─────────────────────────────────────────────────────────────────────

def cmd_diff(args: argparse.Namespace) -> int:
    fork = Path(args.fork).resolve()
    master = _fetch_master()
    try:
        err = _validate_fork(fork, master)
        if err is not None:
            return err
        c = _classify(master, fork)
        print(f"fork:   {fork}")
        print(f"master: {UPSTREAM}@{REF}")
        print()
        print("Summary:")
        print(f"  {len(c['created']):3d} file(s) would be created")
        print(f"  {len(c['modified']):3d} file(s) would be modified")
        print(f"  {len(c['identical']):3d} file(s) already up-to-date")
        if c["created"]:
            print("\nCreated (new in master, missing in fork):")
            for p in c["created"]:
                print(f"  + {p}")
        if c["modified"]:
            print("\nModified (differ between master and fork):")
            for p in c["modified"]:
                delta = (master / p).stat().st_size - (fork / p).stat().st_size
                sign = "+" if delta >= 0 else "-"
                print(f"  ~ {p}  ({sign}{abs(delta)} bytes)")
        return 0
    finally:
        shutil.rmtree(master, ignore_errors=True)


# ─── apply ────────────────────────────────────────────────────────────────────

def cmd_apply(args: argparse.Namespace) -> int:
    fork = Path(args.fork).resolve()
    master = _fetch_master()
    try:
        err = _validate_fork(fork, master)
        if err is not None:
            return err
        c = _classify(master, fork)

        if not args.yes and not args.dry_run:
            print(f"fork:   {fork}")
            print(f"master: {UPSTREAM}@{REF}")
            print(f"plan:   {len(c['created'])} create, {len(c['modified'])} modify, {len(c['identical'])} unchanged")
            print(f"preserved (fork-owned, never touched): {', '.join(PRESERVED_PATHS)}")
            try:
                resp = input("\nproceed? [y/N] ").strip().lower()
            except EOFError:
                resp = ""
            if resp not in {"y", "yes"}:
                print("aborted by user.")
                return 3

        created = modified = 0
        rel = None
        try:
            for rel in c["created"]:
                if not args.dry_run:
                    _atomic_copy(master / rel, fork / rel)
                created += 1
            for rel in c["modified"]:
                if not args.dry_run:
                    _atomic_copy(master / rel, fork / rel)
                modified += 1
        except OSError as exc:
            print(f"error: copy failed at {rel}: {exc}", file=sys.stderr)
            return 4

        tag = "  [dry-run]" if args.dry_run else ""
        print(f"applied to {fork}:{tag}")
        print(f"  created:  {created} file(s)")
        print(f"  modified: {modified} file(s)")
        print(f"  preserved (fork-owned, not touched): {', '.join(PRESERVED_PATHS)}")

        if MIGRATION_NOTES in c["created"] or MIGRATION_NOTES in c["modified"]:
            action = "created" if MIGRATION_NOTES in c["created"] else "updated"
            print()
            print("─" * 72)
            print(f"⚠  MIGRATION.md was {action} in this upgrade.")
            print()
            print("   Master shipped structural changes (renames, removals, restructures)")
            print("   that this skill is intentionally not allowed to perform on your fork.")
            print("   Open the file and run the manual steps in the dated section(s) added")
            print("   since your last upgrade:")
            print()
            print(f"     {fork / MIGRATION_NOTES}")
            print()
            print("   Without those steps, your fork will keep working but may carry stale")
            print("   files from upstream renames, and per-Talk content under talks/ may")
            print("   drift out of alignment with the new spec.")
            print("─" * 72)
        return 0
    finally:
        shutil.rmtree(master, ignore_errors=True)


# ─── arg parsing ──────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="upgrade", description=f"Sync a downstream Talksmith fork with {UPSTREAM}@{REF}.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("diff", help="report which core files differ between master and a fork")
    pd.add_argument("--fork", required=True)
    pd.set_defaults(func=cmd_diff)

    pa = sub.add_parser("apply", help="copy core files from master into a fork (create + modify only; never deletes)")
    pa.add_argument("--fork", required=True)
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--yes", action="store_true")
    pa.set_defaults(func=cmd_apply)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
