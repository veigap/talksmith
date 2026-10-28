"""Headless Chrome, located once and run the same way by both exporters.

The export path deliberately has no browser-automation dependency: Chrome is driven by plain
command-line invocations (`--dump-dom`, `--print-to-pdf`, `--screenshot`) and everything it needs
to send back travels in the page's own DOM. That is what keeps the PDF and `.pptx` exports
runnable anywhere the HTML deck can be built, with nothing to install beyond a browser most
machines already have.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

# Ordered by "what a presenter is most likely to already have", macOS bundles first because the
# deck's other tooling is developed there. Any Chromium build works — nothing here uses a
# Chrome-only flag.
_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
_PATH = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
         "chrome", "microsoft-edge", "brave-browser"]


class ChromeMissing(RuntimeError):
    pass


def find() -> str | None:
    """The browser to drive, or None. `$TALKSMITH_CHROME` overrides every probe."""
    env = os.environ.get("TALKSMITH_CHROME")
    if env:
        return env if Path(env).exists() else None
    for p in _MAC:
        if Path(p).exists():
            return p
    for n in _PATH:
        found = shutil.which(n)
        if found:
            return found
    return None


def require() -> str:
    exe = find()
    if exe:
        return exe
    raise ChromeMissing(
        "no Chrome/Chromium found — the PDF and .pptx exports render through a headless browser.\n"
        "  Install Google Chrome, or point TALKSMITH_CHROME at an existing Chromium binary.\n"
        "  Probed: " + ", ".join(_MAC + _PATH))


def file_url(path: Path, query: str = "") -> str:
    """A `file://` URL for a local deck. Quoted because a Talk folder may hold spaces or
    accented characters, both of which are ordinary in the decks this renders."""
    url = "file://" + quote(str(Path(path).resolve()))
    return url + ("?" + query if query else "")


def run(args: list[str], url: str, timeout: int = 180, quiet: bool = True) -> bytes:
    """One headless invocation. Returns stdout.

    `--virtual-time-budget` is what makes this deterministic: Chrome fast-forwards timers instead
    of sleeping, so a deck whose harvest is gated on a 15s backstop still finishes in seconds,
    and the wait is bounded by work rather than by wall clock.
    """
    exe = require()
    cmd = [exe, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--hide-scrollbars"] + args + [url]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if proc.returncode != 0 and not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
        raise RuntimeError("chrome exited %d: %s" % (proc.returncode, " / ".join(err)))
    if not quiet and proc.stderr:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
    return proc.stdout
