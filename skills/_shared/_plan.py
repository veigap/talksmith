"""Plan-file plumbing shared by the two Step-6 polish skills.

`polish-ascii` and `polish-images` are deliberate siblings: same staged sequence (scan → extract →
prepare-render-args → stamp-renders → cleanup), same plan JSON envelope, same `gc` pass. Only the
*block* differs — a ` ```ascii ` fence versus a `<!-- generate-image: … -->` directive. Everything
around that block is identical, and when it lived in both files it drifted: one grew an `-o` flag
the other didn't, one's error text said "plan" where the other's said "plan JSON".

So the scaffolding lives here, imported the same way both already import `_context`:

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_shared"))
    from _plan import add_plan_args, load_plan, read_json_arg, referenced_stems

The block-specific parts — what a scan detects, what a sidecar holds, how a stamp is computed —
stay in each skill. This is the shared frame, not shared behavior.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Every `![…](images/<name>)` reference, including the ones inside the `<!-- aside: … -->` comments
# polish-images writes — the pattern is the same either way, so `gc` sees the same live set.
IMG_REF_RE = re.compile(r"!\[[^\]]*\]\(\s*(?:\./)?images/([^)\s]+?)\s*\)")
IMG_EXT_RE = re.compile(r"\.(svg|png|jpe?g|gif|webp|avif)$", re.IGNORECASE)


def add_plan_args(p: argparse.ArgumentParser) -> None:
    """The argument trio every plan-consuming subcommand takes."""
    p.add_argument("--final", required=True, help="path to the Talk's final.md")
    p.add_argument("--plan", required=True)
    p.add_argument("--dry-run", action="store_true")


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
