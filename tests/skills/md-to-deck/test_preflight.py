#!/usr/bin/env python3
"""Tests for `preflight` — the FILL audits as one command.

Run:  python3 tests/skills/md-to-deck/test_preflight.py

The preflight adds no checks of its own; it runs the audits Step 1.5 always runs together. So the
property that matters is that it changes nothing about them: each audit's verdict inside the
preflight is the verdict that audit gives when run on its own, the overall exit is blocking exactly
when one of them failed, `--draft` runs only the shape audits in warn-only mode, and a missing
model is reported instead of half-run. The style-reference fixture is a good subject precisely
because it is *not* clean — it carries a `fallback` slide and a one-item enumeration on purpose —
so both verdicts get exercised.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "md-to-deck" / "scripts"
FIXTURE = ROOT / "tests" / "skills" / "md-to-deck"
sys.path.insert(0, str(SCRIPTS))
import preflight as P  # noqa: E402

FAILURES = 0


def _check(name: str, cond: bool, detail: str = "") -> None:
    global FAILURES
    FAILURES += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"\n      {detail}" if not cond and detail else ""))


def _run(*args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(SCRIPTS / "preflight.py"), *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    model, source = FIXTURE / "slide-model.json", FIXTURE / "final.md"
    code, out = _run("--model", str(model), "--source", str(source))
    verdicts = dict(re.findall(r"^── (\w+): (ok|FAIL)", out, re.M))
    _check("runs the seven Step-1.5 audits", len(verdicts) == 7, out[-400:])

    alone = {}
    for name, args in P.plan(model, source, draft=False):
        r = subprocess.run([sys.executable, str(SCRIPTS / "audits" / f"{name}.py"), *args], capture_output=True)
        alone[name] = "ok" if r.returncode == 0 else "FAIL"
    _check("each verdict is the audit's own, run alone", verdicts == alone, f"{verdicts} vs {alone}")
    _check("exit is blocking exactly when an audit failed",
           (code == 1) == ("FAIL" in alone.values()) and code in (0, 1), f"exit {code}")

    code, out = _run("--model", str(model), "--draft")
    drafted = re.findall(r"^── (\w+):", out, re.M)
    _check("--draft runs only the shape audits, warn-only",
           drafted == ["degenerate_enum", "template_diversity"] and code == 0, out[-300:])

    code, out = _run("--model", str(FIXTURE / "no-such-model.json"), "--source", str(source))
    _check("a missing model is reported, not half-run", code == 2 and "missing" in out, out)

    print()
    if FAILURES:
        print(f"{FAILURES} test(s) FAILED.")
        return 1
    print("all preflight tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
