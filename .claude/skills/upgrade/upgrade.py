#!/usr/bin/env python3
"""talksmith:upgrade — sync a downstream Talksmith fork with master.

Subcommands:
  diff   --fork <path>                       # report what would change
  apply  --fork <path> [--dry-run] [--yes]   # mirror master into the fork + run migrations

Always pulls master from https://github.com/veigap/talksmith @ main. Shallow
clones to a tempdir, mirrors the core paths into the fork, applies any
declared migrations, cleans up.

Two layers, both run in one `apply`:

1. **Strict mirror within master-owned paths.** `.claude/`, `CLAUDE.md`,
   `README.md`, `MIGRATION.md`, `config/principles.md`,
   `config/image-styles/`. Files are created, modified, OR deleted as needed
   so the fork matches master exactly. Renames upstream propagate
   automatically as "old gone + new appears". `.claude/settings.local.json`
   is excluded — user-local config master never ships.

2. **Declared migrations from MIGRATION.md.** Master can ship rename
   directives that apply *outside* the strict-mirror tree — typically per-Talk
   path renames under `talks/` (when a per-Talk file convention changes).
   Format: `<!-- migration:rename from="<glob>" to="<basename>" -->` embedded
   in MIGRATION.md prose. The skill parses these, walks the matches in the
   fork, and applies each rename idempotently. **Renames preserve content** —
   only the path changes; the file's bytes stay intact. Conflicts (both old
   and new exist) are skipped and reported, never auto-resolved.

User-owned content (`config/profile.md`, `config/learnings.md`,
`config/feedback-backlog.md`, `config/feedback-processed.md`, and the
*content* of files under `talks/`) is never overwritten or deleted — the
migration step renames paths but never touches what's inside.

See SKILL.md for the full contract.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM = "https://github.com/veigap/talksmith.git"
REF = "main"

# Core paths owned by master, relative to repo root. (path, kind ∈ {"dir","file"}).
# These are the only paths apply's strict-mirror step will create, modify, or delete files within.
CORE_PATHS: list[tuple[str, str]] = [
    (".claude", "dir"),
    ("CLAUDE.md", "file"),
    ("README.md", "file"),
    ("MIGRATION.md", "file"),
    ("config/principles.md", "file"),
    ("config/image-styles", "dir"),
]

# Files that live inside master-owned paths but are nonetheless user-local
# (gitignored, never shipped by master). Strict-mirror skips these.
USER_LOCAL: set[Path] = {
    Path(".claude/settings.local.json"),
}

# When this file was just created or modified, `apply` prints a banner.
MIGRATION_NOTES = Path("MIGRATION.md")

# Parser for rename directives embedded in MIGRATION.md.
#   <!-- migration:rename from="talks/*/master.md" to="draft.md" -->
MIGRATION_RENAME_RE = re.compile(
    r'<!--\s*migration:rename\s+from="([^"]+)"\s+to="([^"]+)"\s*-->'
)

# The fork must have this file at root (sanity check).
FORK_MARKER = "CLAUDE.md"

# User-owned paths shown in the "preserved" line for reassurance.
PRESERVED_PATHS = [
    "talks/  (content)",
    "config/profile.md",
    "config/learnings.md",
    "config/feedback-backlog.md",
    "config/feedback-processed.md",
]

# Build artifacts / OS junk — never collected on either side.
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
    """Return {created, modified, deleted, identical} for the master-owned tree."""
    m_files = _collect(master)
    f_files = _collect(fork)
    created = sorted(m_files - f_files)
    deleted = sorted(f_files - m_files - USER_LOCAL)
    common = sorted(m_files & f_files)
    modified: list[Path] = []
    identical: list[Path] = []
    for rel in common:
        if (master / rel).read_bytes() != (fork / rel).read_bytes():
            modified.append(rel)
        else:
            identical.append(rel)
    return {"created": created, "modified": modified, "deleted": deleted, "identical": identical}


def _parse_migrations(migration_md: Path) -> list[tuple[str, str]]:
    """Parse `<!-- migration:rename from="X" to="Y" -->` directives from MIGRATION.md.

    Returns a list of (from_glob, to_basename) tuples in declaration order.
    Returns [] if the file doesn't exist or contains no directives.

    Directives whose `from` or `to` contain `<` or `>` are skipped — those are
    placeholder examples in prose / templates (e.g. `from="<glob>"`), not real
    directives. Real directives use valid path syntax.
    """
    if not migration_md.exists():
        return []
    text = migration_md.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for m in MIGRATION_RENAME_RE.finditer(text):
        src, dst = m.group(1), m.group(2)
        if any(c in src or c in dst for c in "<>"):
            continue
        out.append((src, dst))
    return out


def _expand_glob(fork: Path, pattern: str) -> list[Path]:
    """Expand a glob like `talks/*/master.md` against the fork. Returns absolute paths.

    Supports `*` as one path-segment wildcard (any segment that contains a `*` is
    treated as a glob component). Only matches files, not directories.
    """
    parts = pattern.split("/")
    return sorted(_expand_segments(fork, parts))


def _expand_segments(base: Path, segments: list[str]) -> list[Path]:
    if not segments:
        return [base] if base.is_file() else []
    head, *rest = segments
    if "*" in head:
        if not base.is_dir():
            return []
        out: list[Path] = []
        for child in sorted(base.iterdir()):
            if fnmatch.fnmatchcase(child.name, head):
                out.extend(_expand_segments(child, rest))
        return out
    next_path = base / head
    if rest:
        return _expand_segments(next_path, rest) if next_path.is_dir() else []
    return [next_path] if next_path.is_file() else []


def _apply_migrations(
    fork: Path, migrations: list[tuple[str, str]], dry_run: bool
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    """Apply each `(from_glob, to_basename)` rename idempotently.

    For each match:
    - if old exists, new doesn't  → rename (records under `applied`).
    - if old doesn't exist        → no-op (already done; not reported).
    - if both old and new exist   → conflict (records under `conflicts`).

    Returns (applied, conflicts) where each entry is (old_path, new_path), absolute.
    """
    applied: list[tuple[Path, Path]] = []
    conflicts: list[tuple[Path, Path]] = []
    for from_glob, to_name in migrations:
        for old in _expand_glob(fork, from_glob):
            new = old.parent / to_name
            if new.exists():
                conflicts.append((old, new))
                continue
            if not dry_run:
                os.replace(old, new)
            applied.append((old, new))
    return applied, conflicts


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _rmdir_empty(start: Path, stop: Path) -> None:
    """Walk up from `start` removing empty directories until reaching `stop`."""
    cur = start
    while cur != stop and cur.exists() and cur.is_dir() and not any(cur.iterdir()):
        cur.rmdir()
        cur = cur.parent


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
        migrations = _parse_migrations(master / MIGRATION_NOTES)
        # Dry-run the migrations to see what would happen without actually renaming.
        m_applied, m_conflicts = _apply_migrations(fork, migrations, dry_run=True)

        print(f"fork:   {fork}")
        print(f"master: {UPSTREAM}@{REF}")
        print()
        print("Summary:")
        print(f"  {len(c['created']):3d} file(s) would be created   (master-owned paths)")
        print(f"  {len(c['modified']):3d} file(s) would be modified  (master-owned paths)")
        print(f"  {len(c['deleted']):3d} file(s) would be deleted   (master-owned paths, no longer in master)")
        print(f"  {len(m_applied):3d} file(s) would be renamed   (declared migrations, content preserved)")
        if m_conflicts:
            print(f"  {len(m_conflicts):3d} migration conflict(s)     (both old and new exist — manual resolution)")
        print(f"  {len(c['identical']):3d} file(s) already up-to-date (master-owned paths)")
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
        if c["deleted"]:
            print("\nDeleted (in fork but no longer in master — usually a rename or removal upstream):")
            for p in c["deleted"]:
                print(f"  - {p}")
        if m_applied:
            print("\nRenamed (per declared migrations — content preserved, only path changes):")
            for old, new in m_applied:
                print(f"  → {old.relative_to(fork)}  →  {new.relative_to(fork)}")
        if m_conflicts:
            print("\nMigration conflicts (both old and new exist — needs manual resolution):")
            for old, new in m_conflicts:
                print(f"  ! {old.relative_to(fork)}  AND  {new.relative_to(fork)}")
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
        migrations = _parse_migrations(master / MIGRATION_NOTES)
        # Dry-run the migrations once to surface the plan in the prompt.
        m_planned, m_conflicts_pre = _apply_migrations(fork, migrations, dry_run=True)

        if not args.yes and not args.dry_run:
            print(f"fork:   {fork}")
            print(f"master: {UPSTREAM}@{REF}")
            print(
                f"plan:   {len(c['created'])} create, {len(c['modified'])} modify, "
                f"{len(c['deleted'])} delete, {len(m_planned)} rename, "
                f"{len(c['identical'])} unchanged"
            )
            print(f"preserved (user-owned, never touched): {', '.join(PRESERVED_PATHS)}")
            if c["deleted"]:
                print()
                print("Files that would be deleted (no longer in master):")
                for p in c["deleted"]:
                    print(f"  - {p}")
            if m_planned:
                print()
                print("Files that would be renamed (content preserved):")
                for old, new in m_planned:
                    print(f"  → {old.relative_to(fork)}  →  {new.relative_to(fork)}")
            if m_conflicts_pre:
                print()
                print("Migration conflicts — will be SKIPPED (needs manual resolution):")
                for old, new in m_conflicts_pre:
                    print(f"  ! {old.relative_to(fork)}  AND  {new.relative_to(fork)}")
            try:
                resp = input("\nproceed? [y/N] ").strip().lower()
            except EOFError:
                resp = ""
            if resp not in {"y", "yes"}:
                print("aborted by user.")
                return 3

        created = modified = deleted = 0
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
            for rel in c["deleted"]:
                target = fork / rel
                if not args.dry_run and target.exists():
                    target.unlink()
                    _rmdir_empty(target.parent, fork)
                deleted += 1
        except OSError as exc:
            print(f"error: failed at {rel}: {exc}", file=sys.stderr)
            return 4

        # Migrations run AFTER strict-mirror so the migration list comes from the
        # freshly mirrored MIGRATION.md (the same one we already parsed). Re-running
        # _apply_migrations isn't quite right here because the strict-mirror step
        # may have created new files — but migrations only touch paths under
        # talks/ etc. and the strict-mirror tree is disjoint from those, so the
        # dry-run plan we computed is still valid.
        m_applied, m_conflicts = _apply_migrations(fork, migrations, dry_run=args.dry_run)

        tag = "  [dry-run]" if args.dry_run else ""
        print(f"applied to {fork}:{tag}")
        print(f"  created:  {created} file(s)")
        print(f"  modified: {modified} file(s)")
        print(f"  deleted:  {deleted} file(s)")
        print(f"  renamed:  {len(m_applied)} file(s) (content preserved)")
        if m_conflicts:
            print(f"  conflicts: {len(m_conflicts)} migration(s) skipped — see list above")
        print(f"  preserved (user-owned, not touched): {', '.join(PRESERVED_PATHS)}")

        if MIGRATION_NOTES in c["created"] or MIGRATION_NOTES in c["modified"]:
            action = "created" if MIGRATION_NOTES in c["created"] else "updated"
            print()
            print("─" * 72)
            print(f"⚠  MIGRATION.md was {action} in this upgrade.")
            print()
            print("   File-path renames declared by master (e.g. per-Talk path changes)")
            print("   were applied automatically above. Open MIGRATION.md for any")
            print("   additional notes — semantic changes that need your judgement, not")
            print("   just mechanical renames:")
            print()
            print(f"     {fork / MIGRATION_NOTES}")
            if m_conflicts:
                print()
                print("   Some declared renames were skipped due to conflicts; resolve")
                print("   by hand and re-run `upgrade apply` to finish them.")
            print("─" * 72)
        return 0
    finally:
        shutil.rmtree(master, ignore_errors=True)


# ─── arg parsing ──────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="upgrade", description=f"Mirror master ({UPSTREAM}@{REF}) into a Talksmith fork and apply declared migrations.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("diff", help="report what would change in the fork (creates, modifies, deletes, renames)")
    pd.add_argument("--fork", required=True)
    pd.set_defaults(func=cmd_diff)

    pa = sub.add_parser("apply", help="mirror master into the fork + apply declared migrations (renames preserve content)")
    pa.add_argument("--fork", required=True)
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--yes", action="store_true")
    pa.set_defaults(func=cmd_apply)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
