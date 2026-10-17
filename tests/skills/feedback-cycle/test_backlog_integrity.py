#!/usr/bin/env python3
"""Tests for the integrity of `config/feedback-backlog.md` / `feedback-processed.md`.

Run:  python3 tests/skills/feedback-cycle/test_backlog_integrity.py

Two defects found in a real working directory (BUG-20261004-10):

- **Tags on the wrong row.** `mirror-row` took a bare `--line`. Line numbers go stale inside a
  round — every `close` inserts a `Resolution:` line — so a stale `--line` landed on a neighbouring
  `[closed]` bullet and mirrored *it*, with the tags meant for another. `--expect-text` now proves
  which bullet the caller meant (exit 5 on mismatch), and a bullet already in the backlog is
  refused (exit 6).
- **Move only copied.** Step 8's Move was a hand edit; promoted rows reached `feedback-processed.md`
  and stayed in the backlog, so every later recurrence scan counted them twice. `move` appends and
  deletes in one call, sweeps rows an earlier copy-only Move left behind, and post-checks the
  invariant from disk.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_CLI = _ROOT / "skills" / "feedback-cycle" / "feedback_cycle.py"
sys.path.insert(0, str(_ROOT / "skills" / "feedback-cycle"))
from feedback_cycle import _parse_rows  # noqa: E402

_DRAFT = '''# 1. Sección

## 1. Primer slide

### Presenter feedback

- [open] 2026-08-20 — "el título es largo"
- [open] 2026-08-20 — "cambiar el orden"

## 2. Segundo slide

### Presenter feedback

- [open] 2026-08-20 — "cambiar el orden"
'''

_BACKLOG = "# Feedback backlog\n\n## Entries\n\n<!-- Editor appends entries below this line. -->\n"


def _row(talk: str, loc: str, fb: str, res: str, tags: str, extra: str = "") -> str:
    return (f'- talk: {talk}\n  date: 2026-08-19\n  location: Slide "{loc}"\n  feedback: "{fb}"\n'
            f"  resolution: {res}\n  tags: [{tags}]\n{extra}")


# A backlog in the state the bug left it: rows A and B were "moved" to L8 but only copied, and A's
# slide was renamed afterwards (location drift). C and C' are twins — the same note pasted on two
# slides, resolved differently. D is untouched.
_B_ROWS = [
    _row("t", "1. Renombrado", "nota A", "res A", "x"),
    _row("t", "2. B", "nota B", "res B", "y"),
    _row("t", "3. C", "nota C", "res C3", "z"),
    _row("t", "4. C", "nota C", "res C4", "z"),
    _row("t", "5. D", "nota D", "res D", "w"),
]
_P_ROWS = [
    _row("t", "1. Original", "nota A", "res A", "x", "  promoted_to: L8\n  promoted_at: 2026-08-20\n"),
    _row("t", "2. B", "nota B", "res B", "y", "  promoted_to: L8\n  promoted_at: 2026-08-20\n"),
]
_PROCESSED = "# Feedback — processed\n\n## Entries\n\n<!-- Editor role appends entries below this line during the Step 8 Move pass. -->\n"

_RESULTS: list[tuple[str, bool]] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail and not ok else ''}")


def _run(tmp: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_CLI), *args], capture_output=True, text=True,
                          cwd=tmp, input=stdin)


def _feedbacks(path: Path) -> list[str]:
    return [r["fields"].get("feedback", "") for r in _parse_rows(path.read_text().splitlines())]


def mirror_tests(tmp: Path) -> None:
    print("mirror-row:")
    talk = tmp / "talks" / "t"
    talk.mkdir(parents=True)
    draft, backlog = talk / "draft.md", tmp / "feedback-backlog.md"
    draft.write_text(_DRAFT)
    backlog.write_text(_BACKLOG)
    d, b = str(draft), str(backlog)

    # Close line 7 first: it inserts a Resolution line, so "cambiar el orden" moves from 8 to 9.
    _run(tmp, "close", "--draft", d, "--line", "7", "--resolution", "acortado.")
    r = _run(tmp, "mirror-row", "--draft", d, "--backlog", b, "--line", "7",
             "--expect-text", "el título es largo", "--tags", "length")
    _record("mirror_row_accepts_matching_text", r.returncode == 0, r.stderr)

    _run(tmp, "close", "--draft", d, "--line", "9", "--resolution", "reordenado.")
    # The stale-line case: the caller still believes "cambiar el orden" is at line 8 (pre-close).
    # Line 8 is now the Resolution line; a stale line pointing at line 7 is the neighbour bullet.
    r = _run(tmp, "mirror-row", "--draft", d, "--backlog", b, "--line", "7",
             "--expect-text", '"cambiar el orden"', "--tags", "order")
    _record("stale_line_is_refused", r.returncode == 5 and "line(s) 9" in r.stderr,
            f"rc={r.returncode} {r.stderr}")
    _record("stale_line_writes_nothing", len(_feedbacks(backlog)) == 1, str(_feedbacks(backlog)))

    r = _run(tmp, "mirror-row", "--draft", d, "--backlog", b, "--line", "7",
             "--expect-text", "el título es largo", "--tags", "length")
    _record("duplicate_row_is_refused", r.returncode == 6 and len(_feedbacks(backlog)) == 1,
            f"rc={r.returncode} {r.stderr}")

    r = _run(tmp, "mirror-row", "--draft", d, "--backlog", b, "--line", "9",
             "--expect-text", "cambiar el orden", "--tags", "order")
    _record("first_twin_mirrors", r.returncode == 0, r.stderr)
    # The same verbatim on another slide is a different bullet, not a duplicate.
    _run(tmp, "close", "--draft", d, "--line", "16", "--resolution", "movido.")
    r = _run(tmp, "find-closed-unmirrored", "--draft", d, "--backlog", b, "--format", "json")
    pending = json.loads(r.stdout)
    _record("twin_on_another_slide_is_still_pending",
            [p["location"] for p in pending] == ['Slide "2. Segundo slide"'], r.stdout)
    r = _run(tmp, "mirror-row", "--draft", d, "--backlog", b, "--line", "16",
             "--expect-text", "cambiar el orden", "--tags", "order")
    _record("second_twin_mirrors", r.returncode == 0 and len(_feedbacks(backlog)) == 3, r.stderr)


def move_tests(tmp: Path) -> None:
    print("move:")
    backlog, processed = tmp / "feedback-backlog.md", tmp / "feedback-processed.md"
    backlog.write_text(_BACKLOG + "".join(_B_ROWS))
    processed.write_text(_PROCESSED + "".join(_P_ROWS))
    b, p = str(backlog), str(processed)
    before_b, before_p = backlog.read_text(), processed.read_text()

    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--rows", "-", "--promoted-to", "L9",
             stdin=json.dumps([{"talk": "t", "feedback": "nota C"}]))
    _record("ambiguous_selector_is_refused",
            r.returncode == 2 and "matches 2" in r.stderr and backlog.read_text() == before_b,
            r.stderr)
    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--rows", "-", "--promoted-to", "L9",
             stdin=json.dumps([{"talk": "t", "feedback": "nota D"}, {"talk": "t", "feedback": "nada"}]))
    _record("one_bad_selector_aborts_all",
            r.returncode == 2 and backlog.read_text() == before_b and processed.read_text() == before_p,
            r.stderr)
    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--rows", "-",
             stdin=json.dumps([{"talk": "t", "feedback": "nota D"}]))
    _record("promoted_to_is_required", r.returncode == 2, r.stderr)

    sel = [{"talk": "t", "feedback": "nota C", "location": 'Slide "3. C"'}]
    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--rows", "-", "--promoted-to", "L9",
             "--promoted-at", "2026-10-17", stdin=json.dumps(sel))
    _record("move_succeeds", r.returncode == 0, f"rc={r.returncode} {r.stderr}")
    left = _feedbacks(backlog)
    # Moved: C (3). Swept: A (location drifted, same resolution) and B (exact copy). Kept: C' and D.
    _record("backlog_keeps_only_unprocessed_rows",
            left == ['"nota C"', '"nota D"'], str(left))
    kept = _parse_rows(backlog.read_text().splitlines())
    _record("twin_survives_its_sibling_move", kept[0]["fields"].get("resolution") == "res C4",
            str(kept[0]["fields"]))
    rows = _parse_rows(processed.read_text().splitlines())
    last = rows[-1]["fields"]
    _record("archived_row_is_stamped",
            len(rows) == 3 and last.get("promoted_to") == "L9" and last.get("promoted_at") == "2026-10-17"
            and last.get("tags") == "[z]" and last.get("resolution") == "res C3", str(last))
    _record("processed_history_untouched", processed.read_text().startswith(before_p.rstrip("\n")))

    snap_b, snap_p = backlog.read_text(), processed.read_text()
    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--rows", "-", "--promoted-to", "L9",
             stdin=json.dumps(sel))
    _record("rerun_is_idempotent",
            r.returncode == 0 and "noop" in r.stdout and backlog.read_text() == snap_b
            and processed.read_text() == snap_p, f"rc={r.returncode} {r.stdout} {r.stderr}")

    # Crash between the two writes: the row is in processed and still in the backlog.
    backlog.write_text(snap_b + _B_ROWS[2])
    r = _run(tmp, "move", "--backlog", b, "--processed", p)
    _record("sweep_repairs_a_half_done_move",
            r.returncode == 0 and _feedbacks(backlog) == ['"nota C"', '"nota D"']
            and processed.read_text() == snap_p, f"rc={r.returncode} {r.stdout} {r.stderr}")

    r = _run(tmp, "move", "--backlog", b, "--processed", p, "--dry-run")
    _record("dry_run_on_clean_files_plans_nothing", r.returncode == 0 and "remove 0 row(s)" in r.stdout,
            r.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        mirror_tests(Path(td) / "m")
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "v").mkdir()
        move_tests(Path(td) / "v")
    failures = sum(1 for _, ok in _RESULTS if not ok)
    print()
    if failures:
        print(f"{failures} test(s) FAILED.")
        return 1
    print(f"all {len(_RESULTS)} backlog-integrity tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
