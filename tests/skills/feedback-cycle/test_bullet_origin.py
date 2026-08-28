#!/usr/bin/env python3
"""Tests for the bullet **origin** qualifier in `feedback_cycle.py`.

Run:  python3 tests/skills/feedback-cycle/test_bullet_origin.py

**The case that matters is `find_closed_unmirrored_excludes_editor_origin`.** `find-closed-unmirrored`
used to count every `[closed]` bullet as a candidate for the cross-Talk backlog. But the Editor also
writes closed bullets as a log of its *own* changes, so one mass edit reported 52 rows "pending
mirror" when almost none belonged in a backlog shared across Talks. Origin is now recorded when the
bullet is stamped; an unqualified bullet is presenter feedback, so every pre-existing `draft.md`
parses exactly as before.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_CLI = _ROOT / "skills" / "feedback-cycle" / "feedback_cycle.py"
sys.path.insert(0, str(_ROOT / "skills" / "feedback-cycle"))
from feedback_cycle import CLOSED_BULLET, OPEN_BULLET, _origin_of  # noqa: E402

_DRAFT = '''# 1. Sección

## 1. Primer slide

### Content

- algo.

### Presenter feedback

- [closed] 2026-08-20 — "el título es largo"
  Resolution: acortado.
- [closed] 2026-08-21 (editor) — "faltaba la fuente del dato"
  Resolution: agregada.
- [closed] 2026-08-22 (presenter) — "cambiar el orden"
  Resolution: reordenado.
'''

_BACKLOG = "# Feedback backlog\n\n## Entries\n\n<!-- Editor appends entries below this line. -->\n"

_RESULTS: list[tuple[str, bool]] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail and not ok else ''}")


def _run(tmp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_CLI), *args], capture_output=True, text=True, cwd=tmp
    )


def main() -> int:
    # --- grammar ---------------------------------------------------------------------------------
    print("bullet grammar:")
    m = CLOSED_BULLET.match('- [closed] 2026-08-20 — "el título es largo"')
    _record("unqualified_bullet_is_presenter", bool(m) and _origin_of(m) == "presenter")
    m = CLOSED_BULLET.match('- [closed] 2026-08-21 (editor) — "faltaba la fuente"')
    _record("editor_qualifier_parses", bool(m) and _origin_of(m) == "editor"
            and m.group("text") == "faltaba la fuente")
    m = OPEN_BULLET.match('- [open] 2026-08-22 (presenter) — "cambiar el orden"')
    _record("explicit_presenter_qualifier_parses", bool(m) and _origin_of(m) == "presenter")
    _record("bogus_qualifier_is_not_a_bullet",
            CLOSED_BULLET.match('- [closed] 2026-08-20 (alguien) — "x"') is None)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        talk = tmp / "talks" / "prompting"
        talk.mkdir(parents=True)
        (talk / "draft.md").write_text(_DRAFT)
        (tmp / "config").mkdir()
        (tmp / "config" / "feedback-backlog.md").write_text(_BACKLOG)
        draft, backlog = str(talk / "draft.md"), str(tmp / "config" / "feedback-backlog.md")

        print("find-closed-unmirrored:")
        r = _run(tmp, "find-closed-unmirrored", "--draft", draft, "--backlog", backlog)
        _record("find_closed_unmirrored_excludes_editor_origin",
                "found 2 closed bullet(s)" in r.stdout and "1 non-presenter-origin" in r.stdout,
                r.stdout)
        r = _run(tmp, "find-closed-unmirrored", "--draft", draft, "--backlog", backlog, "--origin", "all")
        _record("origin_all_restores_the_old_behaviour", "found 3 closed bullet(s)" in r.stdout, r.stdout)
        r = _run(tmp, "find-closed-unmirrored", "--draft", draft, "--backlog", backlog, "--origin", "editor")
        _record("origin_editor_selects_only_the_change_log",
                "found 1 closed bullet(s)" in r.stdout and "faltaba la fuente" in r.stdout, r.stdout)

        print("mirror-row:")
        r = _run(tmp, "mirror-row", "--draft", draft, "--backlog", backlog, "--line", "13", "--tags", "x")
        _record("mirror_row_refuses_editor_origin", r.returncode == 4, f"rc={r.returncode} {r.stderr}")
        r = _run(tmp, "mirror-row", "--draft", draft, "--backlog", backlog, "--line", "13",
                 "--tags", "x", "--allow-editor-origin")
        _record("mirror_row_override_works", r.returncode == 0, f"rc={r.returncode} {r.stderr}")
        r = _run(tmp, "mirror-row", "--draft", draft, "--backlog", backlog, "--line", "11", "--tags", "y")
        _record("mirror_row_accepts_presenter_origin", r.returncode == 0, f"rc={r.returncode} {r.stderr}")

        print("stamp / close:")
        (talk / "draft.md").write_text(_DRAFT + '- "algo nuevo"\n')
        line = len(_DRAFT.splitlines()) + 1
        _run(tmp, "stamp", "--draft", draft, "--line", str(line), "--date", "2026-08-28",
             "--origin", "editor")
        after = (talk / "draft.md").read_text().splitlines()[line - 1]
        _record("stamp_writes_the_origin",
                after == '- [open] 2026-08-28 (editor) — "algo nuevo"', after)
        _run(tmp, "close", "--draft", draft, "--line", str(line), "--resolution", "hecho.")
        after = (talk / "draft.md").read_text().splitlines()[line - 1]
        _record("close_preserves_the_origin",
                after == '- [closed] 2026-08-28 (editor) — "algo nuevo"', after)

    failures = sum(1 for _, ok in _RESULTS if not ok)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(_RESULTS)} bullet-origin tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
