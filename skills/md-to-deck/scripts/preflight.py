#!/usr/bin/env python3
"""Step 1.5 — CHECK the model: every FILL audit in one command, one report.

Usage:
    python3 preflight.py --talk talks/<Talk>            # output/slide-model.json against final.md
    python3 preflight.py --talk talks/<Talk> --draft    # the live view: slide-model.draft.json
    python3 preflight.py --model <slide-model.json> --source <final.md>

The FILL is the LLM's judgment, so it can slip; the audits under `audits/` are the mechanical catch
before RENDER. They always run together — and again after every CLASSIFY-REVIEW change — so this
runs them all, in the order `SKILL.md` → *Step 1.5* explains, and keeps each one's own output and
exit code. What each audit checks, and why, is in its own module and in `SKILL.md`; this file
only decides which ones run and how their verdicts add up:

- **Blocking** — a non-zero exit stops the render: `degenerate_enum` (a one-item enumeration),
  `template_diversity` (a `fallback` slide), `text_coverage --strict-notes` (a speaker-notes line
  that never reached its slide).
- **Advisory** — exit 0 with a list to fix before the deliverable render: `field_coverage`,
  `image_coverage`, `notes_coverage`, `block_coverage`, and everything `template_diversity`
  reports besides a fallback.

`--draft` checks an in-progress live-view model: only the two shape audits, with `--warn-only` —
the coverage audits read `final.md`, which a model filled from `draft.md` is not measured against.

Exit codes: 0 = no blocking failure (advisories may still be listed); 1 = at least one blocking
audit failed — fix the model, then run this again; 2 = a file is missing.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AUDITS = Path(__file__).resolve().parent / "audits"


def plan(model: Path, source: Path, draft: bool) -> list[tuple[str, list[str]]]:
    """(audit, argv) in the order Step 1.5 runs them."""
    m, s = str(model), str(source)
    if draft:
        return [("degenerate_enum", [m, "--warn-only"]),
                ("template_diversity", [m, "--warn-only"])]
    return [("degenerate_enum", [m]),
            ("template_diversity", [m]),
            ("field_coverage", [m]),
            ("image_coverage", [s, m]),
            ("text_coverage", [s, m, "--strict-notes"]),
            ("notes_coverage", [m, "--source", s]),
            ("block_coverage", [m, "--source", s])]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--talk", type=Path, help="the Talk folder (uses output/slide-model.json and final.md)")
    ap.add_argument("--model", type=Path, help="the slide model, when not using --talk")
    ap.add_argument("--source", type=Path, help="the final.md it was filled from, when not using --talk")
    ap.add_argument("--draft", action="store_true", help="the live view: slide-model.draft.json, shape audits only")
    a = ap.parse_args(argv)

    if a.talk:
        model = a.model or a.talk / "output" / ("slide-model.draft.json" if a.draft else "slide-model.json")
        source = a.source or a.talk / "final.md"
    elif a.model:
        model, source = a.model, a.source or Path("final.md")
    else:
        ap.error("pass --talk, or --model (with --source)")
    missing = [p for p in ([model] if a.draft else [model, source]) if not p.is_file()]
    if missing:
        print("preflight: missing " + ", ".join(map(str, missing)), file=sys.stderr)
        return 2

    failed = []
    steps = plan(model, source, a.draft)
    for name, args in steps:
        r = subprocess.run([sys.executable, str(AUDITS / f"{name}.py"), *args], capture_output=True, text=True)
        verdict = "ok" if r.returncode == 0 else f"FAIL (exit {r.returncode})"
        if r.returncode:
            failed.append(name)
        print(f"── {name}: {verdict}")
        for out in (r.stdout, r.stderr):
            if out.strip():
                print(out.rstrip())
    print(f"\npreflight: {len(steps)} audits · "
          + (f"{len(failed)} blocking failure(s): {', '.join(failed)}" if failed else "no blocking failure"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
